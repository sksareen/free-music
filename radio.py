"""Infinite Radio — AI-curated music exploration via Spotify previews.

Run: uv run python radio.py
Open: http://localhost:8000
"""

from __future__ import annotations

import json
import os
import random
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from openai import OpenAI
from pydantic import BaseModel

from spotify import Spotify

app = FastAPI()
sp = Spotify()

openrouter = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY", ""),
)

# Verified track IDs with previews (from decades.py + extras)
KNOWN_TRACKS: dict[str, str] = {
    "3n3Ppam7vgaVa1iaRUc9Lp": "Mr. Brightside — The Killers",
    "7tFiyTwD0nx5a1eklYtX2J": "Bohemian Rhapsody — Queen",
    "0VjIjW4GlUZAMYd2vXMi3b": "Blinding Lights — The Weeknd",
    "4PTG3Z6ehGkBFwjybzWkR8": "Never Gonna Give You Up — Rick Astley",
    "7qiZfU4dY1lWllzX7mPBI3": "Shape of You — Ed Sheeran",
    "0aym2LBJBk9DAYuHHutrIl": "Hey Jude — The Beatles",
    "2qSkIjg1o9h3YT9RAgYN75": "Espresso — Sabrina Carpenter",
    "4eHbdreAnSOrDDsFfc4Fpm": "I Will Always Love You — Whitney Houston",
    "7o2CTH4ctstm8TNelqjb51": "Sweet Child O' Mine — Guns N' Roses",
    "32OlwWuMpZ6b0aN2RZOeMS": "Uptown Funk — Mark Ronson ft. Bruno Mars",
    "1DIXPcTDzTj8ZMHt3PDt8p": "Gangsta's Paradise — Coolio",
    "4YCnTYbq3oL1Lqpyxg33CU": "The Twist — Chubby Checker",
    "4pbG9SUmWIvsROVLF0zF9s": "I Want to Hold Your Hand — The Beatles",
    "3BQHpFgAp4l80e1XslIjNI": "Yesterday — The Beatles",
    "5t9KYe0Fhd5cW6UYT4qP8f": "Good Vibrations — The Beach Boys",
    "5AoTuHE5P5bvC7BBppYnja": "Respect — Aretha Franklin",
    "6l8EbYRtQMgKOyc1gcDHF9": "Bridge Over Troubled Water — Simon & Garfunkel",
    "7pKfPomDEeI4TPT6EOYjn9": "Imagine — John Lennon",
    "3M8FzayQWtkvOhqMn2V4T2": "Lean on Me — Bill Withers",
    "40riOy7x9W7GXjyGp4pjAv": "Hotel California — Eagles",
    "4UDmDIqJIbrW0hMBQMFOsM": "Stayin' Alive — Bee Gees",
    "57JVGBtBLCfHw2muk5416J": "Another One Bites the Dust — Queen",
    "5ehcf6UL1TkwozB386cRAp": "Don't Stop Believin' — Journey",
    "2KH16WveTQWT6KOG9Rg6e2": "Eye of the Tiger — Survivor",
    "1JSTJqkT5qHq8MDJnJbRE1": "Every Breath You Take — The Police",
    "4jDmJ51x1o9NZB5Nxxc7gY": "Careless Whisper — George Michael",
    "14p4jbULrRxZvnSt4NDSEs": "Like a Prayer — Madonna",
    "4hy4fb5D1KL50b3sng9cjw": "Smells Like Teen Spirit — Nirvana",
    "0Q0IVlqMV64kNLlwjPj0Hl": "Killing Me Softly — Fugees",
    "3MjUtNVVq3C8Fn0MP3zhXa": "...Baby One More Time — Britney Spears",
    "0i69ZiWitf3SFiaTA8249M": "Smooth — Santana ft. Rob Thomas",
    "7iL6o9tox1zgHpKUfh9vuC": "In da Club — 50 Cent",
    "5IVuqXILoxVWvWEPm82Jxr": "Crazy in Love — Beyoncé",
    "5rb9QrpfcKFHM1EUbSIurX": "Yeah! — Usher",
    "3ZFTkvIE7kyPt6Nu3PEa7V": "Hips Don't Lie — Shakira",
    "49FYlytm3dAAraYgpoJZux": "Umbrella — Rihanna",
    "0Mf44YldPCnOetNeaOEdjQ": "Poker Face — Lady Gaga",
    "6IAZHEBUIGJ6NJKxxOBIEr": "Rolling in the Deep — Adele",
    "4wCmqSrbyCgxEXROQE6vtV": "Somebody That I Used to Know — Gotye",
    "6NPVjNh8Jhru9xOmyQigds": "Happy — Pharrell Williams",
    "1zi7xx7UVEFkmKfv06H8x0": "One Dance — Drake",
    "6DCZcSspjsKoFjzjrWoCdn": "God's Plan — Drake",
    "2YlZnhMnbLCBJghZPyBleA": "Old Town Road — Lil Nas X",
    "5HCyWlXZPP0y6Gqq8TgA20": "Stay — The Kid LAROI & Justin Bieber",
    "4LRPiXqCikLlN15c3yImP7": "As It Was — Harry Styles",
    "0yLdNVWF3Srea0uzk55zFn": "Flowers — Miley Cyrus",
    "5vNRhkKd0yEAg8suGBpjeY": "APT. — ROSÉ & Bruno Mars",
}

