include <case_base.scad>   // 土台（Z_TOP / IN_Z / tsw_*() / spk_obround / hex_pocket / NUT_T / NUT_AF / SCR_D）
// ============================================================
// 📦 btn_v4.scad — 会話ボタン一式（2026-08-28 に case_base.scad と case_v4.scad から集約）
// ============================================================
// なぜ切り出したか（🔒 ユーザーの指摘・2026-08-28）:
//   「なんでつまみみたいに会話ボタンを別ファイル参照にせずに、CAD 上で直接やってんの」
//   会話ボタンは 1 個の部品としてどこにも存在せず、天板の一部として溶けていた。
//   受けは case_base.scad、天板に彫る欠きは case_v4.scad の top_v4() の中に**生の絶対座標**
//   （9.3 / 17.8 / 45.9 / 6.7 / 10.0 / 12.4）で直書きされていた。BTN4 を動かしてもこれらは
//   付いてこないし、天板側で何かが動いてもここは知らない。今日出た事故はこの境目で起きている。
//
// 誰が何を持つか（つまみ knob_v5.scad と同じ分け方）:
//   ・**このファイルが持つ**: ボタンの形の全部（受け・下から留める板・キャップ・クリップ）と、
//     天板に彫る欠きの全部。座標は **BTN4 を原点にした相対値**でしか書かない。
//   ・**case_v4.scad が持つ**: BTN4（置き場所）だけ。相対値を絶対値に直す関数と、
//     検証済みの絶対値を守る assert もそちら（つまみの k4x0() と同じ置き方）。
//
// 🔴 つまみと違って `use <>` ではなく `include <>` で読む。つまみは印刷物として独立していて
//    自分のローカル Z を持てるが、会話ボタンの Z は**天板の天井（Z_TOP・IN_Z）が決めている**ので
//    独立させると新しい座標系を発明することになる（それは禁じ手）。土台を上で自分で読んでいる。
//
//   ⭐ このファイルは**単体で開くと組んだ姿が出る**（1 行目で土台を読み、最後で絵を描く）。
//     _v4_core.scad はこのファイルだけを include すればよく、case_base.scad はここから
//     連れて来られる（二重 include を作らないため）。
//     読み込まれた側では絵は出ない（`BTN_SOLO` を _v4_core.scad が false にする）。
// ============================================================

// ---- 前列（会話ボタン＋スピーカー）の逃がし量 ----
// 🔒 2026-08-28 ユーザー「動かしてください」。ナットの座を ReSpeaker の前リブが 0.98mm 塞いでいた。
//   リブは X も Y も動かせないので、前列を +Y へ逃がした。値の置き場所はここ 1 か所だけ。
//   🔒 スピーカーも同じだけ動く（ユーザー「デザイン的にスピーカーの中央とは一緒にしたい」）。
//     _v4_core.scad の ROW_Y がこれを読んで BTN4 と SPK4 の両方に配る。
BTN_ROW_DY = 2.5;

