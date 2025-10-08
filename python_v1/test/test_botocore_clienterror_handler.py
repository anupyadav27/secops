git commit -m "Updated Python Scanner project - 2025-10-04"import boto3
from botocore.exceptions import BotoCoreError

def download_file():
    s3 = boto3.client('s3')
    try:
        s3.download_file('my-bucket', 'my-key', '/tmp/my-file')
    except BotoCoreError as e:
        print(f'Error occurred: {str(e)}')

if __name__ == "__main__":
    download_file()
