"""运行：uv run python examples/demo.py（也可以直接 python3 examples/demo.py）"""

import sys
from pathlib import Path

# 未安装 bassline 包时（例如用系统 Python 直接运行），从 src 目录导入
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bassline import ExerciseInputError, generate_exercise

requests = [
    {"type": "chord-tones", "chords": [{"root": "C", "quality": "major"}]},
    {"type": "chord-tones", "chords": [{"root": "Eb", "quality": "minor7"}]},
    {"type": "root-fifth-octave", "chords": [{"root": "C", "quality": "major"}]},
    {"type": "walking-bass", "chords": [{"root": "C", "quality": "major7"}, {"root": "F", "quality": "major7"}]},
    {"type": "walking-bass", "chords": [{"root": "D", "quality": "minor7"}, {"root": "G", "quality": "dominant7"}, {"root": "C", "quality": "major7"}]},
    {"type": "chord-tones", "chords": [{"root": "H", "quality": "major"}]},
    {"type": "chord-tones", "chords": [{"root": "C", "quality": "ninth"}]},
]

for req in requests:
    print("输入:", req)
    try:
        ex = generate_exercise(req)
    except ExerciseInputError as e:
        print("错误:", e.to_dict(), "\n")
        continue
    print(ex.description)
    for n in ex.notes:
        print(f"  {n.pitch:<5} midi={n.midi:<3} {n.duration:<8} 第{n.bar}小节第{n.beat:g}拍  {n.chord_symbol:<6} {n.tab.string}弦{n.tab.fret:>2}品  {n.role:<19} {n.interval}")
    print()
