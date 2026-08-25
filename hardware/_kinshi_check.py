# 禁止コマンドの番人（2026-08-24）
# 原典: case_v2.scad:422 の禁止ルール。反転系のコマンドは使わない。回転は rotate だけで書く。
# 同じ行に「例外承認:」の注記（理由つき）が無ければ赤。0 件になるまで赤が出続ける。
# 使い方: python _kinshi_check.py
import glob, re, sys
BAN = re.compile(r'mirror\s*\(|scale\s*\(\s*\[?\s*-')   # 検出対象のコマンド名（機械が読む場所にだけ置く）
red = []
for f in sorted(glob.glob('*.scad')):
    for i, line in enumerate(open(f, encoding='utf-8', errors='replace'), 1):
        if BAN.search(line) and '例外承認:' not in line and not line.lstrip().startswith('//'):
            red.append(f"{f}:{i}")
print(f"禁止コマンド {len(red)} 件" + ("（合格）" if not red else ""))
for r in red: print(" ", r)
sys.exit(0 if not red else 1)
