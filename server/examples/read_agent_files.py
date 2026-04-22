"""
Example: run read_agent_files on a real agent directory.

Usage:
    uv run python examples/read_agent_files.py /path/to/agent/dir
    uv run python examples/read_agent_files.py /path/to/agent/dir runs memory
"""

import sys
from pathlib import Path


def read_agent_files(agent_dir: str, exclude_dirs: list[str] | None = None) -> list[dict[str, str]]:
    root = Path(agent_dir)
    excluded = set(exclude_dirs or [])
    result: list[dict[str, str]] = []

    for file_path in root.rglob("*"):
        if not file_path.is_file():
            continue
        rel = file_path.relative_to(root)
        if rel.parts and rel.parts[0] in excluded:
            continue
        try:
            result.append({"path": str(rel), "content": file_path.read_text(encoding="utf-8")})
        except Exception:
            continue

    return result


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: read_agent_files.py <agent_dir> [exclude_dir ...]")
        sys.exit(1)

    agent_dir = sys.argv[1]
    exclude_dirs = sys.argv[2:] or None

    result = read_agent_files(agent_dir, exclude_dirs=exclude_dirs)

    print(f"dir      : {agent_dir}")
    print(f"excluded : {exclude_dirs or 'none'}")
    print(f"files    : {len(result)}")
    print()

    for item in result:
        print(f"─── {item['path']}")
        # print(item["content"])
        # print()


if __name__ == "__main__":
    main()
