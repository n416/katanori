// つまみユニット v3 ── 台座を筐体天面に一体化した版（2026-08-15・ユーザー提案）
//
//   openscad -o knob.stl -D 'part="knob"' hardware/knob_top.scad   // つまみ（1部品）
//   openscad -o ring.stl -D 'part="ring"' hardware/knob_top.scad   // 押さえリング
//   openscad -o deck.stl -D 'part="deck"' hardware/knob_top.scad   // 卓上テスト用の座
//   （part 未指定なら組み立てビュー）
//
// ============================================================
// 🔒 構成（v1・v2 の失敗を踏まえた形）
// ============================================================
// v1: つば付き軸を1部品で焼いた → **組めなかった**（つばφ9が軸穴φ6.35を通らない。
//     上から挿せばつばが、下から挿せば本体が引っかかる）。さらに**軸のブレ未計算**
//     （穴3mmで受けると磁石が1.0mm振れる。許容0.25の4倍・ユーザー指摘）
// v2: 持ち手を別部品にして圧入 → **持ち手が外れる**（レジンの圧入は経時で緩む）
//
// v3 の答え:
//   **つまみ＝持ち手＋軸＋フランジ＋磁石ポケットの1部品**（同芯の急所を1部品に戻す）
//   筐体天面の穴（φ21.7）へ**上から落とし込み**、内側から**押さえリングを M2×2 で留める**。
//   ・上に抜く → 持ち手φ25 が穴φ21.7 に当たって抜けない
//   ・下に落ちる → フランジがガラス球ごしに押さえリングに乗る
//   🔒 **外れるのは、箱を開けて M2 を2本外したときだけ。**
//
// 🔒 台座は筐体天面と一体（ユーザー提案に同意した理由）:
//   ① 穴・柱・ねじ台が1回の印刷で同じ座標系に焼かれる（貼り合わせの誤差項が消える）
//   ② 箱は電池交換でどうせ開く。内側からの組立経路は最初からある
//   ③ 代償は「機構を直すたび天面ごと刷り直し」と「そのたびゼロ点取り直し（knobzero）」
//
// 軸受け: ✅ uxcell ガラス球 φ2（非磁性・ユーザー保有）を **φ14.5 の輪**で受ける。
//   ⚠ v2 の φ20 から内へ寄せた ── AS5600 の柱（内縁 r9.0）と押さえリングが
//   場所を取り合うため。溝は**フランジ側の1本だけ**でリング側は平面
//   （球は「溝＋平面」で芯が出る。両側に彫るとリング外周の肉が薄くなりすぎる）。
//
// 回転の壁: 🔒 **315度**（SPAN270＋吸着帯45・docs/KNOB-ENCODER.md「機構に壁が要る」）。
//   軸の根元のラグ(25度)とリング裏のポスト(20度)で 360−45=315度。
//
// ---- 🔒 治具から引き継ぐ実績値（作り直さない）----
//   SHRINK 0.1 / MAG_D 4.10 / CHIP_GAP 1.1 / HOLE_PITCH 17.0 / SLOT_LEN 2.0 / STANDOFF_D 6.0
//
// ---- 🔒 印刷（サポートあり・2026-08-15 ユーザー決定）----
//   つまみ: **持ち手の天面をプレートに置く**（part="knob" がその向きで出る）。
//     サポートが付くのは**フランジの上面**＝逃げに変えた面なので、傷は機能に触れない。
//     ⭐ 球の溝は印刷では上を向く＝きれいに出る側。ここが精度の急所なので向きを変えない。
//   リング: 柵を上に向けて置く。押さえ面（平面レース）も上向き。
//   天板  : 内側（柱の側）を上に向けて置く。外に見える面がプレート側になる。
//
// ---- ⬜ まだ入っていないもの ----
//   ・リード用磁石(φ6×2)のポケット … 🔴 **先に閉じる距離を測る**（A-3 の順番。
//     測る前に刷ると2回刷ることになる）。持ち手の外周に足す予定
//   ・刷り直したらゼロ点を取り直す（knobzero）── 機構を変えるたび必ず

part = "all";
$fn = 96;

// ---- 治具から引き継ぐ ----
SHRINK     = 0.1;
MAG_D      = 4.10;
MAG_DEPTH  = 2.2;
SHAFT_D    = 6.0;
PCB        = 23.0;
PCB_T      = 1.6;
CHIP_H     = 1.1;
CHIP_GAP   = 1.1;
HOLE_PITCH = 17.0;
SLOT_LEN   = 2.0;
M2_D       = 2.0 + SHRINK;
STANDOFF_D = 6.0;
NUT_AF     = 4.3;          // M2ナットの六角ポケット（呼び4＋0.3・PRINT.md の実績）
NUT_T      = 1.8;

