import sys
from pathlib import Path

# Python 3.13.11 skips .pth files inside hidden directories (UF_HIDDEN),
# which breaks editable installs inside .venv. Manually add package src dirs.
server_root = Path(__file__).parent
for src_dir in server_root.glob("packages/*/src"):
    path = str(src_dir)
    if path not in sys.path:
        sys.path.insert(0, path)
