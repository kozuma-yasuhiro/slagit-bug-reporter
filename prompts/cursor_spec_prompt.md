---

承知いたしました！AWS Secrets Manager を利用する方式を、先ほどのCursor向けプロンプトに反映させます。特に、シークレットの取得方法、IAMロールの権限、および関連する環境変数の指示を更新しました。

---

## Cursor向けプロンプト：Slackバグ報告 → GitHub Issue 自動作成システム (`slagit-bug-reporter`) - Secrets Manager対応版

---

### プロジェクト概要と目的

以下の要件に基づき、Slackに投稿されたバグ報告メッセージを自動的にGitHub Issueとして作成するサーバーレスシステムを構築してください。

**目的**: 開発チームがバグ報告を効率的に管理し、迅速な対応を可能にすること。手動でのIssue作成の手間を排除し、情報の一元化とトレーサビリティを向上させます。

### システムアーキテクチャ

システムは以下の**サーバーレスアーキテクチャ**を想定しています。

1.  **Slack App / Event Subscription**: Slackからのメッセージ投稿イベントを検知し、指定のエンドポイントへHTTP POSTを送信します。
2.  **API Gateway / Cloud Functions HTTPトリガー**: SlackからのHTTP POSTリクエストを受け付ける公開エンドポイントです。
3.  **Serverless Function (AWS Lambda)**: コアロジックを実装します。
4.  **AWS Secrets Manager**: GitHub Personal Access Token (PAT) などの秘匿情報を安全に保存・取得します。
5.  **GitHub Repository**: 作成されたIssueが登録されるリポジトリです。
6.  **GitHub API**: Issue作成に使用します。

### 技術スタック

* **プログラミング言語**: Python 3.9+ (Pythonを優先)
* **クラウドプロバイダー**: **AWS Lambda** を使用した実装を前提とします。
    * API Gateway
    * Lambda Function
    * **AWS Secrets Manager** (GitHub PATの安全な管理のため)
    * AWS IAM (Lambda実行ロールの権限設定)
* **依存ライブラリ**: `requests` (HTTPリクエストのため), `boto3` (AWSサービスとの連携のため)

### 主要機能要件

1.  **Slackメッセージ受信**:
    * API Gateway (Lambdaトリガー) は、SlackからのHTTP POSTリクエストを受け取ります。
    * SlackからのWebhookペイロード（`event.type` が `message` かつ `subtype` がない通常のメッセージ）を解析します。
    * `event.text` (メッセージ本文) を抽出します。
    * **重要**: SlackのChallenge/Response認証フローに対応してください。
2.  **GitHub Issue情報抽出・整形**:
    * 受信したSlackメッセージ本文 (`event.text`) から、GitHub Issueの**タイトル**と**本文**を抽出・整形するロジックを実装します。
    * **タイトル抽出**:
        * メッセージが特定のキーワード (例: `[Bug]`, `Bug:`) を含み、かつその後にタイトルらしきテキストが続く場合、それをIssueタイトルとします。
        * 例: `"[Bug] ログイン後にセッションが切れる"` -> `タイトル: "ログイン後にセッションが切れる"`
        * または、メッセージの最初の行をタイトルとして利用することも検討します。
    * **本文抽出**:
        * Slackメッセージの残りの部分をIssue本文とします。
        * GitHubのMarkdown形式に変換できると望ましいです。
        * **特定のセクションの抽出**: メッセージ内に「再現手順:」「期待される動作:」「実際の動作:」「環境:」「エラーログ:」などのキーワードが含まれる場合、それらをGitHub Issue本文の対応するセクションに整形して組み込んでください。
            ```
            # GitHub Issue 本文の想定フォーマット
            ## 問題の要約
            (Slackメッセージから抽出)

            ## 再現手順
            (Slackメッセージから抽出)

            ## 期待される動作
            (Slackメッセージから抽出)

            ## 実際の動作
            (Slackメッセージから抽出)

            ### 環境
            (Slackメッセージから抽出)

            ### エラーログ
            ```
            (Slackメッセージから抽出されたコードブロックなど)
            ```
3.  **GitHub Issue作成**:
    * GitHub API (REST API: `POST /repos/{owner}/{repo}/issues`) を使用して、Issueを作成します。
    * **認証**: GitHub Personal Access Token (PAT) を使用します。このPATは**AWS Secrets Manager**から安全に取得・利用するようにしてください。
    * **ターゲットリポジトリ**: Issueを作成するGitHubリポジトリのオーナーとリポジトリ名は、環境変数で設定できるようにしてください (例: `GITHUB_REPO_OWNER`, `GITHUB_REPO_NAME`)。
    * **ラベルの自動付与**: `Bug` ラベルを自動的に付与してください。
4.  **Slackへの結果通知（任意）**:
    * Issueの作成が成功した場合、元のSlackチャンネル（または設定されたチャンネル）に、作成されたGitHub IssueのURLを通知します。
    * Slack Incoming Webhook URLも環境変数で設定できるようにしてください (例: `SLACK_WEBHOOK_URL`)。

### エラーハンドリング

* **Slack Challenge/Responseの失敗**: 正しく応答できない場合。
* **Slack Webhookペイロードの解析失敗**: 不正な形式のデータが送られてきた場合。
* **GitHub API呼び出しの失敗**: ネットワークエラー、認証エラー、レートリミット超過など。適切なエラーメッセージをログに出力してください。
* **Secrets Managerからのシークレット取得失敗**: シークレットが見つからない、権限がない、復号できないなどのエラー。
* **環境変数の不足**: 必須の環境変数が設定されていない場合。
* エラー発生時は、可能であればSlackにエラー通知を送信し、問題の特定に役立つ情報をログに出力してください。

### セキュリティ

* GitHub PATはハードコードせず、必ずAWS Secrets Managerから**安全に取得**するようにしてください。
* LambdaのIAMロールには、Secrets Managerからシークレット (`secretsmanager:GetSecretValue` アクション) を取得するための**最小限の権限**のみを付与してください。対象リソースは**特定のシークレットのARN**に限定してください。

### コード構造の指示

* Lambda Functionのハンドラ関数は、`lambda_handler(event, context)` の形式でお願いします。
* GitHub APIとの通信部分は別関数 (`create_github_issue`) として切り出すなど、モジュール性を意識してください。
* **Secrets Managerからのシークレット取得ロジック**は、`get_secret` のような独立したヘルパー関数として実装してください。
* テストしやすいように、ビジネスロジックと外部サービス（Slack, GitHub, Secrets Manager）との連携部分は分離してください。

### 環境変数 (Lambda Function)

以下の環境変数をLambdaに設定できるようにしてください。

* `GITHUB_PAT_SECRET_NAME`: AWS Secrets Managerに保存されているGitHub PATのシークレット名（例: `slagit-bug-reporter/github_pat`）
* `GITHUB_REPO_OWNER`: GitHubリポジトリのオーナー名
* `GITHUB_REPO_NAME`: GitHubリポジトリ名
* `SLACK_WEBHOOK_URL`: Slackへの通知に使用するIncoming WebhookのURL (任意、設定しない場合は通知しない)
* `AWS_REGION`: Lambdaが動作するAWSリージョン (boto3でSecrets Managerクライアントを初期化する際に使用)

### 例（Pythonの想定）

```python
# lambda_function.py (または src/lambda_function/handler.py)

