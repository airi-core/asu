#!/usr/bin/env python3
"""
AI Generatif Production Ready
Standar Industri untuk Penanganan User Request
Bahasa Indonesia - Siap Produksi

Arsitektur:
User Input → Validasi → Preprocessing → AI Model → Postprocessing → Output File → Google Drive

Author: Assistant
Version: 1.0
"""

import os
import json
import logging
import requests
import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import uuid
from pathlib import Path

# ================================
# KONSTANTA KONFIGURASI SISTEM
# ================================

class ModelConfig:
    """Konfigurasi Model AI - Isi sesuai kebutuhan"""
    TOGETHER_AI_API_KEY = "YOUR_TOGETHER_AI_API_KEY"  # Ganti dengan API key Anda
    MODEL_NAME = "YOUR_MODEL_NAME"  # contoh: "mistralai/Mixtral-8x7B-Instruct-v0.1"
    TEMPERATURE = 0.7  # Nilai 0.0-1.0 untuk kreativitas output
    MAX_TOKENS = 2048
    BASE_URL = "https://api.together.xyz/v1/chat/completions"

class PathConfig:
    """Konfigurasi Path Google Drive - Sesuaikan dengan struktur Anda"""
    GDRIVE_INPUT_PATH = "/path/to/gdrive/input/"  # Path input di Google Drive
    GDRIVE_OUTPUT_PATH = "/path/to/gdrive/output/"  # Path output di Google Drive
    LOCAL_TEMP_PATH = "./temp/"  # Path sementara lokal
    LOG_PATH = "./logs/"

class FileFormat(Enum):
    """Format file yang didukung sistem"""
    TXT = "txt"
    JSON = "json"
    CSV = "csv"
    MD = "md"
    HTML = "html"

# ================================
# DATA CLASSES & MODELS
# ================================

@dataclass
class UserRequest:
    """Model untuk request user"""
    user_id: str
    request_id: str
    prompt: str
    output_format: FileFormat
    max_length: Optional[int] = None
    custom_params: Optional[Dict] = None
    timestamp: datetime.datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.datetime.now()

@dataclass
class AIResponse:
    """Model untuk response AI"""
    request_id: str
    content: str
    metadata: Dict[str, Any]
    file_path: str
    status: str
    processing_time: float

# ================================
# LOGGING SETUP
# ================================

class LogManager:
    """Manager untuk logging sistem"""
    
    @staticmethod
    def setup_logging():
        """Setup konfigurasi logging"""
        os.makedirs(PathConfig.LOG_PATH, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'{PathConfig.LOG_PATH}/ai_generatif.log'),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger(__name__)

# ================================
# VALIDASI & KEAMANAN
# ================================

class SecurityValidator:
    """Validator untuk keamanan input"""
    
    FORBIDDEN_KEYWORDS = [
        'import os', 'import sys', 'exec(', 'eval(',
        'subprocess', '__import__', 'open(', 'file(',
        'delete', 'remove', 'rm -rf', 'format c:',
        'hack', 'exploit', 'malware', 'virus'
    ]
    
    SENSITIVE_PATTERNS = [
        r'\b\d{16}\b',  # Credit card pattern
        r'\b\d{3}-\d{2}-\d{4}\b',  # SSN pattern
        r'password\s*[:=]\s*\S+',  # Password pattern
    ]
    
    @classmethod
    def validate_input(cls, prompt: str) -> Dict[str, Any]:
        """Validasi keamanan input user"""
        issues = []
        
        # Check forbidden keywords
        prompt_lower = prompt.lower()
        for keyword in cls.FORBIDDEN_KEYWORDS:
            if keyword in prompt_lower:
                issues.append(f"Kata kunci terlarang ditemukan: {keyword}")
        
        # Check sensitive patterns
        import re
        for pattern in cls.SENSITIVE_PATTERNS:
            if re.search(pattern, prompt, re.IGNORECASE):
                issues.append("Pola data sensitif terdeteksi")
        
        # Length validation
        if len(prompt) > 10000:
            issues.append("Input terlalu panjang (maksimal 10000 karakter)")
        
        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
            "sanitized_prompt": cls._sanitize_prompt(prompt) if len(issues) == 0 else ""
        }
    
    @staticmethod
    def _sanitize_prompt(prompt: str) -> str:
        """Sanitasi prompt untuk keamanan"""
        # Basic HTML escape
        prompt = prompt.replace('<', '&lt;').replace('>', '&gt;')
        # Remove potential script injections
        prompt = prompt.replace('javascript:', '').replace('data:', '')
        return prompt.strip()

# ================================
# AI MODEL HANDLER
# ================================

