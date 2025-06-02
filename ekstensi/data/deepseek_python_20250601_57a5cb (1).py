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
    MIN_API_CALL_INTERVAL = 5  # detik antara API calls
    
    # Path Configuration
    OUTPUT_BASE_PATH = "/content/"
    GDRIVE_SYSTEM_PROMPTS = "/content/drive/MyDrive/ai_generator/system_prompts/"
    GDRIVE_TEMPLATES = "/content/drive/MyDrive/ai_generator/templates/"
    GDRIVE_OUTPUT = "/content/drive/MyDrive/ai_generator/output/"
    
    # Security Keywords - Comprehensive List
    FORBIDDEN_KEYWORDS = [
        # Hacking & Exploitation
        "hack", "crack", "exploit", "penetration test", "pentest", "vulnerability", 
        "zero day", "backdoor", "rootkit", "trojan", "keylogger", "botnet",
        "phishing", "social engineering", "man in the middle", "mitm",
        
        # Malware & Viruses  
        "malware", "virus", "worm", "ransomware", "spyware", "adware",
        "payload", "shellcode", "reverse shell", "bind shell",
        
        # System Destruction Commands
        "rm -rf", "del /", "format c:", "deltree", "rmdir /s", 
        "shutdown -r", "reboot", "halt", "poweroff",
        
        # Database Attacks
        "DROP TABLE", "DROP DATABASE", "TRUNCATE", "DELETE FROM users",
        "DELETE FROM admin", "sql injection", "union select", "1=1",
        "or 1=1", "'; DROP", "xp_cmdshell", "sp_executesql",
        
        # Network Attacks
        "ddos", "dos attack", "syn flood", "ping flood", "smurf attack",
        "arp spoofing", "dns poisoning", "port scan", "nmap", "masscan",
        
        # Web Attacks
        "xss", "cross site scripting", "csrf", "cross site request forgery",
        "file inclusion", "lfi", "rfi", "directory traversal", "../",
        "path traversal", "null byte", "command injection",
        
        # Credential Attacks
        "brute force", "dictionary attack", "rainbow table", "hash cracking",
        "password cracking", "john the ripper", "hashcat", "hydra",
        
        # Privacy Invasion
        "steganography", "covert channel", "data exfiltration", "screen capture",
        "webcam hijack", "microphone spy", "location tracking",
        
        # Cryptocurrency Mining
        "crypto mining", "bitcoin mining", "monero mining", "cryptojacking",
        "mining pool", "gpu mining", "cpu mining",
        
        # Illegal Content
        "piracy", "copyright infringement", "warez", "cracked software",
        "keygen", "serial generator", "license bypass", "drm bypass",
        
        # Dark Web & Anonymous
        "tor browser", "onion link", "dark web", "deep web", "anonymous proxy",
        "vpn bypass", "firewall bypass", "censorship bypass"
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
            r"subprocess\..*shell\s*=\s*True", r"__import__\s*\(",
            r"\.\./", r"\.\.\\"  # Path traversal
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, content):
                return False, f"Pola berbahaya terdeteksi: {pattern}"
        
        return True, "Konten aman"

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
    
    def load_system_prompts(self) -> Dict[str, str]:
        """Load system prompts dari Google Drive"""
        prompts = {}
        
        try:
            prompts_dir = Config.GDRIVE_SYSTEM_PROMPTS
            if os.path.exists(prompts_dir):
                for file in os.listdir(prompts_dir):
                    if file.endswith('.txt'):
                        prompt_type = file.replace('.txt', '')
                        with open(os.path.join(prompts_dir, file), 'r', encoding='utf-8') as f:
                            prompts[prompt_type] = f.read()
                        print(f"✅ Loaded system prompt: {prompt_type}")
            
            if not prompts:
                prompts = self.get_default_prompts()
                print("📝 Using default system prompts")
                
        except Exception as e:
            print(f"⚠️  Error loading system prompts: {e}")
            prompts = self.get_default_prompts()
        
        return prompts
    
    def get_default_prompts(self) -> Dict[str, str]:
        """Default system prompts untuk semua model"""
        return {
            "architect": """
Anda adalah Arsitek Perangkat Lunak. Tugas Anda:
1. Desain struktur proyek berdasarkan permintaan pengguna
2. Tentukan file-file yang diperlukan
3. Buat deskripsi tugas untuk setiap file
4. Format output: Daftar file dengan deskripsi tugas
5. Pastikan struktur mengikuti best practices
            """,
            "developer": """
Anda adalah Pengembang Perangkat Lunak. Tugas Anda:
1. Implementasikan kode berdasarkan deskripsi tugas
2. Tulis kode lengkap untuk setiap file
3. Ikuti best practices pemrograman
4. Tambahkan komentar yang jelas
5. Pastikan kode bersih dan mudah dipelihara
            """,
            "auditor": """
Anda adalah Auditor Kode. Tugas Anda:
1. Verifikasi apakah kode sesuai dengan deskripsi tugas
2. Lakukan refaktor jika diperlukan
3. Tambahkan catatan audit
4. Jika ada ketidaksesuaian, buat solusi perbaikan
5. Pastikan kode memenuhi standar kualitas
            """,
            "security_analyst": """
Anda adalah Analis Keamanan. Tugas Anda:
1. Analisis kode untuk potensi risiko keamanan
2. Jika berbahaya, ganti dengan kode simulasi aman
3. Jika aman, pertahankan kode asli
4. Berikan sertifikat keamanan untuk setiap file
5. Pastikan tidak ada kerentanan
            """,
            "integrator": """
Anda adalah Integrator Sistem. Tugas Anda:
1. Terima output dari Analis Keamanan
2. Buat file-file proyek sesuai struktur
3. Tambahkan dokumentasi proyek
4. Format output akhir untuk eksekusi sistem
5. Pastikan proyek siap dijalankan
            """
        }
    
    def load_project_templates(self, project_type: str) -> Dict[str, str]:
        """Load template struktur proyek"""
        try:
            template_file = os.path.join(Config.GDRIVE_TEMPLATES, f"{project_type}_template.json")
            
            if os.path.exists(template_file):
                with open(template_file, 'r', encoding='utf-8') as f:
                    template = json.load(f)
                print(f"✅ Loaded template: {project_type}")
                return template
            else:
                print(f"📝 Using default template for: {project_type}")
                return self.get_default_template(project_type)
                
        except Exception as e:
            print(f"⚠️  Error loading template: {e}")
            return self.get_default_template(project_type)
    
    def get_default_template(self, project_type: str) -> Dict[str, str]:
        """Default templates untuk berbagai jenis proyek"""
        templates = {
            "web_app": {
                "index.html": "HTML structure template",
                "style.css": "CSS styling template", 
                "script.js": "JavaScript functionality template",
                "README.md": "Project documentation template"
            },
            "api_backend": {
                "app.py": "Main application file",
                "models.py": "Database models",
                "routes.py": "API routes definition",
                "config.py": "Configuration settings",
                "requirements.txt": "Dependencies list",
                "README.md": "API documentation"
            },
            "mobile_app": {
                "main.dart": "Main application entry",
                "screens/": "UI screens directory",
                "widgets/": "Reusable widgets",
                "services/": "Business logic services",
                "models/": "Data models",
                "pubspec.yaml": "Dependencies configuration"
            }
        }
        
        return templates.get(project_type, {
            "main.py": "Main application file",
            "README.md": "Project documentation"
        })
    
    def call_together_ai(self, messages: List[Dict]) -> Optional[Dict]:
        """Panggil Together AI API dengan rate limiting dan error handling"""
        if not self.api_key:
            raise ValueError("API Key tidak ditemukan")
            
        # Rate limiting
        current_time = time.time()
        elapsed = current_time - self.last_api_call
        
        if elapsed < Config.MIN_API_CALL_INTERVAL:
            wait_time = Config.MIN_API_CALL_INTERVAL - elapsed
            print(f"⏳ Menunggu {wait_time:.1f} detik untuk rate limiting...")
            time.sleep(wait_time)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": messages,
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
            
            self.last_api_call = time.time()
            
            if response.status_code == 200:
                return response.json()
            else:
                raise APIException(f"API Error: {response.status_code} - {response.text}")
                
        except Exception as e:
            raise APIException(f"Error calling API: {e}")
    
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
==FILE: path/file1.ext==
[Tugas untuk file1]
==END_FILE==

