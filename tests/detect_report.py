"""Measure automatic framing on the labelled real-print fixtures and print a table.

Each photo goes through the app's own decode and detection (decodeFile + setSource), and the proposed
frame is compared with tests/fixtures/real-prints/labels.json:
  auto      accepted without confirmation and matching a labelled print (right corners and orientation)
  suggest   shown for confirmation and matching a labelled print
  fallback  the whole image, waiting for the user to frame it
  WRONG     a frame that matches no labelled print, or a labelled print turned the wrong way
Used by tests/test_real_prints.py; run directly for a report: python tests/detect_report.py
"""
import base64
import json
import math
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/real-prints"
LABELS = json.loads((FIXTURES / "labels.json").read_text(encoding="utf-8"))
TOLERANCE = .04   # each corner within 4% of the card's diagonal

DETECT = """async ({name, data}) => {
  const bytes=Uint8Array.from(atob(data),c=>c.charCodeAt(0)),file=new File([bytes],name,{type:'image/jpeg'});
  const img=await decodeFile(file),t=performance.now();setSource(img,null,true);
  return {quad,format,confirm:scanNeedsConfirm,W:src.width,H:src.height,ms:Math.round(performance.now()-t)};
}"""


def diag(q):
    return max(math.dist(q[0], q[2]), math.dist(q[1], q[3]))


def corner_error(q, label):
    """Largest corner distance as a share of the label's diagonal, with the corners in the same order."""
    return max(math.dist(a, b) for a, b in zip(q, label)) / diag(label)


def classify(name, r):
    W, H = r["W"], r["H"]
    full = [[0, 0], [W, 0], [W, H], [0, H]]
    is_full = all(abs(a - b) <= 1.5 for p, q in zip(r["quad"], full) for a, b in zip(p, q))
    if is_full and r["format"] == "free":
        # The untouched whole image is the fallback, even where a scan's card happens to fill it.
        return ("fallback", None, True) if r["confirm"] else ("WRONG", None, False)
    best = None
    for label in LABELS[name]["prints"]:
        # An unrecognised film is framed by its picture window ("原比例" adds its own border).
        target = label["window"] if r["format"] == "free" and "window" in label else label["quad"]
        err = corner_error(r["quad"], target)
        turned = min(corner_error(r["quad"][k:] + r["quad"][:k], target) for k in (1, 2, 3))
        if best is None or err < best[0]:
            best = (err, turned, label)
    if best and best[0] <= TOLERANCE:
        kind = "suggest" if r["confirm"] else "auto"
        film = best[2]["format"]
        return kind, best[0], (film == "free" or r["format"] == film or (film == "polaroid" and r["format"] == "go"))
    if is_full and r["confirm"]:
        return "fallback", None, True
    return "WRONG", best[0] if best else None, False


def run(page):
    rows = []
    for name in sorted(k for k in LABELS if not k.startswith("_")):
        data = base64.b64encode((FIXTURES / name).read_bytes()).decode()
        r = page.evaluate(DETECT, {"name": name, "data": data})
        kind, err, fmt_ok = classify(name, r)
        rows.append({"name": name, "kind": kind, "err": err, "format": r["format"], "format_ok": fmt_ok,
                     "confirm": r["confirm"], "ms": r["ms"], "labelled": len(LABELS[name]["prints"])})
    return rows


def table(rows):
    lines = []
    for r in rows:
        err = "" if r["err"] is None else f"{r['err'] * 100:4.1f}%"
        fmt = r["format"] + ("" if r["format_ok"] else " (format?)")
        lines.append(f"  {r['name']:<32} {r['kind']:<9} {err:>6}  {fmt:<22} {r['ms']:>4} ms")
    found = [r for r in rows if r["kind"] in ("auto", "suggest")]
    labelled = [r for r in rows if r["labelled"]]
    lines.append(f"  found {len(found)}/{len(labelled)} labelled photos "
                 f"({sum(r['kind'] == 'auto' for r in rows)} automatic), "
                 f"{sum(r['kind'] == 'WRONG' for r in rows)} wrong, "
                 f"{sum(r['kind'] == 'fallback' and not r['labelled'] for r in rows)}/{len(rows) - len(labelled)} unlabelled photos left to the user")
    return "\n".join(lines)


if __name__ == "__main__":
    from playwright.sync_api import sync_playwright
    page_path = Path(os.environ.get("INSTANT_ALBUM_TEST_PAGE", ROOT / "相角.html"))
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(page_path.as_uri())
        page.wait_for_function("() => !restoring")
        print(table(run(page)))
        browser.close()
