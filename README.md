# katanori-sim

カタノリロボ シミュレーター (Vite + React)

## 概要
`simulator.html` の全機能・コンポーネント・CSSスタイルを維持したまま、編集およびデプロイ可能な Vite + React プロジェクト構造に移植したリポジトリです。

## ローカル開発手順

```bash
# 依存パッケージのインストール
npm install

# 開発サーバー起動
npm run dev
```

## ビルド手順

```bash
# 本番用ビルドの生成 (dist/ ディレクトリへ出力)
npm run build
```

## Cloudflare Workers / Assets へのデプロイ手順

```bash
# Cloudflare アカウントへのログイン
npx wrangler login

# デプロイの実行
npm run deploy
```