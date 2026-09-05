// ============================================================
// 筐体 v5（2026-09-05 着手）
//   方針（ユーザー 2026-09-05）: 配置は v4 のまま・Y と Z を広げて当たりを減らす。最初は大きく、縮めるのは CAD の中だけ。
//   前の版のファイルは読まない。読むのは parts/ の模型と hub_board_parts.scad（口の表）と、docs/CASE-V4.md §2 に言葉で書かれた配置だけ。
//
//   実行: "C:/Program Files/OpenSCAD (Nightly)/openscad.exe" --backend=manifold -o x.png -D "part=\"look\"" hardware/case_v5.scad
//
// ---- スイッチは part 一本。語はここで決めて、意味を変えない ----
//   look     … 中身（基板・電池・口・線の出だし）。皮は描かない
//   plugs    … 口だけ（ハブ 8 口＋OLED＋電流計＋PowerBoost＋XIAO＋つまみ）
//   bridge   … ブリッジ（皿＋土手＋壁への帯）・前板・留め帯 3 本と、それが受ける電池・電流計
//   explode  … bridge と同じ物を上下にばらす（前板は下へ、帯・電池・電流計は上へ）
//   tcfit    … Type-C 基板と、床（受け込み・橙）・左の壁（押さえ込み・青）・ハッチ（緑）だけ
//   skin     … 皮（板 6 枚・ハッチは蓋の彫り込みと縁込み）。蓋・ロック・床の板は単位 shutter / lock / hatchplate
//   all      … 皮＋中身＋ブリッジ一式
//   hit_<名>  … その 1 単位 ↔ 他の全部 の当たり（体積を STL で取る。0 が正）。名は oled rsp hub bat ina pb tc knob btn spk tgl bridge reed
//   pair_<a>_<b> … 2 単位の重なり（例 pair_ina_btn）
//   only_<名> … 1 つだけ（外形を数字で取る用）。名は oled rsp hub bat ina pb tc knob btn spk tgl（基板＋その口）と hubplugs oledplug inaplug pbplug xiaoplugs knobplugs（口だけ）
//   （皮・板・検査の語は皮を起こすときにここへ足す。既にある語の意味は変えない）
// ============================================================
part = "look";

use <parts/parts.scad>
use <parts/respeaker_lite.scad>
use <parts/hub_board.scad>
use <parts/typec_115426.scad>
use <parts/plug.scad>
use <parts/btn_v3.scad>    // 会話ボタン v3（🔒 2026-08-30）。原点 = ボタンの芯・z0 = 天板の外面
use <parts/knob_v5.scad>   // つまみ v5。原点 = 軸・z0 = 天板の外面
include <parts/hub_board_parts.scad>   // HUB_HEADERS（口の表・自動生成）。数字はここから読む
PLUG_EMBEDDED = true; HUB_EMBEDDED = true;
$fn = 32;

// ---- 箱の中の座標（v4 と同じ）----
//   X: 左の壁の内面が LW_X 1.694・右の壁の内面が IN_X 86.05（ReSpeaker の板の左端 2.0 から測った v4 の座標）・Y 0 = フロント板の内面・Z 0 = 床の上面
//   +X 右（XIAO の USB-C 側）・+Y 後ろ（ハッチ側）・+Z 上（天面）
// ---- 広げる量（Y は AI の初期値・当たり表の最大 3.7 の 2 倍。Z はユーザー決定）----
GROW_Y = 3.25;   // 🔒 ユーザー 2026-09-05「意味不明な拡大はおかしいでしょ」: 8 → 0 → I2C の L 字がハッチの床の板にかかり「3mm 伸ばそう」→「Y を 0.25 増やして」: 3.25（電流計の I2C ↔ 床の板の空き 0.19 → 0.44）
GROW_Z = 8.0;    // 🔒 2026-09-05 ユーザー「高さを変えずに構成できました」。電流計の直立ての口の頭 56.44 ↔ 天井 56.45（空き 0.01）は事実として残す。AI が 8.5 にしてユーザーに戻された。一時 12.5 にした案も取り下げ

// ---- 配置（docs/CASE-V4.md §2 の言葉と数字。v4 と同じ席）----
OLED_AT = [8.0, 8.5, 0];            // 背面の板の角。X 8.0・背面が Y 8.5・床に直置き（§2「OLED を前に立てる」）
RSP_X   = 2.0;                      // 左端（ジャックの筒が左の壁の口へ）
RSP_Y1  = 10.035;                   // 板の背面（XIAO 面）の Y
RSP_Z   = 2.5;                      // 板の下端。v4 BOARD_Z 2.5（半田面の逃げ）
HUB_Y0  = 11.9;                     // v4 HUB_Y0（10.035 ＋ 前の逃げ）。電池の Y はここから測る
HUB_DY  = 4.0;                      // v4 HUB_DY（板だけ後ろへ 4。口も一緒に動く）
HUB_AT  = [6.0, HUB_Y0 + HUB_DY, 2.5];   // §2「X 6.0〜80.0・前縁 Y 15.9」。Z 2.5 = v4 BOARD_Z
// ハブの口の頭: 板の下面 2.0 + 板 1.6 + 樹脂 2.5 + ハウジング 14 + 曲がり 3.0 = 23.1
HUB_PLUG_TOP = HUB_AT[2] + 1.6 + 2.5 + plug_top();
BRG_T   = 2.0;
BRG_DZ  = 0.5;                      // 🔒 ユーザー 2026-09-05「ブリッジの高さを 2mm 上げて」→「1mm 下げて」→「0.5mm 下げて」: +2 → +1 → +0.5
BRG_ZB  = HUB_PLUG_TOP + 0.775 + 0.5 + BRG_DZ;   // ブリッジの裏 25.375（口の曲がりの頭 23.6 ＋ 線の半径 0.775 ＋ 0.5 ＋ 0.5）。電池・帯・電流計はこれに付いて上がる
BAT_X0  = 14.5 - 3.0 + 3.0;         // v4 BAT_X0 = 14.5 + BAT_DX(−3)。🔒 ユーザー 2026-09-05「電池を 3mm 右に」: +3（皿・土手・帯・前板・電池の口も一緒）
BAT_YS  = 1.0;                      // v4 BAT_YS: 電池を前板の返し（1.0）の後ろへ
TRAY_Y0 = HUB_Y0 + (52.0 - lipo_size()[0]) / 2;   // 皿の前縁 12.9（v4 の BAT_Y0）。前板・帯の区間・電流計の枠はここから測る
BAT_Y0  = TRAY_Y0 + BAT_YS;                        // 電池の前縁 13.9（🔴 2026-09-05 まで BAT_YS を落としていて電池が返しに 138mm³ 食い込んでいた）
BAT_AT  = [BAT_X0, BAT_Y0, BRG_ZB + BRG_T];   // Z は皿の上（v4 BAT_Z 23.4 を口の頭 23.1 + 0.5 + 皿 2.0 に置き換え）
BAT_TOP = BAT_AT[2] + lipo_size()[2];
STRAP_T = 2.0;                      // 留め帯の天板の厚み（v4 STRAP_T）
PAIR_Y0 = TRAY_Y0 + (lipo_size()[0] - (pb_size()[1] + 0.5 + ina_size()[1])) / 2;   // v4 PAIR_Y0（電流計と PowerBoost を電池の Y の中央に並べる）
STRAP_C_POCKET = 0.0;               // 2026-09-05 一度 1.0 にしたが、ユーザー「ピンヘッダ部分は 1.2mm 掘って」で板を帯に直置きにしたので 0 に戻す
HDR_POCKET_D = 1.2 + 0.3;           // 電源ヘッダの足の裏出し 1.2 の逃げ（帯 C の天板に掘る・床 0.5 残る）
INA_DX  = -4.7; INA_DY = 3.0; INA_LIFT = 0.0; INA_THETA = 0;   // INA_LIFT: v4 は 1.0。🔒 ユーザー 2026-09-05「浮いてるでしょ」: 足の逃げは帯に掘って板は帯に直置き（0）   // v4 の値（🔒 2026-08-29 INA_DY 3.0・2026-08-26 0°）
BOARD_LIFT = 0.5;                   // v4: PowerBoost の蝶番を帯の面から 0.5 浮かせる（🔒 2026-08-25）
INA_SX  = -4.0;                     // 🔒 ユーザー 2026-09-05 …→「右に 2mm」(−1)。電池を +3 したとき枠が動いたぶんを −3 補正して −4（電流計の場所は変えない）
INA_SY  = 1.2;                      // 🔒 ユーザー 2026-09-05 …→ +2.7 →「手前に 1.5mm」: +1.2
INA_RZ  = 180;                      // 🔒 ユーザー 2026-09-05「電流計を Z 軸を中心に 180 度回転」: 板の中心まわり。0 なら I2C 前・電源 後ろ、180 なら I2C 後ろ・電源 前
PB_DY   = -4.0;                     // 🔒 ユーザー 2026-09-05「PowerBoost と電流計を 4mm 前へ」（電流計もこの値を読む）
PB_DY2  = -2.0;                     // 🔒 ユーザー 2026-09-05「PowerBoost 手前に 4mm」→「2mm くらい奥に」（天井に付けた後・PowerBoost だけ）: −4 → −2
// （PowerBoost の枠は下の at_pb()。v4 pb_frame() と同じ式）
PB_TILT = 0;                        // 🔒 ユーザー 2026-09-05「PowerBoost の傾きを無くして」。v4 の 14°（2026-08-29）は電流計を前縁の下へ潜らせるための物で、重ねるなら要らない
LW_X    = 1.694;                    // 左の壁の内面（v4: ReSpeaker の板の左端 2.024 − 0.33）
IN_X    = RSP_X + respeaker_L() + xiao_usb_out() + 0.5;   // 右の壁の内面 86.05（v4: USB-C の先 ＋ 0.5）
IN_Y    = HUB_Y0 + 52.0 + 10.1 + GROW_Y;      // v4 の式: HUB_Y0 11.9 ＋ 板 52 ＋ 後ろの逃げ 10.1（BACK_CL・2026-09-05）＝ 74.0。ハブの後縁 67.9 から 6.1（🔴 一時 HUB_AT[1]（+4）から数えて 86 にしていた）
IN_Z    = 48.454 + GROW_Z;          // v4 の内寸 48.454（§1）+ 広げ
Z_TOP   = IN_Z;                     // 天面の内面
TOP_T   = 2.5;                      // 天板の厚み。btn_v3（B3_PLATE_T）と knob_v5（DECK_T）が 2.5 で形を持っているので同じ値
KNOB_AT = [65.704 - 2.5, 33.3 + 1.6 - 1.1 + 8];   // v4: X 65.704 ＋ KNOB_DX −2.5（🔒 2026-08-26「内側へ 4」）＝ 63.2 ／ Y KNOB_YC 33.8 ＋ KNOB_DY 8（🔒 2026-08-29「ノブを後ろに」）＝ 41.8
ROW_Y   = 17.3;                     // 会話ボタンとスピーカーの列（🔒 Y は同じ）。22.3 − 0.5 − 7.5 + 3.0（BTN_ROW_DY 3.0・2026-08-29）
BTN_AT  = [22.0, ROW_Y];            // 🔒 ユーザー 2026-09-05「ボタンを右へ 2mm」→「左へ 4mm」（右・左は OLED 正面から見た向き。+X が右）: 24 → 26 → 22
SPK_AT  = [63.2, ROW_Y];            // §2「SPK4 X 63.204」
TC_AT   = [1.694, IN_Y + 0.4 - 15.0, 0.75];      // §2「X 1.694〜3.294・Y 57.4〜72.4（IN_Y 72）・Z 0.5〜20.5」。Y はハッチに追従
TGL_AT  = [40.0, IN_Y, IN_Z - 8.4];        // ハッチに付くトグルの軸（AI の仮定: 天井から 8.4）

