// ============================================================
// 📦 v4 電池の入れ替え口（後ろ抜き）—— **横（右へ）スライド**の蓋（2026-08-26）
//   🔒 ユーザー GO「後ろから出すのは配置を指定した時から分かっていた事」。
//   レール＋留め帯＝ +Y にだけ開いた鞘・タブは後ろ向き 🔒 → 口はハッチ。抜く接続は電池の JST 1 本。
//
//   🔴 2026-08-26 下スライドを廃止して横スライドへ。理由はユーザー指摘:
//      「下にスライドするけど普段は落ちないなんてありえない」。v3 の蓋は上へ持ち上げて外す型なので
//      自重が閉じる向きに効いていたが、v4 はそれを 180° 回して写したため自重が開く向きに効き、
//      ロックのビスが構造材になっていた。横なら自重はスライドと直角なので、ロックは v3 と同じ「念のための止め」に戻る。
//      左へは逃がせない（Type-C 基板がハッチ内面の左に付いていて、増し肉が 45.49mm³ 食い込む）。右は 0。
//
//   型は v3 のまま: 蓋（板＋耳＋磁石 2）＋外面の彫り込み帯＋門形ロック（M2＋ナット・外せば磁石だけで開閉）。
//   寸法の定数（SHUT_*・磁石 ✅ゲージ確定 φ6.1）は case_v3_shutter.scad のを共有する。
//   軸の写像: v3 左壁（外面 x=-WALL・スライド +Z・耳 ±Y）→ v4 ハッチ（外面 y=SW4_YOUT・スライド +X・耳 ±Z）。
//     ・磁石の部屋（SHUT_EXT）は口の**左右**（Z に 7mm しか無いので上下には置けない）
//     ・耳は上下 1 個ずつ・X の中央。v4 と同じで「上下が同じ位置」でないと逃がし口を 1 か所で通れない
//     ・逃がし口（リップを抜く所）は帯の**右端**。ここにロックが座る
//   ⚠ 蓋の裏 ↔ 電池の尻は空く（電池は前ガードとこの蓋の間で Y に遊ぶ）。⬜ 詰め物はユーザー。
//   ⚠ 線: PB の L ピン 3 本（_v4_core の w_pwr3）は帯とロックのボスに当たったので Z 35.2/36.7/38.2 へ上げた。
// ============================================================
SW4_X0 = BAT_X0 - 0.5;                        // 口（電池の断面 35 × 6 ＋ 逃げ 0.5）
SW4_X1 = BAT_X0 + lipo_size()[1] + 0.5;
SW4_Z0 = BAT_Z - 0.5;
SW4_Z1 = BAT_Z + lipo_size()[2] + 0.5;
SW4_YOUT = IN_Y + HATCH_T;                    // ハッチの外面

SW4_NOSE_R = 4.3;    // 🔒 2026-08-26 ユーザー朱書き: ロックの外端に、ビスを中心にした半円を出す
SW4_FILLET = 0.8;    // 🔒 同: 舌（半円）が枠に刺さる 2 か所の入り隅の角を取る

// ---- Y の面（外面から中へ）----
function sw4_yb() = SW4_YOUT - SHUT_T;        // 蓋の裏面
function sw4_yl() = SW4_YOUT - SHUT_LIP;      // リップの裏面
function sw4_yg() = sw4_yb() - SHUT_CL;       // 彫り込み（溝）の床
function sw4_ye() = sw4_yl() - SHUT_CL;       // 耳の外面側

// ---- 蓋（X の両端に磁石の部屋 SHUT_EXT）----
function sw4_lx0() = SW4_X0 - SHUT_MARG - SHUT_EXT;
function sw4_lx1() = SW4_X1 + SHUT_MARG + SHUT_EXT;
function sw4_lz0() = SW4_Z0 - SHUT_MARG;
function sw4_lz1() = SW4_Z1 + SHUT_MARG;
function sw4_lw()  = sw4_lx1() - sw4_lx0();

