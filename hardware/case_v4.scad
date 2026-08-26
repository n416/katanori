include <_v4_core.scad>
// ============================================================
// 📦 v4 の外皮とボス（2026-08-25）
//   芯（_v4_core.scad: 固定群＋自由な部品＋線 17 束）に合わせて描く従属変数の皮。
//   板の構造・丸みの持ち主・ベベル・継ぎ目 45°・貫通＋ナットは v3 の規則（CASE-V3.md §4）を引き継ぐ。
//   v3 からの形の差分（CASE-V4.md §4 ①〜③）:
//     ① 右壁: XIAO USB-C の口は ✅ 正しい位置（XIAO_PORT_C）＋ 🔒 局所薄肉 0.8（2026-08-25 ユーザー）
//     ② 天面: ReSpeaker の前リブは X 31.4〜37.4（⚠ 仮決め・CASE-V4 §4）。右の腕はスピーカー移動で
//        v3 の X 69.5〜74.2 が真下になったため X 50.0〜54.7 へ（⚠ AI 仮: OLED の線の帯 48.1 とつまみの島 57.2 の隙間）
//     ③ PowerBoost の壁の機構（ダボ・唇・フック・KNOB_TRIM・棚）は全部撤去（PB は電池の上へ移った）
//   充電口はハッチ（Type-C 基板の鼻先が 🔒 ハッチ内面に付くため）。
//   実行例: openscad --backend=manifold -o x.stl -D 'part="chk_top"' hardware/case_v4.scad
// ============================================================
include <case_v4_shutter.scad>   // 電池の入れ替え口（後ろ抜き・v3 の蓋の型）
W = "none";      // _v4_core の内部スイッチ（芯だけの検査 deskseat/batchk 等はあちらの W で。皮はこの part で）
// ---- part の一覧（v3 と同じ流儀・2026-08-25 ユーザー「V3 と同じ part を」で V/P4 を廃止）----
//   絵     : look（組んだ全体）/ inside（OPEN の板を外して中身）/ explode（分解・組む向き）
//   板     : p_floor p_lwall p_rwall p_top p_front p_hatch p_shutter p_lock p_tail（印刷部品・角丸込み）
//            bridge（ブリッジ＋電池・電流計・PowerBoost・左右の壁・結束バンド。🔒 単体では見えないのでこの一式で出す）
//   刷る向き: print_floor 〜 print_hatch print_shutter print_lock print_tail（外面を下に・底 Z0）
//   静止   : chk_floor chk_lwall chk_rwall chk_top chk_front chk_hatch（板 ↔ 中身＋他の板）/ chk_all（皮全部 ↔ 中身）
//            chk_top_spk（天板 ↔ SPK_LIFT で持ち上げたスピーカー。枠ごと板に入るので専用に見張る）
//            —— **全部 0 が正**（押し代は除外済み）。chk_press だけは **≈6mm3 が正**（ReSpeaker の押さえが板に届いている証拠）
//   動き   : close_lwall close_rwall（壁を上から降ろす）/ close_top（天面一式を降ろす）/ close_front（前から差す）/
//            close_hatch（蓋・トグルごと閉じる）/ close_desk（ブリッジを降ろす＝core の deskseat）
//   線     : chk_wire（WP で 1 束に絞れる・束 ↔ 部品と皮）/ chk_wire_w（束 ↔ 他の束＋電源系）/ chk_wire_pwr（電源系 7 本）
//   充電基板: chk_tc（Type-C の受け＋押さえ ↔ 基板と周り。**0 が正**）
//   電池   : chk_shut_slide（蓋を下へずらす）/ chk_shut_out（蓋を抜く）/ chk_swap（電池を後ろへ抜く・v3 と同名）
part = "t1";
WP = "";         // chk_wire 系で束を 1 つに: xiao / oled / as5600 / btn2 / phin / phout / ina / tgl / reed / chg（"" で全部）

// ---- v4 の配置（芯と同じ式。数字を増やさない） ----
KNOB4 = [KNOB_AT[0] + 1.5, KNOB_AT[1] + 7, KNOB_AT[2]];   // 🔒 2026-08-25 ユーザー「つまみも 2mm 移動」で +5 → +7            // 🔒 つまみ +1.5 右・+5 後ろ（2026-08-25「少しだけ内側へ」で +3 → +1.5・⚠ 量は仮）
BTN4  = [22, 22.3 - 0.5 - spk_w() / 2];                            // 会話ボタン（core と同じ式・[22, 14.3]）
SPK4  = [KNOB_AT[0] + 1.5, 22.3 - 0.5 - spk_w() / 2];              // スピーカーの中心（core と同じ式）
SPK4_X = SPK4[0] - SPK_L / 2; SPK4_Y = SPK4[1] - SPK_W / 2;
HUB_HOLES4 = [for (h = HUB_HOLES) [h[0] + HUB_DX, h[1] + HUB_DY]]; // ハブのビス穴（HUB_DY=4 に追従）
RIB4_X = 31.4; RIB4_W = 6.0;                                       // ⚠ 前リブの仮決め（CASE-V4 §4）
ARM4_X0 = 50.0; ARM4_X1 = 54.7;                                    // ⚠ 腕の移設（上のヘッダ参照）

// ---- ボス（v3 の型）----
//   天面: 後ろの柱 2（BOSSES）＋ 前は耳兼用の柱 2（ear_col）。床: 前 2 本は v3 のまま。
//   🔒 2026-08-25 後ろの床ビスを**復活**（ユーザー「無いと落下でバラける」）: どちらも L 形＝ハブの角を欠いて立てる。
//   右: 壁 84.354 で真っ直ぐな 7 幅が取れない → X 77.4〜84.354 からハブの柱の角（X<80.8 ∩ Y<68.6）を欠く。ナット [82.0, 69.5]
//   左: 充電基板を +11.5 上げて角を空けた（🔒 同日ユーザー）→ X 1.694〜7.7 からハブの柱の角（X>5.2 ∩ Y<68.4）を欠く。ナット [4.4, 69.5]
//   ⚠ どちらもナットの六角の角がハブ側の欠きに小さく開く（開口はナットの二面幅より狭く抜けない）
module bottom_boss_br() difference() {
    color("#b6c0cc") translate([77.4, 65, 0]) cube([IN_X - 77.4, 7.0, BOSS_B_H]);
    translate([77.4 - 1, 65 - 1, -1]) cube([80.8 - 77.4 + 1, 68.6 - 65 + 1, BOSS_B_H + 2]);
    translate([82.0, 69.5, BOSS_B_H - NUT_T]) rotate([0, 0, 30]) hex_pocket(NUT_T + 1);
    translate([82.0, 69.5, -1]) cylinder(d = SCR_D, h = BOSS_B_H + 2, $fn = 24);
}
module bottom_boss_bl() difference() {
    color("#b6c0cc") translate([LW_X, 65, 0]) cube([7.7 - LW_X, 7.0, BOSS_B_H]);   // 右端 7.7 ＝ 床の爪の帯（X 8〜）の 0.3 手前
    translate([5.2, 65 - 1, -1]) cube([7.7 - 5.2 + 1, 68.4 - 65 + 1, BOSS_B_H + 2]);   // ハブの柱（φ7・X 5.5〜）から 0.3
    translate([4.4, 69.5, BOSS_B_H - NUT_T]) rotate([0, 0, 30]) hex_pocket(NUT_T + 1);
    translate([4.4, 69.5, -1]) cylinder(d = SCR_D, h = BOSS_B_H + 2, $fn = 24);
}
V4_FLOOR_SCREWS = [[0.7 + BOSS / 2, 2 + BOSS_B_DY_F / 2], [78.3 + BOSS / 2, 2 + BOSS_B_DY_F / 2], [82.0, 69.5]];   // 前 2 本は +2（柱と一緒に）   // 床の裏からのビス 3 本（前 2＋復活した後ろ右。後ろ左は ⬜ 保留）   // 床の裏からのビス 3 本（前 2＋復活した後ろ右。後ろ左は ⬜ 保留）

