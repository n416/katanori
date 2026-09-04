// 積み上げの検討（2026-08-19・ユーザー案）── **画面で見るための模型。刷らない。**
//
//   openscad hardware/stack_study.scad                    // 組んだところ
//   openscad -D 'view="exp"' hardware/stack_study.scad    // 分解（下から重なる）
//   openscad -D 'view="sec"' hardware/stack_study.scad    // 断面（y<0 を残す）
//
// ============================================================
// 案（ユーザー・2026-08-19）: 彫るのをやめて積む
// ============================================================
// 掘り込みの底は、刷ると必ず天井になる。だから凹みを「彫った穴」ではなく
// 「2枚のあいだの隙間」にする。段の数だけ板を分ければ、どの板も**貫通穴しか持たない**。
//
// ⚠ すり鉢は**要らなくなった**。円錐が要ったのは「棚を作らずに受け止める」ため
//    （棚は水平な上向きの面なので、天板を裏返して刷ると天井になる）。
//    板を天板の**下に**重ねてペグで留めるなら、受け止める必要そのものが無い。
//
// ============================================================
// 部品と、入れる向き
// ============================================================
//   天板 … φ26.2 の**貫通穴**だけ。裏にペグの止まり穴が2つ
//   A（内側凸＋回転限界止め）… 上面がへこみの底。円弧のスリットは**貫通**。
//                              残した 20度 がそのまま壁になる
//   B（内側溝の床）… 上面が溝の底。中央が軸の穴
//   ペグ2本 … 下から挿して、B と A を貫き、天板の止まり穴へ圧入
//
// 🔒 **組む向きは全部「下から」。上から落とすものは1つも無い。**
//    A も B も天板の穴（φ26.2）より大きいので、上からは入らないし、上へも抜けない。
//    上から入るのはつまみだけ（段 φ10 が軸の穴 φ11 を通る）。
//
// ============================================================
// 🔒 刷る向きと、そのとき各面がどうなるか
// ============================================================
//   天板 : 見える面をプレートへ。
//          ・見える面      … プレートに接する  ✅
//          ・φ26.2 の穴    … 貫通・垂直        ○ 層の縞
//          ・裏面（A の座）… 上を向く          ✅
//          ・ペグの止まり穴… **上へ開く**       ✅ 天井にならない
//   A    : 下面をプレートへ（上面にペグを生やさないこと）。
//          ・上面（へこみの底・見える）… 上を向く ✅
//          ・下面                      … プレートに接する ✅
//          ・スリットの壁（ツメが当たる）… 貫通・垂直 ○
//   B    : どちらでもよい。両面とも平ら
//   🔴 **どの部品にも下を向く水平面が無い。** これが今回の狙いそのもの。

view = "explode";
// 受け方の切り替え。
//   "peg"   … 板を天板の**下**に重ねてペグで吊る（最初の版）
//   "shelf" … 板を穴の**中**へ落として棚で受ける
//   "cone"  … 板を穴の**中**へ落として**すり鉢**で受ける
//   "screw" … 板を天板の**下**に重ねて、**下からのねじ2本で天板へ引き付ける**
//   "onepiece" … 🔒 **天板と床を一体のままにして、壁だけ別部品にする**（2026-08-19 ユーザー案）
//     床が天板と一体なので落ちようがなく、支える仕掛けが一切要らない。
//     壁は床の上に乗るだけ。上へは持ち手（0.5mm 上）が蓋になる。
// 🔒 違いは重さの行き先。ペグ版は重力が板を天板から引き剥がす向きに働くので、
//    ぶら下がるもの（基板・柱・半月・つまみ・指の力）を全部ペグの摩擦が持つ。
//    棚版は重力が板を棚へ押し付けるので、ペグ（＝溝）は回り止めだけになる。
SEAT = "onepiece";
$fn  = 96;

