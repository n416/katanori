// ナット／ねじの口の検査の呼び出し口（tools/nutpath_chk.py が使う）。case_v6_1.scad は触らない。
//   口から外へ道を掃き、**その口を使う場面の世界**と交わりを取る。0 が正。
//   2026-09-18 に組み直した。旧 part="nutpath"（case_v6_1.scad）は スピーカーの 2 口だけを「全部が同時に在る」世界に当てていた。
//   NP_MODE="list"  → 口の表を echo（名前・種類・口の芯・向き・長さ・使う場面）
//          "probe" → NP_ID の道だけ / "scene" → NP_SCENE の世界だけ / "tok" → NP_TOK の 1 部品だけ
//          "hit"   → 道 ∩ 世界（NP_TOK が空なら場面ぜんぶ・あれば その 1 部品 ＝ 誰が塞いでいるか）
include <../case_v6_1.scad>
NP_MODE = ""; NP_ID = ""; NP_SCENE = ""; NP_TOK = "";
NP_L  = NUT_PATH_L;   // ナットの道の長さ（case_v6_1.scad。⚠ 誰も実測を持っていない数）
NP_DD = SCR_CB;       // ドライバー／ねじの頭が通る柱の径。既定は模型の座ぐり φ4.4（模型自身が「頭と工具に要る」と言っている径）
NP_DL = 45;           // その柱の長さ
// ---- 部品ファイルの数。use した部品の変数は見えないので、nutpath_chk.py が部品を単体で開いて echo させ、-D で渡す ----
//   （ここに数字を写さない。parts/btn_v61.scad は別の担当が編集中で、写しはすぐ古くなる）
NP_BTN = [];   // [BLK_DY, NUT_Z0, NUT_T, NUT_AF + SHRINK, SCR_X, SW_DX, Z_SCR, SEAT_H, ear_foot_z0]
NP_KNB = [];   // [SCREW_ANG, SCREW_R, Z_BOSS_BOT, NUT_POCK_AF, Z_WALL_T - SCR_CB_T]
HEAD_T = 1.6;  // M2 なべの頭の高さ（道は頭の上から始める。模型に描いてある頭に当てない）

function Wb(p) = [BTN_AT[0], BTN_AT[1], Z_TOP + TOP_T] + rotz(p, BTN_RZ);
function Wk(p) = [KNOB_AT[0], KNOB_AT[1], Z_TOP + TOP_T] + rotz(p, KNOB_RZ);
SLOT = ["box", NUT_AF + 0.1, NUT_T];            // 横差しの溝の断面（溝の幅 × ナットの厚み）
HEXC = ["hex", (NUT_AF + 0.1) / cos(30)];
DRV  = ["cyl", NP_DD];

// ⭐ 2026-09-18 pt_tap（「ナイロンの左前はタッピング」の決め打ち）を捨てた。
//   模型側のタッピングは無くなった（上の柱 4 本ともナット。case_v6_1.scad の post_t）。
//   さらに、同じ規則をここと模型の 2 か所に書くのがそもそも間違いだった。
//   4 本とも口として测れば、溝の無い柱は「口が塞がっている」として自分で出る。
//   NPTAP は python 側の約束なので空で残す
function pt_zmid(p) = Z_TOP - (p[2] ? EAR_T : 0) - POST_T_SKIN - NUT_T / 2;
function pt_org(p)  = post_front(p) ? [(p[0] < IN_X / 2) ? p[0] + post_w(p) : p[0], post_t_y0(p) + post_dy(p) / 2, pt_zmid(p)]   // ⭐ 2026-09-18 Y は post_t_y0（左前は前の壁へ 0.8 食い込んでいる）
                                    : [post_cx(p), p[1], pt_zmid(p)];
function pt_dir(p)  = post_front(p) ? [(p[0] < IN_X / 2) ? 1 : -1, 0, 0] : [0, -1, 0];
function hubn_dir(i) = [cos(hub_nut_ang(i)), sin(hub_nut_ang(i)), 0];

