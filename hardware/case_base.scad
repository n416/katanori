// ============================================================
// 📦 case_base.scad — v4 の土台（2026-08-25 に case_v3.scad から分離）
//   v4 が使う **寸法・座標の変数／関数／共通モジュール** だけを残した写し。
//   v3 の機構（壁・ブリッジ・トンネル・電池の蓋・棚・v3 の線）と part= の描画は全部除去してある。
//   このファイル単体では何も描かない（top-level の形は無い）。
//   v3 の完全な形は case_v3.scad（履歴・単体でいまも開ける）。
//   🔴 **このファイルが正。** _make_base.py で 1 度だけ case_v3 から作ったが、その後は手で育てていて、
//      いま流し直すと 65 行ぶん（FRONT_DY・WIN_SUNK・FY_OUT/FY_IN・PH2.0 のソケット・HOUS_R 4.5 など）が
//      v3 の値に戻る。_make_base.py は実行できないようにしてある。
//   🔒 2026-08-25 X の式は付け替え済み（ユーザー「使ってる場所が間違ってる」）: 部品（つまみ・ハブ・OLED）の
//      X は検証済みの世界座標へ凍結し、壁（IN_X）は殻の面 85.554 ＋ 0.15 から導く。右の耳の内側の縁も凍結。
//   🔴 IN_Y / IN_Z は v3 の機構の変数から導かれた式のまま。値を変えたくなったら同様に式ごと書き直すこと。
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

$fn   = 48;     // 🔒 v2 と同じ分割数。🔴 無いと小さい円（マイクのヒゲ・口の角丸）が 5〜6 角形で出て粗雑に見える（2026-08-23 ユーザー指摘）
SWEEP = 40;     // 降ろす距離（mm）
STEP  = 1;

// ---- 肉厚 ------------------------------------------------------------
WALL    = 2.0;   // 壁（落下前提 2.0）
FLOOR_T = 2.0;   // まな板
TOP_T   = 2.5;   // 天面
BEZ_T   = 2.0;   // フロント
FRONT_DY = 0;    // フロント板の前後位置（+ でハッチ寄り）。既定 0 ＝ v1/v2/v3 は今までどおり
HATCH_T = 2.0;   // ハッチ

// ---- まな板: ハブと ReSpeaker（v2 の値。ReSpeaker の位置はマイクで決まる） ----
BOARD_Z   = 2.5;                                   // 半田面の逃げ
RSP_X     = 2.0;
LW_X = 1.694;   // 🔒 2026-08-25 左壁の内面 ＝ ReSpeaker の板の左端 2.024 − 0.33（右と同じ逃げ）。左壁に付く物と皮の左端はここから測る
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
HOUS_R = 4.5;    // ✅ 2026-08-25 ユーザー実測: ハブ基板の**部品面から一番高いところまで 17mm**（＝挿した DuPont の
                 //    線が曲がっている所）。内訳は ヘッダの樹脂 2.5 ＋ ハウジング 10.0 ＋ 曲がり **4.5**。
                 //    🔴 それまでの 3.6 は AI の既定値で、0.9 甘かった。曲がりの頭は Z 20.2 → **21.1**。
                 //    ブリッジの皿の裏（21.4）までの隙間は 1.2 → **0.3**。部品どうしは 0 のままだが線が当たる（CASE-V4-OPEN）
                 //    （case_v3.scad は 3.6 のまま。v3 は履歴なので追従させない）
// 🔒 2026-08-22 ユーザー決定: **線は 10 本全部挿してから側面構造体を載せる**（⑩ を ⑨ の前へ）
PLUGGED_9 = ["XIAO", "PHIN", "OLED", "AS5600", "BTN2", "REED", "PHOUT", "PWR", "INA", "TOGGLE"];
PLUGGED_10 = [];

