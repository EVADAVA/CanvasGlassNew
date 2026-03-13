Canvas & Glass New Bible

Last updated: 2026-03-12

Purpose

This file is the working source of truth for the current CanvasGlassNew system design.
It summarizes the agent architecture, orchestration flow, Google Sheet logic, music and wine decision layers, and the currently approved implementation direction.

Terms

- `SP` = System Prompt
- `OSR` = Overlay System Rules
- `MS` = Main Script
- `WAO` = Wine Agent Orchestration
- `MAO` = Music Agent Orchestration

Core Project Goal

`MS` produces one long-form Canvas & Glass episode per artist.

Episode structure:
- 1 artist per episode
- 3 paintings
- 3 viewing sessions
- 4 monologues
- wine pairing layer
- Spotify playlist layer
- final rendered video

Primary Product Goal

The system must maximize video retention.

This affects:
- monologue pacing
- music pacing
- QR timing
- visual continuity
- anti-repetition logic

Runtime modes

- `test [Artist Name]`
  - creates a test run
  - does not consume a production episode number
  - target finish is `youtube_package_ready`
  - render is skipped in test mode
- `start [Artist Name]`
  - creates a release run
  - consumes the next production episode number
  - continues past the YouTube package into render and publish layers

Pipeline Order

Canonical order for one episode:
1. `MS start`
2. `ADNA Agent`
3. `NB Agent`
4. user generates or places 3 paintings
5. `PD Agent`
6. `Wine Agent`
7. `Music / Playlist Agent`
8. `Avatar Agent`
9. stop before `HeyGen execution`
10. `HeyGen` execution only after template readiness
11. `Painting QR Agent`
12. `Publisher Agent`
13. in `test` mode stop at `youtube_package_ready`
14. in `start` mode continue to `Render Maker Agent`
15. publish
16. mark artist `used`

Operational rule:
- do not skip forward if the previous layer has not produced its canonical output artifacts
- for the current episode, the stop point before HeyGen is intentional
- monologue filename state is canonical:
- `*_draft.txt` = not final, not allowed into HeyGen prompts
- `*_final.txt` = final Avatar output, allowed into HeyGen prompts
- final monologue filenames must include the selected `narrative_pattern_name` slug so the correct avatar/template choice in HeyGen is obvious from the filename alone
- `*_draft_vs_final.diff` = visible content delta between local draft assembly and API-finalized monologue
- HeyGen prompt submission is manual, not automatic API generation, until further notice

Skeleton reference:
- [PIPELINE_SKELETON.md](/Users/akg/EVADAVA/CanvasGlassNew/PIPELINE_SKELETON.md)

Agent Map

Canonical agents currently in scope:
- `ADNA Agent`
- `NB Agent`
- `Painting Describer Agent`
- `Wine Agent`
- `Music Agent`
- `Random Agent`
- `Avatar Agent`
- `Publisher Agent`
- `Render Maker Agent`

NB Layer

`NB Agent` is the prompt-engineering layer for Nano Banana.

Canonical definition:
- input: `Artist DNA` from `ADNA Agent`
- output: `3 prompts` for `Nano Banana Pro / NB2`
- each prompt receives a painting title before image generation
- NB prompt filenames must include `Painting1/2/3` before the title slug
- painting titles may and should draw from `ADNA`, including how the reference artist might plausibly have named or held such an image, without copying known artwork titles
- rules source:
  - [docs/final-nb-prompt-agent.txt](/Users/akg/EVADAVA/CanvasGlassNew/docs/final-nb-prompt-agent.txt)
  - [docs/final-nb-agent-osr.txt](/Users/akg/EVADAVA/CanvasGlassNew/docs/final-nb-agent-osr.txt)
  - [docs/nb-engineering-prompt-agent.txt](/Users/akg/EVADAVA/CanvasGlassNew/docs/nb-engineering-prompt-agent.txt)

Interpretation rule:
- there is not a separate downstream `NB Prompt Engineering Agent`
- `NB Agent` itself performs the prompt-engineering step and applies its `OSR`

Main Script start rule:
- `start [Artist Name]` must create or normalize the requested artist inside `ARTIST_POOL`
- `start` must not fail only because the artist is missing from the pool
- `test [Artist Name]` = test run, folder slug `test_<artist_slug>`, no numbered release slot consumed
- `start [Artist Name]` = release run, folder slug `episodeNNN_<artist_slug>`

