"""Refine hand-placed print corners to the real card edges and draw overlays for checking.

Usage: python label_tool.py rough.json out.json overlay_dir
rough.json: {"file.jpg": {"prints": [{"quad": [[x,y]x4], "format": "polaroid", "pinned": [side indexes on the image border]}], ...}}
Each side (0 top: c0→c1, 1 right: c1→c2, 2 bottom: c2→c3, 3 left: c3→c0) is refitted to the strongest edge
within a few pixels of the rough line; pinned sides stay where they are (cards cropped by the scan).
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent


def refine_side(grad_x, grad_y, a, b, radius=10):
    a, b = np.array(a, float), np.array(b, float)
    d = b - a
    length = np.hypot(*d)
    t_hat, n_hat = d / length, np.array([-d[1], d[0]]) / length
    pts = []
    h, w = grad_x.shape
    for t in np.linspace(.06, .94, 60):
        p = a + d * t
        best, best_v = None, 0
        for s in np.arange(-radius, radius + .5, .5):
            q = p + n_hat * s
            x, y = int(round(q[0])), int(round(q[1]))
            if not (1 <= x < w - 1 and 1 <= y < h - 1):
                continue
            v = abs(grad_x[y, x] * n_hat[0] + grad_y[y, x] * n_hat[1])
            if v > best_v:
                best, best_v = q, v
        if best is not None and best_v > 12:
            pts.append(best)
    if len(pts) < 8:
        return a, b, len(pts)
    pts = np.array(pts)
    # Robust line: keep the 70% of points closest to a first fit, then refit.
    for _ in range(2):
        vx, vy, x0, y0 = cv2.fitLine(pts.astype(np.float32), cv2.DIST_HUBER, 0, .01, .01).ravel()
        r = np.abs((pts[:, 0] - x0) * vy - (pts[:, 1] - y0) * vx)
        pts = pts[r <= np.quantile(r, .7) + .5]
    vx, vy, x0, y0 = cv2.fitLine(pts.astype(np.float32), cv2.DIST_L2, 0, .01, .01).ravel()
    p0, dirv = np.array([x0, y0]), np.array([vx, vy])
    proj = lambda p: p0 + dirv * np.dot(np.array(p) - p0, dirv)
    return proj(a), proj(b), len(pts)


def intersect(p1, p2, p3, p4):
    a1, a2, b1, b2 = map(np.array, (p1, p2, p3, p4))
    da, db, dp = a2 - a1, b2 - b1, a1 - b1
    den = da[0] * db[1] - da[1] * db[0]
    t = (db[0] * dp[1] - db[1] * dp[0]) / den
    return a1 + da * t


def refine(img, quad, pinned):
    gray = cv2.GaussianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32), (0, 0), 1.2)
    gx, gy = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3), cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    lines, support = [], []
    for i in range(4):
        a, b = quad[i], quad[(i + 1) % 4]
        if i in pinned:
            lines.append((np.array(a, float), np.array(b, float)))
            support.append('pinned')
        else:
            pa, pb, n = refine_side(gx, gy, a, b)
            lines.append((pa, pb))
            support.append(n)
    corners = [intersect(*lines[(i - 1) % 4], *lines[i]) for i in range(4)]
    return [[round(float(c[0]), 1), round(float(c[1]), 1)] for c in corners], support


def main(rough_path, out_path, overlay_dir):
    rough = json.loads(Path(rough_path).read_text(encoding='utf-8'))
    out, overlay_dir = {}, Path(overlay_dir)
    overlay_dir.mkdir(exist_ok=True)
    for name, entry in rough.items():
        img = cv2.imdecode(np.fromfile(str(HERE / name), np.uint8), cv2.IMREAD_COLOR)   # imread cannot open non-ASCII paths on Windows
        h, w = img.shape[:2]
        prints = []
        vis = img.copy()
        for pr in entry.get('prints', []):
            quad, support = refine(img, pr['quad'], set(pr.get('pinned', [])))
            quad = [[min(max(x, 0), w), min(max(y, 0), h)] for x, y in quad]
            prints.append({**{k: v for k, v in pr.items() if k != 'quad'}, 'quad': quad})
            cv2.polylines(vis, [np.array(quad, np.int32)], True, (0, 0, 255), 2)
            for c in quad:
                cv2.circle(vis, (int(c[0]), int(c[1])), 5, (0, 255, 255), -1)
            print(name, pr.get('format'), quad, support)
        out[name] = {**{k: v for k, v in entry.items() if k != 'prints'}, 'prints': prints}
        cv2.imencode('.png', vis)[1].tofile(str(overlay_dir / f'check-{name[:-4]}.png'))
    Path(out_path).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main(*sys.argv[1:4])
