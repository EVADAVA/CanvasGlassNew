from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import streamlit as st


BASE_DIR = Path("/Users/akg/EVADAVA/CanvasGlassNew")
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"
SCRIPTS_DIR = BASE_DIR / "scripts"
START_SCRIPT = SCRIPTS_DIR / "start_episode.py"
CONTINUE_SCRIPT = SCRIPTS_DIR / "continue_episode.py"

PIPELINE_STEPS = [
    "MS start/test",
    "ADNA",
    "NB",
    "Paintings",
    "PD",
    "Wine",
    "Spotify",
    "Avatar",
    "HeyGen prompts",
    "YouTube package",
]

STATUS_TO_STEP = {
    "selected": 0,
    "adna_ready": 1,
    "nb_ready": 2,
    "awaiting_paintings": 3,
    "pd_ready": 4,
    "wine_ready": 5,
    "playlist_ready": 6,
    "spotify_posted": 6,
    "awaiting_spotify_cover_selection": 6,
    "awaiting_cover_selection": 6,
    "cover_selected": 6,
    "avatar_draft_ready": 7,
    "avatar_final_ready": 8,
    "heygen_prompt_ready_not_sent": 8,
    "youtube_package_ready": 9,
    "published": 9,
}

AGENT_GROUPS = ["MS", "ADNA", "NB", "Paintings", "PD", "Wine", "Spotify", "Avatar", "HeyGen prompts", "YouTube package"]


@dataclass
class RunState:
    manifest_path: Path
    data: dict[str, Any]

    @property
    def run_id(self) -> str:
        return self.data.get("episode_slug") or self.data.get("episode_id") or self.manifest_path.stem

    @property
    def status(self) -> str:
        return self.data.get("status", "unknown")

    @property
    def created_at(self) -> str:
        return self.data.get("created_at", "")

    @property
    def artist_name(self) -> str:
        return self.data.get("artist_name", "Unknown")


def list_manifests() -> list[RunState]:
    manifests: list[RunState] = []
    for manifest_path in sorted(OUTPUT_DIR.glob("*/publish/*_start-manifest.json")):
        try:
            data = json.loads(manifest_path.read_text())
        except json.JSONDecodeError:
            continue
        manifests.append(RunState(manifest_path=manifest_path, data=data))
    manifests.sort(key=lambda item: item.created_at or "", reverse=True)
    return manifests


def read_text_if_exists(path_str: str) -> str:
    path = Path(path_str)
    if not path.exists() or not path.is_file():
        return ""
    return path.read_text()


def save_manifest(run: RunState, data: dict[str, Any]) -> None:
    run.manifest_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def now_iso() -> str:
    from datetime import datetime

    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def existing_input_files(run: RunState) -> list[Path]:
    run_input_dir = Path(run.data.get("input_dir", ""))
    if not run_input_dir.exists():
        return []
    return sorted(path for path in run_input_dir.iterdir() if path.is_file())


def image_input_files(run: RunState) -> list[Path]:
    allowed = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}
    return [path for path in existing_input_files(run) if path.suffix.lower() in allowed]


def expected_inputs(run: RunState) -> list[Path]:
    return [Path(item) for item in run.data.get("expected_inputs", [])]


def canonicalize_painting_inputs(run: RunState) -> list[Path]:
    expected = expected_inputs(run)
    if not expected:
        return []

    files = image_input_files(run)
    if len(files) < len(expected):
        raise RuntimeError("Not enough image files to canonicalize.")

    renamed: list[Path] = []
    for source, target in zip(sorted(files), expected):
        final_target = target.with_suffix(source.suffix.lower())
        if source.resolve() != final_target.resolve():
            if final_target.exists():
                final_target.unlink()
            source.rename(final_target)
        renamed.append(final_target)

    return renamed


def artifact_rows(run: RunState) -> list[tuple[str, str, bool]]:
    rows: list[tuple[str, str, bool]] = []
    for key, value in sorted(run.data.get("artifacts", {}).items()):
        path = Path(value)
        rows.append((key, value, path.exists()))
    return rows


def artifact_exists(run: RunState, key: str) -> bool:
    value = run.data.get("artifacts", {}).get(key)
    if not value:
        return False
    path = Path(value)
    return path.exists() and path.is_file()


