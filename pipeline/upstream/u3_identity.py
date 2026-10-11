"""Step U3: identity check of every sampled frame against reference photo(s) of the person (OpenCV YuNet + SFace, cosine).
-> work/identity.json  {cid: [{f, n, sim, ...}]}, work/user_clips.json (clips that are clearly the person),
   work/bad_clips.json (clips where a different person appears: any single-face sample with sim < 0.25)
env: MONTAGE_REF_FACE  one or more reference images, comma-separated (clear frontal photos of the person to keep)"""
import os, glob, json, cv2, numpy as np
MROOT = os.environ.get('MONTAGE_ROOT', os.path.abspath('.')); os.chdir(MROOT)
det = cv2.FaceDetectorYN.create('work/models/yunet.onnx', '', (320, 320), 0.7, 0.3, 5000); rec = cv2.FaceRecognizerSF.create('work/models/sface.onnx', '')
def faces(img): h, w = img.shape[:2]; det.setInputSize((w, h)); _, f = det.detect(img); return [] if f is None else f
def embed(img, f): return rec.feature(rec.alignCrop(img, f))
refs = []
for p in os.environ['MONTAGE_REF_FACE'].split(','):
    img = cv2.imread(p.strip()); img = cv2.resize(img, (1280, int(img.shape[0] * 1280 / img.shape[1]))); fs = faces(img)
    if len(fs): refs.append(embed(img, fs[np.argmax(fs[:, 2] * fs[:, 3])]))
assert refs, 'no face found in MONTAGE_REF_FACE'
res = {}
for fp in sorted(glob.glob('work/facesamp/*.jpg')):
    cid = int(os.path.basename(fp).split('_')[0]); img = cv2.imread(fp)
    if img is None: continue
    fs = faces(img)
    if len(fs) != 1: res.setdefault(cid, []).append(dict(f=fp, n=len(fs))); continue
    f = fs[0]; sim = max(float(rec.match(embed(img, f), r, cv2.FaceRecognizerSF_FR_COSINE)) for r in refs); H, Wd = img.shape[:2]
    res.setdefault(cid, []).append(dict(f=fp, n=1, sim=round(sim, 3), cx=float((f[0] + f[2] / 2) / Wd), cy=float((f[1] + f[3] / 2) / H), w=float(f[2] / Wd)))
json.dump({str(k): v for k, v in res.items()}, open('work/identity.json', 'w'), indent=0)
good = {k: [x for x in v if x['n'] == 1 and x.get('sim', 0) >= 0.42] for k, v in res.items()}
bad = sorted(str(k) for k, v in res.items() if any(x['n'] == 1 and x.get('sim', 1) < 0.25 for x in v))
user = {str(k): v for k, v in good.items() if v and str(k) not in bad}
json.dump(user, open('work/user_clips.json', 'w'), indent=0); json.dump(bad, open('work/bad_clips.json', 'w'))
print('clips that are clearly the person:', len(user), '| clips with someone else:', len(bad))
