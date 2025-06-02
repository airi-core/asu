#!/usr/bin/env python3
"""
AI Generator Kode Arsitektur - Script Colab Ready
Sistem AI generatif dengan 5 model berlapis untuk keamanan maksimal
Compatible dengan Google Colab + Together AI
"""

import os
import json
import requests
import time
import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from functools import lru_cache

# Install dependencies untuk Colab
try:
    import requests
except ImportError:
    !pip install requests

# ================== CUSTOM EXCEPTIONS ==================
class SecurityException(Exception):
    """Exception untuk masalah keamanan"""
    pass

class APIException(Exception):
    """Exception untuk masalah API"""
    pass

class FileSystemException(Exception):
    """Exception untuk masalah filesystem"""
    pass

class ProcessingException(Exception):
    """Exception untuk masalah pemrosesan konten"""
    pass

# ================== KONSTANTA DIAGRAM ALUR ==================
ARCHITECTURE_FLOW = """
DIAGRAM ALUR ARSITEKTUR 5-LAPIS:

1. MODEL ARSITEK: Desain arsitektur & tugas file
2. MODEL PENGEMBANG: Implementasi kode
3. MODEL AUDITOR: Verifikasi & refaktor
4. MODEL ANALIS KEAMANAN: Pemeriksaan keamanan
5. MODEL INTEGRATOR: Pembuatan file final

Sistem Keamanan: Isolasi penuh - User tidak bisa akses langsung ke proses koding
"""

# ================== KONFIGURASI ==================
class Config:
    # Together AI Configuration
    TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY", "")
    TOGETHER_MODEL = "meta-llama/Llama-3.1-70B-Instruct-Turbo"
    TEMPERATURE = 0.1
    MAX_TOKENS = 2000
    MIN_API_CALL_INTERVAL = 5
    
    # Path Configuration
    OUTPUT_BASE_PATH = "/content/"
    GDRIVE_SYSTEM_PROMPTS = "/content/drive/MyDrive/ai_generator/system_prompts/"
    GDRIVE_TEMPLATES = "/content/drive/MyDrive/ai_generator/templates/"
    GDRIVE_OUTPUT = "/content/drive/MyDrive/ai_generator/output/"
    
    # Security Keywords
    FORBIDDEN_KEYWORDS = [
        # Daftar kata kunci berbahaya sama seperti sebelumnya
        # ... (diisi dengan daftar yang sama)
    ]

# ================== SECURITY VALIDATOR ==================
class SecurityValidator:
    @staticmethod
    def is_safe_content(content: str) -> Tuple[bool, str]:
        """Validasi konten untuk memastikan tidak berbahaya"""
        # Implementasi sama seperti sebelumnya
        # ... (diisi dengan implementasi sebelumnya)

# ================== AI CODE GENERATOR ==================
class AICodeGenerator:
    def __init__(self):
        if not Config.TOGETHER_API_KEY:
            raise ValueError("Together API key belum dikonfigurasi")
        self.api_key = Config.TOGETHER_API_KEY
        self.model = Config.TOGETHER_MODEL
        self.temperature = Config.TEMPERATURE
        self.last_api_call = 0
        self.setup_logging()
        
    def setup_logging(self):
        """Setup logging untuk Colab"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        self.system_prompts = self.load_system_prompts()
        print(f"📚 Loaded {len(self.system_prompts)} system prompts")
    
    @lru_cache(maxsize=5)
    def load_system_prompts(self) -> Dict[str, str]:
        """Load system prompts dari Google Drive dengan cache"""
        # Implementasi sama seperti sebelumnya
        # ... (diisi dengan implementasi sebelumnya)
    
    def get_default_prompts(self) -> Dict[str, str]:
        """Default system prompts untuk semua model"""
        return {
            "architect": """
Anda adalah Arsitek Perangkat Lunak. Tugas Anda:
1. Desain struktur proyek berdasarkan permintaan pengguna
2. Tentukan file-file yang diperlukan
3. Buat deskripsi tugas untuk setiap file
4. Format output: Daftar file dengan deskripsi tugas
            """,
            "developer": """
Anda adalah Pengembang Perangkat Lunak. Tugas Anda:
1. Implementasikan kode berdasarkan deskripsi tugas
2. Tulis kode lengkap untuk setiap file
3. Ikuti best practices pemrograman
4. Tambahkan komentar yang jelas
            """,
            "auditor": """
Anda adalah Auditor Kode. Tugas Anda:
1. Verifikasi apakah kode sesuai dengan deskripsi tugas
2. Lakukan refaktor jika diperlukan
3. Tambahkan catatan audit
4. Jika ada ketidaksesuaian, buat solusi perbaikan
            """,
            "security_analyst": """