// ---- 充電（Type-C）基板の受け（🔒 2026-08-25 ユーザー「この絵で良いと思いますよ」で形は検収済み）----
//   ⚠ 検収されたのは**形**。現物が未注文なので、②③④ の Y の位置は板が届いたら取り直しになる
//   板は 📄 秋月 [115426] の寸法図で 20 × 15 × 1.6。左壁の内面にベタ付けで立ち、世界座標は
//   **X 1.694〜3.294（＝LW_X＋1.6）・Y 57.4〜72.4・Z 0.5〜20.5**（tcb_v4 を単体 STL に出した bbox から）。
//   Y 48.669 まで前へ出ているのは板ではなく**デュポンのハウジング 4 個**（X 4.524〜7.065・Z は 4 つの帯）。
//   受けは 4 つで持つ:
//     ① 底の座    板の下端 0.5 を面で受ける（口の Z 中心 10.5 が下がらないよう、床から 0.5 上げた面に座らせる）
//     ② 前の当て  板の前縁の 0.25 手前に立つ壁。**ケーブルを挿す力（−Y）を受けるのはここだけ**
//     ③ 前の返し  ②から +Y へ折れた L の腕。板の表を全高で押さえる（＝倒れ止め・前）
//     ④ 後ろの控え ピン列の後端 61.21 と コネクタ胴の前端 65.85 の隙間に立つ全高の柱（＝倒れ止め・後ろ）
//   Z の抜けは受けでは止まらない。ブリッジの帯の裏に付けた押さえ（_v4_core の brg_tc_press）が止める。
//   −X（壁側）は左の壁の内面そのもの。🔴 このため **Type-C 基板は左右の壁を降ろした後に立てる**（組む順が変わる）。
//   逃げの実績: ③ の表 4.25 ↔ ハウジング 4.524 = 0.274 / ③ の後端 58.35 ↔ ピン列 58.67 = 0.32 /
//               ④ の後端 65.5 ↔ コネクタ胴 65.85 = 0.35 / ⑤ の右 5.9 ↔ ハブの左端 6.002 = 0.102
TC4_XF  = LW_X + 1.6;         // 板の表（3.294）
TC4_Y0  = 57.4; TC4_Y1 = 72.4;   // 板の前縁・後縁（後縁はハッチの内面 IN_Y に 0.4 入る）
TC4_ZT  = 20.5;               // 板の上端
TC4_CL  = 0.25;               // 板と受けの隙間
TC4_GX0 = TC4_XF + TC4_CL;    // 返し・控えの内面（3.544）
TC4_GX1 = 4.25;               // 返しの表（ハウジング 4.524 へ 0.274）
TC4_BX1 = 4.70;               // 控えの表
TC4_FY1 = TC4_Y0 - TC4_CL;    // 前の当ての後ろ面（57.15）
TC4_FY0 = TC4_FY1 - 1.2;      // 前の当ての前面（55.95）
module tc_seat4() {
    // ① 底の座（板の下端 Z 0.5 を受ける。床の後端 IN_Y までで切る）
    translate([LW_X, TC4_FY0, 0]) cube([3.9 - LW_X, IN_Y - TC4_FY0, 0.5]);
    // ② 前の当て（−Y を止める壁・全高）
    translate([LW_X, TC4_FY0, 0]) cube([TC4_GX1 - LW_X, 1.2, TC4_ZT]);
    // ③ 前の返し（L の腕・板の表を全高で押さえる）
    translate([TC4_GX0, TC4_FY1, 0]) cube([TC4_GX1 - TC4_GX0, 58.35 - TC4_FY1, TC4_ZT]);
    // ④ 後ろの控え（ピン列とコネクタ胴の間・全高）
    translate([TC4_GX0, 62.0, 0]) cube([TC4_BX1 - TC4_GX0, 65.5 - 62.0, TC4_ZT]);
    // ⑤ 補強の三角（② は 1.2 厚で 20.5 立つので前へ、④ は右へ。どちらも Z の途中で消える）
    translate([LW_X, 0, 0]) rotate([90, 0, 90]) linear_extrude(TC4_GX1 - LW_X)
        polygon([[TC4_FY0 - 3.75, 0], [TC4_FY0, 0], [TC4_FY0, 12.0]]);
    translate([0, 65.5, 0]) rotate([90, 0, 0]) linear_extrude(65.5 - 62.0)
        polygon([[TC4_BX1, 0], [5.9, 0], [TC4_BX1, 10.0]]);
}

// ---- 床 ----
//   v3 の床（まな板）と同じ形。違いは ① ハブのビス穴と柱が +4（HUB_DY）② ブリッジの前の脚の受け溝 ③ 後ろ右の床ビスの位置
LEG4_W = lipo_size()[1] - 2 * (LEG_X0 - BAT_X0);   // 脚の幅 23（_v4_core の brg_v4 と同じ式）
module floor_v4() {
    difference() {
        union() {
            color("#9aa5b1") translate([LW_X - WALL, FY_IN, -FLOOR_T]) cube([IN_X + 2 * WALL - LW_X, IN_Y - FY_IN, FLOOR_T]);   // 前端はフロント板の内面まで（板を後ろへ寄せた分だけ詰める）
            color("#9aa5b1") for (h = HUB_HOLES4) translate([h[0], h[1], 0]) cylinder(d = HUB_POST_D, h = BOARD_Z, $fn = 32);
            // ReSpeaker の溝（v3 と同じ）
            color("#9aa5b1") translate([RSP_RIB_X0, RSP_SLOT_Y0, 0]) cube([RSP_RIB_X1 - RSP_RIB_X0, RSP_SLOT_Y1 - RSP_SLOT_Y0, RSP_Z]);
            color("#9aa5b1") translate([RSP_RIB_X0, RSP_BD_Y0 - 2, 0]) cube([RSP_RIB_X1 - RSP_RIB_X0, 2 - RSP_SLOT_CL, RSP_Z + 3]);
            color("#9aa5b1") for (g = [[RSP_X, HUB_AT[0] - 0.3 - RSP_X, 5.0], [80, 4, RSP_Z + 4]])
                translate([g[0], RSP_BD_Y1 + 0.3, 0]) cube([g[1], HUB_Y0 - 0.3 - (RSP_BD_Y1 + 0.3), g[2]]);
            // 🔴 2026-08-25 振れ止めは左右とも壁の役目に（板の端 ↔ 内面 0.33 ずつ）。リブは廃止
            // OLED の下辺の後ろのリブ（v3 と同じ・フィルムの切り欠きは開ける）
            color("#9aa5b1") difference() {
                translate([OLED_X0 + 2, OLED_RIB_Y0, 0]) cube([oled_l() - 4, OLED_RIB_T, OLED_RIB_H]);
                translate([OLED_X0 + oled_l() / 2 - 23 / 2 - 1, OLED_RIB_Y0 - 1, -1]) cube([23 + 2, OLED_RIB_T + 2, OLED_RIB_H + 2]);
            }
            // ハッチの爪の帯。🔴 v3 の Y 66〜のままだとハブ（+4）の半田面の予約（裏 2mm・Y 〜67.9）に 221mm³ 入る
            //    → 前縁をハブの後端 + 0.5 ＝ Y 68.4 へ。バーは Y 68.4〜70 に痩せるが、爪の唇（〜Y 68.2）はまだ 1.6 掛かる。
            //    ⚠ バーの前面とハブの半田面の予約の隙間は 0.1（予約は包絡。実際の足はまばら）
            color("#9aa5b1") translate([RSP_RIB_X0, HUB_Y0 + HUB_DY + HUB_W + 0.5, 0]) cube([RSP_RIB_X1 - RSP_RIB_X0, IN_Y - (HUB_Y0 + HUB_DY + HUB_W + 0.5), CLAW_STRIP_H]);
            // 充電（Type-C）基板の受け 🔒 2026-08-25（形はユーザー検収済み）
            //   🔴 ここには「前の振れ止めリブ」（X LW_X〜4.694・Y 47.7〜48.4・Z 0〜3.0）が立っていたが、
            //      板の前縁を 48.67 と読み違えたもので、実際の板は Y 57.4〜。リブは何にも触っていなかったので廃止。
            color("#9aa5b1") tc_seat4();
            // ブリッジの前の脚（1 枚板・厚み 2.0）の受け溝 ⚠ AI 仮（ReSpeaker の「溝＋押さえ」の型の写し。Z の留めは無し・⬜）
            //   脚 X 21.5〜44.5・Y 12.9〜14.9。溝は ±0.25、壁は前 1.6・後ろ 0.45（🔴 ハブの前縁 15.9（⚠ HUB_DY=4 仮）から 0.3 逃げた残り）
            color("#9aa5b1") difference() {
                translate([LEG_X0 - 1.5, 11.05, 0]) cube([LEG4_W + 3.0, 15.6 - 11.05, 2.5]);
                translate([LEG_X0 - 0.5, 12.65, -1]) cube([LEG4_W + 1.0, 2.5, 4.5]);
            }
        }
        // ハブのビス（M3）: 通し穴＋裏のザグリ
        for (h = HUB_HOLES4) translate([h[0], h[1], 0]) {
            translate([0, 0, -FLOOR_T - 1]) cylinder(d = M3_CLEAR, h = FLOOR_T + BOARD_Z + 2, $fn = 24);
            translate([0, 0, -FLOOR_T - 1]) cylinder(d = M3_HEAD_D, h = M3_HEAD_H + 1, $fn = 32);
        }
        // 壁のビス（M2）: 通し穴＋裏のザグリ
        for (c = V4_FLOOR_SCREWS) translate([c[0], c[1], 0]) {
            translate([0, 0, -FLOOR_T - 1]) cylinder(d = SCR_D, h = FLOOR_T + 2, $fn = 24);
            translate([0, 0, -FLOOR_T - 1]) cylinder(d = SCR_CB, h = SCR_CBT + 1, $fn = 32);
        }
        // 爪のポケット（v3 と同じ）
        for (cx = CLAW_X) {
            translate([cx[0], CLAW_STRIP_Y0 + 1.0, 0.3]) cube([cx[1] - cx[0], IN_Y - CLAW_STRIP_Y0, CLAW_BAR_Z0 - 0.3]);
            translate([cx[0], CLAW_BAR_Y1, CLAW_BAR_Z0 - 0.01]) cube([cx[1] - cx[0], IN_Y - CLAW_BAR_Y1 + 1, CLAW_STRIP_H]);
        }
    }
}

