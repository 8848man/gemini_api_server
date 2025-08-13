import os
import json
import firebase_admin
from firebase_admin import credentials, auth
from pathlib import Path
import logging
from src.core.config import get_settings  # Settings 불러오기

logger = logging.getLogger(__name__)
settings = get_settings()

firebase_app = None

def initialize_firebase():
    global firebase_app

    if firebase_admin._apps:
        logger.info("Firebase already initialized.")
        return

    try:
        firebase_key_json = os.getenv("FIREBASE_KEY_JSON", "").strip()
        if firebase_key_json:
            logger.info("Initializing Firebase Admin SDK with JSON string from environment variable.")
            key_info = json.loads(firebase_key_json)
            cred = credentials.Certificate(key_info)
            firebase_app = firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin initialized from environment variable JSON.")
        else:
            cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            logger.info(f"Firebase credential path: {cred_path}")

            if cred_path:
                cred_path = Path(cred_path)
                if not cred_path.exists():
                    raise FileNotFoundError(f"Firebase credential not found: {cred_path}")
                cred = credentials.Certificate(str(cred_path))
                firebase_app = firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin initialized with service account file.")
            else:
                firebase_app = firebase_admin.initialize_app()
                logger.info("Firebase Admin initialized with Application Default Credentials.")

        return firebase_app

    except Exception as e:
        logger.exception(f"Failed to initialize Firebase: {e}")
        raise

def verify_firebase_token(token: str):
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token  # dict containing uid, email, etc.
    except Exception as e:
        return None