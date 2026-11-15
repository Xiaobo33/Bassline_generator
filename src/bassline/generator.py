"""练习生成：输入检查 + 三种练习的规则。纯函数，无随机性，相同输入得到相同输出。"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Any, NoReturn, cast

from .fingering import assign_tabs_by_bar
from .models import (
    BassNote,
    ChordInfo,
    ChordQuality,
    ErrorCode,
    Exercise,
    ExerciseInputError,
    ExerciseType,
    NoteDuration,
    NoteRole,
)
from .theory import (
    BASS_HIGHEST_MIDI,
    BASS_LOWEST_MIDI,
    CHORDS,
    SUPPORTED_KEYS,
    SUPPORTED_QUALITIES,
    SUPPORTED_ROOTS,
    SpelledPitch,
    lowest_root_midi,
    parse_key,
    parse_root,
    spell_chromatic,
    spell_interval,
)

BEATS_PER_BAR = 4
DURATION_BEATS: dict[NoteDuration, float] = {"whole": 4, "half": 2, "quarter": 1, "eighth": 0.5}
EXERCISE_TYPES: tuple[ExerciseType, ...] = ("chord-tones", "root-fifth-octave", "walking-bass", "combined")
MAX_CHORDS = 16  # 和弦进行最多几个和弦


@dataclass(frozen=True)
class _Chord:
    """校验后的和弦：根音拼写 + 根音放在贝斯低音区的 MIDI。"""

    root: SpelledPitch
    quality: ChordQuality
    symbol: str
    root_midi: int


@dataclass(frozen=True)
class _Draft:
    """还没排上小节/拍位的音。"""

    pitch: SpelledPitch
    midi: int
    duration: NoteDuration
    chord: _Chord
    role: NoteRole
    interval: str | None


def generate_exercise(request: Mapping[str, Any]) -> Exercise:
    """生成一个贝斯练习。

    request 是普通 dict（可以直接来自网页 JSON），所有字段都会在运行时检查。
    输入不合法时抛出 ExerciseInputError（带 code、field、message）。
    """
    if not isinstance(request, Mapping):
        _fail("INVALID_REQUEST", "", '请求必须是一个 dict，例如 {"type": "chord-tones", "chords": [{"root": "C", "quality": "major"}]}。')
    ex_type = request.get("type")
    if ex_type not in EXERCISE_TYPES:
        _fail("UNSUPPORTED_EXERCISE_TYPE", "type", f"不支持的练习类型 {ex_type!r}。支持：{'、'.join(EXERCISE_TYPES)}。")

    key = _resolve_key(request.get("key"))
    needs_two = ex_type in ("walking-bass", "combined")  # walking bass 要从一个和弦走到下一个
    chords = _resolve_progression(request.get("chords"), 2 if needs_two else 1)

    if ex_type == "chord-tones":
        exercise = _chord_tones(chords)
    elif ex_type == "root-fifth-octave":
        exercise = _root_fifth_octave(chords)
    elif ex_type == "walking-bass":
        exercise = _walking_bass(chords)
    else:
        exercise = _combined(chords)
    return replace(exercise, key=key)


# ---------- 各种练习的规则（每个和弦一小节） ----------


def _chord_tones(chords: list[_Chord]) -> Exercise:
    """和弦音：每个和弦从低音区根音向上依次弹出所有和弦音，四分音符。"""
    parts = [_finish("chord-tones", "", [c], _chord_tone_drafts(c)) for c in chords]
    return _concat("chord-tones", f"{_symbols(chords)} 和弦音（向上分解），四分音符", chords, parts)


def _root_fifth_octave(chords: list[_Chord]) -> Exercise:
    """根音–五度–八度：每个和弦三个四分音符。五度按和弦类型取 5、b5 或 #5。"""
    parts = [_finish("root-fifth-octave", "", [c], _root_fifth_octave_drafts(c)) for c in chords]
    return _concat("root-fifth-octave", f"{_symbols(chords)} 根音–五度–八度，四分音符", chords, parts)


