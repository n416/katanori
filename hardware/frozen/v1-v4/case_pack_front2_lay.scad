// 箱詰めスタディ ── 寝かせた版
//
// **case_pack_front2.scad の中身をそのまま使い、フラグだけ差し替える。**
// 🔒 コピーしていない。**本体を直せばこちらにも反映される。**
//
//   openscad hardware/case_pack_front2_lay.scad
//
// ⚠ OpenSCAD は「同じスコープの最後の代入が勝つ」ので、
//    include の**後ろ**に書いた値が、include した中の geometry にも効く。
//    （前に書くと include 側の既定値に上書きされる）

include <case_pack_front2.scad>

STAND_ALL  = false;   // ← ハブ基板も電池も PowerBoost も寝かせる
S_CORRIDOR = 0;       // 行S の線は下段へ降りる想定（数字を本体と揃えるため）
