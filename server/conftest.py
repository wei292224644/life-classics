"""根级别 conftest：确保 server/ 根目录在 sys.path 最前面，防止同名子包遮蔽顶层包。"""
import sys
from pathlib import Path

_server_root = str(Path(__file__).parent)
if _server_root not in sys.path:
    sys.path.insert(0, _server_root)