Current prompt/spec files:
- [docs/adna-agent-perplexity-system-prompt.txt](/Users/akg/EVADAVA/CanvasGlassNew/docs/adna-agent-perplexity-system-prompt.txt)
- [docs/final-nb-prompt-agent.txt](/Users/akg/EVADAVA/CanvasGlassNew/docs/final-nb-prompt-agent.txt)
- [docs/final-pd-agent.txt](/Users/akg/EVADAVA/CanvasGlassNew/docs/final-pd-agent.txt)
- [docs/final-random-agent.txt](/Users/akg/EVADAVA/CanvasGlassNew/docs/final-random-agent.txt)
- [docs/final-avatar-agent.txt](/Users/akg/EVADAVA/CanvasGlassNew/docs/final-avatar-agent.txt)
- [docs/final-master-monologue-prompt.txt](/Users/akg/EVADAVA/CanvasGlassNew/docs/final-master-monologue-prompt.txt)
- [docs/final-render-maker-agent.txt](/Users/akg/EVADAVA/CanvasGlassNew/docs/final-render-maker-agent.txt)
- [docs/final-wine-agent.txt](/Users/akg/EVADAVA/CanvasGlassNew/docs/final-wine-agent.txt)
- [docs/final-wine-agent-orchestration-prompt.txt](/Users/akg/EVADAVA/CanvasGlassNew/docs/final-wine-agent-orchestration-prompt.txt)
- [docs/final-wine-agent-orchestration-osr.txt](/Users/akg/EVADAVA/CanvasGlassNew/docs/final-wine-agent-orchestration-osr.txt)
- [docs/final-music-agent.txt](/Users/akg/EVADAVA/CanvasGlassNew/docs/final-music-agent.txt)
- [docs/final-music-agent-orchestration-prompt.txt](/Users/akg/EVADAVA/CanvasGlassNew/docs/final-music-agent-orchestration-prompt.txt)
- [docs/final-music-agent-orchestration-osr.txt](/Users/akg/EVADAVA/CanvasGlassNew/docs/final-music-agent-orchestration-osr.txt)
- [docs/final-painting-qr-agent-prompt.txt](/Users/akg/EVADAVA/CanvasGlassNew/docs/final-painting-qr-agent-prompt.txt)
- [docs/final-painting-qr-agent-osr.txt](/Users/akg/EVADAVA/CanvasGlassNew/docs/final-painting-qr-agent-osr.txt)
- [docs/final-publisher-agent.txt](/Users/akg/EVADAVA/CanvasGlassNew/docs/final-publisher-agent.txt)

Monologue Layer

Current monologue source:
- [docs/final-avatar-agent.txt](/Users/akg/EVADAVA/CanvasGlassNew/docs/final-avatar-agent.txt)

Current state:
- `MON1` updated from external draft
- `MON2` updated from external draft
- `MON3` still structurally incomplete
- `MON4` has rules but no full fixed template block

Meditation flow canon:
- episode length = `60 minutes`
- `MON1` = `[00:00]` threshold / hook / breathing entry / painting 1 / wine bouquet / Spotify call
- `MON2` = `[20:00]` reset / painting 2 / exactly 2 ADNA sensory facts / response logic
- `MON3` = `[40:00]` philosophical catharsis / philosophical anchor / wine aftertaste evolution
- `MON4` = `[60:00]` return / gratitude / back-to-reality bridge / QR prints-or-originals CTA
- target length per monologue = `up to 500 words`

Current narrative-pattern source:
- [docs/final-avatar-narrative-patterns.txt](/Users/akg/EVADAVA/CanvasGlassNew/docs/final-avatar-narrative-patterns.txt)

Canonical narrative patterns:
- `THE SENSUALIST PHILOSOPHER`
- `THE ALCHEMIST CURATOR`
- `THE DOUBLE AGENT`
- `THE LITURGIST`
- `THE WITNESS OF TRANSFORMATION`

PD Layer

Current PD prompt:
- [docs/final-pd-agent.txt](/Users/akg/EVADAVA/CanvasGlassNew/docs/final-pd-agent.txt)

PD output is a structured operational description, not criticism.
It is designed for:
- wine pairing
- music curation
- monologue writing
- sales page copy

Wine Layer

