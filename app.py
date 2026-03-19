"""Mini Spotify preview player — 10 classic tracks in the terminal."""

import sys
import subprocess
from spotify import Spotify

CLASSICS = [
    ("3n3Ppam7vgaVa1iaRUc9Lp", "Mr. Brightside"),
    ("4uLU6hMCjMI75M1A2tKUQC", "Never Gonna Give You Up"),
    ("7ouMYWpwJ422jRcDASZB7P", "Knights of Cydonia"),
    ("4cOdK2wGLETKBW3PvgPWqT", "Smells Like Teen Spirit"),
    ("6dGnYIeXmHdcikdzNNDMm2", "Bohemian Rhapsody"),
    ("0aym2LBJBk9DAYuHHutrIl", "Hey Jude"),
    ("2374M0fQpWi3dLnB54qaLX", "Africa"),
    ("5ghIJDpPoe3CfHMGu71E6T", "Blinding Lights"),
    ("1mea3bSkSGXuIRvnydlB5b", "Viva la Vida"),
    ("3KkXRkHbMCARz0aVfEt68P", "Sunflower"),
]

player_proc = None


def play(url: str):
    global player_proc
    stop()
    player_proc = subprocess.Popen(
        ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", url],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def stop():
    global player_proc
    if player_proc:
        player_proc.terminate()
        player_proc.wait()
        player_proc = None


def main():
    sp = Spotify()
    print("\n  Loading tracks...\n")

    tracks = []
    for track_id, fallback_name in CLASSICS:
        try:
            t = sp.embed_track(track_id)
            tracks.append(t)
        except Exception:
            tracks.append({"name": fallback_name, "artists": [], "preview_url": None})

    while True:
        print("  ╔══════════════════════════════════════════════╗")
        print("  ║         SPOTIFY PREVIEW PLAYER               ║")
        print("  ╠══════════════════════════════════════════════╣")
        for i, t in enumerate(tracks, 1):
            artists = ", ".join(a["name"] for a in t.get("artists", []))
            name = t["name"]
            has_preview = "♫" if t.get("preview_url") else "✗"
            print(f"  ║  {has_preview} {i:2d}. {name[:22]:<22s} {artists[:18]:<18s} ║")
        print("  ╠══════════════════════════════════════════════╣")
        print("  ║  Enter number to play · s to stop · q to quit║")
        print("  ╚══════════════════════════════════════════════╝")
        print()

        try:
            choice = input("  > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            break

        if choice == "q":
            break
        elif choice == "s":
            stop()
            print("  Stopped.\n")
        elif choice.isdigit() and 1 <= int(choice) <= len(tracks):
            t = tracks[int(choice) - 1]
            url = t.get("preview_url")
            if url:
                artists = ", ".join(a["name"] for a in t.get("artists", []))
                print(f"\n  ▶ Playing: {t['name']} — {artists}\n")
                play(url)
            else:
                print("  No preview available for this track.\n")
        else:
            print("  Invalid choice.\n")

    stop()
    print("  Bye!\n")


if __name__ == "__main__":
    main()
