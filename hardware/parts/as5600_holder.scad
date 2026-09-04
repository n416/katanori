// ============================================================
// 🔴 この部品は **knob_v5 に置き換わった。現行機では使っていない。**
//     （2026-08-20 ユーザー指摘。AI がこのファイルの「ビスは1本も使わない」を
//      現行機の仕様として引用し、間違えた）
//
//  現行の AS5600 の止め方は **knob_v5.scad の assembly()**:
//    ・四隅のスタンドオフ ＋ M2 ナット4個（knob_v5.scad:542〜549）
//    ・島の留めは M2.5 ナイロンねじ2本
//  🔒 **AS5600 の止め方をここから引用しない。** 正は knob_v5.scad。
//     下の「ビスは1本も使わない」「前から挿して上からロックを落とす」は、
//     この旧部品の仕様であって、現行機の仕様ではない。
//
//  残してある理由: docs/PRINT.md と docs/KNOB-ENCODER.md が印刷の記録として参照している
// ============================================================

// AS5600 保持枠 — ピンヘッダーに当たりようがない形にする
//
// knob_jig.scad のベース（スタンドオフ＋長穴＋窓）の置き換え。つまみとブリッジは
// そのまま使う。
//
// なぜ作り直すか（docs/PRINT.md の🔒 / docs/DIMENSIONS.md 1.5章）:
//   窓を広げる方向で2回やって、2回とも当たっている。最終版でも窓がピンヘッダーに
//   対してギリギリで、基板が少し斜めに付いたまま（未解決）。
//   → **「通す」のをやめる。基板の下に物を置かない。**
//
// この枠の約束（これが仕様）:
//   1. 基板の真下（23mm角の footprint）には、**四隅とレール以外なにも無い**。
//      下は床まで素通し。ヘッダの位置を知らなくても当たりようがない
//   2. 基板に触るのは4か所だけ:
//        - 左右の辺の縁 2.0mm（座レール・下から。姿勢はここで決まる）
//        - 四隅の三角のひさし（上から・浮き止め。押さえ付けはしない）
//        - 奥の辺（ヨーの基準・全幅）
//        - 手前の辺の両端2か所（ロック。真ん中には触れない）
//   3. ビスは1本も使わない。**前から挿して、上からロックを落とす**だけ
//   4. 弾性に頼る形（板バネ・スナップ）は作らない
//      … 🔒 レジン①では1日半で全数破断する（docs/DIMENSIONS.md 4章）
//
// ⚠ 組むときの向き（これを間違えると全部無効）:
//   **ピンヘッダーの辺を手前（+Y、開いている側）に向ける。**
//   ヘッダは平らな面（＝下）に付いていて、パッドは基板の縁にある
//   （docs/KNOB-ENCODER.md「ピンヘッダは平らな面側に付ける」）。
//   手前は、下も真ん中も開いているので、ハウジングも線も指も通る。
//
// ⚠ 刷る前に5秒で見ること:
//   基板を裏返して、**四隅から 3mm 四方に何も乗っていないこと**。
//   4ピンヘッダ（10.16mm）が辺の中央にあるなら両端に6.4mmずつ空くので当たらないが、
//   端に寄っている個体なら当たる。当たったら TAB_LEG を小さくするか、基板を90度回す。
//
// 出力:
//   openscad -o as5600_frame.stl   -D 'part="frame"'   as5600_holder.scad
//   openscad -o as5600_lock.stl    -D 'part="lock"'    as5600_holder.scad
//   openscad -o as5600_fittest.stl -D 'part="fittest"' as5600_holder.scad   // 嵌合だけ見る低い版
//
//   ブリッジは knob_jig.scad から刷り直す（脚が短くなる。座の面がこの枠の上面になるため）:
//   openscad -o hardware/as5600_bridge_v2.stl -D 'part="bridge"' -D 'STANDOFF_H=0' hardware/knob_jig.scad
//   ⚠ v2 = 溝なし・両端タブ。溝入りの旧 as5600_bridge.stl は3枚連続で溝に沿って
//     破断したため名前ごと廃止（スライサーの履歴から拾わせない）
//   つまみ（knob.stl）は変更なし。
//
// 印刷: 壁を下にしてプレート直置き・サポート不要。接地するのは壁の断面（細い帯）だけで、
//   広い平面は下を向かない（docs/PRINT.md「底面が広い部品」の件）。
//   高さ約30mm＝そのまま時間なので、まず fittest（高さ12mm）で嵌合を見てから本番を刷る。

