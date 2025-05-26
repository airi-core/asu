#!/usr/bin/env python3
"""
UTEK Virtual — 963-Tempik Executor for .asu Files
Proyek: ASU Virtual UTEK 963-Tempik
Pengembang: Kode Baris Rahasia & Python Research
Berdasarkan standar NDAS & MIKIR

ASU: Application Storage Usage
NDAS – Non-Deterministic Adaptive System
MIKIR – Modular Integrity Kernel for Isolated Runtime
UTEK – Universal Trusted Execution Kernel
"""

import asyncio
import hashlib
import json
import logging
import os
import shutil
import subprocess
import tempfile
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable, Tuple

import gzip
import lz4.frame  # pip install lz4
# import requests # Digunakan oleh NetworkUnit nantinya
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding as rsa_padding
# from pyfakefs.fake_filesystem_unittest import TestCase # Contoh untuk VirtualFS dengan pyfakefs
# from flask import Flask, request, jsonify # Contoh untuk API Remote

# Konfigurasi Logging Dasar
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%SZ'
)
logger = logging.getLogger(__name__)


class TempikStatus(Enum):
    """Status untuk setiap Tempik virtual dalam sistem 963-Tempik"""
    IDLE = "idle"
    FETCH = "fetch"
    DECODE = "decode"
    EXECUTE = "execute"
    MEMORY_ACCESS = "memory_access"
    WRITE_BACK = "write_back"
    BUSY = "busy" # Status umum saat pipeline aktif
    FAILED = "failed"
    COMPLETED = "completed"
    HALTED = "halted"


class InstruksiASU(Enum):
    """Daftar instruksi yang didukung dalam format .asu"""
    # ENVIRONMENT & KONFIGURASI
    SET_ENV = "SET_ENV"
    INIT_ENV = "INIT_ENV"
    SET_CONTEXT = "SET_CONTEXT"
    SYNC_CLOCK = "SYNC_CLOCK"
    AUTH = "AUTH"
    
    # PENGAMBILAN SUMBER & DEPENDENSI
    FETCH_REPO = "FETCH_REPO"
    CHECKOUT = "CHECKOUT"
    INSTALL = "INSTALL"
    UNPACK = "UNPACK"  
    MOUNT = "MOUNT"
    INJECT = "INJECT"
    COMPILE = "COMPILE"
    
    # EKSEKUSI & THREADING
    EXECUTE = "EXECUTE"
    CALL = "CALL"
    SPAWN_THREAD = "SPAWN_THREAD" # Akan dipertimbangkan implementasinya dengan Scheduler
    WAIT = "WAIT"
    DELEGATE_TO = "DELEGATE_TO"
    INVOKE_REMOTE = "INVOKE_REMOTE"
    HALT = "HALT"
    SHUTDOWN = "SHUTDOWN"
    
    # KEAMANAN & VERIFIKASI
    VERIFY_HASH = "VERIFY_HASH"
    VERIFY = "VERIFY" # Verifikasi signature
    SIGN = "SIGN" # Membuat signature
    DECRYPT = "DECRYPT"
    LOCK_EXEC = "LOCK_EXEC" # Mengunci eksekusi file .asu tertentu
    
    # AUDIT, LOGGING & EVENTS
    AUDIT_LOG = "AUDIT_LOG"
    LOG = "LOG"
    EMIT_EVENT = "EMIT_EVENT"
    
    # JARINGAN & DISTRIBUSI
    NETWORK_UP = "NETWORK_UP"
    MAP_PORT = "MAP_PORT"
    PUSH_RESULT = "PUSH_RESULT"
    
    # LOGIKA & KONTROL
    IF = "IF"
    ELSE = "ELSE"
    ENDIF = "ENDIF"
    ASSERT = "ASSERT"
    
    # EKSPOR & PEMBERSIHAN
    EXPORT = "EXPORT"
    CLEANUP = "CLEANUP"

    # Operasi dasar untuk ALU (contoh, bisa diperluas)
    ADD = "ADD"
    SUB = "SUB"
    AND = "AND"
    OR = "OR"
    XOR = "XOR"
    CMP = "CMP" # Compare
    JMP = "JMP" # Jump
    JZ = "JZ" # Jump if Zero
    JNZ = "JNZ" # Jump if Not Zero


@dataclass
class HeaderASU:
    """Header struktur file .asu sesuai spesifikasi ASU1"""
    processor_spec: str = "963-Tempik"
    protocol_version: str = "v1.0.4-beta"
    execution_environment: str = "python3.10"
    memory_profile: str = "512MiB"
    filesystem_scheme: str = "overlayfs"
    security_flags: str = "sandboxed"
    time_budget: str = "max-exec-time=60s"
    checksum_signature: str = "" # Signature dari hash file .asu (bukan hash file itu sendiri)
    compression_info: str = "gzip"
    asu_build_info: str = ""
    
    # Elemen standar baru sesuai audit
    dependency_manifest_hash: str = ""  # Hash dari manifest dependensi
    target_platform: str = "any"        # Platform target (e.g., wasm32, linux/amd64)
    execution_mode: str = "batch"       # Mode eksekusi (e.g., batch, interactive, service)
    networking_mode: str = "isolated"   # Mode jaringan (e.g., isolated, restricted, full)
    license_access_info: str = "proprietary" # Info lisensi atau hak akses
    max_size: str = "1GB"               # Ukuran maksimum file .asu yang diizinkan
    
    def to_dict(self) -> Dict[str, str]:
        return self.__dict__

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HeaderASU':
        return cls(**data)


@dataclass
class InstruksiEksekusi:
    """Representasi instruksi dalam body file .asu"""
    instruksi: InstruksiASU
    label: Optional[str] = None # Untuk JMP, CALL
    parameter: Dict[str, Any] = field(default_factory=dict)
    timeout: float = 30.0
    retry_count: int = 1 # Default retry 1 kali (total 2 attempt)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "instruksi": self.instruksi.value,
            "label": self.label,
            "parameter": self.parameter,
            "timeout": self.timeout,
            "retry_count": self.retry_count
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'InstruksiEksekusi':
        try:
            instruksi_enum = InstruksiASU(data['instruksi'])
        except ValueError:
            raise ValueError(f"Instruksi tidak dikenal: {data['instruksi']}")
        return cls(
            instruksi=instruksi_enum,
            label=data.get('label'),
            parameter=data.get('parameter', {}),
            timeout=data.get('timeout', 30.0),
            retry_count=data.get('retry_count', 1)
        )

@dataclass
class FileASU:
    """Representasi lengkap file .asu"""
    header: HeaderASU
    body: List[InstruksiEksekusi] = field(default_factory=list)
    # Struktur body bisa mendukung folder virtual
    # Contoh: body bisa menjadi Dict[str, Union[List[InstruksiEksekusi], Dict]]
    # Untuk saat ini, kita tetap List[InstruksiEksekusi] untuk body utama,
    # dan VirtualFS akan menangani path internal.
    virtual_fs_structure: Dict[str, Any] = field(default_factory=dict) # Untuk body.scripts, body.deps
    hash_sha256: str = "" # Hash dari konten file (header + body_json_string)
    
    def generate_hash(self) -> str:
        # Konten yang di-hash harus konsisten
        # Urutkan keys untuk memastikan konsistensi JSON string
        header_dict = self.header.to_dict()
        body_list = [instr.to_dict() for instr in self.body]
        
        content_for_hash = {
            "header": {k: header_dict[k] for k in sorted(header_dict.keys())},
            "body": body_list, # Urutan instruksi penting
            "virtual_fs_structure": self.virtual_fs_structure # Perlu dipertimbangkan bagaimana ini di-hash
        }
        
        content_str = json.dumps(content_for_hash, sort_keys=True)
        hash_obj = hashlib.sha256(content_str.encode('utf-8'))
        self.hash_sha256 = hash_obj.hexdigest()
        return self.hash_sha256

# --- Komponen Arsitektur Mikro (Low-Level) ---

class RegisterFile:
    """Mewakili register seperti r0–r15, pc, sp, dan flags."""
    def __init__(self, num_general_registers: int = 16):
        self.general_registers = [0] * num_general_registers  # r0-r15
        self.pc = 0  # Program Counter
        self.sp = 0  # Stack Pointer (jika MemoryUnit mendukung stack)
        self.flags = {
            "ZF": False,  # Zero Flag
            "CF": False,  # Carry Flag
            "SF": False,  # Sign Flag
            "OF": False   # Overflow Flag
        }
        # Register khusus lainnya bisa ditambahkan di sini
        self.instruction_register: Optional[InstruksiEksekusi] = None # Menyimpan instruksi yang sedang didecode/dieksekusi

    def read_register(self, index: int) -> int:
        if 0 <= index < len(self.general_registers):
            return self.general_registers[index]
        raise ValueError(f"Indeks register tidak valid: {index}")

    def write_register(self, index: int, value: int):
        if 0 <= index < len(self.general_registers):
            self.general_registers[index] = value
        else:
            raise ValueError(f"Indeks register tidak valid: {index}")

    def get_flag(self, flag_name: str) -> bool:
        return self.flags.get(flag_name, False)

    def set_flag(self, flag_name: str, value: bool):
        if flag_name in self.flags:
            self.flags[flag_name] = value
        else:
            raise ValueError(f"Nama flag tidak valid: {flag_name}")

class ProgramCounter:
    """Komponen yang menyimpan posisi instruksi saat ini."""
    def __init__(self, initial_address: int = 0):
        self._address = initial_address

    @property
    def value(self) -> int:
        return self._address

    def increment(self):
        self._address += 1

    def set(self, new_address: int):
        self._address = new_address

class ALU:
    """Arithmetic Logic Unit virtual."""
    def __init__(self, register_file: RegisterFile):
        self.register_file = register_file

    def execute(self, operation: str, operand1: int, operand2: int) -> int:
        result = 0
        # Reset flags sebelum operasi
        self.register_file.set_flag("ZF", False)
        self.register_file.set_flag("CF", False)
        self.register_file.set_flag("SF", False)
        self.register_file.set_flag("OF", False)

        if operation == "ADD":
            result = operand1 + operand2
            # Logika untuk set CF, OF (simplified)
            if result > 2**31 -1 or result < -(2**31): # Asumsi 32-bit signed
                 self.register_file.set_flag("OF", True)
        elif operation == "SUB":
            result = operand1 - operand2
        elif operation == "AND":
            result = operand1 & operand2
        elif operation == "OR":
            result = operand1 | operand2
        elif operation == "XOR":
            result = operand1 ^ operand2
        elif operation == "CMP": # Compare: operand1 - operand2, set flags, result tidak disimpan
            cmp_res = operand1 - operand2
            if cmp_res == 0:
                self.register_file.set_flag("ZF", True)
            if cmp_res < 0: # operand1 < operand2
                self.register_file.set_flag("SF", True) # Sign flag (negative result)
            # CF untuk CMP (unsigned less than)
            if operand1 < operand2: # Perlu penanganan unsigned
                 self.register_file.set_flag("CF", True)
            return cmp_res # Mengembalikan hasil perbandingan untuk logika branching
        else:
            raise ValueError(f"Operasi ALU tidak dikenal: {operation}")

        if result == 0:
            self.register_file.set_flag("ZF", True)
        if result < 0:
            self.register_file.set_flag("SF", True)
        
        # Batasi hasil ke range integer tertentu jika perlu (misal 32-bit)
        # result = result & 0xFFFFFFFF 
        return result

class MemoryUnit:
    """Bentuk nyata WADAEH. Menyimpan data runtime .asu."""
    def __init__(self, size_bytes: int = 1024 * 1024): # Default 1MB
        self.memory = bytearray(size_bytes)
        self.size = size_bytes
        # Untuk stack (opsional, bisa diimplementasikan lebih lanjut)
        # self.stack_pointer_register = register_file.sp # Jika RegisterFile punya SP
        # self.stack_base = size_bytes - 1 
        # self.stack_limit = size_bytes // 2 

    def read(self, address: int, num_bytes: int = 4) -> bytes:
        if 0 <= address and address + num_bytes <= self.size:
            return self.memory[address : address + num_bytes]
        raise MemoryError(f"Alamat memori tidak valid atau di luar batas: {address}")

    def write(self, address: int, value: bytes):
        if 0 <= address and address + len(value) <= self.size:
            self.memory[address : address + len(value)] = value
        else:
            raise MemoryError(f"Alamat memori tidak valid atau di luar batas saat menulis: {address}")
    
    # Contoh fungsi stack (jika diimplementasikan)
    # def push(self, value_bytes: bytes): ...
    # def pop(self, num_bytes: int) -> bytes: ...

class InstructionCache:
    """Cache untuk instruksi yang sudah di-fetch."""
    def __init__(self, capacity: int = 128): # Jumlah instruksi yang bisa di-cache
        self.cache: Dict[int, InstruksiEksekusi] = {} # address -> instruction
        self.capacity = capacity
        self.access_order: List[int] = [] # Untuk LRU eviction policy

    def get(self, address: int) -> Optional[InstruksiEksekusi]:
        if address in self.cache:
            # Pindahkan ke akhir untuk LRU
            self.access_order.remove(address)
            self.access_order.append(address)
            return self.cache[address]
        return None

    def put(self, address: int, instruction: InstruksiEksekusi):
        if len(self.cache) >= self.capacity:
            # Evict LRU
            lru_address = self.access_order.pop(0)
            del self.cache[lru_address]
        
        self.cache[address] = instruction
        self.access_order.append(address)

class DataCache:
    """Cache untuk data runtime."""
    def __init__(self, capacity_bytes: int = 1024 * 64): # 64KB cache
        self.cache: Dict[int, bytes] = {} # address -> data_bytes
        self.capacity = capacity_bytes
        self.current_size = 0
        self.access_order: List[int] = []

    def get(self, address: int, num_bytes: int) -> Optional[bytes]:
        # Implementasi cache data bisa lebih kompleks (cache lines, etc.)
        # Ini adalah versi sederhana
        if address in self.cache: # Asumsi address adalah key unik untuk blok data
            self.access_order.remove(address)
            self.access_order.append(address)
            # Perlu memastikan num_bytes sesuai dengan yang di-cache
            return self.cache[address][:num_bytes] 
        return None

    def put(self, address: int, data: bytes):
        data_len = len(data)
        while self.current_size + data_len > self.capacity and self.access_order:
            lru_address = self.access_order.pop(0)
            evicted_data = self.cache.pop(lru_address)
            self.current_size -= len(evicted_data)
        
        if self.current_size + data_len <= self.capacity:
            self.cache[address] = data
            self.access_order.append(address)
            self.current_size += data_len