WALL = 2.0; FLOOR_T = 2.0; FRONT_T = 2.0; HATCH_T = 2.0;   // 板の厚み（v4 と同じ）。皮の節より前に置く（shutter_v4 の include が読む）
BAT_Z = BAT_AT[2];                  // 電池の下面（shutter_v4 が読む）
include <parts/shutter_v4.scad>     // 電池の蓋（v4 の形）: 蓋・ロック・床の板・ハッチの縁・彫り込み
module sw4_carve_targets() one("tc");   // 増し肉を削る相手（v5: Type-C 基板）

// ---- 置き道具 ----
module at_oled() translate(OLED_AT) rotate([90, 0, 0]) children();                          // 模型の +Z（正面）→ −Y（前）
module at_rsp()  translate([RSP_X + respeaker_L(), RSP_Y1, RSP_Z]) rotate([0, 0, 180]) children();   // XIAO 面を後ろへ・USB-C を右へ
module at_hub()  translate(HUB_AT) children();
// 電流計の姿勢（ユーザー 2026-09-05「PowerBoost の上に電流計は乗らないのかね」「L 字にするよ」の検討）
//   "横並び"      … v4 のまま（PowerBoost の前縁の下に潜る）。電源の L が左の壁を 7.2 貫く
//   "重ね_I2C右"  … PowerBoost の上に重ね（板は平行・JST の頭 5.2 の 0.5 上）。I2C の口が右・電源の口が左。壁を 2.5 貫き天井を 1.1 越える
//   "重ね_I2C左"  … 同・I2C が左・電源が右
//   "重ね_I2C後"  … 同・I2C が後ろ・電源が前
//   "重ね_I2C前"  … 同・I2C が前（OLED 側）・電源が後ろ（ハッチ側）
//   "下_I2C前"    … 電流計が帯の上（PowerBoost の枠の位置）・PowerBoost がその上（PB_ON_INA_Z）。向きは INA_RZ（0: I2C 前・電源 後ろ／180: その逆）と INA_SX・INA_SY で送る
INA_POSE = "下_I2C前";             // 🔒 ユーザー 2026-09-05「PowerBoost と電流計の位置を入れ替えて」: 電流計が帯の上・PowerBoost がその上。向き（I2C 前・電源 後ろ）はそのまま
INA_PWR_L = true;   // 電源の口: true = L 字（🔒 ユーザー 2026-09-05）／ false = 直立て（v4・🔒 2026-08-26）。比較用
INA_ON_PB_Z = 1.6 + 5.2 + 0.5;   // PowerBoost の板の裏から電流計の板の裏まで（板 1.6 ＋ JST 5.2 ＋ 隙間 0.5）
module at_ina() {
    if (INA_POSE == "横並び") translate([INA_DX + BAT_X0 + (lipo_size()[1] - ina_size()[0]) / 2 + ina_size()[0], PAIR_Y0 + INA_DY + ina_size()[1], BAT_TOP + STRAP_T + INA_LIFT]) rotate([-INA_THETA, 0, 0]) rotate([0, 0, 180]) children();   // v4 ina_frame()
    else if (INA_POSE == "下_I2C前") translate([INA_SX, INA_SY, INA_LIFT - BOARD_LIFT - STRAP_C_POCKET]) pb_frame0() translate([pb_size()[0] / 2, pb_size()[1] / 2, 0]) rotate([0, 0, -90 + INA_RZ]) translate([-ina_size()[0] / 2, -ina_size()[1] / 2, 0]) children();   // PowerBoost の枠の位置に電流計。PowerBoost はその上
    else at_pb() translate([pb_size()[0] / 2, pb_size()[1] / 2, INA_ON_PB_Z]) rotate([0, 0, (INA_POSE == "重ね_I2C右") ? 0 : (INA_POSE == "重ね_I2C左") ? 180 : (INA_POSE == "重ね_I2C後") ? 90 : -90]) translate([-ina_size()[0] / 2, -ina_size()[1] / 2, 0]) children();   // PowerBoost の板の中央に重ねる
}
// PowerBoost の枠（v4 pb_frame() と同じ式・PB_DY と傾きを足したもの）。長辺 36 は X・Z 軸 180°: micro USB が右端・JST は前（−Y）・L 字は後ろの外向き
module pb_frame0() translate([BAT_X0 + (lipo_size()[1] - pb_size()[0]) / 2 + pb_size()[0], PAIR_Y0 + ina_size()[1] + 0.5 + pb_size()[1] + PB_DY, BAT_TOP + STRAP_T + BOARD_LIFT]) rotate([-PB_TILT, 0, 0]) rotate([0, 0, 180]) children();
PB_ON_INA_Z = 1.6 + 2.5 + 1.27 + 0.5 + 1.2;   // 電流計の板の裏から PowerBoost の板の裏まで（L 字のハウジングの頭 5.37 ＋ 隙間 0.5 ＋ PowerBoost の足の裏出し 1.2）
PB_SX = -9.0;                       // 🔒 ユーザー 2026-09-05「PowerBoost を 2mm 左へ」→「左に 4mm」(−6)。電池を +3 したとき枠が動いたぶんを −3 補正して −9（PowerBoost の場所は変えない）
// 🔒 ユーザー 2026-09-05「PowerBoost は天井につけましょう」: 板の裏を天板の内面に向けて（部品は下向き）座 PB_CEIL_SO で浮かす。
//   XY の中心は pb_frame0 の場所のまま。
PB_CEIL_SO = pb_pcb_t() + 5.2 + 0.5;   // 天板の内面 ↔ 板の裏 7.3（板 1.6 ＋ JST 5.2 ＋ 隙間 0.5）。🔒 ユーザー 2026-09-05「基板面を下にしなければならない理由はない」: 部品面を上（天井側）に
PB_FLIP = [0, 0, 0];                // 裏返さない（部品が上）。2026-09-05 まで [180,0,0]
PB_RZ = 0;                          // 🔒 ユーザー 2026-09-05「Z 軸で 180 度回転」は裏返し（PB_FLIP）と組で JST 前・L 字 後ろにする値だった。部品面を上にして裏返しをやめたので 0 で同じ向き（JST 前・L 字 後ろ）
PBC = [BAT_X0 + (lipo_size()[1] - pb_size()[0]) / 2 + pb_size()[0] / 2 + PB_SX, PAIR_Y0 + ina_size()[1] + 0.5 + pb_size()[1] / 2 + PB_DY + PB_DY2];   // 板の中心 XY（27.0, 44.2）
module at_pb() translate([PBC[0], PBC[1], Z_TOP - PB_CEIL_SO]) rotate([0, 0, PB_RZ]) rotate(PB_FLIP) rotate([0, 0, 180]) translate([-pb_size()[0] / 2, -pb_size()[1] / 2, 0]) children();
module at_bat()  translate([BAT_AT[0] + lipo_size()[1], BAT_AT[1], BAT_AT[2]]) rotate([0, 0, 90]) children();   // 模型は 50 が X。箱では 50 を Y（前後）に寝かせる（§2 X 11.5〜46.5・Y 13.9〜63.9・タブは後ろ）
module at_tc()   translate([TC_AT[0], TC_AT[1], TC_AT[2] + tc_size()[0]]) rotate([0, 90, 0]) children();   // 板の裏を左の壁の内面（X 1.694）に。局所 X（20）→ 下向き Z・局所 Y（15・口は +Y）→ 後ろ・部品面 → +X（箱の中）
module at_knob() translate([KNOB_AT[0], KNOB_AT[1], Z_TOP + TOP_T]) children();             // 天板の外面が z0
module at_btn()  translate([BTN_AT[0], BTN_AT[1], Z_TOP + TOP_T]) children();               // 天板の外面が z0（btn_v3 の約束）
module at_spk()  translate([SPK_AT[0] - spk_l() / 2, SPK_AT[1] - spk_w() / 2, Z_TOP - spk_th() - 0.2 + 0.9]) children();   // v4: 天板の座（0.9）に持ち上げ、振動板の上に 0.2
TGL_RY = 90;                        // 🔒 ユーザー 2026-09-05「トグルスイッチ Y 軸を中心に 90 度回転」: 胴の 13 が縦になる
module at_tgl()  translate(TGL_AT) rotate([0, TGL_RY, 0]) rotate([-90, 0, 0]) children();   // 軸を +Y（ハッチの外）へ