class TogetherAIHandler:
    """Handler untuk Together AI API"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.api_key = ModelConfig.TOGETHER_AI_API_KEY
        self.base_url = ModelConfig.BASE_URL
    
    def generate_content(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate content menggunakan Together AI"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": ModelConfig.MODEL_NAME,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": kwargs.get('temperature', ModelConfig.TEMPERATURE),
                "max_tokens": kwargs.get('max_tokens', ModelConfig.MAX_TOKENS),
                "top_p": kwargs.get('top_p', 0.9),
                "repetition_penalty": kwargs.get('repetition_penalty', 1.1)
            }
            
            self.logger.info(f"Mengirim request ke Together AI: {ModelConfig.MODEL_NAME}")
            
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                return {
                    "success": True,
                    "content": content,
                    "usage": result.get('usage', {}),
                    "model": result.get('model', ModelConfig.MODEL_NAME)
                }
            else:
                self.logger.error(f"API Error: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": f"API Error: {response.status_code}",
                    "content": ""
                }
                
        except Exception as e:
            self.logger.error(f"Error dalam generate_content: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "content": ""
            }

# ================================
# FILE HANDLER
# ================================

class FileHandler:
    """Handler untuk operasi file"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        os.makedirs(PathConfig.LOCAL_TEMP_PATH, exist_ok=True)
    
    def save_content(self, content: str, format_type: FileFormat, filename: str) -> str:
        """Simpan content ke file sesuai format"""
        try:
            file_path = os.path.join(PathConfig.LOCAL_TEMP_PATH, f"{filename}.{format_type.value}")
            
            if format_type == FileFormat.JSON:
                # Coba parse sebagai JSON
                try:
                    json_data = json.loads(content)
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(json_data, f, indent=2, ensure_ascii=False)
                except json.JSONDecodeError:
                    # Jika bukan JSON valid, simpan sebagai JSON string
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump({"content": content}, f, indent=2, ensure_ascii=False)
            
            elif format_type == FileFormat.CSV:
                # Basic CSV handling
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            elif format_type == FileFormat.HTML:
                # HTML dengan template basic
                html_content = f"""<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Generated Content</title>
</head>
<body>
    <div style="max-width: 800px; margin: 0 auto; padding: 20px;">
        <h1>Konten yang Dihasilkan AI</h1>
        <div style="white-space: pre-wrap;">{content}</div>
    </div>
</body>
</html>"""
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
            
            else:  # TXT, MD, dan format lainnya
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            self.logger.info(f"File berhasil disimpan: {file_path}")
            return file_path
            
        except Exception as e:
            self.logger.error(f"Error menyimpan file: {str(e)}")
            raise

# ================================
# MAIN PROCESSOR
# ================================

class AIContentProcessor:
    """Processor utama untuk AI generatif"""
    
    def __init__(self):
        self.logger = LogManager.setup_logging()
        self.ai_handler = TogetherAIHandler()
        self.file_handler = FileHandler()
        self.logger.info("AI Content Processor initialized")
    
    def process_request(self, user_request: UserRequest) -> AIResponse:
        """Proses request user dari awal hingga akhir"""
        start_time = datetime.datetime.now()
        
        try:
            # Step 1: Validasi keamanan
            self.logger.info(f"[{user_request.request_id}] Memulai validasi keamanan")
            validation = SecurityValidator.validate_input(user_request.prompt)
            
            if not validation["is_valid"]:
                raise ValueError(f"Input tidak valid: {', '.join(validation['issues'])}")
            
            # Step 2: Preprocessing prompt
            self.logger.info(f"[{user_request.request_id}] Preprocessing prompt")
            processed_prompt = self._preprocess_prompt(validation["sanitized_prompt"], user_request)
            
            # Step 3: Generate content dengan AI
            self.logger.info(f"[{user_request.request_id}] Generating content dengan AI")
            ai_result = self.ai_handler.generate_content(
                processed_prompt,
                temperature=ModelConfig.TEMPERATURE,
                max_tokens=user_request.max_length or ModelConfig.MAX_TOKENS
            )
            
            if not ai_result["success"]:
                raise Exception(f"AI generation failed: {ai_result.get('error', 'Unknown error')}")
            
            # Step 4: Postprocessing
            self.logger.info(f"[{user_request.request_id}] Postprocessing content")
            final_content = self._postprocess_content(ai_result["content"], user_request)
            
            # Step 5: Simpan ke file
            self.logger.info(f"[{user_request.request_id}] Menyimpan ke file")
            filename = f"{user_request.user_id}_{user_request.request_id}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            file_path = self.file_handler.save_content(final_content, user_request.output_format, filename)
            
            # Step 6: Siapkan response
            processing_time = (datetime.datetime.now() - start_time).total_seconds()
            
            response = AIResponse(
                request_id=user_request.request_id,
                content=final_content[:500] + "..." if len(final_content) > 500 else final_content,
                metadata={
                    "model_used": ModelConfig.MODEL_NAME,
                    "temperature": ModelConfig.TEMPERATURE,
                    "tokens_used": ai_result.get("usage", {}),
                    "format": user_request.output_format.value,
                    "file_size": len(final_content)
                },
                file_path=file_path,
                status="success",
                processing_time=processing_time
            )
            
            self.logger.info(f"[{user_request.request_id}] Proses selesai dalam {processing_time:.2f} detik")
            return response
            
        except Exception as e:
            processing_time = (datetime.datetime.now() - start_time).total_seconds()
            self.logger.error(f"[{user_request.request_id}] Error: {str(e)}")
            
            return AIResponse(
                request_id=user_request.request_id,
                content="",
                metadata={"error": str(e)},
                file_path="",
                status="error",
                processing_time=processing_time
            )
    
    def _preprocess_prompt(self, prompt: str, request: UserRequest) -> str:
        """Preprocessing prompt sebelum dikirim ke AI"""
        # Tambahkan context format yang diminta
        format_instruction = f"\nHarap berikan output dalam format yang sesuai untuk file {request.output_format.value.upper()}."
        
        # Tambahkan instruksi bahasa Indonesia
        language_instruction = "\nBerikan respons dalam Bahasa Indonesia yang baik dan benar."
        
        # Tambahkan batasan panjang jika ada
        length_instruction = ""
        if request.max_length:
            length_instruction = f"\nBatasi respons maksimal {request.max_length} karakter."
        
        return f"{prompt}{format_instruction}{language_instruction}{length_instruction}"
    
    def _postprocess_content(self, content: str, request: UserRequest) -> str:
        """Postprocessing content setelah dari AI"""
        # Basic cleanup
        content = content.strip()
        
        # Format-specific postprocessing
        if request.output_format == FileFormat.JSON:
            # Pastikan JSON valid atau wrap dalam struktur JSON
            try:
                json.loads(content)
            except json.JSONDecodeError:
                content = json.dumps({"generated_content": content}, ensure_ascii=False, indent=2)
        
        elif request.output_format == FileFormat.CSV:
            # Basic CSV formatting
            if not content.startswith('"') and ',' in content:
                lines = content.split('\n')
                content = '\n'.join([f'"{line}"' if ',' in line else line for line in lines])
        
        return content