// ---- 傘とその穴（v2 §4.7 そのまま）----
BTN_L = 18.0; BTN_W = 12.0; BTN_GAP = 0.5;
BTN_DISH_L = BTN_L + BTN_GAP * 2 + 0.2; BTN_DISH_W = BTN_W + BTN_GAP * 2 + 0.2;
BTN_TRAVEL = tsw_travel() + 0.25;
BTN_OUT = 3.0; BTN_H = BTN_OUT + 1.5; BTN_DISH_T = BTN_H - BTN_OUT + BTN_TRAVEL;
BTN_WALL = 1.6; BTN_PLG_D = 5.0; BTN_HOLE_D = BTN_PLG_D + 0.6;
BTN_NECK_D = 3.2; BTN_CLIP_T = 1.2; BTN_CLIP_D = 7.0; BTN_LIP_H = 0.8;
Z_BTN_DISH = Z_TOP - BTN_DISH_T; BTN_PAD_T = 1.6; Z_BTN_PAD = Z_BTN_DISH - BTN_PAD_T;
Z_NECK0 = Z_BTN_PAD - 0.2; Z_NECK1 = Z_NECK0 - BTN_CLIP_T - BTN_TRAVEL - 0.2; Z_TIP = Z_NECK1 - BTN_LIP_H;
Z_TSW_TOP = Z_TIP - (tsw_h() - tsw_body_h()); Z_TSW_BOT = Z_TSW_TOP - tsw_body_h();
BTN_PAD_X = 25.0; BTN_PAD_Y = 15.0; BTN_CLAW_W = 5.0; BTN_CLAW_G = 0.5; BTN_PKT_T = 1.2; BTN_POST_I = 3.6;
// 🔴 2026-08-28 実機（天板の初刷り）ユーザー「天板の会話ボタンの受け側部分が割れてしまった」
//    「おそらく、サポート柱を切っている最中に圧力が加わったから」。
//    受けのポケット（9.6 角）と板の間は 2.35mm しか空いておらず、そこに支柱が 8 本立っていた。
//    2.35mm の隙間にニッパーは入らないので、力は逃げ場を失って**柱**に掛かる。
//    柱は 1.2 角 x 4 本 ＝ 断面 5.76mm² しかない。ここが折れた。
//    ⇒ 🔒 ユーザー「そこ線通す訳じゃないなら囲っちゃえばいいんじゃないの？」。柱をやめ、
//      ポケットを**板まで伸ばして一体**にする（9.6 角 − 首の穴 φ5.6 ＝ 断面 67.5mm² ＝ 11.7 倍）。
//      ここには線は 1 本も通らない（INA の逃げは X 9.3〜14.3・受けは X 17.2〜26.8）。
//      隙間そのものが消えるので、**あの 8 本の支柱は 1 本も立たなくなる**。
//    ⚠ 消えた隙間は v1〜v3 で C 型クリップ（`button_clip` φ7.0・キャップの抜け止め）を
//      横から差す所だった。v4 は模型（`top_btn`）にも手順にも刷る 18 点にもクリップが無い。
//      クリップを使うなら、この胴に横から口を開け直すこと。
BTN_POCKET_TOP = Z_BTN_PAD;
BTN_AT = [TOP_MARGIN + BTN_DISH_L / 2, TOP_MARGIN + SPK_EMB_D + TOP_MARGIN + BTN_DISH_W / 2];
// 🔒 2026-08-27 ユーザー「あっちもカクカクで」「削れる所あるかみてくれる？」→「1.6 で」。
//    受けの板は 25 x 15 の長方形だったが、支えているのは皿（19.2 x 13.2 の小判）の底だけで、
//    隅の 80.0mm²（21%・肉 108mm³）は空気だった。皿の輪郭に壁 1.6 を残して沿わせる。
//    ⚠ 外へは広げない（BTN_PAD_X x BTN_PAD_Y の中で切るだけ）。皿＋1.6 は Y で 16.4 になり
//      元の 15.0 を超えるので、そこは元の縁で止まる。
//    🔴 この板の隅は 2026-08-26 に 2 度、手で欠いてある（INA の線の逃げ／OLED の
//       ナットの座）。1 度目は皿の底を抜いて表に穴が開いた。板が皿に沿っていれば要らない欠き。
BTN_PAD_WALL = 1.6;
module btn_pad_2d() intersection() {
    offset(r = BTN_PAD_WALL) hull() for (s = [-1, 1])
        translate([s * (BTN_DISH_L - BTN_DISH_W) / 2, 0]) circle(d = BTN_DISH_W, $fn = 64);
    square([BTN_PAD_X, BTN_PAD_Y], center = true);
}

