# Real-photo workflow diagnostic / 真实照片流程诊断

Checked on 2026-10-29 in an isolated desktop Chromium session. Three publicly licensed photographs depicting physical instant prints were visually reviewed and exercised in the application. The source images are linked below and are not bundled with the app; local copies and derived screenshots were not kept.

| Source and credit | Scene | Observed workflow |
|:--|:--|:--|
| [Instax!](https://commons.wikimedia.org/wiki/File:Instax!_(8205624761).jpg), Christopher Michel, [CC BY 2.0](https://creativecommons.org/licenses/by/2.0/) | A physical WIDE print beside a camera on a table, photographed in perspective | Automatic output required manual confirmation. Approximate manually selected print corners and WIDE format produced a corrected view. |
| [Exposed Polaroid film](https://commons.wikimedia.org/wiki/File:Exposed_Polaroid_film_(Unsplash).jpg), Markus Spiske, [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) | A blank or overexposed print held by a hand, with an obscured corner | Automatic output required manual confirmation. Manual framing exercised the occlusion case without a page error; it cannot recover absent image content. |
| [Polaroid-Camera](https://commons.wikimedia.org/wiki/File:Polaroid-Camera.jpg), WI-Photos, [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) | Multiple prints and cameras in warm-lit clutter; several objects touch the image boundary | Automatic output required manual confirmation. One visible print was selected manually and corrected without a page error. |

The first scene exposed a false warning: before the print was framed, the white paper bottom was treated as a possible glare patch. The scan screen now asks for framing confirmation before analysing uncertain selections. The three cases were rerun to confirm the framing-first behavior. Deliberate corner adjustment or “Use the full original” enables the local quality check.

This is a workflow diagnostic, not an accuracy evaluation. There are no calibrated corner labels, reference scans, paired glare-free photographs or representative device samples. The three selected scenes do not establish recognition precision/recall, glare-removal quality or camera coverage. Synthetic fixtures separately verify geometry, relative blur hints, white-border exclusion and warning placement.

本轮检查使用三张公开授权、确实包含实体相纸的场景照片。三例都需要手动确认选框；用目视选取的近似四角验证了手动拉正流程。它们不构成准确率测试集，也未验证真实配对照片的去反光效果。检测到的白边误提示已通过“先确认框选，再分析画面”的流程修正。

## Automatic framing / 自动框选

Twelve further licensed photographs of physical prints are kept in [`tests/fixtures/real-prints`](../tests/fixtures/real-prints/CREDITS.md). The true corners of every complete print are in `labels.json`; they were fitted to the card edges with `label_tool.py` and checked on overlays. The photos cover prints on wood and beige paper, a hand-held print, overlapping prints, and scans cropped to or into the card. Three scenes have no complete print: an Instax leaving the camera, a print running off the photo, and motion-blurred prints around a camera. `python tests/detect_report.py` runs the app's own import detection on each photo and compares the frame with the labels. A frame counts when every corner is within 4% of the card's diagonal, with the corners in the same order (the print the right way up).

Results on 2026-10-30, with the line-and-border detector. “Automatic” below means eligible for automatic straightening during batch import; a single import always opens the scan view for review:

| Photo | Result | Corner error | Film |
|:--|:--|--:|:--|
| `print-on-beige-paper` | eligible for automatic batch straightening | 1.4% | Polaroid |
| `scan-cropped-top` | eligible for automatic batch straightening | 2.3% | Polaroid |
| `scan-faded-expired` | eligible for automatic batch straightening | 0.8% | Polaroid |
| `scan-washington-square` | eligible for automatic batch straightening | 0.4% | Polaroid |
| `two-overlapping-prints` | eligible for automatic batch straightening | 0.6% | instax WIDE |
| `handheld-blank-print` | framed, waits for confirmation | 1.8% | Polaroid |
| `three-prints-on-wood` | framed, waits for confirmation (several prints) | 1.0% | Polaroid |
| `scan-cropped-bottom-border` | full image (Polaroid Spectra, not a supported format) | | |
| `scan-old-family-print` | full image (peel-apart print, not a supported format) | | |
| `instax-ejecting`, `print-on-playing-cards`, `prints-around-camera` | full image (no complete print) | | |

Out of the 9 labelled photos, 7 are framed, 5 eligible for automatic batch straightening, and no frame is wrong. All three scenes without a complete print are left to the user. Detection takes 40–280 ms per photo in Chromium. The previous detector, which grew the background inwards from the image border, framed none of the twelve on 2026-10-29. `tests/test_real_prints.py` imports each photo through the UI and fails if any frame is wrong or if fewer prints are found.

Twelve photos are too few to estimate accuracy, so the detector was also run on 260 synthetic scenes with known corners. Each positive scene places a crop of a fixture photo inside a card with one film's border proportions. The card is warped onto a wood, paper, fabric, dark or cluttered background, with perspective, a lighting gradient, blur, noise and sometimes a thumb over a corner. The negative scenes hold borderless photos, blank sheets or card-like rectangles, none of which should be framed. Two sets with different seeds (7 and 1234), made and scored with `tests/synthetic_prints.py`, gave:

| | Set A | Set B |
|:--|--:|--:|
| **Complete prints** | 84 | 89 |
| eligible for automatic batch straightening | 38 | 50 |
| framed for confirmation | 40 | 32 |
| full image | 5 | 7 |
| wrong frame, shown for confirmation | 1 | 0 |
| **Scenes without a complete print** | 46 | 41 |
| full image | 45 | 40 |
| wrong frame, shown for confirmation | 1 | 1 |
| **Wrong automatic straightening** | 0 | 0 |

Automatic frames had a median corner error of about 1%, and the worst was 2.4%. Eight of the frames shown for confirmation guessed a different film format, which the user can change. The missed prints mostly have a border close to the background colour (white prints on paper, prints on patterned fabric) or a covered corner. The slowest scene took 0.66 s. The synthetic scenes come from the same twelve photos and a simple renderer, so they test geometry and robustness, not real-world precision.

Photos of a print's back have no picture window. For them the app looks for a card with clear edges and the front's proportions, and it always asks for confirmation. On 100 synthetic backs (seeds 99 and 2024) it proposed the right card for 56 and a wrong one for 3. In the rest it found nothing, mostly where the back's colour is close to the table's, and showed the full image.

Known issue: choosing “Use the full original” on a scan cropped to a Polaroid card can flag the bottom border as possible glare (`scan-washington-square.jpg`). Automatic framing now recognises that scan as a Polaroid, so this only happens when the full original is chosen.

另有 12 张公开授权的真实相纸照片放在 `tests/fixtures/real-prints`，每张完整相纸的真实四角标在 `labels.json`。`python tests/detect_report.py` 用应用自己的识别跑一遍，再和标注比对：每个角的误差都不超过相纸对角线的 4%，方向也对，才算框对。2026-10-30 的结果：9 张拍到完整相纸的照片框出 7 张，其中 5 张直接拉正，没有框错；3 张没有完整相纸的照片都留给手动。旧的识别方法（从画面四边向里长出背景）在 2026-10-29 一张也没框出来。另用 `tests/synthetic_prints.py` 生成 260 张已知四角的合成场景检查：173 张完整相纸框出 160 张，88 张直接拉正，没有一张自动拉错；漏掉的多是白边和背景颜色太近，或者被手指挡住。背面照片只按外形找卡片，找到了也要确认。已知问题：贴着相纸裁切的 Polaroid 扫描图使用「整张原图」时，底部白边可能被提示为反光（`scan-washington-square.jpg`）。