# ================================
# API INTERFACE (Contoh Penggunaan)
# ================================

def main_example():
    """Contoh penggunaan sistem"""
    
    # Inisialisasi processor
    processor = AIContentProcessor()
    
    # Contoh request user
    user_request = UserRequest(
        user_id="user_001",
        request_id=str(uuid.uuid4()),
        prompt="Buatkan artikel singkat tentang teknologi AI dalam Bahasa Indonesia",
        output_format=FileFormat.MD,
        max_length=1000
    )
    
    # Proses request
    result = processor.process_request(user_request)
    
    # Tampilkan hasil
    if result.status == "success":
        print("✅ Pemrosesan berhasil!")
        print(f"📁 File disimpan di: {result.file_path}")
        print(f"⏱️  Waktu proses: {result.processing_time:.2f} detik")
        print(f"📊 Metadata: {json.dumps(result.metadata, indent=2, ensure_ascii=False)}")
    else:
        print("❌ Pemrosesan gagal!")
        print(f"Error: {result.metadata.get('error')}")

# ================================
# DIAGRAM ALUR KONSTANTA
# ================================

ARCHITECTURE_FLOW = """
DIAGRAM ALUR ARSITEKTUR AI GENERATIF

1. INPUT LAYER
   ├── User Request (prompt, format, params)
   ├── Request ID Generation
   └── Timestamp Logging

2. SECURITY LAYER
   ├── Input Validation
   ├── Forbidden Keywords Check
   ├── Sensitive Data Detection
   └── Prompt Sanitization

3. PREPROCESSING LAYER
   ├── Format Instructions Addition
   ├── Language Context Setup
   ├── Length Limitations
   └── Custom Parameters Integration

4. AI MODEL LAYER
   ├── Together AI API Call
   ├── Model Configuration (Temperature, Tokens)
   ├── Error Handling
   └── Response Validation

5. POSTPROCESSING LAYER
   ├── Content Cleanup
   ├── Format-Specific Processing
   ├── Quality Assurance
   └── Final Content Preparation

6. FILE HANDLING LAYER
   ├── Format-Specific File Creation
   ├── Local Temporary Storage
   ├── File Path Management
   └── Metadata Attachment

7. OUTPUT LAYER
   ├── Response Object Creation
   ├── Success/Error Status
   ├── Processing Time Calculation
   └── Logging & Monitoring

8. INTEGRATION LAYER (Untuk implementasi Anda)
   ├── Google Drive Upload
   ├── Path Management
   ├── Access Control
   └── File Sharing
"""

if __name__ == "__main__":
    print("🤖 AI Generatif Production Ready")
    print("=" * 50)
    print("\n📋 Langkah-langkah setup:")
    print("1. Ganti YOUR_TOGETHER_AI_API_KEY dengan API key Anda")
    print("2. Ganti YOUR_MODEL_NAME dengan model yang ingin digunakan")
    print("3. Sesuaikan path Google Drive di PathConfig")
    print("4. Jalankan main_example() untuk testing")
    print("\n📐 Lihat ARCHITECTURE_FLOW untuk diagram alur lengkap")
    print("\n▶️  Menjalankan contoh...")
    
    # Uncomment untuk testing
    # main_example()
