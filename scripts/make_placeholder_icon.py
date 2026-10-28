"""Generate the provisional Flow icon source (a white 'F' monogram).

This is a placeholder so packaging has a complete icon set. Replace the output
with real branding and re-run:

    python scripts/make_placeholder_icon.py
    npx tauri icon src-tauri/icons/flow-source.png
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

SIZE = 1024
ACCENT = (22, 119, 255, 255)
WHITE = (255, 255, 255, 255)


def build() -> Image.Image:
    image = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # Rounded square background.
    draw.rounded_rectangle((0, 0, SIZE - 1, SIZE - 1), radius=220, fill=ACCENT)

    # Monogram "F" built from rounded bars (no font dependency).
    draw.rounded_rectangle((330, 230, 480, 800), radius=36, fill=WHITE)
    draw.rounded_rectangle((330, 230, 720, 380), radius=36, fill=WHITE)
    draw.rounded_rectangle((330, 460, 650, 600), radius=36, fill=WHITE)
    return image


def main() -> None:
    target = Path(__file__).resolve().parent.parent / "src-tauri" / "icons" / "flow-source.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    build().save(target)
    print(f"Wrote {target}")


if __name__ == "__main__":
    main()
