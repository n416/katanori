# 機体の音を PC で確かめる

`mww_live` を書き込んだ機体から、聞き分けに渡している音を取り出して PC の推論にかける。
シリアルは COM5（`session.py` に書いてある）。DTR/RTS は触らない。

| ファイル | 役目 |
|---|---|
| `session.py <接頭辞>` | 機体の判定の行を `<接頭辞>.log` に残し続け、`<接頭辞>.flag` を作ると直近の音を受け取って WAV にする。欠けた行は取り直す |
| `pcinfer.py <model.tflite> <wav>... [--timeline]` | microWakeWord の `predict_clip` と同じ計算で推論する（16kHz の WAV） |
| `compare48.py <48kHz の wav> <model>...` | 48kHz の取り出しから「3 つの平均」と正しい落とし方の 2 通りを作って並べる |

環境: `tensorflow-cpu`・`pymicro-features`・`soundfile`・`numpy`・`scipy`（推論側）、`pyserial`（受け取り側）。

手順:
1. `python session.py cap` を裏で動かす（機体は常に直近をためている）
2. 呼ぶ
3. `cap.flag` を作る → `cap_nabu_ch0x4.wav` と `cap_nabu_ch1x4.wav` が出来る
4. `python compare48.py cap_nabu_ch0x4.wav <model>`（48kHz でためている今の版）
