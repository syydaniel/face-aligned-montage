"""Step U5 (optional): month-by-year heatmap of the library (videos, minutes, clips with the person) -> work/heatmap.html"""
import os, json, csv, collections
MROOT = os.environ.get('MONTAGE_ROOT', os.path.abspath('.')); os.chdir(MROOT)
rows = [r for r in csv.DictReader(open('work/inventory_by_date.csv')) if r['date'][:1].isdigit()]
M = collections.defaultdict(lambda: dict(v=0, m=0.0, p=0, me=0))
for r in rows:
    x = M[r['date'][:7]]; x['v'] += int(r['videos']); x['m'] += float(r['minutes']); x['p'] += int(r['photos']); x['me'] += int(r['me'])
years = sorted({k[:4] for k in M}); mx = max(1, max(x['v'] for x in M.values()))
H = ['<!doctype html><meta charset="utf-8"><title>heatmap</title><style>body{font-family:-apple-system,"PingFang SC",sans-serif;background:#111;color:#eee;margin:32px}td{width:64px;height:52px;text-align:center;border-radius:6px}th{color:#999;font-weight:400}</style><table><tr><th></th>' + ''.join(f'<th>{m}月</th>' for m in range(1, 13)) + '</tr>']
for y in years:
    H.append(f'<tr><th>{y}</th>')
    for m in range(1, 13):
        x = M.get(f'{y}-{m:02d}'); a = (x['v'] / mx) ** 0.5 if x else 0
        H.append(f'<td style="background:rgba(255,154,60,{a:.2f})" title="视频 {x["v"] if x else 0} · {round(x["m"]) if x else 0} 分钟 · 照片 {x["p"] if x else 0} · 出镜 {x["me"] if x else 0}">{x["v"] if x else ""}</td>')
    H.append('</tr>')
open('work/heatmap.html', 'w').write('\n'.join(H) + '</table>'); print('months', len(M))