import json
import os
import requests
import boto3
from botocore.exceptions import ClientError

# 環境変数から設定値を取得
GITHUB_API_URL = "[https://api.github.com](https://api.github.com)"
GITHUB_PAT_SECRET_NAME = os.environ.get("GITHUB_PAT_SECRET_NAME")
GITHUB_REPO_OWNER = os.environ.get("GITHUB_REPO_OWNER")
GITHUB_REPO_NAME = os.environ.get("GITHUB_REPO_NAME")
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL") # 任意
AWS_REGION = os.environ.get('AWS_REGION') # Lambdaの実行環境から自動で取得される

def get_secret(secret_name):
    """
    AWS Secrets Managerから指定されたシークレットの値を安全に取得します。
    シークレットはJSON形式で保存されていることを想定し、辞書として返します。
    """
    client = boto3.client('secretsmanager', region_name=AWS_REGION)
    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    except ClientError as e:
        # エラーハンドリング (ResourceNotFoundExceptionなど)
        print(f"Error retrieving secret '{secret_name}': {e}")
        raise # 例外を再スロー
    else:
        if 'SecretString' in get_secret_value_response:
            secret = get_secret_value_response['SecretString']
            return json.loads(secret) # JSON形式を想定
        else:
            # バイナリデータの場合 (今回のユースケースでは想定外)
            print(f"Secret '{secret_name}' is in binary format, not SecretString.")
            return None

def parse_slack_message(slack_event_text):
    """
    SlackメッセージからGitHub Issueのタイトルと本文を抽出・整形します。
    """
    # ここにSlackメッセージのパースロジックを実装
    # 例: "[Bug] タイトル\n再現手順:\n..." のようなフォーマットを解析
    lines = slack_event_text.splitlines()
    title_line = lines[0] if lines else "No Title Provided"
    
    # タイトルから "[Bug]" などのプレフィックスを取り除く
    if title_line.startswith("[Bug]") or title_line.startswith("Bug:"):
        title = title_line.split("]", 1)[1].strip() if "]" in title_line else title_line.split(":", 1)[1].strip()
    else:
        title = title_line.strip()

    # 残りの行を本文として結合し、Markdown形式に整形
    body_content = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""

    # より詳細なパース（「再現手順:」などでセクションを区切るなど）は、この関数内で実装
    # 例: body_contentを正規表現などで解析し、GitHub Issue本文のテンプレートに当てはめる
    formatted_body = f"## 問題の要約\n\n{title_line}\n\n"
    if "再現手順:" in body_content:
        # 簡易的な例。実際はより複雑なパースが必要
        formatted_body += f"## 再現手順\n\n{body_content.split('再現手順:', 1)[1].split('期待される動作:', 1)[0].strip()}\n\n"
        # 他のセクションも同様に追加
    else:
        formatted_body += f"{body_content}\n" # デフォルト

    return title, formatted_body