// ---- 口を使う場面（🔒 ユーザー 2026-09-18 の組む順から私が読んだ物。違っていたらここを直す）----
//   場面の名前は下の np_scene()。**どれか 1 つの場面で空いていれば正**（ナットはねじを締める前ならいつ入れてもよい）
//   レジン: ① 電池 ② PCB ③ 手前のねじ ④ 壁を仮締め ⑤⑥ 開いて ReSpeaker・OLED のライザー ⑦⑧ 閉じて本締め ⑨ 天板 ⑩ フロント ⑪ ハッチ
//   ナイロン: PCB → トグル → ReSpeaker → OLED → 電池 → 蓋
W_WALL_L = ["deskWL", "top"]; W_WALL_R = ["deskWR", "top"];   // 壁に付いた口: 壁を机の上で持っているとき／壁を閉じて天板を載せる前
W_DESK0 = ["desk0"]; W_DESK1 = ["desk1"]; W_DESK2 = ["desk2"];
function w_pt(i) = nylon() ? ["hub", "lid"] : ((i == 0 || i == 2) ? W_WALL_L : W_WALL_R);

// [名前, 種類 nut/drv, 口の芯（世界）, 向き, 断面, 長さ, 回し（縦の道だけ）, 使う場面, 説明]
PROBES = concat(
    [for (i = [0 : 3]) [str("pt", i), "nut", pt_org(POSTS_T[i]), pt_dir(POSTS_T[i]), SLOT, NP_L, 0, w_pt(i), "上の柱のナット"]],
    nylon() ? [] : [for (i = [0 : 3]) let (p = POSTS_B[i], c = post_c(p), fr = post_front(p))   // 前 2 本は口が前板側（−Y）・後ろ 2 本（壁の羽）はハッチ側（+Y）
        [str("pb", i), "nut", [c[0], fr ? p[1] : p[1] + post_dy(p), POST_B_H - POST_B_SKIN - NUT_T / 2], [0, fr ? -1 : 1, 0], SLOT, NP_L, 0,
         concat((i == 0 || i == 3) ? W_WALL_L : W_WALL_R, [fr ? "front" : "hatch"]), fr ? "前の下の柱のナット（口は前板側）" : "壁の羽のナット（口はハッチ側）"]],
    nylon() ? [for (i = [0, 1, 3]) let (h = HUB_HOLES_W[i])
                [str("hubn", i), "nut", [h[0], h[1], HUB_AT[2] - HUB_NUT_SKIN - NUT_T / 2] + (HUB_POST_D / 2) * hubn_dir(i), hubn_dir(i), SLOT, NP_L, 0, ["hub"], "PCB の柱のナット（横差し）"]]
            : [for (i = [0, 1]) let (h = HUB_HOLES_W[i])   // レジンの後ろ 2 本は床の裏から（pb2 pb3・dpb2 dpb3）
                [str("hubn", i), "nut", [h[0], h[1], -FLOOR_T], [0, 0, -1], HEXC, NP_L, 30, ["s3"], "PCB のねじのナット（床の裏）"]],
    nylon() ? [["fs", "nut", [HUB_HOLES_W[2][0], IN_Y - RAIL_W_R, FS_Z0 + FS_FLOOR + NUT_T / 2], [0, 1, 0], SLOT, NP_L, 0, W_DESK2, "フラップの座のナット（口は後ろ）"]]
            : [["hf", "nut", [HSCR_X[0], IN_Y - HFOOT_D, HFOOT_FLOOR + NUT_T / 2], [0, -1, 0], SLOT, NP_L, 0, ["deskH"], "ハッチの足のナット（口は前）"]],
    len(NP_BTN) == 0 ? [] : concat(
        // ⭐ 2026-09-18: 口は**内側（バスタブ側）**（🔒 ユーザー「ナットの入口を内側に」）。バスタブを付ける前に差すので場面は desk0（板だけ。ブロックは天板の一部）
        [for (s = [1, -1]) [s > 0 ? "btnvP" : "btnvM", "nut", Wb([s * btn3_blk_xi(), NP_BTN[0], NP_BTN[1] + NP_BTN[2] / 2]), rotz([-s, 0, 0], BTN_RZ), ["box", NP_BTN[3], NP_BTN[2]], NP_L, 0, W_DESK0, "会話ボタンの縦ねじのナット（ブロックの内面から・バスタブの前）"]],
        [for (s = [1, -1]) [s > 0 ? "btnsP" : "btnsM", "nut", Wb([s * NP_BTN[4] + NP_BTN[5], btn3_tub_y1(), NP_BTN[6]]), rotz([0, 1, 0], BTN_RZ), ["cyl", NP_BTN[3] / cos(30)], NP_L, 0, W_DESK1, "会話ボタンのスイッチねじのナット"]],
        [for (s = [1, -1]) [s > 0 ? "dbtnsP" : "dbtnsM", "drv", Wb([s * NP_BTN[4] + NP_BTN[5], btn3_tub_y0() + NP_BTN[7] - HEAD_T, NP_BTN[6]]), rotz([0, -1, 0], BTN_RZ), DRV, NP_DL, 0, W_DESK2, "会話ボタンのスイッチねじ"]],
        [for (s = [1, -1]) [s > 0 ? "dbtnvP" : "dbtnvM", "drv", Wb([s * btn3_v_scr_x(), NP_BTN[0], NP_BTN[8]]), [0, 0, -1], DRV, NP_DL, 0, W_DESK2, "会話ボタンの縦ねじ（バスタブの底から）"]]),
    len(NP_KNB) == 0 ? [] : concat(
        [for (k = [0, 1]) [str("knobn", k), "nut", Wk(rotz([NP_KNB[1], 0, NP_KNB[2]], NP_KNB[0][k])), [0, 0, -1], ["hex", NP_KNB[3] / cos(30)], NP_L, 30 + NP_KNB[0][k] + KNOB_RZ, W_DESK0, "つまみの島のナット（天板の裏から）"]],
        [for (k = [0, 1]) [str("dknob", k), "drv", Wk(rotz([NP_KNB[1], 0, NP_KNB[4] + HEAD_T], NP_KNB[0][k])), [0, 0, 1], DRV, NP_DL, 0, W_DESK0, "つまみの島のねじ（持ち手を付ける前）"]]),
    // ---- PCB のねじ ----
    [for (i = [0 : 3]) if (nylon() || i < 2) let (h = HUB_HOLES_W[i], below = nylon() && i >= 2)   // レジンの後ろ 2 本は床の裏から（dpb2 dpb3 が見る）。ナイロンの後ろ 2 本も床の裏から
        [str("dhub", i), "drv", [h[0], h[1], below ? -FLOOR_T : HUB_AT[2] + 1.6 + HEAD_T], [0, 0, below ? -1 : 1], DRV, NP_DL, 0,
         nylon() ? [below ? "done" : "rsp"] : ["s3"], "PCB のねじ"]],
    [for (i = [0 : 3]) let (p = POSTS_T[i]) [str("dtop", i), "drv", [post_cx(p), p[1] + post_dy(p) / 2, Z_TOP + TOP_T], [0, 0, 1], DRV, NP_DL, 0, ["done"], "天板のねじ"]],
    nylon() ? [] : [for (i = [0 : 3]) let (c = post_c(POSTS_B[i])) [str("dpb", i), "drv", [c[0], c[1], -FLOOR_T], [0, 0, -1], DRV, NP_DL, 0, ["done"], i < 2 ? "前の下の柱のねじ（床の裏から）" : "壁の羽のねじ（床の裏から）"]],
    nylon() ? [] : [["dhf", "drv", [HSCR_X[0], HFOOT_Y, -FLOOR_T], [0, 0, -1], DRV, NP_DL, 0, ["done"], "ハッチの足のねじ（床の裏から）"]]
);
// スピーカーは部品ファイルの道をそのまま使う（spk_v61.scad は別の担当が編集中。口の芯を持たないので「最初に当たる距離」は出ない）
//   ナット: スピーカーより先に座の側から差す（🔒 ユーザー 2026-09-18）＝ 天板だけの場面
PROBES_M = [["spkn", "nut", W_DESK0, "スピーカーのナット（座の側から）"], ["dspk", "drv", W_DESK2, "スピーカーの上向きねじ（バスタブの裏から）"]];

