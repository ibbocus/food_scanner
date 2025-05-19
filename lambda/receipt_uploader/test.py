import json
import requests
import base64

# Configuration
ENDPOINT = "https://yycd5k53na.execute-api.eu-west-2.amazonaws.com/prod/receipt_uploader_lambda"
IMAGE_PATH = "images/receipt.jpg"
USER_ID = "test_user"

# Read raw image bytes
with open(IMAGE_PATH, "rb") as f:
    img_bytes = f.read()

def test_receipt_api():
    # Encode image to Base64
    encoded = base64.b64encode(img_bytes).decode('utf-8')

    # Build headers
    headers = {
    "Content-Type": "text/plain"
    }
    resp = requests.post(
    ENDPOINT,
    headers=headers,
    data=encoded,          # your base64 string
    timeout=10
    )

    # Output results
    print(f"Status: {resp.status_code}")
    print(resp.content)

if __name__ == "__main__":
    test_receipt_api()