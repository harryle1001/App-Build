# Batch AI try-on with OOTDiffusion (Hugging Face Space). Needs a HF token with ZeroGPU quota.
# Usage: python3 run_vton.py APPDIR VTONDIR [max_jobs]
# Writes APPDIR/ai/{model}__{garment}__{color}.webp and skips combos that already exist.
import os, sys, json, glob, shutil, time
from PIL import Image
from gradio_client import Client, handle_file

APP, VT = sys.argv[1], sys.argv[2]
MAXJ = int(sys.argv[3]) if len(sys.argv) > 3 else 999
data = json.loads(open(os.path.join(APP, 'data.js')).read().split('=', 1)[1].rstrip(';\n'))
src = {m['id']: f for m, f in zip(data['models'], ['049447_0.jpg', '051482_0.jpg', 'model_9.png', '049713_0.jpg', '053514_0.jpg',
                                                   'model_8.png', '052472_0.jpg', '053228_0.jpg', '051918_0.jpg', '049205_0.jpg'])}
os.makedirs(os.path.join(APP, 'ai'), exist_ok=True)
REN = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'render')
client = Client('levihsu/OOTDiffusion', hf_token=os.environ.get('HF_TOKEN'), verbose=False)
jobs = []
for g in data['garments']:
    cat = 'Lower-body' if g['cat'] == 'quan' else 'Dress'
    for m in data['models']:
        c = g['colors'][0]['id']
        jobs.append((m['id'], g['key'], c, cat))
done = 0
for mid, key, c, cat in jobs:
    out = os.path.join(APP, 'ai', f'{mid}__{key}__{c}.webp')
    if os.path.exists(out) or done >= MAXJ:
        continue
    garm = os.path.join(REN, f'{key}__{c}.png')
    flat = garm.replace('.png', '_white.jpg')
    im = Image.open(garm).convert('RGBA'); bg = Image.new('RGBA', im.size, 'white'); bg.alpha_composite(im); bg.convert('RGB').save(flat)
    try:
        r = client.predict(handle_file(os.path.join(VT, 'models', src[mid])), handle_file(flat), cat, 1, 20, 2.0, 42, api_name='/process_dc')
        Image.open(r[0]['image']).convert('RGB').resize((600, 800)).save(out, 'WEBP', quality=82)
        done += 1; print('OK', mid, key, c, flush=True)
    except Exception as e:
        print('FAIL', mid, key, c, str(e)[:160], flush=True)
        if 'quota' in str(e).lower():
            break
        time.sleep(5)
