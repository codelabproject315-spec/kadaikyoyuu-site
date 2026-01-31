import boto3
import os
import datetime
import streamlit as st
from botocore.exceptions import ClientError

# --- 設定の読み込み (Secrets優先) ---
def get_secret(key, default=None):
    return st.secrets.get(key) or os.getenv(key) or default

BUCKET_NAME = get_secret("S3_BUCKET_NAME")
TABLE_NAME = get_secret("DYNAMO_TABLE_NAME") 
REGION = get_secret("AWS_DEFAULT_REGION", "ap-northeast-1")
ACCESS_KEY = get_secret("AWS_ACCESS_KEY_ID")
SECRET_KEY = get_secret("AWS_SECRET_ACCESS_KEY")

# AWSクライアントの初期化
session = boto3.Session(
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
    region_name=REGION
)

s3 = session.client('s3')
dynamodb = session.resource('dynamodb')

def get_table():
    if not TABLE_NAME:
        st.error("❌ Secretsに 'DYNAMO_TABLE_NAME' が設定されていません。")
        return None
    return dynamodb.Table(TABLE_NAME)

def upload_exam(file, subject, year):
    table = get_table()
    if not table or not BUCKET_NAME:
        return False
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    file_key = f"exams/{year}/{subject}_{timestamp}_{file.name}"
    
    try:
        s3.upload_fileobj(file, BUCKET_NAME, file_key, ExtraArgs={'ContentType': file.type})
        file_url = f"https://{BUCKET_NAME}.s3.{REGION}.amazonaws.com/{file_key}"
        
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
    table = get_table()
    if not table: return []
    try:
        response = table.scan()
        return response.get('Items', [])
    except Exception as e:
        return []

def delete_exam(exam_id, file_key):
    """S3とDynamoDBからの削除処理（データ欠落に対応）"""
    table = get_table()
    if not table: return False
    try:
        # 1. file_key（S3のパス）がある場合のみS3から削除
        if file_key and str(file_key) != "None":
            try:
                s3.delete_object(Bucket=BUCKET_NAME, Key=file_key)
            except Exception as s3_e:
                # ファイルが既になくてもDB削除へ進むために警告にとどめる
                st.warning(f"S3ファイルの削除に失敗（スキップ）: {s3_e}")

        # 2. DynamoDBからレコードを削除
        table.delete_item(Key={'exam_id': exam_id})
        return True
    except Exception as e:
        st.error(f"AWS削除エラー: {e}")
        return False
