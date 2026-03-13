#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

from finalize_avatar_monologues import fs_slug as pattern_fs_slug
from start_episode import ENV_LOCAL, ROOT, call_anthropic, call_perplexity, load_env_file
from sync_google_sheet_schema import AVATAR_SHEET, EPISODES_SHEET, get_token, get_values, now_iso, update_values


OUTPUT_ROOT = ROOT / "output"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def find_manifest(run_slug: str) -> Path:
    manifest_path = OUTPUT_ROOT / run_slug / "publish" / f"{run_slug}_start-manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"Manifest not found: {manifest_path}")
    return manifest_path


def image_paths_from_manifest(manifest: dict) -> list[Path]:
    paths = [Path(item) for item in manifest.get("expected_inputs", [])]
    if not all(path.exists() for path in paths):
        raise RuntimeError("Not all expected painting files are present.")
    return paths


def image_block(path: Path) -> dict:
    media_type = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".tif": "image/tiff",
        ".tiff": "image/tiff",
    }.get(path.suffix.lower(), "image/jpeg")
    data = base64.b64encode(path.read_bytes()).decode()
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": media_type,
            "data": data,
        },
    }


def prepare_pd_ready_image(run_slug: str, image_path: Path, index: int) -> Path:
    pd_dir = OUTPUT_ROOT / run_slug / "pd"
    pd_dir.mkdir(parents=True, exist_ok=True)
    prepared = pd_dir / f"{run_slug}_painting{index}_pd.jpg"
    subprocess.run(
        [
            os.environ.get("PYTHON", "python3"),
            str(ROOT / "scripts" / "prepare_pd_image.py"),
            str(image_path),
            "--output",
            str(prepared),
            "--target-mb",
            "4.5",
            "--hard-max-mb",
            "5.0",
        ],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
        text=True,
    )
    return prepared


