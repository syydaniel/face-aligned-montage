"""web/index.html -> web/index_en.html (English labels, English subtitle wrapping, LinkedIn call to action)."""
import os
MROOT = os.environ.get('MONTAGE_ROOT', os.path.abspath('.'))          # working dir of the montage pipeline
XROOT = os.environ.get('EXPLAINER_ROOT', os.path.abspath('.'))        # working dir of the explainer
MOUT = os.environ.get('MONTAGE_OUT', os.path.join(MROOT, 'out'))
MFINAL = os.environ.get('MONTAGE_FINAL', os.path.join(MOUT, 'opening_4k.mp4'))
import re
R = XROOT
s = open(R + '/web/index.html', encoding='utf-8').read()
CODE = [  # structural edits first (exact snippets)
    ("T(b, 400, 540 + i * 64, 38,", "T(b, 480, 540 + i * 64, 38,"),
    ("['素材', 150]", "['source', 150]"), ('T("A MASTER\'S CUT  ·  幕后"', 'T("A MASTER\'S CUT  ·  BEHIND THE SCENES"'),
    ("const TL = await J('/web/timeline.json');", "const TL = await J('/web/timeline_en.json');"),
    ("const FONT = '\"PingFang SC\",\"Hiragino Sans GB\",sans-serif'", "const FONT = '\"Helvetica Neue\",Helvetica,\"PingFang SC\",sans-serif'"),
    ("T(nm, x + w / 2, y + 56, 30, {al: 'center', w: on || nm === hi ? 600 : 400,", "T(nm, x + w / 2, y + 52, 21, {al: 'center', w: on || nm === hi ? 600 : 400,"),
    ("T(p, x + w / 2, y + 58, hot ? 40 : 32, {al: 'center'", "T(p, x + w / 2, y + 56, hot ? 26 : 20, {al: 'center'"),
    ("T('块', 72, R.y + R.h + 160, 28, {c: COL.dim});", "T('bricks', 72, R.y + R.h + 160, 28, {c: COL.dim});"),
    ("cross(72 + (2155 - 840) / 2160 * S, 880 + 1000 / 2160 * S, 12);", "cross(72 + (2155 - 840) / 2160 * S, 880 + 1000 / 2160 * S, 12); T('github.com/syydaniel/face-aligned-montage', 72, 1400, 30, {f: MONO, c: COL.acc2});"),
    ("T(done ? '已关注' : '＋ 关注', 784, 1105, 52, {al: 'center', w: 600, c: done ? COL.text : COL.bg, a: clamp(kp)});", "T('Link in post', 784, 1105, 44, {al: 'center', w: 600, c: done ? COL.text : COL.bg, a: clamp(kp)});"),
]
for a, b in CODE:
    assert a in s, a[:60]; s = s.replace(a, b)
