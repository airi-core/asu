#!/usr/bin/env python3
"""
AI Generator Kode Arsitektur - Script Produksi
Sistem AI generatif untuk membuat struktur proyek dengan berbagai jenis file
Menggunakan Together AI dengan validasi keamanan dan standar industri
"""

import os
import json
import requests
import time
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import logging
from datetime import datetime

# ================== KONSTANTA DIAGRAM ALUR ==================
ARCHITECTURE_FLOW = """
DIAGRAM ALUR ARSITEKTUR AI CODE GENERATOR:

1. INPUT VALIDATION
   ├── Validasi API Key & Model
   ├── Sanitasi Input User  
   ├── Cek Format Request
   └── Security Screening

2. PLANNING PHASE
   ├── Analisis Requirement
   ├── Generate Architecture Plan
   ├── Validasi Structure Safety
   └── Create File Mapping

3. CODE GENERATION
   ├── Generate Base Structure
   ├── Create Individual Files
   ├── Apply Code Standards
   └── Security Validation

4. QUALITY ASSURANCE
   ├── Code Review Automation
   ├── Security Scan
   ├── Best Practice Check
   └── Legal Compliance Check

5. OUTPUT DELIVERY
   ├── Package Files
   ├── Generate Documentation
   ├── Save to Storage Path
   └── Return Success Report
"""

# ================== KONFIGURASI ==================
class Config:
    # Together AI Configuration
    TOGETHER_API_KEY = ""  # ISI API KEY TOGETHER AI
    TOGETHER_MODEL = "meta-llama/Llama-2-70b-chat-hf"  # MODEL PILIHAN
    TEMPERATURE = 0.3  # TEMPERATURE UNTUK KONSISTENSI
    MAX_TOKENS = 4000
    
    # Path Configuration (Google Drive Integration Ready)
    DRIVE_INPUT_PATH = "/content/drive/MyDrive/ai_generator/input/"
    DRIVE_OUTPUT_PATH = "/content/drive/MyDrive/ai_generator/output/"
    
    # Security Configuration
    FORBIDDEN_KEYWORDS = [
        "hack", "crack", "exploit", "malware", "virus", "backdoor",
        "password", "private_key", "secret", "token", "admin",
        "sql injection", "xss", "csrf", "ddos", "botnet"
    ]
    
    ALLOWED_FILE_TYPES = [
        ".py", ".js", ".html", ".css", ".json", ".yaml", ".yml",
        ".md", ".txt", ".sql", ".xml", ".dockerfile", ".gitignore"
    ]

# ================== SISTEM KEAMANAN ==================
class SecurityValidator:
    @staticmethod
    def is_safe_content(content: str) -> Tuple[bool, str]:
        """Validasi konten untuk memastikan tidak berbahaya"""
        content_lower = content.lower()
        
        for keyword in Config.FORBIDDEN_KEYWORDS:
            if keyword in content_lower:
                return False, f"Konten mengandung kata terlarang: {keyword}"
        
        # Cek pattern berbahaya
        dangerous_patterns = [
            "eval(", "exec(", "os.system(", "__import__(", 
            "subprocess.", "shell=True", "rm -rf", "del /",
            "DROP TABLE", "DELETE FROM", "UPDATE SET"
        ]
        
        for pattern in dangerous_patterns:
            if pattern in content:
                return False, f"Pola berbahaya terdeteksi: {pattern}"
        
        return True, "Konten aman"
    
    @staticmethod
    def validate_file_structure(files: Dict[str, str]) -> Tuple[bool, str]:
        """Validasi struktur file yang akan dibuat"""
        for filename, content in files.items():
            # Cek ekstensi file
            file_ext = Path(filename).suffix
            if file_ext not in Config.ALLOWED_FILE_TYPES:
                return False, f"Tipe file tidak diizinkan: {file_ext}"
            
            # Cek konten file
            is_safe, message = SecurityValidator.is_safe_content(content)
            if not is_safe:
                return False, f"File {filename}: {message}"
        
        return True, "Struktur file aman"