// Type-C 基板の L 字ヘッダ（v4 tcb_ra と同じ形）: 板の下辺の 7 穴（局所 y 2.54・x 2.54+2.54i）。樹脂は板の上（X 3.294〜5.8）、ピンは芯 X 5.8 で −Y（前）へ 6。使うのは 0・1・4・5（VBUS・GND・CC1・CC2）
TC_Y0 = TC_AT[1]; TC_ZT = TC_AT[2] + tc_size()[0];
TC_PINS = [0, 1, 4, 5];
TC_PIN_XC = TC_AT[0] + tc_size()[2] + 2.5;   // ピンの芯の X 5.79（板の表 3.294 ＋ 樹脂 2.5）
module tc_ra() for (i = [0 : 6]) { z = TC_ZT - (2.54 + i * 2.54);
    color("#222")    translate([TC_AT[0] + tc_size()[2], TC_Y0 + 2.54 - 1.27, z - 1.27]) cube([2.5, 2.54, 2.54]);            // 樹脂
    color("#c8ccd0") translate([TC_PIN_XC - 0.32, TC_Y0 + 2.54 - 6.0, z - 0.32]) cube([0.64, 6.0 + 0.32, 0.64]); }              // 板に沿うピン（−Y へ 6）
module tc_plugs() for (i = TC_PINS) { z = TC_ZT - (2.54 + i * 2.54);
    translate([TC_PIN_XC, TC_Y0 + 2.54 - 1.27, z]) rotate([90, 0, 0]) plug(1, [1, 0]); }   // 樹脂の前面から −Y へハウジング 14・線は +X（箱の中）へ曲がる

// ---- Type-C 基板の受け（v4 tc_seat4 の形。🔒 2026-09-05 ユーザー「物理的に固定できない」→ 床と一体にする）と左の壁の押さえ ----
//   入れ方: 壁を立てた後・ブリッジの前に、ハッチ側から板を溝へ後ろから滑り込ませ、前の当てに当てる（押さえが溝の上に被さるので真上からは入らない）。ハウジングは板が入ってから前側で挿す
//   板の裏を左の壁の内面に付けて立てる基板を、底の座（床〜0.75）・前の当て（1.2）・前の返し（板の表に 0.25 の逃げ）・後ろの控え（3.5）で受ける。浮きは壁の押さえ（板の上端 ＋0.2）が止める
TC4_XF = TC_AT[0] + tc_size()[2];              // 板の表 3.294
TC4_Y1 = TC_AT[1] + tc_size()[1]; TC4_Y0 = TC_AT[1];   // 後縁 IN_Y+0.4・前縁
TC4_ZT = TC_AT[2] + tc_size()[0]; TC4_ZB = TC_AT[2];   // 上端 20.75・下端 0.75
TC4_CL = 0.25; TC4_GX0 = TC4_XF + TC4_CL; TC4_GX1 = 4.25; TC4_BX1 = 4.70;
TC4_FY1 = TC4_Y0 - TC4_CL; TC4_FY0 = TC4_FY1 - 3.0;   // 前の当ての厚み 1.2 → 3.0（ケーブルを挿す力を受ける・2026-09-05）
TC4_SEAT_H = 6.0;   // 受けの高さ（🔒 ユーザー 2026-09-05「床からそんな長いの生やすわけ？」: 20.75 → 6.0。板の上は壁の押さえとハッチの穴が持つ）
module tc_seat() color("#c9d0d8") {
    translate([LW_X, TC4_FY0, 0]) cube([3.9 - LW_X, IN_Y - TC4_FY0, TC4_ZB]);                          // 底の座（床から板の下端まで）
    translate([LW_X, TC4_FY0, 0]) cube([TC4_GX1 - LW_X, TC4_FY1 - TC4_FY0, TC4_SEAT_H]);                // 前の当て（3.0 厚・高さ 6）
    translate([TC4_GX0, TC4_FY1, 0]) cube([TC4_GX1 - TC4_GX0, (TC4_Y1 - 14.05) - TC4_FY1, TC4_SEAT_H]);   // 前の返し（0.7 厚・高さ 6。DuPont のハウジングが X 4.52 なので厚くできない）
    translate([TC4_GX0, TC4_Y1 - 10.4, 0]) cube([5.2 - TC4_GX0, 3.5, TC4_SEAT_H]);                      // 後ろの控え（X 3.544〜5.2・高さ 6。L 字のピン X 5.47〜 が後ろから滑り込むので 5.9 にはできない）
}
TC_PRESS = [TC4_FY1 - 4.0, IN_Y, TC4_ZT + 0.2];   // 左の壁の押さえ [Y0, Y1, Z0]: 板の上端の 0.2 上・足の前面（Y 55.15）からハッチまで（足の上も埋める・ユーザー 2026-09-05）。v4 は IN_Y−13.4〜−9.8 の 3.6 だった（🔒 ユーザー 2026-09-05「もう少し長く」）
TC_PRESS_LIP = 6.0; TC_PRESS_LIP_T = 4.0;   // 押さえの前端から下へ落とす L の足の高さ 6.0・厚み 4.0（🔒 ユーザー 2026-09-05「これくらい厚くしていいでしょ・意匠的にも」）（🔒 ユーザー 2026-09-05「末端を L 字で下に少し落として抑えに。橙の抑えだけだと USB を押し込む時に斜めになりそう」）
module tc_press() {
    translate([LW_X - 0.01, TC_PRESS[0], TC_PRESS[2]]) cube([TC4_GX1 - LW_X + 0.01, TC_PRESS[1] - TC_PRESS[0], BRG_ZB - TC_PRESS[2] - 0.5]);   // レール: 壁からブリッジの裏の 0.5 下まで
    translate([LW_X - 0.01, TC4_FY1 - TC_PRESS_LIP_T, TC_PRESS[2] - TC_PRESS_LIP]) cube([TC4_GX1 - LW_X + 0.01, TC_PRESS_LIP_T, TC_PRESS_LIP + 0.01]);   // 前端の足: 板の前縁の 0.25 前（床の当てと同じ面）に下へ 6.0・厚み 4.0
}