// ---- 受け（天板の裏に立つ・ビス 2 本で下から留める）----
// 🔒 2026-08-28 受け（ユーザー案「ビス 2 本で下から留める。天板側の裏にナット穴のポケットで
//    ナットは横からいれる」）。一度却下 → 見たいので巻き戻して作った版。
//    ✅ 実物の足（3 穴 x 4 穴 ＝ 5.08 x 7.62）: 足は X 3.46〜4.16 / Y 2.19〜2.89 に立って下りる。
//      ・胴の真下（|X| ≤ 3.0）に足は無い → 板が胴の底を全面で受けられる
//      ・±Y の壁は足より外（3.15）なので全高で立つ ＝ スイッチは**まっすぐ下から入る**（滑らせない）
//      ・±X の位置決めは足の根元（胴の底から 1.2〜1.8）より上の帯だけ
//    🔴 腕（ねじを受ける肉）は**片側にしか下ろせない**。反対側（world X 11〜17.5）は会話ボタン
//      自身の線 BTN2 が Z 39.7〜47.1 を埋めていて、置くと chk_top に 20.9mm³ 乗る。
//      ⇒ ねじ 2 本とも空いている側へ寄せ、板は反対側へ**片持ち**で伸ばす。
//      片持ちの計算: 押す 2.5N が腕から 7mm 先。曲げ 4.9MPa・たわみ 0.053mm。効かない。
//    ⭐ 刷る向きでは、ポケットは**上に開いた穴**になる。下向きの天井がどこにも出来ないので、
//      割れた原因だった「隙間の支柱」は 1 本も立たない。
BTN_SLOT     = tsw_body() + 0.3;   // 6.3 胴 6.0 ＋ 0.3（PRINT.md の実績「呼び ＋0.3 でジャスト」）
//   ✅ 2026-08-28 実機（試し刷り 1 枚目）: 6.3 に胴 6.0 は「すんなり落ちる。割とそれでもスカスカ」。
//      位置決めは下の板と ±X の帯が持つ設計なので、これ以上は詰めない（詰めると入らない側に倒れる）。
BTN_GUIDE_Z0 = 2.0;                // X の位置決めの帯の下端（胴の底から）
// 🔒 2026-08-28 実機（ユーザー）「深さが足りません。厚みが 3mm ありますが 0.2mm くらい飛び出ています」。
//    ポケットの高さは Z_TSW_TOP − Z_TSW_BOT ＝ tsw_body_h() ＝ 3.000 で、胴 3.0 と**ぴったり同じ**だった。
//    幅は BTN_SLOT で呼び ＋0.3 を取ってあるのに、**深さだけ +0** だった。刷る向きではポケットは
//    上に開いた穴なので、底（＝世界の天井）が硬化で盛れば必ず浅くなる。実機の 0.2 はここ。
//    ⇒ **天井だけ 0.3 上げる。**板（Z_TSW_BOT）は動かさない。
//      🔴 板を下げる直し方は採らない: スイッチの底ごと 0.3 下がって軸も下がり、キャップの遊びが
//         0.3 増える（travel 0.75 に対して大きい）。天井なら底も軸も動かないので代償が無い。
TSW_CL_Z   = 0.3;                  // 胴の上に取る逃げ（呼び ＋0.3・PRINT.md の実績と同じ流儀）
Z_TSW_ROOF = Z_TSW_TOP + TSW_CL_Z; // ポケットの天井（胴の上面 Z_TSW_TOP とは別物。位置決めは胴の底＝板）
BTN_ARM_X0   = 4.5;                // 腕の内側（足の外 4.16 に 0.34 空ける）
// 🔴 2026-08-28 実機（ユーザー）「六角がくずれて穴が開いてる」。
//    ねじの芯 7.0 に対して腕の内側は 4.5。六角の対角の半分は 2.48 なので、内側の壁は
//    **4.5 − (7.0 − 2.48) = 0.02mm** しか無かった（＝壁が無い）。当然抜ける。
//    ⇒ 腕を外へ 0.6 伸ばし（10.4 → 11.0・皿の輪郭の内）、ねじの芯を 7.0 → 7.9 へ逃がす。
//      内側の壁 0.92mm・外側は口として抜くので壁は要らない。
BTN_ARM_X1   = 11.0;               // 腕の外側（ナットを横から差す口が開く所）
BTN_ARM_HY   = 6.9;                // 腕の半分（ねじ ±3.5 ＋ ナット 2.15 ＋ 壁 1.2）
BTN_SCR_X    = 7.9;                // 留めねじの芯（空いている側だけ）
BTN_SCR_Y    = 3.5;                // ねじ 2 本の間隔の半分
BTN_PLATE_T  = 1.5;                // 下から留める板の厚み
BTN_LEGWIN   = [3.1, 4.5];         // 板に開ける足の窓（X）。足 3.46〜4.16 の外へ 0.34 ずつ
module btn_screws() for (sy = [-1, 1]) translate([-BTN_SCR_X, sy * BTN_SCR_Y, 0]) children();
module btn_nut_slot() {
    btn_screws() {
    // 🔴 2026-08-28 実機（ユーザー）「右だけ入らない。完全に柱が邪魔して入らない」。
    //    六角どうしの hull は**幅が一定ではない**（両端が六角の頂点へ細る）うえ、腕の外面は
    //    皿の輪郭で斜めに切ってあるので、口の幅が場所によって 4.3 を下回っていた。
    //    ⇒ hull をやめ、**幅 4.3 × 高さ 1.8 の真っ直ぐな溝**を腕の外まで引く。どこで切っても 4.3 ある。
    // 🔒🔒 2026-08-28 ユーザー裁定「**絶対に広げないでください。**実物も通っていました。
    //    通らなかったのは L 字で邪魔された右側だけ」。
    //    ⇒ **NUT_AF / NUT_T をこの溝のために膨らませてはいけない。**呼び寸法ちょうど（4.3 × 1.8）で正。
    //    🔴 「右が入らない」の原因は溝の寸法ではない。**隣に立っている別の部品**である。
    //       ✅ 2026-08-28 測定（part="chk_self" を足して初めて見えた）: ナットを 0.25mm 刻みで
    //         掃引すると、**片側だけ 28.5012mm³ 塞がる。その全量が ReSpeaker の押さえ
    //         （rsp_press4・前リブ X 31.4〜37.4）**。OLED の L は 0.0000mm³ だった。
    //         もう片側は 0.0000mm³。左右対称な溝の寸法では片側だけにはならない。
    //       ⚠ AI は最初「原因は OLED の L」と書いた。**測る前に書いた。**直す場所は押さえの側。
    //    🔴 AI がここで何度も繰り返した過ち: 掃引して余裕 0.00mm を出し、
    //       「呼び ＋0.3 が実績だから実際には通らない」と一般則で断定した。**実物は通っている。**
    //       「幾何学的には」で始まる推測を、ユーザーの実測の上に置かないこと。
    translate([0, 0, Z_BTN_PAD - NUT_T]) {
        hex_pocket(NUT_T + 0.01);
        translate([-30, -NUT_AF / 2, 0]) cube([30, NUT_AF, NUT_T + 0.01]);
    }
    translate([0, 0, Z_TSW_BOT - BTN_PLATE_T - 1]) cylinder(d = SCR_D, h = Z_BTN_PAD - Z_TSW_BOT + 3, $fn = 24);
    }
}
module btn_socket() {
    ho = BTN_POST_I + BTN_PKT_T;   // 4.8 ポケットの外形の半分
    hy = BTN_SLOT / 2;             // 3.15 胴を受ける穴の半分
    difference() {
        union() {
            translate([0, 0, Z_BTN_PAD]) linear_extrude(IN_Z - Z_BTN_PAD) btn_pad_2d();   // 皿の輪郭 ＋ 壁
            difference() {   // ポケットの天井 ＋ 首の胴（板まで一体）
                translate([-ho, -ho, Z_TSW_ROOF]) cube([ho * 2, ho * 2, BTN_POCKET_TOP - Z_TSW_ROOF]);
                translate([0, 0, Z_TSW_ROOF - 1]) cylinder(d = BTN_HOLE_D, h = BTN_POCKET_TOP - Z_TSW_ROOF + 2, $fn = 32);
            }
            for (sy = [-1, 1]) translate([-ho, sy * hy + (sy < 0 ? -(ho - hy) : 0), Z_TSW_BOT])   // ±Y の壁（全高）
                cube([ho * 2, ho - hy, Z_TSW_ROOF - Z_TSW_BOT]);
            for (sx = [-1, 1]) translate([sx * hy + (sx < 0 ? -(ho - hy) : 0), -ho, Z_TSW_BOT + BTN_GUIDE_Z0])  // ±X の位置決め
                cube([ho - hy, ho * 2, Z_TSW_ROOF - Z_TSW_BOT - BTN_GUIDE_Z0]);
            // 🔴 2026-08-28 ユーザーが刃物状の薄片を丸で指摘。腕を皿の丸い輪郭で切っていたので、
            //    真っ直ぐな溝の横壁が外へ向かって痩せ、x −9.08 で 0 になっていた（「壁 1.05」は
            //    ねじの芯の 1 点の値）。丸い外形に真っ直ぐな溝を切る限り、どこかが刃物になる。
            //    ⇒ **腕は四角**（輪郭で切らない）。外壁 1.25・内壁 0.92 が全長で一定になる。
            //      上端は天板の裏 IN_Z まで（皿の輪郭の外の部分が宙に浮かないように）。
            translate([-BTN_ARM_X1, -BTN_ARM_HY, Z_TSW_BOT])
                cube([BTN_ARM_X1 - BTN_ARM_X0, BTN_ARM_HY * 2, IN_Z - Z_TSW_BOT]);
        }
        btn_nut_slot();
    }
}
// 下から留める板。胴の底を全面で受け、足は 2 つの窓を通す。ねじは空いている側に 2 本
//   🔴 2026-08-28 ユーザー「なぜ天板側に切り込みがあるのに、蓋に切り込みがないんですか？」
//     → いったん皿の輪郭で切って揃えたが、腕を四角にした（刃物の薄片の件）ので、板も同じ四角で揃える。
//   🔴 2026-08-28 板の先 5.0 が BTN2 の線（Z 39.0〜39.7・local x 4.65 から・⚠経路は仮定）に 0.74mm³
//     乗っていた。胴の下（|x| ≤ 3.0）を覆えば板の仕事は済むので、先を 4.4 で止める（線まで 0.25）。
module btn_plate() difference() {
    union() {
        translate([-BTN_ARM_X1, -4.8, Z_TSW_BOT - BTN_PLATE_T]) cube([BTN_ARM_X1 + 4.4, 9.6, BTN_PLATE_T]);
        translate([-BTN_ARM_X1, -BTN_ARM_HY, Z_TSW_BOT - BTN_PLATE_T]) cube([BTN_ARM_X1 - BTN_ARM_X0, BTN_ARM_HY * 2, BTN_PLATE_T]);
    }
    for (sx = [-1, 1]) translate([sx > 0 ? BTN_LEGWIN[0] : -BTN_LEGWIN[1], -3.3, Z_TSW_BOT - BTN_PLATE_T - 1])
        cube([BTN_LEGWIN[1] - BTN_LEGWIN[0], 6.6, BTN_PLATE_T + 2]);   // 足の窓
    btn_screws() translate([0, 0, Z_TSW_BOT - BTN_PLATE_T - 1]) cylinder(d = SCR_D, h = BTN_PLATE_T + 2, $fn = 24);
    // 🔒 2026-08-28 ユーザー「このねじ止め部分のパーツなんですが、羊羹の分けずってあるんですか？
    //    削ってないですよね？ってことは本番用とテスト用が別物ってことですよね。困ります」→ そのとおりだった。
    //    ✅ 測定: 板は羊羹（ReSpeaker の前リブ）に **6.191mm³ 食い込んでいた**（太らせる前も 1.524mm³）。
    //    🔴 一度も検査に出ていなかった。板は**別に刷る部品**なので innards4() に無く chk_top の対象外、
    //       chk_self の TOPBITS にも入れていなかった。しかも print_btntest には羊羹が入らないので、
    //       **試し刷りでは入り、本番では入らない**という食い違いになっていた。
    //    ⇒ 羊羹の footprint を、逃げ 0.3 を付けて板から欠く。
    //      🔴 数字は羊羹（RIB4_X / RIB4_W）から引く。板の中に生の数字を書かない。羊羹が動けば逃げも動く。
    //      （モジュールの中なので、後で定義される RIB4_X を参照しても解決する）
    let (rx0 = RIB4_X - BTN4[0], rx1 = RIB4_X + RIB4_W - BTN4[0],
         ry0 = RSP_BD_Y0 - 0.5 - BTN4[1], ry1 = RSP_BD_Y0 - 0.5 + respeaker_T() + 1.0 - BTN4[1], cl = 0.3)
        translate([-rx1 - cl, -ry1 - cl, Z_TSW_BOT - BTN_PLATE_T - 1])
            cube([(rx1 - rx0) + cl * 2, (ry1 - ry0) + cl * 2 + 10, BTN_PLATE_T + 2]);   // +Y 側は板の外まで抜く
}

