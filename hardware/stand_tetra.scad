// 4面体の枠（2026-08-08・ユーザー案「2つのねじで立体的な4面体の枠」）
//
// 🔴 初版は頂点に球を置いて包む作りにしたため、丸い棒と直径9.2mmの玉が出た。
//    ユーザー「幾何学的な形にしてほしかったのに」。**4面体を張りに行っていなかった。**
//    この版は 4頂点から本物の四面体を張り、**4つの面それぞれに三角の窓を開ける**。
//    稜は平面で構成され、角が立つ。丸みは一切入れていない。
//
// 頂点は4つ:
//   A … 基板の取付穴A（📄左から2.492 / 下から31.577 / φ2.20）。マイク面で切って座にする
//   B … v17の貫通ネジの頭の座（基板系 y=5.6 / 左から60.202 / 下から2.657）。
//       **穴Bは基板を落とすとクレードルの中に入って掴めない。** その代わり、
//       クレードルを貫通したネジの頭がここに出るので、同じネジで枠も留める
//   C … 土台の前・左寄り ／ D … 土台の前・右寄り（どちらも世界z=BASE_Tで切って足にする）
//
// ⚠ 枠は**前（マイク面）側にしか組めない。** 裏は左から2〜20にXIAO＋ヘッダーが
//    高さ10で立っていて、A→Bの線がそこを突き抜ける。前側は📄公式CADで確認済み:
//    A–Bの線は左マイク（下から15.25〜18.75）の高さで下から約29、
//    D1・LED1（14.27〜17.95）の高さで約12.8 を通り、どれにも掛からない
//
// ⚠ 未解決: 稜が v16/v17 の前壁（高さ13.5）と 486mm³ 取り合う。
//    前壁を低い返し(z5)に戻して前倒れを枠に持たせるか、枠を前へ膨らませるか、未決定
//
//   openscad -o tetra.png --render stand_tetra.scad

include <stand_seat_test.scad>
show = "none";

SHOW_TETRA = "assembly";   // "assembly" | "part" | "check"

WIN_K   = 7.0;    // 面に開ける三角の窓の寄せ量（稜の太さを決める）
PAD_T   = 3.0;    // Bのネジ座のパッドの厚み
SCREW_D = 2.4;

MIC_FACE  = BOARD_Y + respeaker_T();   // 基板のマイク面（前）
XIAO_FACE = BOARD_Y;                   // 基板のXIAO面（後ろ）

// ---- v19: トラスを**後ろ（XIAO面側）**へ回す（2026-08-08・ユーザー案）----
// 前に置いていたときは、基板の自重（重心は支点より約4.9mm後ろ）が足を**浮かせる**
// 向きに働き、軽い枠(1〜2g)では重い基板(15g前後)を押さえられなかった＝後ろへ倒れる。
// 後ろへ回すと自重がトラスを押し、足をベースへ**押し付ける**。向きが逆になる。
// 前のネジは角度を作る役ではなく、基板をトラスへ引き付けて浮き上がりと
// ケーブルの前押しを止める役。**角度はトラスの当たり面が決める**
// 📄裏の留め先は両方無地: 穴Aの裏はXIAO上端(約25.7)より上、穴Bの裏は最寄りC16が下から6.07
V_A = [ 2.492, XIAO_FACE + 2.0, 31.577];   // 面より前へ出しておき、面で切って座にする
V_B = [60.202, XIAO_FACE + 2.0,  2.657];
V_C = [ -4.0, -20.0, 4.0];                 // 足は基板の後ろ（世界yで負）
V_D = [ 70.0, -20.0, 4.0];
P   = [V_A, V_B, V_C, V_D];
FACES = [[0,1,2], [0,1,3], [0,2,3], [1,2,3]];

function unit(v) = v / norm(v);
function fcent(f) = (P[f[0]] + P[f[1]] + P[f[2]]) / 3;
function opposite(f) = [for (i = [0:3]) if (i != f[0] && i != f[1] && i != f[2]) i][0];

module pt(p) { translate(p) cube(0.002, center = true); }

// 四面体そのもの（4点のhull＝平面4枚・稜6本の正しい多面体）
module tetra_solid() { hull() for (p = P) pt(p); }

// 面 f に開ける三角の窓。3頂点を面の重心へ WIN_K 寄せ、**面の法線**方向へ突き抜けさせる
// ⚠ 掘る向きは必ず法線。「重心→対頂点」で掘ると斜めに突き抜けて隣の稜まで削る
//    （2026-08-08にそれをやって、枠が薄い板1枚になった）
module face_window(f) {
    c  = fcent(f);
    nn = unit(cross(P[f[1]] - P[f[0]], P[f[2]] - P[f[0]]));
    n  = (nn * (P[opposite(f)] - c) > 0) ? nn : -nn;   // 中を向くほうに揃える
    hull() for (i = f) {
        q = P[i] + unit(c - P[i]) * WIN_K;
        pt(q + n * 200);
        pt(q - n * 200);
    }
}

// 稜を角柱で作る。立方体2つのhull＝平面で囲まれた角のある梁になる。
// ⚠ 面に窓を掘る方式は捨てた。この四面体は細長く、面によっては寄せ量で面ごと
//    消えて枠が4つに分断された（2026-08-08・Volumes:5）。**稜を作るほうが確実**
module beam(p, q, s) { hull() { translate(p) cube(s, center = true); translate(q) cube(s, center = true); } }

EDGES = [[0,1], [0,2], [0,3], [1,2], [1,3], [2,3]];
BEAM  = 4.5;

module tetra_frame() {
    difference() {
        union() {
            for (e = EDGES) beam(P[e[0]], P[e[1]], BEAM);
            for (i = [0:3]) translate(P[i]) cube(BEAM + 2.0, center = true);   // 頂点を少し太く

        }
        // ネジ2本（どちらも基板の面に垂直・マイク面側から挿す）
        translate([V_A[0], XIAO_FACE - 12, V_A[2]]) rotate([-90, 0, 0])
            cylinder(d = SCREW_D, h = 16);
        translate([V_B[0], XIAO_FACE - 12, V_B[2]]) rotate([-90, 0, 0])
            cylinder(d = SCREW_D, h = 16);
        // 座: XIAO面より前（基板側）は削る＝基板の裏に平らに当たる
        translate([-100, XIAO_FACE, -100]) cube([400, 200, 400]);
    }
}

module tetra_placed() { in_board_frame() tetra_frame(); }

// 基板＋部品を CLR だけ太らせた体積。稜がXIAOやヘッダーに当たる場所は、
// **形を変えずにここで削り取る**（2026-08-09・ユーザー指示
// 「板が当たる所を削ればいいのにそれが無駄な梁になるとしても」）。
// 梁が途中で切れて構造として用を成さなくなっても、見た目を優先する。
CLR = 1.2;
module board_clearance() {
    for (d = [[0,0,0], [CLR,0,0], [-CLR,0,0], [0,CLR,0], [0,-CLR,0], [0,0,CLR], [0,0,-CLR]])
        translate(d) board_placed();
}

module tetra_final() {
    difference() {
        tetra_placed();
        translate([-60, -60, -50]) cube([300, 200, 50 + BASE_T]);   // 足はベース上面で切る
        board_clearance();                                          // 当たる所を削る
    }
}

if (SHOW_TETRA == "assembly") {
    stand();
    board_placed();
    color("#c94") tetra_final();
} else if (SHOW_TETRA == "part") {
    tetra_final();
} else if (SHOW_TETRA == "check") {
    intersection() {
        tetra_final();
        union() { stand(); board_placed(); }
    }
}