part = "frame";   // "frame" | "lock" | "fittest" | "check" | "all"

$fn = 96;

// ---- 基板（docs/DIMENSIONS.md 1章）----
PCB      = 23.0;   // ✅ 定規で実測（knob_jig.scad と同じ出典）
PCB_T    = 1.6;    // ⚠ 未実測。スロットは緩めに取ってあるので 1.2〜1.8 なら効く
CHIP_H   = 1.1;    // ⚠ SOIC想定
CHIP_GAP = 1.1;    // ✅ 治具の実測（AGC 43〜67 に入った値）

// ---- 印刷の補正（docs/PRINT.md 4章・レジン①/0.05/2.5s/35s×5層）----
SHRINK = 0.1;      // 穴・内寸は設計値から約0.1mm縮む

// ---- 基板の下にどれだけ要るか ----
// ⚠ 全部推定。**実測は1つで足りる: 基板の平らな面から、挿したハウジングの
//    お尻までの距離。** そこだけ測れば HDR_BODY+HOUSING_L を1つの数字に置き換えられる。
// なお当たらないことは高さではなく「下に物を置かない」ことで担保している。
// ここで高さを取るのは、線が曲がる余地と、抜き挿しする指のため
// （docs/DIMENSIONS.md 1.5章の「数えるのはコネクタ本体だけでは足りない」3項目）。
HDR_BODY  =  2.5;  // ⚠ ヘッダの樹脂の厚み
HOUSING_L = 14.0;  // ⚠ Dupontハウジング（knob_jig.scad の記録）
WIRE_BEND =  9.5;  // ⚠ 線の曲がり＋指
LIFT      = HDR_BODY + HOUSING_L + WIRE_BEND;   // = 26.0 基板の下面の高さ
LIFT_TEST = 12.0;  // 嵌合テスト版の高さ

// ---- 嵌合 ----
FIT_X      = 0.30;   // 基板とボスの遊び（全幅）
SLOT_CLEAR = 0.40;   // ひさしの下の遊び。**押さえ付けない。** 姿勢は座で決める
SEAT_IN    = 2.0;    // 座レールが基板の下へ入る量（左右の辺だけ）
SEAT_T     = 1.0;    // 座レールの肉厚
TAB_LEG    = 2.6;    // 隅のひさしの一辺
TAB_T      = 1.0;

HALF     = PCB / 2;                             // 11.50 基板の端
WALL_IN  = (PCB + FIT_X + SHRINK) / 2;          // 11.70 ボス内面（X基準）
SLOT_H   = PCB_T + SLOT_CLEAR;                  //  2.00 座からひさし下面まで
BOSS_H   = SLOT_H + TAB_T;                      //  3.00 隅のボスの高さ

// ---- 枠の外形 ----
// 2026-08-04: 最初 18.0 で書いていた。ほぞ穴が x=15.5・φ3.35 なので、外側の肉が
// 18.0 - (15.5 + 3.35/2) = **0.83mm しか無かった**。スタンドオフが2本折れたときと
// 同じ型の見落とし（穴のまわりの肉厚を計算していない・docs/DIMENSIONS.md の事故表）。
// 19.0 にして 1.83mm 確保する。ブリッジの脚（|x| 13〜18）は変わらず載る。
WALL_OUT  = 19.0;   // 壁の外面X。ブリッジの脚（|x| 13〜18）を受ける
BACK_OUT  = 18.0;   // 奥の壁の外面Y
FRONT_OUT = 17.0;   // 壁の手前端Y
RIB_OVER  = 1.0;    // 奥の当ての、基板上面からの出っ張り
RIB_Y     = 3.0;    // 奥の当ての厚み
NOTCH_W   = 12.0;   // 奥の壁の配線逃げ（線を後ろへ出したいとき用）
NOTCH_H   =  8.0;

