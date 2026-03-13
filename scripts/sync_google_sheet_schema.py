#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


ROOT = Path(__file__).resolve().parents[1]
GSHEETS_KEY = ROOT / "secrets" / "legacy_canvasglass" / "gsheets_key.json"
SHEET_ID = "1ydqWqciQIQSKDCmp7jzvC0q04w_MP_e6ST9VENdHpew"

ARTIST_POOL_SHEET = "ARTIST_POOL"
EPISODES_SHEET = "EPISODES"
TRACKS_SHEET = "Tracks"
TRACK_PROBLEMS_SHEET = "TRACK_PROBLEMS"
SETTINGS_SHEET = "SETTINGS"
WINE_REGISTRY_SHEET = "WINE_REGISTRY"
AVATAR_SHEET = "AVATAR"
AVATAR_REGISTRY_SHEET = "AVATAR_REGISTRY"
REDIRECT_REGISTRY_SHEET = "REDIRECT_REGISTRY"


ARTIST_POOL_HEADERS = [
    "artist_name",
    "artist_slug",
    "category",
    "status",
    "used",
    "processed",
    "episode_id",
    "selected_at",
    "used_at",
    "last_episode",
    "notes",
]

EPISODES_HEADERS = [
    "episode_id",
    "episode_slug",
    "artist_name",
    "artist_slug",
    "artist_pool_status",
    "episode_status",
    "input_dir",
    "output_dir",
    "playlist_name",
    "spotify_playlist_url",
    "spotify_cover_url",
    "spotify_qr_path",
    "video_redirect_url",
    "playlist_redirect_url",
    "painting1_redirect_url",
    "painting2_redirect_url",
    "painting3_redirect_url",
    "youtube_video_url",
    "youtube_video_id",
    "video_description_path",
    "created_at",
    "updated_at",
    "published_at",
    "error",
]

TRACKS_HEADERS = [
    "spotify_track_id",
    "track_name",
    "track_artist",
    "album_name",
    "spotify_playlist_id",
    "spotify_playlist_name",
    "used_episode_id",
    "used_artist_slug",
    "session_index",
    "used_at",
]

TRACK_PROBLEMS_HEADERS = [
    "track_key",
    "track_name",
    "track_artist",
    "reason",
    "source_stage",
    "is_active",
    "recorded_at",
    "notes",
]

WINE_REGISTRY_HEADERS = [
    "episode_id",
    "artist_name",
    "artist_slug",
    "wine1",
    "wine1_description",
    "wine1_type",
    "wine1_region",
    "wine1_producer",
    "wine1_normalized_key",
    "wine2",
    "wine2_description",
    "wine2_type",
    "wine2_region",
    "wine2_producer",
    "wine2_normalized_key",
    "wine3",
    "wine3_description",
    "wine3_type",
    "wine3_region",
    "wine3_producer",
    "wine3_normalized_key",
    "recorded_at",
]

AVATAR_HEADERS = [
    "episode_id",
    "artist_name",
    "artist_slug",
    "narrative_pattern_id",
    "narrative_pattern_name",
    "avatar_registry_id",
    "avatar_id",
    "avatar_name",
    "mon1_tone_variant",
    "mon2_tone_variant",
    "mon3_tone_variant",
    "mon4_tone_variant",
    "mon4_closing_mode",
    "recorded_at",
]

AVATAR_REGISTRY_HEADERS = [
    "avatar_registry_id",
    "avatar_id",
    "avatar_name",
    "avatar_type",
    "narrative_pattern_id",
    "narrative_pattern_name",
    "default_voice_id",
    "is_active",
    "notes",
]

REDIRECT_REGISTRY_HEADERS = [
    "episode_id",
    "artist_name",
    "artist_slug",
    "redirect_type",
    "entity_name",
    "redirect_key",
    "public_url",
    "target_url",
    "status",
    "recorded_at",
    "notes",
]

