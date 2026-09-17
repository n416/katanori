// 掃引検査の外部呼び出し口（tools/sweep_chk.py が使う）。case_v6_1.scad は触らない。
//   SW_MODE="mover" → 動かす物を素の位置で出す / "world" → 相手を出す / "hit" → SW_Q の姿勢で交わりを取る
include <../case_v6_1.scad>
SW_MOVER = ""; SW_WORLD = ""; SW_MODE = ""; SW_Q = [0, 0, 0, 0, 0, 0]; SW_C = [0, 0, 0];
module sw_mover() {
    if (SW_MOVER == "hub")  hub_unit();
    if (SW_MOVER == "rsp")  { one("rsp");  one("riser"); }
    if (SW_MOVER == "oled") { one("oled"); one("oriser"); }
    if (SW_MOVER == "bat")  one("bat");
    if (SW_MOVER == "lidmain") { p_top(); lid_units(); }              // 天板と天板に付く物（真下へ降りる）
    if (SW_MOVER == "lidflap") { lwall_flap(); flap_seat(); }         // 左の L 字（降りるあいだ外へ 1.5 たわむ）
}
module sw_world() {
    if (SW_WORLD == "hub")  world_for_hub();
    if (SW_WORLD == "rsp")  world_for_rsp();
    if (SW_WORLD == "oled") world_for_oled();
    if (SW_WORLD == "bat")  world_for_bat();
    if (SW_WORLD == "lidmain" || SW_WORLD == "lidflap") world_for_lid();
}
if (SW_MODE == "mover") sw_mover();
if (SW_MODE == "world") sw_world();
if (SW_MODE == "hit")   intersection() { at_pose(SW_Q, SW_C) sw_mover(); sw_world(); }
// 道・回す中心・端までの長さ（case_v6_1.scad が唯一の出どころ）
if (SW_MODE == "pose") echo(SWPOSE = [["hub",  PATH_HUB,  hub_c(), hub_r()],
                                      ["rsp",  PATH_RSP,  [0, 0, 0], 0],
                                      ["oled", PATH_OLED, [0, 0, 0], 0],
                                      ["bat",  PATH_BAT,  [0, 0, 0], 0],
                                      ["lidmain", PATH_LIDMAIN, [0, 0, 0], 0],
                                      ["lidflap", PATH_LIDFLAP, [0, 0, 0], 0]]);
