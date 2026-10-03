"""Generate ``assets/icon.ico`` (16..256 px, all embedded) and ``assets/icon.png``.

The user's own branding is authoritative: ``assets/logo.png`` (a copy of ``Logo&icon/icon-2.png``)
is used whenever it is present, so the packaged EXE, the installer, the shortcuts and the Qt window
all show exactly the same artwork. The painted gradient below is only a last-resort fallback for a
checkout that somehow lost ``assets/logo.png``; it is never used to override the real logo.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
# Where the user's original artwork lives. ``assets/logo.png`` is the in-project copy used by builds;
# the repository-level ``Logo&icon/`` folder is the upstream source it was taken from.
SOURCES = (ASSETS / "logo.png", ROOT.parent / "Logo&icon" / "icon-2.png", ROOT.parent / "Logo&icon" / "icon.png")
SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
SIZE = 1024


def build() -> Image.Image:
    """Fallback artwork (only used if the user's branding asset is missing)."""
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    grad = Image.new("RGBA", (SIZE, SIZE))
    px = grad.load()
    for y in range(SIZE):
        for x in range(SIZE):
            t = (x + y) / (2 * SIZE)
            px[x, y] = (int(77 + (94 - 77) * t), int(163 + (92 - 163) * t), int(255 + (230 - 255) * t), 255)
    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, SIZE - 1, SIZE - 1), radius=int(SIZE * 0.22), fill=255)
    img.paste(grad, (0, 0), mask)
    d = ImageDraw.Draw(img)
    s = SIZE
    for box in ((0.22, 0.40, 0.54, 0.70), (0.38, 0.28, 0.72, 0.66), (0.55, 0.40, 0.79, 0.70)):
        d.ellipse([c * s for c in box], fill="white")
    d.rounded_rectangle((0.30 * s, 0.50 * s, 0.72 * s, 0.70 * s), radius=int(0.08 * s), fill="white")
    arrow = [(0.5, 0.40), (0.62, 0.54), (0.54, 0.54), (0.54, 0.66), (0.46, 0.66), (0.46, 0.54), (0.38, 0.54)]
    d.polygon([(x * s, y * s) for x, y in arrow], fill=(79, 125, 240, 255))
    return img


def master() -> tuple[Image.Image, Path | None]:
    for candidate in SOURCES:
        if candidate.exists():
            with Image.open(candidate) as im:
                img = im.convert("RGBA")
            largest = max(SIZES)[0]
            if img.width != largest:  # keep the largest embedded size pixel-exact
                img = img.resize((largest, largest), Image.LANCZOS)
            return img, candidate
    return build(), None


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    img, source = master()
    img.save(ASSETS / "icon.png")
    img.save(ASSETS / "icon.ico", sizes=SIZES)
    print("wrote", ASSETS / "icon.ico", "from", source or "built-in fallback artwork")


if __name__ == "__main__":
    main()
