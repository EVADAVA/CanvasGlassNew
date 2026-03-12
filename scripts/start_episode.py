#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path

from sync_google_sheet_schema import (
    ARTIST_POOL_SHEET,
    EPISODES_SHEET,
    REDIRECT_REGISTRY_SHEET,
    SETTINGS_SHEET,
    append_values,
    get_token,
    get_values,
    now_iso,
    update_values,
)


ROOT = Path(__file__).resolve().parents[1]
INPUT_ROOT = ROOT / "input"
OUTPUT_ROOT = ROOT / "output"
ENV_LOCAL = ROOT / ".env.local"
OUTPUT_SUBDIRS = ["adna", "nb", "pd", "wine", "spotify", "monologues", "heygen", "qr", "publish"]
PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODELS = [
    "claude-sonnet-4-5-20250929",
    "claude-sonnet-4-20250514",
    "claude-3-7-sonnet-20250219",
]
DEFAULT_NB_PATTERN = "THE WITNESS OF TRANSFORMATION"


def slugify(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")
    return slug or "artist"


def fs_slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_") or "untitled"


def load_env_file(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    if not path.exists():
        return data
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip()
    return data


def looks_like_slug(text: str) -> bool:
    return bool(text) and bool(re.fullmatch(r"[a-z0-9_]+", text))


def values_to_dict(rows: list[list[str]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for row in rows[1:]:
        if row and row[0]:
            result[row[0]] = row[1] if len(row) > 1 else ""
    return result


def ensure_len(row: list[str], length: int) -> list[str]:
    if len(row) < length:
        row = row + [""] * (length - len(row))
    return row


def header_index(headers: list[str], *candidates: str) -> int:
    for candidate in candidates:
        if candidate in headers:
            return headers.index(candidate)
    raise KeyError(f"Missing header candidates: {candidates}")


def http_json(url: str, payload: dict, headers: dict[str, str]) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={**headers, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read())


def call_perplexity(api_key: str, system_prompt: str, user_prompt: str) -> str:
    payload = {
        "model": "sonar-pro",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
    }
    body = http_json(PERPLEXITY_URL, payload, {"Authorization": f"Bearer {api_key}"})
    return body["choices"][0]["message"]["content"].strip()


def call_anthropic(api_key: str, system_prompt: str, user_prompt: str) -> str:
    last_error: str | None = None
    for model in ANTHROPIC_MODELS:
        payload = {
            "model": model,
            "max_tokens": 5000,
            "temperature": 0.5,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        req = urllib.request.Request(
            ANTHROPIC_URL,
            data=json.dumps(payload).encode(),
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                body = json.loads(resp.read())
            parts = [item.get("text", "") for item in body.get("content", []) if item.get("type") == "text"]
            text = "\n".join(parts).strip()
            if text:
                return text
            last_error = f"Anthropic returned empty text for model {model}"
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            last_error = f"{model}: HTTP {exc.code} {detail}"
        except Exception as exc:  # noqa: BLE001
            last_error = f"{model}: {exc}"
    raise RuntimeError(last_error or "Anthropic request failed")


def next_episode_id(settings: dict[str, str], artist_rows: list[list[str]], episode_rows: list[list[str]]) -> str:
    padding = int(settings.get("episode_id_padding", "3") or "3")
    values: list[int] = []
    for rows in (artist_rows[1:], episode_rows[1:]):
        for row in rows:
            for candidate in row:
                if candidate and re.fullmatch(r"\d+", candidate):
                    values.append(int(candidate))
    nxt = max(values, default=0) + 1
    return f"{nxt:0{padding}d}"


def find_artist_row(headers: list[str], rows: list[list[str]], artist_name: str) -> tuple[int, list[str]]:
    for idx, row in enumerate(rows[1:], start=2):
        row = ensure_len(row, len(headers))
        candidate_cells = {
            row[header_index(headers, "artist_name")] if "artist_name" in headers else "",
            row[header_index(headers, "name")] if "name" in headers else "",
        }
        if artist_name.strip().lower() in {cell.strip().lower() for cell in candidate_cells if cell}:
            return idx, row
    raise ValueError(f"Artist not found in {ARTIST_POOL_SHEET}: {artist_name}")


def ensure_artist_in_pool(token: str, artist_name: str, ts: str) -> None:
    rows = get_values(token, f"{ARTIST_POOL_SHEET}!A:Z")
    headers = rows[0]
    try:
        find_artist_row(headers, rows, artist_name)
        return
    except ValueError:
        pass

    row = [""] * len(headers)
    if "name" in headers:
        row[headers.index("name")] = artist_name
    if "artist_name" in headers:
        row[headers.index("artist_name")] = artist_name
    if "artist_slug" in headers:
        row[headers.index("artist_slug")] = slugify(artist_name)
    if "category" in headers:
        row[headers.index("category")] = "Established"
    if "used" in headers:
        row[headers.index("used")] = "0"
    if "processed" in headers:
        row[headers.index("processed")] = "0"
    if "added_at" in headers:
        row[headers.index("added_at")] = ts
    append_values(token, f"{ARTIST_POOL_SHEET}!A:Z", [row])


def update_artist_pool(token: str, artist_name: str, episode_id: str, ts: str) -> tuple[str, str]:
    ensure_artist_in_pool(token, artist_name, ts)
    rows = get_values(token, f"{ARTIST_POOL_SHEET}!A:Z")
    headers = rows[0]
    row_number, row = find_artist_row(headers, rows, artist_name)

    slug_idx = header_index(headers, "artist_slug")
    legacy_name_idx = header_index(headers, "name")
    artist_name_idx = header_index(headers, "artist_name")
    category_idx = header_index(headers, "category")
    status_idx = header_index(headers, "status")
    episode_idx = header_index(headers, "episode_id", "episode_used")
    selected_idx = header_index(headers, "selected_at")
    used_idx = header_index(headers, "used")

    legacy_second = row[1].strip() if len(row) > 1 else ""
    if not row[slug_idx] or row[slug_idx] == "artist":
        row[slug_idx] = legacy_second if looks_like_slug(legacy_second) else slugify(artist_name)
    if not row[category_idx]:
        row[category_idx] = "Established"
    row[legacy_name_idx] = artist_name
    row[artist_name_idx] = artist_name
    row[status_idx] = "selected"
    row[episode_idx] = episode_id
    row[selected_idx] = ts
    if used_idx < len(row) and row[used_idx] == "":
        row[used_idx] = "0"

    update_values(token, f"{ARTIST_POOL_SHEET}!A{row_number}:Z{row_number}", [row])
    return row[artist_name_idx], row[slug_idx]


def reserve_redirects(token: str, episode_id: str, artist_name: str, artist_slug: str, ts: str) -> dict[str, str]:
    rows = get_values(token, f"{REDIRECT_REGISTRY_SHEET}!A:K")
    headers = rows[0]
    redirect_key_idx = header_index(headers, "redirect_key")
    existing = {ensure_len(row, len(headers))[redirect_key_idx] for row in rows[1:] if row}

    seeds = [
        ("video", "episode_video", f"episode{episode_id}_{artist_slug}_video"),
        ("playlist", "spotify_playlist", f"episode{episode_id}_{artist_slug}_playlist"),
        ("painting", "painting1", f"episode{episode_id}_{artist_slug}_painting1"),
        ("painting", "painting2", f"episode{episode_id}_{artist_slug}_painting2"),
        ("painting", "painting3", f"episode{episode_id}_{artist_slug}_painting3"),
    ]

    append_rows: list[list[str]] = []
    urls: dict[str, str] = {}
    for redirect_type, entity_name, key in seeds:
        url = f"https://evadava.com/{key}/"
        urls[entity_name] = url
        if key in existing:
            continue
        append_rows.append(
            [
                episode_id,
                artist_name,
                artist_slug,
                redirect_type,
                entity_name,
                key,
                url,
                "",
                "reserved",
                ts,
                "Created by start_episode bootstrap.",
            ]
        )
    if append_rows:
        append_values(token, f"{REDIRECT_REGISTRY_SHEET}!A:K", append_rows)
    return urls


def append_episode_row(
    token: str,
    episode_id: str,
    artist_name: str,
    artist_slug: str,
    input_dir: Path,
    output_dir: Path,
    redirects: dict[str, str],
    ts: str,
) -> None:
    rows = get_values(token, f"{EPISODES_SHEET}!A:AE")
    headers = rows[0]
    row = [""] * len(headers)
    field_values = {
        "episode": episode_id,
        "episode_ref": f"episode{episode_id}_{artist_slug}",
        "artist": artist_name,
        "category": "Established",
        "status": "selected",
        "created_at": ts,
        "episode_id": episode_id,
        "episode_slug": f"episode{episode_id}_{artist_slug}",
        "artist_name": artist_name,
        "artist_slug": artist_slug,
        "artist_pool_status": "selected",
        "episode_status": "selected",
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "video_redirect_url": redirects["episode_video"],
        "playlist_redirect_url": redirects["spotify_playlist"],
        "painting1_redirect_url": redirects["painting1"],
        "painting2_redirect_url": redirects["painting2"],
        "painting3_redirect_url": redirects["painting3"],
        "updated_at": ts,
    }
    for key, value in field_values.items():
        if key in headers:
            row[headers.index(key)] = value
    append_values(token, f"{EPISODES_SHEET}!A:AE", [row])


def create_workspace(episode_id: str, artist_slug: str) -> tuple[Path, Path]:
    episode_dir = f"episode{episode_id}_{artist_slug}"
    input_dir = INPUT_ROOT / episode_dir
    output_dir = OUTPUT_ROOT / episode_dir
    input_dir.mkdir(parents=True, exist_ok=True)
    for name in OUTPUT_SUBDIRS:
        (output_dir / name).mkdir(parents=True, exist_ok=True)
    return input_dir, output_dir


def write_manifest(
    episode_id: str,
    artist_name: str,
    artist_slug: str,
    input_dir: Path,
    output_dir: Path,
    redirects: dict[str, str],
    ts: str,
) -> Path:
    manifest = {
        "episode_id": episode_id,
        "episode_slug": f"episode{episode_id}_{artist_slug}",
        "artist_name": artist_name,
        "artist_slug": artist_slug,
        "status": "selected",
        "created_at": ts,
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "expected_inputs": [
            str(input_dir / "painting1.jpg"),
            str(input_dir / "painting2.jpg"),
            str(input_dir / "painting3.jpg"),
        ],
        "redirects": redirects,
        "next_step": "Run ADNA Agent on selected artist name, then feed Artist DNA into NB Agent.",
    }
    manifest_path = output_dir / "publish" / f"episode{episode_id}_{artist_slug}_start-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return manifest_path


def extract_adna_facts(adna_text: str) -> dict[str, str]:
    facts: dict[str, str] = {}
    for idx in range(1, 7):
        match = re.search(rf"fact_{idx}:\s*(.+?)(?:\n\n|\Z)", adna_text, re.DOTALL | re.IGNORECASE)
        if match:
            facts[f"fact_{idx}"] = " ".join(match.group(1).strip().split())
    return facts


def parse_nb_blocks(text: str) -> list[tuple[str, str, str]]:
    pattern = re.compile(
        r"(?:#+\s*)?PAINTING\s+([123])\s+·\s+([A-Z]+)\s*[\r\n]+(?:\*\*)?TITLE:(?:\*\*)?\s*(.+?)\s*[\r\n]+(?:\*\*)?PROMPT:(?:\*\*)?\s*(.*?)(?=(?:\n---\n|\Z))",
        re.DOTALL,
    )
    blocks: list[tuple[str, str, str]] = []
    for match in pattern.finditer(text):
        blocks.append((match.group(1).strip(), match.group(3).strip(), match.group(4).strip()))
    if len(blocks) != 3:
        raise RuntimeError("Could not parse 3 NB prompt blocks.")
    return blocks


def generate_adna_and_nb(artist_name: str, artist_slug: str, episode_id: str, output_dir: Path) -> dict[str, str]:
    env = {**load_env_file(ENV_LOCAL), **os.environ}
    perplexity_key = env.get("PERPLEXITY_API_KEY", "").strip()
    anthropic_key = env.get("ANTHROPIC_API_KEY", "").strip()
    if not perplexity_key:
        raise RuntimeError("Missing PERPLEXITY_API_KEY for ADNA generation.")
    if not anthropic_key:
        raise RuntimeError("Missing ANTHROPIC_API_KEY for NB generation.")

    adna_system = (ROOT / "docs" / "adna-agent-perplexity-system-prompt.txt").read_text().strip()
    adna_user = f"Research this artist and return the ADNA block in the exact required schema.\n\nArtist name: {artist_name}"
    adna_text = call_perplexity(perplexity_key, adna_system, adna_user)
    adna_path = output_dir / "adna" / f"episode{episode_id}_{artist_slug}_ADNA-text.txt"
    adna_path.write_text(adna_text.strip() + "\n")

    nb_system = (ROOT / "docs" / "final-nb-prompt-agent.txt").read_text().strip()
    nb_user = (
        "Use the following episode input block and return exactly three NB prompt blocks.\n\n"
        f"{adna_text}\n\n"
        f"NARRATIVE_PATTERN: {DEFAULT_NB_PATTERN}\n"
        "SEASON: spring\n"
    )
    nb_text = call_anthropic(anthropic_key, nb_system, nb_user)
    nb_blocks = parse_nb_blocks(nb_text)

    artifact_data: dict[str, str] = {"adna_text": str(adna_path)}
    for index, title, prompt in nb_blocks:
        title_slug = fs_slug(title)
        path = output_dir / "nb" / f"episode{episode_id}_{artist_slug}_NB_Painting{index}_{title_slug}.txt"
        path.write_text(f"PAINTING {index}\nTITLE: {title}\nPROMPT:\n{prompt}\n")
        artifact_data[f"nb_prompt_{index}"] = str(path)
        artifact_data[f"painting{index}"] = title
    artifact_data.update(extract_adna_facts(adna_text))
    return artifact_data


def update_episode_after_nb(token: str, episode_id: str, ts: str) -> None:
    rows = get_values(token, f"{EPISODES_SHEET}!A:AE")
    headers = rows[0]
    values = rows[:]
    for idx, row in enumerate(values[1:], start=1):
        row = row + [""] * (len(headers) - len(row))
        if row[headers.index("episode_id")] != episode_id:
            continue
        if "episode_status" in headers:
            row[headers.index("episode_status")] = "awaiting_paintings"
        if "status" in headers:
            row[headers.index("status")] = "awaiting_paintings"
        if "updated_at" in headers:
            row[headers.index("updated_at")] = ts
        if "error" in headers:
            row[headers.index("error")] = ""
        values[idx] = row
        break
    update_values(token, f"{EPISODES_SHEET}!A1:AE{len(values)}", values)


def update_manifest_after_nb(
    manifest_path: Path,
    manifest: dict,
    artifact_data: dict[str, str],
    input_dir: Path,
) -> None:
    manifest["status"] = "awaiting_paintings"
    manifest["next_step"] = "Generate or place 3 paintings, then continue to PD Agent."
    manifest.setdefault("artifacts", {})
    manifest["artifacts"]["adna_text"] = artifact_data["adna_text"]
    manifest["artifacts"]["nb_prompt_1"] = artifact_data["nb_prompt_1"]
    manifest["artifacts"]["nb_prompt_2"] = artifact_data["nb_prompt_2"]
    manifest["artifacts"]["nb_prompt_3"] = artifact_data["nb_prompt_3"]
    manifest["painting_titles"] = {
        "painting1": artifact_data["painting1"],
        "painting2": artifact_data["painting2"],
        "painting3": artifact_data["painting3"],
    }
    manifest["expected_inputs"] = [
        str(input_dir / f"{manifest['episode_slug']}_{fs_slug(artifact_data['painting1'])}.jpg"),
        str(input_dir / f"{manifest['episode_slug']}_{fs_slug(artifact_data['painting2'])}.jpg"),
        str(input_dir / f"{manifest['episode_slug']}_{fs_slug(artifact_data['painting3'])}.jpg"),
    ]
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap a Canvas & Glass episode from Main Script.")
    parser.add_argument("artist_name", help="Artist name to lock for the episode.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    artist_name = args.artist_name.strip()
    token = get_token()
    settings = values_to_dict(get_values(token, f"{SETTINGS_SHEET}!A:C"))
    artist_rows = get_values(token, f"{ARTIST_POOL_SHEET}!A:Z")
    episode_rows = get_values(token, f"{EPISODES_SHEET}!A:AE")
    episode_id = next_episode_id(settings, artist_rows, episode_rows)
    ts = now_iso()

    artist_name, artist_slug = update_artist_pool(token, artist_name, episode_id, ts)
    input_dir, output_dir = create_workspace(episode_id, artist_slug)
    redirects = reserve_redirects(token, episode_id, artist_name, artist_slug, ts)
    append_episode_row(token, episode_id, artist_name, artist_slug, input_dir, output_dir, redirects, ts)
    manifest_path = write_manifest(episode_id, artist_name, artist_slug, input_dir, output_dir, redirects, ts)

    artifact_data = generate_adna_and_nb(artist_name, artist_slug, episode_id, output_dir)
    update_episode_after_nb(token, episode_id, now_iso())
    manifest = json.loads(manifest_path.read_text())
    update_manifest_after_nb(manifest_path, manifest, artifact_data, input_dir)

    print(f"Episode started: episode{episode_id}_{artist_slug}")
    print(f"Artist locked: {artist_name}")
    print(f"Input dir: {input_dir}")
    print(f"Output dir: {output_dir}")
    print(f"Manifest: {manifest_path}")
    print(f"ADNA: {artifact_data['adna_text']}")
    print(f"NB 1: {artifact_data['nb_prompt_1']}")
    print(f"NB 2: {artifact_data['nb_prompt_2']}")
    print(f"NB 3: {artifact_data['nb_prompt_3']}")
    print("Redirects:")
    for key, url in redirects.items():
        print(f"- {key}: {url}")


if __name__ == "__main__":
    main()
