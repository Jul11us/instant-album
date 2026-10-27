import base64, pathlib, sys
root = pathlib.Path(sys.argv[1])
uri = 'data:image/jpeg;base64,' + base64.b64encode((root/'assets'/'sample.jpg').read_bytes()).decode()
for f in (root/'src').glob('*.html'):
    (root/f.name).write_text(f.read_text(encoding='utf-8').replace('__IMG__', uri), encoding='utf-8')
    print('built', f.name)
