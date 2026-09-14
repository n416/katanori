// ============================================================
// v6 つまみの機構 ── 歯車・軸・軸受け・保持（2026-09-13）
//
//   ⚠ この一本は**機構だけ**を持つ。外形・顔・部品の置き場は _v6_portrait.scad が正で、
//     こちらはその座標を include で借りている（🔴 同じ数字を 2 か所に書かない）。
//   ⚠ _v6_portrait.scad は**触っていない**。統合はデザイン担当がやる。
//
//   実行:
//     "C:/Program Files/OpenSCAD (Nightly)/openscad.exe" --backend=manifold \
//        -o x.png --camera=... -D "part=\"glook\"" hardware/frozen/v6/_v6_gear.scad
//   part の値:
//     glook   … 機構だけを組んだ姿（殻は薄く）
//     gguts   … 中身（ReSpeaker・板・電池）と一緒に
//     gcut    … つまみの芯を通る Y-Z 断面
//     gexp    … 分解
//     gflat   … 部品を並べた図（刷る単位）
//     p_knob / p_khub / p_idler / p_rotor / p_sgear / p_brk … 部品 1 つずつ（STL 用）
//     chk_*   … 当たり検査（下の「検査」節）
//
// ---- 組む順番（🔴 これが背骨。閉じたあと届かなくなる物を先に入れる）----
//   前の殻は**最後に載る**（柱は全部背面の殻から立っている）ので、前の壁に付く物は先に仕込む。
//   A. つまみを前の殻へ仕込む（🔴 姿勢が 2 度変わる。ここを間違えると入らない）
//     A1 **皿を表（顔）を下にして台に置く。**その前に**シリコングリスを塗る**:
//        スカートの外面 φ12.60 のうち、**細くなっている段（z 21.00）より上**だけに薄く。
//        🔴 段が目印である。下端の 0.20 と穴の中には塗らない ── そこが接着の面で、
//           グリスが回ると接着しない。手の精度 0.3 で足りるように段を付けた
//        前の殻を顔を下にして皿へ被せ、スカートを穴 φ12.85 へ入れる。
//        止めピン（φ2.60・出しろ 0.90）が溝に入る向きで
//        ⚠ 皿は殻の**外**に付くので、殻を置いてから皿を載せることはできない。皿が先に台にある
//     A2 **ハブに 2 液エポキシを塗る。**塗る所は 2 つ:
//        A スカートの下端が乗る輪 … 歯車の天面の、柱のまわり（穴の縁 → φ11.80）**57.40mm²**
//        B 柱の側面 … 二面幅も含めた周り全部。隙間は片側 0.05・高さ 1.00 で **26.36mm²**
//        ⇒ 合計 **83.76mm²**（裁定 #2 の栓は柱の天面 50.51mm² の 1 面だけだった）
//        上（＝内側）からハブの柱を皿の穴へ挿す。**穴は二面幅**なので向きは 2 通りだけ
//     A3 **ここで回してみる。**皿を回してハブの歯車が連れて回ることを確かめる。
//        ⚠ エポキシには可使時間があるので、ここでまだ直せる。裁定 #2 が瞬間接着剤を
//           落とした理由（確かめる前に固まる）は、エポキシでは起きない
//     A4 **ハブを皿へ押し付けたまま硬化させる。**顔を下にしたまま置けば重力がハブを皿へ寄せる。
//        足りなければ背面側から棒で押す。はみ出しの行き先は 2 つとも逃げに入る:
//        外へ … スカートを細くした所 **4.07mm³**（軸受けの隙間 0.125 へ上がらない）
//        上へ … 毛管止めの溝 φ9.70 × 0.30 **4.74mm³**（その上に乾いた穴が 0.30 残る）
//        🔴 **φ11 の穴から見えるのは、皿の呼び込みの円錐と柱の天面だけ。**
//           接着剤はどちらにも届かない（chk_bond_cone が空・対照 21 が 1.65mm³）
//     A5 **殻を顔が上になるように返す。**皿とハブは 1 つの体になっている。
//        皿は自重で壁の外面に座り、ハブは歯先 φ14.85 が穴 φ12.85 を通れないので落ちない
//     A6 **もう一度、顔を下にして置く。**中継（idler）を壁の止まり軸 φ3 に落とす。
//        🔴 ここから前の殻は**傾けられない**（中継は載るだけで押さえが無い）
//   B. 背面の殻の上でスタックを組む
//     B1 中継基板を柱 4 本に留める。**右下の M2 でブラケット（brk）を共締めする**
//        ⚠ **AGC を見ながら締める。**ブラケットの穴 φ2.4 ↔ M2 φ2.0 に直径 0.40（芯で 0.20）の
//           遊びがあり、これは誤差ではなく**調整代**である。docs/KNOB-ENCODER.md 47 行
//           「AS5600 保持板の穴は長穴にする … 静的なずれを最後に AGC で追い込むため」。
//           🔴 データシートの同芯 0.25 は「磁石の中心 ⇔ 回転軸」の話（ロータ自身の作り・echo ⑥）で、
//              チップと軸の静的なずれとは別物。混ぜない
//        ⚠ ねじ 1 本なので、締めた後の回り止めは座の摩擦だけである。座は板に触れる面積
//           20.9mm²（うち M2 のまわり 18.1mm²）。1 度回ると芯は 0.097mm 動く
//     B2 磁石 φ4×2 をロータの下の穴へ押し込み、ロータをブラケットの筒へ上から落とす
//        （鍔が筒の天面に乗って止まる ＝ ここでエアギャップ 1.10 が決まる）
//     B3 電池 → ReSpeaker を柱へ。ロータのくびれ φ3.6 は ReSpeaker の右の縁から 0.39 空く
//     B4 読み取りの歯車（sgear）をロータの柱へ上から被せる（二面幅・締め代 0.05）
//        ⚠ 圧入は仮止めで、**抜け止めは前の壁**である（上へ 0.50 で壁に当たり、掛かり 0.24 が残る）。
//           part="ghold" -D LIFT=1 で、3 つとも限界まで動かした姿が見える
//   C. 前の殻を降ろす。噛み合いは中継 ↔ 読み取りの 1 か所だけが「盲」なので、
//      両方の歯の端に 0.30 の面取りを付けてある（歯先どうしが乗り上げずに入る）
//   D. ゼロ点: つまみを OFF 側の壁に当てて `knobzero`
// ============================================================

include <_v6_portrait.scad>

part = "ghold";      // 🔴 include より後に置く（親の part="guts" を上書きする）。
                     //    親の part の値（face/guts/shellonly/inside/cut/explode）とは
                     //    1 つも重ならない名前にしてあるので、親側は何も描かれない。
$fn = 72;

// ============================================================
// 0. 実績値（出どころのある数字だけ。⚠ の付いた物は私の仮定）
// ============================================================
RUN      = 0.25;   // 🔒 回る嵌め合いの遊び（直径）。knob_v5.scad の BORE_CLEAR（実績）
RUN_S    = 0.20;   // 読み取りの軸受けだけ 0.20（磁石の振れを 0.25 以内に入れるため。下の echo ⑤）
SLIP     = FIT_SLIP;  // 🔒 狙いの隙間。parts/fit.scad が 1 か所で持つ（_v6_portrait.scad が include 済み）。
                      //    皿は表をプレート側にして刷るので、この穴は**口が上**＝ fit_hole_up の側で、
                      //    初層の太りの打ち消し（FIT_BURN）は要らない ＝ 狙いの隙間だけが効く。
                      //    ⚠ 0.05 に詰めれば二面幅の遊びは 1.05 → 0.52 度になるが、それは数式の外の値。
                      //    ゲージ（🔒 2026-09-10・peg_gauge）で裏の取れているのは +0.1 の方なので離れない
MINWALL  = 0.30;   // 🔒 薄壁の下限（docs/PRINT.md §2「0.3mm が形になる」）
MAG_D    = 4.00;   // 🔒 φ4 磁石のポケット。SK本舗 4.10 → ELEGOO は縮み ≒ 0 なので 4.00
                   //    （PRINT.md「SK 6.10 → ELEGOO 6.00」と同じ引き算）
MAG_T    = 2.00;   // 📄 AS5600 キット付属の径方向着磁 φ4 × 2
MAG_PKT  = 2.20;   // ポケットの深さ（磁石の上に 0.2 の空き）。knob_v5 の MAG_DEPTH と同じ
LEADCH   = 0.30;   // 歯の端の食い付き面取り（閉じるとき歯先どうしが乗り上げないように）

// 積み上げの見込み（⚠ 私の仮定。実測ではない）
TOL_SHELL = 0.20;  // 前の殻の中の 1 寸法
TOL_STACK = 0.20;  // 背面の殻 → 柱 → 板／ReSpeaker
TOL_SPLIT = 0.15;  // 合わせ面の閉じ残り
TOL_CHIP  = 0.25;  // 📄 SOIC-8 の高さ 1.35〜1.75 ＋ はんだ 0.05〜0.15

// ============================================================
// 1. 面と鎖（親から導く。直書きしない）
// ============================================================
// WALL_IN（21.0 前の壁の内面）は 🔒 親が 31 行で持つ。ここでは定義しない
FACE_Z  = BODY_Z;                 // 23.0 前の面
RS_TOP  = RS_Z + 1.85;            // 18.85 ReSpeaker のマイク面（前）
RS_EDGE = RS_X + 34.007;          // 36.007 ReSpeaker の右の縁（📄 BOARD_H）
PCB_TOP = HB_Z + HB_T;            // 4.6 中継基板の表面
CHIP_TOP= PCB_TOP + CHIP[2];      // 6.35 AS5600 の天面（エアギャップはここから測る）

// 🔴 歯車の使える帯は ReSpeaker のマイク面 〜 前の壁の内面の 2.15 しかない。
//    そこへ「前の殻の鎖」と「背面の殻の鎖」が別々にぶら下がるので、歯幅は 1.8 では取れない。
BAND    = WALL_IN - RS_TOP;                      // 2.15
TOL_XS  = TOL_SHELL + TOL_STACK + TOL_SPLIT;     // 0.55 殻とスタックの相対ずれ（最悪）

// ---- 歯車の平面 ----
// 🔒 2026-09-13 デザイン担当が A5 を入れた（GEAR_W 1.8 → 1.4・GZ 19.05 → 19.40）。
//    ⇒ **この 3 つは親が持つ。**ここで数字を書き直さない（片方だけ動く事故のもと）
GW      = GEAR_W;                 // 1.40 つまみ・中継の歯幅（親）
GBOT    = GZ;                     // 19.40 歯車の底（親）。天面 GTOP も親が持つ
SGW     = 1.20;                   // 読み取りの歯幅（板の鎖にぶら下がるので細くする）
SGBOT   = 19.30;                  // 読み取りの歯車の底（板の面から 14.70）
SGTOP   = SGBOT + SGW;            // 20.50

// ============================================================
// 2. 歯形（インボリュート）
//   🔴 親のモデルは「円柱の塊」で、歯は 1 枚も切っていない。切ると分かること:
//      モジュール 0.5・歯末 1.0m・バックラッシュ 0.24 だと**歯先の厚みが 0.21mm**で、
//      薄壁の下限 0.3mm を割る。⇒ 歯末を 0.85m に詰めて 0.32mm を作る（echo ②）
// ============================================================
G_PA   = 20;      // 圧力角
G_THIN = 0.12;    // 歯厚の削り（1 枚あたり）。噛み合い 1 か所のバックラッシュ = 2 × 0.12 = 0.24
G_ADD  = 0.85;    // 歯末（× モジュール）
G_DED  = 1.25;    // 歯元（× モジュール）
G_SEG  = 8;       // インボリュートの分割

