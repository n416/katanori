// カタノリ 卓上スタンド ― 竹ひごモックの再現（2026-08-08）
//
// ユーザーが竹ひごとホットボンドで実物のモックを作った。**それが答え。**
// このファイルは、その骨組みをCADに起こしたもの。
//
// 写真から読み取った構成:
//   - 机の上で三角を作り、基板の裏へ集まる**立体トラス**（平面トラスではない）
//   - 上端は**基板の上辺に掛かる**。ネジではなく、上辺を跨いで押さえている
//   - 基板は下辺で机に立ち、後ろへトラスへ預ける。
//     **自重がトラスを押して足を机に押し付ける向き**（計算で行き着いた向きと同じ）
//   - 節点はホットボンドの団子。丸棒どうしが角度を持って集まる
//     → 断面は丸でよい。以前「幾何学的に」と言われて球をやめたが、あれは
//        断面の話ではなく**骨組みの形**の話だった
//
// 🔴 確認の方法（ユーザー指摘 2026-08-08）:
//   **3D座標を数字で復唱しても人間は想像できない。** 形の確認は
//   「同じアングルで絵を作って実物写真と並べる」でやること。数字の読み合わせはしない。
//
// 座標: 世界。机が z=0、基板は下辺で机に乗り、後傾TILT°で -Y 側へ倒れる。
//
//   openscad -o tri.png --render -D 'SHOW="assembly"' stand_tripod.scad

use <respeaker_lite.scad>

SHOW = "assembly";   // "assembly" | "part" | "check"
$fn  = 32;

TILT   = 15;
ROD    = 4.0;     // 丸棒の直径（実物の竹ひごは約3mm）
NODE   = 5.6;     // 節点の団子

// ---- 骨格（ユーザーの言葉どおり）----
//   「4面体の上部頂点から、傾斜したバーが出ていること」
//   「同立体の1辺が4面体の底面トラスを作っている事が大事」
// → 四面体は **1辺を机に置く**。その辺が底面トラス。残り2頂点が上。
//   上の頂点から**傾斜したバー**が前へ出て、基板の上辺を受ける。
//   机に接しているのは「四面体の底辺1本」と「基板の下辺の線」の2本
BOT_Y  = -42.0;   // 底面トラス（机の上の1辺）の位置
BOT_L  =   8.0;   // その辺の左端
BOT_R  =  74.0;   // 右端
U_X    =  41.0;   // 上の頂点（前寄り・高い）
U_Y    = -18.0;
U_Z    =  33.0;
V_X    =  41.0;   // もう一つの上の頂点（後ろ寄り・低い）
V_Y    = -62.0;
V_Z    =  13.0;
BAR_L  =  12.0;   // 傾斜バーが基板の上辺に触れる位置（左から）
BAR_R  =  70.0;
HOOK_GAP  = 2.6;   // 爪の内寸（板1.51＋部品0.6の逃げ）
HOOK_DROP = 5.0;   // マイク面側へ回り込む深さ

function bf(x, zb) = [x, -zb * sin(TILT), zb * cos(TILT)];   // 基板系(左から,下から)→世界

D1 = [BOT_L, BOT_Y, 0];   D2 = [BOT_R, BOT_Y, 0];   // 底面トラス＝机に置く1辺
U  = [U_X, U_Y, U_Z];     V  = [V_X, V_Y, V_Z];     // 上の2頂点
N1 = bf(BAR_L, 34.007);   N2 = bf(BAR_R, 34.007);   // 傾斜バーの先端（基板の上辺）

module rod(p, q, d = ROD) { hull() { translate(p) sphere(d = d); translate(q) sphere(d = d); } }
module node(p) { translate(p) sphere(d = NODE); }

// 上辺に掛ける爪。基板の上辺を跨いでマイク面側へ少し回り込む
module hook(x) {
    rotate([TILT, 0, 0]) translate([x, 0, 34.007])
        difference() {
            translate([-NODE / 2, -NODE, -6]) cube([NODE, HOOK_GAP + 2 * NODE, 6 + NODE]);
            translate([-NODE, -0.01, -6.01]) cube([2 * NODE, HOOK_GAP, 6 + HOOK_DROP]);
        }
}

module frame() {
    difference() {
        union() {
            // 四面体の6辺（D1-D2 が机に置く底面トラス）
            rod(D1, D2); rod(D1, U); rod(D2, U); rod(D1, V); rod(D2, V); rod(U, V);
            for (p = [D1, D2, U, V]) node(p);
            // 上部頂点から出る傾斜バー2本。先端が基板の上辺を受ける
            rod(U, N1); rod(U, N2);
            node(N1); node(N2);
            hook(BAR_L); hook(BAR_R);
        }
        translate([-300, -300, -100]) cube([600, 600, 100]);   // 机で切る
    }
}

module board() { rotate([TILT, 0, 0]) respeaker_lite(); }

if (SHOW == "assembly") { board(); color("#c94") frame(); }
else if (SHOW == "part") frame();
else if (SHOW == "check") intersection() { frame(); board(); }
