"""For each subject-on-camera clip: sample frames, detect faces (YuNet), verify identity (SFace vs the user's reference), keep frontal large faces -> work/face_align.json {cid: {path,W,H,fps,dur,cands:[{t,ex,ey,dist,ang,size,sim}]}}"""
import os
MROOT = os.environ.get('MONTAGE_ROOT', os.path.abspath('.'))          # working dir of the montage pipeline
XROOT = os.environ.get('EXPLAINER_ROOT', os.path.abspath('.'))        # working dir of the explainer
MOUT = os.environ.get('MONTAGE_OUT', os.path.join(MROOT, 'out'))
MFINAL = os.environ.get('MONTAGE_FINAL', os.path.join(MOUT, 'opening_4k.mp4'))
import json, subprocess, cv2, numpy as np, csv, os, sys
SHARD, NSH = (int(sys.argv[1]), int(sys.argv[2])) if len(sys.argv) > 2 else (0, 1)
ROOT = MROOT
det = cv2.FaceDetectorYN.create(ROOT + '/work/models/yunet.onnx', '', (320, 320), 0.6, 0.3, 500)
rec = cv2.FaceRecognizerSF.create(ROOT + '/work/models/sface.onnx', '')
ref_img = cv2.imread(os.environ['MONTAGE_REF_FACE'])   # one clear frontal photo of the person to keep; det.setInputSize((ref_img.shape[1], ref_img.shape[0])); _, fs = det.detect(ref_img)
ref = rec.feature(rec.alignCrop(ref_img, fs[0])) if fs is not None else None; print('reference ok', ref is not None)
rows = [r for r in csv.DictReader(open(os.environ['MONTAGE_SOURCES_CSV'])) if r['verdict'] == '是我'][SHARD::NSH]
out = {}
for r in rows:
    p = r['path']; pr = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height,r_frame_rate,duration', '-of', 'json', p], capture_output=True, text=True); st = json.loads(pr.stdout)['streams'][0]
    W, H = int(st['width']), int(st['height']); a, b = st['r_frame_rate'].split('/'); fps = float(a) / float(b); dur = float(r['dur'])
    n = min(14, max(5, int(dur * 1.2))); ts = [dur * (i + 0.5) / n for i in range(n)]; cands = []
    for t in ts:
        pr = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{t:.3f}', '-i', p, '-frames:v', '1', '-vf', 'scale=640:-2', '-f', 'image2pipe', '-vcodec', 'png', '-'], capture_output=True)
        im = cv2.imdecode(np.frombuffer(pr.stdout, np.uint8), cv2.IMREAD_COLOR)
        if im is None: continue
        det.setInputSize((im.shape[1], im.shape[0])); _, faces = det.detect(im)
        if faces is None: continue
        sc = W / im.shape[1]
        for f in faces:
            x, y, w, h = f[:4]; re_, le_ = f[4:6], f[6:8]; nose = f[8:10]
            sim = float(rec.match(ref, rec.feature(rec.alignCrop(im, f)), cv2.FaceRecognizerSF_FR_COSINE)) if ref is not None else 1.0
            if sim < 0.30: continue
            ex, ey = (re_[0] + le_[0]) / 2 * sc, (re_[1] + le_[1]) / 2 * sc; dist = float(np.hypot(le_[0] - re_[0], le_[1] - re_[1])) * sc; ang = float(np.degrees(np.arctan2(le_[1] - re_[1], le_[0] - re_[0])))
            frontal = 1 - abs((nose[0] - (re_[0] + le_[0]) / 2) / max(1e-3, (le_[0] - re_[0]))) * 2
            cands.append(dict(t=round(t, 3), ex=round(float(ex), 1), ey=round(float(ey), 1), dist=round(dist, 1), ang=round(ang, 1), size=round(float(w * sc / W), 3), sim=round(sim, 2), frontal=round(float(frontal), 2)))
    out[r['cid']] = dict(path=p, W=W, H=H, fps=round(fps, 3), dur=dur, date=r['date'], cands=cands); print(r['cid'], len(cands), flush=True)
json.dump(out, open(ROOT + f'/work/face_align_{SHARD}.json', 'w')); print('DONE', sum(1 for v in out.values() if v['cands']), 'clips with faces')
