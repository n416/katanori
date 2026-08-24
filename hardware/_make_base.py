# case_v3.scad -> case_base.scad 抽出スクリプト（使い捨て）
#   1) top-level の `if (part == ...)` 文を全部除去（brace/paren バランスで文末まで）
#   2) `part = ...;` の行を除去
#   3) v3 専用モジュール（KEEP に無い module 定義）を除去。変数・関数・コメントは全部残す
import re, sys

SRC = 'hardware/case_v3.scad'
DST = 'hardware/case_base.scad'

KEEP = {
    'housing', 'hub_at', 'respeaker_at', 'oled_at', 'hex_pocket', 'hex_pocket_af',
    'win_rrect', 'win_bev_slab', 'win_chamfer_cut', 'whisker_plate', 'whisker_cut', 'whiskers_cut',
    'cham_box', 'round_box', 'outer_envelope',
    'bottom_boss', 'hatch_claws', 'ear_col', 'top_boss',
    'port_rrect', 'port_rrect_xz', 'wall_icon_x', 'icon_svg', 'icon_bolt',
    'oled_brackets', 'grille_xy', 'btn_socket', 'button_cap', 'button_clip',
    'seam_top_half', 'seam_front_half', 'front_ears', 'front_plate_raw',
    'tcb_at', 'tcb_box', 'tcb_ra', 'tcb_hous', 'tcb_slot_cut',
    'tail_cap', 'tail_at',   # 尻尾（トグルに被せる別刷り。2026-08-25 落としていたのを復活）
    'wall_port_x', 'wall_recess_x', 'wall_pocket_x', 'right_wall_ports_cut', 'xiao_pad',   # 右壁の口の彫り（v2/v3 の形。2026-08-25 復活）
}

s = open(SRC, encoding='utf-8').read()

def skip_ws_comments(s, i):
    n = len(s)
    while i < n:
        if s.startswith('//', i):
            j = s.find('\n', i)
            i = n if j < 0 else j + 1
        elif s.startswith('/*', i):
            j = s.find('*/', i)
            i = n if j < 0 else j + 2
        elif s[i] in ' \t\r\n':
            i += 1
        else:
            break
    return i

def scan_statement(s, i):
    """i は文の先頭（if/module ヘッダの後の本体、または任意の文）。文末の次位置を返す。"""
    n = len(s)
    i = skip_ws_comments(s, i)
    depth = 0
    while i < n:
        c = s[i]
        if s.startswith('//', i):
            j = s.find('\n', i); i = n if j < 0 else j + 1; continue
        if s.startswith('/*', i):
            j = s.find('*/', i); i = n if j < 0 else j + 2; continue
        if c == '"':
            i += 1
            while i < n and s[i] != '"':
                i += 2 if s[i] == '\\' else 1
            i += 1; continue
        if c in '([':
            depth += 1; i += 1; continue
        if c in ')]':
            depth -= 1; i += 1; continue
        if c == '{':
            if depth == 0:
                # ブロック本体 → 対応する } まで消費して文は終わり
                b = 1; i += 1
                while i < n and b > 0:
                    if s.startswith('//', i):
                        j = s.find('\n', i); i = n if j < 0 else j + 1; continue
                    if s.startswith('/*', i):
                        j = s.find('*/', i); i = n if j < 0 else j + 2; continue
                    if s[i] == '"':
                        i += 1
                        while i < n and s[i] != '"':
                            i += 2 if s[i] == '\\' else 1
                        i += 1; continue
                    if s[i] == '{': b += 1
                    elif s[i] == '}': b -= 1
                    i += 1
                return i
            depth += 1; i += 1; continue
        if c == '}':
            depth -= 1; i += 1; continue
        if c == ';' and depth == 0:
            return i + 1
        i += 1
    return i

def find_paren_end(s, i):
    """i は '(' の位置。対応する ')' の次を返す（コメント・文字列を考慮）。"""
    n = len(s); depth = 0
    while i < n:
        if s.startswith('//', i):
            j = s.find('\n', i); i = n if j < 0 else j + 1; continue
        if s.startswith('/*', i):
            j = s.find('*/', i); i = n if j < 0 else j + 2; continue
        if s[i] == '"':
            i += 1
            while i < n and s[i] != '"':
                i += 2 if s[i] == '\\' else 1
            i += 1; continue
        if s[i] == '(':
            depth += 1
        elif s[i] == ')':
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return i

