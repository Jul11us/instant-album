import base64, pathlib, sys
root = pathlib.Path(sys.argv[1])
uri = 'data:image/jpeg;base64,' + base64.b64encode((root/'design-demos'/'assets'/'sample.jpg').read_bytes()).decode()
src = (root/'src'/'app.html').read_text(encoding='utf-8')
page = '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"></head><body>' + src.replace('__IMG__', uri) + '</body></html>'
(root/'贴进相册.html').write_text(page, encoding='utf-8')
# 本地预览与发布文件保持一致
(root/'preview.html').write_text(page, encoding='utf-8')
print('ok')
