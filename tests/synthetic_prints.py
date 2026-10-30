"""Synthetic held-out scenes for automatic framing: known corners, varied backgrounds, angles, light and occlusion.

  python tests/synthetic_prints.py fronts OUT [seed] [prints] [others]   prints, plus scenes without one
  python tests/synthetic_prints.py backs OUT [seed] [count]              backs of prints (no picture window)
  python tests/synthetic_prints.py eval OUT [OUT ...]                    run the app's detection and tally

A print is a crop of a fixture photo inside a card with one film's border proportions (±0.5%), warped onto wood,
paper, fabric, a dark surface or clutter with perspective, a lighting gradient, blur, noise and sometimes a thumb
over a corner. Scenes without a print hold a borderless photo, a blank sheet or a card-like rectangle. A back is a
plain dark or light card with some printed words. docs/scan-validation.md reports fronts with seeds 7 and 1234
(90 prints + 40 others each) and backs with seeds 99 and 2024 (50 each).
Needs OpenCV, NumPy and Pillow; eval also needs Playwright and a built 相角.html.
"""
import base64
import json
import math
import random
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
EDGES = {"mini": ([.074, .081, .074, .198], 54 / 86), "square": ([.069, .081, .069, .198], 72 / 86), "wide": ([.042, .081, .042, .198], 108 / 86),
         "polaroid": ([.058, .06, .058, .216], 88 / 107), "go": ([.064, .068, .064, .242], 53.9 / 66.6)}
read = lambda p: cv2.imdecode(np.fromfile(str(p), np.uint8), cv2.IMREAD_COLOR)   # imread cannot open non-ASCII paths on Windows
# Plain picture content only: crops from inside real photos (never a whole scan, which would bring its own white border)
photos = []
for p in sorted((ROOT / "tests/fixtures/real-prints").glob("*.jpg")):
    im = read(p); h, w = im.shape[:2]
    for fx, fy in ((.3, .3), (.2, .35), (.4, .25)):
        photos.append(im[int(h * fy):int(h * (fy + .4)), int(w * fx):int(w * (fx + .4))])


def background(W, H):
    kind = random.choice(["wood", "paper", "fabric", "dark", "clutter"])
    if kind == "wood":
        base = np.array(random.choice([(60, 80, 110), (40, 55, 75), (90, 120, 150)]), np.float32)
        y = np.arange(H)[:, None]; x = np.arange(W)[None, :]
        stripes = np.sin(y / random.uniform(6, 14) + 3 * np.sin(x / random.uniform(80, 200))) * 18
        img = base[None, None, :] + stripes[..., None] + np.random.normal(0, 6, (H, W, 1))
    elif kind == "paper":
        base = np.array(random.choice([(205, 222, 235), (215, 225, 230), (230, 232, 233)]), np.float32)
        img = base[None, None, :] + np.random.normal(0, 3, (H, W, 3))
    elif kind == "fabric":
        base = np.array([random.randint(60, 200) for _ in range(3)], np.float32)
        x = np.arange(W)[None, :]; y = np.arange(H)[:, None]
        img = base[None, None, :] + (np.sin(x / 3) * np.sin(y / 3) * 14)[..., None] + np.random.normal(0, 5, (H, W, 3))
    elif kind == "dark":
        img = np.full((H, W, 3), random.randint(18, 50), np.float32) + np.random.normal(0, 4, (H, W, 3))
    else:
        img = np.full((H, W, 3), random.randint(90, 170), np.float32)
        for _ in range(random.randint(6, 14)):
            c = [random.randint(0, 255) for _ in range(3)]; x0, y0 = random.randint(-100, W), random.randint(-100, H)
            if random.random() < .5: cv2.rectangle(img, (x0, y0), (x0 + random.randint(40, 300), y0 + random.randint(40, 300)), c, -1)
            else: cv2.circle(img, (x0, y0), random.randint(20, 120), c, -1)
    return kind, img


def card(fmt, long=900):
    (l, t, r, b), aspect = EDGES[fmt]
    l, t, r, b = [v + random.uniform(-.005, .005) for v in (l, t, r, b)]
    Hc = long if aspect < 1 else int(long / aspect); Wc = int(Hc * aspect)
    paper = np.array(random.choice([(246, 247, 248), (235, 240, 242), (226, 236, 240)]), np.float32)
    img = np.empty((Hc, Wc, 3), np.float32); img[:] = paper
    img += np.random.normal(0, 1.5, img.shape)
    x0, y0, x1, y1 = int(l * Wc), int(t * Hc), int(Wc * (1 - r)), int(Hc * (1 - b))
    ph = random.choice(photos); pw, phh = x1 - x0, y1 - y0
    sh, sw = ph.shape[:2]; k = max(pw / sw, phh / sh); res = cv2.resize(ph, (int(sw * k) + 1, int(sh * k) + 1))
    oy, ox = (res.shape[0] - phh) // 2, (res.shape[1] - pw) // 2
    img[y0:y1, x0:x1] = res[oy:oy + phh, ox:ox + pw]
    return img, Wc, Hc, (x0, y0, x1, y1)


