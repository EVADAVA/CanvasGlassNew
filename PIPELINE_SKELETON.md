Canvas & Glass New Pipeline Skeleton

Episode algorithm

1. `MS start` or `MS test` selects the artist and creates the run workspace.
2. `ADNA Agent` builds `Artist DNA`.
3. `NB Agent` turns `Artist DNA` into 3 titled Nano Banana prompts.
4. user generates or places 3 paintings into the episode input folder.
5. `PD Agent` describes the 3 paintings and proposes one shared playlist name.
6. `Wine Agent` builds 3 wine picks from `PD` outputs.
7. `Music / Playlist Agent` builds the playlist package from `PD` outputs and playlist title.
8. `Avatar Agent` selects one `narr.patt`, builds the tone path, and prepares monologue outputs.
9. stop when approved manual `HeyGen prompts` are ready.
10. `HeyGen` later turns approved monologue prompts into avatar videos through manual operator submission.
11. `Painting QR Agent` prepares painting QR assets.
12. `Publisher Agent` builds title, description, links, and publish package.
13. if the run is `test`, stop when the YouTube package is ready in `output/<run>/youtube/`.
14. if the run is `start`, `Render Maker Agent` assembles the final video.
15. publish the episode.
16. `MS` marks the artist as `used`.

Pipeline table

| Step | Layer / Agent | Main input | Main output | API / external system | Filesystem target |
|---|---|---|---|---|---|
| 1 | `MS start` / `MS test` | `ARTIST_POOL`, `SETTINGS`, user command `start [Artist Name]` or `test [Artist Name]` | `run_id`, run folders, manifest, redirect reservations | Google Sheets API | `input/test_*` or `input/episode*`, matching `output/` |
| 2 | `ADNA Agent` | `artist_name` | `ADNA-text`, `fact_1..6` | Perplexity API | `output/episode*_artistname/adna/` |
| 3 | `NB Agent` | `ADNA-text`, optional `season`, `genre`, `narrative_pattern` bias | `painting_title_1..3`, `nb_prompt_1..3` | no execution API required at prompt-writing stage | `output/episode*_artistname/nb/` |
| 4 | user / image generation | `NB` prompts | 3 painting image files | Nano Banana Pro / NB2 | `input/episode*_artistname/` |
| 5 | `PD Agent` | `painting_1..3` | `pd_text_1..3`, shared `playlist_name` | vision-capable model layer | `output/episode*_artistname/pd/` |
| 6 | `Wine Agent` | `pd_text_1..3` | `wine1..3`, 2-sentence descriptions | search/reasoning layer, no posting API required | `output/episode*_artistname/wine/` |
| 7 | `Music / Playlist Agent` | `pd_text_1..3`, `playlist_name`, duration settings | playlist package, track list, playlist redirect, later Spotify URL/QR | Perplexity API for search layer, Spotify API for posting | `output/episode*_artistname/spotify/` |
| 8 | `Avatar Agent` | `ADNA`, `PD`, wines, playlist data, duration settings | `narrative_pattern_id`, tone path, `mon1..4_draft`, then `mon1..4_final` after API pass | Anthropic API | `output/episode*_artistname/monologues/draft/` and `output/episode*_artistname/monologues/final/` |
| 9 | stop gate | approved avatar package with `*_final.txt` scripts and manual HeyGen prompt handoff | `HeyGen status = prompt_ready_not_sent` | none | manifest + monologue package |
| 10 | `HeyGen` execution | approved monologue prompts and avatar mapping | rendered avatar clips | manual operator action inside HeyGen UI, supported by HeyGen API references | `output/episode*_artistname/heygen/` |
| 11 | `Painting QR Agent` | painting redirect URLs | `painting_1_qr..painting_3_qr` | QR generation utility, redirect registry on `evadava.com` | `output/episode*_artistname/qr/` |
| 12 | `Publisher Agent` | all episode assets and metadata | `videodescription`, timestamps, SEO blocks, YouTube package | YouTube-facing prep layer, optional Sheets updates | `output/episode*_artistname/youtube/` and `output/episode*_artistname/publish/` |
| 13 | test stop gate | approved package for channel upload | `youtube_package_ready` | none | manifest + `output/.../youtube/` |
| 14 | `Render Maker Agent` | paintings, monologues, QR assets, timing, HeyGen clips | final render package / video | ffmpeg / local render stack | `output/episode*_artistname/render/` or final publish path |
| 15 | publish | final video package | YouTube private video, final URL | YouTube API | `EPISODES`, publish logs |
| 16 | `MS finalize` | publish success state | `ARTIST_POOL.status = used` | Google Sheets API | Google Sheet only |

Google Sheet skeleton

| Tab | Purpose | Main fields |
|---|---|---|
| `ARTIST_POOL` | artist selection and anti-repeat | `artist_name`, `artist_slug`, `status`, `episode_id`, `selected_at`, `used_at` |
| `EPISODES` | one row per episode | `episode_id`, `episode_slug`, `artist_name`, `playlist_name`, `episode_status`, redirect URLs, publish fields |
| `Tracks` | anti-repeat for playlist tracks | `spotify_track_id`, `track_name`, `spotify_playlist_name`, `used_episode_id` |
| `WINE_REGISTRY` | anti-repeat and storage for wines | `wine1..3`, descriptions, normalized keys |
| `AVATAR` | episode-level narrative pattern and tone path | `narrative_pattern_id`, `mon1..4_tone_variant`, `mon4_closing_mode` |
| `AVATAR_REGISTRY` | maps `narr.patt` to avatar ids later | `avatar_registry_id`, `avatar_id`, `narrative_pattern_id` |
| `REDIRECT_REGISTRY` | canonical public redirect URLs | `redirect_type`, `redirect_key`, `public_url`, `target_url`, `status` |
| `SETTINGS` | runtime variables | durations, repeat thresholds, redirect settings, avatar rules |

Current API map

| Module | API / system |
|---|---|
| `MS`, registry sync, statuses | Google Sheets API |
| `ADNA Agent` | Perplexity API |
| `NB Agent` | no external posting API at prompt stage |
| image generation | Nano Banana Pro / NB2 |
| `PD Agent` | model vision layer |
| `Wine Agent` | reasoning/search layer |
| `Music Agent` search layer | Perplexity API |
| `Music Agent` posting layer | Spotify API |
| `Avatar Agent` | Anthropic API |
| `HeyGen` | HeyGen API |
| publish | YouTube API |

Current stop rule

- For the current workflow, the assistant may go up to `Avatar Agent` outputs and prompt/package preparation.
- The assistant must stop before sending anything to `HeyGen`; prompt submission is manual until further notice.
- Only `*_final.txt` monologues may become part of HeyGen prompts.
- `*_final.txt` monologue filenames must include the chosen `narrative_pattern_name` slug.
- `*_draft.txt` monologues are not HeyGen-ready.
