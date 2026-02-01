import boto3
import streamlit as st
from botocore.exceptions import ClientError
from datetime import datetime
import os

# --- AWS接続設定 ---
# StreamlitのSecrets (.streamlit/secrets.toml) から取得
try:
    S3_BUCKET = st.secrets["AWS_S3_BUCKET"]
    REGION = st.secrets.get("AWS_REGION", "ap-northeast-1")

    s3_client = boto3.client(
        "s3",
        aws_access_key_id=st.secrets["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=st.secrets["AWS_SECRET_ACCESS_KEY"],
        region_name=REGION
    )
except KeyError:
    st.error("AWSの認証情報が設定されていません。secrets.tomlを確認してください。")

def upload_exam(file, subject, year, univ_id):
    """
    ファイルをS3にアップロードする。
    パス構造: {univ_id}/{year}/{subject}_{timestamp}.ext
    例: sit.ac.jp/2024/数学_20260201.pdf
    """
    # タイムスタンプ生成
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_extension = os.path.splitext(file.name)[1]
    
    # 埼玉工業大学(sit.ac.jp)などのドメインをフォルダ名に使用
    file_key = f"{univ_id}/{year}/{subject}_{timestamp}{file_extension}"

    try:
        s3_client.upload_fileobj(
            file, 
            S3_BUCKET, 
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
    """
    S3バケット内の全オブジェクトを取得し、情報をリスト化して返す
    """
    exams = []
    try:
        # バケット内のオブジェクトをリストアップ
        response = s3_client.list_objects_v2(Bucket=S3_BUCKET)
        
        if "Contents" in response:
            for obj in response["Contents"]:
                key = obj["Key"]
                # パス形式: univ_id/year/filename
                parts = key.split("/")
                
                if len(parts) >= 3:
                    u_id = parts[0]
                    yr = parts[1]
                    fname = parts[2]
                    
                    # 署名付きURLを発行（1時間有効）
                    # これにより、非公開設定のファイルも安全に閲覧可能
                    url = s3_client.generate_presigned_url(
                        'get_object',
                        Params={'Bucket': S3_BUCKET, 'Key': key},
                        ExpiresIn=3600
                    )
                    
                    exams.append({
                        "exam_id": key,
                        "university_id": u_id,  # App.pyでのフィルタリングに使用
                        "subject": fname.split("_")[0], # ファイル名から教科名を復元
                        "year": yr,
                        "file_url": url,
                        "file_key": key
                    })
    except ClientError as e:
        st.error(f"データ取得失敗: {e}")
    
    return exams

def delete_exam(exam_id, file_key):
    """
    指定されたファイルをS3から削除する
    """
    try:
        s3_client.delete_object(Bucket=S3_BUCKET, Key=file_key)
        return True
    except ClientError as e:
        st.error(f"削除失敗: {e}")
        return False
