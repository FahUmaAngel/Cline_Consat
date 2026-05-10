import re
from collections import Counter
from pathlib import Path


def main() -> int:
    files = [
        Path("templates/dashboard.html"),
        Path("templates/data-explorer.html"),
        Path("index.html"),
        Path("dashboard.html"),
    ]

    any_dups = False
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        ids = re.findall(r'\bid\s*=\s*"([^"]+)"', text)
        counts = Counter(ids)
        dups = sorted((k, v) for k, v in counts.items() if v > 1)

        print(f"{path}: {len(ids)} ids, {len(dups)} duplicates")
        for k, v in dups:
            any_dups = True
            print(f"  DUP {k}: {v}")

    return 1 if any_dups else 0


if __name__ == "__main__":
    raise SystemExit(main())