// ---- 帯（彫り込み）----
function sw4_bx0() = sw4_lx0() - SHUT_CL;
function sw4_bx1() = sw4_lx1() + SHUT_SLIDE + SHUT_CL;
function sw4_bz0() = sw4_lz0() - SHUT_EAR - SHUT_CL;
function sw4_bz1() = sw4_lz1() + SHUT_EAR + SHUT_CL;

// ---- 耳（上下 1 個ずつ・X の中央）----
function sw4_ex0()  = sw4_lx0() + (sw4_lw() - SHUT_EAR_H) / 2;
function sw4_lend() = sw4_ex0() + SHUT_EAR_H + 0.5;   // 🔒 リップの右端（閉の耳の先 +0.5）＝逃がし口の左端

// ---- 磁石（左右の部屋の中央・Z は蓋の中央）----
// 🔴 2026-09-01 実機（1525）ユーザー「電池の蓋の磁石部分の淵が印刷されなかった」。
//   芯を SHUT_EXT（6.30）の中央に置いていたので、蓋の外周までの肉が
//   **6.30/2 − 6.10/2 = 0.10mm** しか無かった。外面の 0.75 はプレートに着くので残り、
//   その上に立つ 0.10 x 高さ 2.0 の輪だけが消えた。
//   ⇒ 芯は**蓋の外周から数えて置く**（山分けにしない）。効くのは外周側だけで、内側は無限に肉。
//     残りが口までの肉（＝ハッチ側の座と穴の間の壁）になる。SHUT_EXT 6.80 で 1.00 / 0.50。
SW4_MAG_WALL = 1.00;   // 🔒 蓋の外周 ↔ 磁石の穴。ここが 0.10 で焼けなかった（実機 1525）
function sw4_mag_z()  = (sw4_lz0() + sw4_lz1()) / 2;
function sw4_mag_room() = SHUT_MARG + SHUT_EXT;                       // 口の外に残っている帯の幅
function sw4_mag_inner() = sw4_mag_room() - SW4_MAG_WALL - SHUT_MAG_D;   // 口までの肉（ハッチ側の壁）
function sw4_mag_xs() = [sw4_lx0() + SW4_MAG_WALL + SHUT_MAG_D / 2,
                         sw4_lx1() - SW4_MAG_WALL - SHUT_MAG_D / 2];
assert(sw4_mag_inner() >= 0.42,
       "磁石の座と電池の口の間の壁が 0.42 を切る（PRINT.md の最薄肉）。SHUT_EXT を増やす");

// ---- ロック（v3 の門形を右へ回したもの）----
//   v3: 帯の上端に横棒・脚は下・舌は蓋の頭に乗る  →  ここ: 帯の右端に縦棒・脚は左・舌は蓋の右端に乗る
function sw4_lk_xr()   = sw4_lx1() + SHUT_LK_CL;          // 蓋の右端（舌が乗る所）
function sw4_lock_x()  = sw4_lk_xr() + SHUT_LOCK_CB / 2;  // ネジの X（頭のザグリが蓋の縁に触れる位置・v3 の規則）
function sw4_lock_z()  = (sw4_lz0() + sw4_lz1()) / 2;     // ネジの Z（蓋の中央）
function sw4_lk_x1()   = sw4_bx1() - SHUT_CL;             // 縦棒の右端
function sw4_lk_x0()   = sw4_lend() + SHUT_CL;            // 脚の足先（左）。リップの端より内側で止める
function sw4_lk_z0()   = sw4_bz0() + SHUT_CL;
function sw4_lk_z1()   = sw4_bz1() - SHUT_CL;
function sw4_lk_boss_z1() = sw4_lz1() + 3.0;              // ナットのボスの上端（🔒 ナットは上から落とし込む）