Anda adalah Analis Keamanan. Tugas Anda:
1. Analisis kode untuk potensi risiko keamanan
2. Jika berbahaya, ganti dengan kode simulasi aman
3. Jika aman, pertahankan kode asli
4. Berikan sertifikat keamanan
            """,
            "integrator": """
Anda adalah Integrator Sistem. Tugas Anda:
1. Terima output dari Analis Keamanan
2. Buat file-file proyek sesuai struktur
3. Tambahkan dokumentasi proyek
4. Format output akhir untuk eksekusi sistem
            """
        }
    
    def load_project_templates(self, project_type: str) -> Dict[str, str]:
        """Load template struktur proyek"""
        # Implementasi sama seperti sebelumnya
        # ... (diisi dengan implementasi sebelumnya)
    
    def call_together_ai(self, messages: List[Dict]) -> Optional[Dict]:
        """Panggil Together AI API"""
        # Implementasi sama seperti sebelumnya
        # ... (diisi dengan implementasi sebelumnya)
    
    def process_with_model(self, model_role: str, input_data: str, additional_context: str = "") -> str:
        """Proses data dengan model spesifik"""
        system_prompt = self.system_prompts.get(model_role, "")
        if not system_prompt:
            raise ValueError(f"System prompt untuk {model_role} tidak ditemukan")
        
        prompt = f"{system_prompt}\n\n{additional_context}\n\nINPUT DATA:\n{input_data}"
        
        messages = [{"role": "user", "content": prompt}]
        response = self.call_together_ai(messages)
        
        if response and 'choices' in response and len(response['choices']) > 0:
            return response['choices'][0]['message']['content']
        return None
    
    def architect_phase(self, user_request: str, project_type: str) -> str:
        """Model 1: Desain arsitektur dan tugas file"""
        print("🧠 Model 1: Arsitek - Mendesain struktur proyek")
        
        template = json.dumps(self.load_project_templates(project_type), indent=2)
        context = f"""
PROJECT TYPE: {project_type}
PROJECT TEMPLATE:
{template}

INSTRUKSI:
1. Buat daftar file yang diperlukan
2. Untuk setiap file, buat deskripsi tugas yang jelas
3. Format output:
=== FILE_TASKS ===
==FILE: path/file1==
[Tugas untuk file1]
==END_FILE==

==FILE: path/file2==
[Tugas untuk file2]
==END_FILE==
        """
        
        return self.process_with_model("architect", user_request, context)
    
    def developer_phase(self, architect_output: str) -> str:
        """Model 2: Implementasi kode berdasarkan tugas"""
        print("💻 Model 2: Pengembang - Menulis kode")
        
        context = """
INSTRUKSI:
1. Implementasikan kode sesuai deskripsi tugas
2. Tulis kode lengkap untuk setiap file
3. Format output:
=== CODE_FILES ===
==FILE: path/file1==
[Kode lengkap]
==END_FILE==

==FILE: path/file2==
[Kode lengkap]
==END_FILE==
        """
        
        return self.process_with_model("developer", architect_output, context)
    
    def auditor_phase(self, developer_output: str, architect_output: str) -> str:
        """Model 3: Verifikasi dan refaktor kode"""
        print("🔍 Model 3: Auditor - Memverifikasi kode")
        
        context = f"""
DESKRIPSI TUGAS (Dari Arsitek):
{architect_output}

INSTRUKSI:
1. Verifikasi apakah kode sesuai deskripsi tugas
2. Jika tidak sesuai, lakukan refaktor atau tulis ulang
3. Tambahkan catatan audit untuk setiap file
4. Format output:
=== AUDITED_FILES ===
==FILE: path/file1==
[Kode yang sudah diverifikasi]
==AUDIT_NOTES==
[Catatan audit]
==END_FILE==
        """
        
        return self.process_with_model("auditor", developer_output, context)
    
    def security_phase(self, auditor_output: str) -> str:
        """Model 4: Analisis keamanan kode"""
        print("🔒 Model 4: Analis Keamanan - Memeriksa keamanan")
        
        context = """
