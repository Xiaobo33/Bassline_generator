import json

from bassline.web_api import exercise_json, make_exercise, options, options_json

C_MAJOR = {"type": "chord-tones", "chords": [{"root": "C", "quality": "major"}]}


def test_options():
    data = options()
    assert "C" in data["roots"]
    assert "major" in data["qualities"]
    assert {"value": "Cm", "label": "C 小调"} in data["keys"]
    assert json.loads(options_json()) == data


def test_make_exercise_returns_alphatex():
    data = make_exercise({**C_MAJOR, "key": "C"})
    assert data["exercise"]["key"] == "C"
    assert "\\ks c" in data["alphatex"]


def test_make_exercise_returns_error():
    data = make_exercise({"type": "chord-tones", "chords": [{"root": "H", "quality": "major"}]})
    assert data["error"]["code"] == "INVALID_ROOT"
    assert make_exercise(None)["error"]["code"] == "INVALID_REQUEST"


def test_tempo():
    assert "\\tempo 120" in make_exercise({**C_MAJOR, "tempo": 120})["alphatex"]
    assert "\\tempo 80" in make_exercise(C_MAJOR)["alphatex"]
    assert make_exercise({**C_MAJOR, "tempo": 300})["error"]["code"] == "INVALID_TEMPO"


def test_json_wrappers():
    # 网页（Pyodide）传进来和拿回去的都是 JSON 字符串
    assert "alphatex" in json.loads(exercise_json(json.dumps(C_MAJOR)))
    assert json.loads(exercise_json("not json"))["error"]["code"] == "INVALID_REQUEST"
