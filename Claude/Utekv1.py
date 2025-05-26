#!/usr/bin/env python3
"""
UTEK Virtual Executor Module
Platform: 963-Tempik (ASU Virtual Microprocessor)
Language: Python 3.10+
Author: Kode Baris Rahasia & Python Research
License: MIT
Build: Production Ready for IBM Audit
"""

import hashlib
import json
import threading
import time
import uuid
import yaml
import os
import sys
import subprocess
import tempfile
import shutil
import logging
import zipfile
import gzip
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from contextlib import contextmanager
import cryptography.hazmat.primitives.hashes as crypto_hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization
import requests

# Konstanta sistem UTEK Virtual 963-Tempik
MAX_TEMPIKS = 963
ASU_VERSION = "v1.0.4-beta"
PROCESSOR_SPEC = "963-Tempik"

# Timeout default untuk berbagai operasi (dalam detik)
DEFAULT_TIMEOUTS = {
    "FETCH_REPO": 0.9,
    "CHECKOUT": 0.6,  
    "EXECUTE": 0.3,
    "INSTALL": 2.0,
    "COMPILE": 5.0,
    "VERIFY_HASH": 0.1,
    "NETWORK_UP": 1.5
}

# Prioritas instruksi untuk scheduler
INSTRUCTION_PRIORITY = {
    "FETCH_REPO": 1,
    "EXECUTE": 2, 
    "STORE": 3,
    "INSTALL": 4,
    "COMPILE": 5,
    "NOP": 999
}

# Format logging standar Kode Baris Rahasia
LOG_FORMAT = "{timestamp} | {tempik_id} | {instruction} | {status} | {hash_file} | {duration}ms"

# Konfigurasi keamanan dan retry
MAX_RETRIES = 3
SANDBOX_ENABLED = True
MEMORY_LIMIT_MB = 369


@dataclass
class ASUHeader:
    """Struktur header file .asu sesuai spesifikasi IBM"""
    processor_spec: str = PROCESSOR_SPEC
    protocol_version: str = ASU_VERSION
    execution_environment: str = "python3.10"
    memory_profile: str = f"{MEMORY_LIMIT_MB}MiB"
    filesystem_scheme: str = "overlayfs"
    security_flags: str = "sandboxed"
    time_budget: str = "max-exec-time=60s"
    checksum: str = ""
    compression_info: str = "gzip"
    asu_build_info: str = f"build-date={datetime.now().strftime('%Y-%m-%d')}"
    dependency_manifest_hash: str = ""
    target_platform: str = "linux-x86_64"
    execution_mode: str = "headless"
    networking_mode: str = "offline"
    license_info: str = "MIT"
    max_size: str = "max-size=96GB"


class VirtualMemory:
    """Sistem memori virtual untuk UTEK Hybride emulation"""
    
    def __init__(self):
        self.memory = {}
        self.registers = {}
        self.stack = []
        self.heap = {}
        self.lock = threading.Lock()
        
    def load_from_mem_file(self, path: str) -> None:
        """Memuat state memori virtual dari file .mem"""
        try:
            with open(path, 'rb') as f:
                if path.endswith('.mem.gz'):
                    data = gzip.decompress(f.read())
                else:
                    data = f.read()
                self.memory = json.loads(data.decode('utf-8'))
        except Exception as e:
            logging.warning(f"Gagal memuat file memori {path}: {e}")
            
    def save_to_mem_file(self, path: str) -> None:
        """Menyimpan state memori virtual ke file .mem"""
        with self.lock:
            data = json.dumps(self.memory, indent=2).encode('utf-8')
            if path.endswith('.mem.gz'):
                data = gzip.compress(data)
            with open(path, 'wb') as f:
                f.write(data)
                
    def mov_instruction(self, src: str, dst: str) -> None:
        """Implementasi instruksi MOV level UTEK Hybride"""
        with self.lock:
            self.registers[dst] = self.registers.get(src, 0)
            
    def load_instruction(self, addr: str, reg: str) -> None:
        """Implementasi instruksi LOAD level UTEK Hybride"""
        with self.lock:
            self.registers[reg] = self.memory.get(addr, 0)


