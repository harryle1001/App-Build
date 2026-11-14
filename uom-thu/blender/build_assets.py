# Crop renders, make overlay (no shadow) + thumbnail (white bg) WebPs, compute anchor points, write data.js
import os, sys, json, glob
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from specs import G

REN = os.path.join(HERE, 'render')
OUT = sys.argv[1]
VT = sys.argv[2]  # vton dir (models)
os.makedirs(os.path.join(OUT, 'g'), exist_ok=True)
os.makedirs(os.path.join(OUT, 'm'), exist_ok=True)

# anchor x in cm and how far out on the body's shoulder half-width it sits
SHOULDER = {'mangto': (19.5, -3, 0.9), 'dam-hai-day': (6.8, 1.0, 0.5), 'dam-so-mi': (17.5, -3, 0.95),
            'dam-chu-a': (12.5, -2, 0.7), 'dam-babydoll': (14, 0, 0.75)}

garments = []
for key, g in G.items():
    files = sorted(glob.glob(os.path.join(REN, key + '__*.png')))
    if not files:
        continue
    out = g['outline']; ys = [p[1] for p in out]; xs = [p[0] for p in out]
    top, bot = max(ys), min(ys); h, w = top - bot, max(xs) - min(xs)
    scale = max(h * 1.14, w * 1.14 * 4 / 3); ppc = 1024 / scale; cy = (top + bot) / 2
    to_px = lambda x, y: (384 + x * ppc, 512 - (y - cy) * ppc)
    entry = {'key': key, 'cat': g['cat'], 'name': g['name'], 'colors': []}
    crop = None
    for f in files:
        im = Image.open(f).convert('RGBA')
        a = im.getchannel('A')
        solid = a.point(lambda v: 255 if v > 245 else 0)
        if crop is None:
            l, t, r, b = solid.getbbox(); crop = (max(0, l - 2), max(0, t - 2), min(768, r + 2), min(1024, b + 2))
        # overlay: drop the soft shadow (partial alpha) but keep anti-aliased edges
        ov = im.copy(); oa = a.point(lambda v: max(0, min(255, int((v - 215) * 255 / 40))))
        for poly in g['dark']:  # open neckline: let the model's neck / top show through
            ImageDraw.Draw(oa).polygon([to_px(*q) for q in poly], fill=0)
        ov.putalpha(oa)
        ov = ov.crop(crop)
        k = 560 / ov.height; ov = ov.resize((round(ov.width * k), 560), Image.LANCZOS)
        cid = os.path.basename(f)[len(key) + 2:-4]
        ov.save(os.path.join(OUT, 'g', f'{key}__{cid}.webp'), 'WEBP', quality=82, method=6)
        th = Image.new('RGBA', im.size, (255, 255, 255, 255)); th.alpha_composite(im)
        tb = th.convert('RGB').crop((max(0, crop[0] - 30), max(0, crop[1] - 20), min(768, crop[2] + 30), min(1024, crop[3] + 30)))
        tb.thumbnail((220, 260)); tb.save(os.path.join(OUT, 'g', f'{key}__{cid}_t.webp'), 'WEBP', quality=78)
        nm, hx = g['colors'][cid]
        entry['colors'].append({'id': cid, 'name': nm, 'hex': hx})
    cw, ch = crop[2] - crop[0], crop[3] - crop[1]
    fx = lambda x, y: ((to_px(x, y)[0] - crop[0]) / cw, (to_px(x, y)[1] - crop[1]) / ch)
    entry['aspect'] = round(cw / ch, 4)
    entry['hcm'] = round(ch / ppc, 2)
    if g['cat'] == 'quan':
        wx = max(p[0] for p in out if p[1] == 0)
        entry['anchor'] = {'type': 'waist', 'l': fx(-wx, 0)[0], 'r': fx(wx, 0)[0], 'y': fx(0, 0)[1], 'ref': 100}
    else:
        ax, ay, frac = SHOULDER['mangto' if g['cat'] == 'mangto' else key]
        entry['anchor'] = {'type': 'shoulder', 'l': fx(-ax, ay)[0], 'r': fx(ax, ay)[0], 'y': fx(0, ay)[1], 'frac': frac, 'ref': 130}
    entry['anchor'] = {k2: (round(v, 4) if isinstance(v, float) else v) for k2, v in entry['anchor'].items()}
    garments.append(entry)

# models: percent keypoints (sy shoulder y, sl/sr shoulder x, wy waist y, wl/wr waist x, ay ankle y, cx centre x)
MODELS = [
    ('049447_0.jpg', 'Dáng thon, cao', dict(sy=16, sl=31, sr=63, wy=30, wl=37, wr=60, ay=88, cx=48)),
    ('051482_0.jpg', 'Dáng mảnh', dict(sy=9, sl=38, sr=62, wy=33, wl=41, wr=62, ay=87, cx=52)),
    ('model_9.png', 'Dáng nhỏ nhắn', dict(sy=19, sl=33, sr=68, wy=38, wl=38, wr=62, ay=90, cx=50)),
    ('049713_0.jpg', 'Dáng khỏe', dict(sy=15, sl=36, sr=68, wy=38, wl=43, wr=62, ay=88, cx=53)),
    ('053514_0.jpg', 'Dáng đồng hồ cát', dict(sy=8, sl=37, sr=65, wy=28, wl=40, wr=63, ay=88, cx=51)),
    ('model_8.png', 'Dáng chân dài', dict(sy=17, sl=33, sr=65, wy=39, wl=39, wr=62, ay=88, cx=50)),
    ('052472_0.jpg', 'Dáng cao, mảnh', dict(sy=8, sl=36, sr=61, wy=33, wl=39, wr=58, ay=89, cx=49)),
    ('053228_0.jpg', 'Dáng cân đối', dict(sy=10, sl=33, sr=62, wy=31, wl=37, wr=60, ay=85, cx=49)),
    ('051918_0.jpg', 'Nam, vai rộng', dict(sy=18, sl=31, sr=69, wy=45, wl=37, wr=62, ay=88, cx=49)),
    ('049205_0.jpg', 'Nam, dáng gầy', dict(sy=13, sl=31, sr=70, wy=43, wl=35, wr=63, ay=87, cx=49)),
]
models = []
for i, (f, label, kp) in enumerate(MODELS):
    im = Image.open(os.path.join(VT, 'models', f)).convert('RGB')
    mid = f'm{i + 1}'
    im.resize((600, 800), Image.LANCZOS).save(os.path.join(OUT, 'm', mid + '.webp'), 'WEBP', quality=80, method=6)
    t = im.resize((120, 160), Image.LANCZOS); t.save(os.path.join(OUT, 'm', mid + '_t.webp'), 'WEBP', quality=75)
    models.append({'id': mid, 'label': label, 'kp': kp})

ai = sorted(os.path.basename(p)[:-5] for p in glob.glob(os.path.join(OUT, 'ai', '*.webp')))
with open(os.path.join(OUT, 'data.js'), 'w') as fh:
    fh.write('window.WARDROBE=' + json.dumps({'garments': garments, 'models': models, 'ai': ai}, ensure_ascii=False) + ';\n')
print(len(garments), 'garments', sum(len(g['colors']) for g in garments), 'colourways', len(models), 'models')