Current wine prompt files:
- [docs/final-wine-agent.txt](/Users/akg/EVADAVA/CanvasGlassNew/docs/final-wine-agent.txt)
- [docs/final-wine-agent-orchestration-prompt.txt](/Users/akg/EVADAVA/CanvasGlassNew/docs/final-wine-agent-orchestration-prompt.txt)
- [docs/final-wine-agent-orchestration-osr.txt](/Users/akg/EVADAVA/CanvasGlassNew/docs/final-wine-agent-orchestration-osr.txt)

Wine architecture

`MS`
- receives:
  - `episode_AN_PD_text1`
  - `episode_AN_PD_text2`
  - `episode_AN_PD_text3`

`MS -> WAO`
- passes the 3 PD texts into `WAO`

`WAO`
- runs the Wine Agent `SP` separately for each PD text
- checks Google Sheet `Wine Registry`
- reads repeat-control variables from `SETTINGS`
- enforces anti-repeat logic
- re-runs a wine slot if repeat threshold is violated

Wine output

Approved output to `MS`:
- `wine1`
- `wine1_description`
- `wine2`
- `wine2_description`
- `wine3`
- `wine3_description`

Each wine description:
- exactly 2 sentences

Wine Registry logic

Google Sheet tab:
- `Wine Registry`

Current episode-level row model:
- `Episode`
- `Artist Name`
- `Wine1`
- `Wine2`
- `Wine3`
- `Wine1_Description`
- `Wine2_Description`
- `Wine3_Description`
- `Wine1_Type`
- `Wine2_Type`
- `Wine3_Type`
- `Wine1_Region`
- `Wine2_Region`
- `Wine3_Region`
- `Wine1_Producer`
- `Wine2_Producer`
- `Wine3_Producer`
- `Wine1_Normalized_Key`
- `Wine2_Normalized_Key`
- `Wine3_Normalized_Key`
- `Recorded_At`

Wine repeat settings

Google Sheet tab:
- `SETTINGS`

Keys:
- `wine_repeat_kr`
- `wine_repeat_history_depth`

Meaning:
- `wine_repeat_kr` = allowed repeat share
- `wine_repeat_history_depth` = how many previous episodes are checked

Music Layer

Current music prompt files:
- [docs/final-music-agent.txt](/Users/akg/EVADAVA/CanvasGlassNew/docs/final-music-agent.txt)
- [docs/final-music-agent-orchestration-prompt.txt](/Users/akg/EVADAVA/CanvasGlassNew/docs/final-music-agent-orchestration-prompt.txt)
- [docs/final-music-agent-orchestration-osr.txt](/Users/akg/EVADAVA/CanvasGlassNew/docs/final-music-agent-orchestration-osr.txt)

Music architecture

`Music Agent SP` is now explicitly the Search Layer.

Search Layer:
- input:
  - `pd_text_1`
  - `pd_text_2`
  - `pd_text_3`
  - target playlist duration
- search/reasoning base:
  - `Perplexity API`
- function:
  - derive seed artists
  - derive genre vector
  - derive session feature targets
  - propose candidate track list

Execution Layer:
- `Spotify API`
- creates playlist
- adds tracks
- later uploads final cover

Orchestration Layer:
- `MAO`

`MAO` responsibilities:
- run Music Search Layer
- pass structured brief into Spotify execution layer
- check repeat history
- read repeat settings from `SETTINGS`
- enforce duration fit
- generate 3 Spotify cover variants
- show the 3 covers to the user
- wait for explicit user cover choice
- create playlist before QR finalization
- defer final QR until YouTube private URL exists

Music node flow

Canonical flow:
1. `PD Agent -> MS`
2. `MS -> MAO`
3. `MAO -> Perplexity API search layer`
4. `Perplexity API search layer -> MAO`
5. `MAO -> Spotify API execution layer`
6. `Spotify API execution layer -> MAO`
7. `MAO -> Google Sheet / Sheet Spotify`
8. `MAO -> cover generation step`
9. `cover generation step -> MAO`
10. `MAO -> user`
11. `user -> MAO`
12. `MAO -> links.evadava.com redirect target`
13. `MAO -> QR generation step`
14. `QR generation step -> MAO`
15. `MAO -> MS`

Music retention doctrine

Music is not just “matching”.
Music must actively support retention.

Retention rules currently accepted:
- no dead-air opening
- no harsh early disruption
- no static mid-playlist collapse unless the visual arc strongly supports it
- no sonically exhausting climax before the last session
- no abrupt emotional drop at the end
- continuity is more important than cleverness
- fit is more important than prestige

