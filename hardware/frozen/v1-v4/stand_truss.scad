// カタノリ 卓上スタンド ― トラスのみ（2026-08-08・ユーザー案「土台なしレールなし」）
//
// 土台も溝もレールも無い。**トラスが机に立ち、基板がそれにボルト留めされる**だけ。
// 支えは「基板の下辺の線」＋「トラスの足」の2つ。
//
// 成立の根拠（📄 = 公式CAD ReSpeakerLitev1.1.step / docs/RESPEAKER-LITE.md 5.6）:
//   - 📄 基板の下辺（下から0の線）には部品が載っていない。全長で素の板なので机に直接立つ
//     （スイッチK1/K2は下から4.11から、ジャックのハンダ足でも下から2.18から）
//   - 📄 留め先の穴2つ。A=左2.492/下から31.577、B=左60.202/下から2.657、どちらもφ2.20。
//     ✅実物に2mmネジが通ることをユーザーが確認（2026-08-08）
//   - 📄 A・Bの裏（XIAO面側）はどちらも無地。Aの裏はXIAO上端(約25.7)より上、
//     Bの裏は最寄りの部品C16が下から6.07
//   - ⚠ **A→Bを直線で結ぶとXIAO＋ヘッダー（左から2〜20・面から高さ10）を突き抜ける。**
//     なので四面体の本体はXIAOより後ろに置き、穴へは短い柱2本だけを前へ伸ばす。
//     こうすると稜を曲げずに済み、四面体は幾何形状としてきれいなまま残る
//
// 座標: X=左から / Z=下から / Y: **XIAO面が0、後ろが負**（マイク面が +BOARD_T）。
//       机は世界z=0。基板は下辺で机に乗る
//
//   openscad -o truss.png --render -D 'SHOW="assembly"' stand_truss.scad

use <respeaker_lite.scad>

SHOW = "assembly";   // "assembly" | "part" | "check"
$fn  = 48;

TILT  = 15;      // 後傾
BEAM  = 5.0;     // 稜の角柱の一辺
POST  = 6.5;     // 穴へ伸ばす柱の太さ
BACK  = 14.0;    // 四面体の本体を基板のXIAO面から何mm後ろに置くか
                 // ⚠ XIAO＋ヘッダーが面から10mm出ているので、それより大きいこと
TAIL  = 28.0;    // 足を後ろへどれだけ伸ばすか（倒れにくさに直結）
SCREW_D = 2.4;
NUT_AF  = 4.3;
NUT_T   = 1.9;

HOLE_A = [ 2.492, 31.577];
HOLE_B = [60.202,  2.657];

// 四面体の4頂点（基板系）
T1 = [HOLE_A[0], -BACK, HOLE_A[1]];      // 穴Aの真後ろ
T2 = [HOLE_B[0], -BACK, HOLE_B[1]];      // 穴Bの真後ろ
// 足は基板の短辺より外へ出す。そこから前へ橇（そり）を伸ばして爪先を作る。
// ⚠ 基板の下辺が机に付いているので、足を基板の下へ通すことはできない。
//    前へ出すには短辺の外側（左端より左・右端より右）を回り込むしかない
T3 = [ -8.0, -TAIL, -6.0];               // 足・左（机で切る）
T4 = [ 90.0, -TAIL, -6.0];               // 足・右
SLED_BACK  = 26.0;   // 橇の後ろ端（世界y）
SLED_FRONT = 17.0;   // 橇の前端＝爪先（世界y）。ここが前倒れの余裕を決める
SLED_H     =  5.0;   // 橇の高さ
TP = [T1, T2, T3, T4];
EDGES = [[0,1],[0,2],[0,3],[1,2],[1,3],[2,3]];

module in_bf() { rotate([TILT, 0, 0]) children(); }
module pt(p) { translate(p) cube(0.002, center = true); }
module beam(p, q, s) { hull() { translate(p) cube(s, center = true); translate(q) cube(s, center = true); } }

module truss_raw() {
    // 四面体（稜は角柱＝平面と角のまま。丸みは入れない）
    for (e = EDGES) beam(TP[e[0]], TP[e[1]], BEAM);
    for (p = TP) translate(p) cube(BEAM + 1.5, center = true);
    // 穴へ伸ばす柱2本。先端は基板のXIAO面(y=0)で切って平らな座にする
    beam(T1, [HOLE_A[0], 1.0, HOLE_A[1]], POST);
    beam(T2, [HOLE_B[0], 1.0, HOLE_B[1]], POST);
}

// 🔴 橇（机に沿う角箱の runner）は作ったが**廃止**（2026-08-08・ユーザー
//    「切り落とされた感じがよかったのに」）。この造形の顔は、斜めの梁を
//    **机の平面で斬った断面**で出ている。机に沿う箱を足すと言語が混ざる。
//    前倒れの余裕（約12gf）は別の手で稼ぐこと。橇では解かない。
module truss() {
    difference() {
        in_bf() difference() {
            truss_raw();
            // ネジ2本（基板の面に垂直・マイク面側から挿す）とナットのポケット
            for (h = [HOLE_A, HOLE_B]) {
                translate([h[0], 2, h[1]]) rotate([90, 0, 0])
                    cylinder(d = SCREW_D, h = BACK + 6);
                translate([h[0], -BACK + 1.0, h[1]]) rotate([90, 0, 0])
                    cylinder(d = NUT_AF / cos(30), h = NUT_T, $fn = 6);
            }
            // 座: 基板のXIAO面(y=0)より前は削る
            translate([-100, 0, -100]) cube([400, 200, 400]);
        }
        // 足は机(世界z=0)で切る
        translate([-100, -200, -100]) cube([400, 400, 100]);
    }
}

module board() { in_bf() respeaker_lite(); }

if (SHOW == "assembly") { board(); color("#c94") truss(); }
else if (SHOW == "part") truss();
else if (SHOW == "check") intersection() { truss(); board(); }
