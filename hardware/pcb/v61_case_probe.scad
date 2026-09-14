// v6.1 の板の数字を筐体（case_v6_1.scad）から取り直す道具。2026-09-14
//   "C:/Program Files/OpenSCAD (Nightly)/openscad.exe" --backend=manifold -o x.echo hardware/pcb/v61_case_probe.scad
// 出た値を v61_board.py と突き合わせる（板の座標 = 世界 − (2.0, 13.5)）
part = "none";
include <../case_v6_1.scad>
echo(str("PCB x0=", HUB_AT[0], " x1=", HUB_AT[0] + PCB_L, " y0=", PCB_Y0, " y1=", PCB_Y1, " L=", PCB_L, " W=", PCB_W, " zbot=", HUB_AT[2]));
echo(str("USBC y=", USBC_Y, " sz=", USBC_SZ, " out=", USBC_OUT, " portC=", USBC_PORT_C));
echo(str("KNOB=", KNOB_AT, " as_ic_z=", AS_IC_Z, " mag_z0=", MAG61_Z0));
echo(str("HOLES=", HUB_HOLES_W));
echo(str("RSP_X=", RSP_X, " rspL=", respeaker_L(), " IN_X=", IN_X, " WALL=", WALL));