function invd(a) = tan(a) * 180 / PI - a;          // インボリュート関数（度）
function g_rp(z)  = GEAR_M * z / 2;
function g_rb(z)  = g_rp(z) * cos(G_PA);
function g_ra(z)  = g_rp(z) + GEAR_M * G_ADD;
function g_rf(z)  = g_rp(z) - GEAR_M * G_DED;
function g_half(z) = (GEAR_M * PI / 2 - G_THIN) / (2 * g_rp(z)) * 180 / PI + invd(G_PA);
function g_tipth(z) =                                // 歯先の厚み（mm）
    2 * (g_half(z) - invd(acos(g_rb(z) / g_ra(z)))) * PI / 180 * g_ra(z);

function _flank(z, i) = let (r0 = max(g_rb(z), g_rf(z)),
                             r  = r0 + (g_ra(z) - r0) * i / G_SEG,
                             a  = g_half(z) - invd(acos(g_rb(z) / r)))
                        [r * cos(a), r * sin(a)];

module gear2d(z) {
    rf = g_rf(z);
    circle(r = rf + 0.01);
    for (k = [0 : z - 1]) rotate(k * 360 / z) polygon(concat(
        [[rf * cos(-g_half(z) - 3), rf * sin(-g_half(z) - 3)]],
        [for (i = [0 : G_SEG]) let (p = _flank(z, i)) [p[0], -p[1]]],
        [for (i = [G_SEG : -1 : 0]) _flank(z, i)],
        [[rf * cos(g_half(z) + 3), rf * sin(g_half(z) + 3)]]));
}
// 歯車の板（端に食い付きの面取りを付ける。閉じるときに歯先どうしが乗り上げない）
module gear3d(z, h) hull_chamfer(z, h);
module hull_chamfer(z, h) {
    linear_extrude(h) gear2d(z);
    // 上下の端を LEADCH だけ細らせる（歯先を落とすだけ。歯元は触らない）
    for (s = [0, 1]) translate([0, 0, s ? h - LEADCH : 0])
        difference() {
            linear_extrude(LEADCH) circle(r = g_ra(z) + 0.5);
            translate([0, 0, -0.01]) cylinder(r1 = s ? g_ra(z) : g_ra(z) - LEADCH,
                                              r2 = s ? g_ra(z) - LEADCH : g_ra(z),
                                              h = LEADCH + 0.02);
        }
}
module gear_body(z, h) intersection() { linear_extrude(h) gear2d(z); gear_env(z, h); }
// 位相（🔴 塊で置いていたときは無かった条件）。相手の方を向く線に、片方は歯・片方は歯溝が来る。
//   rB = (θ+180) − (rA − θ)·zA/zB + 180/zB   （θ = A から B を見た角）
function mesh_rot(rA, zA, zB, th) = (th + 180) - (rA - th) * zA / zB + 180 / zB;
TH_KI  = atan2(IDLER[1] - KN_C[1], IDLER[0] - KN_C[0]);
TH_IS  = atan2(SENS[1] - IDLER[1], SENS[0] - IDLER[0]);
ROT_K  = 0;
ROT_I  = mesh_rot(ROT_K, GEAR_N, GEAR_NI, TH_KI);
ROT_S  = mesh_rot(ROT_I, GEAR_NI, GEAR_N, TH_IS);
module gear_env(z, h) {                                  // 歯先を上下で LEADCH 落とす外套
    r = g_ra(z);
    cylinder(r1 = r - LEADCH, r2 = r, h = LEADCH);
    translate([0, 0, LEADCH]) cylinder(r = r, h = h - 2 * LEADCH);
    translate([0, 0, h - LEADCH]) cylinder(r1 = r, r2 = r - LEADCH, h = LEADCH);
}

// ============================================================
// 3. つまみ ── 皿（外）＋ ハブ（内）の 2 部品で壁を挟む
//
//   🔴 いまの形は**成立していない**: 皿の抜きが φ11.0 なのに殻の軸穴が φ9.0 で、
//      皿の肉（内縁 r5.5）に届く軸は最大でも φ8.75。**直径で 2.25 足りない**（echo ③）。
//   ⇒ 皿を「中空の帽子」にする。スカート（φ12.6）が殻の穴（φ12.85）の中で回り、
//      壁の外は皿・内はハブで挟む。**皿の見た目（φ28.5・抜き φ11・厚み 2.5）は変えない。**
//      要求は殻の軸穴 φ9.0 → φ12.85（皿の下に隠れる。皿は r14.25 まで被さる）
// ============================================================
// 🔒 2026-09-13 デザイン担当が A1 を入れた（KN_BORE 9.0 → 12.85）。親のコメントの指示どおり
//    スカートは**穴から導く**。ここに 12.60 と書かない
KN_SKIRT = KN_BORE - RUN;         // 12.60 スカートの外径（軸受け）
KN_PEG   = 8.60;                  // スカートの内径＝ハブの柱
KN_FLAT  = 6.60;                  // 柱の二面幅（回り止め）
// KN_DISHZ（23.05・皿の裏）は 🔒 親が持つ（A4 が入った）。ここでは定義しない
KN_ENG   = 1.80;                  // 柱の掛かり
// 🔒 2026-09-13 裁定 #2（調停役）。皿の穴は真円ではなく**柱と同じ二面幅**にする。
//    それまでは穴が真円で、φ8.60 の柱は**どの角度でも φ8.70 の真円に収まっていた**
//    ＝ 二面幅に相手がいない ＝ トルクが 1 つも伝わっていなかった
//    （chk_torque_05 / _20 / _45 がどれも 0.0000mm3 だった）。
// 🔒 2026-09-13 裁定 #2 を**取り消し**（ユーザー）。「上からみて『接着してるな～』って
//    分かるようなものは、ネジの頭を出すより悪い」。栓は φ11 の穴の**真下**にあり、
//    穴の底がそのまま栓の天面だった ＝ 見えるのは接着剤そのものだった。
//    ⇒ 接着を**前の壁の内側**へ移す。φ11 の穴から見えるのは、皿の呼び込みの円錐と
//      柱の天面（どちらも印刷したままの面）だけ。接着剤は 1 つも見えない。
//    接着の面は 2 つ:
//      A スカートの下端の輪（z GTOP・穴の縁 → φBND_UC）… 引っ張りで受ける。主
//      B 柱と穴の隙間（SLIP/2 ＝ 0.05 片側・GTOP → BND_STOPZ）… せん断で受ける。従
//    逃げも 2 つ。どちらも「見える所・回る所へ出さない」ためにある:
//      外へ BND_UC   … スカートの下端を細くする。軸受けの隙間（RUN/2 ＝ 0.125）へ上がらせない
//      上へ BND_STOP … 穴の上の方に溝を彫る。円錐（＝穴から見える所）へ届かせない
//    🔴 接着剤は UV レジンではない。**2 液エポキシ**。理由は 2 つとも「場所を移した」結果:
//      ① A も B も壁の内側の閉じた隙間で、**UV が 1 本も入らない**
//      ② エポキシは可使時間があるので、裁定 #2 の手順 2「回ることを確かめる」が
//         そのまま残る（瞬間接着剤はここで失格になったが、それは CA 固有の欠点）
BND_UC    = 11.80;   // スカートの下端の外径（KN_SKIRT 12.60 から 0.40 細くする）
BND_UCZ   = WALL_IN - GTOP;   // 0.20 細い所の高さ。壁の内面で終わるので軸受けは 1 つも短くならない
BND_STOPZ = 21.80;   // 毛管止めの溝の下端。🔴 22.00 だと溝の天井（22.30）と円錐の底（22.59）の
                     //   間に残る内向きの庇が 0.29 しかなく、_stl_preflight が「平たい肉 0.29（下限 0.42）」
                     //   を 2 か所で出した。0.20 下げて庇を 0.49 にした（接着 B は 1.20 → 1.00 に減る）
BND_STOPT = 0.30;    // 溝の高さ
BND_STOPD = 9.70;    // 溝の径（穴 φ8.70 から 0.50 外へ）
BND_DRY   = GTOP + KN_ENG - (BND_STOPZ + BND_STOPT);   // 0.30 溝より上に残る「乾いた穴」
BND_DRAW  = 0.20;    // ⚠ 絵の厚み。実際の膜は A が 0 に近く B が 0.05。explode で場所が見えるように太らせる

// 回り止め（可動域）。🔒 ファームは壁があることを前提に書いてある:
//   firmware/esp32/src/main.cpp 660行「本番の機構は壁があるので 0..SPAN の外へは行けない」
//   platformio.ini の KATANORI_KNOB_SPAN_DEG = 310 ⇒ 可動域は 310 度より少し広いこと
// 🔒 2026-09-13 デザイン担当が A2 を入れた。STP_R / STP_D / STP_W / STP_DEP / STP_ISL と
//    抜き穴（STP_VENT）は**親が持つ**。私が持つのはピンの出しろだけ。
//    ⚠ 親の溝には抜き穴があり、私の複製には無かった（＝既にずれていた）
STP_PIN  = 0.90;                  // ピンの出しろ。🔴 1.15 だと溝の底（22.0）を 0.10 掘っていた（0.31mm3）

// 🔒 2026-09-13 リードスイッチ用の磁石（電源を切る側）。運び手は**皿の裏**と決めた（機構担当）。
//   皿の肉は実測 1.698（輪で切って 体積 ÷ 面積。窪み KN_SINK は中実の円錐なので中心まで効く）。
//   ⇒ φ4 × 1 を埋めて天井 0.698（🔒 薄壁の下限 0.30 に対し余裕あり）。φ4 × 1.5 は入らない。
//   🔴 角度は止めピンから +90 度。溝を走らないので角度は自由で、ピンと離せる
//      （ピンから +10 度 だと中心間 2.57 しか取れず φ4 が置けなかった）。
//   ⚠ 圧入は採らない（PRINT.md「磁石は圧入にならず抜ける」）。A5 の UV レジンと同じ工程で留める。
//   🔴 2026-09-13 に r8.4・+90 度 から動かした。リード（3.3 角）が入るのは
//      **板の右の谷（箱 X 37〜46）だけ**で（前の壁の下は全周 2.15 しかない・デザイン担当の実測）、
//      そこへ届かせるには磁石を外周へ出し、OFF のとき角度 0（＝ +X）へ来させる必要がある。
//      島が 20 度 になったので OFF はピンが −10 度 ⇒ **磁石はピンから +10 度**。
//   🔴 φ4 はこの角度に置けない。ピンとの中心間が 3.50 要るので 芯 r ≥ 12.53 か ≤ 6.38 になり、
//      前者は外縁 14.53 が皿の縁 14.25 を割り、後者は内縁 4.38 が抜き 5.50 を割る。⇒ **φ3 が上限**。
//   ⭐ 外縁の到達点は磁石の径によらず X 37.95（縁 14.25 − 薄壁 0.30 で決まる）。
//      ⇒ φ3 でも谷への届き方は φ4 と同じで、失うのは体積だけ（12.57 → 7.07mm³）。
//   🔴 2026-09-13 もう一度動かした。**止めピンの反対側**へ置く。
//      きっかけは「リード 3.2 角が入るのは板の右の谷だけ」という報告だが、その前提は
//      「前の壁の下は 2.15 しかない」だった。**前の壁は彫れる。**止めの溝があるのは
//      r 7.95〜10.95（印刷）だけで、それ以外の半径では内面から 23.0 − 0.30 = **22.70 まで 1.70 彫れる**。
//      ⇒ リードに使える深さは 2.15 ＋ 1.70 = **3.85 > 3.2**。谷でなくてもリードは入る。
//      ⇒ 磁石をピンの反対側（つまみの左）へ置けば、**リードを磁石の真下に置ける**。
//      ⇒ ピンとの離れの縛りが消えるので **φ4 に戻せる**（φ3 の 7.07 → 12.57mm³）。
MAG2_D   = 4.00;                  // ポケットの径（ELEGOO は縮み ≒ 0）
MAG2_T   = 1.00;                  // 磁石の厚み
MAG2_R   = 11.75;                 // 芯の半径。外縁 13.75 ＝ 縁 14.25 まで 0.50
                                  //   🔴 11.95（縁 0.30 ちょうど）から引いた。0.30 は薄壁の下限そのもので
                                  //      余裕が無く、_stl_preflight も「先細りの縁 0.30→0.43」と出していた