// ---- 左の壁 ----
//   v4 は素の板＋ボスだけ（電池の蓋・充電口・棚は無い）。Type-C 基板が内面にベタ付くので前の振れ止めリブだけ立てる。
//   ⬜ Type-C 基板の保持（X に倒れる向き・Z の抜け）と、ブリッジの帯の左端の受けは未設計（ユーザー裁可待ち。
//      帯の真下 X 0〜5.4 は Type-C 基板（Z 〜20.5・⚠ 未実測）が居るため、v3 の棚（ナット入り LEDGE）が素直に立たない）
//   🔒 2026-08-25 ユーザー「左壁も右と同じだけ詰められる筈」: 内面 LW_X 1.694（板の左端 2.024 − 0.33）。
//   ついでの発見（初出）: **左壁は ReSpeaker のイヤホンジャック（J1）の口を塞いでいた**。壁が寄った結果、
//   筒の先（X 0.424）が外面（-0.306）の 0.73 裏に来る ＝ ハッチの充電口と同じ 1 段の口が開けられる → 開けた。
//   ⚠ J1 の模型は 📄 STEP の角箱（先端の断面 Y 10.0〜15.0 × Z 5.9〜13.3）。実物の筒は丸のはずなので
//     口は包絡＋0.6 の仮。⬜ 実測（筒の φ と中心）で丸口に直す。印は無し（印の絵はユーザーの SVG 規則）。
//   上端の小さい張り出し（X 1.14〜・Z 34.7〜35.9・⚠ 正体未確認）は盲ポケット。
//   🔒 ユーザー「（ReSpeaker 側の）USB ポートは出さなくていい」: 模型では左端に USB の張り出しは無い（⚠ 実物照合待ち。
//     張り出しがあれば盲ポケットで受ける）
//   📄 2026-08-25 STEP の実体（ユーザー「大穴あけおって」→ 包絡の窓をやめ、筒の丸に合わせた口へ）:
//     筒 = φ5.45・軸 世界 [Y 12.52, Z 9.00]・先端 X 0.424（外面 -0.306 の 0.73 裏）
//     USB1（ReSpeaker 自身の USB-C・🔒 出さない）= 殻 8.94×3.16・Y 10.27〜13.43・Z 25.79〜34.73・X 1.14 まで
//     J1 の金属カバー = Y 13.17〜17.56・Z 6.15〜11.40・X 1.32 まで
LJACK_C = [12.52, 9.00];   // 口の中心 [Y, Z]（筒の軸・📄）
LJACK_D = 5.45 + 0.6;      // 口の径（筒 ＋ 0.6）
module lwall_port_cut4() {
    translate([LW_X - WALL - 1, LJACK_C[0], LJACK_C[1]]) rotate([0, 90, 0]) cylinder(d = LJACK_D, h = WALL + 2, $fn = 48);   // 丸口（貫通）
    hull() {                                                                            // 外面のベベル
        translate([LW_X - WALL + PORT_BEV, LJACK_C[0], LJACK_C[1]]) rotate([0, 90, 0]) cylinder(d = LJACK_D, h = 0.01, $fn = 48);
        translate([LW_X - WALL - 1.0, LJACK_C[0], LJACK_C[1]]) rotate([0, 90, 0]) cylinder(d = LJACK_D + 2 * (PORT_BEV + 1.0), h = 0.01, $fn = 48);
    }
    // 壁を降ろす道①: 筒の通り道（内面側から X 0.274 まで・筒の頭 11.73 の上まで。外の皮 0.58 ⚠）
    translate([0.274, 9.19, -0.5]) cube([LW_X - 0.274 + 0.01, 15.85 - 9.19, 12.2 + 0.5]);
    // 道②: J1 の金属カバー（X 1.17 まで・皮 1.47）
    translate([1.17, 12.87, -0.5]) cube([LW_X - 1.17 + 0.01, 17.87 - 12.87, 11.9 + 0.5]);
    // 盲ポケット＋道③: USB1（🔒 出さない・X 0.99 まで・皮 1.29）
    translate([0.99, 9.97, -0.5]) cube([LW_X - 0.99 + 0.01, 13.73 - 9.97, 35.03 + 0.5]);
}
module lwall_v4() {
    difference() {
        union() {
            color("#b6c0cc") translate([LW_X - WALL, FY_IN, 0]) cube([WALL, IN_Y - FY_IN, IN_Z]);
            brg_ledges(-1);   // ブリッジを留める棚（Y 30.5〜36.5・ナット入り・_v4_core の「箱への固定」）
            brg_ledge_up();   // 3 点目の棚（Y 63.2〜69.2・帯の左端を**上から**留める・_v4_core の BLU_*）
            for (b = BOSSES) if (b[0] < IN_X / 2) top_boss(b, BOSS_H);
            ear_col(EAR_X[0][0], EAR_X[0][1]);
            color("#b6c0cc") difference() {
                bottom_boss([0.7, 2]);   // 🔒 前の床ビスを +2（ハッチ方向）
                // 🔴 2026-08-25 壁は上から降りる。ボスの XY の影に居る物は、静止で当たっていなくても降りる間に通る
                //    （下の肉も上へ抜けていくときに通る）。ReSpeaker の前面の部品（X 6.21〜7.70・Y 6.91〜7.50・Z 17.75〜21.25）
                //    の分、後ろ右の角を**全高で**欠く（±0.3）。ナットの六角は Y 6.61 の高さでは X 5.61 までなので掛からない
                translate([5.91, 6.61, -1]) cube([7.7 - 5.91 + 1, 7.5 - 6.61 + 1, BOSS_B_H + 2]);
            }   // 🔴 [LW_X] 起点だと OLED の左端（8.002）に届く → 右端を 7.7（OLED − 0.3）に
            // bottom_boss_bl();   // ⬜ 後ろ左は保留: 立てるには充電基板を帯の上（口 Z≈33.5）へ上げる必要がある（帯は切らない 🔒）。判断待ち
        }
        lwall_port_cut4();
    }
}

