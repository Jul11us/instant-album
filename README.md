<div align="center">
  <img src="docs/cover.svg" alt="A little darkroom for instant photos" width="100%">
  <br><br>
  <h1>贴进相册</h1>
  <p><strong>把手里的拍立得，留进手机相册。</strong></p>
  <p>扫描正反面，写下故事，做一本属于自己的数字相册。</p>
  <p><sub>SCAN &nbsp; / &nbsp; CREATE &nbsp; / &nbsp; REMEMBER</sub></p>
  <p><a href="#开始使用">开始使用</a> &nbsp;·&nbsp; <a href="#功能一览">功能一览</a> &nbsp;·&nbsp; <a href="#使用须知">使用须知</a> &nbsp;·&nbsp; <a href="#english">English</a></p>
</div>

<br>

### 一张照片，一间小小暗房

「贴进相册」是一款单文件网页工具，帮你把实体即时成像照片整理成数字相册。拍一张或上传图片，拉正相纸、记录正反面和照片背后的故事；把照片收进主题相册，也可以将几张回忆拼成一页，慢慢收藏。编辑时，照片背后还会呈现低调的暗房光影。

## 功能一览

| | |
|:--|:--|
| **开始 / 首页** | 直接拍摄或导入照片，从「继续上次整理」回到上次使用的照片，或独立打开「我的相册」。示例只在选择「先用示例体验一下」后载入，不会保存到个人收藏。 |
| **01 / 扫描与拉正** | 尝试识别照片边缘并校正透视；支持 instax mini、SQUARE、WIDE 与 Polaroid i-Type/600、Go。也可以手动调整四角或选择相纸，拖角时手指旁会出现放大镜。框选界面会提示可能的反光位置、裁边、可用像素不足或细节偏少，给出补拍建议；可展开查看、忽略本张提醒，或直接拉正。普通照片可按原比例处理。 |
| **02 / 减少反光** | 换个角度补拍后尝试对齐并合成，或用画笔手动修补小光斑。合成后可按住对比合成前，再决定保留还是撤回。两张照片在同一位置都有反光时无法通过合成恢复细节。 |
| **03 / 色彩与相纸** | 使用滤镜、亮度、对比、色温和颗粒调整照片；保留原框，选择代码绘制的相纸样式，或绘制、上传自己的边框。 |
| **04 / 留下字迹** | 为照片添加文字、选择字体，并加上胶片相机风格的日期印章。 |
| **05 / 写下回忆** | 为每张照片记录地点、人物和一句故事，可选择把地点、人物印在白边上。「照片里的日期」与「翻拍日期」分开记录：默认按翻拍日期推测，可改成拍立得当天；记不清时可以记录到年月、季节、年份、「大约某年」或「不记得」，相册与时间线会按所选精度展示和排序。还可以拍下相纸背面，和正面存在一起，随时翻面查看。 |
| **06 / 导出与拼页** | 导出整张相纸或只要画面，选择 JPEG、PNG 与尺寸；多张可打包为 ZIP 并附「回忆.txt」。有背面的照片可与正面并排导出或另存一张。把几张照片拼成手账贴纸墙、胶片接触印、旅行明信片或回忆时间线；调整照片顺序，换底色、胶带和摆放方式，存成以后还能接着改的相册页。 |
| **07 / 我的相册** | 建立「旅行」「朋友」等相册并设置封面，按日期、地点、人物或故事查找，在应用里按日期精度分组翻看收藏；点有背面的照片可以翻面。 |
| **08 / 本地草稿** | 在浏览器支持时自动保存照片、背面、四角、编辑设置、相册和相册页，下次打开时尝试恢复。编辑区显示等待保存、正在保存、已保存或保存失败；失败后可重试。只有浏览器实际完成写入后才显示已保存；「导出图片」用于另存到设备。可删除单张或清空草稿。 |
| **09 / 了解相机** | 根据选择的相机查看拍摄提示和推荐参数；通过程序化 3D 模型探索即时成像相机的通用内部结构。 |

## 开始使用

