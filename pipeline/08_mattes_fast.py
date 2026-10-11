"""AI subject mattes (rembg isnet) for the 裸眼3D cuts (sec==2): source frames -> RGBA -> ProRes 4444 with alpha, 4K"""
import os
MROOT = os.environ.get('MONTAGE_ROOT', os.path.abspath('.'))          # working dir of the montage pipeline
XROOT = os.environ.get('EXPLAINER_ROOT', os.path.abspath('.'))        # working dir of the explainer
MOUT = os.environ.get('MONTAGE_OUT', os.path.join(MROOT, 'out'))
MFINAL = os.environ.get('MONTAGE_FINAL', os.path.join(MOUT, 'opening_4k.mp4'))
import json, subprocess, os, glob, numpy as np
from rembg import remove, new_session
from PIL import Image
ROOT = MROOT; CL = json.load(open(ROOT + '/work/open_cutlist.json')); fa = {}
for f in glob.glob(ROOT + '/work/face_align_*.json') + glob.glob(ROOT + '/work/face_photos_*.json'): fa.update(json.load(open(f)))
sess = new_session('isnet-general-use'); made = []
for c in CL['items']:
    if c['sec'] != 3 or c['track'] != 1: continue
    v = fa[str(c['cid'])]; out = f"{ROOT}/assets/open_mattes/{c['cid']}_{c['sf']}.mov"
    if os.path.exists(out): made.append(out); continue
    tmp = f"{ROOT}/assets/open_mattes/_tmp_{c['cid']}_{c['sf']}"; os.makedirs(tmp, exist_ok=True)
    n = c['tf'] + 2; t = c['sf'] / v['fps']
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{t:.4f}', '-i', v['path'], '-frames:v', str(n), '-vf', 'scale=1920:-2', f'{tmp}/%04d.png'])
    for fp in sorted(glob.glob(tmp + '/*.png')):
        o = remove(Image.open(fp).convert('RGB'), session=sess); o = o.resize((3840, 2160), Image.LANCZOS)
        arr = np.asarray(o).copy(); a = arr[..., 3]
        import cv2
        a = cv2.erode(a, np.ones((5, 5), np.uint8), iterations=1); a = cv2.GaussianBlur(a, (0, 0), 2.0)   # pull the edge in and feather it: no bright fringe against the black bars
        arr[..., 3] = a; o = Image.fromarray(arr, 'RGBA'); o.save(fp)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-framerate', '60', '-i', f'{tmp}/%04d.png', '-c:v', 'prores_ks', '-profile:v', '4444', '-pix_fmt', 'yuva444p10le', out])
    for fp in glob.glob(tmp + '/*.png'): os.remove(fp)
    os.rmdir(tmp); made.append(out); print(os.path.basename(out), n, flush=True)
json.dump(made, open(ROOT + '/work/open_mattes.json', 'w')); print('MATTES_DONE', len(made))
