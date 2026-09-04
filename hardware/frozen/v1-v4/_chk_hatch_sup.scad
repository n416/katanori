include <case_v4.scad>
// 支え（柱・球・枝・円錐・ラフト）と、素の部品の重なり
intersection() { union() { props_hatch(); raft_hatch(); } hatch_print(); }