module frame(org, d, spin) {   // 局所 +Z を道の向きに。横の道は 局所 X = 水平の幅・Y = 世界 Z
    X = abs(d[2]) < 0.5 ? [-d[1], d[0], 0] / norm([d[0], d[1]]) : rotz([1, 0, 0], spin);
    Y = cross(d, X);
    multmatrix([[X[0], Y[0], d[0], org[0]], [X[1], Y[1], d[1], org[1]], [X[2], Y[2], d[2], org[2]], [0, 0, 0, 1]]) children();
}
EPS = 0.02;   // 口の面と同じ平面に乗せない
module sect(sec, len) translate([0, 0, EPS]) {
    if (sec[0] == "box") translate([-sec[1] / 2, -sec[2] / 2, 0]) cube([sec[1], sec[2], len - EPS]);
    if (sec[0] == "hex") cylinder(d = sec[1], h = len - EPS, $fn = 6);
    if (sec[0] == "cyl") cylinder(d = sec[1], h = len - EPS, $fn = 32);
}
module np_probe(id) {
    for (q = PROBES) if (q[0] == id) frame(q[2], q[3], q[6]) sect(q[4], q[5]);
    if (id == "spkn") at_spk() spk_nut_path(NP_L);
    if (id == "dspk") at_spk() difference() { spk_driver_probe(NP_DD, NP_DL); spk_tub_screws(); }   // 道はバスタブの板の裏から始まるが、頭は板の裏から 0.5 出ている。そのねじ自身を道から引く（引かないと自分の頭 5.7mm³ × 2 に当たる）
}