def _walking_bass(chords: list[_Chord]) -> Exercise:
    """沿着一串和弦走 walking bass（每个和弦一小节，最后一个和弦全音符）。

    每小节：根音 – 三度(sus4 为四度) – 五度 – 半音经过音，进入下一个和弦的根音。
    根音都放在最低的八度（和「和弦音」练习一样），第 1–3 拍就是这个和弦的三和弦手型。
    例：C → A → D → G 的根音在 A 弦 3 品、E 弦 5 品、A 弦 5 品、E 弦 3 品。
    """
    drafts: list[_Draft] = []
    for chord, next_chord in zip(chords, chords[1:]):
        bar = _chord_tone_drafts(chord)[:3]  # 每种和弦前三个音都是 根音、三度(或四度)、五度
        bar.append(_approach(chord, beat3_midi=bar[2].midi, target_midi=next_chord.root_midi))
        drafts += bar
    last = chords[-1]
    drafts.append(_Draft(last.root, last.root_midi, "whole", last, "root", "1"))
    desc = f"{_symbols(chords)} walking bass：每个和弦弹三和弦手型（根音、三度、五度），第 4 拍半音进入下一个和弦"
    return _finish("walking-bass", desc, chords, drafts)


def _approach(chord: _Chord, beat3_midi: int, target_midi: int) -> _Draft:
    """第 4 拍的半音经过音，进入 target_midi（下一个根音）。

    1. 下一个根音比第 3 拍高（或同音）时从半音下方进入，否则从半音上方进入。
    2. 若经过音与第 3 拍同音或超出贝斯音域，则改从另一侧进入。
    3. 下方进入的经过音用 # 拼写，上方进入的用 b 拼写（自然音优先）。
    """
    def invalid(below: bool) -> bool:
        m = target_midi + (-1 if below else 1)
        return m == beat3_midi or not BASS_LOWEST_MIDI <= m <= BASS_HIGHEST_MIDI

    from_below = target_midi >= beat3_midi
    if invalid(from_below):
        from_below = not from_below
    midi = target_midi + (-1 if from_below else 1)
    pitch = spell_chromatic(midi, "sharp" if from_below else "flat")
    return _Draft(pitch, midi, "quarter", chord, "chromatic-approach", None)


def _combined(chords: list[_Chord]) -> Exercise:
    """三种练习在同一个和弦进行上依次各走一遍：和弦音 → 根音–五度–八度 → walking bass。"""
    parts = [_chord_tones(chords), _root_fifth_octave(chords), _walking_bass(chords)]
    desc = f"{_symbols(chords)} 综合练习：和弦音 → 根音–五度–八度 → walking bass"
    return _concat("combined", desc, chords, parts)


def _chord_tone_drafts(chord: _Chord) -> list[_Draft]:
    return [
        _Draft(spell_interval(chord.root, t.degree, t.semitones), chord.root_midi + t.semitones, "quarter", chord, t.role, t.interval)
        for t in CHORDS[chord.quality].tones
    ]


def _root_fifth_octave_drafts(chord: _Chord) -> list[_Draft]:
    fifth = CHORDS[chord.quality].fifth
    return [
        _Draft(chord.root, chord.root_midi, "quarter", chord, "root", "1"),
        _Draft(spell_interval(chord.root, 5, fifth.semitones), chord.root_midi + fifth.semitones, "quarter", chord, "fifth", fifth.interval),
        _Draft(chord.root, chord.root_midi + 12, "quarter", chord, "octave", "8"),
    ]