// ---- 球の輪 ----
BALL_D     = 2.0;          // ✅ ガラス球
RACE_R     = 7.25;         // 輪の半径（φ14.5）
BALL_N     = 10;
GROOVE_R   = BALL_D / 2 + 0.1;   // 溝の断面半径。遊び0.1
GROOVE_CUT = 0.6;                // フランジ側の溝の深さ

// ---- つまみ ----
GRIP_D     = 25.0;
GRIP_H     = 12.0;         // ⚠ 分厚さの残りの主因。使い勝手と相談して詰める余地
RIB_N      = 24;
RIB_D      = 1.2;
FLANGE_D   = 21.0;
FLANGE_T   = 2.0;
// 🔒 **引き上げの止めは「持ち手の裏」**（2026-08-15・サポート前提に切り替えて見直し）。
//    ⚠ それまではフランジ上面が止めだったが、**そこは印刷でサポートが付く面**で、
//    傷がそのまま軸方向のガタになる。持ち手の裏は印刷では上を向くのできれいに出る。
GRIP_GAP   = 0.25;         // 持ち手の裏と天面の隙間＝**軸方向の遊び（止め）**
FLANGE_CL  = 0.6;          // フランジ上面と天面裏の逃げ。**サポート傷の逃がし。触れない**

// ---- 天面（台座＝筐体の天板）----
DECK_T     = 2.5;
HOLE_D     = FLANGE_D + SHRINK + 0.6;   // 21.7 落とし込みの穴
SEAT_X     = 31.0;         // 座の X。押さえリングのねじ台のぶん Y より広い
SEAT_Y     = 27.0;         // 座の Y（柱の外〜外25＋壁1×2）。🔒 箱の Y に効くのはこちら
BOSS_X     = 12.5;         // リング固定ねじの位置（±X）。穴 r10.85 の外に台を置く

// ---- 押さえリング ----
RING_OUT   = 17.6;         // 外径。⚠ 柱の内縁(r9.0)より内側に収める
RING_IN    = SHAFT_D + 1.2;
RING_T     = 2.0;

// ---- 回転の壁 ----
LUG_ARC    = 25;           // 軸側ラグの角度幅
POST_ARC   = 20;           // リング側ポストの角度幅 → 可動域 360-25-20=315度

// ---- Z（天面の上面 = 0、+Z が外）----
Z_DECK_BOT = -DECK_T;                          // -2.5
Z_FLANGE_T = Z_DECK_BOT - FLANGE_CL;           // -3.1（触れない逃げ）
Z_FLANGE_B = Z_FLANGE_T - FLANGE_T;            // -4.6
Z_BALL_C   = Z_FLANGE_B - (GROOVE_R - GROOVE_CUT);   // -5.1 球の中心
Z_RING_T   = Z_BALL_C - BALL_D / 2;            // -6.1 リング上面（平面）
Z_RING_B   = Z_RING_T - RING_T;                // -8.1
Z_LUG_T    = Z_RING_B - 0.2;                   // -8.3 壁のラグ
Z_LUG_B    = Z_LUG_T - 1.4;                    // -9.7
Z_MAG_BOT  = Z_LUG_B - 0.3;                    // -10.0 磁石の下面＝軸の下端
Z_CHIP_TOP = Z_MAG_BOT - CHIP_GAP;             // -11.1
Z_PCB_TOP  = Z_CHIP_TOP - CHIP_H;              // -12.2
Z_PCB_BOT  = Z_PCB_TOP - PCB_T;                // -13.8

// 外へ出す値（🔒 use は変数を渡さない。必ず関数で）
function knob_deep()   = -Z_PCB_BOT;           // 天面から下に要る深さ 13.8
function knob_grip_h() = GRIP_GAP + GRIP_H;    // 外へ出る高さ 12.4
function knob_bay()    = SEAT_Y;               // 箱の Y に効く座の幅 27
function knob_bay_x()  = SEAT_X;

module race_torus() { rotate_extrude() translate([RACE_R, 0]) circle(r = GROOVE_R); }

// 扇形の柱（回転の壁に使う）
module arc_block(r0, r1, a, z0, z1) {
    translate([0, 0, z0]) rotate_extrude(angle = a)
        translate([r0, 0]) square([r1 - r0, z1 - z0]);
}