// ---- 世界 ----
// 箱と「先に入っている物」は case_v6_1.scad の world_for_*()（掃引と同じ出どころ。格子も world_box() が持つ）。
module np_plate() { if (nylon()) lid(); else p_top(); }   // 机の上で小組を載せる板（ナイロンは蓋 ＝ 天板＋左の板）
module np_scene(s) {
    if (s == "bat")   world_for_bat();
    if (s == "hub")   world_for_hub();
    if (s == "rsp")   world_for_rsp();
    if (s == "oled")  world_for_oled();
    if (s == "lid")   world_for_lid();
    if (s == "s3")    { p_floor(); one("bat"); one("hub"); }   // レジン ③ 手前のねじ: 床＋電池＋PCB。壁はまだ無い（world_for_* にこの場面は無い）
    if (s == "lwall") world_for_lwall();
    if (s == "rwall") world_for_rwall();
    if (s == "top")   world_for_top();                       // ⑧ 壁を閉じて本締め・天板の前
    if (s == "front") world_for_front();
    if (s == "hatch") world_for_hatch();
    if (s == "done")  { for (n = UNITS) one(n); if (nylon()) { shell(); lid(); } else { p_floor(); p_top(); p_lwall(); p_rwall(); p_front(); p_hatch(); ribs(); } }   // 組み上がり。トグルはどの場面にも置かない（🔒 ユーザー 2026-09-18）
    if (s == "desk0") np_plate();                                        // 机: 板だけ
    if (s == "desk1") { np_plate(); lid_units(tub = false); }           // 机: 板＋つまみ・会話ボタン・スピーカー（バスタブの前）
    if (s == "desk2") { np_plate(); lid_units(); }                       // 机: 板＋小組ぜんぶ
    if (s == "deskH") { p_hatch(); panel_ribs("hatch"); }                // 机: ハッチだけ
    if (s == "deskWL") { p_lwall(); panel_ribs("lwall"); }               // 机: 左の壁だけ
    if (s == "deskWR") { p_rwall(); panel_ribs("rwall"); }
}
// 誰が塞いでいるか（当たった口だけ、部品 1 つずつに当て直す）
NP_TOKS = concat(nylon() ? ["shell", "lid"] : ["floor", "top", "lwall", "rwall", "front", "hatch", "ribs"],
                 [for (n = UNITS) str("u:", n)], ["knob"]);
module np_tok(t) {
    if (t == "floor") p_floor();  if (t == "top") p_top();      if (t == "lwall") p_lwall();
    if (t == "rwall") p_rwall();  if (t == "front") p_front();  if (t == "hatch") p_hatch();
    if (t == "ribs") ribs();      if (t == "shell") shell();    if (t == "lid") lid();
    if (t == "knob") { at_knob() for (g = KNOB61_GROUPS) knob_group(g); knob61_shaft(); }
    for (n = UNITS) if (t == str("u:", n)) one(n);
}

if (NP_MODE == "list") {
    echo(NPLIST = concat([for (q = PROBES) [q[0], q[1], q[2], q[3], q[5], q[7], q[8]]], [for (q = PROBES_M) [q[0], q[1], [], [], 0, q[2], q[3]]]));
    echo(NPTOKS = NP_TOKS);
    echo(NPTAP = []);   // ⭐ 2026-09-18 タッピングは無い。溝の欠けは上の pt* が「塞がっている」で拾う
}
if (NP_MODE == "probe") np_probe(NP_ID);
if (NP_MODE == "scene") np_scene(NP_SCENE);
if (NP_MODE == "tok")   np_tok(NP_TOK);
if (NP_MODE == "hit")   intersection() { np_probe(NP_ID); if (NP_TOK == "") np_scene(NP_SCENE); else intersection() { np_tok(NP_TOK); np_scene(NP_SCENE); } }
