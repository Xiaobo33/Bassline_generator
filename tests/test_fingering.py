from bassline import SUPPORTED_QUALITIES, SUPPORTED_ROOTS, TabPosition, generate_exercise
from bassline.fingering import STRINGS, assign_tabs


def test_c_major_stays_in_one_position():
    # C E G → A 弦 3 品、D 弦 2 品、D 弦 5 品（不用 G 空弦）
    assert assign_tabs([36, 40, 43]) == [TabPosition("A", 3), TabPosition("D", 2), TabPosition("D", 5)]


def test_root_fifth_octave_shape():
    # 根音某弦 x 品 → 五度高一根弦 x+2 品 → 八度再高一根弦 x+2 品
    def shape(root):
        notes = generate_exercise({"type": "root-fifth-octave", "chords": [{"root": root, "quality": "minor"}]}).notes
        return [(n.tab.string, n.tab.fret) for n in notes]

    assert shape("A") == [("E", 5), ("A", 7), ("D", 7)]
    assert shape("C") == [("A", 3), ("D", 5), ("G", 5)]
    assert shape("G") == [("E", 3), ("A", 5), ("D", 5)]


def frets(midis):
    return [(t.string, t.fret) for t in assign_tabs(midis)]


def test_minor_third_on_same_string_as_root():
    # C Eb G → A3 A6 D5（食指按根音）
    assert frets([36, 39, 43]) == [("A", 3), ("A", 6), ("D", 5)]


def test_semitone_steps_stay_on_one_string():
    # C → Am：C E G G# A → A3 D2 D5 D6 D7
    assert frets([36, 40, 43, 44, 45]) == [("A", 3), ("D", 2), ("D", 5), ("D", 6), ("D", 7)]
    # Dm7 → G7：D F A Ab G → A5 A8 D7 D6 D5
    assert frets([38, 41, 45, 44, 43]) == [("A", 5), ("A", 8), ("D", 7), ("D", 6), ("D", 5)]


def test_open_string_only_when_unavoidable():
    assert assign_tabs([28]) == [TabPosition("E", 0)]  # E1 只能弹空弦
    assert assign_tabs([43]) != [TabPosition("G", 0)]  # G2 可以按 D 弦 5 品


def all_exercises():
    for root in SUPPORTED_ROOTS:
        for quality in SUPPORTED_QUALITIES:
            chord = {"root": root, "quality": quality}
            yield generate_exercise({"type": "chord-tones", "chords": [chord]})
            yield generate_exercise({"type": "root-fifth-octave", "chords": [chord]})
            for target in SUPPORTED_ROOTS:
                yield generate_exercise({"type": "walking-bass", "chords": [chord, {"root": target, "quality": "major"}]})


def test_every_tab_matches_its_pitch_and_stays_near_its_bar_root():
    for exercise in all_exercises():
        notes = exercise.notes
        bar_roots = {}
        for i, note in enumerate(notes):
            assert 0 <= note.tab.fret <= 12
            assert STRINGS[note.tab.string] + note.tab.fret == note.midi
            root = bar_roots.setdefault(note.bar, note.tab)  # 每小节第一个音是这一小节的根音
            assert root.string in ("E", "A"), exercise.description
            if note.role == "chromatic-approach":
                # 经过音属于下一个把位：在下一个根音同一根弦的相邻一品（下一个根音是空弦且从下方进入时除外）
                nxt = notes[i + 1].tab
                assert note.tab.string == nxt.string or nxt.fret == 0, exercise.description
                continue
            hand = max(root.fret, 1)  # 根音是空弦时，左手在第 1 把位
            if note.tab.fret > 0:
                assert abs(note.tab.fret - hand) <= 5, exercise.description  # 离这一小节的根音不超过 5 品


def test_walking_1625_roots_and_approach_on_next_root_string():
    chords = [{"root": r, "quality": "major"} for r in ["C", "A", "D", "G"]]
    notes = generate_exercise({"type": "walking-bass", "chords": chords}).notes
    tabs = [(n.tab.string, n.tab.fret) for n in notes]
    # 根音：C 在 A 弦 3 品、A 在 E 弦 5 品、D 在 A 弦 5 品、G 在 E 弦 3 品
    assert [tabs[i] for i in (0, 4, 8, 12)] == [("A", 3), ("E", 5), ("A", 5), ("E", 3)]
    # 每小节第 1–3 拍是三和弦手型，和「和弦音」练习的指法一样
    assert tabs[0:3] == [("A", 3), ("D", 2), ("D", 5)]
    assert tabs[4:7] == [("E", 5), ("A", 4), ("A", 7)]
    # 经过音在下一个根音的同一根弦、相邻一品：Bb E6 → A E5，Eb A6 → D A5，Ab E4 → G E3
    assert [tabs[i] for i in (3, 7, 11)] == [("E", 6), ("A", 6), ("E", 4)]


def test_long_progression_tabs_match_pitches():
    chords = [{"root": r, "quality": "dominant7"} for r in ["F", "Bb", "F", "F", "Bb", "Bb", "F", "F", "C", "Bb", "F", "C"]]
    for note in generate_exercise({"type": "walking-bass", "chords": chords}).notes:
        assert STRINGS[note.tab.string] + note.tab.fret == note.midi
        assert note.tab.fret <= 8  # 根音都在低把位，整条线不会跑到高把位