// ---- 道具 ----
// X-Z の 2D 輪郭を Y へ伸ばす（2D の縦がそのまま Z になる向き）
module sw4_ext(y0, ylen) translate([0, y0 + ylen, 0]) rotate([90, 0, 0]) linear_extrude(ylen) children();
module sw4_fillet(f) offset(r = -f) offset(r = f) children();   // 入り隅だけ丸める（膨らませてから縮める）
// X-Z 面の角丸長方形を Y 方向へ伸ばす
module sw4_rrect(y0, ylen, x0, x1, z0, z1, r) {
    hull() for (x = [x0 + r, x1 - r], z = [z0 + r, z1 - r])
        translate([x, y0, z]) rotate([-90, 0, 0]) cylinder(r = r, h = ylen, $fn = 48);
}
module sw4_magnets(y0, h) {
    for (x = sw4_mag_xs()) translate([x, y0, sw4_mag_z()]) rotate([-90, 0, 0]) cylinder(d = SHUT_MAG_D, h = h, $fn = 48);
}
module sw4_lock_bore(y0, h, d) {
    translate([sw4_lock_x(), y0, sw4_lock_z()]) rotate([-90, 0, 0]) cylinder(d = d, h = h, $fn = 32);
}

// ---- ロックの 2D 輪郭 ----
module sw4_nose_2d() translate([sw4_lock_x(), sw4_lock_z()]) circle(r = SW4_NOSE_R, $fn = 64);
// 🔒 2026-08-26 ユーザーの before/after: 右端の角丸が半円からはみ出して「耳」に見えていた。
//   端は足先と同じ小さい角にして真っすぐにする（旧 SHUT_R - SHUT_CL = 2.25 → SHUT_LK_RF）
module sw4_lk_end_2d() { r = SHUT_LK_RF;    // 右端（縦棒）の角
    for (z = [sw4_lk_z0() + r, sw4_lk_z1() - r]) translate([sw4_lk_x1() - r, z]) circle(r = r, $fn = 32); }
module sw4_lk_leg_2d() { rf = SHUT_LK_RF;   // 左の足先
    for (z = [sw4_lk_z0() + rf, sw4_lk_z1() - rf]) translate([sw4_lk_x0() + rf, z]) circle(r = rf, $fn = 32); }
module sw4_lk_frame_2d() hull() { sw4_lk_end_2d(); sw4_lk_leg_2d(); }
module sw4_lk_out_2d()   union() { sw4_lk_frame_2d(); sw4_nose_2d(); }
// 蓋が通る窓（蓋の角丸と同心）
module sw4_lk_hole_2d() {
    ri = SHUT_R - SHUT_CL + SHUT_LK_CL;
    hull() {
        for (z = [sw4_lz0() - SHUT_LK_CL + ri, sw4_lz1() + SHUT_LK_CL - ri])
            translate([sw4_lk_xr() - ri, z]) circle(r = ri, $fn = 64);
        translate([sw4_lk_x0() - 3, sw4_lz0() - SHUT_LK_CL]) square([3, sw4_lz1() - sw4_lz0() + 2 * SHUT_LK_CL]);
    }
}
// 舌（蓋の外面に乗る半円）
module sw4_lk_tongue_2d() {
    intersection() {
        translate([sw4_lk_xr() + SHUT_LK_R - SHUT_LK_DIP, sw4_lock_z()]) circle(r = SHUT_LK_R, $fn = 64);
        translate([sw4_lk_xr() - SHUT_LK_DIP, sw4_lock_z() - SHUT_LK_R - 1]) square([SHUT_LK_DIP, (SHUT_LK_R + 1) * 2]);
    }
}
module sw4_lk_body_2d() difference() { sw4_lk_out_2d(); sw4_lk_hole_2d(); }
// 外面の 1 枚だけ舌が付く。🔒 角を取るのは**舌が枠に刺さる 2 か所だけ**（鼻は後から足して端の形は変えない）
module sw4_lk_face_2d() union() {
    sw4_fillet(SW4_FILLET) union() { difference() { sw4_lk_frame_2d(); sw4_lk_hole_2d(); } sw4_lk_tongue_2d(); }
    sw4_lk_body_2d();
}
module sw4_lk_lap_2d() intersection() { sw4_lk_face_2d(); sw4_lk_hole_2d(); }   // 蓋に被さる分（舌＋角を取った肉）