// ---- 内寸（変数。手書きしない） ------------------------------------------
RIGHT_CL = -1.2;   // 🔒 2026-08-25 ユーザー「壁の移動が足りないだけ」: 殻を壁に貫通させ口の面を外面の 0.8 裏に（ハッチの充電口と同じ）。内面 84.354。経緯: 0.45（2.45 埋没）→ 0.15（すり鉢・2 段）→ -1.2（1 段）
BACK_CL  = 8.1;                                    // 🔴 2026-08-23 v2 の値に戻す（ユーザー「Y 5mm を稼ぐ」）。初版は HOUS_H + HOUS_R = 13.6（後列の口が立ち上がる分・⬜未実測）で奥行きが v2 より 5.5 増えていた
IN_X = RSP_X + respeaker_L() + xiao_usb_out() + RIGHT_CL;   // 86.0
// IN_Y・IN_Z・HUB_AT は下で（積み上げから決める）
HUB_X  = 6.002;   // 🔒 凍結 2026-08-25（旧式 (IN_X-HUB_L)/2 を IN_X=86.004 で評価した値・全配線検証済み。部品を壁から測らない）
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
PB_X1 = 84.804;   // 凍結 2026-08-25（v3 の遺産・旧式 IN_X-PB_STANDOFF を IN_X=86.004 で評価。v4 の PB は電池の上）
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
OLED_X0 = 8.002; OLED_Y1 = 8.5;   // 🔒 X は凍結 2026-08-25（旧式 (IN_X-oled_l())/2 を IN_X=86.004 で評価・全配線検証済み。壁が動いても OLED は動かない）
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
CHG_C_LW = [IN_Y - 0.8 - 3.5, 10.75];   // [67.7, 10.75] ハッチの内面から 0.8（3.5 = 胴の厚み TC_T 7 の半分。TC_T は後で定義）・🔴 2026-08-27（9 度目の机上の通し）に 10.5 → 10.75 へ 0.25 上げた: 逃げ 0.4 を見ていたのは**胴の下**（4.5）だけで、その下に伸びる**ピン列のデュポンのハウジング**（下の口の底 Z 3.99）がハブ基板の上面 4.1 に 0.11 食い込んでいた。上げて逃げ 0.14。CASE-V4-LOG.md §22   // 左の壁の口の中心 [Y, Z]（ユーザーが上面図・左側面図で指した枠 Y 61〜68・Z 4〜16 の中心）。🔒 縦置き（口は Z 9.54 × Y 3.86・ユーザー）
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
KNOB_AT = [65.704, KNOB_YC, Z_TOP];   // 🔒 X は凍結 2026-08-25（旧式 IN_X-13-dish/2+6.8 を IN_X=86.004 で評価・全配線検証済み）
// ReSpeaker の頭を押さえるリブ（v2: 前のリブ X 39.1〜45.1 と右の腕。押し代 0.3）
RSP_TOP = RSP_Z + respeaker_H(); RSP_PRESS = 0.3; RIB1_X = 39.1; RIB1_W = 6.0; RSP_ARM_X0 = 69.5; RSP_ARM_X1 = 74.2; RSP_ARM_T = 2.0;   // 🔴 2026-08-23 腕 X 74〜78.7 → 69.5〜74.2: OLED の右のビス（X 76.5・M2×6 の先が L の後ろへ 2.4 出る）を避ける
// トグルの棚の爪（天板の裏）: 棚の両側のフランジが −Y へ滑り込む L 字 2 本
SHELF_HOOK_T = 1.6; SHELF_HOOK_LIP = 1.5; SHELF_FLANGE_T = 1.2;

// ---- フロント（OLED の窓・ベベル・マイクのヒゲ。v2 §4.6 そのまま）----
WIN_CR = 2.0; WIN_CH = 1.2; WIN_R = 0.4;
// OLED の所だけ壁を薄くする彫り込み（既定 0 ＝ 彫らない。v1/v2/v3 は今までどおり）
WIN_SUNK = 0;      // 外面をこの深さだけ彫る ⇒ 窓まわりの壁の厚みは BEZ_T − WIN_SUNK
WIN_SUNK_M = 2.5;  // 彫り込みが窓の外へ出る量（⚠ 仮）
WIN_X0 = OLED_X0 + oled_glass_x() - 0.3;  WIN_X1 = WIN_X0 + oled_glass()[0] + 0.6;
WIN_Z0 = OLED_Z0 + oled_glass_y() - 0.3;  WIN_Z1 = WIN_Z0 + oled_glass()[1] + 0.6;
WSK_L = 6.0; WSK_W = 1.0; WSK_CH = 0.5; WSK_R = 0.4; WSK_ANG = 4;
// ---- 外周の角丸（v2 と同じ。12 辺と 8 隅を半径 WALL で丸める。🔒 天面とフロントの継ぎ目は角丸の真ん中）----
CHAM = WALL; EDGE_ROUND = true;
FY_OUT = -BEZ_T + FRONT_DY;   // フロント板の外面の Y（＝機体の前の面）
FY_IN  = FRONT_DY;            // フロント板の内面の Y
OUT_X = IN_X + 2 * WALL; OUT_Y = IN_Y - FY_OUT + HATCH_T; OUT_Z = IN_Z + TOP_T + FLOOR_T;

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
    if (id == "PHIN" || id == "PHOUT") {
        // 🔴 2026-08-25 ユーザー「DuPont が刺さるか？刺さらねえよ」: この 2 口は 2.54 ヘッダではなく
        //    📄 JST PH2.0 の 2P ソケット（relay_board.html PHCONN・胴 5.9×4.5・⬜ トップ型かサイド型かは現物合わせ）。
        //    それまで全口共通の DuPont（樹脂 2.5＋胴 10）を立てていた＝存在しない挿さり方だった。
        //    高さ 6.0 は JST PH の標準 ⚠。プラグと線の空間は ⬜ 型が決まってから
        color("#e8e8e8") translate([p[0] - 5.9 / 2, p[1] - 4.5 / 2, p[2]]) cube([5.9, 4.5, 6.0]);
    } else {
        color("#c93") translate([p[0] - wl[0] / 2, p[1] - wl[1] / 2, p[2]]) cube([wl[0], wl[1], HDR_PL]);                 // ヘッダの樹脂
        color("#333") translate([p[0] - wl[0] / 2, p[1] - wl[1] / 2, p[2] + HDR_PL]) cube([wl[0], wl[1], HOUS_H]);       // ハウジング
        color("#c0392b", 0.6) translate([p[0], p[1], p[2] + HDR_PL + HOUS_H]) cylinder(d = HOUS_R, h = HOUS_R, $fn = 24);   // 線が曲がり切るまでの予約
    }
}
module hub_at() { translate(HUB_AT) hub_board(false); }
module respeaker_at() { translate([RSP_X + respeaker_L(), RSP_BD_Y1, RSP_Z]) rotate([0, 0, 180]) respeaker_lite(); }
module oled_at() { translate([OLED_X0, OLED_Y1, OLED_Z0]) rotate([90, 0, 0]) oled_242(); }

