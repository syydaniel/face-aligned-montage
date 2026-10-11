"""Step U1: scan a video library -> work/clipmeta.json and 3 review frames per clip (work/review/<cid>_a|b|c.jpg).
cid = running number, category = folder path relative to the library root, date = YYYYMMDD in the file name, else the
container creation_time, else the file mtime.   env: MONTAGE_ROOT, MONTAGE_LIBRARY (folder with your videos)"""
import os, re, json, subprocess, datetime
MROOT = os.environ.get('MONTAGE_ROOT', os.path.abspath('.')); LIB = os.environ['MONTAGE_LIBRARY']
EXT = ('.mp4', '.mov', '.m4v', '.mts', '.avi', '.mkv'); os.makedirs(MROOT + '/work/review', exist_ok=True)
def probe(p):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration:format_tags=creation_time', '-of', 'json', p], capture_output=True, text=True)
    f = json.loads(r.stdout or '{}').get('format', {}); return float(f.get('duration', 0) or 0), (f.get('tags') or {}).get('creation_time', '')
def date_of(p, ct):
    m = re.search(r'(20\d{2})(\d{2})(\d{2})', os.path.basename(p))
    if m: return f'{m.group(1)}-{m.group(2)}-{m.group(3)}'
    if ct: return ct[:10]
    return datetime.date.fromtimestamp(os.path.getmtime(p)).isoformat()
files = sorted(os.path.join(d, f) for d, _, fs in os.walk(LIB) for f in fs if f.lower().endswith(EXT) and not f.startswith('.'))
meta = {}
for cid, p in enumerate(files):
    dur, ct = probe(p); frames = []
    for s, frac in zip('abc', (0.2, 0.5, 0.8)):
        fp = f'{MROOT}/work/review/{cid}_{s}.jpg'
        if not os.path.exists(fp): subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{dur * frac:.2f}', '-i', p, '-frames:v', '1', '-vf', 'scale=640:-2', '-q:v', '4', fp])
        frames.append(fp)
    meta[cid] = dict(path=p, dur=round(dur, 3), cat=os.path.relpath(os.path.dirname(p), LIB), name=os.path.basename(p), date=date_of(p, ct), frames=frames)
    if cid % 50 == 0: print(cid, '/', len(files), flush=True)
json.dump(meta, open(MROOT + '/work/clipmeta.json', 'w'), ensure_ascii=False); print('clips', len(meta))
