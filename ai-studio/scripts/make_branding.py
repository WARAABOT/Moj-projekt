"""Izradi logo i bannere kanala u mapi branding/.

Pokretanje: python scripts/make_branding.py "Byte Crew" "AI tools & tech tips · new videos every day"
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = Path(__file__).resolve().parent.parent / "branding"
NAME = sys.argv[1] if len(sys.argv) > 1 else "Byte Crew"
TAGLINE = sys.argv[2] if len(sys.argv) > 2 else "AI tools & tech tips · new videos every day"

BG = (7, 4, 15)
PINK, CYAN, VIOLET = (255, 43, 214), (0, 229, 255), (138, 60, 255)
FONTS = ["/usr/share/fonts/opentype/inter/Inter-Black.otf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]

# isti likovi kao na ploči (web/app.js)
BODY = [".SSSSSSSSSS.", ".SSEESSEESS.", ".SSSSSSSSSS.", "..SSSMMSSS..", "...SSSSSS...",
        "..TTTTTTTT..", ".TTTTTTTTTT.", "STTTTTTTTTTS", "STTTTTTTTTTS"]
HAIR = {"short": ["..HHHHHHHH..", ".HHHHHHHHHH.", ".HHSSSSSSHH."],
        "long": ["..HHHHHHHH..", ".HHHHHHHHHH.", "HHHSSSSSSHHH"],
        "cap": ["..CCCCCCCC..", ".CCCCCCCCCCCC", ".HHSSSSSSHH."]}
CREW = [  # boja, kosa, koža, majica, frizura
    ("#00e5ff", "#2b1a0e", "#f2c39b", "#00b8d4", "cap"), ("#ffd400", "#5b2a86", "#ffd8b5", "#ff9f1a", "long"),
    ("#ff3b5c", "#111111", "#c98b62", "#e0244a", "short"), ("#ff7a1a", "#ff5a1f", "#f5c9a4", "#ffb800", "long"),
    ("#18ff8a", "#1d6b3a", "#8d5a3b", "#12c46b", "cap"), ("#ff2bd6", "#2a0f3d", "#ffd8b5", "#d91fb5", "short"),
    ("#4d9dff", "#3a2414", "#e8b48a", "#2f6fff", "short"), ("#b06bff", "#ff8a00", "#f7cfae", "#8a3cff", "long"),
]
# robot za logo (16x16)
ROBOT = [
    ".......AA.......", ".......PP.......", "...MMMMMMMMMM...", "..MCCCCCCCCCCM..",
    "..MCKKKCCKKKCM..", "..MCKEKCCKEKCM..", "..MCKKKCCKKKCM..", "..MCCCCCCCCCCM..",
    "..MCCPPPPPPCCM..", "..MCCCCCCCCCCM..", "...MMMMMMMMMM...", ".....MMMMMM.....",
    "...VVVVVVVVVV...", "..VVVVVVVVVVVV..", "..VV.VVVVVV.VV..", "..VV.VVVVVV.VV..",
]


def font(size):
    for f in FONTS:
        if Path(f).exists():
            return ImageFont.truetype(f, size)
    return ImageFont.load_default(size)


def pixels(rows, colors, px):
    w = max(len(r) for r in rows)
    img = Image.new("RGBA", (w * px, len(rows) * px), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            if ch in colors:
                d.rectangle([x * px, y * px, (x + 1) * px - 1, (y + 1) * px - 1], fill=colors[ch])
    return img


def crew_member(i, px):
    c, hair, skin, shirt, style = CREW[i]
    rows = HAIR[style] + BODY
    if style == "long":
        rows = rows[:4] + ["HSSEESSEESSH", "HSSSSSSSSSSH"] + rows[6:]
    return pixels(rows, {"H": hair, "S": skin, "E": "#1a1030", "M": "#b8456b", "T": shirt, "C": c}, px)


def glow(base, layer, radius, strength=2):
    g = layer.filter(ImageFilter.GaussianBlur(radius))
    for _ in range(strength):
        base = Image.alpha_composite(base, g)
    return Image.alpha_composite(base, layer)


def gradient_bg(w, h):
    img = Image.new("RGBA", (w, h), BG + (255,))
    spot = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(spot)
    d.ellipse([w * 0.15, -h * 0.6, w * 0.85, h * 0.7], fill=(60, 20, 130, 120))
    d.ellipse([w * 0.6, h * 0.5, w * 1.2, h * 1.5], fill=(255, 43, 214, 40))
    return Image.alpha_composite(img, spot.filter(ImageFilter.GaussianBlur(min(w, h) // 5)))


def logo(size=1024):
    img = gradient_bg(size, size)
    ring = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(ring)
    m = size // 14
    d.ellipse([m, m, size - m, size - m], outline=PINK + (255,), width=size // 60)  # krug: profilne slike se režu u krug
    img = glow(img, ring, size // 40)
    bot = pixels(ROBOT, {"A": "#ffd400", "P": "#ff2bd6", "M": "#8a3cff", "C": "#1a1033", "K": "#00e5ff",
                         "E": "#ffffff", "V": "#5b2cc4"}, size // 26)
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    layer.paste(bot, ((size - bot.width) // 2, (size - bot.height) // 2 - size // 40), bot)
    return glow(img, layer, size // 50, 1)


def wordmark(draw_on, text, center, size, color=PINK):
    layer = Image.new("RGBA", draw_on.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    f = font(size)
    w = d.textlength(text, font=f)
    x, y = center[0] - w / 2, center[1] - size / 2
    d.text((x, y), text, font=f, fill=color + (255,), stroke_width=size // 10, stroke_fill=color + (255,))
    out = Image.alpha_composite(draw_on, layer.filter(ImageFilter.GaussianBlur(size // 6)))
    d2 = ImageDraw.Draw(out)
    d2.text((x, y), text, font=f, fill="white", stroke_width=max(2, size // 25), stroke_fill=(30, 0, 50))
    return out


def banner(w, h, safe_h, crew_px):
    img = gradient_bg(w, h)
    cy = h // 2
    img = wordmark(img, NAME.upper(), (w // 2, cy - safe_h // 6), safe_h // 3)
    d = ImageDraw.Draw(img)
    f = font(max(18, safe_h // 11))
    tw = d.textlength(TAGLINE, font=f)
    d.text(((w - tw) / 2, cy + safe_h // 8), TAGLINE, font=f, fill=CYAN)
    # tim lijevo i desno od teksta
    people = [crew_member(i, crew_px) for i in range(8)]
    pw = people[0].width
    gap = pw // 3
    row_w = 4 * pw + 3 * gap
    text_half = max(d.textlength(NAME.upper(), font=font(safe_h // 3)), tw) / 2
    for side, group in ((-1, people[:4]), (1, people[4:])):
        x0 = w // 2 + side * (text_half + gap * 2) - (row_w if side < 0 else 0)
        for k, p in enumerate(group):
            layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
            layer.paste(p, (int(x0 + k * (pw + gap)), cy - p.height // 2), p)
            img = glow(img, layer, crew_px, 1)
    return img


def main():
    OUT.mkdir(exist_ok=True)
    lg = logo()
    lg.convert("RGB").save(OUT / "logo.png")
    lg.resize((400, 400), Image.LANCZOS).convert("RGB").save(OUT / "logo-400.png")
    # YouTube: 2560x1440, sve bitno u sredini 1546x423 (vidi se i na mobitelu)
    banner(2560, 1440, 423, 9).convert("RGB").save(OUT / "youtube-banner.png")
    # X/Twitter i Facebook naslovna
    banner(1500, 500, 380, 6).convert("RGB").save(OUT / "header-1500x500.png")
    print("Spremljeno u", OUT)


if __name__ == "__main__":
    main()
