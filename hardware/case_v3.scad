// ============================================================
// 筐体 v3 —— 組む順番（docs/CASE-V3.md）から作る。寸法は全部変数。
// ============================================================
// 🔴 これは **⑨〜⑫ を確かめるための粗い形**（2026-08-22）。壁・板は箱、ブリッジは板、
//    留め（ビス・ナット・張り出し）はまだ無い。機構はユーザーが決める。
//   当たり:  openscad --backend=manifold -o x.stl -D "part=\"close\""       hardware/case_v3.scad   // ⑨ 側面構造体をまな板へ Z で降ろす
//            openscad --backend=manifold -o x.stl -D "part=\"close_top\""   hardware/case_v3.scad   // ⑫ 天面を Z で降ろす
//            openscad --backend=manifold -o x.stl -D "part=\"close_front\"" hardware/case_v3.scad   // ⑫ フロントを前から差し込む
//            openscad --backend=manifold -o x.stl -D "part=\"close_hatch\"" hardware/case_v3.scad   // ⑬ ハッチ（トグル付き）を Y で閉じる
//   絵:      part="look9"（⑨ の直後・天面と前とハッチ無し） / "look"（全部）
//            part="bridge" **トラス（波板）だけ**。実際の切り欠きを通した実物（v2 から復活）
//            part="bridge_eaten" その切り欠きで欠けた分だけ（体積を測る用）
// ============================================================
use <parts.scad>
use <respeaker_lite.scad>
use <hub_board.scad>
use <knob_v5.scad>
use <icon_gear_wrench.scad>   // メンテナンスの印（ユーザーの SVG から gen_icon_svg.py が起こした）
use <usb_l_adapter.scad>          // 充電口の L 字アダプタ（B0CTMHK3BY・2026-08-24）。🔴 同日、規格違反（C メス → micro-B）と分かり不採用
use <typec_115426.scad>           // 充電口の Type-C 基板（秋月 115426・2026-08-24。⚠ 未注文）
use <wires.scad>              // 線を実体で描く（v2 と同じ道具）
include <hub_board_parts.scad>

part  = "inside";
$fn   = 48;     // 🔒 v2 と同じ分割数。🔴 無いと小さい円（マイクのヒゲ・口の角丸）が 5〜6 角形で出て粗雑に見える（2026-08-23 ユーザー指摘）
SWEEP = 40;     // 降ろす距離（mm）
STEP  = 1;

// ---- 肉厚 ------------------------------------------------------------
WALL    = 2.0;   // 壁（落下前提 2.0）
FLOOR_T = 2.0;   // まな板
TOP_T   = 2.5;   // 天面
BEZ_T   = 2.0;   // フロント
HATCH_T = 2.0;   // ハッチ

// ---- まな板: ハブと ReSpeaker（v2 の値。ReSpeaker の位置はマイクで決まる） ----
BOARD_Z   = 2.5;                                   // 半田面の逃げ
RSP_X     = 2.0;
RSP_Z     = BOARD_Z;
RSP_SW_OUT = 2.585;  RSP_GAP = 1.0;
RSP_BD_Y0 = oled_back() + RSP_SW_OUT + RSP_GAP;    // 8.185 基板の前面
RSP_BD_Y1 = RSP_BD_Y0 + respeaker_T();             // 10.035
HUB_L = hub_size()[0]; HUB_W = hub_size()[1]; HUB_T = hub_size()[2];
HUB_FRONT_CL = 11.9 - 10.035;                      // ハブの手前 ↔ ReSpeaker の背面（v2: 1.865）
HUB_Y0_MIN = 10.035 + HUB_FRONT_CL;                // 11.9（v2 の値）。⬜ 下で後列の口がブリッジを外れる分だけ後ろへ送る
HUB_TOP_Z = BOARD_Z + HUB_T + hub_top(true);       // 部品面の頂点 15.1（ボタン 11。ハウジングは housing() で別に置く）

// ---- 線（挿したハウジング）。⑨ の時点でハブに挿さっている 7 本 --------------
HOUS_H = 10.0;   // ✅ DuPont ハウジングの高さ（ユーザー実測。2026-08-24 まで「未実測」と書いていたのは誤り）
HOUS_R = 3.6;    // 束が曲がり切るまで
// 🔒 2026-08-22 ユーザー決定: **線は 10 本全部挿してから側面構造体を載せる**（⑩ を ⑨ の前へ）
PLUGGED_9 = ["XIAO", "PHIN", "OLED", "AS5600", "BTN2", "REED", "PHOUT", "PWR", "INA", "TOGGLE"];
PLUGGED_10 = [];

// ---- 内寸（変数。手書きしない） ------------------------------------------
RIGHT_CL = 0.45;                                   // ⬜ XIAO の USB-C の殻 ↔ 右の壁の内面
BACK_CL  = 8.1;                                    // 🔴 2026-08-23 v2 の値に戻す（ユーザー「Y 5mm を稼ぐ」）。初版は HOUS_H + HOUS_R = 13.6（後列の口が立ち上がる分・⬜未実測）で奥行きが v2 より 5.5 増えていた
IN_X = RSP_X + respeaker_L() + xiao_usb_out() + RIGHT_CL;   // 86.0
// IN_Y・IN_Z・HUB_AT は下で（積み上げから決める）
HUB_X  = (IN_X - HUB_L) / 2;
function port_at(id) = [for (h = HUB_HEADERS) if (h[0] == id)
    [HUB_AT[0] + (h[4] + h[6]) / 2, HUB_AT[1] + (h[5] + h[7]) / 2, HUB_AT[2] + HUB_T]][0];
function port_wl(id) = [for (h = HUB_HEADERS) if (h[0] == id)
    [max(h[6] - h[4], 2.54) + 0.6, max(h[7] - h[5], 2.54) + 0.6]][0];

// ---- 側面構造体: ブリッジ・INA226・PowerBoost・電池 ----------------------
INA_CL   = 0.5;                                    // INA226 の部品面 ↔ ハブの部品面
BR_DEPTH = 6.1;                                    // ブリッジの厚み（v2）
BR_ZB    = HUB_TOP_Z + ina_back_env() + ina_h() + INA_CL;   // ブリッジの下面 23.2（INA226 がぶら下がる分）
BR_ZT    = BR_ZB + BR_DEPTH;                       // 29.3
LIPO_L = lipo_size()[0]; LIPO_W = lipo_size()[1]; LIPO_TH = lipo_size()[2];
TUN_CL = 0.4; TUN_T = 2.0; TUN_END_T = 1.6;   // トンネルの壁 / 奥の端板（v2 と同じ 1.6。つまみの裾との取り合い）
XIAO_HEAD_Y = RSP_BD_Y1 + 10.0;                    // 20.035 XIAO の積み重ねの頭（✅実測 10.0）。ReSpeaker で一番奥
BR_CL   = 0.5;                                     // ブリッジの前面 ↔ XIAO の頭
BR_Y0   = XIAO_HEAD_Y + BR_CL;                     // 20.5（v2 は 19.2 で頭に 8.1mm3 当たっていた）
LIPO_AT = [2.0, BR_Y0 + TUN_T + TUN_CL, BR_ZT];    // 電池はブリッジの上（v2）。Y 22.9
BR_Y1 = LIPO_AT[1] + LIPO_W + TUN_CL + TUN_T;      // 60.3 トンネルの後ろの壁の外面

PB_TH = pb_size()[2]; PB_W = pb_size()[1]; PB_L = pb_size()[0];
// 🔒 PowerBoost はダボ（2026-08-22 ユーザー）。壁の内面のピン 4 本が基板の穴 φ2.5 を通る。
//    基板の裏には JST と配線パッドの半田の盛りがあるので、ピンの肩で 1.2 浮かせる
PB_STANDOFF = 1.2;                                 // 肩の高さ（基板の裏 ↔ 壁の内面）。（2026-08-24 に裏出しのため +2.9 を試したが、C6 の逃げが座を 2.9 余計に削ることになり不成立）
DOWEL_D = 2.3; DOWEL_SH_D = 4.0; DOWEL_OUT = 0.2;  // ピン径 / 肩の径 / 基板の面から出る長さ（1.0 だと後ろ下のピンの先が L の唇に 0.45mm3 入る）
PB_X1 = IN_X - PB_STANDOFF;                        // 基板の裏の面（v2 は IN_X に密着）
PB_Y0 = 24.0;
PB_DROP = 2.6;                                     // JST の先（ハウジング込み）がブリッジの下面より下に出る分（v2: 22.4 → 19.8）
// （2026-08-24 に上下反転・床置きを試して取り下げた。PB_ZT は IN_Z の直後で定義）（旧）R_ZB - PB_DROP + pb_jst_out() + PB_W;   // v2〜8/24: 48.15 基板の上端。🔴 初版は pb_jst_out() を忘れて 3.8 低かった（充電プラグが足に 131mm3）
BR_X1 = PB_X1 - PB_TH;                             // ブリッジは板の面で終わる
// ブリッジ ↔ 右の壁: v2 と同じ「前の足」と「後ろの柱」で、PowerBoost の前後で壁に届く（2026-08-22 ユーザー「筐体広げても無理?」→ 広げずにブリッジを後ろへ延ばす）
POST_W  = 6.0;                                     // 後ろの柱の Y 幅。M2.5 のナット（5.3）とビスが通る幅（3.5 では入らない）
PB_REAR_CL = 0.3;                                  // 基板の後端 ↔ 柱後端が micro-USB の側になり、殻が 0.5 出ている分を足した（立ち上がりに 4mm³）
PB_FRONT_CL = 0.6;                                 // 基板の前端 ↔ 足（0.3 だと板の前に出ている物に 0.8mm3 触れる）
BR_Y1_R = max(BR_Y1, PB_Y0 + PB_L + PB_REAR_CL + POST_W);   // 63.9 右端だけ後ろへ延ばす
PB_FACE_X = PB_X1 - pb_pcb_t();                    // 83.2 基板の部品側の面
LIP_GAP = 0.3; LIP_T = 2.0; LIP_OVER = 1.5;        // 唇: 基板の面との隙間 / 厚み / 縁に被さる幅（v2 と同じ）
// 後ろの L の高さ: 基板の平らな帯（局所 y 14.0〜19.9。R12 が y 20.46〜、端子台の足跡の pad が y 〜12）に合わせる
//    🔴 初版はブリッジの帯の高さ（Z 23.6〜29.3）に置いたが、PowerBoost の高さを直したらそこは基板の下の縁（JST・R12）だった
// LIP_Z0/Z1 は IN_Z の後で定義（PB_ZT に依存・局所 y 14.0〜19.9 の平らな帯）
RISE_X0 = BR_X1 - 2;                               // 76.0 立ち上がりの −X の端（柱と同じ）。初版は 80.9（唇の −X の面）で幅 5.1 しか無かった
// ビス: 🔒 **ハブ（M3）以外は全部 M2**（2026-08-23 ユーザー「ハブ以外 M2 に揃えましょう」）。v2 の M2 の実績値（OLED・ロック）
//    ナット二面幅 4.0 ＋ 0.3 / 厚み 1.6 ＋ 0.2 / 通し穴 2.4 ＋ 0.1 / 頭のザグリ φ4.4 × 1.6
NUT_AF = 4.3; NUT_T = 1.8; SCR_D = 2.5; SCR_CB = 3.0 + 0.4; SCR_CBT = 1.3 + 0.3;   // 頭 ✅ φ3.0 × 1.3（2026-08-23 ユーザー実測・鉄）→ ザグリ φ3.4 × 1.6
LEDGE_H = 8.0; LEDGE_W = 10.0;                     // ブリッジを受ける棚（ナット入り）。🔴 5.8 → 10: 蓋の彫り込み（X 〜1.0）と裏の肉（〜2.2）を避けてナットを X 5 に
LEDGE_L_Y = [[31.0, 37.0], [52.0, 58.0]];          // 左の棚 2 つ（Y）。🔴 前の棚 24〜30 → 31〜37: J2（PHIN の相手）のプラグの尻（Y 〜29）が棚に入るため
LEDGE_W_R = 6.0;
DRV_D = 4.0;                                       // 🔒 工具の穴の径（2026-08-23 B 案）。M2 の頭 φ3.0 が落ちる。実測できる上限は #7 の φ4.0（φ4.5 は 4.4 で止まる）
DRV_D_R = 3.6;                                     // 🔒 右の 1 本だけ細くする。抜きの分だけ PowerBoost を押さえる立ち上がりが薄くなるので、
                                                   //    頭 φ3.0 ＋ 0.3 の逃げまで詰めた。工具はどのみち座ぐり（φ3.4）で決まって φ3.2 以下                                   // 右の柱の棚の幅。10 だと X 76〜 になって PHIN/PHOUT の線（口の真上 X 76）に入る
INA_AT = [48, 20 + (39 - ina_size()[1]) / 2, BR_ZB - ina_back_env() - ina_h()];   // 🔒 2026-08-24 L 字を裏に出す分（3.8）だけ下げ、ブリッジの座の柱で受ける
XIAO_WIRE_Y = RSP_BD_Y1 + HOUS_H + 1.8;            // 21.8 XIAO のソケットへ線が入る Y（ソケットの背面の 1.8 後ろ・v2 と同じ）
TUN_SPG = 1.9;                                     // 電池の上のスポンジ
BAT_C0 = [0, LIPO_AT[1] - TUN_CL, LIPO_AT[2]];                                              // 電池の小部屋（v2 と同じ式）
BAT_C1 = [LIPO_AT[0] + LIPO_L + TUN_CL, LIPO_AT[1] + LIPO_W + TUN_CL, LIPO_AT[2] + LIPO_TH + TUN_SPG];
BAT_HOLE_X = BAT_C1[0] + TUN_END_T + 2.6;          // 56.6 電池線がブリッジを下りる穴の X（端板の右 2.6）
CHG_LANE_X = 47.7; CHG_CROSS_Y = 50.5;             // 充電ケーブルが屋根の上を後ろへ走る X（座の板の縁 X 49.7・Z 42.0〜 の手前）/ 受けの前へ横切る Y（つまみの裾 48.4 の後ろ・受け 52.5 の前）
BAT_HOLE_Y = 51.0;                                 // 電池線の穴の Y（INA226 の板の縁 49.5 の後ろ・Type-C の受け 52.5 の前）
// 🔴 後列の口（PWR・REED・INA・TOGGLE）はブリッジの後ろから上へ挿す（⑩）。ハウジングの前面が
//    ブリッジの後端より後ろに要る。v2 は 0.4、v3 の初版は 1.1 ブリッジの下に入っていた。
//    ⇒ ハブを後ろへ送る（変数）。HUB_Y0 11.9 → 13.3
//    🔴 同日、ユーザー決定「先に線を全部挿してから載せる」で、上から挿す必要が消えた。
//    ハウジングの頭（17.7）はブリッジの下面（23.2）より低いので、ブリッジの下に居てよい。⇒ 11.9 に戻す
HUB_Y0 = HUB_Y0_MIN;
TOP_MARGIN = 13.0; KNOB_DX = 6.8; KNOB_YC = 33.3 + 1.6 - 1.1;  // つまみ（v2 の位置＋🔒 1.6 後ろへ・2026-08-22 ユーザー。🔒 2026-08-24 ユーザー: −1.1 前へ。USB の 1 ピンのハウジングがデッキの後ろ角に 1.06 重なった分）
HUB_AT = [HUB_X, HUB_Y0, BOARD_Z];
IN_Y = HUB_Y0 + HUB_W + BACK_CL;                   // 78.9
// 🔴 2026-08-23 **胴の縦は 13 ではなく 8**。`parts.scad` の実測は 胴 13 × 8（✅ 2026-08-16「胴は角い」・それ以前の φ13 は破棄済み）で、
//    `mts102()` は 13 を local X に置く。ハッチ向きの `rotate([-90,0,0])` は X 軸まわりなので 13 は横のまま残り、**縦になるのは 8**。
//    ここで 13 を縦として使っていたのは、破棄されたはずの「胴径 13」の読みの残り。天井が 4.35 高くなっていた
TGL_BODY_X = mts102_w();   // 13 胴の幅（X）
TGL_BODY_Z = mts102_d();   //  8 胴の丈（Z）
TGL_RAIL_Z = BAT_C1[2] + TUN_T + 0.3 + TGL_BODY_Z / 2;   // 43.5 トグルの軸の Z: トンネルの屋根（39.2）に 0.3 浮かせて胴を載せる（🔒 2026-08-23 ユーザー「トンネル側のレールで持つ」）
PB_ZT = BR_ZB - PB_DROP + pb_jst_out() + PB_W;   // 48.15 基板の上端（JST 下向き・v2 と同じ）
PB_ZB = PB_ZT - PB_W;                              // 基板の下端
IN_Z = max(oled_w(), LIPO_AT[2] + LIPO_TH + TUN_SPG, PB_ZT + 0.3, TGL_RAIL_Z + TGL_BODY_Z / 2 + 0.3);   // 48.454（PowerBoost の上端 ＋ 0.3）。🔴 2026-08-24 に一度 PB の項を外して 48.1 になり、板とヘッダが天井に 0.05 入っていた
// 後ろの L の唇。通常: 局所 y 14.0〜19.9 の平らな帯。反転: 後端が micro-USB の端になり、平らなのは y 15.63〜17.82 だけ
LIP_Z0 = PB_ZT - 19.9;                             // 28.25
LIP_Z1 = PB_ZT - 14.0;                             // 34.15   // 48.454（PowerBoost の上端 ＋ 0.3）。トグルの項は 47.8 で負ける。🔴 胴の縦を 13 と誤っていた版は 52.8

// ---- OLED / 天面 / ハッチ --------------------------------------------
OLED_X0 = (IN_X - oled_l()) / 2; OLED_Y1 = 8.5;
// 🔒 2026-08-23 ユーザー「ベゼルの中央になるように下げて」: OLED の Z は**ガラスの中心を外形の前面の中心に合わせて**決める。
//    前の式は OLED_Z0 = IN_Z - oled_w()（＝上辺を天井にツライチ）で、内寸がトグルのために 48.45 → 52.8 へ伸びたとき、
//    増えた 4.35 が全部下の隙間に落ちて窓だけが上がっていた。いまは 4.7 → 1.9（窓は 2.8 下がる）
// max(0, ...) は床より下へ行かせない止め。内寸の高さが OLED の丈（48.1）に迫ると中央に置けなくなる
OLED_Z0 = max(0, (IN_Z + TOP_T - FLOOR_T) / 2 - (oled_glass_y() + oled_glass()[1] / 2));   // 0（IN_Z 48.454 では中央は −0.27 なので床に置く）
OLED_L_W = 6.0;    // L の足の幅（穴の周り）。🔒 8 → 6（2026-08-23 B 案: 両端にフロントの耳の場所を作る）
OLED_L_T = 2.0;    // L の足の厚み（Y）
OLED_L_DROP = IN_Z - (OLED_Z0 + oled_mount()[1][1]) + 5.5;   // 10.85 天面の下面から足の下端まで（天井→上の穴 5.35 ＋ 穴の下 5.5）。OLED を下げた分だけ足が伸びる
SCR_HEAD_D = 3.8; SCR_HEAD_H = 1.3;   // M2 なべ頭

// 🔒 トグルは天板の棚に載る（2026-08-22 ユーザーの絵）。ハッチは穴だけで、外の六角ナットが Y の止め
SHELF_HUNG = false;   // 🔴 2026-08-23 ユーザー「天井からの板は要らない」: 天面から吊る棚（U＋フランジ＋天面の鉤）をやめる。トグルはトンネル側のレールで持つ（次の段）
TGL_BODY_D = TGL_BODY_X; SHELF_T = 1.6; SHELF_CL = 0.3; MTS_BODY_H_ = 12.0;   // 棚（🔒 廃止済み・SHELF_HUNG = false）が使う胴の幅。MTS_BODY_H_ は胴の奥行き（parts.scad MTS_BODY_H）
TGL_AT  = [40, SHELF_HUNG ? IN_Z - TGL_BODY_D / 2 - SHELF_T - SHELF_CL : TGL_RAIL_Z];   // 軸: レール持ちなら屋根の上 46.0。吊りなら天井から 8.4（v2 は 4.3）
CHG_ON  = "left";         // 🔴 2026-08-23 ユーザー「充電 USB の口をここに」: 左の壁・後ろ下（電池の蓋の下・後ろの角の手前）。"hatch" で前の置き方に戻る
CHG_C_LW = [IN_Y - 0.8 - 3.5, 10.5];   // [67.7, 10.5] ハッチの内面から 0.8（3.5 = 胴の厚み TC_T 7 の半分。TC_T は後で定義）・胴の下はハブの基板の上面（4.1）から 0.4   // 左の壁の口の中心 [Y, Z]（ユーザーが上面図・左側面図で指した枠 Y 61〜68・Z 4〜16 の中心）。🔒 縦置き（口は Z 9.54 × Y 3.86・ユーザー）
CHG_C_B = [63.0, 35.5];   // 🔒 充電口はハッチ [X, Z]。ユーザー「後ろから見て左上」＝XIAO の壁の側 → 71.5。🔴 2026-08-23 Type-C の胴（奥行 25）が PowerBoost の出力パッドと PWR の線の道に被さるので 63 へ（ユーザー「やってみて」）

BOSS = 7.0; BOSS_H = 9.0;   // 四隅の柱（M2.5・7×7×9）。🔴 BOSSES_B より前に置く（後ろだと undef で柱が原点に落ちる）
KNOB_TRIM_X = PB_FACE_X - 2.5 - 1.27 - 0.3;   // 79.1   // 反転 74.4 / 通常 79.1（L 型のハウジング） 🔒 2026-08-24 上下を戻したら JST（X 78〜）・インダクタ（79.9〜）・4 ピンヘッダ（74.7〜）が座の板の下に来た（58mm³）。（旧）79.1 つまみの座の板と本体の右端はここから右を落とす。🔒 2026-08-24 L 型ヘッダのハウジング（ピン中心 2.5 ± 1.27）のため 80.4 → 79.1（それまでは PowerBoost の C6 の 2.5）
// ---- 尻尾（トグルのレバーに挿すカバー。v2 そのまま。アンテナの通り道も同じ）----
TAIL_L = 34.0; TAIL_D0 = 13.0; TAIL_D1 = 3.5; TAIL_BORE = 3.2; TAIL_ANG = 25.0;
TAIL_GAP = 5.0 + 0.5;   // 5.5 模型のトグルの原点（ハッチの内面）からブッシングの先（5.0）＋0.5。尻尾もその原点で回す（レバーと同じ軸）
ANT_CH_D = 1.6; ANT_OFF = 4.5;
module tail_cap() {
    difference() {
        hull() { translate([0, 0, TAIL_D0 / 2]) sphere(d = TAIL_D0, $fn = 48); translate([0, 0, TAIL_L - TAIL_D1 / 2]) sphere(d = TAIL_D1, $fn = 32); }
        translate([0, 0, -0.01]) cylinder(d = TAIL_BORE, h = 9.5, $fn = 32);
        translate([0, ANT_OFF, -0.01]) cylinder(d = ANT_CH_D, h = 11, $fn = 16);
        translate([0, 0, 9]) cylinder(d = ANT_CH_D, h = TAIL_L - 9 - 1.2, $fn = 16);
        hull() { translate([0, ANT_OFF, 10]) cylinder(d = ANT_CH_D, h = 0.01, $fn = 16); translate([0, 0, 11]) cylinder(d = ANT_CH_D, h = 0.01, $fn = 16); }
    }
}
module tail_at() { color("#9aa5b1") translate([TGL_AT[0], IN_Y, TGL_AT[1]]) rotate([-90, 0, 0]) rotate([TAIL_ANG, 0, 0]) translate([0, 0, TAIL_GAP]) tail_cap(); }
// ---- 天面のレイアウト（v2 §2.5 の意匠をそのまま: 左にスピーカーと会話ボタンを縦積み・右につまみ・マージン 13）----
Z_TOP = IN_Z + TOP_T;
SPK_L = spk_l(); SPK_W = spk_w(); SPK_TH = spk_th(); SPK_DIA = spk_dia();
SPK_RIM = 0.8; SPK_RIM_M = 0.8; SPK_REL = 0.4; EMB_H = 1.2; EMB_M = 3.0;
SPK_EMB_W = SPK_DIA[0] + EMB_M * 2; SPK_EMB_D = SPK_DIA[1] + EMB_M * 2;
SPK_C = [TOP_MARGIN + SPK_EMB_W / 2, TOP_MARGIN + SPK_EMB_D / 2];
SPK_X = SPK_C[0] - SPK_L / 2; SPK_Y = SPK_C[1] - SPK_W / 2;
// 会話ボタン（v2 §4.7 そのまま）
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
BTN_AT = [TOP_MARGIN + BTN_DISH_L / 2, TOP_MARGIN + SPK_EMB_D + TOP_MARGIN + BTN_DISH_W / 2];
KNOB_AT = [IN_X - TOP_MARGIN - knob_dish_d() / 2 + KNOB_DX, KNOB_YC, Z_TOP];
// ReSpeaker の頭を押さえるリブ（v2: 前のリブ X 39.1〜45.1 と右の腕。押し代 0.3）
RSP_TOP = RSP_Z + respeaker_H(); RSP_PRESS = 0.3; RIB1_X = 39.1; RIB1_W = 6.0; RSP_ARM_X0 = 69.5; RSP_ARM_X1 = 74.2; RSP_ARM_T = 2.0;   // 🔴 2026-08-23 腕 X 74〜78.7 → 69.5〜74.2: OLED の右のビス（X 76.5・M2×6 の先が L の後ろへ 2.4 出る）を避ける
// トグルの棚の爪（天板の裏）: 棚の両側のフランジが −Y へ滑り込む L 字 2 本
SHELF_HOOK_T = 1.6; SHELF_HOOK_LIP = 1.5; SHELF_FLANGE_T = 1.2;

