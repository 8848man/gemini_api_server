import logging
import os
import json

from google.cloud import firestore
from google.oauth2 import service_account
from src.core.config import get_settings  # Settings 불러오기
from pathlib import Path

logger = logging.getLogger(__name__)
settings = get_settings()

class FirestoreService:
    def __init__(self):
        try:
            # 환경변수에서 JSON 문자열 읽기
            firebase_key_json = os.getenv("FIREBASE_KEY_JSON").strip()
            
            # 프로젝트 id 선언
            project_id : str = "machat-f1450"
            if firebase_key_json:
                logger.info("Initializing Firestore with JSON string from environment variable.")
                key_info = json.loads(firebase_key_json)
                creds = service_account.Credentials.from_service_account_info(key_info)
                self.client = firestore.AsyncClient(credentials=creds, project=project_id)
                logger.info("Firestore initialized from environment variable JSON.")
            else:
                # 기존처럼 파일 경로로 초기화 시도
                cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
                logger.info(f"Firestore credential path: {cred_path}")

                if cred_path:
                    path_obj = Path(cred_path)
                    if not path_obj.exists():
                        raise FileNotFoundError(f"Firestore credential not found: {cred_path}")

                    creds = service_account.Credentials.from_service_account_file(str(path_obj))
                    self.client = firestore.AsyncClient(credentials=creds, project=project_id)
                    logger.info("Firestore initialized with service account file.")
                else:
                    # ADC (Application Default Credentials) 사용
                    self.client = firestore.AsyncClient(project=project_id)
                    logger.info("Firestore initialized with Application Default Credentials.")

        except Exception as e:
            logger.exception(f"Failed to initialize Firestore: {e}")
            raise

    async def get_word_data(self, word: str) -> dict | None:
        try:
            doc_ref = self.client.collection('master_voca').document(word)
            doc = await doc_ref.get()
            if doc.exists:
                return doc.to_dict()
            return None
        except Exception as e:
            logger.warning(f"that word doesn't exist in collection or error occurred : {e}")


    async def save_word_data(self, word: str, data: dict):
        doc_ref = self.client.collection('master_voca').document(word)
        await doc_ref.set(data)

firestore_service = FirestoreService()