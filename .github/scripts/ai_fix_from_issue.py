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

# リポジトリのファイル一覧を取得（再帰的に全てのファイルを取得）
def fetch_all_files(repo, directory=""):
    contents = repo.get_contents(directory)
    all_files = []
    for item in contents:
        if item.type == "file":
            all_files.append(item.path)
        elif item.type == "dir":
            all_files.extend(fetch_all_files(repo, item.path))
    return all_files

files = fetch_all_files(repo)
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
    model=os.environ["OPENAI_MODEL"],
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
    sanitized_fname = os.path.basename(fname)  # Extract base filename
    if sanitized_fname in [os.path.basename(f) for f in files]:  # Validate against whitelist
        with open(sanitized_fname, "w") as f:
            f.write(content.strip())
    else:
        print(f"Warning: Invalid filename '{fname}' detected. Skipping file write.")

print("AIによるファイル修正完了")