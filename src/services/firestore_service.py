from google.cloud import firestore

class FirestoreService:
    def __init__(self):
        self.client = firestore.AsyncClient()  # 비동기 클라이언트

    async def get_word_data(self, word: str) -> dict | None:
        doc_ref = self.client.collection('master_voca').document(word)
        doc = await doc_ref.get()
        if doc.exists:
            return doc.to_dict()
        return None

    async def save_word_data(self, word: str, data: dict):
        doc_ref = self.client.collection('master_voca').document(word)
        await doc_ref.set(data)

firestore_service = FirestoreService()