MAG2_ANG = 10;                    // 止めピン（180 度）の 170 度 反対。
                                  //   OFF（ピンが島の縁 −10 度）のとき、磁石は world 180 度
                                  //   ＝ つまみの左・箱 X 12.05・Y 30.04 に来る
function knob_travel() = 360 - STP_ISL - 2 * asin(STP_D / 2 / STP_R);

module knob_dish() color("#3c3f43") translate([KN_C[0], KN_C[1], 0]) {
    difference() {
        union() {
            translate([0, 0, KN_DISHZ]) cylinder(d = KN_OD, h = KN_OUT);         // 皿
            translate([0, 0, GTOP]) cylinder(d = KN_SKIRT, h = KN_DISHZ - GTOP); // スカート
            rotate(180) translate([STP_R, 0, KN_DISHZ - STP_PIN])   // 🔴 島（角度 0）の反対側
                cylinder(d = STP_D, h = STP_PIN + 0.01);            // 止めピン
        }
        translate([0, 0, KN_DISHZ + KN_OUT - KN_SINK])
            cylinder(d1 = KN_OD - 6.0, d2 = KN_OD - 1.5, h = KN_SINK + 0.01);
        translate([0, 0, KN_DISHZ - 0.01]) cylinder(d = KN_ID, h = KN_OUT + 1);  // 抜き φ11
        rotate(MAG2_ANG) translate([MAG2_R, 0, KN_DISHZ - 0.01])                // リード用磁石のポケット
            cylinder(d = MAG2_D, h = MAG2_T + 0.01);
        intersection() {                                     // 柱を受ける穴（二面幅つき）
            translate([0, 0, GTOP - 0.01]) cylinder(d = KN_PEG + SLIP, h = KN_ENG + 0.01);
            translate([-KN_PEG, -(KN_FLAT + SLIP) / 2, GTOP - 1])
                cube([2 * KN_PEG, KN_FLAT + SLIP, KN_ENG + 2]);
        }
        translate([0, 0, BND_STOPZ]) cylinder(d = BND_STOPD, h = BND_STOPT);     // 毛管止めの溝
        translate([0, 0, GTOP - 0.01]) difference() {          // スカートの下端を細く（外への逃げ）
            cylinder(d = KN_SKIRT + 2, h = BND_UCZ + 0.01);
            translate([0, 0, -0.5]) cylinder(d = BND_UC, h = BND_UCZ + 1.0);
        }
        translate([0, 0, GTOP + KN_ENG - 0.01])                                  // 呼び込みの円錐
            cylinder(d1 = KN_PEG + SLIP, d2 = KN_ID, h = KN_DISHZ - GTOP - KN_ENG + 0.02);
    }
}
// 呼び込みの円錐 ── **φ11 の穴から見える所**。2026-09-13 からここは**空のまま**。
//   栓（裁定 #2）はここを満たしていた。取り消したので、穴から見えるのは
//   この円錐（皿の印刷面）と、その底の柱の天面（ハブの印刷面）の 2 つだけになった。
//   🔴 円錐は皿の穴と**同じ式**で引く。別に引き直すと作図差が出て、面で乗るだけの所に
//      体積が立つ（最初 0.0833mm3 出た）
module knob_cone() translate([KN_C[0], KN_C[1], GTOP + KN_ENG - 0.01])
    cylinder(d1 = KN_PEG + SLIP, d2 = KN_ID, h = KN_DISHZ - GTOP - KN_ENG + 0.02);

// 接着剤（2 液エポキシ）。実体として持つ ── 磁石と同じで、模型に入る物である。
//   ⚠ 厚みは BND_DRAW で太らせた**絵**。当たり検査の実体側には入れない（0.05 の板は細片になる）。
//      入れるのは「見える所・回る所へ届いていないか」を見る検査だけ。
module knob_bond() color("#e0a030", 0.90) translate([KN_C[0], KN_C[1], 0]) {
    difference() {                                   // A スカートの下端の輪（歯車の天面に乗る）
        translate([0, 0, GTOP - BND_DRAW]) cylinder(d = BND_UC, h = BND_DRAW);
        translate([0, 0, GTOP - BND_DRAW - 1]) cylinder(d = KN_PEG + SLIP, h = BND_DRAW + 2);
    }
    difference() {                                   // B 柱と穴の隙間（溝で止まる）
        // 🔴 ここは**実寸**で描く（膜 0.05）。太らせると gface で柱の縁から橙がはみ出し、
        //    「穴から接着剤が見える」という嘘の絵になる
        translate([0, 0, GTOP]) cylinder(d = KN_PEG + SLIP, h = BND_STOPZ - GTOP);
        translate([0, 0, GTOP - 1]) cylinder(d = KN_PEG, h = BND_STOPZ - GTOP + 2);
    }
}
module knob_reed_magnet() color("#e8e8ea") translate([KN_C[0], KN_C[1], 0])
    rotate(MAG2_ANG) translate([MAG2_R, 0, KN_DISHZ]) cylinder(d = MAG2_D, h = MAG2_T);
module knob_hub() color("#8d949c") translate([KN_C[0], KN_C[1], 0]) {
    translate([0, 0, GBOT]) rotate([0, 0, ROT_K]) gear_body(GEAR_N, GW);           // 歯車
    intersection() {                                                              // 柱（二面幅）
        translate([0, 0, GTOP - 0.01]) cylinder(d = KN_PEG, h = KN_ENG + 0.01);
        translate([-KN_PEG, -KN_FLAT / 2, GTOP - 1]) cube([2 * KN_PEG, KN_FLAT, KN_ENG + 2]);
    }
}
// knob_stop_groove() は 🔒 親が持つ（抜き穴つき）。ここでは定義しない

// ============================================================
// 4. 中継の歯車 ── 前の壁から下ろした止まり軸に載るだけ
//   下は ReSpeaker（18.85）・上は壁（21.0）で、使える帯は 2.15。
//   軸受けの長さは 1.70 しか取れないので、**倒れは軸受けではなく上下の鍔で止める**
// ============================================================
ID_PIN  = ID_PIN_D;               // 3.00 前の壁から生やす止まり軸（🔒 親が持つ）
ID_BORE = ID_PIN + RUN;           // 3.25
ID_FLG  = 10.00;                  // 上下の鍔（倒れ止め）。φ10 なら隣の歯先 r7.425 と 12.5 - 7.425 = 5.075 で当たらない
ID_FT   = 0.15;                   // 鍔の厚み
ID_BOT  = GBOT - ID_FT;           // 19.25
ID_TOP  = GTOP + ID_FT;           // 20.95
ID_PINZ = ID_BOT - 0.10;          // 軸の先（鍔より 0.10 下・ReSpeaker まで 0.30）

module idler() color("#9aa5b1") translate([IDLER[0], IDLER[1], 0]) rotate([0, 0, ROT_I]) difference() {
    union() {
        translate([0, 0, GBOT]) gear_body(GEAR_NI, GW);
        translate([0, 0, ID_BOT]) cylinder(d = ID_FLG, h = ID_FT);
        translate([0, 0, GTOP])   cylinder(d = ID_FLG, h = ID_FT);
    }
    translate([0, 0, ID_BOT - 1]) cylinder(d = ID_BORE, h = 6);
}
// 🔒 中継の軸の形は**親が持つ**（idler_pin()）。私は先端の Z だけを関数 1 行で上書きする。
//    ⇒ ID_FT（鍔の厚み）を動かせば追従し、軸の形に親が何か足しても自動で入る。
//    🔴 モジュールごと複製してはいけない。今日それで事故った（私の複製した溝には親の抜き穴
//       STP_VENT が無く、検査が「抜き穴の無い溝」を見ていた）。
//    ⚠ 変数では上書きできない（最後の代入の右辺が最初の代入の位置で評価されるため）。
//       関数とモジュールだけが上書きできる ── 最小の実験で確かめた。
function id_pin_bot() = ID_PINZ;

// ============================================================
// 5. 読み取り ── ロータ（軸＋磁石）＋ 歯車 ＋ 板に共締めする軸受けブラケット
//
//   🔴 なぜ板側で受けるのか（echo ⑥）:
//     エアギャップの許容は 0.5〜3.0 で、下限を割ると磁石がチップに当たる。
//     ロータを**前の殻から吊る**と、鎖が 前の殻 → 合わせ面 → 背面の殻 → 柱 → 板 → チップ と
//     6 段になり、最悪 0.84mm 振れる（RSS 0.35）。1.10 の狙いに対して 0.26 まで落ちる。
//     **板の面を基準にすると鎖は ブラケット → ロータ → チップ の 3 段**で、最悪 0.41（RSS 0.27）。
//   ⚠ 代わりに板へ 2 つ頼む（報告の 4 章）。頼めないなら磁石を大きくするしかない。
MAG_GAP2 = 1.10;                   // 🔒 knob_v5 の CHIP_GAP 1.1（実機で AGC が通った値）
MAGZ     = CHIP_TOP + MAG_GAP2;    // 7.45 磁石の下面＝ロータの下端
ROT_D    = 7.00;                   // ロータの胴（磁石 φ4.0 に肉 1.5）
ROT_WST  = 3.60;                   // くびれ。ReSpeaker の縁まで 38.2 - 36.007 = 2.193 しかない
// 🔴 2026-09-13: 8.60 → 8.10。ReSpeaker の柱（POSTS[4]・箱 33.577, 5.457・φ5.0・Z 2.0〜17.0）が
//    読み取りの芯まで 6.48 しかなく、鍔 8.60 は 0.32 食い込んでいた（chk_post_rot 0.1298mm³）。
//    ⚠ 鍔は筒の穴 7.20 より大きくないと座れないので、柱が φ5.0 のままだと上限 7.36 ＝ 掛かり 0.08 で成立しない。
//    ⇒ **柱を φ4.0 にしてもらう前提**で 8.10（掛かり 0.45・柱まで 0.13 空く）。デザイン担当へ要求済み。
ROT_COL  = 8.10;                   // 受けの鍔
// 🔴 ReSpeaker は板の裏（XIAO 面）に Z 15.71 まで垂れている物がある
//    （X 31.31〜36.01・Y 3.55〜16.02。_v6_gear_probe.scad で測った）。
//    φ3.786 より太い所は**全部 15.71 より下**でなければならない。検査で 2.30 → 0.35mm3 と出た
RS_UNDER = 15.71;
BRK_TOP  = 15.10;                  // 軸受けの天面（ここで鍔を受ける）
BRK_BOT  =  8.80;                  // 軸受けの底。磁石の芯 8.45 とほぼ同じ高さまで下ろす
                                   //   （磁石が軸受けの中に入るので、芯の振れが遊びの半分で止まる）