// ---- 口（全部 plug.scad）----
// ハブ 10 口: 口の表 HUB_HEADERS = [id, label, 出る向き, 本数, x0, y0, x1, y1]（板の局所・ピン 1 本目 = (x0,y0)）
// 🔒 PHIN・PHOUT は PH2.0 のソケット（表では kind "ph"）。DuPont は挿さらない（ユーザー 2026-09-05「PH コネクタの上にピンヘッダー立てないで」）。ここでは飛ばす
module hub_plugs() at_hub() for (h = HUB_HEADERS) if (h[0] != "PHIN" && h[0] != "PHOUT") {
    n = h[3]; alongx = (h[6] - h[4]) >= (h[7] - h[5]);
    e = hub_dir(h[2]);
    translate([h[4], h[5], 1.6 + 2.5])
        if (alongx) plug(n, e);
        else rotate([0, 0, 90]) plug(n, [e[1], -e[0]]);   // ピンが Y に並ぶ口は 90° 回す。exit も局所へ回す
}
// OLED: ヘッダは板の上辺の裏（oled_hdr() の xy）・樹脂の外面は局所 z = oled_hous_z_top()+14・ハウジングは板の裏（−z 局所 ＝ 後ろ +Y）へ・線は下（局所 −y ＝ 世界 −Z）へ曲がる
OLED_EXIT = [-1, 0];   // OLED の口から出た線の向き（plug の局所）。[0,-1] は下（−Z）。🔒 ユーザー 2026-09-05「OLED のケーブルを水平に」→ 左（−X・ハブの OLED の口の側）へ
module oled_plug() at_oled() { c = oled_hdr(); translate([c[0] - 1.5 * 2.54, c[1], oled_hous_z_top() + dupont_h()]) mirror([0, 0, 1]) plug(4, OLED_EXIT); }
// 電流計: L 字ヘッダ（ina_hdr() = [x0, x長, y0, y長, 高さ]）。樹脂の外面 x = x0+高さ・ピン 1 本目 y = y0+1.27・ピンの芯 z = 板 1.6 + 2.5
//   ハウジングは −X（板の外）へ水平・線は後ろ（+Y）へ曲がる（ハブの電流計の口は後縁で +Y 向き）
INA_I2C_YAW = 0;   // I2C の L 字は振れない（5 ピンの L 字ヘッダ・🔒 ユーザー 2026-09-05「そっちは角度つけられんよ」）
INA_I2C_EXIT = [0, 1];   // I2C の口から出た線が曲がる向き（plug の局所）。[-1,0] は後ろ（ハッチへ 3.4 出た・2026-09-05）→ 横へ
module ina_plug() at_ina() { hd = ina_hdr(); translate([hd[0] + hd[4] + 1.27, hd[2] + 1.27, 1.6 + 2.5]) rotate([0, 0, INA_I2C_YAW]) translate([-1.27, 0, 0]) rotate([0, -90, 0]) rotate([0, 0, 90]) plug(4, INA_I2C_EXIT); }   // ピンの根元（樹脂の中心線）で INA_I2C_YAW だけ振る
// 電流計の電源の口: 4 本・L 字（🔒 ユーザー 2026-09-05「では電流計を L 字にしてください」。同日 直立て→L→直立て→L と往復）。ピンは端子側の縁（局所 +x）の外へ水平・樹脂の外面 x = 26+1.27・芯 z = 1.6+2.5。線は上へ曲がる
INA_PWR_EXIT = [0, 1];    // 口から出た線が曲がる向き（plug の局所 xy）。[-1,0] = 上（板の法線）・[0,1] = 右（+X 世界）・[0,-1] = 左。上だとバスタブの底に入るので右へ（行き先の電池のコネクタ対と PowerBoost の JST が右側・2026-09-05）
INA_PWR_YAW = 30;   // 🔒 ユーザー 2026-09-05「4 本とも右に 25 度」→「30 度へ」: L 字のピンを根元で板の面内に振る（+ で世界の +X 側）
module ina_pwr_plug() at_ina() for (q = ina_pwr_pins()) translate([q[0] + 1.27, q[1], 1.6 + 2.5 + 1.27]) rotate([0, 0, INA_PWR_YAW]) rotate([0, 90, 0]) plug(1, INA_PWR_EXIT);   // ピンの芯は板 1.6 ＋ 樹脂 2.5 ＋ 1.27。根元で INA_PWR_YAW だけ振る
// PowerBoost: JP2 の L 字（pb_ra_pwr() 3 本 ＋ pb_ra_chg() 2 本・ピンは板の上を +y へ水平・芯 z = 1.6 + 2.5）。ハウジングは 1 本ずつ。線は上（+Z）へ曲がる
module pb_plug() at_pb() for (i = concat(pb_ra_pwr(), pb_ra_chg())) translate([pb_jp2_x0() + i * 2.54, 0, 1.6 + 2.5]) rotate([90, 0, 0]) plug(1, [0, -1]);   // L 字は縁の外（局所 −y）へ水平。樹脂の外面 y=0。線は下（−Z・部品面が上なので天井を避ける）へ曲がる
// XIAO: 2 列 × 使う本数（下の列 3 本・上の列 4 本）。ヘッダは XIAO の上（面から 1.4+2.5）・ハウジングは XIAO 面から真上（後ろ）へ
//   線は低い車線（Z 19 前後）へ: 上の列は下へ、下の列は上へ曲がる
module xiao_plugs() at_rsp() for (r = [0, 1]) { z = [9.397, 24.627][r]; used = [[0, 1, 2], [2, 3, 4, 5]][r];
    x0 = 2.932 + used[0] * 2.54;
    translate([x0, -(1.4 + 2.5), z]) rotate([90, 0, 0]) plug(len(used), (r == 0) ? [0, 1] : [0, -1]); }   // 局所 +z → −Y（後ろ）・局所 +y → +Z
// つまみ AS5600: 板の裏から下へ 2 列（左 2 本・右 3 本）
module knob_plugs() at_knob() translate([0, 0, -knob_deep()]) rotate([0, 0, 90]) for (s = [-1, 1]) {   // 基板の裏 = 天板の外面から knob_deep() 下
    x = s * (as5600_pcb() / 2 - as5600_edge_in_s(s)); row = (s < 0) ? as5600_row_l() : as5600_row_r(); used = (s < 0) ? as5600_used_l() : as5600_used_r();
    for (i = used) translate([x, row[i], -2.5]) mirror([0, 0, 1]) plug(1, [-s, 0]); }

module plugs() { hub_plugs(); oled_plug(); ina_plug(); ina_pwr_plug(); pb_plug(); xiao_plugs(); knob_plugs(); }

// 単位（基板＋その口を 1 つに数える。ピンはハウジングの中に居るので、別々に数えると自分同士の重なりが出る）
UNITS = ["oled", "rsp", "hub", "bat", "ina", "pb", "tc", "knob", "btn", "spk", "tgl", "bridge", "front", "straps", "shutter", "lock", "hatchplate"];   // pbmount は天板と一体・tcseat は床と一体にした（2026-09-05）   // リードスイッチは 2026-09-05 に一度置いて外した（ユーザー「そんなところについてないだろ」）
module one(n) {
    if (n == "oled") { at_oled() oled_242(); oled_plug(); }
    if (n == "rsp")  { at_rsp()  respeaker_lite(); xiao_plugs(); }
    if (n == "hub")  { at_hub()  hub_board(ra = false); hub_plugs(); }
    if (n == "bat")  at_bat()  lipo_1000mah();
    if (n == "ina")  { at_ina()  ina226_module(ra = true, pwr_ra = INA_PWR_L, hous = false, pwr_yaw = INA_PWR_YAW, i2c_yaw = INA_I2C_YAW); ina_plug(); ina_pwr_plug(); }   // I2C も電源も L 字・電源の 4 本は直立て（🔒 2026-08-26）
    if (n == "pb")   { at_pb()   { powerboost_1000c(ra_dir = -1); pb_jst_plug(); } pb_plug(); }   // L 字は板の縁の外（🔒 2026-08-25）・電池の JST は挿した状態
    if (n == "tc")   { at_tc() typec_115426(pins = false); tc_ra(); tc_plugs(); }   // ピンは L 字（v4 tcb_ra）: 板に沿って前（−Y）へ。ハウジングは X 4.5〜7.1（ハブの左端 6.0 の上に少しかかる・v4 と同じ）
    if (n == "knob") { at_knob() assembly(show_deck = false); knob_plugs(); }   // 台座（knob_station_add/cut）は天板 p_top() の側   // 島・つまみ・柱・基板・E リング・磁石
    if (n == "btn")  at_btn()  { btn3_piston(); btn3_tub(); btn3_switch(); btn3_sw_screws(); btn3_v_screws(); }   // 台座（btn3_station_add/cut）は天板 p_top() の側   // バスタブ込み
    if (n == "spk")  at_spk()  speaker_112495();
    if (n == "tgl")  at_tgl()  mts102();
    if (n == "bridge") bridge();
    if (n == "front")  brg_front();
    if (n == "straps") straps();
    if (n == "shutter") { color("#b8c4d8") battery_shutter4(); sw4_magnets_shutter(); }   // 蓋（磁石 2 個込み）
    if (n == "lock") { color("#b8c4d8") battery_lock4(); sw4_lock_screw(); sw4_lock_nut(); }   // ロック（M2・ナット込み）
    if (n == "hatchplate") { color("#27ae60") sw4_floor_plate(); sw4_magnets_wall(); }   // 床の板（ハッチの裏・別部品・磁石 2 個込み）
    if (n == "pbmount") pb_mount();
    if (n == "hubplugs")  hub_plugs();
    if (n == "oledplug")  oled_plug();
    if (n == "inaplug")   { ina_plug(); ina_pwr_plug(); }
    if (n == "pbplug")    pb_plug();
    if (n == "xiaoplugs") xiao_plugs();
    if (n == "knobplugs") knob_plugs();
}
module others(n) for (m = UNITS) if (m != n) one(m);
function tail(s, k) = len(s) > k ? _join([for (i = [k : len(s) - 1]) s[i]]) : "";
function _join(v, i = 0) = i >= len(v) ? "" : str(v[i], _join(v, i + 1));
function starts(s, pre) = len(s) >= len(pre) && _join([for (i = [0 : len(pre) - 1]) s[i]]) == pre;