// ① まな板 ＋ ② ReSpeaker ＋ ③⑤ 挿した線
MP = "";   // まな板側を1つに: floor / hub / rsp / hous（"" で全部）
SP = "";   // 側面構造体側を1つに: walls / bridge / ina / pb / lipo / boss
module hex_pocket_af(af, h) cylinder(d = af / cos(30), h = h, $fn = 6);
function bev_pts(c, k, n = 10) = [for (i = [0 : n]) let (t = i / n, p = (1 - k) * c / 2) [2 * t * (1 - t) * p + t * t * c, (1 - t) * (1 - t) * c + 2 * t * (1 - t) * p]];
module win_rrect(g = 0) { hull() for (x = [WIN_X0 + WIN_CR, WIN_X1 - WIN_CR], z = [WIN_Z0 + WIN_CR, WIN_Z1 - WIN_CR]) translate([x, z]) circle(r = WIN_CR + g, $fn = 40); }
module win_bev_slab(g, y) { translate([0, y + 0.01, 0]) rotate([90, 0, 0]) linear_extrude(0.01) win_rrect(g); }
module win_chamfer_cut() { hull() { win_bev_slab(WIN_CH, FY_OUT - 0.5); for (p = bev_pts(WIN_CH, WIN_R)) win_bev_slab(p[1], FY_OUT + p[0]); } }
// 🔴 彫り込みは**裏**（内面 Y=0 側）。外面は平らのまま = 外から見た顔は変わらない。
//    深さ WIN_SUNK だけ内面を彫るので、窓まわりの壁の厚みが BEZ_T − WIN_SUNK になる
module win_sunk_cut() if (WIN_SUNK > 0) hull() {
    win_bev_slab(WIN_SUNK_M, FY_IN - WIN_SUNK);        // 彫り込みの底（外面から BEZ_T − WIN_SUNK の所）
    win_bev_slab(WIN_SUNK_M + WIN_SUNK + 0.5, FY_IN + 0.5);   // 内面の 0.5 内側まで 45° で開く
}
module whisker_plate(l, w, y) { translate([-l / 2, y, -w / 2]) rotate([90, 0, 0]) spk_obround(l, w, 0.01); }
// 🔴 2026-08-23 v2 から写すとき 2 つ目の hull（内面まで貫くスリット）が落ちていて、外面を 0.5 彫っただけのベベルになっていた
//    （ユーザー「マイクの穴空いてない？」）。外のベベル＋貫通の 2 段で 1 本のヒゲ
module whisker_cut(l, w, ch) {
    fy = -BEZ_T / 2;   // 🔴 相対値。呼び出し側の translate（FY_OUT + BEZ_T/2）に乗るので、ここも FY_OUT 化すると二重になり外面に届かない＝穴が消える（2026-08-25 やらかした）
    hull() { whisker_plate(l + ch * 2, w + ch * 2, fy - 0.5); for (p = bev_pts(ch, WSK_R)) whisker_plate(l + p[1] * 2, w + p[1] * 2, fy + p[0]); }   // 外面のベベル
    hull() { whisker_plate(l, w, fy + ch); whisker_plate(l, w, fy + BEZ_T + 1); }                                                                   // 内面まで貫く（v2 と同じ）
}
module whiskers_cut() {   // マイクのヒゲ（位置は ReSpeaker の CAD から）
    for (ref = ["U4", "U5"]) {
        m = cad_part(ref, -1);
        bx = RSP_X + respeaker_L() - (m[2] + m[3]) / 2; bz = RSP_Z + (m[4] + m[5]) / 2; out = (bx < IN_X / 2) ? 1 : -1;
        for (i = [-1, 0, 1]) translate([bx - out * 1.0, FY_OUT + BEZ_T / 2, bz + i * 3.6]) rotate([0, out * i * WSK_ANG, 0]) whisker_cut(WSK_L, WSK_W, WSK_CH);
    }
}
module cham_box(p0, sz, k) { hull() { translate([p0[0] + k, p0[1], p0[2]]) cube([sz[0] - 2 * k, sz[1], sz[2]]); translate([p0[0], p0[1] + k, p0[2]]) cube([sz[0], sz[1] - 2 * k, sz[2]]); translate([p0[0], p0[1], p0[2] + k]) cube([sz[0], sz[1], sz[2] - 2 * k]); } }
module round_box(p0, sz, k) { hull() for (x = [p0[0] + k, p0[0] + sz[0] - k], y = [p0[1] + k, p0[1] + sz[1] - k], z = [p0[2] + k, p0[2] + sz[2] - k]) translate([x, y, z]) sphere(r = k, $fn = 48); }
module outer_envelope() { if (EDGE_ROUND) round_box([LW_X - WALL, FY_OUT, -FLOOR_T], [OUT_X - LW_X, OUT_Y, OUT_Z], CHAM); else cham_box([LW_X - WALL, FY_OUT, -FLOOR_T], [OUT_X - LW_X, OUT_Y, OUT_Z], CHAM); }   // 左端は LW_X に追従（2026-08-25）
// 部品を外周の角丸で切る。スピーカーの盛り上げ（天面の上 EMB_H）だけは許す（v2 と同じ）
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
module hex_pocket(h) cylinder(d = NUT_AF / cos(30), h = h, $fn = 6);
COL_Y0 = PB_Y0 + PB_L + PB_REAR_CL;                // 60.37 柱の前面
SCR_L = [for (yy = LEDGE_L_Y) [LEDGE_W / 2, (yy[0] + yy[1]) / 2]];                 // 左のビス 2 本 [X, Y]
SCR_R = [IN_X - LEDGE_W_R / 2, COL_Y0 + POST_W / 2];                              // 右の柱のビス
// 電池のトンネル（v2 の battery_tunnel から。BTN2 の溝は天面側の話なのでここでは無し）
function knob_seat_x0() = KNOB_AT[0] - knob_bay_x() / 2;   // 凍結した KNOB_AT から導く（壁に依存しない）
function knob_seat_x1() = knob_seat_x0() + knob_bay_x();
// 波板（v2 §2.6 そのまま）: 平らな上板 1.6 ＋ 波（部材 2.0・落下前提）＋ 下弦 2.0。山と谷はスパン方向（X）に走る
BR_T = 2.0; BR_TOP_T = 1.6; BR_WAVES = 6;
   // 波を前後の面で切りそろえる（v2 と同じ。丸が 1.0 出て XIAO ソケットの頭に 8.2mm3 当たる）