// 水抜き（洗浄）。上を向いた止まり穴は洗浄機の水流が入らず、袋小路に液が残る。
// **穴の底から外面へ横に抜く。** 排水路であると同時に空気穴で、これが無いと
// 真空になって振っても落ちない。stand_seat_test.scad で座の中央を貫通させたのと同じ手。
DRAIN_D = 1.5;

// ---- 接地の逃げ（プレートから剥がすため）2026-08-05 ----
// bridge・lock×2 の3個が、**未硬化のままプレートから剥がすときに砕け散った**。
// docs/PRINT.md「直置きを選んだら、接地面積を設計で減らす」の実装。
//
// 形は**半円の溝**。角溝ではない。理由は3つ:
//   1. 内側に角が立たない。ボトム層は部品の中でいちばん硬い層で、そこに角を切ると
//      そのまま割れの起点になる。**いま壊れているのと同じ場所に弱点を作らない**
//   2. 断面が層ごとに少しずつ増えるので、溝の上を丸ごと渡る層が存在しない。
//      角溝は天井の1層が宙に出る（島）
//   3. 両端が外へ抜けている。洗浄液が抜け、空気も入る。閉じた凹みは吸盤になる
//
// 幅 = RELIEF_D、深さ = RELIEF_D/2、減る接地面積の割合 = RELIEF_D / ピッチ。
// ⚠ 減らしすぎると印刷中に落ちる。1層ごとの剥離力は断面積（溝の上では元のまま）で
//    決まるのに、それを受ける根元だけが細くなるため。**約4割に留めてある。**
// ⚠ この値は初期層 5層/35秒（docs/PRINT.md の🔒）を前提にしている。
//    3層/25秒のままで面積を落とすと、食いつきが二重に弱くなって印刷中に落ちる。
RELIEF_CUT  = 0.38;   // 接地面積を何割落とすか（これ1つで全部の溝のピッチが決まる）
RELIEF_D_FR = 3.0;    // 枠: 深さ1.5。壁は7.3mm厚・高さ26mmなので効かない
RELIEF_D_LK = 1.8;    // ロック: 板厚2.6mmなので浅く。深さ0.9 → 残り1.7mm

// 接地面 z0 に、X方向へ走る半円溝を並べる（Yに y0〜y1 の範囲でピッチ配分）
module relief_x(z0, y0, y1, x0, x1, d) {
    p = d / RELIEF_CUT;
    n = max(0, floor((y1 - y0) / p));
    for (i = [0 : n])
        translate([x0, y0 + ((y1 - y0) - n * p) / 2 + i * p, z0])
            rotate([0, 90, 0]) cylinder(d = d, h = x1 - x0, $fn = 48);
}

// 同・Y方向へ走る溝（Xに x0〜x1 の範囲でピッチ配分）
module relief_y(z0, x0, x1, y0, y1, d) {
    p = d / RELIEF_CUT;
    n = max(0, floor((x1 - x0) / p));
    for (i = [0 : n])
        translate([x0 + ((x1 - x0) - n * p) / 2 + i * p, y0, z0])
            rotate([-90, 0, 0]) cylinder(d = d, h = y1 - y0, $fn = 48);
}

// ---- ブリッジ（knob_jig.scad と同じ値。**変えない**）----
PEG_D      = 3.0;
PEG_H      = 2.5;
PEG_HOLE_D = PEG_D + SHRINK + 0.25;   // 3.35 ← 台座はこの値で刷ってある（基準。もう動かさない）
BRIDGE_PEG_X = 15.5;                  // = LEG_CX（脚の中心X）
// 2026-08-05: ダボ3.0はプカプカ、3.2は入らず（無理に押すと折れて穴に詰まる）、
// **3.1で実測「良い」（破片の脚で検証・確定）**。
// 一般則: 差し込みのほぞ径 = 穴の設計値 − 0.25（穴3.35に対し3.1）。
// ⚠ 力を入れても入らないときは押し込まない。脆い。折るより刷り直しが安い
PEG_FIT_D  = 3.1;   // ✅ 実測確定 2026-08-05
PEG_TIP_C  = 0.5;   // 先端の面取り。入りやすくし、こじれて折る力を減らす

