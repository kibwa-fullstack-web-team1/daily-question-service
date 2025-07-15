import boto3
from botocore.exceptions import ClientError
import logging
import os

# 로깅 설정
logger = logging.getLogger(__name__)

# Config 임포트
from app.config.config import Config

class S3Service:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY,
            region_name=Config.AWS_REGION
        )
        self.bucket_name = Config.S3_BUCKET_NAME

    def upload_file(self, file_content: bytes, object_name: str):
        """S3 버킷에 파일을 업로드합니다.

        :param file_content: 파일 내용 (바이트).
        :param object_name: S3 객체 이름. 지정되지 않으면 파일 이름이 사용됩니다.
        :return: 파일 업로드 성공 시 True, 실패 시 False.
        """
        if not self.bucket_name:
            logger.error("S3_BUCKET_NAME 환경 변수가 설정되지 않았습니다.")
            return False

        try:
            self.s3_client.put_object(Bucket=self.bucket_name, Key=object_name, Body=file_content)
            logger.info(f"파일 {object_name}이(가) {self.bucket_name}에 업로드되었습니다.")
        except ClientError as e:
            logger.error(f"파일 {object_name} 업로드 실패: {e}")
            return False
        return True

    def get_file_url(self, object_name: str):
        """S3 객체의 공개 URL을 생성합니다."""
        if not self.bucket_name:
            return None
        # Config에서 AWS_REGION을 가져와 사용
        return f"https://{self.bucket_name}.s3.{Config.AWS_REGION}.amazonaws.com/{object_name}"
