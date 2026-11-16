"""Designer: naslovna slika (kadar iz videa + veliki neonski tekst)."""
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

FONTS = [
    "/usr/share/fonts/opentype/inter/Inter-Black.otf",
    "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def _font(size: int):
    for f in FONTS:
        if Path(f).exists():
            return ImageFont.truetype(f, size)
    return ImageFont.load_default(size)


def make(frame: Path, text: str, out: Path, accent=(255, 43, 214)) -> Path:
    img = Image.open(frame).convert("RGB").resize((1080, 1920))
    img = ImageEnhance.Brightness(img).enhance(0.55)
    font = _font(150)
    lines = textwrap.wrap(text.upper(), width=10)[:4]
    draw = ImageDraw.Draw(img)
    heights = [draw.textbbox((0, 0), ln, font=font)[3] for ln in lines]
    y = (1920 - sum(heights) - 30 * len(lines)) // 2

    # sjaj: isti tekst u boji, zamućen, ispod bijelog teksta
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    pos = []
    for ln, h in zip(lines, heights):
        w = draw.textlength(ln, font=font)
        pos.append(((1080 - w) / 2, y))
        gd.text(((1080 - w) / 2, y), ln, font=font, fill=accent + (255,), stroke_width=14, stroke_fill=accent + (255,))
        y += h + 30
    glow = glow.filter(ImageFilter.GaussianBlur(18))
    img = Image.alpha_composite(img.convert("RGBA"), glow)
    draw = ImageDraw.Draw(img)
    for (x, yy), ln in zip(pos, lines):
        draw.text((x, yy), ln, font=font, fill="white", stroke_width=6, stroke_fill=(20, 0, 40))
    img.convert("RGB").save(out, quality=90)
    return out
