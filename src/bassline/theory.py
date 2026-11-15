"""乐理基础：音名解析与拼写、和弦定义、贝斯音域。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from .models import ChordQuality, NoteRole

LETTERS = ("C", "D", "E", "F", "G", "A", "B")
LETTER_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}

# 四弦贝斯标准调弦的音域：空弦 E1 (28) 到 G 弦 12 品 G3 (55)
BASS_LOWEST_MIDI = 28
BASS_HIGHEST_MIDI = 55

SUPPORTED_ROOTS = (
    "C", "C#", "Db", "D", "D#", "Eb", "E", "F", "F#",
    "Gb", "G", "G#", "Ab", "A", "A#", "Bb", "B",
)  # fmt: skip

# 有标准调号（最多 7 个升号或降号）的 30 个调，按五度圈排列。小调在后面加 "m"
SUPPORTED_KEYS = (
    "Cb", "Gb", "Db", "Ab", "Eb", "Bb", "F", "C", "G", "D", "A", "E", "B", "F#", "C#",
    "Abm", "Ebm", "Bbm", "Fm", "Cm", "Gm", "Dm", "Am", "Em", "Bm", "F#m", "C#m", "G#m", "D#m", "A#m",
)  # fmt: skip


@dataclass(frozen=True)
class SpelledPitch:
    """带拼写的音级：字母 + 升降号数量（+1 = #，-1 = b）。"""

    letter: str
    alter: int

    @property
    def pitch_class(self) -> int:
        return (LETTER_PC[self.letter] + self.alter) % 12

    @property
    def name(self) -> str:
        return self.letter + ("#" * self.alter if self.alter > 0 else "b" * -self.alter)

    def octave_at(self, midi: int) -> int:
        """已知 MIDI 音高时算出八度号（正确处理 Cb、B# 跨八度）。"""
        return (midi - self.alter - LETTER_PC[self.letter]) // 12 - 1


def parse_root(text: str) -> SpelledPitch | None:
    """解析根音字符串；不在 SUPPORTED_ROOTS 内则返回 None。"""
    normalized = text.strip().replace("♯", "#").replace("♭", "b")
    m = re.fullmatch(r"([A-Ga-g])(#|b)?", normalized)
    if not m:
        return None
    letter, acc = m.group(1).upper(), m.group(2) or ""
    if letter + acc not in SUPPORTED_ROOTS:  # 排除 E#、Fb、B#、Cb
        return None
    return SpelledPitch(letter, {"#": 1, "b": -1, "": 0}[acc])


def parse_key(text: str) -> str | None:
    """解析调名，如 "eb" → "Eb"、"F♯m" → "F#m"；不在 SUPPORTED_KEYS 内则返回 None。"""
    normalized = text.strip().replace("♯", "#").replace("♭", "b")
    normalized = normalized[:1].upper() + normalized[1:]
    return normalized if normalized in SUPPORTED_KEYS else None


def spell_interval(root: SpelledPitch, degree: int, semitones: int) -> SpelledPitch:
    """按「音程度数 + 半音数」拼写，例如 C 的小三度是 Eb 而不是 D#。"""
    letter = LETTERS[(LETTERS.index(root.letter) + degree - 1) % 7]
    target = root.pitch_class + semitones
    alter = (target - LETTER_PC[letter] + 6) % 12 - 6
    return SpelledPitch(letter, alter)


def spell_chromatic(midi_or_pc: int, prefer: Literal["sharp", "flat"]) -> SpelledPitch:
    """按半音拼写单个音（用于经过音）：能用自然音就用自然音，否则按偏好用 # 或 b。"""
    pc = midi_or_pc % 12
    for letter, value in LETTER_PC.items():
        if value == pc:
            return SpelledPitch(letter, 0)
    step = -1 if prefer == "sharp" else 1
    neighbor = (pc + step) % 12
    letter = next(l for l, v in LETTER_PC.items() if v == neighbor)
    return SpelledPitch(letter, -step)


@dataclass(frozen=True)
class ChordTone:
    degree: int  # 1, 3, 4, 5, 7
    semitones: int
    interval: str  # 显示用，如 "b3"
    role: NoteRole


@dataclass(frozen=True)
class ChordDef:
    suffix: str
    tones: tuple[ChordTone, ...]

    @property
    def fifth(self) -> ChordTone:
        return next(t for t in self.tones if t.degree == 5)


_R = ChordTone(1, 0, "1", "root")
_M3 = ChordTone(3, 4, "3", "third")
_m3 = ChordTone(3, 3, "b3", "third")
_P4 = ChordTone(4, 5, "4", "fourth")
_P5 = ChordTone(5, 7, "5", "fifth")
_d5 = ChordTone(5, 6, "b5", "fifth")
_A5 = ChordTone(5, 8, "#5", "fifth")
_M7 = ChordTone(7, 11, "7", "seventh")
_m7 = ChordTone(7, 10, "b7", "seventh")
_d7 = ChordTone(7, 9, "bb7", "seventh")

CHORDS: dict[ChordQuality, ChordDef] = {
    "major": ChordDef("", (_R, _M3, _P5)),
    "minor": ChordDef("m", (_R, _m3, _P5)),
    "diminished": ChordDef("dim", (_R, _m3, _d5)),
    "augmented": ChordDef("aug", (_R, _M3, _A5)),
    "sus4": ChordDef("sus4", (_R, _P4, _P5)),
    "dominant7": ChordDef("7", (_R, _M3, _P5, _m7)),
    "major7": ChordDef("maj7", (_R, _M3, _P5, _M7)),
    "minor7": ChordDef("m7", (_R, _m3, _P5, _m7)),
    "half-diminished7": ChordDef("m7b5", (_R, _m3, _d5, _m7)),
    "diminished7": ChordDef("dim7", (_R, _m3, _d5, _d7)),
}

SUPPORTED_QUALITIES: tuple[ChordQuality, ...] = tuple(CHORDS)


def lowest_root_midi(root: SpelledPitch) -> int:
    """根音放在贝斯最低的那个八度：MIDI 28 (E1) 到 39 (Eb2) 之间。"""
    return BASS_LOWEST_MIDI + (root.pitch_class - BASS_LOWEST_MIDI) % 12