def avatar_stage(run: RunState) -> str:
    finals_ready = all(
        artifact_exists(run, key)
        for key in ("mon1_final", "mon2_final", "mon3_final", "mon4_final")
    )
    heygen_ready = artifact_exists(run, "heygen_handoff")
    draft_dir = OUTPUT_DIR / run.run_id / "monologues" / "draft"
    drafts_ready = draft_dir.exists() and any(draft_dir.iterdir())
    if heygen_ready and finals_ready:
        return "heygen_ready"
    if finals_ready:
        return "final_ready"
    if drafts_ready:
        return "draft_ready"
    return "not_started"


def compute_step_states(status: str) -> list[str]:
    current_index = STATUS_TO_STEP.get(status, -1)
    states: list[str] = []
    for idx, _ in enumerate(PIPELINE_STEPS):
        if idx < current_index:
            states.append("done")
        elif idx == current_index:
            states.append("current")
        else:
            states.append("pending")
    return states


def compute_progress(status: str) -> float:
    current_index = STATUS_TO_STEP.get(status, 0)
    if not PIPELINE_STEPS:
        return 0.0
    return min(1.0, max(0.0, (current_index + 1) / len(PIPELINE_STEPS)))


def detect_agent_state(run: RunState, agent_name: str) -> str:
    status = run.status
    step_lookup = {
        "MS": 0,
        "ADNA": 1,
        "NB": 2,
        "Paintings": 3,
        "PD": 4,
        "Wine": 5,
        "Spotify": 6,
        "Avatar": 7,
        "HeyGen prompts": 8,
        "YouTube package": 9,
    }
    current_step = STATUS_TO_STEP.get(status, 0)
    agent_step = step_lookup[agent_name]
    avatar_state = avatar_stage(run)
    if agent_name == "Paintings":
        files_ready = len(image_input_files(run)) >= 3
        if status == "awaiting_paintings" and files_ready:
            return "ready_for_trigger"
    if agent_name == "Spotify" and status in {"awaiting_cover_selection", "awaiting_spotify_cover_selection", "cover_selected"}:
        return "current" if status in {"awaiting_cover_selection", "awaiting_spotify_cover_selection"} else "done"
    if agent_name == "Avatar":
        if avatar_state in {"final_ready", "heygen_ready"}:
            return "done"
        if avatar_state == "draft_ready":
            return "current"
        if current_step > agent_step:
            return "done"
        return "pending"
    if agent_name == "HeyGen prompts":
        if avatar_state == "heygen_ready" and status == "heygen_prompt_ready_not_sent":
            return "waiting_human"
        if avatar_state == "heygen_ready":
            return "done"
        if current_step > agent_step:
            return "done"
        return "pending"
    if agent_step < current_step:
        return "done"
    if agent_step == current_step:
        return "current"
    return "pending"


def run_start_command(mode: str, artist_name: str) -> tuple[bool, str]:
    cmd = [sys.executable, str(START_SCRIPT)]
    if mode == "test":
        cmd.append("--test")
    else:
        cmd.append("--release")
    cmd.append(artist_name)
    completed = subprocess.run(cmd, capture_output=True, text=True, cwd=str(BASE_DIR))
    output = completed.stdout.strip()
    error = completed.stderr.strip()
    if completed.returncode == 0:
        return True, output or "Run created."
    return False, error or output or "Unknown error"


def run_continue_command(run_slug: str, event: str) -> tuple[bool, str]:
    cmd = [sys.executable, str(CONTINUE_SCRIPT), "--run-slug", run_slug, "--event", event]
    completed = subprocess.run(cmd, capture_output=True, text=True, cwd=str(BASE_DIR))
    output = completed.stdout.strip()
    error = completed.stderr.strip()
    if completed.returncode == 0:
        return True, output or "Continuation completed."
    return False, error or output or "Unknown error"


def render_pipeline(run: RunState) -> None:
    st.subheader("Pipeline")
    st.progress(compute_progress(run.status), text=f"Current status: {run.status}")
    states = compute_step_states(run.status)
    columns = st.columns(5)
    for idx, step in enumerate(PIPELINE_STEPS):
        with columns[idx % 5]:
            state = states[idx]
            if state == "done":
                st.success(f"{step} ✅")
            elif state == "current":
                st.warning(f"{step} ⏳")
            else:
                st.info(f"{step} ⚪")


