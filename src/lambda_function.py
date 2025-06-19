import json
import os
import re
import requests
import boto3
from botocore.exceptions import ClientError
from typing import Tuple, Optional

# 環境変数
GITHUB_API_URL = "https://api.github.com"
GITHUB_PAT_SECRET_NAME = os.environ.get("GITHUB_PAT_SECRET_NAME")
GITHUB_REPO_OWNER = os.environ.get("GITHUB_REPO_OWNER")
GITHUB_REPO_NAME = os.environ.get("GITHUB_REPO_NAME")
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")
AWS_REGION = os.environ.get("AWS_REGION")


def get_secret(secret_name: str) -> dict:
    """
    AWS Secrets Managerから指定されたシークレット(JSON)を取得。
    """
    client = boto3.client('secretsmanager', region_name=AWS_REGION)
    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    except ClientError as e:
        print(f"Error retrieving secret '{secret_name}': {e}")
        raise
    else:
        if 'SecretString' in get_secret_value_response:
            secret = get_secret_value_response['SecretString']
            try:
                return json.loads(secret)
            except Exception:
                return {"github_pat": secret}  # プレーンテキストの場合
        else:
            print(f"Secret '{secret_name}' is in binary format, not SecretString.")
            return {}

def parse_slack_message(slack_event_text: str) -> Tuple[str, str]:
    """
    SlackメッセージからGitHub Issueのタイトルと本文を抽出・整形。
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
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    data = {
        "title": title,
        "body": body,
        "labels": ["Bug"]
    }
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/issues"
    response = requests.post(url, headers=headers, data=json.dumps(data))
    response.raise_for_status()
    return response.json()

def send_slack_notification(webhook_url: Optional[str], message_text: str):
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
    # Slack Challenge/Response認証
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
    # ボットメッセージやスレッド返信を除外するフィルター
    if slack_event.get("type") != "message" or slack_event.get("subtype") in ["bot_message", "message_changed", "message_deleted"]:
        print(f"Skipping unhandled Slack event type or subtype: {slack_event.get('type')}, {slack_event.get('subtype')}")
        return {"statusCode": 200, "body": "Event type not handled or skipped"}

    message_text = slack_event.get("text")
    channel_id = slack_event.get("channel")

    if not message_text:
        print("Received Slack event with no message text.")
        return {"statusCode": 200, "body": "No message text found"}

    if "[Bug]" not in message_text and "Bug:" not in message_text:
        print(f"Message does not contain bug report keyword: {message_text[:50]}...")
        return {"statusCode": 200, "body": "Not a bug report message"}

    try:
        if not all([GITHUB_PAT_SECRET_NAME, GITHUB_REPO_OWNER, GITHUB_REPO_NAME, AWS_REGION]):
            raise ValueError("Missing required environment variables for GitHub, Secrets Manager, or AWS region.")
        secret_data = get_secret(GITHUB_PAT_SECRET_NAME)
        github_pat = secret_data.get('github_pat') or next(iter(secret_data.values()), None)
        if not github_pat:
            raise ValueError(f"GitHub PAT not found in secret '{GITHUB_PAT_SECRET_NAME}'. Ensure it's stored as 'github_pat' key or as plain string.")
        title, body = parse_slack_message(message_text)
        print(f"Parsed Issue Title: {title}")
        print(f"Parsed Issue Body (first 100 chars): {body[:100]}...")
        issue_info = create_github_issue(title, body, github_pat, GITHUB_REPO_OWNER, GITHUB_REPO_NAME)
        issue_url = issue_info.get("html_url")
        issue_number = issue_info.get("number")
        print(f"Successfully created GitHub Issue: {issue_url}")
        if SLACK_WEBHOOK_URL:
            notification_message = f"GitHub Issueが作成されました: <{issue_url}|#{issue_number} {title}>"
            send_slack_notification(SLACK_WEBHOOK_URL, notification_message)
        return {"statusCode": 200, "body": "Issue created successfully"}
    except Exception as e:
        print(f"Error processing Slack event: {e}")
        error_message = f"GitHub Issueの作成中にエラーが発生しました: {e}"
        if SLACK_WEBHOOK_URL:
            send_slack_notification(SLACK_WEBHOOK_URL, error_message)
        return {"statusCode": 500, "body": f"Error: {str(e)}"} 