// ============================================================
// ブリッジ（🔒 ユーザー 2026-09-05「先にブリッジを設計しましょう」→ 3 段案は却下・PowerBoost は天井へ）
//   皿（電池）＋土手＋壁への帯。電流計は留め帯 B の支柱に載る（v4 と同じ）。
//   数字は全部いまの中身の外形から（電池 X 11.5〜46.5・Y 12.9〜62.9・Z 26.1〜32.1／電流計の穴 (14.2,43.1)(29.8,43.1)／PowerBoost の穴 (42.5,53.1)(42.5,35.3)(11.1,50.5)(11.1,37.3)）
// ============================================================
BR_X0 = BAT_X0 - 2.5;  BR_X1 = BAT_X0 + lipo_size()[1] + 2.5;   // 皿の X 9.0〜49.0（v4 と同じ・土手の外面まで）
BR_Y0 = TRAY_Y0;       BR_Y1 = TRAY_Y0 + lipo_size()[0] + 2.0;   // 皿の Y 12.9〜64.9（v4 と同じ。後ろは開ける）
ARM_Y = [50.5, 62.9];                 // 壁への帯の Y（v4 と同じ・幅 12.4・左右とも）。
// 帯の両端を壁の棚へ M2×6 で留める（v4 と同じ流儀: ブリッジ側は通し φ2.3＋座ぐり φ4.4×1.6、ナットは壁の棚の中＝皮を描くときに彫る）。2026-09-05
BRG_ANCH = [[LW_X + 3.5, (ARM_Y[0] + ARM_Y[1]) / 2], [IN_X - 3.5, (ARM_Y[0] + ARM_Y[1]) / 2]];   // ねじの芯 [X, Y]: 壁の内面から 3.5
BRG_ANCH_D = 2.3; BRG_ANCH_CB = 4.4; BRG_ANCH_CBH = 1.6;   // （🔒 ユーザー 2026-09-05「奥のクソ細い橋は却下」。帯はつまみの口（X 58.7〜68.8・Y 〜49.8・Z 19〜）の後ろを通る）
// ---- 前板（v4 の brg_front と同じ形・🔒 ユーザー 2026-09-05「v4 と同じ支え板を設置」）----
//   首 23 × 2.0 が床の溝に立ち、皿を貫く抜きを通って、皿の裏の掘り込み（1.0）にフランジ（1.0 厚・奥行き 6）が沈む。上は返し（1.0 厚・電池の高さ 6）。ねじ無し（前へ倒れるとフランジが掘り込みの天井に、後ろへ倒れると首が抜きの奥に当たる）
LEG_X0 = BAT_X0 + 6;                  // 17.5（v4: 意匠の引っ込み 6）
LEG4W  = lipo_size()[1] - 2 * 6;      // 23
BRGF_T = 1.0; BRGF_SINK = 1.0; BRGF_D = 6.0; BRGF_CL = 0.2;
FP_Y0  = TRAY_Y0;                     // 前板の前面 12.9（皿の前縁と面一）
FP_ZT  = BRG_ZB + BRG_T;              // 皿の天面 26.875
// 🔒 ユーザー 2026-09-05「支え板、平ねじでブリッジ上から留められるように」: 皿の上から M2 平ねじ 2 本 → 皿 2.0 → フランジ 1.0 → フランジの下のナットの箱（床 1.0＋ナット 1.6・横差し）。M2×6
FP_SCR_X = [LEG_X0 + 4.5];                  // ねじの芯 X 22.0・1 本（🔒 ユーザー 2026-09-05「1 個でいいよ」。右は XIAO の口の上で置けない）
FP_SCR_Y = FP_Y0 + BRG_T + 3.1;            // 18.0（フランジ Y 14.3〜20.9 の中）
FP_SCR_D = 2.3; FP_CSK_D = 4.0; FP_CSK_H = 0.85;   // 通し・皿もみ（M2 平ねじの頭 φ3.8）
FP_NUT_AF = 4.0; FP_NUT_T = 1.6; FP_NUT_FLOOR = 1.0;
FP_BOX = [LEG_X0 + 1.5, LEG_X0 + 7.5, FP_SCR_Y - 3.0, FP_Y0 + BRG_T + BRGF_D];   // ナットの箱 X 19.0〜25.0・Y 15.0〜20.9（フランジの中に収める）
FP_NUT_ROOF = 0.4;                                                       // ナットの溝の天井とフランジの裏の間に残す肉（フランジ 1.0 と合わせて 1.4）
FP_BOX_Z0 = BRG_ZB - FP_NUT_ROOF - FP_NUT_T - FP_NUT_FLOOR;                // 箱の底 21.875（ハブの口の頭 24.4 は X 26.5〜 にしか無い）
module bridge() color("#c9a86a") difference() {
    union() {
        translate([BR_X0, BR_Y0, BRG_ZB]) cube([BR_X1 - BR_X0, BR_Y1 - BR_Y0, BRG_T]);                       // 皿
        translate([LW_X, ARM_Y[0], BRG_ZB]) cube([IN_X - LW_X, ARM_Y[1] - ARM_Y[0], BRG_T]);                    // 壁〜壁の帯（皿と一体・v4 と同じ Y）
        banks();                                                                                                 // 土手（留め帯の足の区間だけ途切れる）
    }
    tab_slots();   // 留め帯のツバの溝
    for (a = BRG_ANCH) translate([a[0], a[1], 0]) { translate([0, 0, BRG_ZB - 1]) cylinder(d = BRG_ANCH_D, h = BRG_T + 2, $fn = 24); translate([0, 0, BRG_ZB + BRG_T - BRG_ANCH_CBH]) cylinder(d = BRG_ANCH_CB, h = BRG_ANCH_CBH + 0.01, $fn = 32); }   // 壁への留め（通し＋座ぐり）
    for (x = FP_SCR_X) translate([x, FP_SCR_Y, 0]) { translate([0, 0, BRG_ZB - 1]) cylinder(d = FP_SCR_D, h = BRG_T + 2, $fn = 24); translate([0, 0, BRG_ZB + BRG_T - FP_CSK_H]) cylinder(d1 = FP_SCR_D, d2 = FP_CSK_D, h = FP_CSK_H + 0.01, $fn = 32); }   // 前板の平ねじ（通し＋皿もみ）
    translate([LEG_X0 - BRGF_CL, FP_Y0 - 1.0, BRG_ZB - 1]) cube([LEG4W + 2 * BRGF_CL, BRG_T + 1.0 + BRGF_CL, BRG_T + 2]);   // 首を通す抜き（皿を貫通・Y 11.9〜15.1）
    translate([LEG_X0 - BRGF_CL, FP_Y0 + BRG_T + BRGF_CL, BRG_ZB - 1]) cube([LEG4W + 2 * BRGF_CL, BRGF_D, 1 + BRGF_SINK + 0.1]);   // フランジの掘り込み（皿の裏・深さ 1.0）
}

// ---- 留め帯 3 本（🔒 v4 2026-08-25〜09-03 の形をそのまま・ユーザー 2026-09-05「3 本のバッテリーストラップを復活させて」）----
//   ⊓: 足（厚み 2）が皿の縁の上に立ち、天板（厚み 2）が電池の上。足の前後のツバ（長さ 2・上面 45°）を、皿の土手を X に貫く溝へ横差し。
//   差した後に電池を後ろから入れると電池が楔になって戻らない（ねじ無し）。土手は厚み 2・高さ 4・足の区間だけ途切れる。
STRAP_GAP = 51.7 - (33.2 + 13.3);   // 帯の間隔 5.2（B〜C）。🔒 ユーザー 2026-09-05「1・2・3 番目の間隔を同じに」
STRAP_DY = -4.0;   // 🔒 ユーザー 2026-09-05「3 つの帯を 4mm 手前へ」
STRAP_BANDS = [[58.6 - 13.3 - STRAP_GAP - 6.9 - STRAP_GAP - 6.9 + STRAP_DY, 6.9], [58.6 - 13.3 - STRAP_GAP - 6.9 + STRAP_DY, 6.9], [58.6 - 13.3 + STRAP_DY, 13.3]];   // A / B / C。🔒 ユーザー 2026-09-05「3 番目と 1 番目を入れ替えて」: A 6.9・B 6.9・C 13.3。C の後端 58.6 を動かさず間隔 5.2 → A 21.1〜28.0・B 33.2〜40.1・C 45.3〜58.6、さらに STRAP_DY −4 で A 17.1〜24.0・B 29.2〜36.1・C 41.3〜54.6
BANK_H = 4.0;
TAB_L = 1.5; TAB_H = 1.5; TAB_CL = 0.2; TAB_MIN = 3.5;   // 掛かり 2.0 → 1.5・45°（🔒 ユーザー 2026-09-05「細すぎ」: 土手の根元 = 帯の間隔 5.2 − 溝 1.7×2 = 1.8。v4 は 2.0 で根元 0.8）
TAB_TIP = 0.4;   // ツバの先端の平らな高さ。🔒 ユーザー 2026-09-05「足の三角が鋭角すぎて入れるのに苦労した」: 刃（0）→ 0.4 の面で止め、そこから 45°
TAB_Z0 = BRG_ZB + BRG_T;                // ツバの下面 = 足の裏 = 皿の上
function foot_x(right) = right ? BAT_X0 + lipo_size()[1] + 0.5 : BAT_X0 - 2.5;   // 足の X（電池との隙間 0.5）: 9.0 / 47.0
function rail_segs(right) = [for (i = [0 : len(STRAP_BANDS)])   // 左右とも皿の前縁から（v4 は左を最初の帯の後ろから始めていた: J2 の欠きのため。v5 は皿が J2 の頭 23.5 より上なので要らない・ユーザー 2026-09-05）
    let (a = (i == 0) ? TRAY_Y0 : STRAP_BANDS[i - 1][0] + STRAP_BANDS[i - 1][1],
         b = (i == len(STRAP_BANDS)) ? TRAY_Y0 + lipo_size()[0] : STRAP_BANDS[i][0]) if (b > a) [a, b]];
function tab_front(y0, right) = len([for (s = rail_segs(right)) if (abs(s[1] - y0) < 0.01 && s[1] - s[0] >= TAB_MIN) 1]) > 0;
function tab_rear(y1, right)  = len([for (s = rail_segs(right)) if (abs(s[0] - y1) < 0.01 && s[1] - s[0] >= TAB_MIN) 1]) > 0;
module banks() for (right = [false, true]) for (sg = rail_segs(right))
    translate([foot_x(right), sg[0], TAB_Z0]) cube([STRAP_T, sg[1] - sg[0], BANK_H]);