// ---- ロック ----
LOCK_T      = 2.6;    // 板厚。基板の上面より上に出るのは 1.0mm
LOCK_FRONT  = 20.5;   // つまみ側の端（指がかり）
LOCK_PEG_X  = 15.5;
// 2026-08-05: 14.5 で書いていた。壁の手前端が 17.0 なので、穴の手前の肉が
// **0.825mm しか無かった**。前日に同じ間違いをX方向で直したのに、Y方向を数えていない。
// ここはフタを抜き挿しするたび力がかかる。13.5 へ寄せて 1.83mm 確保する。
// → 数えるのを人間に任せるのをやめて、下の MIN_WALL の assert で機械に見張らせる。
LOCK_PEG_Y  = 13.5;
// ほぞは短いほうが折れにくい（曲げの腕が短くなる）。位置決めだけなので3.5で足りる。
// 止まり穴も浅くなるので洗いやすい
LOCK_PEG_L  = 3.5;
LOCK_FACE_B = 12.0;   // 基板に当たる面: 下側のY（座の高さで）
LOCK_FACE_T = 11.2;   // 同・上側のY。下ほど手前＝落とすと基板が奥へ寄る傾斜
LOCK_FREE_X =  6.0;   // |x| がこれ未満は基板に触れない（ヘッダ・はんだ・線の列）
LOCK_RELIEF = 13.5;   // 触れない範囲の面のY（逃げ）
GRIP_X      = 15.5;   // 指がかりの下向きの出っ張り
GRIP_DROP   =  6.0;
// 2026-08-05: lock が3枚とも「切り欠きの角→ほぞの脇→縁」の同じ線で割れた。
// 一晩置いても即剥がしても100%同じ場所（ユーザー報告）＝時間でも設定でもなく形。
// 直角の内角は応力集中の起点になるので丸める
LOCK_NOTCH_R = 2.0;

// ---- つまみの影（設計の拘束条件）----
// つまみは φ25＋リブ1.2 ＝ 半径13.1。基板の辺の中央は半径11.5 しかないので、
// **辺を上から押さえる部品はつまみに当たる。** 隅（16.3）だけが影の外。
KNOB_R      = 25.0 / 2 + 1.2 / 2;        // 13.10
KNOB_MARGIN = 0.5;
KNOB_BOTTOM = PCB_T + CHIP_H + CHIP_GAP; // 座から 3.8mm。つまみの底面

// 隅のひさしの内側の稜線（斜辺）までの距離
TAB_R_FRONT = (WALL_IN + (HALF - 1.2) - TAB_LEG) / sqrt(2);
TAB_R_BACK  = (WALL_IN + HALF - TAB_LEG) / sqrt(2);

// ---- 穴のまわりの肉厚を機械に数えさせる ----
// 🔒 この事故は3回起きている。スタンドオフ2本折れ（0.3mm・docs/DIMENSIONS.md）、
//    ほぞ穴の外側（0.83mm・2026-08-04）、フタのほぞ穴の手前（0.83mm・2026-08-05）。
//    3回とも「難しくて分からなかった」ではなく **数えなかった**。
//    だから設計値を足すたびに、ここが勝手に数える。穴を足したら行を足すこと。
MIN_WALL = 1.5;
assert(WALL_OUT - (BRIDGE_PEG_X + PEG_HOLE_D / 2) >= MIN_WALL, "ブリッジほぞ穴: 外側Xの肉が薄い");
assert((BRIDGE_PEG_X - PEG_HOLE_D / 2) - WALL_IN >= MIN_WALL, "ブリッジほぞ穴: 内側Xの肉が薄い");
assert(WALL_OUT - (LOCK_PEG_X + PEG_HOLE_D / 2) >= MIN_WALL,   "フタほぞ穴: 外側Xの肉が薄い");
assert((LOCK_PEG_X - PEG_HOLE_D / 2) - WALL_IN >= MIN_WALL,    "フタほぞ穴: 内側Xの肉が薄い");
assert(FRONT_OUT - (LOCK_PEG_Y + PEG_HOLE_D / 2) >= MIN_WALL,  "フタほぞ穴: 手前Yの肉が薄い");
assert(LOCK_PEG_Y - PEG_HOLE_D / 2 > LOCK_FACE_T,              "フタほぞ穴がフタの板からはみ出す");

