"""Read the ECHS login CAPTCHA automatically.

The CAPTCHA is 6 coloured letters/digits on a light background, and the server
checks it case-sensitively. ddddocr reads the characters well but often gets
the case wrong for letters whose upper and lower case look the same apart from
size (c/C, o/O, s/S, x/X ...). Those are fixed by measuring each character's
height: in this CAPTCHA, capitals and digits are ~22px tall, lowercase ~16px.
"""
from collections import deque
from io import BytesIO

import ddddocr
import numpy as np
from PIL import Image
from playwright.sync_api import Page

CAPTCHA_IMAGE = "#img_captcha"
CAPTCHA_LENGTH = 6

# x-height lowercase: lowercase me CHHOTE, uppercase me TALL -> height se case pakka.
SIZE_ONLY_CASE = set("acemnorsuvwxz")
# descenders: lowercase me baseline ke NEECHE latakte hain -> position se case.
DESCENDER_CASE = set("gjpqy")
# in ascenders ka uppercase TOP chaura hota hai (b/d/h) -> top-width se case; k,l,t,f chhode (OCR ka case rakho).
TOPWIDE_CASE = set("bdh")

_ocr = None


def _get_ocr():
    global _ocr
    if _ocr is None:
        _ocr = ddddocr.DdddOcr(show_ad=False)
    return _ocr


def _colour_labels(img: np.ndarray) -> np.ndarray:
    """0 = background, 1 = black ink, 2/3/4 = red/green/blue ink."""
    mx, mn = img.max(-1), img.min(-1)
    labels = np.zeros(img.shape[:2], dtype=np.int8)
    coloured = (mx - mn) > 100
    labels[coloured] = img.argmax(-1)[coloured] + 2
    labels[mx < 100] = 1
    return labels


def _glyph_boxes(labels: np.ndarray) -> list[tuple[int, int, int, int]]:
    """Bounding boxes (x0, x1, y0, y1) of characters, left to right.

    Uses connected components per colour, so neighbouring characters of
    different colours are separated even when they touch.
    """
    h, w = labels.shape
    seen = np.zeros_like(labels, dtype=bool)
    boxes = []
    for y in range(h):
        for x in range(w):
            lab = labels[y, x]
            if lab == 0 or seen[y, x]:
                continue
            q = deque([(y, x)])
            seen[y, x] = True
            area, x0, x1, y0, y1 = 0, x, x, y, y
            while q:
                cy, cx = q.popleft()
                area += 1
                x0, x1, y0, y1 = min(x0, cx), max(x1, cx), min(y0, cy), max(y1, cy)
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = cy + dy, cx + dx
                        if 0 <= ny < h and 0 <= nx < w and not seen[ny, nx] and labels[ny, nx] == lab:
                            seen[ny, nx] = True
                            q.append((ny, nx))
            if area >= 15:  # ignore background speckles
                boxes.append([x0, x1, y0, y1])

    # Merge pieces that sit in the same column (e.g. the dot of an i or j).
    boxes.sort()
    merged = []
    for b in boxes:
        if merged:
            m = merged[-1]
            overlap = min(m[1], b[1]) - max(m[0], b[0])
            if overlap > 0.5 * min(m[1] - m[0], b[1] - b[0]):
                m[:] = [min(m[0], b[0]), max(m[1], b[1]), min(m[2], b[2]), max(m[3], b[3])]
                continue
        merged.append(b)
    return [tuple(b) for b in merged]


def _box_from_columns(ink: np.ndarray, x0: int, x1: int) -> list[int] | None:
    rows = np.where(ink[:, x0:x1 + 1].any(1))[0]
    if rows.size == 0:
        return None
    return [x0, x1, int(rows[0]), int(rows[-1])]


def _split_merged(boxes: list, ink: np.ndarray, wanted: int) -> list:
    """Split boxes that hold two touching characters of the same colour.

    The widest box is cut at its thinnest column (fewest ink pixels) near the
    middle, until there are as many boxes as characters.
    """
    boxes = [list(b) for b in boxes]
    while len(boxes) < wanted:
        i = max(range(len(boxes)), key=lambda k: boxes[k][1] - boxes[k][0])
        x0, x1, *_ = boxes[i]
        width = x1 - x0
        lo, hi = x0 + int(width * 0.3), x0 + int(width * 0.7)
        if hi <= lo:
            break
        cut = lo + int(np.argmin(ink[:, lo:hi + 1].sum(0)))
        # Leave a 2px margin either side of the cut so the neighbour's edge
        # doesn't inflate the measured height.
        left = _box_from_columns(ink, x0, max(x0, cut - 2))
        right = _box_from_columns(ink, min(x1, cut + 2), x1)
        if left is None or right is None:
            break
        boxes[i:i + 1] = [left, right]
    return boxes


