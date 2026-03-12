#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "sites" / "links"
DIST_DIR = SOURCE_DIR / "dist"
ROUTES_PATH = ROOT / "docs" / "reserved_painting_routes.json"
VIDEO_ROUTES_PATH = ROOT / "docs" / "reserved_video_routes.json"


def load_routes() -> list[dict]:
    data = json.loads(ROUTES_PATH.read_text(encoding="utf-8"))
    return data["routes"]


def load_video_routes() -> list[dict]:
    if not VIDEO_ROUTES_PATH.exists():
        return []
    data = json.loads(VIDEO_ROUTES_PATH.read_text(encoding="utf-8"))
    return data["routes"]


def ensure_clean_dist() -> None:
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    (DIST_DIR / "paintings").mkdir(parents=True, exist_ok=True)


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_home() -> str:
    return (SOURCE_DIR / "index.html").read_text(encoding="utf-8")


def build_paintings_index(routes: list[dict]) -> str:
    route_links = "\n".join(
        f'        <a class="route" href="/paintings/{route["slug"]}">{route["slug"]}</a>'
        for route in routes
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Canvas & Glass Painting Routes</title>
  <style>
    :root {{
      --bg: #f6f1e7;
      --ink: #181410;
      --muted: #6e665b;
      --panel: rgba(255,255,255,.84);
      --line: rgba(24,20,16,.10);
      --accent: #9a7829;
      --soft: #ece4d4;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      font-family: Georgia, "Times New Roman", serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(154,120,41,.18), transparent 30%),
        linear-gradient(180deg, #faf6ef 0%, var(--bg) 100%);
    }}
    main {{
      max-width: 980px;
      margin: 0 auto;
      padding: 40px 20px 80px;
    }}
    .hero, .grid {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 24px;
      box-shadow: 0 18px 44px rgba(0,0,0,.07);
      backdrop-filter: blur(10px);
    }}
    .hero {{ padding: 28px; margin-bottom: 20px; }}
    .grid {{ padding: 22px; }}
    h1, h2 {{ margin: 0; text-transform: uppercase; letter-spacing: .05em; }}
    h1 {{ font-size: clamp(1.7rem, 4vw, 3rem); line-height: .95; }}
    h2 {{ font-size: .9rem; color: var(--muted); margin-bottom: 10px; }}
    p {{ color: var(--muted); line-height: 1.6; }}
    .routes {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
      gap: 10px;
      margin-top: 12px;
    }}
    .route {{
      display: block;
      padding: 12px 10px;
      border-radius: 16px;
      background: white;
      border: 1px solid var(--line);
      color: var(--ink);
      text-decoration: none;
      text-align: center;
    }}
    code {{ font-family: "SFMono-Regular", Menlo, monospace; }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <h2>Links.Evadava.com</h2>
      <h1>Reserved Painting Routes</h1>
      <p>
        These are the currently reserved QR and landing destinations for painting pages.
        Each route is episode-specific and ready to receive final landing content.
      </p>
      <p>
        Pattern: <code>https://links.evadava.com/paintings/&lt;episode&gt;_&lt;painting&gt;</code>
      </p>
    </section>
    <section class="grid">
      <h2>Reserved Routes</h2>
      <div class="routes">
{route_links}
      </div>
    </section>
  </main>
</body>
</html>
"""


def build_video_index(routes: list[dict]) -> str:
    route_links = "\n".join(
        f'        <a class="route" href="/video/{route["slug"]}/">{route["slug"]}</a>'
        for route in routes
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Canvas & Glass Video Redirects</title>
  <style>
    :root {{
      --bg: #f6f1e7;
      --ink: #181410;
      --muted: #6e665b;
      --panel: rgba(255,255,255,.84);
      --line: rgba(24,20,16,.10);
      --accent: #9a7829;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      font-family: Georgia, "Times New Roman", serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top right, rgba(154,120,41,.18), transparent 28%),
        linear-gradient(180deg, #faf6ef 0%, var(--bg) 100%);
    }}
    main {{
      max-width: 980px;
      margin: 0 auto;
      padding: 40px 20px 80px;
    }}
    .hero, .grid {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 24px;
      box-shadow: 0 18px 44px rgba(0,0,0,.07);
      backdrop-filter: blur(10px);
    }}
    .hero {{ padding: 28px; margin-bottom: 20px; }}
    .grid {{ padding: 22px; }}
    h1, h2 {{ margin: 0; text-transform: uppercase; letter-spacing: .05em; }}
    h1 {{ font-size: clamp(1.7rem, 4vw, 3rem); line-height: .95; }}
    h2 {{ font-size: .9rem; color: var(--muted); margin-bottom: 10px; }}
    p {{ color: var(--muted); line-height: 1.6; }}
    .routes {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 10px;
      margin-top: 12px;
    }}
    .route {{
      display: block;
      padding: 12px 10px;
      border-radius: 16px;
      background: white;
      border: 1px solid var(--line);
      color: var(--ink);
      text-decoration: none;
      text-align: center;
    }}
    code {{ font-family: "SFMono-Regular", Menlo, monospace; }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <h2>Links.Evadava.com</h2>
      <h1>Reserved Video Redirects</h1>
      <p>
        These are episode-level placeholder redirects used for QR generation before the final
        YouTube private URL is attached.
      </p>
      <p>
        Pattern: <code>https://links.evadava.com/video/&lt;episode_artist&gt;/</code>
      </p>
    </section>
    <section class="grid">
      <h2>Reserved Routes</h2>
      <div class="routes">
{route_links}
      </div>
    </section>
  </main>
</body>
</html>
"""


def build_video_page(route: dict) -> str:
    slug = route["slug"]
    episode = route["episode"]
    artist = route["artist_name"]
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Canvas & Glass · Video Redirect · {slug}</title>
  <style>
    :root {{
      --bg: #f3eee4;
      --ink: #181410;
      --muted: #6e665b;
      --panel: rgba(255,255,255,.85);
      --line: rgba(24,20,16,.10);
      --accent: #9a7829;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      font-family: Georgia, "Times New Roman", serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top, rgba(154,120,41,.18), transparent 30%),
        linear-gradient(180deg, #faf6ef 0%, var(--bg) 100%);
    }}
    main {{
      max-width: 980px;
      margin: 0 auto;
      padding: 40px 20px 80px;
    }}
    .hero {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 24px;
      box-shadow: 0 18px 44px rgba(0,0,0,.07);
      padding: 28px;
    }}
    h1, h2 {{ margin: 0; text-transform: uppercase; letter-spacing: .05em; }}
    h1 {{ font-size: clamp(1.7rem, 4vw, 3rem); line-height: .95; }}
    h2 {{ font-size: .9rem; color: var(--muted); margin-bottom: 10px; }}
    p {{ color: var(--muted); line-height: 1.6; }}
    .pill {{
      display: inline-block;
      margin: 10px 12px 0 0;
      padding: 10px 14px;
      border-radius: 999px;
      background: white;
      border: 1px solid var(--line);
    }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <h2>Links.Evadava.com</h2>
      <h1>Episode {episode} Video Redirect</h1>
      <p>
        This route is reserved for the final episode video URL.
        It is stable enough to use in QR generation before the YouTube private link is attached.
      </p>
      <p class="pill">Slug: {slug}</p>
      <p class="pill">Artist: {artist}</p>
    </section>
  </main>
</body>
</html>
"""


def build_painting_page(route: dict) -> str:
    slug = route["slug"]
    episode = route["episode"]
    painting_index = route["painting_index"]
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Canvas & Glass · Episode {episode} · Painting {painting_index}</title>
  <style>
    :root {{
      --bg: #f6f1e7;
      --ink: #181410;
      --muted: #6e665b;
      --panel: rgba(255,255,255,.84);
      --line: rgba(24,20,16,.10);
      --accent: #9a7829;
      --soft: #ece4d4;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      font-family: Georgia, "Times New Roman", serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(154,120,41,.18), transparent 30%),
        linear-gradient(180deg, #faf6ef 0%, var(--bg) 100%);
    }}
    main {{
      max-width: 980px;
      margin: 0 auto;
      padding: 40px 20px 80px;
    }}
    .hero {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 24px;
      box-shadow: 0 18px 44px rgba(0,0,0,.07);
      backdrop-filter: blur(10px);
      padding: 28px;
    }}
    h1, h2 {{ margin: 0; text-transform: uppercase; letter-spacing: .05em; }}
    h1 {{ font-size: clamp(1.7rem, 4vw, 3rem); line-height: .95; }}
    h2 {{ font-size: .9rem; color: var(--muted); margin-bottom: 10px; }}
    p {{ color: var(--muted); line-height: 1.6; }}
    .meta {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      margin-top: 18px;
    }}
    .pill {{
      padding: 12px 14px;
      border-radius: 16px;
      background: var(--soft);
      color: var(--ink);
      font-size: .95rem;
    }}
    .cta {{
      display: inline-block;
      margin-top: 16px;
      padding: 12px 18px;
      border-radius: 999px;
      text-decoration: none;
      color: white;
      background: var(--ink);
    }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <h2>Links.Evadava.com</h2>
      <h1>Episode {episode} · Painting {painting_index}</h1>
      <p>
        This page is reserved for the final Canvas & Glass painting landing.
        The QR target is stable; painting content, store link, and redirect logic will be attached later.
      </p>
      <div class="meta">
        <div class="pill">Slug: {slug}</div>
        <div class="pill">Episode: {episode}</div>
        <div class="pill">Painting: {painting_index}</div>
      </div>
      <a class="cta" href="/paintings">Back to reserved routes</a>
    </section>
  </main>
</body>
</html>
"""


def main() -> None:
    routes = load_routes()
    video_routes = load_video_routes()
    ensure_clean_dist()
    write(DIST_DIR / "index.html", build_home())
    write(DIST_DIR / "paintings" / "index.html", build_paintings_index(routes))
    if video_routes:
        write(DIST_DIR / "video" / "index.html", build_video_index(video_routes))
    for route in routes:
        write(
            DIST_DIR / "paintings" / route["slug"] / "index.html",
            build_painting_page(route),
        )
    for route in video_routes:
        write(
            DIST_DIR / "video" / route["slug"] / "index.html",
            build_video_page(route),
        )


if __name__ == "__main__":
    main()