1. 下载仓库，在浏览器中打开 **[贴进相册.html](贴进相册.html)**。
2. 在首页选择「拍一张」或「导入照片」。检查选框并选择合适的相纸，再确认拉正；普通照片可以点「使用整张原图」，保留原始方向和比例。没有足够相纸特征时会先展示完整原图，批量导入中的不确定结果会留在待确认队列。
3. 拉正后调整照片、边框和文字，写下回忆。编辑区的保存状态表示当前浏览器中的草稿写入情况；点「导出图片」另存成品，也可打包保存或拼成相册页。
4. 下次打开从首页选择「继续上次整理」或「我的相册」。想先了解工具时，可以主动打开示例体验。

无需安装后端。普通浏览器中，保存会显示图片和下载链接，可直接下载，或右键 / 长按另存；支持系统分享的浏览器可以直接分享；支持相应能力的 Claude Artifact 环境可以调用原生保存。字体、3D 功能和暗房背景需要网络连接。

## 使用须知

- 自动识别和反光处理是启发式方法，结果取决于照片、光线和背景。反光算法目前使用模拟图像测试，尚未以真实拍立得照片验证。
- 扫描提醒在本机分析当前选框，不上传照片；拖角、旋转或更换相纸后会重新检查。亮斑和细节偏少也可能来自原片内容，提示不能确认反光或失焦，尚未用真实照片数据集评估准确率。背面不检查反光与清晰度；批量自动拉正的照片可点「重扫」查看提醒。
- 渐变或多色边框可能无法自动识别为相纸；请手动选择相纸型号，或先选择相机。识别不到边缘时可手动调整四角。
- 照片日期设为月份时，日期印章只印年月；设为季节、年份或「大约某年」时只印年份，设为「不记得」时不印日期。
- 桌面端支持拖放、粘贴和多张导入；未识别的照片会进入待框选队列，拉正一张后自动继续下一张，也可以通过「继续框选」返回队列。待框选文件仅保留在当前页面，刷新前请完成拉正；完成后才会保存为草稿。
- 高清导出依照片中实际可用的像素决定，最长边最高 3200 像素；补拍合成的照片最高为标准尺寸。
- 草稿只保存在当前设备的当前浏览器中，清理浏览器数据或存储空间不足时可能丢失，请及时导出。手机浏览器能否经由分享直接存入系统相册，因系统和浏览器而异。
- 启动时若无法完整读取旧收藏，会暂停导入和保存，并在首页提供「重试读取本机收藏」，避免把未读出的照片当作已删除数据覆盖。
- 3D 相机外形参考公开尺寸；内部零件是通用结构示意，并非官方拆解图。
- 「问问 Claude」仅在提供相关运行时能力的环境中出现；该功能可能发送照片或照片分析数据，并使用用户自己的 Claude 额度。
- 相机资料与出处详见 [product-facts.md](product-facts.md)。

## 项目结构与构建

| 文件 | 用途 |
|:--|:--|
| [`src/app.html`](src/app.html) | 页面源码：HTML、CSS 与 JavaScript |
| [`贴进相册.html`](贴进相册.html) | 可直接打开的构建结果 |
| [`build.py`](build.py) | 将示例照片嵌入页面 |
| [`product-facts.md`](product-facts.md) | 相机规格、拍摄建议与来源 |
| [`design-demos/`](design-demos/) | 早期设计探索和示例素材 |

修改源码后，在项目目录运行：

```bash
python build.py .
```

