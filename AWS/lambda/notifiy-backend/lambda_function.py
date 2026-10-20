import urllib.request
import json
import hmac
import hashlib
import os

# Environment Variables
AWS_SECRET = os.environ.get('AWS_SECRET')
API_BASE_URL = os.environ.get('API_BASE_URL')
AWS_EMAIL = os.environ.get('AWS_EMAIL')
AWS_PASSWORD = os.environ.get('AWS_PASSWORD')

LOGIN_URL = f"{API_BASE_URL}/api/v1/auth/login-aws"
NOTIIFY_URL = f"{API_BASE_URL}/api/v1/files/file-uploaded"

def get_access_token():
    """Step 1: Authenticate and get the JWT"""
    payload = json.dumps({
        "email": AWS_EMAIL,
        "password": AWS_PASSWORD
    }).encode('utf-8')

    req = urllib.request.Request(LOGIN_URL, data=payload, method='POST')
    req.add_header('Content-Type', 'application/json')

    try:
        with urllib.request.urlopen(req) as response:
            response_data = json.loads(response.read().decode('utf-8'))
            return response_data.get('accessToken')
    except Exception as e:
        print(f"Failed to authenticate Lambda: {str(e)}")
        raise e

def lambda_handler(event, context):
    try:
        # 1. Extract values exactly as they appear in the AWS event dictionary
        timestamp = event['timestamp']
        requestId = event['requestContext']['requestId']
        s3Key = event['requestPayload']['Records'][0]['s3']['object']['key']

        # 2. Login
        accessToken = get_access_token()

        # 3. Generate HMAC (Prevents replay attacks even within the 60-second window)
        message = f"{requestId}.{timestamp}.{s3Key}".encode('utf-8')
        secret = AWS_SECRET.encode('utf-8')
        signature = hmac.new(secret, message, hashlib.sha256).hexdigest()

        # 4. Create Payload and Request Header
        payload = json.dumps({"s3Key": s3Key}).encode('utf-8')
        req = urllib.request.Request(NOTIIFY_URL, data=payload, method='PATCH')
        # Attach ALL security headers
        req.add_header('Content-Type', 'application/json')
        req.add_header('Authorization', f'Bearer {accessToken}')
        req.add_header('X-AWS-RequestId', requestId)
        req.add_header('X-AWS-Timestamp', timestamp)
        req.add_header('X-AWS-Signature', signature)

        with urllib.request.urlopen(req) as response:
            print(f"Success! Status: {response.status}")

        return {
                'statusCode': 200,
                'body': json.dumps('Successfully notified backend')
            }

    except Exception as e:
        print(f"process failed: {str(e)}")
        raise e