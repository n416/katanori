// 組み立てマニュアル v5 の「部品の呼び名」の挿絵。筐体の部品ではない・絵だけの道具
//   openscad --backend=manifold --render=full --autocenter --viewall -D 'G="obi"' -o x.png hardware/tools/manual_v5/_asm_gloss_v5.scad
include <../../case_v5.scad>
part = "none";
G = "";
if (G == "sara")   { color("#c9a45c") bridge(); }                                              // 皿と腕（ブリッジ）
if (G == "obi")    { color("#c9a45c", 0.35) bridge(); color("#e0a040") straps(); }              // 帯 3 本（皿の上）
if (G == "koobi")  { color("#e0a040", 0.35) straps(); color("#5b7fa6", 0.5) one("ina"); color("#e07a5f") ina_bar(); }   // 小帯（電流計の 2 穴のダボに掛ける橋・帯 B の上）
if (G == "maeita") { color("#c9a45c", 0.35) bridge(); color("#e0a040") brg_front(); }           // 前板
if (G == "dote")   { color("#c9a45c") bridge(); color("#e0a040", 0.5) straps(); }               // 土手（皿の縁の壁。帯のツバが入る溝がある）
if (G == "yokan")  { color("#c9d0d8", 0.3) p_top(); color("#e07a5f") rsp_press(); }            // 羊羹とマッチ棒（天板の裏・ReSpeaker の頭を押す）
if (G == "za")     { color("#e0a040", 0.3) p_floor(); color("#e07a5f") { rsp_seat(); oled_rib(); } }   // 座（床・ReSpeaker の板が乗る台と唇）と OLED のリブ
if (G == "L")      { color("#c9d0d8", 0.3) p_top(); color("#e07a5f") oled_brackets(); }         // OLED の L
if (G == "tsume")  { color("#e0a040", 0.3) p_floor(); color("#27ae60", 0.3) p_hatch(); color("#e07a5f") { hatch_strip(); hatch_claws(); } }   // ハッチの爪と床の帯
if (G == "uke")    { color("#c9d0d8", 0.3) p_top(); color("#e07a5f") tgl_cradle(); one("tgl"); }   // トグルの受け
if (G == "futa")   { one("hatchplate"); one("shutter"); one("lock"); }                          // 蓋・ロック・蓋の床の板
if (G == "hashira") { color("#4a90d9", 0.3) p_lwall(); color("#4a90d9", 0.3) p_rwall(); color("#e07a5f") { fasten_lwall(); fasten_rwall(); } }   // 柱と棚（壁の内面）
if (G == "mimi")   { color("#9b59b6", 0.3) p_front(); color("#27ae60", 0.3) p_hatch(); color("#e07a5f") { front_ears(); front_ears_low(); hatch_ears_top(); hatch_ears_low(); } }   // 耳（フロント 4・ハッチ 3）
if (G == "tub")    { at_btn() { btn3_tub(); btn3_switch(); btn3_sw_screws(); btn3_v_screws(); } color("#c9d0d8", 0.3) at_btn() btn3_station_add(); }   // 会話ボタンのバスタブと腕
if (G == "uke_tc") { color("#e0a040", 0.3) p_floor(); color("#4a90d9", 0.3) p_lwall(); color("#e07a5f") { tc_seat(); tc_press(); } one("tc"); }   // Type-C 基板の受けと押さえ
