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
//   explode  … 箱全体の分解（皮 6 枚を外へ、天板は小組ごと上へ、ブリッジ・帯・電池・電流計・PowerBoost は段に分けて上へ。床とハブ・ReSpeaker・OLED・Type-C は置いたまま）
//   tcfit    … Type-C 基板と、床（受け込み・橙）・左の壁（押さえ込み・青）・ハッチ（緑）だけ
//   skin     … 皮（板 6 枚・ハッチは蓋の彫り込みと縁込み）。蓋・ロック・床の板は単位 shutter / lock / hatchplate
//   all      … 皮＋中身＋ブリッジ一式
//   p_floor / p_top / p_lwall / p_rwall / p_front / p_hatch … 板 1 枚だけ（柱・棚・耳・ダボ・穴込み）
//   fasten   … 締結の絵: 左右の壁（柱・棚）を不透明、床と天板を半透明、ブリッジと前板と帯を重ねる
//   hit_<名>  … その 1 単位 ↔ 他の全部 の当たり（体積を STL で取る。0 が正）。名は oled rsp hub bat ina pb tc knob btn spk tgl bridge reed
//   pair_<a>_<b> … 2 単位の重なり（例 pair_ina_btn）
//   only_<名> … 1 つだけ（外形を数字で取る用）。名は oled rsp hub bat ina pb tc knob btn spk tgl（基板＋その口）と hubplugs oledplug inaplug pbplug xiaoplugs knobplugs（口だけ）
//   wires    … 中身＋線（束は丸・口の近くは 1 本ずつ扇）。wiresonly は線だけ
//   hit_wires … 線 ↔ 中身と皮の全部の当たり。hit_w_<束> は束 1 つだけ（xiao oled as5600 pwr chg ina tgl btn2 phin phout bat batout）。only_w_<束> は束 1 つの絵
//   print_<板>  … 刷る向き（floor top lwall rwall front hatch は外面を下・bridge は皿の裏を下・brgfront は前の面を下・shutter lock shutfloor は外面/溝の床を下。v4 と同じ。つまみは parts/knob_v5.scad、会話ボタンは parts/btn_v3.scad の print_piston / print_tub をそのファイルで焼く）＋ 支柱とラフト（parts/props_v5_gen.scad）
//   sk_<名>    … その 1 単位 ↔ 皮 6 枚 の当たり（0 が正。ReSpeaker の押し 0.3 は意図した当たり）
//   seam_<板>_<板> … 板 2 枚の重なり（例 seam_top_front。0 が正）
//   print_strap_a / print_strap_b / print_strap_c … 帯 1 本を刷る向き（直置き・足の裏が Z 0）＋ 支柱とラフト（parts/props_v5_gen.scad・python hardware/tools/props_gen.py）。素の形は -D PROPS_OFF=true
//   （皮・板・検査の語は皮を起こすときにここへ足す。既にある語の意味は変えない）
// ============================================================
part = "look";
PROPS_OFF = false;   // true: 刷る向きの素の形（支柱・ラフト無し）。tools/props_gen.py がこれで焼いて支柱の位置を決める

use <parts/parts.scad>
use <parts/respeaker_lite.scad>
use <parts/hub_board.scad>
use <parts/typec_115426.scad>
use <parts/plug.scad>
use <parts/wires.scad>    // 線（丸束・曲げ半径で丸めた点列）
use <parts/btn_v3.scad>    // 会話ボタン v3（🔒 2026-08-30）。原点 = ボタンの芯・z0 = 天板の外面
use <parts/knob_v5.scad>   // つまみ v5。原点 = 軸・z0 = 天板の外面
include <parts/hub_board_parts.scad>   // HUB_HEADERS（口の表・自動生成）。数字はここから読む
include <icons/icon_wrench_u.scad>   // スパナ（🔒 ユーザーの絵 uuu.svg から）
include <icons/icon_headphone.scad>  // ヘッドホン（ユーザーの EPS から）
PLUG_EMBEDDED = true; HUB_EMBEDDED = true;
$fn = 48;   // 🔒 v4 と同じ分割数（無いと小さい円が 5〜6 角形で出る・2026-08-23 ユーザー指摘）

// ---- 箱の中の座標（v4 と同じ）----
//   X: 左の壁の内面が LW_X 1.694・右の壁の内面が IN_X 86.05（ReSpeaker の板の左端 2.0 から測った v4 の座標）・Y 0 = フロント板の内面・Z 0 = 床の上面
//   +X 右（XIAO の USB-C 側）・+Y 後ろ（ハッチ側）・+Z 上（天面）
// ---- 広げる量（Y は AI の初期値・当たり表の最大 3.7 の 2 倍。Z はユーザー決定）----
GROW_Y = 3.25;   // 🔒 ユーザー 2026-09-05「意味不明な拡大はおかしいでしょ」: 8 → 0 → I2C の L 字がハッチの床の板にかかり「3mm 伸ばそう」→「Y を 0.25 増やして」: 3.25（電流計の I2C ↔ 床の板の空き 0.19 → 0.44）
GROW_Z = 2.0;    // 🔒 ユーザー 2026-09-05: 初期値 8 → 電流計を 215° に回して口をバスタブの外へ出し、会話ボタンを X 19 にして「+2 で」（内寸 50.45・外寸 55）。一時 12.5・8.5 にした案は取り下げ

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
BAT_X0  = 14.5 - 3.0 + 3.0 - 0.6;   // v4 BAT_X0 = 14.5 + BAT_DX(−3)。🔒 ユーザー 2026-09-05「電池を 3mm 右に」: +3 →「電池（帯ごと）を左へ 0.6」: −0.6（皿・土手・帯・前板・電池の口も一緒。帯の右の足が AS5600 の板の左端と 0.3 重なったぶん）
BAT_YS  = 1.0;                      // v4 BAT_YS: 電池を前板の返し（1.0）の後ろへ
TRAY_Y0 = HUB_Y0 + (52.0 - lipo_size()[0]) / 2;   // 皿の前縁 12.9（v4 の BAT_Y0）。前板・帯の区間・電流計の枠はここから測る
BAT_Y0  = TRAY_Y0 + BAT_YS;                        // 電池の前縁 13.9（🔴 2026-09-05 まで BAT_YS を落としていて電池が返しに 138mm³ 食い込んでいた）
BAT_AT  = [BAT_X0, BAT_Y0, BRG_ZB + BRG_T];   // Z は皿の上（v4 BAT_Z 23.4 を口の頭 23.1 + 0.5 + 皿 2.0 に置き換え）
BAT_TOP = BAT_AT[2] + lipo_size()[2];
STRAP_T = 2.0;                      // 留め帯の天板の厚み（v4 STRAP_T）
PAIR_Y0 = TRAY_Y0 + (lipo_size()[0] - (pb_size()[1] + 0.5 + ina_size()[1])) / 2;   // v4 PAIR_Y0（電流計と PowerBoost を電池の Y の中央に並べる）
STRAP_C_POCKET = 0.0;               // 2026-09-05 一度 1.0 にしたが、ユーザー「ピンヘッダ部分は 1.2mm 掘って」で板を帯に直置きにしたので 0 に戻す
HDR_POCKET_D = 1.2 + 0.3;           // 電源ヘッダの足の裏出し 1.2 の逃げ（帯 C の天板に掘る・床 0.5 残る）
INA_DX  = -4.7; INA_DY = 3.0; INA_LIFT = 0.0; INA_THETA = 0;   // 2026-09-06 一度 4.5 にしたが取り消し（ヘッダは表・裏は足の先だけ）。   // INA_LIFT: v4 は 1.0。🔒 ユーザー 2026-09-05「浮いてるでしょ」: 足の逃げは帯に掘って板は帯に直置き（0）   // v4 の値（🔒 2026-08-29 INA_DY 3.0・2026-08-26 0°）
BOARD_LIFT = 0.5;                   // v4: PowerBoost の蝶番を帯の面から 0.5 浮かせる（🔒 2026-08-25）
INA_SX  = -4.0 + 5.0 + 0.6 - 2.0 + 1.0 + 4.0 + 5.0;   // →「右に 4mm」: +4 →「右に 5mm」: +5。 🔒 ユーザー 2026-09-05 …→ −4 →「右に 5mm」: +1 →「2mm 左に」: −1 →「1mm 右に」: 0。電池を −0.6 したとき枠が動いたぶんを +0.6 補正（電流計の場所は変えない）
INA_SY  = 1.2 - 3.0;                // 🔒 ユーザー 2026-09-05 …→ +1.2 →「手前に 3mm」: −1.8
INA_RZ  = 180;                      // 🔒 ユーザー 2026-09-05「電流計の Y 軸回転をやめて水平に」（ユーザーの「Y 軸回転」＝上下の軸まわり＝ここでは Z）: 45 右・90 左・10 右で 215 にしていたのを、回す前の 180（板を箱の軸に平行・I2C の口が後ろ・電源の口が前）に戻す
PB_DY   = -4.0;                     // 🔒 ユーザー 2026-09-05「PowerBoost と電流計を 4mm 前へ」（電流計もこの値を読む）
PB_DY2  = -2.0;                     // 🔒 ユーザー 2026-09-05「PowerBoost 手前に 4mm」→「2mm くらい奥に」（天井に付けた後・PowerBoost だけ）: −4 → −2
// （PowerBoost の枠は下の at_pb()。v4 pb_frame() と同じ式）
PB_TILT = 0;                        // 🔒 ユーザー 2026-09-05「PowerBoost の傾きを無くして」。v4 の 14°（2026-08-29）は電流計を前縁の下へ潜らせるための物で、重ねるなら要らない
LW_X    = 1.694;                    // 左の壁の内面（v4: ReSpeaker の板の左端 2.024 − 0.33）
RIGHT_CL = -1.2;   // 🔒 v4 2026-08-25 ユーザー「壁の移動が足りないだけ」: XIAO の USB-C の殻（先 85.554）を壁に貫通させ、口の面を外面の 0.8 裏に置く
IN_X    = RSP_X + respeaker_L() + xiao_usb_out() + RIGHT_CL;   // 右の壁の内面 84.354（🔴 2026-09-05 まで +0.5 の 86.054 で 1.7 外に置き「v4」と書いていた。ユーザー「XIAO の USB 口も全く違う」）
XIAO_FACE_X = RSP_X + respeaker_L() + xiao_usb_out();   // 85.554 レセプタクルの面
IN_Y    = HUB_Y0 + 52.0 + 10.1 + GROW_Y;      // v4 の式: HUB_Y0 11.9 ＋ 板 52 ＋ 後ろの逃げ 10.1（BACK_CL・2026-09-05）＝ 74.0。ハブの後縁 67.9 から 6.1（🔴 一時 HUB_AT[1]（+4）から数えて 86 にしていた）
IN_Z    = 48.454 + GROW_Z;          // v4 の内寸 48.454（§1）+ 広げ
Z_TOP   = IN_Z;                     // 天面の内面
TOP_T   = 2.5;                      // 天板の厚み。btn_v3（B3_PLATE_T）と knob_v5（DECK_T）が 2.5 で形を持っているので同じ値
ROW_Y   = 17.3;                     // 会話ボタンとスピーカーの列（🔒 Y は同じ）。22.3 − 0.5 − 7.5 + 3.0（BTN_ROW_DY 3.0・2026-08-29）
SPK_AT  = [63.2 + 1.5, ROW_Y];      // 🔒 ユーザー 2026-09-05「スピーカーも右に 1.5mm」（つまみの台座と一緒）。§2「SPK4 X 63.204」
KNOB_AT = [SPK_AT[0], 33.3 + 1.6 - 1.1 + 8];   // 🔒 ユーザー 2026-09-05「つまみの X 中央をスピーカーの X 中央に合わせて」（Y に合わせたのは言い間違い・41.8 に戻す）。X: 63.2 ＋ 右へ 1.5 ＝ 64.7（スピーカーと同じ）。Y: v4 KNOB_YC 33.8 ＋ KNOB_DY 8（🔒 2026-08-29「ノブを後ろに」）＝ 41.8
BTN_AT  = [19.0 + 1.0 - 2.0 + 2.0, ROW_Y];   // →「2mm 右へ」: 20。 🔒 ユーザー 2026-09-05「右へ 2」→「左へ 4」→「左に 3mm」→「1mm 右へ」→「2mm 左へ」: 24 → 26 → 22 → 19 → 20 → 18
TC_AT   = [1.694, IN_Y + 0.4 - 15.0, 0.75];      // §2「X 1.694〜3.294・Y 57.4〜72.4（IN_Y 72）・Z 0.5〜20.5」。Y はハッチに追従
TGL_AT  = [SPK_AT[0], IN_Y, IN_Z - 7.1];   // 🔒 ユーザー 2026-09-05「トグルの X 中央をスピーカーの X 中央に」（一度「右端をつまみの右端に」で 74.2 にしたが戻した）: 64.7。        // ハッチに付くトグルの軸。天井から 7.1（胴の上端は天井の 0.6 下・胴の下端は蓋の縁の上端 37.5 の 0.45 上）。🔴 8.4 は AI の仮定で、+2 にしたとき蓋の縁に 2.0 入っていた