BRK_BORE = ROT_D + RUN_S;          // 7.20
BRK_OD   = BRK_BORE + 2 * 1.20;    // 9.60
// 🔴 歯車を「段」で受けようとすると、ReSpeaker の面 18.85 と歯車の底 19.30 のあいだが
//    0.45 しかなく、逃げ 0.25 を引いた段は**厚み 0.20**にしかならない（実績の下限 0.42 を割る。
//    _stl_preflight が「平たい肉 0.20mm」で捕まえた）。⇒ 段はやめ、**歯車を止まり穴で被せて
//    穴の天井を柱の頭で受ける**。柱 19.30〜20.10（0.80 掛かり）・天井の肉 0.40
ROT_SHLD = 19.30;                  // 柱の根元（＝歯車の底）
// 🔴 2026-09-13: 20.10 → 20.05。読み取りの歯車の止まり穴の天井が **0.40** で、
//    _stl_preflight が「平たい肉 0.40mm（実績の下限 0.42 を割る）」と出した。
//    ⚠ PRINT.md §2 は「薄壁の下限 0.3mm」で、ツールの 0.42 とは別の数だが、
//       どちらが正かを争うより両方を超える形にするほうが安い（掛かりは 0.80 → 0.75 になるだけ）。
ROT_PEGT = 20.05;                  // 柱の頭（歯車の穴の天井が乗る面）。天井 0.45
SG_PRESS = 0.05;                   // 歯車の穴の締め代（PRINT.md「ELEGOO は 0.05 で丁度」）

module rotor() color("#c8b98a") translate([SENS[0], SENS[1], 0]) rotate([0, 0, ROT_S]) difference() {
    union() {
        translate([0, 0, MAGZ])      cylinder(d = ROT_D, h = BRK_TOP - MAGZ);
        translate([0, 0, BRK_TOP])   cylinder(d = ROT_COL, h = 0.30);           // 受けの鍔
        translate([0, 0, BRK_TOP + 0.30]) cylinder(d1 = ROT_COL, d2 = ROT_WST,   // 15.40〜15.68 で細り切る
                                                  h = RS_UNDER - 0.03 - (BRK_TOP + 0.30));
        translate([0, 0, RS_UNDER - 0.03]) cylinder(d = ROT_WST, h = ROT_SHLD - (RS_UNDER - 0.03));
        intersection() {                                            // 歯車を挿す柱（二面幅）
            translate([0, 0, ROT_SHLD - 0.01]) cylinder(d = ROT_WST, h = ROT_PEGT - ROT_SHLD + 0.01);
            translate([-ROT_WST, -(ROT_WST - 0.8) / 2, ROT_SHLD - 1])
                cube([2 * ROT_WST, ROT_WST - 0.8, ROT_PEGT - ROT_SHLD + 2]);
        }
    }
    translate([0, 0, MAGZ - 0.01]) cylinder(d = MAG_D, h = MAG_PKT + 0.01);   // 磁石のポケット
}
module rotor_magnet() color("#b9bcc0") translate([SENS[0], SENS[1], MAGZ])
    cylinder(d = MAG_D, h = MAG_T);
// 🔴 2026-09-13: 一度「圧入だけでは抜ける」と読んで天井に注ぎ口を開けたが、**要らなかった**。
//    測ると読み取りの歯車の上は**前の壁が 0.50 しか空いていない**。上へ逃げても 0.50 で壁に当たり、
//    そのとき柱への掛かりは 0.73 → **0.24 残る**。⇒ 中継と同じで、上下に挟まれていて抜けられない。
//    ⚠ PRINT.md の「圧入は抜ける」を読んで、**上に何があるかを見ずに**接着を足そうとした。
//       圧入は「組む途中の仮止め」として残す。見るのは part="ghold" -D LIFT=1。
module sgear() color("#9aa5b1") translate([SENS[0], SENS[1], 0]) rotate([0, 0, ROT_S]) difference() {
    translate([0, 0, SGBOT]) gear_body(GEAR_N, SGW);
    translate([0, 0, SGBOT - 1]) intersection() {                   // 止まり穴（下向き）。天井 0.45
        cylinder(d = ROT_WST - SG_PRESS, h = 1 + (ROT_PEGT - SGBOT));
        translate([-ROT_WST, -(ROT_WST - 0.8 - SG_PRESS) / 2, 0])
            cube([2 * ROT_WST, ROT_WST - 0.8 - SG_PRESS, 1 + (ROT_PEGT - SGBOT)]);
    }
}

// ブラケット（板の右下の M2 に共締め）。板の座標 → 箱は [+HB_X, +HB_Y]
BRK_SCR = [HB_X + 40.5, HB_Y + 3.5];               // 箱 (42.5, 6.5) = 板 (40.5, 3.5)
// 🔒 2026-09-13 チップの足跡は**親が持つ**（CHIP 胴 3.90 × 4.90 ／ CHIP_PAD 足跡 7.40 × 5.40）。
//    デザイン担当が KiCad の .kicad_mod のパッドを直接読んで確定した:
//      パッド 1〜8 は x ±2.475（size 1.95 × 0.6）⇒ X ±3.450 ＝ 6.90・Y はパッド列 4.41 だが
//      胴 4.90 の方が大きいので外形 6.90 × 4.90、逃げ 0.25/片側で 7.40 × 5.40。
//    🔴 私はこれを 4.9 × 6.2 と置いていた ＝ **90 度回っていた**。板の X がリードの張り出し、
//       Y が胴の長さである（gen_pcb.py の U4 は ang 0）。回路担当が実物の板で見つけた。
//    ⚠ ランドは直っていない（板側の足形の方が元から大きかった）。直したのはモデルだけ。
CHIP_BODY = [CHIP[0], CHIP[1]];   // 胴（親）
CHIP_SLDR = 0.10;                 // はんだの盛り
AXIS_CLR = max(ROT_D, norm(CHIP_PAD)) + 0.60;      // 8.50
// 🔒 2026-09-13 裁定: 0.80 → 2.15。共締めの M2 のナット（背 1.6）が AS5600（天面 6.45）を
//    平面で 1.56 跨ぐので、**足を厚くしてナットを U4 の上へ宙で持ち上げる**。
//      足の天面 4.60 + 2.15 = 6.75（U4 まで +0.30）／ ナットの天面 8.35（軸受けの底 8.80 まで +0.45）
//    ⚠ 1.85 だと U4 と ±0.00・2.40 だと軸受けまで 0.20。2.15 が両側に取れる値
BRK_FT  = 2.15;
module brk() color("#7fa77f") difference() {
    union() {
        hull() {                                                       // 足（ねじの座）
            translate([BRK_SCR[0], BRK_SCR[1], PCB_TOP]) cylinder(d = 6.4, h = BRK_FT);
            translate([BRK_SCR[0] - 3.4, BRK_SCR[1] - 0.8, PCB_TOP]) cylinder(d = 3.4, h = BRK_FT);
        }
        hull() {                                                       // 柱
            translate([BRK_SCR[0] - 3.4, BRK_SCR[1] - 0.8, PCB_TOP]) cylinder(d = 3.4, h = BRK_FT);
            translate([BRK_SCR[0] - 3.4, BRK_SCR[1] - 0.8, BRK_TOP - 3.0]) cylinder(d = 3.4, h = 3.0);
        }
        hull() {                                                       // 腕
            translate([BRK_SCR[0] - 3.4, BRK_SCR[1] - 0.8, BRK_TOP - 3.0]) cylinder(d = 3.4, h = 3.0);
            translate([SENS[0], SENS[1], BRK_TOP - 3.0]) cylinder(d = BRK_OD, h = 3.0);
        }
        translate([SENS[0], SENS[1], BRK_BOT]) cylinder(d = BRK_OD, h = BRK_TOP - BRK_BOT);
    }
    translate([SENS[0], SENS[1], BRK_BOT - 1]) cylinder(d = BRK_BORE, h = 40);
    // 芯まわりの逃げ。🔴 2026-09-13 に丸 1 本から 2 段へ変えた。
    //   丸 φ9.76 を足の高さ全部に通していたので、ナットの座（M2 の外接円 φ3.7）が
    //   AS5600 の側で削られ、残り 4.3mm²（丸ごとなら 6.23）しか無かった。
    //   足は BRK_FT 2.15 で天面 6.75 ＝ **チップの天面 6.45 より上**にいるので、
    //   チップの逃げは**チップの形**で足りる。丸が要るのはロータが通る上の段だけ。
    // 🔴 箱も筒と同じ高さ（BRK_BOT）まで通す。途中で切ると、その天面が厚み 0.00 の薄片として残る
    //    （最初 6.75 で止めて _stl_preflight に「平たい肉 0.00mm」で捕まった）。
    //    上へ伸ばしても失う物は無い ── ねじの芯 (42.5, 6.5) は箱の外（X で 4.3 > 4.0）
    translate([SENS[0] - (CHIP_PAD[0] + 0.6) / 2, SENS[1] - (CHIP_PAD[1] + 0.6) / 2, PCB_TOP - 1])
        cube([CHIP_PAD[0] + 0.6, CHIP_PAD[1] + 0.6, BRK_BOT - PCB_TOP + 1]);
    // 🔴 筒は Z で**重ねて**引く。境目を CHIPCLR_Z にちょうど合わせると、箱と筒の面が同じ高さに
    //    来て厚み 0.00 の薄片が残った（_stl_preflight が「平たい肉 0.00mm」で捕まえた）
    translate([SENS[0], SENS[1], PCB_TOP - 1])
        cylinder(d = ROT_D + 0.60, h = BRK_BOT - PCB_TOP + 1);
    translate([BRK_SCR[0], BRK_SCR[1], PCB_TOP - 1]) cylinder(d = 2.4, h = 10);
    // 🔴 ReSpeaker の柱の逃げ。筒（φ9.6）は柱と 0.82 重なっていた（chk_post_brk 10.9190mm³）。
    //    荷重は噛み合いで逆側（中継 33.0, 21.4 の方）へ押されるので、こちら側は開けてよい。
    //    ⚠ 径は親の POSTS から導く。柱が細くなれば逃げも自動で小さくなる
    translate([POSTS[4][0], POSTS[4][1], WALL - 1])
        cylinder(d = POSTS[4][3] + 0.60, h = POSTS[4][2] - WALL + 2);
    translate([-1, -1, -1]) cube([BODY_X + 2, HB_Y + 0.5 + 1, 60]);   // 板からはみ出す分を落とす
}

// ============================================================
// 6. 前の殻へ足す物・彫る物（デザイン担当が _v6_portrait.scad へ移す分）
// ============================================================
// 🔒 どちらも親のモジュールをそのまま呼ぶ。私は形を持たない
module shell_add()  { idler_pin(); }
module shell_cut()  { knob_bore_front(); knob_stop_groove(); }

