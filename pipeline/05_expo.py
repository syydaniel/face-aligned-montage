"""per-candidate exposure / white-balance gains measured on the face (landmark box) -> adds 'gain' to work/pool_gain.json"""
import os
MROOT = os.environ.get('MONTAGE_ROOT', os.path.abspath('.'))          # working dir of the montage pipeline
XROOT = os.environ.get('EXPLAINER_ROOT', os.path.abspath('.'))        # working dir of the explainer
MOUT = os.environ.get('MONTAGE_OUT', os.path.join(MROOT, 'out'))
MFINAL = os.environ.get('MONTAGE_FINAL', os.path.join(MOUT, 'opening_4k.mp4'))
import json, glob, subprocess, cv2, numpy as np
ROOT = MROOT; qa = json.load(open(ROOT + '/work/pool_qa.json')); LM = {}
for f in glob.glob(ROOT + '/work/pool_landmarks_*.json'): LM.update(json.load(open(f)))
fa = {}
for f in glob.glob(ROOT + '/work/face_align_*.json') + glob.glob(ROOT + '/work/face_photos_*.json'): fa.update(json.load(open(f)))
stats = {}
for key, err in qa.items():
    if err > 25: continue
    e = LM[key]; v = fa[str(e['cid'])]
    pr = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f"{(e['sf'] + 0.5) / v['fps']:.4f}", '-i', v['path'], '-frames:v', '1', '-vf', 'scale=960:-2', '-f', 'image2pipe', '-vcodec', 'png', '-'], capture_output=True)
    im = cv2.imdecode(np.frombuffer(pr.stdout, np.uint8), 1)
    if im is None: continue
    sc = im.shape[1] / e['W']; p = e['pts']; xs = [p[k][0] * sc for k in ('eyeR', 'eyeL', 'mouthR', 'mouthL')]; ys = [p[k][1] * sc for k in ('eyeR', 'eyeL', 'mouthR', 'mouthL', 'chin')]
    x0, x1 = int(min(xs)), int(max(xs)); y0, y1 = int(min(ys) - (max(ys) - min(ys)) * 0.15), int(max(ys))
    face = im[max(0, y0):y1, max(0, x0):x1].astype(np.float32) / 255.0
    if face.size == 0: continue
    lin = face ** 2.2; m = lin.reshape(-1, 3).mean(0)[::-1]   # RGB linear means
    stats[key] = dict(rgb=[float(x) for x in m], luma=float(0.2126 * m[0] + 0.7152 * m[1] + 0.0722 * m[2]))
# targets: median skin ratios of the pool, luma target 0.30 (linear) ~ 0.58 sRGB
R = np.array([s['rgb'] for s in stats.values()]); ratio = np.median(R / R.mean(1, keepdims=True), 0); LT = 0.30
out = {}
for key, s in stats.items():
    m = np.array(s['rgb']); g_l = LT / max(1e-4, s['luma']); g_wb = ratio / (m / m.mean())           # per-channel gain to the pool skin ratio
    g = np.clip(g_l * g_wb, 0.55, 2.2) ** 0.85                                                         # soften (don't fully flatten the look)
    out[key] = dict(gain=[round(float(x), 3) for x in g], luma=round(s['luma'], 3))
json.dump(out, open(ROOT + '/work/pool_gain.json', 'w')); L = [s['luma'] for s in stats.values()]; print('gains', len(out), 'face luma range %.2f-%.2f median %.2f' % (min(L), max(L), float(np.median(L))))
