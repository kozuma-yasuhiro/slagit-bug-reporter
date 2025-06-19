import json
import os
import re
import requests
import boto3
from typing import Tuple

GITHUB_API_URL = "https://api.github.com"

def get_secret(secret_name: str) -> str:
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    return response['SecretString']

def parse_slack_message(slack_event_text: str) -> Tuple[str, str]:
    """
    Slackメッセージからタイトルと本文を抽出・整形する。
    - [Bug]やBug:などのキーワードをタイトルに利用。
    - セクションキーワードを抽出し、GitHub Issue本文テンプレートに整形。
    """
    # タイトル抽出
    title_match = re.search(r"\[Bug\][^\n]*|Bug:[^\n]*", slack_event_text)
    if title_match:
        title = title_match.group().replace("[Bug]", "").replace("Bug:", "").strip()
    else:
        title = slack_event_text.split('\n')[0].strip()

    # セクション抽出
    def extract_section(keyword):
        pattern = rf"{keyword}[:：]?(.+?)(?=\n\S|$)"
        match = re.search(pattern, slack_event_text, re.DOTALL)
        return match.group(1).strip() if match else ""

    summary = extract_section("問題の要約") or title
    steps = extract_section("再現手順")
    expected = extract_section("期待される動作")
    actual = extract_section("実際の動作")
    env = extract_section("環境")
    error_log = extract_section("エラーログ")
    extra = extract_section("技術情報|追加情報")

    body = f"""## 問題の要約\n{summary}\n\n## 再現手順\n{steps}\n\n### 環境\n{env}\n\n## 期待される動作\n{expected}\n\n## 実際の動作\n{actual}\n\n## 技術情報/追加情報\n{error_log}\n{extra}"""
    return title, body

def create_github_issue(title: str, body: str, github_pat: str, owner: str, repo: str) -> dict:
    headers = {
        "Authorization": f"token {github_pat}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "title": title,
        "body": body,
        "labels": ["Bug"]
    }
    response = requests.post(f"{GITHUB_API_URL}/repos/{owner}/{repo}/issues", headers=headers, data=json.dumps(data))
    response.raise_for_status()
    return response.json()

def send_slack_notification(webhook_url: str, message_text: str):
    payload = {"text": message_text}
    requests.post(webhook_url, json=payload)

def lambda_handler(event, context):
    # Slack Challenge/Response認証
    if "challenge" in event:
        return {
            "statusCode": 200,
            "body": event["challenge"],
            "headers": {"Content-Type": "text/plain"}
        }

    if "event" not in event:
        print("Invalid Slack event payload:", json.dumps(event))
        return {"statusCode": 400, "body": "Invalid event payload"}

    slack_event = event["event"]
    if slack_event.get("type") == "message" and not slack_event.get("subtype"):
        message_text = slack_event.get("text")
        channel_id = slack_event.get("channel")
        if not message_text:
            return {"statusCode": 200, "body": "No message text found"}
        if "[Bug]" not in message_text and "Bug:" not in message_text:
            return {"statusCode": 200, "body": "Not a bug report message"}
        try:
            github_repo_owner = os.environ.get("GITHUB_REPO_OWNER")
            github_repo_name = os.environ.get("GITHUB_REPO_NAME")
            slack_webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
            github_pat_secret_name = os.environ.get("GITHUB_PAT_SECRET_NAME", "github_pat_secret")
            if not all([github_repo_owner, github_repo_name, slack_webhook_url]):
                raise ValueError("Missing required environment variables for GitHub or Slack.")
            github_pat = get_secret(github_pat_secret_name)
            if not github_pat:
                raise ValueError("Failed to retrieve GitHub PAT from Secrets Manager.")
            title, body = parse_slack_message(message_text)
            issue_info = create_github_issue(title, body, github_pat, github_repo_owner, github_repo_name)
            issue_url = issue_info.get("html_url")
            notification_message = f"GitHub Issueが作成されました: <{issue_url}|{title}>"
            send_slack_notification(slack_webhook_url, notification_message)
            return {"statusCode": 200, "body": "Issue created successfully"}
        except Exception as e:
            print(f"Error processing Slack event: {e}")
            error_message = f"GitHub Issueの作成中にエラーが発生しました: {e}"
            # send_slack_notification(slack_webhook_url, error_message) # 必要に応じて有効化
            return {"statusCode": 500, "body": f"Error: {str(e)}"}
    return {"statusCode": 200, "body": "Event type not handled"} 