// ============================================================
// 7. 組んだ姿
// ============================================================
module mech() { knob_dish(); knob_hub(); idler(); idler_pin(); rotor(); rotor_magnet(); sgear(); brk(); }
if (part == "gmech") { mech(); chip_solid(); board_solid();
    color("#55585c", 0.25) difference() {                       // 前の壁だけ（機構が見えるように）
        translate([0, 0, WALL_IN]) cube([BODY_X, BODY_Y, WALL]);
        shell_cut(); top_mics(); scr_pocket(); aa_window(); }
}
module chip_solid() color("#2c2c2a") {
    translate([SENS[0] - CHIP_BODY[0] / 2, SENS[1] - CHIP_BODY[1] / 2, PCB_TOP])     // 胴
        cube([CHIP_BODY[0], CHIP_BODY[1], CHIP[2] + CHIP_SLDR]);
    translate([SENS[0] - CHIP_PAD[0] / 2, SENS[1] - CHIP_PAD[1] / 2, PCB_TOP])       // リードとはんだ
        cube([CHIP_PAD[0], CHIP_PAD[1], 0.60 + CHIP_SLDR]);
}
// 🔒 2026-09-13 デザイン担当が中身を 8 つのモジュールに切り出した。
//    ⇒ **中身の形は親が持つ。**ここは名前を繋ぐだけにして、写しを置かない。
//    今後あちらが中身に足した物（電池のタブ・USB の殻など）は、私の検査へ自動で入る。
module rs_solid()  respeaker();
module bat_solid() battery();
module oled_solid() oled();
// 🔴 board_solid だけは親の hub_board() と**わざと違う**。hub_board() は板に加えて
//    「口の層」（板一面に 4.0 の塊・HB_PLUG）を持つが、あれは実体ではなく仮の場所取りである。
//    ブラケットの足はその塊の中に立つので、hub_board() で当たりを見ると必ず当たる。
//    ⇒ ここは**板だけ**を見る（数字は全部親から借りている）。
//    ⚠ 口の層が実体に割れたら、この検査は本物の口と突き合わせに変える
module board_solid() color("#d85a30") translate([HB_X, HB_Y, HB_Z]) cube([HB_W, HB_L, HB_T]);
// 🔒 殻は**親の shell_solid() をそのまま呼ぶ**。抜きを並べ直さない。
//    🔴 2026-09-13 に 2 回踏んだ:
//      ① 抜きを手で並べ直していて、親が足した glass_relief() が私の殻に入っていなかった
//      ② その後 shell_a() を呼んでいたが、**shell_a() には柱 10 本が入っていない。**
//         親の実体は shell_solid()（柱・cavity・aa_window・rsp_btn_relief まで全部入り）の方で、
//         shell_a() は古い形。⇒ 私の chk_*_shell は柱に対して盲だった（調停役の指摘）
module shell_mech(a = 1.0) color("#55585c", a) shell_solid();

// ============================================================
// 7b. 機構が見える図（2026-09-13・ユーザーの依頼で私が足した）
//
//   part="gspin" ／ -D SPIN=<つまみの角度（度）>
//   つまみを SPIN だけ回すと、3 枚が**正しい比で**連れて回る。
//     つまみ z28 を +SPIN ⇒ 中継 z22 は −SPIN × 28/22 ⇒ 読み取り z28 は +SPIN
//   ⇒ 端の 2 枚は 1:1 で同じ向き（中継の歯数は比に効かない）。可動域は 320.0 度。
//   🔴 これは**見るための図**であって、機構そのものは上の節が持つ。ここで形を作らない。
// ============================================================
SPIN = 0;
module spin_at(c, a) translate([c[0], c[1], 0]) rotate([0, 0, a])
    translate([-c[0], -c[1], 0]) children();
SPIN_I = -SPIN * GEAR_N / GEAR_NI;     // 中継（逆向き・歯数の比で速い）
SPIN_S =  SPIN;                        // 読み取り（つまみと同じ向き・1:1）

// 🔴 印（witness mark）。これが無いと、回した figure と回していない figure が見分けられない。
//    歯車の天面より少し上に赤い棒を 1 本ずつ置く（部品ではない・この図だけの物）
module spin_mark(c, r, z) color("#d8382f") translate([c[0], c[1], z])
    translate([0, -0.35, 0]) cube([r, 0.7, 0.35]);

module mech_spun() {
    // 皿は輪郭だけ（実体で置くと下の歯車を全部隠す）。印は一番上に出す
    spin_at(KN_C,  SPIN) {
        color("#3c3f43", 0.35) translate([KN_C[0], KN_C[1], FACE_Z]) difference() {
            cylinder(d = KN_OD, h = 0.4);
            translate([0, 0, -0.5]) cylinder(d = KN_OD - 1.2, h = 2);
        }
        knob_hub();
        spin_mark(KN_C,  KN_OD / 2, FACE_Z + 0.6);
    }
    spin_at(IDLER, SPIN_I) { idler();  spin_mark(IDLER, g_ra(GEAR_NI), FACE_Z + 0.6); }
    spin_at(SENS,  SPIN_S) { rotor(); rotor_magnet(); sgear();
                             spin_mark(SENS,  g_ra(GEAR_N),  FACE_Z + 0.6); }
    idler_pin(); brk(); chip_solid();
}
module spin_label() color("#20242a") translate([0, 0, FACE_Z + 2]) {
    translate([KN_C[0] - 24.0, KN_C[1] + 2.0])  linear_extrude(0.1) text("knob  z28", size = 2.2);
    translate([IDLER[0] + 7.0, IDLER[1] + 2.0])  linear_extrude(0.1) text("idler z22", size = 2.2);
    translate([SENS[0] - 21.0, SENS[1] - 6.0])   linear_extrude(0.1) text("sensor z28", size = 2.2);
    translate([4.0, 50.0]) linear_extrude(0.1)
        text(str("knob ", SPIN, " deg  ->  sensor ", SPIN_S, " deg   (1:1)"), size = 2.6);
    // 🔴 可動域は SPIN ±160.02（止めピンは島の反対側 180 度から出発する）。0〜320 ではない
    translate([4.0, 46.5]) linear_extrude(0.1)
        text(abs(SPIN) > knob_travel() / 2 ? "OUT OF TRAVEL  (limit +-160.02 deg)"
                                           : "travel  +-160.02 deg", size = 2.2);
}
// ---- part="ghold" … 何がどこで止まっているかの図（2026-09-13・ユーザーの依頼で私が足した）----
//   つまみの芯 → 読み取りの芯 の線に直角から見た**側面図**。触れている所が見えるように
//   Z 方向へ少しずつ引き離してある（-D EXP=0 にすると組んだ姿になる）。
//   🔴 断面（intersection で切る）はやめた。CLI の PNG 書き出しでは真偽演算の結果に色が乗らず、
//      最後に置いた色が全部に乗ってしまう（2026-09-13 に最小の実験で確かめた）。
//      引き離した図なら色がそのまま出るので、こちらを正とする。
EXP = 1;
LIFT = 0;                       // 1 で、回る 3 つを動ける限界まで動かした姿にする
module lim(dz) translate([0, 0, LIFT * dz]) children();
// 🔴 2026-09-13 ユーザー「それぞれの床の間にギアがあるならそう分かるように」:
//    **歯車は動かさない。動かすのは床の方。**歯車を Z へ散らすと、
//    「どの床とどの床の間にいるか」というただ一つ見たい事が消える。
//    ⇒ 前の壁を上へ・ReSpeaker を下へ・中継基板をさらに下へ開く。歯車 3 枚は真ん中に残る。
module mv(dz) translate([0, 0, EXP * dz]) children();
module floor_plate(z, c) color(c, 0.28)
    translate([-12, -6, z - 0.15]) cube([BODY_X + 30, BODY_Y + 12, 0.30]);
// ---- part="gstop" … 回転止めを顔の側から見る（2026-09-13・ユーザーの依頼）----
//   -D SPIN=<つまみの角度>。ピンが溝の中を走り、島に突き当たって止まるのが見える。
//   🔴 溝は「彫った跡」なので、切って見せると色が付かない。**溝の体積そのものを色で置く。**
if (part == "gstop") {
    color("#b8b09a") difference() {                       // 前の壁（つまみのまわりだけ）
        translate([KN_C[0], KN_C[1], WALL_IN]) cylinder(r = 15.5, h = WALL);
        translate([KN_C[0], KN_C[1], WALL_IN - 1]) cylinder(d = KN_BORE, h = WALL + 2);
    }
    color("#f2ead2") knob_stop_groove();                  // 溝（ピンの通り道）
    color("#3c3f43", 0.10) translate([KN_C[0], KN_C[1], KN_DISHZ])
        cylinder(d = KN_OD, h = 0.30);                    // 皿の輪郭
    spin_at(KN_C, SPIN) color("#d0342c")                  // 止めピン
        translate([KN_C[0], KN_C[1], 0]) rotate(180)
            translate([STP_R, 0, KN_DISHZ - STP_PIN]) cylinder(d = STP_D, h = STP_PIN + 0.5);
    color("#20242a") translate([0, 0, FACE_Z + 2.5]) {
        translate([KN_C[0] - 15.0, KN_C[1] + 17.0]) linear_extrude(0.1)
            text(str("knob ", SPIN, " deg"), size = 2.4);
        translate([KN_C[0] - 15.0, KN_C[1] + 13.4]) linear_extrude(0.1)
            text(abs(abs(SPIN) - knob_travel()/2) < 0.5 ? "STOP  (island)" :
                 (abs(SPIN) > knob_travel()/2 ? "OUT OF TRAVEL" : ""), size = 2.4);
    }
}

if (part == "ghold") {
    // ---- 上の床: 前の壁 ----
    mv(+6.0) { knob_dish(); knob_reed_magnet(); }        // 皿は壁の外なので、壁より上へ
    mv(+5.0)   knob_bond();                             // 接着剤はスカートの下端（壁の内側）
    mv(+4.0) { floor_plate(WALL_IN, "#c9c2a8"); idler_pin(); }
    // ---- 歯車の帯（ここは動かさない）----
    lim(+0.25) knob_hub();
    lim(-0.40) idler();
    lim(+0.50) sgear();
    // ---- 下の床: ReSpeaker ----
    // ReSpeaker とそれを留めている柱 2 本（POSTS[4] / POSTS[5]・M2 貫通＋ナット）
    mv(-4.0) { floor_plate(RS_TOP, "#b9c6b9");
               color("#8a8f96", 0.22) for (i = [4, 5]) difference() {
                   post_solid(POSTS[i]); post_hole(POSTS[i]); post_cb(POSTS[i]); } }
    // ---- さらに下: ロータの柱と板 ----
    mv(-6.0) { rotor(); rotor_magnet(); brk(); chip_solid(); }
    mv(-8.0)   floor_plate(PCB_TOP, "#d85a30");
}


if (part == "gspin") {
    mech_spun(); spin_label();
    // 相手の物は薄く。歯車の帯を上から見るので、前の壁と OLED は出さない
    color("#c9d3c9", 0.30) translate([RS_X, RS_Y, RS_Z]) cube([34.007, 82.024, 1.85]);
    color("#d85a30", 0.30) translate([HB_X, HB_Y, HB_Z]) cube([HB_W, HB_L, HB_T]);
    // 殻の輪郭（前の壁の内面に薄い板を敷いて、歯先と内壁の逃げが見えるようにする）
    color("#55585c", 0.12) difference() {
        translate([0, 0, WALL_IN]) cube([BODY_X, BODY_Y, 0.4]);
        translate([WALL, WALL, WALL_IN - 1]) cube([BODY_X - 2 * WALL, BODY_Y - 2 * WALL, 3]);
    }
}
if (part == "glook") { shell_mech(0.10); mech(); chip_solid(); }
if (part == "gguts") { shell_mech(0.08); mech(); chip_solid(); rs_solid(); board_solid(); bat_solid(); }
// 断面: つまみの芯と読み取りの芯を結ぶ線を含む厚み 6 の板で切る（機構の鎖が 1 枚に写る）
GSEC_A = atan2(SENS[1] - KN_C[1], SENS[0] - KN_C[0]);
if (part == "gcut")  intersection() {
    union() { shell_mech(1.0); mech(); chip_solid(); board_solid();
              color("#c9d3c9") translate([RS_X, RS_Y, RS_Z]) cube([34.007, 82.024, 1.85]);
              color("#b7c1b7") translate([RS_X, RS_Y, RS_UNDER])              // 板の裏に垂れている物
                  cube([34.007, 82.024, RS_Z - RS_UNDER]); }
    translate([KN_C[0], KN_C[1], 0]) rotate(GSEC_A) translate([-4, -3.0, -1])
        cube([34, 3.0, BODY_Z + 2]);
}
if (part == "gexp") {
    translate([0, 0, 26]) knob_dish();
    translate([0, 0, 16]) knob_hub();
    translate([0, 0, 12]) { idler(); sgear(); }
    translate([0, 0,  6]) { rotor(); rotor_magnet(); }
    brk(); chip_solid(); board_solid();
    translate([0, 0, 34]) shell_mech(0.10);
}
if (part == "gflat") {                                  // 刷る単位を並べた図
    translate([  0, 0, 0]) translate(-[KN_C[0], KN_C[1], 0]) knob_dish();
    translate([ 34, 0, 0]) translate(-[KN_C[0], KN_C[1], 0]) knob_hub();
    translate([ 62, 0, 0]) translate(-[IDLER[0], IDLER[1], 0]) idler();
    translate([ 82, 0, 0]) translate(-[SENS[0], SENS[1], 0]) sgear();
    translate([104, 0, 0]) translate(-[SENS[0], SENS[1], 0]) { rotor(); rotor_magnet(); }
    translate([120, 0, 0]) translate(-[SENS[0], SENS[1], 0]) brk();
}
if (part == "p_knob")  translate(-[KN_C[0], KN_C[1], 0]) knob_dish();
if (part == "p_khub")  translate(-[KN_C[0], KN_C[1], 0]) knob_hub();
if (part == "p_idler") translate(-[IDLER[0], IDLER[1], 0]) idler();
if (part == "p_sgear") translate(-[SENS[0], SENS[1], 0]) sgear();
if (part == "p_rotor") translate(-[SENS[0], SENS[1], 0]) rotor();
if (part == "p_brk")   translate(-[SENS[0], SENS[1], 0]) brk();

