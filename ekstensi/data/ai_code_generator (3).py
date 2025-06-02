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
    def setup_logging(self):
        """Setup logging untuk Colab"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Load system prompts dan templates dari GDrive
        self.system_prompts = self.load_system_prompts()
        print(f"📚 Loaded {len(self.system_prompts)} system prompts")
        
        if not self.api_key:
            print("⚠️  WARNING: API Key Together AI belum diset!")
            print("Set API key di Config.TOGETHER_API_KEY")
    
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
            
            # Default prompts jika tidak ada di GDrive
            if not prompts:
                prompts = self.get_default_prompts()
                print("📝 Using default system prompts")
                
        except Exception as e:
            print(f"⚠️  Error loading system prompts: {e}")
            prompts = self.get_default_prompts()
        
        return prompts
    
    def get_default_prompts(self) -> Dict[str, str]:
        """Default system prompts jika GDrive tidak tersedia"""
        return {
            "web_app": """
Anda adalah expert web developer. Buat aplikasi web profesional dengan:
- Struktur HTML5 semantic yang clean
- CSS modern dengan responsive design
- JavaScript vanilla atau framework sesuai kebutuhan
- Best practices untuk performance dan accessibility
- Kode yang aman dan tidak mengandung vulnerability
- Dokumentasi dan komentar yang jelas
            """,
            "api_backend": """
Anda adalah expert backend developer. Buat REST API dengan:
- Arsitektur yang scalable dan maintainable
- Error handling yang proper
- Input validation dan sanitization
- Authentication dan authorization
- Database integration yang aman
- API documentation yang lengkap
- Security best practices
            """,
            "mobile_app": """
Anda adalah expert mobile developer. Buat aplikasi mobile dengan:
- UI/UX yang user-friendly
- Performance optimization
- Cross-platform compatibility
- Offline capability jika diperlukan
- Security measures untuk data protection
- Clean architecture pattern
            """
        }
    
    def load_project_templates(self, project_type: str) -> Dict[str, str]:
        """Load template struktur proyek dari Google Drive"""
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
        """Setup logging untuk Colab"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def create_focused_prompt(self, user_request: str, project_type: str) -> str:
        """Buat prompt gabungan system prompt (dari GDrive) + user input"""
        # Ambil system prompt sesuai project type
        system_prompt = self.system_prompts.get(project_type, self.system_prompts.get("web_app", ""))
        
        # Load template struktur jika ada
        template_structure = self.load_project_templates(project_type)
        
        return f"""
{system_prompt}

{ARCHITECTURE_FLOW}

TEMPLATE STRUKTUR YANG DIREKOMENDASIKAN:
{json.dumps(template_structure, indent=2)}

USER REQUEST (INPUT LANGSUNG):
{user_request}

INSTRUKSI PENTING:
1. Gunakan system prompt di atas sebagai panduan teknis
2. Ikuti template struktur yang sudah didefinisikan  
3. Setiap file harus berisi KODE ASLI yang berfungsi, bukan placeholder
4. Gunakan best practices untuk setiap bahasa pemrograman
5. Tambahkan komentar yang berguna dan dokumentasi
6. Pastikan kode bisa langsung dijalankan dan aman
7. WAJIB validasi semua input dan hindari vulnerability

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

Mulai sekarang, buat proyek berdasarkan USER REQUEST di atas!
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
        """Buat file-file proyek di Colab dan backup ke Google Drive"""
        try:
            # Buat folder proyek dengan timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            project_dir = f"{Config.OUTPUT_BASE_PATH}{project_name}_{timestamp}"
            
            # Buat juga backup di Google Drive jika tersedia
            gdrive_project_dir = f"{Config.GDRIVE_OUTPUT}{project_name}_{timestamp}"
            
            # Buat direktori
            os.makedirs(project_dir, exist_ok=True)
            
            # Coba buat di Google Drive juga
            try:
                os.makedirs(gdrive_project_dir, exist_ok=True)
                gdrive_available = True
                print("📁 Google Drive backup enabled")
            except:
                gdrive_available = False
                print("⚠️  Google Drive not mounted, saving to local only")
            
            created_files = []
            
            for filepath, content in file_data.items():
                # Buat path lengkap untuk local
                full_path = os.path.join(project_dir, filepath)
                
                # Buat direktori jika belum ada
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                
                # Tulis file ke local
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
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
            
            print(f"\n📁 Project created at: {project_dir}")
            if gdrive_available:
                print(f"💾 Backup saved at: {gdrive_project_dir}")
            
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

# ================== INTERACTIVE FUNCTIONS ==================
def interactive_generate():
    """Fungsi interaktif untuk generate proyek"""
    print("🤖 AI CODE GENERATOR - Interactive Mode")
    print("="*50)
    
    # Check API key
    if not Config.TOGETHER_API_KEY:
        print("❌ ERROR: API Key belum diset!")
        print("Set dengan: Config.TOGETHER_API_KEY = 'your_api_key'")
        return
    
    # Tampilkan project types yang tersedia
    print("\n📋 Available Project Types:")
    print("1. web_app - Web Application (HTML/CSS/JS)")
    print("2. api_backend - REST API Backend")
    print("3. mobile_app - Mobile Application")
    print("4. desktop_app - Desktop Application") 
    print("5. data_science - Data Science Project")
    print("6. custom - Custom Project Type")
    
    # Input project type
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
    
    # Input user request
    print("\n📝 Describe your project requirements:")
    print("(Jelaskan fitur, teknologi, struktur yang diinginkan)")
    user_request = input("➤ Your request: ").strip()
    
    if not user_request:
        print("❌ Request tidak boleh kosong!")
        return
    
    # Generate project
    print(f"\n🚀 Generating {project_type} project...")
    print("⏳ Please wait...")
    
    generator = AICodeGenerator()
    result = generator.generate_project(user_request, project_type)
    
    if result["success"]:
        print(f"\n🎉 SUCCESS! Project generated!")
        print(f"📁 Location: {result['project_path']}")
        print(f"📄 Files: {len(result['files_created'])}")
        
        # Tampilkan struktur
        show_project_structure(result['project_path'])
        
        # Tampilkan dokumentasi
        if result.get('documentation'):
            print(f"\n📖 DOCUMENTATION:")
            print("="*50)
            print(result['documentation'])
        
        # Tanya apakah ingin edit
        edit_choice = input("\n🛠️  Do you want to edit any file? (y/n): ").strip().lower()
        if edit_choice == 'y':
            edit_mode(result['project_path'])
            
    else:
        print(f"❌ ERROR: {result['error']}")

def edit_mode(project_path: str):
    """Mode interaktif untuk edit file"""
    print(f"\n🛠️  EDIT MODE - {project_path}")
    print("="*50)
    
    # List semua file dalam proyek
    files = []
    for root, dirs, filenames in os.walk(project_path):
        for filename in filenames:
            if not filename.startswith('.'):
                rel_path = os.path.relpath(os.path.join(root, filename), project_path)
                files.append(rel_path)
    
    if not files:
        print("❌ No files found in project")
        return
    
    print("📄 Available files:")
    for i, file in enumerate(files, 1):
        print(f"{i}. {file}")
    
    # Pilih file untuk edit
    try:
        file_choice = int(input(f"\n🎯 Select file to edit (1-{len(files)}): ")) - 1
        if 0 <= file_choice < len(files):
            selected_file = files[file_choice]
            file_path = os.path.join(project_path, selected_file)
            
            print(f"\n✅ Selected: {selected_file}")
            
            # Input edit request
            edit_request = input("📝 What changes do you want to make? ")
            
            if edit_request.strip():
                print("⏳ Processing edit request...")
                
                generator = AICodeGenerator()
                result = generator.edit_existing_file(file_path, edit_request)
                
                if result["success"]:
                    print("✅ File edited successfully!")
                    print(f"💾 Backup saved: {result['backup_path']}")
                else:
                    print(f"❌ Edit failed: {result['error']}")
            else:
                print("❌ Edit request cannot be empty!")
        else:
            print("❌ Invalid file selection!")
            
    except ValueError:
        print("❌ Please enter a valid number!")

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
    
    # Buat contoh system prompts
    example_prompts = {
        "web_app.txt": """
