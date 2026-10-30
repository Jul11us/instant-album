import base64
import pathlib
import sys


def render(root):
    root = pathlib.Path(root)
    src = (root / 'src/app.html').read_text(encoding='utf-8')
    # Opening the template in a browser leads to the distributable. Its app
    # script stays inert until all build-time assets have been embedded.
    _, marker, src = src.partition('<!-- source-entry:end -->')
    if not marker:
        raise ValueError('Missing source entry guard')
    src = src.lstrip('\r\n')
    script = '<script type="text/x-instant-album-source">'
    if src.count(script) != 1:
        raise ValueError('Expected one source app script')
    src = src.replace(script, '<script>', 1)
    images = [('__IMG__', 'sample.jpg'), ('__HOME__', 'home-front.jpg'), ('__IMG2__', 'home-left.jpg'), ('__IMG3__', 'home-right.jpg')]
    for marker, name in images:
        uri = 'data:image/jpeg;base64,' + base64.b64encode((root / 'design-demos/assets' / name).read_bytes()).decode()
        src = src.replace(marker, uri)
    src = src.replace('__BACKUP_JS__', (root / 'src/backup.js').read_text(encoding='utf-8'))
    return '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"></head><body>' + src + '</body></html>'


if __name__ == '__main__':
    root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else '.')
    page = render(root)
    (root / '相角.html').write_text(page, encoding='utf-8')
    (root / 'preview.html').write_text(page, encoding='utf-8')
    print('ok')
