#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

from sync_google_sheet_schema import AVATAR_SHEET, EPISODES_SHEET, get_token as get_gsheets_token
from sync_google_sheet_schema import get_values, now_iso, update_values


ROOT = Path(__file__).resolve().parents[1]
ENV_LOCAL = ROOT / ".env.local"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODELS = [
    "claude-sonnet-4-5-20250929",
    "claude-sonnet-4-20250514",
    "claude-3-7-sonnet-20250219",
]


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


def read_text(path: str) -> str:
    return Path(path).read_text().strip()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


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
            parts = []
            for item in body.get("content", []):
                if item.get("type") == "text":
                    parts.append(item.get("text", ""))
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


def parse_blocks(text: str) -> dict[str, str]:
    pattern = re.compile(
        r"<<<MON(?P<index>[1-4])>>>\s*(?P<body>.*?)\s*<<<END_MON(?P=index)>>>(?:\s*|$)",
        re.DOTALL,
    )
    result: dict[str, str] = {}
    for match in pattern.finditer(text):
        result[f"mon{match.group('index')}"] = match.group("body").strip()
    if set(result) != {"mon1", "mon2", "mon3", "mon4"}:
        raise RuntimeError("Could not parse all four monologue blocks from Anthropic output.")
    return result


def normalize_for_comparison(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def sentence_chunks(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [part.strip().lower() for part in parts if part.strip()]


def overlap_ratio(a: str, b: str) -> float:
    a_tokens = {token for token in re.findall(r"[a-z0-9']+", a.lower()) if token}
    b_tokens = {token for token in re.findall(r"[a-z0-9']+", b.lower()) if token}
    if not a_tokens or not b_tokens:
        return 0.0
    return len(a_tokens & b_tokens) / min(len(a_tokens), len(b_tokens))


def validate_finals(drafts: dict[str, str], finals: dict[str, str]) -> None:
    issues: list[str] = []

    for mon_key, draft_text in drafts.items():
        final_text = finals[mon_key]
        if normalize_for_comparison(draft_text) == normalize_for_comparison(final_text):
            issues.append(f"{mon_key}: final is identical to draft.")
            continue

        draft_sentences = sentence_chunks(draft_text)
        final_sentences = sentence_chunks(final_text)
        changed_sentences = 0
        for sentence in final_sentences:
            if not draft_sentences or max(overlap_ratio(sentence, draft) for draft in draft_sentences) < 0.92:
                changed_sentences += 1
        if changed_sentences < 1:
            issues.append(f"{mon_key}: finalization is too cosmetic.")

    mon2_sentences = sentence_chunks(finals["mon2"])
    if len(mon2_sentences) >= 4:
        for i in range(len(mon2_sentences) - 1):
            if overlap_ratio(mon2_sentences[i], mon2_sentences[i + 1]) > 0.72:
                issues.append("mon2: adjacent sentences are too duplicative.")
                break

    if issues:
        raise RuntimeError("Final monologue validation failed: " + " ".join(issues))


def build_system_prompt(avatar_sp: str, avatar_osr: str) -> str:
    return (
        "You are the final Avatar Agent execution layer for Canvas & Glass.\n\n"
        "Your job is to transform four draft monologues into four approved final monologues.\n"
        "You must preserve mandatory content, maintain one coherent episode-level voice, and satisfy OSR.\n"
        "Alexander must sound like a real person: a gallerist and painter, but unmistakably human, warm, and present.\n"
        "These monologues must feel connected in temperament, pressure, and authorship across the full hour.\n"
        "Do not behave like a proofreader. Behave like a final spoken-language writer.\n"
        "Do not output commentary, notes, markdown, or explanations.\n"
        "Return only the four monologue blocks using the exact delimiters provided.\n\n"
        "System Prompt Canon:\n"
        f"{avatar_sp}\n\n"
        "OSR Canon:\n"
        f"{avatar_osr}"
    )


def build_user_prompt(package: dict, manifest: dict) -> str:
    adna_text = read_text(manifest["artifacts"]["adna_text"])
    pd1 = read_text(manifest["artifacts"]["pd_text_1"])
    pd2 = read_text(manifest["artifacts"]["pd_text_2"])
    pd3 = read_text(manifest["artifacts"]["pd_text_3"])
    wine1 = read_text(manifest["artifacts"]["wine_1"])
    wine2 = read_text(manifest["artifacts"]["wine_2"])
    wine3 = read_text(manifest["artifacts"]["wine_3"])
    playlist = read_text(manifest["artifacts"]["playlist_package"])
    mon1 = read_text(package["draft_monologue_scripts"]["mon1"])
    mon2 = read_text(package["draft_monologue_scripts"]["mon2"])
    mon3 = read_text(package["draft_monologue_scripts"]["mon3"])
    mon4 = read_text(package["draft_monologue_scripts"]["mon4"])

    return f"""
Episode:
- episode_id: {package['episode_id']}
- episode_slug: {package['episode_slug']}
- artist_name: {package['artist_name']}
- artist_slug: {package['artist_slug']}
- narrative_pattern_id: {package['narrative_pattern_id']}
- narrative_pattern_name: {package['narrative_pattern_name']}

Tone path:
- mon1_tone_variant: {package['tone_path']['mon1_tone_variant']}
- mon2_tone_variant: {package['tone_path']['mon2_tone_variant']}
- mon3_tone_variant: {package['tone_path']['mon3_tone_variant']}
- mon4_tone_variant: {package['tone_path']['mon4_tone_variant']}
- mon4_closing_mode: {package['tone_path']['mon4_closing_mode']}

Session durations:
- duration_1_min: 20
- duration_2_min: 20
- duration_3_min: 20
- total_duration_min: 60

Redirects and playlist:
- playlist_name: {manifest['playlist_name']}
- spotify_playlist_url: {manifest['spotify_playlist_url']}
- playlist_redirect_url: {manifest['redirects']['spotify_playlist']}
- video_redirect_url: {manifest['redirects']['episode_video']}

ADNA:
{adna_text}

PD_TEXT_1:
{pd1}

PD_TEXT_2:
{pd2}

PD_TEXT_3:
{pd3}

WINE_1:
{wine1}

WINE_2:
{wine2}

WINE_3:
{wine3}

PLAYLIST_PACKAGE:
{playlist}

Draft MON1:
{mon1}

Draft MON2:
{mon2}

Draft MON3:
{mon3}

Draft MON4:
{mon4}

Task:
1. Rewrite these four drafts into final approved monologues.
2. Keep the same base narrative pattern across all four.
3. Make them sound human-spoken, warm, linked, and non-modular.
4. Preserve required content from draft and upstream materials.
5. Preserve the artist name in spoken English as Ivan Aivazovsky.
6. Preserve the playlist name Light After the Tide.
7. MON1, MON2, MON3, MON4 must still feel like one authored hour.
8. Do not produce generic outro language.
9. Do not mention prompt logic, variables, or OSR.
10. This is a real finalization pass, not a cosmetic proofread. Each monologue should gain meaningful improvement in flow, linkage, embodiment, or emotional clarity.
11. Avoid module-stacking. Biography, painting description, wine, playlist, and transition should feel woven into spoken movement.
12. MON2 must not duplicate its own orientation logic. If you include an arc paragraph and a painting-2 paragraph, they must do different jobs.
13. MON3 must deepen the approach into the third painting. Do not limit MON3 changes to factual cleanup only.
14. MON4 must sound gathered and human, with gratitude integrated into the closing movement rather than pasted in as a stock thank-you.
15. Return only the four blocks in this exact format:

<<<MON1>>>
[final mon1 text]
<<<END_MON1>>>
<<<MON2>>>
[final mon2 text]
<<<END_MON2>>>
<<<MON3>>>
[final mon3 text]
<<<END_MON3>>>
<<<MON4>>>
[final mon4 text]
<<<END_MON4>>>
""".strip()


def write_finals(final_paths: dict[str, str], monologues: dict[str, str]) -> None:
    for key, path in final_paths.items():
        Path(path).write_text(monologues[key].strip() + "\n")


def build_heygen_prompt_files(package: dict, env: dict[str, str]) -> dict[str, str]:
    heygen_dir = ROOT / "output" / package["episode_slug"] / "heygen" / "prompts"
    heygen_dir.mkdir(parents=True, exist_ok=True)
    prompt_files: dict[str, str] = {}
    for mon_key, final_path in package["final_monologue_scripts"].items():
        prompt_name = Path(final_path).name.replace("_final.txt", "_heygen.txt")
        prompt_path = heygen_dir / prompt_name
        text = Path(final_path).read_text().strip()
        prompt_path.write_text(text + "\n")
        prompt_files[mon_key] = str(prompt_path)

    handoff = {
        "episode_id": package["episode_id"],
        "episode_slug": package["episode_slug"],
        "narrative_pattern_id": package["narrative_pattern_id"],
        "narrative_pattern_name": package["narrative_pattern_name"],
        "heygen_status": "prompt_ready_not_sent",
        "character_type": "talking_photo",
        "talking_photo_id": env.get("HEYGEN_TALKING_PHOTO_ID", ""),
        "voice_id": env.get("HEYGEN_VOICE_ID", ""),
        "template_mapping_status": package["hg_template_mapping"]["status"],
        "prompt_files": prompt_files,
    }
    handoff_path = heygen_dir.parent / f"{package['episode_slug']}_heygen-handoff.json"
    handoff_path.write_text(json.dumps(handoff, ensure_ascii=False, indent=2) + "\n")
    return {"prompt_files": prompt_files, "handoff_path": str(handoff_path)}


def update_package(package_path: Path, package: dict, heygen_payload: dict[str, str]) -> None:
    package["heygen_prompt_handoff"] = {
        "status": "prompt_ready_not_sent",
        "note": "Final monologues exist. HeyGen prompts are assembled, but nothing has been sent to HeyGen.",
        "prompt_files": heygen_payload["prompt_files"],
        "handoff_path": heygen_payload["handoff_path"],
    }
    package["avatar_api_status"] = "finalized_via_anthropic_api"
    package_path.write_text(json.dumps(package, ensure_ascii=False, indent=2) + "\n")


def update_manifest(manifest_path: Path, manifest: dict, package: dict, heygen_payload: dict[str, str]) -> None:
    manifest["status"] = "heygen_prompt_ready_not_sent"
    manifest["next_step"] = "Review HeyGen templates and stop. Do not submit to HeyGen yet."
    manifest.setdefault("artifacts", {})
    manifest.setdefault("avatar_selection", {})
    manifest["artifacts"]["mon1_final"] = package["final_monologue_scripts"]["mon1"]
    manifest["artifacts"]["mon2_final"] = package["final_monologue_scripts"]["mon2"]
    manifest["artifacts"]["mon3_final"] = package["final_monologue_scripts"]["mon3"]
    manifest["artifacts"]["mon4_final"] = package["final_monologue_scripts"]["mon4"]
    manifest["artifacts"]["heygen_handoff"] = heygen_payload["handoff_path"]
    manifest["avatar_selection"]["heygen_status"] = "prompt_ready_not_sent"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")


def update_episode_row(episode_id: str, error: str = "") -> None:
    token = get_gsheets_token()
    rows = get_values(token, "EPISODES!A:AE")
    headers = rows[0]
    values = rows[:]
    for idx, row in enumerate(values[1:], start=1):
        row = row + [""] * (len(headers) - len(row))
        if "episode_id" in headers and row[headers.index("episode_id")] == episode_id:
            if "episode_status" in headers:
                row[headers.index("episode_status")] = "heygen_prompt_ready_not_sent"
            if "updated_at" in headers:
                row[headers.index("updated_at")] = now_iso()
            if "error" in headers:
                row[headers.index("error")] = error
            values[idx] = row
            break
    update_values(token, f"{EPISODES_SHEET}!A1:AE{len(values)}", values)


def update_avatar_row(package: dict) -> None:
    token = get_gsheets_token()
    rows = get_values(token, "AVATAR!A:N")
    headers = rows[0]
    values = rows[:]
    target_episode = package["episode_id"]
    found = False
    for idx, row in enumerate(values[1:], start=1):
        row = row + [""] * (len(headers) - len(row))
        if row[headers.index("episode_id")] == target_episode:
            mapping = {
                "episode_id": package["episode_id"],
                "artist_name": package["artist_name"],
                "artist_slug": package["artist_slug"],
                "narrative_pattern_id": package["narrative_pattern_id"],
                "narrative_pattern_name": package["narrative_pattern_name"],
                "mon1_tone_variant": package["tone_path"]["mon1_tone_variant"],
                "mon2_tone_variant": package["tone_path"]["mon2_tone_variant"],
                "mon3_tone_variant": package["tone_path"]["mon3_tone_variant"],
                "mon4_tone_variant": package["tone_path"]["mon4_tone_variant"],
                "mon4_closing_mode": package["tone_path"]["mon4_closing_mode"],
                "recorded_at": now_iso(),
            }
            for key, value in mapping.items():
                if key in headers:
                    row[headers.index(key)] = value
            values[idx] = row
            found = True
            break
    if not found:
        new_row = [""] * len(headers)
        mapping = {
            "episode_id": package["episode_id"],
            "artist_name": package["artist_name"],
            "artist_slug": package["artist_slug"],
            "narrative_pattern_id": package["narrative_pattern_id"],
            "narrative_pattern_name": package["narrative_pattern_name"],
            "mon1_tone_variant": package["tone_path"]["mon1_tone_variant"],
            "mon2_tone_variant": package["tone_path"]["mon2_tone_variant"],
            "mon3_tone_variant": package["tone_path"]["mon3_tone_variant"],
            "mon4_tone_variant": package["tone_path"]["mon4_tone_variant"],
            "mon4_closing_mode": package["tone_path"]["mon4_closing_mode"],
            "recorded_at": now_iso(),
        }
        for key, value in mapping.items():
            if key in headers:
                new_row[headers.index(key)] = value
        values.append(new_row)
    update_values(token, f"{AVATAR_SHEET}!A1:N{len(values)}", values)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Finalize Avatar monologues through Anthropic API and assemble HeyGen prompts.")
    parser.add_argument("--package", required=True, help="Path to avatar package JSON.")
    parser.add_argument("--manifest", required=True, help="Path to episode manifest JSON.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    env = {**load_env_file(ENV_LOCAL), **os.environ}
    api_key = env.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("Missing ANTHROPIC_API_KEY in environment or .env.local.")

    package_path = Path(args.package)
    manifest_path = Path(args.manifest)
    package = load_json(package_path)
    manifest = load_json(manifest_path)

    avatar_sp = read_text(str(ROOT / "docs" / "final-avatar-agent.txt"))
    avatar_osr = read_text(str(ROOT / "docs" / "final-avatar-agent-orchestration-osr.txt"))

    response = call_anthropic(
        api_key,
        build_system_prompt(avatar_sp, avatar_osr),
        build_user_prompt(package, manifest),
    )
    monologues = parse_blocks(response)
    drafts = {key: read_text(path) for key, path in package["draft_monologue_scripts"].items()}
    validate_finals(drafts, monologues)
    write_finals(package["final_monologue_scripts"], monologues)
    heygen_payload = build_heygen_prompt_files(package, env)
    update_package(package_path, package, heygen_payload)
    update_manifest(manifest_path, manifest, package, heygen_payload)
    update_episode_row(package["episode_id"])
    update_avatar_row(package)

    print("Final monologues written:")
    for key, path in package["final_monologue_scripts"].items():
        print(f"- {key}: {path}")
    print("HeyGen prompt handoff:")
    print(f"- {heygen_payload['handoff_path']}")


if __name__ == "__main__":
    main()
