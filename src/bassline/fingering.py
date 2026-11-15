"""四弦贝斯指法：为每个音选一个弦位（弦 + 品）。

规则：
1. 根音（第一个音）放在 E 弦或 A 弦上，选品位最低的按弦位置。
2. 左手按「一指一品」覆盖 4 个品，有两种把位可选：
   - 食指按根音：覆盖 根音 ~ 根音+3 品（例：Cm 的 Eb 在 A 弦 6 品）
   - 中指按根音：覆盖 根音-1 ~ 根音+2 品（例：C 的 E 在 D 弦 2 品）
   两种都试，选超出把位最少的；一样时用食指把位。
3. 和上一个音只差半音时，留在同一根弦上（例：G G# A → D5 D6 D7）。
4. 尽量不用空弦：只有某个音除了空弦没有别的弹法时才用空弦。
5. 多个小节（和弦进行）时，每小节的根音都按规则 1 重新定位，再按规则 2 扩展三和弦手型。
   上一小节最后一个音如果和这个根音只差半音（walking bass 的经过音），
   就把它挪到根音同一根弦的相邻一品，手指顺着弦滑进根音。
   例：C → A：经过音 Bb 在 E 弦 6 品，滑到 E 弦 5 品的 A。

例：
- C 和弦音 C E G       → A3 D2 D5
- Cm 和弦音 C Eb G     → A3 A6 D5
- Am 根音–五度–八度    → E5 A7 D7
"""

from __future__ import annotations

from .models import TabPosition

# 标准调弦，从粗到细：弦名 → 空弦 MIDI 音高
STRINGS = {"E": 28, "A": 33, "D": 38, "G": 43}
MAX_FRET = 12
HAND_SPAN = 4  # 一个把位覆盖的品数


def positions_for(midi: int) -> list[TabPosition]:
    """一个音在指板上所有可弹的位置；有按弦位置时去掉空弦。"""
    options = [
        TabPosition(string, midi - open_midi)
        for string, open_midi in STRINGS.items()
        if 0 <= midi - open_midi <= MAX_FRET
    ]
    if not options:
        raise ValueError(f"MIDI {midi} 超出四弦贝斯 0–{MAX_FRET} 品的范围")
    fretted = [p for p in options if p.fret > 0]
    return fretted or options


def root_position(midi: int) -> TabPosition:
    options = positions_for(midi)
    on_low_strings = [p for p in options if p.string in ("E", "A")]
    return min(on_low_strings or options, key=lambda p: p.fret)


def outside_hand(fret: int, hand: int) -> int:
    """这个品超出把位多少品；在把位内（或空弦）为 0。hand 是食指所在的品。"""
    if fret == 0:
        return 0
    return max(hand - fret, fret - (hand + HAND_SPAN - 1), 0)


def assign_tabs_by_bar(bars: list[list[int]]) -> list[TabPosition]:
    """为多个小节选弦位：每小节的第一个音是这一小节的根音（规则 5）。"""
    tabs: list[TabPosition] = []
    prev_midi = None
    for midis in bars:
        bar_tabs = assign_tabs(midis)
        root = bar_tabs[0]
        if prev_midi is not None and abs(prev_midi - midis[0]) == 1:
            fret = root.fret + (prev_midi - midis[0])  # 同一根弦上，高半音就高一品
            if 0 <= fret <= MAX_FRET:
                tabs[-1] = TabPosition(root.string, fret)
        tabs += bar_tabs
        prev_midi = midis[-1]
    return tabs


def assign_tabs(midis: list[int]) -> list[TabPosition]:
    """为一串音选弦位，第一个音是根音。"""
    root = root_position(midis[0])
    index_finger_on_root = max(root.fret, 1)
    middle_finger_on_root = max(root.fret - 1, 1)

    best_tabs: list[TabPosition] = []
    best_cost = None
    for hand in (index_finger_on_root, middle_finger_on_root):
        tabs = _tabs_in_hand(midis, root, hand)
        cost = sum(outside_hand(t.fret, hand) for t in tabs)
        if best_cost is None or cost < best_cost:
            best_tabs, best_cost = tabs, cost
    return best_tabs


def _tabs_in_hand(midis: list[int], root: TabPosition, hand: int) -> list[TabPosition]:
    tabs = [root]
    for prev_midi, midi in zip(midis, midis[1:]):
        options = positions_for(midi)
        same_string = [p for p in options if p.string == tabs[-1].string]
        if abs(midi - prev_midi) == 1 and same_string:
            tabs.append(same_string[0])  # 半音：顺着同一根弦挪一品
        else:
            tabs.append(min(options, key=lambda p: (outside_hand(p.fret, hand), p.fret)))
    return tabs
