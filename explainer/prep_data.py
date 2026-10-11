"""Data for the explainer animations (main venv). Writes into data/."""
import os
MROOT = os.environ.get('MONTAGE_ROOT', os.path.abspath('.'))          # working dir of the montage pipeline
XROOT = os.environ.get('EXPLAINER_ROOT', os.path.abspath('.'))        # working dir of the explainer
MOUT = os.environ.get('MONTAGE_OUT', os.path.join(MROOT, 'out'))
MFINAL = os.environ.get('MONTAGE_FINAL', os.path.join(MOUT, 'opening_4k.mp4'))
import json, glob, subprocess, random, os
import numpy as np, cv2, soundfile as sf
C = MROOT; O = XROOT + '/data'
FINAL = MFINAL
def grab(path, t, w=None, alpha=False):
    vf = [f'scale={w}:-2:flags=lanczos'] if w else []
    pr = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{t:.4f}', '-i', path, '-frames:v', '1'] + (['-vf', ','.join(vf)] if vf else []) + ['-f', 'image2pipe', '-vcodec', 'png', '-pix_fmt', 'rgba' if alpha else 'rgb24', '-'], capture_output=True)
    return cv2.imdecode(np.frombuffer(pr.stdout, np.uint8), cv2.IMREAD_UNCHANGED)
fa = {}
for f in glob.glob(C + '/work/face_align_*.json') + glob.glob(C + '/work/face_photos_*.json'): fa.update(json.load(open(f)))
CL = json.load(open(C + '/work/open_cutlist.json'))
# 1) opening frames 30 fps 1280 wide
if not os.path.exists(O + '/open/01000.jpg'):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', FINAL, '-vf', 'fps=30,scale=1280:-2:flags=lanczos', '-q:v', '3', '-start_number', '0', O + '/open/%05d.jpg'])
print('open frames', len(os.listdir(O + '/open')))
# 2) cut/timeline/score data
sc = json.load(open(C + '/work/three/scores/' + os.environ.get('MONTAGE_SCORE_JOB', 'trailer') + '.json'))
a, sr = sf.read(C + '/work/music/open_mix.wav'); a = a.mean(1) if a.ndim > 1 else a
hop = sr // 100; env = [float(np.sqrt((a[i:i + hop] ** 2).mean())) for i in range(0, len(a) - hop, hop)]; mx = max(env); env = [round(e / mx, 3) for e in env]
items = [dict(tr=i['track'], t=round(i['rf'] / 60, 4), d=round(i['tf'] / 60, 4), sec=i.get('sec', 9), k=i.get('kind', '')) for i in CL['items']]
json.dump(dict(env=env, env_fps=100, bpm=sc['bpm'], beats=sc['beats'], hits=sc['hits'], strong=sc['strong'], drop=CL['drop'], dur=CL['dur'], items=items, flash=[f / 60 for f in CL['flash']], pulse=[p / 60 if isinstance(p, (int, float)) else p for p in CL.get('pulse', [])]), open(O + '/edit.json', 'w'))
print('edit items', len(items))
# 3) exposure pairs: 6 faces spanning luma
pl = {}
for f in glob.glob(C + '/work/pool_landmarks_*.json'): pl.update(json.load(open(f)))
gain = json.load(open(C + '/work/pool_gain.json'))
ks = sorted([k for k in gain if k in pl and not pl[k]['cid'].startswith('P_')], key=lambda k: gain[k]['luma'])
pick = [ks[int(i * (len(ks) - 1) / 5)] for i in range(6)]; ex = []
for n, k in enumerate(pick):
    e = pl[k]; v = fa[e['cid']]; im = grab(v['path'], (e['sf'] + 0.5) / v['fps'])
    ex_, ey = np.mean([e['pts']['eyeL'], e['pts']['eyeR']], 0); d = abs(e['pts']['eyeL'][0] - e['pts']['eyeR'][0]); s = d * 3.2
    x0, y0 = int(ex_ - s / 2), int(ey - s * 0.42); crop = im[max(0, y0):y0 + int(s), max(0, x0):x0 + int(s)]
    crop = cv2.resize(crop, (480, 480), interpolation=cv2.INTER_AREA)
    g = np.clip(np.array(gain[k]['gain'][::-1]) ** 0.7, 0.75, 1.5)    # BGR order, as built
    lin = (crop / 255.0) ** 2.2 * g; fix = (np.clip(lin, 0, 1) ** (1 / 2.2) * 255).astype(np.uint8)
    cv2.imwrite(f'{O}/expo/raw{n}.jpg', crop, [cv2.IMWRITE_JPEG_QUALITY, 90]); cv2.imwrite(f'{O}/expo/fix{n}.jpg', fix, [cv2.IMWRITE_JPEG_QUALITY, 90])
    ex.append(dict(raw=f'data/expo/raw{n}.jpg', fix=f'data/expo/fix{n}.jpg', luma=gain[k]['luma'], gain=[round(x, 2) for x in g[::-1]]))
