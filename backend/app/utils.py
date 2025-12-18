
import uuid
import boto3
import os

YC_ACCESS_KEY = os.environ.get("YC_ACCESS_KEY")
YC_SECRET_KEY = os.environ.get("YC_SECRET_KEY")
YC_BUCKET = os.environ.get("YC_BUCKET")
YC_ENDPOINT = "https://storage.yandexcloud.net"

s3_client = boto3.client(
    "s3",
    endpoint_url=YC_ENDPOINT,
    aws_access_key_id=YC_ACCESS_KEY,
    aws_secret_access_key=YC_SECRET_KEY,
)

def upload_image_to_yc(file):
    file_extension = file.filename.split(".")[-1]
    key = f"{uuid.uuid4()}.{file_extension}"

    s3_client.upload_fileobj(
        file.file,
        YC_BUCKET,
        key,
        ExtraArgs={"ContentType": file.content_type}
    )

    url = f"{YC_ENDPOINT}/{YC_BUCKET}/{key}"
    return url