#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI GENERATIF STANDARD INDUSTRI
================================
Script Python untuk AI Generatif yang sesuai standard industri
dengan integrasi Together AI dan Google Drive

Author: AI Assistant
Version: 1.0.0
License: MIT

DIAGRAM ALUR ARSITEKTUR:
========================

[USER INPUT] 
    ↓
[VALIDASI & SANITASI]
    ↓
[FILTER KEAMANAN]
    ↓
[PREPROCESSING]
    ↓
[TOGETHER AI API]
    ↓
[POSTPROCESSING]
    ↓
[VALIDASI OUTPUT]
    ↓
[SAVE TO GOOGLE DRIVE]
    ↓
[RETURN FILE PATH]

KOMPONEN UTAMA:
===============
1. Input Handler & Validator
2. Security Filter
3. Content Moderator  
4. AI Model Interface (Together AI)
5. Output Processor
6. File Manager (Google Drive)
7. Logging & Monitoring
8. Error Handler
"""

import os
import json
import logging
import hashlib
import re
from datetime import datetime
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass
from enum import Enum
import requests
import time
from pathlib import Path

# Konfigurasi Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ai_generatif.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class OutputFormat(Enum):
    """Format output yang didukung"""
    TEXT = "txt"
    JSON = "json"
    MARKDOWN = "md"
    HTML = "html"
    CSV = "csv"
    XML = "xml"

class SecurityLevel(Enum):
    """Level keamanan konten"""
    SAFE = "safe"
    MODERATE = "moderate"
    UNSAFE = "unsafe"

@dataclass
class AIConfig:
    """Konfigurasi AI Model"""
    api_key: str
    model_name: str
    temperature: float = 0.7
    max_tokens: int = 2048
    top_p: float = 0.9
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0

@dataclass
class UserRequest:
    """Struktur permintaan user"""
    user_id: str
    prompt: str
    output_format: OutputFormat
    additional_params: Dict[str, Any]
    timestamp: datetime

class ContentModerator:
    """Moderator konten untuk keamanan"""
    
    def __init__(self):
        # Daftar kata/frasa yang dilarang (contoh dasar)
        self.forbidden_patterns = [
            r'\b(hack|crack|exploit)\b',
            r'\b(virus|malware|trojan)\b',
            r'\b(bomb|weapon|violence)\b',
            r'\b(illegal|criminal|fraud)\b',
            # Tambahkan pattern lain sesuai kebutuhan
        ]
        
        # Pattern untuk informasi pribadi
        self.pii_patterns = [
            r'\b\d{16}\b',  # Credit card
            r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
        ]
    
    def check_content_safety(self, content: str) -> SecurityLevel:
        """Periksa keamanan konten"""
        content_lower = content.lower()
        
        # Periksa konten terlarang
        for pattern in self.forbidden_patterns:
            if re.search(pattern, content_lower, re.IGNORECASE):
                logger.warning(f"Konten tidak aman terdeteksi: {pattern}")
                return SecurityLevel.UNSAFE
        
        # Periksa informasi pribadi
        for pattern in self.pii_patterns:
            if re.search(pattern, content):
                logger.warning("Informasi pribadi terdeteksi")
                return SecurityLevel.MODERATE
        
        return SecurityLevel.SAFE
    
    def sanitize_input(self, content: str) -> str:
        """Bersihkan input dari karakter berbahaya"""
        # Hapus karakter kontrol
        sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', content)
        
        # Batasi panjang input
        if len(sanitized) > 10000:
            sanitized = sanitized[:10000]
            logger.warning("Input dipotong karena terlalu panjang")
        
        return sanitized.strip()

class TogetherAIClient:
    """Client untuk Together AI API"""
    
    def __init__(self, config: AIConfig):
        self.config = config
        self.base_url = "https://api.together.xyz/v1"
        self.headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json"
        }
        self.rate_limit_delay = 1.0  # detik
        self.last_request_time = 0
    
    def _rate_limit(self):
        """Implementasi rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - time_since_last)
        
        self.last_request_time = time.time()
    
    def generate_content(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate konten menggunakan Together AI"""
        self._rate_limit()
        
        payload = {
            "model": self.config.model_name,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "top_p": self.config.top_p,
            "frequency_penalty": self.config.frequency_penalty,
            "presence_penalty": self.config.presence_penalty,
            **kwargs
        }
        
        try:
            logger.info(f"Mengirim request ke Together AI dengan model: {self.config.model_name}")
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=60
            )
            
            response.raise_for_status()
            result = response.json()
            
            logger.info("Response berhasil diterima dari Together AI")
            return {
                "success": True,
                "content": result["choices"][0]["message"]["content"],
                "usage": result.get("usage", {}),
                "model": result.get("model", self.config.model_name)
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error saat request ke Together AI: {e}")
            return {
                "success": False,
                "error": str(e),
                "content": None
            }
        except Exception as e:
            logger.error(f"Error tidak terduga: {e}")
            return {
                "success": False,
                "error": str(e),
                "content": None
            }

class OutputProcessor:
    """Processor untuk berbagai format output"""
    
    @staticmethod
    def format_content(content: str, output_format: OutputFormat) -> str:
        """Format konten sesuai format yang diminta"""
        if output_format == OutputFormat.TEXT:
            return content
        
        elif output_format == OutputFormat.JSON:
            return json.dumps({
                "generated_content": content,
                "timestamp": datetime.now().isoformat(),
                "format": "json"
            }, indent=2, ensure_ascii=False)
        
        elif output_format == OutputFormat.MARKDOWN:
            return f"""# Generated Content

**Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Content

{content}

---
*Generated by AI Generatif Standard Industri*
"""
        
        elif output_format == OutputFormat.HTML:
            return f"""<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Generated Content</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f0f0f0; padding: 10px; border-radius: 5px; }}
        .content {{ margin-top: 20px; line-height: 1.6; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Generated Content</h1>
        <p><strong>Timestamp:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
    <div class="content">
        {content.replace(chr(10), '<br>')}
    </div>
</body>
</html>"""
        
        elif output_format == OutputFormat.CSV:
            return f"""timestamp,content
"{datetime.now().isoformat()}","{content.replace('"', '""')}"
"""
        
        elif output_format == OutputFormat.XML:
            return f"""<?xml version="1.0" encoding="UTF-8"?>
<generated_content>
    <timestamp>{datetime.now().isoformat()}</timestamp>
    <content><![CDATA[{content}]]></content>
</generated_content>"""
        
        else:
            return content

class FileManager:
    """Manager untuk operasi file dan Google Drive"""
    
    def __init__(self, google_drive_path: str = "/content/drive/MyDrive/AI_Output"):
        self.drive_path = Path(google_drive_path)
        self.ensure_directory_exists()
    
    def ensure_directory_exists(self):
        """Pastikan direktori output ada"""
        try:
            self.drive_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Direktori output siap: {self.drive_path}")
        except Exception as e:
            logger.error(f"Error membuat direktori: {e}")
            # Fallback ke direktori lokal
            self.drive_path = Path("./output")
            self.drive_path.mkdir(parents=True, exist_ok=True)
    
    def generate_filename(self, user_id: str, output_format: OutputFormat) -> str:
        """Generate nama file unik"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        user_hash = hashlib.md5(user_id.encode()).hexdigest()[:8]
        return f"ai_output_{user_hash}_{timestamp}.{output_format.value}"
    
    def save_file(self, content: str, filename: str) -> Dict[str, Any]:
        """Simpan file ke Google Drive"""
        try:
            file_path = self.drive_path / filename
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"File berhasil disimpan: {file_path}")
            
            return {
                "success": True,
                "file_path": str(file_path),
                "filename": filename,
                "size": len(content.encode('utf-8'))
            }
            
        except Exception as e:
            logger.error(f"Error menyimpan file: {e}")
            return {
                "success": False,
                "error": str(e),
                "file_path": None
            }

class AIGeneratifSystem:
    """Sistem AI Generatif Standard Industri"""
    
    def __init__(self, 
                 together_api_key: str,
                 model_name: str = "meta-llama/Llama-2-7b-chat-hf",
                 temperature: float = 0.7,
                 google_drive_path: str = "/content/drive/MyDrive/AI_Output"):
        
        # Inisialisasi komponen sistem
        self.config = AIConfig(
            api_key=together_api_key,
            model_name=model_name,
            temperature=temperature
        )
        
        self.content_moderator = ContentModerator()
        self.ai_client = TogetherAIClient(self.config)
        self.output_processor = OutputProcessor()
        self.file_manager = FileManager(google_drive_path)
        
        # Statistik sistem
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "blocked_requests": 0,
            "errors": 0
        }
        
        logger.info("AI Generatif System berhasil diinisialisasi")
    
    def process_request(self, user_request: UserRequest) -> Dict[str, Any]:
        """
        Proses permintaan user sesuai alur arsitektur:
        1. Validasi & Sanitasi
        2. Filter Keamanan
        3. Preprocessing
        4. Together AI API
        5. Postprocessing
        6. Validasi Output
        7. Save to Google Drive
        8. Return File Path
        """
        
        self.stats["total_requests"] += 1
        request_id = hashlib.md5(f"{user_request.user_id}_{user_request.timestamp}".encode()).hexdigest()[:12]
        
        logger.info(f"[{request_id}] Memproses permintaan dari user: {user_request.user_id}")
        
        try:
            # STEP 1: Validasi & Sanitasi
            logger.info(f"[{request_id}] Step 1: Validasi & Sanitasi")
            sanitized_prompt = self.content_moderator.sanitize_input(user_request.prompt)
            
            if not sanitized_prompt:
                self.stats["blocked_requests"] += 1
                return {
                    "success": False,
                    "error": "Prompt kosong setelah sanitasi",
                    "request_id": request_id
                }
            
            # STEP 2: Filter Keamanan
            logger.info(f"[{request_id}] Step 2: Filter Keamanan")
            security_level = self.content_moderator.check_content_safety(sanitized_prompt)
            
            if security_level == SecurityLevel.UNSAFE:
                self.stats["blocked_requests"] += 1
                return {
                    "success": False,
                    "error": "Konten tidak aman terdeteksi",
                    "request_id": request_id
                }
            
            # STEP 3: Preprocessing
            logger.info(f"[{request_id}] Step 3: Preprocessing")
            processed_prompt = self._preprocess_prompt(sanitized_prompt, user_request.additional_params)
            
            # STEP 4: Together AI API
            logger.info(f"[{request_id}] Step 4: Together AI API")
            ai_response = self.ai_client.generate_content(processed_prompt)
            
            if not ai_response["success"]:
                self.stats["errors"] += 1
                return {
                    "success": False,
                    "error": f"AI API Error: {ai_response['error']}",
                    "request_id": request_id
                }
            
            # STEP 5: Postprocessing
            logger.info(f"[{request_id}] Step 5: Postprocessing")
            processed_content = self._postprocess_content(ai_response["content"])
            
            # STEP 6: Validasi Output
            logger.info(f"[{request_id}] Step 6: Validasi Output")
            output_security = self.content_moderator.check_content_safety(processed_content)
            
            if output_security == SecurityLevel.UNSAFE:
                self.stats["blocked_requests"] += 1
                return {
                    "success": False,
                    "error": "Output tidak aman terdeteksi",
                    "request_id": request_id
                }
            
            # STEP 7: Format Output
            logger.info(f"[{request_id}] Step 7: Format Output")
            formatted_content = self.output_processor.format_content(
                processed_content, 
                user_request.output_format
            )
            
            # STEP 8: Save to Google Drive
            logger.info(f"[{request_id}] Step 8: Save to Google Drive")
            filename = self.file_manager.generate_filename(
                user_request.user_id, 
                user_request.output_format
            )
            
            save_result = self.file_manager.save_file(formatted_content, filename)
            
            if not save_result["success"]:
                self.stats["errors"] += 1
                return {
                    "success": False,
                    "error": f"Error menyimpan file: {save_result['error']}",
                    "request_id": request_id
                }
            
            # STEP 9: Return Result
            self.stats["successful_requests"] += 1
            
            result = {
                "success": True,
                "request_id": request_id,
                "file_path": save_result["file_path"],
                "filename": save_result["filename"],
                "file_size": save_result["size"],
                "output_format": user_request.output_format.value,
                "security_level": security_level.value,
                "ai_usage": ai_response.get("usage", {}),
                "processing_time": (datetime.now() - user_request.timestamp).total_seconds(),
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"[{request_id}] Request berhasil diproses: {save_result['file_path']}")
            return result
            
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"[{request_id}] Error tidak terduga: {e}")
            return {
                "success": False,
                "error": f"Error sistem: {str(e)}",
                "request_id": request_id
            }
    
    def _preprocess_prompt(self, prompt: str, additional_params: Dict[str, Any]) -> str:
        """Preprocessing prompt sebelum dikirim ke AI"""
        # Tambahkan context atau instruksi khusus jika diperlukan
        processed = prompt
        
        # Tambahkan parameter tambahan ke prompt jika ada
        if additional_params:
            context = "\n".join([f"{k}: {v}" for k, v in additional_params.items()])
            processed = f"Context: {context}\n\nPrompt: {processed}"
        
        return processed
    
    def _postprocess_content(self, content: str) -> str:
        """Postprocessing konten dari AI"""
        # Bersihkan output dari karakter yang tidak diinginkan
        processed = content.strip()
        
        # Hapus markup atau format yang tidak diinginkan
        processed = re.sub(r'<[^>]+>', '', processed)  # Remove HTML tags
        
        return processed
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Dapatkan statistik sistem"""
        return {
            **self.stats,
            "success_rate": (self.stats["successful_requests"] / max(1, self.stats["total_requests"])) * 100,
            "config": {
                "model": self.config.model_name,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens
            }
        }

# ============================================================================
# FUNGSI UTAMA DAN CONTOH PENGGUNAAN
# ============================================================================

def create_ai_system(api_key: str, 
                    model_name: str = "meta-llama/Llama-2-7b-chat-hf",
                    temperature: float = 0.7,
                    google_drive_path: str = "/content/drive/MyDrive/AI_Output") -> AIGeneratifSystem:
    """Factory function untuk membuat AI system"""
    return AIGeneratifSystem(
        together_api_key=api_key,
        model_name=model_name,
        temperature=temperature,
        google_drive_path=google_drive_path
    )

def process_user_request(ai_system: AIGeneratifSystem,
                        user_id: str,
                        prompt: str,
                        output_format: str = "txt",
                        **additional_params) -> Dict[str, Any]:
    """Helper function untuk memproses request user"""
    
    # Konversi string format ke enum
    try:
        format_enum = OutputFormat(output_format.lower())
    except ValueError:
        return {
            "success": False,
            "error": f"Format output tidak didukung: {output_format}. Gunakan: {', '.join([f.value for f in OutputFormat])}"
        }
    
    # Buat user request
    user_request = UserRequest(
        user_id=user_id,
        prompt=prompt,
        output_format=format_enum,
        additional_params=additional_params,
        timestamp=datetime.now()
    )
    
    # Proses request
    return ai_system.process_request(user_request)

# ============================================================================
# CONTOH PENGGUNAAN
# ============================================================================

if __name__ == "__main__":
    # KONFIGURASI - GANTI DENGAN API KEY DAN MODEL ANDA
    TOGETHER_API_KEY = "your_together_ai_api_key_here"  # Ganti dengan API Key Anda
    MODEL_NAME = "meta-llama/Llama-2-7b-chat-hf"       # Ganti dengan model yang diinginkan
    TEMPERATURE = 0.7                                    # Sesuaikan temperature
    GOOGLE_DRIVE_PATH = "/content/drive/MyDrive/AI_Output"  # Path Google Drive Anda
    
    print("🚀 Memulai AI Generatif Standard Industri")
    print("=" * 50)
    
    try:
        # Inisialisasi sistem AI
        ai_system = create_ai_system(
            api_key=TOGETHER_API_KEY,
            model_name=MODEL_NAME,
            temperature=TEMPERATURE,
            google_drive_path=GOOGLE_DRIVE_PATH
        )
        
        print("✅ Sistem AI berhasil diinisialisasi")
        
        # Contoh penggunaan
        test_requests = [
            {
                "user_id": "user_001",
                "prompt": "Tulis artikel tentang teknologi AI dalam bahasa Indonesia",
                "output_format": "markdown",
                "topic": "AI Technology",
                "language": "Indonesian"
            },
            {
                "user_id": "user_002", 
                "prompt": "Buat ringkasan tentang manfaat renewable energy",
                "output_format": "json",
                "category": "Environment"
            }
        ]
        
        # Proses setiap request
        for i, req in enumerate(test_requests, 1):
            print(f"\n📝 Memproses Request {i}")
            print("-" * 30)
            
            result = process_user_request(
                ai_system=ai_system,
                user_id=req["user_id"],
                prompt=req["prompt"],
                output_format=req["output_format"],
                **{k: v for k, v in req.items() if k not in ["user_id", "prompt", "output_format"]}
            )
            
            if result["success"]:
                print(f"✅ Request berhasil diproses")
                print(f"📁 File disimpan di: {result['file_path']}")
                print(f"📊 Ukuran file: {result['file_size']} bytes")
                print(f"⏱️ Waktu proses: {result['processing_time']:.2f} detik")
            else:
                print(f"❌ Request gagal: {result['error']}")
        
        # Tampilkan statistik sistem
        print(f"\n📊 Statistik Sistem")
        print("=" * 30)
        stats = ai_system.get_system_stats()
        for key, value in stats.items():
            if isinstance(value, dict):
                print(f"{key}:")
                for k, v in value.items():
                    print(f"  {k}: {v}")
            else:
                print(f"{key}: {value}")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        logger.error(f"Error dalam main: {e}")

# ============================================================================
# DOKUMENTASI INTEGRASI
# ============================================================================

"""
LANGKAH-LANGKAH INTEGRASI:

