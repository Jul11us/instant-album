<div align="center">
  <img src="docs/cover.svg" alt="A little darkroom for instant photos" width="100%">
  <br><br>
  <h1>贴进相册</h1>
  <p><strong>把手里的拍立得，留进手机相册。</strong></p>
  <p>扫描、拉正、修饰，再为每一张照片留下一点自己的痕迹。</p>
  <p><a href="#开始使用">开始使用</a> &nbsp;·&nbsp; <a href="#功能一览">功能一览</a> &nbsp;·&nbsp; <a href="#使用须知">使用须知</a> &nbsp;·&nbsp; <a href="#english">English</a></p>
</div>

<br>

### 一张照片，一间小小暗房

「贴进相册」是一款单文件网页工具，帮助你把实体即时成像照片整理成数字照片。拍一张或上传图片，调整四角，修饰色彩与边框，然后保存下来。桌面端也支持拖放、粘贴和多张导入。

## 功能一览

| | |
|:--|:--|
| **01 / 扫描与拉正** | 尝试识别照片边缘并校正透视；支持 instax mini、SQUARE、WIDE 与 Polaroid i-Type/600、Go。也可以手动调整四角或选择相纸。普通照片可按原比例处理。 |
| **02 / 减少反光** | 换个角度补拍后尝试对齐并合成，或用画笔手动修补小光斑。两张照片在同一位置都有反光时无法通过合成恢复细节。 |
| **03 / 色彩与相纸** | 使用滤镜、亮度、对比、色温和颗粒调整照片；保留原框，选择代码绘制的相纸样式，或绘制、上传自己的边框。 |
| **04 / 留下字迹** | 为照片添加文字、选择字体，并加上胶片相机风格的日期印章。 |
| **05 / 了解相机** | 根据选择的相机查看拍摄提示和推荐参数；通过程序化 3D 模型探索即时成像相机的通用内部结构。 |

## 开始使用

1. 下载仓库，在浏览器中打开 **[贴进相册.html](贴进相册.html)**。
2. 上传或拍摄照片；如果自动识别不准确，拖动四角并选择合适的相纸。
3. 拉正后调整照片、边框和文字，再按页面提示保存。

无需安装后端。普通浏览器中，保存会打开图片，使用右键或长按将其另存；支持相应能力的 Claude Artifact 环境可以调用原生保存。字体和 3D 功能需要网络连接。

## 使用须知

- 自动识别和反光处理是启发式方法，结果取决于照片、光线和背景。反光算法目前使用模拟图像测试，尚未以真实拍立得照片验证。
- 渐变或多色边框可能无法自动识别为相纸；请手动选择相纸型号，或先选择相机。识别不到边缘时可手动调整四角。
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

## English

**An instant photo workspace for the pictures you can hold.**

贴进相册 is a single-file web app for turning physical instant photographs into digital keepsakes. Import an image, straighten it, adjust its look, add a frame or a handwritten note, and save the result. The interface is currently in Chinese.

- **Scan:** Detect edges and correct perspective, or adjust the corners and film format manually. Ordinary photographs can retain their original proportions.
- **Restore:** Try a second, differently angled shot to reduce glare, or brush over small spots. Results depend on the images; glare removal has been tested on simulated images, not yet on real instant photographs.
- **Create:** Experiment with filters, adjustments, frames, captions, and date stamps.
- **Explore:** Browse camera-specific shooting tips and illustrative 3D models of generic instant-camera internals.

Open [贴进相册.html](贴进相册.html) in a browser to start. No backend installation is required. Fonts and the 3D library require an internet connection. In a regular browser, save through the displayed image using right-click or long-press. Claude-specific saving and the optional “Ask Claude” feature depend on the host runtime; the latter may send a photo or analysis data and use your own Claude quota.

## 图片署名 / Image credits

示例照片由 **Scotch Mist** 拍摄，来自 Wikimedia Commons，采用 [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) 许可：
[Palanga 01](https://commons.wikimedia.org/wiki/File:Palanga_01.jpg) · [Palanga 02](https://commons.wikimedia.org/wiki/File:Palanga_02.jpg) · [Palanga 09](https://commons.wikimedia.org/wiki/File:Palanga_09.jpg)。`design-demos/assets/sample.jpg` 为上述照片裁切缩小后的版本，采用相同许可。封面为本项目原创插画。

## 商标 / Trademarks

instax 是 FUJIFILM 的商标，Polaroid 是 Polaroid 的商标。本项目与两家公司均无关联。页面中的相纸边框和相机模型由代码重新绘制，未使用官方产品图片。

instax and Polaroid are trademarks of their respective owners. This independent project is not affiliated with either company. Frame designs and camera models are recreated in code.