// 🔒 上下を戻した置き方（2026-08-24）: 板の法線まわりに 180°。部品面は内向きのまま、前後も入れ替わる（USB-A のヘッダが前 Y 29・micro-USB が後ろ）
   // 🔴 壁ポーズは 8 ピン列のハウジングの挿し込みが成立しない（インダクタ）。置き場所は検討中（part="pb_floor_look"）
// 充電プラグの空間（v2 の pb_usb_space をそのまま）
PB_USB_PLUG = 12.0; PB_USB_MARG = 1.5;
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
// 🔒 前の 2 本は耳と兼用（2026-08-23 ユーザー「それなら4本でもいいね」）。フロントの耳の真下に立てる柱で、
//    ビスは 天面（ザグリ）→ 耳（素通し）→ この柱のナット と 1 本で 3 枚を通す。上面に六角ポケット（ナットは上から落とし、耳が蓋）＋通し穴。
//    耳の真下は中身・線・他の板と当たり 0（12mm 下ろして 0mm³・45mm でも 1.16mm³。`_ear_col_chk.scad`）
EAR_COL_H = 9.0;
module ear_col(x0, x1 = undef) {   // 2026-08-25 幅を耳の実スパンから取る（右の耳は壁の移動で EAR_W より痩せるため）
    w = (x1 == undef ? EAR_W : x1 - x0);
    difference() {
        color("#b6c0cc") translate([x0, max(EAR_Y0, FY_IN), IN_Z - EAR_T - EAR_COL_H]) cube([w, EAR_Y1 - max(EAR_Y0, FY_IN), EAR_COL_H]);   // 前端はフロント板の内面まで（板を後ろへ寄せた分だけ詰める）
        translate([x0 + w / 2, (EAR_Y0 + EAR_Y1) / 2, IN_Z - EAR_T - NUT_T]) rotate([0, 0, 30]) hex_pocket(NUT_T + 1);   // 二面幅を X に
        translate([x0 + w / 2, (EAR_Y0 + EAR_Y1) / 2, IN_Z - EAR_T - EAR_COL_H - 1]) cylinder(d = SCR_D, h = EAR_COL_H + 2, $fn = 24);
        // 🔒 耳を +2（EAR_Y1 = 10）にしたら柱の裾が ReSpeaker の板の上端（Z 36.5）を 0.25 かすめる
        //    → 板の帯（Y 7.885〜10.335・±0.3）だけ、板の頭 +0.3 まで欠く。ナット（Z 43.45〜）と縦のビス穴（中心 Y 6）には掛からない
        translate([x0 - 1, RSP_BD_Y0 - 0.3, IN_Z - EAR_T - EAR_COL_H - 1]) cube([w + 2, respeaker_T() + 0.6, RSP_TOP + 0.3 - (IN_Z - EAR_T - EAR_COL_H) + 1]);
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
SHUT_OPEN = 0;   // 蓋: 0 = 閉, 1 = ずらし切った
// ⑥ 側面構造体（左壁・ブリッジ・右壁・INA226・PowerBoost・電池）
// 🔒 2026-08-23 天面のビスは 4 本（ユーザー）。前の 2 本は独立した柱を持たず、フロントの耳と兼用にした（`ear_col`）。
//    それまでは前の柱（Y 8.4〜15.4）と耳（Y 0〜8）が Y で 7.9 しか離れずに 2 本並び、天面が 6 本になっていた
BOSSES = [[LW_X, IN_Y - BOSS], [IN_X - BOSS, IN_Y - BOSS]];   // 後ろの 2 本だけ（左端は壁 LW_X に追従・2026-08-25）
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
   // 頭（前面の手前 Y 1.7〜3.0）。絵にだけ出す（天面の部品には入れない）
OLED_PCB_Y_FRONT = 3.0;   // OLED の基板の前面（parts.scad OLED_PCB_Y。use<> では見えない）
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
   // 天面の裏に貼る＝下へ離す
// つまみの座の板と本体の右端は PowerBoost の C6 に当たるので落とす（2026-08-23 ユーザー）。
// 🔒 落とすのは**組んだ位置**なので、explode で散らす前に引く
// トグルの棚の爪（天板の裏から下りる L 字。棚のフランジを −Y に滑り込ませる）
// 棚の外壁 X = TGL ± w/2。フランジはそこから外へ 1.5（天井の下・隙間 0.3）。爪の脚はフランジの外 0.3 に立ち、唇がフランジの下へ内側に 1.5 入る
function shelf_w() = TGL_BODY_D + 2 * (SHELF_T + SHELF_CL);
function shelf_d() = mts102_deep() + SHELF_CL;
TP = "";   // 天面側を1つに: plate / oledL / shelf / toggle / knob
// 前のフック（天板から）: 基板の前の上の角に被さる。下端は充電プラグの空間より上（v2 と同じ Z 41.8）
function pb_usb_space_top() = pb2box([-0.5, pb_usb()[1], pb_pcb_t() + pb_usb_sz()[2] / 2])[2] + pb_usb_sz()[1] / 2 + PB_USB_MARG;
HOOK_Z0 = PB_ZT - 5.0;   // 前のフックの下端。（旧）充電プラグの空間の上 42.8。micro-B を使わなくなったので板の上端から 5（2026-08-24）
// 🔒 天面とフロントの継ぎ目は角丸の真ん中（2026-08-22 ユーザー）: 前上の角の円弧の中心（Y 0・Z IN_Z）を通る 45° の面で割る。
//    天面 = Y + Z >= IN_Z、フロント = Y + Z <= IN_Z（フロントは天面の厚みの分まで上に伸び、その 45° で切れる）
// 🔴 初版は rotate(+45) で面が裏返り（Z >= Y + IN_Z）、天面がほぼ消えてフロントが上へ伸びた（ユーザー「天板もなくなっちゃいました」）。−45 が正
// 🔴 2026-08-25 蝶番はフロント板の**内面**（FY_IN）。板を後ろへ寄せたとき 0 のまま切ると、旧斜面と新しい板の間に
//    楔の欠けが開く（右上の角で 1mm³・ユーザー「天板の斜めを切り直してないからだね」）
module seam_top_half()   { translate([-WALL - 1, FY_IN, IN_Z]) rotate([-45, 0, 0]) translate([0, -100, 0]) cube([OUT_X + 2, 200, 100]); }        // (Y−FY_IN) + Z >= IN_Z の側
module seam_front_half() { translate([-WALL - 1, FY_IN, IN_Z]) rotate([-45, 0, 0]) translate([0, -100, -100]) cube([OUT_X + 2, 200, 100]); }    // (Y−FY_IN) + Z <= IN_Z の側
// 🔒 B 案（2026-08-23 ユーザー）: フロントの耳（天面とつなぐビスの受け）は OLED の両脇（X 0〜6.25 / 79.75〜86）・OLED の L の手前〜横・天井の下。
//    ビスは天面の表から M2×6（頭は天面・後ろの 2 本と同じ見え方）。🔒 2026-08-23 ナットは耳から `ear_col`（耳の真下の壁の柱）へ移し、
//    この 1 本で 天面・耳・壁 の 3 枚を締める（六角は二面幅を X に向ける。幅 6.2 に対して 4.3・Y は角 5.0 が 8 に入る）。
//    🔴 最初は OLED の裏（X 20〜30 / 56〜66）に耳を描いたが、OLED が前面の内側を X 8〜78・天井まで埋めていて 102mm3 当たった
EAR_W = OLED_X0 + oled_mount()[0][0] - OLED_L_W / 2 - 0.3;   // 6.25 耳の X 幅（L の足まで 0.3）
EAR_X = [[LW_X, EAR_W], [79.352, IN_X]]; EAR_Y0 = 2.0; EAR_Y1 = 10.0; EAR_T = 3.2;   // 🔒 2026-08-25 ユーザー「天面と底面のネジを 2mm ハッチ方向に移動」: 耳（天面の前 2 本）を 0〜8 → 2〜10   // 🔒 耳の内側の縁（左 6.652・右 79.352）は OLED の L の都合＝凍結 2026-08-25。外側の縁と幅は壁に追従
// 🔴 2026-08-27 耳の**前端**は EAR_Y0 ではなくフロント板の内面（FY_IN）。EAR_Y0 は 🔒 ビスの位置
//    （中心 Y 6.0）を決めるだけで、板と繋ぐ縁ではない。耳を 0〜8 → 2〜10 へ動かした 2026-08-25 に板から
//    2.0mm 離れ、FRONT_DY = 1.0 で 1.0mm になり、**耳 2 個が板と繋がっていない欠片**になっていた
//    （p_front の STL が中身 3 個・[CASE-V4-OPEN.md](../docs/CASE-V4-OPEN.md) T-5）。上の帯（FY_IN + 0.01 まで）と
//    0.01 重ねて繋ぐ。ビスの中心は動かさない
module front_ears() {
    y0 = min(EAR_Y0, FY_IN);
    for (ex = EAR_X) difference() {
        translate([ex[0], y0, IN_Z - EAR_T]) cube([ex[1] - ex[0], EAR_Y1 - y0, EAR_T]);
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
            color("#c9d0d8") translate([LW_X - WALL, FY_OUT, -FLOOR_T]) cube([IN_X + 2 * WALL - LW_X, BEZ_T, Z_TOP + FLOOR_T]);   // 上は天面の厚みの分まで（45° で切られる）・下は床の裏まで（下前の丸みはフロントが持つ）
            color("#c9d0d8") translate([LW_X - WALL, FY_OUT, IN_Z - EAR_T]) cube([IN_X + 2 * WALL - LW_X, BEZ_T + 0.01, EAR_T]);   // （耳はここに付く）
        }
        translate([0, FY_OUT - 1, 0]) rotate([-90, 0, 0]) linear_extrude(BEZ_T + 2) mirror([0, 1]) win_rrect(0);   // 窓（ガラス＋0.3）
        win_sunk_cut();                                                                                          // OLED の所だけ壁を薄くする彫り込み（**裏**）
        win_chamfer_cut();                                                                                       // 窓のベベル（外面）
        whiskers_cut();                                                                                          // マイクのヒゲ
    }
    } }
    color("#c9d0d8") front_ears();
    }
}
// ハッチの充電口: Type-C メスのハウジングを内面のポケットで受ける（⚠ 寸法は着荷実測待ち・仮 25×12×7）。鼻先は口から出る
TC_POCKET_T = 1.6; TC_POCKET_CL = 0.3; TC_POCKET_L = false;   // ⬜ 左の壁の受けは製品が決まってから（壁 1.6＋隙間 0.3 が基板の縁とハッチの間 8.1 に入らない）
// 🔒 2026-08-23 ユーザー: 充電口のメス側の胴を支える受けは**別刷り**（ケーブル着荷 8/27〜9/6 の後）。壁には受けを留める座だけ今入れる。
//    ビスは下から嫌（ユーザー）→ 壁の内面の座に横向き（+X から M2）。ナットは座の上からスリットに落とす（貫通＋ナット・樹脂にネジを切らない）
TC_HOLD_Y0 = 65.0; TC_HOLD_Y1 = IN_Y - 0.2; TC_HOLD_Z0 = CHG_C_LW[1] + 6.0 + 1.5;   // 座: Y 65〜71.8（ハブの後ろ左の柱 Y 〜64.4 の後ろ・ハッチの手前 0.2）・Z 18〜25（胴の上端 16.5 の上 1.5）
TC_HOLD_D = BOSS; TC_HOLD_H = 7.0;
function tc_hold_scr() = [TC_HOLD_D, (TC_HOLD_Y0 + TC_HOLD_Y1) / 2, TC_HOLD_Z0 + TC_HOLD_H / 2];   // ビスの入口（座の +X 面の中心）[X, Y, Z]
// 口（横長・殻の大きさ・⚠ ハウジング待ちの仮）。外側はベベル 1.0・角丸 1.2。印は稲妻（v2 と同じ絵・口の長辺の 7 割・外から見て口の右＝−X 側）
module port_rrect_xz(sz, r, g = 0) { hull() for (a = [-1, 1], b = [-1, 1]) translate([a * (sz[0] / 2 - r), b * (sz[1] / 2 - r)]) circle(r = r + g, $fn = 40); }
module icon_bolt(h) { s = h / 6; polygon([[0.9, 3], [-1.3, -0.4], [-0.1, -0.4], [-0.9, -3], [1.3, 0.4], [0.1, 0.4]] * s); }   // v2 の稲妻（丈 6 単位）
TC_PORT_SZ = [USBC_PORT[1], USBC_PORT[0]];   // [X 9.54, Z 3.86]
TC_ICON_H  = 0.7 * TC_PORT_SZ[0];
TC_PORT_SZ_L = USBC_PORT;                    // 左の壁は縦置き [Y 3.86, Z 9.54]
TC_ICON_Y = CHG_C_LW[0] - (TC_PORT_SZ_L[0] / 2 + PORT_BEV + ICON_GAP + TC_ICON_H * 2.6 / 6 / 2);   // 外（−X）から見て口の右（−Y）            // 6.68（口の長辺の 7 割・右の壁の印と同じ丈）
TC_ICON_X  = CHG_C_B[0] - (TC_PORT_SZ[0] / 2 + PORT_BEV + ICON_GAP + TC_ICON_H * 2.6 / 6 / 2);   // 後ろから見て口の右（−X）
ANT_SLOT_W = 2.2;
// ⑬ ハッチ（トグル付き）
   // トグルはハッチに外のナットで付く（⑬ で一緒に入る）

   // 前から後ろへ（フロントの差し込み）

