import os
import json
import boto3
from boto3.dynamodb.conditions import Key

CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET,OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization'
}

# DynamoDB table and index names from environment
TABLE_NAME = os.environ.get('DDB_TABLE', 'ReceiptsTable')
USER_INDEX = os.environ.get('USER_INDEX', 'user_id-index')

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(TABLE_NAME)

def lambda_handler(event, context):
    """
    Expects a GET request with a query string parameter 'user_id'.
    Returns all receipts saved for that user.
    """
    # Handle CORS preflight
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 204,
            'headers': CORS_HEADERS,
            'body': ''
        }

    # Extract user_id from query parameters
    user_id = event.get('queryStringParameters', {}).get('user_id')
    if not user_id:
        return {
            'statusCode': 400,
            'headers': CORS_HEADERS,
            'body': json.dumps({'error': 'Missing required parameter user_id'})
        }

    # Query the GSI on user_id
    try:
        resp = table.query(
            IndexName=USER_INDEX,
            KeyConditionExpression=Key('user_id').eq(user_id)
        )
        items = resp.get('Items', [])
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': CORS_HEADERS,
            'body': json.dumps({'error': str(e)})
        }

    return {
        'statusCode': 200,
        'headers': CORS_HEADERS,
        'body': json.dumps({'receipts': items}, default=str)
    }