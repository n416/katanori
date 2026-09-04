// ============================================================
// 電池の蓋（シャッター）・ロック・磁石 —— v2 §2.8 からそのまま移植（2026-08-23）
//   🔒 2026-08-22 ユーザー「電池の蓋は使います」。形は v2 のまま。違いは置く壁が側面構造体の左の壁（別部品）になったこと
//   case_v3.scad から include する（変数を共有する）。BAT_C0/BAT_C1/WALL/BR_* は case_v3.scad 側
//   元: case_v2.scad の BAT_HOUSING 〜 shutter_backing()
// ============================================================
BAT_HOUSING = true;
SHUT_T     = 2.75;  // 板厚。磁石 2.0 ＋ 外面の肉 0.75
SHUT_EAR_T = 0.75;  // 耳の厚み。🔒 **電池の押しはここが受ける**
SHUT_LIP   = 0.70;  // リップの厚み（外面から）
SHUT_EAR   = 1.60;  // 耳の掛かり（Y 片側）
SHUT_EAR_H = 4.50;  // 耳の丈（Z）
SHUT_SLIDE = 5.50;  // 逃がすためにずらす量。⚠ 耳の丈 + 1.0。リップの上端との間に
                    //    上下 0.5 ずつの逃げが要る（0.3 だと擦って 0.600mm3 出た）
SHUT_CL    = 0.25;  // 隙間
SHUT_MARG  = 0.80;  // 開口を被る量
SHUT_BACK  = 2.20;  // 壁の内面から裏へ足す肉。⚠ 彫ると壁が 0 になるため
SHUT_R     = 2.50;  // 角丸
// 🔒 2026-09-02 実機 1525 で磁石の枠（0.10mm）が焼けなかった。6.30 → **6.80**。
//   ユーザー「帯の右側をここまで広げなくてはいけない理由はなんだろう？磁石ポケットを
//   もうちょっと内側に入れればいいんじゃないの？」→ **半分正しい**ので 7.30 から戻した。
//   ・磁石は口（v4 で X 11..47）の上には置けない。ハッチ側に相手を受ける肉が無いため。
//     置けるのは口の外に残る帯 SHUT_MARG + SHUT_EXT だけ
//   ・7.30 のときは帯 8.10 − 磁石 6.10 = 2.00 を **1.00 / 1.00 で山分け**していた。
//     蓋にとって効くのは**外周側だけ**（内側は無限に肉）。口までの数字はハッチ側の壁の話で、
//     欠けたのはそっちではない ⇒ 外周 1.00 を固定し、口までは 0.50 でよい
//   ⇒ 帯 7.60 = 磁石 6.10 + 外周 1.00 + 口まで 0.50。蓋の太りは片側 0.5mm で済む
//     （蓋 50.2 → 51.2 / 帯 X 3.65..59.85 → 3.15..60.35）。🔒 ユーザー「そうだね。6.80 で」
SHUT_EXT   = 6.80;  // 蓋を口の外へ伸ばす量。磁石の部屋を開口の外に作るため（v3 は下・v4 は左右）
// 🔴 2026-09-01 実機（1525・ELEGOO 透明）ユーザー「磁石の圧入を試したのだけどスポスポ抜けちゃう。
//   実はこれ、ノブもそうなんだ」。6.10 → **6.00**。
//   答えは既に出ていた。knob_v5.scad:257 に ✅ 2026-08-31 のユーザー実測がある:
//     旧レジン（SK本舗）… 縮み 0.1。設計 2.02 → 焼き 1.92
//     ELEGOO 透明     … **ほとんど縮まない。設計 ≒ 焼き上がり**
//   ⇒ この穴も同じ。旧レジンでは 設計 6.10 → 焼き 6.00 ＝ 磁石と同寸で圧入になっていた。
//     透明では 設計 6.10 → 焼き 6.10 ＝ 隙間 0.10 で落ちる。**焼き上がり 6.00 を作り直すには設計 6.00。**
//   ⚠ まだ緩ければ 5.95（締め代 0.05）へ。つまみは同じ理屈で 2.02 → 1.97（締め代 0.05）にして
//     「丁度入りますね。すこしキツイくらいなので丁度いいです」で当たっている（knob_v5.scad:277）。
//   🔒 レジンの銘柄が変わったらこの値は取り直す。**どのレジンで刷った物の話かを先に確かめること。**
SHUT_MAG_D = 6.00;  // 磁石の穴。✅ **2026-09-02 実機で確定**（ELEGOO・回 0540）。
                    //   ユーザー「磁石は丁度いい圧入です。取れないです」。旧 6.10 は SK本舗（縮み 0.1）の値
