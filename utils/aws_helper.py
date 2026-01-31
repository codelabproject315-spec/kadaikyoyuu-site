import boto3
import os
import datetime
import streamlit as st
from botocore.exceptions import ClientError

# --- 設定の読み込み (Secrets優先) ---
def get_secret(key, default=None):
    return st.secrets.get(key) or os.getenv(key) or default

BUCKET_NAME = get_secret("S3_BUCKET_NAME")
# 提供された名前に合わせて DYNAMO_TABLE_NAME を参照
TABLE_NAME = get_secret("DYNAMO_TABLE_NAME") 
REGION = get_secret("AWS_DEFAULT_REGION", "ap-northeast-1")
ACCESS_KEY = get_secret("AWS_ACCESS_KEY_ID")
SECRET_KEY = get_secret("AWS_SECRET_ACCESS_KEY")

# AWSクライアントの初期化
# Secretsに認証情報がある場合、明示的に渡すことで接続を確実にします
session = boto3.Session(
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
    region_name=REGION
)

s3 = session.client('s3')
dynamodb = session.resource('dynamodb')

def get_table():
    if not TABLE_NAME:
        st.error("❌ DYNAMO_TABLE_NAME が設定されていません。")
        return None
    return dynamodb.Table(TABLE_NAME)

def upload_exam(file, subject, year):
    table = get_table()
    if not table or not BUCKET_NAME:
        return False

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    file_key = f"exams/{year}/{subject}_{timestamp}_{file.name}"
    
    try:
        s3.upload_fileobj(
            file, 
            BUCKET_NAME, 
            file_key,
            ExtraArgs={'ContentType': file.type}
        )
        
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
        st.error(f"アップロードエラー: {e}")
        return False

def get_all_exams():
    table = get_table()
    if not table:
        return []
    try:
        response = table.scan()
        return response.get('Items', [])
    except Exception as e:
        st.error(f"取得エラー: {e}")
        return []

def delete_exam(exam_id, file_key):
    table = get_table()
    if not table:
        return False
    try:
        s3.delete_object(Bucket=BUCKET_NAME, Key=file_key)
        table.delete_item(Key={'exam_id': exam_id})
        return True
    except Exception as e:
        st.error(f"削除エラー: {e}")
        return False
