import sys
from PIL import Image
from pathlib import Path

renders = Path(r"D:\gehub\twin28xx\review\renders")
crops = Path(r"D:\gehub\twin28xx\review\crops")
crops.mkdir(exist_ok=True)

# 3D top/bottom: 3200x1600. Crop into 6 tiles (3 cols x 2 rows) so each crop is 1067x800.
# But the board itself doesn't fill the full image — there's grey background padding.
# So first compute the actual board bounding box in the image. Eyeballing top_3d.png:
# board occupies roughly x:[420, 2780], y:[200, 1380] of 3200x1600.

def tile(src_name: str, x0: int, y0: int, x1: int, y1: int, cols: int, rows: int, prefix: str):
    img = Image.open(renders / src_name)
    bw = x1 - x0
    bh = y1 - y0
    cw = bw // cols
    rh = bh // rows
    for r in range(rows):
        for c in range(cols):
            cx0 = x0 + c * cw
            cy0 = y0 + r * rh
            cx1 = x0 + (c + 1) * cw if c < cols - 1 else x1
            cy1 = y0 + (r + 1) * rh if r < rows - 1 else y1
            tile_img = img.crop((cx0, cy0, cx1, cy1))
            out = crops / f"{prefix}_r{r}c{c}.png"
            tile_img.save(out, "PNG", optimize=True)
            print(f"  {out.name}: {tile_img.size}")

# Top: 3 cols x 2 rows
print("TOP tiles:")
tile("top_3d.png", 420, 200, 2780, 1380, 3, 2, "top")

# Bottom: same crop  (same image dims)
print("BOTTOM tiles:")
tile("bottom_3d.png", 420, 200, 2780, 1380, 3, 2, "bot")