// ============================================================
// 8. 検査 ── 🔴 1 つずつ見る。空（MISSING）と 0 を分ける。
//    わざと古い値を入れて反応することを確かめてから読むこと（chk_ctrl）
// ============================================================
module all_gears() { knob_hub(); idler(); sgear(); }
module all_rot()   { knob_dish(); knob_hub(); idler(); rotor(); rotor_magnet(); sgear(); }

if (part == "chk_gear_shell") intersection() { all_gears(); shell_mech(); }
if (part == "chk_gear_rs")    intersection() { all_gears(); rs_solid(); }
if (part == "chk_rot_rs")     intersection() { union() { rotor(); rotor_magnet(); } rs_solid(); }
if (part == "chk_rot_bat")    intersection() { union() { rotor(); brk(); } bat_solid(); }
if (part == "chk_brk_chip")   intersection() { brk(); chip_solid(); }
if (part == "chk_rot_chip")   intersection() { union() { rotor(); rotor_magnet(); } chip_solid(); }
if (part == "chk_brk_board")  intersection() { brk(); board_solid(); }
if (part == "chk_mesh_ki")    intersection() { knob_hub(); idler(); }     // 噛み合い（バックラッシュ）
if (part == "chk_mesh_is")    intersection() { idler(); sgear(); }
if (part == "chk_knob_pin")   intersection() { knob_dish(); shell_mech(); }
if (part == "chk_pin_rotor")  intersection() { idler_pin(); rs_solid(); }
// 対照 1: 記録に残っている実際の当たり（CASE-V6-PLAN 9 章「歯車の平面を 18.8 に置いていて
//   ReSpeaker の頭に 0.05 触っていた」）を塊で再現する。ここが空なら chk_gear_rs が壊れている。
//   🔴 2026-09-13 に直した（私）。平面 19.05 の塊を置いていて、ReSpeaker の面 18.85 と
//      最初から触っておらず、**対照として空のまま通っていた**（＝何も証明していなかった）
OLDGZ = 18.80;
module old_gear_disc() { translate([KN_C[0], KN_C[1], OLDGZ]) cylinder(d = 15.0, h = 1.8);
                         translate([IDLER[0], IDLER[1], OLDGZ]) cylinder(d = 12.0, h = 1.8);
                         translate([SENS[0], SENS[1], OLDGZ]) cylinder(d = 15.0, h = 1.8); }
if (part == "chk_ctrl")       intersection() { old_gear_disc(); rs_solid(); }
if (part == "chk_ctrl2")      intersection() { all_gears(); rs_solid_up(); }
module rs_solid_up() translate([0, 0, 0.6]) rs_solid();   // ReSpeaker を 0.6 持ち上げた対照
// 対照 3: 歯車を 0.4 前へ寄せる。前の壁に当たるはず（chk_gear_shell が生きている証拠）
if (part == "chk_ctrl3")      intersection() { translate([0, 0, 0.4]) all_gears(); shell_mech(); }
// 対照 4: ロータを 0.5 下げる。磁石がチップに当たるはず（chk_rot_chip が生きている証拠）
if (part == "chk_ctrl4")      intersection() {
    translate([0, 0, -1.5]) union() { rotor(); rotor_magnet(); } chip_solid(); }
// 対照 5: 読み取りの歯車を中継へ 0.3 寄せる。噛み合いが食い込むはず（chk_mesh_is が生きている証拠）
// ⚠ 0.3 では 0.0895mm3 しか出ずぎりぎりだった（裁定 #6）。0.6 へ
if (part == "chk_ctrl5")      intersection() {
    translate(0.6 * (IDLER - SENS) / norm(IDLER - SENS)) sgear(); idler(); }
// 対照 6: ブラケットを芯へ 1.5 寄せる。チップに乗るはず（chk_brk_chip が生きている証拠）
if (part == "chk_ctrl6")      intersection() {
    translate(1.5 * (SENS - BRK_SCR) / norm(SENS - BRK_SCR)) brk(); chip_solid(); }
if (part == "chk_brk_rs")     intersection() { brk(); rs_solid(); }
// 止めの溝（前の面を 1.0 掘る）が OLED の頭（Z 19.15〜21.8・Y 39.3〜）に届いていないか
if (part == "chk_groove_oled") intersection() { knob_stop_groove(); oled_solid(); }
// 対照 7: 溝を 2.0 下げる。OLED の板（Y 39.30〜・Z 19.15〜20.15）に届くはず。
//   🔴 2026-09-13 に 0.9 から 2.0 へ直した。OLED が塊 → 板＋ガラスに割れた日に、
//      0.9 では届かなくなって**対照が空のまま通っていた**（ガラスは Y 44.69 から始まる）。
//      相手の形が変わったら、対照が生きているかを必ず見る
if (part == "chk_ctrl7")       intersection() {
    translate([0, 0, -2.0]) knob_stop_groove(); oled_solid(); }
if (part == "chk_brk_gear")   intersection() { brk(); all_gears(); }
if (part == "chk_rot_shell")  intersection() { union() { rotor(); sgear(); } shell_mech(); }

// ---- 中継が組んだ後に落ちないか（2026-09-13）----
// 組んだ後、中継の下には ReSpeaker（天面 18.85）がある。落ちられる分だけ落として、
// ① ReSpeaker に当たること ② それでも軸に嵌まったままであること、の 2 つを見る。
IDROP = 0.40;
if (part == "chk_idler_drop") intersection() { translate([0, 0, -IDROP]) idler(); rs_solid(); }
// 🔴 掛かりは「軸と穴の交差」では測れない（隙間があるので常に空になる。最初これで空を見た）。
//    穴の**空間**を筒で作って軸と交差させ、体積 ÷ 軸の断面 ＝ 掛かりの長さ で読む。
module idler_bore(dz) translate([IDLER[0], IDLER[1], ID_BOT - dz])
    cylinder(d = ID_BORE, h = ID_TOP - ID_BOT);
if (part == "chk_idler_stay") intersection() { idler_bore(IDROP); idler_pin(); }

// ---- 柱 10 本との当たり（2026-09-13・調停役の指摘）----
// 🔴 柱は床から 1.0〜17.15 で箱の真ん中を貫いているのに、検査が 1 本も無かった。
//    shell_a() に柱が入っていなかったため、chk_*_shell が「空」を返し続けていた。
if (part == "chk_post_brk")   intersection() { brk(); posts(); }
if (part == "chk_post_rot")   intersection() { union() { rotor(); rotor_magnet(); sgear(); } posts(); }
if (part == "chk_post_gear")  intersection() { all_gears(); posts(); }
// 対照 24〜26: それぞれを柱の方へ 2.0 寄せる。当たるはず
if (part == "chk_ctrl24")     intersection() { translate([-2.0, 0, 0]) brk(); posts(); }
if (part == "chk_ctrl25")     intersection() {
    translate([-2.0, 0, 0]) union() { rotor(); rotor_magnet(); sgear(); } posts(); }
// ⚠ 2.0 では届かなかった。ReSpeaker の柱の頭 17.00 ↔ 読み取りの歯車の底 19.30 で 2.30 空くため。
//    3.0 下げる（歯車 3 枚はどの柱の頭よりも上にいる、というのがここで言いたいこと）
if (part == "chk_ctrl26")     intersection() { translate([0, 0, -3.0]) all_gears(); posts(); }

// ---- リード用磁石の検査（2026-09-13）----
// 磁石は皿の裏と面一なので、殻（面 23.0）とは 0.05 空くはず
if (part == "chk_mag2_shell") intersection() { knob_reed_magnet(); shell_mech(); }
// 対照 22: 磁石を 0.30 沈める（＝皿から出す）。殻に当たるはず
if (part == "chk_ctrl22")     intersection() {
    translate([0, 0, -0.30]) knob_reed_magnet(); shell_mech(); }
// 磁石のポケットが止めピンを食っていないか（ピンは皿の一部なので、食えば穴が開く）
if (part == "chk_mag2_pin")   intersection() { knob_reed_magnet(); knob_dish(); }
// 対照 23: 磁石を止めピンの角度（180 度）へ置く。皿の肉と重なるはず
if (part == "chk_ctrl23")     intersection() {
    color("#e8e8ea") translate([KN_C[0], KN_C[1], 0]) rotate(180)
        translate([MAG2_R, 0, KN_DISHZ]) cylinder(d = MAG2_D, h = MAG2_T);
    knob_dish(); }

// ---- 接着の検査（2026-09-13・裁定 #2 の取り消しを自分で確かめる）----
// 🔴 ここで確かめたいのは強さではない。**接着剤が見える所・回る所へ出ていないこと**。
// ① 円錐（＝φ11 の穴から見える所）へ届いていないか。空が正
if (part == "chk_bond_cone")  intersection() { knob_bond(); knob_cone(); }
// 対照 21: 毛管止めの溝が無かった場合（接着剤を柱の天面まで伸ばす）。円錐に届くはず
//   ⚠ 0.30 分だけ円錐へ上がらせる。柱の天面で止めると面で触れるだけの細片（0.0533mm3）になり、
//      対照が「生きているかどうか分からない」値になった
module bond_no_stop() color("#e0a030") translate([KN_C[0], KN_C[1], 0]) difference() {
    translate([0, 0, GTOP]) cylinder(d = KN_PEG + SLIP, h = KN_ENG + 0.30);
    translate([0, 0, GTOP - 1]) cylinder(d = KN_PEG + SLIP - 2 * BND_DRAW, h = KN_ENG + 2);
}
if (part == "chk_ctrl21")     intersection() { bond_no_stop(); knob_cone(); }
// ② 軸受け（スカートの外・壁の穴の中）へ上がっていないか。空が正
module brg_gap() translate([KN_C[0], KN_C[1], WALL_IN]) difference() {
    cylinder(d = KN_BORE, h = WALL);
    translate([0, 0, -1]) cylinder(d = KN_SKIRT, h = WALL + 2);
}
if (part == "chk_bond_brg")   intersection() { knob_bond(); brg_gap(); }
// 対照 24: スカートを細くしなかった場合（接着剤の輪を軸受けの隙間まで広げる）。当たるはず
module bond_no_uc() color("#e0a030") translate([KN_C[0], KN_C[1], 0]) difference() {
    translate([0, 0, GTOP - BND_DRAW]) cylinder(d = KN_BORE, h = BND_DRAW + WALL);
    translate([0, 0, GTOP - BND_DRAW - 1]) cylinder(d = KN_PEG + SLIP, h = BND_DRAW + WALL + 2);
}
if (part == "chk_ctrl28")     intersection() { bond_no_uc(); brg_gap(); }
// ③ 接着剤はハブ（歯車の天面と柱）に食い込んで描いてある。**反応するのが正**
//    ＝ A の輪とハブの天面が本当に向き合っている（向き合っていなければ貼る相手がいない）
if (part == "chk_bond_hub")   intersection() { knob_bond(); knob_hub(); }
// ④ スカートを細くした分が軸受けを食っていないか。
//    軸受けの帯（壁の厚みの中のスカートの外面）と、細りで削った肉を当てる。0.0000 が正
module uc_cut() translate([KN_C[0], KN_C[1], 0]) difference() {      // 細りで削った肉
    translate([0, 0, GTOP]) cylinder(d = KN_SKIRT, h = BND_UCZ);
    translate([0, 0, GTOP - 0.5]) cylinder(d = BND_UC, h = BND_UCZ + 1);
}
module brg_band() translate([KN_C[0], KN_C[1], WALL_IN]) cylinder(d = KN_SKIRT, h = WALL);
if (part == "chk_uc_brg")     intersection() { uc_cut(); brg_band(); }
// 対照 25: 細りを 0.30 上へ伸ばす。軸受けの帯を食うはず
if (part == "chk_ctrl27")    intersection() {
    translate([0, 0, 0.30]) uc_cut(); brg_band(); }