assert(TAB_R_FRONT > KNOB_R + KNOB_MARGIN,
       "手前のひさしがつまみの下に入る。TAB_LEG を小さくすること");
assert(TAB_R_BACK  > KNOB_R + KNOB_MARGIN,
       "奥のひさしがつまみの下に入る。TAB_LEG を小さくすること");
assert(SLOT_H + TAB_T < KNOB_BOTTOM - 0.5,
       "ひさしの上面がつまみに当たる。SLOT_CLEAR か TAB_T を下げること");
assert(PCB_T + RIB_OVER < KNOB_BOTTOM - 0.5,
       "奥の当てがつまみに当たる。RIB_OVER を下げること");
assert(LOCK_T < KNOB_BOTTOM - 0.5,
       "ロックの板がつまみに当たる。LOCK_T を下げること");

echo(str("基板の下面の高さ LIFT = ", LIFT, " mm"));
echo(str("ひさしの内側 半径 = ", TAB_R_FRONT, " / つまみ半径 = ", KNOB_R));
echo(str("ブリッジは -D STANDOFF_H=0 で刷り直す（脚が ",
         0 + PCB_T + CHIP_H + CHIP_GAP + 10.0 - 6.0, " mm になる）"));

// =====================================================================
// 枠（台）
// =====================================================================

// 左右の壁（Yに走る板）と奥の壁。上面 = 座の高さ = lift
module walls(lift) {
    for (m = [0, 1]) mirror([m, 0, 0])
        translate([WALL_IN, -BACK_OUT, 0])
            cube([WALL_OUT - WALL_IN, BACK_OUT + FRONT_OUT, lift]);
    // 奥の壁（左右をつなぐ）。内面が基板の奥の端
    translate([-WALL_OUT, -BACK_OUT, 0])
        cube([2 * WALL_OUT, BACK_OUT - HALF, lift]);
}

// 座レール — 基板の下へ入るのはここだけ。左右の辺の縁 2.0mm。
// ヘッダは手前の辺にあるので、左右の辺には何も乗っていない。
// 下は45度のガセットにして、壁から生やす（片持ちの薄板にしない）。
module seat_rails(lift) {
    for (m = [0, 1]) mirror([m, 0, 0])
        hull() {
            translate([WALL_IN - SEAT_IN, -HALF, lift - SEAT_T])
                cube([SEAT_IN, HALF + 15.0, SEAT_T]);
            translate([WALL_IN - 0.8, -HALF, lift - SEAT_T - SEAT_IN])
                cube([0.8, HALF + 15.0, SEAT_T]);
        }
}

// 隅のボス（X基準）＋三角のひさし（浮き止め）
//   sy = +1 手前 / -1 奥。手前は 1.2mm 内側へ引く（ロックの板と場所を分けるため）
module corner_boss(sy, lift) {
    cy = sy > 0 ? HALF - 1.2 : -HALF;
    y0 = sy > 0 ? cy - TAB_LEG : cy;
    // ボス（壁の上に立つ。内面 WALL_IN が基板のX基準）
    translate([WALL_IN, y0, lift])
        cube([WALL_OUT - WALL_IN, TAB_LEG, BOSS_H]);
    // ひさし（三角。斜辺はつまみの外側を通る）
    translate([0, 0, lift + SLOT_H])
        linear_extrude(TAB_T)
            polygon([[WALL_IN, cy],
                     [WALL_IN - TAB_LEG, cy],
                     [WALL_IN, cy - sy * TAB_LEG]]);
}

// 奥の当て（全幅）。基板の奥の辺をここへ押し当てる = ヨーの基準。
// 斜めに付く事故はここで殺す。
module back_rib(lift) {
    translate([-WALL_OUT, -HALF - RIB_Y, lift])
        cube([2 * WALL_OUT, RIB_Y, PCB_T + RIB_OVER]);
}

// 止まり穴の底から、壁の外面へ横に抜く穴。穴の底面と面一になる高さに置く
module drain(px, py, pz) {
    translate([px, py, pz + DRAIN_D / 2])
        rotate([0, 90, 0])
            cylinder(d = DRAIN_D, h = WALL_OUT - px + 1);
}

