"""scan photos folder JPGs for the subject's face (YuNet + SFace vs reference); matches -> 1 s 60fps mp4 in assets/open_photos + work/face_photos_<shard>.json (same schema as face_align)"""
import os
MROOT = os.environ.get('MONTAGE_ROOT', os.path.abspath('.'))          # working dir of the montage pipeline
XROOT = os.environ.get('EXPLAINER_ROOT', os.path.abspath('.'))        # working dir of the explainer
MOUT = os.environ.get('MONTAGE_OUT', os.path.join(MROOT, 'out'))
MFINAL = os.environ.get('MONTAGE_FINAL', os.path.join(MOUT, 'opening_4k.mp4'))
import json, cv2, numpy as np, os, sys, subprocess, glob
ROOT = MROOT; SH, NSH = int(sys.argv[1]), int(sys.argv[2])
det = cv2.FaceDetectorYN.create(ROOT + '/work/models/yunet.onnx', '', (320, 320), 0.6, 0.3, 500); rec = cv2.FaceRecognizerSF.create(ROOT + '/work/models/sface.onnx', '')
ref_img = cv2.imread(os.environ['MONTAGE_REF_FACE'])   # one clear frontal photo of the person to keep; det.setInputSize((ref_img.shape[1], ref_img.shape[0])); _, fs = det.detect(ref_img); ref = rec.feature(rec.alignCrop(ref_img, fs[0]))
files = sorted(f for f in glob.glob(os.environ.get('MONTAGE_PHOTOS', 'photos') + '/*') if f.lower().endswith(('.jpg', '.jpeg')))[SH::NSH]
out = {}
for fp in files:
    im = cv2.imread(fp)
    if im is None: continue
    H0, W0 = im.shape[:2]; sc = 800 / max(W0, H0); sm = cv2.resize(im, (int(W0 * sc), int(H0 * sc))) if sc < 1 else im; sc = sm.shape[1] / W0
    det.setInputSize((sm.shape[1], sm.shape[0])); _, faces = det.detect(sm)
    if faces is None: continue
    cands = []; others = 0
    for f in faces:
        sim = float(rec.match(ref, rec.feature(rec.alignCrop(sm, f)), cv2.FaceRecognizerSF_FR_COSINE))
        if sim < 0.32: others += 1 if f[2] * f[3] > 0.004 * sm.shape[0] * sm.shape[1] else 0; continue
        re_, le_, nose = f[4:6], f[6:8], f[8:10]; frontal = 1 - abs((nose[0] - (re_[0] + le_[0]) / 2) / max(1e-3, (le_[0] - re_[0]))) * 2
        cands.append(dict(t=0.2, ex=round(float((re_[0] + le_[0]) / 2 / sc), 1), ey=round(float((re_[1] + le_[1]) / 2 / sc), 1), dist=round(float(np.hypot(le_[0] - re_[0], le_[1] - re_[1]) / sc), 1), ang=round(float(np.degrees(np.arctan2(le_[1] - re_[1], le_[0] - re_[0]))), 1), size=round(float(f[2] / sc / W0), 3), sim=round(sim, 2), frontal=round(float(frontal), 2)))
    if not cands or others: continue   # skip photos with other people's faces
    name = os.path.basename(fp).rsplit('.', 1)[0]; mp4 = f'{ROOT}/assets/open_photos/P_{name}.mp4'
    # 1 s clip at the photo's own resolution (even dims), 16:9 pad not needed: Resolve fits height
    W2, H2 = (W0 // 2) * 2, (H0 // 2) * 2
    if not os.path.exists(mp4): subprocess.run(['ffmpeg', '-v', 'error', '-y', '-loop', '1', '-i', fp, '-t', '1', '-r', '60', '-vf', f'crop={W2}:{H2}', '-c:v', 'libx264', '-crf', '12', '-pix_fmt', 'yuv420p', mp4])
    out['P_' + name] = dict(path=mp4, W=W2, H=H2, fps=60.0, dur=1.0, date='photo', cands=cands[:1])
    print(name, cands[0]['sim'], flush=True)
json.dump(out, open(ROOT + f'/work/face_photos_{SH}.json', 'w')); print('PHOTOS_DONE', len(out))
