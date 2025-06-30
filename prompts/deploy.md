## AWS Lambdaデプロイ用 GitHub Actions ワークフローの作成

### プロジェクト概要と目的

以下の要件に基づき、`slagit-bug-reporter` プロジェクトのAWS Lambda関数をGitHub Actions経由でデプロイするためのワークフローを生成してください。

**目的**:

  * Gitリポジトリへのプッシュ（特定のブランチ）をトリガーに、Lambda関数が自動的にAWSにデプロイされるようにする。
  * デプロイプロセスを自動化し、CI/CDパイプラインを確立する。
  * 秘匿情報（AWS認証情報）を安全に扱う。

### 技術スタック

  * **CI/CDツール**: GitHub Actions
  * **デプロイ先**: AWS Lambda
  * **デプロイ方法**: **`aws-cli` を使用したデプロイ**を想定し、必要に応じてPythonスクリプトでビルドとパッケージングを行う。
  * **プログラミング言語**: Python 3.9+ (Lambda関数コード)

### 求める成果物

1.  `.github/workflows/deploy.yml` ファイルの内容。
2.  Lambda関数をパッケージングしてデプロイするためのPythonスクリプト (`scripts/deploy_lambda.py`)。

### GitHub Actions ワークフロー (`.github/workflows/deploy.yml`) 要件

  * **ワークフロー名**: `Deploy Lambda Function`

  * **トリガー**: `main` ブランチへの`push`イベントでトリガーされるように設定してください。

  * **実行環境**: `ubuntu-latest` を使用します。

  * **ステップ**:

    1.  **リポジトリのチェックアウト**: GitHubリポジトリのコードをビルドエージェントにチェックアウトします。
    2.  **Pythonセットアップ**: Python 3.9環境をセットアップします。
    3.  **依存関係のインストール**: `src/lambda_function` ディレクトリ内のLambda関数が必要とするPythonライブラリをインストールします。これらのライブラリは、Lambdaのデプロイパッケージに含まれる必要があります。`src/lambda_function/requirements.txt` を使用して、一時的なディレクトリにインストールし、後でZIPに含められるようにしてください。
    4.  **AWS認証情報の設定**: GitHub ActionsのSecrets (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`) を使用して、AWS CLI認証を設定します。
          * `aws-actions/configure-aws-credentials@v1` アクションを使用してください。
    5.  **Lambdaデプロイパッケージの作成**:
          * `scripts/deploy_lambda.py` スクリプトを呼び出し、Lambdaコードと依存ライブラリをまとめてデプロイ可能なZIPファイルを作成します。
          * ZIPファイルの出力パスは `artifact/lambda_package.zip` のように指定し、このアーティファクトを次のステップで利用できるようにしてください。
    6.  **Lambda関数へのデプロイ**:
          * 作成されたZIPファイル (`artifact/lambda_package.zip`) を使用して、AWS CLIの `aws lambda update-function-code` コマンドでLambda関数をデプロイします。
          * もし関数が存在しない場合は `aws lambda create-function` を使用することを考慮しても良いですが、**まずは `update-function-code` で既存関数の更新**を優先してください。
          * Lambda関数名、ハンドラー、ランタイムなどの設定は、環境変数 (`LAMBDA_FUNCTION_NAME`, `LAMBDA_HANDLER`, `LAMBDA_RUNTIME`) から取得できるようにしてください。
          * IAM Role の ARN も環境変数 (`LAMBDA_ROLE_ARN`) から取得できるようにしてください。
          * ZIPファイルをS3バケットにアップロードし、そこからデプロイする方式 (`--s3-bucket` オプション) を採用してください。S3バケット名は環境変数 (`S3_BUCKET_FOR_DEPLOYMENT`) から取得します。

  * **AWS認証情報の扱い**:

      * AWSのアクセスキーIDとシークレットアクセスキーは、GitHubリポジトリの**Secrets**に保存されていることを前提とします。変数名は `AWS_ACCESS_KEY_ID` と `AWS_SECRET_ACCESS_KEY` としてください。
      * AWSリージョンもSecrets (`AWS_REGION`) に保存されているか、またはワークフロー内で直接指定できるようにしてください。

### Lambdaデプロイスクリプト (`scripts/deploy_lambda.py`) 要件

GitHub Actionsのワークフローから呼び出されるPythonスクリプトを作成します。

  * **機能**:
    1.  `src/lambda_function` ディレクトリ内のすべてのPythonファイル (`.py` 拡張子を持つファイル) を検出します。
    2.  `src/lambda_function/requirements.txt` に記載された依存ライブラリを、Lambdaデプロイパッケージのルートディレクトリにインストールします。
          * インストールには `pip install --target <temp_dir> -r requirements.txt` のようなコマンドを使用し、その後、その一時ディレクトリの内容とLambdaソースコードをZIPに含めてください。
    3.  検出されたLambdaコードファイルと、インストールされた依存ライブラリを全て含んだ**単一のZIPファイル**を作成します。
    4.  ZIPファイルの出力パスはCLI引数で指定できるようにします。
  * **エラーハンドリング**: パッケージング中にエラーが発生した場合、適切なメッセージを出力し、非ゼロの終了コードを返してください。
  * **CLI引数**: パッケージの出力パス (`--output <path>`) をCLI引数で受け取れるようにしてください。

### ディレクトリ構成 (参考)

```
.
├── .github/
│   └── workflows/
│       └── deploy.yml          # GitHub Actions ワークフロー (生成対象1)
├── src/
│   ├── lambda_function/
│   │   ├── handler.py          # Lambdaのメインハンドラー
│   │   ├── requirements.txt    # Lambda関数の依存関係
│   │   └── utils/              # 共通ユーティリティなど
│   │       ├── github_api.py
│   │       └── slack_parser.py
│   └── ...
├── scripts/
│   └── deploy_lambda.py        # Lambdaデプロイスクリプト (生成対象2)
├── ...
```

### 環境変数 (GitHub Actionsのワークフロー内で設定)

以下の環境変数をGitHub Actionsのワークフロー内で設定し、デプロイ時に使用できるようにしてください。

  * `LAMBDA_FUNCTION_NAME`: `slagit-bug-reporter-function` のように、デプロイ対象のLambda関数名を指定します。
  * `LAMBDA_HANDLER`: `src/lambda_function/handler.lambda_handler` のように、Lambdaのハンドラーパスを指定します。
  * `LAMBDA_RUNTIME`: `python3.9` のように、Lambdaのランタイムを指定します。
  * `LAMBDA_ROLE_ARN`: Lambda関数に割り当てるIAMロールのARN。
  * `S3_BUCKET_FOR_DEPLOYMENT`: デプロイパッケージを一時的にアップロードするためのS3バケット名。このバケットは事前に作成されている必要があります。
