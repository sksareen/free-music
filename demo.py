"""Demo: Spotify client with no API keys, no browser, no OAuth."""

from spotify import Spotify


def main():
    sp = Spotify()

    # ── Auth info ────────────────────────────────────────────────────
    print("=== Authentication ===")
    info = sp.info
    print(f"Client ID:      {info['client_id']}")
    print(f"Anonymous:      {info['is_anonymous']}")
    print(f"TOTP version:   {info['secret_version']}")
    print(f"App version:    {info['app_version']}")
    print(f"Client token:   {sp.client_token[:40]}...")
    print()

    # ── Embed: Track (no rate limits) ────────────────────────────────
    print("=== Track (embed) ===")
    track = sp.embed_track("4uLU6hMCjMI75M1A2tKUQC")
    artists = ", ".join(a["name"] for a in track["artists"])
    mins = track["duration_ms"] // 60000
    secs = (track["duration_ms"] % 60000) // 1000
    print(f"  {track['name']} — {artists}")
    print(f"  Duration: {mins}:{secs:02d}")
    print(f"  Explicit: {track['explicit']}")
    print(f"  Preview:  {track['preview_url']}")
    print()

    # ── Embed: Album ─────────────────────────────────────────────────
    print("=== Album (embed): OK Computer ===")
    album = sp.embed_album("6dVIqQ8qmQ5GBnJ9shOYGE")
    print(f"  {album['name']} — {album['subtitle']}")
    print(f"  {album['track_count']} tracks")
    for i, t in enumerate(album["tracks"], 1):
        dur = f"{t['duration_ms']//60000}:{(t['duration_ms']%60000)//1000:02d}"
        preview = "MP3" if t["preview_url"] else "—"
        print(f"  {i:2d}. {t['title']} ({dur}) [{preview}]")
    print()

    # ── Embed: Playlist ──────────────────────────────────────────────
    print("=== Playlist (embed): Today's Top Hits ===")
    playlist = sp.embed_playlist("37i9dQZF1DXcBWIGoYBM5M")
    print(f"  {playlist['name']}")
    print(f"  {playlist['track_count']} tracks shown")
    for t in playlist["tracks"][:10]:
        artists = ", ".join(a["name"] for a in t["artists"])
        print(f"  • {t['title']} — {artists}")
    print()

    # ── Embed: Artist ────────────────────────────────────────────────
    print("=== Artist (embed): Radiohead ===")
    artist = sp.embed_artist("4Z8W4fKeB5YxbusRsdQVPb")
    print(f"  {artist['name']}")
    print(f"  Top tracks:")
    for t in artist["top_tracks"][:5]:
        print(f"  • {t['title']}")
    print()

    # ── oEmbed (always works) ────────────────────────────────────────
    print("=== oEmbed ===")
    oembed = sp.oembed("https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC")
    print(f"  Title:     {oembed['title']}")
    print(f"  Thumbnail: {oembed['thumbnail_url']}")
    print()

    # ── API: Search (may hit rate limits) ────────────────────────────
    print("=== Search via API (may be slow if rate limited) ===")
    try:
        results = sp.search("Bohemian Rhapsody", types="track", limit=3)
        for t in results["tracks"]["items"]:
            artists = ", ".join(a["name"] for a in t["artists"])
            print(f"  {t['name']} — {artists} (popularity: {t['popularity']})")
    except Exception as e:
        print(f"  Rate limited: {e}")

    sp.close()


if __name__ == "__main__":
    main()