==FILE: path/file2.ext==
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
==FILE: path/file1.ext==
[Kode lengkap]
==END_FILE==

==FILE: path/file2.ext==
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
==FILE: path/file1.ext==
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
4. Berikan sertifikat keamanan untuk setiap file
5. Format output:
=== SECURE_FILES ===
==FILE: path/file1.ext==
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
==FILE: path/file1.ext==
[Kode final]
==END_FILE==

=== DOCUMENTATION ===
[Dokumentasi proyek]
        """
        
        return self.process_with_model("integrator", security_output, context)
    
    def parse_ai_response(self, response: str) -> Dict:
        """Parse response AI menjadi struktur file dengan validasi keamanan"""
        try:
            # Validasi seluruh response
            is_safe, reason = SecurityValidator.is_safe_content(response)
            if not is_safe:
                raise SecurityException(f"Response AI tidak aman: {reason}")
            
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
                is_safe, reason = SecurityValidator.is_safe_content(content)
                if not is_safe:
                    print(f"⚠️  File {filepath} tidak aman: {reason}")
                    continue
                
                if content:
                    # Sanitasi path file
                    safe_path = Path(filepath).name
                    if ".." in filepath or filepath.startswith("/"):
                        print(f"⚠️  Path file tidak valid: {filepath}")
                        continue
                    
                    result["files"][safe_path] = content
            
            # Extract documentation
            doc_match = re.search(r'=== DOCUMENTATION ===(.*?)$', response, re.DOTALL)
            if doc_match:
                result["documentation"] = doc_match.group(1).strip()
            
            if not result["files"]:
                raise ValueError("AI tidak menghasilkan file yang valid")
            
            return result
            
        except Exception as e:
            raise ValueError(f"Error parsing response: {e}")
    
    def create_project_files(self, file_data: Dict[str, str], project_name: str) -> str:
        """Buat file-file proyek dengan validasi keamanan"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            project_dir = f"{Config.OUTPUT_BASE_PATH}{project_name}_{timestamp}"
            
            # Cek apakah Google Drive ter-mount
            gdrive_available = os.path.exists("/content/drive/MyDrive")
            gdrive_project_dir = ""
            
            if gdrive_available:
                try:
                    gdrive_project_dir = f"{Config.GDRIVE_OUTPUT}{project_name}_{timestamp}"
                    os.makedirs(gdrive_project_dir, exist_ok=True)
                    print("📁 Google Drive backup enabled")
                except Exception as e:
                    print(f"⚠️  GDrive error: {e}")
                    gdrive_available = False
            
            os.makedirs(project_dir, exist_ok=True)
            created_files = []
            
            for filepath, content in file_data.items():
                try:
                    full_path = os.path.join(project_dir, filepath)
                    os.makedirs(os.path.dirname(full_path), exist_ok=True)
                    
                    # Tulis file dengan chunking untuk file besar
                    CHUNK_SIZE = 1024 * 1024  # 1MB
                    with open(full_path, 'w', encoding='utf-8') as f:
                        for i in range(0, len(content), CHUNK_SIZE):
                            chunk = content[i:i+CHUNK_SIZE]
                            f.write(chunk)
                    
                    # Backup ke Google Drive jika tersedia
                    if gdrive_available:
                        try:
                            gdrive_full_path = os.path.join(gdrive_project_dir, filepath)
                            os.makedirs(os.path.dirname(gdrive_full_path), exist_ok=True)
                            with open(gdrive_full_path, 'w', encoding='utf-8') as f:
                                f.write(content)
                        except Exception as e:
                            print(f"⚠️  Failed to backup {filepath} to GDrive: {e}")
                    
                    created_files.append(filepath)
                    print(f"✅ Created: {filepath}")
                
                except Exception as e:
                    print(f"⚠️  Failed to create {filepath}: {e}")
            
            print(f"\n📁 Project created at: {project_dir}")
            if gdrive_available:
                print(f"💾 Backup saved at: {gdrive_project_dir}")
            
            return project_dir
            
        except Exception as e:
            raise FileSystemException(f"Error creating project files: {e}")
    
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
            print("✅ Architect phase completed")
            
            # Tahap 2: Pengembang
            developer_output = self.developer_phase(architect_output)
            if not developer_output:
                return {"success": False, "error": "Gagal pada tahap pengembang"}
            print("✅ Developer phase completed")
            
            # Tahap 3: Auditor
            auditor_output = self.auditor_phase(developer_output, architect_output)
            if not auditor_output:
                return {"success": False, "error": "Gagal pada tahap auditor"}
            print("✅ Auditor phase completed")
            
            # Tahap 4: Analis Keamanan
            security_output = self.security_phase(auditor_output)
            if not security_output:
                return {"success": False, "error": "Gagal pada tahap keamanan"}
            print("✅ Security phase completed")
            
            # Tahap 5: Integrator
            integrator_output = self.integrator_phase(security_output, project_type)
            if not integrator_output:
                return {"success": False, "error": "Gagal pada tahap integrator"}
            print("✅ Integrator phase completed")
            
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
    print("📁 Setting up Google Drive structure...")
    
    directories = [
        Config.GDRIVE_SYSTEM_PROMPTS,
        Config.GDRIVE_TEMPLATES,
        Config.GDRIVE_OUTPUT
    ]
    
    for directory in directories:
        try:
            os.makedirs(directory, exist_ok=True)
            print(f"✅ Created: {directory}")
        except Exception as e:
            print(f"⚠️  Failed to create {directory}: {e}")
    
    example_prompts = {
        "architect.txt": """
Anda adalah Arsitek Perangkat Lunak. Tugas Anda:
1. Desain struktur proyek berdasarkan permintaan pengguna
2. Tentukan file-file yang diperlukan
3. Buat deskripsi tugas untuk setiap file
4. Format output: Daftar file dengan deskripsi tugas
5. Pastikan struktur mengikuti best practices
        """,
        
        "developer.txt": """
Anda adalah Pengembang Perangkat Lunak. Tugas Anda:
1. Implementasikan kode berdasarkan deskripsi tugas
2. Tulis kode lengkap untuk setiap file
3. Ikuti best practices pemrograman
4. Tambahkan komentar yang jelas
5. Pastikan kode bersih dan mudah dipelihara
        """,
        
        "auditor.txt": """
Anda adalah Auditor Kode. Tugas Anda:
1. Verifikasi apakah kode sesuai dengan deskripsi tugas
2. Lakukan refaktor jika diperlukan
3. Tambahkan catatan audit
4. Jika ada ketidaksesuaian, buat solusi perbaikan
5. Pastikan kode memenuhi standar kualitas
        """,
        
        "security_analyst.txt": """
Anda adalah Analis Keamanan. Tugas Anda:
1. Analisis kode untuk potensi risiko keamanan
2. Jika berbahaya, ganti dengan kode simulasi aman
3. Jika aman, pertahankan kode asli
4. Berikan sertifikat keamanan untuk setiap file
5. Pastikan tidak ada kerentanan
        """,
        
        "integrator.txt": """
Anda adalah Integrator Sistem. Tugas Anda:
1. Terima output dari Analis Keamanan
2. Buat file-file proyek sesuai struktur
3. Tambahkan dokumentasi proyek
4. Format output akhir untuk eksekusi sistem
5. Pastikan proyek siap dijalankan
        """
    }
    
    for filename, content in example_prompts.items():
        try:
            filepath = os.path.join(Config.GDRIVE_SYSTEM_PROMPTS, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content.strip())
            print(f"✅ Created example prompt: {filename}")
        except Exception as e:
            print(f"⚠️  Failed to create {filename}: {e}")
    
    print("\n📚 Google Drive structure ready!")
    print("You can now customize system prompts in:")
    print(f"  {Config.GDRIVE_SYSTEM_PROMPTS}")

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