SETTINGS_HEADERS = ["key", "value", "description"]
SETTINGS_DEFAULTS = [
    ["duration_1_min", "20", "Session 1 duration in minutes"],
    ["duration_2_min", "20", "Session 2 duration in minutes"],
    ["duration_3_min", "20", "Session 3 duration in minutes"],
    ["episode_id_padding", "3", "Episode id zero-padding width"],
    ["artist_pool_sheet", ARTIST_POOL_SHEET, "Canonical tab for artist selection"],
    ["artist_pool_select_value", "selected", "Status value written when an artist is assigned to an episode"],
    ["artist_pool_used_value", "used", "Status value written after the episode is published"],
    ["wine_repeat_kr", "20", "Allowed wine repeat share in percent"],
    ["wine_repeat_history_depth", "30", "How many previous episodes wine anti-repeat checks back"],
    ["track_repeat_kr", "20", "Allowed track repeat share in percent"],
    ["track_repeat_history_depth", "30", "How many previous episodes music anti-repeat checks back"],
    ["avatar_repeat_kr", "30", "Allowed narrative-pattern/avatar repeat share in percent"],
    ["avatar_repeat_history_depth", "10", "How many previous episodes avatar anti-repeat checks back"],
    ["spotify_cover_count", "3", "How many playlist cover variants to generate"],
    ["redirect_public_domain", "evadava.com", "Canonical public redirect domain used in QR and landing URLs"],
    ["video_redirect_base_path", "/", "Video redirects use root-level episode slugs on evadava.com"],
    ["painting_redirect_base_path", "/", "Painting redirects use root-level episode slugs on evadava.com"],
    ["playlist_redirect_base_path", "/", "Playlist redirects use root-level episode slugs on evadava.com"],
    [
        "redirect_slug_pattern",
        "episode{episode_id}_{artist_slug}_{entity_name}",
        "Canonical redirect slug pattern for video, playlist, and painting entities.",
    ],
    ["heygen_avatar_selection_mode", "by_narrative_pattern_id", "How AAO maps a narrative pattern to a HeyGen avatar for a full episode"],
]

NARRATIVE_PATTERNS = [
    ("01", "THE SENSUALIST PHILOSOPHER"),
    ("02", "THE ALCHEMIST CURATOR"),
    ("03", "THE DOUBLE AGENT"),
    ("04", "THE LITURGIST"),
    ("05", "THE WITNESS OF TRANSFORMATION"),
]

TRACK_PROBLEMS_DEFAULTS = [
    [
        "arvo pärt - spiegel im spiegel",
        "Spiegel im Spiegel",
        "Arvo Pärt",
        "duration_out_of_range",
        "spotify_publish",
        "1",
        "",
        "Rejected for playlist publishing under current Canvas & Glass constraints.",
    ],
    [
        "nils frahm - says",
        "Says",
        "Nils Frahm",
        "duration_out_of_range",
        "spotify_publish",
        "1",
        "",
        "Rejected for playlist publishing under current Canvas & Glass constraints.",
    ],
    [
        "tigran hamasyan - markos and maro",
        "Markos and Maro",
        "Tigran Hamasyan",
        "track_not_found_or_mismatch",
        "spotify_publish",
        "1",
        "",
        "The planned title mismatched Spotify inventory and should not be reused.",
    ],
    [
        "christian löffler - haul",
        "Haul",
        "Christian Löffler",
        "duration_out_of_range",
        "spotify_publish",
        "1",
        "",
        "Rejected for playlist publishing under current Canvas & Glass constraints.",
    ],
    [
        "max richter - on the nature of daylight",
        "On the Nature of Daylight",
        "Max Richter",
        "duration_out_of_range",
        "spotify_publish",
        "1",
        "",
        "Rejected for playlist publishing under current Canvas & Glass constraints.",
    ],
    [
        "ludovico einaudi - nuvole bianche",
        "Nuvole Bianche",
        "Ludovico Einaudi",
        "duration_out_of_range",
        "spotify_publish",
        "1",
        "",
        "Rejected for playlist publishing under current Canvas & Glass constraints.",
    ],
]


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def b64url(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode()
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def get_token() -> str:
    key_data = json.loads(GSHEETS_KEY.read_text())
    ts = int(time.time())
    header = b64url(json.dumps({"alg": "RS256", "typ": "JWT"}))
    payload = b64url(
        json.dumps(
            {
                "iss": key_data["client_email"],
                "scope": "https://www.googleapis.com/auth/spreadsheets",
                "aud": "https://oauth2.googleapis.com/token",
                "exp": ts + 3600,
                "iat": ts,
            }
        )
    )
    pk = serialization.load_pem_private_key(
        key_data["private_key"].encode(),
        password=None,
        backend=default_backend(),
    )
    sig = pk.sign(f"{header}.{payload}".encode(), padding.PKCS1v15(), hashes.SHA256())
    jwt = f"{header}.{payload}.{b64url(sig)}"
    data = urllib.parse.urlencode(
        {
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": jwt,
        }
    ).encode()
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())["access_token"]


