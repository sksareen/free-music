"""Spotify Decades — biggest hit of every year, 1960–2025.

Album art, color theming, waveform visualization, AI-generated fun facts & transitions.

Run: uv run python decades.py

Controls:
  →/n  next track (auto-plays)
  ←/p  previous track
  space  play/pause
  a  toggle auto-advance
  q  quit
"""

import json
import os
import select
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import time
import tty
import termios

import httpx

from spotify import Spotify

HITS = [
    (1960, "4YCnTYbq3oL1Lqpyxg33CU", "The Twist — Chubby Checker"),
    (1961, "7HDQqox0O0fTE7elQu4XxS", "Tossin' and Turnin' — Bobby Lewis"),
    (1962, "79nJj5dMyTsUzKvN5jUXsJ", "I Can't Stop Loving You — Ray Charles"),
    (1963, "2nLLenueHlqs60IcDn9lan", "Sugar Shack — Jimmy Gilmer"),
    (1964, "4pbG9SUmWIvsROVLF0zF9s", "I Want to Hold Your Hand — The Beatles"),
    (1965, "3BQHpFgAp4l80e1XslIjNI", "Yesterday — The Beatles"),
    (1966, "5t9KYe0Fhd5cW6UYT4qP8f", "Good Vibrations — The Beach Boys"),
    (1967, "5AoTuHE5P5bvC7BBppYnja", "Respect — Aretha Franklin"),
    (1968, "0aym2LBJBk9DAYuHHutrIl", "Hey Jude — The Beatles"),
    (1969, "0HZlND4giwzgolBpaNIRGV", "Aquarius/Let the Sunshine In — The 5th Dimension"),
    (1970, "6l8EbYRtQMgKOyc1gcDHF9", "Bridge Over Troubled Water — Simon & Garfunkel"),
    (1971, "7pKfPomDEeI4TPT6EOYjn9", "Imagine — John Lennon"),
    (1972, "3M8FzayQWtkvOhqMn2V4T2", "Lean on Me — Bill Withers"),
    (1973, "3gsCAGsWr6pUm1Vy7CPPob", "Killing Me Softly — Roberta Flack"),
    (1974, "7pGMRy91RcQT9oHdPgYz3A", "Seasons in the Sun — Terry Jacks"),
    (1975, "7tFiyTwD0nx5a1eklYtX2J", "Bohemian Rhapsody — Queen"),
    (1976, "5pKJtX4wBeby9qIfFhyOJj", "Don't Go Breaking My Heart — Elton John"),
    (1977, "40riOy7x9W7GXjyGp4pjAv", "Hotel California — Eagles"),
    (1978, "4UDmDIqJIbrW0hMBQMFOsM", "Stayin' Alive — Bee Gees"),
    (1979, "1HOMkjp0nHMaTnfAkslCQj", "My Sharona — The Knack"),
    (1980, "57JVGBtBLCfHw2muk5416J", "Another One Bites the Dust — Queen"),
    (1981, "5ehcf6UL1TkwozB386cRAp", "Don't Stop Believin' — Journey"),
    (1982, "2KH16WveTQWT6KOG9Rg6e2", "Eye of the Tiger — Survivor"),
    (1983, "1JSTJqkT5qHq8MDJnJbRE1", "Every Breath You Take — The Police"),
    (1984, "1ZPlNanZsJSPK5h9YZZFbZ", "Like a Virgin — Madonna"),
    (1985, "4jDmJ51x1o9NZB5Nxxc7gY", "Careless Whisper — George Michael"),
    (1986, "5L6HNuXN71bfeuKXYtRasF", "Walk Like an Egyptian — The Bangles"),
    (1987, "4PTG3Z6ehGkBFwjybzWkR8", "Never Gonna Give You Up — Rick Astley"),
    (1988, "7o2CTH4ctstm8TNelqjb51", "Sweet Child O' Mine — Guns N' Roses"),
    (1989, "14p4jbULrRxZvnSt4NDSEs", "Like a Prayer — Madonna"),
    (1990, "07iHAswcApphvyllRDQrEa", "Nothing Compares 2 U — Sinead O'Connor"),
    (1991, "4hy4fb5D1KL50b3sng9cjw", "Smells Like Teen Spirit — Nirvana"),
    (1992, "4eHbdreAnSOrDDsFfc4Fpm", "I Will Always Love You — Whitney Houston"),
    (1993, "4UrgDocbHywDZv2f3mBhCq", "I'd Do Anything for Love — Meat Loaf"),
    (1994, "3ZpQiJ78LKINrW9SQTgbXd", "All I Wanna Do — Sheryl Crow"),
    (1995, "1DIXPcTDzTj8ZMHt3PDt8p", "Gangsta's Paradise — Coolio"),
    (1996, "0Q0IVlqMV64kNLlwjPj0Hl", "Killing Me Softly — Fugees"),
    (1997, "0lnxrQAd9ZxbhBBe7d8FO8", "MMMBop — Hanson"),
    (1998, "3MjUtNVVq3C8Fn0MP3zhXa", "...Baby One More Time — Britney Spears"),
    (1999, "0i69ZiWitf3SFiaTA8249M", "Smooth — Santana ft. Rob Thomas"),
    (2000, "1MPuke7OnvKkUAEq7KVeQr", "Breathe — Faith Hill"),
    (2001, "0wqOReZDnrefefEsrIGeR4", "Hanging by a Moment — Lifehouse"),
    (2002, "7iL6o9tox1zgHpKUfh9vuC", "In da Club — 50 Cent"),
    (2003, "5IVuqXILoxVWvWEPm82Jxr", "Crazy in Love — Beyoncé"),
    (2004, "5rb9QrpfcKFHM1EUbSIurX", "Yeah! — Usher"),
    (2005, "3LmvfNUQtglbTrydsdIqFU", "We Belong Together — Mariah Carey"),
    (2006, "3ZFTkvIE7kyPt6Nu3PEa7V", "Hips Don't Lie — Shakira"),
    (2007, "49FYlytm3dAAraYgpoJZux", "Umbrella — Rihanna"),
    (2008, "0CAfXk7DXMnon4gLudAp7J", "Low — Flo Rida"),
    (2009, "0Mf44YldPCnOetNeaOEdjQ", "Poker Face — Lady Gaga"),
    (2010, "0HPD5WQqrq7wPWR7P7Dw1i", "TiK ToK — Kesha"),
    (2011, "6IAZHEBUIGJ6NJKxxOBIEr", "Rolling in the Deep — Adele"),
    (2012, "4wCmqSrbyCgxEXROQE6vtV", "Somebody That I Used to Know — Gotye"),
    (2013, "5PUvinSo4MNqW7vmomGRS7", "Blurred Lines — Robin Thicke"),
    (2014, "6NPVjNh8Jhru9xOmyQigds", "Happy — Pharrell Williams"),
    (2015, "32OlwWuMpZ6b0aN2RZOeMS", "Uptown Funk — Mark Ronson ft. Bruno Mars"),
    (2016, "1zi7xx7UVEFkmKfv06H8x0", "One Dance — Drake"),
    (2017, "7qiZfU4dY1lWllzX7mPBI3", "Shape of You — Ed Sheeran"),
    (2018, "6DCZcSspjsKoFjzjrWoCdn", "God's Plan — Drake"),
    (2019, "2YlZnhMnbLCBJghZPyBleA", "Old Town Road — Lil Nas X"),
    (2020, "0VjIjW4GlUZAMYd2vXMi3b", "Blinding Lights — The Weeknd"),
    (2021, "5HCyWlXZPP0y6Gqq8TgA20", "Stay — The Kid LAROI & Justin Bieber"),
    (2022, "4LRPiXqCikLlN15c3yImP7", "As It Was — Harry Styles"),
    (2023, "0yLdNVWF3Srea0uzk55zFn", "Flowers — Miley Cyrus"),
    (2024, "2qSkIjg1o9h3YT9RAgYN75", "Espresso — Sabrina Carpenter"),
    (2025, "5vNRhkKd0yEAg8suGBpjeY", "APT. — ROSÉ & Bruno Mars"),
]

