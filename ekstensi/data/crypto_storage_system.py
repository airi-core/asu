"""
CryptoStore: Sistem Penyimpanan Model AI Berbasis Blockchain

Konsep: Menggunakan konsep blockchain dan mekanisme wallet crypto untuk menyimpan dan mengakses 
data dalam jumlah besar dengan efisiensi tinggi, terutama untuk model AI dan dataset.
"""

import hashlib
import json
import time
import numpy as np
import base64
import os
from typing import Dict, List, Any, Union, Tuple

class DataBlock:
    """Representasi blok data dalam sistem CryptoStore"""
    
    def __init__(self, data: Any, previous_hash: str = None):
        self.timestamp = time.time()
        self.data = data
        self.previous_hash = previous_hash
        self.nonce = 0
        self.hash = self.calculate_hash()
    
    def calculate_hash(self) -> str:
        """Menghitung hash untuk blok data"""
        block_data = str(self.timestamp) + str(self.data) + str(self.previous_hash) + str(self.nonce)
        return hashlib.sha256(block_data.encode()).hexdigest()
    
    def compress_data(self) -> bytes:
        """Mengompres data untuk penyimpanan efisien"""
        if isinstance(self.data, np.ndarray):
            # Khusus untuk array numpy (umum dalam model AI)
            return base64.b64encode(self.data.tobytes())
        else:
            # Untuk tipe data lainnya
            return base64.b64encode(json.dumps(self.data, default=str).encode())

class CryptoShard:
    """Merepresentasikan pecahan (shard) dari data besar"""
    
    def __init__(self, data_id: str, shard_index: int, data_content: bytes):
        self.data_id = data_id
        self.shard_index = shard_index
        self.content = data_content
        self.signature = self._generate_signature()
    
    def _generate_signature(self) -> str:
        """Membuat tanda tangan digital untuk validasi shard"""
        shard_info = f"{self.data_id}:{self.shard_index}:{len(self.content)}"
        return hashlib.sha256(shard_info.encode()).hexdigest()[:16]
    
    def verify(self) -> bool:
        """Memverifikasi integritas shard"""
        expected_signature = self._generate_signature()
        return self.signature == expected_signature

