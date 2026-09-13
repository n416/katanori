// ============================================================
// 並べ替えの提案（2026-09-13）で使う「単位」の共通定義
//   ハブ基板・PowerBoost・電流計・OLED 2.42" は入れない（ユーザーの条件）。
//   v5 の部品（ReSpeaker＋XIAO・電池・Type-C・つまみ v5・会話ボタン v3・スピーカー v5・トグル・リード）と
//   v6 の小さい OLED（1.54"・HS154L03W2C01）を、parts/ の実模型のまま呼ぶ。
//
//   局所の約束（case_v5 と同じ）:
//     u_knob / u_btn / u_spk / u_tgl … z0 = 板の外面・+Z が外。板の中へ沈む深さは下の関数
//     u_rsp   … respeaker_lite() そのまま（X 0〜82 板の長さ・Z 0〜34 板の高さ・Y 0〜1.85 板厚。XIAO 面が −Y・マイク面が +Y・XIAO の USB は x 0 端・ジャックは x 82 端）
//     u_bat   … 50 × 35 × 6 の角が原点
//     u_tc    … 秋月 Type-C 基板。板の左下が原点・口は +Y・部品面 +Z
//     u_oled  … 1.54" OLED。板の中心が原点・板 z 0〜1.0・ガラス z 1.0〜2.65（+Z が見る側）
//   口（皮に開ける穴）は c_* で同じ局所座標に置く。皮は各案のファイルが持つ。
// ============================================================
use <../parts/parts.scad>
use <../parts/respeaker_lite.scad>
use <../parts/typec_115426.scad>
use <../parts/btn_v3.scad>
use <../parts/knob_v5.scad>
use <../parts/spk_v5.scad>

// ---- 数字（parts/ の関数から。ここに直書きしない）----
function cu_rsp_len()   = respeaker_L();          // 82.024
function cu_rsp_h()     = respeaker_H();          // 34.007
function cu_rsp_t()     = respeaker_T();          // 1.85
function cu_rsp_xiao_out() = xiao_usb_out();      // 1.53  XIAO の USB-C が板の端から出る量（x 0 端）
function cu_rsp_jack_out() = 83.60 - 82.024;      // 1.576 ジャックの筒が板の端から出る量（x 82 端・📄 STEP）
function cu_rsp_back()  = respeaker_xiao_head() + 3.6;   // 17.5  XIAO 面から DuPont の頭 13.9 ＋ 線の曲がり 3.6（respeaker_xiao_housings の bend）。2026-09-13 に模型の bbox で確かめた
function cu_rsp_front() = 2.6;                    // マイク面の部品の頭（模型の bbox: 面から 2.59。2026-09-13 に測った。D1 の 1.185 より高い物が載っている）
function cu_rsp_mic_x() = [5.0, 77.0];            // ⚠ マイク U4/U5 の x（両端。docs/RESPEAKER-LITE.md の「マイク面の両端」から置いた概数）
function cu_rsp_jack_yz() = [6.502, -2.485];      // ジャックの筒の芯（板の下端から z・XIAO 面から −y）📄
function cu_rsp_usb_z()   = xiao_usb_yz()[1];     // XIAO の USB-C の中心の z
function cu_bat()   = lipo_size();                // [50, 35, 6]
function cu_tc()    = tc_size();                  // [20, 15, 1.6]
function cu_tc_mouth_y() = tc_nose_y();           // 15.8
function cu_tc_zc() = tc_conn_zc();               // 3.23
function cu_knob_deep() = 22.4;                   // つまみ v5 の板の外面から下端（吊りの板の裏 −22.4・knob_v5 Z_HANG_BOT）
function cu_knob_pad()  = [32.0, 39.0, -16.7];    // 台座の足跡 X 32 × Y 39（y −16.7〜+22.3）
function cu_knob_grip() = [27.0, 5.5];            // 持ち手 φ27・外へ 5.5
function cu_btn_deep()  = 15.085;                 // 会話ボタン v3 のバスタブの底
function cu_btn_head()  = [18.0, 12.0, 3.0];      // 頭 18 × 12・外へ 3.0
function cu_btn_tub()   = [18.2 + 6.0, 9.9 + 4.0];   // バスタブ＋耳の足跡（⚠ 概数。耳は ±X に出る）
function cu_spk_deep()  = 10.2;                   // スピーカー v5 のバスタブ 3 の底
function cu_spk_foot()  = [34.0, 20.0];           // 手・バスタブ 3 込みの足跡（⚠ 概数）
function cu_tgl_deep()  = mts102_deep();          // 18 胴 12 ＋ 端子 6
function cu_tgl_body()  = [mts102_w(), mts102_d()];   // 13 × 8
function cu_oled_pcb()  = [42.40, 38.00, 1.00];   // 📄 HS154L03W2C01
function cu_oled_glass()= [40.04, 27.22, 1.65];   // 📄
function cu_oled_holes()= [37.40, 33.00, 3.0];    // 📄 穴の中心間と径
function cu_oled_t()    = 2.65;