// 🔒 "look" は印刷物と同じ角丸をかけた外皮で見せる（2026-08-23 ユーザー「カックカク」→ 角丸前の図を見ていた）。検査は角丸無しのまま
// ---- 見るための図: "all"（組んだ全部）/ "inside"（外皮を透かす）/ "explode"（組む向きにばらす）----
// 🔴 2026-08-23 透かし（color の alpha）は F6/--render では効かず、外皮が不透明に出て中が見えなかった（ユーザー指摘）。
//    inside / wires は外皮を「外す」で見せる。OPEN に挙げた板を描かない（既定: 既定カメラの手前にくる 天面・フロント・右の壁）
OPEN = ["top", "front", "rwall"];   // 外す板: "floor" "lwall" "rwall" "top" "front" "hatch"
EXPLODE = 40;     // explode の離し量（mm）
EXPLODE_X = 22;   // 左右の壁を X に離す量（別部品だと分かるように）
EXPLODE_S = 6;    // 1 つの板に付く小物（蓋・ロック・磁石・ビス・つまみの中身・ボタン）を離す量
function shown(n) = len([for (o = OPEN) if (o == n) 1]) == 0;
// C6（1210・高さ 2.5・局所 x 24.68〜27.64 / y 2.61〜7.55）を箱で置いて、つまみのどこが入るかを見る
// ユーザー案（2026-08-23）: Type-C メスのピッグテール（4 芯・B0BGXL6J76）を PowerBoost の USB/GND ピンに半田付けし、
//   メスのハウジングは**壁の外面の彫り込み**に埋める（開口は壁に沿う向き）。線は小穴で中へ。⇒ micro-B のプラグの空間が消える。
//   ハウジングは仮 9 × 6.5 × 16（⚠ 記載なし）。彫り込みの床が壁の内側へ出る分（6.5 − 2 ＋ 床 1.2）を内側の塊として当てる
PT_W = 9.0; PT_T = 6.5; PT_L = 16.0; PT_FLOOR = 1.2;
PT_C = [18.405, 36.0];
   // ブリッジの足と柱と L ↔ PowerBoost
   // ブリッジ ↔ まな板（床・ハブ・ReSpeaker・後列のハウジング）
   // 穴にピンが入る分だけ出るのが正
