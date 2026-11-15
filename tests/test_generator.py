import copy
import json
import random

import pytest

from bassline import (
    BASS_HIGHEST_MIDI,
    BASS_LOWEST_MIDI,
    SUPPORTED_QUALITIES,
    SUPPORTED_ROOTS,
    ExerciseInputError,
    generate_exercise,
)


def req(type_, *chords, **extra):
    """req("walking-bass", "D", "minor7", "G", "dominant7") → 请求。和弦参数两两一组：根音, 和弦类型。"""
    pairs = zip(chords[::2], chords[1::2])
    return {"type": type_, "chords": [{"root": r, "quality": q} for r, q in pairs], **extra}


def generate(type_, *chords, **extra):
    return generate_exercise(req(type_, *chords, **extra))


def pitches(ex):
    return [n.pitch for n in ex.notes]


# ---------- 和弦音 ----------


def test_chord_tones_c_major():
    ex = generate("chord-tones", "C", "major")
    assert pitches(ex) == ["C2", "E2", "G2"]
    assert [n.midi for n in ex.notes] == [36, 40, 43]
    assert [(n.bar, n.beat) for n in ex.notes] == [(1, 1), (1, 2), (1, 3)]
    assert ex.total_beats == 3


@pytest.mark.parametrize(
    ("root", "quality", "expected"),
    [
        ("C", "minor", ["C", "Eb", "G"]),
        ("E", "major", ["E", "G#", "B"]),
        ("Db", "major7", ["Db", "F", "Ab", "C"]),
        ("B", "half-diminished7", ["B", "D", "F", "A"]),
        ("C", "diminished7", ["C", "Eb", "Gb", "Bbb"]),
        ("G", "dominant7", ["G", "B", "D", "F"]),
        ("C", "augmented", ["C", "E", "G#"]),
        ("D", "sus4", ["D", "G", "A"]),
    ],
)
def test_chord_tones_spelled_by_interval(root, quality, expected):
    assert [n.name for n in generate("chord-tones", root, quality).notes] == expected


def test_octave_number_follows_letter():
    assert pitches(generate("chord-tones", "B", "augmented")) == ["B1", "D#2", "F##2"]


def test_chord_tones_progression_one_bar_per_chord():
    # 1–6–2–5：C A D G 大三，每个和弦一小节
    ex = generate("chord-tones", "C", "major", "A", "major", "D", "major", "G", "major")
    assert pitches(ex) == ["C2", "E2", "G2", "A1", "C#2", "E2", "D2", "F#2", "A2", "G1", "B1", "D2"]
    assert [n.bar for n in ex.notes] == [1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4]
    assert [n.chord_symbol for n in ex.notes if n.role == "root"] == ["C", "A", "D", "G"]
    assert ex.description.startswith("C → A → D → G 和弦音")


# ---------- 根音–五度–八度 ----------


def test_root_fifth_octave():
    assert pitches(generate("root-fifth-octave", "C", "major")) == ["C2", "G2", "C3"]
    dim = generate("root-fifth-octave", "B", "diminished")
    assert pitches(dim) == ["B1", "F2", "B2"]
    assert [n.interval for n in dim.notes] == ["1", "b5", "8"]


def test_root_fifth_octave_progression():
    ex = generate("root-fifth-octave", "C", "major", "A", "minor")
    assert pitches(ex) == ["C2", "G2", "C3", "A1", "E2", "A2"]
    assert [n.bar for n in ex.notes] == [1, 1, 1, 2, 2, 2]


def test_root_input_is_lenient():
    assert generate("chord-tones", "f♯", "minor").chords[0].symbol == "F#m"
    assert generate("chord-tones", " B♭ ", "dominant7").chords[0].symbol == "Bb7"


# ---------- walking bass ----------


def test_walking_bass_dm7_to_g7():
    ex = generate("walking-bass", "D", "minor7", "G", "dominant7")
    # 根音都在最低的八度：G 是 G1；经过音从上方 Ab1 进入
    assert pitches(ex) == ["D2", "F2", "A2", "Ab1", "G1"]
    assert [n.role for n in ex.notes] == ["root", "third", "fifth", "chromatic-approach", "root"]
    assert [(n.bar, n.beat, n.duration) for n in ex.notes] == [
        (1, 1, "quarter"), (1, 2, "quarter"), (1, 3, "quarter"), (1, 4, "quarter"), (2, 1, "whole"),
    ]
    assert ex.total_beats == 8


def test_walking_bass_approach_from_below_uses_sharp():
    # E 的五度 B1 比下一个根音 D2 低，从下方 C#2 进入
    assert pitches(generate("walking-bass", "E", "major", "D", "major")) == ["E1", "G#1", "B1", "C#2", "D2"]


def test_walking_bass_approach_never_repeats_beat3():
    # 从下方进入会是 B1（和第 3 拍重复），所以改从上方 Db2 进入 C2
    assert pitches(generate("walking-bass", "E", "major", "C", "major")) == ["E1", "G#1", "B1", "Db2", "C2"]


def test_walking_bass_1625():
    ex = generate("walking-bass", "C", "major", "A", "major", "D", "major", "G", "major")
    assert pitches(ex) == ["C2", "E2", "G2", "Bb1", "A1", "C#2", "E2", "Eb2", "D2", "F#2", "A2", "Ab1", "G1"]
    assert [n.bar for n in ex.notes] == [1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4]
    assert [c.symbol for c in ex.chords] == ["C", "A", "D", "G"]
    assert ex.notes[-1].duration == "whole"