// ---- フロント（OLED の窓・ベベル・マイクのヒゲ。v2 §4.6 そのまま）----
WIN_CR = 2.0; WIN_CH = 1.2; WIN_R = 0.4;
WIN_X0 = OLED_X0 + oled_glass_x() - 0.3;  WIN_X1 = WIN_X0 + oled_glass()[0] + 0.6;
WIN_Z0 = OLED_Z0 + oled_glass_y() - 0.3;  WIN_Z1 = WIN_Z0 + oled_glass()[1] + 0.6;
WSK_L = 6.0; WSK_W = 1.0; WSK_CH = 0.5; WSK_R = 0.4; WSK_ANG = 4;
// ---- 外周の角丸（v2 と同じ。12 辺と 8 隅を半径 WALL で丸める。🔒 天面とフロントの継ぎ目は角丸の真ん中）----
CHAM = WALL; EDGE_ROUND = true;
OUT_X = IN_X + 2 * WALL; OUT_Y = IN_Y + BEZ_T + HATCH_T; OUT_Z = IN_Z + TOP_T + FLOOR_T;

// ---- まな板（床）----
// ① ハブ: 4 本のビスを**下から**通し、ナットは板の上。頭は床の裏のザグリ（床は肩・スタンドに載る面なので頭を出さない）
M3_CLEAR = 3.4; M3_NAF = 5.8; M3_NT = 2.6; M3_HEAD_D = 6.0; M3_HEAD_H = 2.2;   // ハブの穴 φ3.2 → M3（ナット 5.5 ＋ 0.3 / 2.4 ＋ 0.2）
HUB_POST_D = 7.0;                                                          // ハブの下の柱（半田面の逃げ BOARD_Z の高さ）
HUB_HOLES = [for (sx = [-1, 1], sy = [-1, 1]) [HUB_AT[0] + HUB_L / 2 + sx * HUB_MOUNT[0] / 2, HUB_AT[1] + HUB_W / 2 + sy * HUB_MOUNT[1] / 2]];
// ② ReSpeaker: 床の溝に立てる（v2 の lower と同じ形）。前の土手（全長）・後ろの土手（両端だけ。裏面の部品とハブを避ける）・
//    左右の端の振れ止め。板の下端（Z 2.5）は座に載る。🔴 初版は前後とも全長のリブ（高さ 8.5）にして裏面の部品に 55.9mm3 当たった
RSP_SLOT_CL = 0.2;
RSP_SLOT_Y0 = RSP_BD_Y0 - RSP_SLOT_CL; RSP_SLOT_Y1 = RSP_BD_Y1 + RSP_SLOT_CL;   // 7.985〜10.235
RSP_RIB_X0 = 8.0; RSP_RIB_X1 = IN_X - 8.0;                                    // 座の X（四隅の柱 X 0〜7 / 79〜86 を避ける）
// OLED: 下辺の後ろに低いリブ（前はフロントの板が止める）。OLED の裏 4.6 と ReSpeaker の前のリブ 6.5 の間
OLED_RIB_Y0 = oled_back() + 0.2; OLED_RIB_T = 1.2; OLED_RIB_H = 5.0;
// ③ 壁 ↔ 床: 壁の内面の下の柱（四隅）にナット（上から落とす）、ビスは床の裏から。頭は床の裏のザグリ
BOSS_B_H = 12.0;                                                            // 下の柱の高さ。🔒 ユーザーの手持ちが M2×15（12 は無い）なので、床 2 ＋ 柱 12 で先が 1mm 出るだけにした（2026-08-23）
BOSSES_B = (CHG_ON == "left") ? [[0, 0], [IN_X - BOSS, 0], [IN_X - BOSS, IN_Y - BOSS]]                 // 🔒 2026-08-23 後ろ左の床ビスはやめる（充電口のハウジングの場所・ユーザー「良い」）
                              : [[0, 0], [IN_X - BOSS, 0], [0, IN_Y - BOSS], [IN_X - BOSS, IN_Y - BOSS]];   // 下の柱は四隅そのもの（前の柱を Y 8.4 に下げたのは天面の OLED の L のため。下には無い）。ハブ（X 6〜80・Y 11.9〜）を避ける
// ④ ハッチの爪: 床の後ろの帯（Z 0〜2.5）にポケット 2 つ。爪の唇がバーの下へ −Y に滑り込む。上はトグルのナット
CLAW_X = [[12, 20], [66, 74]];                                              // 爪の X（2 つ）
CLAW_STRIP_Y0 = IN_Y - 6.0; CLAW_STRIP_H = 2.5;                              // 帯
CLAW_BAR_Y0 = IN_Y - 4.0; CLAW_BAR_Y1 = IN_Y - 2.0; CLAW_BAR_Z0 = 1.5;       // バー（Y 73.5〜75.5・Z 1.5〜2.5）。その後ろ（Y 75.5〜77.5）は脚が通る
CLAW_LIP_T = 0.8; CLAW_LIP_L = 3.0; CLAW_LEG_T = 1.0; CLAW_CL = 0.2;         // 唇の厚み / 長さ（−Y へ）/ 脚の厚み / 隙間

echo(str("v3 内寸 ", IN_X, " x ", IN_Y, " x ", IN_Z,
         "  ブリッジ Z ", BR_ZB, "-", BR_ZT, "  電池の頭 ", LIPO_AT[2] + LIPO_TH,
         "  後列の口 Y ", port_at("PWR")[1], " ハッチ内面 Y ", IN_Y, "  ブリッジの後端 Y ", BR_Y1));

include <case_v3_shutter.scad>   // 電池の蓋（v2 §2.8 の移植）。BAT_C0/C1・WALL・BR_ZB/BR_ZT を使う

// ============================================================
// 部品群（組む順番の単位）
// ============================================================
module housing(id) {
    // 🔴 2026-08-24 精緻化: ハウジングは板の上に直接ではなく**ピンヘッダの樹脂（2.5）の上に座る**。
    //    それまで頭を 14.1（板上 10）として v3 の検査を通していたが、実際は 16.6・線の曲がり込みで 20.2。
    //    hub_board.scad の「裸のヘッダで数えるな」（2026-08-15 ユーザー指摘×2）と同じ忘れ方をここでもしていた。
    p = port_at(id); wl = port_wl(id); HDR_PL = 2.5;   // 2.54mm ピンヘッダの樹脂の高さ（parts.scad PB_HDR_PLASTIC と同じ）
    color("#c93") translate([p[0] - wl[0] / 2, p[1] - wl[1] / 2, p[2]]) cube([wl[0], wl[1], HDR_PL]);                 // ヘッダの樹脂
    color("#333") translate([p[0] - wl[0] / 2, p[1] - wl[1] / 2, p[2] + HDR_PL]) cube([wl[0], wl[1], HOUS_H]);       // ハウジング
    color("#c0392b", 0.6) translate([p[0], p[1], p[2] + HDR_PL + HOUS_H]) cylinder(d = HOUS_R, h = HOUS_R, $fn = 24);
}
module hub_at() { translate(HUB_AT) hub_board(false); }
module respeaker_at() { translate([RSP_X + respeaker_L(), RSP_BD_Y1, RSP_Z]) rotate([0, 0, 180]) respeaker_lite(); }
module oled_at() { translate([OLED_X0, OLED_Y1, OLED_Z0]) rotate([90, 0, 0]) oled_242(); }

