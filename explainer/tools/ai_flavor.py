"""Chinese copy 'AI flavour' linter: flags templated structures and filler words that make text read machine-written.
usage: python tools/ai_flavor.py FILE [...]   (.py LINES dicts or .md/.txt)  -> per-sentence flags + a score (lower is better)"""
import os
MROOT = os.environ.get('MONTAGE_ROOT', os.path.abspath('.'))          # working dir of the montage pipeline
XROOT = os.environ.get('EXPLAINER_ROOT', os.path.abspath('.'))        # working dir of the explainer
MOUT = os.environ.get('MONTAGE_OUT', os.path.join(MROOT, 'out'))
MFINAL = os.environ.get('MONTAGE_FINAL', os.path.join(MOUT, 'opening_4k.mp4'))
import re, sys, importlib.util
from pathlib import Path

BUZZ = ['赋能', '极致', '震撼', '沉浸', '打造', '助力', '深度', '全方位', '一站式', '重磅', '硬核', '颠覆', '天花板', '绝绝子', 'yyds',
        '干货满满', '建议收藏', '宝藏', '神器', '炸裂', '封神', '无与伦比', '匠心', '初心', '温度', '质感满满', '高能', '燃爆', '史诗级',
        '独具匠心', '别具一格', '美轮美奂', '令人惊叹', '叹为观止', '完美呈现', '全新升级', '焕然一新', '精彩纷呈', '不容错过', '满满的']
STOCK = ['让我们', '值得一提的是', '总而言之', '综上所述', '不难发现', '毋庸置疑', '在这个', '时代', '一起来看看', '话不多说', '接下来',
         '首先', '其次', '最后', '总的来说', '可以说', '真正的', '更是', '不仅仅是', '而是一种', '见证', '旅程', '探索', '魅力', '灵魂']
PATTERNS = [
    (r'不是[^，。！？]{1,14}[，,]\s*(?:而)?是', '「不是A，是B」对立句'),
    (r'不仅[^，。]{1,16}[，,]\s*(?:更|还|也)', '「不仅…更…」递进句'),
    (r'既[^，。]{1,10}[，,]?\s*又', '「既…又…」'),
    (r'(?:一[^，。、]{1,3}[，、]){2,}一[^，。、]{1,3}', '「一X，一Y，一Z」排比'),
    (r'(?:[^，。]{2,6}[，、]){2}[^，。]{2,6}[，、。]', None),   # generic triad, scored below
    (r'[—–]', '破折号'),
    (r'[!！]{2,}', '连续感叹号'),
]
EMOJI = re.compile('[\U0001F300-\U0001FAFF☀-➿]')


def sentences(text):
    parts = re.split(r'(?<=[。！？!?\n])', text)
    return [p.strip() for p in parts if p.strip()]


def load(path):
    p = Path(path)
    if p.suffix == '.py':
        spec = importlib.util.spec_from_file_location('m', p); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        return [(k, v[1]) for k, v in m.LINES.items()]
    out = []
    for i, line in enumerate(p.read_text().splitlines()):
        s = line.strip()
        if not s or s.startswith(('#', '|', '```', '- `', '`')) or s.startswith('**') and s.endswith('**'):
            continue
        out.append((f'L{i + 1}', s))
    return out


def lint(text):
    flags = []
    for w in BUZZ:
        if w in text: flags.append(f'空词「{w}」')
    for w in STOCK:
        if w in text: flags.append(f'套话「{w}」')
    for pat, name in PATTERNS:
        if name and re.search(pat, text): flags.append(name)
    four = re.findall(r'(?:^|(?<=[，。、！？；：\s]))[\u4e00-\u9fff]{4}(?=[，。、！？；：]|$)', text)
    if len(four) >= 3: flags.append(f'四字词扎堆×{len(four)}')
    if text.count('：') >= 1 and len(text) < 60: flags.append('冒号铺垫')
    if EMOJI.search(text): flags.append('表情符号')
    return flags


if __name__ == '__main__':
    total = n = 0
    for f in sys.argv[1:]:
        items = load(f)
        lens = [len(t) for _, t in items]
        for k, t in items:
            fl = lint(t)
            n += 1; total += len(fl)
            if fl: print(f'{k:10s} {"；".join(fl)}\n           {t}')
        if len(lens) > 4:
            import statistics
            cv = statistics.pstdev(lens) / max(1, statistics.mean(lens))
            if cv < 0.25: print(f'{f}: 句子长度过于整齐（变异系数 {cv:.2f}），像模板')
    print(f'\nflags {total} / {n} lines, score {total / max(1, n):.2f}')