def render_agent_board(run: RunState) -> None:
    st.subheader("Agent Board")
    cols = st.columns(5)
    for idx, agent_name in enumerate(AGENT_GROUPS):
        state = detect_agent_state(run, agent_name)
        with cols[idx % 5]:
            if state == "done":
                st.success(f"{agent_name}\nDONE")
            elif state == "current":
                st.warning(f"{agent_name}\nIN PROGRESS / WAIT")
            elif state == "ready_for_trigger":
                st.warning(f"{agent_name}\nREADY FOR HUMAN LOOP")
            elif state == "waiting_human":
                st.warning(f"{agent_name}\nWAITING APPROVAL")
            else:
                st.info(f"{agent_name}\nPENDING")


def render_pause_box(run: RunState) -> None:
    status = run.status
    if status == "awaiting_paintings":
        st.error("Пауза: нужны 3 картины в input-папке этого run.")
        expected = expected_inputs(run)
        if expected:
            st.markdown("Ожидаемые файлы:")
            for path in expected:
                st.write(f"- `{path}`")
        present = image_input_files(run)
        if present:
            st.markdown("Найденные image-файлы:")
            for path in present:
                st.write(f"- `{path}`")
    elif status in {"awaiting_spotify_cover_selection", "awaiting_cover_selection"}:
        st.warning("Пауза: нужен выбор финальной Spotify cover.")
    elif status == "heygen_prompt_ready_not_sent":
        st.warning("Пауза: HeyGen prompts готовы, генерация ещё не запущена.")
    elif status == "youtube_package_ready":
        st.success("Тестовый финал достигнут: YouTube package готов. Рендер в test-режиме пропускается.")
    else:
        next_step = run.data.get("next_step")
        if next_step:
            st.info(next_step)


def render_human_loop_controls(run: RunState) -> None:
    st.subheader("Human Loop")
    status = run.status
    if status == "awaiting_paintings":
        ready = len(image_input_files(run)) >= 3
        if ready:
            st.success("Картины на месте. Триггер готов.")
        else:
            st.warning("Ждём 3 картины в канонических именах.")
        if st.button("Paintings are placed", disabled=not ready, use_container_width=True):
            renamed = canonicalize_painting_inputs(run)
            data = dict(run.data)
            human = dict(data.get("human_loop", {}))
            human["paintings_placed_at"] = now_iso()
            human["paintings_triggered_in_web"] = True
            human["canonicalized_inputs"] = [str(path) for path in renamed]
            data["human_loop"] = human
            data["expected_inputs"] = [str(path) for path in renamed]
            data["updated_at"] = now_iso()
            data["last_human_trigger"] = "paintings_placed"
            save_manifest(run, data)
            ok, message = run_continue_command(run.run_id, "paintings_placed")
            if ok:
                st.success("Картины приведены к каноническим именам. Продолжение пайплайна запущено.")
                st.code(message)
                st.rerun()
            st.error(message)
    elif status in {"awaiting_spotify_cover_selection", "awaiting_cover_selection"}:
        options = run.data.get("spotify_cover_options", [])
        contact_sheet = run.data.get("spotify_cover_contact_sheet", "")
        if contact_sheet:
            st.image(contact_sheet, caption="Spotify cover contact sheet", use_container_width=True)
        if options:
            cols = st.columns(len(options))
            for idx, option in enumerate(options, start=1):
                with cols[idx - 1]:
                    st.image(option, caption=f"Option {idx}", use_container_width=True)
                    if st.button(f"Select cover {idx}", key=f"cover_{idx}", use_container_width=True):
                        playlist_id = run.data.get("spotify_playlist_id", "") or ""
                        cmd = [
                            sys.executable,
                            str(SCRIPTS_DIR / "select_spotify_cover.py"),
                            "--episode-slug",
                            run.run_id,
                            "--episode-id",
                            run.data.get("episode_id", run.run_id),
                            "--option",
                            str(idx),
                        ]
                        if playlist_id:
                            cmd.extend(["--playlist-id", playlist_id])
                        completed = subprocess.run(cmd, capture_output=True, text=True, cwd=str(BASE_DIR))
                        if completed.returncode != 0:
                            st.error(completed.stderr.strip() or completed.stdout.strip() or "Cover selection failed.")
                        else:
                            ok, message = run_continue_command(run.run_id, "cover_selected")
                            if ok:
                                st.success("Cover selected. Continuation into Avatar started.")
                                if message:
                                    st.code(message)
                                st.rerun()
                            else:
                                st.error(message)
        else:
            st.warning("Cover options are not registered in the manifest yet.")
    elif status == "heygen_prompt_ready_not_sent":
        st.success("Финальные монологи и HeyGen prompts готовы.")
        if st.button("Monologues are placed", use_container_width=True):
            data = dict(run.data)
            human = dict(data.get("human_loop", {}))
            human["monologues_approved_at"] = now_iso()
            human["monologues_triggered_in_web"] = True
            data["human_loop"] = human
            data["updated_at"] = now_iso()
            data["last_human_trigger"] = "monologues_approved"
            save_manifest(run, data)
            ok, message = run_continue_command(run.run_id, "monologues_approved")
            if ok:
                st.success("Monologue approval принят. YouTube package собирается / собран.")
                st.code(message)
                st.rerun()
            st.error(message)
    else:
        st.caption("На текущем шаге ручного триггера нет.")