module button_cap() {
    z_head = Z_TOP - (BTN_H - BTN_OUT); z_top = z_head + BTN_H;
    difference() {
        hull() {
            translate([-BTN_L / 2, -BTN_W / 2, z_head]) spk_obround(BTN_L, BTN_W, BTN_H - 0.8);
            translate([-(BTN_L - 1.6) / 2, -(BTN_W - 1.6) / 2, z_top - 0.01]) spk_obround(BTN_L - 1.6, BTN_W - 1.6, 0.01);
        }
        difference() {
            translate([-(BTN_L - BTN_WALL * 2) / 2, -(BTN_W - BTN_WALL * 2) / 2, z_head - 0.01]) spk_obround(BTN_L - BTN_WALL * 2, BTN_W - BTN_WALL * 2, BTN_H - BTN_WALL);
            cylinder(d = BTN_PLG_D + 2.4, h = 100);
        }
    }
    translate([0, 0, Z_NECK0]) cylinder(d = BTN_PLG_D, h = z_head - Z_NECK0 + 0.01, $fn = 32);
    translate([0, 0, Z_NECK1]) cylinder(d = BTN_NECK_D, h = Z_NECK0 - Z_NECK1 + 0.01, $fn = 32);
    translate([0, 0, Z_TIP])   cylinder(d = BTN_PLG_D, h = BTN_LIP_H + 0.01, $fn = 32);
}
module button_clip() { linear_extrude(BTN_CLIP_T) difference() { circle(d = BTN_CLIP_D, $fn = 48); circle(d = BTN_NECK_D + 0.15, $fn = 32); polygon([[-1.45, -1.0], [1.45, -1.0], [2.3, -BTN_CLIP_D], [-2.3, -BTN_CLIP_D]]); } }