// 電池の蓋まわり
   // 電池を左へ抜く道（壁の外 5 まで）
   // 右の壁を Z で降ろすとき USB-C の殻を通るか（環だと当たる＝想定どおり）
// ⑨ は 2 段: (a) 左の壁＋ブリッジ＋INA226＋電池を Z で降ろす (b) 右の壁（ダボに載せた PowerBoost ごと）を +X から差す
// （経緯）一度「右の壁だけ横から差す」にしたが、ユーザー「両方上から降ろせないとダメ」で取り下げ。検査だけ残す
// 断面の絵: 口の Y（18.4）で切った X-Z。壁・増し壁・殻・殻の通り道
// まな板
   // ハッチを −Y へ滑り込ませる道（12mm）
// ---- 印刷部品（外周の角丸をかけた物）。刷る向きは別（print_* で出す）----
// ---- v2 の part="bridge" を復活（2026-08-23 ユーザー）----------------------
// **波板（トラス）だけ**を、実際に効いている切り欠きを通した実物で見る。トンネル・足・柱・L は外す。
// ⭐ v2 の教訓「F5 の絵で形を判断しない。体積で確かめる」。欠けた分は "bridge_eaten" で出して測る:
//    openscad --backend=manifold -o x.stl -D 'part="bridge_eaten"' hardware/case_v3.scad → python _bbox.py x.stl
   // 底の球の先を Z 0 に
   // レバーは尻尾と同じ角度（ボアの中）
   // 継ぎ目で重なっていないか