// ---- 刷る部品 ----
// 蓋。open = 0 で閉、1 で右へ SHUT_SLIDE ずらし切った状態
module battery_shutter4(open = 0) {
    translate([open * SHUT_SLIDE, 0, 0]) difference() {
        union() {
            sw4_rrect(sw4_yb(), SHUT_T, sw4_lx0(), sw4_lx1(), sw4_lz0(), sw4_lz1(), SHUT_R - SHUT_CL);
            for (z = [sw4_lz0() - SHUT_EAR, sw4_lz1()])          // 上下の耳
                translate([sw4_ex0(), sw4_ye() - SHUT_EAR_T, z]) cube([SHUT_EAR_H, SHUT_EAR_T, SHUT_EAR]);
        }
        sw4_magnets(sw4_yb() - 0.01, SHUT_MAG_H + 0.01);          // 磁石は裏面から埋める（外面に 0.75 残る）
        sw4_ext(SW4_YOUT - SHUT_LK_T - SHUT_LK_CL, SHUT_LK_T + SHUT_LK_CL + 0.01)
            offset(r = SHUT_LK_CL) sw4_lk_lap_2d();               // 舌の逃げ（外面側）
    }
}
// ロック
module battery_lock4() {
    difference() {
        union() {
            sw4_ext(sw4_yg(), SW4_YOUT - sw4_yg() - SHUT_LK_T) sw4_lk_body_2d();
            sw4_ext(SW4_YOUT - SHUT_LK_T, SHUT_LK_T)            sw4_lk_face_2d();
        }
        sw4_lock_bore(sw4_yg() - 2, SW4_YOUT - sw4_yg() + 4, SHUT_LOCK_D);
        sw4_lock_bore(SW4_YOUT - SHUT_LOCK_CBT, SHUT_LOCK_CBT + 0.01, SHUT_LOCK_CB);
    }
}

// ---- ハッチから引くもの ----
// 口（蓋が塞ぐのでベベル無し・v3 と同じ）
module battery_port_cut4() {
    translate([SW4_X0, sw4_yg() - SHUT_BACK - 1, SW4_Z0])
        cube([SW4_X1 - SW4_X0, SHUT_BACK + SHUT_T + 2, SW4_Z1 - SW4_Z0]);
}
// 彫り込み
// 🔒 2026-09-04 ユーザー「端までレールである必要がない。実際手元でそのレールを 6mm 以外
//   塞いでも動作してる」（実機で確認済み）。理由は印刷で、レールの下に柱が立って滑る面がガビガビになる。
//   耳は蓋の X 中央にしか無く、閉（sw4_ex0）から逃がし口へ 5.5 動くだけなので、
//   **耳が届かない左側の縁は溝を掘らない**（＝壁が Y 71〜74 まで通しの肉になる）。
//   ロックの形は変えない（ユーザー指示）。逃がし口から右は今までどおりロックの外形が彫る。
// ⚠ 角丸 SHUT_R のぶん、レールの左端は口が細っている（掃引で耳と 0.07mm³ 当たった）。
//   耳の閉位置で断面が丸まっていないよう、角丸 + 隙間ぶん左へ出す
SW4_RAIL_LEAD = SHUT_R + SHUT_CL;   // レールを耳の閉位置より左へ伸ばす分
function sw4_rail_x0() = sw4_ex0() - SW4_RAIL_LEAD;   // レール（縁まで高い溝）の左端
module sw4_band_cut() {
    sw4_rrect(sw4_yg(), sw4_yl() - sw4_yg(), sw4_bx0(), sw4_bx1(),
              sw4_lz0() - SHUT_CL, sw4_lz1() + SHUT_CL, SHUT_R);                                    // 蓋の本体が走る溝（全長・蓋の高さ）
    sw4_rrect(sw4_yg(), sw4_yl() - sw4_yg(), sw4_rail_x0(), sw4_bx1(), sw4_bz0(), sw4_bz1(), SHUT_R);   // 耳が走るレール（耳が届く所だけ・上下の縁まで）
    sw4_rrect(sw4_yl() - 0.01, SHUT_LIP + 0.02, sw4_bx0(), sw4_bx1(),
              sw4_lz0() - SHUT_CL, sw4_lz1() + SHUT_CL, SHUT_R);                                    // 蓋の本体が出る窓（全ストローク分）
    // 🔒 ロックが座る所（＝耳の逃がし口も兼ねる）。**ロックの外形から作る**ので、ロックの形を変えても彫り込みが必ず追従する
    sw4_ext(sw4_yg(), SW4_YOUT - sw4_yg() + 0.01) offset(r = SHUT_CL) sw4_lk_out_2d();
    sw4_magnets(sw4_yg() - SHUT_MAG_H, SHUT_MAG_H + 0.01);                                          // 相手側の磁石の座
}
// ロックのネジ穴とナットの座
// 🔒 2026-08-29 ユーザー「磁石の中央穴開けちゃえば？だって蓋で見えなくなるでしょ？周囲に枠が
//   あればそれでいい」。彫り込み帯の残り（Y 68.6〜69.0 の **0.40mm**）は、磁石の所だけ裏の
//   増し肉（sw4_backing）が途切れていて単独の板になり、刷ると 7.9mm² が浮いた天井になっていた。
//   支柱を立てると 0.40mm の皮を破るので立てられない、と警告に出ていた所。
//   ⇒ 磁石の芯に窓を開けて枠だけ残す。蓋が閉まれば見えない。φ6.1 の磁石に対して φ4.1（枠 1.0）。
SW4_MAG_WIN_D = 4.1;
module sw4_mag_window() for (x = sw4_mag_xs())
    translate([x, sw4_yg() - 4.0, sw4_mag_z()]) rotate([-90, 0, 0])
        cylinder(d = SW4_MAG_WIN_D, h = 6.0, $fn = 48);