// ① まな板 ＋ ② ReSpeaker ＋ ③⑤ 挿した線
MP = "";   // まな板側を1つに: floor / hub / rsp / hous（"" で全部）
SP = "";   // 側面構造体側を1つに: walls / bridge / ina / pb / lipo / boss
module m_(k) if (MP == "" || MP == k) children();
module s_(k) if (SP == "" || SP == k) children();
module hex_pocket_af(af, h) cylinder(d = af / cos(30), h = h, $fn = 6);
function bev_pts(c, k, n = 10) = [for (i = [0 : n]) let (t = i / n, p = (1 - k) * c / 2) [2 * t * (1 - t) * p + t * t * c, (1 - t) * (1 - t) * c + 2 * t * (1 - t) * p]];
module win_rrect(g = 0) { hull() for (x = [WIN_X0 + WIN_CR, WIN_X1 - WIN_CR], z = [WIN_Z0 + WIN_CR, WIN_Z1 - WIN_CR]) translate([x, z]) circle(r = WIN_CR + g, $fn = 40); }
module win_bev_slab(g, y) { translate([0, y + 0.01, 0]) rotate([90, 0, 0]) linear_extrude(0.01) win_rrect(g); }
module win_chamfer_cut() { hull() { win_bev_slab(WIN_CH, -BEZ_T - 0.5); for (p = bev_pts(WIN_CH, WIN_R)) win_bev_slab(p[1], -BEZ_T + p[0]); } }
module whisker_plate(l, w, y) { translate([-l / 2, y, -w / 2]) rotate([90, 0, 0]) spk_obround(l, w, 0.01); }
// 🔴 2026-08-23 v2 から写すとき 2 つ目の hull（内面まで貫くスリット）が落ちていて、外面を 0.5 彫っただけのベベルになっていた
//    （ユーザー「マイクの穴空いてない？」）。外のベベル＋貫通の 2 段で 1 本のヒゲ
module whisker_cut(l, w, ch) {
    fy = -BEZ_T / 2;
    hull() { whisker_plate(l + ch * 2, w + ch * 2, fy - 0.5); for (p = bev_pts(ch, WSK_R)) whisker_plate(l + p[1] * 2, w + p[1] * 2, fy + p[0]); }   // 外面のベベル
    hull() { whisker_plate(l, w, fy + ch); whisker_plate(l, w, fy + BEZ_T + 1); }                                                                   // 内面まで貫く（v2 と同じ）
}
module whiskers_cut() {   // マイクのヒゲ（位置は ReSpeaker の CAD から）
    for (ref = ["U4", "U5"]) {
        m = cad_part(ref, -1);
        bx = RSP_X + respeaker_L() - (m[2] + m[3]) / 2; bz = RSP_Z + (m[4] + m[5]) / 2; out = (bx < IN_X / 2) ? 1 : -1;
        for (i = [-1, 0, 1]) translate([bx - out * 1.0, -BEZ_T / 2, bz + i * 3.6]) rotate([0, out * i * WSK_ANG, 0]) whisker_cut(WSK_L, WSK_W, WSK_CH);
    }
}
module cham_box(p0, sz, k) { hull() { translate([p0[0] + k, p0[1], p0[2]]) cube([sz[0] - 2 * k, sz[1], sz[2]]); translate([p0[0], p0[1] + k, p0[2]]) cube([sz[0], sz[1] - 2 * k, sz[2]]); translate([p0[0], p0[1], p0[2] + k]) cube([sz[0], sz[1], sz[2] - 2 * k]); } }
module round_box(p0, sz, k) { hull() for (x = [p0[0] + k, p0[0] + sz[0] - k], y = [p0[1] + k, p0[1] + sz[1] - k], z = [p0[2] + k, p0[2] + sz[2] - k]) translate([x, y, z]) sphere(r = k, $fn = 48); }
module outer_envelope() { if (EDGE_ROUND) round_box([-WALL, -BEZ_T, -FLOOR_T], [OUT_X, OUT_Y, OUT_Z], CHAM); else cham_box([-WALL, -BEZ_T, -FLOOR_T], [OUT_X, OUT_Y, OUT_Z], CHAM); }
// 部品を外周の角丸で切る。スピーカーの盛り上げ（天面の上 EMB_H）だけは許す（v2 と同じ）
module rounded() { intersection() { children(); union() { outer_envelope(); translate([SPK_X - 6, SPK_Y - 6, Z_TOP - 1]) cube([SPK_L + 12, SPK_W + 12, EMB_H + 1]); } } }
module floor_v3() {
    difference() {
        union() {
            // 🔒 2026-08-23 ユーザー: 丸みは フロント＝天面 ＞ 側面 ＞ 背面 ＞ 底面 の順で当該パーツが取る（側面は板のままなので取らない）。
            //    床は前後の唇（Y −2〜0 と 72〜74）を手放し、下前の丸みはフロント・下後ろの丸みはハッチが持つ。床が持つのは左右の下の稜線だけ
            color("#9aa5b1") translate([-WALL, 0, -FLOOR_T]) cube([IN_X + 2 * WALL, IN_Y, FLOOR_T]);
            // ① ハブの柱（半田面の逃げ）
            color("#9aa5b1") for (h = HUB_HOLES) translate([h[0], h[1], 0]) cylinder(d = HUB_POST_D, h = BOARD_Z, $fn = 32);
            // ② ReSpeaker の溝（v2 と同じ）
            color("#9aa5b1") translate([RSP_RIB_X0, RSP_SLOT_Y0, 0]) cube([RSP_RIB_X1 - RSP_RIB_X0, RSP_SLOT_Y1 - RSP_SLOT_Y0, RSP_Z]);            // 座（板の下端 Z 2.5）
            color("#9aa5b1") translate([RSP_RIB_X0, RSP_BD_Y0 - 2, 0]) cube([RSP_RIB_X1 - RSP_RIB_X0, 2 - RSP_SLOT_CL, RSP_Z + 3]);             // 前の土手（X 8〜78・Z 〜5.5。四隅の下の柱を避ける）
            color("#9aa5b1") for (g = [[RSP_X, HUB_AT[0] - 0.3 - RSP_X, 5.0], [80, 4, RSP_Z + 4]])                                              // 後ろの土手（両端だけ。左は 3.5mm ジャックの胴を避けて Z 5 まで）
                translate([g[0], RSP_BD_Y1 + 0.3, 0]) cube([g[1], HUB_Y0 - 0.3 - (RSP_BD_Y1 + 0.3), g[2]]);                                    // 厚みはハブの手前 0.3 まで（1.265。v2 の 1.7 はハブに 0.135 入っていた）
            color("#9aa5b1") for (g = [[RSP_X - 1.6, 5.0], [RSP_X + respeaker_L(), RSP_Z + 6]])                                               // 左右の端の振れ止め（X）
                translate([g[0], RSP_BD_Y0 - 2, 0]) cube([1.6, 6, g[1]]);
            // OLED の下辺の後ろのリブ
            // 🔒 2026-08-24 フィルムが下の切り欠き（幅 23・ユーザー実測）から裏へ回る所はリブを切る。リブは両端だけ残る
            color("#9aa5b1") difference() {
                translate([OLED_X0 + 2, OLED_RIB_Y0, 0]) cube([oled_l() - 4, OLED_RIB_T, OLED_RIB_H]);
                translate([OLED_X0 + oled_l() / 2 - 23 / 2 - 1, OLED_RIB_Y0 - 1, -1]) cube([23 + 2, OLED_RIB_T + 2, OLED_RIB_H + 2]);
            }
            // ④ ハッチの爪の帯とバー
            color("#9aa5b1") translate([RSP_RIB_X0, CLAW_STRIP_Y0, 0]) cube([RSP_RIB_X1 - RSP_RIB_X0, IN_Y - CLAW_STRIP_Y0, CLAW_STRIP_H]);
        }
        // ① ハブのビス: 通し穴＋裏のザグリ
        for (h = HUB_HOLES) translate([h[0], h[1], 0]) {
            translate([0, 0, -FLOOR_T - 1]) cylinder(d = M3_CLEAR, h = FLOOR_T + BOARD_Z + 2, $fn = 24);
            translate([0, 0, -FLOOR_T - 1]) cylinder(d = M3_HEAD_D, h = M3_HEAD_H + 1, $fn = 32);
        }
        // ③ 壁のビス（四隅の下の柱へ）: 通し穴＋裏のザグリ
        for (b = BOSSES_B) { front = (b[1] < IN_Y / 2);
            translate([b[0] + BOSS / 2, b[1] + (front ? BOSS_B_DY_F : BOSS) / 2, 0]) {
                translate([0, 0, -FLOOR_T - 1]) cylinder(d = front ? M2_CLEAR : SCR_D, h = FLOOR_T + 2, $fn = 24);
                translate([0, 0, -FLOOR_T - 1]) cylinder(d = front ? M2_CB : SCR_CB, h = (front ? M2_CBT : SCR_CBT) + 1, $fn = 32);
            }
        }
        // ④ 爪のポケット（+Y に開く）
        for (cx = CLAW_X) {
            translate([cx[0], CLAW_STRIP_Y0 + 1.0, 0.3]) cube([cx[1] - cx[0], IN_Y - CLAW_STRIP_Y0, CLAW_BAR_Z0 - 0.3]);                    // 唇の通り道（Y 72.5〜77.5・Z 0.3〜1.5）
            translate([cx[0], CLAW_BAR_Y1, CLAW_BAR_Z0 - 0.01]) cube([cx[1] - cx[0], IN_Y - CLAW_BAR_Y1 + 1, CLAW_STRIP_H]);                  // バーの後ろは上も開ける（脚が通る）
        }
    }
}
// 壁の下の柱（四隅・ナットは上から落とす・ビスは床の裏から）
// 🔴 前の下の柱は Y 5.5 まで。ReSpeaker のマイクの先（Y 5.91）が右端の柱の真上に居て、6.0 だと降ろすときに 13.3mm3 当たる。
//    5.5 に M2.5 のナット（5.3）は入らない → これが「ハブ以外 M2」の決め手
BOSS_B_DY_F = 5.5;
M2_CLEAR = SCR_D; M2_NAF = NUT_AF; M2_NT = NUT_T; M2_CB = SCR_CB; M2_CBT = SCR_CBT;   // 名前の互換（今は全部 M2）
module bottom_boss(b) {
    dy = (b[1] < IN_Y / 2) ? BOSS_B_DY_F : BOSS;
    difference() {
        translate([b[0], b[1], 0]) cube([BOSS, dy, BOSS_B_H]);
        translate([b[0] + BOSS / 2, b[1] + dy / 2, BOSS_B_H - NUT_T]) hex_pocket(NUT_T + 1);
        translate([b[0] + BOSS / 2, b[1] + dy / 2, -1]) cylinder(d = SCR_D, h = BOSS_B_H + 2, $fn = 24);
    }
}
// ハッチの爪（ハッチの内面の下端から）
module hatch_claws() {
    for (cx = CLAW_X) {
        translate([cx[0] + CLAW_CL, IN_Y - CLAW_LEG_T, 0.3 + CLAW_CL]) cube([cx[1] - cx[0] - 2 * CLAW_CL, CLAW_LEG_T + 0.01, CLAW_STRIP_H - 0.3 - CLAW_CL + 0.01]);   // 脚（ハッチの内面に沿って下りる・Y 76.5〜77.5）
        translate([cx[0] + CLAW_CL, CLAW_BAR_Y0 + CLAW_CL, 0.3 + CLAW_CL]) cube([cx[1] - cx[0] - 2 * CLAW_CL, IN_Y - (CLAW_BAR_Y0 + CLAW_CL), CLAW_LIP_T]);   // 唇（脚からバーの下を −Y へ。バーの前端まで）
    }
}
module manaita(plugged = PLUGGED_9) {
    m_("floor") floor_v3();
    m_("hub") hub_at();
    m_("rsp") respeaker_at();
    m_("hous") for (id = plugged) housing(id);
}
module hex_pocket(h) cylinder(d = NUT_AF / cos(30), h = h, $fn = 6);
module nut_ledge(x0, y0, w, l, ztop) {   // 壁の内面の棚。上面に六角ポケット、ビスは上から
    difference() {
        translate([x0, y0, ztop - LEDGE_H]) cube([w, l, LEDGE_H]);
        translate([x0 + w / 2, y0 + l / 2, ztop - NUT_T]) hex_pocket(NUT_T + 1);
        translate([x0 + w / 2, y0 + l / 2, ztop - LEDGE_H - 1]) cylinder(d = SCR_D, h = LEDGE_H + 2, $fn = 24);
    }
}
module screw_cut(x, y, ztop) {   // ブリッジの上からのビス穴（座ぐり付き）
    translate([x, y, BR_ZB - 1]) cylinder(d = SCR_D, h = BR_DEPTH + 2, $fn = 24);
    translate([x, y, ztop - SCR_CBT]) cylinder(d = SCR_CB, h = SCR_CBT + 1, $fn = 24);
}
COL_Y0 = PB_Y0 + PB_L + PB_REAR_CL;                // 60.37 柱の前面
SCR_L = [for (yy = LEDGE_L_Y) [LEDGE_W / 2, (yy[0] + yy[1]) / 2]];                 // 左のビス 2 本 [X, Y]
SCR_R = [IN_X - LEDGE_W_R / 2, COL_Y0 + POST_W / 2];                              // 右の柱のビス
// 電池のトンネル（v2 の battery_tunnel から。BTN2 の溝は天面側の話なのでここでは無し）
function knob_seat_x0() = IN_X - TOP_MARGIN - knob_dish_d() / 2 + KNOB_DX - knob_bay_x() / 2;
function knob_seat_x1() = knob_seat_x0() + knob_bay_x();
module battery_tunnel() {
    difference() {
        // 🔒 奥（+X）の端板は v2 と同じ 1.6 通し（2.0 だと端板が X 54.4 まで来て、つまみの裾と AS5600 の板（X 54.2〜）に 61mm3 入る）
        translate([BAT_C0[0], BR_Y0, BAT_C0[2]]) cube([BAT_C1[0] - BAT_C0[0] + TUN_END_T, BR_Y1 - BR_Y0, BAT_C1[2] + TUN_T - BAT_C0[2]]);
        translate([BAT_C0[0] - WALL - 2, BAT_C0[1], BAT_C0[2]]) cube([BAT_C1[0] - BAT_C0[0] + WALL + 2, BAT_C1[1] - BAT_C0[1], BAT_C1[2] - BAT_C0[2]]);   // 電池の通り道（左へ抜ける）
        translate([BAT_C1[0] - 1, BAT_C0[1] + 1, BAT_C0[2] + 1]) cube([TUN_END_T + 2, BAT_C1[1] - BAT_C0[1] - 2, LIPO_TH - 2]);   // 電池線の口（奥の端板）
        translate([knob_seat_x0(), BR_Y0 - 1, BAT_C1[2] - 0.01]) cube([knob_seat_x1() - knob_seat_x0(), BR_Y1 - BR_Y0 + 2, TUN_T + 2]);   // 座の下は天井を抜く
        // 充電ケーブルの下り口: 屋根の奥右の角（X 46.6〜座の切り欠き・Y 48.4〜52.6）を抜く。ケーブル（φ3.6）は屋根の上 Z 41.2 から
        //   ここで Z 39.5（座の板 41.95 の下・スポンジ 37.2 の上）へ下り、端板の切り欠きを横切って Type-C の受けの前へ行く
        //   🔒 同日、充電口を左の壁へ移したので無し（CHG_ON == "hatch" のときだけ）
        if (CHG_ON == "hatch") translate([CHG_LANE_X - 2.1, CHG_CROSS_Y - 2.1, BAT_C1[2] - 0.01]) cube([knob_seat_x0() - CHG_LANE_X + 2.2, 4.2, TUN_T + 2]);
        // 会話ボタンの受け（天面から下りる）がトンネルの屋根と重なる → 屋根の板だけを抜く（v2 と同じ。幅は受けの柱 2×(3.6+1.2)＋0.6）
        translate([BTN_AT[0] - BTN_POST_I - BTN_PKT_T - 0.3, BR_Y0 - 1, BAT_C1[2]]) cube([2 * (BTN_POST_I + BTN_PKT_T) + 0.6, BR_Y1 - BR_Y0 + 2, TUN_T + 0.01]);
        // 🔴 つまみの下の部品（AS5600 の板とその上の柱・X 52.4〜・Z 32.9〜37.2・Y 23.2〜46.6）が奥の端板（X 52.4〜54.0）に 37.8mm3 入る。
        //    端板のその範囲だけ Z 32.4 から上を抜く（電池の +X の止めは Z 29.3〜32.4 の 3.1 が残る）。v2 の「座の下は天井を抜く」と同じ扱い
        //    🔴 2026-08-23 Y 47.1 → 52.5 まで延ばした: 充電ケーブルが端板を Z 34〜37 で横切る（電池の +X の止めは下の 3.1 が全長で残る）
        //    🔒 同日、充電口を左の壁へ移したので Y 47.1 に戻す
        translate([BAT_C1[0] - 0.01, 23.2 - 0.5, 32.9 - 0.5]) cube([TUN_END_T + 1, 46.6 - 23.2 + 1.0, IN_Z]);
        // 🔴 トグルの棚（X 29〜51・Z 31.3〜）とトグルの胴（Y 59.5〜）がトンネルの後ろの壁（Y 58.3〜60.3・Z 〜39.2）に入る（113mm3）。
        //    棚の下だけ後ろの壁と天井の後ろの縁を Z 31.0 まで切り欠く。電池の +Y の止めはその範囲で 1.7 残る（他は全高）
        //    🔒 2026-08-23 棚をやめたので切り欠きも無し（胴 Y 60〜・Z 39.5〜 は壁の上 39.2 に掛からない）。電池の +Y の止めは全高に戻る
        if (SHELF_HUNG) translate([TGL_AT[0] - TGL_BODY_D / 2 - SHELF_T - SHELF_CL - 0.3, BAT_C1[1] - 0.01, 31.0])
            cube([TGL_BODY_D + 2 * (SHELF_T + SHELF_CL) + 0.6, BR_Y1 - BAT_C1[1] + 1, IN_Z]);
    }
}
// 波板（v2 §2.6 そのまま）: 平らな上板 1.6 ＋ 波（部材 2.0・落下前提）＋ 下弦 2.0。山と谷はスパン方向（X）に走る
BR_T = 2.0; BR_TOP_T = 1.6; BR_WAVES = 6;
module bridge_section() { intersection() { translate([BR_Y0, BR_ZB]) square([BR_Y1 - BR_Y0, BR_DEPTH]); bridge_section_raw(); } }   // 波を前後の面で切りそろえる（v2 と同じ。丸が 1.0 出て XIAO ソケットの頭に 8.2mm3 当たる）
module bridge_section_raw() {   // Y-Z 断面
    translate([BR_Y0, BR_ZT - BR_TOP_T]) square([BR_Y1 - BR_Y0, BR_TOP_T]);
    st = (BR_Y1 - BR_Y0) / BR_WAVES;
    for (i = [0 : BR_WAVES - 1]) hull() for (k = [i, i + 1])
        translate([BR_Y0 + k * st, (k % 2 == 0) ? BR_ZB + BR_T / 2 : BR_ZT - BR_TOP_T - BR_T / 2]) circle(d = BR_T, $fn = 16);
    translate([BR_Y0, BR_ZB]) square([BR_Y1 - BR_Y0, BR_T]);
}
module bridge_v3() {   // 波板＋トンネル＋足・柱・L
    difference() {
        union() {
            color("#b6c0cc") rotate([90, 0, 90]) linear_extrude(BR_X1) bridge_section();                                   // 波板（X 0〜78）
            // ビスの所だけ中実（波の中は空洞なので、座ぐりとナット側の受けが要る）。左の棚の上 2 つ（幅 10 × 7）
            color("#b6c0cc") for (sc = SCR_L) translate([0, sc[1] - 3.5, BR_ZB]) cube([LEDGE_W, 7, BR_DEPTH]);
            // 🔒 INA226 の受け（2026-08-24）: 穴の位置だけ波を中実にして、下からビス・中にナット。
            //    穴は写真の射影読み ⚠ ±1（INA_HOLES）。値はパラメータなので、着荷実測で INA_HOLES を直せばここも動く。ブリッジは元々「INA の受け待ち」で未印刷
            color("#b6c0cc") for (h = ina_holes()) translate([INA_AT[0] + h[0] - 4, INA_AT[1] + ina_size()[1] - h[1] - 4, BR_ZB - ina_back_env()]) cube([8, 8, BR_DEPTH + ina_back_env()]);   // 裏出しの分だけ座の柱を下へ
            color("#b6c0cc") battery_tunnel();
            // 右端: 前の足（基板の前）と後ろの柱（基板の後ろ）で壁まで。X は基板の部品面 78.0 から壁 86 まで
            color("#b6c0cc") translate([BR_X1, BR_Y0, BR_ZB]) cube([IN_X - BR_X1, PB_Y0 - PB_FRONT_CL - BR_Y0, BR_DEPTH]);
            color("#b6c0cc") translate([BR_X1 - 2, COL_Y0, BR_ZB]) cube([IN_X - BR_X1 + 2, POST_W, BR_DEPTH]);
            // 🔴 2026-08-23 柱と L が本体から **0.035 離れていた**（波板の後端 60.335 ↔ 柱の前面 COL_Y0 60.37）。
            //    `BR_Y1_R` が定義だけで一度も使われておらず、「右端だけ後ろへ延ばす」が入っていなかった。
            //    柱と重なる X（BR_X1-2 〜 BR_X1）だけ、波板の後端を BR_Y1_R まで延ばして繋ぐ
            //    🔒 2026-08-23 ユーザー「剥がす時危険なので」: 幅を 2 → **5**（X 73〜78）。PWR の口（X 63〜71.24）
            //       から立ち上がる線との空きは 1.76 残る
            color("#b6c0cc") translate([BR_X1 - 5, BR_Y1 - 0.01, BR_ZB]) cube([5, BR_Y1_R - BR_Y1 + 0.01, BR_DEPTH]);
            // 🔒 後ろの L（ユーザー案）: 柱から立ち上がり、基板の後ろの縁に被さって基板を壁へ押さえる（X の止め）
            // 🔒 2026-08-23 ユーザー「立ち上がりを X に伸ばしておいた方が良い」: 工具の穴で Y が 2.5 → 1.20 になった分を
            //    X の幅で取り戻す。−X の端は**柱の −X の面**（BR_X1 − 2）まで。そこまでは真下が柱（Z 23.2〜29.3）なので宙に浮かない
            color("#2f855a") translate([RISE_X0, COL_Y0, BR_ZT - 0.01])
                cube([IN_X - RISE_X0, 2.5, LIP_Z1 - BR_ZT + 0.01]);                                        // 柱の上の立ち上がり
            color("#2f855a") translate([PB_FACE_X - LIP_GAP - LIP_T, PB_Y0 + PB_L - LIP_OVER, LIP_Z0])
                cube([LIP_T, LIP_OVER + PB_REAR_CL + 0.01, LIP_Z1 - LIP_Z0]);                               // 縁に被さる唇
        }
        for (sc = SCR_L) screw_cut(sc[0], sc[1], BR_ZT);
        for (h = ina_holes()) translate([INA_AT[0] + h[0], INA_AT[1] + ina_size()[1] - h[1], 0]) {
            translate([0, 0, BR_ZB - ina_back_env() - 1]) cylinder(d = 2.4, h = BR_DEPTH + ina_back_env() + 2, $fn = 24);            // ビス M2（下から）
            translate([0, 0, BR_ZB - ina_back_env() + 2.0]) rotate([0, 0, 30]) cylinder(d = 4.0 / cos(30) + 0.3, h = 2.0, $fn = 6);   // ナットの座（板 1.6 ＋ 2.0 → M2×6 で届く）
        }
        screw_cut(SCR_R[0], SCR_R[1], BR_ZT);
        // 🔒 2026-08-23 工具の穴（ユーザー B 案）。3 本とも上から入れるが、頭の座の真上が塞がっていて
        //    ビスを立てることも回すこともできなかった（左 2 本は電池の小部屋の屋根まで 9.5、右 1 本は
        //    座ぐりが袋穴で 2.6）。M2×15 を立てるには 16.3 要る。⇒ 塞いでいる自分の印刷部品を φ4.0 で貫く。
        //    M2 の頭は φ3.0 なので、この穴からビスを落として同じ穴でドライバを通す。
        //    ⚠ **電池より先に締める**（電池が入っていると軸は 1.6 で塞がる。空なら 7.6）
        //    🔴 丸のまま抜くと羽が出る（_thin.py）。屋根の左の縁（X 2.5）との間に 0.1〜0.5、
        //       立ち上がりの +Y 面（Y 62.87）との接線に 0.30。⇒ v2 から続く手で **抜きを掃いて**
        //       側面をまっすぐな壁にし、薄い肉を残さない（羽つぶし）
        //       左 2 本は丸のまま。左の縁まで掃くと、刷る姿勢（Y −20°）で 12.2mm² の浮き島が出る
        //       （縁へ向かって下っていく肉を切り落とすため）。残る羽は #7 の 1 か所 0.30mm ×2mm で、
        //       蓋の裏のロックのボス（Y 36 で X 4.90 まで出ている）との間に挟まれた縁の肉
        for (sc = SCR_L) translate([sc[0], sc[1], BAT_C1[2] - 0.01]) cylinder(d = DRV_D, h = TUN_T + 0.02, $fn = 48);   // 屋根 2.0
        hull() for (dx = [0, -3.0], dy = [0, 6.0])                                     // L の立ち上がり 4.86。−X と +Y の両方へ掃く
            translate([SCR_R[0] + dx, SCR_R[1] + dy, BR_ZT - 0.01]) cylinder(d = DRV_D_R, h = LIP_Z1 - BR_ZT + 1, $fn = 48);
        // 電池線の穴: トンネルの端板（X 〜54.0）のすぐ右・電池の JST の出口（Y 〜54）の真下。角の無い長丸（2 本・φ2.5）
        //   🔴 Y 51〜56 だと Type-C の受け（Y 52.5〜・Z 31.7〜）の真下で線が受けに入る → Y 46〜50（つまみの柱 Y 〜46 の後ろ）
        //   🔴 Y 46.5〜50 だと線が INA226 の板（Y 〜49.5）の上に下りる → 穴は Y 51 の丸 1 つ（線 2 本は縦に並ぶ）
        //   🔴 2026-08-23 羽つぶし: 丸が波のウェブに接して厚み 0.30 の羽が 2 つ出ていた（X 55.7 と 57.3・Y 49.1）。
        //      半径を 1.85 → 2.05 にして接線を飲み込む（線の逃げは増える方向）
        translate([BAT_HOLE_X, BAT_HOLE_Y, BR_ZB - 1]) cylinder(r = 1.25 + 0.8, h = BR_DEPTH + 2, $fn = 32);
        // XIAO の線の穴（v2 bridge_clear ②）: ソケットの上段（Z 27.5）はブリッジと同じ高さなので、前面の角の無い長丸で抜いて線を通す
        //   🔴 2026-08-23 ユーザー指摘「食いちぎったような抜き方」: 丸が前面（BR_Y0 20.535）を 1.1 はみ出して
        //      いたので、縁が斜めに切れて両端に薄い歯が残っていた。⇒ **前へ掃いた包絡**にして、側面を Y に平行な
        //      まっすぐな壁、奥だけ元の丸にする（開ける量は同じ。前面がきれいに開く）
        //   🔴 同日、奥の辺が 3.4° 傾いていた（ユーザー指摘）。束の太さが違う（下段 1.545 / 上段 1.783）と
        //      2 円の共通接線が傾く。⇒ **太い方（1.783）に揃える**。下段側の穴が 0.24 広がるだけ
        hull() for (dy = [0, -(XIAO_WIRE_Y - BR_Y0) - 2]) for (x = [66, 70])
            translate([x, XIAO_WIRE_Y + dy, BR_ZB - 1]) cylinder(r = 1.783 + 0.6, h = BR_DEPTH + 2, $fn = 48);
        // 左端: 蓋の彫り込みの裏の肉（shutter_backing・ロックのボス込み）は左の壁の部品なので、その形＋0.3 をブリッジから引く。
        //    左の壁はブリッジに X で被せる（裏の肉がブリッジの切り欠きに入る）
        minkowski() { shutter_backing(); cube(0.6, center = true); }
        // 右端: 前の足は右の壁の増し壁（XIAO の口の周り・X 84.65〜86）と同じ場所に居る（14.5mm3）。増し壁＋0.3 を足から抜く
        // 🔴 2026-08-23 羽つぶし: 抜きの丸が足の後ろの縁に**接して**厚み 0.30 の羽が残っていた（X 85.1〜85.9）。
        //    面を動かしても接線が動くだけなので、**抜きを後ろへ掃いて**足の後ろ側に肉を残さない（線の穴と同じ手）
        minkowski() { hull() for (dy = [0, 4]) translate([0, dy, 0]) xiao_pad(); cube(0.6, center = true); }
        translate([-1, -1, -1]) cube([1 + 0.3, IN_Y + 2, IN_Z + 2]);   // X 0〜0.3 も空ける（壁の内面との隙間）
    }
}
// 🔒 上下を戻した置き方（2026-08-24）: 板の法線まわりに 180°。部品面は内向きのまま、前後も入れ替わる（USB-A のヘッダが前 Y 29・micro-USB が後ろ）
module pb_v3() { translate([PB_X1, PB_Y0, PB_ZT]) rotate([0, -90, 0]) rotate([0, 0, 90]) { powerboost_1000c(hdr = "front"); pb_jst_plug(); } }   // 🔴 壁ポーズは 8 ピン列のハウジングの挿し込みが成立しない（インダクタ）。置き場所は検討中（part="pb_floor_look"）
// 充電プラグの空間（v2 の pb_usb_space をそのまま）
PB_USB_PLUG = 12.0; PB_USB_MARG = 1.5;
module pb_usb_space() {
    c = pb2box([-0.5, pb_usb()[1], pb_pcb_t() + pb_usb_sz()[2] / 2]);
    color("#f6ad55", 0.4) translate([c[0] - pb_usb_sz()[2] / 2 - PB_USB_MARG, c[1] - PB_USB_PLUG, c[2] - pb_usb_sz()[1] / 2 - PB_USB_MARG])
        cube([pb_usb_sz()[2] + PB_USB_MARG * 2, PB_USB_PLUG, pb_usb_sz()[1] + PB_USB_MARG * 2]);
}
function pb_usb_space_bot() = pb2box([-0.5, pb_usb()[1], pb_pcb_t() + pb_usb_sz()[2] / 2])[2] - pb_usb_sz()[1] / 2 - PB_USB_MARG;
SLOT_LIP_T = 1.7;   // 差し込み口の上の唇。（旧）pb_usb_space_bot() − 0.2 − BR_ZT ＝ 1.7。micro-B を使わなくなったので値で固定（2026-08-24）