WALL = 2.0; FLOOR_T = 2.0; FRONT_T = 2.8; HATCH_T = 2.0;   // 板の厚み。フロントは 2.8（🔒 2026-09-04 二次硬化で鞍型に歪んだので 2.0 → 2.8）。皮の節より前に置く（shutter_v4 の include が読む）
BAT_Z = BAT_AT[2];                  // 電池の下面（shutter_v4 が読む）
include <parts/shutter_v4.scad>     // 電池の蓋（v4 の形）: 蓋・ロック・床の板・ハッチの縁・彫り込み
module sw4_carve_targets() one("tc");   // 増し肉を削る相手（v5: Type-C 基板）
// つばの欠き: トグルの胴（X 36〜44・下端 36.85）の真下だけ、蓋の縁の上のつば 1.0 を欠いて帯の縁（36.525）で止める（隙間 0.3・天板を上げずにトグルを入れる・2026-09-05）
// 蓋の床の板のトグルの逃げ: 胴（幅 mts102_d 8）の左右 0.3・胴の下端の 0.3 下から上を欠く（🔒 ユーザー 2026-09-05「蓋の底をトグルスイッチ分削って」）
// つまみの台座の後ろの縁の欠き: トグルの端子（幅 1.2・列は Z に 3 つ・先は Y 59.25）の周り 0.5。台座は Y 61.3 まで来ていて端子が 2.0 入っていた
module tgl_term_notch() translate([TGL_AT[0] - 0.6 - 0.5, tgl_term(0)[1] - 0.5, TGL_AT[2] - mts102_w() / 2 - 0.5]) cube([1.2 + 1.0, 30, mts102_w() + 1.0]);
module tgl_plate_notch() translate([TGL_AT[0] - mts102_d() / 2 - 0.3, IN_Y - 30, TGL_AT[2] - mts102_w() / 2 - 0.3]) cube([mts102_d() + 0.6, 31, 30]);
module sw4_flange_notch_2d() translate([TGL_AT[0] - 4.0 - 0.3, sw4_bz1() - 0.01]) square([8.0 + 0.6, SW4_BACK_FL + 1]);

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
PB_SX = -9.0 + 0.6 + 3.0 + 2.0;     // 🔒 ユーザー 2026-09-05「右に 3mm」（回転 15° の後）→「右に 2mm」（17° の後）。電池を −0.6 したとき枠が動いたぶんを +0.6 補正（PowerBoost の場所は変えない）。🔒 ユーザー 2026-09-05「PowerBoost を 2mm 左へ」→「左に 4mm」(−6)。電池を +3 したとき枠が動いたぶんを −3 補正して −9（PowerBoost の場所は変えない）
// 🔒 ユーザー 2026-09-05「PowerBoost は天井につけましょう」: 板の裏を天板の内面に向けて（部品は下向き）座 PB_CEIL_SO で浮かす。
//   XY の中心は pb_frame0 の場所のまま。
PB_CEIL_SO = pb_pcb_t() + 5.2 + 0.5;   // 天板の内面 ↔ 板の裏 7.3（板 1.6 ＋ JST 5.2 ＋ 隙間 0.5）。🔒 ユーザー 2026-09-05「基板面を下にしなければならない理由はない」: 部品面を上（天井側）に
PB_FLIP = [0, 0, 0];                // 裏返さない（部品が上）。2026-09-05 まで [180,0,0]
PB_RZ = 0;                          // 🔒 ユーザー 2026-09-05「Z 軸左回転 15 度」→「もう 2 度」→「元に戻して」: 0（JST 前・L 字 後ろ）（上から見て反時計回り）。それまで 0（JST 前・L 字 後ろ。「Z 軸で 180 度回転」は裏返しと組の値で、部品面を上にしたとき 0 に戻した）
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
TC_RA_N = 6;   // L 字ヘッダの本数。板の穴は 7（VBUS GND D+ D− CC1 CC2 GND）だが 7 本目の GND は使わないので 6 本にする（7 本目の樹脂がハブの左後ろの柱 φ7 に 0.3・ピンの先がハブの板の左端に 0.11 かかるため。2026-09-05）
module tc_ra() for (i = [0 : TC_RA_N - 1]) { z = TC_ZT - (2.54 + i * 2.54);
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
module ina_plug() at_ina() ina_back_flip() { hd = ina_hdr(); translate([hd[0] + hd[4] + 1.27, hd[2] + 1.27, 1.6 + 2.5]) rotate([0, 0, INA_I2C_YAW]) translate([-1.27, 0, 0]) rotate([0, -90, 0]) rotate([0, 0, 90]) plug(4, INA_I2C_EXIT); }
// I2C ヘッダが裏（INA_HDR_BACK）なら、上に描いた口を板の中面 z 0.8 で鏡にして裏へ（2026-09-06）
module ina_back_flip() { if (ina_back_env() > 0) translate([0, 0, 0.8]) mirror([0, 0, 1]) translate([0, 0, -0.8]) children(); else children(); }   // ピンの根元（樹脂の中心線）で INA_I2C_YAW だけ振る
// 電流計の電源の口: 4 本・L 字（🔒 ユーザー 2026-09-05「では電流計を L 字にしてください」。同日 直立て→L→直立て→L と往復）。ピンは端子側の縁（局所 +x）の外へ水平・樹脂の外面 x = 26+1.27・芯 z = 1.6+2.5。線は上へ曲がる
INA_PWR_EXIT = [0, 1];    // 口から出た線が曲がる向き（plug の局所 xy）。[-1,0] = 上（板の法線）・[0,1] = 右（+X 世界）・[0,-1] = 左。上だとバスタブの底に入るので右へ（行き先の電池のコネクタ対と PowerBoost の JST が右側・2026-09-05）
INA_PWR_YAW = [90 - 180, 0, 0, 0];   // 電源の L 字ピン 4 本の根元の振り（板の局所 y 3.6・7.87・12.13・16.4 の順＝板が 180 のとき世界の左から右）。🔒 ユーザー 2026-09-05「一番左のピンだけを左に 90 度回転」: 1 本目 +90（左＝反時計回り）→「右に 180 度」: −90（ハウジングが左＝−X を向く）。それまで 0（「右に 25 度」→「30 度」→「0 に戻す」）
function ina_pwr_yaw(j) = is_list(INA_PWR_YAW) ? INA_PWR_YAW[j] : INA_PWR_YAW;
module ina_pwr_plug() at_ina() for (j = [0 : 3]) let (q = ina_pwr_pins()[j]) translate([q[0] + 1.27, q[1], 1.6 + 2.5 + 1.27]) rotate([0, 0, ina_pwr_yaw(j)]) rotate([0, 90, 0]) plug(1, INA_PWR_EXIT);   // ピンの芯は板 1.6 ＋ 樹脂 2.5 ＋ 1.27。根元で INA_PWR_YAW だけ振る
// PowerBoost: JP2 の L 字（pb_ra_pwr() 3 本 ＋ pb_ra_chg() 2 本・ピンは板の上を +y へ水平・芯 z = 1.6 + 2.5）。ハウジングは 1 本ずつ。線は上（+Z）へ曲がる
module pb_plug() at_pb() for (i = concat(pb_ra_pwr(), pb_ra_chg())) translate([pb_jp2_x0() + i * 2.54, 0, 1.6 + 2.5]) rotate([90, 0, 0]) plug(1, [0, -1]);   // L 字は縁の外（局所 −y）へ水平。樹脂の外面 y=0。線は下（−Z・部品面が上なので天井を避ける）へ曲がる
// XIAO: 2 列 × 使う本数（🔒 2026-09-06 下の列 = 信号 4 本・上の列 = 電源 3 本。公式ピン配置を USB-C 左に回した向き＝マニュアル手順 2。それまで逆に置いていた）。ヘッダは XIAO の上（面から 1.4+2.5）・ハウジングは XIAO 面から真上（後ろ）へ
//   線は低い車線（Z 19 前後）へ: 上の列は下へ、下の列は上へ曲がる
module xiao_plugs() at_rsp() for (r = [0, 1]) { z = [9.397, 24.627][r]; used = [[2, 3, 4, 5], [0, 1, 2]][r];
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
    if (n == "hatchplate") { color("#27ae60") difference() { sw4_floor_plate(); tgl_plate_notch(); } sw4_magnets_wall(); }   // 床の板（ハッチの裏・別部品・磁石 2 個込み）。🔒 ユーザー 2026-09-05「蓋の底をトグルスイッチ分削って」: トグルの胴の逃げ
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
BRG_ANCH_D = 2.3; BRG_ANCH_CB = 4.4; BRG_ANCH_CBH = 0.6;   // 座ぐりの深さ 1.6 → 0.6（2026-09-05）: 腕は 2.0 厚なので 1.6 だと底が 0.4 しか残らず印刷の下限 0.42 を割る。腕の上は箱の中で頭が 0.7 出ても当たる物が無い   // （🔒 ユーザー 2026-09-05「奥のクソ細い橋は却下」。帯はつまみの口（X 58.7〜68.8・Y 〜49.8・Z 19〜）の後ろを通る）
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
STRAP_W = 6.9;    // 帯の太さ（3 本とも同じ）。🔒 ユーザー 2026-09-05「帯の太さをもっとせまく」: 13.3 → 6.9（元の A・B の太さ）。間隔 2.525 では足の三角（ツバ・TAB_MIN 3.5 以上の区間にだけ付く）が消えていた
STRAP_N = 3;   // 🔒 ユーザー 2026-09-05「帯を 2 個から 3 個に増やし等間隔に」（様子見・調整はまだ）
STRAP_SP = (lipo_size()[0] - STRAP_N * STRAP_W) / (STRAP_N + 1);   // 電池の長さ 50 の中に帯 3 本を、両端の余白も含めて同じ間隔で並べる（6.9 なら 7.3）
STRAP_BANDS = [for (i = [0 : STRAP_N - 1]) [BAT_Y0 + STRAP_SP + i * (STRAP_W + STRAP_SP), STRAP_W]];   // 6.9 のとき 21.2〜28.1・35.4〜42.3・49.6〜56.5
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
                              a = -90 + INA_RZ,
                              r = [v[0] * cos(a) - v[1] * sin(a), v[0] * sin(a) + v[1] * cos(a)],   // rotate Z(−90+INA_RZ)（任意の角度）
                              q = [r[0] + pb_size()[0] / 2, r[1] + pb_size()[1] / 2])
                         [INA_SX + PBF_O[0] - q[0], INA_SY + PBF_O[1] - q[1]];          // pb_frame0 の Z 軸 180° と送り
INA_HOLES_W = [for (h = ina_holes()) ina_hole_w(h)];
// E リング（呼び 1.5）の軸: φ2.0・板 1.6 の上に遊び 0.1 → 溝（径 1.5・幅 0.5）→ 掴みしろ 0.6。🔒 ユーザー 2026-09-05「電流計に E リング。PowerBoost もダボ＋E リング」。溝の数字は規格値（AI が置いた）
E15_D = 2.0; E15_GRV_D = 1.5; E15_GRV_W = 0.5 + 0.3; E15_PLAY = 0.1; E15_GRIP = 0.6;   // 溝の幅 0.8（リング 0.4 ＋ 0.4）。🔒 ユーザー 2026-09-05「AS5600 のダボの E リングが取れないくらい厳しい。PowerBoost と電流計の溝も同じはず」: 0.5 → 0.8、軸は同じだけ長くなる（e15_len）
function e15_len(t) = t + E15_PLAY + E15_GRV_W + E15_GRIP;   // 板厚 t の板を留める軸の長さ（板の面から）
module e15_shaft(t) ering_shaft(t, E15_D, E15_GRV_D, E15_GRV_W);
// 電流計の軸: 3.0（穴 3.2〜3.4）に E-2.3（軸 3〜4 用）の溝。🔒 ユーザー 2026-09-06「軸 3 を留める E リングなんていくらでも持ってる」。溝径 2.3・幅は板厚 0.6 ＋ 0.4（E-1.5 の溝を 0.4 広げた前例と同じ）
E23_D = 3.0; E23_GRV_D = 2.3; E23_GRV_W = 0.6 + 0.4;
module e23_shaft(t) ering_shaft(t, E23_D, E23_GRV_D, E23_GRV_W);
module ering_shaft(t, d, grv_d, grv_w) difference() {   // 板厚 t の板を留める軸。板の上に遊び E15_PLAY → 溝 → 掴みしろ E15_GRIP。🔴 2026-09-06 ユーザー「E-1.5 のピンに電流計の 3mm 近い穴を乗せるとどうなると思ってんの」: 2.0 の軸を 3.0 の穴に通していた（1mm ガタ）
    cylinder(d = d, h = t + E15_PLAY + grv_w + E15_GRIP, $fn = 32);
    translate([0, 0, t + E15_PLAY]) difference() { cylinder(d = d + 1, h = grv_w, $fn = 32); translate([0, 0, -1]) cylinder(d = grv_d, h = grv_w + 2, $fn = 32); }
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
        for (h = INA_HOLES_W) translate([h[0], h[1], BAT_TOP + STRAP_T - STRAP_C_POCKET]) { if (INA_LIFT > 0) cylinder(d = 5.8, h = INA_LIFT); translate([0, 0, INA_LIFT]) e23_shaft(ina_size()[2]); }   // 電流計の支柱: 軸 3.0 ＋ E-2.3 の溝（🔒 ユーザー 2026-09-06「この穴は恐らく 3.2 か 3.4 ある。つまり軸は 3 でいい」「軸 3 を留める E リングなんていくらでも持ってる」）
    }
    if (STRAP_C_POCKET > 0) translate([INA_FOOT[0] - 0.5, INA_FOOT[2] - 0.5, BAT_TOP + STRAP_T - STRAP_C_POCKET]) cube([INA_FOOT[1] - INA_FOOT[0] + 1.0, INA_FOOT[3] - INA_FOOT[2] + 1.0, STRAP_C_POCKET + 1]);
    at_ina() translate([26.0 - 1.27 - 1.0, 3.6 - 1.27 - 1.0, -HDR_POCKET_D]) cube([2.54 + 2.0, 16.4 - 3.6 + 2.54 + 2.0, HDR_POCKET_D + 1]);   // 電源ヘッダの足の列の逃げ（板の座標で彫る。板が回れば一緒に回る。🔒 ユーザー 2026-09-05「ピンヘッダ部分は 1.2mm 掘って」）
    at_ina() hull() for (y = [4.0 - 0.5, 4.0 + 4 * 2.54 + 0.5]) translate([3.3, y, -STRAP_T - 1]) cylinder(d = 3.6, h = STRAP_T + 2, $fn = 32);   // I2C ヘッダ 5 本（x 3.3・y 4.0〜14.7）の足の先の逃げ。🔒 ユーザー 2026-09-06「そんな薄い天井ありえない。アールつけつつ穴あけとけ」: 帯 C を貫通する長穴（幅 3.6・両端 R 1.8）。🔴 同日実機: 電源側だけ掘って前を掘らず、板が帯に載らなかった。帯の下は電池なので、足が 2.0 より長ければ切る
}
// ---- 帯 1 本だけ・刷る向き ----
//   strap_one(k): 帯 k（ツバ込み・その帯の上に立つ電流計の軸込み）。straps() を Y の板で切る（v4 strap_one と同じ切り方・ツバ TAB_L のぶん広げる）
//   strap_print(k): 直置き（組んだ姿勢のまま・足の裏とツバの裏が Z 0。🔒 ユーザー 2026-09-03「帯については浮かすのも傾けるのもやめましょう。柱を立てる方のパイプラインで」）。
//     天板の裏（足と足の間 36mm のアーチ）は tools/props_gen.py が立てる柱（props_strap_*）と 0.3 のラフト（raft_strap_*）で受ける。電流計の軸は上を向くので支えは要らない
module strap_one(k) intersection() { straps(); translate([-100, STRAP_BANDS[k][0] - TAB_L - 0.05, -100]) cube([400, STRAP_BANDS[k][1] + 2 * TAB_L + 0.1, 400]); }
module strap_print(k) translate([0, 0, -TAB_Z0]) strap_one(k);
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
FRONT_DY = 1.0;    // 🔒 v4 2026-08-25 ユーザー「板の位置を y−1」: フロント板を 1.0 後ろへ寄せ、OLED のガラスの面（Y 0）が外面の 1.0 奥に来る（黒枠は窓を素通りして前へ 1.0 出る）
OUT_X0 = LW_X - WALL; OUT_X1 = IN_X + WALL; OUT_Y0 = -FRONT_T + FRONT_DY; OUT_Y1 = IN_Y + HATCH_T;
// 角穴＋外面のベベル。c = 穴の中心（板の厚みの中央）・w, h = 板の面内の [横, 縦]・t = 板厚・axis = 板の法線 "x"|"y"・外面は法線の +側
PORT_R = 1.2;      // 口の角の丸み（v4 USBC_PORT_R）。🔴 2026-09-05 まで角の立った長方形で切っていた（ユーザー「何で四角いの」）
module port_rr(sz, r, g = 0) hull() for (a = [-1, 1], b = [-1, 1]) translate([a * (sz[0] / 2 - r), b * (sz[1] / 2 - r)]) circle(r = r + g, $fn = 40);   // 角丸の四角（2D）。g で外へ広げる
// 口: 角丸の四角を板に貫通させ、外面に 45° のベベル（PORT_BEV）。axis "x": w は Y・h は Z、外面は +X ／ axis "y": w は X・h は Z、外面は +Y
module port_cut(c, w, h, t, axis) {
    translate(c) rotate(axis == "x" ? [90, 0, 90] : [-90, 0, 0]) {   // 2D の x → Y（"x"）/ X（"y"）・押し出しは外向き
        translate([0, 0, -t / 2 - 1]) linear_extrude(t + 2) port_rr([w, h], PORT_R);
        hull() { translate([0, 0, t / 2 - PORT_BEV]) linear_extrude(0.01) port_rr([w, h], PORT_R); translate([0, 0, t / 2 + 1.0]) linear_extrude(0.01) port_rr([w, h], PORT_R, PORT_BEV + 1.0); }
    }
}

