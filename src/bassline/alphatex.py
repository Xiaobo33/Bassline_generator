"""把练习转成 alphaTex 文本，交给网页上的 alphaTab 显示五线谱 + TAB 并播放。

alphaTex 里一个音写作 "品.弦.时值"，例如 "5.3.4" = 第 3 弦第 5 品、四分音符。
弦从细到粗编号：G=1, D=2, A=3, E=4。小节之间用 "|" 分隔。
语法按 alphaTab 1.8 核对过。
"""

from __future__ import annotations

from .models import BassNote, Exercise

STRING_NUMBER = {"G": 1, "D": 2, "A": 3, "E": 4}
BEATS_PER_BAR = 4
DURATION_NUMBER = {"whole": 1, "half": 2, "quarter": 4, "eighth": 8}

# 音名里的升降号 → alphaTex 的 acc 写法。不指定的话 alphaTab 会自己选，比如把 Ab 写成 G#
ACCIDENTAL = {"#": "#", "##": "x", "b": "b", "bb": "bb"}


def to_alphatex(exercise: Exercise, tempo: int = 80) -> str:
    header = [
        f'\\title "{exercise.description}"',
        f'\\subtitle "调：{key_label(exercise.key)}"' if exercise.key else "",  # 在标题下方显示调名
        f"\\tempo {tempo}",
        ".",
        '\\track "Bass"',
        "\\staff {score tabs}",  # 同时显示五线谱和 TAB
        "\\tuning (G2 D2 A1 E1)",  # 四弦贝斯标准调弦
        "\\instrument electricbassfinger",  # 播放音色：指弹电贝斯
        "\\displaytranspose 12",  # 贝斯谱习惯比实际音高高一个八度记谱
    ]

    tokens = ["\\clef F4"]  # 低音谱号
    if exercise.key:  # 请求里指定了调才加调号
        tokens.append(f"\\ks {alphatex_key(exercise.key)}")
    beat = 0.0  # 写到第几拍了
    prev_chord = None

    def add(token: str) -> None:
        if beat > 0 and beat % BEATS_PER_BAR == 0:  # 到了新一小节，先画小节线
            tokens.append("|")
        tokens.append(token)

    for note in exercise.notes:
        while beat < note.start_beat:  # 中间空着的拍子补四分休止符
            add("r.4")
            beat += 1
        token = _note_token(note)
        if note.chord_symbol != prev_chord:  # 和弦变化时在上方标出和弦名
            token += f' {{ch "{note.chord_symbol}"}}'
            prev_chord = note.chord_symbol
        add(token)
        beat += note.beats
    while beat % BEATS_PER_BAR != 0:  # 最后一小节不满时补休止符
        add("r.4")
        beat += 1

    return "\n".join(line for line in header if line) + "\n" + " ".join(tokens) + "\n"


def key_label(key: str) -> str:
    """调名 → 显示用文字：大调 "Eb" → "Eb 大调"，小调 "Cm" → "C 小调"。"""
    if key.endswith("m"):
        return f"{key[:-1]} 小调"
    return f"{key} 大调"


def alphatex_key(key: str) -> str:
    """调名 → alphaTex 写法：大调 "Eb" → "eb"，小调 "Cm" → "cminor"。"""
    if key.endswith("m"):
        return key[:-1].lower() + "minor"
    return key.lower()


def _note_token(note: BassNote) -> str:
    """例如 Ab2 在 G 弦 1 品、四分音符 → "1.1{acc b}.4"。"""
    fret_and_string = f"{note.tab.fret}.{STRING_NUMBER[note.tab.string]}"
    accidental = note.name[1:]  # "Ab" → "b"，"C" → ""
    if accidental:
        fret_and_string += f"{{acc {ACCIDENTAL[accidental]}}}"
    return f"{fret_and_string}.{DURATION_NUMBER[note.duration]}"