# --- Modul Fungsional Utama ---

class InstructionDecoder:
    """Mengubah instruksi mentah menjadi objek Instruction."""
    def __init__(self, register_file: RegisterFile):
        self.register_file = register_file

    def decode(self, raw_instruction: InstruksiEksekusi) -> InstruksiEksekusi:
        # Validasi, konversi, atau pre-processing instruksi
        # Misalnya, mengisi instruction_register di RegisterFile
        self.register_file.instruction_register = raw_instruction
        # Logika decoding lebih lanjut bisa ditambahkan di sini
        logger.debug(f"Decoding instruction: {raw_instruction.instruksi.value}")
        return raw_instruction # Untuk saat ini, hanya meneruskan

class AuditLogger:
    """Modul pencatatan lengkap untuk semua eksekusi."""
    def __init__(self, log_file_path: Optional[str] = "audit_log.txt"):
        self.log_file_path = log_file_path
        if self.log_file_path:
            # Pastikan direktori ada
            os.makedirs(os.path.dirname(self.log_file_path) or '.', exist_ok=True)


    def log(self, tempik_id: str, instruction_name: str, result_status: str, duration_ms: int, current_file_hash: str, details: str = ""):
        """Format Deloitte: timestamp | Tempik_id | instruction | result | duration_ms."""
        # Catatan: Format Deloitte yang disebutkan tidak menyertakan current_file_hash atau details,
        # namun ini adalah informasi yang berguna. Akan disesuaikan.
        timestamp = datetime.now().isoformat() # Sesuai ISO 8601, lebih standar dari strftime
        log_entry = f"{timestamp} | {tempik_id} | {instruction_name} | {result_status} | {duration_ms}ms"
        if current_file_hash:
             log_entry += f" | file_hash={current_file_hash}"
        if details:
            log_entry += f" | details={details}"
        
        logger.info(f"AUDIT: {log_entry}") # Juga log ke logger utama
        if self.log_file_path:
            try:
                with open(self.log_file_path, 'a') as f:
                    f.write(log_entry + "\n")
            except Exception as e:
                logger.error(f"Gagal menulis ke audit log file {self.log_file_path}: {e}")

class IOHandler:
    """Menangani input/output dasar."""
    def __init__(self, virtual_fs: 'VirtualFS', tempik_id: str): # Forward declaration untuk VirtualFS
        self.virtual_fs = virtual_fs
        self.tempik_id = tempik_id

    def read_file(self, path: str) -> bytes:
        logger.debug(f"{self.tempik_id}: Reading file from VFS: {path}")
        return self.virtual_fs.read_file(path)

    def write_file(self, path: str, content: bytes):
        logger.debug(f"{self.tempik_id}: Writing file to VFS: {path}")
        self.virtual_fs.write_file(path, content)

    def log_to_terminal(self, message: str, level: str = "INFO"):
        # Ini akan menggunakan logger standar Python yang sudah dikonfigurasi
        log_level = getattr(logging, level.upper(), logging.INFO)
        logger.log(log_level, f"TEMPİK_IO [{self.tempik_id}]: {message}")

    def get_user_input(self, prompt: str) -> str:
        # Dalam konteks eksekusi non-interaktif, ini mungkin tidak digunakan
        # atau harus di-pipe dari sumber lain.
        logger.warning(f"{self.tempik_id}: Permintaan input pengguna tidak didukung dalam mode ini: {prompt}")
        return "" # Atau raise error

class ExecutionContextManager:
    """Menyimpan seluruh konteks runtime .asu."""
    def __init__(self, tempik_id: str, initial_env_vars: Optional[Dict[str, str]] = None):
        self.tempik_id = tempik_id
        self.env_vars: Dict[str, str] = initial_env_vars or {}
        self.current_working_directory: str = "/" # Path root di VirtualFS
        self.role: Optional[str] = None
        self.namespace: Optional[str] = "default"
        self.timeout_profile: float = 60.0 # Timeout per instruksi default
        self.resource_limits: Dict[str, Any] = {} # Misal: max_memory, max_storage
        self.current_user: Optional[str] = None # Untuk AUTH
        self.security_policy: Dict[str, Any] = {} # readonly, no-network, etc.
        self.conditional_flags = {"last_if_condition": False, "in_else_block": False} # Untuk IF/ELSE/ENDIF

    def set_env_var(self, key: str, value: str):
        self.env_vars[key] = value
        # Juga set di os.environ jika diperlukan untuk subprocess, tapi hati-hati dengan isolasi
        # os.environ[key] = value 
        logger.debug(f"{self.tempik_id}: ENV_VAR set: {key}={value}")

    def get_env_var(self, key: str) -> Optional[str]:
        return self.env_vars.get(key)

    def set_working_directory(self, path: str, virtual_fs: 'VirtualFS'):
        # Validasi path di VirtualFS
        if virtual_fs.dir_exists(path):
            self.current_working_directory = path
            logger.debug(f"{self.tempik_id}: CWD set to: {path}")
        else:
            raise FileNotFoundError(f"Direktori tidak ditemukan di VFS: {path}")

    def resolve_path(self, path: str) -> str:
        """Resolve path relatif terhadap CWD di VFS."""
        if path.startswith('/'):
            return path
        # Sederhana, bisa diperluas dengan '..' etc.
        return os.path.join(self.current_working_directory, path).replace('\\', '/')


class VirtualFS:
    """Filesystem virtual untuk isolasi per Tempik."""
    def __init__(self, tempik_id: str):
        self.tempik_id = tempik_id
        # Struktur dasar: {'/path/to/file': b'content', '/path/to/dir': {'file_in_dir': b'content'}}
        self.fs_root: Dict[str, Any] = {"/": {}} # Root direktori
        self.mount_points: Dict[str, str] = {} # vfs_path -> host_path (untuk MOUNT)

        # Inisialisasi struktur folder standar jika ada (misal dari body .asu)
        self._create_dir_recursive("/scripts")
        self._create_dir_recursive("/deps")
        self._create_dir_recursive("/output")
        self._create_dir_recursive("/temp")

    def _get_node(self, path: str) -> Tuple[Optional[Dict], Optional[str]]:
        """Helper untuk mendapatkan node parent dan nama item."""
        parts = [part for part in path.strip('/').split('/') if part]
        current_level = self.fs_root["/"]
        parent = None
        item_name = "/"
        
        if not parts: # Root path
            return self.fs_root, "/"

        for i, part in enumerate(parts):
            if not isinstance(current_level, dict):
                return None, None # Path tidak valid, mencoba masuk ke file seolah-olah direktori
            if part not in current_level:
                return None, None # Path tidak ditemukan
            
            if i == len(parts) - 1: # Item terakhir
                parent = current_level
                item_name = part
            else: # Navigasi ke subdirektori
                current_level = current_level[part]
        return parent, item_name


    def _create_dir_recursive(self, path: str):
        parts = [part for part in path.strip('/').split('/') if part]
        current_level = self.fs_root["/"]
        for part in parts:
            if part not in current_level:
                current_level[part] = {} # Buat direktori baru
            elif not isinstance(current_level[part], dict):
                raise FileExistsError(f"Path '{path}' konflik dengan file yang ada.")
            current_level = current_level[part]


    def dir_exists(self, path: str) -> bool:
        parent, item_name = self._get_node(path)
        if parent is None or item_name is None: return False
        if item_name == "/": return True # Root selalu ada
        return item_name in parent and isinstance(parent[item_name], dict)

    def file_exists(self, path: str) -> bool:
        parent, item_name = self._get_node(path)
        if parent is None or item_name is None: return False
        return item_name in parent and isinstance(parent[item_name], bytes)

    def write_file(self, path: str, content: bytes, create_dirs: bool = True):
        # Pastikan path tidak kosong dan bukan hanya "/"
        if not path or path.strip() == "/":
            raise ValueError("Tidak dapat menulis file ke root path '/' secara langsung.")

        dir_path = os.path.dirname(path)
        filename = os.path.basename(path)

        if create_dirs and dir_path and dir_path != "/":
            self._create_dir_recursive(dir_path)
        
        parent_dir_node, _ = self._get_node(dir_path) # Dapatkan node direktori parent
        if parent_dir_node is None or not isinstance(parent_dir_node.get(os.path.basename(dir_path)) if dir_path != "/" else parent_dir_node.get("/"), dict) :
             # Jika dir_path adalah root, parent_dir_node adalah fs_root, dan kita cek item "/" di dalamnya
             if dir_path == "/":
                 parent_actual_node = parent_dir_node.get("/") if parent_dir_node else None
             else: # Jika bukan root, kita cek item os.path.basename(dir_path)
                 parent_actual_node = parent_dir_node.get(os.path.basename(dir_path)) if parent_dir_node else None

             if not isinstance(parent_actual_node, dict):
                raise FileNotFoundError(f"Direktori '{dir_path}' tidak ditemukan untuk menulis file '{filename}'.")

        # Setelah memastikan direktori parent ada, kita bisa menulis file
        # Node parent yang benar adalah node dari dir_path itu sendiri
        target_dir_node, dir_item_name = self._get_node(dir_path)
        if target_dir_node is None or dir_item_name is None:
            raise FileNotFoundError(f"Direktori '{dir_path}' tidak valid.")
        
        actual_parent_dict = target_dir_node[dir_item_name] if dir_item_name != "/" else target_dir_node # Jika dir_path adalah root
        if not isinstance(actual_parent_dict, dict):
             raise NotADirectoryError(f"Path '{dir_path}' bukan direktori.")

        actual_parent_dict[filename] = content
        logger.debug(f"{self.tempik_id} VFS: File '{path}' ditulis ({len(content)} bytes).")


    def read_file(self, path: str) -> bytes:
        parent, item_name = self._get_node(path)
        if parent and item_name and item_name in parent and isinstance(parent[item_name], bytes):
            logger.debug(f"{self.tempik_id} VFS: File '{path}' dibaca.")
            return parent[item_name]
        raise FileNotFoundError(f"File tidak ditemukan di VFS: {path}")

    def list_dir(self, path: str) -> List[str]:
        parent, item_name = self._get_node(path)
        if parent and item_name and item_name in parent and isinstance(parent[item_name], dict):
            return list(parent[item_name].keys())
        elif path == "/" and isinstance(self.fs_root["/"], dict): # Handle root
            return list(self.fs_root["/"].keys())
        raise NotADirectoryError(f"Path bukan direktori atau tidak ditemukan di VFS: {path}")

    def remove_file(self, path: str):
        parent, item_name = self._get_node(path)
        if parent and item_name and item_name in parent and isinstance(parent[item_name], bytes):
            del parent[item_name]
            logger.debug(f"{self.tempik_id} VFS: File '{path}' dihapus.")
        else:
            raise FileNotFoundError(f"File tidak ditemukan di VFS untuk dihapus: {path}")

    def remove_dir(self, path: str, recursive: bool = False):
        parent, item_name = self._get_node(path)
        if parent and item_name and item_name in parent and isinstance(parent[item_name], dict):
            if not recursive and parent[item_name]: # Direktori tidak kosong
                raise OSError(f"Direktori tidak kosong: {path}")
            del parent[item_name]
            logger.debug(f"{self.tempik_id} VFS: Direktori '{path}' dihapus.")
        else:
            raise FileNotFoundError(f"Direktori tidak ditemukan di VFS untuk dihapus: {path}")

    def mount_host_path(self, vfs_path: str, host_path: str):
        # Ini adalah placeholder. Implementasi nyata memerlukan interaksi OS
        # atau library seperti pyfakefs untuk overlay.
        # Untuk saat ini, hanya mencatatnya.
        if not os.path.exists(host_path) or not os.path.isdir(host_path):
            logger.warning(f"Host path untuk mount tidak ada atau bukan direktori: {host_path}")
            # raise FileNotFoundError(f"Host path untuk mount tidak ada atau bukan direktori: {host_path}")
        
        self._create_dir_recursive(vfs_path) # Pastikan mount point ada di VFS
        self.mount_points[vfs_path] = host_path
        logger.info(f"{self.tempik_id} VFS: Host path '{host_path}' di-mount ke VFS path '{vfs_path}' (simulasi).")
        # Jika file dari host_path perlu "terlihat" di vfs_path, perlu logika tambahan
        # untuk menyalin atau memetakan.

    def unmount_host_path(self, vfs_path: str):
        if vfs_path in self.mount_points:
            del self.mount_points[vfs_path]
            logger.info(f"{self.tempik_id} VFS: Host path di-unmount dari VFS path '{vfs_path}' (simulasi).")
        else:
            logger.warning(f"{self.tempik_id} VFS: Tidak ada mount point di '{vfs_path}' untuk di-unmount.")

    def populate_from_dict(self, structure: Dict[str, Any], base_path: str = "/"):
        """Populate VFS dari struktur dictionary (misal dari body .asu)."""
        for name, content in structure.items():
            current_path = os.path.join(base_path, name).replace('\\', '/')
            if isinstance(content, str): # Asumsi string adalah konten file
                self.write_file(current_path, content.encode('utf-8'), create_dirs=True)
            elif isinstance(content, bytes):
                self.write_file(current_path, content, create_dirs=True)
            elif isinstance(content, dict): # Subdirektori
                self._create_dir_recursive(current_path)
                self.populate_from_dict(content, base_path=current_path)
            else:
                logger.warning(f"Tipe konten tidak didukung untuk VFS population di '{current_path}': {type(content)}")