// ---- 単位（部品そのもの）----
module u_rsp(dupont = true) { respeaker_lite(); if (dupont) respeaker_xiao_housings(true, 10.0); }   // 線の DuPont（頭 13.9）込み。dupont=false で XIAO のピンの先 9.9 まで
function cu_rsp_back_pins() = respeaker_xiao_head() - 10.0 + 6.0;   // 9.9  DuPont を挿さないときの XIAO 面の高さ（XIAO 1.4 ＋ 樹脂 2.5 ＋ ピン 6.0）
module u_bat() lipo_1000mah();
module u_tc()  typec_115426(pins = false);
module u_knob() assembly(show_deck = false);      // knob_v5: 島・つまみ・柱・基板・E リング・磁石・吊り
module u_btn() { btn3_piston(); btn3_tub(); btn3_switch(); btn3_sw_screws(); btn3_v_screws(); }
module u_spk() { spk_body(); spk_tub_all(); }
module u_tgl() mts102(ang = 15);                  // ON-ON なので必ずどちらかに倒れている
module u_oled() {
    p = cu_oled_pcb(); g = cu_oled_glass(); h = cu_oled_holes();
    color("#7f77dd", 0.9) difference() {
        translate([-p[0] / 2, -p[1] / 2, 0]) cube(p);
        for (sx = [-1, 1], sy = [-1, 1]) translate([sx * h[0] / 2, sy * h[1] / 2, -1]) cylinder(d = h[2], h = p[2] + 2, $fn = 24);
    }
    color("#20243a", 0.95) translate([-g[0] / 2, -g[1] / 2, p[2]]) cube(g);
}