// ---- knob_v4 から持ってきた実寸 ----
DECK_T   = 2.5;            // 見える面の厚み
DISH_D   = 26.2;           // へこみ＝持ち手 φ25 が沈む貫通穴
BORE_D   = 11.0;           // 軸（段 φ10）が通る穴
STOP_R0  = 9.8;            // 回転の溝の内側
STOP_R1  = 12.0;           // 　　　　　外側
STOP_ANG = 270;            // 壁の位置
POST_ARC = 20;             // 壁の角度幅
A_T      = 1.5;            // A の厚み ＝ 溝の深さ
B_T      = 1.5;            // B の厚み
// A・B の外形。🔒 天板の穴（26.2）を全周でくわえること。⚠ Y は 28 が下限で、
//    かかりは片側 0.9mm しか無い（実物の座 44×28 と同じ事情）
PLATE_X  = 40.0;
PLATE_Y  = 28.0;
PEG_D    = 4.0;
PEG_L    = 1.4;            // 天板へ入る長さ
PEG_R    = 16.0;           // ペグの位置（±X）。⚠ へこみの縁 13.1 の外・板の縁 20 の内
PEG_CL   = 0.2;            // A・B のペグ穴の逃げ（径）。⚠ 締め代は天板側だけで作る
PAD_X    = 44; PAD_Y = 28;
// ---- ねじ止め版 ----
// 🔒 ペグ版の弱点（重さを摩擦だけで持つ）を、ねじに置き換えただけ。
//    板は穴（φ26.2）より大きいので**上へ抜けない**。下からのねじで天板へ引き付けるので、
//    逆さにしても落ちない。ねじ2本が回り止めも兼ねる。
// 🔒 組む向き: 壁と床は**下から**。つまみだけ**上から**（段 φ10 が軸の穴 φ11 を通る）。
SCR_R    = 16.0;           // ねじの位置（±X）。⚠ へこみの縁 13.1 より外＝天板の肉がある所
SCR_CL   = 2.4;            // 壁・床の通し穴（M2）
SCR_PILOT = 1.7;           // 天板の下穴。🔒 case_v2 の M2_PILOT と同じ値
SCR_DEPTH = 1.5;           // 下穴の深さ。⚠ 天板 2.5 に対して残り 1.0mm
PLT_X = 40.0; PLT_Y = 28.0;
// ---- 棚で受ける版 ----
// 🔒 重さの行き先が変わる。板は天板の**穴の中**に落ちるので、重力は板を棚へ押し付ける。
//    ペグ版は板が天板の**下**に重なるので、重力が板を引き剥がす向きに働き、
//    ペグの摩擦だけが全部を持っていた（下にぶら下がる基板・柱・半月・つまみも含めて）。
SHELF_W  = 1.0;            // 棚の幅。⚠ 刷ると「青」と同じ生まれ方をする輪になる。
                           //    青は幅 1.1mm だったので、それ以上広げない
SEAT_CL  = 0.2;            // 板と穴の逃げ（径）
// 回り止め。⚠ **ペグは入らない。** 板は穴の中（半径13.1まで）に居るので、
//    ペグを置ける場所が「内側の輪（幅4.3・折れやすい）」か「外側の輪（幅1.1）」しかない。
//    そこで穴の壁に**縦の溝**を1本切って、板側の出っぱりで受ける。
//    刷ると縦の面なので天井にならない。⚠ 上から見ると壁に切れ目が1本見える
KEY_W    = 5.0;
KEY_D    = 1.5;
KEY_ANG  = 180;
// ---- すり鉢で受ける版（ユーザーの元案）----
// 🔒 台形円錐を上から落とし、穴の壁の傾きで受け止める。段の数だけ落とす。
//    棚と違って**下を向いた水平面ができない**。円錐面はどの層も外周ひと回りが
//    下の層に乗るので、赤のような片持ちにならない。
// ⚠ 代わりに突き当たりが無い。径が細いぶんだけ深く座る（45度なら差の半分）。
//    下の echo で「径 0.1 あたり何mm沈むか」を出してある。
CONE_ANG = 45;
CONE_CL  = 0.15;
// ---- 壁の回り止め（2026-08-19 ユーザー指摘「乗せるだけだと回転してしまう」）----
// 🔒 壁は限界止めを持っているので、つまみを止めたときの力がそのまま壁を回そうとする。
//    床に乗せるだけでは受けられない。**外周に爪を1つ出して、穴の壁の縦溝で受ける。**
// 🔒 溝は天板の**下まで抜く**。途中で止めると、その天井が下向きの水平面になる。
// ⚠ へこみ（0〜-2.5）は丸いまま。溝が始まるのは壁の上面（-2.5）からなので、
//    真上から見えるのはへこみの底の縁にある小さな窪みだけで、見える面には出ない。
LUG_W  = 5.0;              // 爪の幅
LUG_D  = 1.5;              // 爪の出っぱり（半径方向）
LUG_CL = 0.2;              // 溝の逃げ
LUG_ANG2 = 180;            // 置く角度。⚠ 回転止めの壁（270度）とは別の場所           // 板と穴の逃げ（径）。⚠ これがそのまま沈み込みになる
function cone_d(z) = DISH_D + 2 * (z - Z_A_T) * tan(CONE_ANG);   // 深いほど細い

