import json
import os
import urllib.parse
import boto3
from process_pdf import apply_watermark

# Initialize the S3 client
s3 = boto3.client('s3')

# Retrieve the destination bucket name from Lambda Environment Variables
DESTINATION_BUCKET = os.environ.get('DESTINATION_BUCKET', "chrion-careerhub-watermark-files")
WATERMARK_TEXT = os.environ.get('WATERMARK_TEXT', 'Chrion - CONFIDENTIAL')


def lambda_handler(event, context):
    print(event)
    # 1. Extract the bucket name and object key from the event
    source_bucket = event['Records'][0]['s3']['bucket']['name']

    # URL decode the key (Critical: S3 replaces spaces with '+' in event payloads)
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')

    # Define local /tmp paths for Lambda file processing
    file_name = os.path.basename(key)
    download_path = f'/tmp/{file_name}'
    upload_path = f'/tmp/watermarked_{file_name}'
    upload_key = key

    try:
        # 2. Download the original PDF from the source S3 bucket
        print(f"Downloading {key} from {source_bucket}...")
        s3.download_file(source_bucket, key, download_path)

        # 3. If the file is txt name it .pdf
        if key.lower().endswith('.txt'):
            upload_key = key[:-4] + '.pdf'
            upload_path = upload_path[:-4]+".pdf"

        # 3. Apply the watermark
        if key.lower().endswith('.pdf') or key.lower().endswith('.txt'):
            apply_watermark(download_path, upload_path, WATERMARK_TEXT)
        else:
            return {
            'statusCode': 200,
            'body': f'File type not supported {key}'
        }

        # 4. Upload the modified PDF to the destination bucket
        print(f"Uploading to {DESTINATION_BUCKET}...")
        s3.upload_file(upload_path, DESTINATION_BUCKET, upload_key)

        return {
            'statusCode': 200,
            'body': f'Successfully watermarked {upload_key}'
        }

    except Exception as e:
        print(f"Error processing object {key} from bucket {source_bucket}: {str(e)}")
        raise e
