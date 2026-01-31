import boto3
import os
from botocore.exceptions import ClientError

# AWSクライアントの設定
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.getenv("DYNAMODB_TABLE_NAME"))
BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

def get_all_exams():
    # 全データ取得ロジック（実際の実装に合わせて調整してください）
    response = table.scan()
    return response.get('Items', [])

def upload_exam(file, subject, year):
    file_key = f"exams/{year}/{subject}_{file.name}"
    try:
        # S3へアップロード
        s3.upload_fileobj(file, BUCKET_NAME, file_key)
        file_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{file_key}"
        
        # DynamoDBへ保存
        import datetime
        table.put_item(Item={
            'exam_id': file_key, # 一意識別子としてパスを使用
            'subject': subject,
            'year': year,
            'file_url': file_url,
            'file_key': file_key,
            'created_at': datetime.datetime.now().isoformat()
        })
        return True
    except Exception as e:
        print(f"Upload error: {e}")
        return False

def delete_exam(exam_id, file_key):
    """DynamoDBとS3の両方からデータを削除する"""
    try:
        # 1. S3から削除
        s3.delete_object(Bucket=BUCKET_NAME, Key=file_key)
        # 2. DynamoDBから削除
        table.delete_item(Key={'exam_id': exam_id})
        return True
    except Exception as e:
        print(f"Delete error: {e}")
        return False
