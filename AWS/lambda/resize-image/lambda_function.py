import base64
import boto3
import os
from io import BytesIO
from PIL import Image

s3 = boto3.client('s3')
SOURCE_BUCKET = os.environ.get('SOURCE_BUCKET', 'chrion-careerhub-profiles')

def lambda_handler(event, context):
    try:
        # 1. Extract image path and requested width from URL
        # Example URL: https://.../profile.jpg?w=300
        object_key = event.get('rawPath', '').lstrip('/')
        query_params = event.get('queryStringParameters') or {}
        requested_width = query_params.get('w')

        if not object_key:
            return {"statusCode": 400, "body": "No image specified"}

        # 2. Download original image from S3
        response = s3.get_object(Bucket=SOURCE_BUCKET, Key=object_key)
        original_image = response['Body'].read()
        content_type = response.get('ContentType', 'image/jpeg')

        print("contentType: ",content_type)

        # If no width parameter is passed or not a image content, just return the original file
        if not requested_width or content_type not in ['image/jpeg','image/png','image/webp']:
            return build_response(original_image, content_type)

        # 3. Resize image using Pillow while maintaining aspect ratio
        with Image.open(BytesIO(original_image)) as img:
            width = int(requested_width)
            w_percent = (width / float(img.size[0]))
            h_size = int((float(img.size[1]) * float(w_percent)))

            # LANCZOS provides the highest quality downscaling
            img = img.resize((width, h_size), Image.Resampling.LANCZOS)

            # Save to in-memory buffer
            buffer = BytesIO()
            # Handle formats (e.g., JPEG doesn't support RGBA transparency)
            if img.mode in ("RGBA", "P") and content_type == 'image/jpeg':
                img = img.convert("RGB")

            img_format = img.format if img.format else content_type.split('/')[-1].upper()
            if img_format == 'JPG': img_format = 'JPEG'

            img.save(buffer, format=img_format)
            resized_image = buffer.getvalue()

        # 4. Return the resized binary image to CloudFront
        return build_response(resized_image, content_type)

    except s3.exceptions.NoSuchKey:
        return {"statusCode": 404, "body": "Image not found"}
    except Exception as e:
        print(f"Error: {str(e)}")
        return {"statusCode": 500, "body": "Internal Server Error"}

def build_response(image_bytes, content_type):
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": content_type,
            # Tell CloudFront and browsers to cache this size for 1 year
            "Cache-Control": "public, max-age=31536000"
        },
        # Binary data must be base64 encoded when returned through Lambda HTTP integrations
        "body": base64.b64encode(image_bytes).decode('utf-8'),
        "isBase64Encoded": True
    }
