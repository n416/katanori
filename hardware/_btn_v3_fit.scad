// btn_v3 が case_v4 の中に置けるか。0 が正。
//   🔴 2026-08-30 ここに btn3_station_add() の**写し**を書いていて、本体の変更（ブロックの Y の送り）を
//     読んでいなかった。掃引しても数字が 1mm も動かず、無効な結論を出した。
//     ⇒ 形は必ず本体のモジュールから取る。この検査は自分で形を描かない。
//   🔴 W="rsp"（羊羹）は**当たりとして数えない**。羊羹も座も同じ天板に付く物なので、
//     重なれば union で 1 つの塊になるだけ（ユーザー指摘 2026-08-30）。
//   ⚠ 旧: 「case_v4 にはまだ btn_v2 が組まれていて自分自身と重なる」→ 🔴 2026-09-01 もう成立しない。
//      case_v4 が呼ぶのは btn3_* だけ（_v4_core.scad 3 行目が btn_v3.scad を読む）。⬜ W="all" の可否は取り直し。
//     信じてよいのは相手ごとの数字だけ。
include <btn_v3.scad>
include <case_v4.scad>
part = "none"; PROPS_OFF = true; BTN3_SOLO = false;
W = "all";
// 🔒 検査が生きているかを毎回申告する（「空」と「動いていない」を取り違えないため）
echo(str("FIT 生存確認: BTN4=", BTN4, " Z_TOP=", Z_TOP, " 相手=", W,
         " BLK_DY=", B3_BLK_DY, " 座 ", B3_PAD_L, " x ", B3_PAD_W, " DX=", DX, " DY=", DY));

// v3 のボタン一式が world で占める体積（天板側の肉 ＋ バスタブ ＋ 押し子の軌跡）
STEP = 0.25;
DX = 0;   // BTN4 を X へ動かしてみる量（case 側の判断材料）
DY = 0;   // 同 Y
module btn3_v3_volume() translate([BTN4[0] + DX, BTN4[1] + DY, Z_TOP]) {
    difference() { btn3_station_add(); btn3_station_cut(); }
    btn3_tub();
    for (i = [-B3_TRAVEL : STEP : 0]) translate([0, 0, i]) btn3_piston();
}

intersection() {
    btn3_v3_volume();
    if (W == "all") innards4();
    else if (W == "rsp") rsp_press4();          // 羊羹
    else if (W == "rspbd") respeaker_at();
    else if (W == "oled") oled_at();
    else if (W == "oledh") oled_hous();      // 🔴 OLED のピンヘッダ／ハウジング
    else if (W == "xiaoh") xiao_hous();
    else if (W == "hous") { for (id = PLUGGED_9) translate([HUB_DX, HUB_DY, 0]) housing(id); }
    else if (W == "ina") ina_bat();
    else if (W == "brg") brg_v4();
    else if (W == "straps") straps_v4();
    else if (W == "bat") bat_v4();
    else if (W == "pb") { pb_bat(); pbl_hous(); pbu_hous(); }
    else if (W == "hub") hub_unit();
    else if (W == "wpwr") wires_pwr();
    else if (W == "wsig") wires_sig();
    else if (W == "skin") { for (k = SKINS) if (k != "top") skin1(k); }
}