def test_walking_bass_rules_for_all_chord_pairs():
    in_range = lambda m: BASS_LOWEST_MIDI <= m <= BASS_HIGHEST_MIDI  # noqa: E731
    for r1 in SUPPORTED_ROOTS:
        for q1 in SUPPORTED_QUALITIES:
            for t in ("chord-tones", "root-fifth-octave"):
                assert all(in_range(n.midi) for n in generate(t, r1, q1).notes)
            for r2 in SUPPORTED_ROOTS:
                for q2 in SUPPORTED_QUALITIES:
                    m = [n.midi for n in generate("walking-bass", r1, q1, r2, q2).notes]
                    label = f"{r1}{q1}->{r2}{q2}: {m}"
                    assert len(m) == 5, label
                    assert all(in_range(x) for x in m), label
                    assert m[0] <= 39 and m[4] <= 39, label  # 根音都在最低的八度（E1–Eb2）
                    assert abs(m[3] - m[4]) == 1, label  # 经过音与下一个根音相差半音
                    assert m[3] != m[2], label  # 经过音不重复第 3 拍


def test_long_progressions():
    rng = random.Random(0)
    for _ in range(300):
        n = rng.randint(2, 16)
        chords = [x for _ in range(n) for x in (rng.choice(SUPPORTED_ROOTS), rng.choice(SUPPORTED_QUALITIES))]
        m = [note.midi for note in generate("walking-bass", *chords).notes]
        assert len(m) == 4 * (n - 1) + 1
        assert all(BASS_LOWEST_MIDI <= x <= BASS_HIGHEST_MIDI for x in m)
        for bar in range(n - 1):
            assert abs(m[4 * bar + 3] - m[4 * bar + 4]) == 1  # 第 4 拍半音进入下一个根音


# ---------- 全部结合 ----------


def test_combined_runs_each_exercise_over_the_progression():
    ex = generate("combined", "C", "major", "F", "major")
    assert pitches(ex) == [
        "C2", "E2", "G2", "F1", "A1", "C2",  # 和弦音：第 1–2 小节
        "C2", "G2", "C3", "F1", "C2", "F2",  # 根音–五度–八度：第 3–4 小节
        "C2", "E2", "G2", "Gb1", "F1",  # walking bass：第 5–6 小节
    ]
    assert [n.bar for n in ex.notes] == [1, 1, 1, 2, 2, 2, 3, 3, 3, 4, 4, 4, 5, 5, 5, 5, 6]
    assert [n.index for n in ex.notes] == list(range(17))
    assert ex.total_beats == 24
    assert [c.symbol for c in ex.chords] == ["C", "F"]


# ---------- 其他 ----------


def test_deterministic_and_json_serializable():
    request = req("walking-bass", "Eb", "major7", "C", "minor7")
    a = generate_exercise(request)
    assert a == generate_exercise(copy.deepcopy(request))
    json.dumps(a.to_dict(), ensure_ascii=False)


@pytest.mark.parametrize(
    ("request_", "code", "field"),
    [
        (None, "INVALID_REQUEST", ""),
        ({"type": "scale"}, "UNSUPPORTED_EXERCISE_TYPE", "type"),
        ({"type": "chord-tones"}, "INVALID_REQUEST", "chords"),
        (req("chord-tones"), "INVALID_REQUEST", "chords"),  # 0 个和弦
        (req("walking-bass", "C", "major"), "INVALID_REQUEST", "chords"),  # walking bass 只有 1 个和弦
        ({"type": "walking-bass", "chords": "C G"}, "INVALID_REQUEST", "chords"),
        (req("chord-tones", *["C", "major"] * 17), "INVALID_REQUEST", "chords"),  # 超过 16 个
        (req("chord-tones", "E#", "major"), "INVALID_ROOT", "chords[0].root"),
        (req("chord-tones", "H", "major"), "INVALID_ROOT", "chords[0].root"),
        (req("chord-tones", "C", "maj9"), "UNSUPPORTED_QUALITY", "chords[0].quality"),
        (req("walking-bass", "C", "major", 42, "major"), "INVALID_ROOT", "chords[1].root"),
        (req("chord-tones", "C", "major", key="D#"), "INVALID_KEY", "key"),  # 9 个升号，没有标准调号
        (req("chord-tones", "C", "major", key="C major"), "INVALID_KEY", "key"),
        (req("chord-tones", "C", "major", key=1), "INVALID_KEY", "key"),
    ],
)
def test_invalid_input(request_, code, field):
    with pytest.raises(ExerciseInputError) as info:
        generate_exercise(request_)
    assert (info.value.code, info.value.field) == (code, field)
    assert info.value.message


def test_error_messages_are_helpful():
    with pytest.raises(ExerciseInputError, match="支持：major"):
        generate("chord-tones", "C", "x")
    with pytest.raises(ExerciseInputError, match="至少 2 个"):
        generate("walking-bass", "C", "major")


def test_key_is_optional():
    assert generate("chord-tones", "C", "major").key is None
    assert generate("chord-tones", "C", "major", key="c").key == "C"
    assert generate("chord-tones", "F#", "minor", key="F♯m").key == "F#m"
