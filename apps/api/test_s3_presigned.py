import boto3
from botocore.config import Config

REGION = "us-east-2"
BUCKET = "papermind-dev-8086"
KEY = "test/presigned-test.pdf"

s3 = boto3.client(
    "s3",
    region_name=REGION,
    endpoint_url=f"https://s3.{REGION}.amazonaws.com",
    config=Config(signature_version="s3v4"),
)

url = s3.generate_presigned_url(
    ClientMethod="put_object",
    Params={
        "Bucket": BUCKET,
        "Key": KEY,
        "ContentType": "application/pdf",
    },
    ExpiresIn=300,
)

print("Presigned upload URL:")
print(url)