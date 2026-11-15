"""本地预览服务器：python3 web/server.py，会自动打开 http://localhost:8000

乐谱是在浏览器里用 Pyodide 运行 Python 生成的，这个服务器只负责提供文件，
目录结构和发布到 GitHub Pages 后一样：
- /                  → web/index.html
- /bassline/xxx.py   → src/bassline/xxx.py

不能直接双击打开 index.html：浏览器不允许 file:// 页面读取 .py 文件。
只用 Python 自带的 http.server，不需要安装任何东西。页面从 CDN 加载 Pyodide 和 alphaTab，所以需要联网。
"""

import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "web" / "index.html"
PACKAGE = ROOT / "src" / "bassline"
PORT = 8000


def resolve(path: str) -> Path | None:
    """把网址路径对应到本地文件；不存在或不允许访问时返回 None。"""
    path = path.split("?")[0]
    if path == "/":
        return PAGE
    if path.startswith("/bassline/") and path.endswith(".py"):
        file = PACKAGE / path.removeprefix("/bassline/")
        if file.parent == PACKAGE and file.is_file():  # 只允许包目录下的 .py 文件
            return file
    return None


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        file = resolve(self.path)
        if file is None:
            self.send_error(404)
            return
        body = file.read_bytes()
        content_type = "text/html; charset=utf-8" if file.suffix == ".html" else "text/plain; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")  # 改了代码刷新页面就能看到
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)  # 只在本机访问
    url = f"http://localhost:{PORT}"
    print(f"已启动：{url}  （按 Ctrl+C 停止）")
    webbrowser.open(url)  # 自动打开浏览器
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