CACHE_FILE = os.path.join(os.path.dirname(__file__), ".track_cache.json")
AI_CACHE_FILE = os.path.join(os.path.dirname(__file__), ".ai_cache.json")

IMGCAT = shutil.which("imgcat") or os.path.expanduser(
    "~/Applications/iTerm.app/Contents/Resources/utilities/imgcat"
)

# ── ANSI color helpers ───────────────────────────────────────────────


def rgb_fg(r: int, g: int, b: int) -> str:
    return f"\033[38;2;{r};{g};{b}m"


def rgb_bg(r: int, g: int, b: int) -> str:
    return f"\033[48;2;{r};{g};{b}m"


RESET = "\033[0m"
DIM = "\033[2m"
BOLD = "\033[1m"


def color_from_spotify(c: dict | None, fallback=(180, 180, 180)) -> tuple[int, int, int]:
    if c:
        return (c.get("red", 180), c.get("green", 180), c.get("blue", 180))
    return fallback


# ── Cache helpers ────────────────────────────────────────────────────


def load_json_cache(path: str) -> dict:
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}


def save_json_cache(path: str, data: dict):
    with open(path, "w") as f:
        json.dump(data, f, ensure_ascii=False)


# ── Track loading ────────────────────────────────────────────────────


def load_tracks(sp: Spotify) -> list[dict]:
    cache = load_json_cache(CACHE_FILE)
    tracks = []
    changed = False

    for year, track_id, fallback in HITS:
        if track_id in cache:
            tracks.append(cache[track_id])
            continue

        try:
            t = sp.embed_track(track_id)
            entry = {
                "year": year,
                "id": track_id,
                "name": t["name"],
                "artists": ", ".join(a["name"] for a in t.get("artists", [])),
                "preview_url": t.get("preview_url"),
                "duration_ms": t.get("duration_ms", 0),
                "image_url": t["images"][-1]["url"] if t.get("images") else None,  # largest
                "bg_color": t.get("colors", {}).get("background"),
                "text_color": t.get("colors", {}).get("text"),
            }
        except Exception:
            name_part = fallback.split(" — ")
            entry = {
                "year": year,
                "id": track_id,
                "name": name_part[0],
                "artists": name_part[1] if len(name_part) > 1 else "",
                "preview_url": None,
                "duration_ms": 0,
                "image_url": None,
                "bg_color": None,
                "text_color": None,
            }

        cache[track_id] = entry
        tracks.append(entry)
        changed = True
        sys.stdout.write(f"\r  Loading... {year} {entry['name'][:30]:<30s}")
        sys.stdout.flush()

    if changed:
        save_json_cache(CACHE_FILE, cache)
        sys.stdout.write("\r" + " " * 60 + "\r")
        sys.stdout.flush()

    return tracks


