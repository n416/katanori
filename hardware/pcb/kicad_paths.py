# -*- coding: utf-8 -*-
"""KiCad 10 の置き場所。PC ごとに違うので、ここだけで探す。

別荘の PC は C:\\Program Files（全ユーザー向け）、本拠点の PC は winget で入れた
%LOCALAPPDATA%\\Programs（ユーザー向け）に入っている。環境変数 KICAD_DIR があればそれを使う。
"""

import os
import pathlib

_CANDIDATES = [
    os.environ.get("KICAD_DIR", ""),
    r"C:\Program Files\KiCad\10.0",
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "KiCad", "10.0"),
]


def _find():
    for c in _CANDIDATES:
        if c and (pathlib.Path(c) / "bin" / "kicad-cli.exe").exists():
            return pathlib.Path(c)
    raise SystemExit("KiCad 10 が見つからない。KICAD_DIR に KiCad\\10.0 のフォルダを入れること。探した場所: "
                     + " / ".join(c for c in _CANDIDATES if c))


KICAD = _find()
CLI = str(KICAD / "bin" / "kicad-cli.exe")
SYMDIR = KICAD / "share" / "kicad" / "symbols"
FPDIR = KICAD / "share" / "kicad" / "footprints"
