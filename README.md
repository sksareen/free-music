# spotify-client

Spotify Web Player client in Python. No browser, no OAuth, no API keys needed.

Extracts TOTP secrets from Spotify's JS bundle at runtime (like [yt-dlp](https://github.com/yt-dlp/yt-dlp) extracts YouTube's signature cipher) and generates access tokens programmatically.

## How it works

```
1. Fetch open.spotify.com → extract JS bundle URL
2. Fetch web-player.HASH.js (4.4MB) → regex-extract TOTP secrets
3. XOR transform: charCode ^ (index % 33 + 9) → base32
4. Generate RFC 6238 TOTP (SHA1, 6 digits, 30s)
5. GET /api/token with TOTP → Bearer access token
```

Two data paths:

| Path | Auth | Rate limited | Data |
|------|------|-------------|------|
| **Embed** | None | No | Track/album/playlist metadata, 30s MP3 preview URLs, album art, colors |
| **API** | TOTP token | Yes | Full metadata: popularity, followers, genres, ISRC, markets, search |

## Install

```bash
uv sync
```

## Usage

### As a library

```python
from spotify import Spotify

sp = Spotify()

# Embed path (no rate limits)
track = sp.embed_track("3n3Ppam7vgaVa1iaRUc9Lp")
track["name"]         # "Mr. Brightside"
track["preview_url"]  # https://p.scdn.co/mp3-preview/...
track["artists"]      # [{"name": "The Killers", "uri": "..."}]

album = sp.embed_album("2noRn2Aes5aoNVsU6iWThc")  # Discovery - Daft Punk
playlist = sp.embed_playlist("37i9dQZF1DXcBWIGoYBM5M")  # Today's Top Hits
artist = sp.embed_artist("4Z8W4fKeB5YxbusRsdQVPb")  # Radiohead

# API path (richer data, may rate limit)
sp.search("Radiohead", types="track", limit=5)
sp.track("3n3Ppam7vgaVa1iaRUc9Lp")
sp.artist("4Z8W4fKeB5YxbusRsdQVPb")
sp.artist_top_tracks("4Z8W4fKeB5YxbusRsdQVPb")
sp.new_releases()
```

### Decades player

A terminal music player that plays the biggest hit of every year from 1960 to 2025. Features album art (iTerm2), color theming from album colors, audio waveform visualization, and AI-generated fun facts + DJ transitions.

```bash
uv run python decades.py
```

**Controls:** `←`/`→` prev/next, `space` play/pause, `a` toggle auto-advance, `q` quit

**Requirements:** `ffplay` (from ffmpeg) for audio playback, iTerm2 for album art display, `OPENROUTER_API_KEY` env var for AI DJ (optional).

### Simple player

10 classic tracks with preview playback:

```bash
uv run python app.py
```

### Demo

Exercises all API methods:

```bash
uv run python demo.py
```

## Dependencies

- `httpx` — HTTP client
- `pyotp` — TOTP generation
- `openai` — OpenRouter API for AI DJ (only used by decades.py)

## How the TOTP cipher works

Spotify embeds TOTP secrets in their minified web player JS bundle:

```javascript
let e4 = [
  {secret: ',7/*F("rLJ2oxaKL^f+E1xvP@N', version: 61},
  {secret: 'OmE{ZA.J^":0FG\\Uz?[@WW', version: 60},
  // ...
];
```

The `tt` transform function XORs each character code with `(index % 33 + 9)`, joins the results as a digit string, hex-encodes, and base32-encodes. The result is a standard TOTP secret (SHA1, 6 digits, 30s interval).

Secrets rotate when Spotify deploys a new bundle (the hash in the URL changes). This client extracts them at runtime, so it adapts automatically — just like yt-dlp's JS interpreter adapts to YouTube's signature cipher rotations.
