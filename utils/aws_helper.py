import boto3
import streamlit as st
from botocore.exceptions import ClientError
from datetime import datetime
import os

def get_s3_resource():
    """AWS S3への接続を確立し、クライアントとバケット名を返す"""
    try:
        # StreamlitのSecretsから認証情報を読み込む
        client = boto3.client(
            "s3",
            aws_access_key_id=st.secrets["AWS_ACCESS_KEY_ID"],
            aws_secret_access_key=st.secrets["AWS_SECRET_ACCESS_KEY"],
            region_name=st.secrets.get("AWS_REGION", "ap-northeast-1")
        )
        bucket = st.secrets["AWS_S3_BUCKET"]
        return client, bucket
    except Exception as e:
        st.error(f"AWS接続設定エラー: {e}")
        return None, None

def upload_exam(file, subject, year, univ_id):
    """大学IDをフォルダ名(Prefix)にしてS3にアップロードする"""
    client, bucket = get_s3_resource()
    if not client: return False
    
    # パス構造: univ_id/年度/ファイル名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_extension = os.path.splitext(file.name)[1]
    file_key = f"{univ_id}/{year}/{subject}_{timestamp}{file_extension}"

    try:
        client.upload_fileobj(
            file, 
            bucket, 
            file_key,
            ExtraArgs={
                "ContentType": file.type,
                "Metadata": {
                    "university_id": univ_id,
                    "subject": subject,
                    "year": str(year)
                }
            }
        )
        return True
    except ClientError as e:
        st.error(f"アップロード失敗: {e}")
        return False

def get_all_exams():
    """S3から全データを取得し、大学IDを含むリストを返す"""
    client, bucket = get_s3_resource()
    if not client: return []
    
    exams = []
    try:
        response = client.list_objects_v2(Bucket=bucket)
        if "Contents" in response:
            for obj in response["Contents"]:
                key = obj["Key"]
                parts = key.split("/")
                # 正しい階層（大学/年度/ファイル）であるか確認
                if len(parts) >= 3:
                    u_id = parts[0] # ここに sit.ac.jp 等が入る
                    
                    # 1時間有効な署名付きURLを発行
                    url = client.generate_presigned_url(
                        'get_object',
                        Params={'Bucket': bucket, 'Key': key},
                        ExpiresIn=3600
                    )
                    
                    exams.append({
                        "exam_id": key,
                        "university_id": u_id,
                        "subject": parts[2].split("_")[0],
                        "year": parts[1],
                        "file_url": url
                    })
    except ClientError as e:
        st.error(f"データ取得失敗: {e}")
    return exams

def delete_exam(file_key):
    """指定されたファイルを削除する"""
    client, bucket = get_s3_resource()
    if not client: return False
    try:
        client.delete_object(Bucket=bucket, Key=file_key)
        return True
    except ClientError as e:
        st.error(f"削除失敗: {e}")
        return False
