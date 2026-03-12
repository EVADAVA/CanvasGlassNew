#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import qrcode
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from sync_google_sheet_schema import get_token as get_gsheets_token
from sync_google_sheet_schema import get_values, update_values


ROOT = Path(__file__).resolve().parents[1]
SIZE = 3000
MASTER_LOGO_CANDIDATES = [
    ROOT / "logos" / "Profile Mono.png",
    ROOT / "logos" / "Profile Double.jpeg",
]


def rounded_rectangle_mask(size: tuple[int, int], radius: int) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, size[0], size[1]), radius=radius, fill=255)
    return mask


def load_font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def fit_font(text: str, width: int, target_size: int) -> ImageFont.FreeTypeFont:
    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    size = target_size
    while size >= 36:
        font = load_font(size)
        bbox = probe.textbbox((0, 0), text, font=font, stroke_width=max(2, size // 28))
        if (bbox[2] - bbox[0]) <= width:
            return font
        size -= 6
    return load_font(36)


def fit_artist_font(text: str, width: int) -> ImageFont.FreeTypeFont:
    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    for size in (286, 277, 265, 253, 238, 223, 208, 193, 178, 166, 154):
        font = load_font(size)
        bbox = probe.textbbox((0, 0), text, font=font, stroke_width=max(3, size // 26))
        if (bbox[2] - bbox[0]) <= width:
            return font
    return fit_font(text, width, 154)


def pick_artist_and_qr_layout(text: str, inner_w: int, padding: int) -> tuple[ImageFont.FreeTypeFont, int]:
    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    qr_max = int(inner_w * 0.34)
    qr_min = int(inner_w * 0.14)
    for font_size in (286, 277, 265, 253, 238, 223, 208, 193, 178):
        font = load_font(font_size)
        artist_bbox = probe.textbbox((0, 0), text, font=font, stroke_width=max(3, font_size // 26))
        artist_width = artist_bbox[2] - artist_bbox[0]
        qr_width = qr_max
        while qr_width >= qr_min:
            content_width = inner_w - (padding * 3) - (qr_width + 40)
            if artist_width <= content_width:
                return font, qr_width
            qr_width -= 16
    fallback_qr = qr_min
    fallback_width = inner_w - (padding * 3) - (fallback_qr + 16)
    return fit_artist_font(text, fallback_width), fallback_qr


def build_qr_image(url: str, size: int) -> Image.Image:
    qr = qrcode.QRCode(border=2, box_size=12)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    return img.resize((size, size), Image.Resampling.LANCZOS)


def paste_qr(overlay: Image.Image, qr_img: Image.Image, box: tuple[int, int, int, int]) -> None:
    x0, y0, x1, y1 = box
    target = min(x1 - x0, y1 - y0)
    qr = qr_img.resize((target, target), Image.Resampling.LANCZOS).convert("RGBA")
    plate = Image.new("RGBA", (target, target), (255, 255, 255, 230))
    plate_draw = ImageDraw.Draw(plate)
    plate_draw.rounded_rectangle((0, 0, target - 1, target - 1), radius=16, fill=(255, 255, 255, 230))
    plate.alpha_composite(qr, (0, 0))
    overlay.alpha_composite(plate, (x0, y0))


def paste_round_logo(overlay: Image.Image, logo_file: Path, box: tuple[int, int, int, int]) -> None:
    x0, y0, x1, y1 = box
    size = min(x1 - x0, y1 - y0)
    logo = Image.open(logo_file).convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((0, 0, size - 1, size - 1), fill=255)
    clipped = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    clipped.alpha_composite(logo)
    clipped.putalpha(mask)
    overlay.alpha_composite(clipped, (x0, y0))


def resolve_logo() -> Path:
    for candidate in MASTER_LOGO_CANDIDATES:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("No round logo source found in /logos")


def make_cover(
    painting_path: Path,
    logo_path: Path,
    artist_name: str,
    qr_target: str,
    out_path: Path,
) -> None:
    base = ImageOps.fit(Image.open(painting_path).convert("RGB"), (SIZE, SIZE), Image.Resampling.LANCZOS, centering=(0.5, 0.5))
    base = ImageEnhanceProxy.enhance(base)

    overlay = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    style_box = (90, SIZE - 1065, SIZE - 90, SIZE - 120)
    draw.rounded_rectangle(style_box, radius=34, fill=(10, 10, 10, 170))

    x0, y0, x1, y1 = style_box
    inner_w = x1 - x0
    fill = (248, 244, 236, 255)
    stroke_fill = (0, 0, 0)
    stroke_width = 5
    padding = 48
    artist_label = artist_name.upper()
    artist_font, qr_zone_width = pick_artist_and_qr_layout(artist_label, inner_w, padding)
    content_width = inner_w - (padding * 3) - (qr_zone_width + 16)

    fixed_lines = [
        "IMMERSIVE WINE",
        "ART MEDITATION",
        "BY ALEXANDER KUGUK",
        "INSPIRED BY THE ART OF",
    ]
    fonts = [
        fit_font(fixed_lines[0], content_width, 182),
        fit_font(fixed_lines[1], content_width, 182),
        fit_font(fixed_lines[2], content_width, 76),
        fit_font(fixed_lines[3], content_width, 76),
    ]
    measure = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    bboxes = [measure.textbbox((0, 0), line, font=font, stroke_width=stroke_width) for line, font in zip(fixed_lines, fonts)]
    artist_bbox = measure.textbbox((0, 0), artist_label, font=artist_font, stroke_width=stroke_width + 1)
    artist_height = artist_bbox[3] - artist_bbox[1]

    line_gaps = [20, 50, 20, 18]
    top_x = x0 + padding
    visual_top = y0 + padding
    artist_x = x0 + padding
    artist_y = y1 - padding - artist_height - artist_bbox[1]
    y = visual_top - bboxes[0][1]
    positions: list[int] = []
    for idx, bbox in enumerate(bboxes):
        if idx > 0:
            prev_bbox = bboxes[idx - 1]
            y += line_gaps[idx - 1] + prev_bbox[3] - bbox[1]
        positions.append(y)

    second_bottom = positions[1] + bboxes[1][3]
    third_top_target = second_bottom + max(
        0,
        ((artist_y + artist_bbox[1]) - second_bottom - ((bboxes[2][3] - bboxes[2][1]) + 20 + (bboxes[3][3] - bboxes[3][1]))) // 2,
    )
    positions[2] = third_top_target - bboxes[2][1]
    positions[3] = positions[2] + (bboxes[2][3] - bboxes[2][1]) + 20 + bboxes[2][1] - bboxes[3][1]

    fourth_line_bottom = visual_top
    for idx, (line, font, bbox) in enumerate(zip(fixed_lines, fonts, bboxes)):
        draw.text((top_x, positions[idx]), line, font=font, fill=fill, stroke_width=stroke_width, stroke_fill=stroke_fill)
        if idx == 3:
            fourth_line_bottom = positions[idx] + bbox[3]
    draw.text((artist_x, artist_y), artist_label, font=artist_font, fill=fill, stroke_width=stroke_width + 1, stroke_fill=stroke_fill)

    qr_img = build_qr_image(qr_target, 1200)
    qr_top = visual_top
    qr_plate_size = int(fourth_line_bottom - qr_top)
    paste_qr(
        overlay,
        qr_img,
        (x1 - padding - qr_plate_size, qr_top, x1 - padding, qr_top + qr_plate_size),
    )

    logo_size = int(qr_plate_size * 1.18)
    logo_right = SIZE - 48
    logo_top = 48
    paste_round_logo(
        overlay,
        logo_path,
        (logo_right - logo_size, logo_top, logo_right, logo_top + logo_size),
    )

    final = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    final.save(out_path, format="JPEG", quality=95)


class ImageEnhanceProxy:
    @staticmethod
    def enhance(image: Image.Image) -> Image.Image:
        # Keep it restrained; the template calls for only a light polish.
        sharpened = image.filter(ImageFilter.UnsharpMask(radius=1.6, percent=112, threshold=3))
        return ImageOps.autocontrast(sharpened, cutoff=1)


def make_contact_sheet(image_paths: list[Path], out_path: Path) -> None:
    images = [Image.open(path).convert("RGB").resize((900, 900), Image.Resampling.LANCZOS) for path in image_paths]
    canvas = Image.new("RGB", (2800, 1120), (246, 243, 238))
    draw = ImageDraw.Draw(canvas)
    title_font = load_font(90)
    label_font = load_font(72)
    draw.text((90, 40), "SPOTIFY COVER OPTIONS", font=title_font, fill=(23, 24, 27))
    x_positions = [90, 950, 1810]
    for idx, (img, x) in enumerate(zip(images, x_positions), start=1):
        canvas.paste(img, (x, 120))
        draw.text((x, 1040), f"OPTION {idx}", font=label_font, fill=(23, 24, 27))
    canvas.save(out_path, format="JPEG", quality=92)


def update_episode_status(episode_id: str, option_paths: list[Path]) -> None:
    token = get_gsheets_token()
    rows = get_values(token, "EPISODES!A:AE")
    headers = rows[0]
    values = rows[:]
    for idx, row in enumerate(values[1:], start=1):
        row = row + [""] * (len(headers) - len(row))
        if row[headers.index("episode_id")] != episode_id:
            continue
        if "episode_status" in headers:
            row[headers.index("episode_status")] = "awaiting_cover_selection"
        if "status" in headers:
            row[headers.index("status")] = "awaiting_cover_selection"
        if "spotify_cover_option_1" in headers:
            row[headers.index("spotify_cover_option_1")] = str(option_paths[0])
        if "spotify_cover_option_2" in headers:
            row[headers.index("spotify_cover_option_2")] = str(option_paths[1])
        if "spotify_cover_option_3" in headers:
            row[headers.index("spotify_cover_option_3")] = str(option_paths[2])
        values[idx] = row
        break
    update_values(token, f"EPISODES!A1:AE{len(values)}", values)


def update_manifest(episode_slug: str, option_paths: list[Path], contact_sheet: Path) -> None:
    manifest_path = ROOT / "output" / episode_slug / "publish" / f"{episode_slug}_start-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["status"] = "awaiting_cover_selection"
    manifest["spotify_cover_options"] = [str(path) for path in option_paths]
    manifest["spotify_cover_contact_sheet"] = str(contact_sheet)
    manifest["next_step"] = "Show the 3 Spotify cover options to the user and wait for cover selection."
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Spotify cover variants for one episode.")
    parser.add_argument("--episode-slug", required=True)
    parser.add_argument("--episode-id", required=True)
    parser.add_argument("--artist-name", required=True)
    parser.add_argument("--qr-target", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_dir = ROOT / "input" / args.episode_slug
    output_dir = ROOT / "output" / args.episode_slug / "spotify"
    logo_path = resolve_logo()
    paintings = sorted(input_dir.iterdir())
    option_paths: list[Path] = []
    for idx, painting in enumerate(paintings[:3], start=1):
        out_path = output_dir / f"{args.episode_slug}_spotify_cover_option_{idx:02d}.jpg"
        make_cover(painting, logo_path, args.artist_name, args.qr_target, out_path)
        option_paths.append(out_path)
    contact_sheet = output_dir / f"{args.episode_slug}_spotify_cover_contact_sheet.jpg"
    make_contact_sheet(option_paths, contact_sheet)
    update_episode_status(args.episode_id, option_paths)
    update_manifest(args.episode_slug, option_paths, contact_sheet)
    print("\n".join(str(path) for path in option_paths + [contact_sheet]))


if __name__ == "__main__":
    main()
