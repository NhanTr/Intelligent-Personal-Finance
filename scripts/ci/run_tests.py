"""Run the same frozen Python 3.12 test suite locally and in GitHub Actions."""

from pathlib import Path
import subprocess
import sys


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    commands = [
        ["uv", "sync", "--python", "3.12", "--frozen"],
        ["uv", "run", "--python", "3.12", "--frozen", "--no-sync",
         "python", "-m", "pytest", "-v"],
    ]
    try:
        for command in commands:
            print("+ " + " ".join(command), flush=True)
            result = subprocess.run(command, cwd=root, check=False)
            if result.returncode:
                return result.returncode
    except FileNotFoundError:
        print("Install uv before running this command: https://docs.astral.sh/uv/", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