// ---- 薄いつまみ（🔒 ユーザー 2026-09-13「会話ボタンと同じ高さに」「PCB 基板を作るから DuPont も要らないし、バスタブ 2 も不要」）----
//   皿は v6 の数字（φ28.5・外へ 2.5・スカート φ12.6 が板の穴 φ12.85 の中で回る・皿とハブで板を挟んで抜け止め: frozen/v6/_v6_gear.scad の KN_*）。
//   軸は板の裏のハブから磁石まで。磁石（φ4 × 2）の下面は AS5600 の IC の上 1.0（v5 の CHIP_GAP 1.1 と同じ考え）。
//   AS5600 は自作基板に直付け（モジュール・ヘッダ・DuPont・吊りのバスタブ 2 は無い）。基板の裏を pcb_bot に置く。既定は会話ボタンのバスタブの底 −15.085。
//   ⚠ 皿の回り止め・ハブの留め方・基板の留め方は描いていない（v6 の A1〜A4 をそのまま使う前提）
KF_DISH_D = 28.5; KF_DISH_T = 2.5; KF_SKIRT_D = 12.6; KF_BORE_D = 12.85; KF_HUB_D = 16.0; KF_HUB_T = 1.5; KF_STEM_D = 7.0;
KF_MAG_D = 4.0; KF_MAG_T = 2.0; KF_GAP = 1.0; KF_IC = [5.0, 4.0, 1.1]; KF_PCB = [30.0, 30.0, 1.6];
function cu_kflat_deep(pcb_bot = -15.085) = -pcb_bot;   // 単位の底 ＝ 基板の裏
module u_knob_flat(pcb_bot = -15.085, deck_t = 2.5) {
    pcb_top = pcb_bot + KF_PCB[2]; ic_top = pcb_top + KF_IC[2]; mag_bot = ic_top + KF_GAP; hub_top = -deck_t - 0.25;
    color("#c9ccd2") difference() { cylinder(d = KF_DISH_D, h = KF_DISH_T); translate([0, 0, KF_DISH_T - 0.8]) cylinder(d = KF_DISH_D - 6, h = 1); }   // 皿（上面のへこみ 0.8）
    color("#c9ccd2") translate([0, 0, hub_top]) cylinder(d = KF_SKIRT_D, h = -hub_top + 0.01);                                                    // スカート（板の穴の中）
    color("#e0a040") translate([0, 0, hub_top - KF_HUB_T]) cylinder(d = KF_HUB_D, h = KF_HUB_T);                                                  // ハブ（板の裏・皿と挟む）
    color("#e0a040") translate([0, 0, mag_bot + KF_MAG_T - 0.01]) cylinder(d = KF_STEM_D, h = hub_top - KF_HUB_T - (mag_bot + KF_MAG_T) + 0.02);   // 軸
    color("#bbb") translate([0, 0, mag_bot]) cylinder(d = KF_MAG_D, h = KF_MAG_T);                                                                 // 磁石
    color("#333") translate([-KF_IC[0] / 2, -KF_IC[1] / 2, pcb_top]) cube(KF_IC);                                                                  // AS5600（IC・自作基板の上）
    color("#2b6b3f") translate([-KF_PCB[0] / 2, -KF_PCB[1] / 2, pcb_bot]) cube(KF_PCB);                                                            // 自作基板 ⚠ 大きさは仮
}
module c_knob_flat(t = 10) { cylinder(d = KF_BORE_D, h = 2 * t, center = true, $fn = 48); }   // スカートが回る穴

// ---- 口（皮から引く形。局所は単位と同じ・+Z が外。t は皮の厚みより大きく取る）----
module c_knob(t = 10)  { cylinder(d = 12.0, h = 2 * t, center = true, $fn = 48); }     // 軸が通る穴（台座の詳細は knob_station_cut の仕事）
module c_btn(t = 10)   { h = cu_btn_head(); linear_extrude(2 * t, center = true) offset(r = 2.3) offset(delta = -2.0) square([h[0] + 0.8, h[1] + 0.8], center = true); }
module c_spk(t = 10)   { spk_grille(); }                                               // spk_v5 のハニカム（板の内面から外へ抜ける）
module c_tgl(t = 10)   { mts102_hole(2 * t); translate([0, 0, -2 * t]) mts102_hole(2 * t); }
module c_oled(t = 10)  { g = cu_oled_glass(); translate([0, 0, 0]) linear_extrude(2 * t, center = true) square([g[0] + 0.6, g[1] + 0.6], center = true); }
module c_usbc(t = 10)  { linear_extrude(2 * t, center = true) offset(r = 1.6) square([9.5 - 3.2, 3.8 - 3.2], center = true); }   // 9.5 × 3.8 の小判（XIAO・Type-C 共通）
module c_jack(t = 10)  { cylinder(d = 6.5, h = 2 * t, center = true, $fn = 32); }
module c_mic(t = 10)   { linear_extrude(2 * t, center = true) offset(r = 0.6) square([6.0 - 1.2, 1.4 - 1.2], center = true); }   // マイクの細長い口 6 × 1.4