1. PERSIAPAN ENVIRONMENT:
   pip install requests pathlib

2. KONFIGURASI API:
   - Daftar di Together AI (https://api.together.xyz/)
   - Dapatkan API Key
   - Pilih model yang diinginkan

3. SETUP GOOGLE DRIVE:
   - Mount Google Drive di Colab: 
     from google.colab import drive
     drive.mount('/content/drive')
   - Atau setup Google Drive API untuk production

4. KONFIGURASI SCRIPT:
   - Ganti TOGETHER_API_KEY dengan API key Anda
   - Sesuaikan MODEL_NAME dengan model pilihan
   - Atur TEMPERATURE sesuai kebutuhan (0.0-1.0)
   - Set GOOGLE_DRIVE_PATH ke folder yang diinginkan

5. PENGGUNAAN:
   - Import module: from ai_generatif import create_ai_system, process_user_request
   - Inisialisasi sistem: ai_system = create_ai_system(api_key="your_key")
   - Proses request: result = process_user_request(ai_system, user_id, prompt, format)

6. MONITORING:
   - Cek log file: ai_generatif.log
   - Monitor statistik: ai_system.get_system_stats()
   - Setup alerting untuk error handling

7. PRODUCTION DEPLOYMENT:
   - Tambahkan database untuk logging
   - Implementasi caching
   - Setup load balancing
   - Tambahkan monitoring dan alerting
   - Implementasi rate limiting per user
   - Setup backup dan recovery

CONTOH MODEL TOGETHER AI YANG POPULER:
- meta-llama/Llama-2-7b-chat-hf
- meta-llama/Llama-2-13b-chat-hf
- meta-llama/Llama-2-70b-chat-hf
- mistralai/Mixtral-8x7B-Instruct-v0.1
- NousResearch/Nous-Hermes-2-Mixtral-8x7B-DPO

CATATAN KEAMANAN:
- Semua input dan output difilter untuk keamanan
- Informasi pribadi akan dideteksi dan ditangani
- Konten berbahaya akan diblokir
- Rate limiting diterapkan untuk mencegah abuse
- Logging lengkap untuk audit trail
"""