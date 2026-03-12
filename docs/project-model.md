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
5. `NB Agent` receives `Artist DNA` and performs the Nano Banana prompt-engineering step under its `OSR`.
6. `NB Agent` outputs 3 prompts for `Nano Banana Pro / NB2`, each with a pre-generation painting title.
7. `Script` pauses and waits for 3 paintings in the episode input folder.
8. `Painting Describer Agent` generates `PD-text-1..3`.
9. `Wine Agent` generates 3 wine recommendations.
10. `Music Agent` creates Spotify playlist, 3 cover options, playlist URL, and playlist QR.
11. `Avatar Agent` generates 4 monologues.
12. `Publisher Agent` prepares the YouTube publication package.
13. `Script` asks for confirmation before render.
14. `Script` renders the final 60-minute video.
15. `Script` publishes the video to YouTube private state.

## Episode Folder Layout

```text
input/
  episode001_aivazovsky/
    painting1.jpg
    painting2.jpg
    painting3.jpg

output/
  episode001_aivazovsky/
    adna/
      episode001_aivazovsky_ADNA-text.txt
    nb/
      episode001_aivazovsky_NB_Painting1_Threshold_of_First_Light.txt
      episode001_aivazovsky_NB_Painting2_Sea_Under_Pressure.txt
      episode001_aivazovsky_NB_Painting3_After_the_Squall_Light.txt
    pd/
      episode001_aivazovsky_PD-text1.txt
      episode001_aivazovsky_PD-text2.txt
      episode001_aivazovsky_PD-text3.txt
    wine/
      episode001_aivazovsky_painting1_wine1.txt
      episode001_aivazovsky_painting2_wine2.txt
      episode001_aivazovsky_painting3_wine3.txt
    spotify/
      episode001_aivazovsky_playlist.txt
      episode001_aivazovsky_playlist_cover_final.jpg
      episode001_aivazovsky_playlist_qr.png
    monologues/
      comparison/
        episode001_aivazovsky_painting1_mon1_draft_vs_final.diff
        episode001_aivazovsky_painting2_mon2_draft_vs_final.diff
        episode001_aivazovsky_painting3_mon3_draft_vs_final.diff
        episode001_aivazovsky_mon4_draft_vs_final.diff
      draft/
        episode001_aivazovsky_painting1_mon1_draft.txt
        episode001_aivazovsky_painting2_mon2_draft.txt
        episode001_aivazovsky_painting3_mon3_draft.txt
        episode001_aivazovsky_mon4_draft.txt
      final/
        episode001_aivazovsky_painting1_mon1_final.txt
        episode001_aivazovsky_painting2_mon2_final.txt
        episode001_aivazovsky_painting3_mon3_final.txt
        episode001_aivazovsky_mon4_final.txt
    heygen/
    qr/
      episode001_aivazovsky_painting1_qr.png
      episode001_aivazovsky_painting2_qr.png
      episode001_aivazovsky_painting3_qr.png
    publish/
      episode001_aivazovsky_videodescription.txt
```

## Episode Status Model

### Canonical Statuses

- `queued`: artist has been selected from the registry and episode workspace has not started yet
- `initializing`: Script is creating the episode workspace and loading base settings
- `adna_ready`: `ADNA Agent` output is ready
- `prompts_ready`: `NB Agent` output is ready and waiting for paintings
- `awaiting_paintings`: Script is paused until 3 paintings appear in the episode input folder
- `paintings_ready`: all 3 paintings are present and accepted for processing
- `analysis_ready`: `PD-text-1..3` and wine recommendations are ready
- `playlist_ready`: Spotify playlist, URL, QR, and 3 cover options are ready
- `awaiting_cover_selection`: Script is paused until the user selects one playlist cover
- `cover_selected`: one playlist cover has been approved
- `monologues_ready`: all 4 monologues are ready
- `youtube_package_ready`: `TYDescription.txt` and publish package are ready
- `ready_for_render`: all required assets are present and Script is waiting for explicit render approval
- `rendering`: ffmpeg render is in progress
- `rendered`: final video file exists and passed basic output checks
- `awaiting_publish_confirmation`: render is complete and Script is waiting for explicit publish approval
- `publishing`: YouTube upload/publication is in progress
- `published_private`: video has been published to YouTube private state
- `completed`: episode is fully done and registry has been updated
- `failed`: episode hit an unrecoverable error
- `paused`: episode was intentionally paused outside the standard wait states