out = []
i = 0
n = len(s)
removed_ifs = 0
removed_mods = []
line_start = True
while i < n:
    if line_start:
        m = re.match(r'if \(part ', s[i:])
        if m:
            # if の条件の閉じ括弧 → 本体文の終わりまで捨てる（行末の改行も）
            p = s.index('(', i)
            j = find_paren_end(s, p)
            j = scan_statement(s, j)
            if j < n and s[j] == '\n':
                j += 1
            removed_ifs += 1
            i = j
            line_start = True
            continue
        m = re.match(r'part\s*=\s*"[^"]*"\s*;[^\n]*\n?', s[i:])
        if m:
            i += m.end()
            continue
        m = re.match(r'module\s+(\w+)\s*\(', s[i:])
        if m and m.group(1) not in KEEP:
            name = m.group(1)
            p = s.index('(', i + m.start())
            j = find_paren_end(s, p)
            j = scan_statement(s, j)
            if j < n and s[j] == '\n':
                j += 1
            removed_mods.append(name)
            i = j
            line_start = True
            continue
    c = s[i]
    out.append(c)
    line_start = (c == '\n')
    i += 1

body = ''.join(out)

header = '''// ============================================================
// 📦 case_base.scad — v4 の土台（2026-08-25 に case_v3.scad から分離）
//   v4 が使う **寸法・座標の変数／関数／共通モジュール** だけを残した写し。
//   v3 の機構（壁・ブリッジ・トンネル・電池の蓋・棚・v3 の線）と part= の描画は全部除去してある。
//   このファイル単体では何も描かない（top-level の形は無い）。
//   v3 の完全な形は case_v3.scad（履歴・単体でいまも開ける）。生成: _make_base.py（case_v3 を後で直したら流し直す）
//   🔒 2026-08-25 X の式は付け替え済み（ユーザー「使ってる場所が間違ってる」）: 部品（つまみ・ハブ・OLED）の
//      X は検証済みの世界座標へ凍結し、壁（IN_X）は殻の面 85.554 ＋ 0.15 から導く。右の耳の内側の縁も凍結。
//   🔴 IN_Y / IN_Z は v3 の機構の変数から導かれた式のまま。値を変えたくなったら同様に式ごと書き直すこと。
// ============================================================
'''
# 元ヘッダ（v3 の説明 13 行）を新ヘッダに差し替え
lines = body.split('\n')
k = 0
while k < len(lines) and (lines[k].startswith('//') or lines[k].strip() == ''):
    k += 1
body = header + '\n'.join(lines[k:])

