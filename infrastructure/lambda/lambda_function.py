import json
import requests

def lambda_handler(event, context):
    # CORS headers
    cors_headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Allow-Methods": "OPTIONS,POST"
    }

    # Handle preflight OPTIONS request
    if event["httpMethod"] == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": cors_headers,
            "body": json.dumps({"message": "CORS preflight OK"})
        }

    try:
        body = json.loads(event["body"])
        barcode = body.get("barcode")

        if not barcode:
            return {
                "statusCode": 400,
                "headers": cors_headers,
                "body": json.dumps({"error": "Missing 'barcode'"})
            }

        response = requests.get(
            f"https://world.openfoodfacts.org/api/v0/product/{barcode}.json"
        )

        return {
            "statusCode": 200,
            "headers": cors_headers,
            "body": response.text
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": cors_headers,
            "body": json.dumps({"error": str(e)})
        }