### Expected State Flow

1. `queued`
2. `initializing`
3. `adna_ready`
4. `prompts_ready`
5. `awaiting_paintings`
6. `paintings_ready`
7. `analysis_ready`
8. `playlist_ready`
9. `awaiting_cover_selection`
10. `cover_selected`
11. `monologues_ready`
12. `youtube_package_ready`
13. `ready_for_render`
14. `rendering`
15. `rendered`
16. `awaiting_publish_confirmation`
17. `publishing`
18. `published_private`
19. `completed`

### Transition Rules

- `awaiting_paintings -> paintings_ready` only after all 3 painting files are present
- `playlist_ready -> awaiting_cover_selection` is mandatory if more than one cover option exists
- `awaiting_cover_selection -> cover_selected` only after explicit user choice
- monologue files must encode state in filename:
  - `*_draft.txt` = assembled or prompt-ready text, not allowed into HeyGen prompts
  - `*_final.txt` = API-finalized Avatar output, allowed into HeyGen prompts
- monologue comparison files live in `monologues/comparison/`
  - `*_draft_vs_final.diff` = unified diff between locally assembled draft and API-finalized monologue
- `youtube_package_ready -> ready_for_render` only after all required assets are present
- `ready_for_render -> rendering` only after explicit user confirmation
- `rendered -> awaiting_publish_confirmation` is mandatory
- `awaiting_publish_confirmation -> publishing` only after explicit user confirmation
- any state can move to `failed` on unrecoverable processing error
- any long-running user wait state can move to `paused` if intentionally suspended

## Google Sheet Registry Model

Google Sheet is the canonical operational registry for artist selection, episode tracking, settings, and track reuse control.

### Required Tabs

- `ARTIST_POOL`
- `EPISODES`
- `Tracks`
- `WINE_REGISTRY`
- `AVATAR`
- `AVATAR_REGISTRY`
- `REDIRECT_REGISTRY`
- `SETTINGS`

### Tab: `ARTIST_POOL`

Purpose:
- source queue for `Artist Name`
- prevent artist reuse
- allow controlled sequencing

Required columns:
- `artist_name`
- `artist_slug`
- `category`
- `status`
- `used`
- `processed`
- `episode_id`
- `selected_at`
- `used_at`
- `last_episode`
- `notes`

Script responsibilities:
- read the next artist that is not already locked by `selected` or finalized as `used`
- if the requested artist does not yet exist, create and normalize the artist row during `start`
- derive or verify `artist_slug`
- assign `episode_id` using zero-padded mask `001`, `002`, `003` ...
- write `status = selected` when an episode starts
- write `status = used` only after successful publication

### Tab: `EPISODES`

Purpose:
- registry of all episode runs
- current operational state for each episode

Required columns:
- `episode_id`
- `episode_slug`
- `artist_name`
- `artist_slug`
- `artist_pool_status`
- `episode_status`
- `input_dir`
- `output_dir`
- `playlist_name`
- `spotify_playlist_url`
- `spotify_cover_url`
- `spotify_qr_path`
- `video_redirect_url`
- `playlist_redirect_url`
- `painting1_redirect_url`
- `painting2_redirect_url`
- `painting3_redirect_url`
- `youtube_video_url`
- `youtube_video_id`
- `video_description_path`
- `created_at`
- `updated_at`
- `published_at`
- `error`

Script responsibilities:
- create one row per episode
- update `episode_status` on every state transition
- persist the episode-level `playlist_name` generated from the 3 paintings and reused by Spotify
- store final YouTube URL and video ID after successful publish
- write `error_message` on failure

### Tab: `Tracks`

Purpose:
- prevent repeated use of the same Spotify tracks across episodes
- maintain historical track usage

Required columns:
- `spotify_track_id`
- `track_name`
- `track_artist`
- `album_name`
- `spotify_playlist_id`
- `spotify_playlist_name`
- `used_episode_id`
- `used_artist_slug`
- `session_index`
- `used_at`

Script responsibilities:
- check candidate tracks against this registry before playlist creation
- record all selected playlist tracks after playlist creation

