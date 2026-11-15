"""贝斯练习生成器（规则驱动）。对外只需从这里导入。"""

from .alphatex import to_alphatex
from .generator import generate_exercise
from .models import (
    BassNote,
    ChordInfo,
    ChordInput,
    ChordQuality,
    Exercise,
    ExerciseInputError,
    ExerciseRequest,
    ExerciseType,
    TabPosition,
)
from .theory import BASS_HIGHEST_MIDI, BASS_LOWEST_MIDI, SUPPORTED_KEYS, SUPPORTED_QUALITIES, SUPPORTED_ROOTS

__all__ = [
    "generate_exercise",
    "to_alphatex",
    "BassNote",
    "ChordInfo",
    "ChordInput",
    "ChordQuality",
    "Exercise",
    "ExerciseInputError",
    "ExerciseRequest",
    "ExerciseType",
    "TabPosition",
    "BASS_HIGHEST_MIDI",
    "BASS_LOWEST_MIDI",
    "SUPPORTED_KEYS",
    "SUPPORTED_QUALITIES",
    "SUPPORTED_ROOTS",
]
