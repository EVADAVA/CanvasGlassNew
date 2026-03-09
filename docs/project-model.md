# CanvasGlassNew Project Model

## Core Goal

`Script` produces one 60-minute YouTube episode per artist.

Each episode:
- uses one `AN` (`artist_name`)
- contains 3 visual sessions of 20 minutes each
- includes 4 monologues
- uses gallery ASMR ambience as the audio bed
- recommends music through Spotify instead of embedding music into the render

## Main Unit

### Episode

One `Episode` equals one `Artist Name`.

The artist is selected from Google Sheet registry logic in sequence to avoid repeats.

## Naming

- `artist_name`: human-readable artist name from registry
- `artist_slug`: filesystem-safe folder name derived from `artist_name`

Example:

- `artist_name = Vincent van Gogh`
- `artist_slug = vincent-van-gogh`

All filesystem paths must use `artist_slug`, not raw `artist_name`.

## High-Level Flow

1. Telegram triggers `Script`.
2. `Script` reads Google Sheet registry and picks the next artist.
3. `Script` creates episode workspace for that artist.
4. `ADNA Agent` generates `ADNA-text` and 6 biography facts.
5. `NB Agent` generates 3 Nano Banana prompts.
6. `Script` pauses and waits for 3 paintings in the artist input folder.
7. `Painting Describer Agent` generates `PD-text-1..3`.
8. `Wine Agent` generates 3 wine recommendations.
9. `Music Agent` creates Spotify playlist, 3 cover options, playlist URL, and playlist QR.
10. `Avatar Agent` generates 4 monologues.
11. `Publisher Agent` prepares the YouTube publication package.
12. `Script` asks for confirmation before render.
13. `Script` renders the final 60-minute video.
14. `Script` publishes the video to YouTube private state.

## Agents

### ADNA Agent

- input: `artist_name`
- output: `adna_text`, `adna_fact_1..6`

### NB Agent

- input: `adna_text`
- output: `nb_prompt_1..3`

### Painting Describer Agent

- input: `painting_1..3`
- output: `pd_text_1..3`

### Wine Agent

- input: `pd_text_1..3`
- output: 3 wine recommendations
- rule: if red wine is recommended, also recommend a wide-bowl glass and decanter

### Music Agent

- input: `pd_text_1..3`
- output: Spotify playlist, 3 cover options, playlist URL, playlist QR

### Avatar Agent

- input: project variables
- output: `monologue_1..4`

### Publisher Agent

- input: project variables and content assets
- output: `TYDescription.txt` and YouTube publication package

## Modules

- `Commercial`
- `Affiliates`
- `Publisher Module`
- `SMM`
- `Communication Layer`

## Render Composition

The final video is built from:

- `monologue_1` + `painting_1` + Spotify playlist QR + painting/shop QR
- `monologue_2` + `painting_2` + painting/shop QR
- `monologue_3` + `painting_3` + painting/shop QR
- `monologue_4` as the closing block
- gallery ASMR ambience under the full 60-minute video

Spotify is recommendation output only. It is not used as render audio.

## Entity Variables

### Artist

- `artist_name`
- `artist_slug`
- `artist_sheet_row_id`

### Episode

- `episode_id`
- `artist_name`
- `artist_slug`
- `episode_status`
- `input_dir`
- `output_dir`
- `created_at`
- `updated_at`
- `sheet_registry_ref`

### ADNA Knowledge

- `adna_text`
- `adna_fact_1`
- `adna_fact_2`
- `adna_fact_3`
- `adna_fact_4`
- `adna_fact_5`
- `adna_fact_6`

### NB Prompt Set

- `nb_prompt_1`
- `nb_prompt_2`
- `nb_prompt_3`

### Paintings

- `painting_1_path`
- `painting_2_path`
- `painting_3_path`
- `painting_1_store_url`
- `painting_2_store_url`
- `painting_3_store_url`
- `painting_1_qr_path`
- `painting_2_qr_path`
- `painting_3_qr_path`
- `pd_text_1`
- `pd_text_2`
- `pd_text_3`

### Wine Recommendations

- `wine_1_name`
- `wine_1_type`
- `wine_1_rationale`
- `wine_1_glass`
- `wine_1_decanter`
- `wine_2_name`
- `wine_2_type`
- `wine_2_rationale`
- `wine_2_glass`
- `wine_2_decanter`
- `wine_3_name`
- `wine_3_type`
- `wine_3_rationale`
- `wine_3_glass`
- `wine_3_decanter`

### Playlist

- `spotify_playlist_id`
- `spotify_playlist_name`
- `spotify_playlist_url`
- `spotify_track_list`
- `spotify_cover_option_1`
- `spotify_cover_option_2`
- `spotify_cover_option_3`
- `spotify_selected_cover`
- `spotify_playlist_qr_path`

### Monologues

- `monologue_1_text`
- `monologue_2_text`
- `monologue_3_text`
- `monologue_4_text`

### YouTube Package

- `youtube_title`
- `youtube_description`
- `youtube_timestamps`
- `youtube_links_block`
- `youtube_seo_keywords`
- `youtube_tags`
- `youtube_description_file_path`

### Render

- `asmr_audio_path`
- `render_status`
- `render_output_path`
- `video_duration_seconds`

## Variable Classes

### Input Variables

These enter the system from outside or from fixed project settings.

- `artist_name`
- `artist_slug`
- `artist_sheet_row_id`
- `episode_id`
- `sheet_registry_ref`
- `painting_1_path`
- `painting_2_path`
- `painting_3_path`
- `painting_1_store_url`
- `painting_2_store_url`
- `painting_3_store_url`
- `asmr_audio_path`

### Derived Variables

These are produced by agents or Script logic.

- `adna_text`
- `adna_fact_1..6`
- `nb_prompt_1..3`
- `pd_text_1..3`
- `wine_1_*`
- `wine_2_*`
- `wine_3_*`
- `spotify_playlist_id`
- `spotify_playlist_name`
- `spotify_playlist_url`
- `spotify_track_list`
- `spotify_cover_option_1..3`
- `spotify_playlist_qr_path`
- `painting_1_qr_path`
- `painting_2_qr_path`
- `painting_3_qr_path`
- `monologue_1_text..4`
- `youtube_title`
- `youtube_description`
- `youtube_timestamps`
- `youtube_links_block`
- `youtube_seo_keywords`
- `youtube_tags`
- `youtube_description_file_path`
- `render_output_path`

### User-Approved Variables

These require explicit human confirmation or selection.

- `spotify_selected_cover`
- `render_confirmation`
- `publish_confirmation`

## Native Pause Points

### Pause 1: waiting for paintings

`Script` must pause after generating prompts and wait for user-supplied paintings in the artist input folder.

### Pause 2: cover selection

`Script` must present the 3 playlist cover options and wait for the user to select one.

### Pause 3: render confirmation

`Script` must not render until the user confirms.

### Pause 4: publish confirmation

`Script` must not publish until the user confirms.

## Current Unknowns

These are not resolved yet and should be specified before implementation:

- exact Google Sheet tab structure
- exact folder layout under each artist episode
- exact role and output format of the 4 monologues
- final YouTube metadata template
- final responsibilities of `Commercial`, `Affiliates`, `Publisher Module`, and `SMM`