# ================== AI CODE GENERATOR ==================
class AICodeGenerator:
    def __init__(self):
        self.api_key = Config.TOGETHER_API_KEY
        self.model = Config.TOGETHER_MODEL
        self.temperature = Config.TEMPERATURE
        self.session = requests.Session()
        self.setup_logging()
    
    def setup_logging(self):
        """Setup logging untuk monitoring"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('ai_generator.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def validate_inputs(self, user_request: str, project_type: str) -> Tuple[bool, str]:
        """Validasi input dari user"""
        if not self.api_key:
            return False, "API Key Together AI belum diset"
        
        if not user_request or len(user_request.strip()) < 10:
            return False, "Request terlalu pendek atau kosong"
        
        # Security check pada request
        is_safe, message = SecurityValidator.is_safe_content(user_request)
        if not is_safe:
            return False, f"Request tidak aman: {message}"
        
        return True, "Input valid"
    
    def create_system_prompt(self) -> str:
        """Membuat system prompt dengan diagram alur keamanan"""
        return f"""
        {ARCHITECTURE_FLOW}
        
        Anda adalah AI Code Generator profesional yang mengikuti standar industri.
        
        ATURAN KETAT:
        1. TIDAK BOLEH menghasilkan kode yang melanggar hukum
        2. TIDAK BOLEH membuat backdoor, malware, atau exploit
        3. WAJIB mengikuti best practices coding
        4. WAJIB menambahkan dokumentasi pada setiap file
        5. WAJIB menggunakan struktur folder yang standar
        
        TUGAS:
        - Buat arsitektur proyek yang bersih dan terstruktur
        - Generate multiple files sesuai kebutuhan
        - Pastikan setiap file memiliki purpose yang jelas
        - Tambahkan komentar dan dokumentasi
        - Follow coding standards (PEP8 untuk Python, ESLint untuk JS, dll)
        
        FORMAT OUTPUT: JSON dengan struktur:
        {{
            "project_structure": "deskripsi arsitektur",
            "files": {{
                "path/filename.ext": "content file",
                ...
            }},
            "documentation": "penjelasan proyek"
        }}
        """
    
    def call_together_ai(self, prompt: str) -> Optional[str]:
        """Panggil Together AI API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.create_system_prompt()},
                {"role": "user", "content": prompt}
            ],
            "temperature": self.temperature,
            "max_tokens": Config.MAX_TOKENS
        }
        
        try:
            response = self.session.post(
                "https://api.together.xyz/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']
        
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error calling Together AI: {e}")
            return None
    
    def parse_ai_response(self, response: str) -> Optional[Dict]:
        """Parse respons AI menjadi struktur yang bisa diproses"""
        try:
            # Coba ekstrak JSON dari response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                return None
            
            json_str = response[start_idx:end_idx]
            return json.loads(json_str)
        
        except json.JSONDecodeError:
            self.logger.error("Gagal parse JSON response dari AI")
            return None
    
    def create_project_files(self, file_data: Dict[str, str], output_path: str) -> bool:
        """Buat file-file proyek di path yang ditentukan"""
        try:
            output_dir = Path(output_path)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            for filepath, content in file_data.items():
                full_path = output_dir / filepath
                full_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                self.logger.info(f"File dibuat: {full_path}")
            
            return True
        
        except Exception as e:
            self.logger.error(f"Error membuat file: {e}")
            return False
    
    def generate_project(self, user_request: str, project_type: str = "web_app") -> Dict:
        """Fungsi utama untuk generate proyek"""
        self.logger.info(f"Memulai generate proyek: {project_type}")
        
        # Step 1: Validasi Input
        is_valid, message = self.validate_inputs(user_request, project_type)
        if not is_valid:
            return {"success": False, "error": message}
        
        # Step 2: Buat prompt untuk AI
        enhanced_prompt = f"""
        Proyek Type: {project_type}
        Request User: {user_request}
        
        Buat arsitektur proyek lengkap dengan multiple files.
        Pastikan struktur folder professional dan kode berkualitas tinggi.
        """
        
        # Step 3: Panggil AI
        ai_response = self.call_together_ai(enhanced_prompt)
        if not ai_response:
            return {"success": False, "error": "Gagal mendapat respons dari AI"}
        
        # Step 4: Parse respons AI
        parsed_data = self.parse_ai_response(ai_response)
        if not parsed_data or "files" not in parsed_data:
            return {"success": False, "error": "Format respons AI tidak valid"}
        
        # Step 5: Validasi keamanan
        is_safe, safety_message = SecurityValidator.validate_file_structure(
            parsed_data["files"]
        )
        if not is_safe:
            return {"success": False, "error": f"Validasi keamanan gagal: {safety_message}"}
        
        # Step 6: Buat timestamp untuk folder output
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        project_name = project_type.replace(" ", "_").lower()
        output_path = f"{Config.DRIVE_OUTPUT_PATH}{project_name}_{timestamp}/"
        
        # Step 7: Buat file-file proyek
        success = self.create_project_files(parsed_data["files"], output_path)
        
        if success:
            return {
                "success": True,
                "output_path": output_path,
                "files_created": list(parsed_data["files"].keys()),
                "project_structure": parsed_data.get("project_structure", ""),
                "documentation": parsed_data.get("documentation", "")
            }
        else:
            return {"success": False, "error": "Gagal membuat file proyek"}
    
    def edit_existing_code(self, file_path: str, edit_request: str) -> Dict:
        """Edit kode yang sudah ada berdasarkan request user"""
        try:
            # Baca file yang ada
            with open(file_path, 'r', encoding='utf-8') as f:
                current_code = f.read()
            
            # Validasi keamanan edit request
            is_safe, message = SecurityValidator.is_safe_content(edit_request)
            if not is_safe:
                return {"success": False, "error": f"Edit request tidak aman: {message}"}
            
            # Buat prompt untuk editing
            edit_prompt = f"""
            KODE SAAT INI:
            {current_code}
            
            PERMINTAAN EDIT:
            {edit_request}
            
            Lakukan perubahan sesuai permintaan dengan tetap menjaga:
            1. Struktur kode yang baik
            2. Keamanan aplikasi
            3. Best practices
            4. Dokumentasi yang ada
            
            Berikan hasil edit dalam format JSON:
            {{"edited_code": "kode hasil edit", "changes_summary": "ringkasan perubahan"}}
            """
            
            # Panggil AI untuk editing
            ai_response = self.call_together_ai(edit_prompt)
            if not ai_response:
                return {"success": False, "error": "Gagal mendapat respons AI untuk editing"}
            
            # Parse hasil edit
            edit_result = self.parse_ai_response(ai_response)
            if not edit_result or "edited_code" not in edit_result:
                return {"success": False, "error": "Format hasil edit tidak valid"}
            
            # Validasi keamanan kode hasil edit
            is_safe, message = SecurityValidator.is_safe_content(edit_result["edited_code"])
            if not is_safe:
                return {"success": False, "error": f"Kode hasil edit tidak aman: {message}"}
            
            # Simpan file yang sudah diedit
            backup_path = file_path + ".backup"
            os.rename(file_path, backup_path)  # Backup file asli
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(edit_result["edited_code"])
            
            return {
                "success": True,
                "file_path": file_path,
                "backup_path": backup_path,
                "changes_summary": edit_result.get("changes_summary", "Perubahan berhasil diterapkan")
            }
        
        except Exception as e:
            self.logger.error(f"Error editing file: {e}")
            return {"success": False, "error": f"Gagal mengedit file: {str(e)}"}

# ================== CONTOH PENGGUNAAN ==================
def main():
    """Contoh penggunaan AI Code Generator"""
    # Inisialisasi generator
    generator = AICodeGenerator()
    
    # Contoh 1: Generate proyek baru
    user_request = """
    Buatkan aplikasi web sederhana untuk manajemen tugas (todo list) dengan fitur:
    - Tambah tugas baru
    - Hapus tugas
    - Tandai tugas selesai
    - Filter tugas berdasarkan status
    
    Gunakan HTML, CSS, JavaScript murni tanpa framework.
    """
    
    print("=== GENERATING PROJECT ===")
    result = generator.generate_project(user_request, "todo_web_app")
    
    if result["success"]:
        print(f"✅ Proyek berhasil dibuat!")
        print(f"📁 Path: {result['output_path']}")
        print(f"📄 Files: {', '.join(result['files_created'])}")
        print(f"📋 Struktur: {result['project_structure']}")
    else:
        print(f"❌ Error: {result['error']}")
    
    # Contoh 2: Edit kode yang sudah ada
    # edit_result = generator.edit_existing_code(
    #     "/path/to/existing/file.py",
    #     "Tambahkan validasi input dan error handling"
    # )

if __name__ == "__main__":
    main()
