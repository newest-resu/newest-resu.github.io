# news/generator.py
# Bu dosya geriye dönük uyumluluk için tutulur.
# Asıl üretim scripts/build_latest.py içindedir.

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.build_latest import main  # noqa: E402


if __name__ == "__main__":
    main()
