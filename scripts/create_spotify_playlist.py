#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

from sync_google_sheet_schema import TRACK_PROBLEMS_SHEET, get_token as get_gsheets_token
from sync_google_sheet_schema import get_values, update_values


ROOT = Path(__file__).resolve().parents[1]
CREDS_PATH = ROOT / "credentials.env"
TOKENS_PATH = ROOT / "tokens.json"
TRACK_DURATION_MIN_MS = 150_000
TRACK_DURATION_MAX_MS = 550_000
TRACK_DURATION_SWEET_MIN_MS = 180_000
TRACK_DURATION_SWEET_MAX_MS = 270_000
PLAYLIST_DISCLAIMER = (
    "Independent artistic response. Not affiliated with, endorsed by, or representing the reference artist or their estate."
)


def load_env_file(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip()
    return data


def load_tokens() -> dict[str, str]:
    return json.loads(TOKENS_PATH.read_text())


def save_tokens(tokens: dict[str, str]) -> None:
    TOKENS_PATH.write_text(json.dumps(tokens, indent=2) + "\n")


def basic_auth_header(client_id: str, client_secret: str) -> str:
    raw = f"{client_id}:{client_secret}".encode()
    return "Basic " + base64.b64encode(raw).decode()


def refresh_access_token(client_id: str, client_secret: str, refresh_token: str) -> str:
    payload = urllib.parse.urlencode(
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
    ).encode()
    req = urllib.request.Request(
        "https://accounts.spotify.com/api/token",
        data=payload,
        headers={
            "Authorization": basic_auth_header(client_id, client_secret),
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
    return data["access_token"]


def spotify_json(url: str, token: str, method: str = "GET", payload: dict | None = None) -> dict:
    last_exc: Exception | None = None
    for attempt in range(5):
        data = None if payload is None else json.dumps(payload).encode()
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method=method,
        )
        try:
            with urllib.request.urlopen(req) as resp:
                body = resp.read()
            return json.loads(body) if body else {}
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < 4:
                retry_after = exc.headers.get("Retry-After")
                sleep_seconds = float(retry_after) if retry_after else (2 ** attempt)
                time.sleep(sleep_seconds)
                last_exc = exc
                continue
            raise
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if attempt < 4:
                time.sleep(2 ** attempt)
                continue
            raise
    if last_exc:
        raise last_exc
    return {}


def normalize_token(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def track_key(track_line: str) -> str:
    return normalize_token(track_line.replace("–", "-"))


def token_overlap_score(expected: str, actual: str) -> int:
    expected_tokens = {token for token in normalize_token(expected).split() if token}
    actual_tokens = {token for token in normalize_token(actual).split() if token}
    if not expected_tokens or not actual_tokens:
        return 0
    return len(expected_tokens & actual_tokens)


def parse_playlist_plan(path: Path) -> tuple[str, str, int, list[str], str, str]:
    lines = [line.strip() for line in path.read_text().splitlines() if line.strip()]
    name = next(line.split(": ", 1)[1] for line in lines if line.startswith("PLAYLIST_NAME:"))
    rationale = next(line.split(": ", 1)[1] for line in lines if line.startswith("PLAYLIST_RATIONALE:"))
    target_min = int(next(line.split(": ", 1)[1] for line in lines if line.startswith("PLAYLIST_TARGET_DURATION_MIN:")))
    tracks = [line.split(": ", 1)[1] for line in lines if line.startswith("TRACK_")]
    redirect_url = next(line.split(": ", 1)[1] for line in lines if line.startswith("PLAYLIST_REDIRECT_URL:"))
    qr_target = next(line.split(": ", 1)[1] for line in lines if line.startswith("PLAYLIST_QR_TARGET:"))
    return name, rationale, target_min, tracks, redirect_url, qr_target


def load_track_problem_registry() -> dict[str, dict[str, str]]:
    token = get_gsheets_token()
    rows = get_values(token, f"{TRACK_PROBLEMS_SHEET}!A:H")
    if not rows:
        return {}
    headers = rows[0]
    registry: dict[str, dict[str, str]] = {}
    for row in rows[1:]:
        if not row:
            continue
        padded = row + [""] * (len(headers) - len(row))
        record = dict(zip(headers, padded))
        if record.get("is_active", "").strip() != "1":
            continue
        key = record.get("track_key", "").strip().lower()
        if key:
            registry[key] = record
    return registry


def search_track(track_line: str, token: str, blocked_tracks: dict[str, dict[str, str]]) -> dict:
    blocked = blocked_tracks.get(track_key(track_line))
    if blocked:
        reason = blocked.get("reason", "blocked")
        raise RuntimeError(f"Spotify track blocked by TRACK_PROBLEMS registry: {track_line} ({reason})")
    artist, track = [part.strip() for part in track_line.split(" - ", 1)]
    candidate_queries = [
        f"track:{track} artist:{artist}",
        f"{artist} {track}",
        track,
    ]
    best_candidate: dict | None = None
    best_score = -1
    for raw_query in candidate_queries:
        query = urllib.parse.quote(raw_query)
        url = f"https://api.spotify.com/v1/search?q={query}&type=track&limit=5"
        result = spotify_json(url, token)
        items = result.get("tracks", {}).get("items", [])
        if not items:
            continue
        for item in items:
            if not (TRACK_DURATION_MIN_MS <= item.get("duration_ms", 0) <= TRACK_DURATION_MAX_MS):
                continue
            item_artists = " ".join(a["name"] for a in item.get("artists", []))
            item_name = item.get("name", "")
            score = token_overlap_score(artist, item_artists) * 3 + token_overlap_score(track, item_name) * 5
            exactish_artist = normalize_token(artist) in normalize_token(item_artists)
            exactish_title = normalize_token(track) in normalize_token(item_name)
            if exactish_artist and exactish_title:
                return item
            if score > best_score:
                best_candidate = item
                best_score = score
    if best_candidate and best_score >= 4:
        return best_candidate
    raise RuntimeError(f"Spotify track not found: {track_line}")


def validate_track_items(track_items: list[dict], target_min: int) -> None:
    violations: list[str] = []
    total_ms = 0
    for index, item in enumerate(track_items, start=1):
        duration_ms = item.get("duration_ms", 0)
        total_ms += duration_ms
        if not (TRACK_DURATION_MIN_MS <= duration_ms <= TRACK_DURATION_MAX_MS):
            violations.append(
                f"Track {index} violates duration rule: {item['artists'][0]['name']} - {item['name']} ({duration_ms} ms)"
            )
    total_min = total_ms / 60_000
    if total_min < target_min:
        violations.append(f"Playlist total duration {total_min:.2f} min is below target {target_min} min.")
    if violations:
        raise RuntimeError("Spotify playlist validation failed: " + " ".join(violations))


def ensure_playlist(token: str, name: str, description: str) -> dict:
    payload = {
        "name": name,
        "description": description,
        "public": False,
    }
    return spotify_json("https://api.spotify.com/v1/me/playlists", token, "POST", payload)


def add_tracks_to_playlist(playlist_id: str, uris: list[str], token: str) -> None:
    spotify_json(
        f"https://api.spotify.com/v1/playlists/{playlist_id}/items",
        token,
        "POST",
        {"uris": uris},
    )


def update_episode_row(episode_id: str, playlist_name: str, playlist_url: str) -> None:
    token = get_gsheets_token()
    rows = get_values(token, "EPISODES!A:AE")
    headers = rows[0]
    for idx, row in enumerate(rows[1:], start=2):
        row = row + [""] * (len(headers) - len(row))
        if "episode_id" in headers and row[headers.index("episode_id")] == episode_id:
            if "playlist_name" in headers:
                row[headers.index("playlist_name")] = playlist_name
            if "spotify_playlist_url" in headers:
                row[headers.index("spotify_playlist_url")] = playlist_url
            if "episode_status" in headers:
                row[headers.index("episode_status")] = "spotify_posted"
            if "status" in headers:
                row[headers.index("status")] = "spotify_posted"
            if "updated_at" in headers:
                row[headers.index("updated_at")] = "2026-03-12 11:30:00"
            update_values(token, f"EPISODES!A{idx}:AE{idx}", [row])
            return


def append_track_rows(episode_id: str, artist_slug: str, playlist_name: str, playlist_id: str, track_items: list[dict]) -> None:
    token = get_gsheets_token()
    rows = get_values(token, "Tracks!A:J")
    values = rows[:]
    existing = {
        (row[0], row[5], row[6])
        for row in rows[1:]
        if len(row) > 6
    }
    for index, item in enumerate(track_items, start=1):
        key = (item["id"], playlist_name, episode_id)
        if key in existing:
            continue
        values.append(
            [
                item["id"],
                item["name"],
                item["artists"][0]["name"],
                item["album"]["name"],
                playlist_id,
                playlist_name,
                episode_id,
                artist_slug,
                str(index),
                "2026-03-12 11:30:00",
            ]
        )
    update_values(token, f"Tracks!A1:J{len(values)}", values)


def update_redirect_target(episode_id: str, playlist_url: str) -> None:
    token = get_gsheets_token()
    rows = get_values(token, "REDIRECT_REGISTRY!A:K")
    values = rows[:]
    headers = rows[0]
    for idx, row in enumerate(values[1:], start=1):
        row = row + [""] * (len(headers) - len(row))
        is_episode = row[0] == episode_id
        is_playlist = len(row) > 3 and row[3] == "playlist"
        if is_episode and is_playlist:
            row[7] = playlist_url
            row[8] = "active"
            values[idx] = row
    update_values(token, f"REDIRECT_REGISTRY!A1:K{len(values)}", values)


def update_playlist_file(plan_path: Path, playlist_id: str, playlist_url: str) -> None:
    lines = plan_path.read_text().splitlines()
    new_lines: list[str] = []
    inserted = False
    disclaimer_inserted = False
    for line in lines:
        if line.startswith("DISCLAIMER:"):
            if not disclaimer_inserted:
                new_lines.append(f"DISCLAIMER: {PLAYLIST_DISCLAIMER}")
                disclaimer_inserted = True
            continue
        new_lines.append(line)
        if line.startswith("PLAYLIST_TARGET_DURATION_MIN:"):
            new_lines.append(f"SPOTIFY_PLAYLIST_ID: {playlist_id}")
            new_lines.append(f"SPOTIFY_PLAYLIST_URL: {playlist_url}")
            inserted = True
    if not inserted:
        new_lines.append(f"SPOTIFY_PLAYLIST_ID: {playlist_id}")
        new_lines.append(f"SPOTIFY_PLAYLIST_URL: {playlist_url}")
    if not disclaimer_inserted:
        new_lines.append(f"DISCLAIMER: {PLAYLIST_DISCLAIMER}")
    plan_path.write_text("\n".join(new_lines) + "\n")


def update_manifest(episode_slug: str, playlist_url: str, playlist_file: Path) -> None:
    manifest_path = ROOT / "output" / episode_slug / "publish" / f"{episode_slug}_start-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["status"] = "spotify_posted"
    manifest["spotify_playlist_url"] = playlist_url
    manifest["artifacts"]["playlist_package"] = str(playlist_file)
    manifest["next_step"] = "Continue with Avatar Agent outputs and stop before HeyGen execution."
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a Spotify playlist from an episode playlist plan.")
    parser.add_argument("--episode-slug", required=True)
    parser.add_argument("--episode-id", required=True)
    parser.add_argument("--artist-slug", required=True)
    parser.add_argument("--plan-file", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    creds = load_env_file(CREDS_PATH)
    tokens = load_tokens()
    access_token = refresh_access_token(
        creds["SPOTIFY_CLIENT_ID"],
        creds["SPOTIFY_CLIENT_SECRET"],
        tokens["refresh_token"],
    )
    tokens["access_token"] = access_token
    save_tokens(tokens)

    plan_path = Path(args.plan_file)
    name, rationale, target_min, track_lines, redirect_url, qr_target = parse_playlist_plan(plan_path)
    description = (
        f"Canvas & Glass episode playlist for {args.episode_slug}. "
        f"{rationale} {PLAYLIST_DISCLAIMER} Redirect: {redirect_url} | Video target: {qr_target}"
    )
    playlist = ensure_playlist(access_token, name, description[:300])
    playlist_id = playlist["id"]
    playlist_url = playlist["external_urls"]["spotify"]

    blocked_tracks = load_track_problem_registry()
    track_items = [search_track(track_line, access_token, blocked_tracks) for track_line in track_lines]
    validate_track_items(track_items, target_min)
    add_tracks_to_playlist(playlist_id, [item["uri"] for item in track_items], access_token)

    update_playlist_file(plan_path, playlist_id, playlist_url)
    update_episode_row(args.episode_id, name, playlist_url)
    append_track_rows(args.episode_id, args.artist_slug, name, playlist_id, track_items)
    update_redirect_target(args.episode_id, playlist_url)
    update_manifest(args.episode_slug, playlist_url, plan_path)

    print(f"Playlist created: {playlist_url}")
    print(f"Playlist ID: {playlist_id}")
    print(f"Tracks added: {len(track_items)} / target {target_min} min plan")


if __name__ == "__main__":
    main()