module sw4_lock_cut() {
    sw4_lock_bore(sw4_yg() - SHUT_LOCK_B - 2, SHUT_LOCK_B + SHUT_T + 4, SHUT_LOCK_D);
    translate([sw4_lock_x(), sw4_yg() - SHUT_LOCK_B, sw4_lock_z()]) rotate([-90, 0, 0]) rotate([0, 0, 30])
        cylinder(d = SHUT_LOCK_NAF / cos(30), h = SHUT_LOCK_NT + 0.01, $fn = 6);                    // ナットの六角ポケット
    translate([sw4_lock_x() - SHUT_LOCK_NAF / 2, sw4_yg() - SHUT_LOCK_B, sw4_lock_z()])
        cube([SHUT_LOCK_NAF, SHUT_LOCK_NT + 0.01, sw4_lk_boss_z1() - sw4_lock_z() + 0.01]);         // 落とす溝（ボスの頭まで）
}
// 彫ったぶんハッチの裏へ足す肉＋ロックのボス＋磁石のパッド
// ボスの下端 ＝ 六角の下の頂点 − 床の厚み。🔒 旧「− 2.5」は直書きで、床が 0.017mm しか
//   残っていなかった（2026-09-02。case_v3_shutter.scad の SHUT_LOCK_FLR の節）
function sw4_lock_boss_z0() = sw4_lock_z() - SHUT_LOCK_NAF / cos(30) / 2 - SHUT_LOCK_FLR;
module sw4_lock_boss() translate([sw4_lock_x() - 4.5, sw4_yg() - SHUT_LOCK_B, sw4_lock_boss_z0()])
    cube([9.0, SHUT_LOCK_B, sw4_lk_boss_z1() - sw4_lock_boss_z0()]);