def create_github_issue(title, body, github_pat, owner, repo):
    """
    GitHub APIを呼び出してIssueを作成します。
    """
    headers = {
        "Authorization": f"token {github_pat}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28" # APIバージョンを指定
    }
    data = {
        "title": title,
        "body": body,
        "labels": ["Bug"] # 固定ラベル
    }
    
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/issues"
    response = requests.post(url, headers=headers, data=json.dumps(data))
    response.raise_for_status() # HTTPエラーが発生した場合に例外をスロー
    return response.json() # 作成されたIssueの情報を返す

def send_slack_notification(webhook_url, message_text):
    """
    Slack Incoming Webhookを使用して通知を送信します。
    """
    if not webhook_url:
        print("Slack Webhook URL is not configured. Skipping notification.")
        return

    payload = {"text": message_text}
    try:
        response = requests.post(webhook_url, json=payload, timeout=5)
        response.raise_for_status()
        print("Slack notification sent successfully.")
    except requests.exceptions.RequestException as e:
        print(f"Failed to send Slack notification: {e}")

def lambda_handler(event, context):
    """
    AWS Lambdaのメインハンドラー関数。
    """
    # Slack Challenge/Response認証のハンドリング
    if "challenge" in event:
        print("Handling Slack URL verification challenge.")
        return {
            "statusCode": 200,
            "body": event["challenge"],
            "headers": {"Content-Type": "text/plain"}
        }

    # Slackイベントの処理
    if "event" not in event:
        print("Invalid Slack event payload (missing 'event' key):", json.dumps(event))
        return {"statusCode": 400, "body": "Invalid event payload"}

    slack_event = event["event"]
    # ボットメッセージやスレッド返信を除外するフィルター (必要に応じて調整)
    if slack_event.get("type") != "message" or slack_event.get("subtype") in ["bot_message", "message_changed", "message_deleted"]:
        print(f"Skipping unhandled Slack event type or subtype: {slack_event.get('type')}, {slack_event.get('subtype')}")
        return {"statusCode": 200, "body": "Event type not handled or skipped"}

    message_text = slack_event.get("text")
    channel_id = slack_event.get("channel") # 通知元チャンネル取得用 (必要に応じて使用)

    if not message_text:
        print("Received Slack event with no message text.")
        return {"statusCode": 200, "body": "No message text found"}

    # メッセージに特定のキーワード（例: "[Bug]"）が含まれる場合のみ処理
    # これにより、すべてのメッセージを処理するのを避ける
    if "[Bug]" not in message_text:
        print(f"Message does not contain bug report keyword: {message_text[:50]}...")
        return {"statusCode": 200, "body": "Not a bug report message"}

    try:
        # 必須環境変数の確認
        if not all([GITHUB_PAT_SECRET_NAME, GITHUB_REPO_OWNER, GITHUB_REPO_NAME]):
            raise ValueError("Missing required environment variables for GitHub or Secrets Manager.")

        # Secrets ManagerからGitHub PATを取得
        secret_data = get_secret(GITHUB_PAT_SECRET_NAME)
        github_pat = secret_data.get('github_pat') # シークレットをJSON形式で保存した場合

        if not github_pat:
            raise ValueError(f"GitHub PAT not found in secret '{GITHUB_PAT_SECRET_NAME}'. Ensure it's stored as 'github_pat' key.")

        # SlackメッセージからIssue情報を抽出・整形
        title, body = parse_slack_message(message_text)
        print(f"Parsed Issue Title: {title}")
        print(f"Parsed Issue Body (first 100 chars): {body[:100]}...")

        # GitHub Issueを作成
        issue_info = create_github_issue(title, body, github_pat, GITHUB_REPO_OWNER, GITHUB_REPO_NAME)
        issue_url = issue_info.get("html_url")
        issue_number = issue_info.get("number")
        print(f"Successfully created GitHub Issue: {issue_url}")

        # Slackに通知 (SLACK_WEBHOOK_URLが設定されている場合のみ)
        if SLACK_WEBHOOK_URL:
            notification_message = f"GitHub Issueが作成されました: <{issue_url}|#{issue_number} {title}>"
            send_slack_notification(SLACK_WEBHOOK_URL, notification_message)

        return {"statusCode": 200, "body": "Issue created successfully"}

    except Exception as e:
        print(f"Error processing Slack event: {e}")
        # エラー時にSlackに通知することも検討
        error_message = f"GitHub Issueの作成中にエラーが発生しました: {e}"
        if SLACK_WEBHOOK_URL:
            send_slack_notification(SLACK_WEBHOOK_URL, error_message) # エラー通知を有効にする場合
        return {"statusCode": 500, "body": f"Error: {str(e)}"}

```