Z_A_T = -DECK_T;                 // A の上面＝へこみの底
Z_A_B = Z_A_T - A_T;             // A の下面＝溝の底の高さ
Z_B_B = Z_A_B - B_T;

// ---- 天板＋床が一体・壁だけ別（ユーザー案・2026-08-19）----
// ⚠ ここは Z_A_B より**後**に置くこと。OpenSCAD は前方参照しない（undef になる）
Z_FLOOR  = Z_A_B;          // -4.0 床の面（＝壁が乗る高さ）
LAND_R0  = 11.9;           // 壁を受ける輪の内側。ここより内は掘り下げて触らせない
RELIEF_T = 0.4;            // 掘り下げる量
PAD_BOT  = -7.7;           // 座の裏（knob_v4 の Z_PAD_BOT）

// A・B の外形。角は丸める（剥がすときに欠けやすいので）
module plate_body(h) {
    linear_extrude(h) offset(r = 2) square([PLATE_X - 4, PLATE_Y - 4], center = true);
}

module peg_holes(d, z0, h) {
    for (s = [-1, 1]) translate([s * PEG_R, 0, z0]) cylinder(d = d, h = h);
}

module deck() {
    difference() {
        translate([-PAD_X / 2, -PAD_Y / 2, -DECK_T]) cube([PAD_X, PAD_Y, DECK_T]);
        translate([0, 0, -DECK_T - 1]) cylinder(d = DISH_D, h = DECK_T + 2);
        // ペグの止まり穴。🔒 見える面へ抜かない。⚠ 刷るときは上へ開く＝天井にならない
        peg_holes(PEG_D, -DECK_T - 0.01, PEG_L + 0.31);
    }
}

// A … 内側凸＋回転限界止め。🔒 円弧のスリットは**貫通**（彫ると底が天井になる）
module part_a() {
    difference() {
        translate([0, 0, Z_A_B]) plate_body(A_T);
        translate([0, 0, Z_A_B - 1]) cylinder(d = BORE_D, h = A_T + 2);
        difference() {
            translate([0, 0, Z_A_B - 1]) rotate_extrude()
                translate([STOP_R0, 0]) square([STOP_R1 - STOP_R0, A_T + 2]);
            rotate([0, 0, STOP_ANG]) translate([0, 0, Z_A_B - 2]) rotate_extrude(angle = POST_ARC)
                translate([STOP_R0 - 1, 0]) square([STOP_R1 - STOP_R0 + 2, A_T + 4]);
        }
        peg_holes(PEG_D + PEG_CL, Z_A_B - 1, A_T + 2);
    }
}

// B … 溝の床
module part_b() {
    difference() {
        translate([0, 0, Z_B_B]) plate_body(B_T);
        translate([0, 0, Z_B_B - 1]) cylinder(d = BORE_D, h = B_T + 2);
        peg_holes(PEG_D + PEG_CL, Z_B_B - 1, B_T + 2);
    }
}

// ペグ。下から挿して B・A を貫き、天板へ食い込む
module pegs() {
    for (s = [-1, 1]) translate([s * PEG_R, 0, Z_B_B])
        cylinder(d = PEG_D, h = A_T + B_T + PEG_L);
}

// faces.png と同じ塗り分け。どの面がどの板に移ったかを見るため
FILM = 0.12;
module band(r0, r1, z, a = 360, a0 = 0)
    rotate([0, 0, a0]) translate([0, 0, z]) rotate_extrude(angle = a)
        translate([r0, 0]) square([r1 - r0, FILM]);

module faces() {
    color("#e03131") band(BORE_D / 2, STOP_R0, Z_A_T);              // 赤: 内側の輪
    color("#1c7ed6") band(STOP_R1, DISH_D / 2, Z_A_T);              // 青: 外側の輪
    color("#2f9e44") band(STOP_R0, STOP_R1, Z_A_T, POST_ARC, STOP_ANG);   // 緑: 壁の上面
    color("#f59f00") band(STOP_R0, STOP_R1, Z_A_B, 340, STOP_ANG + POST_ARC); // 橙: 溝の床
}

