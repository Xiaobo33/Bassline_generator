import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "web"))

from server import PACKAGE, PAGE, resolve  # noqa: E402


def test_serves_page_and_package_files():
    assert resolve("/") == PAGE
    assert resolve("/bassline/generator.py") == PACKAGE / "generator.py"
    assert resolve("/bassline/web_api.py?v=1") == PACKAGE / "web_api.py"


def test_refuses_everything_else():
    assert resolve("/bassline/missing.py") is None
    assert resolve("/bassline/../../web/server.py") is None  # 不能跳出包目录
    assert resolve("/README.md") is None
    assert resolve("/web/server.py") is None
