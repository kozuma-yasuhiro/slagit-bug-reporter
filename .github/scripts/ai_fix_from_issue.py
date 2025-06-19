import os
import openai
from github import Github

# 環境変数から情報取得
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
REPO_NAME = os.environ["REPO_NAME"]
ISSUE_NUMBER = int(os.environ["ISSUE_NUMBER"])
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

g = Github(GITHUB_TOKEN)
repo = g.get_repo(REPO_NAME)
issue = repo.get_issue(number=ISSUE_NUMBER)

# リポジトリのファイル一覧を取得（例としてルートディレクトリのみ。必要に応じて拡張可）
files = [f.path for f in repo.get_contents("") if f.type == "file"]

# AIへのプロンプト生成
prompt = f"""
あなたはGitHubリポジトリのAIコントリビューターです。
次のIssueの内容から、どのファイルをどのように修正すべきか考えてください。
Issueタイトル: {issue.title}
Issue本文: {issue.body}
リポジトリ内のファイル一覧: {files}

修正すべきファイル名と、その新しい内容を
# file: ファイル名
<修正後のコード>
# endfile
の形式で返してください。必要なファイルだけ、複数でも一つでも構いません。
"""

openai.api_key = OPENAI_API_KEY
response = openai.ChatCompletion.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": prompt}],
    temperature=0.2,
    max_tokens=4096,
)
result = response.choices[0].message['content']

# AIの返答を検証
import re

if not re.search(r"# file: .+?\n.*?# endfile", result, re.DOTALL):
    print("Error: AI response is not in the expected format.")
    print("Response received:", result)
    exit(1)

# AIの返答をパースして各ファイルを書き換える
for match in re.finditer(r"# file: (.+?)\n(.*?)# endfile", result, re.DOTALL):
    fname, content = match.groups()
    with open(fname, "w") as f:
        f.write(content.strip())

print("AIによるファイル修正完了")