def api_json(token: str, url: str, method: str = "GET", payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def quote_range(range_a1: str) -> str:
    return urllib.parse.quote(range_a1, safe="!':")


def get_sheet_titles(token: str) -> list[str]:
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}?fields=sheets(properties(title))"
    meta = api_json(token, url)
    return [sheet["properties"]["title"] for sheet in meta.get("sheets", [])]


def create_sheet(token: str, title: str) -> None:
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}:batchUpdate"
    api_json(token, url, "POST", {"requests": [{"addSheet": {"properties": {"title": title}}}]})


def get_values(token: str, range_a1: str) -> list[list[str]]:
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{quote_range(range_a1)}"
    return api_json(token, url).get("values", [])


def update_values(token: str, range_a1: str, values: list[list[str]]) -> None:
    url = (
        f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/"
        f"{quote_range(range_a1)}?valueInputOption=RAW"
    )
    api_json(token, url, "PUT", {"values": values})


def append_values(token: str, range_a1: str, values: list[list[str]]) -> None:
    url = (
        f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/"
        f"{quote_range(range_a1)}:append?valueInputOption=RAW&insertDataOption=INSERT_ROWS"
    )
    api_json(token, url, "POST", {"values": values})


def ensure_sheet_with_headers(token: str, title: str, required_headers: list[str]) -> list[str]:
    titles = get_sheet_titles(token)
    if title not in titles:
        create_sheet(token, title)
    rows = get_values(token, f"{title}!1:2")
    existing_headers = rows[0] if rows else []
    merged_headers = list(existing_headers)
    for header in required_headers:
        if header not in merged_headers:
            merged_headers.append(header)
    if not existing_headers or merged_headers != existing_headers:
        update_values(token, f"{title}!1:1", [merged_headers])
    return merged_headers


def ensure_settings(token: str) -> None:
    ensure_sheet_with_headers(token, SETTINGS_SHEET, SETTINGS_HEADERS)
    rows = get_values(token, f"{SETTINGS_SHEET}!A:C")
    existing = {row[0]: row for row in rows[1:] if row}
    missing = [row for row in SETTINGS_DEFAULTS if row[0] not in existing]
    if missing:
        append_values(token, f"{SETTINGS_SHEET}!A:C", missing)
    force_values = {
        "redirect_public_domain": "evadava.com",
        "video_redirect_base_path": "/",
        "painting_redirect_base_path": "/",
        "playlist_redirect_base_path": "/",
        "redirect_slug_pattern": "episode{episode_id}_{artist_slug}_{entity_name}",
    }
    changed = False
    values = rows[:]
    for idx, row in enumerate(values[1:], start=1):
        if not row:
            continue
        key = row[0]
        if key not in force_values:
            continue
        while len(row) < 3:
            row.append("")
        if row[1] != force_values[key]:
            row[1] = force_values[key]
            values[idx] = row
            changed = True
    if changed:
        update_values(token, f"{SETTINGS_SHEET}!A:C", values)