Music OMR integrated into current direction

Source file used:
- `/Users/akg/Downloads/agents_04_music_omr_rules.txt`

Integrated rules:
- instrumental only
- track duration windows
- exclusion keywords
- BPM arc by session
- global BPM floor and ceiling
- adjacent BPM and energy smoothing
- audio-feature targets by session
- crossfade awareness
- genre palette and quotas
- repeat prevention
- structured brief before Spotify API execution

Current accepted music search constraints

Instrumental rule:
- `instrumentalness_min = 0.85`

Track duration:
- min `150000 ms`
- max `300000 ms`
- sweet spot `180000-270000 ms`

BPM arc:
- session 1: `80-95`
- session 2: `95-112`
- session 3: `100-118`
- `MON1 / MON4` framing zone: `80-90`
- global floor: `72`
- global ceiling: `128`

Transition smoothing:
- adjacent BPM delta max `15`
- adjacent energy delta max `0.2`

Audio features:
- loudness `-18 to -8 dB`
- prefer major mode for higher valence

Genre quotas:
- `Contemporary Jazz / ECM` max `30%`
- `Neo-Classical / Modern Classical` max `30%`
- `Ambient / Drone` max `25%`
- `Post-Rock Instrumental` max `15%`
- `Electronic / Minimal Ambient` max `20%`
- `World / Ethnic Instrumental` max `15%`
- `Acoustic / Folk Instrumental` max `15%`

Episode genre rule:
- minimum 2 genres per playlist
- no single genre above 60 percent of one playlist

Music repeat settings

Google Sheet tab:
- `SETTINGS`

Keys:
- `track_repeat_kr`
- `track_repeat_history_depth`

Meaning:
- `track_repeat_kr` = allowed repeat share
- `track_repeat_history_depth` = how many previous episodes are checked

Spotify Covers

Cover template source:
- `/Users/akg/Downloads/Create 3 Spotify playlist cover variants from the 3 episode paintings..rtf`

Approved cover logic:
- one fixed master layout
- variables only:
  - background painting
  - artist name
  - QR content URL
- square JPEG covers
- centered square crop from painting
- `3000x3000`
- one dark semi-transparent rounded panel near lower part
- fixed Bebas Neue typography
- fixed logo placement in top-right
- QR inside panel on the right
- fixed text lines must be exactly:
  - `IMMERSIVE WINE`
  - `ART MEDITATION`
  - `BY ALEXANDER KUGUK`
  - `INSPIRED BY THE ART OF`
  - `ARTIST NAME` as the 5th line, uppercase, visually dominant
- do not improvise alternate copy on Spotify covers
- output 3 cover options plus contact sheet preview

Current logo source folder:
- [logos](/Users/akg/EVADAVA/CanvasGlassNew/logos)

Recovered canonical asset mapping:
- original template expected `channel_logo_round_master.jpg`
- current project fallback for that role:
  - [Profile Mono.png](/Users/akg/EVADAVA/CanvasGlassNew/logos/Profile%20Mono.png)

Spotify cover flow

Current approved logic:
- playlist can be created before final cover and final QR
- cover variants are generated from `painting_1`, `painting_2`, `painting_3`
- user chooses one cover
- final cover is uploaded later if needed

QR and Redirect Logic

Playlist QR must point to the episode video, not to the channel.

Problem:
- final YouTube video URL does not exist until publication to private state

Approved solution:
- use `links.evadava.com` as redirect layer
- create playlist first
- reserve redirect target
- after YouTube private URL exists, update redirect
- then generate the final playlist QR
- use that QR in final render flow

Painting QR Layer

Current QR prompt files:
- [docs/final-painting-qr-agent-prompt.txt](/Users/akg/EVADAVA/CanvasGlassNew/docs/final-painting-qr-agent-prompt.txt)
- [docs/final-painting-qr-agent-osr.txt](/Users/akg/EVADAVA/CanvasGlassNew/docs/final-painting-qr-agent-osr.txt)

Painting QR logic:
- generate `painting_1_qr_path`
- generate `painting_2_qr_path`
- generate `painting_3_qr_path`
- each QR maps to one painting-specific destination
- QR assets must exist before final render approval

Publisher Layer

Current publisher prompt file:
- [docs/final-publisher-agent.txt](/Users/akg/EVADAVA/CanvasGlassNew/docs/final-publisher-agent.txt)