# ── AI DJ (fun facts + transitions) ─────────────────────────────────


class AIDJ:
    """Generates and caches fun facts and transitions via OpenRouter."""

    def __init__(self, tracks: list[dict]):
        self.tracks = tracks
        self._cache = load_json_cache(AI_CACHE_FILE)
        self._client = None
        self._pending: set[str] = set()
        self._lock = threading.Lock()

    def _get_client(self):
        if not self._client:
            from openai import OpenAI
            api_key = os.environ.get("OPENROUTER_API_KEY", "")
            if not api_key:
                return None
            self._client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=api_key,
            )
        return self._client

    def _cache_key(self, idx: int) -> str:
        t = self.tracks[idx]
        return f"{t['year']}_{t['id']}"

    def get(self, idx: int) -> dict | None:
        """Return cached {fact, transition} or None."""
        key = self._cache_key(idx)
        with self._lock:
            return self._cache.get(key)

    def ensure(self, idx: int):
        """Generate fact+transition in background if not cached."""
        key = self._cache_key(idx)
        with self._lock:
            if key in self._cache or key in self._pending:
                return
            self._pending.add(key)
        threading.Thread(target=self._generate, args=(idx, key), daemon=True).start()

    def _generate(self, idx: int, key: str):
        try:
            client = self._get_client()
            if not client:
                return

            t = self.tracks[idx]
            next_t = self.tracks[idx + 1] if idx + 1 < len(self.tracks) else None

            transition_prompt = ""
            if next_t:
                transition_prompt = f'\nTRANSITION: [A witty one-sentence DJ bridge from "{t["name"]}" ({t["year"]}) to "{next_t["name"]}" by {next_t["artists"]} ({next_t["year"]}), max 120 chars]'

            resp = client.chat.completions.create(
                model="google/gemini-2.0-flash-001",
                messages=[{
                    "role": "user",
                    "content": f"""You are a witty, knowledgeable music DJ narrating a journey through decades of hits.
Give me this in plain text (no markdown):

FACT: [One surprising, specific fun fact about "{t['name']}" by {t['artists']} ({t['year']}), max 120 chars]{transition_prompt}""",
                }],
                max_tokens=150,
            )

            text = resp.choices[0].message.content.strip()
            fact = ""
            transition = ""
            for line in text.split("\n"):
                line = line.strip()
                if line.startswith("FACT:"):
                    fact = line[5:].strip()
                elif line.startswith("TRANSITION:"):
                    transition = line[11:].strip()

            if fact:
                with self._lock:
                    self._cache[key] = {"fact": fact, "transition": transition}
                save_json_cache(AI_CACHE_FILE, self._cache)
        except Exception:
            pass
        finally:
            with self._lock:
                self._pending.discard(key)

    def pregenerate_batch(self, start: int, count: int = 5):
        """Kick off generation for a batch of upcoming tracks."""
        for i in range(start, min(start + count, len(self.tracks))):
            self.ensure(i)