### Tab: `WINE_REGISTRY`

Purpose:
- store all 3 wine recommendations for each episode
- maintain historical wine usage
- support later reuse rules if wine repetition should be limited

Required columns:
- `episode_id`
- `artist_name`
- `artist_slug`
- `wine1`
- `wine1_description`
- `wine1_type`
- `wine1_region`
- `wine1_producer`
- `wine1_normalized_key`
- `wine2`
- `wine2_description`
- `wine2_type`
- `wine2_region`
- `wine2_producer`
- `wine2_normalized_key`
- `wine3`
- `wine3_description`
- `wine3_type`
- `wine3_region`
- `wine3_producer`
- `wine3_normalized_key`
- `recorded_at`

Script responsibilities:
- append exactly 1 wine registry row per completed wine recommendation step
- keep one row per episode
- store all 3 final wine recommendations in the same row for downstream retrieval
- preserve normalized helper fields so WAO can enforce anti-repeat logic reliably

### Tab: `AVATAR`

Purpose:
- store episode-level narrative pattern decisions
- maintain historical tone-of-voice usage
- support anti-repetition rules for the Avatar layer

Required columns:
- `episode_id`
- `artist_name`
- `artist_slug`
- `narrative_pattern_id`
- `narrative_pattern_name`
- `avatar_registry_id`
- `avatar_id`
- `avatar_name`
- `mon1_tone_variant`
- `mon2_tone_variant`
- `mon3_tone_variant`
- `mon4_tone_variant`
- `mon4_closing_mode`
- `recorded_at`

Script responsibilities:
- append exactly 1 avatar row per completed episode-level avatar decision
- keep one row per episode
- preserve pattern, avatar, and tone-path history so AAO can enforce anti-repeat logic reliably

### Tab: `AVATAR_REGISTRY`

Purpose:
- map available HeyGen avatar ids to `narrative_pattern_id`
- make avatar selection deterministic after Random Agent chooses the episode pattern

Required columns:
- `avatar_registry_id`
- `avatar_id`
- `avatar_name`
- `avatar_type`
- `narrative_pattern_id`
- `narrative_pattern_name`
- `default_voice_id`
- `is_active`
- `notes`

Script responsibilities:
- read one active avatar mapping for the chosen `narrative_pattern_id`
- pass the same avatar choice through `MON1..MON4` for the full episode

### Tab: `REDIRECT_REGISTRY`

Purpose:
- reserve stable public URLs before final landing targets exist
- store video, playlist, and painting redirect routes used by QR generation

Required columns:
- `episode_id`
- `artist_name`
- `artist_slug`
- `redirect_type`
- `entity_name`
- `redirect_key`
- `public_url`
- `target_url`
- `status`
- `recorded_at`
- `notes`

Approved test redirects:
- `https://evadava.com/episode001_aivazovsky_video/`
- `https://evadava.com/episode001_aivazovsky_playlist/`
- `https://evadava.com/episode001_aivazovsky_painting1/`
- `https://evadava.com/episode001_aivazovsky_painting2/`
- `https://evadava.com/episode001_aivazovsky_painting3/`

### Tab: `SETTINGS`

Purpose:
- store runtime settings and reusable project configuration

Required columns:
- `key`
- `value`
- `description`

Expected setting keys:
- `duration_1_min`
- `duration_2_min`
- `duration_3_min`
- `episode_id_padding`
- `artist_pool_sheet`
- `artist_pool_select_value`
- `artist_pool_used_value`
- `spotify_cover_count`
- `wine_repeat_kr`
- `wine_repeat_history_depth`
- `track_repeat_kr`
- `track_repeat_history_depth`
- `avatar_repeat_kr`
- `avatar_repeat_history_depth`
- `redirect_public_domain`
- `video_redirect_base_path`
- `painting_redirect_base_path`
- `playlist_redirect_base_path`
- `redirect_slug_pattern`
- `heygen_avatar_selection_mode`

Script responsibilities:
- read settings at startup
- fall back to local config only if a setting is intentionally absent

### Recommended Selection Rule

When Telegram starts a new run:

1. read `settings`
2. read `ARTIST_POOL`
3. select the next artist not already in terminal `used` state
4. create `episode_id`
5. set artist `status = selected`
6. create episode folder tree
7. insert new row in `EPISODES`
7. continue processing