class CryptoEngine:
    """Menangani SIGN, VERIFY_HASH, DECRYPT."""
    def __init__(self):
        # Kunci bisa di-load atau digenerate per instance/sesi
        self.private_key: Optional[rsa.RSAPrivateKey] = None
        self.public_key: Optional[rsa.RSAPublicKey] = None
        # self._generate_key_pair() # Atau load dari konfigurasi

    def _generate_key_pair(self):
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        self.public_key = self.private_key.public_key()

    def load_private_key(self, key_bytes: bytes, password: Optional[bytes] = None):
        self.private_key = serialization.load_pem_private_key(key_bytes, password=password)
        self.public_key = self.private_key.public_key()

    def load_public_key(self, key_bytes: bytes):
        self.public_key = serialization.load_pem_public_key(key_bytes)

    def sign_data(self, data: bytes) -> bytes:
        if not self.private_key:
            raise ValueError("Private key tidak di-load untuk signing.")
        signature = self.private_key.sign(
            data,
            rsa_padding.PSS(
                mgf=rsa_padding.MGF1(hashes.SHA256()),
                salt_length=rsa_padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return signature

    def verify_signature(self, data: bytes, signature: bytes) -> bool:
        if not self.public_key:
            raise ValueError("Public key tidak di-load untuk verifikasi.")
        try:
            self.public_key.verify(
                signature,
                data,
                rsa_padding.PSS(
                    mgf=rsa_padding.MGF1(hashes.SHA256()),
                    salt_length=rsa_padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except Exception: # InvalidSignature
            return False

    def encrypt_data(self, data: bytes) -> bytes:
        # Implementasi enkripsi simetris atau asimetris (misal RSA-OAEP)
        # Untuk RSA, enkripsi biasanya untuk data kecil (seperti kunci simetris)
        if not self.public_key:
             raise ValueError("Public key tidak di-load untuk enkripsi.")
        ciphertext = self.public_key.encrypt(
            data,
            rsa_padding.OAEP(
                mgf=rsa_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return ciphertext


    def decrypt_data(self, ciphertext: bytes) -> bytes:
        if not self.private_key:
            raise ValueError("Private key tidak di-load untuk dekripsi.")
        plaintext = self.private_key.decrypt(
            ciphertext,
            rsa_padding.OAEP(
                mgf=rsa_padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return plaintext

    @staticmethod
    def calculate_hash(data: bytes, algorithm: str = "sha256") -> str:
        h = None
        if algorithm.lower() == "sha256":
            h = hashlib.sha256()
        elif algorithm.lower() == "sha512":
            h = hashlib.sha512()
        # Tambahkan algoritma lain jika perlu
        else:
            raise ValueError(f"Algoritma hash tidak didukung: {algorithm}")
        h.update(data)
        return h.hexdigest()

class NetworkUnit:
    """Komponen untuk operasi jaringan."""
    def __init__(self, context_manager: ExecutionContextManager):
        self.context_manager = context_manager
        # Bisa menggunakan library 'requests' atau 'aiohttp' untuk async
        # import requests # Pindahkan import ke atas jika akan digunakan global
        # import aiohttp

    async def fetch_repo(self, url: str, target_dir_vfs: str, io_handler: IOHandler) -> Dict[str, Any]:
        # Ini adalah simulasi. Implementasi nyata akan menggunakan subprocess git.
        # Hasil clone akan ditulis ke VirtualFS melalui IOHandler.
        if self.context_manager.security_policy.get("networking_mode") == "isolated":
            raise PermissionError("Operasi jaringan tidak diizinkan (mode isolated).")

        logger.info(f"NETWORK_UNIT: Fetching repo from {url} to VFS:{target_dir_vfs}")
        # Contoh: membuat file placeholder di VFS
        try:
            io_handler.virtual_fs._create_dir_recursive(target_dir_vfs) # Pastikan dir ada
            readme_content = f"# Simulated repo from {url}\nTimestamp: {datetime.now()}".encode('utf-8')
            io_handler.write_file(os.path.join(target_dir_vfs, "README.md").replace('\\', '/'), readme_content)
            return {"status": "success", "message": f"Simulated fetch to VFS:{target_dir_vfs}"}
        except Exception as e:
            logger.error(f"NETWORK_UNIT: Gagal simulasi fetch_repo: {e}")
            return {"status": "failed", "error": str(e)}


    async def invoke_remote(self, endpoint: str, method: str = "POST", data: Optional[Dict] = None, headers: Optional[Dict]=None) -> Dict[str, Any]:
        if self.context_manager.security_policy.get("networking_mode") == "isolated":
            raise PermissionError("Operasi jaringan tidak diizinkan (mode isolated).")
        
        logger.info(f"NETWORK_UNIT: Invoking remote {method} {endpoint}")
        # try:
        #     # Gunakan aiohttp untuk async request
        #     async with aiohttp.ClientSession() as session:
        #         async with session.request(method, endpoint, json=data, headers=headers) as response:
        #             return {
        #                 "status_code": response.status,
        #                 "response_body": await response.json() if response.content_type == 'application/json' else await response.text()
        #             }
        # except Exception as e:
        #     logger.error(f"NETWORK_UNIT: Gagal invoke_remote: {e}")
        #     return {"status_code": 500, "error": str(e)}
        return {"status": "simulated_success", "endpoint": endpoint, "message": "Remote invocation simulated."} # Placeholder

class SecurityModule:
    """Melindungi runtime dari instruksi berbahaya dan menerapkan policy."""
    def __init__(self, context_manager: ExecutionContextManager, crypto_engine: CryptoEngine):
        self.context_manager = context_manager
        self.crypto_engine = crypto_engine

    def verify_asu_signature(self, file_asu: FileASU, public_key_pem: Optional[bytes] = None) -> bool:
        """Verifikasi checksum_signature di header .asu."""
        if not file_asu.header.checksum_signature:
            logger.warning("Tidak ada checksum_signature di header .asu untuk diverifikasi.")
            return True # Atau False jika signature wajib

        if public_key_pem:
            self.crypto_engine.load_public_key(public_key_pem)
        elif not self.crypto_engine.public_key:
            logger.error("Public key tidak tersedia untuk verifikasi signature .asu.")
            return False

        # Data yang di-sign adalah hash dari konten file
        # (Perlu dipastikan proses signing di sisi pembuat .asu konsisten)
        data_to_verify = file_asu.hash_sha256.encode('utf-8') 
        signature_bytes = bytes.fromhex(file_asu.header.checksum_signature) # Asumsi signature adalah hex string

        return self.crypto_engine.verify_signature(data_to_verify, signature_bytes)

    def check_instruction_policy(self, instruction: InstruksiEksekusi) -> bool:
        """Periksa apakah instruksi diizinkan berdasarkan policy."""
        # Contoh: jika networking_mode=isolated, tolak FETCH_REPO
        if instruction.instruksi == InstruksiASU.FETCH_REPO and \
           self.context_manager.security_policy.get("networking_mode") == "isolated":
            logger.warning(f"Instruksi {instruction.instruksi.value} diblokir oleh policy jaringan.")
            return False
        
        # Contoh: jika security_flags=readonly, tolak operasi tulis VFS
        if "readonly" in self.context_manager.security_policy.get("flags", []) and \
            instruction.instruksi in [InstruksiASU.INJECT, InstruksiASU.EXPORT]: # Tambahkan instruksi tulis lainnya
            # Perlu cara untuk tahu apakah EXECUTE akan menulis
            logger.warning(f"Instruksi {instruction.instruksi.value} diblokir oleh policy readonly.")
            return False
            
        # Implementasi sandbox untuk EXECUTE (misal, filter command berbahaya)
        if instruction.instruksi == InstruksiASU.EXECUTE:
            command_str = "".join(map(str,instruction.parameter.get("command", ""))) # Gabungkan jika list
            
            # Filter command berbahaya (contoh sederhana)
            dangerous_commands = ["rm -rf", "curl | sh", "mkfs"] 
            if any(dc in command_str for dc in dangerous_commands):
                logger.error(f"Potensi command berbahaya terdeteksi dan diblokir: {command_str}")
                return False
        return True

    def apply_resource_limits(self):
        # Terapkan max_exec_time, memory_profile, dll.
        # Ini bisa dilakukan dengan memonitor durasi dan penggunaan memori.
        # Untuk memory_profile, bisa menggunakan library `resource` di Unix.
        pass

class InterruptController:
    """Menyediakan mekanisme INT atau EXCEPTION."""
    def __init__(self):
        self.interrupt_pending = False
        self.interrupt_type: Optional[str] = None
        self.interrupt_handler: Optional[Callable] = None

    def raise_interrupt(self, interrupt_type: str, handler: Optional[Callable] = None):
        self.interrupt_pending = True
        self.interrupt_type = interrupt_type
        self.interrupt_handler = handler
        logger.warning(f"INTERRUPT: {interrupt_type} diajukan.")

    def clear_interrupt(self):
        self.interrupt_pending = False
        self.interrupt_type = None
        self.interrupt_handler = None

    def handle_interrupt_if_pending(self, tempik: 'Tempik'): # Forward declaration
        if self.interrupt_pending and self.interrupt_handler:
            self.interrupt_handler(tempik, self.interrupt_type)
            self.clear_interrupt() # Atau biarkan handler yang clear

# --- Komponen Pipeline dan Kontrol ---

class Pipeline:
    """Struktur pipeline 5 tahap: FETCH, DECODE, EXECUTE, MEMORY, WRITEBACK."""
    def __init__(self, tempik: 'Tempik'): # Forward declaration
        self.tempik = tempik # Referensi kembali ke Tempik pemilik pipeline
        self.stages = {
            TempikStatus.FETCH: self._fetch_stage,
            TempikStatus.DECODE: self._decode_stage,
            TempikStatus.EXECUTE: self._execute_stage,
            TempikStatus.MEMORY_ACCESS: self._memory_access_stage,
            TempikStatus.WRITE_BACK: self._write_back_stage,
        }
        self.current_stage_data: Dict[str, Any] = {} # Data yang dibawa antar stage

    async def _fetch_stage(self) -> Optional[InstruksiEksekusi]:
        """Tahap FETCH: Ambil instruksi dari memori (atau cache)."""
        pc_value = self.tempik.program_counter.value
        instruction = self.tempik.instruction_cache.get(pc_value)
        if not instruction:
            if 0 <= pc_value < len(self.tempik.program_memory):
                instruction = self.tempik.program_memory[pc_value]
                self.tempik.instruction_cache.put(pc_value, instruction)
                logger.debug(f"TEMPİK-{self.tempik.tempik_id} FETCH: Instruction at PC={pc_value} from memory.")
            else:
                logger.info(f"TEMPİK-{self.tempik.tempik_id} FETCH: Program Counter di luar batas. Program selesai atau error.")
                self.tempik.status = TempikStatus.COMPLETED # Atau FAILED
                return None
        else:
            logger.debug(f"TEMPİK-{self.tempik.tempik_id} FETCH: Instruction at PC={pc_value} from cache.")
        
        self.current_stage_data['fetched_instruction'] = instruction
        self.tempik.program_counter.increment() # Increment PC untuk instruksi berikutnya
        return instruction

    async def _decode_stage(self) -> Optional[InstruksiEksekusi]:
        """Tahap DECODE: Decode instruksi."""
        fetched_instruction = self.current_stage_data.get('fetched_instruction')
        if not fetched_instruction: return None

        decoded_instruction = self.tempik.instruction_decoder.decode(fetched_instruction)
        self.current_stage_data['decoded_instruction'] = decoded_instruction
        logger.debug(f"TEMPİK-{self.tempik.tempik_id} DECODE: {decoded_instruction.instruksi.value}")
        return decoded_instruction

    async def _execute_stage(self) -> Optional[Dict[str, Any]]:
        """Tahap EXECUTE: Jalankan instruksi (misal di ALU atau handler khusus)."""
        decoded_instruction = self.current_stage_data.get('decoded_instruction')
        if not decoded_instruction: return None

        # Periksa policy keamanan sebelum eksekusi
        if not self.tempik.security_module.check_instruction_policy(decoded_instruction):
            error_msg = f"Pelanggaran policy keamanan untuk instruksi {decoded_instruction.instruksi.value}"
            logger.error(f"TEMPİK-{self.tempik.tempik_id} EXECUTE: {error_msg}")
            self.current_stage_data['execution_result'] = {"status": "failed", "error": error_msg}
            self.tempik.status = TempikStatus.FAILED # Set status Tempik ke FAILED
            return self.current_stage_data['execution_result']

        # Cek kondisi IF/ELSE
        ctx_mgr = self.tempik.execution_context_manager
        if decoded_instruction.instruksi == InstruksiASU.ELSE:
            if not ctx_mgr.conditional_flags.get("last_if_condition_evaluated", False): # ELSE tanpa IF sebelumnya
                 raise RuntimeError("ELSE tanpa IF yang sesuai.")
            if ctx_mgr.conditional_flags["last_if_condition"]: # Jika IF=true, skip ELSE
                logger.debug(f"TEMPİK-{self.tempik.tempik_id} EXECUTE: Skipping ELSE block (IF was true).")
                self.current_stage_data['execution_result'] = {"status": "skipped_else", "skipped": True}
                return self.current_stage_data['execution_result']
            else: # IF=false, masuk ELSE
                ctx_mgr.conditional_flags["in_else_block"] = True
                self.current_stage_data['execution_result'] = {"status": "entering_else", "skipped": False}
                return self.current_stage_data['execution_result']

        elif decoded_instruction.instruksi == InstruksiASU.ENDIF:
            ctx_mgr.conditional_flags["last_if_condition"] = False
            ctx_mgr.conditional_flags["in_else_block"] = False
            ctx_mgr.conditional_flags["last_if_condition_evaluated"] = False
            self.current_stage_data['execution_result'] = {"status": "endif_processed"}
            return self.current_stage_data['execution_result']
        
        elif ctx_mgr.conditional_flags.get("in_else_block") == False and \
             ctx_mgr.conditional_flags.get("last_if_condition_evaluated") and \
             not ctx_mgr.conditional_flags.get("last_if_condition") and \
             decoded_instruction.instruksi != InstruksiASU.ELSE and \
             decoded_instruction.instruksi != InstruksiASU.ENDIF:
            # Jika IF sebelumnya false, dan kita belum di blok ELSE atau ENDIF, skip instruksi ini
            if not ctx_mgr.conditional_flags.get("currently_skipping_if_block", False):
                logger.debug(f"TEMPİK-{self.tempik.tempik_id} EXECUTE: Skipping instruction due to prior IF=false: {decoded_instruction.instruksi.value}")
                ctx_mgr.conditional_flags["currently_skipping_if_block"] = True

            self.current_stage_data['execution_result'] = {"status": "skipped_due_to_if", "skipped": True}
            return self.current_stage_data['execution_result']
        
        # Jika kita sampai di sini, berarti kita tidak sedang skip karena IF false
        ctx_mgr.conditional_flags["currently_skipping_if_block"] = False


        # Panggil handler instruksi yang sesuai
        # Ini akan dipetakan ke InstructionSet nantinya
        handler = self.tempik.instruction_set.get_handler(decoded_instruction.instruksi)
        if not handler:
            raise ValueError(f"Handler tidak ditemukan untuk instruksi: {decoded_instruction.instruksi.value}")

        logger.debug(f"TEMPİK-{self.tempik.tempik_id} EXECUTE: Running handler for {decoded_instruction.instruksi.value}")
        
        # Retry mechanism
        execution_result = None
        last_exception = None
        for attempt in range(decoded_instruction.retry_count +1): # retry_count=0 berarti 1 attempt
            try:
                execution_result = await asyncio.wait_for(
                    handler(self.tempik, decoded_instruction.parameter), # Handler menerima Tempik dan parameter
                    timeout=decoded_instruction.timeout
                )
                # Jika IF, simpan hasilnya untuk ELSE/ENDIF
                if decoded_instruction.instruksi == InstruksiASU.IF:
                    condition_result = execution_result.get("condition_met", False)
                    ctx_mgr.conditional_flags["last_if_condition"] = condition_result
                    ctx_mgr.conditional_flags["in_else_block"] = False # Reset saat IF baru
                    ctx_mgr.conditional_flags["last_if_condition_evaluated"] = True
                    if not condition_result:
                        logger.debug(f"TEMPİK-{self.tempik.tempik_id} EXECUTE: IF condition FALSE. Skipping to next ELSE/ENDIF.")
                break # Sukses, keluar dari loop retry
            except asyncio.TimeoutError:
                last_exception = TimeoutError(f"Instruksi {decoded_instruction.instruksi.value} timeout setelah {decoded_instruction.timeout}s pada attempt {attempt+1}")
                logger.warning(str(last_exception))
            except Exception as e:
                last_exception = e
                logger.error(f"TEMPİK-{self.tempik.tempik_id} EXECUTE: Error pada attempt {attempt+1} untuk {decoded_instruction.instruksi.value}: {e}")
            
            if attempt < decoded_instruction.retry_count:
                await asyncio.sleep(0.1 * (attempt + 1)) # Exponential backoff sederhana
            elif last_exception: # Gagal setelah semua retry
                execution_result = {"status": "failed", "error": str(last_exception)}
                self.tempik.status = TempikStatus.FAILED # Set status Tempik

        self.current_stage_data['execution_result'] = execution_result
        return execution_result

    async def _memory_access_stage(self) -> Optional[Any]:
        """Tahap MEMORY: Akses memori jika diperlukan (load/store)."""
        # Contoh: jika instruksi adalah LOAD atau STORE dari/ke MemoryUnit
        # Untuk saat ini, banyak instruksi tidak langsung berinteraksi dengan MemoryUnit di tahap ini.
        # Ini akan lebih relevan untuk instruksi set level rendah.
        execution_result = self.current_stage_data.get('execution_result', {})
        logger.debug(f"TEMPİK-{self.tempik.tempik_id} MEMORY_ACCESS: Result from EXECUTE: {execution_result.get('status', 'N/A')}")
        # Data yang perlu ditulis ke register atau memori disiapkan di sini
        self.current_stage_data['data_for_writeback'] = execution_result # Atau bagian tertentu dari result
        return execution_result # Meneruskan hasil

    async def _write_back_stage(self) -> Optional[Any]:
        """Tahap WRITE_BACK: Tulis hasil kembali ke register atau memori."""
        data_to_write = self.current_stage_data.get('data_for_writeback')
        # Contoh: self.tempik.register_file.write_register(index, value_from_data_to_write)
        logger.debug(f"TEMPİK-{self.tempik.tempik_id} WRITE_BACK: Data: {data_to_write}")
        
        # Reset data pipeline untuk siklus berikutnya
        final_status = data_to_write.get("status", "unknown") if isinstance(data_to_write, dict) else "completed"
        
        # Log audit setelah semua tahap selesai untuk satu instruksi
        decoded_instruction = self.current_stage_data.get('decoded_instruction')
        if decoded_instruction:
            duration_ms = int((time.time() - self.tempik.current_instruction_start_time) * 1000)
            error_details = data_to_write.get("error", "") if isinstance(data_to_write, dict) else ""
            self.tempik.audit_logger.log(
                tempik_id=f"Tempik-{self.tempik.tempik_id:03d}",
                instruction_name=decoded_instruction.instruksi.value,
                result_status=final_status.upper(),
                duration_ms=duration_ms,
                current_file_hash=self.tempik.current_file_hash,
                details=error_details
            )
        
        self.current_stage_data.clear()
        return data_to_write # Hasil akhir instruksi

    async def run_cycle(self) -> Optional[Dict[str, Any]]:
        """Menjalankan satu siklus pipeline penuh."""
        self.tempik.status = TempikStatus.FETCH
        if not await self.stages[TempikStatus.FETCH](): return None # Jika fetch gagal (misal EOF)
        
        self.tempik.status = TempikStatus.DECODE
        if not await self.stages[TempikStatus.DECODE](): return None # Jika decode gagal
        
        self.tempik.status = TempikStatus.EXECUTE
        execution_result = await self.stages[TempikStatus.EXECUTE]()
        if execution_result and execution_result.get("status") == "failed":
            # Langsung ke write_back untuk logging error, skip memory_access jika tidak relevan
            self.current_stage_data['data_for_writeback'] = execution_result
            self.tempik.status = TempikStatus.WRITE_BACK
            final_output = await self.stages[TempikStatus.WRITE_BACK]()
            self.tempik.status = TempikStatus.FAILED # Pastikan status Tempik adalah FAILED
            return final_output

        # Jika instruksi adalah HALT, langsung selesaikan
        decoded_instr = self.current_stage_data.get('decoded_instruction')
        if decoded_instr and decoded_instr.instruksi == InstruksiASU.HALT:
            self.tempik.status = TempikStatus.HALTED
            logger.info(f"TEMPİK-{self.tempik.tempik_id} HALTED by HALT instruction.")
            # Lakukan write_back untuk logging
            self.current_stage_data['data_for_writeback'] = execution_result
            await self.stages[TempikStatus.WRITE_BACK]()
            return execution_result

        self.tempik.status = TempikStatus.MEMORY_ACCESS
        await self.stages[TempikStatus.MEMORY_ACCESS]()
        
        self.tempik.status = TempikStatus.WRITE_BACK
        final_output = await self.stages[TempikStatus.WRITE_BACK]()
        
        # Kembali ke IDLE jika tidak ada instruksi lagi atau program selesai/halted
        # Logika ini akan diatur oleh ControlUnit atau Tempik run loop
        return final_output


class ControlUnit:
    """Unit kendali eksekusi instruksi: mengatur fetch, decode, execute."""
    def __init__(self, tempik: 'Tempik'): # Forward declaration
        self.tempik = tempik
        self.pipeline = Pipeline(tempik)
        self.is_running = False

    async def start_execution(self, program: List[InstruksiEksekusi], initial_pc: int = 0):
        self.tempik.load_program(program, initial_pc)
        self.is_running = True
        logger.info(f"TEMPİK-{self.tempik.tempik_id} ControlUnit: Execution started.")
        
        instruction_count = 0
        max_instructions = 10000 # Batas untuk mencegah infinite loop dalam simulasi
        
        while self.is_running and self.tempik.status not in [TempikStatus.COMPLETED, TempikStatus.FAILED, TempikStatus.HALTED] \
              and self.tempik.program_counter.value < len(self.tempik.program_memory) \
              and instruction_count < max_instructions:
            
            self.tempik.interrupt_controller.handle_interrupt_if_pending(self.tempik)
            if self.tempik.status == TempikStatus.HALTED: # Jika interrupt menyebabkan halt
                break

            self.tempik.current_instruction_start_time = time.time()
            result = await self.pipeline.run_cycle()
            instruction_count +=1

            if result is None and self.tempik.status != TempikStatus.COMPLETED : # EOF atau error fetch
                logger.info(f"TEMPİK-{self.tempik.tempik_id} ControlUnit: No result from pipeline cycle, assuming end of program or fetch error.")
                self.tempik.status = TempikStatus.COMPLETED # Atau FAILED jika fetch error
                break
            
            # Logika untuk JMP, JZ, JNZ
            instr_obj = self.tempik.register_file.instruction_register
            if instr_obj:
                params = instr_obj.parameter
                if instr_obj.instruksi == InstruksiASU.JMP and "target_label" in params:
                    self.tempik.jump_to_label(params["target_label"])
                elif instr_obj.instruksi == InstruksiASU.JZ and "target_label" in params and self.tempik.register_file.get_flag("ZF"):
                    self.tempik.jump_to_label(params["target_label"])
                elif instr_obj.instruksi == InstruksiASU.JNZ and "target_label" in params and not self.tempik.register_file.get_flag("ZF"):
                    self.tempik.jump_to_label(params["target_label"])
            
            if self.tempik.status in [TempikStatus.FAILED, TempikStatus.HALTED]:
                break # Hentikan loop jika Tempik gagal atau di-halt

        if instruction_count >= max_instructions:
            logger.warning(f"TEMPİK-{self.tempik.tempik_id} ControlUnit: Max instruction limit reached.")
            self.tempik.status = TempikStatus.FAILED
            self.tempik.interrupt_controller.raise_interrupt("MAX_INSTRUCTIONS_REACHED")


        if self.tempik.status not in [TempikStatus.FAILED, TempikStatus.HALTED]:
             self.tempik.status = TempikStatus.COMPLETED
        logger.info(f"TEMPİK-{self.tempik.tempik_id} ControlUnit: Execution finished with status {self.tempik.status.value}.")
        self.is_running = False


    def halt_execution(self, reason: str = "External Halt"):
        self.is_running = False
        self.tempik.status = TempikStatus.HALTED
        logger.info(f"TEMPİK-{self.tempik.tempik_id} ControlUnit: Execution halted. Reason: {reason}")
        # Bisa trigger interrupt
        self.tempik.interrupt_controller.raise_interrupt("HALT_REQUESTED", handler=lambda t, type: t.set_status(TempikStatus.HALTED))


# --- Definisi InstructionSet dan Handler ---
InstructionHandler = Callable[['Tempik', Dict[str, Any]], Coroutine[Any, Any, Dict[str, Any]]]

class InstructionSet:
    """Berisi definisi dan handler untuk semua instruksi .asu."""
    def __init__(self):
        self.handlers: Dict[InstruksiASU, InstructionHandler] = {}
        self._register_default_handlers()

    def _register_default_handlers(self):
        # Implementasi handler akan ada di sini atau di kelas terpisah
        # Contoh:
        self.handlers[InstruksiASU.SET_ENV] = self._handle_set_env
        self.handlers[InstruksiASU.INIT_ENV] = self._handle_init_env
        self.handlers[InstruksiASU.EXECUTE] = self._handle_execute
        self.handlers[InstruksiASU.LOG] = self._handle_log
        self.handlers[InstruksiASU.FETCH_REPO] = self._handle_fetch_repo
        self.handlers[InstruksiASU.VERIFY_HASH] = self._handle_verify_hash
        self.handlers[InstruksiASU.CLEANUP] = self._handle_cleanup
        self.handlers[InstruksiASU.IF] = self._handle_if
        self.handlers[InstruksiASU.ELSE] = self._handle_else # Sebenarnya ELSE dan ENDIF lebih ke flow control di pipeline
        self.handlers[InstruksiASU.ENDIF] = self._handle_endif
        self.handlers[InstruksiASU.ASSERT] = self._handle_assert
        self.handlers[InstruksiASU.HALT] = self._handle_halt
        self.handlers[InstruksiASU.SHUTDOWN] = self._handle_shutdown # Mirip HALT tapi untuk seluruh UTEK
        self.handlers[InstruksiASU.SET_CONTEXT] = self._handle_set_context
        self.handlers[InstruksiASU.AUTH] = self._handle_auth
        self.handlers[InstruksiASU.MOUNT] = self._handle_mount
        self.handlers[InstruksiASU.INJECT] = self._handle_inject
        self.handlers[InstruksiASU.EXPORT] = self._handle_export
        self.handlers[InstruksiASU.UNPACK] = self._handle_unpack
        self.handlers[InstruksiASU.INSTALL] = self._handle_install # Placeholder
        self.handlers[InstruksiASU.COMPILE] = self._handle_compile # Placeholder
        self.handlers[InstruksiASU.CHECKOUT] = self._handle_checkout # Placeholder

        # Instruksi baru dari audit
        self.handlers[InstruksiASU.MAP_PORT] = self._handle_map_port
        self.handlers[InstruksiASU.INVOKE_REMOTE] = self._handle_invoke_remote
        self.handlers[InstruksiASU.DELEGATE_TO] = self._handle_delegate_to
        self.handlers[InstruksiASU.EMIT_EVENT] = self._handle_emit_event
        self.handlers[InstruksiASU.SIGN] = self._handle_sign
        self.handlers[InstruksiASU.DECRYPT] = self._handle_decrypt
        self.handlers[InstruksiASU.VERIFY] = self._handle_verify # Verifikasi signature
        self.handlers[InstruksiASU.LOCK_EXEC] = self._handle_lock_exec

        # Instruksi ALU (contoh)
        self.handlers[InstruksiASU.ADD] = self._handle_alu_op
        self.handlers[InstruksiASU.SUB] = self._handle_alu_op
        self.handlers[InstruksiASU.CMP] = self._handle_alu_op
        # JMP, JZ, JNZ ditangani oleh ControlUnit setelah eksekusi CMP

    def get_handler(self, instruksi: InstruksiASU) -> Optional[InstructionHandler]:
        return self.handlers.get(instruksi)

    # --- Implementasi Handler ---
    # Handler menerima (tempik: Tempik, params: Dict) dan mengembalikan Dict hasil
    
    async def _handle_set_env(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        for key, value in params.items():
            tempik.execution_context_manager.set_env_var(key, str(value))
        return {"status": "success", "vars_set": len(params)}

    async def _handle_init_env(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        # working_dir sekarang di VFS, defaultnya "/"
        vfs_working_dir = params.get("working_dir", "/")
        try:
            tempik.execution_context_manager.set_working_directory(vfs_working_dir, tempik.virtual_fs)
            # Jika ada struktur direktori awal yang perlu dibuat di VFS dari params
            initial_structure = params.get("initial_fs_structure")
            if isinstance(initial_structure, dict):
                tempik.virtual_fs.populate_from_dict(initial_structure, base_path=vfs_working_dir)

            return {"status": "success", "working_dir_vfs": vfs_working_dir}
        except Exception as e:
            return {"status": "failed", "error": str(e)}


    async def _handle_execute(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        command_param = params.get("command", "")
        args = params.get("args", [])
        
        # Command bisa berupa path di VFS atau command sistem (jika diizinkan policy)
        # Untuk saat ini, kita simulasikan eksekusi
        
        cmd_str_list = []
        if isinstance(command_param, list):
            cmd_str_list.extend(command_param)
        else:
            cmd_str_list.append(str(command_param))
        cmd_str_list.extend(map(str, args))
        
        full_command_str = " ".join(cmd_str_list)
        logger.info(f"TEMPİK-{tempik.tempik_id} EXECUTE (simulated): {full_command_str} in VFS CWD: {tempik.execution_context_manager.current_working_directory}")
        
        # Placeholder untuk eksekusi nyata (misal dengan subprocess jika diizinkan)
        # Jika command adalah path ke skrip di VFS, baca dan interpretasikan (jika bahasa didukung)
        # Ini adalah bagian yang sangat kompleks dan sensitif keamanan.
        
        # Contoh: jika command adalah "python" dan ada file.py di VFS
        if cmd_str_list[0] == "python" and len(cmd_str_list) > 1:
            script_path_vfs = tempik.execution_context_manager.resolve_path(cmd_str_list[1])
            if tempik.virtual_fs.file_exists(script_path_vfs):
                script_content = tempik.virtual_fs.read_file(script_path_vfs).decode('utf-8')
                # Eksekusi Python code (SANGAT BERBAHAYA TANPA SANDBOX KUAT)
                # Untuk demo, kita tidak akan exec() secara langsung.
                return {"status": "simulated_python_execution", "script": script_path_vfs, "output": "Python script executed (simulated)."}

        return {"status": "simulated_success", "command": full_command_str, "output": "Command executed (simulated)."}

    async def _handle_log(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        message = params.get("message", "")
        level = params.get("level", "INFO").upper()
        tempik.io_handler.log_to_terminal(message, level)
        return {"status": "success", "logged_message": message}

    async def _handle_fetch_repo(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        url = params.get("url")
        target_vfs_path = params.get("target", f"/deps/{os.path.basename(url or 'default_repo')}")
        if not url: return {"status": "failed", "error": "URL repository diperlukan"}
        
        # Gunakan NetworkUnit
        return await tempik.network_unit.fetch_repo(url, target_vfs_path, tempik.io_handler)

    async def _handle_verify_hash(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        file_vfs_path = params.get("file")
        expected_hash = params.get("hash", "").lower()
        algorithm = params.get("algorithm", "sha256").lower()
        if not file_vfs_path: return {"status": "failed", "error": "Path file VFS diperlukan"}

        try:
            file_content = tempik.io_handler.read_file(tempik.execution_context_manager.resolve_path(file_vfs_path))
            actual_hash = tempik.crypto_engine.calculate_hash(file_content, algorithm)
            verified = actual_hash == expected_hash
            return {"status": "success", "file": file_vfs_path, "verified": verified, "actual_hash": actual_hash, "expected_hash": expected_hash}
        except FileNotFoundError:
            return {"status": "failed", "error": f"File tidak ditemukan di VFS: {file_vfs_path}"}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    async def _handle_cleanup(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        target_vfs_path = params.get("dir", tempik.execution_context_manager.current_working_directory)
        resolved_path = tempik.execution_context_manager.resolve_path(target_vfs_path)
        try:
            if tempik.virtual_fs.dir_exists(resolved_path):
                # Hapus isi direktori, bukan direktori itu sendiri jika CWD
                # Atau implementasi rm -rf (hati-hati)
                if resolved_path == "/" : # Jangan hapus root
                    return {"status": "failed", "error": "Tidak dapat cleanup root VFS."}

                # Hapus semua file dan subdirektori di dalam resolved_path
                items_to_delete = tempik.virtual_fs.list_dir(resolved_path)
                for item in items_to_delete:
                    item_path = os.path.join(resolved_path, item).replace('\\','/')
                    if tempik.virtual_fs.file_exists(item_path):
                        tempik.virtual_fs.remove_file(item_path)
                    elif tempik.virtual_fs.dir_exists(item_path):
                        tempik.virtual_fs.remove_dir(item_path, recursive=True) # Hapus direktori secara rekursif
                
                # Jika bukan CWD, hapus direktori itu sendiri
                if resolved_path != tempik.execution_context_manager.current_working_directory:
                     if tempik.virtual_fs.dir_exists(resolved_path): # Cek lagi karena bisa saja sudah terhapus jika kosong
                          tempik.virtual_fs.remove_dir(resolved_path, recursive=True)

                return {"status": "success", "cleaned_vfs_path": resolved_path}
            elif tempik.virtual_fs.file_exists(resolved_path):
                tempik.virtual_fs.remove_file(resolved_path)
                return {"status": "success", "cleaned_vfs_file": resolved_path}
            else:
                return {"status": "warning", "message": f"Path VFS tidak ditemukan untuk cleanup: {resolved_path}"}
        except Exception as e:
            return {"status": "failed", "error": f"Error saat cleanup VFS {resolved_path}: {e}"}

    async def _handle_if(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        # Kondisi bisa kompleks, melibatkan variabel dari context, hasil register, dll.
        # Contoh sederhana: evaluasi string "true" atau "false", atau perbandingan
        condition_str = str(params.get("condition", "false")).lower()
        
        # Evaluasi kondisi dinamis (contoh sederhana)
        # Misal: "register[0] > 10" atau "env['MY_VAR'] == 'expected'"
        # Ini memerlukan parser ekspresi yang aman.
        # Untuk sekarang, hanya boolean string atau perbandingan sederhana.
        condition_met = False
        if condition_str == "true":
            condition_met = True
        elif condition_str == "false":
            condition_met = False
        else: # Coba evaluasi ekspresi sederhana (placeholder, tidak aman untuk produksi)
            try:
                # Ini SANGAT TIDAK AMAN jika `condition_str` dari input tidak terpercaya
                # eval_globals = {'env': tempik.execution_context_manager.env_vars, 
                #                 'reg': tempik.register_file.general_registers}
                # condition_met = bool(eval(condition_str, eval_globals, {}))
                logger.warning(f"Evaluasi kondisi dinamis IF '{condition_str}' belum sepenuhnya aman.")
                # Untuk demo, anggap saja sebagai string literal "true" atau "false"
                if "==" in condition_str: # Misal "var1 == var2"
                    parts = condition_str.split("==")
                    # Perlu cara untuk mendapatkan nilai var1 dan var2 dari context
                    val1 = tempik.execution_context_manager.get_env_var(parts[0].strip())
                    val2 = parts[1].strip().strip("'\"") # Hilangkan quote
                    condition_met = (val1 == val2)

            except Exception as e:
                logger.error(f"Error evaluasi kondisi IF '{condition_str}': {e}")
                condition_met = False # Default ke false jika error

        # Hasilnya akan digunakan oleh pipeline untuk skip/execute blok berikutnya
        return {"status": "success", "condition_met": condition_met, "condition_str": condition_str}

    async def _handle_else(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        # Logika ELSE ditangani di pipeline berdasarkan flag dari IF sebelumnya
        return {"status": "success", "message": "ELSE block encountered"}

    async def _handle_endif(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        # Logika ENDIF ditangani di pipeline untuk mereset flag kondisional
        return {"status": "success", "message": "ENDIF block encountered"}

    async def _handle_assert(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        condition_str = str(params.get("condition", "false")).lower()
        message = params.get("message", f"Assertion failed: {condition_str}")
        # Evaluasi kondisi mirip dengan IF
        condition_met = False
        if condition_str == "true": condition_met = True
        # Tambahkan evaluasi dinamis yang lebih baik di sini
        
        if not condition_met:
            tempik.interrupt_controller.raise_interrupt("ASSERTION_FAILURE", handler=lambda t, type: t.set_status(TempikStatus.FAILED))
            raise AssertionError(message) # Ini akan menghentikan eksekusi instruksi saat ini dan ditangkap oleh pipeline
        return {"status": "success", "assertion_passed": True}

    async def _handle_halt(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        reason = params.get("reason", "HALT instruction executed")
        tempik.control_unit.halt_execution(reason) # Memberitahu ControlUnit untuk berhenti
        return {"status": "halt_requested", "reason": reason} # Pipeline akan menangani status HALTED

    async def _handle_shutdown(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        # Ini harusnya memberi sinyal ke UTEKVirtualExecutor untuk menghentikan semua Tempik
        reason = params.get("reason", "SHUTDOWN instruction executed")
        logger.critical(f"TEMPİK-{tempik.tempik_id} requested UTEK SHUTDOWN. Reason: {reason}")
        # tempik.parent_executor.request_shutdown(reason) # Perlu referensi ke parent
        # Untuk saat ini, sama seperti HALT untuk Tempik ini
        tempik.control_unit.halt_execution(f"Shutdown requested: {reason}")
        return {"status": "shutdown_requested", "reason": reason}

    async def _handle_set_context(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        ctx_mgr = tempik.execution_context_manager
        if "role" in params: ctx_mgr.role = params["role"]
        if "namespace" in params: ctx_mgr.namespace = params["namespace"]
        if "timeout_profile" in params: ctx_mgr.timeout_profile = float(params["timeout_profile"])
        if "resource_limits" in params: ctx_mgr.resource_limits.update(params["resource_limits"])
        if "current_user" in params: ctx_mgr.current_user = params["current_user"]
        if "security_policy" in params: ctx_mgr.security_policy.update(params["security_policy"])
        
        # Jika ada "working_directory", set melalui VFS
        if "working_directory" in params:
            try:
                ctx_mgr.set_working_directory(params["working_directory"], tempik.virtual_fs)
            except FileNotFoundError as e:
                return {"status": "failed", "error": str(e), "context_updated": False}
        
        logger.info(f"TEMPİK-{tempik.tempik_id} context updated: Role={ctx_mgr.role}, Namespace={ctx_mgr.namespace}")
        return {"status": "success", "context_updated": True}

    async def _handle_auth(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        service = params.get("service")
        auth_type = params.get("type", "token") # token, credentials
        credentials = params.get("credentials", {}) # user, pass, token_value
        
        if not service: return {"status": "failed", "error": "Nama service diperlukan untuk AUTH."}

        # Logika otentikasi nyata (misal, menyimpan token untuk NetworkUnit)
        # Untuk saat ini, hanya mencatat dan menyimpan user jika ada
        user = credentials.get("user") or credentials.get("token_value") # Ambil user atau token sebagai identitas
        if user:
            tempik.execution_context_manager.current_user = user
            logger.info(f"TEMPİK-{tempik.tempik_id} AUTH: User '{user}' authenticated for service '{service}' (simulated).")
            return {"status": "success", "authenticated_service": service, "user": user}
        else:
            logger.warning(f"TEMPİK-{tempik.tempik_id} AUTH: No user/token provided for service '{service}'.")
            return {"status": "failed", "error": "User/token tidak disediakan.", "authenticated_service": service}

    async def _handle_mount(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        vfs_path = params.get("target_vfs_path")
        host_path = params.get("source_host_path") # Path di sistem host executor
        # fs_type = params.get("type", "bind") # bind, overlay (belum didukung penuh)
        # options = params.get("options", []) # ro, rw

        if not vfs_path or not host_path:
            return {"status": "failed", "error": "source_host_path dan target_vfs_path diperlukan untuk MOUNT."}
        
        try:
            # Security check: Pastikan host_path diizinkan (misal, dalam direktori yang aman)
            # ... (belum diimplementasikan) ...
            tempik.virtual_fs.mount_host_path(vfs_path, host_path)
            return {"status": "success", "mounted_vfs": vfs_path, "host_path": host_path}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    async def _handle_inject(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        vfs_path = params.get("path")
        content_str = params.get("content", "") # Konten bisa string atau base64 encoded bytes
        encoding = params.get("encoding", "utf-8") # utf-8, base64
        
        if not vfs_path: return {"status": "failed", "error": "Path VFS diperlukan untuk INJECT."}
        
        try:
            content_bytes = b''
            if encoding == "base64":
                import base64
                content_bytes = base64.b64decode(content_str)
            else: # default utf-8
                content_bytes = content_str.encode(encoding)
            
            resolved_vfs_path = tempik.execution_context_manager.resolve_path(vfs_path)
            tempik.io_handler.write_file(resolved_vfs_path, content_bytes)
            return {"status": "success", "injected_to_vfs": resolved_vfs_path, "size": len(content_bytes)}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    async def _handle_export(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        source_vfs_path = params.get("source_vfs_path")
        # Target bisa berupa path di host (jika diizinkan) atau nama untuk dikembalikan ke UTEK executor
        target_name_or_host_path = params.get("target") 
        
        if not source_vfs_path or not target_name_or_host_path:
            return {"status": "failed", "error": "source_vfs_path dan target diperlukan untuk EXPORT."}

        resolved_source_vfs = tempik.execution_context_manager.resolve_path(source_vfs_path)
        try:
            if not tempik.virtual_fs.file_exists(resolved_source_vfs) and not tempik.virtual_fs.dir_exists(resolved_source_vfs):
                raise FileNotFoundError(f"Source VFS path tidak ditemukan: {resolved_source_vfs}")

            # Jika target adalah path host (memerlukan izin khusus)
            if os.path.isabs(target_name_or_host_path) or target_name_or_host_path.startswith("./") or target_name_or_host_path.startswith("../"):
                # Ini adalah ekspor ke filesystem host. Perlu policy yang ketat.
                # Untuk saat ini, kita tidak implementasi tulis ke host secara langsung karena risiko keamanan.
                # Bisa di-handle oleh UTEKVirtualExecutor setelah Tempik selesai.
                logger.warning(f"Ekspor ke host path '{target_name_or_host_path}' tidak diimplementasikan langsung oleh Tempik. Akan dikembalikan sebagai data.")
                # Kembalikan konten sebagai gantinya
                if tempik.virtual_fs.file_exists(resolved_source_vfs):
                    content = tempik.virtual_fs.read_file(resolved_source_vfs)
                    return {"status": "success_data_returned", "export_name": target_name_or_host_path, "data_base64": base64.b64encode(content).decode(), "source_vfs": resolved_source_vfs}
                else: # Direktori (perlu di-zip atau semacamnya)
                    return {"status": "failed", "error": "Ekspor direktori sebagai data belum didukung penuh."}

            # Jika target adalah nama, kembalikan kontennya untuk diproses UTEK executor
            if tempik.virtual_fs.file_exists(resolved_source_vfs):
                content = tempik.virtual_fs.read_file(resolved_source_vfs)
                # Simpan hasil ini agar UTEKVirtualExecutor bisa mengambilnya
                tempik.exported_data[target_name_or_host_path] = content
                return {"status": "success", "exported_as_name": target_name_or_host_path, "source_vfs": resolved_source_vfs, "size": len(content)}
            elif tempik.virtual_fs.dir_exists(resolved_source_vfs):
                # Untuk direktori, bisa di-zip dan dikembalikan sebagai data
                # (Implementasi zip placeholder)
                logger.info(f"Exporting VFS directory {resolved_source_vfs} as {target_name_or_host_path} (simulated zip).")
                # tempik.exported_data[target_name_or_host_path] = b"simulated_zip_content_for_dir"
                # TODO: Implementasi zip VFS direktori
                return {"status": "pending_zip", "message": "Zip export untuk direktori belum diimplementasikan."}

        except Exception as e:
            return {"status": "failed", "error": str(e)}
        return {"status": "failed", "error": "Logika export belum lengkap."}


    async def _handle_unpack(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        source_vfs_file = params.get("file")
        target_vfs_dir = params.get("target_dir", "/")
        format_type = params.get("format") # zip, tar.gz, auto-detect

        if not source_vfs_file:
            return {"status": "failed", "error": "File VFS sumber diperlukan untuk UNPACK."}
        
        resolved_source_vfs = tempik.execution_context_manager.resolve_path(source_vfs_file)
        resolved_target_vfs = tempik.execution_context_manager.resolve_path(target_vfs_dir)

        try:
            if not tempik.virtual_fs.file_exists(resolved_source_vfs):
                raise FileNotFoundError(f"File arsip tidak ditemukan di VFS: {resolved_source_vfs}")
            if not tempik.virtual_fs.dir_exists(resolved_target_vfs):
                tempik.virtual_fs._create_dir_recursive(resolved_target_vfs)

            archive_bytes = tempik.virtual_fs.read_file(resolved_source_vfs)
            
            # Deteksi format jika tidak diberikan
            if not format_type or format_type == "auto":
                if resolved_source_vfs.endswith(".zip"): format_type = "zip"
                elif resolved_source_vfs.endswith(".tar.gz"): format_type = "tar.gz"
                else: return {"status": "failed", "error": "Tidak dapat mendeteksi format arsip."}

            if format_type == "zip":
                import io
                with zipfile.ZipFile(io.BytesIO(archive_bytes), 'r') as zip_ref:
                    for member_name in zip_ref.namelist():
                        member_path_vfs = os.path.join(resolved_target_vfs, member_name).replace('\\', '/')
                        if member_name.endswith('/'): # Direktori
                            tempik.virtual_fs._create_dir_recursive(member_path_vfs)
                        else: # File
                            dir_of_member = os.path.dirname(member_path_vfs)
                            if dir_of_member: tempik.virtual_fs._create_dir_recursive(dir_of_member)
                            tempik.virtual_fs.write_file(member_path_vfs, zip_ref.read(member_name))
                return {"status": "success", "unpacked_to_vfs": resolved_target_vfs}
            # elif format_type == "tar.gz":
                # Implementasi untuk tar.gz (memerlukan library tarfile)
                # ...
            else:
                return {"status": "failed", "error": f"Format arsip tidak didukung: {format_type}"}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    # Placeholder untuk handler yang lebih kompleks
    async def _handle_install(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        logger.warning("INSTALL instruction is a placeholder and not fully implemented for VFS.")
        return {"status": "simulated_success", "message": "INSTALL simulated."}
    async def _handle_compile(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        logger.warning("COMPILE instruction is a placeholder and not fully implemented for VFS.")
        return {"status": "simulated_success", "message": "COMPILE simulated."}
    async def _handle_checkout(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        logger.warning("CHECKOUT instruction is a placeholder (simulated after FETCH_REPO).")
        return {"status": "simulated_success", "message": "CHECKOUT simulated."}
    
    # Instruksi Baru dari Audit
    async def _handle_map_port(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        # Ini biasanya di-handle di level orchestrator (seperti Docker/Kubernetes)
        # Tempik hanya bisa mencatat permintaan ini.
        internal_port = params.get("internal_port")
        external_port_suggestion = params.get("external_port_suggestion")
        protocol = params.get("protocol", "tcp")
        if not internal_port: return {"status": "failed", "error": "internal_port diperlukan."}
        
        logger.info(f"TEMPİK-{tempik.tempik_id} MAP_PORT request: internal={internal_port}, suggested_external={external_port_suggestion}, proto={protocol} (simulated).")
        # Simpan permintaan ini agar UTEKVirtualExecutor bisa mengetahuinya
        tempik.port_mapping_requests.append(params)
        return {"status": "success", "port_mapping_requested": params}

    async def _handle_invoke_remote(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        endpoint = params.get("endpoint")
        method = params.get("method", "POST")
        payload = params.get("payload") # Bisa dict (JSON) atau string
        headers = params.get("headers")
        if not endpoint: return {"status": "failed", "error": "Endpoint diperlukan."}
        
        return await tempik.network_unit.invoke_remote(endpoint, method, payload, headers)

    async def _handle_delegate_to(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        # Ini akan memberi sinyal ke UTEKVirtualExecutor untuk menjalankan file .asu lain
        asu_file_vfs_path = params.get("asu_file_vfs_path") # Path ke file .asu di dalam VFS saat ini
        input_params = params.get("input_params", {}) # Parameter untuk .asu yang didelegasikan
        if not asu_file_vfs_path: return {"status": "failed", "error": "asu_file_vfs_path diperlukan."}
        
        resolved_path = tempik.execution_context_manager.resolve_path(asu_file_vfs_path)
        if not tempik.virtual_fs.file_exists(resolved_path):
            return {"status": "failed", "error": f"File .asu untuk delegasi tidak ditemukan di VFS: {resolved_path}"}

        # Baca konten file .asu dari VFS
        # asu_content_bytes = tempik.virtual_fs.read_file(resolved_path)
        # UTEKVirtualExecutor akan mengambil ini dan menjalankannya
        tempik.delegation_request = {"asu_vfs_path": resolved_path, "params": input_params}
        logger.info(f"TEMPİK-{tempik.tempik_id} DELEGATE_TO request: {resolved_path} with params {input_params}.")
        # Tempik saat ini akan menunggu (atau bisa juga tidak, tergantung behavior yang diinginkan)
        return {"status": "delegation_requested", "target_asu": resolved_path}

    async def _handle_emit_event(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        event_type = params.get("type", "custom_event")
        event_data = params.get("data", {})
        # Event ini bisa dikirim ke sistem monitoring eksternal atau dicatat secara khusus
        logger.info(f"EVENT EMITTED by TEMPİK-{tempik.tempik_id}: Type='{event_type}', Data={event_data}")
        # tempik.parent_executor.publish_event(tempik.tempik_id, event_type, event_data)
        return {"status": "success", "event_type": event_type, "event_data": event_data}

    async def _handle_sign(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        data_to_sign_str = params.get("data") # Data bisa string atau path ke file di VFS
        key_id_or_vfs_path = params.get("private_key_ref") # Referensi ke private key
        
        if not data_to_sign_str: return {"status": "failed", "error": "Data untuk di-sign diperlukan."}
        
        data_bytes = b''
        if tempik.virtual_fs.file_exists(tempik.execution_context_manager.resolve_path(data_to_sign_str)):
            data_bytes = tempik.virtual_fs.read_file(tempik.execution_context_manager.resolve_path(data_to_sign_str))
        else:
            data_bytes = str(data_to_sign_str).encode('utf-8')

        # Load private key (jika belum) - ini perlu manajemen kunci yang aman
        if key_id_or_vfs_path and not tempik.crypto_engine.private_key:
            # Asumsi key_id_or_vfs_path adalah path ke file kunci PEM di VFS
            try:
                key_pem_bytes = tempik.virtual_fs.read_file(tempik.execution_context_manager.resolve_path(key_id_or_vfs_path))
                tempik.crypto_engine.load_private_key(key_pem_bytes) # Password jika ada
            except Exception as e:
                return {"status": "failed", "error": f"Gagal load private key dari VFS {key_id_or_vfs_path}: {e}"}
        
        if not tempik.crypto_engine.private_key:
            return {"status": "failed", "error": "Private key tidak tersedia untuk SIGN."}

        try:
            signature_bytes = tempik.crypto_engine.sign_data(data_bytes)
            signature_hex = signature_bytes.hex()
            return {"status": "success", "data_signed_hash": hashlib.sha256(data_bytes).hexdigest(), "signature_hex": signature_hex}
        except Exception as e:
            return {"status": "failed", "error": f"Gagal melakukan signing: {e}"}

    async def _handle_decrypt(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        ciphertext_hex_or_vfs_path = params.get("ciphertext")
        key_id_or_vfs_path = params.get("private_key_ref")
        output_vfs_path = params.get("output_vfs_path") # Opsional, jika hasil ingin disimpan ke file VFS

        if not ciphertext_hex_or_vfs_path: return {"status": "failed", "error": "Ciphertext diperlukan."}

        ciphertext_bytes = b''
        if tempik.virtual_fs.file_exists(tempik.execution_context_manager.resolve_path(str(ciphertext_hex_or_vfs_path))):
            ciphertext_bytes = tempik.virtual_fs.read_file(tempik.execution_context_manager.resolve_path(str(ciphertext_hex_or_vfs_path)))
        else:
            try:
                ciphertext_bytes = bytes.fromhex(str(ciphertext_hex_or_vfs_path))
            except ValueError:
                return {"status": "failed", "error": "Ciphertext bukan hex string yang valid atau path VFS."}
        
        if key_id_or_vfs_path and not tempik.crypto_engine.private_key:
            try:
                key_pem_bytes = tempik.virtual_fs.read_file(tempik.execution_context_manager.resolve_path(key_id_or_vfs_path))
                tempik.crypto_engine.load_private_key(key_pem_bytes)
            except Exception as e:
                return {"status": "failed", "error": f"Gagal load private key dari VFS {key_id_or_vfs_path}: {e}"}

        if not tempik.crypto_engine.private_key:
            return {"status": "failed", "error": "Private key tidak tersedia untuk DECRYPT."}
            
        try:
            plaintext_bytes = tempik.crypto_engine.decrypt_data(ciphertext_bytes)
            if output_vfs_path:
                resolved_output_path = tempik.execution_context_manager.resolve_path(output_vfs_path)
                tempik.io_handler.write_file(resolved_output_path, plaintext_bytes)
                return {"status": "success", "decrypted_to_vfs": resolved_output_path}
            else:
                # Kembalikan sebagai string (jika aman) atau base64
                try:
                    return {"status": "success", "plaintext": plaintext_bytes.decode('utf-8')}
                except UnicodeDecodeError:
                    return {"status": "success", "plaintext_base64": base64.b64encode(plaintext_bytes).decode()}
        except Exception as e:
            return {"status": "failed", "error": f"Gagal melakukan dekripsi: {e}"}

    async def _handle_verify(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        # Verifikasi signature digital (berbeda dari VERIFY_HASH)
        data_str_or_vfs_path = params.get("data")
        signature_hex = params.get("signature_hex")
        public_key_ref = params.get("public_key_ref") # Path VFS ke public key PEM atau ID kunci

        if not data_str_or_vfs_path or not signature_hex:
            return {"status": "failed", "error": "Data dan signature_hex diperlukan."}

        data_bytes = b''
        if tempik.virtual_fs.file_exists(tempik.execution_context_manager.resolve_path(str(data_str_or_vfs_path))):
            data_bytes = tempik.virtual_fs.read_file(tempik.execution_context_manager.resolve_path(str(data_str_or_vfs_path)))
        else:
            data_bytes = str(data_str_or_vfs_path).encode('utf-8')
        
        try:
            signature_bytes = bytes.fromhex(signature_hex)
        except ValueError:
            return {"status": "failed", "error": "Signature bukan hex string yang valid."}

        if public_key_ref and not tempik.crypto_engine.public_key: # Load jika belum ada
            try:
                key_pem_bytes = tempik.virtual_fs.read_file(tempik.execution_context_manager.resolve_path(public_key_ref))
                tempik.crypto_engine.load_public_key(key_pem_bytes)
            except Exception as e:
                return {"status": "failed", "error": f"Gagal load public key dari VFS {public_key_ref}: {e}"}
        
        if not tempik.crypto_engine.public_key:
            return {"status": "failed", "error": "Public key tidak tersedia untuk VERIFY."}

        is_valid = tempik.crypto_engine.verify_signature(data_bytes, signature_bytes)
        return {"status": "success", "signature_verified": is_valid}

    async def _handle_lock_exec(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        # Ini memberi sinyal ke UTEKVirtualExecutor untuk mengunci file .asu saat ini
        # atau file .asu lain yang direferensikan.
        file_hash_to_lock = params.get("file_hash", tempik.current_file_hash) # Defaultnya file saat ini
        # tempik.parent_executor.lock_execution(file_hash_to_lock) # Perlu referensi parent
        tempik.lock_requests.append(file_hash_to_lock)
        logger.info(f"TEMPİK-{tempik.tempik_id} LOCK_EXEC request for hash: {file_hash_to_lock}.")
        return {"status": "success", "lock_requested_for_hash": file_hash_to_lock}

    async def _handle_alu_op(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        # Handler generik untuk operasi ALU
        # Parameter: "operation": "ADD", "operand1_reg": 0, "operand2_val": 10, "dest_reg": 1
        # Atau "operand1_val": 5, "operand2_reg": 2
        op_name = tempik.register_file.instruction_register.instruksi.value # ADD, SUB, CMP
        
        op1, op2 = 0, 0
        # Dapatkan operand 1
        if "operand1_reg" in params:
            op1 = tempik.register_file.read_register(params["operand1_reg"])
        elif "operand1_val" in params:
            op1 = int(params["operand1_val"])
        else: return {"status": "failed", "error": "Operand 1 tidak ditemukan untuk operasi ALU."}

        # Dapatkan operand 2
        if "operand2_reg" in params:
            op2 = tempik.register_file.read_register(params["operand2_reg"])
        elif "operand2_val" in params:
            op2 = int(params["operand2_val"])
        else: return {"status": "failed", "error": "Operand 2 tidak ditemukan untuk operasi ALU."}

        result = tempik.alu.execute(op_name, op1, op2)

        if op_name != "CMP": # CMP tidak menulis ke register tujuan, hanya set flag
            dest_reg_idx = params.get("dest_reg")
            if dest_reg_idx is not None:
                tempik.register_file.write_register(dest_reg_idx, result)
                return {"status": "success", "result": result, "dest_reg": dest_reg_idx, "flags": tempik.register_file.flags}
            else: # Jika tidak ada dest_reg, hasil mungkin hanya untuk flag (atau error jika dest wajib)
                return {"status": "success", "result_no_dest": result, "flags": tempik.register_file.flags}
        else: # Untuk CMP
             return {"status": "success", "comparison_result": result, "flags": tempik.register_file.flags}


# --- Kelas Tempik (Pengganti TempikVirtual yang lebih modular) ---

class Tempik:
    """Representasi satu Tempik. Tiap Tempik punya pipeline sendiri, register, dan stack."""
    def __init__(self, tempik_id: int, audit_logger: AuditLogger, parent_executor: 'UTEKVirtualExecutor'):
        self.tempik_id = tempik_id
        self.parent_executor = parent_executor # Referensi ke executor utama
        self.status = TempikStatus.IDLE
        self.current_file_hash: Optional[str] = None # Hash dari file .asu yang sedang dieksekusi
        self.current_instruction_start_time: float = 0.0

        # Komponen Inti
        self.register_file = RegisterFile()
        self.program_counter = ProgramCounter() # Akan disinkronkan dengan register_file.pc
        self.alu = ALU(self.register_file)
        self.memory_unit = MemoryUnit() # Ukuran bisa dikonfigurasi dari header .asu
        self.instruction_cache = InstructionCache()
        self.data_cache = DataCache() # Belum terintegrasi penuh ke pipeline

        # Modul Fungsional
        self.execution_context_manager = ExecutionContextManager(f"Tempik-{tempik_id:03d}")
        self.virtual_fs = VirtualFS(f"Tempik-{tempik_id:03d}")
        self.io_handler = IOHandler(self.virtual_fs, f"Tempik-{tempik_id:03d}")
        self.instruction_decoder = InstructionDecoder(self.register_file)
        self.crypto_engine = CryptoEngine() # Setiap Tempik bisa punya engine sendiri atau shared
        self.network_unit = NetworkUnit(self.execution_context_manager)
        self.security_module = SecurityModule(self.execution_context_manager, self.crypto_engine)
        self.audit_logger = audit_logger # Shared atau per Tempik? Untuk saat ini shared.
        self.interrupt_controller = InterruptController()
        
        # Kontrol dan Program
        self.instruction_set = InstructionSet() # Bisa shared jika immutable, atau per Tempik
        self.control_unit = ControlUnit(self) # ControlUnit memiliki Pipeline
        self.program_memory: List[InstruksiEksekusi] = []
        self.label_map: Dict[str, int] = {} # label -> address (indeks di program_memory)

        # Hasil dan Permintaan Antar Komponen
        self.exported_data: Dict[str, bytes] = {} # Untuk EXPORT
        self.port_mapping_requests: List[Dict] = [] # Untuk MAP_PORT
        self.delegation_request: Optional[Dict] = None # Untuk DELEGATE_TO
        self.lock_requests: List[str] = [] # Untuk LOCK_EXEC

    def load_program(self, program_instructions: List[InstruksiEksekusi], initial_pc: int = 0):
        self.program_memory = program_instructions
        self.program_counter.set(initial_pc)
        self.register_file.pc = initial_pc # Sinkronkan
        self.label_map.clear()
        for i, instr in enumerate(program_instructions):
            if instr.label:
                if instr.label in self.label_map:
                    logger.warning(f"Label duplikat ditemukan: {instr.label} di alamat {i} dan {self.label_map[instr.label]}")
                self.label_map[instr.label] = i
        logger.info(f"TEMPİK-{self.tempik_id}: Program ({len(program_instructions)} instructions) loaded. PC set to {initial_pc}.")

    def jump_to_label(self, label: str):
        if label in self.label_map:
            target_address = self.label_map[label]
            self.program_counter.set(target_address)
            self.register_file.pc = target_address
            logger.debug(f"TEMPİK-{self.tempik_id}: Jumping to label '{label}' (address {target_address}).")
        else:
            # raise ValueError(f"Label '{label}' tidak ditemukan.")
            logger.error(f"TEMPİK-{self.tempik_id}: Label '{label}' tidak ditemukan untuk JMP/BRANCH.")
            self.status = TempikStatus.FAILED
            self.interrupt_controller.raise_interrupt("INVALID_JUMP_LABEL")


    async def run(self, file_asu: FileASU):
        """Mulai eksekusi file .asu di Tempik ini."""
        self.status = TempikStatus.BUSY # Status umum saat aktif
        self.current_file_hash = file_asu.hash_sha256
        self.execution_context_manager.env_vars.clear() # Reset env
        self.execution_context_manager.current_working_directory = "/" # Reset CWD
        self.virtual_fs = VirtualFS(f"Tempik-{self.tempik_id:03d}") # Reset VFS
        if file_asu.virtual_fs_structure: # Populate VFS dari .asu body
            self.virtual_fs.populate_from_dict(file_asu.virtual_fs_structure)

        # Apply header info ke context
        self.execution_context_manager.security_policy["flags"] = file_asu.header.security_flags.split(',')
        self.execution_context_manager.security_policy["networking_mode"] = file_asu.header.networking_mode
        # Parse time_budget, memory_profile, dll.
        
        # Verifikasi signature .asu jika ada kunci publik
        # if self.parent_executor.global_public_key_pem:
        #    if not self.security_module.verify_asu_signature(file_asu, self.parent_executor.global_public_key_pem):
        #        logger.error(f"TEMPİK-{self.tempik_id}: Verifikasi signature file .asu GAGAL.")
        #        self.status = TempikStatus.FAILED
        #        return

        await self.control_unit.start_execution(file_asu.body)
        # Status akhir (COMPLETED, FAILED, HALTED) akan diatur oleh ControlUnit

    def set_status(self, new_status: TempikStatus):
        logger.debug(f"TEMPİK-{self.tempik_id}: Status changed from {self.status.value} to {new_status.value}")
        self.status = new_status

    def get_status_summary(self) -> Dict[str, Any]:
        return {
            "tempik_id": self.tempik_id,
            "status": self.status.value,
            "pc": self.program_counter.value,
            "flags": self.register_file.flags,
            "current_instruction": self.register_file.instruction_register.instruksi.value if self.register_file.instruction_register else "N/A",
            "cwd_vfs": self.execution_context_manager.current_working_directory
        }

# --- Scheduler (Bagian dari UTEKVirtualExecutor) ---

class Scheduler:
    """Menentukan Tempik mana yang mengeksekusi tugas apa."""
    def __init__(self, tempik_pool: List[Tempik]):
        self.tempik_pool = tempik_pool
        self.queue: asyncio.Queue[FileASU] = asyncio.Queue() # Antrian file .asu untuk dieksekusi
        self.tempik_assignment: Dict[int, Optional[FileASU]] = {t.tempik_id: None for t in tempik_pool}

    async def submit_task(self, file_asu: FileASU):
        await self.queue.put(file_asu)
        logger.info(f"SCHEDULER: File .asu {file_asu.hash_sha256} ditambahkan ke antrian.")

    async def run_scheduler_loop(self):
        """Loop utama scheduler untuk menugaskan task ke Tempik idle."""
        logger.info("SCHEDULER: Loop dimulai.")
        while True: # Loop ini bisa dihentikan dengan mekanisme lain
            try:
                file_asu_to_run = await asyncio.wait_for(self.queue.get(), timeout=1.0) # Tunggu task baru
                
                assigned = False
                for tempik in self.tempik_pool: # Round-robin sederhana atau cari yang IDLE
                    if tempik.status == TempikStatus.IDLE:
                        logger.info(f"SCHEDULER: Menugaskan {file_asu_to_run.hash_sha256} ke Tempik-{tempik.tempik_id}.")
                        self.tempik_assignment[tempik.tempik_id] = file_asu_to_run
                        # Tidak block di sini, biarkan Tempik run secara async
                        asyncio.create_task(tempik.run(file_asu_to_run)) 
                        assigned = True
                        break
                
                if not assigned:
                    logger.warning(f"SCHEDULER: Tidak ada Tempik idle. Mengembalikan {file_asu_to_run.hash_sha256} ke antrian.")
                    await self.queue.put(file_asu_to_run) # Kembalikan ke antrian jika tidak ada yang idle
                
                self.queue.task_done() # Tandai task dari queue selesai diproses (ditugaskan)

            except asyncio.TimeoutError:
                # Tidak ada task baru, cek status Tempik atau lakukan housekeeping
                for tempik_id, assigned_file in self.tempik_assignment.items():
                    if assigned_file:
                        tempik = next(t for t in self.tempik_pool if t.tempik_id == tempik_id)
                        if tempik.status in [TempikStatus.COMPLETED, TempikStatus.FAILED, TempikStatus.HALTED]:
                            logger.info(f"SCHEDULER: Tempik-{tempik_id} selesai/gagal/halted dengan {assigned_file.hash_sha256}. Status: {tempik.status.value}")
                            # Lakukan post-processing jika perlu (misal, ambil exported_data)
                            self.tempik_assignment[tempik_id] = None # Kosongkan assignment
                            tempik.status = TempikStatus.IDLE # Set kembali ke IDLE
                pass 
            except Exception as e:
                logger.error(f"SCHEDULER: Error dalam loop: {e}")
                # Tambahkan penanganan error yang lebih baik
            
            await asyncio.sleep(0.1) # Cek berkala


# --- UTEKVirtualExecutor (Refactored) ---
class UTEKVirtualExecutor:
    """Main executor untuk menjalankan file .asu dengan arsitektur 963-Tempik."""
    
    def __init__(self, max_tempik: int = 8): # Mengurangi default untuk testing
        self.max_tempik = max_tempik
        self.audit_logger = AuditLogger() # Satu logger untuk semua
        self.tempik_pool = [Tempik(i, self.audit_logger, self) for i in range(max_tempik)]
        self.scheduler = Scheduler(self.tempik_pool)
        
        self.locked_executions = set() # Set dari hash_sha256 file .asu yang terkunci
        self.global_public_key_pem: Optional[bytes] = None # Untuk verifikasi signature .asu
        self.is_shutting_down = False

        # Placeholder untuk API server jika ada
        # self.api_app = Flask(__name__) # Contoh
        # self._setup_api_routes()

    # def _setup_api_routes(self):
    #     @self.api_app.route("/execute_asu", methods=["POST"])
    #     async def api_execute_asu():
    #         # ... Terima file .asu, parse, submit ke scheduler ...
    #         # Ini memerlukan integrasi Flask/FastAPI dengan asyncio loop
    #         return jsonify({"status": "pending", "message": "ASU execution submitted."})

    def parse_asu_file(self, file_path: str) -> FileASU:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File .asu tidak ditemukan: {file_path}")
        
        if not file_path.endswith('.asu'):
            raise ValueError("File harus memiliki ekstensi .asu")
        
        filename_hash_part = os.path.basename(file_path).replace('.asu', '')
        # Validasi nama file adalah hash SHA-256 (opsional, tapi baik untuk konsistensi)
        # if len(filename_hash_part) != 64 or not all(c in '0123456789abcdefABCDEF' for c in filename_hash_part):
        #     logger.warning(f"Nama file .asu ({filename_hash_part}) tidak tampak seperti SHA-256 hash.")

        try:
            with open(file_path, 'rb') as f:
                compressed_data = f.read()
            
            data = b''
            if compressed_data.startswith(b'\x1f\x8b'):  # gzip
                data = gzip.decompress(compressed_data)
            elif compressed_data.startswith(b'\x04\x22\x4d\x18'):  # lz4
                data = lz4.frame.decompress(compressed_data)
            else: # Tidak terkompresi atau format lain
                data = compressed_data 
            
            content = json.loads(data.decode('utf-8'))
            
            if 'header' not in content or 'body' not in content:
                raise ValueError("Struktur file .asu tidak valid - header dan body diperlukan")
            
            header = HeaderASU.from_dict(content['header'])
            
            body_instructions = []
            if isinstance(content['body'], list): # Format lama/sederhana
                for instr_data in content['body']:
                    body_instructions.append(InstruksiEksekusi.from_dict(instr_data))
            elif isinstance(content['body'], dict): # Format baru dengan struktur folder
                # Asumsi instruksi utama ada di 'main_sequence' atau path default
                # Dan struktur VFS ada di key lain seperti 'scripts', 'deps'
                # Ini perlu disepakati bagaimana struktur VFS direpresentasikan dalam JSON body
                # Untuk saat ini, kita ambil dari 'main_sequence' jika ada
                main_seq_data = content['body'].get('main_sequence', content['body'].get('instructions', []))
                for instr_data in main_seq_data:
                     body_instructions.append(InstruksiEksekusi.from_dict(instr_data))
                
                # Ambil struktur VFS dari body jika ada
                vfs_structure_from_body = content['body'].get('virtual_fs', {})


            file_asu = FileASU(header=header, body=body_instructions)
            if 'vfs_structure_from_body' in locals() and vfs_structure_from_body:
                file_asu.virtual_fs_structure = vfs_structure_from_body
            
            generated_hash = file_asu.generate_hash() # Ini akan jadi hash konten
            # logger.info(f"File .asu diparsed. Konten hash: {generated_hash}, Nama file hash: {filename_hash_part}")
            # Jika nama file HARUS sama dengan hash konten:
            # if generated_hash.lower() != filename_hash_part.lower():
            #     raise ValueError(f"Hash nama file tidak cocok dengan hash konten: {filename_hash_part} vs {generated_hash}")
            
            return file_asu
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Format JSON tidak valid dalam file .asu: {e}")
        except Exception as e:
            logger.error(f"Error parsing file .asu '{file_path}': {e}", exc_info=True)
            raise RuntimeError(f"Error parsing file .asu: {e}")
    
    def create_asu_file(self, header: HeaderASU, instructions: List[InstruksiEksekusi], 
                        virtual_fs_structure: Optional[Dict[str,Any]] = None,
                        output_dir: str = ".") -> str:
        
        file_asu = FileASU(header=header, body=instructions, virtual_fs_structure=virtual_fs_structure or {})
        
        file_hash = file_asu.generate_hash() # Hash dari konten
        filename = f"{file_hash}.asu" # Nama file berdasarkan hash konten
        output_path = os.path.join(output_dir, filename)
        
        current_time_iso = datetime.now().isoformat()
        file_asu.header.asu_build_info = f"build-date={current_time_iso}, asu-sdk=refactored-1.0"
        
        # Jika ada private key, sign hash file dan simpan di checksum_signature
        # if self.global_private_key_for_signing:
        #    signature_bytes = self.crypto_engine_for_signing.sign_data(file_hash.encode('utf-8'))
        #    file_asu.header.checksum_signature = signature_bytes.hex()
        #    file_hash = file_asu.generate_hash() # Hash lagi jika header berubah (tapi ini jadi circular)
        #    # Sebaiknya checksum_signature tidak masuk dalam kalkulasi hash file itu sendiri.
        #    # Hash dihitung dari (header tanpa signature + body), lalu signature dibuat dari hash itu.

        content_to_serialize = {
            "header": file_asu.header.to_dict(),
            "body": [instr.to_dict() for instr in file_asu.body]
        }
        if file_asu.virtual_fs_structure: # Tambahkan jika ada
            content_to_serialize["body"]["virtual_fs"] = file_asu.virtual_fs_structure


        json_data = json.dumps(content_to_serialize, indent=2, ensure_ascii=False)
        
        compressed_data = b''
        if header.compression_info == "gzip":
            compressed_data = gzip.compress(json_data.encode('utf-utf-8'))
        elif header.compression_info == "lz4":
            compressed_data = lz4.frame.compress(json_data.encode('utf-8'))
        else: # Tidak terkompresi
            compressed_data = json_data.encode('utf-8')
        
        os.makedirs(output_dir, exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(compressed_data)
        
        logger.info(f"File .asu berhasil dibuat: {output_path} (Hash Konten: {file_hash})")
        return output_path

    async def execute_asu_file_async(self, file_path: str):
        """Antrikan file .asu untuk eksekusi oleh Scheduler."""
        if self.is_shutting_down:
            logger.warning("UTEK sedang shutdown, tidak menerima task baru.")
            return {"status": "failed", "error": "UTEK is shutting down."}
            
        try:
            file_asu = self.parse_asu_file(file_path)
            
            if file_asu.hash_sha256 in self.locked_executions:
                logger.error(f"Eksekusi file {file_asu.hash_sha256} terkunci.")
                return {"status": "failed", "error": "Execution locked."}

            await self.scheduler.submit_task(file_asu)
            return {"status": "submitted", "file_hash": file_asu.hash_sha256}
        except Exception as e:
            logger.error(f"Gagal mengirim file .asu {file_path} ke scheduler: {e}")
            return {"status": "failed", "error": str(e)}

    def lock_execution(self, file_hash: str):
        self.locked_executions.add(file_hash)
        logger.info(f"Eksekusi untuk file hash {file_hash} telah dikunci.")
    
    def unlock_execution(self, file_hash: str):
        self.locked_executions.discard(file_hash)
        logger.info(f"Lock eksekusi untuk file hash {file_hash} telah dibuka.")

    async def start(self):
        """Mulai Scheduler dan komponen lain jika perlu."""
        logger.info("UTEKVirtualExecutor starting...")
        self.scheduler_task = asyncio.create_task(self.scheduler.run_scheduler_loop())
        # Jika ada API server, mulai di sini (misal dengan hypercorn untuk FastAPI/Flask async)
        # self.api_server_task = asyncio.create_task(run_api_server(self.api_app))
        logger.info("UTEKVirtualExecutor started. Scheduler is running.")

    async def shutdown(self, reason: str = "Shutdown requested"):
        logger.info(f"UTEKVirtualExecutor shutting down... Reason: {reason}")
        self.is_shutting_down = True
        
        # Hentikan Scheduler dari menerima task baru (Queue bisa ditutup)
        if hasattr(self, 'scheduler_task') and self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                logger.info("Scheduler loop cancelled.")
        
        # Tunggu Tempik yang sedang berjalan selesai (dengan timeout) atau halt mereka
        active_tempik_tasks = []
        for tempik in self.tempik_pool:
            if tempik.status not in [TempikStatus.IDLE, TempikStatus.COMPLETED, TempikStatus.FAILED, TempikStatus.HALTED]:
                logger.info(f"Requesting HALT for active Tempik-{tempik.tempik_id}")
                tempik.control_unit.halt_execution("UTEK Shutdown")
                # Jika tempik.run() adalah task asyncio, kita bisa menunggunya
                # Ini tergantung bagaimana tempik.run() di-manage oleh scheduler
        
        # Beri waktu untuk Tempik menyelesaikan/halt
        # await asyncio.sleep(5) # Timeout untuk graceful shutdown Tempik
        
        # Hentikan API server jika ada
        # if hasattr(self, 'api_server_task') and self.api_server_task:
        #    self.api_server_task.cancel()
        #    try: await self.api_server_task
        #    except asyncio.CancelledError: logger.info("API server cancelled.")

        logger.info("UTEKVirtualExecutor shutdown complete.")

    def get_sistem_status(self) -> Dict[str, Any]:
        tempik_statuses = [t.get_status_summary() for t in self.tempik_pool]
        return {
            "total_tempik": self.max_tempik,
            "scheduler_queue_size": self.scheduler.queue.qsize(),
            "locked_executions_count": len(self.locked_executions),
            "is_shutting_down": self.is_shutting_down,
            "tempik_details": tempik_statuses
        }

# --- Fungsi utilitas dan CLI (disesuaikan) ---
def create_sample_asu_file_refactored(output_dir: str = ".") -> str:
    header = HeaderASU(
        processor_spec="963-Tempik-Refactored",
        protocol_version="v1.1.0",
        time_budget="max-exec-time=30s",
        dependency_manifest_hash=hashlib.sha256(b"sample_deps").hexdigest(),
        target_platform="any/virtual",
        execution_mode="batch",
        networking_mode="isolated", # atau "restricted" jika FETCH_REPO diizinkan
        license_access_info="UTEK Internal Use",
        max_size="10MB"
    )
    
    instructions = [
        InstruksiEksekusi(InstruksiASU.INIT_ENV, parameter={"working_dir": "/app"}),
        InstruksiEksekusi(InstruksiASU.SET_ENV, parameter={"API_URL": "http://example.com/api"}),
        InstruksiEksekusi(InstruksiASU.LOG, parameter={"message": "Starting sample ASU execution (refactored)."}),
        InstruksiEksekusi(InstruksiASU.INJECT, parameter={"path": "/app/config.txt", "content": "secret_value=12345"}),
        InstruksiEksekusi(InstruksiASU.VERIFY_HASH, parameter={"file": "/app/config.txt", "hash": hashlib.sha256(b"secret_value=12345").hexdigest()}),
        InstruksiEksekusi(InstruksiASU.IF, parameter={"condition": "env['API_URL'] == 'http://example.com/api'"}),
        InstruksiEksekusi(InstruksiASU.LOG, parameter={"message": "IF condition met!"}),
        InstruksiEksekusi(InstruksiASU.ELSE),
        InstruksiEksekusi(InstruksiASU.LOG, parameter={"message": "ELSE block executed (this shouldn't happen here)."}),
        InstruksiEksekusi(InstruksiASU.ENDIF),
        InstruksiEksekusi(InstruksiASU.EXECUTE, parameter={"command": "echo", "args": ["Hello from VFS Execute!"]}),
        InstruksiEksekusi(InstruksiASU.EXPORT, parameter={"source_vfs_path": "/app/config.txt", "target": "exported_config"}),
        InstruksiEksekusi(InstruksiASU.CLEANUP, parameter={"dir": "/app"}),
        InstruksiEksekusi(InstruksiASU.HALT, parameter={"reason": "Sample execution finished."})
    ]

    # Contoh struktur VFS dalam body
    vfs_struct = {
        "scripts": {
            "myscript.sh": "#!/bin/bash\necho 'Hello from myscript.sh in VFS!'"
        },
        "data": {
            "input.txt": "Sample input data."
        }
    }
    
    executor = UTEKVirtualExecutor() # Hanya untuk create_asu_file
    return executor.create_asu_file(header, instructions, virtual_fs_structure=vfs_struct, output_dir=output_dir)


async def main_cli_refactored():
    import argparse
    parser = argparse.ArgumentParser(description="UTEK Virtual 963-Tempik Executor (Refactored)")
    parser.add_argument("command", choices=["run", "create", "validate", "status"], help="Command to execute")
    parser.add_argument("--file", "-f", help="Path to .asu file for 'run' or 'validate'")
    parser.add_argument("--output_dir", "-o", default=".", help="Output directory for 'create'")
    parser.add_argument("--num_tempik", "-n", type=int, default=2, help="Number of Tempik units")
    
    args = parser.parse_args()
    
    executor = UTEKVirtualExecutor(max_tempik=args.num_tempik)
    
    if args.command == "create":
        print(f"Creating sample refactored .asu file in {args.output_dir}...")
        file_path = create_sample_asu_file_refactored(args.output_dir)
        print(f"Sample refactored .asu file created: {file_path}")
        return

    # Untuk command lain, kita perlu menjalankan event loop executor
    await executor.start() 
    
    try:
        if args.command == "run":
            if not args.file:
                parser.error("--file is required for 'run' command.")
            print(f"Submitting .asu file for execution: {args.file}")
            result = await executor.execute_asu_file_async(args.file)
            print(f"Submission result: {result}")
            if result.get("status") == "submitted":
                print("Execution submitted. Monitor logs or status for completion. Press Ctrl+C to stop executor.")
                # Keep executor running to process the queue
                while not executor.is_shutting_down: # Tunggu hingga semua task selesai atau diinterupsi
                    # Cek apakah semua tempik idle dan queue kosong
                    all_idle = all(t.status == TempikStatus.IDLE for t in executor.tempik_pool)
                    queue_empty = executor.scheduler.queue.empty()
                    if all_idle and queue_empty and executor.scheduler.queue._unfinished_tasks == 0:
                        logger.info("All tasks processed. Shutting down CLI.")
                        break
                    await asyncio.sleep(1)


        elif args.command == "validate":
            if not args.file:
                parser.error("--file is required for 'validate' command.")
            print(f"Validating .asu file: {args.file}")
            try:
                file_asu_obj = executor.parse_asu_file(args.file)
                # Tambahkan validasi lebih lanjut jika perlu (misal, terhadap schema)
                print(f"File .asu parsed successfully. Hash: {file_asu_obj.hash_sha256}")
                print("Basic validation successful.")
            except Exception as e:
                print(f"Validation failed: {e}")

        elif args.command == "status":
            status_info = executor.get_sistem_status()
            print("\n=== UTEK VIRTUAL SYSTEM STATUS ===")
            print(json.dumps(status_info, indent=2))
            print("Press Ctrl+C to stop executor if it's only showing status.")
            # Keep executor running if user just wants to see status and then maybe run
            while not executor.is_shutting_down:
                 await asyncio.sleep(5) # Tampilkan status berkala atau tunggu Ctrl+C
                 status_info = executor.get_sistem_status()
                 print("\n=== UTEK VIRTUAL SYSTEM STATUS (Update) ===")
                 print(json.dumps(status_info, indent=2))


    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received.")
    finally:
        await executor.shutdown("CLI session ended.")

if __name__ == "__main__":
    # Set PYTHONASYNCIODEBUG=1 untuk debug asyncio lebih detail
    # os.environ['PYTHONASYNCIODEBUG'] = '1'
    # logging.getLogger('asyncio').setLevel(logging.DEBUG)
    try:
        asyncio.run(main_cli_refactored())
    except KeyboardInterrupt:
        logger.info("UTEK Executor CLI terminated by user.")

