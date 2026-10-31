"""Transparent PNG overlays for the clip (this ffmpeg build has no drawtext filter)."""

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = int(sys.argv[2]), int(sys.argv[2]) * 9 // 16
out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)


def font(size):
    for path in ("/System/Library/Fonts/HelveticaNeue.ttc", "/System/Library/Fonts/Helvetica.ttc"):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def glass_tag(text, accent):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f = font(H // 26)
    width = int(d.textlength(text, font=f)) + 70
    box = (W // 30, H // 18, W // 30 + width, H // 18 + H // 14)
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(box, 14, fill=(0, 0, 0, 120))
    img = Image.alpha_composite(img, shadow.filter(ImageFilter.GaussianBlur(10)))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(box, 14, fill=(20, 26, 40, 165), outline=(255, 255, 255, 90), width=2)
    d.rectangle((box[0] + 14, box[1] + 14, box[0] + 20, box[3] - 14), fill=accent)
    d.text((box[0] + 36, (box[1] + box[3]) // 2), text, font=f, fill=(255, 255, 255, 255),
           anchor="lm")
    return img


glass_tag("◀◀  REPLAY", (255, 210, 63, 255)).save(out / "replay_tag.png")
glass_tag("3D REPLAY · 1/3 SPEED", (255, 210, 63, 255)).save(out / "replay3d_tag.png")
glass_tag("● LIVE · ball hidden, model tracking", (255, 59, 59, 255)).save(out / "live_tag.png")
print("overlays written")