### Recommended Update Rule

At every major step, Script updates the matching row in `episodes`:

- state change
- important URLs
- final outputs
- failure details

At successful completion:

- set `ARTIST_POOL.status = used`
- write `ARTIST_POOL.used = 1`
- write `ARTIST_POOL.used_at`
- append used tracks to `Tracks`
- append wine recommendations to `WINE_REGISTRY`

## Communication Layer Contract

Communication is driven by Telegram natural-language messages interpreted by an LLM layer.

The LLM does not execute actions directly. It converts user messages into structured intents that are validated against the current `episode_status`.

### Communication Flow

1. Telegram receives a user message.
2. Script loads the active episode context.
3. Script sends message text, current state, and allowed actions to the LLM.
4. LLM returns a structured interpretation.
5. Script validates the returned intent against the current state.
6. Script executes the action or replies with a blocked/clarifying response.

### Required Runtime Context

The LLM interpreter must receive:

- `episode_id`
- `artist_name`
- `artist_slug`
- `episode_status`
- `pending_user_step`
- `allowed_intents`
- `recent_system_messages`
- `recent_user_messages`

### Core User Intents

- `start_episode`
- `get_status`
- `show_expected_next_step`
- `show_cover_options`
- `select_cover`
- `confirm_render`
- `confirm_publish`
- `pause_episode`
- `resume_episode`
- `cancel_episode`
- `help`

### Intent Rules By Status

#### Global intents

These are allowed in any active state:

- `get_status`
- `show_expected_next_step`
- `help`
- `pause_episode`

#### `queued`

Allowed intents:
- `start_episode`
- `get_status`
- `help`

#### `initializing`

Allowed intents:
- `get_status`
- `show_expected_next_step`
- `pause_episode`

#### `adna_ready`

Allowed intents:
- `get_status`
- `show_expected_next_step`
- `pause_episode`

#### `prompts_ready`

Allowed intents:
- `get_status`
- `show_expected_next_step`
- `pause_episode`

#### `awaiting_paintings`

Allowed intents:
- `get_status`
- `show_expected_next_step`
- `pause_episode`

#### `paintings_ready`

Allowed intents:
- `get_status`
- `show_expected_next_step`
- `pause_episode`

#### `analysis_ready`

Allowed intents:
- `get_status`
- `show_expected_next_step`
- `pause_episode`

#### `playlist_ready`

Allowed intents:
- `get_status`
- `show_cover_options`
- `show_expected_next_step`
- `pause_episode`

#### `awaiting_cover_selection`

Allowed intents:
- `get_status`
- `show_cover_options`
- `select_cover`
- `show_expected_next_step`
- `pause_episode`

#### `cover_selected`

Allowed intents:
- `get_status`
- `show_expected_next_step`
- `pause_episode`

#### `monologues_ready`

Allowed intents:
- `get_status`
- `show_expected_next_step`
- `pause_episode`

#### `youtube_package_ready`

Allowed intents:
- `get_status`
- `show_expected_next_step`
- `pause_episode`

#### `ready_for_render`

Allowed intents:
- `get_status`
- `show_expected_next_step`
- `confirm_render`
- `pause_episode`

#### `rendering`

Allowed intents:
- `get_status`
- `show_expected_next_step`

#### `rendered`

Allowed intents:
- `get_status`
- `show_expected_next_step`

#### `awaiting_publish_confirmation`

Allowed intents:
- `get_status`
- `show_expected_next_step`
- `confirm_publish`
- `pause_episode`

#### `publishing`

Allowed intents:
- `get_status`
- `show_expected_next_step`

#### `published_private`

Allowed intents:
- `get_status`
- `show_expected_next_step`

#### `paused`

Allowed intents:
- `get_status`
- `resume_episode`
- `cancel_episode`
- `help`

#### `failed`

Allowed intents:
- `get_status`
- `help`

### Example User Phrases

Examples are natural-language hints, not command syntax requirements.

#### `start_episode`

- `start`
- `start next episode`
- `let's go`
- `begin`

#### `get_status`

- `status`
- `where are we`
- `what's the status`
- `give me update`

#### `show_expected_next_step`

- `what are we waiting for`
- `what's next`
- `what do you need from me`

#### `show_cover_options`

