#!/usr/bin/env python3
"""Generates the brand images (icon + logo, light + dark, 1x + 2x) for the integration.

Original artwork (a stylised kiln with a flame); it deliberately does NOT use the
ROHDE logo. Needs Pillow:  pip install pillow
Usage:  python3 tools/make_brand.py
Output: custom_components/rohde_mykiln/brand/

Tweak WORDMARK, the colours or the shapes below and run it again.
"""
from __future__ import annotations

import os
from PIL import Image, ImageDraw, ImageFont

WORDMARK = "Kiln"
SS = 4  # supersampling factor for smooth edges

FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
)

SCHEMES = {
    # name: body, frame, interior, text
    "light": dict(body="#455A64", frame="#37474F", interior="#1C2429", text="#37474F"),
    "dark": dict(body="#CFD8DC", frame="#ECEFF1", interior="#263238", text="#ECEFF1"),
}
FLAME = dict(outer="#F4511E", mid="#FFA000", core="#FFE082")

OUT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "custom_components", "rohde_mykiln", "brand",
)


def bezier(p0, p1, p2, p3, n=40):
    pts = []
    for i in range(n + 1):
        t = i / n
        a, b, c, d = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t**2, t**3
        pts.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0],
                    a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    return pts


def flame_points(cx, base_y, h, w):
    """Closed flame outline. Profile is given in units of half-width / height."""
    def P(dx, dy):
        return (cx + dx * w / 2, base_y + dy * h)

    pts = []
    pts += bezier(P(0, 0), P(-0.75, 0), P(-0.75, -0.5), P(-0.18, -0.62))     # left belly
    pts += bezier(P(-0.18, -0.62), P(0.02, -0.72), P(-0.02, -0.9), P(0.14, -1.0))  # to tip
    pts += bezier(P(0.14, -1.0), P(0.22, -0.82), P(0.80, -0.72), P(0.74, -0.32))    # right shoulder
    pts += bezier(P(0.74, -0.32), P(0.70, -0.08), P(0.42, 0), P(0, 0))              # right belly
    return pts


def draw_icon(d: ImageDraw.ImageDraw, k: float, ox: float, oy: float, scheme: dict):
    """Draw the 512x512 design scaled by k with offset (ox, oy)."""
    def X(v): return ox + v * k
    def Y(v): return oy + v * k

    def rect(x0, y0, x1, y1): return [X(x0), Y(y0), X(x1), Y(y1)]

    # kiln body: dome + cabinet + feet
    d.ellipse(rect(76, 40, 436, 400), fill=scheme["body"])
    d.rounded_rectangle(rect(76, 220, 436, 440), radius=36 * k, fill=scheme["body"],
                        corners=(False, False, True, True))
    for fx in (112, 340):
        d.rounded_rectangle(rect(fx, 432, fx + 60, 470), radius=10 * k, fill=scheme["frame"])
    # spy hole in the lid
    d.ellipse(rect(240, 80, 272, 112), fill=scheme["frame"])
    # door frame + opening
    d.ellipse(rect(144, 188, 368, 412), fill=scheme["frame"])
    d.rectangle(rect(144, 300, 368, 418), fill=scheme["frame"])
    d.ellipse(rect(160, 204, 352, 396), fill=scheme["interior"])
    d.rectangle(rect(160, 300, 352, 408), fill=scheme["interior"])
    # flame (three nested layers)
    for scale, colour, lift in ((1.0, FLAME["outer"], 0), (0.66, FLAME["mid"], 4), (0.36, FLAME["core"], 8)):
        pts = flame_points(256, 404 - lift, 150 * scale, 112 * scale)
        d.polygon([(X(x), Y(y)) for x, y in pts], fill=colour)


def render_icon(px: int, scheme_name: str) -> Image.Image:
    big = px * SS
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    draw_icon(ImageDraw.Draw(img), big / 512, 0, 0, SCHEMES[scheme_name])
    return img.resize((px, px), Image.LANCZOS)


def find_font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    raise SystemExit("No bold font found; add one to FONT_CANDIDATES")


def render_logo(height: int, scheme_name: str) -> Image.Image:
    """Icon + wordmark on one line, trimmed to its content."""
    scheme = SCHEMES[scheme_name]
    big_h = height * SS
    font = find_font(int(big_h * 0.62))
    probe = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    left, top, right, bottom = probe.textbbox((0, 0), WORDMARK, font=font)
    text_w, text_h = right - left, bottom - top
    gap = int(big_h * 0.06)
    width = big_h + gap + text_w + int(big_h * 0.04)
    img = Image.new("RGBA", (width, big_h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    draw_icon(d, big_h / 512, 0, 0, scheme)
    d.text((big_h + gap - left, (big_h - text_h) / 2 - top + big_h * 0.02), WORDMARK,
           font=font, fill=scheme["text"])
    img = img.crop(img.getbbox())  # trim transparent borders
    scale = height / img.height
    return img.resize((max(1, round(img.width * scale)), height), Image.LANCZOS)


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    for name in ("light", "dark"):
        prefix = "" if name == "light" else "dark_"
        render_icon(256, name).save(os.path.join(OUT, f"{prefix}icon.png"), optimize=True)
        render_icon(512, name).save(os.path.join(OUT, f"{prefix}icon@2x.png"), optimize=True)
        render_logo(128, name).save(os.path.join(OUT, f"{prefix}logo.png"), optimize=True)
        render_logo(256, name).save(os.path.join(OUT, f"{prefix}logo@2x.png"), optimize=True)
    print("Wrote", sorted(os.listdir(OUT)))


if __name__ == "__main__":
    main()