// ---- 棚版 ----
Z_SHELF = Z_B_B;                        // -5.5 棚の面
BORE_UNDER = DISH_D - 2 * SHELF_W;      // 24.2 棚より下の穴

module key_solid(clear = 0) {
    rotate([0, 0, KEY_ANG])
        translate([DISH_D / 2 - 0.01, -(KEY_W + clear) / 2, Z_SHELF - 1])
            cube([KEY_D + clear / 2, KEY_W + clear, 10]);
}

module deck_shelf() {
    difference() {
        translate([-PAD_X / 2, -PAD_Y / 2, Z_SHELF - 1]) cube([PAD_X, PAD_Y, -Z_SHELF + 1]);
        // へこみ＋板の入る穴（同径。板の上面がそのままへこみの底になる）
        translate([0, 0, Z_SHELF]) cylinder(d = DISH_D, h = -Z_SHELF + 1);
        // 棚より下は細い穴。この段差の上面が**棚**
        translate([0, 0, Z_SHELF - 2]) cylinder(d = BORE_UNDER, h = 2.01);
        key_solid(SEAT_CL);
    }
}

module plate_disc(zb, t) {
    difference() {
        union() {
            translate([0, 0, zb]) cylinder(d = DISH_D - SEAT_CL, h = t);
            intersection() { key_solid(); translate([0, 0, zb]) cylinder(d = 40, h = t); }
        }
        translate([0, 0, zb - 1]) cylinder(d = BORE_D, h = t + 2);
    }
}

module part_a_shelf() {
    difference() {
        plate_disc(Z_A_B, A_T);
        difference() {
            translate([0, 0, Z_A_B - 1]) rotate_extrude()
                translate([STOP_R0, 0]) square([STOP_R1 - STOP_R0, A_T + 2]);
            rotate([0, 0, STOP_ANG]) translate([0, 0, Z_A_B - 2]) rotate_extrude(angle = POST_ARC)
                translate([STOP_R0 - 1, 0]) square([STOP_R1 - STOP_R0 + 2, A_T + 4]);
        }
    }
}

// ---- すり鉢版 ----
// 回り止めの溝（天板側）。🔒 下まで抜く
// 🔒 溝の**天井を作らない**。単純な角柱で切ると、上端（-2.5）の外側 1.5mm ぶんが
//    天板の肉の下に残り、そこが下向きの水平面（約 7.8mm²）になる。
//    外へ行くほど上がる 45度 の斜めにして、水平面を消してある。
//    ⚠ 一番外で -1.0 まで上がるので、見える面までは 1.0mm 残る（抜けない）
module lug_slot(clear) {
    R0 = DISH_D / 2 - 0.5;          // 12.6
    R1 = R0 + LUG_D + 0.5;          // 14.6
    RD = DISH_D / 2;                // 13.1 ここから外は天板の肉の下
    rotate([0, 0, LUG_ANG2]) translate([0, (LUG_W + clear) / 2, 0]) rotate([90, 0, 0])
        linear_extrude(LUG_W + clear) polygon([
            [R0, Z_B_B - 1.01], [R1, Z_B_B - 1.01],
            [R1, Z_A_T + 1.5], [RD, Z_A_T], [R0, Z_A_T]]);
}

module deck_cone() {
    difference() {
        translate([-PAD_X / 2, -PAD_Y / 2, Z_B_B - 1]) cube([PAD_X, PAD_Y, -(Z_B_B - 1)]);
        // へこみ（持ち手が沈む。ここは真っ直ぐ）
        translate([0, 0, Z_A_T]) cylinder(d = DISH_D, h = -Z_A_T + 1);
        // すり鉢。A と B の2段ぶんを1つの円錐で受ける
        translate([0, 0, Z_B_B])
            cylinder(d1 = cone_d(Z_B_B), d2 = cone_d(Z_A_T), h = -Z_A_T + Z_A_T - Z_B_B);
        // その下は円錐の細い側のまま抜く
        translate([0, 0, Z_B_B - 2]) cylinder(d = cone_d(Z_B_B), h = 2.01);
        lug_slot(LUG_CL);
    }
}