SEEDS = list(KNOWN_TRACKS.keys())

# In-memory embed cache
_embed_cache: dict[str, dict] = {}


def get_embed(track_id: str) -> dict | None:
    """Get embed data for a track, with caching."""
    if track_id in _embed_cache:
        return _embed_cache[track_id]
    try:
        data = sp.embed_track(track_id)
        if data.get("preview_url"):
            _embed_cache[track_id] = data
            return data
    except Exception:
        pass
    return None


def format_track(data: dict, intro: str = "") -> dict:
    """Format embed data into the API response shape."""
    return {
        "id": data["id"],
        "name": data["name"],
        "artists": ", ".join(a["name"] for a in data.get("artists", [])),
        "preview_url": data.get("preview_url"),
        "image_url": data["images"][-1]["url"] if data.get("images") else None,
        "image_small": data["images"][0]["url"] if data.get("images") else None,
        "bg_color": data.get("colors", {}).get("background"),
        "text_color": data.get("colors", {}).get("text"),
        "duration_ms": data.get("duration_ms", 30000),
        "intro": intro,
    }


def _fast_search(query: str, limit: int = 5) -> list[dict]:
    """Search Spotify API with a short timeout — returns [] on rate limit instead of blocking."""
    import httpx as _httpx
    try:
        resp = _httpx.get(
            f"https://api.spotify.com/v1/search",
            params={"q": query, "type": "track", "limit": limit, "market": "US"},
            headers=sp._full_headers(),
            timeout=10.0,
        )
        if resp.status_code == 200:
            return resp.json().get("tracks", {}).get("items", [])
    except Exception:
        pass
    return []


def _name_match(expected: str, actual: str) -> bool:
    """Check if track names roughly match (LLM IDs are often hallucinated)."""
    e = expected.lower().split(" - ")[0].split(" (")[0].strip()
    a = actual.lower().split(" - ")[0].split(" (")[0].strip()
    # Check if one contains the other, or significant word overlap
    if e in a or a in e:
        return True
    e_words = set(e.split())
    a_words = set(a.split())
    if len(e_words & a_words) >= min(2, len(e_words)):
        return True
    return False


def resolve_track(name: str, artist: str, spotify_id: str | None = None) -> dict | None:
    """Resolve a track name + artist to embed data with a preview URL."""
    # Try provided ID first — but verify the name matches
    if spotify_id and len(spotify_id) >= 20:
        data = get_embed(spotify_id)
        if data and _name_match(name, data["name"]):
            return data

    # Fast search — doesn't block on rate limits
    items = _fast_search(f"{name} {artist}")
    for item in items:
        data = get_embed(item["id"])
        if data:
            return data

    return None


class NextRequest(BaseModel):
    current_name: str
    current_artist: str
    current_id: str
    history: list[dict]  # [{name, artist, id}, ...]


