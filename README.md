---

# slagit-bug-reporter

## SlackからGitHub Issueへバグ報告を自動化

`slagit-bug-reporter` は、Slackに投稿されたバグ報告メッセージを自動的に検知し、GitHubリポジトリに新しいIssueとして登録するシステムです。開発チームがバグ報告を効率的に管理し、迅速な対応を可能にすることを目指します。

## 🚀 導入のメリット

* **報告フローの簡素化**: 開発者やQAチームが普段利用しているSlackから直接バグ報告ができるため、報告の手間が削減されます。
* **情報の一元管理**: Slack上の散逸しがちなバグ情報をGitHub Issueとして集約し、管理しやすくします。
* **対応漏れの防止**: 報告されたバグが自動的にIssue化されるため、対応漏れのリスクを低減します。
* **トレーサビリティの向上**: Slackでの議論とGitHub Issueが連携され、バグ発生から解決までの経緯を追跡しやすくなります。

## 🛠️ システムアーキテクチャ

本システムは、低コストで運用できるよう**サーバーレスアーキテクチャ**を採用しています。

```mermaid
graph TD
    A[開発者/QA] -- Slackにバグ報告 --> B(Slack)
    B -- イベント (メッセージ投稿) --> C{Slack App / Event Subscription}
    C -- HTTP POST --> D[API Gateway / Cloud Functions HTTPトリガー]
    D -- リクエスト転送 --> E[Serverless Function]
    E -- GitHub API呼び出し (Issue作成) --> F(GitHub Repository)
    F -- Issue作成完了 (任意) --> G[Serverless Function]
    G -- Slackに通知 (任意) --> B
```

1.  **Slack**: バグ報告が行われる場所です。特定のチャンネルやスラッシュコマンドを通じてメッセージが投稿されます。
2.  **Slack App / Event Subscription**: Slackからのメッセージ投稿イベントを検知し、設定されたエンドポイント（Serverless Function）へHTTP POSTを送信します。
3.  **API Gateway / Cloud Functions HTTPトリガー**: SlackからのHTTP POSTリクエストを受け付ける公開エンドポイントとして機能します。
4.  **Serverless Function**: バグ報告のコアロジックを担う部分です。
    * SlackからのJSONデータを解析し、GitHub Issueのタイトルと本文を抽出・整形します。
    * GitHub APIを呼び出し、新しいIssueを作成します。
    * 必要に応じて、Issue作成完了をSlackに通知します。
5.  **GitHub Repository**: 作成されたIssueが登録されるGitHubのリポジトリです。

## ⚙️ セットアップ手順

詳細なセットアップ手順は、各クラウドプロバイダー（AWS, GCP, Azure）ごとのドキュメントまたは以下のセクションを参照してください。

### 1. GitHub パーソナルアクセストークン (PAT) の取得

GitHub Issueを作成するために、`repo` スコープを持つ**パーソナルアクセストークン**を生成してください。

### 2. Slack App の作成と設定