module tab_solid(y0, w, right, rear) hull() {
    translate([foot_x(right), rear ? y0 + w - 0.6 : y0 - TAB_L, TAB_Z0]) cube([STRAP_T, TAB_L + 0.6, TAB_TIP]);   // 先端まで高さ 0.6 の面（刃にしない）
    translate([foot_x(right), rear ? y0 + w - 0.6 : y0, TAB_Z0 + TAB_H - 0.01]) cube([STRAP_T, 0.6, 0.01]);       // 足の側は全高 → 上面が 45°
}
module tab_slot(y0, w, right, rear) hull() {
    x = foot_x(right) - 1;
    yl = rear ? y0 + w - 0.1 : y0 - TAB_L - TAB_CL;
    yu = rear ? y0 + w - 0.1 : y0 - TAB_CL;
    translate([x, yl, TAB_Z0]) cube([STRAP_T + 2, TAB_L + TAB_CL + 0.1, TAB_TIP + TAB_CL]);                        // 奥まで高さ 0.8 の壁
    translate([x, yu, TAB_Z0 + TAB_H + TAB_CL - 0.01]) cube([STRAP_T + 2, TAB_CL + 0.1, 0.01]);
}
module tab_slots() for (b = STRAP_BANDS) for (right = [false, true]) {
    if (tab_front(b[0], right))         tab_slot(b[0], b[1], right, false);
    if (tab_rear(b[0] + b[1], right))   tab_slot(b[0], b[1], right, true);
}
module strap_u(y0, w) {
    for (right = [false, true]) translate([foot_x(right), y0, TAB_Z0]) cube([STRAP_T, w, lipo_size()[2] + STRAP_T]);   // 足
    translate([foot_x(false), y0, BAT_TOP]) cube([foot_x(true) + STRAP_T - foot_x(false), w, STRAP_T]);              // 天板
    for (right = [false, true]) { if (tab_front(y0, right)) tab_solid(y0, w, right, false); if (tab_rear(y0 + w, right)) tab_solid(y0, w, right, true); }
}
// 電流計の支柱（B の天板の上・v4 2026-09-03「支柱は帯と一体」）: 胴 φ5.8・高さ INA_LIFT、軸 φ2.0 が穴 φ3.0 を通る。E リング（呼び 1.5）の溝はまだ彫っていない
// 電流計の穴の世界座標: at_ina() の "下_I2C前" と同じ変換を式で（送ると支柱が付いてくる）
PBF_O = [BAT_X0 + (lipo_size()[1] - pb_size()[0]) / 2 + pb_size()[0], PAIR_Y0 + ina_size()[1] + 0.5 + pb_size()[1] + PB_DY];   // pb_frame0 の原点 XY
function ina_hole_w(h) = let (v = [h[0] - ina_size()[0] / 2, h[1] - ina_size()[1] / 2],
                              r = (INA_RZ == 180) ? [-v[1], v[0]] : [v[1], -v[0]],      // rotate Z(−90+INA_RZ)
                              q = [r[0] + pb_size()[0] / 2, r[1] + pb_size()[1] / 2])
                         [INA_SX + PBF_O[0] - q[0], INA_SY + PBF_O[1] - q[1]];          // pb_frame0 の Z 軸 180° と送り
INA_HOLES_W = [for (h = ina_holes()) ina_hole_w(h)];
// E リング（呼び 1.5）の軸: φ2.0・板 1.6 の上に遊び 0.1 → 溝（径 1.5・幅 0.5）→ 掴みしろ 0.6。🔒 ユーザー 2026-09-05「電流計に E リング。PowerBoost もダボ＋E リング」。溝の数字は規格値（AI が置いた）
E15_D = 2.0; E15_GRV_D = 1.5; E15_GRV_W = 0.5; E15_PLAY = 0.1; E15_GRIP = 0.6;
function e15_len(t) = t + E15_PLAY + E15_GRV_W + E15_GRIP;   // 板厚 t の板を留める軸の長さ（板の面から）
module e15_shaft(t) difference() {
    cylinder(d = E15_D, h = e15_len(t), $fn = 24);
    translate([0, 0, t + E15_PLAY]) difference() { cylinder(d = E15_D + 1, h = E15_GRV_W, $fn = 24); translate([0, 0, -1]) cylinder(d = E15_GRV_D, h = E15_GRV_W + 2, $fn = 24); }
}
// 電流計の板の足跡（世界・軸に平行）: 4 隅を ina_hole_w() と同じ変換で写す
INA_FOOT = let (c = [for (q = [[0, 0], [ina_size()[0], 0], [ina_size()[0], ina_size()[1]], [0, ina_size()[1]]]) ina_hole_w(q)])
           [min([for (q = c) q[0]]), max([for (q = c) q[0]]), min([for (q = c) q[1]]), max([for (q = c) q[1]])];   // [x0, x1, y0, y1]
// 電源ヘッダの足の列（板の局所 x 26・y 3.6〜16.4）の世界の足跡
HDR_FOOT = let (c = [for (q = [[26.0 - 1.27, 3.6 - 1.27], [26.0 + 1.27, 3.6 - 1.27], [26.0 + 1.27, 16.4 + 1.27], [26.0 - 1.27, 16.4 + 1.27]]) ina_hole_w(q)])
           [min([for (q = c) q[0]]), max([for (q = c) q[0]]), min([for (q = c) q[1]]), max([for (q = c) q[1]])];
module straps() color("#ed8936") difference() {
    union() {
        for (b = STRAP_BANDS) strap_u(b[0], b[1]);
        for (h = INA_HOLES_W) translate([h[0], h[1], BAT_TOP + STRAP_T - STRAP_C_POCKET]) { if (INA_LIFT > 0) cylinder(d = 5.8, h = INA_LIFT); translate([0, 0, INA_LIFT]) e15_shaft(ina_size()[2]); }   // 電流計の支柱: 浮き 0 なら E リングの軸だけ
    }
    if (STRAP_C_POCKET > 0) translate([INA_FOOT[0] - 0.5, INA_FOOT[2] - 0.5, BAT_TOP + STRAP_T - STRAP_C_POCKET]) cube([INA_FOOT[1] - INA_FOOT[0] + 1.0, INA_FOOT[3] - INA_FOOT[2] + 1.0, STRAP_C_POCKET + 1]);
    translate([HDR_FOOT[0] - 1.0, HDR_FOOT[2] - 1.0, BAT_TOP + STRAP_T - HDR_POCKET_D]) cube([HDR_FOOT[1] - HDR_FOOT[0] + 2.0, HDR_FOOT[3] - HDR_FOOT[2] + 2.0, HDR_POCKET_D + 1]);   // 電源ヘッダの足の列の逃げ（🔒 ユーザー 2026-09-05「ピンヘッダ部分は 1.2mm 掘って」）
}
// PowerBoost のダボ（天板の裏から部品面まで下りる胴 φ5.8・高さ 5.7、軸 φ2.0 が板の穴 φ2.4 を下へ貫いて E リング）。天板を描くとき天板に union する
PB_DOWEL_D = 4.0;   // ダボの胴の径。5.8 だと足元が板の上の小さな部品（0.6〜0.7）に 2.8mm³ 乗る。4.0 で 0（2026-09-05）
module pb_mount() color("#c9d0d8") at_pb() for (h = pb_mount()) translate([h[0], h[1], pb_pcb_t()]) { cylinder(d = PB_DOWEL_D, h = PB_CEIL_SO - pb_pcb_t() + 0.01); mirror([0, 0, 1]) e15_shaft(pb_pcb_t()); }   // 胴は部品面から天井まで 5.7・軸は板を下へ貫き E リングは板の裏（下から差せる）

// 前板そのもの（別部品・v4 brg_front）。断面 Y-Z を X に押し出す
module brg_front() color("#c9d0d8") difference() {
    union() {
        translate([LEG_X0, FP_Y0, 0]) cube([LEG4W, BRG_T, FP_ZT]);                                            // 脚＋首（Y 12.9〜14.9・床から皿の天面まで）
        translate([LEG_X0, FP_Y0, FP_ZT - 0.01]) cube([LEG4W, 1.0, lipo_size()[2] + 0.01]);                 // 返し（Y 12.9〜13.9・高さ 6）
        translate([LEG_X0, FP_Y0 + BRG_T - 0.6, BRG_ZB]) cube([LEG4W, BRGF_D + 0.6, BRGF_T]);                // フランジ（皿の裏の掘り込みへ・厚み 1.0・奥行き 6・首へ 0.6 重ねる）
        translate([FP_BOX[0], FP_BOX[2], FP_BOX_Z0]) cube([FP_BOX[1] - FP_BOX[0], FP_BOX[3] - FP_BOX[2], BRG_ZB - FP_BOX_Z0 + 0.5]);   // ナットの箱（フランジの下・0.5 食い込ませる）
    }
    for (x = FP_SCR_X) translate([x, FP_SCR_Y, 0]) {
        translate([0, 0, FP_BOX_Z0 - 1]) cylinder(d = FP_SCR_D, h = BRG_ZB + BRGF_T - FP_BOX_Z0 + 2, $fn = 24);   // 通し（箱の底からフランジの上まで）
        hull() for (dx = [0, -(x - FP_BOX[0]) - 0.5]) translate([dx, 0, FP_BOX_Z0 + FP_NUT_FLOOR]) rotate([0, 0, 30])
            cylinder(d = (FP_NUT_AF + 0.1) / cos(30), h = FP_NUT_T, $fn = 6);                                 // ナットの溝（−X から横差し・二面幅 4.0・天井はフランジの裏の 0.4 下）
    }
}

