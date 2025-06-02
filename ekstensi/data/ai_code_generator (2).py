#!/usr/bin/env python3
"""
AI Generator Kode Arsitektur - Script Colab Ready
Sistem AI generatif untuk membuat struktur proyek dengan berbagai jenis file
Compatible dengan Google Colab + Together AI
"""

import os
import json
import requests
import time
import re
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import logging
from datetime import datetime

# Install dependencies untuk Colab
try:
    import requests
except ImportError:
    !pip install requests

# ================== KONSTANTA DIAGRAM ALUR ==================
ARCHITECTURE_FLOW = """
DIAGRAM ALUR ARSITEKTUR AI CODE GENERATOR:

1. INPUT VALIDATION → 2. PLANNING PHASE → 3. CODE GENERATION → 4. FILE CREATION → 5. OUTPUT DELIVERY

Sistem Keamanan: Validasi konten → Cek pattern berbahaya → Legal compliance → Safe output
"""

# ================== KONFIGURASI ==================
class Config:
    # Together AI Configuration - ISI DISINI
    TOGETHER_API_KEY = ""  # WAJIB ISI
    TOGETHER_MODEL = "meta-llama/Llama-3.1-70B-Instruct-Turbo"
    TEMPERATURE = 0.1  # Rendah untuk konsistensi
    MAX_TOKENS = 2000
    
    # Colab Path Configuration
    OUTPUT_BASE_PATH = "/content/"
    
    # Security Keywords
    FORBIDDEN_KEYWORDS = [
        "hack", "crack", "exploit", "malware", "virus", "backdoor",
        "rm -rf", "del /", "DROP TABLE", "DELETE FROM users"
    ]

# ================== SECURITY VALIDATOR ==================
class SecurityValidator:
    @staticmethod
    def is_safe_content(content: str) -> Tuple[bool, str]:
        """Validasi konten untuk memastikan tidak berbahaya"""
        if not content:
            return True, "Konten kosong"
            
        content_lower = content.lower()
        
        # Cek kata kunci berbahaya
        for keyword in Config.FORBIDDEN_KEYWORDS:
            if keyword in content_lower:
                return False, f"Konten mengandung kata terlarang: {keyword}"
        
        # Cek pattern berbahaya spesifik
        dangerous_patterns = [
            r"eval\s*\(", r"exec\s*\(", r"os\.system\s*\(",
            r"subprocess\..*shell\s*=\s*True", r"__import__\s*\("
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, content):
                return False, f"Pola berbahaya terdeteksi"
        
        return True, "Konten aman"

# ================== AI CODE GENERATOR ==================
class AICodeGenerator:
    def __init__(self):
        self.api_key = Config.TOGETHER_API_KEY
        self.model = Config.TOGETHER_MODEL
        self.temperature = Config.TEMPERATURE
        self.setup_logging()
        
        if not self.api_key:
            print("⚠️  WARNING: API Key Together AI belum diset!")
            print("Set API key di Config.TOGETHER_API_KEY")
    
    def setup_logging(self):
        """Setup logging untuk Colab"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def create_focused_prompt(self, user_request: str, project_type: str) -> str:
        """Buat prompt yang fokus menghasilkan kode, bukan JSON"""
        return f"""
Anda adalah expert programmer. Buat struktur proyek {project_type} berdasarkan request berikut:

REQUEST: {user_request}

INSTRUKSI PENTING:
1. Buat arsitektur folder dan file yang profesional
2. Setiap file harus berisi KODE ASLI yang berfungsi, bukan placeholder
3. Gunakan best practices untuk setiap bahasa
4. Tambahkan komentar yang berguna
5. Pastikan kode bisa langsung dijalankan

WAJIB IKUTI FORMAT INI PERSIS:
=== PROJECT_STRUCTURE ===
folder1/
├── subfolder1/
│   ├── file1.ext
│   └── file2.ext
├── file3.ext
└── file4.ext

=== FILES ===
==FILE: path/filename.ext==
[isi kode file lengkap disini]
==END_FILE==

==FILE: path/filename2.ext==
[isi kode file lengkap disini]
==END_FILE==