// ---- 右の壁 ----
//   🔒 2026-08-25 ユーザー「ハッチで出来る事が出来ない訳がない。壁の移動が足りないだけ」:
//   壁の内面 84.354（殻の面 − 1.2・case_base の RIGHT_CL）。殻（84.024〜85.554）は壁の口を貫通し、
//   **口の面は外面 86.354 の 0.8 裏** ＝ ハッチの充電口と同じ「口（殻の大きさ）＋ベベルだけ」の 1 段。
//   すり鉢もモールドの座も不要になった（プラグのモールドは外面の外で止まる）。
//   壁を上から降ろすため、口の下は内面側だけ殻の通り道（〜85.704・皮 0.65）を抜く（v2/v3 の U 字の増し壁と同じ理屈）。
//   🔴 経緯: 0.45（2.45 埋没）→ 0.15＋すり鉢（まだ 2 段・ユーザー「幻か？」）→ これ。
//   🔴 後ろ右の床ボスは幅 3.55 になりナットが入らないため廃止（後ろ左を v3 で捨てたのと同じ判断。
//      後ろの床はハッチの爪 2 つとトグルのナットが持つ）⚠ ユーザー検収待ち
module rwall_port_cut4() {
    c = XIAO_PORT_C;
    translate([0, c[0], c[1]]) rotate([90, 0, 90]) {
        translate([0, 0, IN_X - 1]) linear_extrude(WALL + 2) port_rrect(USBC_PORT, USBC_PORT_R);   // 口（殻の大きさ・貫通）
        hull() {                                                                                   // 外面のベベル
            translate([0, 0, IN_X + WALL - PORT_BEV]) linear_extrude(0.01) port_rrect(USBC_PORT, USBC_PORT_R);
            translate([0, 0, IN_X + WALL + 1.0]) linear_extrude(0.01) port_rrect(USBC_PORT, USBC_PORT_R, PORT_BEV + 1.0);
        }
    }
    // 壁を降ろす道: 口の下を内面から殻の通り道（殻の面 ＋ 0.15 ＝ 85.704）まで抜く。外に皮 0.65 残る
    translate([IN_X - 0.01, c[0] - USBC_PORT[0] / 2, -0.5]) cube([85.704 - IN_X + 0.01, USBC_PORT[0], c[1] + 0.5]);
    if (ICONS_ON) wall_icon_x([c[0] + USBC_PORT[0] / 2 + PORT_BEV + ICON_GAP + ICON_H / 2, c[1]]) icon_svg();   // 印（口の右）
}
module rwall_v4() {
    difference() {
        union() {
            color("#b6c0cc") translate([IN_X, FY_IN, 0]) cube([WALL, IN_Y - FY_IN, IN_Z]);
            brg_ledges(1);    // ブリッジを留める棚 2 つ（Y 30.0〜36.0 と 56.9〜62.9・ナット入り）
            for (b = BOSSES) if (b[0] > IN_X / 2) top_boss(b, BOSS_H);
            ear_col(EAR_X[1][0], EAR_X[1][1]);
            color("#b6c0cc") difference() {
                bottom_boss([78.3, 2]);   // 🔒 前の床ビスを +2（ハッチ方向）
                // 🔴 +2 で ReSpeaker の右端の部品（X 78.30〜82.79・Y 5.60〜7.50・Z 6.61〜9.81）と
                //    前面の部品（X 〜79.86・Y 6.91〜7.50・Z 17.75〜21.25）の真下に入る → その帯を欠く（±0.3）。
                //    🔴 2026-08-25 欠きは**全高**で抜く。ボスは壁と一緒に降りるので、部品より下の肉も降りる途中に
                //    その部品を通る（帯だけ欠いた旧版は close_rwall 29.0mm³）。＝ このボスは bottom_boss_br と同じ L 形になる。
                //    ナットは前半分（Y 2.6〜5.3）の壁が捕まえたまま: +Y へ出るには右の角（X 84.28）が残り肉（X 83.09〜85.3）に
                //    掛かり、−X へは前半分の壁で逃げ場が無い（開口 3.77 < 二面幅 4.3）。締める力を受ける座も前半分が残る
                translate([78.0, 5.3, -1]) cube([5.09, 7.5 - 5.3 + 1, BOSS_B_H + 2]);
            }   // 🔴 壁 84.354 で [IN_X-BOSS] だと OLED の右端（78.002）に 0.65 入る → 0.3 逃げ。壁側へ 0.95 めり込む分は自分の壁と一体
            bottom_boss_br();                          // 後ろ右（復活・L 形）
        }
        rwall_port_cut4();
    }
}
// ---- 天面 ----
//   v3 の top_plate_raw の v4 版。KNOB_TRIM・pb_front_hook・棚は無し。
//   🔴 PB の USB ピンの DuPont の逃げの頭（Z 49.2）が天井 48.454 を 0.75 超える（CASE-V4 §9 ⚠②）
//      → 板の裏を局所ポケットで彫る（X 17.9〜22.9・Y 56.4〜61.4・深さ 1.27・残り 1.23 ⚠）
module top_v4() {
    intersection() { seam_top_half();
    difference() {
        union() {
            color("#c9d0d8") translate([LW_X - WALL, FY_OUT, IN_Z]) cube([IN_X + 2 * WALL - LW_X, IN_Y - FY_OUT + HATCH_T, TOP_T]);
            knob_station_add4();                                                        // つまみの座（+3, +5・v4 の欠き入り）
            color("#c9d0d8") translate([BTN4[0], BTN4[1], 0]) rotate([0, 0, 180]) btn_socket();   // 会話ボタンの受け（タクトと同じ 180°）
            color("#c9d0d8") translate([SPK4_X - SPK_RIM_M, SPK4_Y - SPK_RIM_M, IN_Z - SPK_RIM]) difference() {   // スピーカーの位置出しの縁
                spk_obround(SPK_L + SPK_RIM_M * 2, SPK_W + SPK_RIM_M * 2, SPK_RIM);
                translate([SPK_RIM_M - 0.6, SPK_RIM_M - 0.6, -1]) spk_obround(SPK_L + 1.2, SPK_W + 1.2, SPK_RIM + 2);
            }
        }
        translate(KNOB4) knob_station_cut();
        // 会話ボタン: 皿・縁の面取り・首の穴（v3 と同じ形を BTN4 に）
        translate([BTN4[0] - BTN_DISH_L / 2, BTN4[1] - BTN_DISH_W / 2, Z_BTN_DISH]) spk_obround(BTN_DISH_L, BTN_DISH_W, BTN_DISH_T + 1);
        translate([BTN4[0], BTN4[1], Z_TOP - 0.3]) hull() {
            translate([-BTN_DISH_L / 2, -BTN_DISH_W / 2, 0]) spk_obround(BTN_DISH_L, BTN_DISH_W, 0.01);
            translate([-BTN_DISH_L / 2 - 0.3, -BTN_DISH_W / 2 - 0.3, 0.3]) spk_obround(BTN_DISH_L + 0.6, BTN_DISH_W + 0.6, 0.01);
        }
        translate([BTN4[0], BTN4[1], Z_BTN_PAD - 1]) cylinder(d = BTN_HOLE_D, h = BTN_PAD_T + 2, $fn = 32);
        // スピーカー: 振動板の逃げ・天面のへこみ・音の穴（v3 と同じ形を SPK4 に）
        translate([SPK4_X + (SPK_L - SPK_DIA[0]) / 2 - 0.5, SPK4_Y + (SPK_W - SPK_DIA[1]) / 2 - 0.5, IN_Z - 0.01]) spk_obround(SPK_DIA[0] + 1, SPK_DIA[1] + 1, SPK_REL + 0.01);
        // 🔒 SPK_LIFT で持ち上げた分、**枠ごと**天板に入るのでその座（逃げは振動板 15×9 の分しか無く、枠 23×15 が 0.4 食い込んでいた）。
        //    深さは SPK_LIFT ちょうど＝頭の上の隙間は持ち上げ前と同じ 0.2。横は片側 0.3（位置出しの縁 SPK_RIM と二段で効く）
        translate([SPK4_X - 0.3, SPK4_Y - 0.3, IN_Z - 0.01]) spk_obround(SPK_L + 0.6, SPK_W + 0.6, SPK_LIFT + 0.01);
        translate([SPK4[0], SPK4[1], 0]) hull() {
            translate([0, 0, Z_TOP - EMB_H]) linear_extrude(0.01) offset(r = 2) square([SPK_DIA[0] + EMB_M * 2 - 4, SPK_DIA[1] + EMB_M * 2 - 4], center = true);
            translate([0, 0, Z_TOP + 1]) linear_extrude(0.01) offset(r = 2) square([SPK_DIA[0] + EMB_M * 2 - 4 + (EMB_H + 1) * 2, SPK_DIA[1] + EMB_M * 2 - 4 + (EMB_H + 1) * 2], center = true);
        }
        grille_xy(SPK4[0], SPK4[1], SPK_DIA[0], SPK_DIA[1], IN_Z, TOP_T, 2.2, 3.4);
        // 天面のビス 4 本（後ろの柱 2＋耳 2・v3 と同じ）
        for (b = BOSSES) translate([b[0] + BOSS / 2, b[1] + BOSS / 2, 0]) {
            translate([0, 0, IN_Z - 1]) cylinder(d = SCR_D, h = TOP_T + 2, $fn = 24);
            translate([0, 0, Z_TOP - SCR_CBT]) cylinder(d = SCR_CB, h = SCR_CBT + 1, $fn = 32);
        }
        for (ex = EAR_X) translate([(ex[0] + ex[1]) / 2, (EAR_Y0 + EAR_Y1) / 2, 0]) {
            translate([0, 0, IN_Z - 1]) cylinder(d = SCR_D, h = TOP_T + 2, $fn = 24);
            translate([0, 0, Z_TOP - SCR_CBT]) cylinder(d = SCR_CB, h = SCR_CBT + 1, $fn = 32);
        }
        // PB の USB 線の逃げのポケット（頭 49.2 ＋ 0.5）
        translate([17.9, 56.4, IN_Z - 0.01]) cube([5.0, 5.0, 49.72 + BOARD_LIFT - IN_Z]);   // 🔴 板を 0.5 上げた分だけ深くなる（残り肉 1.23 → 0.73 ⚠）
    }
    }
    oled_brackets();   // OLED の L（v3 のまま。継ぎ目の外に置く）
    // ReSpeaker の押さえ: 前リブ（⚠ X 31.4〜37.4）と腕（⚠ X 50.0〜54.7 へ移設・全高でそのまま天井へ）。
    // 🔴 継ぎ目の 45°（Y+Z ≥ 48.454）の**外**に置く。v3 は intersection の中に入れていて、リブの Z 36.2〜40.8 が
    //    切り落とされ、押さえが ReSpeaker（頭 36.5）に届いていなかった（close_top 18.6mm³ に押さえ分が無いのはこのため）。
    //    OLED の L と同じ扱いにする。押し代 0.3 で ReSpeaker と重なるのは正（≈ 6mm³）
    color("#c9d0d8") translate([RIB4_X, RSP_BD_Y0 - 0.5, RSP_TOP - RSP_PRESS]) cube([RIB4_W, respeaker_T() + 1.0, IN_Z - RSP_TOP + RSP_PRESS + 0.01]);
    color("#c9d0d8") translate([ARM4_X0, RSP_BD_Y0 - 0.5, RSP_TOP - RSP_PRESS]) cube([ARM4_X1 - ARM4_X0, respeaker_T() + 1.0, IN_Z - RSP_TOP + RSP_PRESS + 0.01]);
}
// つまみの座（v4 の欠き 3 つ）。v3 の KNOB_TRIM と同じ流儀（🔒 落とすのは組んだ位置）:
//   ① スピーカー側: 座の板の前端が移動後のスピーカー（後端 Y 21.8・頭 Z 48.25）に 159mm³ → Y < 22.3 を欠く
//   ② 右壁側: スピーカー OUT の線の通り道（壁ぎわ・束は幅 2.2 で X 82.4〜84.6・Z 19.5〜47.35）に 220mm³
//      → X > 82.1（線の 0.3 手前）を欠く。皿の縁 82.2 を 0.1 なめるが、削れるのは皿の下（Z < 48.454）の座の肉だけ
//   ③ AS5600 コネクタの列（KNOB4[1]=40.8 で Y 34.37〜36.60）が座の板の下段に 2mm³ → v3 の「4 ピンヘッダの幅だけ切り欠く」と同じ（±0.3）
//      2026-08-26 取付回転は R0（コネクタの列が手前）に決めた（ユーザー「どっちに付けろと書け」→ AI が決定）。
//      この欠きは手前側にしか無いので、R180 にすると切り直しになる
// 🔒 2026-08-26 A-8 の直し: 欠き ③④ の座標を **KNOB4 からの引き算**にした。
//    つまみを動かしたときに手で追うのは、これまで下の 2 行の生の数字だった（追い忘れで当たりが何度か出ている）。
//    ⚠ **凍結をやめたわけではありません。**検証済みの絶対値は下の assert がそのまま持っていて、
//    引き算の結果が 0.001 でもずれれば OpenSCAD がその場で止まります。つまみを動かすときは、
//    KNOB4 を書き換えたうえで **この assert の数字を意図的に更新する**のが手順になります。
// ③ AS5600 コネクタの列。板の中心（KNOB4[0]）から左右へ、前後は列の位置から
function k3x0() = KNOB4[0] -  9.824;
function k3x1() = KNOB4[0] +  9.816;
function k3y0() = KNOB4[1] -  6.430;
function k3y1() = KNOB4[1] -  4.200;
// ④ トグルの線のノッチ。左端は座の板の左端（KNOB4[0] - knob_bay_x()/2 = 51.204）の 0.3 外、
//    後端は座の板の後端（KNOB4[1] + knob_bay_y()/2 = 60.3）を 0.4 抜けるまで
function k4x0() = KNOB4[0] - knob_bay_x() / 2 - 0.300;
function k4x1() = KNOB4[0] - 10.954;
function k4y0() = KNOB4[1] + 13.550;
function k4y1() = KNOB4[1] + knob_bay_y() / 2 + 0.400;
// 🔒 検証済みの絶対値（2026-08-25 の全配線検証で当たり 0 を出したときの座標）
assert(abs(k3x0() - 57.380) < 0.001 && abs(k3x1() - 77.020) < 0.001, "③ の X が凍結値からずれた");
assert(abs(k3y0() - 34.370) < 0.001 && abs(k3y1() - 36.600) < 0.001, "③ の Y が凍結値からずれた");
assert(abs(k4x0() - 50.904) < 0.001 && abs(k4x1() - 56.250) < 0.001, "④ の X が凍結値からずれた");
assert(abs(k4y0() - 54.350) < 0.001 && abs(k4y1() - 60.700) < 0.001, "④ の Y が凍結値からずれた");
module knob_station_add4() difference() {
    color("#c9d0d8") translate(KNOB4) knob_station_add();
    translate([KNOB4[0] - 30, KNOB4[1] - 30, 40]) cube([60, 22.3 - (KNOB4[1] - 30), 8.5]);
    translate([82.1, KNOB4[1] - 30, 30]) cube([10, 60, 18.454]);
    translate([k3x0(), k3y0(), 32.55]) cube([k3x1() - k3x0(), k3y1() - k3y0(), 3.1]);   // （島 −1.5 に追従。🔒 つまみ +2 で 32.37〜34.60 → 34.37〜36.60）
    // ④ トグルの線（立ち上がり X 55.2 → Y 64.8〜55.4 の前送り → Z 46.8 の車線）が座の板の左端（X 52.7〜）の
    //    後角を通る → ノッチ（皿の縁の外・板の後端 58.3 を抜けるまで・±0.3）。
    //    🔴 横穴だと天面を降ろす軌跡でノッチの底の肉が線を通過する（topseat 12mm³）→ 下まで抜いて縦の通り道にする
    translate([k4x0(), k4y0(), 41.9]) cube([k4x1() - k4x0(), k4y1() - k4y0(), 48.0 - 41.9]);   // 🔒 つまみ +2 で板の後端 58.3 → 60.3。ノッチも後端を抜けるまで延長（58.7 → 60.7）   // （島 −1.5: 座の板の左端 51.2 の 0.3 外から）
}