- `give me covers`
- `show covers`
- `show playlist covers`

#### `select_cover`

- `1`
- `2`
- `3`
- `choose 2`
- `take cover 3`

#### `confirm_render`

- `+`
- `render`
- `go ahead`
- `start render`

#### `confirm_publish`

- `publish`
- `upload it`
- `go publish`
- `yes, publish`

#### `pause_episode`

- `pause`
- `stop here`
- `hold it`

#### `resume_episode`

- `resume`
- `continue`
- `go on`

#### `cancel_episode`

- `cancel`
- `abort`
- `stop this episode`

#### `help`

- `help`
- `what can I say`
- `what can you do`

### LLM Output Schema

The LLM interpreter must return structured JSON only.

```json
{
  "intent": "select_cover",
  "allowed": true,
  "confidence": 0.98,
  "arguments": {
    "cover_index": 2
  },
  "reply": "Selected cover 2. Moving to the next step.",
  "needs_clarification": false,
  "clarification_question": null
}
```

### Required Output Fields

- `intent`: normalized intent name
- `allowed`: whether the action is valid in the current episode state
- `confidence`: numeric confidence score from 0 to 1
- `arguments`: parsed action arguments
- `reply`: user-facing message draft
- `needs_clarification`: whether Script should ask a follow-up question instead of executing
- `clarification_question`: follow-up question if clarification is needed

### Validation Rules

- if `intent` is not in `allowed_intents`, Script must reject execution
- if required arguments are missing, `needs_clarification` must be `true`
- numeric cover selection must only map to `select_cover` inside `awaiting_cover_selection`
- `+` must only map to `confirm_render` inside `ready_for_render`
- publish-like phrases must only map to `confirm_publish` inside `awaiting_publish_confirmation`
- LLM must never fabricate unavailable assets, URLs, or state transitions

### Response Style

Script responses should be short, operational, and state-aware.

Examples:

- `Prompts are ready. Waiting for 3 paintings in the input folder.`
- `Please choose one playlist cover: 1, 2, or 3.`
- `Render is complete. Waiting for publish confirmation.`
- `That action is not available right now. I am waiting for cover selection.`

## Master Narrative And Monologue Spec

The 4 monologues are generated by a master narrative layer with:

- one selected `Narrative Pattern`
- fixed monologue skeletons
- variable injection at generation time

All 4 monologues are final full-text outputs.

They are not stored or rendered as disconnected phrase fragments. The language agent produces complete `monologue_1..4` texts for a single episode, with narrative pattern logic already applied.

Narrative Pattern affects the emotional and rhetorical filter applied to painting descriptions and variable content. It does not replace the structural role of each monologue.

### Narrative Pattern Selection

Exactly 1 of 10 patterns is selected per episode.

Selection rule:
- match the chosen pattern to the `ADNA` emotional register of the artist

Patterns:
- `the_reluctant_prophet`
- `the_sensualist_philosopher`
- `the_exile_in_amber`
- `the_slow_radical`
- `the_alchemist_curator`
- `the_wounded_aesthete`
- `the_double_agent`
- `the_liturgist`
- `the_generous_eccentric`
- `the_witness_of_transformation`

### Master Rules For All Monologues

These rules apply to all 4 monologues without exception:

- hook first: open with `hook_fact` or another tension-creating line
- retention arc: move from tension to release to invitation
- selling voice: sell an experience, not a product
- voice: warm, unhurried Canadian English with slight wit
- every monologue must include a smooth spoken transition into the next act of looking
- variable slots are injected into fixed templates
- target ratio: about 60 percent fixed template and 40 percent variable content

### Monologue Roles

#### `monologue_1`

Function:
- opens the episode
- introduces Alexander and the channel
- invites the viewer into the immersive wine art meditation devoted to the artist
- recommends `wine_1`
- introduces the first painting through the selected narrative pattern
- presents the Spotify playlist and QR
- relaxes the viewer into session 1

Mandatory variables:
- `hook_fact_1`
- `hook_fact_2`
- `fact_1`
- `fact_2`
- `wine_1`
- `wine_1_red_note` if applicable
- `playlist_qr`
- `artist_name`
- `pd_text_1`
- `an_description_painting_1`
- `monologue_1_tone_variant`
- `sound_invitation_copy`