// 台形円錐の板。zb から t だけの帯を、穴と同じ傾きで切り出す
module cone_disc(zb, t) {
    difference() {
        union() {
            translate([0, 0, zb])
                cylinder(d1 = cone_d(zb) - CONE_CL, d2 = cone_d(zb + t) - CONE_CL, h = t);
        }
        translate([0, 0, zb - 1]) cylinder(d = BORE_D, h = t + 2);
    }
}

// 壁。🔒 円錐をやめて真っ直ぐな輪にし、床の上に載せる（2026-08-19）。
//    円錐のままだと外周（上端で 1.1mm）が 1.1mm 潜った時点で消え、細い輪が離れて折れる。
module part_a_cone() {
    difference() {
        union() {
            translate([0, 0, Z_A_B])
                cylinder(d = DISH_D - CONE_CL, h = A_T);
            intersection() {
                lug_slot(0);
                translate([0, 0, Z_A_B]) cylinder(d = 60, h = A_T);
            }
        }
        translate([0, 0, Z_A_B - 1]) cylinder(d = BORE_D, h = A_T + 2);
        difference() {
            translate([0, 0, Z_A_B - 1]) rotate_extrude()
                translate([STOP_R0, 0]) square([STOP_R1 - STOP_R0, A_T + 2]);
            rotate([0, 0, STOP_ANG]) translate([0, 0, Z_A_B - 2]) rotate_extrude(angle = POST_ARC)
                translate([STOP_R0 - 1, 0]) square([STOP_R1 - STOP_R0 + 2, A_T + 4]);
        }
    }
}

// 🔒 分解図には部品名を入れる。⚠ 2026-08-19、会話で A / B と呼びながら
//    どれがどれか一度もまともに示さず、「説明が意味不明」と言われた。
//    名前は図の中に置く。文章の中だけに置かない。
LBL_FONT = "MS Gothic";
module label(txt, z, sub = "") {
    color("#111") translate([PAD_X / 2 + 3, -PAD_Y / 2 - 1, z]) rotate([90, 0, 0]) {
        linear_extrude(0.6) text(txt, size = 3.4, font = LBL_FONT);
        translate([0, -3.4, 0]) linear_extrude(0.6) text(sub, size = 2.0, font = LBL_FONT);
    }
}

module labels(gap) {
    // ⚠ 名札は**その版で実際に描いている位置**に合わせる。
    //    下から組む版（screw / peg）は壁が天板寄り、上から落とす版（cone / shelf）は床が先。
    UNDER = (SEAT == "screw" || SEAT == "peg");
    if (SEAT == "onepiece") {
        label("天板＋床", -1.0, "一体。壁が乗る面が掘ってある");
        label("壁", Z_FLOOR + gap + 0.5, "溝の壁と回転止め。上面がへこみの底");
    } else {
    label("天板", -1.0, "見える面とへこみ");
    label("壁", Z_A_B + (UNDER ? gap : gap * 2) + 0.5,
          UNDER ? "溝の壁と回転止め。天板の下に密着" : "溝の壁と回転止め");
    label("床", Z_B_B + (UNDER ? gap * 2 : gap) + 0.5,
          UNDER ? "溝の底。この下からねじが来る" : "溝の底。すり鉢が受ける");
    }
}

// ---- ねじ止め版 ----
module scr_holes(d, z0, h) { for (t = [-1, 1]) translate([t * SCR_R, 0, z0]) cylinder(d = d, h = h); }
module plt(zb, t) {
    difference() {
        translate([0, 0, zb]) linear_extrude(t)
            offset(r = 2) square([PLT_X - 4, PLT_Y - 4], center = true);
        translate([0, 0, zb - 1]) cylinder(d = BORE_D, h = t + 2);
        scr_holes(SCR_CL, zb - 1, t + 2);
    }
}
module deck_screw() {
    difference() {
        translate([-PAD_X / 2, -PAD_Y / 2, -DECK_T]) cube([PAD_X, PAD_Y, DECK_T]);
        translate([0, 0, -DECK_T - 1]) cylinder(d = DISH_D, h = DECK_T + 2);
        // 下穴。🔒 見える面へ抜かない。⚠ 刷るときは上へ開くので天井にならない
        scr_holes(SCR_PILOT, -DECK_T - 0.01, SCR_DEPTH + 0.01);
    }
}
module wall_screw() {
    difference() {
        plt(Z_A_B, A_T);
        difference() {
            translate([0, 0, Z_A_B - 1]) rotate_extrude()
                translate([STOP_R0, 0]) square([STOP_R1 - STOP_R0, A_T + 2]);
            rotate([0, 0, STOP_ANG]) translate([0, 0, Z_A_B - 2]) rotate_extrude(angle = POST_ARC)
                translate([STOP_R0 - 1, 0]) square([STOP_R1 - STOP_R0 + 2, A_T + 4]);
        }
    }
}
module screws() {
    for (t = [-1, 1]) translate([t * SCR_R, 0, Z_B_B]) {
        translate([0, 0, -1.6]) cylinder(d = 3.8, h = 1.6);   // 頭（床の下）
        cylinder(d = 2.0, h = -Z_B_B - DECK_T + SCR_DEPTH);
    }
}