SHUT_MAG_H = 2.00;  // 📄 カタログ φ6 × 2.0。⚠ parts.scad の 2.15 は本人が「疑わしい・
                    //    設計に使うな」と書いている値なので使わない
SHUT_MAG_Z = (BR_ZB + BR_ZT) / 2; // 磁石の中心。ブリッジ（v3: Z 23.2〜29.3）の真ん中（v2 は 25.45 の手書き）
SHUT_MAG_DY = 12.0; // 中心から左右へ振る量（2個）
// ---- ロックパーツ（任意）。⚠ **これとネジを外せば工具なしで開く** ----
// ✅ ユーザー案（2026-08-21・絵）: **帯の幅いっぱいに広げて、両端の逃げまで覆う。**
//    **中央だけ半円で蓋の上に少し下りる。**
// 🔒 両端の脚は耳の逃げ道を塞ぐので、飾りではなく**そのままロックになる**
SHUT_LK_T   = 1.20;  // 蓋に乗る側（中央の半円）の厚み
SHUT_LK_R   = 5.00;  // 中央の半円の半径
SHUT_LK_DIP = 2.50;  // 半円が蓋へ下りる量
SHUT_LK_RF  = 0.50;  // 脚の足先・外側の角丸
// 🔴 2026-09-02 実機（1525 で刷ったロックと蓋を手で合わせた）ユーザー
//   「ロックの足が左右に広がるくらいギリギリでは？」。**その通り**。蓋の丈 8.60 に対して
//   窓は 8.80 しかなく、片側 0.10。レジンの実績は「呼び + 0.30 でジャスト」なので、
//   蓋が太り窓が縮んだ時点で 0.10 は消える。
//   🔒 同日ユーザー「でもいいのか・・・スライドして入れるわけじゃないし。間を取って 0.2 に
//     しておかない？」⇒ **0.20**。滑らせる嵌め合いではないので、見込み 0.30 は要らない。
//   ⚠ 位置はネジと鼻が決めるので、上下のガタは効かない。
//   ⚠ 脚の太さは 1.50 → 1.40 に痩せる（帯の逃がし口はロックの外形から作るので自動で追従する）。
SHUT_LK_CL  = 0.20;  // ✅ **2026-09-02 実機で確定**（ユーザー「ロック部品も問題ありません。よい具合です」）。
                     //   ロック ⇔ 蓋の隙間。旧 0.10 は「滑らないのでギリギリでよい」（2026-08-21
                     //    ユーザー指示）。⚠ 筐体の彫り込みに対しては SHUT_CL のまま
