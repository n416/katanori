// 柱の嵌り試験 ── 台座＋φ3.5 の柱 4 本だけ。16.05 / 16.10 / 16.15 の 3 枚
// ============================================================
// 2026-08-29 ユーザー「knob_v5_deck.stl はでかいので、4 本だけのテスト用を。
//   嵌りを見るだけなので短くていい。印刷時間優先。台座＋4 本で 3 つ」。
//
// 🔒 光造形の時間は樹脂の量ではなく**層数**（docs/PRINT.md §2）。なので Z を削る:
//   knob_v5_deck.stl は Z 20.9mm ＝ 418 層。この駒は **Z 8.0mm ＝ 160 層**（0.05 層厚）。
//   削り方: 天板の板・ねじ台・リードの穴・支柱を全部落とし、柱の 4 本だけ残した。
//   ⚠ 柱の**径と間隔**は knob_v5.scad と同じ数字を使う（POST_D 3.5 / HOLE_PITCH）。
//      短くしたのは長さだけで、嵌りに効く寸法は変えていない。
//
// 🔒 座（SEAT）を残す理由: 基板をチップ面下で載せると、はんだ側のピンが裏へ 2.5mm 出る
//   （⚠ 標準値・parts.scad）。座 3.0mm で浮かせないと、ピンの先が台座に当たって
//   「柱が入らない」のか「ピンが突いている」のか区別できなくなる。
//
// ------------------------------------------------------------
// 使い方
// ------------------------------------------------------------
//   基板の **チップ（黒い四角）のある面を下**にして、4 本の柱に載せる。
//   ヘッダの樹脂とデュポンは上を向く。4 本とも座まで落ちれば、その番号で挿さる。
//   番号は取っ手に浮き出し（1610 = ピッチ 16.10mm）。
//   ⚠ 対角のゲージ（pitch_gauge.scad）で 1610 が出ているので、期待は 1610。
//      1605 と 1615 は「外れる側が本当に外れるか」を見るための両隣。
//      3 枚とも入るなら、4 本挿しは対角 2 本より緩いということになる（そういう結果も答え）。
//
// ------------------------------------------------------------
// 刷り方
// ------------------------------------------------------------
//   3 枚を伏せて **プレートに直置き**（柱が上）。サポートも傾けも要らない。
//   外形と接地は下の echo。実行:
//   openscad --backend=manifold -o stl/post_fit_test.stl hardware/post_fit_test.scad
// ============================================================
$fn = 96;

PITCHES = [16.05, 16.10, 16.15];
GAP     = 3.0;

POST_D    = 3.5;    // 🔒 knob_v5.scad の POST_D と同じ。細くしない
POST_H    = 2.6;    // 座の上に出る胴（基板 1.6 を貫いて 1.0 出る）
TIP_H     = 0.4;    // 先の面取り（入れ始めが分かる）
TIP_D     = 2.7;
NECK_H    = 0.4;    // 座と柱のあいだの逃げ（隅にたまる樹脂を判定に効かせない）
NECK_D    = 3.0;

SEAT_D    = 4.5;    // ピンに当たらない径（当たり検査済み）
SEAT_H    = 3.0;    // 裏へ出るピンの先 2.5mm の逃げ

BASE_T    = 2.0;    // 台座。ここを薄くするのが層数に効く
RIM       = 3.0;    // 柱の中心から台座の縁まで（桟の幅 6.0）
HANDLE    = 10.0;   // 取っ手（番号。基板の縁 11.5mm より外へ出す）
CORNER    = 2.0;
TXT_SIZE  = 3.2;
TXT_H     = 0.6;

module post() {
    cylinder(d = SEAT_D, h = SEAT_H);
    translate([0, 0, SEAT_H])                        cylinder(d = NECK_D, h = NECK_H + 0.01);
    translate([0, 0, SEAT_H + NECK_H])               cylinder(d = POST_D, h = POST_H - TIP_H);
    translate([0, 0, SEAT_H + NECK_H + POST_H - TIP_H])
                                                     cylinder(d1 = POST_D, d2 = TIP_D, h = TIP_H);
}

// 台座は中央を窓で抜く（接地と樹脂を減らす・洗浄液を溜めない）
module tile(p) {
    out = p + RIM * 2;
    win = p - RIM * 2;
    linear_extrude(BASE_T) difference() {
        offset(r = CORNER) offset(delta = -CORNER)
            translate([-out / 2, -out / 2]) square([out + HANDLE, out]);
        offset(r = 1.0) offset(delta = -1.0) square(win, center = true);
    }
    for (x = [-1, 1], y = [-1, 1]) translate([x * p / 2, y * p / 2, BASE_T]) post();
    translate([out / 2 + HANDLE / 2, 0, BASE_T]) linear_extrude(TXT_H)
        text(str(round(p * 100)), size = TXT_SIZE, halign = "center", valign = "center");
}

PMAX = max(PITCHES);
OUT  = PMAX + RIM * 2;
for (i = [0 : len(PITCHES) - 1])
    translate([(OUT + HANDLE + GAP) * i, 0, 0]) tile(PITCHES[i]);

H = BASE_T + SEAT_H + NECK_H + POST_H;
echo(str("ピッチ ", PITCHES, " の 3 枚"));
echo(str("柱 φ", POST_D, "（knob_v5 と同寸）／ 座 φ", SEAT_D, " × ", SEAT_H,
         " ／ 基板の裏は台座から ", SEAT_H, "mm 浮く（ピンの先 2.5 の逃げ 0.5）"));
echo(str("高さ ", H, "mm ＝ 層厚 0.05 で ", ceil(H / 0.05), " 層",
         "（knob_v5_deck.stl は 20.9mm ＝ 418 層）"));
echo(str("外形 ", (OUT + HANDLE + GAP) * (len(PITCHES) - 1) + OUT + HANDLE, " × ", OUT, "mm"));
echo(str("1 枚の接地 約 ", pow(OUT, 2) - pow(min(PITCHES) - RIM * 2, 2) + HANDLE * RIM * 2,
         "mm2  ⇔ bridge.stl 513mm2"));
