import boto3
import os
import datetime
import streamlit as st
from botocore.exceptions import ClientError

# --- 設定の読み込み ---
# Streamlit CloudのSecretsまたはローカルの.envから取得
try:
    # 優先順位: 1. st.secrets (Cloud用) / 2. os.getenv (ローカル.env用)
    BUCKET_NAME = st.secrets.get("S3_BUCKET_NAME") or os.getenv("S3_BUCKET_NAME")
    TABLE_NAME = st.secrets.get("DYNAMODB_TABLE_NAME") or os.getenv("DYNAMODB_TABLE_NAME")
    REGION = st.secrets.get("AWS_REGION") or os.getenv("AWS_REGION", "ap-northeast-1")
except Exception:
    # Secretsが設定されていない初期状態の回避
    BUCKET_NAME = None
    TABLE_NAME = None
    REGION = "ap-northeast-1"

# AWSクライアントの初期化
# ローカルで実行し、環境変数に認証情報がない場合は st.secrets から渡すことも可能
s3 = boto3.client('s3', region_name=REGION)
dynamodb = boto3.resource('dynamodb', region_name=REGION)

def get_table():
    """テーブルオブジェクトを安全に取得する"""
    if not TABLE_NAME:
        st.error("❌ DYNAMODB_TABLE_NAME が設定されていません。Secretsを確認してください。")
        return None
    return dynamodb.Table(TABLE_NAME)

def upload_exam(file, subject, year):
    """S3にファイルをアップロードし、DynamoDBにメタデータを保存する"""
    table = get_table()
    if not table or not BUCKET_NAME:
        return False

    # ファイルパスの生成 (S3上のKey)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    file_key = f"exams/{year}/{subject}_{timestamp}_{file.name}"
    
    try:
        # 1. S3へアップロード
        s3.upload_fileobj(
            file, 
            BUCKET_NAME, 
            file_key,
            ExtraArgs={'ContentType': file.type} # ブラウザで開きやすくするため
        )
        
        # S3のURL構築 (パブリック読み取り設定がない場合は署名付きURLが必要になる場合があります)
        file_url = f"https://{BUCKET_NAME}.s3.{REGION}.amazonaws.com/{file_key}"
        
        # 2. DynamoDBへ保存
        table.put_item(Item={
            'exam_id': file_key,  # パーティションキー
            'subject': subject,
            'year': int(year),
            'file_url': file_url,
            'file_key': file_key,
            'created_at': datetime.datetime.now().isoformat()
        })
        return True
    except ClientError as e:
        st.error(f"AWS Error: {e.response['Error']['Message']}")
        return False
    except Exception as e:
        st.error(f"予期せぬエラー: {e}")
        return False

def get_all_exams():
    """DynamoDBから全データを取得する"""
    table = get_table()
    if not table:
        return []

    try:
        response = table.scan()
        return response.get('Items', [])
    except ClientError as e:
        st.error(f"データ取得失敗: {e.response['Error']['Message']}")
        return []

def delete_exam(exam_id, file_key):
    """S3とDynamoDBの両方から削除する"""
    table = get_table()
    if not table or not BUCKET_NAME:
        return False

    try:
        # 1. S3からオブジェクトを削除
        s3.delete_object(Bucket=BUCKET_NAME, Key=file_key)
        
        # 2. DynamoDBからレコードを削除
        table.delete_item(Key={'exam_id': exam_id})
        
        return True
    except ClientError as e:
        st.error(f"削除エラー: {e.response['Error']['Message']}")
        return False