// ---- フロント ----（OLED・ReSpeaker が 🔒 固定なので v3 と同一。窓・ベベル・ヒゲ・耳）
// ---- ハッチ ----
//   v3 の hatch_raw から: トグルの穴＋アンテナのスリット＋下の爪は同じ。充電口が加わる:
//   🔒 2026-08-25 ③案（ユーザー）: **Type-C 基板の鼻先はハッチの厚みの中へ 1.2**（口の面が外面の 0.8 裏）。
//   プラグが面まで届くのでポケットは不要——**口（殻の大きさ）＋ベベルだけ**。右壁の XIAO の口と同じ顔で意匠が揃う。
//   位置はプローブの bbox（_v4_skin_probe.scad）→ 中心 [3.23, 10.5]・縦の口。印（稲妻）は口の左（+X。右は板の縁）。
//   🔴 経緯: 初版は「内面に鼻先・外から局所薄肉 0.8 のポケット」で、輪郭 3 重＋角の丸みに食い込む顔だった（ユーザー「変」）
CHG4_C = [3.23 + LW_X, 10.5]; TC_PORT_V4 = [3.86, 9.54];   // 基板は左壁ベタ付け（LW_X に追従）
module hatch_chg_cut4() {
    c = CHG4_C;
    translate([c[0], 0, c[1]]) rotate([-90, 0, 0]) {
        translate([0, 0, IN_Y - 1]) linear_extrude(HATCH_T + 2) port_rrect_xz(TC_PORT_V4, USBC_PORT_R);   // 口（殻の大きさ・貫通。殻 3.26×8.94 が中へ入る）
        hull() {                                                                                          // 外面のベベル
            translate([0, 0, IN_Y + HATCH_T - PORT_BEV]) linear_extrude(0.01) port_rrect_xz(TC_PORT_V4, USBC_PORT_R);
            translate([0, 0, IN_Y + HATCH_T + 1.0]) linear_extrude(0.01) port_rrect_xz(TC_PORT_V4, USBC_PORT_R, PORT_BEV + 1.0);
        }
    }
    translate([c[0] + TC_PORT_V4[0] / 2 + PORT_BEV + ICON_GAP + TC_ICON_H * 2.6 / 6 / 2, IN_Y + HATCH_T - ICON_D, c[1]])
        rotate([90, 0, 0]) mirror([0, 0, 1]) linear_extrude(ICON_D + 1.0) icon_bolt(TC_ICON_H);
    // 基板の縁（X 0〜1.6・板 1.6 厚）が +1.2 で内面に 0.4 入る分の逃げ溝（0.7 深・±0.5。内面側なので見えない）
    translate([LW_X - 0.5, IN_Y - 0.01, -0.5]) cube([2.6, 0.71, 21.5]);
}
module hatch_v4() {
    difference() {
        union() {
            color("#c9d0d8") translate([LW_X - WALL, IN_Y, -FLOOR_T]) cube([IN_X + 2 * WALL - LW_X, HATCH_T, IN_Z + FLOOR_T]);
            color("#c9d0d8") hatch_claws();
            color("#c9d0d8") sw4_backing();   // 電池の蓋の彫り込みの裏の増し肉＋ロックのボス＋磁石の座（case_v4_shutter）
        }
        translate([TGL_AT[0], IN_Y - 1, TGL_AT[1]]) rotate([-90, 0, 0]) mts102_hole(HATCH_T + 2);
        hatch_chg_cut4();
        translate([TGL_AT[0] - ANT_SLOT_W / 2, IN_Y - 1, TGL_AT[1] - (ANT_OFF + ANT_SLOT_W / 2)]) cube([ANT_SLOT_W, HATCH_T + 2, ANT_OFF + ANT_SLOT_W / 2]);   // アンテナ線のスリット（トグルの下・v3）
        sw4_band_cut();        // 電池の蓋の彫り込み帯
        sw4_lock_cut();        // ロックのネジ穴とナットの座
        battery_port_cut4();   // 電池の口（蓋が塞ぐのでベベル無し・v3 と同じ）
    }
}
// 蓋の一式（絵と検査に出す実体。open=0 で閉）
module door4(open = 0, fast = false) {
    color("#c8ced6") battery_shutter4(open);
    color("#8892a0") battery_lock4();
    sw4_magnets_wall(); sw4_magnets_shutter();
    if (fast) { sw4_lock_screw(); sw4_lock_nut(); }   // ビスとナットは絵にだけ（v3 と同じ。当たり検査は持たない）
}