Anda adalah expert full-stack web developer dengan 10+ tahun pengalaman.
Buat aplikasi web modern dengan teknologi terkini:

WAJIB GUNAKAN:
- HTML5 semantic structure
- CSS3 dengan responsive design (mobile-first)
- JavaScript ES6+ dengan best practices
- Progressive Web App (PWA) capabilities jika relevan
- Accessibility (WCAG 2.1 AA compliance)
- SEO optimization
- Security headers dan input validation

STRUKTUR YANG DIREKOMENDASIKAN:
- index.html (entry point)
- assets/css/style.css (styling)
- assets/js/script.js (functionality)  
- assets/images/ (media files)
- manifest.json (PWA manifest)
- sw.js (service worker jika diperlukan)

PASTIKAN:
- Cross-browser compatibility
- Performance optimization
- Clean, maintainable code
- Comprehensive documentation
        """,
        
        "api_backend.txt": """
Anda adalah expert backend developer dengan expertise dalam RESTful API design.
Buat backend API yang scalable dan secure:

WAJIB GUNAKAN:
- RESTful API design principles
- Proper HTTP status codes dan error handling
- Input validation dan sanitization
- Authentication & Authorization (JWT/OAuth)
- Rate limiting dan security middleware
- Database integration dengan ORM/ODM
- API documentation (OpenAPI/Swagger)
- Logging dan monitoring

STRUKTUR YANG DIREKOMENDASIKAN:
- app.py/main.py (application entry)
- models/ (database models)
- routes/ (API endpoints)
- middleware/ (custom middleware)
- config/ (configuration files)
- utils/ (helper functions)
- tests/ (unit tests)
- requirements.txt/package.json (dependencies)

PASTIKAN:
- Scalable architecture
- Error handling yang robust
- Security best practices
- Performance optimization
- Comprehensive testing
        """
    }
    
    # Simpan contoh prompts
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
    
    print("🤖 AI CODE GENERATOR v2.0")
    print("="*50)
    
    # STEP 1: SET API KEY DULU!
    print("🔧 SETUP GUIDE:")
    print("1. Set API key: Config.TOGETHER_API_KEY = 'your_api_key'")
    print("2. Mount Google Drive (opsional): from google.colab import drive; drive.mount('/content/drive')")
    print("3. Setup GDrive structure: setup_gdrive_structure()")
    print("4. Run interactive mode: interactive_generate()")
    
    print("\n📝 USAGE EXAMPLES:")
    print("""
# Quick setup
Config.TOGETHER_API_KEY = "your_api_key_here"

# Setup Google Drive (opsional tapi direkomendasikan)
setup_gdrive_structure()

# Mode interaktif (recommended)
interactive_generate()

# Atau quick generate
project_path = quick_generate(
    "Buat todo app dengan React dan local storage",
    "web_app"
)
""")
    
    print("\n🔄 ARSITEKTUR BARU:")
    print("✅ User Input: Langsung interaksi (bukan dari file)")
    print("✅ System Prompts: Dari Google Drive (customizable)")
    print("✅ Templates: Dari Google Drive (reusable)")
    print("✅ Output: Local + Google Drive backup")
    print("✅ Interactive Mode: Edit files setelah generate")

if __name__ == "__main__":
    main()
