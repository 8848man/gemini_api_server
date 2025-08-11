import firebase_admin
from firebase_admin import credentials, auth
from pathlib import Path
import logging
from src.core.config import get_settings  # Settings 불러오기

logger = logging.getLogger(__name__)
settings = get_settings()

firebase_app = None


# def initialize_firebase():
#     global firebase_app
#
#     if firebase_admin._apps:
#         logger.info("Firebase already initialized.")
#         return
#
#     try:
#         cred_path = Path("config/firebase/service-account.json")
#         if not cred_path.exists():
#             raise FileNotFoundError(f"Firebase credential not found: {cred_path}")
#
#         cred = credentials.Certificate(cred_path)
#         firebase_app = firebase_admin.initialize_app(cred)
#
#         logger.info("Firebase initialized successfully.")
#
#     except Exception as e:
#         logger.exception(f"Failed to initialize Firebase: {e}")
#         raise  # 앱 시작을 중단시킬지, soft fail할지는 상황에 따라 결정

def initialize_firebase():
    global firebase_app

    if firebase_admin._apps:
        logger.info("Firebase already initialized.")
        return

    try:
        cred_path = settings.GOOGLE_APPLICATION_CREDENTIALS

        if cred_path:  # 로컬: .env 파일 기반
            cred_path = Path(cred_path)
            if not cred_path.exists():
                raise FileNotFoundError(f"Firebase credential not found: {cred_path}")
            cred = credentials.Certificate(str(cred_path))
            firebase_app = firebase_admin.initialize_app(cred)
            logger.info("Firebase initialized with service account file.")
        else:  # GCP: ADC 기본 인증
            firebase_app = firebase_admin.initialize_app()
            logger.info("Firebase initialized with Application Default Credentials.")

    except Exception as e:
        logger.exception(f"Failed to initialize Firebase: {e}")
        raise

def verify_firebase_token(token: str):
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token  # dict containing uid, email, etc.
    except Exception as e:
        return None