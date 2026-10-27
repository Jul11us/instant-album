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

「贴进相册」是一款单文件网页工具，帮你把实体即时成像照片整理成数字相册。拍一张或上传图片，拉正相纸、记录正反面和照片背后的故事；把照片收进主题相册，也可以将几张回忆拼成一页，慢慢收藏。

## 功能一览

| | |
|:--|:--|
| **01 / 扫描与拉正** | 尝试识别照片边缘并校正透视；支持 instax mini、SQUARE、WIDE 与 Polaroid i-Type/600、Go。也可以手动调整四角或选择相纸，拖角时手指旁会出现放大镜。普通照片可按原比例处理。 |
| **02 / 减少反光** | 换个角度补拍后尝试对齐并合成，或用画笔手动修补小光斑。合成后可按住对比合成前，再决定保留还是撤回。两张照片在同一位置都有反光时无法通过合成恢复细节。 |
| **03 / 色彩与相纸** | 使用滤镜、亮度、对比、色温和颗粒调整照片；保留原框，选择代码绘制的相纸样式，或绘制、上传自己的边框。 |
| **04 / 留下字迹** | 为照片添加文字、选择字体，并加上胶片相机风格的日期印章。 |
| **05 / 写下回忆** | 为每张照片记录地点、人物和一句故事，可选择把地点、人物印在白边上。「照片里的日期」与「翻拍日期」分开记录：默认按翻拍日期推测，可改成拍立得当天。还可以拍下相纸背面，和正面存在一起，随时翻面查看。 |
| **06 / 导出与拼页** | 导出整张相纸或只要画面，选择 JPEG、PNG 与尺寸；多张可打包为 ZIP 并附「回忆.txt」。有背面的照片可与正面并排导出或另存一张。把几张照片拼成手账贴纸墙、胶片接触印、旅行明信片或回忆时间线；调整照片顺序，换底色、胶带和摆放方式，存成以后还能接着改的相册页。 |
| **07 / 我的相册** | 建立「旅行」「朋友」等相册并设置封面，按日期、地点、人物或故事查找，在应用里按月份翻看收藏；点有背面的照片可以翻面。 |
| **08 / 本地草稿** | 在浏览器支持时自动保存照片、背面、四角、编辑设置、相册和相册页，下次打开时尝试恢复；可删除单张或清空草稿。 |
| **09 / 了解相机** | 根据选择的相机查看拍摄提示和推荐参数；通过程序化 3D 模型探索即时成像相机的通用内部结构。 |

## 开始使用

1. 下载仓库，在浏览器中打开 **[贴进相册.html](贴进相册.html)**。
2. 上传或拍摄照片；如果自动识别不准确，拖动四角并选择合适的相纸。
3. 拉正后调整照片、边框和文字，写下回忆；选择单张导出、打包保存或拼成相册页。

无需安装后端。普通浏览器中，保存会显示图片和下载链接，可直接下载，或右键 / 长按另存；支持系统分享的浏览器可以直接分享；支持相应能力的 Claude Artifact 环境可以调用原生保存。字体和 3D 功能需要网络连接。

## 使用须知

- 自动识别和反光处理是启发式方法，结果取决于照片、光线和背景。反光算法目前使用模拟图像测试，尚未以真实拍立得照片验证。
- 渐变或多色边框可能无法自动识别为相纸；请手动选择相纸型号，或先选择相机。识别不到边缘时可手动调整四角。
- 桌面端支持拖放、粘贴和多张导入；多张照片未识别时，先调整第一张，其余需重新导入。
- 高清导出依照片中实际可用的像素决定，最长边最高 3200 像素；补拍合成的照片最高为标准尺寸。
- 草稿只保存在当前设备的当前浏览器中，清理浏览器数据或存储空间不足时可能丢失，请及时导出。手机浏览器能否经由分享直接存入系统相册，因系统和浏览器而异。
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

构建会生成 `贴进相册.html` 和本地预览用的 `preview.html`。Google Fonts 和 Three.js 通过网络加载；Three.js 版本为 0.160.0。

浏览器回归测试需要 Python Playwright 与 Chromium。运行 `tests/` 中的五个 `test_*.py` 脚本，可通过 `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH` 指定已有的 Chromium 可执行文件。

## English

**An instant photo workspace for the pictures you can hold.**

贴进相册 is a single-file web app for turning physical instant photographs into digital keepsakes. Straighten a print, keep its front and back together, and give the story behind it a place to live. The interface is currently in Chinese.

- **Scan:** Detect edges and correct perspective, or adjust the corners with a magnifier and choose a film format. Ordinary photographs can retain their original proportions.
- **Restore:** Try a second, differently angled shot to reduce glare, compare the result, or brush over small spots. Results depend on the images; glare removal has been tested on simulated images, not yet on real instant photographs.
- **Create:** Adjust colour and frames, add captions and date stamps, and record a place, people and a short story. The date of the original moment can be edited separately from the digitisation date. Scan the back of a print too and flip between both sides.
- **Keep & share:** Export a single image as JPEG or PNG, save several as a ZIP, or arrange them into a scrapbook wall, contact sheet, postcard or timeline, then reorder photos, change the paper and tape, and keep the page to edit later. Drafts are stored locally when browser storage is available.
- **Browse:** Group photos into albums with covers, and search by date, place or people.
- **Explore:** Browse camera-specific shooting tips and illustrative 3D models of generic instant-camera internals.

Open [贴进相册.html](贴进相册.html) in a browser to start. No backend installation is required. Fonts and the 3D library require an internet connection. Regular browsers offer a download link and image preview; file sharing depends on browser support. Drafts can be lost when browser data is cleared or storage is unavailable, so export finished work. Claude-specific saving and the optional “Ask Claude” feature depend on the host runtime; the latter may send a photo or analysis data and use your own Claude quota.

## 图片署名 / Image credits

示例照片由 **Scotch Mist** 拍摄，来自 Wikimedia Commons，采用 [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) 许可：
[Palanga 01](https://commons.wikimedia.org/wiki/File:Palanga_01.jpg) · [Palanga 02](https://commons.wikimedia.org/wiki/File:Palanga_02.jpg) · [Palanga 09](https://commons.wikimedia.org/wiki/File:Palanga_09.jpg)。`design-demos/assets/sample.jpg` 为上述照片裁切缩小后的版本，采用相同许可。封面为本项目原创插画。

## 商标 / Trademarks

instax 是 FUJIFILM 的商标，Polaroid 是 Polaroid 的商标。本项目与两家公司均无关联。页面中的相纸边框和相机模型由代码重新绘制，未使用官方产品图片。

instax and Polaroid are trademarks of their respective owners. This independent project is not affiliated with either company. Frame designs and camera models are recreated in code.