// ============================================================
// 天板に彫る欠き（2026-08-28 に case_v4.scad の top_v4() から移設）
// ============================================================
// 🔴 移設前は world の生の数字（9.3 / 17.8 / 45.9 / 6.7 / 10.0 / 12.4）で top_v4() の
//    difference() の中に直書きされていた。BTN4 を動かしても付いてこなかった。
//    ここでは **BTN4 を原点にした相対値**でしか書かない。world へ直す関数と、検証済みの
//    絶対値を守る assert は case_v4.scad 側（つまみの k4x0() と同じ置き方）。
//
// ① INA の線を逃がす縦の溝（受けの上の角・幅 5）
//   🔒 2026-08-26 INA の口が直立てになり、一番手前のピン（Y 19.87）が会話ボタンの受け（X 9.5〜37.4・
//     Y 6.8〜21.8・Z 39〜48.4）の真下に来た。口の頭 46.0 と受けの底 47.1 の間は 1.1 しか無く線（1.5）が通らない。
//     ⇒ 受けの**上の角**に幅 5 の縦の溝を彫って、線を +Y へ逃がす（下から開いた溝なのでブリッジは要らない）。
//   🔴 2026-08-26 初版は高さ 3.0（Z 45.9〜48.9）で切って**天板に 0.446 食い込み**、会話ボタンの皿の底
//     （Z 48.454〜48.704 の 0.25 しか無い）を抜いて表に穴が開いた（ユーザーが CAD で発見）。
//     **天板の内面 IN_Z で止める。**線は Z 46.05〜47.55 にしか居ないので、これで足りる。
// 🔴 2026-08-28 **この 2 つだけは BTN4 に付いて回ってはいけない。**
//    溝は INA の線（world Y 19.87 / 24.14）、角落としは OLED の L（world Y 6.7〜10.0）のための逃げで、
//    相手は動いていない。前列を +2.5 動かしたとき、相対のままだったので逃げが相手から 2.5 ずれ、
//    線が受けの板の下に 1.342mm³ 入った。⇒ **world 位置を保つよう dy を差し引く。**
//    相対にするのは「ボタン自身の形」だけ。外の物のための逃げは相手に釘付けにする。
BTN_GRV_DX = -12.700;                  // world  9.3
BTN_GRV_DY =   3.500 - BTN_ROW_DY;     // world 17.8（前列を動かしても INA の線に付いていく）
BTN_GRV_Z  =  45.900;   // 🔒 world Z。線が Z 46.05〜47.55 に居るので、その下から掘り始める
BTN_GRV_W  =   5.000;
BTN_GRV_D  =   4.800;
// ② OLED の L のナットのための角落とし
//   🔴 2026-08-26 T-3: OLED の左の L（X 7〜13・裏面 Y 6.6）のポケットへナット（二面幅 4.3・厚み 1.6）を
//     後ろから差す空きが、受けの前面 Y 6.8 に塞がれて 0.19mm しか無かった。ナットの上の角
//     （X 9.5〜12.15・Z 47.1〜48.25）が受けの中に入る。⇒ 受けの**手前左の角**を落とす。
//     タクトの胴は X 19〜25・Y 11.3〜17.3、ポケットの壁は X 17.2 から。ここは板の余肉しかない。
//     天板の内面 IN_Z で止める（① と同じ理由。ここを越えると会話ボタンの皿の底を抜く）。
//     X も 12.4 で止める。皿（へこみ）の縁が X 12.4。皿の底の肉 1.6 は、天板の残り 0.25 と
//     **受けの板 1.35 の合わせ**で出来ているので、皿の下の受けを削ると 0.25 だけになる。
//     だから皿の footprint（X 12.4〜31.6・Y 7.7〜20.9）には掛けない。ナットは X 12.15 までなので足りる。
BTN_CNR_DX0 = -12.700;                 // world  9.3
BTN_CNR_DX1 =  -9.600;                 // world 12.4
BTN_CNR_DY0 =  -7.600 - BTN_ROW_DY;    // world  6.7（OLED の L に釘付け）
BTN_CNR_DY1 =  -4.300 - BTN_ROW_DY;    // world 10.0（同上）
// world へ直す用（case_v4.scad の assert が使う）
function btn_grv_dx()  = BTN_GRV_DX;
function btn_grv_dy()  = BTN_GRV_DY;
function btn_grv_z()   = BTN_GRV_Z;
function btn_cnr_dx0() = BTN_CNR_DX0;
function btn_cnr_dx1() = BTN_CNR_DX1;
function btn_cnr_dy0() = BTN_CNR_DY0;
function btn_cnr_dy1() = BTN_CNR_DY1;

