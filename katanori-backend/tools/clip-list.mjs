/*
 * 機体に焼き込む声の一覧（gen-voice-clips.mjs と live-takes.mjs が使う）。
 *
 * name は C の識別子になるので英大文字。増やすぶんだけフラッシュを食う
 * （16kHz 16bit モノラルで 1秒 = 32KB）。
 */
export const CLIPS = [
  {
    name: "BOOT_READY",
    text: "カタノリ、起動しました",
    comment: "Wi-Fiに繋がって会話できる状態になったとき",
  },
  {
    name: "PROV_NEEDED",
    text: "ワイファイの設定をしてください",
    comment: "Wi-Fi設定モードに入ったとき（未設定・繋がらない・手動で入った）",
  },
  {
    name: "WIFI_OK",
    text: "ワイファイにつながりました",
    comment: "設定モードで保存したWi-Fiへの初回接続に成功したとき（パスワードが合っていた合図）",
  },
  {
    name: "WAKE_FROM_SLEEP",
    text: "ちょっと待ってね、いま起きたところ",
    comment: "眠っている間に呼ばれたとき（Wi-Fi を止めているので、つながるまで待たせる）",
  },
  {
    name: "WAKE_WIFI_UP",
    text: "ワイファイがつながったよ、あと少し",
    comment: "眠りから呼ばれて、Wi-Fi がつながったとき（次はサーバーへの接続）",
  },
  {
    name: "WAKE_READY",
    text: "おまたせ！",
    comment: "眠りから呼ばれて、Gemini の準備ができたとき",
  },
];
