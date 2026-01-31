import boto3
import datetime
import streamlit as st
import uuid
from botocore.exceptions import ClientError

# --- 1. 設定の取得 ---
def get_config():
    """Streamlit Secrets から設定を一括取得する"""
    return {
        "ACCESS_KEY": st.secrets.get("AWS_ACCESS_KEY_ID"),
        "SECRET_KEY": st.secrets.get("AWS_SECRET_ACCESS_KEY"),
        "REGION": st.secrets.get("AWS_DEFAULT_REGION", "ap-northeast-1"),
        "BUCKET_NAME": st.secrets.get("S3_BUCKET_NAME"),
        "TABLE_NAME": st.secrets.get("DYNAMO_TABLE_NAME")
    }

# --- 2. AWSリソースの取得 ---
def get_aws_resources():
    config = get_config()
    required_keys = ["ACCESS_KEY", "SECRET_KEY", "BUCKET_NAME", "TABLE_NAME"]
    if not all(config.get(k) for k in required_keys):
        st.error("❌ AWS設定が不足しています。Secretsを確認してください。")
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
    
    # 日本語ファイル名によるエラーを防ぐため、UUIDをファイル名に使用
    file_ext = file.name.split('.')[-1]
    safe_filename = f"{uuid.uuid4()}.{file_ext}"
    file_key = f"exams/{year}/{safe_filename}"
    
    try:
        # S3アップロード（ACL設定なしでアップロード可能）
        s3.upload_fileobj(
            file, 
            config["BUCKET_NAME"], 
            file_key, 
            ExtraArgs={'ContentType': file.type}
        )
        
        # DynamoDB保存（URLは取得時に生成するため、ここではkeyを重視）
        table.put_item(Item={
            'exam_id': str(uuid.uuid4()), # ユニークなID
            'subject': subject,
            'year': int(year),
            'file_key': file_key,
            'created_at': datetime.datetime.now().isoformat()
        })
        return True
    except Exception as e:
        st.error(f"AWSアップロードエラー: {e}")
        return False

def get_all_exams():
    """全データを取得し、S3の署名付きURLを付与する"""
    s3, table, config = get_aws_resources()
    if not table or not s3:
        return []
    try:
        response = table.scan()
        items = response.get('Items', [])
        
        # 各データに対して一時的な署名付きURLを発行
        for item in items:
            if 'file_key' in item:
                try:
                    # 1時間（3600秒）有効なURLを生成
                    item['file_url'] = s3.generate_presigned_url(
                        'get_object',
                        Params={
                            'Bucket': config["BUCKET_NAME"],
                            'Key': item['file_key']
                        },
                        ExpiresIn=3600
                    )
                except Exception:
                    item['file_url'] = "#"
        return items
    except Exception as e:
        st.error(f"データ取得エラー: {e}")
        return []

def delete_exam(exam_id, file_key):
    """S3ファイルとDynamoDBレコードを削除"""
    s3, table, config = get_aws_resources()
    if not s3 or not table:
        return False
    
    try:
        # 1. S3から物理ファイルを削除
        if file_key and str(file_key) != "None":
            s3.delete_object(Bucket=config["BUCKET_NAME"], Key=file_key)

        # 2. DynamoDBからレコードを削除
        table.delete_item(Key={'exam_id': exam_id})
        return True
    except Exception as e:
        st.error(f"AWS削除エラー: {e}")
        return False
