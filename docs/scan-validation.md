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

## Regression fixtures / 回归测试图片

Twelve further licensed photographs of physical prints are kept in [`tests/fixtures/real-prints`](../tests/fixtures/real-prints/CREDITS.md) and run by `tests/test_real_prints.py`. They cover prints on wood, playing cards and beige paper, a hand-held print, an Instax leaving the camera, overlapping prints, prints scattered around a camera, and scans cropped to or into the card. On 2026-10-29 none was framed automatically; every scene fell back to the full image for manual confirmation. The test requires that uncertain scenes never adopt a contour from inside the picture, that anything accepted automatically is a real film format, and that “Use the full original” straightens each image without distortion. The images have no corner labels, so the test does not measure recognition accuracy.

另有 12 张公开授权的真实相纸照片放在 `tests/fixtures/real-prints`，由 `tests/test_real_prints.py` 运行。2026-10-29 检查时没有一张被自动框选，全部退回整张原图等待手动确认。已知问题：贴着相纸裁切的 Polaroid 扫描图使用「整张原图」时，底部白边可能被提示为反光（`scan-washington-square.jpg`）。
