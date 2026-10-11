"""aligned face 'bricks': every usable candidate (QA err<=40) -> 1920x1080 jpg with the face aligned exactly as in the main timeline (eyes at (0.5, 0.463) of the tile, eye distance 0.1224 of width)"""
import os
MROOT = os.environ.get('MONTAGE_ROOT', os.path.abspath('.'))          # working dir of the montage pipeline
XROOT = os.environ.get('EXPLAINER_ROOT', os.path.abspath('.'))        # working dir of the explainer
MOUT = os.environ.get('MONTAGE_OUT', os.path.join(MROOT, 'out'))
MFINAL = os.environ.get('MONTAGE_FINAL', os.path.join(MOUT, 'opening_4k.mp4'))
import json, glob, subprocess, cv2, numpy as np, math, sys, os
sys.argv = ['x']; ROOT = MROOT
src = open(os.path.join(os.environ.get('MONTAGE_PIPELINE', os.path.dirname(os.path.abspath(__file__))), '06_edl.py')).read(); g = {}; exec(src[:src.index('# ---- pool with quality gate ----')], g)
LM, TARGET, fit, fa = g['LM'], g['TARGET'], g['fit'], g['fa']; TW, TH = 3840, 2160
QA = json.load(open(ROOT + '/work/pool_qa.json')); GAIN = json.load(open(ROOT + '/work/pool_gain.json'))
KEYS6 = ['eyeR', 'eyeL', 'nose', 'mouthR', 'mouthL', 'chin']; out = []; k = 0.5
for key, e in LM.items():
    q = QA.get(key); err = q['err'] if isinstance(q, dict) else 999
    if err > 40 or e['yaw'] is None or abs(e['yaw']) > 14 or abs(e['pitch']) > 14: continue
    v = fa[str(e['cid'])]; props = q['props'] if isinstance(q, dict) and q.get('props') else fit(e, KEYS6)[0]
    name = f"{e['cid']}_{e['sf']}.jpg"; fp = f'{ROOT}/assets/open_bricks/{name}'
    if not os.path.exists(fp):
        pr = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f"{(e['sf'] + 0.5) / v['fps']:.4f}", '-i', v['path'], '-frames:v', '1', '-f', 'image2pipe', '-vcodec', 'png', '-'], capture_output=True)
        im = cv2.imdecode(np.frombuffer(pr.stdout, np.uint8), 1)
        if im is None: continue
        H0, W0 = im.shape[:2]; s0 = TH / H0; z = props['ZoomX']; phi = -math.radians(props['RotationAngle']); c_out = np.array([TW / 2 + props['Pan'], TH / 2 - props['Tilt']]) * k; a = z * s0 * k
        M = np.array([[a * math.cos(phi), -a * math.sin(phi), 0], [a * math.sin(phi), a * math.cos(phi), 0]]); M[:, 2] = c_out - M[:, :2] @ np.array([W0 / 2, H0 / 2])
        o = cv2.warpAffine(im, M, (1920, 1080), flags=cv2.INTER_AREA, borderMode=cv2.BORDER_REFLECT)
        gn = np.array(GAIN.get(key, {}).get('gain', [1, 1, 1]))[::-1] ** 0.7; o = np.clip(o.astype(np.float32) * gn, 0, 255).astype(np.uint8)
        cv2.imwrite(fp, o, [cv2.IMWRITE_JPEG_QUALITY, 92])
    out.append(dict(key=key, file=fp, date=v['date'], cid=e['cid'], err=err))
json.dump(out, open(ROOT + '/work/bricks.json', 'w')); print('bricks', len(out))
