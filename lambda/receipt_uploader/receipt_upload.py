import os
import json
import uuid
import base64
from datetime import datetime
import boto3

s3 = boto3.client('s3')
BUCKET = os.environ.get('RECEIPTS_BUCKET')

CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST,OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization,user-id'
}

def lambda_handler(event, context):
    # Preflight support
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 204,
            'headers': CORS_HEADERS,
            'body': ''
        }

    # Extract user ID and base64 body
    user_id = event.get('headers', {}).get('user-id', 'anonymous')
    body = event.get('body', '')
    if event.get('isBase64Encoded', False):
        body = base64.b64decode(body).decode('utf-8')
    image_data = base64.b64decode(body)

    # Construct S3 key
    timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    key = f"{user_id}/{timestamp}_{uuid.uuid4().hex}.jpg"

    # Upload to S3
    s3.put_object(
        Bucket=BUCKET,
        Key=key,
        Body=image_data,
        ContentType='image/jpeg'
    )

    # Response
    return {
        'statusCode': 200,
        'headers': CORS_HEADERS,
        'body': json.dumps({ 'bucket': BUCKET, 'key': key })
    }