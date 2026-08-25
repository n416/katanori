// ============================================================
// 上シェルを外したときに見える物（2026-08-22・見るための道具。筐体の部品ではない）
// ============================================================
// ユーザー「上面をあけると、共通基盤からケーブルが取れるのでは」を確かめるための絵。
// 上シェルと、そこに付く部品を全部消し、**下シェルに残る物**だけを描く。
// ハブ基板の口には DuPont ハウジング（高さ 10・未実測）を立てて色を付ける:
//   赤 = 相手が上シェル側にいる口（上シェルを持ち上げるときに**ここで抜く**）
//   緑 = 相手も下シェル側にいる口（抜かなくてよい）
//
//   絵:  "C:\Program Files\OpenSCAD (Nightly)\openscad.exe" --backend=manifold --render //          --projection=o --autocenter --viewall --camera=0,0,0,8,0,0,260 --imgsize=1700,1250 //          -o hardware/_open_top_look.png hardware/_open_top_look.scad
//   数字: -D 'part="chk"' -D 'HID="OLED"' で、その口の真上の柱（ハウジングの頭〜天井）と
//          下シェル側の実体との当たり。0 ならまっすぐ上へ抜ける
// ============================================================
use <case_v2.scad>
include <hub_board_parts.scad>

part = "look";
HID  = "";
IN_Z = 48.1;
HOUS_H = 10.0;     // ⚠ DuPont ハウジングの高さ（未実測。case_v2.scad と同じ値）
UPPER_SIDE = ["OLED", "AS5600", "REED", "PWR", "INA", "BTN2", "PHOUT"];   // 相手が上シェル側
function is_upper(id) = len([for (u = UPPER_SIDE) if (u == id) 1]) > 0;
function hdr(id) = [for (h = HUB_HEADERS) if (h[0] == id) h][0];
// 口の足元の外形（箱の座標）。ピンの並び ＋ 片側 1.27
function foot(id) = let (h = hdr(id), c = port_at(id),
                         w = h[6] - h[4] + 2.54, l = h[7] - h[5] + 2.54)
    [[c[0] - w / 2, c[1] - l / 2, c[2]], [w, l]];

module housing(id) { f = foot(id);
    translate(f[0]) cube([f[1][0], f[1][1], HOUS_H]); }
module column(id, m = 1.5) { f = foot(id);     // ハウジングの頭から天井まで
    translate([f[0][0] - m, f[0][1] - m, f[0][2] + HOUS_H]) cube([f[1][0] + 2 * m, f[1][1] + 2 * m, IN_Z - f[0][2] - HOUS_H]); }

// 下シェルに残る物。PARTS_V2 の 0 ReSpeaker / 2 ハブ / 8 トグル / 9 尻尾のキャップ
module lower_side() { shell_lower(); for (i = [0, 2, 8, 9]) parts_v2(i); }

if (part == "look") {
    color("#b0b8c2") shell_lower();
    color("#6c7a89") for (i = [0, 2, 8, 9]) parts_v2(i);
    for (h = HUB_HEADERS) { id = h[0]; c = port_at(id);
        color(is_upper(id) ? "#e6194b" : "#3cb44b") housing(id);
        // 文字はピンの並びと直交する向きに寝かせる（隣の口と重ならない）
        along_x = (hdr(id)[5] == hdr(id)[7]);
        color(is_upper(id) ? "#e6194b" : "#3cb44b")
            translate([c[0], c[1], c[2] + HOUS_H + 0.5]) rotate([0, 0, along_x ? 90 : 0])
                linear_extrude(0.6) text(id, size = 2.6, halign = "center", valign = "center");
    }
}
else if (part == "chk") intersection() { column(HID); lower_side(); }