// ---- 外の稜の丸み R 2.0（v4 round_box・半径 = 壁厚）と、板どうしの 45° の継ぎ目 ----
//   各板 = 板の直方体（外面まで伸ばす）− 隣の板と分け合う稜の楔（内側の角から外側の角へ 45°）、を丸い外形 env() と交わらせる
EDGE_R = WALL;
// 角の球。sphere() は極に頂点が無く（$fn 48 で緯度の輪が 3.75° から始まる）、外面が R (1 − cos 3.75°) = 0.0043 内側に来て板 5 枚が 0.0043 浮いた（🔒 ユーザー 2026-09-05「浮いてるってよ」）。
//   半円（頂点が ±Z にある）を回して作ると極も赤道も頂点に乗り、外面が数字どおりの位置に出る
module edge_ball() rotate_extrude($fn = 48) intersection() { circle(r = EDGE_R, $fn = 48); translate([0, -EDGE_R - 1]) square([EDGE_R + 1, 2 * EDGE_R + 2]); }
module env() hull() for (x = [OUT_X0 + EDGE_R, OUT_X1 - EDGE_R], y = [OUT_Y0 + EDGE_R, OUT_Y1 - EDGE_R], z = [-FLOOR_T + EDGE_R, Z_TOP + TOP_T - EDGE_R]) translate([x, y, z]) edge_ball();
BIG = 400;
// 45° の半空間。p = 稜の内側の角（3D）、u = 稜に直交する 2 方向のうち「この板の面に沿う方向」の単位ベクトル、v = 「厚み方向」の単位ベクトル（外向き）。
//   落とすのは (q − p)·u > (q − p)·v の側（隣の板の取り分）。楔 = その半空間 ∩ 角の直方体は、大きな回転した直方体で表す
function vcross(a, b) = [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
module halfspace(p, u, v) { w = vcross(u, v); translate(p) multmatrix([[u[0], v[0], w[0], 0], [u[1], v[1], w[1], 0], [u[2], v[2], w[2], 0], [0, 0, 0, 1]]) rotate([0, 0, -45]) translate([0, -BIG / 2, -BIG / 2]) cube([BIG, BIG, BIG]); }   // 局所 (s, t) = (a·u, a·v)。s > t の側（線 t = s の右下）を落とす
// 板ごとの楔（隣に取られる側）。床: 4 稜（左右の壁・フロント・ハッチ）で、床の面に沿う方向 = 壁へ向かう横方向、厚み方向 = −Z
module floor_wedges() {
    halfspace([LW_X, 0, 0], [-1, 0, 0], [0, 0, -1]);  halfspace([IN_X, 0, 0], [1, 0, 0], [0, 0, -1]);
    halfspace([0, OUT_Y0 + FRONT_T, 0], [0, -1, 0], [0, 0, -1]);  halfspace([0, IN_Y, 0], [0, 1, 0], [0, 0, -1]);
}
module top_wedges() {
    halfspace([LW_X, 0, Z_TOP], [-1, 0, 0], [0, 0, 1]);  halfspace([IN_X, 0, Z_TOP], [1, 0, 0], [0, 0, 1]);
    halfspace([0, OUT_Y0 + FRONT_T, Z_TOP], [0, -1, 0], [0, 0, 1]);  halfspace([0, IN_Y, Z_TOP], [0, 1, 0], [0, 0, 1]);
}
module lwall_wedges() {
    halfspace([LW_X, 0, 0], [0, 0, -1], [-1, 0, 0]);  halfspace([LW_X, 0, Z_TOP], [0, 0, 1], [-1, 0, 0]);
    halfspace([LW_X, OUT_Y0 + FRONT_T, 0], [0, -1, 0], [-1, 0, 0]);  halfspace([LW_X, IN_Y, 0], [0, 1, 0], [-1, 0, 0]);
}
module rwall_wedges() {
    halfspace([IN_X, 0, 0], [0, 0, -1], [1, 0, 0]);  halfspace([IN_X, 0, Z_TOP], [0, 0, 1], [1, 0, 0]);
    halfspace([IN_X, OUT_Y0 + FRONT_T, 0], [0, -1, 0], [1, 0, 0]);  halfspace([IN_X, IN_Y, 0], [0, 1, 0], [1, 0, 0]);
}
module front_wedges() {
    halfspace([LW_X, OUT_Y0 + FRONT_T, 0], [-1, 0, 0], [0, -1, 0]);  halfspace([IN_X, OUT_Y0 + FRONT_T, 0], [1, 0, 0], [0, -1, 0]);
    halfspace([0, OUT_Y0 + FRONT_T, 0], [0, 0, -1], [0, -1, 0]);  halfspace([0, OUT_Y0 + FRONT_T, Z_TOP], [0, 0, 1], [0, -1, 0]);
}
module hatch_wedges() {
    halfspace([LW_X, IN_Y, 0], [-1, 0, 0], [0, 1, 0]);  halfspace([IN_X, IN_Y, 0], [1, 0, 0], [0, 1, 0]);
    halfspace([0, IN_Y, 0], [0, 0, -1], [0, 1, 0]);  halfspace([0, IN_Y, Z_TOP], [0, 0, 1], [0, 1, 0]);
}
// 板の素（外面まで伸ばした直方体 − 楔）∩ 丸い外形
module slab_floor() intersection() { env(); difference() { translate([OUT_X0, OUT_Y0, -FLOOR_T]) cube([OUT_X1 - OUT_X0, OUT_Y1 - OUT_Y0, FLOOR_T]); floor_wedges(); } }
module slab_top()   intersection() { env(); difference() { translate([OUT_X0, OUT_Y0, Z_TOP]) cube([OUT_X1 - OUT_X0, OUT_Y1 - OUT_Y0, TOP_T]); top_wedges(); } }
module slab_lwall() intersection() { env(); difference() { translate([OUT_X0, OUT_Y0, -FLOOR_T]) cube([WALL, OUT_Y1 - OUT_Y0, Z_TOP + TOP_T + FLOOR_T]); lwall_wedges(); } }
module slab_rwall() intersection() { env(); difference() { translate([IN_X, OUT_Y0, -FLOOR_T]) cube([WALL, OUT_Y1 - OUT_Y0, Z_TOP + TOP_T + FLOOR_T]); rwall_wedges(); } }
module slab_front() intersection() { env(); difference() { translate([OUT_X0, OUT_Y0, -FLOOR_T]) cube([OUT_X1 - OUT_X0, FRONT_T, Z_TOP + TOP_T + FLOOR_T]); front_wedges(); } }
module slab_hatch() intersection() { env(); difference() { translate([OUT_X0, IN_Y, -FLOOR_T]) cube([OUT_X1 - OUT_X0, HATCH_T, Z_TOP + TOP_T + FLOOR_T]); hatch_wedges(); } }

// ---- 左の壁: ジャックの丸い口・ReSpeaker の USB-C の盲ポケット ----
JACK_C = [LW_X - WALL / 2, RSP_Y1 + 2.485, RSP_Z + 6.502];   // 筒の軸（respeaker_lite: 面から 2.485・下から 6.502）
JACK_D = 7.0;                                                 // 口の径（プラグの胴 φ5.5〜6 ＋ 逃げ・AI の値）
USB1_POCKET = [LW_X - 0.9, RSP_Y1 - 0.2, RSP_Z + 23.0, 0.9 + 0.01, 3.9, 9.7];   // [x0, y0, z0, dx, dy, dz] 壁の内面に 0.9 の盲ポケット（USB1 の殻が 0.6 入る）
JACK_COVER_POCKET = [LW_X - 0.7, RSP_Y1 + 3.14 - 0.3, RSP_Z + 3.65 - 0.3, 0.7 + 0.01, 7.52 - 3.14 + 0.6, 8.9 - 3.65 + 0.6];   // ジャックの金属カバー（面から 3.14〜7.52・下から 3.65〜8.9・板の端から 0.68 出る）の盲ポケット 0.7
module p_lwall() difference() {
    union() { slab_lwall(); tc_press(); fasten_lwall(); }   // 押さえ・柱・棚は壁と一体
    translate(JACK_C) rotate([0, 90, 0]) { cylinder(d = JACK_D, h = WALL + 2, center = true, $fn = 48); translate([0, 0, -WALL / 2 - 0.01]) cylinder(d1 = JACK_D + 2 * PORT_BEV, d2 = JACK_D, h = PORT_BEV, $fn = 48); }   // 口＋外のベベル（外面は −X）
    translate([USB1_POCKET[0], USB1_POCKET[1], USB1_POCKET[2]]) cube([USB1_POCKET[3], USB1_POCKET[4], USB1_POCKET[5]]);
    translate([JACK_COVER_POCKET[0], JACK_COVER_POCKET[1], JACK_COVER_POCKET[2]]) cube([JACK_COVER_POCKET[3], JACK_COVER_POCKET[4], JACK_COVER_POCKET[5]]);
    lwall_icon_cut();
}
// ---- 右の壁: XIAO の USB-C の口（殻の大きさ＋ベベルの 1 段。殻が壁を貫通し、口の面は外面の 0.8 裏。プラグのモールドは外面の外で止まる）----
XUSB_C = [IN_X + WALL / 2, RSP_Y1 + xiao_usb_yz()[0], RSP_Z + xiao_usb_yz()[1]];
XUSB_SZ = [xiao_usb_sz()[0] + 0.6, xiao_usb_sz()[1] + 0.6];   // [Y, Z] = [3.86, 9.54] 殻 ＋ 片側 0.3（🔴 2026-09-05 まで胴 6.5 × 12.5 ＋ 0.5 の 7.5 × 13.5 で開けていた）
XUSB_REL_Z0 = 14.5;   // 殻の逃げの下端（殻が居るのは Z 15.03 から上・余裕 0.53）
module xusb_shell_relief() translate([IN_X - 0.01, XUSB_C[1] - XUSB_SZ[0] / 2, XUSB_REL_Z0]) cube([XIAO_FACE_X + 0.15 - IN_X + 0.01, XUSB_SZ[0], XUSB_C[2] - XUSB_REL_Z0]);   // 壁を上から降ろすとき殻が通る道: 口の下を内面から殻の面 ＋ 0.15（85.704）まで抜く。外に皮 0.65 残る
module p_rwall() difference() {
    union() { slab_rwall(); fasten_rwall(); }
    port_cut(XUSB_C, XUSB_SZ[0], XUSB_SZ[1], WALL, "x");
    xusb_shell_relief();
    rwall_icon_cut();
}
// ---- フロント: OLED の窓（黒枠 61 × 38.5 ＋ 横 1.0・縦 0.15・下辺の張り出し）・マイクのヒゲ ----
WIN_CL_X = 1.0; WIN_CL_Z = 0.15;   // 🔒 2026-09-03 の値
WSK_L = 6.0; WSK_W = 1.0; WSK_ANG = 4; WSK_CH = 0.5;   // v4: 6.0 × 1.0・3 本・3.6 間隔・±4°
WSK_R = 0.4;   // ヒゲの外面のベベルの丸み
module wsk_plate(l, w, y) translate([-l / 2, y, -w / 2]) rotate([90, 0, 0]) spk_obr(l, w, 0.01);   // 小判の薄い板（X-Z 面・y の位置）
// ヒゲの外面の断面: 外面で ch 広がり、奥へ ch で 0 になる曲線。(0,ch)→(ch,0) を制御点 ((1−k)ch/2, 同) で結ぶ 2 次ベジエ＝内へ吸い込むように反る（k=WSK_R 0.4）。🔴 2026-09-05 まで凸の 1/4 円で描いていて顔が違った（ユーザー「猫ヒゲの形状も違う」）
function bev_pts(c, k, n = 10) = [for (i = [0 : n]) let (t = i / n, p = (1 - k) * c / 2) [2 * t * (1 - t) * p + t * t * c, (1 - t) * (1 - t) * c + 2 * t * (1 - t) * p]];   // [奥行き, 広がり] の列
module whisker(c, ang) translate([c[0], OUT_Y0, c[2]]) rotate([0, ang, 0]) {   // 原点 = 板の外面
    hull() { wsk_plate(WSK_L + 2 * WSK_CH, WSK_W + 2 * WSK_CH, -0.5); for (q = bev_pts(WSK_CH, WSK_R)) wsk_plate(WSK_L + 2 * q[1], WSK_W + 2 * q[1], q[0]); }   // 外面の反ったベベル
    hull() { wsk_plate(WSK_L, WSK_W, WSK_CH); wsk_plate(WSK_L, WSK_W, FRONT_T + 1); }   // 内面まで貫く小判のスリット
}
WIN_CR = WIN_CL_Z;   // 窓の角の丸み。四角いガラスを隙間で囲むと角の丸みは隙間の小さい方（縦 0.15）まで。🔴 2026-09-05 まで角の立った四角で切っていた（ユーザー「液晶のベベルの違い」）
module win_rr2d(g = 0) offset(r = g, $fn = 32) hull() for (a = [0, 1], b = [0, 1]) translate([oled_glass_x() - WIN_CL_X + WIN_CR + a * (oled_glass()[0] + 2 * WIN_CL_X - 2 * WIN_CR), oled_glass_y() - WIN_CL_Z + WIN_CR + b * (oled_glass()[1] + 2 * WIN_CL_Z - 2 * WIN_CR)]) circle(r = WIN_CR, $fn = 24);   // 窓の輪郭（OLED 局所 XY・g で外へ太らせる）
module win_bulge2d(g = 0) offset(r = g + WIN_CL_Z, $fn = 24) oled_bulge_2d(1.0);   // 下辺の張り出しの逃げ（台形・角は隙間ぶん丸い。1.0 は窓の中へ重ねる量）
module win_piece(k, g) { if (k == 0) win_rr2d(g); else win_bulge2d(g); }
WIN_Z_OUT = 8.5 + FRONT_T - FRONT_DY;   // OLED の局所 z で板の外面（背面 8.5 ＋ 板 2.0 − 後ろへ寄せた 1.0 = 9.5）
module p_front() difference() {
    union() { slab_front(); front_ears(); front_ears_low(); }   // 板は Y −1.8〜1（厚み 2.8・内面 Y 1.0）。耳は上 2・下 2
    at_oled() {   // 局所 z 8.5 が板の内面・10.5 が外面
        translate([0, 0, 8.5 - FRONT_DY - 1]) linear_extrude(FRONT_T + 2) { win_rr2d(); win_bulge2d(); }   // 窓（黒枠＋隙間・角丸 WIN_CR）と下辺の張り出しの逃げ（貫通）
        for (k = [0, 1]) hull() {   // 外面のベベル 45°（PORT_BEV）: 輪郭を外へ向かって太らせる。角丸も一緒に太るので外面の角は WIN_CR + PORT_BEV の丸みになる。
            translate([0, 0, WIN_Z_OUT - PORT_BEV]) linear_extrude(0.01) win_piece(k, 0);   //   窓と張り出しの和は凸でないので、凸な部品ごとに hull する（まとめて hull すると張り出しの逃げが埋まる）
            translate([0, 0, WIN_Z_OUT + 1.0]) linear_extrude(0.01) win_piece(k, PORT_BEV + 1.0);
        }
    }
    for (m = [[RSP_X + respeaker_L() - (4.162 + 6.812) / 2, +1], [RSP_X + respeaker_L() - (75.162 + 77.812) / 2, -1]])   // マイク U4（右・X 78.5）・U5（左・X 7.5）。ヒゲは外へ 1.0 寄せる
        for (i = [-1, 0, 1]) whisker([m[0] + m[1] * 1.0, 0, RSP_Z + (15.252 + 18.752) / 2 + i * 3.6], -m[1] * i * WSK_ANG);   // 扇は外（顔の外側）へ開く: 上のひげは外側の端が上がる。🔴 2026-09-05 まで符号が逆で内へ開いていた（ユーザー「角度だよ」）
}
// ---- 刻印（外面に 1.0 彫る。大きさは口の長辺の 7 割 × 1.5、口の縁から 1.5。向きの正: スパナは口が右上・稲妻は右上から左下・ヘッドホンは帯が上）----
ICON_D = 1.0; ICON_GAP = 1.5; ICON_K = 1.5; ICON_R = 0.20; ICON_BOLT_K = 1.3; ICON_HP_SW = 2.0; SVC_MIN_W = 0.5;
module icon_round(r) offset(r = -r) offset(r = r) offset(r = r) offset(r = -r) children();
function icon_r_cap(w) = min(ICON_R * ICON_K, 0.4 * w);   // 線画は線幅の 4 割まで
// スパナ（右の壁・XIAO の USB-C の口の後ろ側）。外から見て +Y が右
ICON_WR_H = 4.87 * ICON_K;
module icon_wrench2d() { sc = ICON_WR_H / icon_wrench_u_span(); icon_round(ICON_R * ICON_K) scale(sc) icon_wrench_u(); }
ICON_WR_C = [XUSB_C[1] + XUSB_SZ[0] / 2 + PORT_BEV + ICON_GAP + ICON_WR_H / 2, XUSB_C[2]];   // [Y, Z]
module rwall_icon_cut() translate([IN_X + WALL - ICON_D, ICON_WR_C[0], ICON_WR_C[1]]) rotate([90, 0, 90]) linear_extrude(ICON_D + 1.0) icon_wrench2d();
// 稲妻（ハッチ・Type-C の口の +X 側 = 後ろから見て口の左。口は左端なので右には置けない）。2D の x → +X。後ろから見ると右が −X なので鏡に見え、右上から左下になる
TC_ICON_H = 0.7 * 9.54;   // 口の長辺（縦 9.54 = TC_PORT_SZ[1]。定義が後ろにあるので数字で）の 7 割
module icon_bolt(h) { s = h / 6; polygon([[-0.9, 3], [1.3, -0.4], [0.1, -0.4], [0.9, -3], [-1.3, 0.4], [-0.1, 0.4]] * s); }
function tc_icon_w() = TC_ICON_H * ICON_K * ICON_BOLT_K * 2.6 / 6;
module icon_bolt_big() icon_round(ICON_R * ICON_K * ICON_BOLT_K) icon_bolt(TC_ICON_H * ICON_K * ICON_BOLT_K);
function tc_icon_c() = [TC_PORT_C[0] + TC_PORT_SZ[0] / 2 + PORT_BEV + ICON_GAP + tc_icon_w() / 2, TC_PORT_C[2]];   // [X, Z]（関数なら定義の順序に依らない）
module hatch_icon_cut() translate([tc_icon_c()[0], IN_Y + HATCH_T + 1.0, tc_icon_c()[1]]) rotate([90, 0, 0]) linear_extrude(ICON_D + 1.0) icon_bolt_big();
// ヘッドホン（左の壁・ジャックの口の後ろ側 = 外から見て口の左）。外から見て −Y が右なので 2D を鏡にする
JACK_ICON_H = 0.7 * JACK_D * ICON_K;
JACK_ICON_SC = JACK_ICON_H / icon_headphone_size()[1];
JACK_ICON_W = JACK_ICON_SC * icon_headphone_size()[0];
JACK_ICON_C = [JACK_C[1] + JACK_D / 2 + PORT_BEV + ICON_GAP + JACK_ICON_W / 2, JACK_C[2]];   // [Y, Z]
module icon_headphone2d() { sw = max(icon_headphone_sw() * ICON_HP_SW, SVC_MIN_W / JACK_ICON_SC); icon_round(icon_r_cap(sw * JACK_ICON_SC)) scale(JACK_ICON_SC) icon_headphone(sw); }
module lwall_icon_cut() translate([LW_X - WALL - 1.0, JACK_ICON_C[0], JACK_ICON_C[1]]) rotate([90, 0, 90]) linear_extrude(ICON_D + 1.0) mirror([1, 0]) icon_headphone2d();

// ---- 天板: つまみの台座と抜き・会話ボタンの台座と口・スピーカーの座とハニカムのグリル ----
SPK_LIFT = 0.9; SPK_CL = 0.3;       // 座の深さ（天板の内面から）・座の逃げ（片側）
SPK_REL = 0.4 + SPK_LIFT;           // 振動板の逃げの深さ（内面から 1.3）: 振動板の上の空気の層 0.4 ＋ 座で持ち上げた 0.9。天板の残りは 1.2
SPK_HEX_AF = 2.2; SPK_HEX_WALL = 0.6;   // ハニカム: 六角の二面幅 2.2・穴どうしの肉 0.6（ピッチ 2.8・開口率 62%）。2026-09-05 まで肉 1.2 で小判に切り抜いていて目が粗く縁の六角が欠けていた（ユーザー指摘）
SPK_RIM_H = 0.8; SPK_RIM_T = 0.6;   // 位置出しの縁: 天板の裏に立つ小判の囲い（高さ 0.8・肉 0.6・逃げは座と同じ SPK_CL）。両面テープで貼るときにここへ落とし込んで位置を出す
module spk_obr(l, w, h) hull() for (sx = [w / 2, l - w / 2]) translate([sx, w / 2, 0]) cylinder(d = w, h = h, $fn = 48);
// ハニカムの穴: 振動板 14 × 8 の範囲に六角を千鳥で並べる（偶数段 nx+1 個・奇数段は半ピッチ狭いので 1 個少ない）。小判で切り抜かず、六角は欠けさせない。平らな辺が左右（X）を向く
module spk_grille() { pitch = SPK_HEX_AF + SPK_HEX_WALL; w = spk_dia()[0]; d = spk_dia()[1]; rh = pitch * 0.866;
    nx = floor(w / pitch + 1e-6); nxo = max(0, floor((w - pitch) / pitch + 1e-6)); ny = floor(d / rh + 1e-6);
    for (j = [0 : ny]) { n = (j % 2) ? nxo : nx;
        for (i = [0 : n]) translate([SPK_AT[0] - n * pitch / 2 + i * pitch, SPK_AT[1] - ny * rh / 2 + j * rh, Z_TOP - 1]) rotate([0, 0, 30]) cylinder(d = SPK_HEX_AF / cos(30), h = TOP_T + 2, $fn = 6); } }
module spk_rim() translate([SPK_AT[0] - spk_l() / 2 - SPK_CL - SPK_RIM_T, SPK_AT[1] - spk_w() / 2 - SPK_CL - SPK_RIM_T, Z_TOP - SPK_RIM_H]) difference() {
    spk_obr(spk_l() + 2 * (SPK_CL + SPK_RIM_T), spk_w() + 2 * (SPK_CL + SPK_RIM_T), SPK_RIM_H + 0.01);
    translate([SPK_RIM_T, SPK_RIM_T, -1]) spk_obr(spk_l() + 2 * SPK_CL, spk_w() + 2 * SPK_CL, SPK_RIM_H + 3);
}
module p_top() difference() {
    union() {
        slab_top();
        at_knob() knob_station_add();
        at_btn()  btn3_station_add();
        pb_mount();   // PowerBoost のダボ（天板と一体・2026-09-05）
        oled_brackets();   // OLED の上の 2 穴を受ける L の足（天板から下ろす）
        rsp_press();       // ReSpeaker の板の頭を押さえる羊羹とマッチ棒
        tgl_cradle();      // トグルの胴の受け（ハッチの上を留める）
        spk_rim();    // スピーカーの位置出しの縁
    }
    at_knob() knob_station_cut();
    tgl_term_notch();   // トグルの端子がつまみの台座の後ろの縁に入る分の欠き（2026-09-05）
    at_btn()  btn3_station_cut();
    top_screw_cuts();
    translate([SPK_AT[0] - spk_l() / 2 - SPK_CL, SPK_AT[1] - spk_w() / 2 - SPK_CL, Z_TOP - 0.01]) spk_obr(spk_l() + 2 * SPK_CL, spk_w() + 2 * SPK_CL, SPK_LIFT + 0.01);   // 座（内面から 0.9）
    translate([SPK_AT[0] - (spk_dia()[0] + 1) / 2, SPK_AT[1] - (spk_dia()[1] + 1) / 2, Z_TOP - 0.01]) spk_obr(spk_dia()[0] + 1, spk_dia()[1] + 1, SPK_REL + 0.01);   // 振動板の逃げ（小判 15 × 9・内面から 1.3）
    spk_grille();   // ハニカムのグリル（天板を貫通）
}
// ---- ハッチ: Type-C の口・トグルの穴・電池の口 ----
TC_PORT_C = [TC_AT[0] + tc_size()[2] + tc_conn()[2] / 2, IN_Y + HATCH_T / 2, TC_AT[2] + tc_size()[0] / 2];   // 板の表 ＋ 胴の高さの半分・板の長さの中央（4.92, ・, 10.75）
TC_PORT_SZ = [3.86, 9.54];   // [X, Z]（殻 3.26 × 8.94 ＋ 片側 0.3）。基板が縦なので口は縦長（🔴 2026-09-05 まで横長に開けていた・ユーザー指摘）
module p_hatch() difference() {
    union() { slab_hatch(); sw4_hatch_rim(); hatch_claws(); hatch_ears_top(); hatch_ears_low(); }   // 縁（溝の床〜内面・つば・爪）・下の爪 2 つ・耳 3 つはハッチと一体
    port_cut(TC_PORT_C, TC_PORT_SZ[0], TC_PORT_SZ[1], HATCH_T, "y");
    battery_port_cut4(); sw4_band_cut(); sw4_lock_cut(); sw4_mag_window();   // 電池の口・蓋の彫り込み・ロックのねじとナット・磁石の窓
    hatch_icon_cut();
    translate([TC_AT[0] - 0.25, IN_Y - 1, TC_AT[2] - 0.25]) cube([tc_size()[2] + 0.5, 1 + (TC4_Y1 - IN_Y) + 0.25, tc_size()[0] + 0.5]);   // Type-C 基板の後縁を受けるスリット（板 1.6 ＋ 片側 0.25・深さ 0.4 ＋ 0.25）
    at_tgl() translate([0, 0, -1]) mts102_hole(HATCH_T + 2);   // 局所 +z がハッチの外（🔴 2026-09-05 まで −z 側に切っていて穴が内側に居た）
}
// ハブ基板の留め（v4 §5: M3×8 ×4・頭は床の裏のザグリ・ナットは基板の上）: 床から柱 φ7.0（高さ = 板の下面 2.5）、通し φ3.2、裏の座ぐり φ6.0 × 2.0
HUB_HOLES_W = [for (sx = [-1, 1], sy = [-1, 1]) [HUB_AT[0] + 37.0 + sx * 34.0, HUB_AT[1] + 26.0 + sy * 23.0]];   // hub_board_parts: 外形 74 × 52・穴の間隔 68 × 46
HUB_POST_D = 8.0; HUB_SCR_D = 3.4; HUB_NUT_AF = 5.8; HUB_NUT_T = 2.6; HUB_FOOT_D = 10.0; HUB_FOOT_T = 0.6;   // ゴム足の座 φ10 × 0.6 の中にナットが隠れる（🔒 v2 の形・CASE-V2.md 736 行。ユーザー 2026-09-05「ゴム足の話から考えてネジは上から」「忘れてるだけだ」）   // 🔒 ユーザー 2026-09-05「ここが丸である利点はなんだ」→ ナットを床の裏の六角に埋め、ねじは基板の上から（二面幅 5.5 + 0.3・厚 2.4 + 0.2。v3 の M3_NAF/M3_NT と同じ数）。柱は 7.0 → 8.0（六角の角 6.70 に対して肉 0.65）   // 🔴 2026-09-05 実機: 3.2 / 6.0 / 1.0 は M3 が通らず頭も沈まなかった（基板の穴径 3.2 を写した AI のミス）。v4 case_base の M3_CLEAR 3.4・M3_CB 6.4・M3_HEAD_H 2.2 に戻す。座ぐりは床 2.0 を抜けて柱に 0.2 入る
module hub_posts() for (h = HUB_HOLES_W) translate([h[0], h[1], -0.01]) cylinder(d = HUB_POST_D, h = HUB_AT[2] + 0.01, $fn = 32);
module hub_screw_cuts() for (h = HUB_HOLES_W) translate([h[0], h[1], 0]) { translate([0, 0, -FLOOR_T - 1]) cylinder(d = HUB_SCR_D, h = FLOOR_T + HUB_AT[2] + 2, $fn = 24); translate([0, 0, -FLOOR_T - 0.01]) rotate([0, 0, 30]) cylinder(d = HUB_NUT_AF / cos(30), h = HUB_NUT_T + 0.01, $fn = 6); translate([0, 0, -FLOOR_T - 0.01]) cylinder(d = HUB_FOOT_D, h = HUB_FOOT_T + 0.01, $fn = 48); }   // 通し φ3.4 ＋ 床の裏の六角（ナット）＋ ゴム足の座。床 2.0 を抜けて柱に 0.6 入る

// ---- ハッチを箱に留める作り（🔒 v3 2026-08-22 ユーザーの絵「下＝爪、上＝ナット」: 床に掛けてから上を倒し、トグルのねじ部に通してナットで止める）----
//   下: ハッチの内面の下端から脚が下り、その唇が床の後ろの帯に埋めたバーの下へ −Y に滑り込む（v3/v4 の爪。X 12〜20・66〜74）
//   上: トグルの胴を天板から下ろした受け（両側の壁と、端子の両脇の前の当て）で X と −Y に固定し、ハッチの外のナットで胴にハッチを締める。
//       胴は下と後ろが開いた受けに、ハッチを倒し込む弧で入る。爪だけでは真後ろへ引く動きを止めないが、上の耳 2 本と下の耳 1 本のねじで柱に留まるので、組んだ状態では動かない（2026-09-06 整理）
CLAW_X = [[12, 20], [66, 74]];                                              // 爪の X（2 つ）
CLAW_STRIP_Y0 = HUB_AT[1] + 52.0 + 0.5;                                    // 床の帯の前縁（ハブの後端 67.9 ＋ 0.5）
CLAW_STRIP_H = 2.5;
CLAW_BAR_Y0 = IN_Y - 4.0; CLAW_BAR_Y1 = IN_Y - 2.0; CLAW_BAR_Z0 = 1.5;       // バー（Y 73.25〜75.25・Z 1.5〜2.5）。その後ろ（〜77.25）は脚が通る
CLAW_LIP_T = 0.8; CLAW_LIP_L = 3.0; CLAW_LEG_T = 1.0; CLAW_CL = 0.2;         // 唇の厚み／長さ（−Y へ）／脚の厚み／隙間
module hatch_strip() translate([RSP_RIB_X0, CLAW_STRIP_Y0, -0.01]) cube([RSP_RIB_X1 - RSP_RIB_X0, IN_Y - CLAW_STRIP_Y0, CLAW_STRIP_H + 0.01]);   // 床の後ろの帯（X 8〜76.35）
module claw_pockets() for (cx = CLAW_X) {
    translate([cx[0], CLAW_BAR_Y0 - 1.0, 0.3]) cube([cx[1] - cx[0], IN_Y - CLAW_BAR_Y0 + 2, CLAW_BAR_Z0 - 0.3]);          // 唇の道（バーの下・床の皮 0.3 を残す）
    translate([cx[0], CLAW_BAR_Y1, CLAW_BAR_Z0 - 0.01]) cube([cx[1] - cx[0], IN_Y - CLAW_BAR_Y1 + 1, CLAW_STRIP_H]);      // 脚の道（バーの後ろ）
}
module hatch_claws() for (cx = CLAW_X) {
    translate([cx[0] + CLAW_CL, IN_Y - CLAW_LEG_T, 0.3 + CLAW_CL]) cube([cx[1] - cx[0] - 2 * CLAW_CL, CLAW_LEG_T + 0.01, CLAW_STRIP_H - 0.3 - CLAW_CL + 0.01]);   // 脚（内面に沿って下りる）
    translate([cx[0] + CLAW_CL, CLAW_BAR_Y0 + CLAW_CL, 0.3 + CLAW_CL]) cube([cx[1] - cx[0] - 2 * CLAW_CL, IN_Y - (CLAW_BAR_Y0 + CLAW_CL), CLAW_LIP_T]);          // 唇（脚からバーの下を −Y へ・バーの前端まで）
}
CRADLE_T = 1.6; CRADLE_CL = 0.3; CRADLE_Z0 = 41.0; CRADLE_Y1 = IN_Y - 2.75;   // 受け: 壁の厚み・胴との隙間・下端（胴の下端 36.85 の 4 上・胴の上 8.9 を抱く）・後端（ハッチの内面の縁とリブの手前）
CRADLE_GAP = 2.2;   // 前の当ての、端子の両脇の切れ目（軸から ±2.2。端子 1.2 と、その両脇を下りる線 2 本が通る）
module tgl_cradle() { x0 = TGL_AT[0] - mts102_d() / 2 - CRADLE_CL; x1 = TGL_AT[0] + mts102_d() / 2 + CRADLE_CL; yf = IN_Y - mts102_deep() + mts102_pin_h() - CRADLE_CL;   // 胴の前面 65.25 の 0.3 前
    for (x = [x0 - CRADLE_T, x1]) translate([x, yf - CRADLE_T, CRADLE_Z0]) cube([CRADLE_T, CRADLE_Y1 - (yf - CRADLE_T), Z_TOP + 0.01 - CRADLE_Z0]);   // 両側の壁
    for (r = [[x0 - CRADLE_T, TGL_AT[0] - CRADLE_GAP], [TGL_AT[0] + CRADLE_GAP, x1 + CRADLE_T]]) translate([r[0], yf - CRADLE_T, CRADLE_Z0]) cube([r[1] - r[0], CRADLE_T, Z_TOP + 0.01 - CRADLE_Z0]);   // 前の当て（端子の両脇）
}
module floor_bosses() for (p = POSTS_B) translate([p[0], p[1], -0.01]) cube([POST_W, post_dy(p), FLOOR_BOSS + 0.01]);   // 耳の下の台（柱と同じ足跡）
module p_floor() difference() { union() { slab_floor(); tc_seat(); hub_posts(); rsp_seat(); oled_rib(); hatch_strip(); floor_bosses(); } floor_screw_cuts(); hub_screw_cuts(); claw_pockets(); }   // Type-C の受け・ハブの柱・ReSpeaker の座・OLED のリブ・ハッチの爪の帯は床と一体
// 刷る部品ごとの色（同じ色 = 同じ部品として刷る）
module skin(a = 0.5) { color("#e0a040", a) p_floor(); color("#c9d0d8", a) p_top(); color("#4a90d9", a) p_lwall(); color("#4a90d9", a) p_rwall(); color("#9b59b6", a) p_front(); color("#27ae60", a) p_hatch(); ribs(); }   // リブ込み（skin / all で見える）

// ============================================================
// 締結（v4 §5 の流儀: 樹脂にねじを切らない・貫通＋ナット。ビスは M2×15 / M2×6 / M2×8・ナット M2）
// ============================================================
NUT_AF = 4.20; NUT_T = 1.8; SCR_D = 2.5; SCR_CB = 4.4; SCR_CBT = 1.6;   // v4 case_base の値（ナット厚 1.8・通し φ2.5・座ぐり φ4.4 × 1.6）。🔴 NUT_AF は 4.10 → 4.20（2026-09-05 実機で 4.10＝ポケット 4.20 にナットが入らず、PRINT.md §2「六角は呼び + 0.3」に戻した。hex_pocket が +0.1 するので 4.30）
POST_W = 6.0;                          // 柱の一辺（v4 BOSS 7.0。OLED の板の端 X 8.0 との隙間を 0.3 取るため 6.0）
POST_W_F = 5.0;       // 前の上の柱（耳の柱）の幅。OLED の L の足（X 7.0〜13.0 / 73.1〜79.1）まで 0.3（v4 の耳 4.96 と同じ理由・2026-09-05）
POST_D_F_T = 8.0;     // 前の上の柱の奥行き（Y 1.0〜9.0・v4 の耳 2〜10）。ナット（二面幅を Y に）の前後に肉 1.9
POST_T_H_F = 10.0;    // 前の上の柱の高さ（裾 Z 37.25 = ReSpeaker の板の頭 36.5 の 0.75 上）
POST_B_H = 12.0;                       // 下の柱の高さ（v4 BOSS_B_H 12・M2×15 ＝ 床 2 ＋ 13）
POST_T_H = 9.0;                        // 後ろの上の柱の高さ（耳の下から）。12 → 9: ハッチの耳のぶん 3.2 下がった柱の裾が、蓋の縁と床の板の左端（Z 〜37.5）に入ったため（裾 38.25）
EAR_T = 3.2;                           // フロント板の耳の厚み（v4 耳 3.2・M2×8）
FLOOR_BOSS = 1.0;                      // 下の柱 3 本の耳の下に足す床の台（🔒 ユーザー 2026-09-05「耳の下に 1.0 の台を床に足す」: ねじの座ぐり 1.6 が床 2.0 に残す底 0.4 を 1.4 にする。耳は 1.0 上がり、柱は 1.0 短い。ねじは M2×15 のまま）
// 下の柱 3 本 [x0, y0]（左前・右前・右後ろ。左後ろは Type-C 基板の席）
FY_IN = OUT_Y0 + FRONT_T;   // フロント板の内面 Y 1.0
POSTS_B = [[LW_X, FY_IN], [IN_X - POST_W, FY_IN], [IN_X - POST_W, IN_Y - POST_W]];
// 上の柱 4 本 [x0, y0, 耳の有無]（後ろ 2 本は天板 → 柱、前 2 本は 天板 → フロントの耳 → 柱）
POSTS_T = [[LW_X, IN_Y - POST_W, true], [IN_X - POST_W, IN_Y - POST_W, true], [LW_X, FY_IN, true], [IN_X - POST_W_F, FY_IN, true]];   // 4 本とも耳付き: 前 2 はフロントの上の耳、後ろ 2 はハッチの上の耳（🔒 ユーザー 2026-09-05「同じ仕組みでハッチにも羽根を」）
module hex_pocket(af, t) rotate([0, 0, 30]) cylinder(d = (af + 0.1) / cos(30), h = t, $fn = 6);
POST_D_FRONT = 4.5;   // 前の下の柱の奥行き（フロント板の内面 Y 1.0 から 5.5。ReSpeaker のボタン K1 が Y 5.6 まで来る）
function post_front(p) = (p[1] == FY_IN);
function post_dy(p) = post_front(p) ? (p[2] == true ? POST_D_F_T : POST_D_FRONT) : POST_W;
function post_w(p) = (post_front(p) && p[2] == true) ? POST_W_F : POST_W;   // 前の上の柱（フロントの耳付き）だけ細い
module post_b(p) difference() {   // 下の柱: 床から POST_B_H。頭に上向きのナットのポケット・通し。前の 2 本はフロントの下の耳（EAR_T）のぶん床から浮く（v4 front_ears_low・2026-09-05 ユーザー「下も同じように止められないんですか」）
    z0 = EAR_T + FLOOR_BOSS;   // 3 本とも 床の台 1.0 ＋ 耳 3.2 のぶん床から浮く: 前 2 はフロントの下の耳、後ろ右はハッチの下の耳（後ろ左は柱が無い）
    translate([p[0], p[1], z0]) cube([POST_W, post_dy(p), POST_B_H - z0]);
    translate([p[0] + POST_W / 2, p[1] + post_dy(p) / 2, -1]) cylinder(d = SCR_D, h = POST_B_H + 2, $fn = 24);
    translate([p[0] + POST_W / 2, p[1] + post_dy(p) / 2, POST_B_H - NUT_T]) hex_pocket(NUT_AF, NUT_T + 1);
}
POST_T_SKIN = 1.6;   // 上の柱: ナットの上に残す肉。ねじは上から締めるので、ナットはこの肉を掴む（🔴 上向きのポケットだと天板＋ねじ＋ナットが一緒に上へ抜ける。ユーザー 2026-09-05「前にナットと天板が上に抜けた」）
module post_t(p) difference() {   // 上の柱: 天井から下がる。耳付きなら耳の厚みだけ低い。ナットは横差しの溝（上に肉 POST_T_SKIN）
    zt = Z_TOP - (p[2] ? EAR_T : 0); h = (post_front(p) && p[2]) ? POST_T_H_F : POST_T_H; w = post_w(p); d = post_dy(p);
    cx = p[0] + w / 2; cy = p[1] + d / 2;
    translate([p[0], p[1], zt - h]) cube([w, d, h]);
    translate([cx, cy, zt - h - 1]) cylinder(d = SCR_D, h = h + 2, $fn = 24);
    if (post_front(p)) {   // 前の柱（幅 5.0）: 溝は箱の内側の X の面へ開く。二面幅を Y に（通路の壁が回り止め）。外側は壁が受ける（v4 ear_col）
        sx = (p[0] < IN_X / 2) ? 1 : -1;
        hull() for (k = [0, sx * 10]) translate([cx + k, cy, zt - POST_T_SKIN - NUT_T]) rotate([0, 0, -30]) hex_pocket(NUT_AF, NUT_T);
    } else {      // 後ろの柱: 溝は −Y（前・箱の内側）へ開く
        hull() for (k = [0, -10]) translate([cx, cy + k, zt - POST_T_SKIN - NUT_T]) hex_pocket(NUT_AF, NUT_T);
    }
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
module top_screw_cuts() for (p = POSTS_T) translate([p[0] + post_w(p) / 2, p[1] + post_dy(p) / 2, 0]) {
    translate([0, 0, Z_TOP - 1]) cylinder(d = SCR_D, h = TOP_T + 2, $fn = 24);
    translate([0, 0, Z_TOP + TOP_T - SCR_CBT]) cylinder(d = SCR_CB, h = SCR_CBT + 0.01, $fn = 32);
}
// フロント板の耳 2 つ（天板と前の耳柱に挟まれる・通し付き）
// フロントの下の耳 2 つ（床と前の下の柱に挟まれる・通し付き）。床の裏からの M2×15 が 床 2 ＋ 耳 3.2 ＋ 柱 8.8 を通ってナットへ
module front_ears_low() for (p = [POSTS_B[0], POSTS_B[1]]) difference() {
    translate([p[0], FY_IN - 0.01, FLOOR_BOSS]) cube([POST_W, post_dy(p) + 0.01, EAR_T]);   // 床の台の上
    translate([p[0] + POST_W / 2, FY_IN + post_dy(p) / 2, -1]) cylinder(d = SCR_D, h = FLOOR_BOSS + EAR_T + 2, $fn = 24);
}
// ハッチの耳: 上 2 つ（天板と後ろの上の柱に挟まれる・M2×8）と下 1 つ（床と後ろ右の下の柱に挟まれる・M2×15）。左下は Type-C 基板の席で柱が無いので爪だけ
module hatch_ears_top() for (p = [POSTS_T[0], POSTS_T[1]]) difference() {
    translate([p[0], p[1], Z_TOP - EAR_T]) cube([post_w(p), post_dy(p) + 0.01, EAR_T]);
    translate([p[0] + post_w(p) / 2, p[1] + post_dy(p) / 2, Z_TOP - EAR_T - 1]) cylinder(d = SCR_D, h = EAR_T + 2, $fn = 24);
}
module hatch_ears_low() { p = POSTS_B[2]; difference() {
    translate([p[0], p[1], FLOOR_BOSS]) cube([POST_W, post_dy(p) + 0.01, EAR_T]);   // 床の台の上
    translate([p[0] + POST_W / 2, p[1] + post_dy(p) / 2, -1]) cylinder(d = SCR_D, h = FLOOR_BOSS + EAR_T + 2, $fn = 24);
} }
module front_ears() for (p = [POSTS_T[2], POSTS_T[3]]) difference() {
    translate([p[0], FY_IN - 0.01, Z_TOP - EAR_T]) cube([post_w(p), post_dy(p) + 0.01, EAR_T]);
    translate([p[0] + post_w(p) / 2, FY_IN + post_dy(p) / 2, Z_TOP - EAR_T - 1]) cylinder(d = SCR_D, h = EAR_T + 2, $fn = 24);
}

// ---- OLED の L（🔒 v4: 天面から L を下ろして OLED の上の 2 穴を中で受ける・フロントにビスを見せない）----
//   足は OLED の裏（Y 4.6）に面で当たる。幅 6.0（前の上の柱まで 0.3）・厚み 3.6（🔒 2026-08-28 2.0 は「ガビガビ」だった）。
//   ビス M2 は Y に通し、ナットは足の後ろの面の六角のポケット。足の下端は穴の 5.5 下
OLED_L_W = 6.0; OLED_L_T = 3.6; OLED_L_BELOW = 5.5;
function oled_back_y() = OLED_AT[1] - (oled_hous_z_top() + 2.5 + dupont_h());   // OLED の板の裏の世界 Y（4.6）
function oled_top_holes_w() = [for (h = oled_mount()) if (h[1] > oled_w() / 2) [OLED_AT[0] + h[0], OLED_AT[2] + h[1]]];   // 上の 2 穴 [X, Z]
module oled_brackets() for (h = oled_top_holes_w()) difference() {
    translate([h[0] - OLED_L_W / 2, oled_back_y(), h[1] - OLED_L_BELOW]) cube([OLED_L_W, OLED_L_T, Z_TOP + 0.01 - (h[1] - OLED_L_BELOW)]);
    translate([h[0], oled_back_y() - 1, h[1]]) rotate([-90, 0, 0]) cylinder(d = SCR_D, h = OLED_L_T + 2, $fn = 24);
    translate([h[0], oled_back_y() + OLED_L_T - NUT_T, h[1]]) rotate([-90, 0, 0]) hex_pocket(NUT_AF, NUT_T + 1);
}
// ---- ReSpeaker の押さえ（🔒 v4 rsp_press4: 羊羹 X 31〜37.5 とマッチ棒 X 50〜52.4。板の頭を 0.3 押す）----
//   Y は板の前面 −0.5 から板の背面まで（v4 は背面 +1.0 だったが、v5 は会話ボタンの台座の前面 Y 10.15 があるので板の背面 10.0 で止める）
RSP_TOP = RSP_Z + respeaker_H(); RSP_PRESS = 0.3;
RSP_BD_Y0 = RSP_Y1 - respeaker_T();   // 板の前面 8.185
YOKAN_X0 = 31.0; YOKAN_W = 6.5; MATCH_X0 = 50.0; MATCH_X1 = 52.4;
module rsp_press() for (x = [[YOKAN_X0, YOKAN_W], [MATCH_X0, MATCH_X1 - MATCH_X0]])
    translate([x[0], RSP_BD_Y0 - 0.5, RSP_TOP - RSP_PRESS]) cube([x[1], RSP_Y1 - (RSP_BD_Y0 - 0.5), Z_TOP + 0.01 - (RSP_TOP - RSP_PRESS)]);
// ---- 床: ReSpeaker の座と OLED の下辺の後ろのリブ（🔒 v4 floor_v4）----
//   座: 板の下端が乗る台（Y 板 ±0.2・高さ RSP_Z）と、その前の唇（厚み 1.8・高さ RSP_Z+3）。X は四隅の柱を避けて 8〜IN_X−8
//   振れ止め: 板の後ろ、ハブの前縁までの間に左右 1 つずつ（左 X 2〜5.7 高さ 5・右 X 80〜84 高さ 6.5）
//   OLED のリブ: 板の裏の 0.2 後ろ・厚み 1.2・高さ 5・中央 25 はフィルムの切り欠き
RSP_SLOT_CL = 0.2; RSP_RIB_X0 = 8.0; RSP_RIB_X1 = IN_X - 8.0;
OLED_RIB_T = 1.2; OLED_RIB_H = 5.0; OLED_RIB_GAP = 0.2; OLED_FILM_W = 23.0;
module rsp_seat() {
    translate([RSP_RIB_X0, RSP_BD_Y0 - RSP_SLOT_CL, -0.01]) cube([RSP_RIB_X1 - RSP_RIB_X0, respeaker_T() + 2 * RSP_SLOT_CL, RSP_Z + 0.01]);          // 台
    translate([RSP_RIB_X0, RSP_BD_Y0 - 2.0, -0.01]) cube([RSP_RIB_X1 - RSP_RIB_X0, 2.0 - RSP_SLOT_CL, RSP_Z + 3.0]);                              // 前の唇
    for (g = [[RSP_X, HUB_AT[0] - 0.3 - RSP_X, 5.0], [80.0, IN_X - 0.35 - 80.0, RSP_Z + 4.0]])
        translate([g[0], RSP_Y1 + 0.3, -0.01]) cube([g[1], HUB_AT[1] - 0.3 - (RSP_Y1 + 0.3), g[2]]);                                                  // 振れ止め
}
module oled_rib() difference() {
    translate([OLED_AT[0] + 2, oled_back_y() + OLED_RIB_GAP, -0.01]) cube([oled_l() - 4, OLED_RIB_T, OLED_RIB_H]);
    translate([OLED_AT[0] + oled_l() / 2 - OLED_FILM_W / 2 - 1, oled_back_y() + OLED_RIB_GAP - 1, -1]) cube([OLED_FILM_W + 2, OLED_RIB_T + 2, OLED_RIB_H + 2]);
}

// ============================================================
// 反り対策のリブ（🔒 v4 _v4_ribs・docs/CASE-V4-OPEN.md「反り対策のリブ」: 板 2.0 の内面に 0/90 の格子。丈 2.0・幅 1.6・ピッチ 8。
//   front は板厚 2.8 なので無し（v4 2026-09-04）。床と天板は v4 でもリブ無し）
//   リブ ＝ 格子 ∩ 内面の空き。空き ＝ 板の輪郭（穴は穴のまま）− 内面から 2.5 の帯に居る物（中身・線・他の板・組む動きの道）を 0.4 太らせた物。
//   細い空き（幅 3 未満）は消し、縁を 0.4 削る（切れ端・薄片を出さない）。中身が動けばリブが勝手に短くなる＝当たりは構成上 0
//   外面を下にして刷るのでリブは上を向く。支柱は要らない
// ============================================================
RIBS_OFF = false; RIB_H = 2.0; RIB_H_FR = 1.0; RIB_W = 1.6; RIB_P = 8.0; RIB_MARG = 0.4; RIB_CLR = 0.5; RIB_OPEN = 1.5; RIB_THIN = 0.4;   // front は丈 1.0（v4 の値。窓の裏は OLED と ReSpeaker で 2.0 は立たない）。🔒 ユーザー 2026-09-05「壁とハッチとフロントにグリッドを」
function rib_h(k) = (k == "front") ? RIB_H_FR : RIB_H;
module rib_slab(k) { b = rib_h(k) + RIB_CLR;
    if (k == "lwall") translate([LW_X, -200, -200]) cube([b, 400, 400]);
    if (k == "rwall") translate([IN_X - b, -200, -200]) cube([b, 400, 400]);
    if (k == "hatch") translate([-200, IN_Y - b, -200]) cube([400, b, 400]);
    if (k == "front") translate([-200, FY_IN, -200]) cube([400, b, 400]);
    if (k == "bridge") translate([-200, -200, BRG_ZB + BRG_T]) cube([400, 400, b]); }   // ブリッジ: 帯（腕・皿）の上面から上へ
module plate_of(k) { if (k == "lwall") p_lwall(); if (k == "rwall") p_rwall(); if (k == "hatch") p_hatch(); if (k == "front") p_front(); if (k == "bridge") bridge(); }
module plates_except(k) { if (k != "lwall") p_lwall(); if (k != "rwall") p_rwall(); if (k != "hatch") p_hatch(); if (k != "front") p_front(); p_floor(); p_top(); }
module innards_except(k) for (n = UNITS) if (n != k) one(n);   // ブリッジ自身を障害物に数えない
module rib_paths(k) { if (k == "lwall") for (t = [0 : 3 : 18]) translate([0, t, 0]) one("tc"); }   // Type-C 基板をハッチ側から後ろへ滑り込ませる道（受けは床・押さえは左の壁）
// 板と一体の物（柱・棚・耳・爪・押さえ）もリブの障害物に数える。板の輪郭に含まれるので放っておくとリブがその上に立ち、柱の頭の横穴（ナット）や耳のねじ穴の端を埋める（🔒 ユーザー 2026-09-05「格子が六角の中に入ってきてない？」）
module plate_features(k) {
    if (k == "lwall") { fasten_lwall(); tc_press(); }
    if (k == "rwall") fasten_rwall();
    if (k == "hatch") { hatch_ears_top(); hatch_ears_low(); hatch_claws(); sw4_hatch_rim(); }
    if (k == "front") { front_ears(); front_ears_low(); }
}
module flat(k) { if (k == "hatch" || k == "front") projection() rotate([-90, 0, 0]) children(); else if (k == "bridge") projection() children(); else projection() rotate([0, 90, 0]) children(); }   // 壁: 2D (x, y) = 世界 (Z, Y) ／ ハッチ・フロント: (X, Z) ／ ブリッジ: (X, Y)
module rib_free2d(k) offset(delta = -RIB_THIN) offset(r = RIB_OPEN) offset(r = -RIB_OPEN) difference() {   // 開きは r（丸）で戻す。delta で戻すと角が元の空きより外へ出て、板や中身に 0.05mm³ 掛かった
    flat(k) plate_of(k);
    offset(r = RIB_MARG) flat(k) intersection() { rib_slab(k); union() { innards_except(k); wires(); plates_except(k); rib_paths(k); plate_features(k); } }
}
// 線は「幅 1.6 が丸ごと空いている区間」だけ、しかも RIB_LMIN 以上の長さだけ引く（🔒 ユーザー 2026-09-05「ある程度以下の長さは出さない。粗雑に見える」）
//   区間は tools/ribs_gen.py が出す（part="ribfree_<板>" の 2D を SVG に書き出し、格子の線との交わりを取る）。🔴 中身・線・板を動かしたら回し直す
//   OpenSCAD の offset で座標を 100 倍に伸ばして篩う方法は精度が壊れて板の上に角が出た（2026-09-05）
RIB_LMIN = 4.0;   // 🔒 ユーザー 2026-09-05「v4 と同じ 8mm 未満ではなく 4mm 未満にしましょう」
include <parts/ribs_v5_gen.scad>   // RIB_SEGS
include <parts/props_v5_gen.scad>  // props_strap_* / raft_strap_*（自動生成・python hardware/tools/props_gen.py）
module rib_2d(k) for (s = RIB_SEGS) if (s[0] == k) { if (s[1] == 0) translate([s[3], s[2] - RIB_W / 2]) square([s[4] - s[3], RIB_W]); else translate([s[2] - RIB_W / 2, s[3]]) square([RIB_W, s[4] - s[3]]); }
module panel_ribs(k) if (!RIBS_OFF) color("#8fb8a0") {
    if (k == "lwall") translate([LW_X + RIB_H, 0, 0]) rotate([0, -90, 0]) linear_extrude(RIB_H) rib_2d(k);
    if (k == "rwall") translate([IN_X, 0, 0]) rotate([0, -90, 0]) linear_extrude(RIB_H) rib_2d(k);
    if (k == "hatch") translate([0, IN_Y, 0]) rotate([90, 0, 0]) linear_extrude(RIB_H) rib_2d(k);
    if (k == "front") translate([0, FY_IN + RIB_H_FR, 0]) rotate([90, 0, 0]) linear_extrude(RIB_H_FR) rib_2d(k);
    if (k == "bridge") translate([0, 0, BRG_ZB + BRG_T - 0.01]) linear_extrude(RIB_H + 0.01) rib_2d(k);   // 🔒 ユーザー 2026-09-05「ブリッジの長い手にもグリッド格子が欲しい（割と歪む）」: 帯の上面に立てる
}
module ribs() { panel_ribs("lwall"); panel_ribs("rwall"); panel_ribs("hatch"); panel_ribs("front"); panel_ribs("bridge"); }

// ---- 中身 ----
module innards() for (n = UNITS) one(n);

// ============================================================
// 線（🔒 ユーザー 2026-09-05「線は引き直し」）。口の世界座標は口の定義から式で引く（数字を手で書かない・wires.scad の約束）
//   束は丸（bundle_d・1 本 1.55）。口の近くは 1 本ずつ扇に開く（口の頭から軸へ 3 出て合流点へ）。曲げ半径 WIRE_R
//   車線（2026-09-05）:
//     皿の下 Z 22.5 … ハブの口の頭（20.6）と皿の裏（25.4）の間。XIAO の束が右へ
//     右の帯 Y 30.5 … XIAO の積み（Y 〜27.9）とつまみの口（Y 33.2〜）の間
//     左の溝 X 5.8〜9.5 … 左の壁と皿（X 11.4）の間。OLED（X 5.8・Z 30）・会話ボタン（X 9・Z 16）・充電（X 9.5・Z 39）
//     後ろの帯 Y 70.5〜71 … ハブの後ろの口の頭（20.6）の上・蓋の板（Y 72.65）の前。電源（Z 33）・電流計 I2C（Z 29.5）
//     ハブの上 Y 24.5 Z 11 … XIAO の口（Y 〜20.3）と AS5600 の口（Y 27.9〜）の間。スピーカー IN の PH
//   REED の口は空き（リードスイッチの場所が未決・2026-09-05）
// ============================================================
WIRE_R = 3.0;   // 束の曲げ半径（1 本 1.55 の一般値）
function rotx(p, a) = [p[0], p[1] * cos(a) - p[2] * sin(a), p[1] * sin(a) + p[2] * cos(a)];
function roty(p, a) = [p[0] * cos(a) + p[2] * sin(a), p[1], -p[0] * sin(a) + p[2] * cos(a)];
function rotz(p, a) = [p[0] * cos(a) - p[1] * sin(a), p[0] * sin(a) + p[1] * cos(a), p[2]];
// 部品の局所 → 世界（at_*() と同じ順の変換を式で書いたもの。at_*() を変えたらここも変える）
function W_hub(p)  = HUB_AT + p;
function W_oled(p) = OLED_AT + rotx(p, 90);
function W_rsp(p)  = [RSP_X + respeaker_L(), RSP_Y1, RSP_Z] + rotz(p, 180);
function W_knob(p) = [KNOB_AT[0], KNOB_AT[1], Z_TOP + TOP_T] + p;
function W_btn(p)  = [BTN_AT[0], BTN_AT[1], Z_TOP + TOP_T] + p;
function W_pb(p)   = [PBC[0], PBC[1], Z_TOP - PB_CEIL_SO] + rotz(rotz(p - [pb_size()[0] / 2, pb_size()[1] / 2, 0], 180), PB_RZ);   // PB_FLIP = [0,0,0] 前提
function PBF_O3()  = [BAT_X0 + (lipo_size()[1] - pb_size()[0]) / 2 + pb_size()[0], PAIR_Y0 + ina_size()[1] + 0.5 + pb_size()[1] + PB_DY, BAT_TOP + STRAP_T + BOARD_LIFT];
function W_ina(p)  = [INA_SX, INA_SY, INA_LIFT - BOARD_LIFT - STRAP_C_POCKET] + PBF_O3() + rotz([pb_size()[0] / 2, pb_size()[1] / 2, 0] + rotz(p - [ina_size()[0] / 2, ina_size()[1] / 2, 0], -90 + INA_RZ), 180);   // INA_POSE "下_I2C前"・PB_TILT 0 前提
function W_ina_d(v) = rotz(rotz(v, -90 + INA_RZ), 180);   // 向きだけ
function W_pb_d(v) = rotz(rotz(v, 180), PB_RZ);   // PowerBoost の向きだけ（JP2 の L 字は局所 −y・JST は局所 +y）
function W_tgl(p)  = TGL_AT + roty(rotx(p, -90), TGL_RY);
function W_tgl_d(v) = roty(rotx(v, -90), TGL_RY);
// 口の頭（線が出る点）と、そこから線が出る向き
function hub_h(id) = [for (h = HUB_HEADERS) if (h[0] == id) h][0];
function hub_part(id) = [for (h = HUB_PARTS) if (h[0] == id) h][0];
function hub_mouth(id, k) = let (h = hub_h(id), ax = (h[6] - h[4]) >= (h[7] - h[5])) W_hub([h[4] + (ax ? k * 2.54 : 0), h[5] + (ax ? 0 : k * 2.54), 1.6 + 2.5 + dupont_h()]);   // ピン k のハウジングの頭・軸は +Z
function ph_mouth(id) = let (h = hub_part(id)) W_hub([(h[3] + h[5]) / 2, (h[4] + h[6]) / 2, 1.6 + h[7] + 2.0]);   // PH のソケットの上 2.0（プラグの頭）・線は上へ
function xiao_mouth(r, k) = let (used = [[2, 3, 4, 5], [0, 1, 2]][r]) W_rsp([2.932 + used[k] * 2.54, -(1.4 + 2.5) - dupont_h(), [9.397, 24.627][r]]);   // 軸は世界 +Y
function oled_mouth(k) = let (c = oled_hdr()) W_oled([c[0] - 1.5 * 2.54 + k * 2.54, c[1], oled_hous_z_top()]);   // 軸は世界 +Y
function ina_i2c_mouth() = let (hd = ina_hdr()) W_ina([hd[0] + hd[4] - dupont_h(), hd[2] + 1.27 + 1.5 * 2.54, (ina_back_env() > 0) ? 0.8 - (1.6 + 2.5 - 0.8) : 1.6 + 2.5]);   // 裏出しなら z −2.5（中面 0.8 の鏡）   // 4 本の中心・軸は W_ina_d([-1,0,0])
function ina_pwr_mouth(j) = let (q = ina_pwr_pins()[j]) W_ina([q[0] + 1.27, q[1], 1.6 + 2.5 + 1.27] + rotz([dupont_h(), 0, 0], ina_pwr_yaw(j)));   // j 0,1 = INPUT / 2,3 = OUTPUT・軸は ina_pwr_ax(j)（ピンごとの振り INA_PWR_YAW 込み）
function ina_pwr_ax(j) = W_ina_d(rotz([1, 0, 0], ina_pwr_yaw(j)));
function pb_mouth(i) = W_pb([pb_jp2_x0() + i * 2.54, -dupont_h(), 1.6 + 2.5]);   // JP2 のピン i・軸は世界 +Y
function pb_jst_mouth() = W_pb([pb_jst()[0], pb_jst()[1] + pb_jst_sz()[1] / 2 + pb_jst_mate(), 1.6 + 2.6]);   // 電池の JST の頭・軸は世界 −Y
function knob_mouth(s, i) = let (x = s * (as5600_pcb() / 2 - as5600_edge_in_s(s)), row = (s < 0) ? as5600_row_l() : as5600_row_r()) W_knob(rotz([x, row[i], -2.5 - dupont_h()], 90) + [0, 0, -knob_deep()]);   // 軸は −Z
function tc_mouth(i) = [TC_PIN_XC, TC_Y0 + 2.54 - 1.27 - dupont_h(), TC_ZT - (2.54 + i * 2.54)];   // 軸は −Y
function tgl_term(i) = W_tgl([i * 4.7, 0, -mts102_deep()]);   // 端子の先（i = −1/0/+1）・軸は W_tgl_d([0,0,-1])
function btn_pin(i) = W_btn(btn3_sw_pin(i));   // マイクロスイッチの端子の先（i = −1/0/+1）・下向き
function j2_mouth() = let (j = respeaker_spk_j2()) W_rsp([(j[0] + j[1]) / 2, -(j[4] + 3.0), (j[2] + j[3]) / 2]);   // ReSpeaker のスピーカーソケットの PH プラグの頭・軸は世界 +Y
BAT_LEAD = [BAT_AT[0] + lipo_size()[1] / 2, BAT_AT[1] + lipo_size()[0], BAT_AT[2] + lipo_size()[2] / 2];   // 電池の線の出口: 後ろの面の中央（タブは後ろ・at_bat）。軸 +Y
SPK_BOT = 45.65;   // スピーカーの模型の下端（測った値）（磁石の出っ張り込み・only_spk の STL から 2026-09-05）。parts.scad に関数が無いので数字
SPK_LEAD = [SPK_AT[0] + 4.0, SPK_AT[1] + spk_w() / 2 - 1.5, SPK_BOT];   // スピーカーの線の出口。⚠ 未確認（秋月 112495 のページに図面が無い。リードの根元の位置は実物で見て入れる）。効くのは線 phout の模型の始点だけで、天板の穴や溝はここから彫っていない。軸 −Z

WIRE_LEN = false;   // true: 束ごとの実長を echo（_asm_manual_v5.py が切る長さの表に使う）
module bnd(pts, n, nm = "") { if (WIRE_LEN) echo(wlen = [nm, n, wire_len(pts, WIRE_R)]); wire(pts, d = bundle_d(n), r = WIRE_R); }   // 束（n 本）
module w1(pts, nm = "", d = 1.55, r = 2.0) { if (WIRE_LEN) echo(wlen = [nm, 1, wire_len(pts, r)]); wire(pts, d = d, r = r); }   // 1 本
module fan(ms, ax, m, r = 2.0, d = 1.55) for (p = ms) wire([p + ax * (d / 2), p + ax * 3.0, m], d = d, r = r);   // 口の頭 → 軸へ 3 → 合流点（1 本ずつ。始点は頭から線の半径だけ出す＝口と重ねない）
function xs(a, b) = [for (i = [a : b]) i];
// ---- 束 ----
module w_xiao() {   // ハブ XIAO 7 ↔ ReSpeaker の XIAO 2 列（🔒 2026-09-06 下 = 信号 4・上 = 電源 3。それまで逆）。口の頭の上（皿の下 Z 22.5）を右へ → 積みの右後ろ（Y 30.5）→ 積みの後ろから
    m1 = [47.0, 20.5, 22.5]; m2 = [72.0, 30.5, 22.5]; m3 = [72.0, 30.5, 25.0]; m4 = [78.5, 30.5, 14.0];   // Y 20.5: OLED の線（Y 23.8〜）の前
    fan([for (k = xs(0, 6)) hub_mouth("XIAO", k)], [0.5, 0, 0.87], m1);   // 少し右へ傾けて出す（左端のピンの真上に前板のナットの箱の角 X 27.4 がある）
    bnd([m1, [64.5, 20.5, 22.5], [64.5, 30.5, 22.5], m2], 7, "xiao");
    bnd([m2, m3], 3, "xiao"); fan([for (k = xs(0, 2)) xiao_mouth(1, k)], [0, 1, 0], m3);                 // 上の列 3 本＝電源（Z 27.1）
    bnd([m2, [78.5, 30.5, 22.5], m4], 4, "xiao"); fan([for (k = xs(0, 3)) xiao_mouth(0, k)], [0, 1, 0], m4);   // 下の列 4 本＝信号（Z 11.9）
}
module w_oled() {   // OLED 4: 口（Y 21.1・Z 46.5）→ 後ろへ 3 → 右へ（Y 23.8）→ X 50 で Z 43.5 に下りて（スピーカーの下・電流計の電源の口の上）→ X 59.5（電源の口の列と電池の線の東）で皿の下（Z 22〜24）まで下り → 2 本 × 2 段（Y 23.8 / 25.5・Z 22.2 / 23.9）でハブの上（XIAO の口 〜20.3 と AS5600 の口 27.9〜 の間）を左へ → ハブの OLED の口へ
    //   口の周りは筒（左・Y 11.4〜）・スピーカー（右上・Z 45.65〜）・PowerBoost（後ろ・Y 26.1〜）・電流計の電源の口（下・頭 Z 42.0）に囲まれ、前の帯は ReSpeaker の背面の部品（Y 〜13.4・Z 〜36）と皿の前板（Y 12.9〜）で塞がっている。φ3.9 の束が通る道は無く、1 本ずつこの道を通す（2026-09-05）
    m1 = [10.5, 30.0, 23.2];
    for (k = xs(0, 3)) { mo = oled_mouth(k); yq = (k < 2) ? 23.8 : 25.5; zq = (k % 2 == 0) ? 22.2 : 23.9;
        w1([mo + [0, 0.8, 0], mo + [0, 3.0, 0], [50.0, 23.0, 46.5], [50.0, 23.0, 43.5], [59.5, 23.0, 43.5], [59.5, 23.0, zq + 2.5], [59.5, yq, zq], [13.0, yq, zq], m1], "oled", d = 1.55, r = 2.0); }   // 上の道は Y 23.0（JST の線が Y 24.7 を通る）
    fan([for (k = xs(0, 3)) hub_mouth("OLED", k)], [0, 0, 1], m1);
}
module w_as5600() {   // ハブ AS5600 4 ↔ つまみの 5 口（左 2・右 3。GND は二股）。口の下から上へ入る。右 3 はリレー（頭 Z 14.1）の上なので前へ逃げてから下りる
    m1 = [40.0, 37.5, 17.0]; m2 = [56.0, 37.5, 12.5]; m3 = [56.0, 41.5, 15.5];
    fan([for (k = xs(0, 3)) hub_mouth("AS5600", k)], [0, 0, 1], m1);
    bnd([m1, m2, m3], 4, "as5600");
    for (i = as5600_used_l()) { p = knob_mouth(-1, i); w1([p + [0, 0, -0.8], p + [0, 0, -3.0], m2], "as5600", d = 1.55, r = 2.0); }
    for (i = as5600_used_r()) { p = knob_mouth(1, i);  w1([p + [0, 0, -0.8], p + [0, -2.5, -1.0], m3], "as5600", d = 1.55, r = 2.0); }
}
module w_pwr() {   // ハブ PWR 3（EN・GND・5Vo）↔ PowerBoost の JP2 の L 字 3。後ろの帯（Y 70.5・Z 33）をトグルの下・蓋の板の前で左へ → X 24 で上がる
    m1 = [67.0, 70.5, 24.0]; m2 = [24.0, 70.5, 47.2];
    fan([for (k = [0, 1, 3]) hub_mouth("PWR", k)], [0, 0, 1], m1);
    bnd([m1, [67.0, 70.5, 33.0], [24.0, 70.5, 33.0], m2], 3, "pwr");
    fan([for (i = pb_ra_pwr()) pb_mouth(i)], W_pb_d([0, -1, 0]), m2);
}
module w_chg() {   // Type-C 基板の VBUS・GND ↔ PowerBoost の USB・GND2。左の溝（X 9.5）を上がって後ろの帯へ
    m1 = [9.5, 46.0, 17.0]; m2 = [10.0, 70.5, 47.2];
    fan([tc_mouth(0), tc_mouth(1)], [0, -1, 0], m1);
    bnd([m1, [9.5, 46.0, 39.0], [9.5, 70.5, 39.0], [9.5, 70.5, 47.2], m2], 2, "chg");
    fan([for (i = pb_ra_chg()) pb_mouth(i)], W_pb_d([0, -1, 0]), m2);
}
module w_ina() {   // ハブ INA 4 ↔ 電流計の I2C の L 字。後ろの帯（Y 71・Z 29.5・PWR の下）を左へ → X 20 で上がって口の向きへ
    ax = W_ina_d([-1, 0, 0]); pm = ina_i2c_mouth();
    m1 = [32.0, 71.0, 24.0];
    fan([for (k = xs(0, 3)) hub_mouth("INA", k)], [0, 0, 1], m1);
    bnd([m1, [32.0, 71.0, 29.5], [20.0, 71.0, 29.5], [20.0, 71.0, 40.5], pm + ax * 6.0, pm + ax * 2.5], 4, "ina");
}
module w_tgl() {   // ハブ TOGGLE 2 ↔ トグルの端子（中 COM・下）。端子（X 64.7・Y 59.25〜65.25）の脇（X ±1.4・Y 64.0）から真下へ、天板の受けの前の当ての切れ目（軸 ±2.2）を抜けて Z 30 まで下り → 皿の帯（Y 〜62.9）の後ろを左へ → TOGGLE と REED の口の間（X 53.15）で下りてハブの口へ
    m1 = [53.15, 64.0, 23.8];
    for (i = [0, 1]) { t = tgl_term(i); sx = (i == 0) ? -1 : 1;
        w1([t + [sx * 1.4, 4.75, 0], [t[0] + sx * 1.4, 64.0, 30.0], [53.15, 64.0, 30.0], m1], "tgl", d = 1.55, r = 2.0); }
    fan([hub_mouth("TOGGLE", 0), hub_mouth("TOGGLE", 1)], [0, 0, 1], m1);
}
module w_btn2() {   // ハブ BTN2 2 ↔ 会話ボタンのマイクロスイッチの端子（両端）。端子の横から前へ出て左の溝（X 9・Z 16）を後ろへ
    m1 = [9.0, 15.9, 36.3]; m2 = [9.0, 63.7, 23.6];   // Z 36.3: 筒の左の足（Z 37.87 まで）の下
    for (i = [-1, 1]) { p = btn_pin(i); w1([p + [0, -1.2, 0.3], p + [0, -2.0, 1.0], m1], "btn2", d = 1.55, r = 2.0); }   // 端子（Y 17.3・幅 0.8）の前の面から線の半径だけ離して始める
    bnd([m1, [9.0, 15.9, 24.5], [9.0, 24.0, 24.5], [9.0, 24.0, 16.0], [9.0, 61.0, 16.0], m2], 2, "btn2");   // Z 24.5 で Y 24 まで後ろへ（左前の角の ReSpeaker のスピーカーソケット J2 とその PH プラグ（Y 〜19.9・Z 〜23）の上・OLED の束（X 5.8・Z 27.5）の下）
    fan([hub_mouth("BTN2", 0), hub_mouth("BTN2", 1)], [0, 0, 1], m2);
}
module w_phin() {   // ReSpeaker のスピーカーソケット J2 → ハブ PHIN（PH 2 本）。左の壁ぎわ（X 5）で下りて → ハブの上（Y 24.5・Z 11）を右へ → X 64.5 を後ろへ → Y 41 で右へ → ソケットの上から
    j = j2_mouth(); ph = ph_mouth("PHIN");
    bnd([j + [0, 0.8, 0], j + [0, 3.0, 0], [5.0, 24.5, 17.0], [5.0, 24.5, 11.0], [64.5, 24.5, 11.0], [64.5, 41.0, 11.0], [ph[0], 41.0, 11.0], [ph[0], 41.0, 15.0], [ph[0], ph[1], 15.0], ph + [0, 0, 0.8]], 2, "phin");
}
module w_phout() {   // ハブ PHOUT → スピーカー（PH 2 本 → リード）。ソケットから右へ出てハブの右端の上（X 80.5・Z 8）を前へ → 右の壁ぎわ（X 83）を上がって → 天井の下（Z 44）を前へ → スピーカーの裏へ
    ph = ph_mouth("PHOUT");
    bnd([ph + [0, 0, 0.8], [ph[0], ph[1], 14.5], [80.5, ph[1], 14.5], [80.5, ph[1], 8.0], [80.5, 31.5, 8.0], [83.0, 31.5, 8.0], [83.0, 31.5, 44.0], [83.0, 22.0, 44.0], [70.0, 22.0, 44.0], SPK_LEAD + [0, 0, -3.0], SPK_LEAD + [0, 0, -0.8]], 2, "phout");
}
module w_bat() {   // 電池 → 電流計 INPUT ±（2 本）。電流計は箱の軸に平行で、INPUT の 1 本目の口は左（X 20.6・Y 28.6・左向き）、2 本目は前（X 38.8・Y 14.6・前向き）。
    //   1 本目: 電池の後ろから左の溝（X 6.6・Z 30.4）を前へ → 皿の左の土手の上を越えて口へ。2 本目: 右（X 53.2・Z 29）を前へ → Y 12 で上がり、口の前へ左から入る
    l0 = BAT_LEAD + [0, 1.6, 0]; l1 = BAT_LEAD + [0, 3, 0]; c = [BAT_LEAD[0], 66.0, BAT_LEAD[2]];
    p0 = ina_pwr_mouth(0); p1 = ina_pwr_mouth(1);
    w1([l0, l1, c, [6.6, 66.0, 30.4], [6.6, 30.0, 30.4], [12.0, 29.5, 37.0], p0 + ina_pwr_ax(0) * 3.0, p0 + ina_pwr_ax(0) * 0.8], "bat", d = 1.55, r = 2.5);
    w1([l0, l1, c, [53.2, 66.0, 29.0], [53.2, 14.0, 29.0], [53.2, 12.0, 39.0], [42.0, 11.6, 39.0], p1 + ina_pwr_ax(1) * 3.0, p1 + ina_pwr_ax(1) * 0.8], "bat", d = 1.55, r = 2.5);
}
module w_batout() {   // 電流計 OUTPUT ± → PowerBoost の JST（2 本・JST の線は φ1.0 → 束 φ1.6）。JST の頭（X 35.4・Y 26.1）の前は会話ボタンの筒の右の腕（X 〜35.35）で 1.2 しか無いので、出てすぐ右（X 37.5）へ → 電源の口の列の上（Z 43.3）を前へ → 口の前（Y 11.6）へ
    ax = W_ina_d([0, -1, 0]); jm = pb_jst_mouth(); jx = W_pb_d([0, 1, 0]); m1 = [40.5, 11.2, 42.5];
    w1([jm + jx * 0.8, jm + jx * 1.5, [37.5, 25.0, 46.5], [37.5, 25.0, 43.3], [37.5, 12.0, 43.3], m1], "batout", d = 1.6, r = 2.0);
    fan([ina_pwr_mouth(2), ina_pwr_mouth(3)], ina_pwr_ax(2), m1, d = 1.0);
}
WIRE_NAMES = ["xiao", "oled", "as5600", "pwr", "chg", "ina", "tgl", "btn2", "phin", "phout", "bat", "batout"];
module w_one(n) color("#e0b060") {
    if (n == "xiao") w_xiao(); if (n == "oled") w_oled(); if (n == "as5600") w_as5600(); if (n == "pwr") w_pwr();
    if (n == "chg") w_chg(); if (n == "ina") w_ina(); if (n == "tgl") w_tgl(); if (n == "btn2") w_btn2();
    if (n == "phin") w_phin(); if (n == "phout") w_phout(); if (n == "bat") w_bat(); if (n == "batout") w_batout();
}
module wires() for (n = WIRE_NAMES) w_one(n);
module all_solid() { innards(); p_floor(); p_top(); p_lwall(); p_rwall(); p_front(); p_hatch(); }   // 線の当たりの相手（中身＋皮）

if (part == "look")  innards();
if (part == "wires") { innards(); wires(); }
if (part == "wiresonly") wires();
if (part == "ribs") ribs();
if (starts(part, "ribfree_")) offset(delta = -RIB_W / 2 - 0.05) rib_free2d(tail(part, 8));   // リブの空き（線の半幅だけ縮めた 2D）。tools/ribs_gen.py が SVG に書き出して区間を出す
if (part == "hit_ribs") intersection() { ribs(); union() { innards(); wires(); } }
if (part == "hit_wires") intersection() { wires(); all_solid(); }
if (starts(part, "hit_w_")) intersection() { w_one(tail(part, 6)); all_solid(); }
if (starts(part, "only_w_")) w_one(tail(part, 7));
if (part == "plugs") plugs();
if (part == "bridge") { bridge(); panel_ribs("bridge"); brg_front(); straps(); one("bat"); one("ina"); }
if (part == "skin")   skin();
// ---- 板 6 枚とブリッジを刷る向き（v4 と同じ）。板は外面を下（柱・棚・耳・格子・台座は全部上を向く）・ブリッジは皿の裏を下。前板（brg_front）と蓋一式（shutter_v4）は未定
PLATES6 = ["floor", "top", "lwall", "rwall", "front", "hatch"];
module plate_named(n) { if (n == "floor") p_floor(); if (n == "top") p_top(); if (n == "lwall") p_lwall(); if (n == "rwall") p_rwall(); if (n == "front") p_front(); if (n == "hatch") p_hatch(); }
module skin_solid() for (n = PLATES6) plate_named(n);
module print_floor()  translate([0, 0, FLOOR_T]) p_floor();
module print_top()    translate([0, 0, Z_TOP + TOP_T]) rotate([180, 0, 0]) p_top();   // つまみのへこみの天井の柱とラフトは v4 と同じく生成器（props_top / raft_top）。knob_v5 の deck_props はつまみ単体の試し刷り用で、ここでは使わない（ユーザー 2026-09-05「ラフト無くなってる」「前のと違う」）
module print_lwall()  translate([0, 0, -OUT_X0]) rotate([0, -90, 0]) { p_lwall(); panel_ribs("lwall"); }
module print_rwall()  translate([0, 0, OUT_X1]) rotate([0, 90, 0]) { p_rwall(); panel_ribs("rwall"); }
module print_front()  translate([0, 0, -OUT_Y0]) rotate([90, 0, 0]) { p_front(); panel_ribs("front"); }
module print_hatch()  translate([0, 0, OUT_Y1]) rotate([-90, 0, 0]) { p_hatch(); panel_ribs("hatch"); }
module print_bridge() translate([0, 0, -BRG_ZB]) { bridge(); panel_ribs("bridge"); }
// 支柱を立ててはいけない体積（keepout。v4 と同じ流儀）: 板を貫く穴・口・軸の穴。tools/props_gen.py が刷る向きで焼き、柱の胴＋逃げ 0.3 が触る候補を落とす
module keepout_top() { at_knob() { knob_station_shaft_cut(); knob_station_screw_cut(); knob_station_reed_cut(); } at_btn() btn3_station_cut(); top_screw_cuts(); spk_grille(); }   // つまみは軸・ねじ・リードの穴だけ（へこみ全体を入れると柱が全部落ちる）
if (part == "keepout_top") translate([0, 0, Z_TOP + TOP_T]) rotate([180, 0, 0]) keepout_top();
// 前板と蓋の 3 点（v4 と同じ向き・🔒 ユーザー 2026-09-05「v4 と同じ方向でいいよ」）: 前板は前の面を下（フランジと返しは上を向く）、蓋とロックはハッチの外面を下、床の板は溝の床の面を下
module print_brgfront()  translate([0, 0, -FP_Y0]) rotate([90, 0, 0]) brg_front();
module print_shutter()   translate([0, 0, SW4_YOUT]) rotate([-90, 0, 0]) battery_shutter4(0);
module print_lock()      translate([0, 0, SW4_YOUT]) rotate([-90, 0, 0]) battery_lock4();
module print_shutfloor() translate([0, 0, sw4_yg()]) rotate([-90, 0, 0]) difference() { sw4_floor_plate(); tgl_plate_notch(); }
if (part == "print_brgfront")  print_brgfront();
if (part == "print_shutter")   print_shutter();
if (part == "print_lock")      print_lock();
if (part == "print_shutfloor") print_shutfloor();
if (part == "print_floor")  { print_floor();  if (!PROPS_OFF) { props_floor();  raft_floor(); } }
if (part == "print_top")    { print_top();    if (!PROPS_OFF) { props_top();    raft_top(); } }
if (part == "print_lwall")  { print_lwall();  if (!PROPS_OFF) { props_lwall();  raft_lwall(); } }
if (part == "print_rwall")  { print_rwall();  if (!PROPS_OFF) { props_rwall();  raft_rwall(); } }
if (part == "print_front")  { print_front();  if (!PROPS_OFF) { props_front();  raft_front(); } }
if (part == "print_hatch")  { print_hatch();  if (!PROPS_OFF) { props_hatch();  raft_hatch(); } }
if (part == "print_bridge") { print_bridge(); if (!PROPS_OFF) { props_bridge(); raft_bridge(); } }
if (starts(part, "sk_"))   intersection() { one(tail(part, 3)); skin_solid(); }
if (starts(part, "seam_")) { ab = tail(part, 5); k = search("_", ab)[0]; a = _join([for (i = [0 : k - 1]) ab[i]]); b = _join([for (i = [k + 1 : len(ab) - 1]) ab[i]]); intersection() { plate_named(a); plate_named(b); } }
if (part == "print_strap_a") { strap_print(0); if (!PROPS_OFF) { props_strap_a(); raft_strap_a(); } }
if (part == "print_strap_b") { strap_print(1); if (!PROPS_OFF) { props_strap_b(); raft_strap_b(); } }
if (part == "print_strap_c") { strap_print(2); if (!PROPS_OFF) { props_strap_c(); raft_strap_c(); } }
if (part == "p_floor") color("#e0a040") p_floor();
if (part == "p_top")   color("#c9d0d8") p_top();
if (part == "p_lwall") { color("#4a90d9") p_lwall(); panel_ribs("lwall"); }
if (part == "p_rwall") { color("#4a90d9") p_rwall(); panel_ribs("rwall"); }
if (part == "p_front") { color("#9b59b6") p_front(); panel_ribs("front"); }
if (part == "p_hatch") { color("#27ae60") p_hatch(); panel_ribs("hatch"); }
if (part == "fasten") { color("#4a90d9") p_lwall(); color("#4a90d9") p_rwall(); color("#e0a040", 0.35) p_floor(); color("#c9d0d8", 0.35) p_top(); color("#9b59b6", 0.35) p_front(); bridge(); brg_front(); straps(); }
if (part == "tcfit")  { one("tc"); color("#e0a040", 0.9) p_floor(); color("#4a90d9", 0.35) p_lwall(); color("#27ae60", 0.35) p_hatch(); }   // 床（受け込み）＝橙・左の壁（押さえ込み）＝青・ハッチ＝緑
if (part == "all")    { skin(); innards(); }
if (part == "explode") {   // 箱全体の分解。🔒 ユーザー 2026-09-05「explode がブリッジだけになっている」
    color("#e0a040") p_floor(); one("hub"); one("rsp"); one("oled"); one("tc");                                       // 置いたまま
    translate([-30, 0, 0]) { color("#4a90d9") p_lwall(); panel_ribs("lwall"); }                                      // 左の壁は左へ
    translate([30, 0, 0])  { color("#4a90d9") p_rwall(); panel_ribs("rwall"); }                                      // 右の壁は右へ
    translate([0, -30, 0]) { color("#9b59b6") p_front(); panel_ribs("front"); }                                      // フロントは前へ
    translate([0, 35, 0])  { color("#27ae60") p_hatch(); panel_ribs("hatch"); one("tgl"); one("hatchplate"); one("shutter"); one("lock"); }   // ハッチは後ろへ（蓋とトグルごと）
    translate([0, 0, 15])  { brg_front(); bridge(); panel_ribs("bridge"); }                                            // ブリッジと前板
    translate([0, 0, 30])  straps();                                                                                    // 帯
    translate([0, 0, 24])  one("bat");                                                                                  // 電池
    translate([0, 0, 42])  one("ina");                                                                                  // 電流計
    translate([0, 0, 60])  { color("#c9d0d8") p_top(); one("pb"); one("knob"); one("btn"); one("spk"); }              // 天板は小組ごと上へ
}
if (starts(part, "only_")) one(tail(part, 5));
if (starts(part, "hit_"))  { n = tail(part, 4); intersection() { one(n); others(n); } }
if (starts(part, "pair_")) { ab = tail(part, 5); k = search("_", ab)[0]; a = _join([for (i = [0 : k - 1]) ab[i]]); b = _join([for (i = [k + 1 : len(ab) - 1]) ab[i]]); intersection() { one(a); one(b); } }
echo(v5 = [IN_Y, IN_Z], hub_plug_top = HUB_PLUG_TOP, brg_zb = BRG_ZB, bat = BAT_AT, pair_y0 = PAIR_Y0);