// ============================================================
// 皮（v4 と同じ板 6 枚。壁 2.0・天板 2.5。口は v4 の一覧のとおり・開口の縁はベベル 1.0）
// ============================================================
PORT_BEV = 1.0;    // 口の縁のベベル（v4 PORT_BEV）
OUT_X0 = LW_X - WALL; OUT_X1 = IN_X + WALL; OUT_Y0 = -FRONT_T; OUT_Y1 = IN_Y + HATCH_T;
// 角穴＋外面のベベル。c = 穴の中心（板の厚みの中央）・w, h = 板の面内の [横, 縦]・t = 板厚・axis = 板の法線 "x"|"y"・外面は法線の +側
module port_cut(c, w, h, t, axis) translate(c) rotate(axis == "x" ? [0, 90, 0] : [-90, 0, 0]) {
    translate([-w / 2, -h / 2, -t / 2 - 1]) cube([w, h, t + 2]);
    hull() { translate([-w / 2, -h / 2, t / 2 - PORT_BEV]) cube([w, h, 0.01]); translate([-(w / 2 + PORT_BEV), -(h / 2 + PORT_BEV), t / 2]) cube([w + 2 * PORT_BEV, h + 2 * PORT_BEV, 1.0]); }
}
// ---- 左の壁: ジャックの丸い口・ReSpeaker の USB-C の盲ポケット ----
JACK_C = [LW_X - WALL / 2, RSP_Y1 + 2.485, RSP_Z + 6.502];   // 筒の軸（respeaker_lite: 面から 2.485・下から 6.502）
JACK_D = 7.0;                                                 // 口の径（プラグの胴 φ5.5〜6 ＋ 逃げ・AI の値）
USB1_POCKET = [LW_X - 0.9, RSP_Y1 - 0.2, RSP_Z + 23.0, 0.9 + 0.01, 3.9, 9.7];   // [x0, y0, z0, dx, dy, dz] 壁の内面に 0.9 の盲ポケット（USB1 の殻が 0.6 入る）
JACK_COVER_POCKET = [LW_X - 0.7, RSP_Y1 + 3.14 - 0.3, RSP_Z + 3.65 - 0.3, 0.7 + 0.01, 7.52 - 3.14 + 0.6, 8.9 - 3.65 + 0.6];   // ジャックの金属カバー（面から 3.14〜7.52・下から 3.65〜8.9・板の端から 0.68 出る）の盲ポケット 0.7
module p_lwall() difference() {
    union() { translate([OUT_X0, OUT_Y0, 0]) cube([WALL, OUT_Y1 - OUT_Y0, Z_TOP]); tc_press(); fasten_lwall(); }   // 押さえ・柱・棚は壁と一体
    translate(JACK_C) rotate([0, 90, 0]) { cylinder(d = JACK_D, h = WALL + 2, center = true, $fn = 48); translate([0, 0, -WALL / 2 - 0.01]) cylinder(d1 = JACK_D + 2 * PORT_BEV, d2 = JACK_D, h = PORT_BEV, $fn = 48); }   // 口＋外のベベル（外面は −X）
    translate([USB1_POCKET[0], USB1_POCKET[1], USB1_POCKET[2]]) cube([USB1_POCKET[3], USB1_POCKET[4], USB1_POCKET[5]]);
    translate([JACK_COVER_POCKET[0], JACK_COVER_POCKET[1], JACK_COVER_POCKET[2]]) cube([JACK_COVER_POCKET[3], JACK_COVER_POCKET[4], JACK_COVER_POCKET[5]]);
}
// ---- 右の壁: XIAO の USB-C の口（ケーブルのプラグの胴 6.5 × 12.5 が通る）----
XUSB_C = [IN_X + WALL / 2, RSP_Y1 + xiao_usb_yz()[0], RSP_Z + xiao_usb_yz()[1]];
XUSB_SZ = [7.5, 13.5];   // [Y, Z]（AI の値: 胴 6.5 × 12.5 ＋ 0.5 ずつ）
module p_rwall() difference() {
    union() { translate([IN_X, OUT_Y0, 0]) cube([WALL, OUT_Y1 - OUT_Y0, Z_TOP]); fasten_rwall(); }
    port_cut(XUSB_C, XUSB_SZ[0], XUSB_SZ[1], WALL, "x");
}
// ---- フロント: OLED の窓（黒枠 61 × 38.5 ＋ 横 1.0・縦 0.15・下辺の張り出し）・マイクのヒゲ ----
WIN_CL_X = 1.0; WIN_CL_Z = 0.15;   // 🔒 2026-09-03 の値
WSK_L = 6.0; WSK_W = 1.0; WSK_ANG = 4; WSK_CH = 0.5;   // v4: 6.0 × 1.0・3 本・3.6 間隔・±4°
module whisker(c, ang) translate(c) rotate([0, ang, 0]) {
    translate([-WSK_L / 2, -FRONT_T - 1, -WSK_W / 2]) cube([WSK_L, FRONT_T + 2, WSK_W]);
    hull() { translate([-WSK_L / 2, -FRONT_T + WSK_CH, -WSK_W / 2]) cube([WSK_L, 0.01, WSK_W]); translate([-WSK_L / 2 - WSK_CH, -FRONT_T - 1, -WSK_W / 2 - WSK_CH]) cube([WSK_L + 2 * WSK_CH, 1.0, WSK_W + 2 * WSK_CH]); }   // 外面のベベル
}
WIN_Z_OUT = 8.5 + FRONT_T;   // OLED の局所 z で板の外面（背面 8.5 ＋ 板 2.0）
module p_front() difference() {
    union() { translate([LW_X, OUT_Y0, 0]) cube([IN_X - LW_X, FRONT_T, Z_TOP]); front_ears(); }
    at_oled() {   // 局所 z 8.5 が板の内面・10.5 が外面
        translate([oled_glass_x() - WIN_CL_X, oled_glass_y() - WIN_CL_Z, 8.5 - 1]) cube([oled_glass()[0] + 2 * WIN_CL_X, oled_glass()[1] + 2 * WIN_CL_Z, FRONT_T + 2]);   // 窓
        translate([0, 0, 8.5 - 1]) linear_extrude(FRONT_T + 2) offset(delta = WIN_CL_Z) oled_bulge_2d();                                                                   // 下辺の張り出し
        hull() { translate([oled_glass_x() - WIN_CL_X, oled_glass_y() - WIN_CL_Z, WIN_Z_OUT - PORT_BEV]) cube([oled_glass()[0] + 2 * WIN_CL_X, oled_glass()[1] + 2 * WIN_CL_Z, 0.01]);
                 translate([oled_glass_x() - WIN_CL_X - PORT_BEV, oled_glass_y() - WIN_CL_Z - PORT_BEV, WIN_Z_OUT]) cube([oled_glass()[0] + 2 * (WIN_CL_X + PORT_BEV), oled_glass()[1] + 2 * (WIN_CL_Z + PORT_BEV), 1.0]); }   // 外面のベベル
    }
    for (m = [[RSP_X + respeaker_L() - (4.162 + 6.812) / 2, +1], [RSP_X + respeaker_L() - (75.162 + 77.812) / 2, -1]])   // マイク U4（右・X 78.5）・U5（左・X 7.5）。ヒゲは外へ 1.0 寄せる
        for (i = [-1, 0, 1]) whisker([m[0] + m[1] * 1.0, 0, RSP_Z + (15.252 + 18.752) / 2 + i * 3.6], m[1] * i * WSK_ANG);
}
// ---- 天板: つまみの台座と抜き・会話ボタンの台座と口・スピーカーの座とハニカムのグリル ----
SPK_LIFT = 0.9; SPK_CL = 0.3;
module spk_obr(l, w, h) hull() for (sx = [w / 2, l - w / 2]) translate([sx, w / 2, 0]) cylinder(d = w, h = h, $fn = 48);
module p_top() difference() {
    union() {
        translate([OUT_X0, OUT_Y0, Z_TOP]) cube([OUT_X1 - OUT_X0, OUT_Y1 - OUT_Y0, TOP_T]);
        at_knob() knob_station_add();
        at_btn()  btn3_station_add();
        pb_mount();   // PowerBoost のダボ（天板と一体・2026-09-05）
    }
    at_knob() knob_station_cut();
    at_btn()  btn3_station_cut();
    top_screw_cuts();
    translate([SPK_AT[0] - spk_l() / 2 - SPK_CL, SPK_AT[1] - spk_w() / 2 - SPK_CL, Z_TOP - 0.01]) spk_obr(spk_l() + 2 * SPK_CL, spk_w() + 2 * SPK_CL, SPK_LIFT + 0.01);   // 座（内面から 0.9）
    intersection() {   // グリル: 振動板 14 × 8 の上にハニカム（二面幅 2.2・壁 1.2）
        translate([SPK_AT[0] - spk_dia()[0] / 2, SPK_AT[1] - spk_dia()[1] / 2, Z_TOP - 1]) spk_obr(spk_dia()[0], spk_dia()[1], TOP_T + 2);
        for (i = [-3 : 3], j = [-2 : 2]) translate([SPK_AT[0] + i * 3.4 + (j % 2 == 0 ? 0 : 1.7), SPK_AT[1] + j * 2.94, Z_TOP - 1]) cylinder(d = 2.2 / cos(30), h = TOP_T + 2, $fn = 6);
    }
}
// ---- ハッチ: Type-C の口・トグルの穴・電池の口 ----
TC_PORT_C = [TC_AT[0] + tc_size()[2] + tc_conn()[2] / 2, IN_Y + HATCH_T / 2, TC_AT[2] + tc_size()[0] / 2];   // 板の表 ＋ 胴の高さの半分・板の長さの中央（4.92, ・, 10.75）
TC_PORT_SZ = [3.86, 9.54];   // [X, Z]（殻 3.26 × 8.94 ＋ 片側 0.3）。基板が縦なので口は縦長（🔴 2026-09-05 まで横長に開けていた・ユーザー指摘）
module p_hatch() difference() {
    union() { translate([LW_X, IN_Y, 0]) cube([IN_X - LW_X, HATCH_T, Z_TOP]); sw4_hatch_rim(); }   // 縁（溝の床〜内面・つば・爪）はハッチと一体
    port_cut(TC_PORT_C, TC_PORT_SZ[0], TC_PORT_SZ[1], HATCH_T, "y");
    battery_port_cut4(); sw4_band_cut(); sw4_lock_cut(); sw4_mag_window();   // 電池の口・蓋の彫り込み・ロックのねじとナット・磁石の窓
    translate([TC_AT[0] - 0.25, IN_Y - 1, TC_AT[2] - 0.25]) cube([tc_size()[2] + 0.5, 1 + (TC4_Y1 - IN_Y) + 0.25, tc_size()[0] + 0.5]);   // Type-C 基板の後縁を受けるスリット（板 1.6 ＋ 片側 0.25・深さ 0.4 ＋ 0.25）
    at_tgl() translate([0, 0, -1]) mts102_hole(HATCH_T + 2);   // 局所 +z がハッチの外（🔴 2026-09-05 まで −z 側に切っていて穴が内側に居た）
}
module p_floor() difference() { union() { translate([OUT_X0, OUT_Y0, -FLOOR_T]) cube([OUT_X1 - OUT_X0, OUT_Y1 - OUT_Y0, FLOOR_T]); tc_seat(); } floor_screw_cuts(); }   // Type-C の受けは床と一体（2026-09-05）
// 刷る部品ごとの色（同じ色 = 同じ部品として刷る）
module skin(a = 0.5) { color("#e0a040", a) p_floor(); color("#c9d0d8", a) p_top(); color("#4a90d9", a) p_lwall(); color("#4a90d9", a) p_rwall(); color("#9b59b6", a) p_front(); color("#27ae60", a) p_hatch(); }

