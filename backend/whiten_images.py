"""Turn the black photo backgrounds white. The original photos are never touched.

Many product photos were saved from transparent images, so their background came out black
(or black bars down the sides). This finds black areas that touch the edge of the picture and
paints them white, with a soft edge so the garment doesn't look cut out with scissors. Results go
to data/products-white/, and the API serves those first.

Run it once (needs the image libraries, which the website itself does not need):
    pip install pillow numpy scipy
    python whiten_images.py
"""

from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

DATA = Path(__file__).resolve().parent.parent / "data"
SRC = DATA / "products"
DST = DATA / "products-white"

BLACK = 24  # a pixel whose brightest color channel is at or below this counts as black
PURE_BLACK = 3  # background that is perfectly black, even in a gap that does not touch the edge
POCKET_MIN = 150  # such a gap (like under a sleeve) must be at least this many pixels big
POCKET_SIDE = 0.35  # and sit in the outer 35% on the left or right, so chest graphics are never touched
GROW = 2  # pixels to grow the white area, to swallow the dark fringe around the garment
SOFTEN = 0.9  # how soft the edge between garment and white is


def whiten(img: Image.Image) -> tuple[Image.Image, float]:
    """Return the picture with its black background made white, and the share of pixels changed."""
    rgb = np.asarray(img.convert("RGB")).astype(np.float32)
    black = rgb.max(axis=2) <= BLACK
    regions, _ = ndimage.label(black)  # groups of touching black pixels
    edge = np.concatenate([regions[0, :], regions[-1, :], regions[:, 0], regions[:, -1]])
    touching_edge = set(np.unique(edge)) - {0}
    if not touching_edge:
        return img.convert("RGB"), 0.0  # no black background: leave the photo alone
    background = np.isin(regions, list(touching_edge))
    # gaps enclosed by the garment (between an arm and the body) are background too, but only if they
    # are perfectly black and off to the side, so black lettering and dark fabric are left alone
    pure = rgb.max(axis=2) <= PURE_BLACK
    pockets, count = ndimage.label(pure)
    if count:
        ids = np.arange(1, count + 1)
        sizes = ndimage.sum(pure, pockets, index=ids)
        across = np.array(ndimage.center_of_mass(pure, pockets, index=ids))[:, 1] / pure.shape[1]
        side = (across < POCKET_SIDE) | (across > 1 - POCKET_SIDE)
        gaps = np.isin(pockets, ids[(sizes >= POCKET_MIN) & side])
        # take the whole dark area around each gap, including its slightly-less-than-black edges
        whole = set(np.unique(regions[gaps])) - {0}
        background |= np.isin(regions, list(whole))
    share = float(background.mean())
    wide = ndimage.binary_dilation(background, iterations=GROW)
    alpha = ndimage.gaussian_filter(wide.astype(np.float32), SOFTEN)[..., None]
    out = rgb * (1 - alpha) + 255.0 * alpha
    return Image.fromarray(out.round().astype(np.uint8)), share


def main() -> None:
    DST.mkdir(exist_ok=True)
    changed = 0
    for path in sorted(SRC.glob("*.jpg")):
        result, share = whiten(Image.open(path))
        result.save(DST / path.name, quality=93)
        if share > 0:
            changed += 1
        print(f"{path.name:70} background {share:5.0%}")
    print(f"\n{changed} photos had a black background; all {len(list(SRC.glob('*.jpg')))} saved to {DST}")


if __name__ == "__main__":
    main()
