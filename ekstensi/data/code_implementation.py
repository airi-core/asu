# model_vm.py
import subprocess
import json
import os
import requests
import uuid
import firebase_admin
from firebase_admin import credentials, storage, firestore
from dotenv import load_dotenv

load_dotenv()

# Inisialisasi Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate(os.getenv('FIREBASE_SERVICE_ACCOUNT'))
    firebase_admin.initialize_app(cred, {
        'storageBucket': os.getenv('FIREBASE_STORAGE_BUCKET')
    })

db = firestore.client()
bucket = storage.bucket()

class ModelVM:
    """
    Virtual Machine untuk menjalankan model AI sebagai smart contract
    """
    def __init__(self, model_id=None):
        """
        Inisialisasi VM untuk model
        
        Args:
            model_id: ID unik untuk model, jika None akan digenerate
        """
        self.model_id = model_id or str(uuid.uuid4())
        self.container_id = None
        self.container_status = "not_created"
        self.endpoint = None
        self.storage_path = f"models/{self.model_id}"
        self.resource_limits = {
            "cpu": os.getenv("VM_CPU_LIMIT", "1"),
            "memory": os.getenv("VM_MEMORY_LIMIT", "2g")
        }
    
    def save_model(self, model_data):
        """
        Menyimpan model AI ke Firebase Storage
        
        Args:
            model_data: Data model yang akan disimpan
            
        Returns:
            storage_path: Path ke model di storage
        """
        try:
            # Simpan model sebagai file sementara
            temp_path = f"/tmp/{self.model_id}_model.json"
            with open(temp_path, 'w') as f:
                json.dump(model_data, f)
            
            # Upload ke Firebase Storage
            model_blob = bucket.blob(f"{self.storage_path}/model.json")
            model_blob.upload_from_filename(temp_path)
            
            # Hapus file sementara
            os.remove(temp_path)
            
            # Update metadata di Firestore
            db.collection('models').document(self.model_id).set({
                'storage_path': f"{self.storage_path}/model.json",
                'status': 'stored',
                'created_at': firestore.SERVER_TIMESTAMP
            }, merge=True)
            
            return f"{self.storage_path}/model.json"
        
        except Exception as e:
            print(f"Error saving model: {e}")
            raise
    
    def create_container(self):
        """
        Membuat container Docker untuk menjalankan model
        
        Returns:
            container_id: ID dari container yang dibuat
        """
        try:
            # Buat Docker container dengan resource limits
            container_name = f"model-{self.model_id}"
            
            cmd = [
                "docker", "run", "-d",
                "--cpus", self.resource_limits["cpu"],
                "--memory", self.resource_limits["memory"],
                "--name", container_name,
                "-e", f"MODEL_ID={self.model_id}",
                "-e", f"FIREBASE_STORAGE_PATH={self.storage_path}",
                "-p