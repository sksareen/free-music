"""
Spotify Web Player client.

Extracts TOTP secrets from Spotify's JS bundle at runtime (like yt-dlp's jsinterp
extracts YouTube's signature cipher) and generates access tokens without a browser.

Two data paths:
  1. API mode: Full Spotify Web API via TOTP-authenticated tokens (richer data, rate limited)
  2. Embed mode: Scrapes the embed page for inline data (no rate limits, preview URLs)

Usage:
    from spotify import Spotify

    sp = Spotify()
    results = sp.search("Radiohead")
    track = sp.track("4uLU6hMCjMI75M1A2tKUQC")
    track_embed = sp.embed_track("4uLU6hMCjMI75M1A2tKUQC")  # no rate limit
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import time
from dataclasses import dataclass

import httpx
import pyotp

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

BASE = "https://open.spotify.com"
API = "https://api.spotify.com/v1"
PARTNER_API = "https://api-partner.spotify.com/pathfinder/v1/query"
CLIENT_TOKEN_URL = "https://clienttoken.spotify.com/v1/clienttoken"


# ── TOTP Cipher ──────────────────────────────────────────────────────

@dataclass
class _CipherSecret:
    """Transforms a raw secret from Spotify's JS bundle into a TOTP-compatible key.

    The algorithm (from the bundle's `tt` function):
      1. XOR each char code with (index % 33 + 9)
      2. Join the resulting ints as a string
      3. UTF-8 encode → hex → base32
    """
    raw: str
    version: int
    b32: str = ""

    def __post_init__(self):
        xored = [ord(c) ^ (i % 33 + 9) for i, c in enumerate(self.raw)]
        joined = "".join(str(n) for n in xored)
        hex_str = joined.encode("utf-8").hex()
        self.b32 = base64.b32encode(bytes.fromhex(hex_str)).decode("ascii")


@dataclass
class _Token:
    access_token: str
    expires_at: float
    client_id: str
    is_anonymous: bool

    @property
    def expired(self) -> bool:
        return time.time() * 1000 >= self.expires_at - 30_000  # 30s buffer


class Spotify:
    """Spotify Web Player client — no browser, no OAuth, no API keys needed."""

    def __init__(self, sp_dc: str | None = None):
        """
        Args:
            sp_dc: Optional sp_dc cookie for authenticated access.
                   Without it, you get anonymous access (search, public metadata).
        """
        self._client = httpx.Client(
            headers={"User-Agent": UA},
            cookies={"sp_dc": sp_dc} if sp_dc else {},
            follow_redirects=True,
            timeout=30.0,
        )
        self._secret: _CipherSecret | None = None
        self._token: _Token | None = None
        self._client_token: str | None = None
        self._client_token_expires: float = 0
        self._app_version: str = ""

    # ── Bundle + TOTP ────────────────────────────────────────────────

    def _extract_secret(self) -> _CipherSecret:
        """Fetch the web player JS bundle and extract the TOTP cipher secret."""
        page = self._client.get(f"{BASE}/").text
        bundle_match = re.search(r'(https://[^"\']+/web-player\.[0-9a-f]+\.js)', page)
        if not bundle_match:
            raise RuntimeError("Could not find web-player JS bundle URL")

        ver_match = re.search(r'"clientVersion"\s*:\s*"([^"]+)"', page)
        if ver_match:
            self._app_version = ver_match.group(1)

        bundle = self._client.get(bundle_match.group(1)).text

        secrets_match = re.search(
            r"""\[(\{secret:['"].+?version:\d+\}(?:,\{secret:['"].+?version:\d+\})*)\];\s*var\s""",
            bundle,
        )
        if not secrets_match:
            raise RuntimeError("Could not find TOTP secrets in JS bundle")

        entries: list[tuple[str, int]] = []
        for m in re.finditer(r"""\{secret:'((?:[^'\\]|\\.)*)'\s*,\s*version:(\d+)\}""", secrets_match.group(1)):
            entries.append((m.group(1).replace("\\'", "'"), int(m.group(2))))
        for m in re.finditer(r"""\{secret:"((?:[^"\\]|\\.)*)"\s*,\s*version:(\d+)\}""", secrets_match.group(1)):
            raw = m.group(1).replace('\\"', '"').replace("\\\\", "\\")
            ver = int(m.group(2))
            if not any(v == ver for _, v in entries):
                entries.append((raw, ver))

        if not entries:
            raise RuntimeError("Found secrets block but could not parse any entries")

        entries.sort(key=lambda e: e[1], reverse=True)
        raw, ver = entries[0]
        return _CipherSecret(raw=raw, version=ver)

    def _get_server_time(self) -> int:
        return self._client.get(f"{BASE}/api/server-time").json()["serverTime"]

    def _generate_totp(self, timestamp: int | None = None) -> tuple[str, str]:
        if not self._secret:
            self._secret = self._extract_secret()
        totp = pyotp.TOTP(self._secret.b32, digits=6, interval=30, digest=hashlib.sha1)
        code_client = totp.now()
        code_server = totp.at(timestamp) if timestamp else code_client
        return code_client, code_server

    # ── Token management ─────────────────────────────────────────────

    def _refresh_token(self) -> None:
        server_time = self._get_server_time()
        code_client, code_server = self._generate_totp(server_time)

        resp = self._client.get(
            f"{BASE}/api/token",
            params={
                "reason": "init",
                "productType": "web_player",
                "totp": code_client,
                "totpServer": code_server,
                "totpVer": str(self._secret.version),
            },
        )
        resp.raise_for_status()
        data = resp.json()

        token = data.get("accessToken")
        if not token:
            raise RuntimeError(f"No access token in response: {data}")

        self._token = _Token(
            access_token=token,
            expires_at=data.get("accessTokenExpirationTimestampMs", 0),
            client_id=data.get("clientId", ""),
            is_anonymous=data.get("isAnonymous", True),
        )

    @property
    def token(self) -> str:
        if not self._token or self._token.expired:
            self._refresh_token()
        return self._token.access_token

    def _refresh_client_token(self) -> None:
        _ = self.token
        resp = self._client.post(
            CLIENT_TOKEN_URL,
            json={
                "client_data": {
                    "client_version": self._app_version or "1.2.86.435.g4953b6a0",
                    "client_id": self._token.client_id,
                    "js_sdk_data": {
                        "device_brand": "Apple",
                        "device_model": "unknown",
                        "device_type": "computer",
                        "os": "macos",
                        "os_version": "unknown",
                    },
                },
            },
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        granted = resp.json().get("granted_token", {})
        self._client_token = granted.get("token")
        ttl = granted.get("expires_after_seconds", 7200)
        self._client_token_expires = time.time() + ttl - 60

    @property
    def client_token(self) -> str:
        if not self._client_token or time.time() >= self._client_token_expires:
            self._refresh_client_token()
        return self._client_token

    # ── HTTP helpers ─────────────────────────────────────────────────

    def _full_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "client-token": self.client_token,
            "app-platform": "WebPlayer",
            "spotify-app-version": self._app_version or "1.2.86.435.g4953b6a0",
            "Origin": "https://open.spotify.com",
            "Referer": "https://open.spotify.com/",
        }

    def _api_get(self, path: str, params: dict | None = None) -> dict:
        for attempt in range(3):
            resp = self._client.get(
                f"{API}{path}",
                params=params,
                headers=self._full_headers(),
            )
            if resp.status_code == 429:
                wait = int(resp.headers.get("Retry-After", 5)) + 1
                time.sleep(min(wait, 120))
                continue
            if resp.status_code == 401:
                self._token = None
                continue
            resp.raise_for_status()
            return resp.json()
        resp.raise_for_status()
        return {}

    # ── Embed scraper (no rate limits) ───────────────────────────────

    def _embed_get(self, entity_type: str, entity_id: str) -> dict:
        """Fetch entity data from the embed page (no auth needed, no rate limits)."""
        resp = self._client.get(
            f"{BASE}/embed/{entity_type}/{entity_id}",
            headers={"User-Agent": UA},
        )
        resp.raise_for_status()
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.+?)</script>', resp.text)
        if not m:
            raise RuntimeError(f"Could not find __NEXT_DATA__ in embed page for {entity_type}/{entity_id}")
        return json.loads(m.group(1))["props"]["pageProps"]["state"]["data"]

    def embed_track(self, track_id: str) -> dict:
        """Get track data via embed (includes preview URL, no rate limit)."""
        data = self._embed_get("track", track_id)
        e = data["entity"]
        return {
            "id": e["id"],
            "name": e["name"],
            "uri": e["uri"],
            "duration_ms": e.get("duration", 0),
            "explicit": e.get("isExplicit", False),
            "playable": e.get("isPlayable", False),
            "preview_url": e.get("audioPreview", {}).get("url"),
            "artists": [{"name": a["name"], "uri": a["uri"]} for a in e.get("artists", [])],
            "images": [
                {"url": img["url"], "width": img.get("maxWidth"), "height": img.get("maxHeight")}
                for img in e.get("visualIdentity", {}).get("image", [])
            ],
            "colors": {
                "background": e.get("visualIdentity", {}).get("backgroundBase"),
                "text": e.get("visualIdentity", {}).get("textBase"),
            },
        }

    def embed_album(self, album_id: str) -> dict:
        """Get album data via embed (includes track list with preview URLs)."""
        data = self._embed_get("album", album_id)
        e = data["entity"]
        tracks = []
        for t in e.get("trackList", []):
            tracks.append({
                "uri": t["uri"],
                "title": t.get("title", ""),
                "subtitle": t.get("subtitle", ""),
                "duration_ms": t.get("duration", 0),
                "explicit": t.get("isExplicit", False),
                "playable": t.get("isPlayable", False),
                "preview_url": t.get("audioPreview", {}).get("url"),
            })
        return {
            "id": e["id"],
            "name": e["name"],
            "uri": e["uri"],
            "subtitle": e.get("subtitle", ""),
            "track_count": len(tracks),
            "tracks": tracks,
        }

    def embed_playlist(self, playlist_id: str) -> dict:
        """Get playlist data via embed (includes track list with preview URLs)."""
        data = self._embed_get("playlist", playlist_id)
        e = data["entity"]
        tracks = []
        for t in e.get("trackList", []):
            artists = [{"name": a["name"], "uri": a.get("uri", "")} for a in t.get("artists", [])]
            tracks.append({
                "uri": t["uri"],
                "title": t.get("title", ""),
                "artists": artists,
                "duration_ms": t.get("duration", 0),
                "explicit": t.get("isExplicit", False),
                "preview_url": t.get("audioPreview", {}).get("url"),
            })
        return {
            "id": e["id"],
            "name": e["name"],
            "uri": e["uri"],
            "subtitle": e.get("subtitle", ""),
            "track_count": len(tracks),
            "tracks": tracks,
        }

    def embed_artist(self, artist_id: str) -> dict:
        """Get artist data via embed."""
        data = self._embed_get("artist", artist_id)
        e = data["entity"]
        tracks = []
        for t in e.get("trackList", []):
            tracks.append({
                "uri": t["uri"],
                "title": t.get("title", ""),
                "subtitle": t.get("subtitle", ""),
                "duration_ms": t.get("duration", 0),
                "preview_url": t.get("audioPreview", {}).get("url"),
            })
        return {
            "id": e["id"],
            "name": e["name"],
            "uri": e["uri"],
            "top_tracks": tracks,
            "images": [
                {"url": img["url"], "width": img.get("maxWidth"), "height": img.get("maxHeight")}
                for img in e.get("visualIdentity", {}).get("image", [])
            ],
        }

    # ── Public API (v1) — needs token, may hit rate limits ───────────

    def search(self, query: str, types: str = "track,artist,album", limit: int = 10, market: str = "US") -> dict:
        return self._api_get("/search", {"q": query, "type": types, "limit": limit, "market": market})

    def track(self, track_id: str, market: str = "US") -> dict:
        return self._api_get(f"/tracks/{track_id}", {"market": market})

    def tracks(self, track_ids: list[str], market: str = "US") -> dict:
        return self._api_get("/tracks", {"ids": ",".join(track_ids[:50]), "market": market})

    def album(self, album_id: str, market: str = "US") -> dict:
        return self._api_get(f"/albums/{album_id}", {"market": market})

    def album_tracks(self, album_id: str, limit: int = 50, market: str = "US") -> dict:
        return self._api_get(f"/albums/{album_id}/tracks", {"limit": limit, "market": market})

    def artist(self, artist_id: str) -> dict:
        return self._api_get(f"/artists/{artist_id}")

    def artist_top_tracks(self, artist_id: str, market: str = "US") -> dict:
        return self._api_get(f"/artists/{artist_id}/top-tracks", {"market": market})

    def artist_albums(self, artist_id: str, limit: int = 20, market: str = "US") -> dict:
        return self._api_get(f"/artists/{artist_id}/albums", {
            "limit": limit, "market": market, "include_groups": "album,single",
        })

    def artist_related(self, artist_id: str) -> dict:
        return self._api_get(f"/artists/{artist_id}/related-artists")

    def playlist(self, playlist_id: str, market: str = "US") -> dict:
        return self._api_get(f"/playlists/{playlist_id}", {"market": market})

    def playlist_tracks(self, playlist_id: str, limit: int = 100, offset: int = 0) -> dict:
        return self._api_get(f"/playlists/{playlist_id}/tracks", {"limit": limit, "offset": offset})

    def user(self, user_id: str) -> dict:
        return self._api_get(f"/users/{user_id}")

    def categories(self, limit: int = 50, country: str = "US") -> dict:
        return self._api_get("/browse/categories", {"limit": limit, "country": country})

    def new_releases(self, limit: int = 20, country: str = "US") -> dict:
        return self._api_get("/browse/new-releases", {"limit": limit, "country": country})

    def recommendations(
        self,
        seed_artists: list[str] | None = None,
        seed_tracks: list[str] | None = None,
        seed_genres: list[str] | None = None,
        limit: int = 20,
    ) -> dict:
        params: dict = {"limit": limit}
        if seed_artists:
            params["seed_artists"] = ",".join(seed_artists[:5])
        if seed_tracks:
            params["seed_tracks"] = ",".join(seed_tracks[:5])
        if seed_genres:
            params["seed_genres"] = ",".join(seed_genres[:5])
        return self._api_get("/recommendations", params)

    # ── oEmbed (lightweight metadata, always works) ──────────────────

    def oembed(self, spotify_url: str) -> dict:
        """Get lightweight metadata via oEmbed. Always works, no auth needed."""
        resp = self._client.get(f"{BASE}/oembed", params={"url": spotify_url})
        resp.raise_for_status()
        return resp.json()

    # ── Convenience ──────────────────────────────────────────────────

    @property
    def info(self) -> dict:
        _ = self.token
        return {
            "client_id": self._token.client_id,
            "is_anonymous": self._token.is_anonymous,
            "expires_at": self._token.expires_at,
            "secret_version": self._secret.version if self._secret else None,
            "app_version": self._app_version,
        }

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