SHUT_LOCK_D   = 2.50;  // M2 の通し穴（2.4 ＋ 印刷の縮み 0.1）
// ✅ **2026-09-02 実機で確定**（ELEGOO・回 0540 の六角ゲージ）。
//   ユーザー「正直全部入るのでもういいです。５あたりで良いと思います」。印 5 = 二面幅 4.10。
//   ⚠ 測れたのは **A（上から落とす袋穴）だけ**。B（横差し）は口を連結棒で塞いでいて 1 個も
//     入らなかった（ゲージの設計ミス）。横差しの値は未測定のまま、同じ 4.10 を使っている。
SHUT_LOCK_NAF = 4.10;  // M2 ナットの二面幅（旧 4.30 は SK本舗の「呼び + 0.3」）
SHUT_LOCK_NT  = 1.80;  // M2 ナットの厚み（1.6 ＋ 0.2）
SHUT_LOCK_B   = 3.60;  // 彫り込みの床から内側へ立てるボスの厚み
// 🔴 2026-09-02 **ナットの床が 0.017mm しか無かった。** ボスの下端を `sw4_lock_z() - 2.5` と
//   直書きしていて、六角の下の頂点（lock_z − 対角 4.965/2 = lock_z − 2.483）と 0.017 差で
//   すれ違っていた。ナットは上から落とし込む設計なので、**止まる先はこの床**。刷れば消える厚みで、
//   実物ではナットが下へ抜ける（ハッチは未印刷なので誰も気づいていなかった）。
//   ⇒ 床を明示の値にする。会話ボタンが既にそうしている（btn_v3.scad の B3_BLK_FLR = 0.8）。
//   ⚠ 深さを決める数字と床の厚みを 1 つの直書きに兼ねさせない。兼ねると今回のように 0 に潰れる。
SHUT_LOCK_FLR = 0.80;  // ナットを載せる床の厚み（六角の下の頂点 → ボスの下端）
SHUT_LOCK_CB  = 4.40;  // ネジ頭のザグリ径
SHUT_LOCK_CBT = 1.60;  // 同 深さ
function cov_y0() = BAT_C0[1];
function cov_y1() = BAT_C1[1];
function cov_z0() = BAT_C0[2];
function cov_z1() = BAT_C1[2];
function cov_w()  = cov_y1() - cov_y0();
// X（外面は -WALL）
function shut_xb()  = -WALL + SHUT_T;              // 蓋の裏面
// 🔴 **耳はリップのすぐ裏に置く**（2026-08-21）。板の裏面から取ると、板を 2.75 に
//    厚くしたときに耳がリップの陰から外れ、**閉のまま引いても掴めなくなった**（実測 0.000）
function shut_xe()  = shut_xl() + SHUT_CL;         // 耳の外面
function shut_xl()  = -WALL + SHUT_LIP;            // リップの裏面
function shut_xg()  = shut_xb() + SHUT_CL;         // 彫り込みの床
// Y
function shut_y0() = cov_y0() - SHUT_MARG;
function shut_y1() = cov_y1() + SHUT_MARG;
function shut_by0() = shut_y0() - SHUT_EAR - SHUT_CL;
function shut_by1() = shut_y1() + SHUT_EAR + SHUT_CL;
// Z
function shut_z0() = cov_z0() - SHUT_MARG - SHUT_EXT;
function shut_z1() = cov_z1() + SHUT_MARG;
function shut_h()  = shut_z1() - shut_z0();
function shut_ez0() = shut_z0() + (shut_h() - SHUT_EAR_H) / 2;  // 耳の下端（閉）
function shut_bz0() = shut_z0() - SHUT_CL;
function shut_bz1() = shut_z1() + SHUT_SLIDE + SHUT_CL;
// 🔒 リップの上端。耳の閉位置の頭（+0.5）と、ずらし切った位置の足（−0.5）の間に置く
function shut_ltop() = shut_ez0() + SHUT_EAR_H + 0.5;
function shut_lock_y() = (shut_y0() + shut_y1()) / 2;
// 🔒 ネジの高さは「頭のザグリが帯の下端に触れる位置」（2026-08-21 ユーザー指示
//    「0.6 下げるだけ」）。前は帯の中央（Z 40.1）で、頭が上端に寄り過ぎていた。
//    ⚠ これより下げると ①ザグリが半円の厚み 1.2 を抜く ②ナット（二面幅 4.3）が
//    電池トンネルの天井（Z 36.4）に食い込む。ナットの下の肉は 0.95
function shut_lock_z() = lk_zb() + SHUT_LOCK_CB / 2;
// ロックパーツの外形
function lk_y0() = shut_by0() + SHUT_CL;
function lk_y1() = shut_by1() - SHUT_CL;
// 🔒 脚の下端。両端は角丸なしで抜いてあるので、リップの上端のすぐ上から始められる
function lk_z0() = shut_ltop() + SHUT_CL;
function lk_z1() = shut_bz1() - SHUT_CL;           // 帯の上端
function lk_zb() = shut_z1() + SHUT_LK_CL;         // 帯の下端（＝蓋の頭）

