import boto3
import os
import uuid
from dotenv import load_dotenv

# ローカル環境用（Streamlit CloudではSecretsが優先されます）
load_dotenv()

# --- AWS設定の読み込み ---
# 変数名をあなたの環境（DYNAMO_TABLE_NAME）に合わせています
REGION = os.getenv("AWS_DEFAULT_REGION", "ap-northeast-1")
BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
TABLE_NAME = os.getenv("DYNAMO_TABLE_NAME")

# クライアントの初期化
s3 = boto3.client('s3', region_name=REGION)
dynamodb = boto3.resource('dynamodb', region_name=REGION)

# テーブル名の取得チェック
if not TABLE_NAME:
    raise ValueError("環境変数 'DYNAMO_TABLE_NAME' が設定されていません。")
table = dynamodb.Table(TABLE_NAME)

def get_all_exams():
    """DynamoDBからすべての過去問データを取得"""
    try:
        response = table.scan()
        return response.get('Items', [])
    except Exception as e:
        print(f"Error scanning DynamoDB: {e}")
        return []

def upload_exam(file_obj, filename, subject, year, exam_type):
    """S3にファイルをアップロードし、DynamoDBにメタデータを保存"""
    try:
        # 1. S3へのアップロード
        file_key = f"exams/{uuid.uuid4()}_{filename}"
        s3.upload_fileobj(file_obj, BUCKET_NAME, file_key)
        
        # 2. DynamoDBへの保存
        exam_id = str(uuid.uuid4())
        item = {
            'exam_id': exam_id,
            'subject': subject,
            'year': year,
            'exam_type': exam_type,
            'file_key': file_key,
            'filename': filename
        }
        table.put_item(Item=item)
        return True
    except Exception as e:
        print(f"Error uploading exam: {e}")
        return False

def delete_exam(exam_id, file_key):
    """DynamoDBのレコードとS3のファイルを削除"""
    try:
        # 1. S3から削除
        s3.delete_object(Bucket=BUCKET_NAME, Key=file_key)
        
        # 2. DynamoDBから削除
        table.delete_item(Key={'exam_id': exam_id})
        return True
    except Exception as e:
        print(f"Error deleting exam: {e}")
        return False

def generate_presigned_url(file_key):
    """S3のファイルを閲覧するための期間限定URLを発行"""
    try:
        url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': BUCKET_NAME, 'Key': file_key},
            ExpiresIn=3600  # 1時間有効
        )
        return url
    except Exception as e:
        print(f"Error generating URL: {e}")
        return None