// 🔒 2026-08-23 天面のビス 4 本化（前の 2 本を耳と兼用）で、フロントは天面と一緒に降りず最後に前から差し込む。⑫ の検査は 2 つに割れた
   // ⑫前半: 天面＋OLED を Z で降ろす
   // ⑫後半: フロントを前から +Y に差し込む
// PowerBoost の局所 → 箱（side_struct の置き方と同じ）。（旧・JST 下向き）(PB_X1 - z, PB_Y0 + x, PB_ZT - y)
function pb2box(p) = [PB_X1 - p[2], PB_Y0 + p[0], PB_ZT - p[1]];
function pb_holes_yz() = [for (m = pb_mount()) let (b = pb2box([m[0], m[1], 0])) [b[1], b[2]]];
XIAO_PORT_C = [RSP_BD_Y1 + xiao_usb_yz()[0], RSP_Z + xiao_usb_yz()[1]];   // [Y, Z] = [18.4, 19.5]
CHG_C_V2 = [XIAO_PORT_C[0], 35.5];                                        // v2: XIAO の口の真上。🔴 v3 ではハウジング（奥行 25）が充電プラグの空間と PowerBoost に 557mm3 当たる
CHG_C = [71.2, 33.5];                                                     // 🔴 右の壁の後ろ寄り → ユーザー却下（2026-08-23）。（経緯のみ）

// 充電口の Type-C メスのハウジング（⚠ 仮 25 × 12 × 7・着荷実測待ち）。鼻先が壁の内面、胴は X の内側へ
TC_L = 25.0; TC_W = 12.0; TC_T = 7.0;
   // c = [Y, Z]
TC_C = CHG_C;   // -D で差し替え

echo(str("PB 穴 [Y,Z] ", pb_holes_yz(), "  PB 板 Y ", PB_Y0, "〜", PB_Y0 + PB_L, " Z ", PB_ZT - PB_W, "〜", PB_ZT,
         "  ブリッジ右端 Y ", BR_Y0, "〜", BR_Y1, " Z ", BR_ZB, "〜", BR_ZT, "  XIAO 口 ", XIAO_PORT_C, " 充電 ", CHG_C));
// 左の壁を**外**から見た絵（カメラ [90,0,270]）。画面の左が後ろ（ハッチ）、右が前（OLED 側）
CHG_C_L = [44.5, 19.2];   // 充電口の候補: 左の壁・電池の蓋の下（前寄りは J2 と AS5600 の口、後ろ寄りは BTN2 の口で塞がる）。30×14×7.6 まで 0
// ⑪ の読み 2 つ（絵）
//   A: 組んだ本体を天面を下にして伏せ、ハッチ（トグル付き）を後ろから当てる
//   B: トグルをレバーを下にして作業台に置き、ハッチの板を上から被せてナットを締める
// ReSpeaker の取付穴 2 つ（正面から見た絵）。A = 右上の角、B = 下辺・左端から 21.8
function rsp_hole_xz(h) = [RSP_X + respeaker_L() - h[0], RSP_Z + h[1]];
RSP_HOLE_A = rsp_hole_xz([2.492, 31.577]); RSP_HOLE_B = rsp_hole_xz([60.202, 2.657]);
// 断面の絵: 左 = PWR の口の X（後列。⑩ で挿す口がブリッジの後ろに見えるか）/ 右 = 電池の中央 Y（X-Z）

