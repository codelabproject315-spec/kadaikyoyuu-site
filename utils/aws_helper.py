import boto3
import os
import datetime
import streamlit as st
from botocore.exceptions import ClientError

# --- 1. 設定の取得 (安全な読み込み) ---
def get_config():
    """Secretsまたは環境変数から設定を一括取得する"""
    return {
        "ACCESS_KEY": st.secrets.get("AWS_ACCESS_KEY_ID") or os.getenv("AWS_ACCESS_KEY_ID"),
        "SECRET_KEY": st.secrets.get("AWS_SECRET_ACCESS_KEY") or os.getenv("AWS_SECRET_ACCESS_KEY"),
        "REGION": st.secrets.get("AWS_DEFAULT_REGION") or os.getenv("AWS_DEFAULT_REGION", "ap-northeast-1"),
        "BUCKET_NAME": st.secrets.get("S3_BUCKET_NAME") or os.getenv("S3_BUCKET_NAME"),
        "TABLE_NAME": st.secrets.get("DYNAMO_TABLE_NAME") or os.getenv("DYNAMODB_TABLE_NAME") # 表記揺れに対応
    }

# --- 2. AWSリソースの取得 ---
def get_aws_resources():
    config = get_config()
    
    # 必須設定が欠けている場合のチェック
    if not all([config["ACCESS_KEY"], config["SECRET_KEY"], config["TABLE_NAME"]]):
        st.error("❌ AWS設定（Access Key, Secret Key, または Table Name）が見つかりません。")
        return None, None, None

    try:
        session = boto3.Session(
            aws_access_key_id=config["ACCESS_KEY"],
            aws_secret_access_key=config["SECRET_KEY"],
            region_name=config["REGION"]
        )
        s3 = session.client('s3')
        dynamodb = session.resource('dynamodb')
        table = dynamodb.Table(config["TABLE_NAME"])
        return s3, table, config
    except Exception as e:
        st.error(f"❌ AWS接続エラー: {e}")
        return None, None, None

# --- 3. 各操作関数 ---

def upload_exam(file, subject, year):
    """過去問をS3にアップロードし、DynamoDBにメタデータを保存"""
    s3, table, config = get_aws_resources()
    if not s3 or not table:
        return False
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    file_key = f"exams/{year}/{subject}_{timestamp}_{file.name}"
    
    try:
        # S3アップロード
        s3.upload_fileobj(file, config["BUCKET_NAME"], file_key, ExtraArgs={'ContentType': file.type})
        file_url = f"https://{config['BUCKET_NAME']}.s3.{config['REGION']}.amazonaws.com/{file_key}"
        
        # DynamoDB保存
        table.put_item(Item={
            'exam_id': file_key,
            'subject': subject,
            'year': int(year),
            'file_url': file_url,
            'file_key': file_key,
            'created_at': datetime.datetime.now().isoformat()
        })
        return True
    except Exception as e:
        st.error(f"AWSアップロードエラー: {e}")
        return False

def get_all_exams():
    """全データを取得"""
    _, table, _ = get_aws_resources()
    if not table:
        return []
    try:
        response = table.scan()
        return response.get('Items', [])
    except Exception as e:
        st.error(f"データ取得エラー: {e}")
        return []

def delete_exam(exam_id, file_key):
    """S3ファイルとDynamoDBレコードを削除"""
    s3, table, config = get_aws_resources()
    if not s3 or not table:
        return False
    
    try:
        # 1. S3から削除
        if file_key and str(file_key) != "None":
            try:
                s3.delete_object(Bucket=config["BUCKET_NAME"], Key=file_key)
            except Exception as s3_e:
                st.warning(f"S3ファイルの削除に失敗（スキップ可能）: {s3_e}")

        # 2. DynamoDBから削除
        table.delete_item(Key={'exam_id': exam_id})
        return True
    except Exception as e:
        st.error(f"AWS削除エラー: {e}")
        return False