def render_artifacts(run: RunState) -> None:
    st.subheader("Артефакты")
    rows = artifact_rows(run)
    if not rows:
        st.caption("Пока нет зарегистрированных артефактов.")
        return
    for key, value, exists in rows:
        marker = "✅" if exists else "⚪"
        st.write(f"{marker} `{key}`")
        st.code(value, language="text")
        if exists and value.endswith(".txt"):
            text = read_text_if_exists(value)
            if text:
                with st.expander(f"Показать {key}"):
                    st.text(text[:8000])


def render_input_status(run: RunState) -> None:
    st.subheader("Input")
    files = existing_input_files(run)
    if not files:
        st.caption("В input-папке пока нет файлов.")
        return
    for path in files:
        st.write(f"- `{path}`")


def render_redirects(run: RunState) -> None:
    redirects = run.data.get("redirects", {})
    if not redirects:
        return
    st.subheader("Redirects")
    for key, url in redirects.items():
        st.markdown(f"- `{key}`: [{url}]({url})")


st.set_page_config(page_title="Canvas & Glass Studio", page_icon="🎨", layout="wide")
st.title("Canvas & Glass Studio")
st.caption("Episode monitor for the current CanvasGlassNew pipeline.")

with st.sidebar:
    st.header("Новый run")
    mode = st.radio("Режим", ["test", "start"], horizontal=True)
    artist_name = st.text_input("Artist Name", value="")
    if st.button("Создать run", use_container_width=True):
        clean_name = artist_name.strip()
        if not clean_name:
            st.error("Нужно имя художника.")
        elif not START_SCRIPT.exists():
            st.error(f"Не найден script: {START_SCRIPT}")
        else:
            ok, message = run_start_command(mode, clean_name)
            if ok:
                st.success(message)
                st.rerun()
            else:
                st.error(message)

    st.divider()
    st.caption(f"BASE_DIR: {BASE_DIR}")


manifests = list_manifests()

if not manifests:
    st.warning("Пока нет ни одного run manifest. Создай новый `test` или `start` слева.")
    st.stop()

run_options = {f"{run.run_id} · {run.artist_name} · {run.status}": run for run in manifests}
selected_label = st.selectbox("Выбери run", list(run_options.keys()))
selected_run = run_options[selected_label]

status_col, meta_col = st.columns([1, 1])
with status_col:
    st.subheader("Статус")
    st.write(f"**Run:** `{selected_run.run_id}`")
    st.write(f"**Artist:** {selected_run.artist_name}")
    st.write(f"**Run type:** `{selected_run.data.get('run_type', 'unknown')}`")
    st.write(f"**Current status:** `{selected_run.status}`")

with meta_col:
    st.subheader("Метаданные")
    st.write(f"**Created:** {selected_run.created_at}")
    st.write(f"**Input dir:** `{selected_run.data.get('input_dir', '')}`")
    st.write(f"**Output dir:** `{selected_run.data.get('output_dir', '')}`")

render_pipeline(selected_run)
render_agent_board(selected_run)
st.divider()

left, right = st.columns([2, 1])
with left:
    render_pause_box(selected_run)
    render_human_loop_controls(selected_run)
    render_artifacts(selected_run)
with right:
    render_input_status(selected_run)
    render_redirects(selected_run)

st.divider()
with st.expander("Manifest JSON"):
    st.json(selected_run.data)
