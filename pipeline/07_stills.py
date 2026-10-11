"""4K aligned stills for the picture-in-picture layers: the exact landmark frame warped by the (QA-corrected) full-face transform -> assets/open_stills/<key>.mp4 (1 s, 60 fps).
A window cropped from such a still is pixel-exact with the template, so PiP layers never drift."""
import os
MROOT = os.environ.get('MONTAGE_ROOT', os.path.abspath('.'))          # working dir of the montage pipeline
XROOT = os.environ.get('EXPLAINER_ROOT', os.path.abspath('.'))        # working dir of the explainer
MOUT = os.environ.get('MONTAGE_OUT', os.path.join(MROOT, 'out'))
MFINAL = os.environ.get('MONTAGE_FINAL', os.path.join(MOUT, 'opening_4k.mp4'))
import json, glob, subprocess, cv2, numpy as np, math, sys, os
sys.argv = ['x']; ROOT = MROOT
src = open(os.path.join(os.environ.get('MONTAGE_PIPELINE', os.path.dirname(os.path.abspath(__file__))), '06_edl.py')).read(); g = {}; exec(src[:src.index('# ---- pool with quality gate ----')], g)
LM, TARGET, fit, fa = g['LM'], g['TARGET'], g['fit'], g['fa']; TW, TH = 3840, 2160
QA = json.load(open(ROOT + '/work/pool_qa.json')); GAIN = json.load(open(ROOT + '/work/pool_gain.json')); os.makedirs(ROOT + '/assets/open_stills', exist_ok=True)
keys = sys.argv[1:] if len(sys.argv) > 1 else [k for k, q in QA.items() if isinstance(q, dict) and q['err'] <= 25]
made = 0
for key in keys:
    e = LM[key]; q = QA.get(key); v = fa[str(e['cid'])]; out = f"{ROOT}/assets/open_stills/{key.replace('|', '_')}.mp4"
    if os.path.exists(out): continue
    props = q['props'] if isinstance(q, dict) and q.get('props') else fit(e, ['eyeR', 'eyeL', 'nose', 'mouthR', 'mouthL', 'chin'])[0]
    pr = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f"{(e['sf'] + 0.5) / v['fps']:.4f}", '-i', v['path'], '-frames:v', '1', '-f', 'image2pipe', '-vcodec', 'png', '-'], capture_output=True)
    im = cv2.imdecode(np.frombuffer(pr.stdout, np.uint8), 1)
    if im is None: continue
    H0, W0 = im.shape[:2]; s0 = TH / H0; z = props['ZoomX']; phi = -math.radians(props['RotationAngle']); c_out = np.array([TW / 2 + props['Pan'], TH / 2 - props['Tilt']]); a = z * s0
    M = np.array([[a * math.cos(phi), -a * math.sin(phi), 0], [a * math.sin(phi), a * math.cos(phi), 0]]); M[:, 2] = c_out - M[:, :2] @ np.array([W0 / 2, H0 / 2])
    o = cv2.warpAffine(im, M, (TW, TH), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REFLECT)
    gn = np.array(GAIN.get(key, {}).get('gain', [1, 1, 1]))[::-1] ** 0.7; o = np.clip(o.astype(np.float32) * gn, 0, 255).astype(np.uint8)
    cv2.imwrite(out[:-4] + '.png', o); subprocess.run(['ffmpeg', '-v', 'error', '-y', '-loop', '1', '-i', out[:-4] + '.png', '-t', '1', '-r', '60', '-c:v', 'libx264', '-crf', '10', '-pix_fmt', 'yuv420p', out]); os.remove(out[:-4] + '.png'); made += 1
print('stills made', made, 'total', len(glob.glob(ROOT + '/assets/open_stills/*.mp4')))
