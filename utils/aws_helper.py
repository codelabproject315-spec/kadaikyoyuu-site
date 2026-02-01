import boto3
import datetime
import streamlit as st

def get_config():
    return {
        "ACCESS_KEY": st.secrets.get("AWS_ACCESS_KEY_ID"),
        "SECRET_KEY": st.secrets.get("AWS_SECRET_ACCESS_KEY"),
        "REGION": st.secrets.get("AWS_DEFAULT_REGION", "ap-northeast-1"),
        "BUCKET_NAME": st.secrets.get("S3_BUCKET_NAME"),
        "TABLE_NAME": st.secrets.get("DYNAMO_TABLE_NAME")
    }

def get_aws_resources():
    config = get_config()
    try:
        session = boto3.Session(
            aws_access_key_id=config["ACCESS_KEY"],
            aws_secret_access_key=config["SECRET_KEY"],
            region_name=config["REGION"]
        )
        return session.client('s3'), session.resource('dynamodb').Table(config["TABLE_NAME"]), config
    except Exception as e:
        st.error(f"AWS接続エラー: {e}")
        return None, None, None

def upload_exam(file, subject, year, univ):
    s3, table, config = get_aws_resources()
    if not s3: return False
    
    file_key = f"exams/{univ}/{year}/{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{file.name}"
    try:
        s3.upload_fileobj(file, config["BUCKET_NAME"], file_key, ExtraArgs={'ContentType': file.type})
        table.put_item(Item={
            'exam_id': file_key,
            'subject': subject,
            'year': int(year),
            'university': univ,
            'file_url': f"https://{config['BUCKET_NAME']}.s3.{config['REGION']}.amazonaws.com/{file_key}",
            'file_key': file_key,
            'created_at': datetime.datetime.now().isoformat()
        })
        return True
    except Exception as e:
        st.error(f"アップロード失敗: {e}")
        return False

def get_all_exams():
    _, table, _ = get_aws_resources()
    if not table: return []
    try:
        return table.scan().get('Items', [])
    except:
        return []

def delete_exam(exam_id, file_key):
    s3, table, config = get_aws_resources()
    try:
        s3.delete_object(Bucket=config["BUCKET_NAME"], Key=file_key)
        table.delete_item(Key={'exam_id': exam_id})
        return True
    except:
        return False

def get_demo_data():
    demo_url = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
    return [
        {"exam_id": "demo1", "subject": "【デモ】数学", "year": 2025, "university": "共通", "created_at": "2025-10-23T10:00:00", "file_url": demo_url, "file_key": "demo/1"},
        {"exam_id": "demo2", "subject": "【デモ】コミュニケーション英語", "year": 2024, "university": "共通", "created_at": "2025-12-07T15:30:00", "file_url": demo_url, "file_key": "demo/2"}
    ]
