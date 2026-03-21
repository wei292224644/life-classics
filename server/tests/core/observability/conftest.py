"""确保 server 根目录优先于 tests/core 出现在 sys.path，避免同名包遮蔽。"""
import sys
from pathlib import Path

# server/ 根目录
_server_root = str(Path(__file__).parents[3])
if _server_root not in sys.path:
    sys.path.insert(0, _server_root)