// ---- 天板＋床 一体版 ----
module deck_one() {
    difference() {
        translate([-PAD_X / 2, -PAD_Y / 2, PAD_BOT]) cube([PAD_X, PAD_Y, -PAD_BOT]);
        // へこみ＋壁の入る座（同径。壁の上面がそのままへこみの底になる）
        translate([0, 0, Z_FLOOR]) cylinder(d = DISH_D, h = -Z_FLOOR + 1);
        // 🔒 床の内側を掘り下げる。**壁が当たるのは外周の輪だけ**にして、
        //    天井のうち垂れる側（内側）に触らせない
        translate([0, 0, Z_FLOOR - RELIEF_T])
            cylinder(d = LAND_R0 * 2, h = RELIEF_T + 0.01);
        // 軸の通る穴
        translate([0, 0, PAD_BOT - 1]) cylinder(d = BORE_D, h = -PAD_BOT + 2);
    }
}
module wall_one() {
    difference() {
        translate([0, 0, Z_FLOOR]) cylinder(d = DISH_D - 0.2, h = A_T);
        translate([0, 0, Z_FLOOR - 1]) cylinder(d = BORE_D, h = A_T + 2);
        difference() {
            translate([0, 0, Z_FLOOR - 1]) rotate_extrude()
                translate([STOP_R0, 0]) square([STOP_R1 - STOP_R0, A_T + 2]);
            rotate([0, 0, STOP_ANG]) translate([0, 0, Z_FLOOR - 2]) rotate_extrude(angle = POST_ARC)
                translate([STOP_R0 - 1, 0]) square([STOP_R1 - STOP_R0 + 2, A_T + 4]);
        }
    }
}

module note(txt, x, z) color("#111")
    translate([x, -0.4, z]) rotate([90, 0, 0]) linear_extrude(0.5)
        text(txt, size = 1.3, font = LBL_FONT);

module cut_view() {
    intersection() { all(); translate([-0.5, 0, -30]) cube([40, 40, 60]); }
    // 注記は絵の外に置くと指す先が分からなくなるので、キャプションで説明する
}

module all(gap = 0) {
    if (SEAT == "onepiece") {
        color("#9aa5b1", 0.8) deck_one();
        color("#e03131")      translate([0, 0, gap]) wall_one();
    } else
    if (SEAT == "screw") {
        color("#9aa5b1", 0.75) deck_screw();
        color("#c8763f")       translate([0, 0, gap])     wall_screw();
        color("#7f8c8d")       translate([0, 0, gap * 2]) plt(Z_B_B, B_T);
        color("#e8e8e8")       translate([0, 0, gap * 3]) screws();
    } else if (SEAT == "cone") {
        color("#9aa5b1", 0.75) deck_cone();
        color("#7f8c8d")       translate([0, 0, gap])     cone_disc(Z_B_B, B_T);   // 先に入る
        color("#c8763f")       translate([0, 0, gap * 2]) part_a_cone();           // 後から乗る
    } else if (SEAT == "shelf") {
        color("#9aa5b1", 0.75) deck_shelf();
        color("#7f8c8d")       translate([0, 0, gap])     plate_disc(Z_B_B, B_T);
        color("#c8763f")       translate([0, 0, gap * 2]) part_a_shelf();
    } else {
        color("#9aa5b1", 0.75) deck();
        color("#c8763f")       translate([0, 0, gap])     part_a();
        color("#7f8c8d")       translate([0, 0, gap * 2]) part_b();
        color("#e8e8e8")       translate([0, 0, gap * 3]) pegs();
    }
}

