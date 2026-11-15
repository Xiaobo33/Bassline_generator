import pytest

from bassline import generate_exercise, to_alphatex
from bassline.alphatex import alphatex_key, key_label


def walking(r1, q1, r2, q2):
    return generate_exercise({"type": "walking-bass", "chords": [{"root": r1, "quality": q1}, {"root": r2, "quality": q2}]})


def test_dm7_to_g7():
    tex = to_alphatex(walking("D", "minor7", "G", "dominant7"))
    assert "\\staff {score tabs}" in tex
    assert "\\tuning (G2 D2 A1 E1)" in tex
    # A 弦 5 品、A 弦 8 品、D 弦 7 品、E 弦 4 品（Ab）| E 弦 3 品全音符（G）
    assert tex.endswith('\\clef F4 5.3.4 {ch "Dm7"} 8.3.4 7.2.4 4.4{acc b}.4 | 3.4.1 {ch "G7"}\n')


def test_accidentals_follow_our_spelling():
    tex = to_alphatex(generate_exercise({"type": "chord-tones", "chords": [{"root": "C", "quality": "diminished7"}]}))
    assert "{acc b}" in tex  # Eb、Gb
    assert "{acc bb}" in tex  # Bbb


def test_tempo_option():
    assert "\\tempo 120" in to_alphatex(walking("C", "major", "F", "major"), tempo=120)


@pytest.mark.parametrize(("key", "expected"), [("C", "c"), ("Eb", "eb"), ("F#", "f#"), ("Cm", "cminor"), ("A#m", "a#minor")])
def test_alphatex_key(key, expected):
    assert alphatex_key(key) == expected


def test_no_key_signature_by_default():
    tex = to_alphatex(generate_exercise({"type": "chord-tones", "chords": [{"root": "Eb", "quality": "major7"}]}))
    assert "\\ks" not in tex
    assert "\\subtitle" not in tex
    assert "{acc b}" in tex  # 没有调号时，降号直接标在音符上


def test_key_signature_when_key_given():
    request = {"type": "walking-bass", "chords": [{"root": "D", "quality": "minor7"}, {"root": "G", "quality": "dominant7"}], "key": "C"}
    tex = to_alphatex(generate_exercise(request))
    assert "\\clef F4 \\ks c " in tex
    assert '\\subtitle "调：C 大调"' in tex
    request = {"type": "chord-tones", "chords": [{"root": "C", "quality": "minor"}], "key": "Cm"}
    assert "\\ks cminor " in to_alphatex(generate_exercise(request))


def test_key_label():
    assert key_label("Eb") == "Eb 大调"
    assert key_label("Cm") == "C 小调"


def test_rests_fill_incomplete_bars():
    # 三和弦只有 3 拍，补一个四分休止符凑满一小节
    tex = to_alphatex(generate_exercise({"type": "chord-tones", "chords": [{"root": "C", "quality": "major"}]}))
    assert tex.endswith('3.3.4 {ch "C"} 2.2.4 5.2.4 r.4\n')
    tex = to_alphatex(generate_exercise(
        {"type": "combined", "chords": [{"root": "C", "quality": "major"}, {"root": "F", "quality": "major"}]}
    ))
    bars = tex.splitlines()[-1].split(" | ")
    assert len(bars) == 6  # 和弦音 2 小节 + 根音–五度–八度 2 小节 + walking bass 2 小节
    assert all(bar.endswith("r.4") for bar in bars[:4])  # 三和弦和根音–五度–八度都是 3 拍，各补一个休止符