=== DOCUMENTATION ===
[penjelasan singkat proyek dan cara menjalankan]

Mulai sekarang, buat proyek yang diminta!
"""

    def call_together_ai(self, prompt: str) -> Optional[str]:
        """Panggil Together AI API dengan error handling"""
        if not self.api_key:
            print("❌ Error: API Key tidak ditemukan")
            return None
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "max_tokens": Config.MAX_TOKENS
        }
        
        try:
            print("🔄 Menghubungi Together AI...")
            response = requests.post(
                "https://api.together.xyz/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                print(f"❌ API Error: {response.status_code}")
                print(f"Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
    
    def parse_ai_response(self, response: str) -> Dict:
        """Parse response AI menjadi struktur file"""
        try:
            result = {
                "project_structure": "",
                "files": {},
                "documentation": ""
            }
            
            # Extract project structure
            structure_match = re.search(r'=== PROJECT_STRUCTURE ===(.*?)=== FILES ===', response, re.DOTALL)
            if structure_match:
                result["project_structure"] = structure_match.group(1).strip()
            
            # Extract files
            file_pattern = r'==FILE:\s*([^=]+)==(.*?)==END_FILE=='
            files = re.findall(file_pattern, response, re.DOTALL)
            
            for filepath, content in files:
                filepath = filepath.strip()
                content = content.strip()
                
                # Validasi keamanan untuk setiap file
                is_safe, _ = SecurityValidator.is_safe_content(content)
                if is_safe and content:
                    result["files"][filepath] = content
            
            # Extract documentation
            doc_match = re.search(r'=== DOCUMENTATION ===(.*?)$', response, re.DOTALL)
            if doc_match:
                result["documentation"] = doc_match.group(1).strip()
            
            return result
            
        except Exception as e:
            print(f"❌ Error parsing response: {e}")
            return {"project_structure": "", "files": {}, "documentation": ""}
    
    def create_project_files(self, file_data: Dict[str, str], project_name: str) -> str:
        """Buat file-file proyek di Colab"""
        try:
            # Buat folder proyek dengan timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            project_dir = f"{Config.OUTPUT_BASE_PATH}{project_name}_{timestamp}"
            
            os.makedirs(project_dir, exist_ok=True)
            
            created_files = []
            
            for filepath, content in file_data.items():
                # Buat path lengkap
                full_path = os.path.join(project_dir, filepath)
                
                # Buat direktori jika belum ada
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                
                # Tulis file
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                created_files.append(filepath)
                print(f"✅ Created: {filepath}")
            
            print(f"\n📁 Project created at: {project_dir}")
            return project_dir
            
        except Exception as e:
            print(f"❌ Error creating files: {e}")
            return ""
    
    def generate_project(self, user_request: str, project_type: str = "web_app") -> Dict:
        """Fungsi utama untuk generate proyek"""
        print(f"🚀 Starting project generation: {project_type}")
        print(f"📝 Request: {user_request[:100]}...")
        
        # Step 1: Validasi input
        is_safe, message = SecurityValidator.is_safe_content(user_request)
        if not is_safe:
            return {"success": False, "error": f"Request tidak aman: {message}"}
        
        # Step 2: Buat prompt
        prompt = self.create_focused_prompt(user_request, project_type)
        
        # Step 3: Panggil AI
        ai_response = self.call_together_ai(prompt)
        if not ai_response:
            return {"success": False, "error": "Gagal mendapat respons dari AI"}
        
        print("✅ AI response received")
        
        # Step 4: Parse respons
        parsed_data = self.parse_ai_response(ai_response)
        
        if not parsed_data["files"]:
            print("⚠️  No files found in AI response")
            return {"success": False, "error": "AI tidak menghasilkan file yang valid"}
        
        print(f"📄 Found {len(parsed_data['files'])} files")
        
        # Step 5: Buat file-file
        project_path = self.create_project_files(
            parsed_data["files"], 
            project_type.replace(" ", "_")
        )
        
        if project_path:
            return {
                "success": True,
                "project_path": project_path,
                "files_created": list(parsed_data["files"].keys()),
                "project_structure": parsed_data["project_structure"],
                "documentation": parsed_data["documentation"]
            }
        else:
            return {"success": False, "error": "Gagal membuat file proyek"}
    
    def edit_existing_file(self, file_path: str, edit_request: str) -> Dict:
        """Edit file yang sudah ada"""
        try:
            if not os.path.exists(file_path):
                return {"success": False, "error": "File tidak ditemukan"}
            
            # Baca file saat ini
            with open(file_path, 'r', encoding='utf-8') as f:
                current_content = f.read()
            
            # Buat prompt untuk editing
            edit_prompt = f"""
