// ============================================================
// 「挿す口」だけを出す道具（2026-08-27）。当たり検査ではない。
//   _asm_access.py が bbox（連結成分）から**挿す軸と、抜き差しに要る後ろの空き**を拾うために使う。
//   実行: openscad --backend=manifold -D 'P="ina"' -o x.stl hardware/_asm_plugs.scad
//   P: ina（電流計の板ごと・電源 4 ＋ I2C）/ pb（PowerBoost の板ごと・JST 込み）/ pbl（L 字 3 ピンの DuPont）
//      pbu（USB ピンの DuPont）/ oled（OLED の 4 連 DuPont）
// ============================================================
include <case_v4.scad>
part = "none";   // case_v4 の描画スイッチを止める（include の後の代入が勝つ）
W    = "none";
P    = "";

if (P == "ina")  ina_bat();
if (P == "pb")   pb_bat();
if (P == "pbl")  pbl_hous();
if (P == "pbu")  pbu_hous();
if (P == "oled") oled_hous();
if (P == "tcb")  tcb_v4();      // Type-C 基板（挿した DuPont ごと）
if (P == "tcbh") difference() { tcb_v4(); tcb_v4_bare(); }   // 充電の DuPont だけ（板・L ピンを引いた残り）
if (P == "tgl")  tgl_v4();      // トグル（ハッチに付く。端子は箱の中を向く）
