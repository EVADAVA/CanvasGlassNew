Canvas & Glass New Pipeline Order

Canonical order for one episode:

1. `MS start`
2. `ADNA Agent`
3. `NB Agent`
4. user generates or places 3 paintings
5. `PD Agent`
6. `Wine Agent`
7. `Music / Playlist Agent`
8. `Avatar Agent`
9. stop when manual `HeyGen prompts` are ready
10. `HeyGen` execution only through manual operator submission
11. `Painting QR Agent`
12. `Publisher Agent`
13. in `test` mode stop at `youtube_package_ready`
14. in `start` mode continue to `Render Maker Agent`
15. publish
16. mark artist `used`

Operational rule:
- do not skip forward if the previous layer has not produced its canonical output artifacts
- for the current episode, the stop point before HeyGen is intentional