1.  [Slack API](https://api.slack.com/apps) で新しいSlack Appを作成します。
2.  **Features > Event Subscriptions** を有効にし、以下を設定します。
    * Request URL: 後述のServerless FunctionのエンドポイントURLを設定します。
    * Subscribe to bot events: `message.channels` や `app_mention` など、バグ報告を検知したいイベントを追加します。
3.  **Features > OAuth & Permissions** にて、`channels:read`, `chat:write` などの適切なスコープを付与します。
4.  Appをワークスペースにインストールし、必要なチャンネルに追加します。

### 3. Serverless Function のデプロイ

選択したクラウドプロバイダー（AWS Lambda）に、本リポジトリのコードをデプロイします。

* **環境変数**: 取得したGitHub PATをセキュアな方法（例: AWS Secrets Manager）で設定し、Function内で利用できるようにします。
* **コードのデプロイ**: 本リポジトリのFunctionコードをデプロイします。コードはSlackからのWebhookペイロードを解析し、GitHub APIを呼び出すロジックを含みます。

### 4. テスト

設定完了後、Slackの対象チャンネルでバグ報告メッセージを投稿し、GitHubにIssueが自動作成されることを確認してください。

## 📝 GitHub Issueのフォーマット

`slagit-bug-reporter` は、Slackメッセージの内容から以下のフォーマットでGitHub Issueを生成することを想定しています。

### タイトル

`[Bug] [影響範囲] 問題の要約`

**例**: `[Bug] [UI/ログイン画面] パスワード再設定時にエラーが発生する`

### 本文

```markdown
## 問題の要約

(タイトルの詳細な説明)

## 再現手順

1. (ステップ1)
2. (ステップ2)
3. ...

### 環境
- OS:
- ブラウザ:
- バージョン:

## 期待される動作

(こうあるべきという動作)

## 実際の動作

(実際に起こる現象。エラーメッセージ、スクリーンショットなど)

## 技術情報/追加情報

(エラーログ、関連する試み、その他参考情報)
```

**ヒント**: Slackでのバグ報告時に、上記のような構成で情報を記述するようチーム内でガイドラインを設けると、より質の高いIssueが生成されます。


## ディレクトリ構成
```
.
├── .github/
│   └── pull_request_template.md  # GitHubのPRテンプレート
├── docs/
│   ├── arch/                   # システムアーキテクチャ図などの資料
│   │   └── system_architecture.mermaid
│   └── wiki/                   # Wikiコンテンツ
│       └── home.md
├── src/                        # コード本体
│   ├── lambda_function/        # Lambda関数（主要なプロセス）
│   │   ├── __init__.py
│   │   ├── handler.py          # Lambdaのメインハンドラー
│   │   └── utils/              # 共通ユーティリティ（例: github_api.py, slack_parser.py）
│   │       ├── __init__.py
│   │       ├── github_api.py
│   │       └── slack_parser.py
│   └── common/                 # 複数のプロセスで共有されるコードなど（もしあれば）
│       └── ...
├── prompts/                    # AIプロンプト（仕様書）
│   └── cursor_spec_prompt.md   # Cursor向け仕様書プロンプト
├── scripts/                    # デプロイやビルドなどのスクリプト
│   ├── deploy.sh               # デプロイスクリプト (例: SAM/Serverless Framework コマンド)
│   └── build.sh                # ビルドスクリプト (もし必要なら)
├── .gitignore
├── README.md                   # リポジトリの概要と使い方
├── pyproject.toml              # Python依存関係管理 (Poetry/PDM/Pipenvなど)
├── requirements.txt            # Python依存関係 (pip用)
└── serverless.yml              # Serverless Framework設定ファイル (もし利用するなら)
```

### 各ディレクトリの説明
* .github/:
    * pull_request_template.md: GitHubのプルリクエストテンプレートを格納します。レビュアーがPRの内容を効率的に把握できるようになります。
* docs/:
    * システムに関するドキュメント全般を格納します。
    * arch/: システムアーキテクチャ図など、設計に関する図や詳細な技術ドキュメントを置きます。
    * wiki/: GitHub Wikiに載せるような、より広範な情報（利用ガイド、FAQ、ユースケースなど）をMarkdownファイルで格納します。GitHubのWiki機能と連携させやすいです。
* src/:
    * コード本体を格納するルートディレクトリです。
    * lambda_function/: 今回のシステムの主要なLambda関数（または他のサーバーレスプロセス）のコードを格納します。プロセス単位でディレクトリを分けることで、将来的に機能が拡張され、別のLambda関数が必要になった場合でも整理しやすくなります。
        * handler.py: Lambdaのイベントを受け取り、主要な処理を呼び出すエントリーポイントです。
        * utils/: github_api.py (GitHub API操作用) や slack_parser.py (Slackメッセージ解析用) のように、特定の機能に特化したユーティリティモジュールを格納します。
    * common/: 複数のLambda関数やスクリプト間で共通して利用されるコード（例: 共通の例外クラス、認証ヘルパーなど）があればここに置きます。
* prompts/:
    * AI（Cursorなど）にコード生成を依頼する際に使用した**プロンプト（仕様書）**を格納します。これにより、どのような指示でコードが生成されたかを追跡できます。
    * cursor_spec_prompt.md: 今回作成したCursor向けのプロンプトをMarkdown形式で保存します。
* scripts/:
    * デプロイ、ビルド、テスト実行など、開発・運用に必要なスクリプトを格納します。
    * deploy.sh: AWS Lambdaへのデプロイコマンドなどを記述します。Serverless FrameworkやAWS SAM CLIを使用する場合のコマンドなどが考えられます。
* README.md:
    * リポジトリの顔となるファイルです。システムの概要、セットアップ方法、使い方などを記述します。
* pyproject.toml / requirements.txt:
    * Pythonプロジェクトの依存関係を管理するファイルです。どちらか、または両方をプロジェクトの管理方法に応じて使用します。
* serverless.yml:
    * もしServerless Frameworkを使用してデプロイを行う場合、その設定ファイルをここに置きます。AWS SAMやTerraformなどを使用する場合は、それに準じた設定ファイルを置きます。
