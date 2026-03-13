#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import shutil
import tempfile
from pathlib import Path

import requests
from PIL import Image

from create_spotify_playlist import (
    load_env_file,
    load_tokens,
    refresh_access_token,
    spotify_json,
)
from sync_google_sheet_schema import get_token as get_gsheets_token
from sync_google_sheet_schema import get_values, update_values


ROOT = Path(__file__).resolve().parents[1]
CREDS_PATH = ROOT / "credentials.env"
TOKENS_PATH = ROOT / "tokens.json"
SPOTIFY_COVER_MAX_BYTES = 180_000


def make_spotify_safe_cover(image_path: Path) -> Path:
    image = Image.open(image_path).convert("RGB")
    fd, temp_name = tempfile.mkstemp(suffix=".jpg")
    Path(temp_name).unlink(missing_ok=True)
    temp_path = Path(temp_name)
    for size in (1200, 1000, 900, 800, 700, 640):
        resized = image.resize((size, size), Image.Resampling.LANCZOS)
        for quality in (88, 82, 76, 70, 64, 58, 52):
            resized.save(temp_path, format="JPEG", quality=quality, optimize=True)
            if temp_path.stat().st_size <= SPOTIFY_COVER_MAX_BYTES:
                return temp_path
    resized = image.resize((640, 640), Image.Resampling.LANCZOS)
    resized.save(temp_path, format="JPEG", quality=45, optimize=True)
    return temp_path


def upload_playlist_cover(playlist_id: str, image_path: Path, token: str) -> None:
    safe_path = make_spotify_safe_cover(image_path)
    payload = base64.b64encode(safe_path.read_bytes())
    try:
        response = requests.put(
            f"https://api.spotify.com/v1/playlists/{playlist_id}/images",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "image/jpeg",
            },
            data=payload,
            timeout=60,
        )
        response.raise_for_status()
    finally:
        safe_path.unlink(missing_ok=True)


def update_episode_row(episode_id: str, final_cover: Path) -> None:
    token = get_gsheets_token()
    rows = get_values(token, "EPISODES!A:AE")
    headers = rows[0]
    values = rows[:]
    for idx, row in enumerate(values[1:], start=1):
        row = row + [""] * (len(headers) - len(row))
        if row[headers.index("episode_id")] != episode_id:
            continue
        if "spotify_selected_cover" in headers:
            row[headers.index("spotify_selected_cover")] = str(final_cover)
        for key in ("spotify_cover_option_1", "spotify_cover_option_2", "spotify_cover_option_3"):
            if key in headers:
                row[headers.index(key)] = ""
        if "episode_status" in headers:
            row[headers.index("episode_status")] = "cover_selected"
        if "status" in headers:
            row[headers.index("status")] = "cover_selected"
        values[idx] = row
        break
    update_values(token, f"EPISODES!A1:AE{len(values)}", values)


def update_manifest(episode_slug: str, final_cover: Path) -> None:
    manifest_path = ROOT / "output" / episode_slug / "publish" / f"{episode_slug}_start-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["status"] = "cover_selected"
    manifest["spotify_selected_cover"] = str(final_cover)
    manifest.pop("spotify_cover_options", None)
    manifest.pop("spotify_cover_contact_sheet", None)
    manifest["next_step"] = "Continue with Avatar Agent outputs and stop before HeyGen execution."
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")


def update_playlist_package(plan_path: Path, final_cover: Path) -> None:
    lines = plan_path.read_text().splitlines()
    filtered = [line for line in lines if not line.startswith("SPOTIFY_SELECTED_COVER:")]
    filtered.append(f"SPOTIFY_SELECTED_COVER: {final_cover}")
    plan_path.write_text("\n".join(filtered) + "\n")


def cleanup_variants(spotify_dir: Path, selected_option: int, final_cover: Path) -> None:
    selected_path = spotify_dir / f"{spotify_dir.parent.name}_spotify_cover_option_{selected_option:02d}.jpg"
    if selected_path.exists() and selected_path != final_cover:
        shutil.move(str(selected_path), str(final_cover))
    elif not final_cover.exists():
        raise FileNotFoundError(f"Selected cover not found: {selected_path}")
    for path in spotify_dir.glob(f"{spotify_dir.parent.name}_spotify_cover_option_*.jpg"):
        if path != final_cover:
            path.unlink(missing_ok=True)
    contact_sheet = spotify_dir / f"{spotify_dir.parent.name}_spotify_cover_contact_sheet.jpg"
    contact_sheet.unlink(missing_ok=True)


def fetch_playlist_url(playlist_id: str, token: str) -> str:
    playlist = spotify_json(f"https://api.spotify.com/v1/playlists/{playlist_id}", token)
    return playlist["external_urls"]["spotify"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Select one Spotify cover option, upload it, and clean up the rest.")
    parser.add_argument("--episode-slug", required=True)
    parser.add_argument("--episode-id", required=True)
    parser.add_argument("--playlist-id", default="")
    parser.add_argument("--option", type=int, choices=[1, 2, 3], required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    spotify_dir = ROOT / "output" / args.episode_slug / "spotify"
    final_cover = spotify_dir / f"{args.episode_slug}_spotify_cover_final.jpg"

    cleanup_variants(spotify_dir, args.option, final_cover)
    playlist_url = ""
    if args.playlist_id:
        creds = load_env_file(CREDS_PATH)
        tokens = load_tokens()
        access_token = refresh_access_token(
            creds["SPOTIFY_CLIENT_ID"],
            creds["SPOTIFY_CLIENT_SECRET"],
            tokens["refresh_token"],
        )
        upload_playlist_cover(args.playlist_id, final_cover, access_token)
        playlist_url = fetch_playlist_url(args.playlist_id, access_token)

    update_episode_row(args.episode_id, final_cover)
    update_manifest(args.episode_slug, final_cover)
    package = next(spotify_dir.glob(f"{args.episode_slug}_playlist_*.txt"))
    update_playlist_package(package, final_cover)

    print(final_cover)
    if playlist_url:
        print(playlist_url)


if __name__ == "__main__":
    main()