// ---- 抜け止めの検査（2026-09-13）----
// 🔴 皿とハブが「触れているか」を実体で見る。締め代があるなら交差が出る。
//    空なら**二つの部品はどこにも接していない**＝軸方向に引き止める物が無い。
if (part == "chk_dish_hub")   intersection() { knob_dish(); knob_hub(); }
// 対照 17: 柱を「穴より 0.10 太い」図にする（＝締め代 0.10 で嵌めた場合）。ここは反応するはず。
//   🔴 最初 KN_PEG + 0.10 = 8.70 と書いたが、それは穴の径（KN_PEG + SLIP）とちょうど同じで
//      締め代 0 だった。対照が空のまま通るのはこの形の書き間違いで起きる
module knob_hub_tight() color("#8d949c") translate([KN_C[0], KN_C[1], 0])
    intersection() {
        translate([0, 0, GTOP - 0.01]) cylinder(d = KN_PEG + SLIP + 0.10, h = KN_ENG + 0.01);
        translate([-KN_PEG, -(KN_FLAT + SLIP + 0.10) / 2, GTOP - 1])
            cube([2 * KN_PEG, KN_FLAT + SLIP + 0.10, KN_ENG + 2]);
    }
if (part == "chk_ctrl17")     intersection() { knob_dish(); knob_hub_tight(); }

// ---- 回り止めの検査（2026-09-13・調停役の指摘を自分で確かめた）----
// 🔴 皿を軸まわりに回してハブに当てる。**反応するのが正**なので対照に置く。
//    全部空だった頃は二面幅に相手がおらず、トルクが 1 つも伝わっていなかった。
module dish_rot(a) translate([KN_C[0], KN_C[1], 0]) rotate([0, 0, a])
    translate(-[KN_C[0], KN_C[1], 0]) knob_dish();
if (part == "chk_ctrl18") intersection() { dish_rot(5);  knob_hub(); }
if (part == "chk_ctrl19") intersection() { dish_rot(20); knob_hub(); }
if (part == "chk_ctrl20") intersection() { dish_rot(45); knob_hub(); }

// ---- 対照 8〜16（2026-09-13・機構担当が足した）----
// 🔴 上の実体 15 本のうち、生きている対照が付いていたのは 6 本だけだった。
//    残り 9 本の「空」は何も裏付けが無かったので、1 本ずつ対にする。
//    どれも**わざと外した図**で、反応しなければ対になっている実体の検査が壊れている。
// 対照 8: ブラケットを 0.5 沈める。足が板に食い込むはず（chk_brk_board の対）
if (part == "chk_ctrl8")  intersection() { translate([0, 0, -0.5]) brk(); board_solid(); }
// 対照 9: ブラケットを 5.0 持ち上げる。腕が歯車の層へ入るはず（chk_brk_gear の対）
if (part == "chk_ctrl9")  intersection() { translate([0, 0, 5.0]) brk(); all_gears(); }
// 対照 10: ブラケットを ReSpeaker の下へ 4 寄せて 3 上げる。当たるはず（chk_brk_rs の対）
if (part == "chk_ctrl10") intersection() { translate([-4.0, 0, 3.0]) brk(); rs_solid(); }
// 対照 11: 皿を 0.5 沈める。裏が前の面へ食い込むはず（chk_knob_pin の対）
if (part == "chk_ctrl11") intersection() { translate([0, 0, -0.5]) knob_dish(); shell_mech(); }
// 対照 12: 中継をつまみへ 0.3 寄せる。噛み合いが食い込むはず（chk_mesh_ki の対）
// ⚠ 0.3 では 0.1083mm3 でぎりぎりだった（裁定 #6）。0.6 へ
if (part == "chk_ctrl12") intersection() {
    translate(0.6 * (KN_C - IDLER) / norm(KN_C - IDLER)) idler(); knob_hub(); }
// 対照 13: 中継の軸を 0.5 伸ばす。ReSpeaker の頭に届くはず（chk_pin_rotor の対。いま 0.30 空き）
if (part == "chk_ctrl13") intersection() { translate([0, 0, -0.5]) idler_pin(); rs_solid(); }
// 対照 14: 電池を Y へ 17 寄せる。ロータに届くはず（chk_rot_bat の対。いま Y の隔たり 16）
if (part == "chk_ctrl14") intersection() {
    union() { rotor(); brk(); } translate([0, -17, 0]) bat_solid(); }
// 対照 15: ロータを 0.6 左へ。くびれが ReSpeaker の右の縁に当たるはず（chk_rot_rs の対。いま 0.39 空き）
if (part == "chk_ctrl15") intersection() {
    translate([-0.6, 0, 0]) union() { rotor(); rotor_magnet(); } rs_solid(); }
// 対照 16: 読み取りを 0.6 右へ。歯先が右の内壁を貫くはず（chk_rot_shell の対。いま 0.3 空き）
// ⚠ 0.6 では 0.0930mm3 でぎりぎりだった（裁定 #6）。1.2 へ。歯先と内壁の逃げは 0.3 なので十分わざと外れている
if (part == "chk_ctrl16") intersection() {
    translate([1.2, 0, 0]) union() { rotor(); sgear(); } shell_mech(); }

// ---- 回しながらの当たり（2026-09-13）----
// 🔴 上の検査 19 本は**すべて SPIN = 0 の 1 姿勢**で見ている。歯車は回ると歯先の位置が変わるので、
//    0 度で空でも途中で当たる余地がある。`-D SPIN=<度>` を変えて同じ検査を掃く。
//    走らせ方: python hardware/frozen/v6/tools/_v6_gear_sweep.py
module spun_knob()  spin_at(KN_C,  SPIN)   { knob_dish(); knob_hub(); }
module spun_idler() spin_at(IDLER, SPIN_I) idler();
module spun_sens()  spin_at(SENS,  SPIN_S) { rotor(); rotor_magnet(); sgear(); }
module spun_all()   { spun_knob(); spun_idler(); spun_sens(); }

if (part == "spin_shell")   intersection() { spun_all(); shell_mech(); }
if (part == "spin_rs")      intersection() { spun_all(); rs_solid(); }
if (part == "spin_mesh_ki") intersection() { spun_knob(); spun_idler(); }
if (part == "spin_mesh_is") intersection() { spun_idler(); spun_sens(); }
if (part == "spin_brk")     intersection() { spun_sens(); brk(); }
if (part == "spin_pin")     intersection() { spun_idler(); idler_pin(); }
// 🔒 止めの検査: 可動域 320.04 度の中では空、外へ出すと止めピンが島に当たるはず。
//    ⇒ SPIN を可動域の外（例 325）にして spin_shell を回すと反応するのが正しい

// ============================================================
// 9. 数字（echo）
// ============================================================
echo(str("① 帯: ReSpeaker ", RS_TOP, " 〜 内壁 ", WALL_IN, " = ", BAND,
         " ／ 殻とスタックの相対ずれ（最悪）", TOL_XS,
         " ⇒ 歯幅 1.8 では上下の逃げが ", (BAND - 1.8) / 2, " しか無く、", TOL_XS, " を飲めない。",
         "つまみ・中継 ", GBOT, "〜", GTOP, "（幅 ", GW, "）／ 読み取り ", SGBOT, "〜", SGTOP,
         "（幅 ", SGW, "）"));
echo(str("② 歯先の厚み: 歯末 1.0m なら z28 ", 2 * ((GEAR_M * PI / 2 - G_THIN) / (2 * g_rp(28)) * 180 / PI
         + invd(G_PA) - invd(acos(g_rb(28) / (g_rp(28) + GEAR_M)))) * PI / 180 * (g_rp(28) + GEAR_M),
         "mm（下限 0.30 を割る） ⇒ 歯末 ", G_ADD, "m で z28 ", g_tipth(28), " / z22 ", g_tipth(22),
         " ／ 歯先円 φ", 2 * g_ra(28), " と φ", 2 * g_ra(22)));
echo(str("③ つまみ: 殻の軸穴 φ", KN_BORE, "（🔒 親）⇒ スカート φ", KN_SKIRT,
         "（= 穴 − 回る隙間 ", RUN, "）。皿の抜き φ", KN_ID, " より ", KN_SKIRT - KN_ID,
         " 太いので皿の肉に届く。皿 r", KN_OD / 2, " ↔ 穴 r", KN_BORE / 2,
         " で半径 ", (KN_OD - KN_BORE) / 2, " 隠れる（顔には出ない）。",
         "⚠ 2026-09-13 より前は穴が φ9.0 で、皿と歯車を繋ぐ実体が 0mm3 だった"));
echo(str("③b 回り止め: 柱 φ", KN_PEG, " を二面幅 ", KN_FLAT, " で削り、",
         "皿の穴を φ", KN_PEG + SLIP, " ∩ 幅 ", KN_FLAT + SLIP, " にした。",
         "⚠ 穴が真円だった頃は φ", KN_PEG, " の柱がどの角度でも φ", KN_PEG + SLIP,
         " の真円に収まり、トルクが 1 つも伝わっていなかった。",
         "栓と溶ける柱の天面は 50.51mm2（実測・_v6_knob_hold.scad の a_peg_top）"));
echo(str("③c リード用磁石: 皿の裏に φ", MAG2_D, " × ", MAG2_T, " を埋める。芯 r", MAG2_R,
         "・止めピンの 170 度 反対。ポケットの内縁 r", MAG2_R - MAG2_D / 2,
         " の肉 1.698 ⇒ 天井 ", 1.698 - MAG2_T,
         "（薄壁の下限 ", MINWALL, "）。磁石 ↔ 殻の内面 ", KN_DISHZ - WALL_IN,
         "。⚠ 圧入にはしない（PRINT.md）。A5 の UV レジンと同じ工程で留める"));
echo(str("④ つまみの軸方向の遊び ", KN_DISHZ - GTOP - WALL, " ⇒ 倒れ ",
         atan((KN_DISHZ - GTOP - WALL) / (KN_OD / 2 + g_ra(GEAR_N))), " 度 ／ 可動域 ",
         knob_travel(), " 度（ファームの SPAN 310 度より広い）"));
