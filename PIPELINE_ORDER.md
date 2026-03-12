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
9. stop before `HeyGen execution`
10. `HeyGen` execution only after template readiness
11. `Painting QR Agent`
12. `Publisher Agent`
13. `Render Maker Agent`
14. publish
15. mark artist `used`

Operational rule:
- do not skip forward if the previous layer has not produced its canonical output artifacts
- for the current episode, the stop point before HeyGen is intentional
