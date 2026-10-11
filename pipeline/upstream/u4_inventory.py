"""Step U4: source lists for the montage.
-> work/sources.csv          cid,date,dur,cat,sim,verdict,path   (verdict 是我 / 含其他人（不用） / 疑似我（相似度低）); set MONTAGE_SOURCES_CSV to it
   work/inventory_by_date.csv date,videos,minutes,photos,me,content
   work/inventory.html        timeline by day with review frames, for a manual pass over the verdicts
Edit the verdict column by hand if the review shows a mistake; 01_face_align.py only scans rows with verdict 是我.
env: MONTAGE_PHOTOS (optional, photos are counted per day by file mtime)"""
import os, csv, json, base64, io, collections, datetime
from PIL import Image
MROOT = os.environ.get('MONTAGE_ROOT', os.path.abspath('.')); os.chdir(MROOT)
cm = json.load(open('work/clipmeta.json')); ident = json.load(open('work/identity.json')); bad = set(json.load(open('work/bad_clips.json')))
me = []
for k, v in cm.items():
    sims = [x.get('sim', 0) for x in ident.get(k, [])]; mx = max(sims) if sims else None
    if k in bad: verdict = '含其他人（不用）'
    elif mx is not None and mx >= 0.36: verdict = '是我'
    elif mx is not None: verdict = '疑似我（相似度低）'
    else: continue
    me.append(dict(cid=int(k), date=v['date'], dur=round(v['dur'], 1), cat=v['cat'], sim=round(mx, 2), verdict=verdict, path=v['path'], frame=(v['frames'][1] if v.get('frames') else '')))
me.sort(key=lambda r: (r['verdict'] != '是我', r['date'], r['cid']))
with open('work/sources.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['cid', 'date', 'dur', 'cat', 'sim', 'verdict', 'path']); w.writeheader(); [w.writerow({a: r[a] for a in w.fieldnames}) for r in me]
pdays = collections.Counter()
if os.environ.get('MONTAGE_PHOTOS'):
    for e in os.scandir(os.environ['MONTAGE_PHOTOS']):
        if e.is_file() and e.name.lower().rsplit('.', 1)[-1] in ('jpg', 'jpeg', 'heic', 'png', 'nef', 'arw', 'dng'): pdays[datetime.date.fromtimestamp(e.stat().st_mtime).isoformat()] += 1
vdays = collections.defaultdict(list)
for k, v in cm.items(): vdays[v['date']].append(v)
mine = collections.Counter(r['date'] for r in me if r['verdict'] == '是我'); rows = []
for d in sorted(set(vdays) | set(pdays)):
    vs = vdays.get(d, []); cats = collections.Counter(v['cat'].split('/')[-1] for v in vs)
    rows.append(dict(date=d, videos=len(vs), minutes=round(sum(v['dur'] for v in vs) / 60, 1), photos=pdays.get(d, 0), me=mine.get(d, 0), content='、'.join(f'{a}×{b}' for a, b in cats.most_common(4))))
with open('work/inventory_by_date.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
def b64(p):
    try: im = Image.open(p); im.thumbnail((200, 200)); b = io.BytesIO(); im.convert('RGB').save(b, 'JPEG', quality=70); return 'data:image/jpeg;base64,' + base64.b64encode(b.getvalue()).decode()
    except Exception: return ''
H = ['<!doctype html><meta charset="utf-8"><title>sources</title><style>body{font-family:-apple-system,"PingFang SC",sans-serif;background:#111;color:#eee;margin:24px}.g{display:flex;flex-wrap:wrap;gap:8px}.c{width:210px;font-size:12px}.c img{width:200px}</style>']
for verdict in ('是我', '疑似我（相似度低）', '含其他人（不用）'):
    rs = [r for r in me if r['verdict'] == verdict]; H.append(f'<h2>{verdict} · {len(rs)}</h2><div class="g">')
    H += [f'<div class="c"><img src="{b64(r["frame"])}"><br>#{r["cid"]} {r["date"]} {r["dur"]}s sim {r["sim"]}<br>{os.path.basename(r["path"])}</div>' for r in rs]; H.append('</div>')
open('work/inventory.html', 'w').write('\n'.join(H)); print('sources', len(me), 'of which 是我', sum(1 for r in me if r['verdict'] == '是我'))
