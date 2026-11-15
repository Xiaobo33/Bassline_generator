"""输入与输出的数据结构。本文件只放数据定义，不含生成逻辑。"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal, TypedDict

ChordQuality = Literal[
    "major",
    "minor",
    "diminished",
    "augmented",
    "sus4",
    "dominant7",
    "major7",
    "minor7",
    "half-diminished7",
    "diminished7",
]

ExerciseType = Literal["chord-tones", "root-fifth-octave", "walking-bass", "combined"]

NoteDuration = Literal["whole", "half", "quarter", "eighth"]

NoteRole = Literal["root", "third", "fourth", "fifth", "seventh", "octave", "chromatic-approach"]

ErrorCode = Literal["INVALID_REQUEST", "UNSUPPORTED_EXERCISE_TYPE", "INVALID_ROOT", "UNSUPPORTED_QUALITY", "INVALID_KEY"]


# ---------- 输入 ----------
# 输入用普通 dict（TypedDict 只用于类型提示），方便以后直接接收网页传来的 JSON。


class ChordInput(TypedDict):
    root: str  # C、C#、Db … B 共 17 种写法，大小写、♯/♭ 均可
    quality: ChordQuality


class KeyOption(TypedDict, total=False):
    """可选字段。key 是练习所在的调，决定五线谱调号：大调如 "C"、"Eb"，小调如 "Am"、"Cm"。不写则不加调号。"""

    key: str


class ExerciseRequest(KeyOption):
    """练习请求。chords 是和弦进行，每个和弦一小节：
    - chord-tones / root-fifth-octave：1–16 个和弦
    - walking-bass / combined：2–16 个和弦

    例：{"type": "walking-bass", "chords": [{"root": "C", "quality": "major"}, {"root": "A", "quality": "minor"}], "key": "C"}
    """

    type: ExerciseType
    chords: list[ChordInput]


# ---------- 输出 ----------


@dataclass(frozen=True)
class TabPosition:
    """四弦贝斯（E–A–D–G）的弦位，由 fingering.py 计算。"""

    string: Literal["E", "A", "D", "G"]
    fret: int


@dataclass(frozen=True)
class BassNote:
    index: int  # 在整个练习中的序号，从 0 开始
    name: str  # 不含八度的音名，如 "Eb"
    octave: int  # 科学音高记号的八度（MIDI 60 = C4）
    pitch: str  # 音名 + 八度，如 "Eb2"
    midi: int
    duration: NoteDuration
    beats: float  # 时值折合四分音符拍数
    bar: int  # 小节号，从 1 开始（4/4 拍）
    beat: float  # 小节内拍号，从 1 开始
    start_beat: float  # 从练习开头算起的起始拍，从 0 开始
    chord_symbol: str  # 所属和弦记号，如 "Cm7"
    role: NoteRole
    interval: str | None  # 相对所属和弦根音的音程，如 "1"、"b3"、"8"；经过音为 None
    tab: TabPosition  # 弦位，如 TabPosition("A", 3)


@dataclass(frozen=True)
class ChordInfo:
    symbol: str
    root: str
    quality: ChordQuality
    tones: tuple[str, ...]  # 和弦音音名，按根音向上排列


@dataclass(frozen=True)
class Exercise:
    type: ExerciseType
    description: str
    time_signature: tuple[int, int]
    chords: tuple[ChordInfo, ...]
    total_beats: float
    notes: tuple[BassNote, ...]
    key: str | None = None  # 练习所在的调，如 "Eb"、"Cm"；None 表示不加调号

    def to_dict(self) -> dict[str, Any]:
        """转成可直接 json.dumps 的 dict，供以后网页接口使用。"""
        return asdict(self)


class ExerciseInputError(ValueError):
    """输入不合法时抛出。code 供程序判断，field 指出出错字段（如 "from.root"），message 给人看。"""

    def __init__(self, code: ErrorCode, field: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.field = field
        self.message = message

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "field": self.field, "message": self.message}