// 🔒 分解図は**組む向きに開く**。円錐版と棚版は穴の中へ**上から**落とすので上へ開き、
//    深く入る B を天板寄り・後から乗る A をその上に置く。
//    ペグ版だけは板が天板の**下**に重なるので下へ開く。
//    ⚠ 2026-08-19、全部下へ開いていて「上から嵌めるのに位置が逆」と指摘された
if      (view == "exp") { all(gap = (SEAT == "peg" || SEAT == "screw") ? -11 : 12);
                          labels((SEAT == "peg" || SEAT == "screw") ? -11 : 12); }
else if (view == "faces") { all(); faces(); }
else if (view == "cut") { cut_view(); }
else if (view == "sec") intersection() { all(); translate([-40, -40, -30]) cube([80, 40, 60]); }
else                    all();

echo(str("座の厚み ", DECK_T + A_T + B_T, "mm（見える面 ", DECK_T, " ＋ A ", A_T,
         " ＋ B ", B_T, "）⚠ knob_v4 の座は 7.7mm。残りは軸受けと柱の受け持ち"));
echo(str("溝 半径 ", STOP_R0, "〜", STOP_R1, "（幅 ", STOP_R1 - STOP_R0,
         "）× 深さ ", A_T, " ＝ A の厚み。壁は ", POST_ARC, "度"));
echo(str("A・B の外形 ", PLATE_X, "×", PLATE_Y, " ↔ 天板の穴 ", DISH_D,
         " → かかり X 片側 ", (PLATE_X - DISH_D) / 2, " / Y 片側 ", (PLATE_Y - DISH_D) / 2,
         "mm ⚠ 負なら上から抜ける"));
echo(str("ペグ ±", PEG_R, " → へこみの縁 ", DISH_D / 2, " まで ", PEG_R - PEG_D / 2 - DISH_D / 2,
         " / 板の縁 ", PLATE_X / 2, " まで ", PLATE_X / 2 - PEG_R - PEG_D / 2, "mm ⚠ 負なら食い込む"));
echo(str("天板に残る肉 ", DECK_T - (PEG_L + 0.3), "mm ⚠ 負なら見える面へ抜ける"));
// 🔴 分けたことで、印刷の弱点が**取り扱いの弱点に化けている**
A_RING_W = STOP_R0 - BORE_D / 2;
echo(str("⚠ A の内側の輪: 幅 ", A_RING_W, " × 厚み ", A_T,
         " が、壁 ", POST_ARC, "度（弧長 ", 2 * 3.14159 * (STOP_R0 + STOP_R1) / 2 * POST_ARC / 360,
         "mm・幅 ", STOP_R1 - STOP_R0, "）のタブ1本でぶら下がる。",
         "刷るときは1層目なので平気だが、**プレートから剥がすときに折れる形**"));