def back(fmt, long=900):
    (l, t, r, b), aspect = EDGES[fmt]
    Hc = long if aspect < 1 else int(long / aspect); Wc = int(Hc * aspect)
    tone = random.choice([(40, 40, 42), (28, 30, 34), (225, 228, 230), (60, 58, 56)])
    img = np.full((Hc, Wc, 3), tone, np.uint8)
    ink = (200, 200, 200) if tone[0] < 128 else (60, 60, 60)
    for _ in range(random.randint(2, 6)):
        cv2.putText(img, random.choice(["instax", "FUJIFILM", "Polaroid", "Made in Japan", "ISO 800"]), (random.randint(10, Wc // 2), random.randint(40, Hc - 20)), cv2.FONT_HERSHEY_SIMPLEX, random.uniform(.8, 1.6), ink, 2)
    return img.astype(np.float32) + np.random.normal(0, 2, (Hc, Wc, 3)), Wc, Hc


def place(scene, src, Wc, Hc):
    H, W = scene.shape[:2]
    size = random.uniform(.3, .85) * min(W, H); k = size / max(Wc, Hc)
    ang = random.uniform(0, 2 * math.pi) if random.random() < .5 else random.uniform(-.35, .35)
    cx, cy = random.uniform(.35, .65) * W, random.uniform(.35, .65) * H
    base = [(-Wc / 2, -Hc / 2), (Wc / 2, -Hc / 2), (Wc / 2, Hc / 2), (-Wc / 2, Hc / 2)]
    dst = []
    for x, y in base:
        x, y = x * k, y * k; jit = .07 * size
        X = cx + x * math.cos(ang) - y * math.sin(ang) + random.uniform(-jit, jit)
        Y = cy + x * math.sin(ang) + y * math.cos(ang) + random.uniform(-jit, jit)
        dst.append((X, Y))
    M = cv2.getPerspectiveTransform(np.float32([(0, 0), (Wc, 0), (Wc, Hc), (0, Hc)]), np.float32(dst))
    warped = cv2.warpPerspective(src, M, (W, H), flags=cv2.INTER_LINEAR)
    mask = cv2.warpPerspective(np.ones((Hc, Wc), np.float32), M, (W, H))[..., None]
    # a soft drop shadow
    shadow = cv2.GaussianBlur(cv2.warpPerspective(np.ones((Hc, Wc), np.float32), M, (W, H)), (0, 0), 6)[..., None]
    scene = scene * (1 - .25 * np.roll(shadow, (4, 4), (0, 1)))
    return scene * (1 - mask) + warped * mask, dst, M


def finish(img):
    H, W = img.shape[:2]
    g = np.linspace(random.uniform(.75, 1), random.uniform(.9, 1.1), W)[None, :, None] * np.linspace(random.uniform(.85, 1), random.uniform(.9, 1.05), H)[:, None, None]
    img = img * g + np.random.normal(0, random.uniform(1, 4), img.shape)
    if random.random() < .4: img = cv2.GaussianBlur(img, (0, 0), random.uniform(.5, 1.2))
    return np.clip(img, 0, 255).astype(np.uint8)


def thumb(img, quad):
    i = random.randrange(4); p = np.array(quad[i]); c = np.mean(quad, axis=0); q = p + (c - p) * .12
    axes = (int(np.linalg.norm(c - p) * .22), int(np.linalg.norm(c - p) * .12))
    cv2.ellipse(img, (int(q[0]), int(q[1])), axes, random.uniform(0, 180), 0, 360, (150, 170, 215), -1)


def save(out, name, img):
    cv2.imencode(".jpg", finish(img), [cv2.IMWRITE_JPEG_QUALITY, 90])[1].tofile(str(out / name))


def fronts(out, prints=60, others=30):
    labels = {}
    for n in range(prints):
        W, H = random.choice([(1200, 900), (900, 1200), (1200, 800), (1100, 1100)])
        kind, scene = background(W, H)
        fmt = random.choice(list(EDGES))
        src, Wc, Hc, (x0, y0, x1, y1) = card(fmt)
        scene, quad, Mx = place(scene, src, Wc, Hc)
        win = cv2.perspectiveTransform(np.float32([[(x0, y0), (x1, y0), (x1, y1), (x0, y1)]]), Mx)[0].tolist()
        occl = random.random() < .2
        if occl: thumb(scene, quad)
        name = f"pos-{n:03d}-{fmt}-{kind}{'-thumb' if occl else ''}.jpg"
        save(out, name, scene)
        labels[name] = {"prints": [{"format": fmt, "quad": [[round(x, 1), round(y, 1)] for x, y in quad], "window": [[round(x, 1), round(y, 1)] for x, y in win]}]}
    for n in range(others):
        W, H = random.choice([(1200, 900), (900, 1200)])
        kind, scene = background(W, H)
        what = random.choice(["photo", "sheet", "cardlike"])
        if what == "photo":
            ph = random.choice(photos); Wc, Hc = 900, int(900 * ph.shape[0] / ph.shape[1]); src = cv2.resize(ph, (Wc, Hc)).astype(np.float32)
        elif what == "sheet":
            Wc, Hc = 800, random.choice([1130, 1000, 600]); src = np.full((Hc, Wc, 3), random.choice([238, 245, 230]), np.float32) + np.random.normal(0, 2, (Hc, Wc, 3))
        else:
            Wc, Hc = 630, 880; src8 = np.full((Hc, Wc, 3), 240, np.uint8)
            for _ in range(8):
                x, y = random.randint(60, 520), random.randint(60, 760); cv2.putText(src8, random.choice("AKQJ1098"), (x, y), cv2.FONT_HERSHEY_SIMPLEX, 3, (40, 40, 160), 6)
            src = src8.astype(np.float32)
        scene, quad, _ = place(scene, src, Wc, Hc)
        name = f"neg-{n:03d}-{what}-{kind}.jpg"
        save(out, name, scene)
        labels[name] = {"prints": []}
    return labels


def backs(out, count=40):
    labels = {}
    for n in range(count):
        W, H = random.choice([(1200, 900), (900, 1200), (1200, 800), (1100, 1100)])
        kind, scene = background(W, H)
        fmt = random.choice(list(EDGES))
        src, Wc, Hc = back(fmt)
        scene, quad, _ = place(scene, src, Wc, Hc)
        name = f"back-{n:03d}-{fmt}-{kind}.jpg"
        save(out, name, scene)
        labels[name] = {"format": fmt, "ratio": EDGES[fmt][1], "quad": [[round(x, 1), round(y, 1)] for x, y in quad]}
    return labels


FIND_CARD = """async ({name, data, ratio}) => {
  const bytes=Uint8Array.from(atob(data),c=>c.charCodeAt(0)),img=await decodeFile(new File([bytes],name,{type:'image/jpeg'}));
  const k=Math.min(1,2400/Math.max(img.width,img.height)),c=mkCv(Math.round(img.width*k),Math.round(img.height*k));c.getContext('2d').drawImage(img,0,0,c.width,c.height);
  const q=findCard(c,ratio);return q&&q.map(p=>[p[0]/k,p[1]/k]);
}"""


def evaluate(dirs):
    """Fronts go through the app's import detection (detect_report); backs through the back-side card search."""
    import detect_report as R
    from PIL import Image
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True); page = browser.new_page()
        page.goto((ROOT / "相角.html").as_uri()); page.wait_for_function("() => !restoring")
        for d in map(Path, dirs):
            labels = json.loads((d / "labels.json").read_text(encoding="utf-8")); tally, errors = {}, []
            for name, e in sorted(labels.items()):
                data = base64.b64encode((d / name).read_bytes()).decode()
                if "ratio" in e:   # a back: the right card in any orientation, within 4% of its diagonal
                    q, lab = page.evaluate(FIND_CARD, {"name": name, "data": data, "ratio": e["ratio"]}), e["quad"]
                    err = q and min(max(math.dist(a, b) for a, b in zip(q[k:] + q[:k], lab)) for k in range(4)) / R.diag(lab)
                    key = "back: none" if not q else "back: right card" if err <= R.TOLERANCE else "back: wrong card"
                else:
                    # A print counts only when its picture is inside the image; the expected frame is the card clipped to it.
                    W, H = Image.open(d / name).size
                    e = {"prints": [{**pr, "quad": [[min(max(x, 0), W), min(max(y, 0), H)] for x, y in pr["quad"]]}
                                    for pr in e["prints"] if all(0 <= x <= W and 0 <= y <= H for x, y in pr["window"])]}
                    R.LABELS = {name: e}
                    r = page.evaluate(R.DETECT, {"name": name, "data": data})
                    kind, err, format_ok = R.classify(name, r)
                    key = ("print: " if e["prints"] else "no print: ") + kind + (" (shown for confirmation)" if kind == "WRONG" and r["confirm"] else "") + (" (other film)" if kind in ("auto", "suggest") and not format_ok else "")
                    if kind == "auto": errors.append(err)
                tally[key] = tally.get(key, 0) + 1
            print(d.name, json.dumps(dict(sorted(tally.items())), ensure_ascii=False, indent=1))
            if errors:
                errors.sort(); print(f"  automatic corner error: median {errors[len(errors) // 2] * 100:.1f}%, worst {errors[-1] * 100:.1f}%")
        browser.close()


if __name__ == "__main__":
    mode, args = sys.argv[1], sys.argv[2:]
    if mode == "eval":
        sys.path.insert(0, str(ROOT / "tests"))
        evaluate(args)
    else:
        out = Path(args[0]); out.mkdir(parents=True, exist_ok=True)
        seed = int(args[1]) if len(args) > 1 else 7
        random.seed(seed); np.random.seed(seed)
        counts = [int(v) for v in args[2:]]
        labels = fronts(out, *counts) if mode == "fronts" else backs(out, *counts)
        (out / "labels.json").write_text(json.dumps(labels, indent=1), encoding="utf-8")
        print(len(labels), "scenes in", out)