// ============================================================
// 締結（v4 §5 の流儀: 樹脂にねじを切らない・貫通＋ナット。ビスは M2×15 / M2×6 / M2×8・ナット M2）
// ============================================================
NUT_AF = 4.10; NUT_T = 1.8; SCR_D = 2.5; SCR_CB = 4.4; SCR_CBT = 1.6;   // v4 case_base の値（ナット二面幅 4.1・厚 1.8・通し φ2.5・座ぐり φ4.4 × 1.6）
POST_W = 6.0;                          // 柱の一辺（v4 BOSS 7.0。OLED の板の端 X 8.0 との隙間を 0.3 取るため 6.0）
POST_B_H = 12.0;                       // 下の柱の高さ（v4 BOSS_B_H 12・M2×15 ＝ 床 2 ＋ 13）
POST_T_H = 12.0;                       // 上の柱の高さ（天井から）
EAR_T = 3.2;                           // フロント板の耳の厚み（v4 耳 3.2・M2×8）
// 下の柱 3 本 [x0, y0]（左前・右前・右後ろ。左後ろは Type-C 基板の席）
POSTS_B = [[LW_X, 0], [IN_X - POST_W, 0], [IN_X - POST_W, IN_Y - POST_W]];
// 上の柱 4 本 [x0, y0, 耳の有無]（後ろ 2 本は天板 → 柱、前 2 本は 天板 → フロントの耳 → 柱）
POSTS_T = [[LW_X, IN_Y - POST_W, false], [IN_X - POST_W, IN_Y - POST_W, false], [LW_X, 0, true], [IN_X - POST_W, 0, true]];
module hex_pocket(af, t) rotate([0, 0, 30]) cylinder(d = (af + 0.1) / cos(30), h = t, $fn = 6);
POST_D_FRONT = 5.0;   // 前の柱の奥行き（ReSpeaker のボタン K1 が Y 5.6 まで来るので 6.0 → 5.0）
function post_dy(p) = (p[1] == 0) ? POST_D_FRONT : POST_W;
module post_b(p) difference() {   // 下の柱: 床から POST_B_H。頭に上向きのナットのポケット・通し
    translate([p[0], p[1], 0]) cube([POST_W, post_dy(p), POST_B_H]);
    translate([p[0] + POST_W / 2, p[1] + post_dy(p) / 2, -1]) cylinder(d = SCR_D, h = POST_B_H + 2, $fn = 24);
    translate([p[0] + POST_W / 2, p[1] + post_dy(p) / 2, POST_B_H - NUT_T]) hex_pocket(NUT_AF, NUT_T + 1);
}
module post_t(p) difference() {   // 上の柱: 天井から POST_T_H 下がる。耳付きなら耳の厚みだけ低い。頭に上向きのナットのポケット・通し
    zt = Z_TOP - (p[2] ? EAR_T : 0);
    translate([p[0], p[1], zt - POST_T_H]) cube([POST_W, post_dy(p), POST_T_H]);
    translate([p[0] + POST_W / 2, p[1] + post_dy(p) / 2, zt - POST_T_H - 1]) cylinder(d = SCR_D, h = POST_T_H + 2, $fn = 24);
    translate([p[0] + POST_W / 2, p[1] + post_dy(p) / 2, zt - NUT_T]) hex_pocket(NUT_AF, NUT_T + 1);
}
// ブリッジの帯を受ける棚（壁から BRG_LDG_W・高さ BRG_LDG_H・上面 = 帯の裏）。ねじの真下に横差しのナット溝（棚の内側の面から）
BRG_LDG_W = 5.0; BRG_LDG_H = 8.0; BRG_LDG_SKIN = 1.6;   // v4 の値。SKIN: 棚の上面 ↔ ナットの上面
LDG_L_Y = [ARM_Y[0], TC4_Y0 - 0.5];   // 左の棚: Type-C 基板（Y 59.4〜）を避けて Y 50.5〜58.9
LDG_R_Y = [ARM_Y[0], ARM_Y[1]];       // 右の棚: 帯の幅いっぱい
module ledge(x0, w, y, anch, h = BRG_LDG_H) difference() {
    translate([x0, y[0], BRG_ZB - h]) cube([w, y[1] - y[0], h]);
    translate([anch[0], anch[1], BRG_ZB - BRG_LDG_H - 1]) cylinder(d = SCR_D, h = BRG_LDG_H + 2, $fn = 24);
    hull() for (dx = [0, (x0 < IN_X / 2) ? 10 : -10]) translate([anch[0] + dx, anch[1], BRG_ZB - BRG_LDG_SKIN - NUT_T]) hex_pocket(NUT_AF, NUT_T);   // ナットの溝（内側の面から横差し）
}
LDG_L_H = BRG_ZB - (19.48 + 0.3);   // 左の棚の高さ 5.6: Type-C の L 字のハウジング（Z 〜19.48）の 0.3 上から帯の裏まで（ナットの溝 Z 22.0〜23.8 は入る）
module fasten_lwall() { post_b(POSTS_B[0]); post_t(POSTS_T[0]); post_t(POSTS_T[2]); ledge(LW_X, BRG_LDG_W, LDG_L_Y, BRG_ANCH[0], LDG_L_H); }
module fasten_rwall() { post_b(POSTS_B[1]); post_b(POSTS_B[2]); post_t(POSTS_T[1]); post_t(POSTS_T[3]); ledge(IN_X - BRG_LDG_W, BRG_LDG_W, LDG_R_Y, BRG_ANCH[1]); }
// 床: 下の柱の真下に通し＋座ぐり（M2×15 の頭は床の裏）
module floor_screw_cuts() for (p = POSTS_B) translate([p[0] + POST_W / 2, p[1] + post_dy(p) / 2, 0]) {
    translate([0, 0, -FLOOR_T - 1]) cylinder(d = SCR_D, h = FLOOR_T + 2, $fn = 24);
    translate([0, 0, -FLOOR_T - 0.01]) cylinder(d = SCR_CB, h = SCR_CBT, $fn = 32);
}
// 天板: 上の柱の真上に通し＋座ぐり（M2×6 / M2×8 の頭は天板の上）
module top_screw_cuts() for (p = POSTS_T) translate([p[0] + POST_W / 2, p[1] + post_dy(p) / 2, 0]) {
    translate([0, 0, Z_TOP - 1]) cylinder(d = SCR_D, h = TOP_T + 2, $fn = 24);
    translate([0, 0, Z_TOP + TOP_T - SCR_CBT]) cylinder(d = SCR_CB, h = SCR_CBT + 0.01, $fn = 32);
}
// フロント板の耳 2 つ（天板と前の耳柱に挟まれる・通し付き）
module front_ears() for (p = [POSTS_T[2], POSTS_T[3]]) difference() {
    translate([p[0], 0, Z_TOP - EAR_T]) cube([POST_W, POST_D_FRONT, EAR_T]);
    translate([p[0] + POST_W / 2, POST_D_FRONT / 2, Z_TOP - EAR_T - 1]) cylinder(d = SCR_D, h = EAR_T + 2, $fn = 24);
}

// ---- 中身 ----
module innards() for (n = UNITS) one(n);

if (part == "look")  innards();
if (part == "plugs") plugs();
if (part == "bridge") { bridge(); brg_front(); straps(); one("bat"); one("ina"); }
if (part == "skin")   skin();
if (part == "tcfit")  { one("tc"); color("#e0a040", 0.9) p_floor(); color("#4a90d9", 0.35) p_lwall(); color("#27ae60", 0.35) p_hatch(); }   // 床（受け込み）＝橙・左の壁（押さえ込み）＝青・ハッチ＝緑
if (part == "all")    { skin(); innards(); }
if (part == "explode") { bridge(); translate([0, 0, -15]) brg_front(); translate([0, 0, 30]) straps(); translate([0, 0, 12]) one("bat"); translate([0, 0, 45]) one("ina"); }
if (starts(part, "only_")) one(tail(part, 5));
if (starts(part, "hit_"))  { n = tail(part, 4); intersection() { one(n); others(n); } }
if (starts(part, "pair_")) { ab = tail(part, 5); k = search("_", ab)[0]; a = _join([for (i = [0 : k - 1]) ab[i]]); b = _join([for (i = [k + 1 : len(ab) - 1]) ab[i]]); intersection() { one(a); one(b); } }
echo(v5 = [IN_Y, IN_Z], hub_plug_top = HUB_PLUG_TOP, brg_zb = BRG_ZB, bat = BAT_AT, pair_y0 = PAIR_Y0);