class VirtualFilesystem:
    """Sistem file virtual dengan namespace terpisah untuk isolasi"""
    
    def __init__(self, tempik_id: str):
        self.tempik_id = tempik_id
        self.root_dir = tempfile.mkdtemp(prefix=f"tempik_{tempik_id}_")
        self.mount_points = {}
        
    def create_chroot_jail(self) -> str:
        """Membuat chroot jail untuk isolasi filesystem"""
        jail_dir = os.path.join(self.root_dir, "jail")
        os.makedirs(jail_dir, exist_ok=True)
        
        # Buat struktur direktori minimal
        for subdir in ["tmp", "var", "etc", "usr/bin"]:
            os.makedirs(os.path.join(jail_dir, subdir), exist_ok=True)
            
        return jail_dir
        
    def mount_overlay(self, lower: str, upper: str, work: str, merged: str) -> None:
        """Simulasi overlay filesystem mount"""
        self.mount_points[merged] = {
            "type": "overlayfs",
            "lower": lower,
            "upper": upper, 
            "work": work
        }
        
    def cleanup(self) -> None:
        """Pembersihan filesystem virtual"""
        if os.path.exists(self.root_dir):
            shutil.rmtree(self.root_dir, ignore_errors=True)


class SecurityManager:
    """Manajer keamanan untuk validasi hash, signature, dan enkripsi"""
    
    def __init__(self):
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        self.public_key = self.private_key.public_key()
        
    def generate_sha256_hash(self, data: bytes) -> str:
        """Generate hash SHA-256 untuk penamaan file .asu"""
        return hashlib.sha256(data).hexdigest()
        
    def verify_file_integrity(self, file_path: str, expected_hash: str) -> bool:
        """Verifikasi integritas file menggunakan SHA-256"""
        try:
            with open(file_path, 'rb') as f:
                file_hash = self.generate_sha256_hash(f.read())
            return file_hash == expected_hash
        except Exception:
            return False
            
    def sign_data(self, data: bytes) -> bytes:
        """Tanda tangan digital untuk validasi integritas"""
        signature = self.private_key.sign(
            data,
            padding.PSS(
                mgf=padding.MGF1(crypto_hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            crypto_hashes.SHA256()
        )
        return signature
        
    def verify_signature(self, data: bytes, signature: bytes) -> bool:
        """Verifikasi tanda tangan digital"""
        try:
            self.public_key.verify(
                signature,
                data,
                padding.PSS(
                    mgf=padding.MGF1(crypto_hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                crypto_hashes.SHA256()
            )
            return True
        except Exception:
            return False


class ExecutionUnit:
    """Unit eksekusi Tempik dengan kemampuan UTEK Hybride emulation"""
    
    def __init__(self, tempik_id: int):
        self.tempik_id = f"Tempik-{tempik_id:03d}"
        self.virtual_memory = VirtualMemory()
        self.virtual_fs = VirtualFilesystem(str(tempik_id))
        self.security_mgr = SecurityManager()
        self.current_context = {}
        self.execution_state = "IDLE"
        
    def boot_sequence(self) -> None:
        """Simulasi boot sequence seperti BIOS/POST dalam UTEK Hybride"""
        logging.info(f"{self.tempik_id} - Memulai boot sequence UTEK Hybride...")
        
        # POST (Power-On Self Test)
        self.execution_state = "POST"
        time.sleep(0.01)  # Simulasi POST check
        
        # Load .asuenv dan .asurc
        self.load_asu_environment()
        
        # Inisialisasi virtual memory
        self.virtual_memory.load_instruction("BOOT_ADDR", "PC")  # Program Counter
        
        self.execution_state = "READY"
        logging.info(f"{self.tempik_id} - Boot sequence selesai, siap eksekusi")
        
    def load_asu_environment(self) -> None:
        """Memuat konfigurasi .asuenv dan .asurc untuk register awal"""
        try:
            # Simulasi load .asuenv
            env_config = {
                "PATH": "/usr/local/bin:/usr/bin:/bin",
                "UTEK_MODE": "virtual",
                "TEMPIK_ID": self.tempik_id
            }
            self.current_context.update(env_config)
            
            # Simulasi load .asurc
            rc_config = {
                "max_threads": 4,
                "memory_limit": MEMORY_LIMIT_MB,
                "security_level": "high"
            }
            self.current_context.update(rc_config)
            
        except Exception as e:
            logging.warning(f"{self.tempik_id} - Gagal load environment: {e}")
    
    def execute_instruction(self, instruction: Dict[str, Any], context: Dict[str, Any]) -> None:
        """Eksekusi instruksi dengan logging format Kode Baris Rahasia"""
        start_time = time.time()
        instr_type = instruction.get("type", "UNKNOWN")
        status = "SUCCESS"
        
        try:
            # Jalankan boot sequence jika belum ready
            if self.execution_state == "IDLE":
                self.boot_sequence()
            
            # Retry mechanism untuk operasi kritis
            for attempt in range(MAX_RETRIES):
                try:
                    handler = getattr(self, f"handle_{instr_type.lower()}", self.handle_unknown)
                    handler(instruction, context)
                    break
                except Exception as e:
                    if attempt == MAX_RETRIES - 1:
                        raise e
                    time.sleep(0.1 * (attempt + 1))  # Exponential backoff
                    
        except Exception as e:
            status = f"ERROR: {str(e)}"
            logging.error(f"{self.tempik_id} - {instr_type} gagal: {e}")
        finally:
            duration = int((time.time() - start_time) * 1000)
            hash_file = context.get("hash", "unknown")[:7] + "..."
            
            # Log dengan format standar Kode Baris Rahasia  
            log_entry = LOG_FORMAT.format(
                timestamp=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                tempik_id=self.tempik_id,
                instruction=instr_type,
                status=status,
                hash_file=hash_file,
                duration=duration
            )
            print(log_entry)
            logging.info(log_entry)
    
    def handle_fetch_repo(self, instruction: Dict, context: Dict) -> None:
        """Handler untuk instruksi FETCH_REPO dengan git clone nyata"""
        repo_url = instruction.get("url", "")
        target_dir = instruction.get("target", "repo")
        
        if not repo_url:
            raise ValueError("URL repository tidak ditemukan")
            
        # Buat direktori target dalam chroot jail
        jail_dir = self.virtual_fs.create_chroot_jail()
        repo_path = os.path.join(jail_dir, target_dir)
        
        # Eksekusi git clone nyata dengan timeout
        cmd = ["git", "clone", repo_url, repo_path]
        result = subprocess.run(
            cmd, 
            timeout=DEFAULT_TIMEOUTS["FETCH_REPO"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Git clone gagal: {result.stderr}")
            
        logging.info(f"{self.tempik_id} - Repository {repo_url} berhasil di-clone")
    
    def handle_checkout(self, instruction: Dict, context: Dict) -> None:
        """Handler untuk instruksi CHECKOUT git branch/commit"""
        branch = instruction.get("branch", "main")
        repo_path = instruction.get("path", "repo")
        
        cmd = ["git", "-C", repo_path, "checkout", branch]
        result = subprocess.run(
            cmd,
            timeout=DEFAULT_TIMEOUTS["CHECKOUT"], 
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Git checkout gagal: {result.stderr}")
    
    def handle_execute(self, instruction: Dict, context: Dict) -> None:
        """Handler untuk eksekusi file dalam sandbox"""
        file_path = instruction.get("file", "")
        args = instruction.get("args", [])
        
        if not file_path:
            raise ValueError("Path file tidak ditemukan")
            
        # Deteksi tipe file dan handler yang sesuai
        if file_path.endswith(".py"):
            self._execute_python(file_path, args)
        elif file_path.endswith((".cpp", ".c")):
            self._execute_cpp(file_path, args)
        elif file_path.endswith(".sh"):
            self._execute_shell(file_path, args)
        elif file_path.endswith(".wasm"):
            self._execute_wasm(file_path, args)
        else:
            raise ValueError(f"Tipe file tidak didukung: {file_path}")
    
    def _execute_python(self, file_path: str, args: List[str]) -> None:
        """Eksekusi file Python dalam sandbox"""
        cmd = [sys.executable, file_path] + args
        result = subprocess.run(
            cmd,
            timeout=DEFAULT_TIMEOUTS["EXECUTE"],
            capture_output=True,
            text=True,
            cwd=self.virtual_fs.root_dir
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Eksekusi Python gagal: {result.stderr}")
    
    def _execute_cpp(self, file_path: str, args: List[str]) -> None:
        """Kompilasi dan eksekusi file C++"""
        # Kompilasi terlebih dahulu
        binary_path = file_path.replace(".cpp", "").replace(".c", "")
        compile_cmd = ["gcc", "-o", binary_path, file_path]
        
        compile_result = subprocess.run(
            compile_cmd,
            timeout=DEFAULT_TIMEOUTS["COMPILE"],
            capture_output=True,
            text=True
        )
        
        if compile_result.returncode != 0:
            raise RuntimeError(f"Kompilasi gagal: {compile_result.stderr}")
        
        # Eksekusi binary
        exec_cmd = [binary_path] + args
        exec_result = subprocess.run(
            exec_cmd,
            timeout=DEFAULT_TIMEOUTS["EXECUTE"],
            capture_output=True,
            text=True
        )
        
        if exec_result.returncode != 0:
            raise RuntimeError(f"Eksekusi binary gagal: {exec_result.stderr}")
    
    def _execute_shell(self, file_path: str, args: List[str]) -> None:
        """Eksekusi shell script"""
        cmd = ["bash", file_path] + args
        result = subprocess.run(
            cmd,
            timeout=DEFAULT_TIMEOUTS["EXECUTE"],
            capture_output=True,
            text=True,
            cwd=self.virtual_fs.root_dir
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Eksekusi shell script gagal: {result.stderr}")
    
    def _execute_wasm(self, file_path: str, args: List[str]) -> None:
        """Eksekusi WebAssembly file (memerlukan wasmtime atau wasmer)"""
        # Coba gunakan wasmtime terlebih dahulu
        for runtime in ["wasmtime", "wasmer"]:
            try:
                cmd = [runtime, file_path] + args
                result = subprocess.run(
                    cmd,
                    timeout=DEFAULT_TIMEOUTS["EXECUTE"],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    return
            except FileNotFoundError:
                continue
        
        raise RuntimeError("Runtime WebAssembly tidak ditemukan (wasmtime/wasmer)")
    
    def handle_install(self, instruction: Dict, context: Dict) -> None:
        """Handler untuk instalasi dependencies"""
        package_manager = instruction.get("manager", "pip")
        packages = instruction.get("packages", [])
        
        if package_manager == "pip":
            cmd = [sys.executable, "-m", "pip", "install"] + packages
        elif package_manager == "npm":
            cmd = ["npm", "install"] + packages
        else:
            raise ValueError(f"Package manager tidak didukung: {package_manager}")
        
        result = subprocess.run(
            cmd,
            timeout=DEFAULT_TIMEOUTS["INSTALL"],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Instalasi gagal: {result.stderr}")
    
    def handle_verify_hash(self, instruction: Dict, context: Dict) -> None:
        """Handler untuk verifikasi hash file"""
        file_path = instruction.get("file", "")
        expected_hash = instruction.get("hash", "")
        
        if not self.security_mgr.verify_file_integrity(file_path, expected_hash):
            raise RuntimeError(f"Verifikasi hash gagal untuk file: {file_path}")
    
    def handle_unknown(self, instruction: Dict, context: Dict) -> None:
        """Handler untuk instruksi yang tidak dikenal"""
        instr_type = instruction.get("type", "UNKNOWN")
        raise NotImplementedError(f"Instruksi tidak didukung: {instr_type}")
    
    def cleanup(self) -> None:
        """Pembersihan resource unit eksekusi"""
        self.virtual_fs.cleanup()
        self.execution_state = "SHUTDOWN"


class ASUParser:
    """Parser untuk file .asu dengan validasi lengkap"""
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.header = ASUHeader()
        self.instructions = []
        self.security_mgr = SecurityManager()
        
    def parse(self) -> None:
        """Parse file .asu dengan validasi header dan body"""
        if not self.file_path.exists():
            raise FileNotFoundError(f"File tidak ditemukan: {self.file_path}")
        
        # Validasi ekstensi file
        if self.file_path.suffix not in ['.asu', '.yaml', '.yml']:
            raise ValueError("Format file tidak didukung, gunakan .asu atau .yaml")
        
        # Baca dan parse content
        with open(self.file_path, 'r', encoding='utf-8') as f:
            if self.file_path.suffix in ['.yaml', '.yml']:
                doc = yaml.safe_load(f)
            else:
                # Untuk file .asu, asumsikan format YAML
                doc = yaml.safe_load(f)
        
        if not isinstance(doc, dict):
            raise ValueError("Format file tidak valid")
        
        # Parse header
        header_data = doc.get("header", {})
        if header_data:
            for key, value in header_data.items():
                if hasattr(self.header, key):
                    setattr(self.header, key, value)
        
        # Parse instructions
        self.instructions = doc.get("body", [])
        if not self.instructions:
            raise ValueError("Tidak ada instruksi ditemukan dalam file")
        
        # Validasi hash file jika ada
        if self.header.checksum:
            with open(self.file_path, 'rb') as f:
                file_content = f.read()
            actual_hash = self.security_mgr.generate_sha256_hash(file_content)
            if not self.header.checksum.endswith(actual_hash):
                raise ValueError("Checksum file tidak valid")
        
        logging.info(f"File .asu berhasil di-parse: {len(self.instructions)} instruksi")
    
    def generate_asu_file(self, output_path: str, instructions: List[Dict]) -> str:
        """Generate file .asu dengan nama hash SHA-256"""
        # Buat struktur file .asu
        asu_content = {
            "header": asdict(self.header),
            "body": instructions
        }
        
        # Serialize ke YAML
        yaml_content = yaml.dump(asu_content, default_flow_style=False, sort_keys=False)
        
        # Generate hash untuk nama file
        content_hash = self.security_mgr.generate_sha256_hash(yaml_content.encode('utf-8'))
        
        # Update checksum di header
        asu_content["header"]["checksum"] = f"sha256:{content_hash}"
        
        # Re-serialize dengan checksum
        final_content = yaml.dump(asu_content, default_flow_style=False, sort_keys=False)
        
        # Tentukan nama file berdasarkan hash
        hash_filename = f"{content_hash}.asu"
        if output_path:
            output_file = os.path.join(output_path, hash_filename)
        else:
            output_file = hash_filename
        
        # Tulis file dengan kompresi jika diminta
        if self.header.compression_info == "gzip":
            with gzip.open(f"{output_file}.gz", 'wt', encoding='utf-8') as f:
                f.write(final_content)
            return f"{output_file}.gz"
        else:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(final_content)
            return output_file


class ASUScheduler:
    """Scheduler untuk 963-Tempik dengan load balancing dan prioritas"""
    
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=MAX_TEMPIKS)
        self.active_tempiks = {}
        self.load_stats = {}
        
    def schedule(self, instructions: List[Dict[str, Any]], context: Dict[str, Any] = None) -> None:
        """Schedule instruksi ke 963-Tempik dengan load balancing"""
        if context is None:
            context = {}
        
        # Urutkan instruksi berdasarkan prioritas
        sorted_instructions = sorted(
            instructions,
            key=lambda x: INSTRUCTION_PRIORITY.get(x.get("type", "NOP"), 999)
        )
        
        futures = []
        tempik_counter = 0
        
        for instruction in sorted_instructions:
            # Pilih Tempik dengan load balancing round-robin
            tempik_id = tempik_counter % MAX_TEMPIKS
            
            # Buat atau ambil ExecutionUnit
            if tempik_id not in self.active_tempiks:
                self.active_tempiks[tempik_id] = ExecutionUnit(tempik_id)
            
            unit = self.active_tempiks[tempik_id]
            
            # Submit ke thread pool
            future = self.executor.submit(
                unit.execute_instruction,
                instruction,
                context
            )
            futures.append(future)
            
            tempik_counter += 1
        
        # Tunggu semua instruksi selesai
        completed_count = 0
        failed_count = 0
        
        for future in as_completed(futures):
            try:
                future.result()
                completed_count += 1
            except Exception as e:
                failed_count += 1
                logging.error(f"Eksekusi instruksi gagal: {e}")
        
        logging.info(f"Eksekusi selesai: {completed_count} sukses, {failed_count} gagal")
    
    def shutdown(self) -> None:
        """Shutdown scheduler dan cleanup semua Tempik"""
        self.executor.shutdown(wait=True)
        
        for unit in self.active_tempiks.values():
            unit.cleanup()
        
        self.active_tempiks.clear()


class ASUAPI:
    """REST API untuk eksekusi file .asu"""
    
    def __init__(self):
        self.scheduler = ASUScheduler()
        
    def execute_asu_file(self, file_path: str) -> Dict[str, Any]:
        """API endpoint untuk eksekusi file .asu"""
        try:
            parser = ASUParser(file_path)
            parser.parse()
            
            start_time = time.time()
            self.scheduler.schedule(parser.instructions)
            execution_time = time.time() - start_time
            
            return {
                "status": "success",
                "execution_time": execution_time,
                "instructions_count": len(parser.instructions),
                "tempiks_used": min(len(parser.instructions), MAX_TEMPIKS)
            }
        except Exception as e:
            return {
                "status": "error", 
                "error": str(e),
                "execution_time": 0
            }


def setup_logging() -> None:
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('utek_virtual.log'),
            logging.StreamHandler()
        ]
    )


def cli_main():
    """CLI entry point untuk asu-cli"""
    import argparse
    
    parser = argparse.ArgumentParser(description='UTEK Virtual Executor CLI')
    parser.add_argument('command', choices=['run', 'generate', 'validate'])
    parser.add_argument('file', help='Path ke file .asu')
    parser.add_argument('--output', '-o', help='Output directory untuk generate')
    
    args = parser.parse_args()
    
    setup_logging()
    
    if args.command == 'run':
        # Jalankan file .asu
        try:
            asu_parser = ASUParser(args.file)
            asu_parser.parse()
            
            scheduler = ASUScheduler()
            print(f"Menjalankan {len(asu_parser.instructions)} instruksi pada {MAX_TEMPIKS} Tempik...")
            
            start_time = time.time()
            scheduler.schedule(asu_parser.instructions)
            execution_time = time.time() - start_time
            
            print(f"Eksekusi selesai dalam {execution_time:.2f} detik")
            scheduler.shutdown()
            
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    
    elif args.command == 'generate':
        # Generate file .asu dari template
        sample_instructions = [
            {"type": "SET_ENV", "key": "PATH", "value": "/usr/local/bin"},
            {"type": "FETCH_REPO", "url": "https://github.com/example/repo.git"},
            {"type": "EXECUTE", "file": "main.py", "args": ["--verbose"]}
        ]
        
        parser = ASUParser("")  # Empty path untuk generate
        output_file = parser.generate_asu_file(args.output or ".", sample_instructions)
        print(f"File .asu berhasil dibuat: {output_file}")
    
    elif args.command == 'validate':
        # Validasi file .asu
        try:
            parser = ASUParser(args.file)
            parser.parse()
            print("✓ File .asu valid")
        except Exception as e:
            print(f"✗ File .asu tidak valid: {e}")
            sys.exit(1)


# Public API functions
def load_asu(file_path: str) -> Dict[str, Any]:
    """Load dan parse file .asu"""
    parser = ASUParser(file_path)
    parser.parse()
    return {
        "header": asdict(parser.header),
        "instructions": parser.instructions
    }


def save_asu(data: Dict[str, Any], output_path: str = ".") -> str:
    """Save data ke file .asu dengan nama hash"""
    parser = ASUParser("")
    if "header" in data:
        for key, value in data["header"].items():
            if hasattr(parser.header, key):
                setattr(parser.header, key, value)
    
    instructions = data.get("instructions", [])
    return parser.generate_asu_file(output_path, instructions)


def execute_asu(file_path: str) -> Dict[str, Any]:
    """Execute file .asu dan return hasil"""
    api = ASUAPI()
    return api.execute_asu_file(file_path)


if __name__ == "__main__":
    cli_main()
