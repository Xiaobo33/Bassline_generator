# Bassline_generator

规则驱动的贝斯练习生成器（核心逻辑，无运行时依赖，Python ≥ 3.10）。

```python
from bassline import generate_exercise, ExerciseInputError

try:
    ex = generate_exercise({
        "type": "walking-bass",
        "chords": [  # 和弦进行，2–16 个
            {"root": "D", "quality": "minor7"},
            {"root": "G", "quality": "dominant7"},
            {"root": "C", "quality": "major7"},
        ],
    })
    for n in ex.notes:
        print(n.pitch, n.midi, n.duration, n.bar, n.beat, n.role)
    data = ex.to_dict()  # 可直接 json.dumps
except ExerciseInputError as e:
    print(e.code, e.field, e.message)
```

- 练习类型：`chord-tones`、`root-fifth-octave`、`walking-bass`、`combined`（前三种在同一个和弦进行上依次各走一遍）。所有练习都用 `chords` 传和弦进行，每个和弦一小节：和弦音、根音–五度–八度 1–16 个，`walking-bass` 和 `combined` 2–16 个
- 可选 `key`：练习所在的调，决定五线谱调号，如 `"C"`、`"Eb"`、`"Am"`、`"Cm"`；不写则不加调号，直接在音符上标升降号
- 和弦类型：`major` `minor` `diminished` `augmented` `sus4` `dominant7` `major7` `minor7` `half-diminished7` `diminished7`
- 数据结构见 `src/bassline/models.py`，指法规则见 `fingering.py`，alphaTex 导出见 `alphatex.py`

```sh
uv sync                          # 安装开发依赖（pytest）
uv run pytest                    # 运行测试
uv run python examples/demo.py   # 打印示例输出（文字）
python3 web/server.py            # 本地预览网页 http://localhost:8000（需联网加载 Pyodide 和 alphaTab）
```

## 网页

`web/index.html` 是纯静态页面：用 [Pyodide](https://pyodide.org) 在浏览器里运行 `src/bassline/` 的 Python 代码生成乐谱，
用 [alphaTab](https://alphatab.net) 显示五线谱 + TAB 并播放。不需要后端服务器，可以直接放在 GitHub Pages 上。

- 本地预览：`python3 web/server.py`（不能直接双击打开 index.html，浏览器不允许 file:// 页面读取 .py 文件）
- 发布：推送到 `main` 后，`.github/workflows/pages.yml` 会跑测试、组装网站（`index.html` + `bassline/*.py`）并发布。
  第一次使用前要在仓库 Settings → Pages → Source 选择 "GitHub Actions"。
- `src/bassline/` 里新增 .py 文件时，要把文件名加到 `web/index.html` 的 `PYTHON_FILES` 里。