// ============================================================
// つまみ（1部品）: 持ち手＋軸＋フランジ＋磁石ポケット＋壁ラグ
// ============================================================
module knob_part() {
    difference() {
        union() {
            // 持ち手
            translate([0, 0, GRIP_GAP]) {
                cylinder(d = GRIP_D, h = GRIP_H);
                for (i = [0 : RIB_N - 1]) rotate([0, 0, i * 360 / RIB_N])
                    translate([GRIP_D / 2, 0, 0]) cylinder(d = RIB_D, h = GRIP_H);
            }
            // 軸
            translate([0, 0, Z_MAG_BOT]) cylinder(d = SHAFT_D, h = GRIP_GAP - Z_MAG_BOT + 0.01);
            // フランジ（落とし込み後、球ごしにリングへ乗る）
            translate([0, 0, Z_FLANGE_B]) cylinder(d = FLANGE_D, h = FLANGE_T);
            // 壁のラグ
            arc_block(SHAFT_D / 2 - 0.5, 5.4, LUG_ARC, Z_LUG_B, Z_LUG_T);
        }
        // 磁石ポケット
        translate([0, 0, Z_MAG_BOT - 0.01]) cylinder(d = MAG_D, h = MAG_DEPTH + 0.01);
        // 球の溝（フランジの下面。溝はこちら側だけ）
        translate([0, 0, Z_BALL_C]) race_torus();
        // 向きの印
        translate([-1, GRIP_D / 4, GRIP_GAP + GRIP_H - 0.8]) cube([2, GRIP_D / 4, 1]);
    }
}

// ============================================================
// 押さえリング（内側から M2×2。上面は平面レース）
// ============================================================
module ring_part() {
    difference() {
        union() {
            translate([0, 0, Z_RING_B]) cylinder(d = RING_OUT, h = RING_T);
            // ねじ台へ届く耳（±X）
            for (s = [-1, 1]) translate([s * (BOSS_X / 2 + 2), 0, Z_RING_B + RING_T / 2])
                cube([BOSS_X + 4, 5.5, RING_T], center = true);
            // 壁のポスト（下へ出す）
            rotate([0, 0, 180]) arc_block(3.8, 5.4, POST_ARC, Z_LUG_B - 0.1, Z_RING_B);
            // 🔒 球の逃げ止めの柵（内外・高さ0.5）。つまみを0.4mm引き上げると
            //    溝の掛かりが0.2mmしか残らず、振ると球が輪から逃げるため（2026-08-15、
            //    組立手順を書いていて発見）。フランジ下面との隙間は0.5残る
            for (rr = [[5.9, 6.3], [8.3, 8.7]])
                translate([0, 0, Z_RING_T]) difference() {
                    cylinder(r = rr[1], h = 0.5);
                    translate([0, 0, -1]) cylinder(r = rr[0], h = 2.5);
                }
        }
        translate([0, 0, Z_RING_B - 1]) cylinder(d = RING_IN, h = RING_T + 2);
        for (s = [-1, 1]) translate([s * BOSS_X, 0, Z_RING_B - 1])
            cylinder(d = M2_D + 0.4, h = RING_T + 2);
    }
}

// ============================================================
// 台座 ── 筐体の天面に union / difference で組み込む
//   knob_station_add() … 柱・ねじ台（天板の下面に生える側）
//   knob_station_cut() … 落とし込みの穴
// ============================================================
module knob_station_add() {
    // AS5600 の柱（小判形。丸柱は長穴の向きの肉厚0.3mmで折れた実績）
    for (x = [-1, 1], y = [-1, 1])
        translate([x * HOLE_PITCH / 2, y * HOLE_PITCH / 2, Z_PCB_TOP])
            difference() {
                hull() for (s = [-1, 1]) translate([s * SLOT_LEN / 2, 0, 0])
                    cylinder(d = STANDOFF_D, h = Z_DECK_BOT - Z_PCB_TOP);
                hull() for (s = [-1, 1]) translate([s * SLOT_LEN / 2, 0, -1])
                    cylinder(d = M2_D, h = Z_DECK_BOT - Z_PCB_TOP + 2);
                hull() for (s = [-1, 1]) translate([s * SLOT_LEN / 2, 0, -0.01])
                    cylinder(d = NUT_AF / cos(30), h = NUT_T, $fn = 6);
            }
    // 押さえリングのねじ台（±X）。ナットは横挿しのポケット
    for (s = [-1, 1]) translate([s * BOSS_X, 0, 0])
        difference() {
            // ⚠ 高さは天板の**上面(Z=0)まで**。以前 +DECK_T-1 として
            //    天板の外へ 1.5mm 突き出していた（2026-08-15 発見）
            translate([-2.75, -2.75, Z_RING_T]) cube([5.5, 5.5, -Z_RING_T]);
            translate([0, 0, Z_RING_T - 1]) cylinder(d = M2_D + 0.2, h = -Z_RING_T);
            // ナットの横挿しポケット（+Y から挿す）
            translate([0, 2.76, Z_RING_T + 1.6]) rotate([90, 0, 0])
                cylinder(d = NUT_AF / cos(30), h = 5.6, $fn = 6);
        }
}
module knob_station_cut() {
    translate([0, 0, Z_DECK_BOT - 1]) cylinder(d = HOLE_D, h = DECK_T + 2);
}