# ---- 2026-08-25 式の付け替え（ユーザー「使ってる場所が間違ってる」）----
#   部品（つまみ・ハブ・OLED・v3 の PB 面）の座標は、壁 IN_X から測る誤用だった。
#   全検査（線 17 束・当たり・軌跡）を通した時点の世界座標へ凍結し、壁は殻の面から導く。
FREEZE = [
    ("RIGHT_CL = 0.45;                                   // ⬜ XIAO の USB-C の殻 ↔ 右の壁の内面",
     "RIGHT_CL = -1.2;   // 🔒 2026-08-25 ユーザー「壁の移動が足りないだけ」: 殻を壁に貫通させ口の面を外面の 0.8 裏に（ハッチの充電口と同じ）。内面 84.354。経緯: 0.45（2.45 埋没）→ 0.15（すり鉢・2 段）→ -1.2（1 段）"),
    ("RSP_X     = 2.0;",
     "RSP_X     = 2.0;" + chr(10) + "LW_X = 1.694;   // 🔒 2026-08-25 左壁の内面 ＝ ReSpeaker の板の左端 2.024 − 0.33（右と同じ逃げ）。左壁に付く物と皮の左端はここから測る"),
    ("HUB_X  = (IN_X - HUB_L) / 2;",
     "HUB_X  = 6.002;   // 🔒 凍結 2026-08-25（旧式 (IN_X-HUB_L)/2 を IN_X=86.004 で評価した値・全配線検証済み。部品を壁から測らない）"),
    ("PB_X1 = IN_X - PB_STANDOFF;                        // 基板の裏の面（v2 は IN_X に密着）",
     "PB_X1 = 84.804;   // 凍結 2026-08-25（v3 の遺産・旧式 IN_X-PB_STANDOFF を IN_X=86.004 で評価。v4 の PB は電池の上）"),
    ("OLED_X0 = (IN_X - oled_l()) / 2; OLED_Y1 = 8.5;",
     "OLED_X0 = 8.002; OLED_Y1 = 8.5;   // 🔒 X は凍結 2026-08-25（旧式 (IN_X-oled_l())/2 を IN_X=86.004 で評価・全配線検証済み。壁が動いても OLED は動かない）"),
    ("KNOB_AT = [IN_X - TOP_MARGIN - knob_dish_d() / 2 + KNOB_DX, KNOB_YC, Z_TOP];",
     "KNOB_AT = [65.704, KNOB_YC, Z_TOP];   // 🔒 X は凍結 2026-08-25（旧式 IN_X-13-dish/2+6.8 を IN_X=86.004 で評価・全配線検証済み）"),
    ("function knob_seat_x0() = IN_X - TOP_MARGIN - knob_dish_d() / 2 + KNOB_DX - knob_bay_x() / 2;",
     "function knob_seat_x0() = KNOB_AT[0] - knob_bay_x() / 2;   // 凍結した KNOB_AT から導く（壁に依存しない）"),
    ("EAR_X = [[0, EAR_W], [IN_X - EAR_W, IN_X]]; EAR_Y0 = 0; EAR_Y1 = 8.0; EAR_T = 3.2;",
     "EAR_X = [[LW_X, EAR_W], [79.352, IN_X]]; EAR_Y0 = 0; EAR_Y1 = 8.0; EAR_T = 3.2;   // 🔒 耳の内側の縁（左 6.652・右 79.352）は OLED の L の都合＝凍結 2026-08-25。外側の縁と幅は壁に追従"),
    ("BOSSES = [[0, IN_Y - BOSS], [IN_X - BOSS, IN_Y - BOSS]];   // 後ろの 2 本だけ",
     "BOSSES = [[LW_X, IN_Y - BOSS], [IN_X - BOSS, IN_Y - BOSS]];   // 後ろの 2 本だけ（左端は壁 LW_X に追従・2026-08-25）"),
    ("module outer_envelope() { if (EDGE_ROUND) round_box([-WALL, -BEZ_T, -FLOOR_T], [OUT_X, OUT_Y, OUT_Z], CHAM); else cham_box([-WALL, -BEZ_T, -FLOOR_T], [OUT_X, OUT_Y, OUT_Z], CHAM); }",
     "module outer_envelope() { if (EDGE_ROUND) round_box([LW_X - WALL, -BEZ_T, -FLOOR_T], [OUT_X - LW_X, OUT_Y, OUT_Z], CHAM); else cham_box([LW_X - WALL, -BEZ_T, -FLOOR_T], [OUT_X - LW_X, OUT_Y, OUT_Z], CHAM); }   // 左端は LW_X に追従（2026-08-25）"),
    ("            color(\"#c9d0d8\") translate([-WALL, -BEZ_T, -FLOOR_T]) cube([IN_X + 2 * WALL, BEZ_T, Z_TOP + FLOOR_T]);   // 上は天面の厚みの分まで（45° で切られる）・下は床の裏まで（下前の丸みはフロントが持つ）",
     "            color(\"#c9d0d8\") translate([LW_X - WALL, -BEZ_T, -FLOOR_T]) cube([IN_X + 2 * WALL - LW_X, BEZ_T, Z_TOP + FLOOR_T]);   // 上は天面の厚みの分まで（45° で切られる）・下は床の裏まで（下前の丸みはフロントが持つ）"),
    ("            color(\"#c9d0d8\") translate([-WALL, -BEZ_T, IN_Z - EAR_T]) cube([IN_X + 2 * WALL, BEZ_T + 0.01, EAR_T]);   // （耳はここに付く）",
     "            color(\"#c9d0d8\") translate([LW_X - WALL, -BEZ_T, IN_Z - EAR_T]) cube([IN_X + 2 * WALL - LW_X, BEZ_T + 0.01, EAR_T]);   // （耳はここに付く）"),
    ('''module ear_col(x0) {
    difference() {
        color("#b6c0cc") translate([x0, EAR_Y0, IN_Z - EAR_T - EAR_COL_H]) cube([EAR_W, EAR_Y1 - EAR_Y0, EAR_COL_H]);
        translate([x0 + EAR_W / 2, (EAR_Y0 + EAR_Y1) / 2, IN_Z - EAR_T - NUT_T]) rotate([0, 0, 30]) hex_pocket(NUT_T + 1);   // 二面幅を X に
        translate([x0 + EAR_W / 2, (EAR_Y0 + EAR_Y1) / 2, IN_Z - EAR_T - EAR_COL_H - 1]) cylinder(d = SCR_D, h = EAR_COL_H + 2, $fn = 24);
    }
}''',
     '''module ear_col(x0, x1 = undef) {   // 2026-08-25 幅を耳の実スパンから取る（右の耳は壁の移動で EAR_W より痩せるため）
    w = (x1 == undef ? EAR_W : x1 - x0);
    difference() {
        color("#b6c0cc") translate([x0, EAR_Y0, IN_Z - EAR_T - EAR_COL_H]) cube([w, EAR_Y1 - EAR_Y0, EAR_COL_H]);
        translate([x0 + w / 2, (EAR_Y0 + EAR_Y1) / 2, IN_Z - EAR_T - NUT_T]) rotate([0, 0, 30]) hex_pocket(NUT_T + 1);   // 二面幅を X に
        translate([x0 + w / 2, (EAR_Y0 + EAR_Y1) / 2, IN_Z - EAR_T - EAR_COL_H - 1]) cylinder(d = SCR_D, h = EAR_COL_H + 2, $fn = 24);
    }
}'''),
]
for fa, fb in FREEZE:
    assert fa in body, fa[:50]
    body = body.replace(fa, fb)

open(DST, 'w', encoding='utf-8', newline='\n').write(body)
print(f'removed if(part) blocks: {removed_ifs}')
print(f'removed modules ({len(removed_mods)}): {" ".join(removed_mods)}')
