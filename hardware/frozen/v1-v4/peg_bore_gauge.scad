// ダボ径と軸受け径の現物合わせゲージ v2
//
// v1 の失敗（2026-08-05・刷る前にユーザー指摘）:
//   98mmのバーにダボを生やしていた。試す穴は**台座側**にあるので、ダボは1本ずつ
//   持って挿せなければテストできない。磁石ゲージ（ゲージ側に穴がある）と混同した設計ミス。
//   バー自体も無駄に大きかった。
//
// v2: 磁石ゲージと同じ「ニッパーで切れる桟」方式。
//   - ダボ5本: それぞれ**持ち手タブ付き**。桟（高さ1.5）を切って1本ずつにする
//   - リング4個: 桟で連結。切り離さなくても軸を挿せる（外径も内径順に大きい）
//
// 使い方（番号 = 印の点の数。どちらも細い→太いの順）:
//   1. ダボを桟から切り離し、台座の**手前の2穴（ロック用・深さ4mm）**に順に挿す。
//      ⚠ 奥の2穴（ブリッジ用）は深さ2.8mmしかなく、ダボ3.5mmが底当たりして浮く。
//      点1=3.0 / 点2=3.1 / 点3=3.2 / 点4=3.3 / 点5=3.4
//      → 「少し力で入り、ガタつかない」いちばん太いダボの**点の数**
//   2. リングにつまみの軸を上から挿して回す。
//      点1=6.2 / 点2=6.3 / 点3=6.4 / 点4=6.5
//      → 「軽く回り、ガタを感じない」いちばん小さいリングの**点の数**
//      いま書き出してある橋は 6.4（点3相当）。点3が正解ならそのまま刷ってよい
//
// ⚠ 印刷設定は本番と同じ（レジン①・0.05mm・2.5s・初期層5層/35s）。
// 印刷: 直置き・サポート不要。部品は全部小さく、桟は細いので剥がすのは楽。
//
// 出力:
//   openscad -o hardware/peg_bore_gauge.stl hardware/peg_bore_gauge.scad

$fn = 96;

PEGS  = [3.0, 3.1, 3.2, 3.3, 3.4];
PEG_L = 3.5;     // ロックのほぞと同じ（as5600_holder.scad の LOCK_PEG_L）
TAB_X = 9.0;     // 持ち手タブ（つまむところ）
TAB_Y = 6.0;     // ⚠ 6以下にすること。台座の隅のボス（穴の脇・高さ3mm）と当たらない上限
TAB_T = 2.5;
PEG_PITCH = 12.0;

BORES  = [6.2, 6.3, 6.4, 6.5];
RING_H = 6.0;    // 橋のデッキ厚と同じ（knob_jig.scad の DECK_T）
RING_WALL = 2.25;
RING_PITCH = 12.5;

SPRUE_W = 2.0;   // 桟。高さ1.5・ニッパーで切る（磁石ゲージと同じ）
SPRUE_H = 1.5;

// 軸受け穴の入口はボトム層で縮むので、橋と同じ逃がしを入れる（knob_jig.scad と同じ値）
RELIEF_D_ADD = 1.2;
RELIEF_H     = 0.6;

module dot() { cylinder(d = 1.0, h = 0.5); }

// ---- ダボ列（タブ＋ダボ＋点。桟で連結）----
module peg_chain() {
    for (i = [0 : len(PEGS) - 1]) {
        cx = i * PEG_PITCH;
        // 持ち手タブ
        translate([cx - TAB_X / 2, -TAB_Y / 2, 0]) cube([TAB_X, TAB_Y, TAB_T]);
        // ダボ（垂直 = ロックの印刷向きと同じ）
        translate([cx, 0, TAB_T]) cylinder(d = PEGS[i], h = PEG_L);
        // 印の点（タブの手前の縁）。y はダボ表面（最大 r1.7）から 0.1 以上離すこと。
        // 接線で接すると非多様体エッジになる（v2 の初回書き出しで実際に出た）
        for (j = [0 : i])
            translate([cx + (j - i / 2) * 1.6, -TAB_Y / 2 + 0.7, TAB_T]) dot();
        // 桟（隣のタブへ）
        if (i < len(PEGS) - 1)
            translate([cx + TAB_X / 2 - 0.1, -SPRUE_W / 2, 0])
                cube([PEG_PITCH - TAB_X + 0.2, SPRUE_W, SPRUE_H]);
    }
}

// ---- リング列（桟で連結。切り離し不要）----
module ring_chain() {
    difference() {
        union() {
            for (i = [0 : len(BORES) - 1]) {
                cx = i * RING_PITCH;
                translate([cx, 0, 0]) cylinder(d = BORES[i] + 2 * RING_WALL, h = RING_H);
                // 印の点（リングの上面）
                for (j = [0 : i])
                    translate([cx, 0, 0]) rotate([0, 0, 90 + (j - i / 2) * 18])
                        translate([BORES[i] / 2 + RING_WALL / 2, 0, RING_H]) dot();
                if (i < len(BORES) - 1)
                    translate([cx, -SPRUE_W / 2, 0])
                        cube([RING_PITCH, SPRUE_W, SPRUE_H]);
            }
        }
        for (i = [0 : len(BORES) - 1]) {
            translate([i * RING_PITCH, 0, -1])
                cylinder(d = BORES[i], h = RING_H + 2);
            // 入口逃がし（プレート側）
            translate([i * RING_PITCH, 0, -0.01])
                cylinder(d = BORES[i] + RELIEF_D_ADD, h = RELIEF_H);
        }
    }
}

peg_chain();
translate([2, 16, 0]) ring_chain();