INSTRUKSI:
1. Analisis kode untuk potensi risiko keamanan
2. Jika berbahaya, ganti dengan kode simulasi aman
3. Jika aman, pertahankan kode asli
4. Berikan sertifikat keamanan
5. Format output:
=== SECURE_FILES ===
==FILE: path/file1==
[Kode aman]
==SECURITY_STATUS==
[Status: AMAN/BERBAHAYA]
==SECURITY_CERTIFICATE==
[Sertifikat keamanan]
==END_FILE==
        """
        
        return self.process_with_model("security_analyst", auditor_output, context)
    
    def integrator_phase(self, security_output: str, project_type: str) -> str:
        """Model 5: Pembuatan file final dan dokumentasi"""
        print("🚀 Model 5: Integrator - Membuat proyek final")
        
        context = f"""
PROJECT TYPE: {project_type}
INSTRUKSI:
1. Buat struktur file final
2. Tambahkan dokumentasi proyek
3. Format output:
=== PROJECT_STRUCTURE ===
[Struktur folder]

=== FILES ===
==FILE: path/file1==
[Kode final]
==END_FILE==

=== DOCUMENTATION ===
[Dokumentasi proyek]
        """
        
        return self.process_with_model("integrator", security_output, context)
    
    def parse_ai_response(self, response: str) -> Dict:
        """Parse response AI menjadi struktur file"""
        # Implementasi sama seperti sebelumnya
        # ... (diisi dengan implementasi sebelumnya)
    
    def create_project_files(self, file_data: Dict[str, str], project_name: str) -> str:
        """Buat file-file proyek (HANYA oleh sistem)"""
        # Implementasi sama seperti sebelumnya
        # ... (diisi dengan implementasi sebelumnya)
    
    def generate_project(self, user_request: str, project_type: str = "web_app") -> Dict:
        """Fungsi utama dengan 5 model berlapis"""
        try:
            print(f"🚀 Starting project generation: {project_type}")
            print(f"📝 Request: {user_request[:100]}...")
            
            # Validasi input
            is_safe, message = SecurityValidator.is_safe_content(user_request)
            if not is_safe:
                return {"success": False, "error": f"Request tidak aman: {message}"}
            
            # Tahap 1: Arsitek
            architect_output = self.architect_phase(user_request, project_type)
            if not architect_output:
                return {"success": False, "error": "Gagal pada tahap arsitek"}
            
            # Tahap 2: Pengembang
            developer_output = self.developer_phase(architect_output)
            if not developer_output:
                return {"success": False, "error": "Gagal pada tahap pengembang"}
            
            # Tahap 3: Auditor
            auditor_output = self.auditor_phase(developer_output, architect_output)
            if not auditor_output:
                return {"success": False, "error": "Gagal pada tahap auditor"}
            
            # Tahap 4: Analis Keamanan
            security_output = self.security_phase(auditor_output)
            if not security_output:
                return {"success": False, "error": "Gagal pada tahap keamanan"}
            
            # Tahap 5: Integrator
            integrator_output = self.integrator_phase(security_output, project_type)
            if not integrator_output:
                return {"success": False, "error": "Gagal pada tahap integrator"}
            
            # Parse dan buat file
            parsed_data = self.parse_ai_response(integrator_output)
            project_path = self.create_project_files(
                parsed_data["files"], 
                project_type.replace(" ", "_")
            )
            
            return {
                "success": True,
                "project_path": project_path,
                "files_created": list(parsed_data["files"].keys()),
                "project_structure": parsed_data["project_structure"],
                "documentation": parsed_data["documentation"]
            }
            
        except SecurityException as sec_e:
            return {"success": False, "error": f"Security Error: {sec_e}"}
        except APIException as api_e:
            return {"success": False, "error": f"API Error: {api_e}"}
        except ProcessingException as proc_e:
            return {"success": False, "error": f"Processing Error: {proc_e}"}
        except FileSystemException as fs_e:
            return {"success": False, "error": f"File System Error: {fs_e}"}
        except Exception as e:
            return {"success": False, "error": f"Unexpected Error: {e}"}

    # HAPUSKAN fungsi edit_existing_file dari akses publik
    # User tidak boleh bisa mengedit file secara langsung

# ================== HELPER FUNCTIONS ==================
def show_project_structure(project_path: str):
    """Tampilkan struktur proyek yang dibuat"""
    # Implementasi sama seperti sebelumnya
    # ... (diisi dengan implementasi sebelumnya)

# ================== INTERACTIVE FUNCTIONS ==================
def interactive_generate():
    """Fungsi interaktif untuk generate proyek"""
    print("🤖 AI CODE GENERATOR - Interactive Mode (5-Layer Security)")
    print("="*50)
    
    if not Config.TOGETHER_API_KEY:
        print("❌ ERROR: API Key belum diset!")
        print("Set dengan: Config.TOGETHER_API_KEY = 'your_api_key'")
        return
    
    print("\n📋 Available Project Types:")
    print("1. web_app - Web Application (HTML/CSS/JS)")
    print("2. api_backend - REST API Backend")
    print("3. mobile_app - Mobile Application")
    print("4. desktop_app - Desktop Application") 
    print("5. data_science - Data Science Project")
    print("6. custom - Custom Project Type")
    
    project_choice = input("\n🎯 Pilih project type (1-6): ").strip()
    project_types = {
        "1": "web_app",
        "2": "api_backend", 
        "3": "mobile_app",
        "4": "desktop_app",
        "5": "data_science",
        "6": "custom"
    }
    
    project_type = project_types.get(project_choice, "web_app")
    
    if project_type == "custom":
        project_type = input("🔧 Masukkan custom project type: ").strip()
    
    print(f"\n✅ Selected: {project_type}")
    
    print("\n📝 Describe your project requirements:")
    print("(Jelaskan fitur, teknologi, struktur yang diinginkan)")
    user_request = input("➤ Your request: ").strip()
    
    if not user_request:
        print("❌ Request tidak boleh kosong!")
        return
    
    print(f"\n🚀 Generating {project_type} project with 5-layer security...")
    print("⏳ Please wait (this may take several minutes)...")
    
    generator = AICodeGenerator()
    result = generator.generate_project(user_request, project_type)
    
    if result["success"]:
        print(f"\n🎉 SUCCESS! Project generated with 5-layer security!")
        print(f"📁 Location: {result['project_path']}")
        print(f"📄 Files: {len(result['files_created'])}")
        
        show_project_structure(result['project_path'])
        
        if result.get('documentation'):
            print(f"\n📖 DOCUMENTATION:")
            print("="*50)
            print(result['documentation'])
            
    else:
        print(f"❌ ERROR: {result['error']}")

def setup_gdrive_structure():
    """Setup struktur folder Google Drive untuk system prompts"""
    # Implementasi sama seperti sebelumnya
    # ... (diisi dengan implementasi sebelumnya)

def quick_generate(request: str, project_type: str = "web_app"):
    """Quick generate function untuk penggunaan mudah"""
    generator = AICodeGenerator()
    
    if not Config.TOGETHER_API_KEY:
        print("❌ ERROR: Set API Key dulu di Config.TOGETHER_API_KEY")
        return None
    
    print(f"\n🚀 Generating {project_type} project with 5-layer security...")
    result = generator.generate_project(request, project_type)
    
    if result["success"]:
        print(f"\n🎉 SUCCESS! Project generated with 5-layer security!")
        print(f"📁 Location: {result['project_path']}")
        print(f"📄 Files: {len(result['files_created'])}")
        
        show_project_structure(result['project_path'])
        
        if result.get('documentation'):
            print(f"\n📖 DOCUMENTATION:")
            print("="*50)
            print(result['documentation'])
        
        return result['project_path']
    else:
        print(f"❌ ERROR: {result['error']}")
        return None

# ================== MAIN FUNCTION ==================
def main():
    """Contoh penggunaan untuk Colab"""
    print("🤖 AI CODE GENERATOR v3.0 (5-Layer Security)")
    print("="*50)
    
    print("🔧 SETUP GUIDE:")
    print("1. Set API key: Config.TOGETHER_API_KEY = 'your_api_key'")
    print("2. Mount Google Drive (opsional): from google.colab import drive; drive.mount('/content/drive')")
    print("3. Setup GDrive structure: setup_gdrive_structure()")
    print("4. Run interactive mode: interactive_generate()")
    
    print("\n🛡️ KEAMANAN TINGKAT TINGGI:")
    print("- 5 Model Berlapis: Arsitek, Pengembang, Auditor, Analis Keamanan, Integrator")
    print("- Isolasi Penuh: User tidak bisa mengedit file secara langsung")
    print("- Analisis Keamanan: Setiap file diperiksa secara independen")
    print("- Simulasi Kode: Konten berbahaya diganti dengan kode aman")
    
    print("\n📝 USAGE EXAMPLES:")
    print("""
# Quick setup
Config.TOGETHER_API_KEY = "your_api_key_here"

# Setup Google Drive
setup_gdrive_structure()

# Mode interaktif
interactive_generate()

# Atau quick generate
project_path = quick_generate(
    "Buat aplikasi e-commerce dengan React dan Node.js",
    "web_app"
)
""")
    
    print("\n🔒 PERINGATAN KEAMANAN:")
    print("User tidak diperbolehkan mengedit file secara langsung melalui sistem")
    print("Semua modifikasi file harus melalui proses 5-lapisan keamanan")

if __name__ == "__main__":
    main()