Publisher normalization direction:
- final YouTube description must be variable-complete
- no unresolved placeholders
- normalized canonical variables must be used for:
  - playlist URL
  - painting store URLs
  - timing blocks
  - links block

Google Sheet Model

Canonical tabs currently in scope:
- `ARTIST_POOL`
- `EPISODES`
- `Tracks`
- `WINE_REGISTRY`
- `AVATAR`
- `AVATAR_REGISTRY`
- `REDIRECT_REGISTRY`
- `SETTINGS`

Important settings keys currently in scope:
- `duration_1_min`
- `duration_2_min`
- `duration_3_min`
- `episode_id_padding`
- `artist_pool_select_value`
- `artist_pool_used_value`
- `wine_repeat_kr`
- `wine_repeat_history_depth`
- `track_repeat_kr`
- `track_repeat_history_depth`
- `avatar_repeat_kr`
- `avatar_repeat_history_depth`
- `spotify_cover_count`
- `redirect_public_domain`
- `video_redirect_base_path`
- `painting_redirect_base_path`
- `playlist_redirect_base_path`
- `redirect_slug_pattern`
- `heygen_avatar_selection_mode`

Current Google Sheet status

Current production spreadsheet:
- title: `CanvasGlass`
- id: stored in the current schema-sync script
- service account access confirmed

Current live tabs found before schema sync:
- `Tracks`
- `ARTIST_POOL`
- `EPISODES`
- `SETTINGS`
- `WINE_REGISTRY`
- `GLASS_REGISTRY`
- `DECANTER_REGISTRY`

Required schema upgrades now approved:
- `ARTIST_POOL` gains canonical selection fields:
  - `artist_name`
  - `artist_slug`
  - `status`
  - `used`
  - `episode_id`
  - `selected_at`
  - `used_at`
- `EPISODES` gains current episode orchestration fields:
  - `input_dir`
  - `output_dir`
  - `playlist_name`
  - `spotify_playlist_url`
  - `playlist_redirect_url`
  - `video_redirect_url`
  - `painting1_redirect_url`
  - `painting2_redirect_url`
  - `painting3_redirect_url`
  - `video_description_path`
- `AVATAR` stores episode-level pattern/tone/avatar decisions
- `AVATAR_REGISTRY` stores reusable HeyGen avatar ids mapped to `narrative_pattern_id`
- `REDIRECT_REGISTRY` stores reserved public URLs for video and painting QR flows

Artist Pool logic

Canonical flow:
1. `MS` reads `ARTIST_POOL`
2. `MS test [Artist Name]` creates `test_<artist_slug>` and does not consume a numbered release slot
3. `MS start [Artist Name]` creates `episodeNNN_<artist_slug>` and does consume the next numbered release slot
4. `MS` writes artist `status = selected`
5. `MS` passes `AN` into `ADNA Agent`
6. after publish, `status = used`

Approved status values:
- `selected`
- `used`

Avatar selection logic

Approved model:
- `Random Agent` selects `narrative_pattern_id`
- `AAO` reads `AVATAR_REGISTRY`
- `AVATAR_REGISTRY` maps `narrative_pattern_id -> avatar_id`
- the chosen avatar remains fixed for the full episode across `MON1..MON4`

Redirect structure