def call_anthropic_with_content(api_key: str, system_prompt: str, content: list[dict], max_tokens: int = 5000) -> str:
    payload = {
        "model": "claude-sonnet-4-5-20250929",
        "max_tokens": max_tokens,
        "temperature": 0.3,
        "system": system_prompt,
        "messages": [{"role": "user", "content": content}],
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
    with urllib.request.urlopen(req, timeout=240) as resp:
        body = json.loads(resp.read())
    parts = [item.get("text", "") for item in body.get("content", []) if item.get("type") == "text"]
    text = "\n".join(parts).strip()
    if not text:
        raise RuntimeError("Anthropic vision returned empty text.")
    return text


def set_episode_status(episode_id: str, status: str, error: str = "") -> None:
    token = get_token()
    rows = get_values(token, f"{EPISODES_SHEET}!A:AE")
    headers = rows[0]
    values = rows[:]
    for idx, row in enumerate(values[1:], start=1):
        row = row + [""] * (len(headers) - len(row))
        if "episode_id" in headers and row[headers.index("episode_id")] == episode_id:
            if "episode_status" in headers:
                row[headers.index("episode_status")] = status
            if "status" in headers:
                row[headers.index("status")] = status
            if "updated_at" in headers:
                row[headers.index("updated_at")] = now_iso()
            if "error" in headers:
                row[headers.index("error")] = error
            values[idx] = row
            break
    update_values(token, f"{EPISODES_SHEET}!A1:AE{len(values)}", values)


def write_pd_files(manifest: dict, anthropic_key: str) -> list[Path]:
    system_prompt = (ROOT / "docs" / "final-pd-agent.txt").read_text().strip()
    episode_dir = Path(manifest["output_dir"]) / "pd"
    episode_dir.mkdir(parents=True, exist_ok=True)
    paths = image_paths_from_manifest(manifest)
    playlist_name: str | None = None
    outputs: list[Path] = []
    for idx, image_path in enumerate(paths, start=1):
        prepared_path = prepare_pd_ready_image(manifest["episode_slug"], image_path, idx)
        extra = ""
        if playlist_name:
            extra = f"\nUse this exact shared PLAYLIST_NAME for this episode: {playlist_name}\n"
        content = [
            {"type": "text", "text": f"Analyse this finished painting image.\nPAINTING_INDEX: {idx}{extra}"},
            image_block(prepared_path),
        ]
        text = call_anthropic_with_content(anthropic_key, system_prompt, content)
        match = re.search(r"PLAYLIST_NAME:\s*(.+)", text)
        if match and not playlist_name:
            playlist_name = match.group(1).strip()
        out = episode_dir / f"{manifest['episode_slug']}_PD-text{idx}.txt"
        out.write_text(text.strip() + "\n")
        outputs.append(out)
    return outputs


def pd_playlist_name(pd_path: Path) -> str:
    text = pd_path.read_text()
    match = re.search(r"PLAYLIST_NAME:\s*(.+)", text)
    if not match:
        raise RuntimeError("PLAYLIST_NAME missing from PD text.")
    return match.group(1).strip()


def write_wine_files(manifest: dict, anthropic_key: str, pd_paths: list[Path]) -> list[Path]:
    system_prompt = (ROOT / "docs" / "final-wine-agent.txt").read_text().strip()
    wine_dir = Path(manifest["output_dir"]) / "wine"
    wine_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    titles = manifest.get("painting_titles", {})
    for idx, pd_path in enumerate(pd_paths, start=1):
        text = call_anthropic(anthropic_key, system_prompt, pd_path.read_text())
        title = titles.get(f"painting{idx}", f"Painting{idx}")
        out = wine_dir / f"{manifest['episode_slug']}_{re.sub(r'[^A-Za-z0-9]+','_', title).strip('_')}_wine{idx}.txt"
        out.write_text(text.strip() + "\n")
        paths.append(out)
    return paths


def write_playlist_plan(manifest: dict, perplexity_key: str, pd_paths: list[Path]) -> Path:
    system_prompt = (ROOT / "docs" / "final-music-agent.txt").read_text().strip()
    playlist_name = pd_playlist_name(pd_paths[0])
    total_duration = 60
    user_prompt = (
        "Build one playlist plan for this episode.\n"
        f"Use this exact playlist name: {playlist_name}\n"
        f"Total duration target: {total_duration} minutes\n\n"
        f"PD_TEXT_1:\n{pd_paths[0].read_text()}\n\n"
        f"PD_TEXT_2:\n{pd_paths[1].read_text()}\n\n"
        f"PD_TEXT_3:\n{pd_paths[2].read_text()}\n"
    )
    text = call_perplexity(perplexity_key, system_prompt, user_prompt)
    spotify_dir = Path(manifest["output_dir"]) / "spotify"
    spotify_dir.mkdir(parents=True, exist_ok=True)
    plan_path = spotify_dir / f"{manifest['episode_slug']}_playlist_{re.sub(r'[^A-Za-z0-9]+','_', playlist_name).strip('_')}.txt"
    enriched = (
        text.strip()
        + "\n"
        + f"PLAYLIST_REDIRECT_URL: {manifest['redirects']['spotify_playlist']}\n"
        + f"PLAYLIST_QR_TARGET: {manifest['redirects']['episode_video']}\n"
    )
    plan_path.write_text(enriched)
    return plan_path


def select_narrative_pattern(manifest: dict, anthropic_key: str, pd_paths: list[Path]) -> dict:
    allowed_patterns = {
        "01": "THE SENSUALIST PHILOSOPHER",
        "02": "THE ALCHEMIST CURATOR",
        "03": "THE DOUBLE AGENT",
        "04": "THE LITURGIST",
        "05": "THE WITNESS OF TRANSFORMATION",
    }
    system_prompt = (ROOT / "docs" / "final-random-agent.txt").read_text().strip()
    adna_text = Path(manifest["artifacts"]["adna_text"]).read_text()
    allowed_block = "\n".join(f"- {k}: {v}" for k, v in allowed_patterns.items())
    user_prompt = f"""
Return exactly these lines:
narrative_pattern_id: ...
narrative_pattern_name: ...
selection_justification: ...
monologue_1_tone_variant: ...
monologue_2_tone_variant: ...
monologue_3_tone_variant: ...
monologue_4_tone_variant: ...
monologue_4_closing_mode: ...
reuse_risk_note: ...

Allowed narrative patterns (use exactly one of these ids and names, no others):
{allowed_block}

episode_id: {manifest['episode_id']}
artist_name: {manifest['artist_name']}

ADNA:
{adna_text}

PD_TEXT_1:
{pd_paths[0].read_text()}

PD_TEXT_2:
{pd_paths[1].read_text()}

PD_TEXT_3:
{pd_paths[2].read_text()}
""".strip()
    text = call_anthropic(anthropic_key, system_prompt, user_prompt)
    data: dict[str, str] = {}
    for line in text.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            data[k.strip()] = v.strip()
    required = [
        "narrative_pattern_id",
        "narrative_pattern_name",
        "monologue_1_tone_variant",
        "monologue_2_tone_variant",
        "monologue_3_tone_variant",
        "monologue_4_tone_variant",
        "monologue_4_closing_mode",
    ]
    missing = [k for k in required if not data.get(k)]
    if missing:
        raise RuntimeError(f"Random Agent output incomplete: {missing}")
    pattern_id = data["narrative_pattern_id"].zfill(2)
    if pattern_id not in allowed_patterns:
        raise RuntimeError(f"Random Agent returned non-canonical narrative_pattern_id: {data['narrative_pattern_id']}")
    data["narrative_pattern_id"] = pattern_id
    data["narrative_pattern_name"] = allowed_patterns[pattern_id]
    return data


def parse_monologue_blocks(text: str) -> dict[str, str]:
    pattern = re.compile(r"<<<MON(?P<index>[1-4])>>>\s*(?P<body>.*?)\s*<<<END_MON(?P=index)>>>(?:\s*|$)", re.DOTALL)
    result: dict[str, str] = {}
    for match in pattern.finditer(text):
        result[f"mon{match.group('index')}"] = match.group("body").strip()
    if set(result) != {"mon1", "mon2", "mon3", "mon4"}:
        raise RuntimeError("Could not parse all four draft monologues.")
    return result


def write_avatar_drafts_and_package(manifest: dict, anthropic_key: str, pd_paths: list[Path], wine_paths: list[Path], plan_path: Path, pattern: dict) -> Path:
    system_prompt = (ROOT / "docs" / "final-avatar-agent.txt").read_text().strip()
    adna_text = Path(manifest["artifacts"]["adna_text"]).read_text()
    playlist_name = pd_playlist_name(pd_paths[0])
    user_prompt = f"""
Write four draft monologue blocks for one episode.
Return only:
<<<MON1>>>...<<<END_MON1>>>
<<<MON2>>>...<<<END_MON2>>>
<<<MON3>>>...<<<END_MON3>>>
<<<MON4>>>...<<<END_MON4>>>

episode_id: {manifest['episode_id']}
artist_name: {manifest['artist_name']}
narrative_pattern_id: {pattern['narrative_pattern_id']}
narrative_pattern_name: {pattern['narrative_pattern_name']}
monologue_1_tone_variant: {pattern['monologue_1_tone_variant']}
monologue_2_tone_variant: {pattern['monologue_2_tone_variant']}
monologue_3_tone_variant: {pattern['monologue_3_tone_variant']}
monologue_4_tone_variant: {pattern['monologue_4_tone_variant']}
monologue_4_closing_mode: {pattern['monologue_4_closing_mode']}
duration_1_min: 20
duration_2_min: 20
duration_3_min: 20
total_duration_min: 60
playlist_url: {manifest.get('spotify_playlist_url', '')}
playlist_qr: {manifest['redirects']['spotify_playlist']}
playlist_name: {playlist_name}
research_hook: {manifest.get('research_hook', '')}
research_sensory_facts: {json.dumps(manifest.get('research_sensory_facts', []), ensure_ascii=False)}
research_philosophy_anchor: {manifest.get('research_philosophy_anchor', '')}

ADNA:
{adna_text}

PD_TEXT_1:
{pd_paths[0].read_text()}

PD_TEXT_2:
{pd_paths[1].read_text()}

PD_TEXT_3:
{pd_paths[2].read_text()}

WINE_1:
{wine_paths[0].read_text()}

WINE_2:
{wine_paths[1].read_text()}

WINE_3:
{wine_paths[2].read_text()}
""".strip()
    response = call_anthropic(anthropic_key, system_prompt, user_prompt)
    blocks = parse_monologue_blocks(response)
    draft_dir = Path(manifest["output_dir"]) / "monologues" / "draft"
    draft_dir.mkdir(parents=True, exist_ok=True)
    pattern_slug = pattern_fs_slug(pattern["narrative_pattern_name"])
    draft_paths = {
        "mon1": draft_dir / f"{manifest['episode_slug']}_{pattern_slug}_painting1_mon1_draft.txt",
        "mon2": draft_dir / f"{manifest['episode_slug']}_{pattern_slug}_painting2_mon2_draft.txt",
        "mon3": draft_dir / f"{manifest['episode_slug']}_{pattern_slug}_painting3_mon3_draft.txt",
        "mon4": draft_dir / f"{manifest['episode_slug']}_{pattern_slug}_mon4_draft.txt",
    }
    for key, path in draft_paths.items():
        path.write_text(blocks[key].strip() + "\n")
    package = {
        "episode_id": manifest["episode_id"],
        "episode_slug": manifest["episode_slug"],
        "artist_name": manifest["artist_name"],
        "artist_slug": manifest["artist_slug"],
        "narrative_pattern_id": pattern["narrative_pattern_id"],
        "narrative_pattern_name": pattern["narrative_pattern_name"],
        "tone_path": {
            "mon1_tone_variant": pattern["monologue_1_tone_variant"],
            "mon2_tone_variant": pattern["monologue_2_tone_variant"],
            "mon3_tone_variant": pattern["monologue_3_tone_variant"],
            "mon4_tone_variant": pattern["monologue_4_tone_variant"],
            "mon4_closing_mode": pattern["monologue_4_closing_mode"],
        },
        "draft_monologue_scripts": {k: str(v) for k, v in draft_paths.items()},
        "final_monologue_scripts": {},
        "hg_template_mapping": {
            "status": "pending_manual_template_selection",
        },
    }
    package_path = Path(manifest["output_dir"]) / "monologues" / f"{manifest['episode_slug']}_{pattern_slug}_avatar-package.json"
    save_json(package_path, package)
    return package_path


def update_manifest_with_artifacts(manifest_path: Path, updates: dict) -> dict:
    manifest = load_json(manifest_path)
    manifest.update({k: v for k, v in updates.items() if k not in {"artifacts", "human_loop"}})
    manifest.setdefault("artifacts", {}).update(updates.get("artifacts", {}))
    if "human_loop" in updates:
        manifest.setdefault("human_loop", {}).update(updates["human_loop"])
    save_json(manifest_path, manifest)
    return manifest


def continue_from_paintings(manifest_path: Path) -> None:
    manifest = load_json(manifest_path)
    env = {**load_env_file(ENV_LOCAL), **os.environ}
    anthropic_key = env.get("ANTHROPIC_API_KEY", "").strip()
    perplexity_key = env.get("PERPLEXITY_API_KEY", "").strip()
    if not anthropic_key or not perplexity_key:
        raise SystemExit("Missing ANTHROPIC_API_KEY or PERPLEXITY_API_KEY.")

    pd_paths = write_pd_files(manifest, anthropic_key)
    set_episode_status(manifest["episode_id"], "pd_ready")
    manifest = update_manifest_with_artifacts(
        manifest_path,
        {
            "status": "pd_ready",
            "next_step": "PD complete. Continue to Wine Agent.",
            "artifacts": {f"pd_text_{idx}": str(path) for idx, path in enumerate(pd_paths, start=1)},
            "playlist_name": pd_playlist_name(pd_paths[0]),
        },
    )

    wine_paths = write_wine_files(manifest, anthropic_key, pd_paths)
    set_episode_status(manifest["episode_id"], "wine_ready")
    manifest = update_manifest_with_artifacts(
        manifest_path,
        {
            "status": "wine_ready",
            "next_step": "Wine complete. Continue to Spotify.",
            "artifacts": {f"wine_{idx}": str(path) for idx, path in enumerate(wine_paths, start=1)},
        },
    )

    plan_path = write_playlist_plan(manifest, perplexity_key, pd_paths)
    set_episode_status(manifest["episode_id"], "playlist_ready")
    manifest = update_manifest_with_artifacts(
        manifest_path,
        {
            "status": "playlist_ready",
            "next_step": "Playlist package complete. Continue to Avatar.",
            "artifacts": {"playlist_package": str(plan_path)},
        },
    )

    spotify_error = ""
    try:
        subprocess.run(
            [
                os.environ.get("PYTHON", "python3"),
                str(ROOT / "scripts" / "create_spotify_playlist.py"),
                "--episode-slug",
                manifest["episode_slug"],
                "--episode-id",
                manifest["episode_id"],
                "--artist-slug",
                manifest["artist_slug"],
                "--plan-file",
                str(plan_path),
            ],
            cwd=str(ROOT),
            check=True,
            capture_output=True,
            text=True,
            timeout=90,
        )
        manifest = load_json(manifest_path)
    except subprocess.CalledProcessError as exc:
        spotify_error = (exc.stderr or exc.stdout or str(exc)).strip()
        manifest = update_manifest_with_artifacts(
            manifest_path,
            {
                "spotify_error": spotify_error,
                "next_step": "Spotify posting failed or was rate-limited. Avatar may continue from playlist package.",
            },
        )
    except subprocess.TimeoutExpired as exc:
        spotify_error = f"Spotify posting timed out after {exc.timeout} seconds."
        manifest = update_manifest_with_artifacts(
            manifest_path,
            {
                "spotify_error": spotify_error,
                "next_step": "Spotify posting timed out. Avatar may continue from playlist package.",
            },
        )

    subprocess.run(
        [
            os.environ.get("PYTHON", "python3"),
            str(ROOT / "scripts" / "generate_spotify_cover_variants.py"),
            "--episode-slug",
            manifest["episode_slug"],
            "--episode-id",
            manifest["episode_id"],
            "--artist-name",
            manifest["artist_name"],
            "--qr-target",
            manifest["redirects"]["episode_video"],
        ],
        cwd=str(ROOT),
        check=True,
    )


def continue_from_cover_selection(manifest_path: Path) -> None:
    manifest = load_json(manifest_path)
    env = {**load_env_file(ENV_LOCAL), **os.environ}
    anthropic_key = env.get("ANTHROPIC_API_KEY", "").strip()
    if not anthropic_key:
        raise SystemExit("Missing ANTHROPIC_API_KEY.")

    pd_paths = [Path(manifest["artifacts"][f"pd_text_{idx}"]) for idx in (1, 2, 3)]
    wine_paths = [Path(manifest["artifacts"][f"wine_{idx}"]) for idx in (1, 2, 3)]
    plan_path = Path(manifest["artifacts"]["playlist_package"])

    pattern = select_narrative_pattern(manifest, anthropic_key, pd_paths)
    package_path = write_avatar_drafts_and_package(manifest, anthropic_key, pd_paths, wine_paths, plan_path, pattern)
    set_episode_status(manifest["episode_id"], "avatar_draft_ready")
    update_manifest_with_artifacts(
        manifest_path,
        {
            "status": "avatar_draft_ready",
            "next_step": "Avatar drafts complete. Finalize monologues and assemble HeyGen prompts.",
            "artifacts": {"avatar_package": str(package_path)},
            "avatar_selection": {
                "narrative_pattern_id": pattern["narrative_pattern_id"],
                "narrative_pattern_name": pattern["narrative_pattern_name"],
            },
        },
    )

    subprocess.run(
        [
            os.environ.get("PYTHON", "python3"),
            str(ROOT / "scripts" / "finalize_avatar_monologues.py"),
            "--package",
            str(package_path),
            "--manifest",
            str(manifest_path),
        ],
        cwd=str(ROOT),
        check=True,
    )


def build_youtube_package(manifest_path: Path) -> None:
    manifest = load_json(manifest_path)
    env = {**load_env_file(ENV_LOCAL), **os.environ}
    anthropic_key = env.get("ANTHROPIC_API_KEY", "").strip()
    if not anthropic_key:
        raise SystemExit("Missing ANTHROPIC_API_KEY.")
    system_prompt = (ROOT / "docs" / "final-publisher-agent.txt").read_text().strip()
    mon1 = Path(manifest["artifacts"]["mon1_final"]).read_text()
    mon2 = Path(manifest["artifacts"]["mon2_final"]).read_text()
    mon3 = Path(manifest["artifacts"]["mon3_final"]).read_text()
    mon4 = Path(manifest["artifacts"]["mon4_final"]).read_text()
    user_prompt = f"""
Return exactly this format:
YOUTUBE_TITLE: ...
YOUTUBE_TIMESTAMPS:
00:00 ...
20:00 ...
40:00 ...
60:00 ...
YOUTUBE_DESCRIPTION:
...
YOUTUBE_TAGS:
tag1, tag2, tag3

artist_name: {manifest['artist_name']}
playlist_name: {manifest.get('playlist_name', '')}
spotify_playlist_url: {manifest.get('spotify_playlist_url', '')}
video_redirect_url: {manifest['redirects']['episode_video']}
painting1_redirect_url: {manifest['redirects']['painting1']}
painting2_redirect_url: {manifest['redirects']['painting2']}
painting3_redirect_url: {manifest['redirects']['painting3']}

MON1:
{mon1}

MON2:
{mon2}

MON3:
{mon3}

MON4:
{mon4}
""".strip()
    text = call_anthropic(anthropic_key, system_prompt, user_prompt)
    youtube_dir = Path(manifest["output_dir"]) / "youtube"
    youtube_dir.mkdir(parents=True, exist_ok=True)
    out = youtube_dir / f"{manifest['episode_slug']}_videodescription.txt"
    out.write_text(text.strip() + "\n")
    set_episode_status(manifest["episode_id"], "youtube_package_ready")
    update_manifest_with_artifacts(
        manifest_path,
        {
            "status": "youtube_package_ready",
            "next_step": "Test mode final reached: YouTube package is ready. Render is skipped.",
            "artifacts": {"youtube_description": str(out)},
        },
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Continue a Canvas & Glass episode after a human-loop checkpoint.")
    parser.add_argument("--run-slug", required=True)
    parser.add_argument("--event", required=True, choices=["paintings_placed", "cover_selected", "monologues_approved"])
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest_path = find_manifest(args.run_slug)
    if args.event == "paintings_placed":
        continue_from_paintings(manifest_path)
        print("Continuation complete through Spotify cover generation.")
    elif args.event == "cover_selected":
        continue_from_cover_selection(manifest_path)
        print("Continuation complete through HeyGen prompts.")
    else:
        build_youtube_package(manifest_path)
        print("YouTube package ready.")


if __name__ == "__main__":
    main()