@app.get("/", response_class=HTMLResponse)
async def index():
    return Path(__file__).parent.joinpath("radio.html").read_text()


@app.get("/api/start")
async def start():
    """Return a random seed track."""
    random.shuffle(SEEDS)
    for seed_id in SEEDS:
        data = get_embed(seed_id)
        if data:
            return format_track(data, intro="Welcome to Infinite Radio. Let the journey begin.")
    return JSONResponse({"error": "No seed tracks available"}, status_code=500)


@app.post("/api/next")
async def next_track(req: NextRequest):
    """Use AI to pick the next track, resolve it, return with intro."""
    played_names = [f'"{h["name"]}" by {h["artist"]}' for h in req.history[-30:]]
    played_ids = {h["id"] for h in req.history}
    played_ids.add(req.current_id)

    history_str = "\n".join(f"  - {n}" for n in played_names[-10:]) if played_names else "  (none yet)"

    for attempt in range(3):
        try:
            resp = openrouter.chat.completions.create(
                model="google/gemini-2.0-flash-001",
                messages=[{
                    "role": "user",
                    "content": f"""You are Infinite Radio, an AI DJ creating a seamless musical journey.
Pick the next track based on the current song and listening history.
Create connections through genre, mood, era, artist relationships, or thematic links.
Surprise the listener — don't just pick obvious choices. Mix eras and genres when it feels right.
IMPORTANT: Only suggest well-known, popular tracks that are definitely on Spotify with preview audio.

Currently playing: "{req.current_name}" by {req.current_artist}

Recent history:
{history_str}

DO NOT suggest any track already played above.
{"IMPORTANT: The last suggestion could not be found on Spotify. Pick a more mainstream/popular track this time." if attempt > 0 else ""}

Respond in this exact JSON format (no markdown, no code blocks, no explanation outside JSON):
{{"track_name": "...", "artist_name": "...", "spotify_id": "the 22-character Spotify track ID from the track's Spotify URL — VERY important to include", "intro": "One to two sentences explaining why this track follows naturally. Be specific about the musical connection. Write as a radio DJ."}}""",
                }],
                max_tokens=250,
            )

            text = resp.choices[0].message.content.strip()
            # Strip markdown code blocks if present
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
            if text.endswith("```"):
                text = text.rsplit("```", 1)[0]
            text = text.strip()

            suggestion = json.loads(text)
            track_name = suggestion["track_name"]
            artist_name = suggestion["artist_name"]
            intro = suggestion.get("intro", "")
            spotify_id = suggestion.get("spotify_id")

            data = resolve_track(track_name, artist_name, spotify_id)
            if data and data["id"] not in played_ids:
                return format_track(data, intro=intro)

        except Exception:
            continue

    # Fallback: ask LLM to pick from our verified catalog
    available = {tid: desc for tid, desc in KNOWN_TRACKS.items() if tid not in played_ids}
    if available:
        try:
            catalog_str = "\n".join(f"  {tid}: {desc}" for tid, desc in list(available.items())[:30])
            resp = openrouter.chat.completions.create(
                model="google/gemini-2.0-flash-001",
                messages=[{
                    "role": "user",
                    "content": f"""Pick the best next track from this catalog to follow "{req.current_name}" by {req.current_artist}.

Available tracks:
{catalog_str}

Respond in JSON (no markdown): {{"spotify_id": "the ID from the list above", "intro": "One sentence DJ intro explaining the connection."}}""",
                }],
                max_tokens=150,
            )
            text = resp.choices[0].message.content.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
            if text.endswith("```"):
                text = text.rsplit("```", 1)[0]
            pick = json.loads(text.strip())
            pick_id = pick.get("spotify_id", "")
            if pick_id in available:
                data = get_embed(pick_id)
                if data:
                    return format_track(data, intro=pick.get("intro", ""))
        except Exception:
            pass

        # Final fallback: first available from catalog
        for tid in available:
            data = get_embed(tid)
            if data:
                return format_track(data, intro="")

    return JSONResponse({"error": "Could not find next track"}, status_code=500)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("radio:app", host="0.0.0.0", port=8000, reload=True)