Current approved canonical public redirect domain:
- [https://evadava.com](https://evadava.com)

Current approved redirect patterns:
- episode video redirect:
  - [https://evadava.com/test_artist_slug_video/](https://evadava.com/test_artist_slug_video/)
- episode playlist redirect:
  - [https://evadava.com/test_artist_slug_playlist/](https://evadava.com/test_artist_slug_playlist/)
- painting redirects:
  - [https://evadava.com/test_artist_slug_painting1/](https://evadava.com/test_artist_slug_painting1/)
  - [https://evadava.com/test_artist_slug_painting2/](https://evadava.com/test_artist_slug_painting2/)
  - [https://evadava.com/test_artist_slug_painting3/](https://evadava.com/test_artist_slug_painting3/)

These must be stored in:
- `REDIRECT_REGISTRY`

Working sync tool:
- [scripts/sync_google_sheet_schema.py](/Users/akg/EVADAVA/CanvasGlassNew/scripts/sync_google_sheet_schema.py)

Current schema-sync result

Applied to the live production spreadsheet:
- created tab `AVATAR`
- created tab `AVATAR_REGISTRY`
- created tab `REDIRECT_REGISTRY`
- added duration settings:
  - `duration_1_min = 20`
  - `duration_2_min = 20`
  - `duration_3_min = 20`
- added avatar repeat settings:
  - `avatar_repeat_kr = 30`
  - `avatar_repeat_history_depth = 10`
- added redirect settings:
  - `redirect_public_domain = evadava.com`
  - `video_redirect_base_path = /`
  - `painting_redirect_base_path = /`
  - `playlist_redirect_base_path = /`
  - `redirect_slug_pattern = episode{episode_id}_{artist_slug}_{entity_name}`
- no hardcoded artist seeds should exist

Reserved canonical routes in the live sheet should be created dynamically by the active run:
- `https://evadava.com/test_artist_slug_video/`
- `https://evadava.com/test_artist_slug_playlist/`
- `https://evadava.com/test_artist_slug_painting1/`
- `https://evadava.com/test_artist_slug_painting2/`
- `https://evadava.com/test_artist_slug_painting3/`

Deployment note:
- `REDIRECT_REGISTRY` now treats these `evadava.com` URLs as canonical public addresses
- actual root-level redirect activation on [https://evadava.com](https://evadava.com) still needs explicit infra wiring

Folder structure

Approved production filesystem rule:
- input paintings go to:
  - `input/test_artist_slug/` for test runs
  - `input/episodeNNN_artist_slug/` for release runs
- all generated episode outputs go to:
  - `output/test_artist_slug/` for test runs
  - `output/episodeNNN_artist_slug/` for release runs

Approved output subfolders inside one episode folder:
- `adna/`
- `nb/`
- `pd/`
- `wine/`
- `spotify/`
- `monologues/draft/`
- `monologues/final/`
- `monologues/comparison/`
- `heygen/`
- `qr/`
- `publish/`

Approved naming direction:
- `test_artist_slug_ADNA-text.txt`
- `test_artist_slug_NB_Painting1_Title_One.txt`
- `test_artist_slug_PD-text1.txt`
- `test_artist_slug_painting1_wine1.txt`
- `monologues/draft/test_artist_slug_painting1_mon1_draft.txt`
- `monologues/draft/test_artist_slug_mon4_draft.txt`
- `monologues/final/test_artist_slug_the_sensualist_philosopher_painting1_mon1_final.txt`
- `monologues/final/test_artist_slug_the_sensualist_philosopher_mon4_final.txt`
- `test_artist_slug_videodescription.txt`

Spotify Integration Status

Working Spotify stack was found in:
- `/Users/akg/EVADAVA/_CanvasGlass`

Relevant scripts there:
- [spotify_auth.py](/Users/akg/EVADAVA/_CanvasGlass/scripts/spotify_auth.py)
- [search_tracks.py](/Users/akg/EVADAVA/_CanvasGlass/scripts/search_tracks.py)
- [create_playlist.py](/Users/akg/EVADAVA/_CanvasGlass/scripts/create_playlist.py)
- [upload_cover.py](/Users/akg/EVADAVA/_CanvasGlass/scripts/upload_cover.py)
- [generate_spotify_qr.py](/Users/akg/EVADAVA/_CanvasGlass/scripts/generate_spotify_qr.py)

Spotify auth status

Confirmed:
- local Spotify credentials exist
- refresh token exists
- refresh flow works
- Spotify API account check works

Credentials storage in this repo

Local-only files now present:
- [credentials.env](/Users/akg/EVADAVA/CanvasGlassNew/credentials.env)
- [tokens.json](/Users/akg/EVADAVA/CanvasGlassNew/tokens.json)
- [secrets/legacy_canvasglass](/Users/akg/EVADAVA/CanvasGlassNew/secrets/legacy_canvasglass)

These are intentionally gitignored.

Legacy cleanup status

Legacy local CanvasGlass-related copies were removed so that `CanvasGlassNew` is the only local source of truth.

Removed:
- `/Users/akg/EVADAVA/CanvasGlass`
- `/Users/akg/EVADAVA/_CanvasGlass`
- `/Users/akg/EVADAVA/_CanvasGlassClaude`
- `/Users/akg/EVADAVA/Links`
- `/Users/akg/Desktop/trash/CanvasGlass`
- related Canvas & Glass drafts and prompt files from `Downloads`

Preserved from legacy projects:
- Spotify credentials and tokens
- Google Sheets credentials
- YouTube credentials/tokens
- legacy `n8n_api.env`

These were copied into:
- [secrets/legacy_canvasglass](/Users/akg/EVADAVA/CanvasGlassNew/secrets/legacy_canvasglass)

VPS / n8n status

Known VPS host from legacy project:
- `root@178.156.141.58`
- old remote root: `/opt/CanvasGlass`

Known old n8n host:
- `https://n8n.evadava.com`

Current state:
- legacy public API JWT was used to remove old `n8n` workflows
- working SSH access was later recovered via private repo infrastructure
- old remote app root `/opt/CanvasGlass` has now been removed

Remote cleanup result:
- old CanvasGlass workflows on `n8n.evadava.com` were deleted
- workflow list is now empty
- old Docker services `canvasglass_n8n`, `canvasglass_runner`, `canvasglass_caddy` were removed
- old Docker volumes for the VPS stack were removed
- old remote app directory `/opt/CanvasGlass` was removed

Current VPS state:
- remaining app root:
  - `/opt/evadava-infra`
  - `/opt/evadava-site`
- remaining container:
  - `evadava_caddy`
- `n8n.evadava.com` is no longer being served
- `evadava.com` remains live as a minimal static TikTok/legal surface

Verified live URLs after cleanup:
- [https://evadava.com](https://evadava.com)
- [https://evadava.com/privacy](https://evadava.com/privacy)
- [https://evadava.com/terms](https://evadava.com/terms)
- [https://evadava.com/auth/tiktok/callback](https://evadava.com/auth/tiktok/callback)

Links / landing reservation status

The old standalone local `Links` project was removed as part of cleanup.

Reserved painting landing routes were preserved inside this repo:
- [docs/reserved_painting_routes.json](/Users/akg/EVADAVA/CanvasGlassNew/docs/reserved_painting_routes.json)

The replacement local source for `links.evadava.com` now lives here:
- [sites/links](/Users/akg/EVADAVA/CanvasGlassNew/sites/links)
- generated static deploy bundle:
  - [sites/links/dist](/Users/akg/EVADAVA/CanvasGlassNew/sites/links/dist)
- generator script:
  - [scripts/build_links_site.py](/Users/akg/EVADAVA/CanvasGlassNew/scripts/build_links_site.py)

Reservation block:
- `001_1` through `020_3`
- total reserved pages: `60`

Current landing pattern:
- `https://links.evadava.com/paintings/<episode>_<painting>`

Current links-site scaffold:
- static landing home
- static reserved painting route index
- real static page per reserved painting slug
- no runtime dependency on `_redirects`

TikTok / evadava.com status

Current `evadava.com` TikTok/legal surface remains separate from CanvasGlassNew.

Known live source:
- `LEGOLOVER`

Current live URLs:
- [https://evadava.com](https://evadava.com)
- [https://evadava.com/privacy](https://evadava.com/privacy)
- [https://evadava.com/terms](https://evadava.com/terms)
- [https://evadava.com/auth/tiktok/callback](https://evadava.com/auth/tiktok/callback)

Current deployed state:
- Cloudflare Pages project:
  - `canvasglass-hub`
- current working Pages deployment:
  - [https://2b3469bf.canvasglass-hub.pages.dev](https://2b3469bf.canvasglass-hub.pages.dev)
- custom domain:
  - [https://links.evadava.com](https://links.evadava.com)
- verified route examples:
  - [https://links.evadava.com/paintings/001_1/](https://links.evadava.com/paintings/001_1/)
  - [https://links.evadava.com/paintings/010_2/](https://links.evadava.com/paintings/010_2/)
  - [https://links.evadava.com/paintings/020_3/](https://links.evadava.com/paintings/020_3/)

Interpretation:
- `evadava.com` currently carries the TikTok/legal surface
- `links.evadava.com` is restored from `CanvasGlassNew/sites/links`

Domain roles

Current approved domain split:
- [https://evadava.com](https://evadava.com) = company / legal / infrastructure surface
- [https://links.evadava.com](https://links.evadava.com) = QR / redirect / episode / painting landing layer
- [https://kuguk.net](https://kuguk.net) = public-facing SMM / bio-link / social hub domain

`kuguk.net` status:
- DNS moved from Namecheap BasicDNS to Cloudflare
- Wix web routing was intentionally removed
- iCloud mail records were preserved:
  - MX
  - SPF
  - Apple TXT verification
  - DKIM
- current `www` record exists in Cloudflare
- root `@` web target is still intentionally unset until the new SMM hub is built

Local env status

Current local env wiring includes placeholders or local-only values for:
- `PERPLEXITY_API_KEY`
- `SPOTIFY_CLIENT_ID`
- `SPOTIFY_CLIENT_SECRET`
- `SPOTIFY_REDIRECT_URI`

See:
- [`.env.example`](/Users/akg/EVADAVA/CanvasGlassNew/.env.example)

Render State

Current render center:
- [scripts/render_test15_signature.py](/Users/akg/EVADAVA/CanvasGlassNew/scripts/render_test15_signature.py)

Current working reference notes:
- [SESSION_SYNC.md](/Users/akg/EVADAVA/CanvasGlassNew/SESSION_SYNC.md)
- [docs/session-sync.md](/Users/akg/EVADAVA/CanvasGlassNew/docs/session-sync.md)
- [docs/randomizer-spec-v1.md](/Users/akg/EVADAVA/CanvasGlassNew/docs/randomizer-spec-v1.md)

Known current visual issue:
- avatar badge still needs final gold-ring treatment

Current implementation direction

Most important near-term implementation tasks:
1. Port and adapt Spotify scripts from `_CanvasGlass` into `CanvasGlassNew`
2. Wire `Perplexity API` into the Music Search Layer
3. Implement `WAO` repeat-control execution against Google Sheet
4. Implement `MAO` repeat-control execution against Google Sheet
5. Implement cover-generation pipeline using approved Spotify cover layout
6. Implement deferred QR finalization via `links.evadava.com`
7. Finalize `MON3`
8. Finalize `MON4` template block

Rules for this Bible

- This file should stay implementation-facing.
- Do not store secret values here.
- Update this file whenever architecture, orchestration, or canonical prompts materially change.

Current run state

- active test run:
  - `test_matthieu_delfini`
- current verified stage:
  - `heygen_prompt_ready_not_sent`
- current verified selected narrative pattern:
  - `04 · THE LITURGIST`
- current verified published Spotify playlist:
  - [Floating in Open Water](https://open.spotify.com/playlist/5ZoQSvUH50zYW8xDLJug2H)

Current HeyGen template findings

- live template ids currently confirmed by API:
  - `9d56b23f021a4357ab3a9af178a1d58c` = `SENS`
  - `9e1e1c98022243e08d659789fabc658c` = `SENS_R`
  - `576c74b751b44125b53324ed23a7cc63` = `SENSV`
- `SENS`
  - has `MONOLOGUE_TEXT` as `text`
  - has `SENS_TEMP` as `voice`
- `SENS_R`
  - has `MONOLOGUE_TEXT` as `text`
- `SENSV`
  - now has `MONOLOGUE_TEXT` as `text`
  - has `SENS_V` as `voice`
- recent live HeyGen jobs:
  - `SENS` test render video id: `8823857394234048a7848fa5baf71a57`
  - `SENS_R` test render video id: `0d7ad3f9f14a4f218203196f90666465`
  - `SENSV` test render video id: `61171d2bb97c4a97945ab4b48bc66471`

Current web orchestration notes

- chat commands are now:
  - `test`
  - `start`
- web studio is where `Artist Name` is entered and run state is monitored
- human-loop controls currently implemented in web:
  - `Paintings are placed`
  - Spotify cover selection (`Select cover 1/2/3`)
  - `Monologues are placed`
- after `Paintings are placed`, backend continuation now runs:
  - `PD`
  - `Wine`
  - `Playlist package`
  - Spotify cover option generation
- after cover selection, backend continuation now runs:
  - `Avatar drafts`
  - `Avatar final monologues`
  - `HeyGen prompts`
- after `Monologues are placed`, test mode continues to:
  - `YouTube package`

Track blacklist

- a dedicated Google Sheet tab now exists:
  - `TRACK_PROBLEMS`
- Spotify publishing now consults this registry and blocks listed tracks from reuse
- seeded problem tracks include:
  - `Arvo Pärt - Spiegel im Spiegel`
  - `Nils Frahm - Says`
  - `Tigran Hamasyan - Markos and Maro`
  - `Christian Löffler - Haul`
  - `Max Richter - On the Nature of Daylight`
  - `Ludovico Einaudi - Nuvole Bianche`