Edit file berikut sesuai permintaan:

CURRENT FILE CONTENT:
{current_content}

EDIT REQUEST: {edit_request}

INSTRUKSI:
1. Lakukan perubahan sesuai permintaan
2. Pertahankan struktur dan format yang ada
3. Pastikan kode tetap berfungsi
4. Tambahkan komentar jika perlu

Berikan HANYA kode hasil edit, tanpa penjelasan tambahan:
"""
            
            # Panggil AI untuk editing
            edited_content = self.call_together_ai(edit_prompt)
            if not edited_content:
                return {"success": False, "error": "Gagal mengedit file"}
            
            # Backup file asli
            backup_path = file_path + ".backup"
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(current_content)
            
            # Simpan file yang sudah diedit
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(edited_content.strip())
            
            return {
                "success": True,
                "file_path": file_path,
                "backup_path": backup_path,
                "message": "File berhasil diedit"
            }
            
        except Exception as e:
            return {"success": False, "error": f"Error: {e}"}

# ================== HELPER FUNCTIONS ==================
def show_project_structure(project_path: str):
    """Tampilkan struktur proyek yang dibuat"""
    print(f"\n📂 PROJECT STRUCTURE: {project_path}")
    print("="*50)
    
    for root, dirs, files in os.walk(project_path):
        level = root.replace(project_path, '').count(os.sep)
        indent = ' ' * 2 * level
        print(f"{indent}{os.path.basename(root)}/")
        
        subindent = ' ' * 2 * (level + 1)
        for file in files:
            print(f"{subindent}{file}")

def quick_generate(request: str, project_type: str = "web_app"):
    """Quick generate function untuk penggunaan mudah"""
    generator = AICodeGenerator()
    
    if not Config.TOGETHER_API_KEY:
        print("❌ ERROR: Set API Key dulu di Config.TOGETHER_API_KEY")
        return None
    
    result = generator.generate_project(request, project_type)
    
    if result["success"]:
        print(f"\n🎉 SUCCESS! Project generated successfully!")
        print(f"📁 Location: {result['project_path']}")
        print(f"📄 Files: {len(result['files_created'])}")
        
        # Tampilkan struktur
        show_project_structure(result['project_path'])
        
        # Tampilkan dokumentasi
        if result.get('documentation'):
            print(f"\n📖 DOCUMENTATION:")
            print("="*50)
            print(result['documentation'])
        
        return result['project_path']
    else:
        print(f"❌ ERROR: {result['error']}")
        return None

# ================== CONTOH PENGGUNAAN ==================
def main():
    """Contoh penggunaan untuk Colab"""
    
    # STEP 1: SET API KEY DULU!
    print("🔧 SETUP:")
    print("1. Set your Together AI API key:")
    print("   Config.TOGETHER_API_KEY = 'your_api_key_here'")
    print("\n2. Kemudian jalankan quick_generate()")
    
    # Contoh penggunaan
    print("\n📝 CONTOH PENGGUNAAN:")
    print("""
# Set API key terlebih dahulu
Config.TOGETHER_API_KEY = "your_api_key_here"

# Generate proyek todo list
project_path = quick_generate(
    "Buat aplikasi todo list dengan HTML, CSS, JS. Fitur: tambah task, hapus task, mark complete",
    "todo_app"
)

# Generate proyek lain
project_path = quick_generate(
    "Buat REST API sederhana dengan Python Flask untuk CRUD products",
    "flask_api"
)
""")

if __name__ == "__main__":
    main()
