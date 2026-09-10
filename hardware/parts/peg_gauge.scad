// ダボとダボ穴のサンプルスケール（🔒 ユーザー 2026-09-10「ちょっとダボとダボ穴のサンプルスケール作らない？」）
// 前提: ボトム公差補償 OFF（🔒 ユーザー 2026-09-10）。
//
// 小帯の件で分かったこと（docs/PRINT.md §2）: プレートに口を向けた止まり穴は吸盤になって塞がる。径では直らない。
// だからこのゲージの穴は、実物と同じ 2 通りの向きで作る。
//   part="pegs"  … ダボの櫛。台 3.0 厚の上に φ2.7〜3.2（0.1 刻み・6 本・高さ 3.7・先の面取り 0.5）。
//                  同じ台に、天板の棒の穴と同じ「口がプレートの反対側」の止まり穴 φ2.9〜3.2（深さ 2.2）を 4 つ。
//   part="holes" … 小帯の凹みと同じ「口がプレート側」の止まり穴 φ3.0〜3.5（0.1 刻み・6 つ・深さ 2.4）に、
//                  小帯 C と同じ φ1.5 の抜き穴を天井から上面へ通した棒。
// 目印: 小さい方の端に切り欠き。上面に数字を彫る（0.4 深さ・印刷の遠い端なので出る）。
// 数字は「30」= φ3.0 のように 10 倍。
part = "pegs";   // pegs / holes

PEG_DS  = [2.7, 2.8, 2.9, 3.0, 3.1, 3.2];   // ダボ径
UP_DS   = [2.9, 3.0, 3.1, 3.2];             // 口が上の穴（天板の棒の条件）
DN_DS   = [3.0, 3.1, 3.2, 3.3, 3.4, 3.5];   // 口が下の穴（小帯の凹みの条件）
PITCH   = 7.0;
PEG_H   = 3.7;  PEG_CH = 0.5;    // 帯 B のダボと同じ面取り
UP_DEEP = 2.2;                   // 天板の棒の穴と同じ深さ
DN_DEEP = 2.4;  VENT_D = 1.5;    // 小帯 C（凹み 2.4 案）と同じ
BASE_T  = 3.0;  BAR_W = 8.0;  BAR_H = 3.1;   // 台の厚み・幅・穴の棒の高さ（小帯の足と同じ）
TXT     = 2.2;  TXT_D = 0.4;

module label(s, x, y, z) translate([x, y, z - TXT_D]) linear_extrude(TXT_D + 0.01) text(s, size = TXT, halign = "center", valign = "center", font = "Liberation Sans:style=Bold");
module notch(x, y, z) translate([x - 1.0, y - 1.0, z - 1.01]) cube([2.0, 2.0, 1.02]);   // 小さい方の端の目印

// ---- ダボの櫛 ＋ 口が上の穴 ----
module pegs() let (n = len(PEG_DS), m = len(UP_DS), L = (n + m) * PITCH + 4) difference() {
    union() {
        cube([L, BAR_W, BASE_T]);
        for (i = [0 : n - 1]) let (d = PEG_DS[i]) translate([2 + PITCH * (i + 0.5), BAR_W / 2, BASE_T - 0.01]) {
            cylinder(d = d, h = PEG_H - PEG_CH + 0.01, $fn = 32);
            translate([0, 0, PEG_H - PEG_CH]) cylinder(d1 = d, d2 = d - 2 * PEG_CH, h = PEG_CH, $fn = 32);
        }
    }
    for (i = [0 : n - 1]) label(str(round(PEG_DS[i] * 10)), 2 + PITCH * (i + 0.5), 1.4, BASE_T);
    for (j = [0 : m - 1]) let (x = 2 + PITCH * (n + j + 0.5)) {
        translate([x, BAR_W / 2, BASE_T - UP_DEEP]) cylinder(d = UP_DS[j], h = UP_DEEP + 1, $fn = 48);   // 口が上（プレートの反対側）
        label(str(round(UP_DS[j] * 10)), x, 1.4, BASE_T);
    }
    notch(0, 0, BASE_T);
}

// ---- 口が下の穴（小帯の凹み）＋ 抜き穴 ----
module holes() let (n = len(DN_DS), L = n * PITCH + 4) difference() {
    cube([L, BAR_W, BAR_H]);
    for (i = [0 : n - 1]) let (x = 2 + PITCH * (i + 0.5)) {
        translate([x, BAR_W / 2, -1]) cylinder(d = DN_DS[i], h = DN_DEEP + 1, $fn = 48);          // 口が下（プレート側）・深さ DN_DEEP
        translate([x, BAR_W / 2, DN_DEEP - 0.01]) cylinder(d = VENT_D, h = BAR_H, $fn = 24);     // 抜き穴（吸盤にしない）
        label(str(round(DN_DS[i] * 10)), x, 1.4, BAR_H);
    }
    notch(0, 0, BAR_H);
}

if (part == "pegs")  pegs();
if (part == "holes") holes();
