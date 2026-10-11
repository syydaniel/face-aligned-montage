"""Single source of truth: VO line placement, scenes, chapters, subtitle phrases, sfx cues -> web/timeline.json"""
import os
MROOT = os.environ.get('MONTAGE_ROOT', os.path.abspath('.'))          # working dir of the montage pipeline
XROOT = os.environ.get('EXPLAINER_ROOT', os.path.abspath('.'))        # working dir of the explainer
MOUT = os.environ.get('MONTAGE_OUT', os.path.join(MROOT, 'out'))
MFINAL = os.environ.get('MONTAGE_FINAL', os.path.join(MOUT, 'opening_4k.mp4'))
import json, re, sys
R = XROOT; sys.path.insert(0, R + '/vo')
import os
LANG = os.environ.get('LANG_TL', 'zh')
if LANG == 'en':
    from lines_en import LINES, ORDER
    CH = json.load(open(R + '/vo/EN_A_vlog_male/choice.json'))
else:
    from lines import LINES, ORDER
    CH = json.load(open(R + '/vo/D_lazy_male/choice.json'))
OPEN_DUR = 33.81
CHAP = dict(hook=None, why='01 起因', ghost='02 认脸', mesh='02 认脸', align='03 对齐', gate='04 筛选', loop='04 回测', light='05 光线', music='06 节拍',
            edit='07 搭建', pip='08 花样', split='08 花样', **{'3d': '08 花样'}, wall='09 结尾', **{'break': '09 结尾'}, tunnel='09 结尾', fail='10 翻车', flow='11 回顾', full='完整版', cta=None)
if LANG == 'en': CHAP = dict(hook=None, why='01 The idea', ghost='02 Faces', mesh='02 Faces', align='03 Align', gate='04 Gates', loop='04 Re-check', light='05 Light', music='06 Beats', edit='07 Build', pip='08 Tricks', split='08 Tricks', **{'3d': '08 Tricks'}, wall='09 Ending', **{'break': '09 Ending'}, tunnel='09 Ending', fail='10 Mistakes', flow='11 Pipeline', full='Full cut', cta=None)
PAD = dict(hook=0.2, why=0.5, ghost=0.9, mesh=0.6, align=1.2, gate=0.5, loop=0.5, light=0.7, music=0.9, edit=0.6, pip=0.6, split=0.6, **{'3d': 0.8}, wall=0.9, **{'break': 0.2}, tunnel=0.9, fail=0.6, flow=0.9, full=0.0, cta=1.6)
EXTRA_AFTER = {'end4': 1.5, 'hook3': 0.15, 'full': 0.35, 'lm2': 0.6, 'gate2': 0.4, 'end3': 0.3}
t = 0.25; lines = []; prev_scene = None; scenes = []
for k in ORDER:
    sc, text = LINES[k]
    if sc != prev_scene:
        if prev_scene is not None:
            t += PAD[prev_scene] + 0.45
        scenes.append(dict(id=sc, t0=max(0.0, t - 0.35), chap=CHAP[sc]))
        prev_scene = sc
    d = CH[k]['dur']; lines.append(dict(key=k, scene=sc, t0=round(t, 3), t1=round(t + d, 3), text=text, file=CH[k]['file']))
    t += d + 0.3 + EXTRA_AFTER.get(k, 0)
    if k == 'full':
        t += OPEN_DUR + 0.6 - 0.3
for i, s in enumerate(scenes): s['t1'] = scenes[i + 1]['t0'] if i + 1 < len(scenes) else round(t + PAD['cta'], 3)
full = [s for s in scenes if s['id'] == 'full'][0]; fl = [l for l in lines if l['key'] == 'full'][0]
full['open_t0'] = round(fl['t1'] + 0.35, 3); full['open_t1'] = round(full['open_t0'] + OPEN_DUR, 3)
# subtitle phrases
subs = []
for l in lines:
    if LANG == 'en':
        parts = [p.strip() + ' ' for p in re.split(r'(?<=[.?!,;:])\s+', l['text']) if p.strip()]
        merged = []
        for p in parts:
            if merged and (len(merged[-1].split()) < 4 or len((merged[-1] + p).split()) <= 9): merged[-1] += p
            else: merged.append(p)
        w = [len(p) + (6 if p.rstrip()[-1] in '.?!' else 3) for p in merged]; tot = sum(w); a = l['t0']; D = l['t1'] - l['t0']
        for p, wi in zip(merged, w):
            b = a + D * wi / tot; subs.append(dict(t0=round(a, 3), t1=round(b, 3), text=p.strip().rstrip(',;:'), key=l['key'])); a = b
        continue
    parts = [p for p in re.split(r'(?<=[，。？！、])', l['text']) if p.strip()]
    merged = []
    for p in parts:
        if merged and len(re.sub(r'[，。？！、]', '', merged[-1])) < 5: merged[-1] += p
        else: merged.append(p)
    w = [len(re.sub(r'[，。？！、]', '', p)) + (1.2 if p[-1] in '，、' else 2.0 if p[-1] in '。？！' else 0) for p in merged]; tot = sum(w); a = l['t0']; D = l['t1'] - l['t0']
    for p, wi in zip(merged, w):
        b = a + D * wi / tot; subs.append(dict(t0=round(a, 3), t1=round(b, 3), text=re.sub(r'[，。、]$', '', p), key=l['key'])); a = b
# cues for sfx (scene transitions); scene-specific cues are added by the page via the same formulas
cues = [dict(t=s['t0'] + 0.3, kind='whoosh') for s in scenes[1:] if s['id'] not in ('full',)]
TOTAL = round(scenes[-1]['t1'], 3)
json.dump(dict(total=TOTAL, fps=30, lines=lines, scenes=scenes, subs=subs, cues=cues), open(R + ('/web/timeline_en.json' if LANG == 'en' else '/web/timeline.json'), 'w'), ensure_ascii=False, indent=0)
print('total', TOTAL, 'scenes', len(scenes))
for s in scenes: print(f"{s['id']:7s} {s['t0']:7.2f} {s['t1']:7.2f} {s['t1']-s['t0']:5.1f}")