Assembly rules:
- opening hook must be built from 2 interesting biography facts about the artist
- hook fact and following biography lines must not duplicate the same claim
- greeting copy must adapt to the selected narrative pattern
- the wine recommendation must be selected from `Wine Agent` output with registry-based repetition control
- the meditation entry must be a calming full-text passage, not a label or instruction stub
- painting 1 description must originate from `pd_text_1` and then be rewritten through the selected narrative pattern
- monologue must contain a soft handoff into looking at painting 1
- playlist and wine blocks may vary in phrasing, but must retain all required information in spoken form
- playlist QR mention must include top-right placement and 60-second visibility
- sound invitation copy should encourage the viewer to turn on or attend to the soundscape

#### `monologue_2`

Function:
- opens session 2
- uses only a short carry-over from painting 1 through the selected narrative pattern
- prepares the viewer for the adjustment required by painting 2
- explains the 3-session arc
- recommends `wine_2`

Mandatory variables:
- `an_description_painting_1`
- `wine_2`
- `wine_2_red_note` if applicable

Negative rules:
- no biography facts
- no academic art-history register
- no instructions, only invitations
- no technique discussion unless it serves emotional description
- no long restatement of painting 1
- the main descriptive energy should prepare perception for painting 2

#### `monologue_3`

Function:
- opens session 3
- reflects on painting 2
- builds toward catharsis
- carries Alexander's most personal reflection in the episode
- recommends `wine_3`

Mandatory variables:
- `an_description_painting_2`
- `fact_3_or_fact_4`
- `alexander_personal_reflection`
- `wine_3`
- `wine_3_red_note` if applicable

Status:
- source prompt is incomplete
- final template must be authored before implementation freeze

#### `monologue_4`

Function:
- closes the episode
- synthesizes all 3 sessions
- reflects on painting 3
- closes with return invitation
- resolves through the selected narrative pattern rather than a fixed outro cadence
- may include a calm support / acquisition invitation after gratitude

Mandatory variables:
- `an_description_painting_3`
- `fact_5`
- `fact_6`
- `artist_name`
- `monologue_4_tone_variant`

Assembly rules:
- closing synthesis must be rewritten through the selected narrative pattern
- the return invitation must sound episode-specific rather than like a reusable subscribe block
- gratitude should acknowledge shared presence with Alexander across the hour and the common meditative space
- any commercial invitation should feel premium, understated, and deserved rather than pushy
- `monologue_4` should vary cadence, intimacy, and emotional temperature across episodes
- no hard summary-drop at the start of the final monologue
- no mechanical reuse of the same closing formula across multiple artists

### Variable Injection Map

- `artist_name`: episode artist
- `hook_fact_1`: first opening biography fact
- `hook_fact_2`: second opening biography fact
- `fact_1`
- `fact_2`
- `fact_3`
- `fact_4`
- `fact_5`
- `fact_6`
- `an_description_painting_1`: painting 1 description filtered through the selected narrative pattern
- `an_description_painting_2`: painting 2 description filtered through the selected narrative pattern
- `an_description_painting_3`: painting 3 description filtered through the selected narrative pattern
- `wine_1`
- `wine_2`
- `wine_3`
- `wine_1_red_note`
- `wine_2_red_note`
- `wine_3_red_note`
- `playlist_url`
- `playlist_qr`
- `narrative_pattern_id`
- `narrative_pattern_name`
- `alexander_personal_reflection`
- `monologue_1_tone_variant`
- `sound_invitation_copy`
- `monologue_4_tone_variant`

### Red Wine Trigger Rule

If any session wine is red:

- inject the corresponding red-wine note into the monologue
- mention wide-bowl glass
- mention decanter timing in a casual, non-instructional way

Default short red-wine note:

`You'll want a wide-bowl glass for this one, and if you have a decanter, give it a little time to open up.`

### Derived Monologue Variables

These should be added to episode runtime state:

- `narrative_pattern_id`
- `narrative_pattern_name`
- `hook_fact_1`
- `hook_fact_2`
- `fact_1`
- `fact_2`
- `fact_3`
- `fact_4`
- `fact_5`
- `fact_6`
- `an_description_painting_1`
- `an_description_painting_2`
- `an_description_painting_3`
- `alexander_personal_reflection`
- `wine_1_red_note`
- `wine_2_red_note`
- `wine_3_red_note`
- `monologue_1_tone_variant`
- `sound_invitation_copy`