# English subtitles: word wrap to two lines, highlight numbers and key terms
old_subs = s[s.index('function subs(t) {'):s.index('const GR = [];')]
new_subs = r'''function subs(t) {
  const s = TL.subs.find(x => t >= x.t0 && t < x.t1 + 0.12); if (!s) return; const a = clamp((t - s.t0) / 0.1) * clamp((s.t1 + 0.12 - t) / 0.1), size = 46, maxW = 940;
  const words = s.text.split(/\s+/).filter(Boolean), lines = [[]]; for (const w of words) { const cur = lines[lines.length - 1]; if (cur.length && TW([...cur, w].join(' '), size, 500) > maxW) lines.push([w]); else cur.push(w); }
  const hot = w => /\d/.test(w) || KEYW.includes(w.toLowerCase().replace(/[^a-z0-9-]/g, ''));
  const y0 = 1560 - (lines.length - 1) * 60, wmax = Math.max(...lines.map(l => TW(l.join(' '), size, 500)));
  g.save(); g.globalAlpha = a; g.fillStyle = 'rgba(11,10,9,0.42)'; g.filter = 'blur(18px)'; g.fillRect(W / 2 - wmax / 2 - 30, y0 - 52, wmax + 60, 60 * lines.length + 24); g.filter = 'none'; g.restore();
  lines.forEach((l, i) => { let x = W / 2 - TW(l.join(' '), size, 500) / 2; for (const w of l) { T(w, x, y0 + i * 60, size, {w: hot(w) ? 600 : 500, c: hot(w) ? COL.acc2 : COL.text, a, sh: 10}); x += TW(w + ' ', size, hot(w) ? 600 : 500); } });
}
'''
s = s.replace(old_subs, new_subs)
s = re.sub(r"const KEYW = \[[^\]]*\];", "const KEYW = ['thirty-three', 'eyes', 'ghost', 'six', 'template', 'gates', 'forty', 'pixels', 'drop', 'thirty-second', 'table', 'script', 'versions', 'halo', 'bricks', 'hold', 'nothing', 'pause', 'flat', 'white', 'warm', 'line', 'myself', 'source', 'comments'];", s)
TR = {
 '两百多张脸': '200+ faces', '眼睛一直在这条线上': 'Eyes locked on this line', '完整版在片尾 ↓': 'Full cut at the end ↓',
 'subject-on-camera的素材 · 按拍摄月份': 'Footage of me · by month shot', '读研这两年': 'Two years of a master’s', '视频': 'video', '照片': 'photo',
 '段视频': 'videos', '张照片': 'photos', '五官钉在同一个位置': 'Features pinned in one place', '眼距 ': 'eye gap ',
 '四张原始画面 · 直接叠加': 'Four raw frames · stacked', '每张脸的大小、位置、角度': 'Size, position and angle all differ',
 '右眼': 'R eye', '左眼': 'L eye', '鼻尖': 'nose', '嘴角': 'mouth', '下巴': 'chin', '个关键点': 'landmarks', '只用其中 6 个': 'Only 6 of them',
 '人脸识别模型 · 每张脸': 'Landmark model · every face', '缩放 ×': 'scale ×', '   旋转 ': '   rotate ', '素材 ': 'face ',
 '对齐前': 'before', '对齐后': 'aligned', '标准脸': 'Template face', '六个点的位置，写死': 'Six fixed target points',
 '偏头 ': 'turned ', '闭眼 ': 'eyes ', '张嘴 ': 'mouth ', '头偏': 'Head turn', '闭眼': 'Eyes closed', '不要': 'out', '嘴张太大': 'Mouth wide open',
 '门槛': 'gate', '份素材': 'sources', '个过了门槛': 'passed', '刀': 'cuts', '过门槛': 'Gates', '目标': 'target', '渲出来': 'rendered',
 '第 ': 'round ', ' 轮  测量 → 推回': '  measure → push back', '示意': 'schematic', '像素': 'pixels', '4K 画面里，眼睛位置偏差的中位数': 'median eye error in a 4K frame',
 '画面宽 3840 px': 'frame width 3840 px', '结果': 'Result', '回测': 'Re-check', '亮度 ': 'luma ', '先测皮肤': 'Measure skin first', '拉齐之后': 'evened out',
 '原始亮度': 'as shot', '落点 ': 'drop ', '八分': '8ths', '十六分': '16ths', '三十二分': '32nds', '实际剪切点': 'actual cuts', '黑白': 'B&W', '彩 ': 'col ', '彩': 'col',
 '帧': 'frame', '缩放': 'scale', '色调': 'look', '剪辑表': 'Cut table', '标题': 'title', '暗角': 'vignette', '漏光': 'leaks', '暖光': 'warm', '画中画': 'Picture in picture',
 '抠像': 'matte', '黑边': 'bars', '人脸': 'faces', '音乐': 'music', '脚本搭进达芬奇': 'Built in Resolve by script', ' 个片段 · 9 条轨道': ' clips · 9 tracks',
 '同一时刻，不同版本': 'Same moment, different versions', '一张嘴': 'One mouth', '一只眼睛': 'One eye', '大脸在底下走，中间只叠一个部位': 'One feature at a time over the base',
 '这一天': 'one day', '另一天': 'another day', '左半张': 'left half', '右半张': 'right half', '拼脸': 'Split face', '中线一对上，就是一张脸': 'Line up the center: one face',
 '① 原画面': '① frame', '② 两条黑边': '② two bars', '③ 抠出来的人': '③ cutout', '裸眼 3D': 'Naked-eye 3D', '人压在黑边上面': 'The cutout sits over the bars',
 '边缘': 'Edges', '换了更细的抠像': 'A finer matting model', '头发边缘 ×3.2': 'hair edge ×3.2', '结尾': 'Ending', '一张脸跟着节拍裂开': 'One face splits on the beat',
 '墙': 'wall', '裂': 'split', '落': 'fall', '停': 'pause', '聚': 'gather', '冲': 'dive', '题': 'title', '碎掉，掉一地': 'Break and fall', '故意停一下': 'Then a deliberate pause',
 '粒子回来，冲进去': 'Gather, then dive', '第一版': 'First version', '隧道': 'tunnel', '现在': 'Now', '加了这一下停顿': 'One pause added', '结尾才立住': 'and the ending lands',
 '翻车记录': 'What went wrong', '白闪': 'White flashes', '竖线': 'A vertical line', '过曝': 'Blown-out ending', '现在：暖色的光': 'Now: warm light', '之前：白闪': 'Before: white flash',
 '一条细竖线，从头挂到尾': 'A thin line, start to finish', '原来是划痕素材里自带的': 'It came from a scratch overlay', '辉光 + 漏光，白成一片': 'Glow + leaks: pure white', '修好': 'fixed',
 '找素材': 'Find footage', '认脸': 'Detect faces', '对齐': 'Align', '筛选': 'Gate', '统一光线': 'Even out light', '扒节拍': 'Extract beats', '写剪辑表': 'Write cut table',
 '搭时间线': 'Build timeline', '做结尾': 'Make the ending', '成片': 'Final', '回头看': 'Looking back', '算得快，改得也快': 'Fast, and never tired', '我': 'Me',
 '哪一刀好看，哪里该停': 'Which cut looks right, where to pause', '一遍遍看出来的': 'seen again and again', '完整版': 'Full cut', '硕士阶段混剪 · 开场': 'A Master’s Cut · opening',
 '结尾那一下停顿': 'The pause', '你觉得是？': 'before the tunnel. Keep it?', '加分': 'Keep it', '多余': 'Cut it', '评论区告诉我': 'Tell me in the comments',
 '下期': 'Open source', '对齐这一步，单独拆开讲': 'Code, data and tutorial', 'AI 配音 · AI 配乐': 'AI voice · AI music', '幕后': 'BEHIND THE SCENES',
}
def tr_literal(m):
    q, body = m.group(1), m.group(2)
    for k in sorted(TR, key=len, reverse=True): body = body.replace(k, TR[k])
    return q + body + q
s = re.sub(r"(['`])([^'`\n]*[一-鿿][^'`\n]*)\1", tr_literal, s)
left = sorted(set(re.findall(r"[一-鿿]+", s)))
open(R + '/web/index_en.html', 'w', encoding='utf-8').write(s)
print('untranslated:', left)
