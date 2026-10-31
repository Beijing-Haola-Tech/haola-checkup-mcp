"""免安装启动器：不 pip install 也能跑。

    python scripts/haola.py quote --budget 800 --concerns "久坐"
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from haola_checkup.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