### Narrative Randomizer Rules

The script must track narrative/tone reuse in Google Sheet and avoid mechanical repetition.

Required controls:

- selected `narrative_pattern` is episode-level
- monologue-specific tone variation may still shift within the chosen narrative family
- repetition quota for monologue tone variants: `20%`
- lookback depth for monologue tone randomizer: last `10` episodes
- the chosen pattern must remain stable across the episode
- tonal motion across `monologue_1..4` is allowed and expected
- tone motion must preserve the hour arc: entry -> adjustment -> pressure -> synthesis
- closing cadences for `monologue_4` should be tracked and rotated to avoid template-feel recurrence

### Narrative Pattern Recommender

Before `Avatar Agent` generation, the system should recommend one base episode pattern.

Inputs:
- `adna_text`
- `pd_text_1`
- `pd_text_2`
- `pd_text_3`
- `playlist_name`

Selection priority:
- ADNA emotional register
- emotional/material behavior of the 3 paintings
- whether the triptych reads as sensual, devotional, melancholic, theatrical, resistant, or synthetic

Output:
- `narrative_pattern_id`
- `narrative_pattern_name`
- short justification
- `monologue_1_tone_variant`
- `monologue_2_tone_variant`
- `monologue_3_tone_variant`
- `monologue_4_tone_variant`

Rule:
- base pattern is recommended once per episode
- monologue tone variants move inside that base pattern
- tone variants are not allowed to become separate competing patterns

This requires registry storage for:

- `episode_id`
- `narrative_pattern_id`
- `monologue_1_tone_variant`
- `monologue_2_tone_variant`
- `monologue_3_tone_variant`
- `monologue_4_tone_variant`
- `recorded_at`

### Random Agent

`Random Agent` is the internal selector that formalizes narrative variation before monologue generation.

It sits between:
- `ADNA Agent`
- `Painting Describer Agent`
- `Avatar Agent`

Its job is not to write language.
Its job is to select a stable episode-level pattern package.

Inputs:
- `episode_id`
- `artist_name`
- `adna_text`
- `pd_text_1`
- `pd_text_2`
- `pd_text_3`
- recent registry history

Outputs:
- `narrative_pattern_id`
- `narrative_pattern_name`
- `selection_justification`
- `monologue_1_tone_variant`
- `monologue_2_tone_variant`
- `monologue_3_tone_variant`
- `monologue_4_tone_variant`
- `monologue_4_closing_mode`
- `reuse_risk_note`

Rules:
- chooses exactly one base pattern per episode
- the chosen pattern remains stable across the hour
- tone movement is allowed only inside that pattern family
- lookback window should cover at least the last `10` episodes
- identical pattern reuse is discouraged
- repeated MON4 closure cadences should be actively rotated
- artistic fit outranks novelty pressure

Operationally:
- `Pattern Recommender` logic becomes the decision core of `Random Agent`
- `Random Agent` is the canonical pre-monologue selector
- `Avatar Agent` receives already-selected pattern + tone package

### Monologue Delivery Constraints

- each monologue should target about 1 minute of spoken delivery
- `monologue_1` must mention the playlist QR visibility window
- `monologue_1` starts at the beginning of the video and occupies about the first minute
- `monologue_2` must establish the arc: entry -> depth -> catharsis
- `monologue_3` must feel most personal
- `monologue_4` must introduce no new information
- `monologue_4` must still feel unique in rhetorical shape even when informational inputs are similar

### Working Template Status

Current readiness:

- `monologue_1`: template available
- `monologue_2`: template available
- `monologue_3`: partially specified, needs completion
- `monologue_4`: template available

## Agents

### ADNA Agent

- input: `artist_name`
- output: `adna_text`, `adna_fact_1..6`

### NB Agent

- input: `adna_text`, `narrative_pattern`, `season`, optional `genre`
- output: `nb_prompt_1..3`, `painting_title_1..3`

### Painting Describer Agent

- input: `painting_1..3`
- output: `pd_text_1..3`
- purpose: produce structured operational painting descriptions for wine, music, monologue, and commercial downstream use

### Wine Agent

