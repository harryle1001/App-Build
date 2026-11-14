# Draw detail masks (R = seams, G = dark inner area, B = buttons) for every garment. Run with system python.
import json, os, sys
from PIL import Image, ImageDraw, ImageFilter
sys.path.insert(0, os.path.dirname(__file__))
from specs import G, PX_PER_CM as P

out = sys.argv[1]
os.makedirs(out, exist_ok=True)
for key, g in G.items():
    pts = [p[:2] for p in g['outline']] + [p[:2] for s in g['slabs'] for p in s['poly']]
    x0 = min(p[0] for p in pts) - 3; x1 = max(p[0] for p in pts) + 3
    y0 = min(p[1] for p in pts) - 3; y1 = max(p[1] for p in pts) + 3
    W, H = int((x1 - x0) * P), int((y1 - y0) * P)
    tx = lambda p: ((p[0] - x0) * P, (y1 - p[1]) * P)
    R = Image.new('L', (W, H)); Gc = Image.new('L', (W, H)); B = Image.new('L', (W, H))
    dr = ImageDraw.Draw(R)
    for l in g['lines']:
        dr.line([tx(p) for p in l], fill=255, width=max(2, int(0.28 * P)), joint='curve')
    for poly in g['dark']:
        ImageDraw.Draw(Gc).polygon([tx(p) for p in poly], fill=255)
    for d in g['dots']:
        cx, cy = tx(d); r = 1.0 * P
        ImageDraw.Draw(B).ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    R = R.filter(ImageFilter.GaussianBlur(1.2)); Gc = Gc.filter(ImageFilter.GaussianBlur(2))
    Image.merge('RGB', (R, Gc, B)).save(os.path.join(out, key + '.png'))
    json.dump({'bbox': [x0, y0, x1, y1]}, open(os.path.join(out, key + '.json'), 'w'))
    print(key, W, H)