// 🔒 2026-09-04 ユーザー「当たった部分だけ削ればいい」。つば（帯の外へ出る縁）の出と、削る隙間。
//   溝は外面から 3.0mm（蓋 2.75 ＋ 隙間 0.25）掘るのにハッチの壁は 2.0mm しかないので、
//   足りない 1.0mm は増し肉から取っている。残る床は 1.2mm で、その外周が帯とぴったり同寸だと
//   **床の縁の先には何も無く**（壁の内面は Y+1.0 の所から始まる）、床は壁につながらない。
//   つばはその 1.0mm の段を跨いで壁に載せるための縁。
SW4_BACK_FL = 1.0;   // つばの出。ロックの座の裏（offset SHUT_CL + 1.0）と同じ
SW4_BACK_CL = 0.3;   // 削るときに部品との間に残す隙間
// 当たる相手を**部品そのもので**引く（🔒 数字を書かない・基板が動けば削れる所も追う）。
//   6 方向へ SW4_BACK_CL ずらした複製との和 ＝ 軸方向にその隙間だけ太らせた形
module sw4_backing_carve(cl) for (d = [[0, 0, 0], [cl, 0, 0], [-cl, 0, 0], [0, cl, 0], [0, -cl, 0], [0, 0, cl], [0, 0, -cl]])
    translate(d) tcb_v4();