LM_MESH = 2 * (2 * G_THIN) / g_rp(GEAR_N) * 180 / PI;
LM_IDL  = (RUN / 2 * 2) / (g_rp(GEAR_N) * cos(G_PA)) * 180 / PI;
LM_KN   = (RUN / 2) / (g_rp(GEAR_N) * cos(G_PA)) * 180 / PI;
LM_SN   = (RUN_S / 2) / (g_rp(GEAR_N) * cos(G_PA)) * 180 / PI;
// 🔒 2026-09-13 裁定 #2 で皿の穴に二面幅を入れた分。柱の角（半径 KN_PEG/2）が
//    溝の壁（半幅 (KN_FLAT + SLIP)/2）に当たるまで回れる角度。乾組みで「回ること」を
//    確かめられる代わりに、ここが鎖に 1 つ増える
LM_DISH = acos(KN_FLAT / KN_PEG) - acos((KN_FLAT + SLIP) / KN_PEG);
// 🔒 止めの強さ。v5 のツメ（折れた記録が無い側）との比で読む。
//   ⭐ 比なので**樹脂の強さの仮定が消える**（3 者が別々に出して 1.673 で一致した数）。
//   v5: 腕 STOP_T 1.3 ／ 断面係数 1.507mm³ ／ 半径 12.1（knob_v5.scad）
//   v6: 腕 STP_PIN ／ π・STP_D³/32 ／ 半径 STP_R（どれも親が持つ）
//   🔴 **STP_D と STP_R は対で 1 つの裁定である。**片方だけ動かすと、入れる前より悪くなることがある
//      （2026-09-13: φ2.4・r9.45 で 0.984 → 溝だけ r8.85 へ引くと 1.816 → φ2.6 を入れて 0.827）。
//      ⇒ この行が 1.0 を超えていたら、対の片方が入っていない
V5_ARMZ = 1.3 / 1.507;
V5_R    = 12.1;
STOP_RATIO = ((STP_PIN / (PI * pow(STP_D, 3) / 32)) / V5_ARMZ) * (V5_R / STP_R);
echo(str("⑫ 止めの強さ: ピン φ", STP_D, " @ r", STP_R, " 掛かり ", STP_PIN,
         " ⇒ **v5 のツメ比 ", STOP_RATIO, "**",
         STOP_RATIO > 1.0 ? "  🔴 v5 より厳しい。STP_D と STP_R は対。片方だけ入っていないか見ること"
                          : "  ✅ v5 以下", " ／ 可動域 ", knob_travel(), " 度"));
echo(str("⑤ 遊び（つまみを戻したとき読みが動き出すまで）: 噛み合い 2 か所 ", LM_MESH,
         " 度 ＋ 中継の軸受け ", LM_IDL, " ＋ つまみ ", LM_KN, " ＋ 読み取り ", LM_SN,
         " ＋ 皿とハブの二面幅 ", LM_DISH,
         " = 最悪 ", LM_MESH + LM_IDL + LM_KN + LM_SN + LM_DISH, " 度（RSS ",
         sqrt(LM_MESH * LM_MESH + LM_IDL * LM_IDL + LM_KN * LM_KN + LM_SN * LM_SN
              + LM_DISH * LM_DISH),
         " 度）。AS5600 の 1 刻みは 0.088 度・ファームの 1% は 3.1 度・",
         "ファームのデッドバンド 2% は ", 0.02 * 310, " 度"));
MAG_EXC = RUN_S / 2 + (BRK_BOT - (MAGZ + MAG_T / 2)) * (RUN_S / (BRK_TOP - BRK_BOT));
echo(str("⑥ 磁石: 軸受け ", BRK_BOT, "〜", BRK_TOP, "（", BRK_TOP - BRK_BOT, " 長）・遊び ", RUN_S,
         " ⇒ 傾き ", atan(RUN_S / (BRK_TOP - BRK_BOT)), " 度・磁石の芯の振れ ", MAG_EXC,
         "mm（AS5600 の許容 0.25。ポケットの締め代 0.05 と作図の同芯 0.03 を足して ",
         MAG_EXC + 0.08, "）"));
echo(str("⑦ エアギャップ ", MAG_GAP2, "（チップ天面 ", CHIP_TOP, " ↔ 磁石の下面 ", MAGZ, "）。",
         "板を基準にした鎖の見込み: ブラケット 0.08 ＋ ロータ 0.08 ＋ チップ ", TOL_CHIP,
         " = 最悪 ±", 0.08 + 0.08 + TOL_CHIP, " ⇒ ", MAG_GAP2 - 0.41, "〜", MAG_GAP2 + 0.41,
         "（許容 0.5〜3.0）。前の殻から吊ると ±", TOL_SHELL + TOL_SPLIT + TOL_STACK + 0.16 + TOL_CHIP,
         " ⇒ 下限を割る"));
echo(str("⑧ 中継: 軸 φ", ID_PIN, " 長さ ", WALL_IN - ID_PINZ, " ／ 軸受けの長さ ", ID_TOP - ID_BOT,
         " ／ 帯の余り ", BAND - (ID_TOP - ID_BOT), " ⇒ 鍔 φ", ID_FLG, " で倒れ ",
         atan((BAND - (ID_TOP - ID_BOT)) / ID_FLG), " 度に止まる（軸受けだけなら ",
         atan(RUN / (ID_TOP - ID_BOT)), " 度）"));
// 🔒 2026-09-13 裁定 #1（調停役）。帯の余り 0.45 は**在庫**である。誰かが中継の鍔を厚くする・
//    歯幅を戻す・壁を厚くするときは、ここから引く。そして真っ先に引いていくのが「育ち」で、
//    これは公差ではなく**片側にしか出ない系統誤差**であり、初層の接地面積で決まる
//    （docs/PRINT.md の v4 実測: LCD 比 26〜27% で +0.2・45% で +0.8・50% で +1.2）。
//    調停役の実測: 前の殻だけなら初層 3,142mm2 ＝ 24.4% ⇒ 育ち +0.2。
//    🔴 前の殻と背面の蓋を同じプレートに載せると 57.3% ＝ 育ち +0.8〜1.2 で、中継 1.70 が入らない。
GROWTH = 0.20;     // 前の殻を単独で刷ったときの育ちの見込み（⚠ 実測ではなく v4 の表からの読み）
echo(str("⑧c 中継の抜け止め: 組んだ後、下は ReSpeaker の天面 ", RS_TOP,
         "。鍔の底 ", ID_BOT, " なので落ち代は ", ID_BOT - RS_TOP,
         "。落ち切っても軸（", ID_PINZ, "〜", WALL_IN, "）への掛かりは ",
         (ID_TOP - (ID_BOT - RS_TOP)) - ID_PINZ,
         " 残る ⇒ **組んだ後は落ちない。**⚠ 落ちるのは組む途中だけで、そこは",
         "「前の殻を伏せたまま背面を逆さに被せる」手順で消している"));
echo(str("⑧b 帯の在庫: 帯 ", BAND, " − 中継の高さ ", ID_TOP - ID_BOT, " = ",
         BAND - (ID_TOP - ID_BOT), " ／ 育ちの取り分 ", GROWTH, " を引くと残り ",
         BAND - (ID_TOP - ID_BOT) - GROWTH,
         "。つまみの軸方向の遊び ", KN_DISHZ - GTOP - WALL, " と止めピンの掛かり ",
         FACE_Z - (KN_DISHZ - STP_PIN), " はこの在庫の中から出ている。",
         "🔴 前の殻と背面の蓋を同じプレートに載せると育ちは +0.8〜1.2 になり、中継が入らない"));
echo(str("⑨ 3 連はほぼ一直線: つまみ〜読み取り ", GEAR_D13, " ／ 中心距離の和 ", 2 * GEAR_CC,
         " ⇒ 残りは ", 2 * GEAR_CC - GEAR_D13, "mm しかない。中継の高さ ", GEAR_H,
         "（つまみか読み取りが ", 2 * GEAR_CC - GEAR_D13, " 離れると 3 枚では組めない）"));
echo(str("⑩ ロータのくびれ: ReSpeaker の右の縁 ", RS_EDGE, " ↔ 読み取りの芯 ", SENS[0],
         " = ", SENS[0] - RS_EDGE, " ⇒ Z ", RS_Z, "〜", RS_TOP, " で通せるのは φ",
         2 * (SENS[0] - RS_EDGE) - 0.6, " まで（いま φ", ROT_WST, "）"));
echo(str("⑪ 板へ要る空き: 読み取りの芯まわり φ", BRK_OD + 0.6, " を板の面から ",
         BRK_TOP + 0.8 - PCB_TOP, " ／ ブラケットの座 板 X ",
         BRK_SCR[0] - HB_X - 3.4 - 1.7, "〜", BRK_SCR[0] - HB_X + 3.2, "・Y 0〜",
         BRK_SCR[1] - HB_Y + 3.2, " ／ 現行の立入禁止（6 × 6 角）では足りない"));

// ⑬ つまみの抜け止め（2026-09-13・裁定 #2 の取り消し後）
//    🔴 ここは「強さ」の行ではなく「**どこに置いたか**」の行である。
//       取り消しの理由は強さではなく、接着剤が φ11 の穴から見えていたことだった。
echo(str("⑬ 抜け止めは接着 2 面。A スカートの下端の輪（z ", GTOP,
         "・穴の縁 → φ", BND_UC, "）57.40mm2 は引っ張りで受ける。",
         "B 柱と穴の隙間（片側 ", SLIP / 2, " × 高さ ", BND_STOPZ - GTOP,
         "）26.36mm2 はせん断で受ける。合計 83.76mm2。",
         "⇒ どちらも前の壁（", WALL_IN, " 〜 ", BODY_Z, "）の**内側**にあり、",
         "φ", KN_ID, " の穴から見えるのは皿の円錐と柱の天面だけ（どちらも印刷面）。",
         "逃げは外へ ", PI / 4 * (pow(KN_BORE, 2) - pow(BND_UC, 2)) * BND_UCZ,
         "mm3（軸受け側へ上がらせない）・上へ ",
         PI / 4 * (pow(BND_STOPD, 2) - pow(KN_PEG, 2)) * BND_STOPT,
         "mm3（円錐へ届かせない。溝の上に乾いた穴 ", BND_DRY, " が残る）。",
         "接着剤は 2 液エポキシ（A も B も閉じた隙間で UV が入らない。",
         "瞬間接着剤は『回るか確かめる前に固まる』で落ちたが、エポキシは可使時間がある）"));

// ---- gface: 顔の側から φ11 の穴を覗いた図（2026-09-13）----
//   🔴 これは「接着剤が見えるか」だけを見るための図である。組んだ物を真上から見ている。
//      見えるべき物: 皿（濃い灰）・呼び込みの円錐（皿と同じ色）・柱の天面（ハブの灰）。
//      ⚠ 柱のまわりには嵌め合いの隙間 0.05 の線が 1 本残る（これは穴である。接着剤ではない）。
//        接着剤（橙）はその線の 0.80 下（毛管止めの溝 21.80）で止まっている。
//        ⇒ 合否は「橙が面として見えるか」。線の奥に橙が覗くかどうかまでは問わない
if (part == "gface") {
    knob_dish();
    knob_hub();
    knob_bond();
    color("#c9c2a8", 0.55) difference() {                 // 前の壁（つまみのまわりだけ）
        translate([KN_C[0], KN_C[1], WALL_IN]) cylinder(r = 16.0, h = WALL);
        translate([KN_C[0], KN_C[1], WALL_IN - 1]) cylinder(d = KN_BORE, h = WALL + 2);
    }
}