module frame(lift) {
    difference() {
        union() {
            walls(lift);
            seat_rails(lift);
            back_rib(lift);
            for (mx = [0, 1]) mirror([mx, 0, 0])
                for (sy = [1, -1]) corner_boss(sy, lift);
        }
        // ブリッジのほぞ穴（貫通させない）＋水抜き
        for (m = [0, 1]) mirror([m, 0, 0]) {
            translate([BRIDGE_PEG_X, 0, lift - PEG_H - 0.3])
                cylinder(d = PEG_HOLE_D, h = PEG_H + 1);
            drain(BRIDGE_PEG_X, 0, lift - PEG_H - 0.3);
        }
        // ロックのほぞ穴＋水抜き
        for (m = [0, 1]) mirror([m, 0, 0]) {
            translate([LOCK_PEG_X, LOCK_PEG_Y, lift - LOCK_PEG_L - 0.5])
                cylinder(d = PEG_HOLE_D, h = LOCK_PEG_L + 1);
            drain(LOCK_PEG_X, LOCK_PEG_Y, lift - LOCK_PEG_L - 0.5);
        }
        // 奥へ線を出したいとき用の逃げ（基板からは遠い・床側）
        translate([-NOTCH_W / 2, -BACK_OUT - 1, 0])
            cube([NOTCH_W, BACK_OUT - HALF + 2, NOTCH_H]);
        // 接地の逃げ溝（半円・X方向へ走って左右の外面へ抜ける）
        relief_x(0, -BACK_OUT + 2, FRONT_OUT - 2, -WALL_OUT - 1, WALL_OUT + 1, RELIEF_D_FR);
    }
}

// =====================================================================
// ロック（前から落として基板の抜けを塞ぐ）
// =====================================================================
// z = 0 が座の面（＝壁の上面）。板は壁の上に載って止まる。
// 基板に当たるのは手前の辺の両端 |x| 6.0〜11.7 の2か所だけで、
// 真ん中（ヘッダ・ハウジング・はんだ・線）には何も来ない。
// 当たり面は下ほど手前に出る傾斜。落とし込むと基板が奥の当てへ寄る。
// 板厚2.6mmのうち基板の上に出るのは1.0mm（つまみの底面まで2.8mm残る）。

module lock() {
    difference() {
        union() {
            // 板本体
            translate([-WALL_OUT, LOCK_FACE_T, 0])
                cube([2 * WALL_OUT, LOCK_FRONT - LOCK_FACE_T, LOCK_T]);
            // ほぞ（径は現物合わせの PEG_FIT_D。穴の設計値 PEG_D とは切り離した。先端は面取り）
            for (m = [0, 1]) mirror([m, 0, 0])
                translate([LOCK_PEG_X, LOCK_PEG_Y, 0]) {
                    translate([0, 0, -LOCK_PEG_L + PEG_TIP_C])
                        cylinder(d = PEG_FIT_D, h = LOCK_PEG_L - PEG_TIP_C + 0.1);
                    translate([0, 0, -LOCK_PEG_L])
                        cylinder(d1 = PEG_FIT_D - 0.8, d2 = PEG_FIT_D, h = PEG_TIP_C);
                }
            // 指がかり（壁の手前端の外へ垂らす。ここをつまんで抜く）
            translate([-GRIP_X, FRONT_OUT + 0.6, -GRIP_DROP])
                cube([2 * GRIP_X, LOCK_FRONT - FRONT_OUT - 0.6, GRIP_DROP + LOCK_T]);
        }
        // 当たり面の傾斜（両端の2か所ぶんだけ削って作る）
        // ⚠ 回転は「座の高さの当たり点」を軸にする。原点で回すと面が0.56mmずれて、
        //    基板に触らないただの隙間になる（2026-08-04・書いた直後に検算で見つけた）
        for (m = [0, 1]) mirror([m, 0, 0])
            translate([LOCK_FREE_X, LOCK_FACE_B, 0])
                rotate([atan2(LOCK_FACE_B - LOCK_FACE_T, LOCK_T), 0, 0])
                    translate([0, -20, -10])
                        cube([WALL_OUT, 20, 20]);
        // 真ん中は基板に触れない（ヘッダの列の逃げ）
        // 2026-08-05: この切り欠きの直角の内角が割れの起点（100%ここから割れた）。
        // 奥の両角を R2 で丸める。基板の縁 y=11.5 では開口が全幅のままなので、
        // 基板・ヘッダとの空きは変わらない
        hull() {
            for (m = [0, 1]) mirror([m, 0, 0])
                translate([LOCK_FREE_X - LOCK_NOTCH_R, LOCK_RELIEF - LOCK_NOTCH_R, -1])
                    cylinder(r = LOCK_NOTCH_R, h = LOCK_T + 2);
            translate([-LOCK_FREE_X, LOCK_FACE_T - 1, -1])
                cube([2 * LOCK_FREE_X, 0.1, LOCK_T + 2]);
        }
    }
}

