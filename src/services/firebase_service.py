import firebase_admin
from firebase_admin import credentials, auth
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

firebase_app = None


def initialize_firebase():
    global firebase_app

    if firebase_admin._apps:
        logger.info("Firebase already initialized.")
        return

    try:
        cred_path = Path("config/firebase/service-account.json")
        if not cred_path.exists():
            raise FileNotFoundError(f"Firebase credential not found: {cred_path}")

        cred = credentials.Certificate(cred_path)
        firebase_app = firebase_admin.initialize_app(cred)

        logger.info("Firebase initialized successfully.")

    except Exception as e:
        logger.exception(f"Failed to initialize Firebase: {e}")
        raise  # 앱 시작을 중단시킬지, soft fail할지는 상황에 따라 결정

def verify_firebase_token(token: str):
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token  # dict containing uid, email, etc.
    except Exception as e:
        return None