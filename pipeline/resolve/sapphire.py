import os
MROOT = os.environ.get('MONTAGE_ROOT', os.path.abspath('.'))          # working dir of the montage pipeline
XROOT = os.environ.get('EXPLAINER_ROOT', os.path.abspath('.'))        # working dir of the explainer
MOUT = os.environ.get('MONTAGE_OUT', os.path.join(MROOT, 'out'))
MFINAL = os.environ.get('MONTAGE_FINAL', os.path.join(MOUT, 'opening_4k.mp4'))
# Sapphire pass on a duplicate timeline OPEN_SAPPHIRE (exec in run_script_unsafe). Items chosen by record frame from the cut list.
import json
CL = json.load(open(MROOT + '/work/open_cutlist.json')); base = sorted([i for i in CL['items'] if i['track'] == 1], key=lambda x: x['rf'])
fu = resolve.Fusion(); SAP = {}
for _k, _v in (fu.GetRegList(fu.CT_Tool) if hasattr(fu, 'CT_Tool') else fu.GetRegList(4)).items():
    try:
        _n = _v.ID if hasattr(_v, 'ID') else str(_v)
        if 'sapphire' in _n.lower(): SAP[_n.split('.')[-1]] = _n
    except Exception: pass
mp = project.GetMediaPool(); src = [project.GetTimelineByIndex(i) for i in range(1, project.GetTimelineCount() + 1) if project.GetTimelineByIndex(i).GetName() == 'OPEN'][0]
for i in range(1, project.GetTimelineCount() + 1):
    t = project.GetTimelineByIndex(i)
    if t.GetName() == 'OPEN_SAPPHIRE': mp.DeleteTimelines([t]); break
tl = src.DuplicateTimeline('OPEN_SAPPHIRE'); project.SetCurrentTimeline(tl); S = tl.GetStartFrame()
byrf = {it.GetStart() - S: it for it in tl.GetItemListInTrack('video', 1)}
strongF = set(CL['flash']); errs = []; done = []
def setp(t, k, v):
    try: t[k] = v
    except Exception as e: errs.append(f'{k}:{str(e)[:40]}')
def anim(t, k, keys):
    try:
        t[k] = comp.BezierSpline()
        for f, v in keys.items(): t[k][f] = v
    except Exception as e: errs.append(f'{k}:{str(e)[:40]}')
plan = []
drop_strong = [c for c in base if c['sec'] == 1 and c['rf'] in strongF]; clim_strong = [c for c in base if c['sec'] == 4 and c['rf'] in strongF and c['tf'] >= 3]
for k, c in enumerate(drop_strong[::2][:6]): plan.append((c, 'S_WarpChroma'))
for k, c in enumerate(clim_strong[::2][:5]): plan.append((c, ['S_Shake', 'S_Glow', 'S_VHSDamage', 'S_Shake', 'S_DigitalDamage'][k]))
plan += [(c, 'S_FilmEffect') for c in base if c['sec'] == 0 and c['tf'] >= 12][:3]
plan += [(c, 'tunnel') for c in base if c['sec'] == 8]
for c, fx in plan[CHUNK[0]:CHUNK[1]]:
    it = byrf.get(c['rf'])
    if it is None: continue
    comp = it.AddFusionComp() or it.GetFusionCompByIndex(it.GetFusionCompCount())
    mi0 = comp.FindTool('MediaIn1'); mo = comp.FindTool('MediaOut1'); n = c['tf']
    try: _o = mo.Input.GetConnectedOutput(); mi = _o.GetTool() if _o else mi0
    except Exception: mi = mi0
    if any(t.ID.startswith('Sapphire') or 'sapphire' in t.ID.lower() for t in comp.GetToolList(False).values()): continue
    if fx == 'S_WarpChroma': t = comp.AddTool(SAP[fx]); t.Input = mi; mo.Input = t; anim(t, 'warp_amount', {0: 1.4, min(n - 1, 4): 0.0}); setp(t, 'to_z_dist', 1.08)
    elif fx == 'S_Shake': t = comp.AddTool(SAP[fx]); t.Input = mi; mo.Input = t; anim(t, 'amplitude', {0: 0.5, min(n - 1, 5): 0.0}); setp(t, 'frequency', 9.0); setp(t, 'motion_blur', 1.0)
    elif fx == 'S_Glow': t = comp.AddTool(SAP[fx]); t.Input = mi; mo.Input = t; anim(t, 'brightness', {0: 1.2, min(n - 1, 5): 0.2}); setp(t, 'glow_width', 0.4)
    elif fx == 'S_VHSDamage': t = comp.AddTool(SAP[fx]); t.Input = mi; mo.Input = t; setp(t, 'color_aberration', 1.5); setp(t, 'shift_amount', 0.6)
    elif fx == 'S_DigitalDamage': t = comp.AddTool(SAP[fx]); t.Input = mi; mo.Input = t; anim(t, 'intensity', {0: 1.0, min(n - 1, 4): 0.2})
    elif fx == 'S_FilmEffect': t = comp.AddTool(SAP[fx]); t.Input = mi; mo.Input = t; setp(t, 'glow_brightness', 0.3)
    elif fx == 'tunnel':
        g = comp.AddTool(SAP['S_UltraGlow']); g.Input = mi; setp(g, 'brightness', 0.7); setp(g, 'glow_width', 0.5); setp(g, 'threshold', 0.55)
        er = comp.AddTool(SAP['S_EdgeRays']); er.Input = g; anim(er, 'rays_length', {0: 0.0, 120: 0.3, n - 1: 0.9}); setp(er, 'rays_brightness', 0.8)
        wc = comp.AddTool(SAP['S_WarpChroma']); wc.Input = er; anim(wc, 'warp_amount', {0: 0.0, 120: 0.3, 190: 1.5, n - 1: 1.5}); mo.Input = wc
    done.append((c['rf'], fx))
result = {'timeline': tl.GetName(), 'plan_total': len(plan), 'done': done, 'errs': errs[:6]}