// 卓上テスト用の座（本番はこの plate が筐体の天板になる）
module deck_test() {
    difference() {
        union() {
            translate([-SEAT_X / 2, -SEAT_Y / 2, Z_DECK_BOT]) cube([SEAT_X, SEAT_Y, DECK_T]);
            knob_station_add();
        }
        knob_station_cut();
    }
}

// ============================================================
module assembly(show_plate = false) {
    color("#d8dde3") knob_part();
    color("#b8623a", 0.9) ring_part();
    color("#e8f4f8") for (i = [0 : BALL_N - 1]) rotate([0, 0, i * 360 / BALL_N])
        translate([RACE_R, 0, Z_BALL_C]) sphere(d = BALL_D);
    if (show_plate) color("#9aa5b1", 0.75) deck_test();
    else            color("#9aa5b1", 0.75) knob_station_add();
    color("#2b6b3f") translate([-PCB / 2, -PCB / 2, Z_PCB_BOT]) cube([PCB, PCB, PCB_T]);
    color("#333")    translate([-2.5, -2, Z_PCB_TOP]) cube([5, 4, CHIP_H]);
    color("#bbb")    translate([0, 0, Z_MAG_BOT]) cylinder(d = 4.0, h = 2.0);
}

// 分解図（組立順を上から: つまみ → 球 → リング → 台座 → AS5600）
module exploded() {
    translate([0, 0, 26]) color("#d8dde3") knob_part();
    color("#e8f4f8") for (i = [0 : BALL_N - 1]) rotate([0, 0, i * 360 / BALL_N])
        translate([RACE_R, 0, Z_BALL_C + 16]) sphere(d = BALL_D);
    translate([0, 0, 8])  color("#b8623a") ring_part();
    color("#9aa5b1", 0.8) deck_test();
    translate([0, 0, -10]) {
        color("#2b6b3f") translate([-PCB / 2, -PCB / 2, Z_PCB_BOT]) cube([PCB, PCB, PCB_T]);
        color("#333") translate([-2.5, -2, Z_PCB_TOP]) cube([5, 4, CHIP_H]);
    }
    translate([0, 0, 20]) color("#bbb") translate([0, 0, Z_MAG_BOT]) cylinder(d = 4.0, h = 2.0);
}

if      (part == "explode") exploded();
else if (part == "knob") translate([0, 0, GRIP_GAP + GRIP_H]) rotate([180, 0, 0]) knob_part();
// ⚠ 壁のポストは Z_RING_B より下へ出るので、そこを基準にしないとプレート下に沈む
else if (part == "ring") translate([0, 0, -(Z_LUG_B - 0.1)]) ring_part();
else if (part == "deck") rotate([180, 0, 0]) deck_test();   // 反転で最下点が Z=0
else                     assembly(show_plate = true);

TILT = atan(2 * (GROOVE_R - BALL_D / 2) / (2 * RACE_R));
echo(str("球の輪 φ", RACE_R * 2, " / 球 φ", BALL_D, " ×", BALL_N, "個 / 溝は片側のみ"));
echo(str("傾き ", TILT, "度 → 磁石の横ずれ ",
         (Z_BALL_C - Z_MAG_BOT) * tan(TILT), "mm（許容 0.25）"));
echo(str("回転の壁 ", 360 - LUG_ARC - POST_ARC, "度（SPAN270＋吸着帯45）"));
echo(str("天面下に要る深さ ", knob_deep(), "mm / 外へ ", knob_grip_h(),
         "mm / 座 ", SEAT_X, "×", SEAT_Y));