// 🔒 2026-09-04 **増し肉は Y 71.0（＝溝の床）で 2 つの部品に割る。**ユーザー「部品が分かれても良い」。
//   理由は印刷。割る前は、溝をまたぐ床の板が刷る向きの Z 3.00 で **327.8mm² 一度に**現れていて、
//   そこへ柱が 48 本立ち、折ると滑る面に跡が残っていた（回 2026-09-03-2037・ユーザー「ガビガビ」）。
//   割ると一度に出る面積は **ハッチ 4.6mm² / 板 15.1mm²** まで落ち、どちらも島は 0（＝柱が要らない）。
//     ・Y 71 より外（1.0mm）＝ ハッチの縁（`sw4_hatch_rim`）。壁と一体で刷る
//     ・Y 71 より内（1.2mm ＋ 磁石の座 ＋ ロックのナットのボス）＝ 床の板（`sw4_floor_plate`）。別に寝かせて刷る
//   合わせ面は Y 71.0 の平面で、接着（磁石と同じ）＋ ロックの M2 を共用して締める。
SW4_REG_H  = 1.0;    // 位置決めの爪: 板の面（Y 71）より内側へ出る高さ。板は同じ所を貫通で欠く
SW4_REG_W  = 3.0;    // 同・幅（Z）
SW4_REG_L  = 1.0;    // 同・長さ（X）。つばの外周から内へ
SW4_REG_CL = 0.25;   // 同・隙間
// 🔴 位置決めは**ハッチ側**に立てる。板側に立てると、板を溝の床の面を下にして寝かせたとき
//   その爪だけが最下層になり、板の本体 544mm² が Z 1.0 で一度に出る（振り出しに戻る）。
//   ハッチ側なら爪は縁（Y 71〜72）の上に生えるだけで、新しい面積が出ない。
// ⚠ 最初は全周を囲む輪にしたが、縁の輪郭が 1.25mm 外へ広がって**信号線に 31.8mm³ 当たった**。
//   ⇒ 線の来ない左右の端だけ、爪 2 個にした。
// つばの 2D 輪郭。板・ハッチの縁・爪は全部これから作る（🔒 形は 1 か所）
module sw4_rrect2d(x0, x1, z0, z1, r) hull() for (x = [x0 + r, x1 - r], z = [z0 + r, z1 - r]) translate([x, z]) circle(r = r, $fn = 48);
module sw4_flange_2d() union() {
    sw4_rrect2d(sw4_bx0() - SW4_BACK_FL, sw4_bx1() + SW4_BACK_FL,
                sw4_bz0() - SW4_BACK_FL, sw4_bz1() + SW4_BACK_FL, SHUT_R + SW4_BACK_FL);
    offset(r = SHUT_CL + 1.0) sw4_lk_out_2d();   // ロックの座の裏（帯の四角から出る分）
}
// 爪の 2D（g = 隙間。爪は 0、板の欠きは SW4_REG_CL）。**縁が確実に残っている所**に 2 個置く:
//   ① 左の端の縦の帯（X 2.15〜3.15・帯の外なので全高ある）  ② 下の帯の中ほど（Z 19.25〜20.25）
//   ⚠ 右の端に置くとロックの鼻の座（半径 5.55 の丸）に縁を食われていて、爪が宙に浮く（実測: 島 1 個・3.00mm²）。
//   ⚠ 上の帯には置かない。電源の線が Y 70.7・Z 32.2 を走っていて、内側へ出る爪が当たる。
SW4_REG_BX = 30.0;   // ②の X の中心
module sw4_reg_2d(g) {
    translate([sw4_bx0() - SW4_BACK_FL - g, sw4_mag_z() - SW4_REG_W / 2 - g])
        square([SW4_REG_L + 2 * g, SW4_REG_W + 2 * g]);                                   // ① 左の端
    translate([SW4_REG_BX - SW4_REG_W / 2 - g, sw4_bz0() - SW4_BACK_FL - g])
        square([SW4_REG_W + 2 * g, SW4_REG_L + 2 * g]);                                   // ② 下の帯
}
// 床の板（別部品）: Y 69.8〜71.0 の 1.2mm ＋ 磁石の座 ＋ ロックのナットのボス
// 🔴 2026-09-02 つばの輪郭は角丸（彫り込みと同じ）。角の立った直方体だと、彫っていない四隅にまで
//   肉が出て Type-C の基板へ 0.721mm³ 食い込んだ。
// 🔴 2026-09-04 その直しは輪郭の全体を溝と同寸まで縮めるやり方で、床を壁につないでいた縁まで消え、
//   床がロックの座だけでぶら下がっていた。⇒ つばを全周に戻し、当たっている所だけ部品で引く。
module sw4_floor_plate() difference() {
    union() {
        sw4_ext(IN_Y - SHUT_BACK, SHUT_BACK - (IN_Y - sw4_yg())) sw4_flange_2d();
        sw4_lock_boss();
        for (x = sw4_mag_xs()) translate([x, sw4_yg() - SHUT_MAG_H - 0.4, sw4_mag_z()])   // 磁石の座の増し
            rotate([-90, 0, 0]) cylinder(d = SHUT_MAG_D + 2.0, h = SHUT_MAG_H + 0.4 + 0.01, $fn = 48);
        // ⚠ 穴の底 0.4（0.8 だと座の前面が INA の I2C の束に入る。磁石は接着が持つ前提）
    }
    sw4_ext(IN_Y - SHUT_BACK - 1, SHUT_BACK + 2) sw4_reg_2d(SW4_REG_CL);   // 爪が入る欠き（貫通）
    sw4_backing_carve(SW4_BACK_CL);   // 当たった所だけ削る（いまは Type-C 基板の角）
}
// ハッチ側の縁（Y 71〜72）＋ 位置決めの爪 2 個（Y 70.0〜71）
module sw4_hatch_rim() difference() {
    union() {
        sw4_ext(sw4_yg(), IN_Y - sw4_yg()) sw4_flange_2d();
        sw4_ext(sw4_yg() - SW4_REG_H, SW4_REG_H) sw4_reg_2d(0);
    }
    sw4_backing_carve(SW4_BACK_CL);
}


// ---- 絵にだけ出す実体 ----
module sw4_lock_screw() color("#e8e8e8") translate([sw4_lock_x(), sw4_yl(), sw4_lock_z()]) rotate([90, 0, 0]) {
    cylinder(d = 2.0, h = 6.0, $fn = 24);                                  // 胴（リップの裏からボスのナットへ）
    translate([0, 0, -1.3]) cylinder(d = 3.0, h = 1.3, $fn = 32);          // 頭（外面のザグリの中）
}
module sw4_lock_nut() color("#888") translate([sw4_lock_x(), sw4_yg() - SHUT_LOCK_B, sw4_lock_z()])
    rotate([-90, 0, 0]) rotate([0, 0, 30]) cylinder(d = SHUT_LOCK_NAF / cos(30), h = SHUT_LOCK_NT, $fn = 6);
module sw4_magnets_wall()    color("#c0c0c0") sw4_magnets(sw4_yg() - SHUT_MAG_H, SHUT_MAG_H);
module sw4_magnets_shutter() color("#c0c0c0") sw4_magnets(sw4_yb() - SHUT_MAG_H, SHUT_MAG_H);