// ============================================================
// 右の壁の XIAO の口（v2 §4.3 の移植。意匠は v2: 彫り込み＋ベベル・口は殻の大きさ・印は口の右・口の 7 割）
//   v2 との違い: 充電の口はここに無い（ハッチへ）。縦の彫り込みは XIAO のポケットだけ
// ============================================================
USB_SEAT = 0.95; SLOT_D = 0.6;                                      // レセプタクルの面 ↔ 彫り込みの床（v2 は 0.3）/ 彫り込みの深さ
// 🔒 0.3 → 0.95（2026-08-23 ユーザー「3 でいきましょう」）。床を遠ざけて、口の下の増し壁を**裏側だけ**削っても **皮 0.8** が残るようにする（下の xiao_pad）。
//    床が遠い分にはプラグは奥まで挿さる（オーバーモールドは面の 0.3 手前で止まり、床には届かない）。0.55 では皮が 0.4 で薄すぎた
USBC_PORT   = [xiao_usb_sz()[0] + 0.6, xiao_usb_sz()[1] + 0.6];   // [Y, Z] = [3.86, 9.54] 殻 ＋ 片側 0.3
XIAO_FACE_X = RSP_X + respeaker_L() + xiao_usb_out();              // 85.554 レセプタクルの面
XIAO_SEAT_X = XIAO_FACE_X + USB_SEAT;                               // 85.854 深い彫り込みの床（オーバーモールドが座る）
XIAO_PAD_T  = 1.2;  XIAO_PAD_X0 = XIAO_SEAT_X - XIAO_PAD_T;  XIAO_PAD_M = 1.0;   // 増し壁: 床の下に残す肉 / 縁
OVERMOLD    = [6.5, 12.5];  USBC_PORT_R = 1.2;  PORT_BEV = 1.0;
SLOT_BEV = 0.6;  SLOT_M = 1.0;
module port_rrect(sz, r, g = 0) { hull() for (a = [-1, 1], b = [-1, 1]) translate([a * (sz[0] / 2 - r), b * (sz[1] / 2 - r)]) circle(r = r + g, $fn = 40); }
module wall_port_x(c, sz, r, bev = PORT_BEV, x0 = IN_X) {
    translate([0, c[0], c[1]]) rotate([90, 0, 90]) {
        translate([0, 0, x0 - 0.01]) linear_extrude(IN_X + WALL - x0 + 0.02) port_rrect(sz, r);
        if (bev > 0) hull() {
            translate([0, 0, IN_X + WALL - bev]) linear_extrude(0.01) port_rrect(sz, r);
            translate([0, 0, IN_X + WALL + 1.0]) linear_extrude(0.01) port_rrect(sz, r, bev + 1.0);
        }
    }
}
module wall_recess_x(c, sz, r, d, bev) {
    translate([0, c[0], c[1]]) rotate([90, 0, 90]) {
        translate([0, 0, IN_X + WALL - d]) linear_extrude(d + 1.0) port_rrect(sz, r);
        hull() {
            translate([0, 0, IN_X + WALL - d]) linear_extrude(0.01) port_rrect(sz, r);
            translate([0, 0, IN_X + WALL + 1.0]) linear_extrude(0.01) port_rrect(sz, r, bev + d + 1.0);
        }
    }
}
module wall_pocket_x(c, sz, r, x_floor, d, bev) {
    translate([0, c[0], c[1]]) rotate([90, 0, 90]) translate([0, 0, x_floor]) linear_extrude(IN_X + WALL + 1.0 - x_floor) port_rrect(sz, r);
    wall_recess_x(c, sz, r, d, bev);
}
function xiao_pocket_sz() = [OVERMOLD[0] + SLOT_M * 2, OVERMOLD[1] + SLOT_M * 2];   // [8.5, 14.5]
// 🔴 増し壁は **U 字（下が開いている）**。閉じた環にすると、下の帯（X 84.65〜85.85）が ReSpeaker の USB-C の殻（X 〜85.55）の
//    通り道に居て、右の壁を Z で降ろせない（v2 の 10.4mm3 と同じ話）。口の下はオーバーモールドが座る床が無くてもよい
// 🔒 2026-08-23 ユーザー: 口は v2 と同じ形（口だけ）で、側面構造体は両方の壁とも上から降ろす。
//    ⇒ 口の下の増し壁を**裏側だけ**削る（外の床は残す）。ReSpeaker の USB-C の殻（X 〜85.554）が通る所の肉を X 85.70 まで抜き、
//       床（X 86.10）との間に 0.4 の皮を残す。外から見える形は v2 と同じ
XIAO_SKIN_X0 = XIAO_FACE_X + 0.15;   // 85.70 皮の裏面（殻との隙間 0.15）
module xiao_pad() {
    c = XIAO_PORT_C; sz = xiao_pocket_sz();
    difference() {
        translate([0, c[0], c[1]]) rotate([90, 0, 90]) translate([0, 0, XIAO_PAD_X0]) linear_extrude(IN_X - XIAO_PAD_X0 + 0.01)
            port_rrect([sz[0] + XIAO_PAD_M * 2, sz[1] + XIAO_PAD_M * 2], USBC_PORT_R + SLOT_M + XIAO_PAD_M);
        translate([XIAO_PAD_X0 - 1, c[0] - USBC_PORT[0] / 2, -1]) cube([XIAO_SKIN_X0 - XIAO_PAD_X0 + 1, USBC_PORT[0], c[1] + 1]);   // 口の下: 裏側だけ X 85.70 まで抜く（皮 0.4 を残す）
    }
}
// 印（v2 の規則: 丈は口の丈の 7 割・彫り 0.4・彫り込みの右（+Y）・縁から 1.5）
ICONS_ON = true;  ICON_D = 0.4;  ICON_GAP = 1.5;  ICON_H = 0.7 * USBC_PORT[1];  SVC_MIN_W = 0.5;
function icon_col_y() = XIAO_PORT_C[0] + xiao_pocket_sz()[0] / 2 + (SLOT_D + SLOT_BEV) + ICON_GAP + ICON_H / 2;
module wall_icon_x(c) { translate([0, c[0], c[1]]) rotate([90, 0, 90]) translate([0, 0, IN_X + WALL - ICON_D]) linear_extrude(ICON_D + 1.0) children(); }
module icon_svg() { sc = ICON_H / icon_gear_wrench_size()[1]; sw = max(icon_gear_wrench_sw(), SVC_MIN_W / sc); scale(sc) icon_gear_wrench(sw); }
module right_wall_ports_cut() {
    wall_pocket_x(XIAO_PORT_C, xiao_pocket_sz(), USBC_PORT_R + SLOT_M, XIAO_SEAT_X, SLOT_D, SLOT_BEV);   // オーバーモールドが座る深い彫り込み
    wall_port_x(XIAO_PORT_C, USBC_PORT, USBC_PORT_R, 0, XIAO_PAD_X0);                                   // 口（増し壁ごと貫く）
    if (ICONS_ON) wall_icon_x([icon_col_y(), XIAO_PORT_C[1]]) icon_svg();                               // メンテナンスの印
}
module right_wall_v3() {
    // 🔴 壁に付く物（ダボ・棚・差し込み口・柱）は全部 union してから口を引く。外で足すと、足の差し込み口の棚（X 〜86）が
    //    彫り込みの床（X 85.854）から 0.15 顔を出して、口の右上に四角く見えていた（2026-08-23 ユーザー「ベベルが中央に」）
    difference() {
        union() {
            color("#b6c0cc") translate([IN_X, 0, 0]) cube([WALL, IN_Y, IN_Z]);
            color("#b6c0cc") xiao_pad();
            // ダボ 4 本（肩 1.2 ＋ ピン）
            for (h = pb_holes_yz()) {
                color("#b6c0cc") translate([IN_X - PB_STANDOFF, h[0], h[1]]) rotate([0, 90, 0]) cylinder(d = DOWEL_SH_D, h = PB_STANDOFF, $fn = 32);
                color("#b6c0cc") translate([PB_FACE_X - DOWEL_OUT, h[0], h[1]]) rotate([0, 90, 0]) cylinder(d = DOWEL_D, h = IN_X - PB_FACE_X + DOWEL_OUT, $fn = 24);
            }
            // 柱を受ける棚（ナット入り）
            nut_ledge(IN_X - LEDGE_W_R, COL_Y0, LEDGE_W_R, POST_W, BR_ZB);
            // 足の差し込み口: 下の棚と上の唇（足は X で滑り込む）
            color("#b6c0cc") translate([IN_X - LEDGE_W, BR_Y0, BR_ZB - 2]) cube([LEDGE_W, PB_Y0 - PB_FRONT_CL - BR_Y0, 2]);
            color("#b6c0cc") translate([IN_X - LEDGE_W, BR_Y0, BR_ZT]) cube([LEDGE_W, PB_Y0 - PB_FRONT_CL - BR_Y0, SLOT_LIP_T]);
            for (b = BOSSES) if (b[0] > IN_X / 2) top_boss(b, BOSS_H);
            ear_col(EAR_X[1][0]);   // 前の柱は耳の真下（天面のビスと耳のビスを 1 本に）
            color("#b6c0cc") for (b = BOSSES_B) if (b[0] > IN_X / 2) bottom_boss(b);   // 床へのビスの柱
        }
        right_wall_ports_cut();
    }
}
// 🔒 前の 2 本は耳と兼用（2026-08-23 ユーザー「それなら4本でもいいね」）。フロントの耳の真下に立てる柱で、
//    ビスは 天面（ザグリ）→ 耳（素通し）→ この柱のナット と 1 本で 3 枚を通す。上面に六角ポケット（ナットは上から落とし、耳が蓋）＋通し穴。
//    耳の真下は中身・線・他の板と当たり 0（12mm 下ろして 0mm³・45mm でも 1.16mm³。`_ear_col_chk.scad`）
EAR_COL_H = 9.0;
module ear_col(x0) {
    difference() {
        color("#b6c0cc") translate([x0, EAR_Y0, IN_Z - EAR_T - EAR_COL_H]) cube([EAR_W, EAR_Y1 - EAR_Y0, EAR_COL_H]);
        translate([x0 + EAR_W / 2, (EAR_Y0 + EAR_Y1) / 2, IN_Z - EAR_T - NUT_T]) rotate([0, 0, 30]) hex_pocket(NUT_T + 1);   // 二面幅を X に
        translate([x0 + EAR_W / 2, (EAR_Y0 + EAR_Y1) / 2, IN_Z - EAR_T - EAR_COL_H - 1]) cylinder(d = SCR_D, h = EAR_COL_H + 2, $fn = 24);
    }
}
// 🔴 2026-08-23 ビスを全部実体で置いて検査したら、天面のビス 4 本が入るこの柱に**穴もナットのポケットも無かった**（1 本あたり 33mm³ 残る）。
//    耳・床の柱と同じ作り: 上面に六角ポケット（ナットは上から落とし、天面が蓋）＋ 通し穴
module top_boss(b, h) {
    difference() {
        color("#b6c0cc") translate([b[0], b[1], IN_Z - h]) cube([BOSS, BOSS, h]);
        translate([b[0] + BOSS / 2, b[1] + BOSS / 2, IN_Z - NUT_T]) hex_pocket(NUT_T + 1);
        translate([b[0] + BOSS / 2, b[1] + BOSS / 2, IN_Z - h - 1]) cylinder(d = SCR_D, h = h + 2, $fn = 24);
    }
}
module left_wall_v3() {
    difference() {
        union() {
            color("#b6c0cc") translate([-WALL, 0, 0]) cube([WALL, IN_Y, IN_Z]);
            color("#b6c0cc") shutter_backing();   // 彫り込みの裏に足す肉（v2）
            for (yy = LEDGE_L_Y) nut_ledge(0, yy[0], LEDGE_W, yy[1] - yy[0], BR_ZB);
            for (b = BOSSES) if (b[0] < IN_X / 2) top_boss(b, BOSS_H);
            ear_col(EAR_X[0][0]);   // 前の柱は耳の真下（天面のビスと耳のビスを 1 本に）
            color("#b6c0cc") for (b = BOSSES_B) if (b[0] < IN_X / 2) bottom_boss(b);   // 床へのビスの柱
            if (CHG_ON == "left" && TC_POCKET_L) color("#b6c0cc") typec_pocket_add_L();
            // （旧）tc_holder_boss(): ケーブルの胴の受け（別刷り）を留める座。🔒 2026-08-24 ユーザー「旧受けの座は消す」（充電口は Type-C 基板 115426 に変わった）
        }
        if (CHG_ON == "left") left_wall_port_cut();   // 充電口（ベベル＋稲妻）
        battery_port_cut();    // 電池の口
        // 🔴 v2 では壁とトンネルが一体で、電池の通り道はトンネル側の cut が裏の肉まで抜いていた。v3 は別部品なので壁側でも抜く（42mm3）
        translate([BAT_C0[0] - WALL - 2, BAT_C0[1], BAT_C0[2]]) cube([WALL + 2 + SHUT_BACK + 1, BAT_C1[1] - BAT_C0[1], BAT_C1[2] - BAT_C0[2]]);
        shutter_band_cut();    // 蓋の彫り込み（裏の肉より後に引く）
        shutter_lock_cut();    // ロックネジの通し穴とナットの座
    }
}
SHUT_OPEN = 0;   // 蓋: 0 = 閉, 1 = ずらし切った
module left_wall_extras() { color("#c8ced6") battery_shutter(SHUT_OPEN); color("#8892a0") battery_lock(); }
// ⑥ 側面構造体（左壁・ブリッジ・右壁・INA226・PowerBoost・電池）
module side_struct() {
    s_("walls") left_wall_v3();
    s_("walls") right_wall_v3();
    s_("bridge") bridge_v3();
    s_("ina") translate([INA_AT[0], INA_AT[1] + ina_size()[1], INA_AT[2] + ina_h()]) rotate([180, 0, 0]) ina226_module();
    s_("pb") pb_v3();
    s_("lipo") translate(LIPO_AT) lipo_1000mah();
}
// 🔒 2026-08-23 天面のビスは 4 本（ユーザー）。前の 2 本は独立した柱を持たず、フロントの耳と兼用にした（`ear_col`）。
//    それまでは前の柱（Y 8.4〜15.4）と耳（Y 0〜8）が Y で 7.9 しか離れずに 2 本並び、天面が 6 本になっていた
BOSSES = [[0, IN_Y - BOSS], [IN_X - BOSS, IN_Y - BOSS]];   // 後ろの 2 本だけ
// ⑫ 天面（つまみの座は中身ごと箱で置く）
// ⬜ ユーザー案（2026-08-22）: 天面から L を下ろして OLED の上の 2 穴を中で受ける（フロントにビスを見せない）
//    L の足は OLED の裏（Y 4.6）に面で当たり、ビスは後ろから通してナットは基板の前（ガラスの厚み 3.0 の中・窓枠の裏）
function oled_top_holes() = [for (h = oled_mount()) if (h[1] > oled_w() / 2) [OLED_X0 + h[0], OLED_Z0 + h[1]]];
// 🔴 2026-08-23 ビスの実体検査: L にビスの穴が無く（1 本 15mm³）、絵の頭が L の後ろに付いていた。🔒 決めた形（ビスは OLED の前から・ナットは L のポケット）に直す:
//    L を Y に貫く穴 ＋ 後ろの面から六角ポケット（ナットは後ろから入れる。残り 0.2）。頭は OLED の基板の前面（Y 3.0）の手前
module oled_brackets() {
    for (h = oled_top_holes()) {
        difference() {
            color("#c9d0d8") translate([h[0] - OLED_L_W / 2, oled_back(), IN_Z - OLED_L_DROP]) cube([OLED_L_W, OLED_L_T, OLED_L_DROP]);
            translate([h[0], oled_back() - 1, h[1]]) rotate([-90, 0, 0]) cylinder(d = SCR_D, h = OLED_L_T + 2, $fn = 24);
            translate([h[0], oled_back() + OLED_L_T - NUT_T, h[1]]) rotate([-90, 0, 0]) hex_pocket(NUT_T + 1);
        }
    }
}
module oled_screw_heads() { for (h = oled_top_holes()) color("#e8e8e8") translate([h[0], OLED_PCB_Y_FRONT, h[1]]) rotate([90, 0, 0]) cylinder(d = SCR_HEAD_D, h = SCR_HEAD_H, $fn = 24); }   // 頭（前面の手前 Y 1.7〜3.0）。絵にだけ出す（天面の部品には入れない）
OLED_PCB_Y_FRONT = 3.0;   // OLED の基板の前面（parts.scad OLED_PCB_Y。use<> では見えない）
module toggle_shelf() if (SHELF_HUNG) {   // ⚠ 粗い形: 天板から下がる U 字（底＋両側。爪は描いていない）
    // 前の壁は無し。Y の止めは外の六角ナット（ユーザー）。前の壁を付けると電池の尻（Y 57.9）に 0.3 入る（22.5mm3）
    w = TGL_BODY_D + 2 * (SHELF_T + SHELF_CL); d = mts102_deep() + SHELF_CL;
    z0 = TGL_AT[1] - TGL_BODY_D / 2 - SHELF_CL - SHELF_T;
    color("#c9d0d8") translate([TGL_AT[0] - w / 2, IN_Y - d, z0])
        difference() { cube([w, d, IN_Z - SHELF_CL - z0]);                                  // 壁の上端は天井の下 0.3（フランジと同じ高さまで）
                       translate([SHELF_T, -1, SHELF_T]) cube([w - 2 * SHELF_T, d + 2, IN_Z]);
                       translate([w / 2 - 3, -1, -1]) cube([6, mts102_deep() - MTS_BODY_H_ + 2, SHELF_T + 2]); }   // 底板の線のスリット（端子の下・X ±3）
}
module grille_xy(cx, cy, w, d, z0, t, dia = 2.6, pitch = 4.2) {
    nx = floor(w / pitch); ny = floor(d / (pitch * 0.866));
    for (j = [0 : ny], i = [0 : nx]) {
        px = cx - nx * pitch / 2 + i * pitch + (j % 2 ? pitch / 2 : 0);
        py = cy - ny * pitch * 0.866 / 2 + j * pitch * 0.866;
        if (abs(px - cx) <= w / 2 && abs(py - cy) <= d / 2) translate([px, py, z0 - 0.01]) cylinder(d = dia, h = t + 0.02, $fn = 24);
    }
}
module btn_socket() {   // v2 §4.7 そのまま
    B = tsw_body(); yi = B / 2 + 0.3;
    translate([-BTN_PAD_X / 2, -BTN_PAD_Y / 2, Z_BTN_PAD]) cube([BTN_PAD_X, BTN_PAD_Y, IN_Z - Z_BTN_PAD]);
    difference() {
        translate([-BTN_POST_I - BTN_PKT_T, -BTN_POST_I - BTN_PKT_T, Z_TSW_TOP]) cube([(BTN_POST_I + BTN_PKT_T) * 2, (BTN_POST_I + BTN_PKT_T) * 2, Z_NECK1 - Z_TSW_TOP]);
        translate([0, 0, Z_TSW_TOP - 1]) cylinder(d = BTN_HOLE_D, h = Z_NECK1 - Z_TSW_TOP + 2, $fn = 32);
    }
    for (sx = [-1, 1], sy = [-1, 1]) translate([sx * BTN_POST_I + (sx < 0 ? -BTN_PKT_T : 0), sy * BTN_POST_I + (sy < 0 ? -BTN_PKT_T : 0), Z_NECK1]) cube([BTN_PKT_T, BTN_PKT_T, Z_BTN_PAD - Z_NECK1]);
    for (sy = [-1, 1]) mirror([0, sy < 0 ? 1 : 0, 0]) translate([-BTN_CLAW_W / 2, yi, 0]) {
        translate([0, 0, Z_TSW_BOT - BTN_CLAW_G]) cube([BTN_CLAW_W, BTN_PKT_T, Z_TSW_TOP - Z_TSW_BOT + BTN_CLAW_G + 0.01]);
        translate([0, 0, Z_TSW_BOT]) rotate([90, 0, 90]) linear_extrude(BTN_CLAW_W) polygon([[0, 0], [-BTN_CLAW_G, 0], [0, -BTN_CLAW_G - 0.8]]);
    }
    for (sx = [-1, 1]) translate([sx * yi + (sx < 0 ? -BTN_PKT_T : 0), -1.0, Z_TSW_TOP - 1.2]) cube([BTN_PKT_T, 2.0, 1.2]);
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
// ---- 天面に付く 3 つ（スピーカー・呼出ボタン・つまみ）を置く道具 ----------------
// 🔒 explode の s（mm）で組む向きへ散らす。s = 0 なら組んだ位置。3 箇所に同じ式を書いていたのをここに集めた（2026-08-23）
module speaker_at(s = 0) translate([SPK_X, SPK_Y, IN_Z - spk_th() - 0.2 - 1.3 * s]) speaker_112495();   // 天面の裏に貼る＝下へ離す
module button_at(s = 0) translate([BTN_AT[0], BTN_AT[1], 0]) {
    translate([0, 0, 1.4 * s]) color("#d8dde3") button_cap();                                  // 蓋は外（上）から差す
    translate([0, 0, Z_NECK1 - 0.9 * s]) color("#c0c0c0") button_clip();                       // 抜け止めの C 型は下から首に嵌める（座は Z_NECK1・ポケットの床）
    translate([0, 0, Z_TSW_BOT - 1.9 * s]) tactswitch();                                       // タクトスイッチは爪の中へ下から
}
// つまみの座の板と本体の右端は PowerBoost の C6 に当たるので落とす（2026-08-23 ユーザー）。
// 🔒 落とすのは**組んだ位置**なので、explode で散らす前に引く
module knob_trim() difference() { translate(KNOB_AT) children(); translate([KNOB_TRIM_X, PB_Y0 - 1, IN_Z - 12]) cube([IN_X - KNOB_TRIM_X + 1, PB_L + 2, 12]); }
module knob_at(s = 0) for (g = knob_parts()) translate([0, 0, knob_exp_dz(g) * s]) knob_trim() knob_group(g);
// トグルの棚の爪（天板の裏から下りる L 字。棚のフランジを −Y に滑り込ませる）
// 棚の外壁 X = TGL ± w/2。フランジはそこから外へ 1.5（天井の下・隙間 0.3）。爪の脚はフランジの外 0.3 に立ち、唇がフランジの下へ内側に 1.5 入る
function shelf_w() = TGL_BODY_D + 2 * (SHELF_T + SHELF_CL);
function shelf_d() = mts102_deep() + SHELF_CL;
module shelf_hooks() {
    w = shelf_w(); d = shelf_d();
    zf0 = IN_Z - SHELF_CL - SHELF_FLANGE_T;            // フランジの下面
    zl0 = zf0 - SHELF_CL - SHELF_HOOK_T;               // 唇の下面
    for (sx = [-1, 1]) {
        xo = TGL_AT[0] + sx * (w / 2 + SHELF_HOOK_LIP + SHELF_CL);   // 脚の内側の面
        translate([sx < 0 ? xo - SHELF_HOOK_T : xo, IN_Y - d, zl0]) cube([SHELF_HOOK_T, d, IN_Z - zl0 + 0.01]);                 // 脚
        translate([sx < 0 ? xo - 0.01 : xo - SHELF_HOOK_LIP - 0.3 + 0.01, IN_Y - d, zl0]) cube([SHELF_HOOK_LIP + 0.3, d, SHELF_HOOK_T]);   // 唇（内側へ。棚の壁に 0.3 重なるまで）
    }
}
module toggle_shelf_flanges() if (SHELF_HUNG) {   // 棚の両側のフランジ（爪の唇の上に載る・天井の下 0.3）
    w = shelf_w(); d = shelf_d();
    for (sx = [-1, 1]) translate([TGL_AT[0] + sx * w / 2 + (sx < 0 ? -SHELF_HOOK_LIP : 0), IN_Y - d, IN_Z - SHELF_CL - SHELF_FLANGE_T]) cube([SHELF_HOOK_LIP, d, SHELF_FLANGE_T]);
}
TP = "";   // 天面側を1つに: plate / oledL / shelf / toggle / knob
module t_(k) if (TP == "" || TP == k) children();
module top_plate_raw() {   // 天面の印刷部品（つまみの座・ボタンの受け・スピーカーの縁・OLED の L・フック・棚の爪・ReSpeaker の押さえ）
    intersection() { seam_top_half();
    difference() {
        union() {
            color("#c9d0d8") translate([-WALL, -BEZ_T, IN_Z]) cube([IN_X + 2 * WALL, IN_Y + BEZ_T + HATCH_T, TOP_T]);
            color("#c9d0d8") translate(KNOB_AT) knob_station_add();                      // つまみの座（knob_v5）
            color("#c9d0d8") translate([BTN_AT[0], BTN_AT[1], 0]) btn_socket();           // 会話ボタンの受け
            color("#c9d0d8") translate([SPK_X - SPK_RIM_M, SPK_Y - SPK_RIM_M, IN_Z - SPK_RIM]) difference() {   // スピーカーの位置出しの縁（貼るだけ）
                spk_obround(SPK_L + SPK_RIM_M * 2, SPK_W + SPK_RIM_M * 2, SPK_RIM);
                translate([SPK_RIM_M - 0.6, SPK_RIM_M - 0.6, -1]) spk_obround(SPK_L + 1.2, SPK_W + 1.2, SPK_RIM + 2);
            }
            pb_front_hook();
            if (SHELF_HUNG) color("#c9d0d8") shelf_hooks();
            // ReSpeaker の頭を押さえるリブ（前）と右の腕（v2）
            color("#c9d0d8") translate([RIB1_X, RSP_BD_Y0 - 0.5, RSP_TOP - RSP_PRESS]) cube([RIB1_W, respeaker_T() + 1.0, IN_Z - RSP_TOP + RSP_PRESS + 0.01]);
            // 🔴 腕は右前の柱（X 79〜・Z 43〜）の手前で止める。壁まで伸ばすと、天面を降ろすとき柱の真下を通って 34mm3 当たる
            color("#c9d0d8") translate([RSP_ARM_X0, RSP_BD_Y0 - 0.5, RSP_TOP - RSP_PRESS]) cube([RSP_ARM_X1 - RSP_ARM_X0, respeaker_T() + 1.0, RSP_ARM_T + RSP_PRESS]);
            color("#c9d0d8") translate([RSP_ARM_X0, RSP_BD_Y0 - 0.5, RSP_TOP]) cube([RSP_ARM_X1 - RSP_ARM_X0, respeaker_T() + 1.0, IN_Z - RSP_TOP + 0.01]);   // 腕を天井につなぐ
        }
        translate(KNOB_AT) knob_station_cut();
        translate([KNOB_TRIM_X, PB_Y0 - 1, IN_Z - 12]) cube([IN_X - KNOB_TRIM_X + 1, PB_L + 2, 12]);   // 座の板の右端を削る（PowerBoost の C6。つまみ本体と同じ）
        // 🔒 2026-08-24 上下を戻したら USB-A の 4 ピンヘッダ（前 Y 28.6〜30.5・X 74.7〜）が座の板の下段（Z 32.5〜36.45）に 3mm³ 掛かる。その幅だけ切り欠く
        // 🔒 2026-08-24 USB のパッド（8 番・Y 54.6・Z 46.9）に真っ直ぐな 1 ピン＋Dupont（−X へ 10）。座の板の後ろ上の角（Y 〜54.4）に 24mm³ 掛かるので角を落とす
        // 会話ボタン: 皿（俵型）・縁の面取り・首の穴
        translate([BTN_AT[0] - BTN_DISH_L / 2, BTN_AT[1] - BTN_DISH_W / 2, Z_BTN_DISH]) spk_obround(BTN_DISH_L, BTN_DISH_W, BTN_DISH_T + 1);
        translate([BTN_AT[0], BTN_AT[1], Z_TOP - 0.3]) hull() {
            translate([-BTN_DISH_L / 2, -BTN_DISH_W / 2, 0]) spk_obround(BTN_DISH_L, BTN_DISH_W, 0.01);
            translate([-BTN_DISH_L / 2 - 0.3, -BTN_DISH_W / 2 - 0.3, 0.3]) spk_obround(BTN_DISH_L + 0.6, BTN_DISH_W + 0.6, 0.01);
        }
        translate([BTN_AT[0], BTN_AT[1], Z_BTN_PAD - 1]) cylinder(d = BTN_HOLE_D, h = BTN_PAD_T + 2, $fn = 32);
        // スピーカー: 振動板の逃げ・天面のへこみ（45 度）・音の穴
        translate([SPK_X + (SPK_L - SPK_DIA[0]) / 2 - 0.5, SPK_Y + (SPK_W - SPK_DIA[1]) / 2 - 0.5, IN_Z - 0.01]) spk_obround(SPK_DIA[0] + 1, SPK_DIA[1] + 1, SPK_REL + 0.01);
        translate([SPK_X + SPK_L / 2, SPK_Y + SPK_W / 2, 0]) hull() {
            translate([0, 0, Z_TOP - EMB_H]) linear_extrude(0.01) offset(r = 2) square([SPK_DIA[0] + EMB_M * 2 - 4, SPK_DIA[1] + EMB_M * 2 - 4], center = true);
            translate([0, 0, Z_TOP + 1]) linear_extrude(0.01) offset(r = 2) square([SPK_DIA[0] + EMB_M * 2 - 4 + (EMB_H + 1) * 2, SPK_DIA[1] + EMB_M * 2 - 4 + (EMB_H + 1) * 2], center = true);
        }
        grille_xy(SPK_X + SPK_L / 2, SPK_Y + SPK_W / 2, SPK_DIA[0], SPK_DIA[1], IN_Z, TOP_T, 2.2, 3.4);
        // 天面のビス 後ろの 2 本（壁の柱へ）: 通し穴＋表のザグリ
        for (b = BOSSES) translate([b[0] + BOSS / 2, b[1] + BOSS / 2, 0]) {
            translate([0, 0, IN_Z - 1]) cylinder(d = SCR_D, h = TOP_T + 2, $fn = 24);
            translate([0, 0, Z_TOP - SCR_CBT]) cylinder(d = SCR_CB, h = SCR_CBT + 1, $fn = 32);
        }
        // 前の 2 本（同じ形）: 耳を貫いて壁の柱（`ear_col`）のナットへ
        for (ex = EAR_X) translate([(ex[0] + ex[1]) / 2, (EAR_Y0 + EAR_Y1) / 2, 0]) {
            translate([0, 0, IN_Z - 1]) cylinder(d = SCR_D, h = TOP_T + 2, $fn = 24);
            translate([0, 0, Z_TOP - SCR_CBT]) cylinder(d = SCR_CB, h = SCR_CBT + 1, $fn = 32);
        }
    }
    }
    // 🔴 2026-08-23 OLED の L は継ぎ目の斜め（Y + Z >= IN_Z）の**外**に置く。中に入れると足の前下が切り落とされ、
    //    OLED を下げたとき（Z0 4.7 → 1.9）ビスの穴が斜めに掛かって穴の周りの肉が無くなる。継ぎ目は殻を割る線で、中の受けを切る線ではない
    oled_brackets();
}
module top_plate() {
    t_("plate") top_plate_raw();
    t_("shelf") { toggle_shelf(); color("#c9d0d8") toggle_shelf_flanges(); }
    if (SHELF_HUNG) t_("toggle") translate([TGL_AT[0], IN_Y, TGL_AT[1]]) rotate([-90, 0, 0]) mts102(0);   // 吊りのときだけ天面側。レール無し（2026-08-23）ではハッチ側
    t_("spk") translate([SPK_X, SPK_Y, IN_Z - spk_th() - 0.2]) speaker_112495();
    t_("btn") { translate([BTN_AT[0], BTN_AT[1], Z_TSW_BOT]) tactswitch(); color("#d8dde3") translate([BTN_AT[0], BTN_AT[1], 0]) button_cap(); }
    // 🔒 座の板の右端を削る（2026-08-23 ユーザー）: PowerBoost の C6（部品面から 2.5・X 80.7）に 1.0 入っていた。
    //    v2 も同じ所を 0.4 削っていた（case_v2 の 2406 行）。ねじの柱（中心から 8.5）には掛からない
    t_("knob") difference() {
        translate([IN_X - TOP_MARGIN - knob_dish_d() / 2 + KNOB_DX, KNOB_YC, IN_Z + TOP_T]) assembly(show_deck = true);
        translate([KNOB_TRIM_X, PB_Y0 - 1, IN_Z - 12]) cube([IN_X - KNOB_TRIM_X + 1, PB_L + 2, 12]);
    }
}
// 前のフック（天板から）: 基板の前の上の角に被さる。下端は充電プラグの空間より上（v2 と同じ Z 41.8）
function pb_usb_space_top() = pb2box([-0.5, pb_usb()[1], pb_pcb_t() + pb_usb_sz()[2] / 2])[2] + pb_usb_sz()[1] / 2 + PB_USB_MARG;
HOOK_Z0 = PB_ZT - 5.0;   // 前のフックの下端。（旧）充電プラグの空間の上 42.8。micro-B を使わなくなったので板の上端から 5（2026-08-24）
module pb_front_hook() {
    color("#2f855a") translate([PB_FACE_X - LIP_GAP - LIP_T, PB_Y0 - 2.0, HOOK_Z0]) cube([IN_X - (PB_FACE_X - LIP_GAP - LIP_T), 2.0, IN_Z - HOOK_Z0]);
    color("#2f855a") translate([PB_FACE_X - LIP_GAP - LIP_T, PB_Y0, HOOK_Z0]) cube([LIP_T, 1.2, PB_ZT - HOOK_Z0]);
}
// 🔒 天面とフロントの継ぎ目は角丸の真ん中（2026-08-22 ユーザー）: 前上の角の円弧の中心（Y 0・Z IN_Z）を通る 45° の面で割る。
//    天面 = Y + Z >= IN_Z、フロント = Y + Z <= IN_Z（フロントは天面の厚みの分まで上に伸び、その 45° で切れる）
// 🔴 初版は rotate(+45) で面が裏返り（Z >= Y + IN_Z）、天面がほぼ消えてフロントが上へ伸びた（ユーザー「天板もなくなっちゃいました」）。−45 が正
module seam_top_half()   { translate([-WALL - 1, 0, IN_Z]) rotate([-45, 0, 0]) translate([0, -100, 0]) cube([OUT_X + 2, 200, 100]); }        // Y + Z >= IN_Z の側
module seam_front_half() { translate([-WALL - 1, 0, IN_Z]) rotate([-45, 0, 0]) translate([0, -100, -100]) cube([OUT_X + 2, 200, 100]); }    // Y + Z <= IN_Z の側
// 🔒 B 案（2026-08-23 ユーザー）: フロントの耳（天面とつなぐビスの受け）は OLED の両脇（X 0〜6.25 / 79.75〜86）・OLED の L の手前〜横・天井の下。
//    ビスは天面の表から M2×6（頭は天面・後ろの 2 本と同じ見え方）。🔒 2026-08-23 ナットは耳から `ear_col`（耳の真下の壁の柱）へ移し、
//    この 1 本で 天面・耳・壁 の 3 枚を締める（六角は二面幅を X に向ける。幅 6.2 に対して 4.3・Y は角 5.0 が 8 に入る）。
//    🔴 最初は OLED の裏（X 20〜30 / 56〜66）に耳を描いたが、OLED が前面の内側を X 8〜78・天井まで埋めていて 102mm3 当たった
EAR_W = OLED_X0 + oled_mount()[0][0] - OLED_L_W / 2 - 0.3;   // 6.25 耳の X 幅（L の足まで 0.3）
EAR_X = [[0, EAR_W], [IN_X - EAR_W, IN_X]]; EAR_Y0 = 0; EAR_Y1 = 8.0; EAR_T = 3.2;
module front_ears() {
    for (ex = EAR_X) difference() {
        translate([ex[0], EAR_Y0, IN_Z - EAR_T]) cube([ex[1] - ex[0], EAR_Y1 - EAR_Y0, EAR_T]);
        translate([(ex[0] + ex[1]) / 2, (EAR_Y0 + EAR_Y1) / 2, IN_Z - EAR_T - 1]) cylinder(d = SCR_D, h = EAR_T + 2, $fn = 24);   // 🔒 ナットは持たない（下の `ear_col` へ移した）
    }
}
// 🔴 2026-08-23 耳は継ぎ目の 45°（Y＋Z ≤ 52.8）の外にある。intersection の中に入れていたので、耳 246mm³ のうち
//    フロントの部品に残っていたのは 67.6mm³ だけで、ビスの穴もナットの座も**どの印刷部品にも入っていなかった**（v3_front.stl も同じ）。
//    耳は intersection の外で足す。窓・ベベル・ヒゲは X 8〜78 なので耳（X 0〜6.2 / 79.8〜86）には掛からない
module front_plate_raw() {
    union() {
    intersection() { seam_front_half(); union() {
    difference() {
        union() {
            color("#c9d0d8") translate([-WALL, -BEZ_T, -FLOOR_T]) cube([IN_X + 2 * WALL, BEZ_T, Z_TOP + FLOOR_T]);   // 上は天面の厚みの分まで（45° で切られる）・下は床の裏まで（下前の丸みはフロントが持つ）
            color("#c9d0d8") translate([-WALL, -BEZ_T, IN_Z - EAR_T]) cube([IN_X + 2 * WALL, BEZ_T + 0.01, EAR_T]);   // （耳はここに付く）
        }
        translate([0, -BEZ_T - 1, 0]) rotate([-90, 0, 0]) linear_extrude(BEZ_T + 2) mirror([0, 1]) win_rrect(0);   // 窓（ガラス＋0.3）
        win_chamfer_cut();                                                                                       // 窓のベベル
        whiskers_cut();                                                                                          // マイクのヒゲ
    }
    } }
    color("#c9d0d8") front_ears();
    }
}
module front_plate() { front_plate_raw(); oled_at(); }
// ハッチの充電口: Type-C メスのハウジングを内面のポケットで受ける（⚠ 寸法は着荷実測待ち・仮 25×12×7）。鼻先は口から出る
TC_POCKET_T = 1.6; TC_POCKET_CL = 0.3; TC_POCKET_L = false;   // ⬜ 左の壁の受けは製品が決まってから（壁 1.6＋隙間 0.3 が基板の縁とハッチの間 8.1 に入らない）
// 🔒 2026-08-23 ユーザー: 充電口のメス側の胴を支える受けは**別刷り**（ケーブル着荷 8/27〜9/6 の後）。壁には受けを留める座だけ今入れる。
//    ビスは下から嫌（ユーザー）→ 壁の内面の座に横向き（+X から M2）。ナットは座の上からスリットに落とす（貫通＋ナット・樹脂にネジを切らない）
TC_HOLD_Y0 = 65.0; TC_HOLD_Y1 = IN_Y - 0.2; TC_HOLD_Z0 = CHG_C_LW[1] + 6.0 + 1.5;   // 座: Y 65〜71.8（ハブの後ろ左の柱 Y 〜64.4 の後ろ・ハッチの手前 0.2）・Z 18〜25（胴の上端 16.5 の上 1.5）
TC_HOLD_D = BOSS; TC_HOLD_H = 7.0;
function tc_hold_scr() = [TC_HOLD_D, (TC_HOLD_Y0 + TC_HOLD_Y1) / 2, TC_HOLD_Z0 + TC_HOLD_H / 2];   // ビスの入口（座の +X 面の中心）[X, Y, Z]
module tc_holder_boss() {
    c = tc_hold_scr();
    difference() {
        translate([0, TC_HOLD_Y0, TC_HOLD_Z0]) cube([TC_HOLD_D, TC_HOLD_Y1 - TC_HOLD_Y0, TC_HOLD_H]);
        translate([0.5, c[1], c[2]]) rotate([0, 90, 0]) cylinder(d = SCR_D, h = TC_HOLD_D + 1, $fn = 24);              // ビス穴（壁の外面まで 2.5 残す）
        translate([2.2, c[1] - (NUT_AF + 0.3) / 2, c[2] - 2.6]) cube([NUT_T + 0.2, NUT_AF + 0.3, TC_HOLD_H]);       // ナットのスリット（上から落とす・壁から 2.2）
    }
}
module typec_pocket_add_L() {   // 左の壁の内面に付くポケット（ハッチ版と同じ作り: 底＋前後の壁。上と線の出る側（+X）は開）
    c = CHG_C_LW; m = TC_POCKET_CL + TC_POCKET_T;   // 縦置き: Y に 7（厚み）・Z に 12（幅）
    translate([0, c[0] - TC_T / 2 - m, c[1] - TC_W / 2 - m]) difference() {
        cube([TC_L, TC_T + 2 * m, TC_W + 2 * m]);
        translate([-1, TC_POCKET_T, TC_POCKET_T]) cube([TC_L + 2, TC_T + 2 * TC_POCKET_CL, TC_W + 2 * TC_POCKET_CL]);
        translate([-1, -1, TC_W / 2 + m]) cube([TC_L + 2, TC_T + 2 * m + 2, 20]);   // 上は開
    }
}
module left_wall_port_cut() {   // 口は横長（Y 9.54 × Z 3.86）。内面 X 0 から外へ貫き、外面で 45° に開く。稲妻は外面から 0.4 彫る
    c = CHG_C_LW;
    translate([0, c[0], c[1]]) rotate([90, 0, -90]) {
        translate([0, 0, -0.01]) linear_extrude(WALL + 0.02) port_rrect(TC_PORT_SZ_L, USBC_PORT_R);
        hull() {
            translate([0, 0, WALL - PORT_BEV]) linear_extrude(0.01) port_rrect(TC_PORT_SZ_L, USBC_PORT_R);
            translate([0, 0, WALL + 1.0]) linear_extrude(0.01) port_rrect(TC_PORT_SZ_L, USBC_PORT_R, PORT_BEV + 1.0);
        }
    }
    translate([-WALL - 1.0, TC_ICON_Y, c[1]]) rotate([90, 0, 90]) linear_extrude(ICON_D + 1.0) mirror([1, 0]) icon_bolt(TC_ICON_H);
}
module typec_pocket_add() {   // ハッチの内面に付くポケット（胴の周り 3 面＋奥の止め無し。線が出る側は開）
    c = CHG_C_B;
    translate([c[0] - TC_W / 2 - TC_POCKET_CL - TC_POCKET_T, IN_Y - TC_L, c[1] - TC_T / 2 - TC_POCKET_CL - TC_POCKET_T])
        difference() {
            cube([TC_W + 2 * (TC_POCKET_CL + TC_POCKET_T), TC_L, TC_T + 2 * (TC_POCKET_CL + TC_POCKET_T)]);
            translate([TC_POCKET_T, -1, TC_POCKET_T]) cube([TC_W + 2 * TC_POCKET_CL, TC_L + 2, TC_T + 2 * TC_POCKET_CL]);
            translate([-1, -1, TC_T / 2 + TC_POCKET_CL + TC_POCKET_T]) cube([TC_W + 2 * (TC_POCKET_CL + TC_POCKET_T) + 2, TC_L + 2, 20]);   // 上は開（ハウジングを上から落とす）
        }
}
// 口（横長・殻の大きさ・⚠ ハウジング待ちの仮）。外側はベベル 1.0・角丸 1.2。印は稲妻（v2 と同じ絵・口の長辺の 7 割・外から見て口の右＝−X 側）
module port_rrect_xz(sz, r, g = 0) { hull() for (a = [-1, 1], b = [-1, 1]) translate([a * (sz[0] / 2 - r), b * (sz[1] / 2 - r)]) circle(r = r + g, $fn = 40); }
module hatch_port_y(c, sz, r, bev) {   // c = [X, Z]、sz = [X, Z]。ハッチの内面 IN_Y から外へ貫き、外面で 45 度に開く
    translate([c[0], 0, c[1]]) rotate([-90, 0, 0]) {
        translate([0, 0, IN_Y - 1]) linear_extrude(HATCH_T + 2) port_rrect_xz(sz, r);
        hull() {
            translate([0, 0, IN_Y + HATCH_T - bev]) linear_extrude(0.01) port_rrect_xz(sz, r);
            translate([0, 0, IN_Y + HATCH_T + 1.0]) linear_extrude(0.01) port_rrect_xz(sz, r, bev + 1.0);
        }
    }
}
module icon_bolt(h) { s = h / 6; polygon([[0.9, 3], [-1.3, -0.4], [-0.1, -0.4], [-0.9, -3], [1.3, 0.4], [0.1, 0.4]] * s); }   // v2 の稲妻（丈 6 単位）
TC_PORT_SZ = [USBC_PORT[1], USBC_PORT[0]];   // [X 9.54, Z 3.86]
TC_ICON_H  = 0.7 * TC_PORT_SZ[0];
TC_PORT_SZ_L = USBC_PORT;                    // 左の壁は縦置き [Y 3.86, Z 9.54]
TC_ICON_Y = CHG_C_LW[0] - (TC_PORT_SZ_L[0] / 2 + PORT_BEV + ICON_GAP + TC_ICON_H * 2.6 / 6 / 2);   // 外（−X）から見て口の右（−Y）            // 6.68（口の長辺の 7 割・右の壁の印と同じ丈）
TC_ICON_X  = CHG_C_B[0] - (TC_PORT_SZ[0] / 2 + PORT_BEV + ICON_GAP + TC_ICON_H * 2.6 / 6 / 2);   // 後ろから見て口の右（−X）
module typec_port_cut() {
    if (CHG_ON == "hatch") {
        hatch_port_y(CHG_C_B, TC_PORT_SZ, USBC_PORT_R, PORT_BEV);
        translate([TC_ICON_X, IN_Y + HATCH_T - ICON_D, CHG_C_B[1]]) rotate([90, 0, 0]) mirror([0, 0, 1]) linear_extrude(ICON_D + 1.0) icon_bolt(TC_ICON_H);   // 稲妻（外面から 0.4 彫る）
    }
    // アンテナ線の穴: トグルの穴の**下**へ細いスリット（🔒 2026-08-23 ユーザー「上に付いているが下に」）。線は尻尾の中の溝（ANT_OFF 4.5・レバーが真っ直ぐのとき下側）へ
    translate([TGL_AT[0] - ANT_SLOT_W / 2, IN_Y - 1, TGL_AT[1] - (ANT_OFF + ANT_SLOT_W / 2)]) cube([ANT_SLOT_W, HATCH_T + 2, ANT_OFF + ANT_SLOT_W / 2]);
}
ANT_SLOT_W = 2.2;
// ⑬ ハッチ（トグル付き）
module hatch_raw() {   // トグルの穴＋充電口＋下の爪＋Type-C のポケット。トグルは天板側
    difference() {
        union() {
            color("#c9d0d8") translate([-WALL, IN_Y, -FLOOR_T]) cube([IN_X + 2 * WALL, HATCH_T, IN_Z + FLOOR_T]);   // 下は床の裏まで（下後ろの丸みはハッチが持つ）
            color("#c9d0d8") hatch_claws();
            if (CHG_ON == "hatch") color("#c9d0d8") typec_pocket_add();
        }
        translate([TGL_AT[0], IN_Y - 1, TGL_AT[1]]) rotate([-90, 0, 0]) mts102_hole(HATCH_T + 2);
        typec_port_cut();
    }
}
module hatch() { hatch_raw(); if (!SHELF_HUNG) translate([TGL_AT[0], IN_Y, TGL_AT[1]]) rotate([-90, 0, 0]) mts102(0); }   // トグルはハッチに外のナットで付く（⑬ で一緒に入る）

module sweep_z(n) for (t = [0 : STEP : n]) translate([0, 0, -t]) children();
module sweep_y(n) for (t = [0 : STEP : n]) translate([0, t, 0]) children();
module sweep_ny(n) for (t = [0 : STEP : n]) translate([0, -t, 0]) children();   // 前から後ろへ（フロントの差し込み）

if (part == "close")       intersection() { side_struct(); sweep_z(SWEEP) manaita(); }
if (part == "close_top")   intersection() { top_plate(); sweep_z(SWEEP) { manaita(concat(PLUGGED_9, PLUGGED_10)); side_struct(); } }
if (part == "chk_bracket") intersection() { oled_brackets(); union() { manaita(concat(PLUGGED_9, PLUGGED_10)); side_struct(); oled_at(); front_plate(); } }
if (part == "pic_oled") {
    HX = oled_top_holes()[0][0];
    slab("#c9d0d8") sec_x(HX) top_plate();
    slab("#c9d0d8") sec_x(HX) front_plate();
    slab("#7d8794") sec_x(HX) manaita();
    slab("#7d8794") sec_x(HX) side_struct();
    slab("#e6194b") sec_x(HX) oled_brackets();
    translate([0, 54]) linear_extrude(1) text(str("X ", HX, " (Y-Z): OLED top hole, L from the top plate"), size = 3);
}
if (part == "close_hatch") intersection() { sweep_y(SWEEP) hatch(); union() { manaita(concat(PLUGGED_9, PLUGGED_10)); side_struct(); top_plate(); } }
if (part == "look9")  { manaita(); side_struct(); }
if (part == "look10") { manaita(concat(PLUGGED_9, PLUGGED_10)); side_struct(); }
// 🔒 "look" は印刷物と同じ角丸をかけた外皮で見せる（2026-08-23 ユーザー「カックカク」→ 角丸前の図を見ていた）。検査は角丸無しのまま
// ---- 見るための図: "all"（組んだ全部）/ "inside"（外皮を透かす）/ "explode"（組む向きにばらす）----
// 🔴 2026-08-23 透かし（color の alpha）は F6/--render では効かず、外皮が不透明に出て中が見えなかった（ユーザー指摘）。
//    inside / wires は外皮を「外す」で見せる。OPEN に挙げた板を描かない（既定: 既定カメラの手前にくる 天面・フロント・右の壁）
OPEN = ["top", "front", "rwall"];   // 外す板: "floor" "lwall" "rwall" "top" "front" "hatch"
EXPLODE = 40;     // explode の離し量（mm）
EXPLODE_X = 22;   // 左右の壁を X に離す量（別部品だと分かるように）
EXPLODE_S = 6;    // 1 つの板に付く小物（蓋・ロック・磁石・ビス・つまみの中身・ボタン）を離す量
function shown(n) = len([for (o = OPEN) if (o == n) 1]) == 0;
module shells_rounded() { rounded() union() { floor_v3(); left_wall_v3(); right_wall_v3(); top_plate_raw(); front_plate_raw(); hatch_raw(); } }
module shells_open() { color("#b6c0cc") rounded() union() {
    if (shown("floor")) floor_v3(); if (shown("lwall")) left_wall_v3(); if (shown("rwall")) right_wall_v3();
    if (shown("top")) top_plate_raw(); if (shown("front")) front_plate_raw(); if (shown("hatch")) hatch_raw(); } }
module innards() {
    hub_at(); respeaker_at(); oled_at(); for (id = PLUGGED_9) housing(id);
    bridge_v3(); translate([INA_AT[0], INA_AT[1] + ina_size()[1], INA_AT[2] + ina_h()]) rotate([180, 0, 0]) ina226_module(); pb_v3(); translate(LIPO_AT) lipo_1000mah();
    toggle_shelf(); toggle_shelf_flanges(); translate([TGL_AT[0], IN_Y, TGL_AT[1]]) rotate([-90, 0, 0]) mts102(TAIL_ANG);
    speaker_at(); button_at(); knob_at();
    left_wall_extras(); tail_at();
    if (CHG_ON == "left") color("#e53e3e") typec_housing_L(CHG_C_LW);   // Type-C のハウジング（⚠ 仮 25×12×7）
    oled_screw_heads();
}
if (part == "all")    { shells_rounded(); innards(); }
if (part == "inside") { shells_open(); innards(); }
if (part == "explode") {
    E = EXPLODE; EX = EXPLODE_X; S = EXPLODE_S;
    rounded() floor_v3(); hub_at(); respeaker_at(); for (id = PLUGGED_9) housing(id);                                   // まな板（①②③⑤⑩⑪）
    // ⑥ 側面構造体。降ろすのは 1 段だが**別部品 3 つ**（左の壁・ブリッジ・右の壁）なので、X にも離して境目を見せる
    //    （2026-08-23 ユーザー「バラバラにならないのに違和感」→ 同じ translate に 3 つ入れていた）
    // 電池まわりは左の壁の外側で 1 本の線に並べる。壁 → **電池** → 磁石 4 個 → 蓋 → ロック → ビス
    // 🔒 2026-08-23 ユーザー「ロックたちを少し離して、筐体とロックたちとの間に（電池を）欲しい」。
    //    電池は左の壁の口から −X へ抜くので、蓋とロックはその分だけ外へ送る（LK_OUT）
    BAT_OUT = LIPO_L + 10; LK_OUT = LIPO_L + 6;   // 電池を抜く量と、蓋・ロックを外へ送る量
    translate([-EX, 0, E]) { rounded() left_wall_v3();
                             translate([0, 0, 0.9 * S]) shutter_lock_nut();                                            // ナットは壁のボスへ上から落とす
                             translate([-BAT_OUT, 0, 0]) translate(LIPO_AT) lipo_1000mah();                             // 電池（口から −X へ抜く。抜き道の検査は part="chk_swap"）
                             translate([-LK_OUT - 1.45 * S, 0, 0]) shutter_magnets_wall();                              // 壁側の磁石 2
                             translate([-LK_OUT - 2.3 * S, 0, 0]) shutter_magnets_shutter();                            // 蓋側の磁石 2（蓋の裏から入れる）
                             translate([-LK_OUT - 3.3 * S, 0, 0]) color("#c8ced6") battery_shutter(0);                  // 電池の蓋
                             translate([-LK_OUT - 4.8 * S, 0, 0]) color("#8892a0") battery_lock();                      // ロック（門形。これとビスを外せば工具なしで開く）
                             translate([-LK_OUT - 6.6 * S, 0, 0]) shutter_lock_screw(); }
    translate([0, 0, E]) { bridge_v3();
                           translate([INA_AT[0], INA_AT[1] + ina_size()[1], INA_AT[2] + ina_h()]) rotate([180, 0, 0]) ina226_module(); }   // ブリッジ（＋INA226。電池は左の壁の線へ）
    translate([EX, 0, E]) { rounded() right_wall_v3(); pb_v3(); }                                                       // 右の壁（＋ダボに載る PowerBoost）
    // 天面（④⑪⑫）。天板に付く 3 つ（スピーカー・呼出ボタン・つまみ）も組む向きへ散らす
    translate([0, 0, 2 * E]) { rounded() top_plate_raw(); toggle_shelf(); toggle_shelf_flanges(); if (SHELF_HUNG) translate([TGL_AT[0], IN_Y, TGL_AT[1]]) rotate([-90, 0, 0]) mts102(TAIL_ANG);
                               speaker_at(S); button_at(S); knob_at(S); }
    translate([0, -E, 2 * E]) { rounded() front_plate_raw(); oled_at(); }                                                // フロント（④・天面と一緒）
    translate([0, E, 2 * E]) { rounded() hatch_raw(); if (!SHELF_HUNG) translate([TGL_AT[0], IN_Y, TGL_AT[1]]) rotate([-90, 0, 0]) mts102(TAIL_ANG); translate([0, E / 2, 0]) tail_at(); }                               // ハッチ（⑬）と尻尾
}
if (part == "look")   { rounded() union() { floor_v3(); left_wall_v3(); right_wall_v3(); top_plate_raw(); front_plate_raw(); hatch_raw(); }
                        hub_at(); respeaker_at(); oled_at(); for (id = PLUGGED_9) housing(id);
                        bridge_v3(); translate([INA_AT[0], INA_AT[1] + ina_size()[1], INA_AT[2] + ina_h()]) rotate([180, 0, 0]) ina226_module(); pb_v3(); translate(LIPO_AT) lipo_1000mah();
                        toggle_shelf(); toggle_shelf_flanges(); translate([TGL_AT[0], IN_Y, TGL_AT[1]]) rotate([-90, 0, 0]) mts102(TAIL_ANG);   // レバーは倒れた位置（尻尾と同じ角度）
                        speaker_at(); button_at(); knob_at();
                        left_wall_extras(); tail_at(); }
if (part == "manaita") manaita();
// C6（1210・高さ 2.5・局所 x 24.68〜27.64 / y 2.61〜7.55）を箱で置いて、つまみのどこが入るかを見る
module pb_c6() { a = pb2box([24.68, 7.55, pb_pcb_t() + 2.5]); b = pb2box([27.64, 2.61, pb_pcb_t()]); translate(a) cube(b - a); }
if (part == "chk_c6") intersection() { pb_c6(); top_plate(); }
// ユーザー案（2026-08-23）: Type-C メスのピッグテール（4 芯・B0BGXL6J76）を PowerBoost の USB/GND ピンに半田付けし、
//   メスのハウジングは**壁の外面の彫り込み**に埋める（開口は壁に沿う向き）。線は小穴で中へ。⇒ micro-B のプラグの空間が消える。
//   ハウジングは仮 9 × 6.5 × 16（⚠ 記載なし）。彫り込みの床が壁の内側へ出る分（6.5 − 2 ＋ 床 1.2）を内側の塊として当てる
PT_W = 9.0; PT_T = 6.5; PT_L = 16.0; PT_FLOOR = 1.2;
module pigtail_bulge(c) translate([IN_X - (PT_T - WALL + PT_FLOOR), c[0] - PT_W / 2 - 1.5, c[1] - PT_L / 2 - 1.5]) cube([PT_T - WALL + PT_FLOOR, PT_W + 3, PT_L + 3]);
PT_C = [18.405, 36.0];
if (part == "probe") intersection() { pb_v3(); translate([79.0, 28, 42.0]) cube([1.5, 30, 4]); }
if (part == "chk_brpb") intersection() { bridge_v3(); pb_v3(); }   // ブリッジの足と柱と L ↔ PowerBoost
if (part == "chk_hook") intersection() { pb_front_hook(); union() { pb_v3(); right_wall_v3(); bridge_v3(); pb_usb_space(); } }
if (part == "chk_usb")  intersection() { pb_usb_space(); union() { right_wall_v3(); bridge_v3(); top_plate(); manaita(); } }
if (part == "chk_wall") intersection() { right_wall_v3(); union() { bridge_v3(); manaita(); translate(LIPO_AT) lipo_1000mah(); } }
if (part == "chk_wall_br") intersection() { right_wall_v3(); bridge_v3(); }
if (part == "chk_br_mana") intersection() { bridge_v3(); manaita(); }   // ブリッジ ↔ まな板（床・ハブ・ReSpeaker・後列のハウジング）
if (part == "chk_wall_m") intersection() { right_wall_v3(); manaita(); }
if (part == "chk_lwall") intersection() { left_wall_v3(); union() { bridge_v3(); manaita(); translate(LIPO_AT) lipo_1000mah(); } }
if (part == "chk_pbdowel") intersection() { pb_v3(); right_wall_v3(); }   // 穴にピンが入る分だけ出るのが正
// 電池の蓋まわり
if (part == "chk_shut")   intersection() { left_wall_extras(); union() { left_wall_v3(); bridge_v3(); translate(LIPO_AT) lipo_1000mah(); manaita(); top_plate(); } }
if (part == "chk_shut_open") intersection() { battery_shutter(1); union() { left_wall_v3(); bridge_v3(); translate(LIPO_AT) lipo_1000mah(); manaita(); top_plate(); } }
if (part == "chk_swap")   intersection() { translate(LIPO_AT - [LIPO_L + WALL + 5, 0, 0]) lipo_swap_path(travel = LIPO_L + WALL + 5, clear = 0.3); union() { left_wall_v3(); bridge_v3(); manaita(); } }   // 電池を左へ抜く道（壁の外 5 まで）
if (part == "chk_lwall_lipo") intersection() { left_wall_v3(); translate(LIPO_AT) lipo_1000mah(); }
if (part == "chk_lwall_m") intersection() { left_wall_v3(); manaita(); }
if (part == "chk_lwall_top") intersection() { left_wall_v3(); top_plate(); }
if (part == "chk_lwall_br") intersection() { left_wall_v3(); bridge_v3(); }
if (part == "chk_rwall_rsp") intersection() { right_wall_v3(); sweep_z(SWEEP) respeaker_at(); }   // 右の壁を Z で降ろすとき USB-C の殻を通るか（環だと当たる＝想定どおり）
// ⑨ は 2 段: (a) 左の壁＋ブリッジ＋INA226＋電池を Z で降ろす (b) 右の壁（ダボに載せた PowerBoost ごと）を +X から差す
module side_struct_noR() { left_wall_v3(); bridge_v3(); translate([INA_AT[0], INA_AT[1] + ina_size()[1], INA_AT[2] + ina_h()]) rotate([180, 0, 0]) ina226_module(); translate(LIPO_AT) lipo_1000mah(); }
module right_wall_grp() { right_wall_v3(); pb_v3(); }
module sweep_x(n) for (t = [0 : STEP : n]) translate([t, 0, 0]) children();
// （経緯）一度「右の壁だけ横から差す」にしたが、ユーザー「両方上から降ろせないとダメ」で取り下げ。検査だけ残す
if (part == "close_a") intersection() { side_struct_noR(); sweep_z(SWEEP) manaita(); }
if (part == "close_b") intersection() { sweep_x(SWEEP) right_wall_grp(); union() { manaita(); side_struct_noR(); } }
// 断面の絵: 口の Y（18.4）で切った X-Z。壁・増し壁・殻・殻の通り道
if (part == "pic_port_sec") {   // カメラは口の中心 [X 86, Z 19.5]・--camera=86,19.5,0,0,0,0,95（画面の上が上）
    slab("#c9d0d8") sec_y(XIAO_PORT_C[0]) right_wall_v3();
    slab("#7d8794") sec_y(XIAO_PORT_C[0]) respeaker_at();
    slab("#9aa5b1") sec_y(XIAO_PORT_C[0]) manaita();                                                     // 床（下が下）
    slab("#e6194b") sec_y(XIAO_PORT_C[0]) intersection() { translate([0, 0, 30]) sweep_z(30) respeaker_at(); translate([XIAO_FACE_X - 2, 0, 0]) cube([3, 40, 80]); }   // 殻の通り道（壁が上から降りる＝壁から見ると殻は上から来る。実体は最終位置の上 30 まで）
}
if (part == "look_rwall_out") { right_wall_v3(); }
// まな板
if (part == "chk_floor")  intersection() { floor_v3(); union() { hub_at(); respeaker_at(); oled_at(); for (id = PLUGGED_9) housing(id); } }
if (part == "chk_floor_side") intersection() { floor_v3(); side_struct(); }
if (part == "chk_floor_hatch") intersection() { floor_v3(); hatch(); }
if (part == "chk_claw_slide") intersection() { sweep_y(12) hatch(); union() { floor_v3(); side_struct(); top_plate(); manaita(); } }   // ハッチを −Y へ滑り込ませる道（12mm）
if (part == "chk_top_parts") intersection() { top_plate_raw(); union() { respeaker_at(); oled_at(); translate([SPK_X, SPK_Y, IN_Z - spk_th() - 0.2]) speaker_112495(); translate([BTN_AT[0], BTN_AT[1], Z_TSW_BOT]) tactswitch(); translate(KNOB_AT) assembly(show_deck = false); translate([TGL_AT[0], IN_Y, TGL_AT[1]]) rotate([-90, 0, 0]) mts102(0); } }
if (part == "chk_top_side") intersection() { top_plate_raw(); union() { side_struct(); translate(LIPO_AT) lipo_1000mah(); } }
if (part == "chk_shelf_hooks") intersection() { shelf_hooks(); union() { toggle_shelf(); toggle_shelf_flanges(); translate([TGL_AT[0], IN_Y, TGL_AT[1]]) rotate([-90, 0, 0]) mts102(0); } }
if (part == "look_top_in") { top_plate(); }
if (part == "chk_top_lwall") intersection() { top_plate_raw(); left_wall_v3(); }
if (part == "chk_top_rwall") intersection() { top_plate_raw(); right_wall_v3(); }
if (part == "chk_floor_rsp") intersection() { floor_v3(); respeaker_at(); }
if (part == "chk_floor_hub") intersection() { floor_v3(); hub_at(); }
if (part == "chk_floor_oled") intersection() { floor_v3(); oled_at(); }
if (part == "look_floor") { floor_v3(); }
if (part == "look_floor_all") { manaita(); }
// ---- 印刷部品（外周の角丸をかけた物）。刷る向きは別（print_* で出す）----
if (part == "p_floor")  rounded() floor_v3();
if (part == "p_lwall")  rounded() left_wall_v3();
if (part == "p_rwall")  rounded() right_wall_v3();
if (part == "p_bridge") bridge_v3();
// ---- v2 の part="bridge" を復活（2026-08-23 ユーザー）----------------------
// **波板（トラス）だけ**を、実際に効いている切り欠きを通した実物で見る。トンネル・足・柱・L は外す。
// ⭐ v2 の教訓「F5 の絵で形を判断しない。体積で確かめる」。欠けた分は "bridge_eaten" で出して測る:
//    openscad --backend=manifold -o x.stl -D 'part="bridge_eaten"' hardware/case_v3.scad → python _bbox.py x.stl
module bridge_slab() translate([0, BR_Y0, BR_ZB]) cube([BR_X1, BR_Y1 - BR_Y0, BR_DEPTH]);
module bridge_truss()     intersection() { bridge_v3(); bridge_slab(); }
module bridge_truss_raw() intersection() { rotate([90, 0, 90]) linear_extrude(BR_X1) bridge_section(); bridge_slab(); }
if (part == "bridge")       bridge_truss();
if (part == "bridge_eaten") difference() { bridge_truss_raw(); bridge_truss(); }
if (part == "p_top")    rounded() top_plate_raw();
if (part == "p_front")  rounded() front_plate_raw();
if (part == "p_hatch")  rounded() hatch_raw();
if (part == "p_shelf")  { toggle_shelf(); toggle_shelf_flanges(); }
if (part == "p_tail")   translate([0, 0, -0.2]) tail_cap();   // 底の球の先を Z 0 に
if (part == "chk_tail") intersection() { tail_at(); union() { hatch_raw(); translate([TGL_AT[0], IN_Y, TGL_AT[1]]) rotate([-90, 0, 0]) mts102(TAIL_ANG); } }   // レバーは尻尾と同じ角度（ボアの中）
if (part == "p_shutter") battery_shutter(0);
if (part == "p_lock")   battery_lock();
if (part == "p_btncap") translate([BTN_AT[0], BTN_AT[1], 0]) button_cap();
if (part == "p_btnclip") button_clip();
if (part == "look_all") { rounded() union() { floor_v3(); left_wall_v3(); right_wall_v3(); top_plate_raw(); front_plate_raw(); hatch_raw(); } bridge_v3(); }
if (part == "chk_seam") intersection() { top_plate_raw(); front_plate_raw(); }   // 継ぎ目で重なっていないか
if (part == "chk_ears") intersection() { front_ears(); union() { oled_at(); respeaker_at(); top_plate_raw(); side_struct(); manaita(); } }
// 🔒 2026-08-23 天面のビス 4 本化（前の 2 本を耳と兼用）で、フロントは天面と一緒に降りず最後に前から差し込む。⑫ の検査は 2 つに割れた
if (part == "close_tf")    intersection() { union() { top_plate_raw(); oled_at(); oled_brackets(); } sweep_z(SWEEP) { manaita(); side_struct(); } }   // ⑫前半: 天面＋OLED を Z で降ろす
if (part == "close_front") intersection() { sweep_ny(SWEEP) front_plate_raw();
                                            union() { manaita(PLUGGED_9); side_struct(); top_plate(); hatch_raw(); oled_at(); oled_brackets(); wires_v3(); } }   // ⑫後半: フロントを前から +Y に差し込む
if (part == "chk_front") intersection() { front_plate_raw(); union() { oled_at(); respeaker_at(); floor_v3(); top_plate_raw(); left_wall_v3(); right_wall_v3(); } }
if (part == "chk_hatch_tc") intersection() { hatch_raw(); union() { manaita(); side_struct(); top_plate_raw(); } }
if (part == "look_lwall") { left_wall_v3(); left_wall_extras(); bridge_v3(); translate(LIPO_AT) lipo_1000mah(); }
// PowerBoost の局所 → 箱（side_struct の置き方と同じ）。（旧・JST 下向き）(PB_X1 - z, PB_Y0 + x, PB_ZT - y)
function pb2box(p) = [PB_X1 - p[2], PB_Y0 + p[0], PB_ZT - p[1]];
function pb_holes_yz() = [for (m = pb_mount()) let (b = pb2box([m[0], m[1], 0])) [b[1], b[2]]];
XIAO_PORT_C = [RSP_BD_Y1 + xiao_usb_yz()[0], RSP_Z + xiao_usb_yz()[1]];   // [Y, Z] = [18.4, 19.5]
CHG_C_V2 = [XIAO_PORT_C[0], 35.5];                                        // v2: XIAO の口の真上。🔴 v3 ではハウジング（奥行 25）が充電プラグの空間と PowerBoost に 557mm3 当たる
CHG_C = [71.2, 33.5];                                                     // 🔴 右の壁の後ろ寄り → ユーザー却下（2026-08-23）。（経緯のみ）

// 充電口の Type-C メスのハウジング（⚠ 仮 25 × 12 × 7・着荷実測待ち）。鼻先が壁の内面、胴は X の内側へ
TC_L = 25.0; TC_W = 12.0; TC_T = 7.0;
module typec_housing(c) translate([IN_X - TC_L, c[0] - TC_W / 2, c[1] - TC_T / 2]) cube([TC_L, TC_W, TC_T]);   // c = [Y, Z]
TC_C = CHG_C;   // -D で差し替え

echo(str("PB 穴 [Y,Z] ", pb_holes_yz(), "  PB 板 Y ", PB_Y0, "〜", PB_Y0 + PB_L, " Z ", PB_ZT - PB_W, "〜", PB_ZT,
         "  ブリッジ右端 Y ", BR_Y0, "〜", BR_Y1, " Z ", BR_ZB, "〜", BR_ZT, "  XIAO 口 ", XIAO_PORT_C, " 充電 ", CHG_C));
// 左の壁を**外**から見た絵（カメラ [90,0,270]）。画面の左が後ろ（ハッチ）、右が前（OLED 側）
CHG_C_L = [44.5, 19.2];   // 充電口の候補: 左の壁・電池の蓋の下（前寄りは J2 と AS5600 の口、後ろ寄りは BTN2 の口で塞がる）。30×14×7.6 まで 0
if (part == "pic_lwall_out") {
    color("#c9d0d8") translate([-WALL, -BEZ_T, -FLOOR_T]) cube([IN_X + 2 * WALL, IN_Y + BEZ_T + HATCH_T, IN_Z + TOP_T + FLOOR_T]);   // 箱の外形
    color("#e53e3e") translate([-WALL - 1.0, CHG_C_LW[0] - 1.93, CHG_C_LW[1] - 4.77]) cube([1.5, 3.86, 9.54]);                     // 充電の口（候補）
    color("#4a5568", 0.5) translate([-WALL - 0.8, LIPO_AT[1] - TUN_CL, LIPO_AT[2] - TUN_CL]) cube([1.0, LIPO_W + 2 * TUN_CL, LIPO_TH + 2 * TUN_CL]);   // 電池の口（v2 の蓋の帯のおおよそ）
    color("#555") translate([-WALL - 1.5, IN_Y - 3, IN_Z - 4]) rotate([90, 0, 270]) linear_extrude(1) text("BACK", size = 3.5);
    color("#555") translate([-WALL - 1.5, 14, IN_Z - 4]) rotate([90, 0, 270]) linear_extrude(1) text("FRONT", size = 3.5);
    color("#555") translate([-WALL - 1.5, CHG_C_LW[0] + 6, CHG_C_LW[1] - 12]) rotate([90, 0, 270]) linear_extrude(1) text("USB-C", size = 3);
    color("#555") translate([-WALL - 1.5, LIPO_AT[1] + 28, LIPO_AT[2] + 9]) rotate([90, 0, 270]) linear_extrude(1) text("battery lid", size = 3);
}
if (part == "pic_rwall") {   // カメラ [90,0,270]（左から見る）で壁の内面が正面。画面の右が前（OLED 側）
    color("#e8e8e8") translate([IN_X, 0, 0]) cube([WALL, IN_Y, IN_Z]);                                // 壁
    color("#2f855a") intersection() { bridge_v3(); translate([IN_X - 0.5, 0, 0]) cube([0.5, IN_Y, IN_Z]); }   // ブリッジが壁に触れる所（緑）
    color("#b6c0cc", 0.5) intersection() { bridge_v3(); translate([BR_X1 - 0.01, 0, 0]) cube([IN_X - BR_X1 + 0.02, IN_Y, IN_Z]); }   // 足と柱
    color("#2b6cb0", 0.5) translate([IN_X - pb_pcb_t() - 0.01, PB_Y0, PB_ZT - PB_W]) cube([pb_pcb_t(), PB_L, PB_W]);   // PB 基板
    for (h = pb_holes_yz()) color("#e6194b") translate([IN_X - 3, h[0], h[1]]) rotate([0, 90, 0]) cylinder(d = 2.5, h = 4, $fn = 24);
    color("#222") translate([IN_X - 1, XIAO_PORT_C[0] - 1.93, XIAO_PORT_C[1] - 4.77]) cube([4, 3.86, 9.54]);   // XIAO の口
    color("#222") translate([IN_X - 1, CHG_C[0] - 1.93, CHG_C[1] - 4.77]) cube([4, 3.86, 9.54]);               // 充電の口（v2 の位置）
    color("#8892a0") for (b = BOSSES) if (b[0] > IN_X / 2) translate([b[0], b[1], IN_Z - BOSS_H]) cube([BOSS, BOSS, BOSS_H]);   // 右の柱
    color("#2f855a") translate([IN_X - 0.5, COL_Y0, BR_ZB]) cube([0.5, POST_W, BR_DEPTH]);                  // 柱が壁に触れる所
    color("#555") translate([IN_X - 1, IN_Y - 8, IN_Z - 6]) rotate([90, 0, 270]) linear_extrude(1) text("BACK", size = 3);
    color("#555") translate([IN_X - 1, 14, IN_Z - 6]) rotate([90, 0, 270]) linear_extrude(1) text("FRONT", size = 3);
}
// ⑪ の読み 2 つ（絵）
//   A: 組んだ本体を天面を下にして伏せ、ハッチ（トグル付き）を後ろから当てる
//   B: トグルをレバーを下にして作業台に置き、ハッチの板を上から被せてナットを締める
module hatch_plate() { color("#c9d0d8") translate([-WALL, IN_Y, 0]) cube([IN_X + 2 * WALL, HATCH_T, IN_Z]); }
module toggle_on_hatch() { translate([TGL_AT[0], IN_Y, TGL_AT[1]]) rotate([-90, 0, 0]) mts102(0); }
module body_no_hatch() { manaita(); side_struct(); top_plate(); front_plate(); }
if (part == "pic_tgl_a") {
    translate([0, 0, IN_Z + TOP_T]) rotate([180, 0, 0]) {                 // 天面を下に（Z を反転）
        body_no_hatch();
        translate([0, 25, 0]) { hatch_plate(); toggle_on_hatch(); }     // ハッチは後ろへ 25 離して
    }
    color("#ddd") translate([-30, -120, -3]) cube([150, 160, 2]);        // 作業台
}
if (part == "pic_tgl_b") {
    L = mts102_lever();
    color("#ddd") translate([-30, -30, -2]) cube([150, 110, 2]);                    // 作業台（上面 Z 0）
    translate([TGL_AT[0], TGL_AT[1], L]) rotate([180, 0, 0]) mts102(0);            // レバーを下にして置く（先端が台）
    translate([0, 0, L + 15 + IN_Y + HATCH_T]) rotate([-90, 0, 0])                  // ハッチの外面を下に、15 上に浮かせる
        color("#c9d0d8", 0.45) difference() { translate([-WALL, IN_Y, 0]) cube([IN_X + 2 * WALL, HATCH_T, IN_Z]); translate([TGL_AT[0], IN_Y - 1, TGL_AT[1]]) rotate([-90, 0, 0]) mts102_hole(HATCH_T + 2); }
}
// ReSpeaker の取付穴 2 つ（正面から見た絵）。A = 右上の角、B = 下辺・左端から 21.8
function rsp_hole_xz(h) = [RSP_X + respeaker_L() - h[0], RSP_Z + h[1]];
RSP_HOLE_A = rsp_hole_xz([2.492, 31.577]); RSP_HOLE_B = rsp_hole_xz([60.202, 2.657]);
if (part == "pic_rsp") {
    respeaker_at();
    color("#9aa5b1") translate([-WALL, -BEZ_T, -FLOOR_T]) cube([IN_X + 2 * WALL, 20, FLOOR_T]);
    color("#b6c0cc") translate([-WALL, 0, 0]) cube([WALL, 20, IN_Z]);
    color("#b6c0cc") translate([IN_X, 0, 0]) cube([WALL, 20, IN_Z]);
    for (h = [RSP_HOLE_A, RSP_HOLE_B]) color("#e6194b") translate([h[0], RSP_BD_Y0 - 3, h[1]]) rotate([-90, 0, 0]) cylinder(d = 4, h = 3, $fn = 24);
    color("#e6194b") translate([RSP_HOLE_A[0] - 8, RSP_BD_Y0 - 3, RSP_HOLE_A[1] + 4]) rotate([90, 0, 0]) linear_extrude(0.5) text("A", size = 5);
    color("#e6194b") translate([RSP_HOLE_B[0] - 2, RSP_BD_Y0 - 3, RSP_HOLE_B[1] + 5]) rotate([90, 0, 0]) linear_extrude(0.5) text("B", size = 5);
}
// 断面の絵: 左 = PWR の口の X（後列。⑩ で挿す口がブリッジの後ろに見えるか）/ 右 = 電池の中央 Y（X-Z）
module sec_x(x) { mirror([1, 0]) rotate(90) projection(cut = true) rotate([0, 90, 0]) translate([-x, 0, 0]) children(); }
module sec_y(y) { mirror([0, 1]) projection(cut = true) rotate([90, 0, 0]) translate([0, -y, 0]) children(); }
module slab(c) color(c) linear_extrude(1) children();
if (part == "pic") {
    PX = port_at("PWR")[0];
    slab("#c9d0d8") sec_x(PX) side_struct();
    slab("#7d8794") sec_x(PX) manaita(concat(PLUGGED_9, PLUGGED_10));
    slab("#e6194b") sec_x(PX) housing("PWR");
    translate([0, 54]) linear_extrude(1) text(str("X ", PX, " (Y-Z): PWR port, hatch open"), size = 3);
    translate([120, 0]) {
        slab("#c9d0d8") sec_y(40) side_struct();
        slab("#7d8794") sec_y(40) manaita(concat(PLUGGED_9, PLUGGED_10));
        slab("#e6194b") sec_y(40) top_plate();
        translate([0, 54]) linear_extrude(1) text("Y 40 (X-Z): bridge, INA226, PB, battery, knob", size = 3);
    }
}
if (part == "side")    side_struct();

// ---- 充電口の Type-C メスのハウジング（仮 25 × 12 × 7・着荷実測待ち）を置いて当てる ----
//   右の壁の後ろ寄りはユーザー却下（2026-08-23「そこが例のとんでもない場所」）。候補は左の壁・前寄りの下（XIAO の口の鏡写し）
module typec_housing_L(c) translate([0, c[0] - TC_T / 2, c[1] - TC_W / 2]) cube([TC_L, TC_T, TC_W]);   // c = [Y, Z]・左の壁の内面から X の内側へ。縦置き（幅 12 が Z）
if (part == "pic_typec_L") {   // 左の壁の充電口の断面（Z = 口の中心・上から）: ハウジング（赤）とハブの後列のプラグ・四隅の柱
    slab("#7d8794") sec_z(CHG_C_LW[1]) manaita(concat(PLUGGED_9, PLUGGED_10));
    slab("#b6c0cc") sec_z(CHG_C_LW[1]) union() { left_wall_v3(); hatch_raw(); floor_v3(); }
    slab("#e53e3e") sec_z(CHG_C_LW[1]) typec_housing_L(CHG_C_LW);
}
if (part == "chk_tgl") intersection() { translate([TGL_AT[0], IN_Y, TGL_AT[1]]) rotate([-90, 0, 0]) mts102(0); union() { side_struct(); top_plate(); manaita(concat(PLUGGED_9, PLUGGED_10)); } }   // トグル（ハッチに付く）↔ 中身
if (part == "chk_typec_L") intersection() { typec_housing_L(TC_C); union() { manaita(); side_struct(); top_plate(); front_plate(); pb_usb_space(); } }
if (part == "look_typec_L") { manaita(); side_struct(); color("#e53e3e") typec_housing_L(TC_C); }

// ---- 充電口の置き場の地図を作るための「中身＋外皮」の一体（scratch/_typec_map.py が読む）----
// ==== 表示を絞る（2026-08-24 ユーザー指示）=========================================
// 使い方: openscad -D 'part="show"' -D 'SHOW=["pb","rsp","rwall"]' hardware/case_v3.scad
//   SHOW = [] は全部。名前は NAMES_ALL のとおり。
//   充電口の検討に要る物だけなら part="chg"（pb・rsp・rwall・bridge・usb）。
NAMES_ALL = ["floor", "hub", "rsp", "oled", "hous", "lwall", "rwall", "bridge",
             "ina", "pb", "lipo", "knob", "top", "front", "hatch", "usb", "adapter", "next", "tcb"];
// 充電口の L 字アダプタ（B0CTMHK3BY）を PowerBoost の口に挿した姿勢。
//   ローカル +Z（プラグ軸・挿さる向き）→ 箱の +Y、ローカル +X（肘＝広い面の側）→ 箱の −X（部品面の側）、ローカル Y → 箱の Z
CHG_PORT_C = pb2box([-0.5, pb_usb()[1], pb_pcb_t() + pb_usb_sz()[2] / 2]);   // 口の面の中心 (81.7, 23.5, 36.4)
module at_chg_port() translate(CHG_PORT_C) multmatrix([[-1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]]) children();
module chg_adapter()      at_chg_port() usb_l_adapter();
module chg_adapter_body() at_chg_port() usb_l_adapter_body();        // 口の外に出る部分（当たり検査用）
module chg_next_plug()    at_chg_port() usb_l_adapter_next_plug();   // 肘の先に挿すストレートのプラグ（⚠ 仮寸法）
echo(str("充電口 L字アダプタ: 口の面から外へ ", la_out_len(), "  肘の先（ソケットの面）は口の軸から内側へ ", la_reach(), "  ⇒ X ", CHG_PORT_C[0] - la_reach()));
module one(k) {
    if (k == "floor")  floor_v3();
    if (k == "hub")    hub_at();
    if (k == "rsp")    respeaker_at();
    if (k == "oled")   oled_at();
    if (k == "hous")   for (id = PLUGGED_9) housing(id);
    if (k == "lwall")  left_wall_v3();
    if (k == "rwall")  right_wall_v3();
    if (k == "bridge") bridge_v3();
    if (k == "ina")    translate([INA_AT[0], INA_AT[1] + ina_size()[1], INA_AT[2] + ina_h()]) rotate([180, 0, 0]) ina226_module();
    if (k == "pb")     pb_v3();
    if (k == "lipo")   translate(LIPO_AT) lipo_1000mah();
    if (k == "knob")   translate(KNOB_AT) assembly(show_deck = false);
    if (k == "top")    top_plate_raw();
    if (k == "front")  front_plate_raw();
    if (k == "hatch")  hatch_raw();
    if (k == "usb")    pb_usb_space();
    if (k == "adapter") chg_adapter();
    if (k == "next")   chg_next_plug();
    if (k == "tcb")    { tcb_at(); tcb_ra(); }
}
module show_only(names) for (k = (len(names) == 0 ? NAMES_ALL : names)) one(k);
SHOW = [];
if (part == "show") show_only(SHOW);
if (part == "chg")  show_only(["pb", "rsp", "rwall", "bridge", "adapter"]);
if (part == "chg_next") show_only(["pb", "rsp", "rwall", "bridge", "adapter", "next"]);
// L 型ヘッダ（8 ピン列・GND/EN/USB）に Dupont ハウジングを挿した状態 ↔ 全部（2026-08-24）
module pb_ra_housings() for (i = [3, 4]) { x = 12.83 + i * 2.54; a = pb2box([x - 1.27, 2.54, pb_pcb_t() + 2.5 - 1.27]); b = pb2box([x + 1.27, 2.54 + HOUS_H, pb_pcb_t() + 2.5 + 1.27]); translate([min(a[0], b[0]), min(a[1], b[1]), min(a[2], b[2])]) cube([abs(a[0] - b[0]), abs(a[1] - b[1]), abs(a[2] - b[2])]); }   // 部品面の L 字（GND・EN）のハウジング
module pb_usb_housing() { c = pb2box([12.83 + 7 * 2.54, 1.27, pb_pcb_t() + 2.5]); translate([c[0] - HOUS_H, c[1] - 1.27, c[2] - 1.27]) cube([HOUS_H, 2.54, 2.54]); }
module pb_usb_housing() { c = pb2box([12.83 + 7 * 2.54, 1.27, pb_pcb_t() + 2.5]); translate([c[0] - HOUS_H, c[1] - 1.27, c[2] - 1.27]) cube([HOUS_H, 2.54, 2.54]); }   // USB の真っ直ぐな 1 ピンに挿すハウジング（−X へ 10）
if (part == "chk_usb_hous") intersection() { pb_ra_housings(); union() { manaita(); side_struct_noPB(); top_plate(); front_plate(); hatch(); } }   // 裏の 3 本まとめて
if (part == "chk_ra_hous") intersection() { pb_ra_housings(); union() { manaita(); side_struct_noPB(); top_plate(); front_plate(); hatch(); } }   // 自分のピンは除く
module side_struct_noPB() { left_wall_v3(); right_wall_v3(); bridge_v3(); translate([INA_AT[0], INA_AT[1] + ina_size()[1], INA_AT[2] + ina_h()]) rotate([180, 0, 0]) ina226_module(); translate(LIPO_AT) lipo_1000mah(); }
if (part == "chk_adapter") intersection() { chg_adapter_body(); union() { manaita(); side_struct(); top_plate(); front_plate(); hatch(); } }   // 口の外に出る部分 ↔ 全部
if (part == "chk_next")    intersection() { chg_next_plug();    union() { manaita(); side_struct(); top_plate(); front_plate(); hatch(); } }
// ==================================================================================
// ---- Access EC22-P-ST（B0B4SHDRZN・25cm・パネル取付 Type-C メス ← ストレート micro-B オス）を L 字アダプタの先に挿した検査（2026-08-24）
//   ⚠ 寸法は商品ページに無い。写真と一般的な同種品からの**仮**: プラグの頭（モールド）11 × 7 × 17、フランジ 28 × 12 × 2（穴ピッチ 20・M3）、胴 12 × 8 × 奥行 14
AC_HEAD = [17.0, 7.0, 11.0];     // X 長さ × Y 厚み × Z 幅（ソケットの広い辺は Z）⚠ 仮
AC_FLANGE = [28.0, 2.0, 12.0];   // X × Y（厚）× Z ⚠ 仮
AC_BODY = [12.0, 14.0, 8.0];     // X × Y（奥行）× Z ⚠ 仮
AC_SOCK_X = CHG_PORT_C[0] - la_reach();                      // L 字アダプタのソケットの面 X 68.0
AC_SOCK_Y = CHG_PORT_C[1] - la_out_len() + 6.5 / 2;           // 胴の厚みの中央 Y 18.75
module access_plug_head() color("#2b6cb0") translate([AC_SOCK_X - AC_HEAD[0], AC_SOCK_Y - AC_HEAD[1] / 2, CHG_PORT_C[2] - AC_HEAD[2] / 2]) cube(AC_HEAD);
module access_panel_tc() {   // ハッチの内面にフランジ、その手前に胴
    c = CHG_C_B;
    color("#2b6cb0") translate([c[0] - AC_FLANGE[0] / 2, IN_Y - AC_FLANGE[1], c[1] - AC_FLANGE[2] / 2]) cube(AC_FLANGE);
    color("#2b6cb0") translate([c[0] - AC_BODY[0] / 2, IN_Y - AC_FLANGE[1] - AC_BODY[1], c[1] - AC_BODY[2] / 2]) cube(AC_BODY);
}
module hatch_noPocket() difference() { hatch(); typec_pocket_add(); }   // 既存のポケット（別品用）は外して当てる
if (part == "chk_access_head")  intersection() { access_plug_head(); union() { manaita(); side_struct(); top_plate(); front_plate(); hatch(); chg_adapter_body(); } }
if (part == "chk_access_panel") intersection() { access_panel_tc(); union() { manaita(); side_struct(); top_plate(); front_plate(); hatch_noPocket(); } }
if (part == "chk_access_panel_pocket") intersection() { access_panel_tc(); typec_pocket_add(); }   // 既存ポケットとの干渉（別品用なので当たって当然）
if (part == "chg_access") { show_only(["pb", "rsp", "rwall", "bridge", "adapter", "lipo", "knob", "hatch"]); access_plug_head(); access_panel_tc(); }
// ---- 充電口の Type-C 基板（秋月 115426）を左の壁・後ろ下（🔒 2026-08-23 CHG_C_LW）に縦置き（2026-08-24）
//   板は壁に平行。口は壁の外面 − 0.3。部品面はハッチ側（+Y）。ピン列（7 本）は上。使う 4 本（VBUS・GND・CC1・CC2）に L 型を付け、箱の内側（+X）へ Dupont
//   🔴 CC1/CC2 は基板に抵抗が無い。5.1kΩ × 2 を CC1-GND / CC2-GND に付ける（スルーホール）
TCB_NOSE_X = -WALL + 0.3;
TCB_X_EDGE = TCB_NOSE_X + tc_nose_y();                        // 14.1 ピン側の縁
TCB_YB     = CHG_C_LW[0] - tc_size()[2] - tc_conn()[2] / 2;   // 64.47 板の裏
TCB_ZTOP   = CHG_C_LW[1] + tc_size()[0] / 2;                  // 20.5
function tcb2box(p) = [-p[1] + TCB_X_EDGE, p[2] + TCB_YB, -p[0] + TCB_ZTOP];
module tcb_at() multmatrix([[0, -1, 0, TCB_X_EDGE], [0, 0, 1, TCB_YB], [-1, 0, 0, TCB_ZTOP], [0, 0, 0, 1]]) typec_115426(pins = false);
module tcb_box(p0, p1) { a = tcb2box(p0); b = tcb2box(p1); translate([min(a[0], b[0]), min(a[1], b[1]), min(a[2], b[2])]) cube([abs(a[0] - b[0]) + 0.001, abs(a[1] - b[1]) + 0.001, abs(a[2] - b[2]) + 0.001]); }
TCB_PINS = [0, 1, 4, 5];
module tcb_ra()   for (i = TCB_PINS) { x = 2.54 + i * 2.54; color("#222") tcb_box([x - 1.27, 1.27, 1.6], [x + 1.27, 3.81, 4.1]); color("#c8ccd0") tcb_box([x - 0.32, 1.27 - 6, 3.78], [x + 0.32, 1.27, 4.42]); }
module tcb_hous() for (i = TCB_PINS) { x = 2.54 + i * 2.54; tcb_box([x - 1.27, 1.27 - HOUS_H, 2.83], [x + 1.27, 1.27, 5.37]); }
module tcb_slot_cut() translate([-WALL - 1, TCB_YB - 0.3, TCB_ZTOP - tc_size()[0] - 0.3]) cube([WALL + 1 + (TCB_NOSE_X + tc_nose_y() - tc_size()[1]) + 0.3, tc_size()[2] + 0.6, tc_size()[0] + 0.6]);   // 板の縁が壁に 0.9 入る分の溝
if (part == "chk_tcb")      intersection() { union() { tcb_at(); tcb_ra(); } union() { manaita(); side_struct(); top_plate(); front_plate(); hatch(); floor_v3(); difference() { left_wall_v3(); tcb_slot_cut(); } } }
if (part == "chk_tcb_hous") intersection() { tcb_hous(); union() { manaita(); side_struct(); top_plate(); front_plate(); hatch(); floor_v3(); left_wall_v3(); } }
if (part == "look_tcb")     { show_only(["lwall", "hub", "floor", "hous", "hatch"]); tcb_at(); tcb_ra(); color("#f6ad55", 0.6) tcb_hous(); }
// ---- 🔍 検討用（本体は動かさない）: PowerBoost を右の床に立てて見る（2026-08-24 ユーザー「試しに置いてみてよ」）
//   右の壁に沿って立てる（裏は壁から 1.2）。JST 上・8 ピン列が下端・部品面の L 字は上向き（ハウジングは手に持って挿してから置く前提）
//   床から 4.5 上げてある（USB のハウジングがハブ基板の上面 4.1 をかわす分）。押さえ方は未設計
PBF_Z0 = 4.5;
module pb_floor_probe() translate([IN_X - 1.2, PB_Y0 + PB_L, PBF_Z0]) rotate([0, -90, 0]) rotate([0, 0, 90]) rotate([0, 0, 180]) { powerboost_1000c(hdr = "front", ra_dir = 1); pb_jst_plug(); }
if (part == "pb_floor_look") { show_only(["floor", "hub", "rsp", "rwall", "bridge", "ina", "lipo", "hous"]); pb_floor_probe(); }
if (part == "obstacles") union() { manaita(); side_struct(); top_plate(); front_plate(); hatch(); pb_usb_space(); }
// 🔒 充電口はハッチ（2026-08-23 ユーザー「ハッチの左上」＝地図の左上＝箱の左の壁寄り・上。後ろから見ると右上）
module typec_housing_B(c) translate([c[0] - TC_W / 2, IN_Y - TC_L, c[1] - TC_T / 2]) cube([TC_W, TC_L, TC_T]);   // c = [X, Z]・ハッチの内面から -Y へ
if (part == "chk_typec_B") intersection() { typec_housing_B(TC_C); union() { manaita(); side_struct(); top_plate(); front_plate(); pb_usb_space(); } }
// ハッチを**後ろから**見た絵（カメラ [90,0,180]）。画面の左が箱の右（XIAO の壁）、右が箱の左（電池の蓋の壁）
if (part == "pic_hatch_out") {
    color("#c9d0d8") translate([-WALL, -BEZ_T, -FLOOR_T]) cube([IN_X + 2 * WALL, IN_Y + BEZ_T + HATCH_T, IN_Z + TOP_T + FLOOR_T]);
    color("#e53e3e") translate([CHG_C_B[0] - 4.77, IN_Y + HATCH_T - 0.5, CHG_C_B[1] - 1.93]) cube([9.54, 1.5, 3.86]);      // 充電の口（横長）
    color("#111") translate([TGL_AT[0], IN_Y + HATCH_T - 0.5, TGL_AT[1]]) rotate([-90, 0, 0]) cylinder(d = 6.4, h = 1.5, $fn = 32);   // トグルの穴
    color("#555") translate([IN_X - 4, IN_Y + HATCH_T + 0.5, IN_Z - 4]) rotate([90, 0, 180]) linear_extrude(1) text("R wall (XIAO)", size = 3);
    color("#555") translate([22, IN_Y + HATCH_T + 0.5, IN_Z - 4]) rotate([90, 0, 180]) linear_extrude(1) text("L wall (lid)", size = 3);
    color("#555") translate([CHG_C_B[0] + 7, IN_Y + HATCH_T + 0.5, CHG_C_B[1] - 8]) rotate([90, 0, 180]) linear_extrude(1) text("USB-C", size = 3);
}
if (part == "look_pad") { xiao_pad(); }
if (part == "look_pad_cut") difference() { xiao_pad(); right_wall_ports_cut(); }
// 充電ケーブル（平たいリボン・幅 ⚠6・厚み ⚠1.5）がハウジングの奥（Y = IN_Y − TC_L）からまっすぐ −Y へ出て、下（ブリッジの上 Z 29.3）へ曲がる空間
CAB_W = 6.0; CAB_T = 1.5; CAB_LEAD = 8.0; CAB_R = 8.0;   // リボンの幅 / 厚み / まっすぐ出る長さ / 曲げ半径（⚠ 見込み）
module typec_cable_zone(c) {   // c = [X, Z]（ハッチの口の中心）
    x0 = c[0] - CAB_W / 2; yb = IN_Y - TC_L;
    translate([x0, yb - CAB_LEAD, c[1] - CAB_T / 2]) cube([CAB_W, CAB_LEAD, CAB_T]);                               // まっすぐ
    translate([x0, yb - CAB_LEAD, c[1] - CAB_T / 2 - CAB_R]) difference() {                                        // 下へ 90° 曲がる（四分円）
        rotate([90, 0, 90]) translate([0, 0, 0]) difference() { cylinder(r = CAB_R + CAB_T, h = CAB_W, $fn = 48); translate([0, 0, -1]) cylinder(r = CAB_R, h = CAB_W + 2, $fn = 48); translate([0, -CAB_R * 3, -1]) cube([CAB_R * 3, CAB_R * 6, CAB_W + 2]); translate([-CAB_R * 3, -CAB_R * 3, -1]) cube([CAB_R * 6, CAB_R * 3, CAB_W + 2]); }
    }
}
if (part == "chk_typec_L") intersection() { typec_housing_L(CHG_C_LW); union() { manaita(concat(PLUGGED_9, PLUGGED_10)); side_struct(); hatch(); floor_v3(); } }
if (part == "chk_typec_cable") intersection() { typec_cable_zone(CHG_C_B); union() { manaita(); side_struct(); top_plate(); front_plate(); pb_usb_space(); } }
if (part == "look_typec_cable") { manaita(); side_struct(); top_plate(); color("#e53e3e") typec_housing_B(CHG_C_B); color("#dd6b20") typec_cable_zone(CHG_C_B); }
// 充電ケーブルの道（ハッチの口 → PowerBoost の micro-B）。平たいリボン（幅 6・厚み 1.5）が急に折れる前提で、区間ごとの箱
//   ① ハウジングの奥ですぐ下へ折る  ② ブリッジの上を +X へ  ③ PowerBoost の前面に沿って −Y へ（リボンは縦向き）  ④ プラグの前で折り返す
module cable_route_B() {
    c = CHG_C_B; yb = IN_Y - TC_L;                                                        // 口の中心 [X, Z]・ハウジングの奥 Y 52.5
    color("#dd6b20") translate([c[0] - CAB_W / 2, yb - 4.0, BR_ZT + 0.3]) cube([CAB_W, 4.0, c[1] + CAB_T / 2 - BR_ZT - 0.3]);   // ① 下へ（Y 48.5〜52.5）
    color("#dd6b20") translate([c[0] - CAB_W / 2, yb - 4.0, BR_ZT + 0.3]) cube([BR_X1 - 0.3 - (c[0] - CAB_W / 2), 4.0, CAB_T]);   // ② +X へ（ブリッジの上・PowerBoost の部品面 78.0 の手前まで）
    color("#dd6b20") translate([BR_X1 - 0.3 - CAB_T, PB_Y0 - 1.0, BR_ZT + 0.3]) cube([CAB_T, yb - PB_Y0 + 1.0, CAB_W]);   // ③ −Y へ（縦向き・PowerBoost の部品面に沿う）
    color("#dd6b20") translate([BR_X1 - 0.3 - CAB_T, 3.0, BR_ZT + 0.3]) cube([CAB_T + 1.3, PB_Y0 - 3.0, pb_usb_space_top() - BR_ZT - 0.3]);   // ④ プラグの前で折り返す（プラグの空間の手前・X 〜79）
}
// 別の道: ハウジングの奥から**折らずにまっすぐ前へ**（Z 38〜39.5・つまみの下の部品の上・座の板の下）→ プラグの前で右へ折り返す
CAB_Z = 38.0;
module cable_route_B2() {
    c = CHG_C_B; yb = IN_Y - TC_L;
    color("#dd6b20") translate([c[0] - CAB_W / 2, 12.0, CAB_Z]) cube([CAB_W, yb - 12.0, CAB_T]);                    // ① まっすぐ前へ（Y 12〜52.5）
    color("#dd6b20") translate([c[0] - CAB_W / 2, 3.0, 32.0]) cube([IN_X - 1.3 - (c[0] - CAB_W / 2), 12.0 - 3.0 + CAB_W, 8.0]);   // ② 右へ折り返してプラグへ（Y 3〜18・Z 32〜40）
}
CAB_SEG = 0;   // 1 = ①だけ, 2 = ②だけ
module cable_route_B2s() { c = CHG_C_B; yb = IN_Y - TC_L;
    if (CAB_SEG != 2) translate([c[0] - CAB_W / 2, 12.0, CAB_Z]) cube([CAB_W, yb - 12.0, CAB_T]);
    if (CAB_SEG != 1) translate([c[0] - CAB_W / 2, 3.0, 32.0]) cube([IN_X - 1.3 - (c[0] - CAB_W / 2), 12.0 - 3.0 + CAB_W, 8.0]); }
// 水平断面（Z 36）: つまみ・PowerBoost・ReSpeaker・プラグの空間・ハッチのハウジングの位置関係
module sec_z(z) projection(cut = true) translate([0, 0, -z]) children();
if (part == "pic_z36") {
    slab("#7d8794") sec_z(36) union() { manaita(); side_struct(); front_plate(); hatch(); }
    slab("#9f7aea") sec_z(36) top_plate();
    slab("#f6ad55") sec_z(36) pb_usb_space();
    slab("#e53e3e") sec_z(36) typec_housing_B(CHG_C_B);
}
// 道 B3: ハウジングの奥で左へ折り、つまみの左の柱とトンネルの端板（切り欠き）の間（X 〜54〜56）を縦向きで前へ抜け、前の通路（Y 12〜20・Z 31〜40）を右へ走ってプラグへ
CAB_X3 = 54.2;   // 縦向きリボンの左面
module cable_route_B3() { c = CHG_C_B; yb = IN_Y - TC_L;
    color("#dd6b20") translate([CAB_X3, yb - 4.0, 33.0]) cube([c[0] + CAB_W / 2 - CAB_X3, 4.0, CAB_W]);              // ① 奥で左へ（縦向き・Y 48.5〜52.5・Z 33〜39）
    color("#dd6b20") translate([CAB_X3, 13.0, 33.0]) cube([CAB_T, yb - 13.0, CAB_W]);                                  // ② 前へ（縦向き）
    color("#dd6b20") translate([CAB_X3, 13.0, 33.0]) cube([IN_X - 1.3 - CAB_X3, CAB_T, CAB_W]);                         // ③ 前の通路を右へ（縦向き・Y 13〜14.5）
}
if (part == "chk_cable_B3") intersection() { cable_route_B3(); union() { manaita(); side_struct(); top_plate(); front_plate(); } }
if (part == "look_cable_B3") { manaita(); side_struct(); top_plate(); color("#e53e3e") typec_housing_B(CHG_C_B); cable_route_B3(); pb_usb_space(); }
if (part == "chk_cable_B2s") intersection() { cable_route_B2s(); union() { manaita(); side_struct(); top_plate(); front_plate(); } }
if (part == "chk_cable_B2") intersection() { cable_route_B2(); union() { manaita(); side_struct(); top_plate(); front_plate(); } }
if (part == "look_cable_B2") { manaita(); side_struct(); top_plate(); color("#e53e3e") typec_housing_B(CHG_C_B); cable_route_B2(); pb_usb_space(); }
if (part == "chk_cable_B") intersection() { cable_route_B(); union() { manaita(); side_struct(); top_plate(); front_plate(); } }
if (part == "look_cable_B") { manaita(); side_struct(); top_plate(); color("#e53e3e") typec_housing_B(CHG_C_B); cable_route_B(); pb_usb_space(); }

// ---- 刷る向き（外面を下に。p_* を回しただけ）。底の Z は 0 に合わせる（stl-preflight） ----
if (part == "print_floor")  translate([0, 0, FLOOR_T]) rounded() floor_v3();
if (part == "print_lwall")  translate([0, 0, WALL]) rotate([0, -90, 0]) rounded() left_wall_v3();
if (part == "print_rwall")  translate([0, 0, IN_X + WALL]) rotate([0, 90, 0]) rounded() right_wall_v3();
if (part == "print_top")    translate([0, 0, Z_TOP]) rotate([180, 0, 0]) rounded() top_plate_raw();
if (part == "print_front")  translate([0, 0, BEZ_T]) rotate([90, 0, 0]) rounded() front_plate_raw();
if (part == "print_hatch")  translate([0, 0, IN_Y + HATCH_T]) rotate([-90, 0, 0]) rounded() hatch_raw();
if (part == "print_bridge") translate([0, 0, -BR_ZB]) bridge_v3();
if (part == "print_shelf")  translate([0, 0, -(TGL_AT[1] - TGL_BODY_D / 2 - SHELF_CL - SHELF_T)]) { toggle_shelf(); toggle_shelf_flanges(); }
if (part == "chk_front_top")  intersection() { front_plate_raw(); top_plate_raw(); }
if (part == "chk_front_oled") intersection() { front_plate_raw(); oled_at(); }
if (part == "chk_front_wall") intersection() { front_plate_raw(); union() { left_wall_v3(); right_wall_v3(); floor_v3(); } }


// ============================================================
// 線（実体）。v2 の wires_v2 と同じ道具で、経路は v3 の置き方で引き直した（2026-08-23）
//   🔒 始点は口の座標（ハブは port_at、相手は各部品の関数）。数字を手で書かない（経由点は例外）
//   openscad --backend=manifold -o x.stl -D "part=\"chk_wire\"" [-D "WIRE_PICK=\"PHIN\""] hardware/case_v3.scad
// ============================================================
WIRE_PICK = "";   // "" で全部。1 本に絞るときに id
WIRE_TRIM = 4.0;  // 終端の止め代（相手の部品と交差させない）
function wire_picked(id) = (WIRE_PICK == "") ? true : is_list(WIRE_PICK) ? len([for (q = WIRE_PICK) if (q == id) 1]) > 0 : WIRE_PICK == id;
function wire_color(id) = (id == "XIAO") ? "#e6194b" : (id == "OLED") ? "#3cb44b" : (id == "AS5600") ? "#ffe119" : (id == "PWR") ? "#f58231"
    : (id == "INA") ? "#911eb4" : (id == "REED") ? "#46f0f0" : (id == "TOGGLE") ? "#f032e6" : (id == "BTN2") ? "#bcf60c" : (id == "PHIN") ? "#808000"
    : (id == "PHOUT") ? "#008080" : (id == "BAT") ? "#9a6324" : (id == "BAT2") ? "#800000" : (id == "CHG") ? "#000075" : "#888";
function port_n(id) = [for (h = HUB_HEADERS) if (h[0] == id) h[3]][0];
function port_out(id) = port_at(id) + [0, 0, HOUS_H + HOUS_R];
module harness(id, dest, mid = [], n = undef) { if (wire_picked(id)) color(wire_color(id)) bundle(wire_trim_end(concat([port_out(id)], mid, [dest]), WIRE_TRIM), is_undef(n) ? port_n(id) : n); }
module loose(id, pts, n, trim = WIRE_TRIM) { if (wire_picked(id)) color(wire_color(id)) bundle(wire_trim_end(pts, trim), n); }
// ---- 相手側の座標（v2 と同じ式。置き方は v3）----
function xiao_x()  = RSP_X + respeaker_L() - 11.0;
function xiao_zl() = RSP_Z + 7.0;
function xiao_zh() = RSP_Z + respeaker_H() - 9.0;
function oled_port() = [OLED_X0 + oled_l() * 0.58, oled_back() + 2, OLED_Z0 + oled_w() - 6];
function ina_hdr_port() = let (h = ina_hdr()) [INA_AT[0] + h[0] + h[1] / 2, INA_AT[1] + ina_size()[1] - (h[2] + h[3]), INA_AT[2] + ina_h() - ina_size()[2] - h[4] / 2];
function ina_z()   = INA_AT[2] + ina_h() - 1.6;
function ina_in()  = [INA_AT[0] + 8.5,  INA_AT[1] + ina_size()[1] - 2, ina_z()];
function ina_out() = [INA_AT[0] + 18.5, INA_AT[1] + ina_size()[1] - 2, ina_z()];
function rsp_j2_box() = let (j = respeaker_spk_j2()) [[RSP_X + respeaker_L() - j[1], RSP_BD_Y1, RSP_Z + j[2]], [RSP_X + respeaker_L() - j[0], RSP_BD_Y1 + j[4], RSP_Z + j[3]]];
function rsp_spk_port() = let (b = rsp_j2_box()) [(b[0][0] + b[1][0]) / 2, b[1][1], (b[0][2] + b[1][2]) / 2];
function pb_pad(xy) = pb2box([xy[0], xy[1], PB_TH + 2.5]);
function pb_jst_tip() = pb2box([pb_jst()[0], PB_W + pb_jst_out(), 6]);
function bat_out() = [LIPO_AT[0] + LIPO_L + 1.5, LIPO_AT[1] + LIPO_W - 4, LIPO_AT[2] + LIPO_TH / 2];   // X 53.5（端板の口の中・Type-C の受け X 55.1 の手前）
AS_PCB_HALF = 11.5;
// ⬜ AS5600 のコネクタの位置は未取得（parts.scad は「裏面のどこか」の箱）。線は板の奥左の角の**上**（座の板の下・Z 40）で止める。
//    v2 の「板の角（Z 32）」にすると、v3 ではつまみの柱（X 55.7〜・Y 40.9〜45.9）と奥の端板に挟まれて届かない
function as_dest() = [KNOB_AT[0] - AS_PCB_HALF - 1.7, KNOB_AT[1] + AS_PCB_HALF, 40.4];   // Z 40.4: 線の下が屋根（39.2）に触れない
function reed_dest() = [KNOB_AT[0], KNOB_AT[1] + 19.7, IN_Z - 6.1];                                    // v2: [KNOB_AT[0], 53, 42]（KNOB_YC 33.3・IN_Z 48.1 からの相対）
function tc_cable_in() = (CHG_ON == "left") ? [TC_L + 0.5, CHG_C_LW[0], CHG_C_LW[1]] : [CHG_C_B[0], IN_Y - TC_L - 0.5, CHG_C_B[1]];                                  // 充電ケーブルが Type-C のハウジングへ入る所
function pb_usb_tip() = let (c = pb2box([-0.5, pb_usb()[1], pb_pcb_t() + pb_usb_sz()[2] / 2])) [c[0], c[1] - PB_USB_PLUG, c[2]];   // micro-B プラグの尻
module wires_v3() {
    LZ = HUB_TOP_Z + 2.5;                  // 17.6 ハブの上を這う高さ（部品の頂点 15.1 ＋ 束の半径）
    // 🔴 2026-08-23 天井を 52.8 → 48.454 に下げたら、つまみの座の板の下面が 46.3 → 41.95 に来て REED（Z 41.0・束の半径 1.23）に 1mm3 掛かった。
    //    屋根（39.2）と座の板（41.95）の間は 2.75 で、束 2.46 は通る。車線を 40.45 に下げて中央に置く（上下 0.14 ずつ）
    LANE_Z = 40.45;
    FY = 15.0;                             // 前の通路（ReSpeaker の裏 13.4 ↔ ブリッジの前 20.5）
    BY = IN_Y - 8.5;                       // 後ろの通路を上がる Y（ハッチの内面から 8.5。初版は IN_Y - 14 = 63.5）
    HZ = IN_Z - 4.5;                       // 天井の下を這う高さ（トンネルの屋根 39.2・Type-C の胴 41.3 の上）＝ 43.95
    // XIAO 7 本 = 上段 4 ＋ 下段 3。ブリッジの前面の穴（X 66/70）を通って上段へ
    harness("XIAO", [xiao_x(), XIAO_WIRE_Y, xiao_zh()], [[port_at("XIAO")[0], port_at("XIAO")[1], LZ], [66, port_at("XIAO")[1], LZ], [66, XIAO_WIRE_Y, LZ], [66, XIAO_WIRE_Y, xiao_zh()]], 4);
    harness("XIAO", [xiao_x(), XIAO_WIRE_Y, xiao_zl()], [[port_at("XIAO")[0], port_at("XIAO")[1], LZ], [70, port_at("XIAO")[1], LZ], [70, XIAO_WIRE_Y, LZ], [70, XIAO_WIRE_Y, xiao_zl()]], 3);
    // OLED 4 本: 口（ブリッジの下）→ 前の通路へ → 上へ → ヘッダ（OLED の上辺・裏）
    harness("OLED", oled_port(), [[port_at("OLED")[0], port_at("OLED")[1], LZ], [port_at("OLED")[0], FY - 1.5, LZ], [port_at("OLED")[0], FY - 1.5, oled_port()[2]], [oled_port()[0], FY - 1.5, oled_port()[2]]]);
    // AS5600 4 本: 口 → 前の通路 → 上（ReSpeaker の頭の上）→ 天井の下を後ろへ → 右へ → 板の奥左の隅
    //   🔴 初版は X 15 で後ろへ走らせて会話ボタンの受け（X 10〜35・Y 39〜54）を貫いた（52.6mm3）。前の通路を右へ走ってから X 51（座の下の屋根の切り欠きの中）を後ろへ
    //   🔴 X 51・Z 38.5 はトンネルの屋根（X 〜50.7・Z 37.2〜39.2）と奥の端板（X 52.4〜）に挟まれて 49.9mm3。屋根の上（Z 41.3）を X 48.8（座の板 X 50.7〜 の手前）で後ろへ走り、端板の切り欠きへ斜めに下りる
    //   屋根の上（Z 41.2・座の板 X 50.7〜 の手前）の車線: REED X 39 / AS5600 X 43 / CHG X 47
    harness("AS5600", as_dest(), [[port_at("AS5600")[0], port_at("AS5600")[1], LZ], [port_at("AS5600")[0], FY, LZ], [port_at("AS5600")[0], FY, 41.2], [43, FY, 41.2], [43, as_dest()[1], 41.2]]);
    // BTN2 2 本: 口（ブリッジの下）→ 後ろの通路 → 上 → 天井の下を前へ → タクト
    //   🔴 初版は天井の下（Z 44）で前へ行って受けの板（Z 42.6〜・Y 39〜54）を貫いた（11mm3）。受けの後ろ（Y 56）で Z 40 まで下りてから入る
    harness("BTN2", [BTN_AT[0], BTN_AT[1], Z_TOP - 13.1], [[port_at("BTN2")[0], port_at("BTN2")[1], LZ], [port_at("BTN2")[0], BY, LZ], [port_at("BTN2")[0], BY, 40], [BTN_AT[0], BY, 40], [BTN_AT[0], BTN_AT[1] + 9.5, 40], [BTN_AT[0], BTN_AT[1] + 9.5, Z_TOP - 13.1]]);
    // REED 2 本: 後列の口 → 後ろの通路 → 上（Type-C の胴の上）→ 右 → 前へ → つまみの座の脇
    //   🔴 後ろの通路で上げると Type-C の胴（X 57〜69）と棚（X 〜51）の間に入らない。前の通路から AS5600 の隣（X 45.5・Z 41.2）で後ろへ
    //   🔴 トグルの胴（X 36〜44・Y 54〜・Z 39.5〜）が屋根の上を横切るので、X 34.5 を Y 52 まで走ってから右へ（座の板は Z 46.4〜 に上がったので Z 41 で下を通れる）
    harness("REED", reed_dest(), [[port_at("REED")[0], port_at("REED")[1], LZ], [34.5, port_at("REED")[1], LZ], [34.5, FY, LZ], [34.5, FY, LANE_Z], [34.5, 52, LANE_Z], [reed_dest()[0] - 4, 52, LANE_Z]]);
    // TOGGLE 2 本: 後列の口 → 後ろの通路 → 上 → トグルの端子（胴の手前）
    //   棚の底板に線のスリット（下の toggle_shelf）。口の真上から後ろの通路へ出て、スリットを上へ
    //   レール持ち: 胴の下（Z 37.5）をトンネルの後ろの壁の切り欠き（Z 31〜）越しに前へ行き、端子（Y 54・Z 46）の前で上がる
    //   🔴 後ろの通路から上げると胴の下（Z 39.5）に当たる。端子（Y 54〜60・Z 46）は屋根の真上なので、前の通路で上がって屋根の上（Z 40.5）を後ろへ走り、端子の下で上がる
    harness("TOGGLE", [TGL_AT[0], IN_Y - mts102_deep() + 2, TGL_AT[1] - 1.5], [[port_at("TOGGLE")[0], port_at("TOGGLE")[1], LZ], [TGL_AT[0], port_at("TOGGLE")[1], LZ], [TGL_AT[0], FY, LZ], [TGL_AT[0], FY, 40.5], [TGL_AT[0], IN_Y - mts102_deep() - 4, 40.5]]);
    // PWR 3 本: 後列の口 → 後ろの通路 → 上 → PowerBoost の出力パッド（部品面の外）
    PAD3 = pb_pad([(pb_out()[0][0] + pb_out()[1][0]) / 2, (pb_out()[0][1] + pb_out()[1][1]) / 2]);
    //   上がるのは X 73.5（Type-C の胴 X 〜72（口を X 66 にした場合）と後ろの柱 X 76〜 の間）。⬜ 口が X 71.5 のままだと胴（X 65.5〜77.5）がパッドの上に被さって通らない
    //   🔴 2026-08-23 柱のタブを 5mm（X 73〜78）に広げたら、この立ち上がり（X 73.5・Y 63.5）がタブの中へ
    //      25.5mm3 入った。⭐ ユーザー「衝突しているのはケーブル。ケーブルは Y に逃げる余地がある」
    //      ⇒ **構造は削らず、立ち上がりだけ後ろへ送る。**Y 68.5（タブの後端 66.37 から 0.8・ハッチの内面 72 から 2.2）
    PWR_RY = 68.5;
    harness("PWR", PAD3, [[port_at("PWR")[0], BY, LZ], [PAD3[0] - 2, BY, LZ], [PAD3[0] - 2, PWR_RY, LZ], [PAD3[0] - 2, PWR_RY, PAD3[2]], [PAD3[0] - 2, PAD3[1] + 4, PAD3[2]]], 3);
    // INA 4 本: 後列の口 → ブリッジの下を前へ（X 40・INA226 の左）→ ヘッダ（INA226 の前・−Y 向き）
    harness("INA", ina_hdr_port(), [[port_at("INA")[0], port_at("INA")[1], LZ], [40, port_at("INA")[1], LZ], [40, ina_hdr_port()[1] - 5, LZ], [ina_hdr_port()[0], ina_hdr_port()[1] - 5, ina_hdr_port()[2]]]);
    // PHIN 2 本: 右の口 → ハブの右脇を前へ → ブリッジの前で上へ（XIAO の積み重ねの上）→ 前の通路の上を左へ → J2
    //   🔴 X 77.5 で上がるとブリッジの足（X 78〜）に入った（47mm3）。口の真上 X 76 で前へ・上へ
    //   🔴 Y 22 で上がるとブリッジの中（35mm3）。X 76 では前の通路が XIAO の積み重ね（X 63〜84）で塞がるので、INA226 の前（Y 27）を X 60 まで左へ行ってから前の通路（Y 18.5・Z 19.5）へ出て左端へ。J2 には +Y から回り込む
    //   🔴 Y 27 は INA226 のヘッダの胴（Y 23.5〜30.5・Z 15.6〜21.6）の中（36mm3）。ヘッダの前 Y 21.5（XIAO の頭 20.03 の後ろ・ブリッジの下）を左へ
    harness("PHIN", rsp_spk_port() + [0, 6, 0], [[port_at("PHIN")[0], port_at("PHIN")[1], LZ], [port_at("PHIN")[0], XIAO_HEAD_Y + 1.5, LZ], [60, XIAO_HEAD_Y + 1.5, LZ], [60, FY + 3.5, rsp_spk_port()[2]], [12, FY + 3.5, rsp_spk_port()[2]], [12, rsp_spk_port()[1] + 11, rsp_spk_port()[2]], [rsp_spk_port()[0], rsp_spk_port()[1] + 11, rsp_spk_port()[2]]]);
    // PHOUT 2 本: 右の口 → 後ろの通路 → 上（X 62）→ 天井の下を左へ → 前へ（X 8・ボタンの受けの左）→ スピーカー
    //   🔴 後ろの通路（Y 63.5）を天井の下で左へ走るとトグルの棚（X 29〜51）を貫いた（14mm3）。棚の手前 Y 56 で左へ
    //   🔴 後ろの通路は使わない（同上）。PHIN と同じくブリッジの下を前へ（Y 21.5）、X 50 で前の通路を上がり、天井の下を左へ
    harness("PHOUT", [SPK_X + SPK_L / 2, SPK_Y + SPK_W / 2, IN_Z - 6], [[port_at("PHOUT")[0], port_at("PHOUT")[1], LZ], [port_at("PHOUT")[0], XIAO_HEAD_Y + 1.5, LZ], [50, XIAO_HEAD_Y + 1.5, LZ], [50, FY - 1, LZ], [50, FY - 1, IN_Z - 6.5], [SPK_X + SPK_L / 2 + 3, FY - 1, IN_Z - 6.5], [SPK_X + SPK_L / 2 + 3, SPK_Y + SPK_W / 2 + 3, IN_Z - 6.5]]);
    // 電池線: 電池の JST（トンネルの奥の端板の口）→ INA226 の INPUT → OUT → PowerBoost の JST（下向き）
    // 電池線はブリッジ（Y 20.5〜60.3・X 0〜78）を貫けないので、トンネルの奥の口から**後ろの通路へ出て**下り、ブリッジの下を前へ戻る
    //   ブリッジの穴（BAT_HOLE_X・Y 51〜56）を真下へ
    //   端板の口（Z 30.3〜36.3・全幅）の中を前へ Y 48 まで行ってから右へ出て、穴を真下へ
    //   INA226 は部品面を下にしてブリッジの下面に付く（板 Z 21.6〜23.2）。線は板の縁（Y 49.5）の後ろで Z 19.5 まで下り、板の下を前へ入る（終端は wire_trim_end で 4 戻る）
    loose("BAT", [bat_out(), [bat_out()[0], BAT_HOLE_Y, bat_out()[2]], [BAT_HOLE_X, BAT_HOLE_Y, bat_out()[2]], [BAT_HOLE_X, BAT_HOLE_Y, 19.5], [ina_in()[0], ina_in()[1] - 2, 19.5]], 2);
    //   JST は下向きに抜けるので、線は下（Z 18）から入る（Y から寄るとハウジングに 21mm3 入る）
    //   🔴 2026-08-23 ユーザー「線の開始の方向」: JST の線は板と平行＝この置き方では**真下**へ出る。縦の脚が 2.5 しか無く、止め代 4 で消えて横から入る絵になっていた。
    //      脚を Z 15.5 まで伸ばし（4.6）、止め代は 0.5 に
    loose("BAT2", [ina_out() + [0, 4, 0], [pb_jst_tip()[0], ina_out()[1] + 4, ina_out()[2]], [pb_jst_tip()[0], ina_out()[1] + 4, LZ], [pb_jst_tip()[0], pb_jst_tip()[1] + 5, LZ], [pb_jst_tip()[0], pb_jst_tip()[1], 15.5], pb_jst_tip() - [0, 0, 1.5]], 2, 0);   // 端の丸（r 1.25）が先端に触れない所で止める
    // 充電ケーブル（Type-C 変換・φ3.6）: micro-B プラグの尻 → 前の通路（XIAO の積み重ねの上）→ 左へ → 下へ → ブリッジの下を後ろへ（X 44）→ 後ろの通路で上へ → 天井の下を前へ → 右へ → Type-C のハウジング
    //   🔴 X 44 で上がるとトグルの棚（X 29〜51）を貫いた。棚と Type-C の胴の間 X 55 で上がり、座の板（Z 41.95〜）の下 Z 39.5 を前へ
    //   🔴 ブリッジの下を後ろへ回す道（約 17cm）はやめた。ハウジングから前へ出て、つまみの柱の間（X 61〜72）を座の板の下（Z 35.5）で前へ通し、前の通路でプラグへ（約 8cm）
    //   🔴 柱の間（X 61〜72）はつまみの軸（中心 φ7・Z 31〜）が居て通れない。前の通路を X 47 まで左へ → 屋根の上（Z 41.2）を後ろへ →
    //      つまみの裾（Y 〜48.4）の後ろ Y 50.5 で端板の切り欠き（Z ≥ 32.4）を横切って下り、ハウジングの前（Y 52.5）へ
    //   左の壁の口: 前の通路を X 40 まで左へ → Z 19.5 へ下りてブリッジの下を後ろへ → ハブの後ろ（Y 67）で Z 10 へ → 左へ → ハウジングの +X の端から入る
    //   🔴 2026-08-23 ユーザー「microUSB も変」: プラグの尻（Y 11.5）から前の通路（Y 16）へ**戻って**から左へ曲がる絵だった。
    //      尻は ReSpeaker の背面（Y 10.0）から 1.5 しか無いので、線は尻からそのまま真横（−X）へ曲がるしかない
    if (CHG_ON == "left") loose("CHG", [pb_usb_tip(), [pb_usb_tip()[0] - 8, pb_usb_tip()[1] + 0.3, pb_usb_tip()[2]], [40, FY + 1, pb_usb_tip()[2]], [40, FY + 1, LZ + 1.9], [40, tc_cable_in()[1], LZ + 1.9], [40, tc_cable_in()[1], tc_cable_in()[2]], tc_cable_in()], 4);
    else loose("CHG", [pb_usb_tip(), [pb_usb_tip()[0], FY + 1, pb_usb_tip()[2]], [CHG_LANE_X, FY + 1, pb_usb_tip()[2]], [CHG_LANE_X, FY + 1, 41.2], [CHG_LANE_X, CHG_CROSS_Y, 41.2],
                  [CHG_LANE_X, CHG_CROSS_Y, 39.5], [57, CHG_CROSS_Y, 39.5], [tc_cable_in()[0], CHG_CROSS_Y, tc_cable_in()[2]], tc_cable_in()], 4);
}
module wires_obstacles() { manaita([]); side_struct(); top_plate(); front_plate(); hatch(); tail_at(); }   // ハウジング（線の代わりの棒）は除く
if (part == "wires")     { wires_v3(); shells_open(); innards(); }
if (part == "chk_wire")  intersection() { wires_v3(); wires_obstacles(); }
if (part == "wires_only") wires_v3();
if (part == "chk_wire_m")  intersection() { wires_v3(); manaita([]); }
if (part == "chk_wire_s")  intersection() { wires_v3(); side_struct(); }
if (part == "chk_wire_t")  intersection() { wires_v3(); union() { top_plate(); front_plate(); hatch(); tail_at(); } }