# ── Waveform generator ──────────────────────────────────────────────


def generate_waveform(mp3_path: str, width: int = 48) -> str:
    """Generate an ASCII waveform from an MP3 file."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-i", mp3_path, "-ac", "1", "-ar", "4000", "-f", "s16le", "-"],
            capture_output=True, timeout=5,
        )
        if not result.stdout:
            return "░" * width

        samples = struct.unpack(f"<{len(result.stdout) // 2}h", result.stdout)
        bucket = max(len(samples) // width, 1)
        bars = "▁▂▃▄▅▆▇█"

        # Peak variation within sub-buckets for visual interest
        sub = max(bucket // 4, 1)
        values = []
        for i in range(width):
            chunk = samples[i * bucket:(i + 1) * bucket]
            if not chunk:
                values.append(0)
                continue
            peaks = []
            for j in range(0, len(chunk), sub):
                sc = chunk[j:j + sub]
                if sc:
                    peaks.append(max(abs(s) for s in sc))
            values.append(max(peaks) - min(peaks) if len(peaks) > 1 else (peaks[0] if peaks else 0))

        max_v = max(values) or 1
        return "".join(bars[int(min(v / max_v, 1) * (len(bars) - 1))] for v in values)
    except Exception:
        return "░" * width


# ── Prefetcher (MP3 + waveform) ──────────────────────────────────────


class Prefetcher:
    def __init__(self):
        self._files: dict[str, str] = {}  # url -> temp file path
        self._waveforms: dict[str, str] = {}  # url -> waveform string
        self._pending: set[str] = set()
        self._lock = threading.Lock()
        self._http = httpx.Client(timeout=15.0)
        self._tmpdir = tempfile.mkdtemp(prefix="spotify_decades_")

    def get_file(self, url: str) -> str | None:
        with self._lock:
            return self._files.get(url)

    def get_waveform(self, url: str) -> str | None:
        with self._lock:
            return self._waveforms.get(url)

    def ensure(self, url: str):
        if not url:
            return
        with self._lock:
            if url in self._files or url in self._pending:
                return
            self._pending.add(url)
        threading.Thread(target=self._download, args=(url,), daemon=True).start()

    def _download(self, url: str):
        try:
            resp = self._http.get(url)
            resp.raise_for_status()
            path = os.path.join(self._tmpdir, f"{abs(hash(url))}.mp3")
            with open(path, "wb") as f:
                f.write(resp.content)
            waveform = generate_waveform(path)
            with self._lock:
                self._files[url] = path
                self._waveforms[url] = waveform
        except Exception:
            pass
        finally:
            with self._lock:
                self._pending.discard(url)

    def cleanup(self):
        self._http.close()
        shutil.rmtree(self._tmpdir, ignore_errors=True)


# ── Album art display ────────────────────────────────────────────────


def show_album_art(image_url: str | None):
    """Display album art inline using iTerm2's imgcat."""
    if not image_url or not os.path.exists(IMGCAT):
        return
    try:
        subprocess.run(
            [IMGCAT, "-W", "20", "-H", "10", "-u", image_url],
            timeout=5,
            stdout=sys.stdout,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


# ── Player ───────────────────────────────────────────────────────────


class Player:
    def __init__(self, tracks: list[dict]):
        self.tracks = tracks
        self.index = 0
        self.proc = None
        self.playing = False
        self.auto = True
        self._lock = threading.Lock()
        self._prefetcher = Prefetcher()
        self._dj = AIDJ(tracks)
        self._prev_index = -1  # for transition display

        # Pipe for background thread -> main thread signaling
        self._sig_r, self._sig_w = os.pipe()

        # Prefetch first few tracks + AI facts
        self._prefetch_around(0)
        self._dj.pregenerate_batch(0, 8)

    def signal_main(self):
        """Wake up the main loop from a background thread."""
        try:
            os.write(self._sig_w, b"x")
        except OSError:
            pass

    def drain_signals(self):
        """Consume any pending signal bytes."""
        try:
            while select.select([self._sig_r], [], [], 0)[0]:
                os.read(self._sig_r, 256)
        except OSError:
            pass

    def _prefetch_around(self, idx: int):
        for i in range(idx, min(idx + 3, len(self.tracks))):
            url = self.tracks[i].get("preview_url")
            if url:
                self._prefetcher.ensure(url)

    def play_current(self):
        self.stop()
        t = self.tracks[self.index]
        url = t.get("preview_url")
        if not url:
            self.playing = False
            if self.auto and self.index < len(self.tracks) - 1:
                self.index += 1
                self.render()
                self.play_current()
            return

        self._prefetch_around(self.index + 1)
        self._dj.pregenerate_batch(self.index, 5)

        source = self._prefetcher.get_file(url) or url

        self.proc = subprocess.Popen(
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", source],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.playing = True
        threading.Thread(target=self._wait_and_next, daemon=True).start()

    def _wait_and_next(self):
        proc = self.proc
        if proc:
            proc.wait()
            with self._lock:
                if self.playing and self.auto and self.proc is proc:
                    if self.index < len(self.tracks) - 1:
                        self._prev_index = self.index
                        self.index += 1
                        self.play_current()
                        self.signal_main()  # wake main loop to re-render

    def stop(self):
        with self._lock:
            self.playing = False
            if self.proc:
                self.proc.terminate()
                try:
                    self.proc.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
                self.proc = None

    def next(self):
        if self.index < len(self.tracks) - 1:
            self._prev_index = self.index
            self.index += 1
            self._prefetch_around(self.index + 1)
            self._dj.pregenerate_batch(self.index, 5)
            if self.auto or self.playing:
                self.play_current()

    def prev(self):
        if self.index > 0:
            self._prev_index = self.index
            self.index -= 1
            if self.auto or self.playing:
                self.play_current()

    def toggle(self):
        if self.playing:
            self.stop()
        else:
            self.play_current()

    def render(self):
        t = self.tracks[self.index]
        status = "PLAYING" if self.playing else "PAUSED"
        auto_label = "AUTO" if self.auto else "MANUAL"

        # Colors from Spotify embed data
        bg = color_from_spotify(t.get("bg_color"), (30, 30, 40))
        fg = color_from_spotify(t.get("text_color"), (255, 255, 255))
        dim_fg = (fg[0] * 2 // 3, fg[1] * 2 // 3, fg[2] * 2 // 3)

        fg_code = rgb_fg(*fg)
        dim_code = rgb_fg(*dim_fg)
        bg_code = rgb_bg(*bg)

        # Clear screen
        sys.stdout.write("\033[2J\033[H")

        # Set background for entire terminal
        sys.stdout.write(bg_code)

        total = len(self.tracks)
        W = 54  # inner width

        # Timeline bar
        bar_w = W - 4
        filled = int((self.index / max(total - 1, 1)) * bar_w)
        bar = "█" * filled + "░" * (bar_w - filled)

        # Waveform
        preview_url = t.get("preview_url")
        waveform = self._prefetcher.get_waveform(preview_url) if preview_url else None
        if not waveform:
            waveform = "░" * (W - 4)

        # AI content
        ai = self._dj.get(self.index)
        fact = ai["fact"] if ai and ai.get("fact") else ""

        # Transition from previous track
        transition = ""
        if self._prev_index >= 0:
            prev_ai = self._dj.get(self._prev_index)
            if prev_ai and prev_ai.get("transition"):
                transition = prev_ai["transition"]

        # Inner content width (between the │ borders, with 2-char margin each side)
        CW = W - 4  # content width = 50

        def pad(text: str, width: int) -> str:
            """Pad plain text to exact visible width, truncating if needed."""
            # Truncate to width
            if len(text) > width:
                text = text[:width - 1] + "…"
            return text + " " * (width - len(text))

        def line(text: str = ""):
            """Format a bordered line. `text` must be plain (no ANSI)."""
            padded = pad(text, CW)
            return f"  {DIM}│{RESET}{bg_code}{fg_code}  {padded}  {DIM}│{RESET}"

        def line_styled(visible: str, styled: str):
            """Line with ANSI styling. `visible` = plain text for width calc, `styled` = display."""
            padding = CW - len(visible)
            if padding < 0:
                # Truncate visible and styled together
                styled = visible[:CW - 1] + "…"
                padding = 0
            return f"  {DIM}│{RESET}{bg_code}{fg_code}  {styled}{' ' * padding}  {DIM}│{RESET}"

        def separator():
            return f"  {DIM}├{'─' * W}┤{RESET}"

        def top():
            return f"  {DIM}┌{'─' * W}┐{RESET}"

        def bottom():
            return f"  {DIM}└{'─' * W}┘{RESET}"

        lines = [
            "",
            f"{fg_code}{bg_code}",
            top(),
            line("SPOTIFY DECADES  ·  1960 – 2025".center(CW)),
            separator(),
        ]

        # Transition line
        if transition:
            tr_text = f"» {transition}"
            lines.append(line())
            lines.append(line_styled(tr_text[:CW], f"{dim_code}{tr_text[:CW]}"))

        # Track info
        year_str = str(t["year"])
        name_str = t["name"][:CW]
        artist_str = t["artists"][:CW]
        lines += [
            line(),
            line_styled(year_str, f"{BOLD}{year_str}{RESET}{bg_code}{fg_code}"),
            line_styled(name_str, f"{BOLD}{name_str}{RESET}{bg_code}{fg_code}"),
            line_styled(artist_str, f"{dim_code}{artist_str}"),
            line(),
        ]

        # Album art
        lines.append(separator())
        print("\n".join(lines))
        sys.stdout.flush()

        show_album_art(t.get("image_url"))

        lines2 = [separator()]

        # Waveform
        wf_display = waveform[:CW] if waveform else "░" * CW
        lines2 += [
            line(wf_display),
            line_styled("~30s preview", f"{dim_code}~30s preview"),
        ]

        # Fun fact
        if fact:
            fact_text = f"» {fact}"[:CW]
            lines2 += [
                separator(),
                line(fact_text),
            ]

        # Timeline
        bar_display = bar[:CW]
        year_line = f"1960{' ' * (CW - 8)}2025"
        lines2 += [
            separator(),
            line_styled(bar_display, f"{dim_code}{bar_display}"),
            line_styled(year_line, f"{dim_code}{year_line}"),
            separator(),
        ]

        # Context tracks
        start = max(0, self.index - 2)
        end = min(total, self.index + 3)
        for i in range(start, end):
            tr = self.tracks[i]
            preview = "♫" if tr.get("preview_url") else "✗"
            name = pad(tr["name"][:20], 20)
            artist = tr["artists"][:14]
            marker = " ▶" if i == self.index else "  "
            plain = f"{marker} {preview} {tr['year']} {name} {artist}"[:CW]
            if i == self.index:
                lines2.append(line_styled(plain, f"{BOLD}{plain}{RESET}{bg_code}{fg_code}"))
            else:
                lines2.append(line_styled(plain, f"{dim_code}{plain}"))

        no_preview = " (no preview)" if not preview_url else ""
        status_line = f"[{status:>7s}]  [{auto_label}]        {self.index + 1:>2d}/{total}{no_preview}"
        controls = "← prev · → next · space play/pause · a auto · q"
        lines2 += [
            separator(),
            line(f"  {status_line}"),
            line_styled(f"  {controls}", f"  {dim_code}{controls}"),
            bottom(),
            RESET,
            "",
        ]

        print("\n".join(lines2))
        sys.stdout.flush()


# ── Input ────────────────────────────────────────────────────────────


def read_key(fd: int) -> str | None:
    """Read a single keypress from a raw fd. Non-blocking — returns None if no data."""
    data = os.read(fd, 32)
    if not data:
        return None
    if data[0:1] == b"\x1b" and len(data) >= 3 and data[1:2] == b"[":
        return {"D": "left", "C": "right", "A": "up", "B": "down"}.get(chr(data[2]), "")
    if data[0:1] == b"\x03":
        return "\x03"
    return data[0:1].decode("utf-8", errors="replace")


# ── Main ─────────────────────────────────────────────────────────────


def main():
    sp = Spotify()
    print(f"\n  {DIM}Loading 66 tracks from Spotify...{RESET}")
    tracks = load_tracks(sp)
    sp.close()

    # Delete stale track cache entries (force re-fetch if missing new fields like image_url)
    if tracks and "image_url" not in tracks[0]:
        os.remove(CACHE_FILE)
        sp = Spotify()
        tracks = load_tracks(sp)
        sp.close()

    player = Player(tracks)

    stdin_fd = sys.stdin.fileno()
    old_term = termios.tcgetattr(stdin_fd)

    try:
        # Put terminal in raw mode once (not per-keypress)
        tty.setraw(stdin_fd)

        player.render()
        player.play_current()

        while True:
            # Wait for either stdin input OR a signal from the background thread
            readable, _, _ = select.select([stdin_fd, player._sig_r], [], [])

            if player._sig_r in readable:
                player.drain_signals()
                player.render()

            if stdin_fd in readable:
                key = read_key(stdin_fd)
                if key in ("q", "\x03"):
                    break
                elif key in ("right", "n"):
                    player.next()
                elif key in ("left", "p"):
                    player.prev()
                elif key == " ":
                    player.toggle()
                elif key == "a":
                    player.auto = not player.auto
                player.render()

    except (EOFError, KeyboardInterrupt):
        pass
    finally:
        termios.tcsetattr(stdin_fd, termios.TCSADRAIN, old_term)
        player.stop()
        player._prefetcher.cleanup()
        os.close(player._sig_r)
        os.close(player._sig_w)
        sys.stdout.write(f"\033[2J\033[H{RESET}")
        print("  Bye!\n")


if __name__ == "__main__":
    main()
