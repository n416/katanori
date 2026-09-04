// ============================================================
// 🔴 btn_v3 が case_v4 の中で当たっている所を**目で見る**ファイル（2026-08-30）
// ============================================================
//   赤 = 当たっている体積そのもの。周りは薄く透かして出す。
//   ⚠ 透過は **F5（プレビュー）**でしか効かない。F6 でレンダーすると全部不透明になる。
//
//   SHOW : all（3 か所ぜんぶ）/ ina / wpwr / rsp（1 か所だけ）
//   CUT  : none / x（-Y を落として X-Z 断面）/ y（-X を落として Y-Z 断面）
//   GHOST: 周りの透け具合（0 = 透明・1 = 不透明）
//   MARK : 赤い十字の串で当たりの位置を指す（当たり自体が 1mm 前後で見つけられないため）
//   ZOOM : true にすると相手を当たりの周りだけに絞る（線が長くて邪魔なときに）
//   ONLY : true = 赤だけ出す。STL に焼けば当たりの寸法をそのまま測れる
//
//   当たりの数字（🔄 2026-08-30 顔を 18.0 → 15.0 に縮めた後の実測・単位 mm）:
//     ina  **0**（当たらなくなった。顔 18.0 のときは 1.17 x 2.22 x 1.30 で座の -X・+Y の角が食い込んでいた）
//     wpwr 1.50 x 1.98 x 1.50  ブロックの -X          world X 11.05〜12.55 / Y 19.12〜21.10 / Z 46.55〜48.05
//     rsp  3.49 x 0.73 x 0.50  付け根の丸みの +X・-Y   world X 31.00〜34.49 / Y  9.80〜10.53 / Z 47.97〜48.46
//   ⭐ 🔴 羊羹は**当たりではない**。羊羹も座も同じ天板に付く物なので、重なれば union で
//     1 つの塊になるだけ（ユーザー指摘 2026-08-30）。「どちらかを削る」という話にしたのが誤り。
//     ⇒ SHOW="all" から外した。残る本物の当たりは**電源線 1 本だけ**。
//     買った物（INA226 の板・ReSpeaker の基板・OLED）は 3 つとも 0。
//   ⚠ 位置を動かす案は測って全滅している: -Y は -1 から OLED、-3 で ReSpeaker の基板に 17mm。
//     -X は 1mm で INA226 が 1.89 に戻る（羊羹を避けるために買った板に当てる取引になる）。
// ============================================================
include <btn_v3.scad>
include <case_v4.scad>
part = "none"; PROPS_OFF = true; BTN3_SOLO = false;

SHOW  = "all";
CUT   = "none";
GHOST = 0.20;
ZOOM  = false;
ONLY  = false;   // true = 赤（当たり）だけを出す。STL に焼いて数字を検算する用
// 🔴 当たりは 1mm 前後しかないので、引きの絵では部品の陰に隠れて見えない。
//   FOCUS = true で**当たりの周りだけを箱で切り出す**（SHOW で選んだ 1 か所を寄りで見る）。
// 当たりは 1mm 前後しかないので、引きの絵では見つけられない。
//   MARK = true で**赤い十字の串**を当たりの芯に刺す（どの角度からでも位置が分かる）。
//   ⚠ 串の位置 hit_c() は 2026-08-30 の実測値の直書き。形を変えたら ONLY=true で測り直して更新する。
MARK = true;
MARK_L = 26; MARK_D = 0.7;
STEP  = 0.25;

echo(str("HIT 生存確認: BTN4=", BTN4, " Z_TOP=", Z_TOP, " SHOW=", SHOW, " CUT=", CUT));

// ---- ボタン一式が占める体積（当たり検査と同じ物を使う。ここで形を描き直さない）----
module b3_vol() translate([BTN4[0], BTN4[1], Z_TOP]) {
    difference() { btn3_station_add(); btn3_station_cut(); }
    btn3_tub();
    for (i = [-B3_TRAVEL : STEP : 0]) translate([0, 0, i]) btn3_piston();
}
// ---- 相手 ----
module nb(w) {
    if (w == "ina")  ina_bat();
    if (w == "wpwr") wires_pwr();
    if (w == "rsp")  rsp_press4();
}
// 当たりの周りだけを見るための窓（ZOOM 用）
// 串の芯。⚠ 実測値の直書き。形を変えたら ONLY=true で STL に焼いて測り直して更新する。
function hit_c(w) = w == "ina"  ? [12.49, 22.71, 45.85]   // ⚠ 顔 18.0 時代の位置。今は当たり 0
                  : w == "wpwr" ? [11.80, 20.11, 47.30]
                  :               [32.74, 10.17, 48.22];   // rsp
module zoom_box(w) translate(hit_c(w)) cube(18, center = true);
module maybe_zoom(w) { if (ZOOM) intersection() { children(); zoom_box(w); } else children(); }

// 🔄 ina は顔 15.0 で当たり 0 になったので "all" から外した（SHOW="ina" で個別に確認はできる）
WS = SHOW == "all" ? ["wpwr"] : [SHOW];

module scene() {
    // ボタン（薄い青・透かし）
    color("#8fb4d9", GHOST) b3_vol();
    // 相手（それぞれの色・透かし）
    for (w = WS) maybe_zoom(w)
        color(w == "ina" ? "#7fc47f" : w == "wpwr" ? "#e06666" : "#c9a227", GHOST) nb(w);
    // 🔴 当たり（赤・不透明）
    // 🔴 当たり。**render() を必ず通す。**プレビューは intersection() を正確に描かないので、
    //   これを外すと座の縁が丸ごと赤く見える（2026-08-30 に一度そう出した）。
    for (w = WS) color("#ff0000") render() intersection() { b3_vol(); nb(w); }
    // 位置を指す串
    if (MARK) for (w = WS) color("#ff0000") translate(hit_c(w)) for (r = [[0,90,0],[90,0,0],[0,0,0]])
        rotate(r) cylinder(d = MARK_D, h = MARK_L, center = true, $fn = 12);
}
module half(ax) difference() {
    children();
    if (ax == "x") translate([BTN4[0] - 60, BTN4[1] - 100, Z_TOP - 60]) cube([120, 100, 120]);
    if (ax == "y") translate([BTN4[0] - 100, BTN4[1] - 60, Z_TOP - 60]) cube([100, 120, 120]);
}
module hits_only() for (w = WS) render() intersection() { b3_vol(); nb(w); }
if (ONLY) hits_only();
else if (CUT == "none") scene();
else half(CUT) scene();