// ---- 置く道具。天板は translate(BTN4) で呼ぶだけにする（つまみの knob_station_* と同じ形）----
//   タクトと同じ 180°（コネクタ側の向き）は**ボタン自身の都合**なので、ここで持つ
module btn_station_add() rotate([0, 0, 180]) btn_socket();
module btn_station_cut() {
    // 皿・縁の面取り・首の穴（v3 と同じ形）
    translate([-BTN_DISH_L / 2, -BTN_DISH_W / 2, Z_BTN_DISH]) spk_obround(BTN_DISH_L, BTN_DISH_W, BTN_DISH_T + 1);
    translate([0, 0, Z_TOP - 0.3]) hull() {
        translate([-BTN_DISH_L / 2, -BTN_DISH_W / 2, 0]) spk_obround(BTN_DISH_L, BTN_DISH_W, 0.01);
        translate([-BTN_DISH_L / 2 - 0.3, -BTN_DISH_W / 2 - 0.3, 0.3]) spk_obround(BTN_DISH_L + 0.6, BTN_DISH_W + 0.6, 0.01);
    }
    translate([0, 0, Z_BTN_PAD - 1]) cylinder(d = BTN_HOLE_D, h = BTN_PAD_T + 2, $fn = 32);
    // ① INA の線の溝
    translate([BTN_GRV_DX, BTN_GRV_DY, BTN_GRV_Z]) cube([BTN_GRV_W, BTN_GRV_D, IN_Z - BTN_GRV_Z]);
    // ② OLED の L のナットのための角落とし
    translate([BTN_CNR_DX0, BTN_CNR_DY0, Z_BTN_PAD - 0.01])
        cube([BTN_CNR_DX1 - BTN_CNR_DX0, BTN_CNR_DY1 - BTN_CNR_DY0, IN_Z - Z_BTN_PAD + 0.01]);
}