def ensure_track_problems_seed(token: str) -> None:
    ensure_sheet_with_headers(token, TRACK_PROBLEMS_SHEET, TRACK_PROBLEMS_HEADERS)
    rows = get_values(token, f"{TRACK_PROBLEMS_SHEET}!A:H")
    existing = {row[0].strip().lower() for row in rows[1:] if row and row[0].strip()}
    to_append: list[list[str]] = []
    for row in TRACK_PROBLEMS_DEFAULTS:
        key = row[0].strip().lower()
        if key in existing:
            continue
        seeded = row[:]
        seeded[6] = now_iso()
        to_append.append(seeded)
    if to_append:
        append_values(token, f"{TRACK_PROBLEMS_SHEET}!A:H", to_append)


def ensure_avatar_registry_seed(token: str) -> None:
    ensure_sheet_with_headers(token, AVATAR_REGISTRY_SHEET, AVATAR_REGISTRY_HEADERS)
    rows = get_values(token, f"{AVATAR_REGISTRY_SHEET}!A:I")
    existing_pattern_ids = {row[4] for row in rows[1:] if len(row) > 4 and row[4]}
    to_append: list[list[str]] = []
    for pattern_id, pattern_name in NARRATIVE_PATTERNS:
        if pattern_id in existing_pattern_ids:
            continue
        to_append.append(
            [
                f"AV{pattern_id}",
                "",
                "",
                "heygen_avatar",
                pattern_id,
                pattern_name,
                "",
                "1",
                "Seed row for future HeyGen avatar mapping by narrative pattern.",
            ]
        )
    if to_append:
        append_values(token, f"{AVATAR_REGISTRY_SHEET}!A:I", to_append)


def ensure_redirect_registry_seed(token: str) -> None:
    ensure_sheet_with_headers(token, REDIRECT_REGISTRY_SHEET, REDIRECT_REGISTRY_HEADERS)
    # No hardcoded artist/test-route seeds.
    # Redirect rows are created by the active run through start_episode.py.


def ensure_artist_pool_seed(token: str) -> None:
    ensure_sheet_with_headers(token, ARTIST_POOL_SHEET, ARTIST_POOL_HEADERS)
    # No hardcoded artist seed.
    # ARTIST_POOL is populated dynamically by start_episode.py when needed.


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync Canvas & Glass Google Sheet schema.")
    parser.add_argument("--apply", action="store_true", help="Apply changes instead of read-only inspection.")
    args = parser.parse_args()

    token = get_token()

    plan = [
        (ARTIST_POOL_SHEET, ARTIST_POOL_HEADERS),
        (EPISODES_SHEET, EPISODES_HEADERS),
        (TRACKS_SHEET, TRACKS_HEADERS),
        (TRACK_PROBLEMS_SHEET, TRACK_PROBLEMS_HEADERS),
        (SETTINGS_SHEET, SETTINGS_HEADERS),
        (WINE_REGISTRY_SHEET, WINE_REGISTRY_HEADERS),
        (AVATAR_SHEET, AVATAR_HEADERS),
        (AVATAR_REGISTRY_SHEET, AVATAR_REGISTRY_HEADERS),
        (REDIRECT_REGISTRY_SHEET, REDIRECT_REGISTRY_HEADERS),
    ]

    if not args.apply:
        titles = get_sheet_titles(token)
        print("Existing sheets:")
        for title in titles:
            print("-", title)
        print("\nPlanned schema sync:")
        for title, headers in plan:
            state = "exists" if title in titles else "missing"
            print(f"- {title}: {state}, required columns={len(headers)}")
        return

    for title, headers in plan:
        ensure_sheet_with_headers(token, title, headers)
    ensure_settings(token)
    ensure_track_problems_seed(token)
    ensure_avatar_registry_seed(token)
    ensure_redirect_registry_seed(token)
    ensure_artist_pool_seed(token)

    print("Google Sheet schema synced.")
    print("No hardcoded artist or redirect seeds were inserted.")


if __name__ == "__main__":
    main()
