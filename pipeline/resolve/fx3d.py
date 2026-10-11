import os
MROOT = os.environ.get('MONTAGE_ROOT', os.path.abspath('.'))          # working dir of the montage pipeline
XROOT = os.environ.get('EXPLAINER_ROOT', os.path.abspath('.'))        # working dir of the explainer
MOUT = os.environ.get('MONTAGE_OUT', os.path.join(MROOT, 'out'))
MFINAL = os.environ.get('MONTAGE_FINAL', os.path.join(MOUT, 'opening_4k.mp4'))
# 裸眼3D motion pass (exec in run_script_unsafe with CHUNK): per 3D cut -> bars slide in (track 2), matte pushes out (track 3), base counter-zooms (track 1)
import json
CL = json.load(open(MROOT + '/work/open_cutlist.json')); sec3 = sorted([i for i in CL['items'] if i['track'] == 1 and i['sec'] == 3], key=lambda x: x['rf'])
tl = project.GetCurrentTimeline(); S = tl.GetStartFrame(); errs = []; done = []
def by_track(tr): return {it.GetStart() - S: it for it in tl.GetItemListInTrack('video', tr)}
T1, T2, T3 = by_track(1), by_track(2), by_track(3)
def anim(comp, tool, k, keys):
    try:
        tool[k] = comp.BezierSpline()
        for f, v in keys.items(): tool[k][f] = v
    except Exception as e: errs.append(f'{k}:{str(e)[:40]}')
def fresh(it):
    comp = it.AddFusionComp() or it.GetFusionCompByIndex(it.GetFusionCompCount())
    for t in list(comp.GetToolList(False).values()):
        if t.Name not in ('MediaIn1', 'MediaOut1'): t.Delete()
    return comp, comp.FindTool('MediaIn1'), comp.FindTool('MediaOut1')
jobs = []
for k, c in enumerate(sec3):
    rf, n = c['rf'], c['tf']; vertical = c.get('bars') == 'v'
    jobs.append(('bars', rf, n, vertical, k)); jobs.append(('matte', rf, n, vertical, k)); jobs.append(('base', rf, n, vertical, k))
for kind, rf, n, vertical, k in jobs[CHUNK[0]:CHUNK[1]]:
    it = {'bars': T2, 'matte': T3, 'base': T1}[kind].get(rf)
    if it is None: continue
    comp, mi, mo = fresh(it); t = comp.AddTool('Transform'); t.Input = mi; mo.Input = t
    if kind == 'bars':      # slide in from the edges over 5 frames (horizontal bars from top/bottom, vertical bars from the sides)
        if vertical: anim(comp, t, 'Size', {0: 1.45, min(n - 1, 5): 1.0})
        else: anim(comp, t, 'Size', {0: 1.0, 0.0: 1.0}); anim(comp, t, 'Center', {0: {1: 0.5, 2: 0.5 + (0.12 if k % 2 else -0.12)}, min(n - 1, 5): {1: 0.5, 2: 0.5}})
    elif kind == 'matte':   # the person pushes toward the camera across the cut (parallax)
        anim(comp, t, 'Size', {0: 1.0, n - 1: 1.07}); 
        try: t['Center'] = {1: 0.5, 2: 0.463}
        except Exception as e: errs.append(str(e)[:40])
    else:                   # background recedes slightly
        anim(comp, t, 'Size', {0: 1.0, n - 1: 0.985})
    done.append((kind, rf))
result = {'jobs': len(jobs), 'done': done, 'errs': errs[:6]}