// ============================================================
// 単体で開いたときの絵（組んだ姿）
// ============================================================
// 🔴 `include` した側では出さない。_v4_core.scad が下の BTN_SOLO を false にする。
//    OpenSCAD は同じ scope で**最後の代入が勝つ**ので、読み込まれた側では false になる。
//    絵は原点＝ボタンの芯（world では BTN4）。Z は world のまま（Z_TSW_BOT 39.65 〜 Z_TOP 50.95）。
BTN_SOLO = true;
if (BTN_SOLO) {
    color("#c9d0d8") btn_station_add();                                    // 受け（天板の裏に立つ）
    color("#8fb4d9") rotate([0, 0, 180]) btn_plate();                      // 下から留める板
    color("#d8dde3") rotate([0, 0, 180]) button_cap();                     // 押す傘
    color("#2b2b2b") translate([0, 0, Z_TSW_BOT]) rotate([0, 0, 180]) tactswitch();   // タクトスイッチ
    color("#b0b0b0") rotate([0, 0, 180]) btn_screws()                      // 横から差すナット 2 個
        translate([0, 0, Z_BTN_PAD - NUT_T]) cylinder(d = NUT_AF / cos(30), h = NUT_T, $fn = 6);
    color("#e08a3c") rotate([0, 0, 180]) btn_screws()                      // 下から入れるビス 2 本
        translate([0, 0, Z_TSW_BOT - BTN_PLATE_T - 1.4]) { cylinder(d = 2.0, h = 6, $fn = 20); cylinder(d = 3.8, h = 1.4, $fn = 24); }
}