// 印刷向き: 上面をプレートに置く。ほぞと指がかりが上を向くので、
// 下向きの張り出しがどこにも無い（サポート不要）。
module lock_print() {
    difference() {
        translate([0, 0, LOCK_T]) rotate([180, 0, 0]) lock();
        // 接地の逃げ溝（Y方向＝板の短手へ走り、前後の縁へ抜ける）。
        // 向きに意味がある: 剥がすとき板はX軸まわりに曲がる。溝をY向きに走らせれば
        // 曲げ線と直交するので、蝶番（弱い線）を作らない。X向きは禁止
        relief_y(0, -17.0, 17.0, -LOCK_FRONT - 1, -LOCK_FACE_T + 1, RELIEF_D_LK);
    }
}

// =====================================================================
// 確認用（印刷しない）
// =====================================================================
module ghost_board() {
    translate([-HALF, -HALF, LIFT]) cube([PCB, PCB, PCB_T]);
    // 手前の辺に付くピンヘッダーとハウジング（⚠ 位置は推定。当たらないことの目視用）
    translate([-5.1, HALF - 2.6, LIFT - HDR_BODY]) cube([10.2, 2.6, HDR_BODY]);
    translate([-5.1, HALF - 2.6, LIFT - HDR_BODY - HOUSING_L])
        cube([10.2, 2.6, HOUSING_L]);
}

// 2026-08-04: 最初は本体を磁石の面の高さに描いていた（軸10mmを忘れて、絵の中で
// つまみが基板を突き破っていた。ユーザー指摘）。実物どおり軸＋本体で描く。
// なお上の assert 群は「本体が磁石の面まで下りてくる」最悪想定のままにしてある。
// 実物より10mm厳しい条件で通っているので、そのまま安全側の見張りとして残す。
SHAFT_LEN = 10.0;   // knob_jig.scad と同じ値
module ghost_knob() {
    z0 = LIFT + PCB_T + CHIP_H + CHIP_GAP;   // 磁石の面（軸の下端）
    translate([0, 0, z0]) cylinder(d = 6.0, h = SHAFT_LEN);          // 軸
    translate([0, 0, z0 + SHAFT_LEN]) cylinder(d = 2 * KNOB_R, h = 12); // 本体
}

// 当たり検査。**空になれば合格**（OpenSCADが "Current top level object is empty"）。
//   openscad -o /dev/null -D 'part="clash"' as5600_holder.scad
// 見ているのは3つ: 枠×ロック / 枠×つまみ / ロック×つまみ。
// 「刷ってから当たりに気付く」を止めるための一段（stand_seat_test.scad と同じ考え）。
module clash() {
    intersection() { frame(LIFT); translate([0, 0, LIFT]) lock(); }
    intersection() { frame(LIFT); ghost_knob(); }
    intersection() { translate([0, 0, LIFT]) lock(); ghost_knob(); }
}

// =====================================================================
if (part == "frame") {
    frame(LIFT);
} else if (part == "lock") {
    lock_print();
} else if (part == "fittest") {
    frame(LIFT_TEST);
} else if (part == "clash") {
    clash();
} else if (part == "check") {
    frame(LIFT);
    color("orange") translate([0, 0, LIFT]) lock();
    %ghost_board();
    %ghost_knob();
} else {
    frame(LIFT);
    translate([0, 48, 0]) lock_print();
}