// ---- 充電口の Type-C メスのハウジング（仮 25 × 12 × 7・着荷実測待ち）を置いて当てる ----
//   右の壁の後ろ寄りはユーザー却下（2026-08-23「そこが例のとんでもない場所」）。候補は左の壁・前寄りの下（XIAO の口の鏡写し）
   // c = [Y, Z]・左の壁の内面から X の内側へ。縦置き（幅 12 が Z）
   // トグル（ハッチに付く）↔ 中身

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
        // 口の外に出る部分（当たり検査用）
   // 肘の先に挿すストレートのプラグ（⚠ 仮寸法）
echo(str("充電口 L字アダプタ: 口の面から外へ ", la_out_len(), "  肘の先（ソケットの面）は口の軸から内側へ ", la_reach(), "  ⇒ X ", CHG_PORT_C[0] - la_reach()));
SHOW = [];
// L 型ヘッダ（8 ピン列・GND/EN/USB）に Dupont ハウジングを挿した状態 ↔ 全部（2026-08-24）
   // 部品面の L 字（GND・EN）のハウジング
   // USB の真っ直ぐな 1 ピンに挿すハウジング（−X へ 10）
   // 裏の 3 本まとめて
   // 自分のピンは除く
   // 口の外に出る部分 ↔ 全部
// ==================================================================================
// ---- Access EC22-P-ST（B0B4SHDRZN・25cm・パネル取付 Type-C メス ← ストレート micro-B オス）を L 字アダプタの先に挿した検査（2026-08-24）
//   ⚠ 寸法は商品ページに無い。写真と一般的な同種品からの**仮**: プラグの頭（モールド）11 × 7 × 17、フランジ 28 × 12 × 2（穴ピッチ 20・M3）、胴 12 × 8 × 奥行 14
AC_HEAD = [17.0, 7.0, 11.0];     // X 長さ × Y 厚み × Z 幅（ソケットの広い辺は Z）⚠ 仮
AC_FLANGE = [28.0, 2.0, 12.0];   // X × Y（厚）× Z ⚠ 仮
AC_BODY = [12.0, 14.0, 8.0];     // X × Y（奥行）× Z ⚠ 仮
AC_SOCK_X = CHG_PORT_C[0] - la_reach();                      // L 字アダプタのソケットの面 X 68.0
AC_SOCK_Y = CHG_PORT_C[1] - la_out_len() + 6.5 / 2;           // 胴の厚みの中央 Y 18.75
   // 既存のポケット（別品用）は外して当てる
   // 既存ポケットとの干渉（別品用なので当たって当然）
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
// ---- 🔍 検討用（本体は動かさない）: PowerBoost を右の床に立てて見る（2026-08-24 ユーザー「試しに置いてみてよ」）
//   右の壁に沿って立てる（裏は壁から 1.2）。JST 上・8 ピン列が下端・部品面の L 字は上向き（ハウジングは手に持って挿してから置く前提）
//   床から 4.5 上げてある（USB のハウジングがハブ基板の上面 4.1 をかわす分）。押さえ方は未設計
PBF_Z0 = 4.5;
// 🔒 充電口はハッチ（2026-08-23 ユーザー「ハッチの左上」＝地図の左上＝箱の左の壁寄り・上。後ろから見ると右上）
   // c = [X, Z]・ハッチの内面から -Y へ
// ハッチを**後ろから**見た絵（カメラ [90,0,180]）。画面の左が箱の右（XIAO の壁）、右が箱の左（電池の蓋の壁）
// 充電ケーブル（平たいリボン・幅 ⚠6・厚み ⚠1.5）がハウジングの奥（Y = IN_Y − TC_L）からまっすぐ −Y へ出て、下（ブリッジの上 Z 29.3）へ曲がる空間
CAB_W = 6.0; CAB_T = 1.5; CAB_LEAD = 8.0; CAB_R = 8.0;   // リボンの幅 / 厚み / まっすぐ出る長さ / 曲げ半径（⚠ 見込み）
// 充電ケーブルの道（ハッチの口 → PowerBoost の micro-B）。平たいリボン（幅 6・厚み 1.5）が急に折れる前提で、区間ごとの箱
//   ① ハウジングの奥ですぐ下へ折る  ② ブリッジの上を +X へ  ③ PowerBoost の前面に沿って −Y へ（リボンは縦向き）  ④ プラグの前で折り返す
// 別の道: ハウジングの奥から**折らずにまっすぐ前へ**（Z 38〜39.5・つまみの下の部品の上・座の板の下）→ プラグの前で右へ折り返す
CAB_Z = 38.0;
CAB_SEG = 0;   // 1 = ①だけ, 2 = ②だけ
// 水平断面（Z 36）: つまみ・PowerBoost・ReSpeaker・プラグの空間・ハッチのハウジングの位置関係
// 道 B3: ハウジングの奥で左へ折り、つまみの左の柱とトンネルの端板（切り欠き）の間（X 〜54〜56）を縦向きで前へ抜け、前の通路（Y 12〜20・Z 31〜40）を右へ走ってプラグへ
CAB_X3 = 54.2;   // 縦向きリボンの左面

// ---- 刷る向き（外面を下に。p_* を回しただけ）。底の Z は 0 に合わせる（stl-preflight） ----


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
   // ハウジング（線の代わりの棒）は除く