def _concat(ex_type: ExerciseType, description: str, chords: list[_Chord], parts: list[Exercise]) -> Exercise:
    """把几段练习接在一起，每一段都从新的一小节开始（不满的小节由 alphaTex 导出时补休止符）。"""
    notes: list[BassNote] = []
    start = 0.0
    for part in parts:
        start = -(-start // BEATS_PER_BAR) * BEATS_PER_BAR  # 进到下一小节的开头（已在开头则不动）
        for note in part.notes:
            beat = start + note.start_beat
            notes.append(replace(
                note,
                index=len(notes),
                start_beat=beat,
                bar=int(beat // BEATS_PER_BAR) + 1,
                beat=beat % BEATS_PER_BAR + 1,
            ))
        start += part.total_beats
    return Exercise(
        type=ex_type,
        description=description,
        time_signature=(BEATS_PER_BAR, 4),
        chords=tuple(_chord_info(c) for c in chords),
        total_beats=start,
        notes=tuple(notes),
    )


def _symbols(chords: list[_Chord]) -> str:
    return " → ".join(c.symbol for c in chords)


# ---------- 辅助函数 ----------


def _resolve_chord(value: object, field: str) -> _Chord:
    if not isinstance(value, Mapping):
        _fail("INVALID_REQUEST", field, f'缺少和弦 {field}，应为 {{"root": "C", "quality": "major"}} 这样的 dict。')
    root_text = value.get("root")
    root = parse_root(root_text) if isinstance(root_text, str) else None
    if root is None:
        _fail("INVALID_ROOT", f"{field}.root", f"无法识别的根音 {root_text!r}。支持：{'、'.join(SUPPORTED_ROOTS)}。")
    quality = value.get("quality")
    if quality not in SUPPORTED_QUALITIES:
        _fail("UNSUPPORTED_QUALITY", f"{field}.quality", f"不支持的和弦类型 {quality!r}。支持：{'、'.join(SUPPORTED_QUALITIES)}。")
    q = cast(ChordQuality, quality)
    return _Chord(root, q, root.name + CHORDS[q].suffix, lowest_root_midi(root))


def _resolve_progression(value: object, min_chords: int) -> list[_Chord]:
    """和弦进行：min_chords ~ MAX_CHORDS 个和弦组成的列表。"""
    if not isinstance(value, list) or not min_chords <= len(value) <= MAX_CHORDS:
        _fail(
            "INVALID_REQUEST",
            "chords",
            f'chords 应为 {min_chords}–{MAX_CHORDS} 个和弦组成的列表'
            + ("（walking bass 要从一个和弦走到下一个，至少 2 个）" if min_chords == 2 else "")
            + '，例如 [{"root": "C", "quality": "major"}, {"root": "A", "quality": "minor"}]。',
        )
    return [_resolve_chord(chord, f"chords[{i}]") for i, chord in enumerate(value)]


def _resolve_key(value: object) -> str | None:
    """key 可选：没写返回 None；写了必须是 SUPPORTED_KEYS 之一。"""
    if value is None:
        return None
    key = parse_key(value) if isinstance(value, str) else None
    if key is None:
        _fail("INVALID_KEY", "key", f"无法识别的调 {value!r}。大调写根音（如 \"Eb\"），小调加 m（如 \"Cm\"）。支持：{'、'.join(SUPPORTED_KEYS)}。")
    return key


def _nearest_in_range(pc: int, reference: int) -> int:
    """在贝斯音域内找到某音级离 reference 最近的 MIDI 音高；距离相同取较高者。"""
    candidates = [m for m in range(BASS_LOWEST_MIDI, BASS_HIGHEST_MIDI + 1) if m % 12 == pc]
    return min(candidates, key=lambda m: (abs(m - reference), -m))


def _finish(ex_type: ExerciseType, description: str, chords: list[_Chord], drafts: list[_Draft]) -> Exercise:
    """按顺序给音符排上 index、小节、拍位和弦位。"""
    starts = []  # 每个音的起始拍
    start = 0.0
    for d in drafts:
        starts.append(start)
        start += DURATION_BEATS[d.duration]

    bars: dict[int, list[int]] = {}  # 小节号 → 这一小节各音的 MIDI，用来按小节选弦位
    for d, beat in zip(drafts, starts):
        bars.setdefault(int(beat // BEATS_PER_BAR), []).append(d.midi)
    tabs = assign_tabs_by_bar(list(bars.values()))

    notes: list[BassNote] = []
    for i, (d, tab, start) in enumerate(zip(drafts, tabs, starts)):
        octave = d.pitch.octave_at(d.midi)
        beats = DURATION_BEATS[d.duration]
        notes.append(
            BassNote(
                index=i,
                name=d.pitch.name,
                octave=octave,
                pitch=f"{d.pitch.name}{octave}",
                midi=d.midi,
                duration=d.duration,
                beats=beats,
                bar=int(start // BEATS_PER_BAR) + 1,
                beat=start % BEATS_PER_BAR + 1,
                start_beat=start,
                chord_symbol=d.chord.symbol,
                role=d.role,
                interval=d.interval,
                tab=tab,
            )
        )
    return Exercise(
        type=ex_type,
        description=description,
        time_signature=(BEATS_PER_BAR, 4),
        chords=tuple(_chord_info(c) for c in chords),
        total_beats=sum(DURATION_BEATS[d.duration] for d in drafts),
        notes=tuple(notes),
    )


def _chord_info(c: _Chord) -> ChordInfo:
    tones = tuple(spell_interval(c.root, t.degree, t.semitones).name for t in CHORDS[c.quality].tones)
    return ChordInfo(symbol=c.symbol, root=c.root.name, quality=c.quality, tones=tones)


def _fail(code: ErrorCode, field: str, message: str) -> NoReturn:
    raise ExerciseInputError(code, field, message)
