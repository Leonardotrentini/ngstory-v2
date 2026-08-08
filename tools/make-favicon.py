"""Gera favicon.ico e favicon.png a partir do emblema circular da logo."""
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "negaostory-logo-source.png")


def main() -> None:
    src = Image.open(SOURCE).convert("RGB")
    px = src.load()

    rows = {}
    for y in range(40, 220):
        xs = [x for x in range(src.width) if sum(px[x, y]) < 720]
        if xs:
            rows[y] = (min(xs), max(xs))

    ys = sorted(rows)
    x0 = min(v[0] for v in rows.values())
    x1 = max(v[1] for v in rows.values())
    cx, cy = (x0 + x1) // 2, (ys[0] + ys[-1]) // 2
    side = max(x1 - x0, ys[-1] - ys[0]) + 10
    emblem = src.crop((cx - side // 2, cy - side // 2, cx + side // 2, cy + side // 2))

    png_path = os.path.join(ROOT, "favicon.png")
    ico_path = os.path.join(ROOT, "favicon.ico")
    apple = emblem.resize((180, 180), Image.LANCZOS)
    apple.quantize(colors=64, method=Image.MEDIANCUT, dither=Image.NONE).save(
        png_path, optimize=True
    )
    emblem.save(ico_path, sizes=[(16, 16), (32, 32), (48, 48)])

    print(f"emblema {emblem.size} de {SOURCE}")
    print(f"favicon.png {os.path.getsize(png_path) / 1024:.1f} KiB")
    print(f"favicon.ico {os.path.getsize(ico_path) / 1024:.1f} KiB")


if __name__ == "__main__":
    main()