- input: `pd_text_1..3`
- output: 3 wine recommendations
- rule: if red wine is recommended, also recommend a wide-bowl glass and decanter

### Music Agent

- input: `pd_text_1..3`
- output: Spotify playlist, 3 cover options, playlist URL, playlist QR

### Random Agent

- input: `adna_text`, `pd_text_1..3`, recent episode registry
- output: one episode-level narrative package
- purpose: select one narrative pattern, four tone variants, and one MON4 closing mode while suppressing recent repetition

### Avatar Agent

- input: project variables
- output: `monologue_1..4`
- narrative logic source: master monologue templates plus one selected episode-level narrative pattern

### Publisher Agent

- input: project variables and content assets
- output: `TYDescription.txt` and YouTube publication package

### Painting QR Agent

- input: `painting_1_store_url`, `painting_2_store_url`, `painting_3_store_url`
- output: `painting_1_qr_path`, `painting_2_qr_path`, `painting_3_qr_path`
- purpose: generate painting-specific QR assets before final render

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

### Render Timing Formula

Episode timing comes from Google Sheet Settings:

- `duration_1_min`
- `duration_2_min`
- `duration_3_min`

Derived:

- `duration_1_sec = duration_1_min * 60`
- `duration_2_sec = duration_2_min * 60`
- `duration_3_sec = duration_3_min * 60`
- `episode_total_duration_sec = duration_1_sec + duration_2_sec + duration_3_sec`

Canonical monologue timing:

- `monologue_1_start_sec = 0`
- `monologue_2_start_sec = duration_1_sec`
- `monologue_3_start_sec = duration_1_sec + duration_2_sec`
- `monologue_4_start_sec = duration_1_sec + duration_2_sec + duration_3_sec - 300`

Interpretation:

- MON1 occupies the first minute of Duration1
- MON2 occupies the first minute of Duration2
- MON3 occupies the first minute of Duration3
- MON4 starts exactly 5 minutes before the end of Duration3

If any rendered monologue crosses into a forbidden overlap zone, the system should flag a timing violation instead of silently stacking blocks.

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
- `episode_started_at`
- `episode_finished_at`
- `input_dir`
- `output_dir`
- `assets_dir`
- `render_dir`
- `created_at`
- `updated_at`
- `sheet_registry_ref`

### Episode Settings

- `duration_1_min`
- `duration_2_min`
- `duration_3_min`
- `episode_total_duration_min`
- `episode_total_duration_sec`

### ADNA Knowledge

- `adna_text`
- `adna_fact_1`
- `adna_fact_2`
- `adna_fact_3`
- `adna_fact_4`
- `adna_fact_5`
- `adna_fact_6`

### NB Prompt Set

- `narrative_pattern`
- `season`
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
- `playlist_name`
- `spotify_playlist_name`
- `spotify_playlist_url`
- `spotify_track_list`
- `spotify_cover_option_1`
- `spotify_cover_option_2`
- `spotify_cover_option_3`
- `spotify_selected_cover`
- `spotify_playlist_qr_path`
- `spotify_redirect_url`
- `playlist_target_duration_min`

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
- `narrative_pattern_id`
- `narrative_pattern_name`
- `monologue_1_tone_variant`
- `monologue_2_tone_variant`
- `monologue_3_tone_variant`
- `monologue_4_tone_variant`
- `monologue_4_closing_mode`
- `wine_1_*`
- `wine_2_*`
- `wine_3_*`
- `playlist_name`
- `spotify_playlist_id`
- `spotify_playlist_name`
- `spotify_playlist_url`
- `spotify_track_list`
- `spotify_cover_option_1..3`
- `spotify_playlist_qr_path`
- `spotify_redirect_url`
- `painting_1_qr_path`
- `painting_2_qr_path`
- `painting_3_qr_path`
- `monologue_1_text..4`
- `monologue_1_start_sec`
- `monologue_2_start_sec`
- `monologue_3_start_sec`
- `monologue_4_start_sec`
- `monologue_1_visible_end_sec`
- `monologue_2_visible_end_sec`
- `monologue_3_visible_end_sec`
- `monologue_4_visible_end_sec`
- `asmr_track_id`
- `avatar_template_id`
- `render_motion_profile`
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
- `selected_cover_index`

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