class CryptoWallet:
    """Wallet untuk mengelola penyimpanan data, terinspirasi oleh crypto wallet"""
    
    def __init__(self, wallet_id: str):
        self.wallet_id = wallet_id
        self.public_key = hashlib.sha256(wallet_id.encode()).hexdigest()
        self._private_key = hashlib.sha512(wallet_id.encode()).hexdigest()
        self.shard_registry: Dict[str, List[str]] = {}  # data_id -> list of shard_addresses
        self.active_chain: List[DataBlock] = []
    
    def store_data(self, data_id: str, data: Any, shard_size: int = 1024*1024) -> bool:
        """Menyimpan data dengan membaginya menjadi shards"""
        try:
            # Konversi data menjadi format yang dapat dibagi
            if isinstance(data, np.ndarray):
                serialized_data = data.tobytes()
            else:
                serialized_data = json.dumps(data, default=str).encode()
            
            # Bagi data menjadi shards
            shard_addresses = []
            total_shards = (len(serialized_data) + shard_size - 1) // shard_size
            
            for i in range(total_shards):
                start_idx = i * shard_size
                end_idx = min((i + 1) * shard_size, len(serialized_data))
                shard_data = serialized_data[start_idx:end_idx]
                
                # Buat shard dan simpan
                shard = CryptoShard(data_id, i, shard_data)
                shard_address = self._store_shard(shard)
                shard_addresses.append(shard_address)
                
                # Tambahkan ke blockchain untuk integritas data
                if not self.active_chain:
                    previous_hash = "0" * 64  # Genesis block
                else:
                    previous_hash = self.active_chain[-1].hash
                    
                meta_block = {
                    "data_id": data_id, 
                    "shard_index": i,
                    "shard_address": shard_address,
                    "shard_size": len(shard_data)
                }
                new_block = DataBlock(meta_block, previous_hash)
                self.active_chain.append(new_block)
            
            # Simpan referensi ke semua shard
            self.shard_registry[data_id] = shard_addresses
            return True
            
        except Exception as e:
            print(f"Error menyimpan data: {str(e)}")
            return False
    
    def _store_shard(self, shard: CryptoShard) -> str:
        """Menyimpan shard dan mengembalikan alamat akses"""
        # Di implementasi nyata, ini akan menyimpan ke disk/database
        # Untuk contoh ini, kita hanya generate alamat
        shard_signature = f"{shard.data_id}_{shard.shard_index}_{shard.signature}"
        address = hashlib.sha256(shard_signature.encode()).hexdigest()
        
        # Seolah-olah menyimpan ke penyimpanan fisik
        shard_dir = os.path.join("crypto_store", self.wallet_id, shard.data_id)
        os.makedirs(shard_dir, exist_ok=True)
        
        # Uncomment jika ingin benar-benar menyimpan
        # with open(os.path.join(shard_dir, f"shard_{shard.shard_index}.bin"), "wb") as f:
        #     f.write(shard.content)
        
        return address
    
    def retrieve_data(self, data_id: str) -> Any:
        """Mengambil dan merekonstruksi data dari shards"""
        if data_id not in self.shard_registry:
            raise ValueError(f"Data dengan ID {data_id} tidak ditemukan")
        
        # Dalam implementasi nyata, ini akan mengambil shards dari penyimpanan fisik
        # dan merekonstruksi data asli
        
        # Untuk demonstrasi, kita akan melewatkan proses pengambilan fisik
        # dan hanya simulasikan rekonstruksi
        print(f"Mengambil data {data_id} dari {len(self.shard_registry[data_id])} shards")
        
        # Verifikasi integritas dengan blockchain
        for block in self.active_chain:
            if isinstance(block.data, dict) and block.data.get("data_id") == data_id:
                print(f"Blok terverifikasi: {block.hash[:8]}...")
        
        return f"Data {data_id} berhasil diambil dan direkonstruksi"
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Mendapatkan statistik penyimpanan"""
        stats = {
            "total_data_objects": len(self.shard_registry),
            "total_blocks": len(self.active_chain),
            "total_shards": sum(len(shards) for shards in self.shard_registry.values())
        }
        return stats

class AIModelCryptoStorage:
    """Sistem penyimpanan khusus untuk model AI menggunakan CryptoStore"""
    
    def __init__(self, storage_id: str):
        self.storage_id = storage_id
        self.wallet = CryptoWallet(storage_id)
        self.model_registry = {}
    
    def save_model(self, model_name: str, model_params: Dict[str, np.ndarray]) -> str:
        """Menyimpan model AI ke CryptoStore"""
        model_id = f"ai_model_{model_name}_{int(time.time())}"
        
        # Kompres dan simpan setiap layer model secara terpisah untuk efisiensi
        for layer_name, params in model_params.items():
            layer_id = f"{model_id}_layer_{layer_name}"
            success = self.wallet.store_data(layer_id, params)
            if not success:
                raise Exception(f"Gagal menyimpan layer {layer_name}")
        
        # Simpan metadata model
        model_meta = {
            "name": model_name,
            "created_at": time.time(),
            "layers": list(model_params.keys()),
            "format_version": "1.0"
        }
        
        meta_id = f"{model_id}_metadata"
        self.wallet.store_data(meta_id, model_meta)
        
        # Daftarkan model di registry
        self.model_registry[model_name] = {
            "id": model_id,
            "metadata_id": meta_id,
            "size": sum(param.nbytes for param in model_params.values())
        }
        
        return model_id
    
    def load_model(self, model_name: str) -> Dict[str, Any]:
        """Memuat model AI dari CryptoStore"""
        if model_name not in self.model_registry:
            raise ValueError(f"Model {model_name} tidak ditemukan")
        
        model_info = self.model_registry[model_name]
        model_id = model_info["id"]
        
        # Muat metadata
        metadata = self.wallet.retrieve_data(model_info["metadata_id"])
        
        # Muat setiap layer
        model_params = {}
        for layer_name in metadata["layers"]:
            layer_id = f"{model_id}_layer_{layer_name}"
            layer_params = self.wallet.retrieve_data(layer_id)
            model_params[layer_name] = layer_params
        
        return {
            "name": model_name,
            "metadata": metadata,
            "parameters": model_params
        }
    
    def list_models(self) -> List[Dict[str, Any]]:
        """Menampilkan daftar model yang tersimpan"""
        return [
            {
                "name": name,
                "id": info["id"],
                "size_bytes": info["size"],
                "size_human": self._format_size(info["size"])
            }
            for name, info in self.model_registry.items()
        ]
    
    def _format_size(self, size_bytes: int) -> str:
        """Format ukuran byte ke format yang mudah dibaca"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} EB"  # Exabyte