if (SEAT == "screw") {
  echo(str("板 ", PLT_X, "×", PLT_Y, " ↔ 天板の穴 φ", DISH_D,
           " → かかり X 片側 ", (PLT_X - DISH_D) / 2, " / Y 片側 ", (PLT_Y - DISH_D) / 2,
           "mm ⚠ 負なら上へ抜ける"));
  echo(str("ねじ ±", SCR_R, "（へこみの縁 ", DISH_D / 2, " の外）／ 下穴 φ", SCR_PILOT,
           " 深さ ", SCR_DEPTH, " → 見える面の下に ", DECK_T - SCR_DEPTH, "mm 残る"));
  echo("🔒 重さの行き先: つまみ・半月・基板・柱 → 床 → 壁 → **ねじ** → 天板。摩擦に頼らない");
  echo("🔒 逆さにしても落ちない。ねじ2本が回り止めも兼ねる（別部品が要らない）");
  echo("🔒 下を向く水平面 0: 天板＝貫通穴と上へ開く下穴／壁・床＝両面平ら・穴とスリットは貫通");
} else if (SEAT == "cone") {
  echo(str("すり鉢 ", CONE_ANG, "度: 口 φ", cone_d(Z_A_T), " → A の下 φ", cone_d(Z_A_B),
           " → B の下 φ", cone_d(Z_B_B)));
  echo(str("🔒 下を向いた**水平**面: 0。円錐面はどの層も外周ひと回りが下の層に乗る",
           "（赤のような片持ちにならない）"));
  echo(str("⚠ 突き当たりが無い: 径が 0.1 細いと ", 0.1 / 2 / tan(CONE_ANG),
           "mm 深く座る。逃げ ", CONE_CL, " ぶんで ", CONE_CL / 2 / tan(CONE_ANG),
           "mm 沈む見込み"));
  echo(str("⚠ A と B は別々に円錐へ座る。逃げが同じなら沈み量も同じなので、",
           "溝の隙間（", A_T, "mm）は保たれる。片方だけ縮むと隙間が変わる"));
  // ⬜ 回り止めは未解決。⚠ 2026-08-19 に AI が縦の角柱で入れたが、
  //    ① 天板の見える面を貫通していた ② 円錐の傾きを無視した出っぱりだった、で撤去。
  // 🔒 B は回り止めが要らない（丸いだけで、向きを持つ形が無い）。
  //    要るのは A だけで、A は回転限界止めを持っている。
  // ⚠ 平面（D カット）では解けない: 溝の外径は 12.0 で、そこより外にしか平面を置けないが、
  //    A の外周は下端で 11.525 まで細るので、平面が当たるのは上の 0.6mm ほどしかない。
  echo(str("回り止め: 壁の外周に爪 ", LUG_W, "×", LUG_D, " を1つ、", LUG_ANG2,
           "度。天板の溝は下まで抜くので天井にならない。床は回り止め不要"));
  echo(str("壁: 真っ直ぐな輪 φ", DISH_D - CONE_CL, " → 外側の輪の幅 ",
           (DISH_D - CONE_CL) / 2 - STOP_R1, "mm を厚み全体で保つ（円錐だと下端で -0.475）"));
  echo("🔒 重さの行き先: つまみ・半月・基板・柱 → B → すり鉢 → 天板");
  // 🔴 A は円錐で細っていくのに、溝の外径は固定。どこで追い越されるかを見る
  A_RO_T = (cone_d(Z_A_T) - CONE_CL) / 2;
  A_RO_B = (cone_d(Z_A_B) - CONE_CL) / 2;
  echo(str("🔴 A の外周: 上 ", A_RO_T, " → 下 ", A_RO_B,
           " ／ 溝の外側は ", STOP_R1, " で固定 → 下端で外側の輪の幅 ",
           A_RO_B - STOP_R1, "mm ⚠ 負ならスリットが横に抜けている"));
  Z_BREAK = Z_A_T - (A_RO_T - STOP_R1);
  echo(str("   外側の輪が消える高さ z=", Z_BREAK, "（A は ", Z_A_T, "〜", Z_A_B,
           "）→ 残っているのは上から ", Z_A_T - Z_BREAK, "mm だけ"));
  echo(str("   つまり A は「内側の輪＋20度のタブ」に、上だけ残った薄い縁が付いた形。",
           "**折れる**"));
} else if (SEAT == "shelf") {
  echo(str("棚: 幅 ", SHELF_W, "mm（穴 φ", DISH_D, " → φ", BORE_UNDER, "）",
           " 面積 ", 3.14159 * (pow(DISH_D/2,2) - pow(BORE_UNDER/2,2)),
           "mm² が重さを受ける"));
  echo(str("⚠ この棚は刷ると**青と同じ生まれ方**をする輪（外周だけで穴の壁に付く）。",
           "青は幅 1.1mm だったので、", SHELF_W, " は同等"));
  echo(str("回り止め: 溝 ", KEY_W, "×", KEY_D, " を ", KEY_ANG, "度 に1本。",
           "⚠ 縦の面なので天井にはならないが、**上から見ると壁に切れ目が見える**"));
  echo("🔒 重さの行き先: つまみ・半月・基板・柱 → B → 棚 → 天板。ペグは持たない");
} else
  echo("🔴 重さの行き先: 全部ペグ2本の摩擦（基板・柱・半月・つまみ・指の力も含めて）");
echo(str("🔒 下を向く水平面: ", SEAT == "shelf" ? "1（棚そのもの）" : "0",
         " ／ A と B の両面は平ら・スリットと穴は貫通・回り止めは縦の面"));
