#!/usr/bin/env python3
"""
Lambda関数デプロイパッケージ作成スクリプト
"""

import os
import sys
import zipfile
import tempfile
import subprocess
import argparse
from pathlib import Path


def find_python_files(directory: str) -> list:
    """指定されたディレクトリ内のPythonファイルを検索"""
    python_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    return python_files


def install_dependencies(requirements_file: str, target_dir: str) -> bool:
    """requirements.txtから依存関係をインストール"""
    try:
        cmd = [
            sys.executable, '-m', 'pip', 'install',
            '--target', target_dir,
            '-r', requirements_file
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"Dependencies installed successfully to {target_dir}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return False


def create_zip_package(source_dir: str, requirements_file: str, output_path: str) -> bool:
    """LambdaデプロイパッケージのZIPファイルを作成"""
    try:
        # 一時ディレクトリを作成
        with tempfile.TemporaryDirectory() as temp_dir:
            print(f"Creating package in temporary directory: {temp_dir}")
            
            # 依存関係をインストール
            if not install_dependencies(requirements_file, temp_dir):
                return False
            
            # Pythonファイルをコピー
            python_files = find_python_files(source_dir)
            for file_path in python_files:
                # 相対パスを計算
                rel_path = os.path.relpath(file_path, source_dir)
                target_path = os.path.join(temp_dir, rel_path)
                
                # ディレクトリを作成
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                
                # ファイルをコピー
                with open(file_path, 'rb') as src, open(target_path, 'wb') as dst:
                    dst.write(src.read())
                print(f"Copied: {file_path} -> {target_path}")
            
            # ZIPファイルを作成
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arc_name = os.path.relpath(file_path, temp_dir)
                        zipf.write(file_path, arc_name)
                        print(f"Added to ZIP: {arc_name}")
            
            print(f"Package created successfully: {output_path}")
            return True
            
    except Exception as e:
        print(f"Error creating package: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Create Lambda deployment package')
    parser.add_argument('--source', default='src/lambda_function',
                       help='Source directory containing Lambda function code')
    parser.add_argument('--requirements', default='src/requirements.txt',
                       help='Path to requirements.txt file')
    parser.add_argument('--output', required=True,
                       help='Output path for the ZIP package')
    
    args = parser.parse_args()
    
    # パスの存在確認
    if not os.path.exists(args.source):
        print(f"Error: Source directory '{args.source}' does not exist")
        sys.exit(1)
    
    if not os.path.exists(args.requirements):
        print(f"Error: Requirements file '{args.requirements}' does not exist")
        sys.exit(1)
    
    # パッケージ作成
    if create_zip_package(args.source, args.requirements, args.output):
        print("Package creation completed successfully")
        sys.exit(0)
    else:
        print("Package creation failed")
        sys.exit(1)


if __name__ == '__main__':
    main() 