构建会生成 `贴进相册.html` 和本地预览用的 `preview.html`。Google Fonts、Three.js 和 [Shaders](https://shaders.com/) 通过网络加载；Three.js 版本为 0.160.0，Shaders 版本为 4.0.4（MIT 许可）。暗房光影需要可用的 WebGPU 和网络；不支持、加载失败或离线时保留原有的深色背景。启用系统「减少动态效果」时，光影会保持静止；代码已为 Shaders 禁用使用统计。

浏览器回归测试需要 Python Playwright 与 Chromium。运行 `tests/` 中的 `test_*.py` 脚本，可通过 `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` 指定已有的 Chromium 可执行文件。

## English

**An instant photo workspace for the pictures you can hold.**

贴进相册 is a single-file web app for turning physical instant photographs into digital keepsakes. Straighten a print, keep its front and back together, and give the story behind it a place to live. A subtle darkroom glow sits behind the photo while you edit. The interface is currently in Chinese.

- **Scan:** Detect edges and correct perspective, or adjust the corners with a magnifier and choose a film format. Ordinary photographs can retain their original proportions.
- **Start & return:** The home screen offers capture, import, the last edited photo and the library. The sample editor is opt-in. Uncertain detections require confirmation; “Use the full original” preserves an ordinary photo’s orientation and aspect ratio.
- **Check before straightening:** Local, non-blocking hints flag possible glare locations, edges close to the image boundary, low usable resolution and limited detail. Adjusting corners, orientation or film format refreshes the check. Hints may reflect the original scene and have only been tested with synthetic fixtures; they do not establish real-photo detection accuracy. Back-side scans skip glare and sharpness checks; automatically straightened batches can be reviewed through the rescan screen.
- **Restore:** Try a second, differently angled shot to reduce glare, compare the result, or brush over small spots. Results depend on the images; glare removal has been tested on simulated images, not yet on real instant photographs.
- **Create:** Adjust colour and frames, add captions and date stamps, and record a place, people and a short story. The date of the original moment can be edited separately from the digitisation date, or kept as vague as you remember it: a year and month, a season, a year, “around” a year, or unknown. Scan the back of a print too and flip between both sides.
- **Keep & share:** Export a single image as JPEG or PNG, save several as a ZIP, or arrange them into a scrapbook wall, contact sheet, postcard or timeline, then reorder photos, change the paper and tape, and keep the page to edit later. Drafts are stored locally when browser storage is available.
- **Know what is saved:** A persistent editor status distinguishes pending changes, a write in progress, completed local storage and a failed write with retry. Exporting an image is a separate action; completing a browser-storage transaction does not save a file to the device’s photo library.
- **Recover before writing:** If startup cannot fully read an existing collection, importing and saving pause until “Retry reading local collection” succeeds, preserving unread photos instead of overwriting them.
- **Browse:** Group photos into albums with covers, and search by date, place or people.
- **Explore:** Browse camera-specific shooting tips and illustrative 3D models of generic instant-camera internals.

Open [贴进相册.html](贴进相册.html) in a browser to start. No backend installation is required. Fonts, the 3D library and the WebGPU darkroom background require an internet connection; if WebGPU is unavailable or the effect fails to load, the original dark background is retained. The effect remains still when reduced motion is requested. Regular browsers offer a download link and image preview; file sharing depends on browser support. The date stamp uses the chosen precision: month and year, year only for seasons, years or approximate years, and no date when unknown. Drafts can be lost when browser data is cleared or storage is unavailable, so export finished work. Claude-specific saving and the optional “Ask Claude” feature depend on the host runtime; the latter may send a photo or analysis data and use your own Claude quota.

## 图片署名 / Image credits

示例照片由 **Scotch Mist** 拍摄，来自 Wikimedia Commons，采用 [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) 许可：
[Palanga 01](https://commons.wikimedia.org/wiki/File:Palanga_01.jpg) · [Palanga 02](https://commons.wikimedia.org/wiki/File:Palanga_02.jpg) · [Palanga 09](https://commons.wikimedia.org/wiki/File:Palanga_09.jpg)。`design-demos/assets/sample.jpg` 为上述照片裁切缩小后的版本，采用相同许可。封面为本项目原创插画。

## 商标 / Trademarks

instax 是 FUJIFILM 的商标，Polaroid 是 Polaroid 的商标。本项目与两家公司均无关联。页面中的相纸边框和相机模型由代码重新绘制，未使用官方产品图片。

instax and Polaroid are trademarks of their respective owners. This independent project is not affiliated with either company. Frame designs and camera models are recreated in code.