def _top_width_ratio(ink: np.ndarray, box) -> float:
    """Top 30% band me ink kitni chaudi hai (0..1). Uppercase (B/D/H) chaura, lowercase patla."""
    x0, x1, y0, y1 = box
    sub = ink[y0:y1 + 1, x0:x1 + 1]
    band = sub[:max(1, int(0.30 * (y1 - y0 + 1))), :]
    cols = np.where(band.any(0))[0]
    return ((cols[-1] - cols[0] + 1) / (x1 - x0 + 1)) if (cols.size and x1 > x0) else 0.0


def _fix_case(text: str, image_bytes: bytes) -> str:
    img = np.asarray(Image.open(BytesIO(image_bytes)).convert("RGB")).astype(int)
    labels = _colour_labels(img)
    ink = labels > 0
    boxes = _glyph_boxes(labels)
    if len(boxes) < len(text):
        boxes = _split_merged(boxes, ink, len(text))
    boxes = sorted((list(b) for b in boxes), key=lambda b: b[0])
    if len(boxes) != len(text):
        return text  # couldn't line characters up with boxes; keep OCR result

    heights = [y1 - y0 + 1 for _, _, y0, y1 in boxes]
    cap_height = float(max(heights))                 # tallest glyph = capital/digit height
    baseline = float(np.median([y1 for _, _, _, y1 in boxes]))

    fixed = []
    for ch, hgt, box in zip(text, heights, boxes):
        low = ch.lower()
        if ch.isdigit():
            pass
        elif low in SIZE_ONLY_CASE:
            ch = ch.upper() if hgt >= 0.82 * cap_height else ch.lower()
        elif low in DESCENDER_CASE:
            ch = ch.lower() if box[3] >= baseline + 4 else ch.upper()
        elif low in TOPWIDE_CASE:
            tw = _top_width_ratio(ink, box)
            if tw >= 0.55:
                ch = ch.upper()
            elif tw <= 0.40:
                ch = ch.lower()
        fixed.append(ch)
    return "".join(fixed)


def _on_white(image_bytes: bytes) -> bytes:
    """Transparent PNG ko white background par bitha do (ddddocr transparent par theek nahi padhta).
    Opaque image par iska koi asar nahi."""
    im = Image.open(BytesIO(image_bytes)).convert("RGBA")
    bg = Image.new("RGB", im.size, (255, 255, 255))
    bg.paste(im, mask=im.split()[-1])
    out = BytesIO()
    bg.save(out, "PNG")
    return out.getvalue()


def read_captcha(image_bytes: bytes) -> str:
    """Return the CAPTCHA text for an image (PNG/JPEG bytes)."""
    image_bytes = _on_white(image_bytes)
    text = _get_ocr().classification(image_bytes)
    text = "".join(ch for ch in text if ch.isalnum())
    return _fix_case(text, image_bytes)


def refresh(page: Page) -> None:
    """Ask the site for a new CAPTCHA image and wait for it to load."""
    old_src = page.get_attribute(CAPTCHA_IMAGE, "src")
    page.evaluate("getCaptcha('c')")
    page.wait_for_function(
        """([sel, old]) => { const i = document.querySelector(sel);
               return i && i.src !== old && i.complete && i.naturalWidth > 0; }""",
        arg=[CAPTCHA_IMAGE, old_src],
    )


def solve(page: Page, max_reads: int = 5) -> str:
    """Read the CAPTCHA currently shown on the page.

    If the OCR result doesn't have the expected length, a new CAPTCHA is
    requested and read again (up to max_reads times).
    """
    page.wait_for_function(
        "sel => { const i = document.querySelector(sel); return i && i.complete && i.naturalWidth > 0; }",
        arg=CAPTCHA_IMAGE,
    )
    for _ in range(max_reads):
        text = read_captcha(page.locator(CAPTCHA_IMAGE).screenshot())
        if len(text) == CAPTCHA_LENGTH:
            return text
        refresh(page)
    raise RuntimeError("Could not read the CAPTCHA.")
