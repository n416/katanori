# Freerouting 2.4.1（Windows・Java 同梱）

`hardware/pcb/route.py` が使う自動配線の実行ファイル。展開した物をそのまま置いてある（141MB）。

- 出どころ: https://github.com/freerouting/freerouting （2.4.1 の Windows 版を展開した物）
- ライセンス: Freerouting は GPL-3.0。ソースは上の GitHub にある。同梱の Java の実行環境のライセンスは `runtime/legal/` にある。
- 🔒 ユーザー 2026-09-15: git に入れる（2 か所の PC で clone するだけで動くように）。それまでは `.gitignore` で外していて、別の PC から手で持ってくる必要があった。
- ⚠ CLI で渡した `--router.*` の設定は `%APPDATA%\freerouting\freerouting.json` に残り、次の起動にも効く。`route.py` は板ごとに全部の値を明示する（docs/VOICE-BOARD.md 10 章）。
