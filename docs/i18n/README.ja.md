[English](../../README.md) / [简体中文](README.zh-CN.md) / [日本語](README.ja.md) / [한국어](README.ko.md)

# PitchMind — Football AI Analysis Engine

![PitchMind ヒーローカバー](../assets/pitchmind-hero.svg)

**PitchMind** は、サッカーの試合リサーチ、AI 支援の分析、構造化レポート生成のための local-first（ローカル優先）デスクトップ Beta です。一般ユーザーが集中して使える研究ワークスペースを目指しており、プライベートな token やローカルの run データをホスト型サービスへ送信する前提ではありません。

> コンプライアンス上の境界：PitchMind は研究とエンターテインメント用途のツールです。賭けの助言、金融上の助言、試合結果の保証ではありません。

## デスクトップ Beta をダウンロード

**最新 Beta:** [`desktop-beta-4`](https://github.com/0801ljw/football-ai-analysis-engine/releases/tag/desktop-beta-4)

| プラットフォーム | 状態 | アセット |
| --- | --- | --- |
| Windows x64 | 利用可能 | `PitchMind-Setup-x64.exe` |
| macOS Apple Silicon | 利用可能 | `PitchMind-macOS-AppleSilicon.dmg` |
| macOS Intel | まだ利用できません | このリリースには Intel DMG はありません |

この Beta は未署名です。インストール時に OS のセキュリティ警告が表示される場合があります。上記の公式 GitHub Release からのみダウンロードし、ミラーや再アップロードされたファイルはインストールしないでください。

## できること

| 領域 | PitchMind が支援する内容 |
| --- | --- |
| 試合リサーチ | サッカーの試合番号、データソースの状態、分析 run を 1 つのローカルワークスペースで整理できます。 |
| AI 支援レポート | データ品質メモとコンプライアンス注意を含む、構造化されたサッカー分析レポートを生成できます。 |
| Run 履歴 | 過去の run、ステータス、エクスポート済み artifact、利用可能な prediction JSON を確認できます。 |
| ローカル優先ワークフロー | 設定、token、生成された run ファイルを自分のマシン上に保持できます。 |
| 安全上の境界 | 未署名 Beta の注意を明示し、出力は研究とエンターテインメント用途に限られることを知らせます。 |

## 3 ステップで始める

1. [`desktop-beta-4` リリースページ](https://github.com/0801ljw/football-ai-analysis-engine/releases/tag/desktop-beta-4)を開き、自分のプラットフォーム向けインストーラーをダウンロードします。
2. PitchMind をインストールして起動します。未署名 Beta のため、ファイルが公式リリースページから取得したものだと確認できる場合のみ OS の警告を許可してください。
3. ローカル run を作成し、データ品質メモを確認します。研究結果を共有する必要があれば、利用可能な artifact をエクスポートします。

## プライバシーと local-first の使い方

- PitchMind は自分のコンピューター上でローカルに動作することを意図しています。
- サポートを求める際も、API token、アカウント token、`.env` ファイル、ローカルデータベース、run artifact を送らないでください。
- ブラウザーまたはデスクトップの token 入力は、あなたのローカルワークフローのためのものです。token は秘密情報として扱ってください。
- この README は、リモートテレメトリー、クラウド同期、自動更新の存在を主張しません。

## 未署名 Beta の安全上の注意

現在のデスクトップ Beta はコード署名されておらず、自動更新も主張していません。Windows または macOS が未署名のプレビューソフトウェアに対してセキュリティ警告を表示するのは想定内です。不安がある場合は、署名済みリリースをお待ちください。

## フィードバックと Issue

バグ、インストール上の問題、使い勝手に関するフィードバックは [GitHub Issues](https://github.com/0801ljw/football-ai-analysis-engine/issues) に投稿してください。OS、ダウンロードしたアセット名、発生した内容を含めてください。token やローカルの個人データは含めないでください。

## 技術スタック

| レイヤー | スタック |
| --- | --- |
| デスクトップシェル | Tauri |
| ローカル Web アプリ | FastAPI, Jinja2 |
| フロントエンド資産 | HTML, CSS, JavaScript |
| ランタイムとツール | Python, SQLite, PyInstaller sidecar, リリース用パッケージングスクリプト |
| リリース先 | GitHub Releases、手動の未署名 Beta 配布 |

## 開発者向け入口

このランディングページは一般ユーザー向けです。以前の開発者向け README は書き換えずに保存されています。

- [開発者ドキュメント](../DEVELOPMENT.md)
- [デスクトップ Beta インストールノート](../../desktop/INSTALL_BETA.md)
- [リリースチェックリスト](../../RELEASE_CHECKLIST.md)
- [デスクトップソース README](../../desktop/README.md)

## 法務・コンプライアンス上の注意

PitchMind は、サッカーデータの研究、確率的な探索、コンテンツ制作支援を、エンターテインメントと学習のために提供します。賭けの助言、予測の保証、賭けを行うための指示は提供しません。常に居住地域の法律と利用するプラットフォームのルールに従ってください。
