"""
Example: run read_agent_files on a real agent directory.

Usage:
    uv run python examples/read_agent_files.py /path/to/agent/dir
    uv run python examples/read_agent_files.py /path/to/agent/dir runs memory
"""

import sys
from unittest.mock import MagicMock

from zenve_services.filesystem import FilesystemService


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: read_agent_files.py <agent_dir> [exclude_dir ...]")
        sys.exit(1)

    agent_dir = sys.argv[1]
    exclude_dirs = sys.argv[2:] or None

    svc = FilesystemService(MagicMock())
    result = svc.read_agent_files(agent_dir, exclude_dirs=exclude_dirs)

    print(f"dir      : {agent_dir}")
    print(f"excluded : {exclude_dirs or 'none'}")
    print(f"files    : {len(result)}")
    print()

    for item in result:
        print(f"─── {item['path']}")
        print(item["content"])
        print()


if __name__ == "__main__":
    main()