// ---- 角丸（v3 の rounded と同じ。スピーカーの盛り上げの例外だけ v4 の位置）----
// 🔒 2026-08-25 ユーザー「黄色い外装はなんで? 灰色にして」: 角丸の intersection で板の color が落ちて
//    OpenSCAD の既定色（黄）に戻っていた。皮の色はここで一括指定（#c9d0d8）
module rounded4() { color("#c9d0d8") intersection() { children(); union() { outer_envelope(); translate([SPK4_X - 6, SPK4_Y - 6, Z_TOP - 1]) cube([SPK_L + 12, SPK_W + 12, EMB_H + 1]); } } }

// ---- 表示と検査（part で選ぶ。一覧は冒頭）----
// フロント板（v4）。床の前 2 本の柱が +2 で Y 2〜7.5 になり、板の裏（Y 1.0）とは当たらなくなったので逃げは持たない
module front_v4() front_plate_raw();
module skin1(k) {
    if (k == "floor") floor_v4();
    if (k == "lwall") lwall_v4();
    if (k == "rwall") rwall_v4();
    if (k == "top")   top_v4();
    if (k == "front") front_v4();
    if (k == "hatch") hatch_v4();
}
SKINS = ["floor", "lwall", "rwall", "top", "front", "hatch"];
module skin_all() for (k = SKINS) skin1(k);
module skin_except(k) for (n = SKINS) if (n != k) skin1(n);
module innards4(tgl = 0) { core(); color("#f6ad55") bat_v4(); pb_bat(); pbl_hous(); pbu_hous(); ina_bat(); tgl_v4(tgl); if (tgl != 0) tail_at(); tcb_v4(); brg_v4(); brg_front(); straps_v4(); wires_pwr(); wires_sig(); door4(0, tgl != 0); }   // tgl: レバーの角度。絵は TAIL_ANG ＋ 尻尾＋蓋のビスの絵付き。door4 = 電池の蓋一式（閉）

if (part == "look") { rounded4() skin_all(); innards4(TAIL_ANG); }
OPEN = ["floor", "lwall", "rwall", "top"];   // 🔒 2026-08-25 ユーザー「inside は本来 壁なし・床なし・天井なし（v3 から壊れてた）」。残すのはフロントとハッチ
function shown(n) = len([for (o = OPEN) if (o == n) 1]) == 0;
if (part == "inside") { rounded4() for (k = SKINS) if (shown(k)) skin1(k); innards4(TAIL_ANG); }

// 印刷部品（p_*）と刷る向き（print_* = 外面を下・底 Z0）
module p_one(k) {
    if (k == "shutter") battery_shutter4(0);
    else if (k == "lock") battery_lock4();
    else if (k == "tail") translate([0, 0, -0.2]) tail_cap();
    else rounded4() skin1(k);
}
P_NAMES = ["floor", "lwall", "rwall", "top", "front", "hatch", "shutter", "lock", "tail"];
for (k = P_NAMES) if (part == str("p_", k)) p_one(k);
// 🔒 v3 と同じ名前（2026-08-25 ユーザー）。芯の _v4_core にある板なので p_ は付けない・角丸も無し・刷る向きは ⬜ 未決（CASE-V4 §10）
// 🔒 2026-08-25 ユーザー「バッテリー、電流計、PowerBoost、左右の壁、結束バンドは必要です」: ブリッジは単体では判断できないので一緒に出す
if (part == "bridge") {
    brg_v4(); brg_front(); straps_v4(); brg_hw();   // brg_hw = 箱へ留める M2×6 とナットの現物（3 か所）
    color("#f6ad55") bat_v4(); ina_bat(); pb_bat();
    rounded4() { skin1("lwall"); skin1("rwall"); }
}
if (part == "print_floor")   translate([0, 0, FLOOR_T]) p_one("floor");
if (part == "print_lwall")   translate([0, 0, WALL]) rotate([0, -90, 0]) p_one("lwall");
if (part == "print_rwall")   translate([0, 0, IN_X + WALL]) rotate([0, 90, 0]) p_one("rwall");
if (part == "print_top")     translate([0, 0, Z_TOP]) rotate([180, 0, 0]) p_one("top");
if (part == "print_front")   translate([0, 0, BEZ_T]) rotate([90, 0, 0]) p_one("front");
if (part == "print_hatch")   translate([0, 0, IN_Y + HATCH_T]) rotate([-90, 0, 0]) p_one("hatch");
if (part == "print_shutter") translate([0, 0, SW4_YOUT]) rotate([-90, 0, 0]) battery_shutter4(0);
if (part == "print_lock")    translate([0, 0, SW4_YOUT]) rotate([-90, 0, 0]) battery_lock4();
if (part == "print_tail")    translate([0, 0, -0.2]) tail_cap();