json.dump(ex, open(O + '/expo.json', 'w')); print('expo', [x['luma'] for x in ex])
# 4) 3D layers (base frame, bars, matte) for 801_2705
v = fa['801']; base = grab(v['path'], (2705 + 0.5) / v['fps'], 1440)
m = grab(C + '/assets/open_mattes/801_2705.mov', 0.0, 1440, alpha=True)
bars = cv2.imread(C + '/assets/bars_3d.png', cv2.IMREAD_UNCHANGED); bars = cv2.resize(bars, (1440, 810), interpolation=cv2.INTER_AREA)
cut = np.dstack([base, m[:, :, 3]]) if m is not None and m.shape[2] == 4 else None
cv2.imwrite(O + '/layers/base.jpg', base, [cv2.IMWRITE_JPEG_QUALITY, 90]); cv2.imwrite(O + '/layers/bars.png', bars)
if cut is not None: cv2.imwrite(O + '/layers/fg.png', cut)
print('layers', base.shape, None if m is None else (m.shape, int(m[:, :, 3].mean())))
# 5) brick atlas 16x16 of 160x90
tiles = sorted(glob.glob(C + '/assets/open_bricks_small/*.jpg'), key=lambda p: int(os.path.basename(p)[:-4])); random.seed(3)
seq = tiles + random.sample(tiles, 256 - len(tiles)); random.shuffle(seq)
atl = np.zeros((90 * 16, 160 * 16, 3), np.uint8)
for i, p in enumerate(seq): atl[(i // 16) * 90:(i // 16 + 1) * 90, (i % 16) * 160:(i % 16 + 1) * 160] = cv2.resize(cv2.imread(p), (160, 90), interpolation=cv2.INTER_AREA)
cv2.imwrite(O + '/bricks_atlas.jpg', atl, [cv2.IMWRITE_JPEG_QUALITY, 88]); print('atlas ok')
# 6) failure frames: bright ending (prev18) vs fixed; white flash search in older versions
T = 25.52
for nm, src, t in [('bright', C + '/out/open_4K_prev18_bright.mp4', T + 0.9), ('fixed', FINAL, T + 0.9)]:
    cv2.imwrite(f'{O}/fail/{nm}.jpg', grab(src, t, 1280), [cv2.IMWRITE_JPEG_QUALITY, 90])
found = None
for ver in ['open_4K_prev14.mp4', 'open_4K_prev12.mp4', 'open_4K_prev10.mp4', 'open_4K_prev6.mp4']:
    pr = subprocess.run(['ffmpeg', '-v', 'error', '-t', '9', '-i', C + '/out/' + ver, '-vf', 'fps=60,scale=64:36', '-f', 'rawvideo', '-pix_fmt', 'gray', '-'], capture_output=True)
    fr = np.frombuffer(pr.stdout, np.uint8).reshape(-1, 36, 64); mean = fr.mean((1, 2))
    hi = [i for i in range(1, len(mean)) if mean[i] > 200 and mean[i] - mean[i - 1] > 60]
    if hi: found = (ver, hi[0] / 60); break
print('white flash', found)
if found:
    cv2.imwrite(O + '/fail/flash.jpg', grab(C + '/out/' + found[0], found[1] + 1 / 120, 1280), [cv2.IMWRITE_JPEG_QUALITY, 90])
    cv2.imwrite(O + '/fail/flash_pre.jpg', grab(C + '/out/' + found[0], found[1] - 3 / 60, 1280), [cv2.IMWRITE_JPEG_QUALITY, 90])
# vertical line: a column that stays brighter than its neighbours across many frames
best = None
for ver in ['open_4K_prev14.mp4', 'open_4K_prev12.mp4', 'open_4K_prev10.mp4', 'open_4K_prev9.mp4', 'open_4K_prev6.mp4']:
    pr = subprocess.run(['ffmpeg', '-v', 'error', '-i', C + '/out/' + ver, '-vf', 'fps=2,scale=1280:720,format=gray', '-f', 'rawvideo', '-'], capture_output=True)
    fr = np.frombuffer(pr.stdout, np.uint8).reshape(-1, 720, 1280).astype(np.float32)
    col = fr.mean(1); hp = col - (np.roll(col, 3, 1) + np.roll(col, -3, 1)) / 2
    persist = (np.abs(hp) > 2.5).mean(0); x = int(np.argmax(persist[5:-5])) + 5
    print(ver, 'col', x, 'persist', round(float(persist[x]), 2))
    if best is None or persist[x] > best[2]: best = (ver, x, float(persist[x]), int(np.argmax(np.abs(hp[:, x]))))
if best:
    ver, x, p, fi = best; cv2.imwrite(O + '/fail/line.jpg', grab(C + '/out/' + ver, fi / 2, 1280), [cv2.IMWRITE_JPEG_QUALITY, 92])
    json.dump(dict(line=dict(ver=ver, x=x, persist=p, t=fi / 2), flash=found), open(O + '/fail.json', 'w'))
print('DONE')
