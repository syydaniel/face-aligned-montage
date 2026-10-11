import os
MROOT = os.environ.get('MONTAGE_ROOT', os.path.abspath('.'))          # working dir of the montage pipeline
XROOT = os.environ.get('EXPLAINER_ROOT', os.path.abspath('.'))        # working dir of the explainer
MOUT = os.environ.get('MONTAGE_OUT', os.path.join(MROOT, 'out'))
MFINAL = os.environ.get('MONTAGE_FINAL', os.path.join(MOUT, 'opening_4k.mp4'))
import json, glob, subprocess, random, os
import numpy as np, cv2
C = MROOT; O = XROOT + '/data'; FINAL = MFINAL
if not os.path.exists(O + '/sq/01000.jpg'):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', FINAL, '-vf', 'fps=30,crop=2160:2160:840:0,scale=1080:1080:flags=lanczos', '-q:v', '2', '-start_number', '0', O + '/sq/%05d.jpg'])
print('sq', len(os.listdir(O + '/sq')))
def grab(path, t, w=320):
    pr = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{max(0, t):.3f}', '-i', path, '-frames:v', '1', '-vf', f'scale={w}:-2', '-f', 'image2pipe', '-vcodec', 'png', '-pix_fmt', 'rgb24', '-'], capture_output=True)
    return cv2.imdecode(np.frombuffer(pr.stdout, np.uint8), 1) if pr.stdout else None
# version thumbs at t=12.0
vs = sorted(glob.glob(C + '/out/open_4K_prev*.mp4'), key=lambda p: int(''.join(ch for ch in os.path.basename(p).split('prev')[1].split('_')[0].split('.')[0] if ch.isdigit()) or 1))
n = 0
for p in vs + [FINAL]:
    if os.path.getsize(p) < 1e6 or 'bright' in p: continue
    im = grab(p, 12.0, 480)
    if im is None: continue
    cv2.imwrite(f'{O}/vers/v{n:02d}.jpg', im, [cv2.IMWRITE_JPEG_QUALITY, 85]); n += 1
print('versions', n)
# raw atlas of source material
fa = {}
for f in glob.glob(C + '/work/face_align_*.json') + glob.glob(C + '/work/face_photos_*.json'): fa.update(json.load(open(f)))
vids = [k for k in fa if not k.startswith('P_')]; phs = [k for k in fa if k.startswith('P_')]
print('videos', len(vids), 'photos', len(phs))
tiles = []
for k in vids + phs:
    v = fa[k]; p = v['path']
    if p.lower().endswith(('.jpg', '.jpeg', '.png')):
        im = cv2.imread(p); 
        if im is None: continue
        h, w = im.shape[:2]; s = 160 / w; im = cv2.resize(im, (160, int(h * s)), interpolation=cv2.INTER_AREA)
    else:
        t = v['cands'][0]['t'] if v.get('cands') else v.get('dur', 2) / 2
        im = grab(p, t, 160)
        if im is None: continue
    h = im.shape[0]
    if h > 90: y0 = (h - 90) // 2; im = im[y0:y0 + 90]
    elif h < 90: im = cv2.resize(im, (int(160 * 90 / h), 90))[:, :160]
    tiles.append(im)
random.seed(5); random.shuffle(tiles); cols = 16; rows = (len(tiles) + cols - 1) // cols
atl = np.zeros((rows * 90, cols * 160, 3), np.uint8)
for i, im in enumerate(tiles): atl[(i // cols) * 90:(i // cols) * 90 + 90, (i % cols) * 160:(i % cols) * 160 + 160] = im[:90, :160]
cv2.imwrite(O + '/raw_atlas.jpg', atl, [cv2.IMWRITE_JPEG_QUALITY, 85]); json.dump(dict(n=len(tiles), cols=cols, rows=rows, videos=len(vids), photos=len(phs)), open(O + '/raw_atlas.json', 'w'))
print('atlas', len(tiles), rows)