// ---- 2026-08-26 ここから 5 点（ブリッジ・留め帯 A/B/C・会話ボタンのキャップ）----
//   それまで STL の出口が無く、刷れるのは板 9 点だけだった（CASE-V4-OPEN A-2）。
// 帯は 3 本が別々の部品。straps_v4() は 3 本＋座を一度に作るので、Y で 1 本ぶんだけ切り出す
//   （座・ナットの横穴・PB の足の逃げ溝も、その帯に属するぶんだけ一緒に出る）
// 🔒 2026-08-26 ツバ（TAB_*）は帯の Y の外へ出るので、切り出しはツバ込みの端（strap_ya/strap_yb）で取る
module strap_one(s) intersection() {
    straps_v4();
    translate([-100, strap_ya(s) - 0.05, -100]) cube([400, strap_yb(s) - strap_ya(s) + 0.1, 400]);
}
// 🔒 2026-08-26 ユーザー「帯を下にして印刷するならこうすれば確実だ」: 天板をベッドに伏せる（うつ伏せ）。
//   絵のとおりの向き（足とツバを下・座を上）でベッドに置く。足の裏とツバの裏は同じ面なので 1 層目は平ら、
//   ツバは上へすぼまるので庇にならない。旧版（断面を寝かせて Y を上へ向ける）は、ツバが押し出しの軸そのものへ
//   出るため 1 層目がツバだけの島になり、その上で断面が宙に浮く。もう使えない。
//   ⚠ この向きでは天板が足と足の間（X 15〜51 ＝ 36）を渡る。支えは要らないがブリッジになる。
module strap_print(s) translate([0, 0, -BAT_Z]) strap_one(s);
if (part == "print_strap_a") strap_print(STRAP_BANDS[0]);
if (part == "print_strap_b") strap_print(STRAP_BANDS[1]);
if (part == "print_strap_c") strap_print(STRAP_BANDS[2]);
// キャップ: 閉じている天面をベッドに伏せる（うつ伏せ）。中の空洞と押し棒が上を向くので支えは要らない
//   （棒の先の返り φ5 × 0.8 だけが庇になる）。z_top = Z_TOP + BTN_OUT
if (part == "print_btn")     translate([0, 0, Z_TOP + BTN_OUT]) rotate([180, 0, 0]) button_cap();
// ブリッジ: 皿を伏せる（2026-08-26・前板を別部品にしたので L 字ではなくなった）。レール・パッドは全部上を向く。
//   ⚠ 皿の裏に 1 つだけ出っ張りが残る: 充電の Type-C の押さえ（X 1.69〜3.9・Y 58.6〜62.2・皿の裏から 0.7 下）。
//     底の Z を 0 にするためにその押さえで置いているので、**皿は 0.7 浮く**。ここだけラフト／サポートが要る
if (part == "print_bridge")  translate([0, 0, -TC_PRESS[2]]) brg_v4();
// 前板（返し＋脚）: **前面を伏せて寝かせる**（🔒 2026-08-26 ユーザー「寝かせる向きでしょ」）。
//   前面（Y 12.9）は 634mm² の 1 枚の平らな面なので、そのままベッドに着く。フランジは真上へ立つ壁になり庇は出ない
if (part == "print_brgfront") translate([0, 0, -BAT_Y0]) rotate([90, 0, 0]) brg_front();

// 静止の当たり: 板 1 枚 ↔ 中身＋他の板。**0 が正**。
//   ReSpeaker の押さえの押し代（リブが板に 0.3 めり込む設計値）は意図した重なりなので検査から除外し、
//   専用の chk_press（**≈6mm3 が正**・消えたら押さえが届いていない）で見張る（2026-08-25 ユーザー「残るも何もないんじゃない?」）
module rsp_press_zone() {   // リブ 2 本の足元（押し代の領域）
    translate([RIB4_X - 0.01, RSP_BD_Y0 - 0.51, RSP_TOP - RSP_PRESS - 0.01]) cube([RIB4_W + 0.02, respeaker_T() + 1.02, RSP_PRESS + 0.02]);
    translate([ARM4_X0 - 0.01, RSP_BD_Y0 - 0.51, RSP_TOP - RSP_PRESS - 0.01]) cube([ARM4_X1 - ARM4_X0 + 0.02, respeaker_T() + 1.02, RSP_PRESS + 0.02]);
}
for (k = SKINS) if (part == str("chk_", k)) difference() { intersection() { skin1(k); union() { innards4(); skin_except(k); } } rsp_press_zone(); }
if (part == "chk_all") difference() { intersection() { skin_all(); innards4(); } rsp_press_zone(); }
if (part == "chk_press") intersection() { top_v4(); respeaker_at(); }   // ≈6mm3 が正（0 なら押さえが板に届いていない）
// 充電（Type-C）基板の受け ↔ 周り。**0 が正**。
//   受け（床の tc_seat4）と 押さえ（ブリッジの brg_tc_press）は、どちらも自分の板の一部なので
//   chk_floor / chk_all では「板 ↔ 中身」の片側に入ってしまい、基板そのものとの当たりが見えない。専用に見張る。
if (part == "chk_tc") intersection() {
    union() { tc_seat4(); brg_tc_press(); }
    union() { core(); tcb_v4(); bat_v4(); pb_bat(); pbl_hous(); pbu_hous(); ina_bat(); straps_v4();
              wires_pwr(); wires_sig(); door4(); lwall_v4(); rwall_v4(); top_v4(); front_v4(); hatch_v4(); }
}

// 組む動き（v4 の①〜⑬は ⬜ ユーザー待ち。板ごとの入れる向きだけ当てる）:
//   壁は上から降ろす（🔒 v3「両方上から降ろせないとダメ」）・天面は上から・フロントは前から・ハッチは後ろから
module stage_noskin() { innards4(); floor_v4(); }
// 🔴 2026-08-25 壁の障害物を「その時点で箱に入っている物」に直した。
//   壁を降ろすのは手順 4 で、ブリッジ・電池・留め帯・基板・上の車線・トグルはまだ入っていない（CASE-V4 §7）。
//   それまでは innards4（＝全部）を障害物にしていたが、壁が素の板だったので偶然 0 だった。
//   ブリッジを留める棚（brg_ledges）が壁に付いた今は、棚が**後から入るブリッジの腕の位置**を通り抜けるので、
//   古い障害物のままだと左 121mm³ / 右 178mm³ が出る。これは順番を守れば起きない当たりなので、
//   障害物の側を正した（close_tc と同じ考え方）。静止の当たりは chk_lwall / chk_rwall が別に見ている。
module stage_walls() { hub_unit(); respeaker_at(); xiao_hous(); rsp_j2_space(); wires_low(); floor_v4(); }
if (part == "close_lwall") intersection() { union() for (t = [0 : STEP : 30]) translate([0, 0, t]) lwall_v4(); stage_walls(); }
if (part == "close_rwall") intersection() { union() for (t = [0 : STEP : 30]) translate([0, 0, t]) rwall_v4(); stage_walls(); }
//   ⚠ close_rwall に残る 25mm³ は スピーカー OUT の**天井下の区間**（X 82.55〜84.05・Y 30〜36・Z 44.35〜47.35）を
//     右の前の棚が通り抜ける分。この 2 本はスピーカー（天面の部品）に付いたまま最後に降りてくるので、
//     壁を降ろす時点では箱に居ない。低い車線に居るのは口から壁ぎわまでの Z 19.5 の区間だけで、そこは 0
// 天面と一緒に降りる物（島・コネクタ・スピーカー・タクト・傘 = core の top_group）は動く側。障害物に入れない
module stage_top() { lower_group(); brg_v4(); brg_front(); bat_v4(); pb_bat(); ina_bat(); straps_v4(); pbl_hous(); pbu_hous();
                     wires_pwr(); wires_sig(); floor_v4(); lwall_v4(); rwall_v4(); }
if (part == "close_top") difference() { intersection() { union() for (t = [0 : STEP : 25]) translate([0, 0, t]) { top_v4(); top_group(); }
                                          stage_top(); } rsp_press_zone(); }   // 押し代は除外。🔒 つまみ +2 後の 2mm³ は「AS5600 の線の逃げ予約（3.6 角）↔ PHIN」。実体同士は Z で 2.15 離れて非接触（2026-08-25 ユーザー確認・PHIN の曲がりは 1.5 に修正済み）。これだけが正
if (part == "close_front") intersection() { union() for (t = [0 : STEP : 20]) translate([0, -t, 0]) front_v4();
                                            union() { stage_noskin(); lwall_v4(); rwall_v4(); top_v4(); } }
if (part == "close_hatch") intersection() { union() for (t = [0 : STEP : 20]) translate([0, t, 0]) { hatch_v4(); tgl_v4(); door4(); }
                                            union() { core(); bat_v4(); pb_bat(); pbl_hous(); pbu_hous(); ina_bat(); tcb_v4(); brg_v4(); brg_front(); straps_v4(); wires_pwr(); wires_sig(); floor_v4(); lwall_v4(); rwall_v4(); top_v4(); front_v4(); } }
