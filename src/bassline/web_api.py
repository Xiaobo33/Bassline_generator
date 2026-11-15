"""给网页用的入口。

网页通过 Pyodide 在浏览器里运行 Python，直接调用这里的函数，不需要服务器。
输入输出用 JSON 字符串（options_json / exercise_json），避免 JavaScript 和 Python 之间转换对象的麻烦。
"""

from __future__ import annotations

import json

from .alphatex import key_label, to_alphatex
from .generator import generate_exercise
from .models import ExerciseInputError
from .theory import SUPPORTED_KEYS, SUPPORTED_QUALITIES, SUPPORTED_ROOTS


def options() -> dict:
    """页面上的选项：根音、和弦类型、调。"""
    return {
        "roots": list(SUPPORTED_ROOTS),
        "qualities": list(SUPPORTED_QUALITIES),
        "keys": [{"value": k, "label": key_label(k)} for k in SUPPORTED_KEYS],
    }


def make_exercise(request: object) -> dict:
    """生成练习，返回 {"exercise": ..., "alphatex": ...}；输入有误时返回 {"error": {...}}。

    除了 generate_exercise 的参数，还可以带 "tempo"（每分钟拍数，40–200，默认 80），只影响乐谱和播放速度。
    """
    tempo = 80
    if isinstance(request, dict) and "tempo" in request:
        request = dict(request)
        tempo = request.pop("tempo")
        if not isinstance(tempo, int) or not 40 <= tempo <= 200:
            return {"error": {"code": "INVALID_TEMPO", "field": "tempo", "message": "速度必须是 40–200 之间的整数。"}}
    try:
        exercise = generate_exercise(request)  # type: ignore[arg-type]
    except ExerciseInputError as e:
        return {"error": e.to_dict()}
    return {"exercise": exercise.to_dict(), "alphatex": to_alphatex(exercise, tempo=tempo)}


def options_json() -> str:
    return json.dumps(options(), ensure_ascii=False)


def exercise_json(request_json: str) -> str:
    try:
        request = json.loads(request_json)
    except json.JSONDecodeError:
        request = None  # 交给 generate_exercise 报 INVALID_REQUEST
    return json.dumps(make_exercise(request), ensure_ascii=False)