// Y-Z 面の角丸長方形を X 方向へ伸ばす。🔒 彫り込みと蓋はこれ1つから作る
module rrect_x(x0, xlen, y0, y1, z0, z1, r) {
    hull() for (y = [y0 + r, y1 - r], z = [z0 + r, z1 - r])
        translate([x0, y, z]) rotate([0, 90, 0]) cylinder(r = r, h = xlen, $fn = 48);
}
module shutter_magnets(x0, h) {
    for (dy = [-SHUT_MAG_DY, SHUT_MAG_DY])
        translate([x0, shut_lock_y() + dy, SHUT_MAG_Z])
            rotate([0, 90, 0]) cylinder(d = SHUT_MAG_D, h = h, $fn = 48);
}
module shutter_lock_bore(x0, h, d) {
    translate([x0, shut_lock_y(), shut_lock_z()]) rotate([0, 90, 0])
        cylinder(d = d, h = h, $fn = 32);
}
// 中央の半円（ロックパーツが蓋へ下りる部分）。gap を足すと蓋側の逃げになる
module lk_tongue(x0, xlen, gap = 0) {
    intersection() {
        translate([x0, shut_lock_y(), lk_zb() + SHUT_LK_R - SHUT_LK_DIP])
            rotate([0, 90, 0]) cylinder(r = SHUT_LK_R + gap, h = xlen, $fn = 64);
        translate([x0 - 1, shut_lock_y() - SHUT_LK_R - 1, lk_zb() - SHUT_LK_DIP - gap])
            cube([xlen + 2, (SHUT_LK_R + 1) * 2, SHUT_LK_DIP + gap * 2]);
    }
}