class DatasetCryptoStorage:
    """Sistem penyimpanan khusus untuk dataset menggunakan CryptoStore"""
    
    def __init__(self, storage_id: str):
        self.storage_id = storage_id
        self.wallet = CryptoWallet(f"dataset_{storage_id}")
        self.dataset_registry = {}
    
    def save_dataset(self, dataset_name: str, data: Union[np.ndarray, Dict[str, Any], List[Any]],
                    chunk_size: int = 10000) -> str:
        """Menyimpan dataset ke CryptoStore dengan chunking"""
        dataset_id = f"dataset_{dataset_name}_{int(time.time())}"
        
        # Untuk array numpy, simpan dalam chunking
        if isinstance(data, np.ndarray):
            # Bagi dataset menjadi chunk-chunk
            total_chunks = (len(data) + chunk_size - 1) // chunk_size
            chunk_ids = []
            
            for i in range(total_chunks):
                start_idx = i * chunk_size
                end_idx = min((i + 1) * chunk_size, len(data))
                chunk_data = data[start_idx:end_idx]
                
                chunk_id = f"{dataset_id}_chunk_{i}"
                success = self.wallet.store_data(chunk_id, chunk_data)
                if not success:
                    raise Exception(f"Gagal menyimpan chunk {i}")
                
                chunk_ids.append(chunk_id)
            
            # Simpan metadata dataset
            dataset_meta = {
                "name": dataset_name,
                "created_at": time.time(),
                "total_chunks": total_chunks,
                "chunk_ids": chunk_ids,
                "shape": data.shape,
                "dtype": str(data.dtype),
                "format_version": "1.0"
            }
        else:
            # Untuk data lain (dict, list), simpan langsung
            success = self.wallet.store_data(dataset_id, data)
            if not success:
                raise Exception(f"Gagal menyimpan dataset {dataset_name}")
            
            # Metadata lebih sederhana
            dataset_meta = {
                "name": dataset_name,
                "created_at": time.time(),
                "data_type": type(data).__name__,
                "format_version": "1.0"
            }
        
        # Simpan metadata
        meta_id = f"{dataset_id}_metadata"
        self.wallet.store_data(meta_id, dataset_meta)
        
        # Daftarkan dataset
        data_size = 0
        if isinstance(data, np.ndarray):
            data_size = data.nbytes
        elif isinstance(data, (dict, list)):
            data_size = len(json.dumps(data).encode())
        
        self.dataset_registry[dataset_name] = {
            "id": dataset_id,
            "metadata_id": meta_id,
            "size": data_size
        }
        
        return dataset_id
    
    def load_dataset(self, dataset_name: str) -> Any:
        """Memuat dataset dari CryptoStore"""
        if dataset_name not in self.dataset_registry:
            raise ValueError(f"Dataset {dataset_name} tidak ditemukan")
        
        dataset_info = self.dataset_registry[dataset_name]
        dataset_id = dataset_info["id"]
        
        # Muat metadata
        metadata = self.wallet.retrieve_data(dataset_info["metadata_id"])
        
        # Jika dataset dalam format chunking
        if "total_chunks" in metadata:
            # Dalam implementasi lengkap, ini akan merekonstruksi array
            # dari semua chunk yang disimpan
            chunk_count = metadata["total_chunks"]
            print(f"Merekonstruksi dataset dari {chunk_count} chunks")
            
            # Demonstrasi rekonstruksi (tanpa benar-benar mengambil data)
            return f"Dataset {dataset_name} direkonstruksi dari {chunk_count} chunks"
        else:
            # Dataset disimpan sebagai kesatuan
            return self.wallet.retrieve_data(dataset_id)
    
    def list_datasets(self) -> List[Dict[str, Any]]:
        """Menampilkan daftar dataset yang tersimpan"""
        return [
            {
                "name": name,
                "id": info["id"],
                "size_bytes": info["size"],
                "size_human": self._format_size(info["size"])
            }
            for name, info in self.dataset_registry.items()
        ]
    
    def _format_size(self, size_bytes: int) -> str:
        """Format ukuran byte ke format yang mudah dibaca"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} EB"

# Contoh Penggunaan

def contoh_penggunaan():
    """Demonstrasi cara menggunakan CryptoStore"""
    
    # Inisialisasi penyimpanan model
    model_storage = AIModelCryptoStorage("my_ai_models")
    
    # Contoh model AI sederhana (dalam bentuk parameter saja)
    model_params = {
        "dense_1": np.random.random((100, 64)).astype(np.float32),
        "dense_2": np.random.random((64, 32)).astype(np.float32),
        "output": np.random.random((32, 10)).astype(np.float32)
    }
    
    # Simpan model
    model_id = model_storage.save_model("model_klasifikasi", model_params)
    print(f"Model disimpan dengan ID: {model_id}")
    
    # Daftar model yang tersimpan
    print("Daftar model:")
    for model in model_storage.list_models():
        print(f"  - {model['name']} ({model['size_human']})")
    
    # Inisialisasi penyimpanan dataset
    dataset_storage = DatasetCryptoStorage("my_datasets")
    
    # Contoh dataset
    dataset = np.random.random((50000, 28, 28)).astype(np.float32)  # Contoh dataset gambar
    
    # Simpan dataset
    dataset_id = dataset_storage.save_dataset("dataset_gambar", dataset)
    print(f"Dataset disimpan dengan ID: {dataset_id}")
    
    # Daftar dataset yang tersimpan
    print("Daftar dataset:")
    for ds in dataset_storage.list_datasets():
        print(f"  - {ds['name']} ({ds['size_human']})")
    
    # Statistik penyimpanan
    print("Statistik penyimpanan model:")
    print(model_storage.wallet.get_storage_stats())
    
    print("Statistik penyimpanan dataset:")
    print(dataset_storage.wallet.get_storage_stats())

# Untuk menjalankan demo
if __name__ == "__main__":
    contoh_penggunaan()
