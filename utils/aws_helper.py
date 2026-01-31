import boto3
import uuid
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# AWS設定（環境変数から読み込み）
S3_BUCKET = "your-bucket-name"
DYNAMO_TABLE = "your-table-name"
REGION = "ap-northeast-1"

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb", region_name=REGION)
table = dynamodb.Table(DYNAMO_TABLE)

def upload_exam(file, subject, year):
    # 1. S3にファイルをアップロード
    file_ext = file.name.split(".")[-1]
    file_key = f"exams/{uuid.uuid4()}.{file_ext}"
    
    s3.upload_fileobj(file, S3_BUCKET, file_key)
    
    # 2. 公開URLの生成（バケットの公開設定が必要）
    file_url = f"https://{S3_BUCKET}.s3.amazonaws.com/{file_key}"
    
    # 3. DynamoDBにメタデータを保存
    table.put_item(
        Item={
            "exam_id": str(uuid.uuid4()),
            "subject": subject,
            "year": int(year),
            "file_url": file_url,
            "created_at": datetime.now().isoformat()
        }
    )

def get_all_exams():
    response = table.scan()
    # 作成日順にソートして返す
    return sorted(response.get("Items", []), key=lambda x: x["created_at"], reverse=True)  