// 蓋そのもの（刷る部品）。open = 0 で閉、1 でずらし切ったところ
module battery_shutter(open = 0) {
    translate([0, 0, open * SHUT_SLIDE]) difference() {
        union() {
            rrect_x(-WALL, SHUT_T, shut_y0(), shut_y1(), shut_z0(), shut_z1(),
                    SHUT_R - SHUT_CL);
            for (y = [shut_y0() - SHUT_EAR, shut_y1()])
                translate([shut_xe(), y, shut_ez0()])
                    cube([SHUT_EAR_T, SHUT_EAR, SHUT_EAR_H]);
        }
        // 磁石は裏面から埋める。外面には 0.75mm の肉が残る
        shutter_magnets(shut_xb() - SHUT_MAG_H, SHUT_MAG_H + 0.01);
        // ロックパーツの半円が乗る逃げ（外面側）
        lk_tongue(-WALL - 0.01, SHUT_LK_T + SHUT_LK_CL + 0.01, SHUT_LK_CL);
    }
}
// 脚の内面（蓋の側面に SHUT_CL で向き合う）
function lk_yi0() = shut_y0() - SHUT_LK_CL;
function lk_yi1() = shut_y1() + SHUT_LK_CL;
// 帯と脚を**1枚の門形**で作る（2026-08-21）。
// 🔴 前は帯（角丸 2.25）の下に脚（幅 1.35・角丸 0.5）を別物で足していて、
//    外面に段、内側は 0.2mm の首で辛うじてつながり、足先が丸かった（ユーザー指摘・絵）。
// ⇒ 外周は上の角を 2.25、足先の外側を 0.5 で丸める。口の角は**蓋の角丸（SHUT_R）と同心**にして、
//    隙間が全周 SHUT_LK_CL で揃うようにした
module lk_frame(x0, xlen) {
    r = SHUT_R - SHUT_CL;
    difference() {
        hull() {
            for (y = [lk_y0() + r, lk_y1() - r])
                translate([x0, y, lk_z1() - r]) rotate([0, 90, 0])
                    cylinder(r = r, h = xlen, $fn = 48);
            // 足先の外側の角（2026-08-21 ユーザー指摘「ここだけカクっとしている」）
            rf = SHUT_LK_RF;
            for (y = [lk_y0() + rf, lk_y1() - rf])
                translate([x0, y, lk_z0() + rf]) rotate([0, 90, 0])
                    cylinder(r = rf, h = xlen, $fn = 32);
        }
        ri = SHUT_R - SHUT_CL + SHUT_LK_CL;  // 蓋の角丸 2.25 と同心
        hull() {
            for (y = [lk_yi0() + ri, lk_yi1() - ri])
                translate([x0 - 1, y, lk_zb() - ri]) rotate([0, 90, 0])
                    cylinder(r = ri, h = xlen + 2, $fn = 64);
            translate([x0 - 1, lk_yi0(), lk_z0() - 1])
                cube([xlen + 2, lk_yi1() - lk_yi0(), 1]);
        }
    }
}
// ロックパーツ（刷る部品）。門形（帯 ＋ 両端の脚） ＋ 中央の半円
module battery_lock() {
    difference() {
        union() {
            lk_frame(-WALL, WALL + shut_xg());
            lk_tongue(-WALL, SHUT_LK_T);
        }
        shutter_lock_bore(-WALL - 1, WALL + shut_xg() + 2, SHUT_LOCK_D);
        shutter_lock_bore(-WALL - 0.01, SHUT_LOCK_CBT, SHUT_LOCK_CB);
    }
}
// 🔴 **2026-08-21、これが無かった。**板は壁の中に描いてあるのに、
//    **壁を抜くモジュールがどこにも無かった。**
//    ⚠ **側面の壁は上シェルの持ち物**（下シェルは床しか無い）
module battery_port_cut() { if (BAT_HOUSING) {
    translate([-WALL - 1, cov_y0(), cov_z0()])
        cube([WALL + 1 + 0.01, cov_w(), cov_z1() - cov_z0()]);
} }
// 彫り込み（上シェルから引く）
module shutter_band_cut() { if (BAT_HOUSING) {
    // 耳が走る溝（リップの裏。全高・全幅）
    rrect_x(shut_xl(), shut_xg() - shut_xl(), shut_by0(), shut_by1(),
            shut_bz0(), shut_bz1(), SHUT_R);
    // 中央は外面まで抜く（蓋の本体が入る）
    rrect_x(-WALL - 0.01, SHUT_LIP + 0.01, shut_y0() - SHUT_CL, shut_y1() + SHUT_CL,
            shut_bz0(), shut_bz1(), SHUT_R);
    // 🔒 リップの上端より上は**全幅で**外面まで抜く（ロックパーツの帯と脚が入る）
    rrect_x(-WALL - 0.01, SHUT_LIP + 0.01, shut_by0(), shut_by1(),
            shut_ltop(), shut_bz1(), SHUT_R);
    // 🔴 上の角丸（SHUT_R）のせいで、**Y の両端だけリップが 2.5mm 高く残る。**
    //    そこを耳が擦った（実測 0.203mm3）。⇒ 両端は角丸なしで抜く
    //    🔒 外側の下の角は脚の足先（r 0.5）と同心の r 0.75 で丸める（2026-08-21
    //    ユーザー指摘「揃ってない」）。隙間は全周 SHUT_CL
    for (sgn = [0, 1]) {
        rp = SHUT_LK_RF + SHUT_CL;
        w  = SHUT_EAR + SHUT_CL;
        h  = SHUT_R + 1;
        y  = sgn == 0 ? shut_by0() : shut_y1();   // 口の Y の始まり
        yc = sgn == 0 ? y + rp : y + w - rp;       // 丸めの中心 Y（外側）
        ys = sgn == 0 ? y + rp : y;                // 角を欠いた下段の始まり
        hull() {
            translate([-WALL - 0.01, yc, shut_ltop() + rp]) rotate([0, 90, 0])
                cylinder(r = rp, h = SHUT_LIP + 0.01, $fn = 32);
            translate([-WALL - 0.01, y, shut_ltop() + rp])
                cube([SHUT_LIP + 0.01, w, h - rp]);
            translate([-WALL - 0.01, ys, shut_ltop()])
                cube([SHUT_LIP + 0.01, w - rp, h]);
        }
    }
    // 相手側の磁石の座（⚠ ブリッジの肉を使っている）
    shutter_magnets(shut_xg() - 0.01, SHUT_MAG_H + 0.01);
} }
// ロックネジの穴とナットの座（上シェルから引く）
module shutter_lock_cut() { if (BAT_HOUSING) {
    shutter_lock_bore(shut_xl() - 1, SHUT_LOCK_B + shut_xg() - shut_xl() + 2,
                      SHUT_LOCK_D);
    // ナットの六角ポケット。🔒 **上から落とし込む**
    translate([shut_xg() + SHUT_LOCK_B - SHUT_LOCK_NT, shut_lock_y(), shut_lock_z()])
        rotate([0, 90, 0]) rotate([0, 0, 90])
            cylinder(d = SHUT_LOCK_NAF / cos(30), h = SHUT_LOCK_NT + 0.01, $fn = 6);
    // 🔴 溝を長く取ると**天板を突き抜ける**。ボスの頭までで止める
    translate([shut_xg() + SHUT_LOCK_B - SHUT_LOCK_NT,
               shut_lock_y() - SHUT_LOCK_NAF / 2, shut_lock_z()])
        cube([SHUT_LOCK_NT + 0.01, SHUT_LOCK_NAF, 3.5 + 0.5]);
} }
// 彫ったぶん、壁の裏へ肉を足す（電池の通り道はあとで difference で抜かれる）
module shutter_backing() { if (BAT_HOUSING) {
    translate([0, shut_by0(), shut_bz0()])
        cube([SHUT_BACK, shut_by1() - shut_by0(), shut_bz1() - shut_bz0()]);
    // ロックネジのナットを持つボス
    translate([shut_xg(), shut_lock_y() - 4.5, shut_lock_z() - 3.5])
        cube([SHUT_LOCK_B, 9.0, 7.0]);
} }
// ---- 絵にだけ出す実体（当たり検査は case_v3_fasteners.scad の FAST が持つ）----
// ロックの M2 ビス。頭は外面のザグリの中、胴は蓋とロックを貫いて壁のボスのナットへ
module shutter_lock_screw() { color("#e8e8e8")
    translate([shut_xl(), shut_lock_y(), shut_lock_z()]) rotate([0, 90, 0]) {
        cylinder(d = 2.0, h = 6.0, $fn = 24);
        translate([0, 0, -1.3]) cylinder(d = 3.0, h = 1.3, $fn = 32);
    }
}
// ロックの M2 ナット（壁のボスの六角ポケット。🔒 上から落とし込む）
module shutter_lock_nut() { color("#888")
    translate([shut_xg() + SHUT_LOCK_B - SHUT_LOCK_NT, shut_lock_y(), shut_lock_z()])
        rotate([0, 90, 0]) rotate([0, 0, 90])
            cylinder(d = SHUT_LOCK_NAF / cos(30), h = SHUT_LOCK_NT, $fn = 6);
}
// φ6 × 2.0 の磁石 4 個。蓋の裏に 2・壁（彫り込みの床）に 2 で向き合う
module shutter_magnets_wall()    { color("#c0c0c0") shutter_magnets(shut_xg(), SHUT_MAG_H); }
module shutter_magnets_shutter() { color("#c0c0c0") shutter_magnets(shut_xb() - SHUT_MAG_H, SHUT_MAG_H); }