// 充電基板の入れ方（🆕 2026-08-25）。**左の壁の内面に当てて、壁と一緒に降ろす**。デュポンはまだ挿していない
//   🔴 壁より先に立てることは出来ない: 板の裏を受ける面が左壁の内面そのものなので、壁が無いと −X 側へ倒れる。
//   🔴 壁より後に真上から落とすことも出来ない: 天面の後ろ左のボス（左壁の一部・X 1.694〜・Y 64〜72・Z 38〜48）が
//      板の平面図の footprint（X 1.694〜3.294・Y 57.4〜72.4）に重なっていて、経路を 75.6mm3 塞ぐ。
//   → 残るのは「壁と一緒に降ろす」の 1 通り。この検査はその姿を見る
//   ⚠ 障害物に電源系の線（wires_pwr）は入れない: 電池は手順 6＝壁より後で、この時点ではまだ通っていない。
//      入れると 20.2mm3 出る（X 2.0〜4.9・Y 57.4〜64.45・Z 27.75〜30.75 ＝ 電池の線が板の真上を横切る場所）。
//      静止では板の上端 20.5 と線の下端 27.75 が 7.25 離れているので当たらないが、線を通すときはここを避けて回す
if (part == "close_tc") intersection() { union() for (t = [0 : STEP : 30]) translate([0, 0, t]) { lwall_v4(); tcb_v4_bare(); }
                                         union() { core(); floor_v4(); } }
if (part == "close_desk") intersection() { union() for (t = [0 : STEP : 30]) translate([0, 0, t]) brg_v4(); union() { lower_group(); brg_front(); } }   // core の deskseat と同じ（🔴 ブリッジは OLED を立てる前に降ろす順が前提・CASE-V4 §10）

// 線の検査（core の wchk/wwchk と同じ中身。WP で 1 束に絞る）
if (part == "chk_wire")   intersection() { wsel(); wire_obst(); }
if (part == "chk_wire_w") intersection() { wsel(); union() { wires_pwr(); if (WP != "") wsig_except(); } }
if (part == "chk_wire_pwr") intersection() { wires_pwr(); union() { core(); bat_v4(); pb_bat(); pbl_hous(); pbu_hous(); ina_bat(); tgl_v4(); tcb_v4(); brg_v4(); brg_front(); straps_v4(); skin_all(); door4(); } }

// 電池の入れ替えの動き: ロックを外す → 蓋を下へずらす → 蓋を後ろへ抜く → JST を抜く → 電池を後ろへ抜く
module world_no_door() { core(); bat_v4(); pb_bat(); pbl_hous(); pbu_hous(); ina_bat(); tgl_v4(); tcb_v4(); brg_v4(); brg_front(); straps_v4(); wires_pwr(); wires_sig(); skin_all(); }
module world_no_door_bat() { core(); pb_bat(); pbl_hous(); pbu_hous(); ina_bat(); tgl_v4(); tcb_v4(); brg_v4(); brg_front(); straps_v4(); w_pwr3(); w_batout(); wires_sig(); skin_all(); }   // 電池のタブ側の線（w_batin）は JST で外して抜くので入れない
if (part == "chk_shut_slide") intersection() { union() for (t = [0 : 0.5 : SHUT_SLIDE]) translate([0, 0, -t]) battery_shutter4(0); world_no_door(); }
if (part == "chk_shut_out")   intersection() { union() for (t = [0 : STEP : 20]) translate([0, t, 0]) battery_shutter4(1); world_no_door(); }
if (part == "chk_swap")       intersection() { union() for (t = [0 : STEP : 45]) translate([0, t, 0]) bat_v4(); world_no_door_bat(); }

// explode（v3 の part="explode" の v4 版。組む向きへ散らす）
EXPLODE4 = 40; EX4 = 22; S4 = 6;
if (part == "explode") {
    E = EXPLODE4; EX = EX4; S = S4;
    rounded4() floor_v4(); hub_unit(); respeaker_at(); xiao_hous(); oled_at(); oled_hous(); tcb_v4();
    translate([-EX, 0, E]) rounded4() lwall_v4();
    translate([EX, 0, E])  rounded4() rwall_v4();
    translate([0, 0, 0.35 * E])          brg_front();                                     // 前板（先に床の溝へ差す）
    translate([0, 0, 0.6 * E])           brg_v4();                                        // ブリッジ（掘り込みが前板のフランジに被さる）
    // 🔒 2026-08-26 順を入れ替えた。留め帯は横（つまみ側 +X）から、電池は後ろ（+Y）から入る
    translate([1.1 * S, 0, 0.6 * E + 2.0 * S]) straps_v4();                               // 留め帯 3 本（横から差す）
    translate([0, 1.1 * E, 0.6 * E])     color("#f6ad55") bat_v4();                       // 電池（後ろから差し込む・皿と同じ高さ）
    translate([0, 0, 0.6 * E + 4.0 * S]) { pb_bat(); ina_bat(); pbl_hous(); pbu_hous(); } // 帯の天面に載る 2 枚＋挿す線
    translate([0, 0, 2 * E]) { rounded4() top_v4(); top_group(); }                        // 天面一式（島・スピーカー・傘ごと）
    translate([0, -E, 2 * E]) rounded4() front_v4();                               // フロント（前から差す）
    translate([0, E, 2 * E]) { rounded4() hatch_v4(); tgl_v4(TAIL_ANG); translate([0, E / 2, 0]) tail_at();
                               translate([0, E / 2, 0]) { color("#c8ced6") battery_shutter4(0); sw4_magnets_shutter(); }
                               translate([0, E * 0.75, 0]) { color("#8892a0") battery_lock4(); sw4_lock_screw(); }
                               sw4_magnets_wall(); sw4_lock_nut(); }   // ハッチ＋トグル＋尻尾＋電池の蓋一式
}

// ---- T-1 の現場を見る（2026-08-26。ブリッジの 3 本目がドライバで届かない件）----
//   part="t1"     左後ろの角だけ切り出す。赤い棒が**ドライバの軸**（φ3.2 × 24 ＝ 外へ抜けるのに要る長さ）。
//                 いまはこれが天面のボス（左の壁と一体・Z 39.454〜48.454）に 13.0mm で刺さって止まる
//   part="t1_noboss"  同じ図から**天面のボスだけ**消した引き算。ボスさえ無ければ抜けることを見る用
//   part="t1_top"     真上から見た図（ボスと棚と耳の重なりが分かる）
//   どれも「見る用」で、印刷にも検査にも使わない
T1_LO = [-2, 54, 14]; T1_HI = [17, 74, 53];
module t1_clip() intersection() { children(); translate(T1_LO) cube([T1_HI[0]-T1_LO[0], T1_HI[1]-T1_LO[1], T1_HI[2]-T1_LO[2]]); }
module t1_boss_box() translate([LW_X - 1, IN_Y - BOSS - 1, IN_Z - BOSS_H - 1]) cube([BOSS + 2, BOSS + 2, BOSS_H + 2]);
module t1_driver() color("#e53e3e", 0.6) translate([BLU_SCR[0], BLU_SCR[1], BLU_PTOP - SCR_CBT]) cylinder(d = 3.2, h = 24, $fn = 32);
module t1_body(boss = true) {
    difference() { rounded4() lwall_v4(); if (!boss) t1_boss_box(); }   // 左の壁（棚と天面ボスごと）
    brg_v4(); brg_ledges(-1); brg_ledge_up(); brg_hw(); brg_hw_up();     // ブリッジ・棚・耳・ネジ
    tcb_v4();                                                            // 真下の Type-C 基板
    color("#8899aa", 0.25) rounded4() floor_v4();
    w_pwr3(); w_ina_i2c(); w_tgl(); w_chg();                             // 帯の上を通る線
}
if (part == "t1")        { t1_clip() t1_body(true);  t1_clip() t1_driver(); }
if (part == "t1_noboss") { t1_clip() t1_body(false); t1_clip() t1_driver(); }
if (part == "t1_top")    { t1_clip() t1_body(true);  t1_clip() t1_driver(); }

echo(v4_skin = "床/左壁/右壁/天面/フロント/ハッチ", knob4 = KNOB4, btn4 = BTN4, spk4 = SPK4);
echo(hub_holes4 = HUB_HOLES4, floor_screws = V4_FLOOR_SCREWS, chg4 = CHG4_C, in_x = IN_X);
if (part == "chk_top_spk")  intersection() { top_v4(); translate([SPK4_X, SPK4_Y, IN_Z - spk_th() - 0.2 + SPK_LIFT]) speaker_112495(); }   // 天板 ↔ 持ち上げたスピーカー（枠ごと入るので専用に見張る・0 が正）



