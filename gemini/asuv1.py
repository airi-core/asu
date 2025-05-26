#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UTEK Virtual — 963-Tempik Executor untuk File .asu (Refactor V3 Sesuai Audit)

Proyek: ASU Virtual UTEK 963-Tempik
Pengembang: Kode Baris Rahasia & Python Research (Direfactor sesuai Audit Internal)
Berdasarkan standar NDAS & MIKIR, serta temuan audit untuk kepatuhan Deloitte & IBM.

Dokumen ini mengimplementasikan arsitektur UTEK Virtual Executor
untuk memproses file .asu secara aman dan modular.
"""

import asyncio
import hashlib
import json
import logging
import os
import shutil
import subprocess # Digunakan dengan hati-hati dan dalam sandbox (konseptual)
import tempfile
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor # Untuk tugas non-async blocking
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable, Tuple
import gzip
import lz4.frame
# import requests # Akan diimpor dan digunakan secara kondisional oleh NetworkUnit
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding as asym_padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

# --- Konfigurasi Logging Global ---
# Menggunakan format logging yang lebih detail dan standar industri
logging.basicConfig(
    level=logging.INFO, # Level default, bisa di-override per modul
    format='%(asctime)s.%(msecs)03dZ | %(levelname)-8s | %(threadName)s | %(module)s.%(funcName)s:%(lineno)d | %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S'
)
# Mengatur timezone default untuk logging ke UTC
logging.Formatter.converter = time.gmtime
logger = logging.getLogger("UTEKVirtualExecutor")


# --- Enumerasi dan Konstanta Utama ---
class TempikStatus(Enum):
    """Status operasional untuk setiap unit Tempik."""
    IDLE = "idle" # Siap menerima tugas baru
    INITIALIZING = "initializing" # Sedang dalam proses inisialisasi
    FETCHING = "fetching" # Tahap pengambilan instruksi
    DECODING = "decoding" # Tahap pendekodean instruksi
    EXECUTING = "executing" # Tahap eksekusi logika instruksi
    MEMORY_ACCESS = "memory_access" # Tahap akses memori atau VFS
    WRITING_BACK = "writing_back" # Tahap penulisan hasil kembali
    WAITING = "waiting" # Menunggu kondisi atau waktu tertentu
    COMPLETED = "completed" # Tugas selesai dengan sukses
    FAILED = "failed" # Tugas gagal karena error
    HALTED = "halted" # Dihentikan secara eksplisit atau karena kondisi kritis

class PipelineStage(Enum):
    """Tahapan dalam siklus pemrosesan instruksi .asu oleh Tempik."""
    FETCH_INSTRUCTION = "FETCH_INSTRUCTION"
    DECODE_INSTRUCTION = "DECODE_INSTRUCTION"
    EXECUTE_OPERATION = "EXECUTE_OPERATION"
    ACCESS_MEMORY_OR_VFS = "ACCESS_MEMORY_OR_VFS"
    WRITE_BACK_RESULT = "WRITE_BACK_RESULT"

class InstruksiASU(Enum):
    """
    Instruction Set Architecture (ISA) untuk file .asu.
    Mendefinisikan semua operasi yang dapat diproses oleh UTEK Virtual Executor.
    """
    # Konfigurasi Lingkungan dan Konteks
    INIT_ENV = "INIT_ENV" # Inisialisasi lingkungan eksekusi Tempik
    SET_ENV = "SET_ENV" # Menetapkan variabel lingkungan
    SET_CONTEXT = "SET_CONTEXT" # Menetapkan parameter konteks eksekusi (role, namespace)
    SYNC_CLOCK = "SYNC_CLOCK" # Sinkronisasi jam (konseptual atau dengan NTP jika diizinkan)
    AUTH = "AUTH" # Autentikasi ke layanan eksternal atau internal

    # Manajemen Sumber Daya dan Dependensi
    FETCH_REPO = "FETCH_REPO" # Mengambil repositori kode dari sumber eksternal
    CHECKOUT = "CHECKOUT" # Pindah ke branch/commit/tag tertentu dalam repositori
    INSTALL = "INSTALL" # Instalasi dependensi atau paket perangkat lunak
    UNPACK = "UNPACK" # Mengekstrak arsip (zip, tar.gz)
    MOUNT = "MOUNT" # Memasang sistem file atau volume eksternal ke VirtualFS
    INJECT = "INJECT" # Menyuntikkan file atau data ke dalam VirtualFS
    COMPILE = "COMPILE" # Mengkompilasi kode sumber

    # Eksekusi Inti dan Kontrol Aliran
    EXECUTE = "EXECUTE" # Menjalankan perintah atau skrip utama
    CALL = "CALL" # Memanggil sub-program atau label dalam .asu saat ini
    RET = "RET" # Kembali dari sub-program (melengkapi CALL)
    JUMP = "JUMP" # Melompat ke label tertentu tanpa syarat
    SPAWN_THREAD = "SPAWN_THREAD" # Membuat thread eksekusi baru (konseptual, bisa Tempik baru)
    WAIT = "WAIT" # Menunggu durasi tertentu atau event
    DELEGATE_TO = "DELEGATE_TO" # Mendelegasikan eksekusi ke file .asu lain
    INVOKE_REMOTE = "INVOKE_REMOTE" # Memanggil layanan atau fungsi jarak jauh
    HALT = "HALT" # Menghentikan eksekusi Tempik saat ini secara terkendali
    SHUTDOWN = "SHUTDOWN" # Meminta penghentian seluruh UTEK Virtual Executor

    # Keamanan, Verifikasi, dan Kriptografi
    VERIFY_HASH = "VERIFY_HASH" # Memverifikasi hash integritas file
    VERIFY = "VERIFY" # Memverifikasi signature digital file atau data
    SIGN = "SIGN" # Menandatangani file atau data secara digital
    ENCRYPT = "ENCRYPT" # Mengenkripsi file atau data
    DECRYPT = "DECRYPT" # Mendekripsi file atau data
    LOCK_EXEC = "LOCK_EXEC" # Mengunci eksekusi file .asu tertentu agar tidak bisa dijalankan ulang

    # Audit, Logging, dan Event
    AUDIT_LOG = "AUDIT_LOG" # Mencatat event audit kustom ke log audit utama
    LOG = "LOG" # Mencatat pesan log standar dari dalam .asu
    EMIT_EVENT = "EMIT_EVENT" # Mengirimkan event ke sistem monitoring eksternal

    # Operasi Jaringan dan Distribusi
    NETWORK_UP = "NETWORK_UP" # Mengaktifkan atau mengkonfigurasi antarmuka jaringan virtual
    MAP_PORT = "MAP_PORT" # Memetakan port dari layanan internal Tempik ke host atau jaringan eksternal
    PUSH_RESULT = "PUSH_RESULT" # Mengirimkan hasil eksekusi ke destinasi eksternal

    # Logika Kondisional dan Kontrol
    IF = "IF" # Memulai blok kondisional berdasarkan evaluasi ekspresi
    ELSE = "ELSE" # Blok alternatif jika kondisi IF tidak terpenuhi
    ENDIF = "ENDIF" # Menandai akhir blok kondisional IF/ELSE
    ASSERT = "ASSERT" # Memastikan suatu kondisi terpenuhi, gagal jika tidak

    # Manajemen Hasil dan Pembersihan
    EXPORT = "EXPORT" # Mengekspor artefak (file/direktori) dari VirtualFS
    CLEANUP = "CLEANUP" # Membersihkan file atau direktori sementara
    NOP = "NOP" # No Operation, tidak melakukan apa-apa

# --- Struktur Data Inti untuk File .asu ---
@dataclass
class HeaderASU:
    """
    Representasi header file .asu, sesuai spesifikasi standar yang diperluas.
    Berisi metadata krusial untuk eksekusi dan pengelolaan file .asu.
    """
    processor_spec: str = "UTEK-963-Tempik-Executor-V3" # Identifikasi platform target
    protocol_version: str = "ASU-Spec-v1.2.1" # Versi spesifikasi .asu yang didukung
    execution_environment: str = "python-3.10-UTEK" # Runtime environment yang dibutuhkan
    memory_profile: str = "balanced-512MiB" # Profil penggunaan memori (misal: "low-128MiB", "high-1GiB")
    filesystem_scheme: str = "isolated-vfs" # Skema filesystem yang digunakan (misal: "chroot-like", "memfs")
    security_flags: List[str] = field(default_factory=lambda: ["sandboxed", "no-root-privileges", "network-restricted"])
    time_budget: str = "max-total-exec-time=300s;max-instruction-time=60s" # Batasan waktu eksekusi
    checksum_signature: str = "" # Checksum (misal SHA256) atau signature digital dari konten file .asu (setelah kompresi)
    compression_info: str = "gzip" # Algoritma kompresi yang digunakan ("gzip", "lz4", "none")
    asu_build_info: str = "" # Informasi build: "builder=SDK-vX.Y;build-timestamp=YYYY-MM-DDTHH:MM:SSZ"
    dependency_manifest_hash: str = "" # Hash dari manifest dependensi eksternal (jika ada)
    target_platform: str = "any-virtualized" # Platform target (misal: "linux/amd64-virtual", "wasm32-sandboxed")
    execution_mode: str = "batch-headless" # Mode eksekusi ("batch-headless", "interactive-service")
    networking_mode: str = "isolated-outbound-only" # Aturan jaringan ("offline", "restricted-outbound", "bridged")
    license_access_info: str = "PROPRIETARY-UTEK-INTERNAL" # Informasi lisensi atau path ke file lisensi
    max_size: str = "2GB" # Ukuran maksimum file .asu yang diizinkan (setelah dekompresi)

    def to_dict(self) -> Dict[str, Any]:
        """Mengkonversi header ke dictionary untuk serialisasi atau logging."""
        return {key: getattr(self, key) for key in self.__annotations__}


@dataclass
class InstruksiEksekusi:
    """
    Representasi satu instruksi dalam body file .asu.
    Mencakup jenis instruksi, parameter, label untuk kontrol aliran, timeout, dan retry.
    """
    instruksi: InstruksiASU
    parameter: Dict[str, Any] = field(default_factory=dict)
    label: Optional[str] = None # Label opsional untuk target JUMP atau CALL
    timeout_seconds: float = 30.0 # Batas waktu eksekusi untuk instruksi ini
    retry_attempts: int = 0 # Jumlah percobaan ulang jika gagal (0 berarti tidak ada retry)
    
    def to_dict(self) -> Dict[str, Any]:
        """Mengkonversi instruksi ke dictionary untuk serialisasi atau logging."""
        return {
            "instruksi": self.instruksi.value,
            "parameter": self.parameter,
            "label": self.label,
            "timeout_seconds": self.timeout_seconds,
            "retry_attempts": self.retry_attempts
        }

@dataclass
class FileASU:
    """
    Representasi lengkap dari file .asu, mencakup header dan body (daftar instruksi).
    Juga menyimpan hash SHA-256 dari kontennya untuk verifikasi integritas.
    """
    header: HeaderASU
    body: List[InstruksiEksekusi] = field(default_factory=list)
    # Hash dari konten (header + body) sebelum kompresi, digunakan untuk nama file dan integritas
    content_hash_sha256: str = "" 

    def generate_content_hash(self) -> str:
        """Menghasilkan hash SHA-256 dari konten header dan body."""
        header_dict_sorted = dict(sorted(self.header.to_dict().items()))
        
        # Memastikan urutan parameter dalam setiap instruksi konsisten untuk hashing
        body_list_prepared_for_hash = []
        for instr_obj in self.body:
            instr_dict = instr_obj.to_dict()
            if isinstance(instr_dict.get("parameter"), dict):
                instr_dict["parameter"] = dict(sorted(instr_dict["parameter"].items()))
            body_list_prepared_for_hash.append(dict(sorted(instr_dict.items())))
        
        content_to_hash = {
            "header": header_dict_sorted,
            "body": body_list_prepared_for_hash
        }
        # Menggunakan separator yang rapat untuk mengurangi variasi spasi
        content_str = json.dumps(content_to_hash, sort_keys=True, separators=(',', ':'))
        hash_obj = hashlib.sha256(content_str.encode('utf-8'))
        self.content_hash_sha256 = hash_obj.hexdigest()
        return self.content_hash_sha256

# --- Komponen Arsitektur UTEK Virtual (Sesuai Daftar Audit) ---

@dataclass
class RegisterStorage: # Menggantikan RegisterFile untuk terminologi yang lebih netral
    """
    Penyimpanan state internal untuk sebuah Tempik.
    Berisi register program counter (PC), stack pointer (SP), link register (LR),
    flag kondisional, dan register serbaguna (gpr) untuk penggunaan instruksi .asu.
    """
    pc: int = 0  # Program Counter: alamat (indeks) instruksi berikutnya dalam body .asu
    sp: int = 0  # Stack Pointer: menunjuk ke puncak stack di MemoryUnit (konseptual)
    lr: int = 0  # Link Register: menyimpan alamat kembali untuk instruksi CALL
    
    # General Purpose Registers (GPRs) untuk penggunaan oleh instruksi .asu
    # Bisa digunakan untuk menyimpan hasil sementara, parameter, atau variabel skrip.
    gpr: Dict[str, Any] = field(default_factory=lambda: {f"gpr{i}": None for i in range(16)})
    
    # Flags untuk hasil operasi dan kontrol aliran kondisional
    flags: Dict[str, bool] = field(default_factory=lambda: {
        "Z": False,  # Zero Flag (hasil operasi terakhir adalah nol)
        "N": False,  # Negative/Sign Flag (hasil operasi terakhir negatif)
        "C": False,  # Carry Flag (terjadi carry/borrow)
        "V": False,  # Overflow Flag (terjadi overflow aritmatika)
        "COND": True # Conditional Execution Flag (hasil evaluasi IF terakhir)
    })

    def get_gpr(self, name: str) -> Any:
        """Mengambil nilai dari General Purpose Register."""
        return self.gpr.get(name.lower())

    def set_gpr(self, name: str, value: Any):
        """Menetapkan nilai ke General Purpose Register."""
        name_lower = name.lower()
        if name_lower in self.gpr:
            self.gpr[name_lower] = value
            logger.debug(f"GPR '{name_lower}' di-set menjadi: {value}")
        else:
            logger.warning(f"Percobaan menulis ke GPR tidak dikenal: {name}")

    def get_flag(self, flag_name: str) -> bool:
        """Mengambil status flag kondisional."""
        return self.flags.get(flag_name.upper(), False) # Default False jika flag tidak ada

    def set_flag(self, flag_name: str, value: bool):
        """Menetapkan status flag kondisional."""
        flag_upper = flag_name.upper()
        if flag_upper in self.flags:
            self.flags[flag_upper] = value
            logger.debug(f"Flag '{flag_upper}' di-set menjadi: {value}")
        else:
            logger.warning(f"Percobaan menetapkan flag tidak dikenal: {flag_name}")


class ProgramCounterManager: # Dipisahkan untuk kejelasan, meski bisa jadi bagian RegisterStorage
    """Mengelola Program Counter (PC) untuk sebuah Tempik."""
    def __init__(self, register_storage: RegisterStorage):
        self._regs = register_storage

    @property
    def current_address(self) -> int:
        """Alamat instruksi saat ini yang ditunjuk oleh PC."""
        return self._regs.pc

    def advance(self, steps: int = 1):
        """Memajukan PC sebanyak 'steps' instruksi."""
        self._regs.pc += steps

    def jump_to(self, new_address: int):
        """Mengatur PC ke alamat instruksi baru."""
        self._regs.pc = new_address
        logger.debug(f"Program Counter diatur ke alamat: {new_address}")


class ControlSignalUnit: # Menggantikan ControlUnit, fokus pada sinyal kontrol
    """
    Unit Sinyal Kontrol (konseptual).
    Dalam implementasi ini, perannya lebih terdistribusi dalam logika Pipeline dan Tempik
    untuk mengkoordinasikan tahapan fetch, decode, dan dispatch eksekusi.
    Tidak direpresentasikan sebagai kelas konkret dengan state internal yang banyak,
    namun logikanya terwujud dalam alur kerja Pipeline.
    """
    def __init__(self, tempik_id_str: str):
        self.tempik_id_str = tempik_id_str
        logger.debug(f"[{self.tempik_id_str}] ControlSignalUnit (konseptual) aktif.")

    def issue_fetch_signal(self, pc_address: int):
        """Memberikan sinyal untuk memulai pengambilan instruksi."""
        logger.debug(f"[{self.tempik_id_str}] Sinyal FETCH dikeluarkan untuk PC={pc_address}")

    def issue_decode_signal(self, fetched_instruction_details: str):
        """Memberikan sinyal untuk memulai pendekodean instruksi."""
        logger.debug(f"[{self.tempik_id_str}] Sinyal DECODE dikeluarkan untuk instruksi: {fetched_instruction_details}")

    def issue_execute_dispatch_signal(self, decoded_instruction_op: str):
        """Memberikan sinyal untuk dispatch eksekusi operasi."""
        logger.debug(f"[{self.tempik_id_str}] Sinyal EXECUTE_DISPATCH dikeluarkan untuk operasi: {decoded_instruction_op}")


class ArithmeticLogicExecutionUnit: # Menggantikan ALU, fokus pada eksekusi logika
    """
    Unit Eksekusi Logika dan Aritmatika.
    Bertugas melakukan evaluasi ekspresi kondisional dan operasi logika/aritmatika
    sederhana yang dibutuhkan oleh instruksi .asu, dan mengatur flag yang relevan.
    """
    def __init__(self, register_storage: RegisterStorage):
        self._regs = register_storage

    def evaluate_condition(self, condition_str: str, context: 'ExecutionContextManager') -> bool:
        """
        Mengevaluasi string kondisi (misalnya dari IF, ASSERT).
        Menggunakan nilai dari RegisterStorage (GPR) dan ExecutionContextManager (env vars).
        PENTING: Implementasi ini harus menggunakan parser ekspresi yang AMAN, bukan eval().
        """
        # Placeholder untuk parser ekspresi yang aman.
        # Contoh logika sederhana (TIDAK AMAN UNTUK PRODUKSI):
        try:
            # Ganti placeholder "reg.gprX" dan "env.VAR_NAME" dengan nilainya
            # Ini adalah contoh yang sangat disederhanakan dan tidak lengkap.
            local_vars = {"True": True, "False": False, "None": None}
            for i in range(16):
                local_vars[f"gpr{i}"] = self._regs.get_gpr(f"gpr{i}")
            
            # Tambahkan env vars dari context (dengan prefix untuk menghindari konflik)
            for key, value in context.environment_vars.items():
                # Pastikan key aman untuk digunakan sebagai nama variabel Python
                safe_key = f"env_{key.replace('-', '_').replace('.', '_')}" 
                local_vars[safe_key] = value
                # Ganti env.VAR_NAME di condition_str dengan safe_key
                condition_str = condition_str.replace(f"env.{key}", safe_key)
            
            # Ganti reg.gprX
            for i in range(16):
                condition_str = condition_str.replace(f"reg.gpr{i}", f"gpr{i}")


            # Contoh evaluasi sederhana (masih berisiko jika condition_str tidak terkontrol)
            # Menggunakan pendekatan yang lebih terkontrol daripada eval() langsung.
            # Misalnya, jika hanya mendukung perbandingan sederhana:
            if "==" in condition_str:
                op1_str, op2_str = [s.strip() for s in condition_str.split("==", 1)]
                op1 = self._resolve_operand_for_eval(op1_str, local_vars)
                op2 = self._resolve_operand_for_eval(op2_str, local_vars)
                result = (op1 == op2)
                self._regs.set_flag("Z", result)
                return result
            elif "!=" in condition_str:
                op1_str, op2_str = [s.strip() for s in condition_str.split("!=", 1)]
                op1 = self._resolve_operand_for_eval(op1_str, local_vars)
                op2 = self._resolve_operand_for_eval(op2_str, local_vars)
                result = (op1 != op2)
                self._regs.set_flag("Z", not result)
                return result
            # Tambahkan operator lain (>, <, >=, <=, AND, OR) dengan parser yang aman
            
            logger.warning(f"Format kondisi '{condition_str}' tidak didukung oleh evaluator sederhana.")
            return False # Default jika tidak bisa dievaluasi
        except Exception as e:
            logger.error(f"Error saat mengevaluasi kondisi '{condition_str}': {e}")
            return False

    def _resolve_operand_for_eval(self, operand_str: str, local_vars: Dict) -> Any:
        """Helper untuk mengambil nilai operand untuk evaluasi kondisi."""
        operand_str_stripped = operand_str.strip()
        if operand_str_stripped in local_vars:
            return local_vars[operand_str_stripped]
        # Cek apakah literal string
        if (operand_str_stripped.startswith("'") and operand_str_stripped.endswith("'")) or \
           (operand_str_stripped.startswith('"') and operand_str_stripped.endswith('"')):
            return operand_str_stripped[1:-1]
        # Cek apakah literal angka
        try: return int(operand_str_stripped)
        except ValueError: pass
        try: return float(operand_str_stripped)
        except ValueError: pass
        # Jika tidak, kembalikan sebagai string (mungkin nama variabel yang tidak dikenal)
        logger.debug(f"Operand '{operand_str_stripped}' tidak ditemukan di local_vars, dianggap string literal.")
        return operand_str_stripped


class RuntimeDataStorage: # Menggantikan MemoryUnit, fokus pada penyimpanan data runtime
    """
    Penyimpanan Data Runtime untuk Tempik.
    Mengelola stack untuk pemanggilan fungsi/sub-program (CALL/RET) dan
    bisa juga digunakan untuk alokasi memori dinamis sederhana jika diperlukan oleh instruksi .asu.
    Data file besar dikelola oleh VirtualFS.
    """
    def __init__(self, register_storage: RegisterStorage, max_stack_size: int = 1024):
        self._regs = register_storage
        self._stack: List[Any] = []
        self._max_stack_size = max_stack_size
        # Inisialisasi Stack Pointer (SP) di RegisterStorage
        self._regs.sp = 0 # Stack kosong, SP menunjuk ke dasar (atau bisa juga puncak)
        logger.debug("RuntimeDataStorage (Stack) diinisialisasi.")

    def push_to_stack(self, value: Any):
        """Mendorong nilai ke puncak stack."""
        if len(self._stack) >= self._max_stack_size:
            raise OverflowError("Stack overflow pada RuntimeDataStorage.")
        self._stack.append(value)
        self._regs.sp = len(self._stack) # SP menunjuk ke jumlah elemen (puncak)
        logger.debug(f"PUSH ke stack: {value}. SP sekarang: {self._regs.sp}")

    def pop_from_stack(self) -> Any:
        """Mengambil dan menghapus nilai dari puncak stack."""
        if not self._stack:
            raise IndexError("Stack underflow pada RuntimeDataStorage (pop dari stack kosong).")
        value = self._stack.pop()
        self._regs.sp = len(self._stack)
        logger.debug(f"POP dari stack: {value}. SP sekarang: {self._regs.sp}")
        return value

    def peek_stack(self) -> Any:
        """Melihat nilai di puncak stack tanpa menghapusnya."""
        if not self._stack:
            raise IndexError("Stack underflow pada RuntimeDataStorage (peek stack kosong).")
        return self._stack[-1]


class InstructionCacheManager: # Menggantikan InstructionCache
    """
    Manajer Cache Instruksi.
    Menyimpan instruksi .asu yang sudah di-fetch dan di-decode untuk mempercepat akses berulang.
    """
    def __init__(self, capacity: int = 256): # Kapasitas cache dalam jumlah instruksi
        self._cache: Dict[int, InstruksiEksekusi] = {} # Alamat PC -> Objek InstruksiEksekusi
        self._capacity = capacity
        self._access_order: List[int] = [] # Untuk implementasi LRU (Least Recently Used)
        logger.debug(f"InstructionCacheManager diinisialisasi dengan kapasitas: {capacity} instruksi.")

    def get_instruction(self, pc_address: int) -> Optional[InstruksiEksekusi]:
        """Mencari instruksi di cache berdasarkan alamat PC."""
        if pc_address in self._cache:
            # Pindahkan ke akhir daftar akses untuk menandai sebagai baru digunakan (LRU)
            self._access_order.remove(pc_address)
            self._access_order.append(pc_address)
            logger.debug(f"Cache HIT untuk instruksi di PC={pc_address}.")
            return self._cache[pc_address]
        logger.debug(f"Cache MISS untuk instruksi di PC={pc_address}.")
        return None

    def store_instruction(self, pc_address: int, instruction: InstruksiEksekusi):
        """Menyimpan instruksi ke cache."""
        if len(self._cache) >= self._capacity:
            # Kapasitas penuh, hapus instruksi yang paling lama tidak digunakan (LRU)
            if self._access_order:
                lru_address = self._access_order.pop(0) # Ambil dari awal daftar
                del self._cache[lru_address]
                logger.debug(f"Cache eviction (LRU): Instruksi di PC={lru_address} dihapus.")
        
        self._cache[pc_address] = instruction
        self._access_order.append(pc_address) # Tambahkan ke akhir daftar akses
        logger.debug(f"Instruksi di PC={pc_address} disimpan ke cache.")


class DataCacheManager: # Menggantikan DataCache
    """
    Manajer Cache Data.
    Menyimpan data yang sering diakses (misalnya, isi file kecil dari VirtualFS)
    untuk mengurangi latensi I/O.
    """
    def __init__(self, max_size_bytes: int = 1 * 1024 * 1024): # Default cache 1MB
        self._cache: Dict[str, bytes] = {} # Kunci data (misal, path VFS) -> konten bytes
        self._max_size_bytes = max_size_bytes
        self._current_size_bytes: int = 0
        self._access_order: List[str] = [] # Untuk LRU
        logger.debug(f"DataCacheManager diinisialisasi dengan kapasitas: {max_size_bytes / (1024*1024):.2f} MB.")

    def get_data(self, key: str) -> Optional[bytes]:
        """Mengambil data dari cache berdasarkan kunci."""
        if key in self._cache:
            self._access_order.remove(key)
            self._access_order.append(key)
            logger.debug(f"Data cache HIT untuk kunci: {key}")
            return self._cache[key]
        logger.debug(f"Data cache MISS untuk kunci: {key}")
        return None

    def store_data(self, key: str, data: bytes):
        """Menyimpan data ke cache."""
        data_size = len(data)
        if data_size > self._max_size_bytes:
            logger.warning(f"Data untuk kunci '{key}' ({data_size} bytes) terlalu besar untuk cache ({self._max_size_bytes} bytes). Tidak disimpan.")
            return

        # Kosongkan ruang jika perlu (LRU)
        while self._current_size_bytes + data_size > self._max_size_bytes and self._access_order:
            lru_key = self._access_order.pop(0)
            lru_data_size = len(self._cache[lru_key])
            del self._cache[lru_key]
            self._current_size_bytes -= lru_data_size
            logger.debug(f"Data cache eviction (LRU): Kunci '{lru_key}' ({lru_data_size} bytes) dihapus.")
            
        self._cache[key] = data
        self._access_order.append(key)
        self._current_size_bytes += data_size
        logger.debug(f"Data untuk kunci '{key}' ({data_size} bytes) disimpan ke cache. Ukuran cache saat ini: {self._current_size_bytes} bytes.")


class InputOutputOperationHandler: # Menggantikan IOHandler
    """
    Penangan Operasi Input/Output untuk Tempik.
    Mengelola logging standar, interaksi dengan VirtualFS (melalui Tempik),
    dan potensi interaksi pengguna jika execution_mode mendukungnya.
    """
    def __init__(self, tempik_id_str: str, audit_logger_ref: 'AuditLogger'):
        self.tempik_id_str = tempik_id_str
        self._audit_logger = audit_logger_ref # Referensi ke logger audit utama
        logger.debug(f"[{self.tempik_id_str}] InputOutputOperationHandler diinisialisasi.")

    def standard_log(self, message: str, level: str = "INFO", source_instruction: Optional[str] = None, current_file_hash: Optional[str] = None):
        """Mencatat pesan log standar dari Tempik."""
        log_level_enum = getattr(logging, level.upper(), logging.INFO)
        # Pesan log utama akan dicatat oleh logger global dengan format yang sudah ada
        logger.log(log_level_enum, f"[{self.tempik_id_str}] {message}")

        # Jika ini adalah output dari instruksi LOG atau EXECUTE, catat juga ke audit
        if source_instruction and current_file_hash and level.upper() in ["INFO", "WARNING", "ERROR", "CRITICAL"]:
            self._audit_logger.log_event(
                datetime.now(timezone.utc).isoformat(), # Gunakan UTC untuk audit
                self.tempik_id_str,
                source_instruction, # Nama instruksi .asu yang menghasilkan log ini
                level.upper(), # Status log sebagai hasil
                0, # Durasi tidak relevan untuk log ini
                current_file_hash,
                f"LOG_OUTPUT: {message}" # Detail pesan log
            )

    # Operasi file VFS (read/write) akan dilakukan oleh Tempik melalui instance VirtualFS-nya,
    # IOHandler ini hanya untuk logging atau interaksi pengguna (jika ada).


class TaskScheduler: # Menggantikan Scheduler
    """
    Penjadwal Tugas untuk UTEK Virtual Executor.
    Bertugas mengalokasikan Tempik yang tersedia untuk menjalankan file .asu.
    """
    def __init__(self, tempik_pool_ref: List['Tempik']):
        self._tempik_pool = tempik_pool_ref # Referensi ke pool Tempik
        self._strategy = "round_robin" # Strategi default
        self._last_assigned_idx = -1 # Untuk round robin
        logger.info(f"TaskScheduler diinisialisasi dengan strategi '{self._strategy}' untuk {len(self._tempik_pool)} Tempik.")

    def request_available_tempik(self) -> Optional['Tempik']:
        """Meminta Tempik yang idle dari pool menggunakan strategi yang dipilih."""
        if not self._tempik_pool:
            return None
        
        # Implementasi Round Robin sederhana
        if self._strategy == "round_robin":
            # Cari Tempik idle mulai dari setelah yang terakhir ditugaskan
            for i in range(len(self._tempik_pool)):
                idx = (self._last_assigned_idx + 1 + i) % len(self._tempik_pool)
                if self._tempik_pool[idx].current_status == TempikStatus.IDLE:
                    self._last_assigned_idx = idx
                    logger.debug(f"TaskScheduler: Tempik-{self._tempik_pool[idx].tempik_id} dialokasikan (Round Robin).")
                    return self._tempik_pool[idx]
        
        # TODO: Implementasi strategi lain (priority, least_busy)
        logger.warning("TaskScheduler: Tidak ada Tempik yang idle saat ini.")
        return None # Tidak ada Tempik idle


# Kelas Tempik dan Pipeline akan direstrukturisasi secara signifikan
# untuk mencerminkan alur kerja yang diminta audit.

class SecurityPolicyModule: # Menggantikan SecurityModule
    """
    Modul Kebijakan Keamanan.
    Menerapkan dan memverifikasi kebijakan keamanan selama eksekusi .asu.
    Termasuk validasi perintah, kontrol akses, dan manajemen status penguncian eksekusi.
    """
    def __init__(self, tempik_id_str: str, initial_security_flags: List[str]):
        self.tempik_id_str = tempik_id_str
        self._flags = set(s.lower() for s in initial_security_flags) # Normalisasi ke lowercase
        self._globally_locked_hashes: Set[str] = set() # Dikelola oleh UTEKVirtualExecutor
        logger.info(f"[{self.tempik_id_str}] SecurityPolicyModule diinisialisasi dengan flags: {self._flags}")

    def update_flags(self, new_flags: List[str]):
        """Memperbarui security flags saat runtime (jika diizinkan)."""
        # Perlu ada mekanisme untuk mengontrol apakah flags bisa diubah.
        self._flags = set(s.lower() for s in new_flags)
        logger.info(f"[{self.tempik_id_str}] Security flags diperbarui menjadi: {self._flags}")

    def is_command_allowed(self, command_parts: List[str], context: 'ExecutionContextManager') -> bool:
        """Memeriksa apakah eksekusi perintah diizinkan berdasarkan policy."""
        if "no-execute" in self._flags:
            logger.warning(f"[{self.tempik_id_str}] Eksekusi perintah '{' '.join(command_parts)}' diblokir oleh flag 'no-execute'.")
            return False
        
        # Implementasi blacklist/whitelist perintah yang lebih canggih
        # Contoh sederhana:
        # command_str = " ".join(command_parts).lower()
        # if "rm -rf" in command_str and "allow-dangerous-commands" not in self._flags :
        #     logger.error(f"[{self.tempik_id_str}] Perintah berbahaya terdeteksi dan diblokir: {command_str}")
        #     return False
        
        # Periksa apakah perintah adalah internal VFS atau memerlukan interaksi host
        if command_parts[0].startswith("vfs_"): # Perintah internal VFS biasanya aman
            return True
        
        # Jika bukan perintah internal, dan tidak ada izin khusus, anggap tidak aman by default
        if "allow-host-subprocess" not in self._flags:
            logger.warning(f"[{self.tempik_id_str}] Eksekusi subproses host untuk '{' '.join(command_parts)}' tidak diizinkan (membutuhkan flag 'allow-host-subprocess').")
            return False
            
        logger.debug(f"[{self.tempik_id_str}] Perintah '{' '.join(command_parts)}' diizinkan untuk eksekusi (dengan asumsi sandbox eksternal).")
        return True # Asumsikan aman jika lolos pemeriksaan dasar

    def is_vfs_readonly(self) -> bool:
        """Apakah VirtualFS dalam mode readonly."""
        return "vfs-readonly" in self._flags or "immutable-fs" in self._flags

    def can_access_network(self, networking_mode_from_context: str) -> bool:
        """Apakah akses jaringan diizinkan berdasarkan flag dan mode jaringan konteks."""
        if "no-network-access" in self._flags:
            return False
        if networking_mode_from_context == "offline" and "force-network-online" not in self._flags:
            return False
        return True

    def lock_file_hash_execution(self, file_hash: str, global_lock_set: Set[str]):
        """Mengunci eksekusi untuk file hash tertentu secara global."""
        global_lock_set.add(file_hash)
        logger.info(f"[{self.tempik_id_str}] Eksekusi untuk file hash '{file_hash}' telah dikunci secara global.")

    def is_file_hash_execution_locked(self, file_hash: str, global_lock_set: Set[str]) -> bool:
        """Memeriksa apakah eksekusi file hash terkunci secara global."""
        return file_hash in global_lock_set


class InterruptHandlingController: # Menggantikan InterruptController
    """
    Pengontrol Penanganan Interupsi.
    Menyediakan mekanisme untuk menangani event tak terduga atau sinyal interupsi
    selama eksekusi Tempik (misalnya, timeout, error kritis, permintaan halt).
    """
    def __init__(self, tempik_ref: 'Tempik'): # Membutuhkan referensi ke Tempik untuk mengubah statusnya
        self._tempik = tempik_ref
        self._interrupt_handlers: Dict[str, Callable[[Any], Coroutine[Any, Any, Any]]] = {} # nama_interupsi -> async handler
        logger.debug(f"[{self._tempik.tempik_id_str}] InterruptHandlingController diinisialisasi.")

    def register_interrupt_handler(self, interrupt_name: str, async_handler: Callable[[Any], Coroutine[Any, Any, Any]]):
        """Mendaftarkan handler asinkron untuk interupsi tertentu."""
        self._interrupt_handlers[interrupt_name.lower()] = async_handler
        logger.debug(f"[{self._tempik.tempik_id_str}] Handler untuk interupsi '{interrupt_name}' didaftarkan.")

    async def signal_interrupt(self, interrupt_name: str, details: Optional[Any] = None):
        """Memicu interupsi dan menjalankan handler yang terdaftar."""
        name_lower = interrupt_name.lower()
        logger.warning(f"[{self._tempik.tempik_id_str}] Interupsi '{name_lower}' diterima dengan detail: {details}")
        
        if name_lower in self._interrupt_handlers:
            try:
                await self._interrupt_handlers[name_lower](details)
            except Exception as e:
                logger.error(f"[{self._tempik.tempik_id_str}] Error saat menjalankan handler untuk interupsi '{name_lower}': {e}", exc_info=True)
                # Fallback jika handler gagal: set status Tempik ke FAILED
                self._tempik.current_status = TempikStatus.FAILED
        else:
            logger.warning(f"[{self._tempik.tempik_id_str}] Tidak ada handler spesifik untuk interupsi '{name_lower}'. Mengambil tindakan default (HALT/FAIL).")
            # Tindakan default jika tidak ada handler
            if name_lower == "critical_error" or name_lower == "unhandled_exception":
                self._tempik.current_status = TempikStatus.FAILED
            else: # Misal untuk timeout atau permintaan halt eksternal
                self._tempik.current_status = TempikStatus.HALTED
        
        # Setelah interupsi ditangani (atau default), pipeline Tempik harus berhenti atau mengambil tindakan sesuai status baru.


class IsolatedVirtualFileSystem: # Menggantikan VirtualFS, nama lebih deskriptif
    """
    Sistem File Virtual Terisolasi untuk setiap Tempik.
    Menyediakan abstraksi filesystem in-memory atau terpetakan (chroot-like)
    untuk operasi file instruksi .asu, memastikan isolasi antar Tempik.
    Implementasi ini adalah in-memory dasar.
    """
    # Implementasi kelas IsolatedVirtualFileSystem (VFSNode, mkdir, write_file, read_file, dll.)
    # akan sama atau sangat mirip dengan VirtualFS di V2.
    # Perubahan utama adalah penekanan pada isolasi dan potensi integrasi
    # dengan mekanisme chroot/jail jika UTEK berjalan di environment yang mendukung.
    # Untuk menjaga respons tidak terlalu panjang, kita akan merujuk ke implementasi VFS dari V2.
    # Pastikan semua path dinormalisasi dan CWD dari ExecutionContextManager digunakan.
    # ... (Salin dan sesuaikan implementasi VirtualFS dari V2 di sini, ganti nama kelas) ...
    # Contoh:
    def __init__(self, tempik_id_str: str):
        self.tempik_id_str = tempik_id_str
        self.root: VFSNode = VFSNode(name="/", is_directory=True) # VFSNode dari V2
        self.mount_points: Dict[str, Tuple[str, Dict[str, Any]]] = {} # vfs_path -> (host_path_or_source, options)
        logger.info(f"[{self.tempik_id_str}] IsolatedVirtualFileSystem diinisialisasi.")

    def _normalize_path(self, path: str, context: 'ExecutionContextManager') -> str:
        """Normalisasi path, menggabungkan dengan CWD jika relatif."""
        if path != "/" and path.endswith("/"): path = path[:-1]
        if not path: path = "/" # Path kosong berarti root

        if path.startswith("/"):
            abs_path = os.path.normpath(path)
        else:
            abs_path = os.path.normpath(os.path.join(context.current_working_directory, path))
        
        if not abs_path.startswith("/"): abs_path = "/" + abs_path
        return abs_path

    def _get_node_and_parent(self, norm_path: str) -> Tuple[Optional[VFSNode], Optional[VFSNode], Optional[str]]:
        """Mendapatkan node pada path, parent-nya, dan nama node terakhir."""
        parts = [part for part in norm_path.strip("/").split("/") if part]
        current_node = self.root
        parent_node = None # Parent dari current_node
        last_part_name = "" # Nama dari current_node relatif terhadap parent_node

        if not parts: return self.root, None, "/" # Path adalah root

        for i, part in enumerate(parts):
            if not current_node.is_directory or current_node.children is None:
                logger.debug(f"Path '{norm_path}' melewati file '{current_node.name}' atau direktori tanpa children.")
                return None, None, None 

            parent_node = current_node
            last_part_name = part
            current_node = current_node.children.get(part)

            if current_node is None: # Node tidak ada
                if i == len(parts) - 1: # Ini adalah node terakhir yang dicari, parent-nya ada
                    return None, parent_node, last_part_name
                logger.debug(f"Path intermediate '{part}' tidak ditemukan dalam '{norm_path}'.")
                return None, None, None # Path intermediate tidak ditemukan
        
        return current_node, parent_node, last_part_name

    def mkdir(self, path: str, context: 'ExecutionContextManager', make_parents: bool = False):
        norm_path = self._normalize_path(path, context)
        if norm_path == "/": return # Root sudah ada

        node, parent, node_name = self._get_node_and_parent(norm_path)

        if node is not None:
            if not node.is_directory:
                raise FileExistsError(f"VFS Error: Path '{norm_path}' sudah ada dan bukan direktori.")
            return # Direktori sudah ada

        if parent is None or node_name is None : # Harusnya tidak terjadi jika path bukan root
            if make_parents:
                parent_dir_path = os.path.dirname(norm_path)
                if parent_dir_path and parent_dir_path != norm_path:
                    self.mkdir(parent_dir_path, context, make_parents=True)
                    # Coba lagi setelah membuat parent
                    _, parent, node_name = self._get_node_and_parent(norm_path)
                    if parent is None or node_name is None: # Tetap gagal
                        raise FileNotFoundError(f"VFS Error: Gagal membuat parent direktori untuk '{norm_path}'.")
            else:
                raise FileNotFoundError(f"VFS Error: Path parent untuk '{norm_path}' tidak ditemukan.")
        
        if parent and node_name and parent.is_directory and parent.children is not None:
            new_dir_node = VFSNode(name=node_name, is_directory=True)
            parent.children[node_name] = new_dir_node
            logger.info(f"[{self.tempik_id_str}] VFS: Direktori dibuat: {norm_path}")
        else:
            raise FileNotFoundError(f"VFS Error: Gagal menemukan parent yang valid untuk membuat direktori '{norm_path}'.")


    def write_file(self, path: str, content: Union[str, bytes], context: 'ExecutionContextManager'):
        norm_path = self._normalize_path(path, context)
        content_bytes = content.encode('utf-8') if isinstance(content, str) else content
        
        node, parent, node_name = self._get_node_and_parent(norm_path)

        if node is not None and node.is_directory:
            raise IsADirectoryError(f"VFS Error: Tidak bisa menulis file, path '{norm_path}' adalah direktori.")

        if parent is None or node_name is None:
            parent_dir_path = os.path.dirname(norm_path)
            if parent_dir_path and parent_dir_path != norm_path: # Bukan root dan ada parent
                self.mkdir(parent_dir_path, context, make_parents=True) # Coba buat parent
                _, parent, node_name = self._get_node_and_parent(norm_path) # Coba lagi
                if parent is None or node_name is None:
                    raise FileNotFoundError(f"VFS Error: Gagal menemukan/membuat parent untuk menulis file '{norm_path}'.")
            else: # Path aneh atau root (tidak bisa menulis file sebagai root node bernama "/")
                 raise FileNotFoundError(f"VFS Error: Path tidak valid untuk menulis file: '{norm_path}'.")

        if parent and node_name and parent.is_directory and parent.children is not None:
            if node is None: # File baru
                file_node = VFSNode(name=node_name, is_directory=False, content=content_bytes)
                parent.children[node_name] = file_node
            else: # Timpa file yang ada (node adalah file)
                node.content = content_bytes
            logger.info(f"[{self.tempik_id_str}] VFS: File ditulis: {norm_path} ({len(content_bytes)} bytes)")
        else: # Seharusnya tidak sampai sini jika logika di atas benar
            raise FileNotFoundError(f"VFS Error: Kondisi tidak terduga saat mencoba menulis file '{norm_path}'.")

    def read_file(self, path: str, context: 'ExecutionContextManager') -> Optional[bytes]:
        norm_path = self._normalize_path(path, context)
        node, _, _ = self._get_node_and_parent(norm_path)
        
        if node is None:
            logger.warning(f"[{self.tempik_id_str}] VFS: File tidak ditemukan: {norm_path}")
            return None
        if node.is_directory:
            logger.warning(f"[{self.tempik_id_str}] VFS: Path adalah direktori, bukan file: {norm_path}")
            return None
        return node.content

    def file_exists(self, path: str, context: 'ExecutionContextManager') -> bool:
        norm_path = self._normalize_path(path, context)
        node, _, _ = self._get_node_and_parent(norm_path)
        return node is not None and not node.is_directory

    def dir_exists(self, path: str, context: 'ExecutionContextManager') -> bool:
        norm_path = self._normalize_path(path, context)
        node, _, _ = self._get_node_and_parent(norm_path)
        return node is not None and node.is_directory

    def list_dir(self, path: str, context: 'ExecutionContextManager') -> Optional[List[str]]:
        norm_path = self._normalize_path(path, context)
        node, _, _ = self._get_node_and_parent(norm_path)
        if node and node.is_directory and node.children is not None:
            return list(node.children.keys())
        logger.warning(f"[{self.tempik_id_str}] VFS: Gagal list direktori, '{norm_path}' bukan direktori atau tidak ada.")
        return None

    def remove_file(self, path: str, context: 'ExecutionContextManager'):
        norm_path = self._normalize_path(path, context)
        node, parent, node_name = self._get_node_and_parent(norm_path)
        if node is None or node.is_directory:
            raise FileNotFoundError(f"VFS Error: File '{norm_path}' tidak ditemukan atau adalah direktori.")
        if parent and node_name and parent.children: # Pastikan parent.children ada
            del parent.children[node_name]
            logger.info(f"[{self.tempik_id_str}] VFS: File dihapus: {norm_path}")
        else: # Seharusnya tidak terjadi jika node ditemukan
            raise FileNotFoundError(f"VFS Error: Gagal menghapus file '{norm_path}', parent atau node_name tidak valid.")


    def remove_dir(self, path: str, context: 'ExecutionContextManager', recursive: bool = False):
        norm_path = self._normalize_path(path, context)
        if norm_path == "/": raise ValueError("VFS Error: Tidak dapat menghapus direktori root.")

        node, parent, node_name = self._get_node_and_parent(norm_path)
        if node is None or not node.is_directory:
            raise FileNotFoundError(f"VFS Error: Direktori '{norm_path}' tidak ditemukan atau adalah file.")
        if not recursive and node.children and len(node.children) > 0:
            raise OSError(f"VFS Error: Direktori '{norm_path}' tidak kosong.")
        if parent and node_name and parent.children: # Pastikan parent.children ada
            del parent.children[node_name]
            logger.info(f"[{self.tempik_id_str}] VFS: Direktori dihapus: {norm_path}")
        else: # Seharusnya tidak terjadi jika node ditemukan
            raise FileNotFoundError(f"VFS Error: Gagal menghapus direktori '{norm_path}', parent atau node_name tidak valid.")

    def mount_external(self, vfs_mount_point: str, host_source_path: str, options: Dict[str, Any], context: 'ExecutionContextManager'):
        """Menghubungkan path VFS ke sumber eksternal (konseptual untuk sekarang)."""
        # Implementasi mount nyata sangat kompleks dan bergantung pada OS.
        # Untuk sekarang, hanya mencatat dan mungkin membatasi akses ke VFS path ini.
        norm_mount_point = self._normalize_path(vfs_mount_point, context)
        if not self.dir_exists(norm_mount_point, context):
            self.mkdir(norm_mount_point, context, make_parents=True) # Buat mount point jika belum ada
        
        self.mount_points[norm_mount_point] = (host_source_path, options)
        logger.info(f"[{self.tempik_id_str}] VFS: Sumber eksternal '{host_source_path}' di-mount ke VFS:'{norm_mount_point}' dengan opsi {options} (konseptual).")
        # Operasi baca/tulis ke path ini perlu di-intercept dan diarahkan ke host_source_path
        # dengan memperhatikan opsi (misal, readonly). Ini tidak diimplementasikan di VFS dasar ini.


class SecureNetworkUnit: # Menggantikan NetworkUnit
    """
    Unit Jaringan Aman.
    Mengelola semua operasi jaringan keluar (dan masuk jika ada) untuk Tempik.
    Menerapkan kebijakan jaringan dari ExecutionContextManager dan SecurityPolicyModule.
    """
    def __init__(self, tempik_id_str: str, context_manager_ref: 'ExecutionContextManager', security_module_ref: 'SecurityPolicyModule'):
        self.tempik_id_str = tempik_id_str
        self._context = context_manager_ref
        self._security_policy = security_module_ref
        self._session = None # Untuk session HTTP persisten (misal, dengan aiohttp.ClientSession)
        logger.debug(f"[{self.tempik_id_str}] SecureNetworkUnit diinisialisasi.")

    async def _get_http_session(self):
        """Menginisialisasi atau mengembalikan session aiohttp."""
        # Dinamis impor aiohttp untuk menghindari dependency keras jika tidak dipakai
        try:
            import aiohttp
        except ImportError:
            logger.error(f"[{self.tempik_id_str}] Pustaka 'aiohttp' tidak ditemukan. Operasi jaringan HTTP tidak akan berfungsi.")
            return None

        if self._session is None or self._session.closed:
            # TODO: Konfigurasi konektor dengan SSL context yang aman, timeout, dll.
            self.session = aiohttp.ClientSession()
        return self.session

    async def _perform_request(self, method: str, url: str, **kwargs) -> Tuple[int, Union[str, bytes, Dict[str, Any]]]:
        """Melakukan permintaan HTTP dan mengembalikan status code dan body."""
        # 1. Cek Izin Jaringan Global
        networking_mode = self._context.current_networking_mode # Diambil dari header .asu via context
        if not self._security_policy.can_access_network(networking_mode):
            msg = f"Akses jaringan diblokir oleh policy keamanan atau mode '{networking_mode}'."
            logger.error(f"[{self.tempik_id_str}] {msg}")
            raise ConnectionRefusedError(msg)

        # 2. Cek Izin Host (jika mode restricted)
        if networking_mode == "restricted-outbound":
            allowed_hosts = self._context.get_env_var("UTEK_ALLOWED_HOSTS", "").split(',')
            from urllib.parse import urlparse
            parsed_url = urlparse(url)
            if parsed_url.hostname not in allowed_hosts:
                msg = f"Akses ke host '{parsed_url.hostname}' diblokir dalam mode restricted. Diizinkan: {allowed_hosts}"
                logger.error(f"[{self.tempik_id_str}] {msg}")
                raise ConnectionRefusedError(msg)
        
        # 3. Cek Batas Operasi Jaringan
        if not self._context.check_and_increment_resource_usage("network_ops_count", 1):
             msg = "Batas maksimum operasi jaringan telah tercapai."
             logger.error(f"[{self.tempik_id_str}] {msg}")
             raise ConnectionAbortedError(msg) # Atau exception khusus resource limit

        # 4. Lakukan Permintaan
        http_session = await self._get_http_session()
        if not http_session:
            return 503, "Layanan jaringan tidak tersedia (aiohttp tidak ada)."

        try:
            logger.info(f"[{self.tempik_id_str}] NetworkUnit: {method} {url} (Args: {kwargs.get('params') or kwargs.get('json') or kwargs.get('data')})")
            async with http_session.request(method, url, **kwargs) as response:
                status_code = response.status
                # Coba baca sebagai JSON, lalu text, lalu bytes
                try:
                    body = await response.json()
                except Exception:
                    try:
                        body = await response.text()
                    except Exception:
                        body = await response.read()
                logger.info(f"[{self.tempik_id_str}] NetworkUnit: Response {status_code} dari {url}")
                return status_code, body
        except Exception as e:
            logger.error(f"[{self.tempik_id_str}] NetworkUnit: Error saat {method} {url}: {e}", exc_info=True)
            return 500, str(e) # Atau exception spesifik

    async def fetch_repository_content(self, repo_url: str, target_vfs_path: str, vfs: IsolatedVirtualFileSystem, context: 'ExecutionContextManager'):
        """Mengambil konten repositori (simulasi, idealnya via Git client dalam sandbox)."""
        # Untuk implementasi nyata, ini akan menggunakan `git clone --depth 1` ke temporary dir
        # lalu menyalin isinya ke VFS. Ini sangat kompleks dan berisiko keamanan.
        # Simulasi:
        logger.info(f"[{self.tempik_id_str}] FETCH_REPO (simulasi): {repo_url} -> VFS:{target_vfs_path}")
        try:
            vfs.mkdir(target_vfs_path, context, make_parents=True)
            vfs.write_file(os.path.join(target_vfs_path, ".git_placeholder"), f"Simulated clone from {repo_url}", context)
            vfs.write_file(os.path.join(target_vfs_path, "README.simulated"), "# Simulated Repo Content", context)
            return {"status": "success_simulated", "message": f"Konten repo dari {repo_url} disimulasikan ke VFS:{target_vfs_path}"}
        except Exception as e:
            return {"status": "failed", "error": f"Simulasi fetch_repo gagal: {str(e)}"}

    async def invoke_remote_service(self, endpoint_url: str, method: str, headers: Optional[Dict], payload: Optional[Any]):
        """Memanggil layanan HTTP jarak jauh."""
        req_kwargs = {}
        if headers: req_kwargs["headers"] = headers
        if payload:
            if isinstance(payload, (dict, list)): req_kwargs["json"] = payload
            else: req_kwargs["data"] = str(payload) # Kirim sebagai form data atau text
        
        status, body = await self._perform_request(method.upper(), endpoint_url, **req_kwargs)
        return {"status_code": status, "body": body, "url": endpoint_url, "method": method}

    async def push_data_to_remote(self, destination_url: str, data_to_push: Union[str, bytes, Dict], method: str = "POST", headers: Optional[Dict] = None):
        """Mengirim data ke destinasi URL."""
        # Serupa dengan invoke_remote_service, tapi lebih spesifik untuk PUSH_RESULT
        req_kwargs = {}
        if headers: req_kwargs["headers"] = headers
        
        if isinstance(data_to_push, dict): req_kwargs["json"] = data_to_push
        elif isinstance(data_to_push, str): req_kwargs["data"] = data_to_push.encode('utf-8') # Default UTF-8
        elif isinstance(data_to_push, bytes): req_kwargs["data"] = data_to_push
        else: return {"status_code": 400, "body": "Tipe data tidak didukung untuk push."}

        status, body = await self._perform_request(method.upper(), destination_url, **req_kwargs)
        return {"status_code": status, "body": body, "destination_url": destination_url}

    async def close_session(self):
        """Menutup session HTTP jika ada."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
            logger.debug(f"[{self.tempik_id_str}] SecureNetworkUnit session ditutup.")


class CryptographicEngine: # Menggantikan CryptoEngine
    """
    Mesin Kriptografi untuk UTEK Virtual Executor.
    Menangani operasi hashing, signature digital, enkripsi, dan dekripsi.
    """
    def __init__(self, tempik_id_str: str):
        self.tempik_id_str = tempik_id_str
        # Kunci bisa di-generate per Tempik atau di-load dari konfigurasi aman.
        # Untuk contoh, kita generate saat inisialisasi.
        self._default_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
        self._default_public_key = self._default_private_key.public_key()
        logger.debug(f"[{self.tempik_id_str}] CryptographicEngine diinisialisasi dengan kunci default baru.")

    def calculate_hash(self, data: bytes, algorithm: str = "sha256") -> str:
        """Menghitung hash dari data menggunakan algoritma yang ditentukan."""
        alg_lower = algorithm.lower()
        hasher: Any # Untuk type hinting
        if alg_lower == "sha256": hasher = hashlib.sha256()
        elif alg_lower == "sha512": hasher = hashlib.sha512()
        elif alg_lower == "md5": hasher = hashlib.md5() # MD5 tidak aman untuk integritas, hanya untuk contoh
        else: raise ValueError(f"Algoritma hash tidak didukung: {algorithm}")
        hasher.update(data)
        return hasher.hexdigest()

    def verify_data_hash(self, data: bytes, expected_hash: str, algorithm: str = "sha256") -> bool:
        """Memverifikasi apakah hash data cocok dengan hash yang diharapkan."""
        actual_hash = self.calculate_hash(data, algorithm)
        return actual_hash.lower() == expected_hash.lower()

    def generate_digital_signature(self, data: bytes, private_key_pem: Optional[bytes] = None) -> bytes:
        """Membuat signature digital untuk data menggunakan private key."""
        priv_key_to_use = self._default_private_key
        if private_key_pem:
            try:
                # Password bisa None jika key tidak terenkripsi, atau perlu di-supply
                priv_key_to_use = serialization.load_pem_private_key(private_key_pem, password=None, backend=default_backend())
            except Exception as e:
                logger.error(f"[{self.tempik_id_str}] Gagal memuat private key PEM eksternal: {e}")
                raise ValueError(f"Private key PEM tidak valid: {e}") from e
        
        signature = priv_key_to_use.sign(
            data,
            asym_padding.PSS(mgf=asym_padding.MGF1(hashes.SHA256()), salt_length=asym_padding.PSS.MAX_LENGTH),
            hashes.SHA256()
        )
        return signature

    def verify_digital_signature(self, data: bytes, signature: bytes, public_key_pem: Optional[bytes] = None) -> bool:
        """Memverifikasi signature digital data menggunakan public key."""
        pub_key_to_use = self._default_public_key
        if public_key_pem:
            try:
                pub_key_to_use = serialization.load_pem_public_key(public_key_pem, backend=default_backend())
            except Exception as e:
                logger.error(f"[{self.tempik_id_str}] Gagal memuat public key PEM eksternal: {e}")
                return False # Gagal load key berarti verifikasi gagal
        
        try:
            pub_key_to_use.verify(
                signature,
                data,
                asym_padding.PSS(mgf=asym_padding.MGF1(hashes.SHA256()), salt_length=asym_padding.PSS.MAX_LENGTH),
                hashes.SHA256()
            )
            return True
        except Exception: # Misal, cryptography.exceptions.InvalidSignature
            logger.warning(f"[{self.tempik_id_str}] Verifikasi signature gagal.")
            return False

    def encrypt_symmetric(self, plaintext: bytes, key: bytes, associated_data: Optional[bytes] = None) -> bytes:
        """Enkripsi data menggunakan AES-GCM (contoh). Key harus 16, 24, atau 32 bytes."""
        if len(key) not in [16, 24, 32]: raise ValueError("Kunci AES harus 16, 24, atau 32 bytes.")
        nonce = os.urandom(12) # Nonce 96-bit (12 bytes) direkomendasikan untuk GCM
        cipher = Cipher(algorithms.AES(key), modes.GCM(nonce), backend=default_backend())
        encryptor = cipher.encryptor()
        if associated_data:
            encryptor.authenticate_additional_data(associated_data)
        ciphertext = encryptor.update(plaintext) + encryptor.finalize()
        # Prepend nonce ke ciphertext, append tag (GCM tag adalah 16 bytes by default)
        return nonce + ciphertext + encryptor.tag

    def decrypt_symmetric(self, ciphertext_with_nonce_tag: bytes, key: bytes, associated_data: Optional[bytes] = None) -> bytes:
        """Dekripsi data menggunakan AES-GCM (contoh)."""
        if len(key) not in [16, 24, 32]: raise ValueError("Kunci AES harus 16, 24, atau 32 bytes.")
        if len(ciphertext_with_nonce_tag) < 12 + 16: # Minimal nonce + tag
            raise ValueError("Ciphertext tidak valid (terlalu pendek).")

        nonce = ciphertext_with_nonce_tag[:12]
        tag = ciphertext_with_nonce_tag[-16:]
        ciphertext = ciphertext_with_nonce_tag[12:-16]
        
        cipher = Cipher(algorithms.AES(key), modes.GCM(nonce, tag), backend=default_backend())
        decryptor = cipher.decryptor()
        if associated_data:
            decryptor.authenticate_additional_data(associated_data)
        
        try:
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            return plaintext
        except Exception as e: # cryptography.exceptions.InvalidTag
            logger.error(f"[{self.tempik_id_str}] Dekripsi gagal (kemungkinan kunci salah, data korup, atau tag tidak valid): {e}")
            raise ValueError(f"Dekripsi gagal: {e}") from e


class CentralAuditLogger: # Menggantikan AuditLogger
    """
    Logger Audit Terpusat untuk UTEK Virtual Executor.
    Mencatat semua event penting eksekusi sesuai format standar (misal, Deloitte).
    Memastikan log bersifat immutable (konseptual, implementasi nyata perlu append-only storage).
    """
    def __init__(self, log_file_path: Optional[str] = "utek_master_audit.log"):
        self._log_entries_buffer: List[str] = [] # Buffer sementara sebelum ditulis ke file
        self._log_file_path = log_file_path
        self._audit_file_handler: Optional[logging.FileHandler] = None

        # Setup logger khusus untuk audit yang hanya menulis ke file audit
        self._file_audit_logger = logging.getLogger("UTEKFileAuditLogger")
        self._file_audit_logger.propagate = False # Jangan teruskan ke root logger
        self._file_audit_logger.setLevel(logging.INFO)

        if self._log_file_path:
            try:
                # Handler file dengan mode append 'a'
                self._audit_file_handler = logging.FileHandler(self._log_file_path, mode='a', encoding='utf-8')
                # Format Deloitte: timestamp | Tempik_id | instruction | result | duration_ms | file_hash | details
                formatter = logging.Formatter('%(message)s') # Pesan sudah diformat sebelum di-log
                self._audit_file_handler.setFormatter(formatter)
                self._file_audit_logger.addHandler(self._audit_file_handler)
                logger.info(f"CentralAuditLogger akan menulis ke file: {self._log_file_path}")
            except Exception as e:
                logger.error(f"Gagal menginisialisasi file handler untuk CentralAuditLogger di {self._log_file_path}: {e}")
                self._log_file_path = None # Matikan logging ke file jika gagal
        else:
            logger.warning("CentralAuditLogger tidak dikonfigurasi dengan path file, log audit hanya akan di buffer (jika ada) atau stdout.")

    def record_event(self, timestamp_utc_iso: str, tempik_id_str: str, 
                     instruction_name: str, result_status: str, 
                     duration_ms: int, asu_file_hash: str, details: str = ""):
        """Mencatat event eksekusi ke buffer dan/atau file."""
        # Format Deloitte: timestamp | Tempik_id | instruction | result | duration_ms | file_hash | details
        # Pastikan timestamp dalam format ISO 8601 UTC
        log_message = f"{timestamp_utc_iso} | {tempik_id_str} | {instruction_name} | {result_status} | {duration_ms}ms | {asu_file_hash}"
        if details:
            # Bersihkan detail dari karakter pipe untuk menjaga integritas format
            cleaned_details = str(details).replace("|", ";").replace("\n", " ")
            log_message += f" | {cleaned_details}"
        
        # Log ke logger file audit jika terkonfigurasi
        if self._log_file_path and self._audit_file_handler:
            self._file_audit_logger.info(log_message)
        else: # Jika tidak ada file, log ke logger utama sebagai fallback (mungkin berisik)
            logger.info(f"AUDIT_EVENT (no-file): {log_message}")
            self._log_entries_buffer.append(log_message) # Simpan di buffer jika tidak ada file

    def get_buffered_logs(self) -> List[str]:
        """Mengembalikan log yang ada di buffer (jika logging file tidak aktif)."""
        return list(self._log_entries_buffer)

    def flush_buffer(self):
        """Membersihkan buffer (misalnya setelah ditulis ke tujuan lain)."""
        self._log_entries_buffer.clear()

    def close_log_file(self):
        """Menutup file log audit jika terbuka."""
        if self._audit_file_handler:
            try:
                self._audit_file_handler.close()
                self._file_audit_logger.removeHandler(self._audit_file_handler)
                logger.info(f"File audit log {self._log_file_path} telah ditutup.")
            except Exception as e:
                logger.error(f"Error saat menutup file audit log {self._log_file_path}: {e}")


class InstructionObjectDecoder: # Menggantikan InstructionDecoder
    """
    Dekoder Objek Instruksi.
    Bertugas mem-parsing data instruksi mentah (dari body .asu) menjadi objek
    InstruksiEksekusi yang terstruktur dan tervalidasi.
    """
    def __init__(self, tempik_id_str: Optional[str] = None): # tempik_id opsional, untuk logging jika perlu
        self.tempik_id_str_prefix = f"[{tempik_id_str}] " if tempik_id_str else ""
        logger.debug(f"{self.tempik_id_str_prefix}InstructionObjectDecoder diinisialisasi.")

    def decode_from_dict(self, raw_instr_dict: Dict[str, Any]) -> InstruksiEksekusi:
        """Mendekode satu instruksi dari format dictionary."""
        instr_value = raw_instr_dict.get("instruksi")
        if not instr_value:
            raise ValueError("Data instruksi mentah tidak memiliki field 'instruksi'.")
        
        try:
            instr_enum = InstruksiASU(instr_value)
        except ValueError:
            logger.error(f"{self.tempik_id_str_prefix}Instruksi tidak dikenal dalam ISA: '{instr_value}'")
            raise ValueError(f"Instruksi tidak dikenal: {instr_value}")
        
        # Validasi parameter dasar (bisa diperluas per instruksi)
        params = raw_instr_dict.get("parameter", {})
        if not isinstance(params, dict):
            logger.warning(f"{self.tempik_id_str_prefix}Parameter untuk instruksi '{instr_enum.value}' bukan dictionary, menggunakan empty dict.")
            params = {}

        return InstruksiEksekusi(
            instruksi=instr_enum,
            parameter=params,
            label=raw_instr_dict.get("label"), # Bisa None
            timeout_seconds=float(raw_instr_dict.get("timeout_seconds", 30.0)),
            retry_attempts=int(raw_instr_dict.get("retry_attempts", 0))
        )


class ExecutionContextCoreManager: # Menggantikan ExecutionContextManager
    """
    Manajer Inti Konteks Eksekusi.
    Menyimpan dan mengelola seluruh state runtime yang relevan untuk eksekusi
    satu file .asu oleh sebuah Tempik. Termasuk variabel lingkungan,
    direktori kerja saat ini (dalam VFS), informasi pengguna/role, dan batasan sumber daya.
    """
    def __init__(self, tempik_id_str: str, initial_header: Optional[HeaderASU] = None):
        self.tempik_id_str = tempik_id_str
        self.environment_vars: Dict[str, str] = os.environ.copy() # Mulai dengan env host, bisa di-override
        self.current_working_directory: str = "/" # Path absolut dalam IsolatedVirtualFileSystem
        
        # Informasi dari header .asu
        self.current_user: str = "utek_default_user"
        self.current_namespace: str = "utek_default_namespace"
        self.current_roles: List[str] = ["guest"]
        self.current_security_flags: List[str] = ["sandboxed"] # Default, akan di-override
        self.current_networking_mode: str = "offline" # Default, akan di-override

        # Batasan sumber daya (default, bisa di-override oleh header atau policy)
        self.resource_limits: Dict[str, Any] = {
            "max_memory_mb": 256,
            "max_cpu_time_seconds_total": 300, # Total waktu CPU untuk seluruh .asu
            "max_instruction_timeout_seconds": 60, # Timeout default per instruksi
            "max_vfs_storage_mb": 512,
            "max_network_operations": 100,
            "max_subprocess_count": 5,
        }
        self.resource_usage: Dict[str, Any] = {
            "network_operations_count": 0,
            "subprocess_spawned_count": 0,
            "vfs_current_size_bytes": 0, # Perlu diupdate oleh VFS
            "cpu_time_elapsed_seconds": 0.0 # Perlu diupdate oleh Tempik/Pipeline
        }
        
        if initial_header:
            self.apply_header_configurations(initial_header)
        
        logger.debug(f"[{self.tempik_id_str}] ExecutionContextCoreManager diinisialisasi. CWD VFS: {self.current_working_directory}")

    def apply_header_configurations(self, header: HeaderASU):
        """Menerapkan konfigurasi dari HeaderASU ke konteks."""
        self.current_security_flags = list(header.security_flags) # Salin list
        self.current_networking_mode = header.networking_mode.lower()
        
        # Parse memory_profile
        try:
            mem_val_str = "".join(filter(str.isdigit, header.memory_profile))
            if mem_val_str:
                mem_val = int(mem_val_str)
                if "gib" in header.memory_profile.lower(): mem_val *= 1024
                self.resource_limits["max_memory_mb"] = mem_val
        except ValueError: logger.warning(f"Gagal parse memory_profile: {header.memory_profile}")

        # Parse time_budget (bisa lebih kompleks, misal "total=X;instr=Y")
        try:
            parts = header.time_budget.split(';')
            for part in parts:
                if "max-total-exec-time=" in part:
                    self.resource_limits["max_cpu_time_seconds_total"] = int(part.split('=')[1].replace('s',''))
                elif "max-instruction-time=" in part:
                    self.resource_limits["max_instruction_timeout_seconds"] = int(part.split('=')[1].replace('s',''))
        except ValueError: logger.warning(f"Gagal parse time_budget: {header.time_budget}")
        
        # Set env vars untuk mode jaringan agar bisa diakses instruksi atau NetworkUnit
        self.set_environment_variable("UTEK_NETWORKING_MODE", self.current_networking_mode)
        # Jika ada allowed_hosts dari policy, bisa juga di-set di sini.

        logger.info(f"[{self.tempik_id_str}] Konteks diinisialisasi/diperbarui dari HeaderASU. Net mode: {self.current_networking_mode}, Mem: {self.resource_limits['max_memory_mb']}MB, Time Total: {self.resource_limits['max_cpu_time_seconds_total']}s")

    def set_environment_variable(self, key: str, value: str):
        """Menetapkan variabel lingkungan dalam konteks eksekusi ini."""
        # Validasi nama key (hindari karakter aneh)
        if not key.isalnum() and "_" not in key: # Izinkan alphanumeric dan underscore
            logger.warning(f"[{self.tempik_id_str}] Nama variabel lingkungan tidak valid: {key}. Tidak di-set.")
            return
        self.environment_vars[key.upper()] = str(value) # Simpan sebagai uppercase (konvensi)
        logger.debug(f"[{self.tempik_id_str}] ENV VAR SET: {key.upper()}='{str(value)}'")

    def get_environment_variable(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Mengambil variabel lingkungan dari konteks ini."""
        return self.environment_vars.get(key.upper(), default)

    def set_current_working_directory(self, vfs_path: str, vfs_ref: IsolatedVirtualFileSystem):
        """Menetapkan direktori kerja saat ini di dalam VFS, setelah validasi."""
        # Path harus absolut dan sudah dinormalisasi oleh VFS
        if not vfs_path.startswith("/"):
            logger.error(f"[{self.tempik_id_str}] CWD harus path VFS absolut: {vfs_path}")
            raise ValueError("CWD harus path VFS absolut.")

        if vfs_ref.dir_exists(vfs_path, self): # VFS perlu konteks untuk normalisasi path relatif jika ada
            self.current_working_directory = vfs_path
            logger.info(f"[{self.tempik_id_str}] CWD VFS diubah ke: {self.current_working_directory}")
        else:
            logger.error(f"[{self.tempik_id_str}] Gagal mengubah CWD VFS: Direktori '{vfs_path}' tidak ditemukan.")
            raise FileNotFoundError(f"Direktori VFS '{vfs_path}' tidak ditemukan.")

    def check_and_increment_resource_usage(self, resource_key: str, increment_amount: int = 1) -> bool:
        """Memeriksa apakah penggunaan sumber daya akan melebihi batas, lalu menginkrement jika aman."""
        # resource_key harus ada di self.resource_usage dan self.resource_limits
        limit_key_map = { # Peta dari usage key ke limit key jika namanya beda
            "network_operations_count": "max_network_operations",
            "subprocess_spawned_count": "max_subprocess_count",
            # Tambahkan pemetaan lain jika perlu
        }
        limit_name = limit_key_map.get(resource_key, resource_key) # Defaultnya nama sama

        current_val = self.resource_usage.get(resource_key, 0)
        max_val = self.resource_limits.get(limit_name)

        if max_val is None: # Tidak ada batasan untuk resource ini
            self.resource_usage[resource_key] = current_val + increment_amount
            return True 
        
        if current_val + increment_amount > max_val:
            logger.warning(f"[{self.tempik_id_str}] Batas sumber daya '{limit_name}' (maks: {max_val}) akan terlampaui oleh penggunaan {current_val + increment_amount}. Operasi ditolak.")
            return False
        
        self.resource_usage[resource_key] = current_val + increment_amount
        logger.debug(f"[{self.tempik_id_str}] Penggunaan sumber daya '{resource_key}' menjadi {self.resource_usage[resource_key]} (batas: {max_val}).")
        return True


# --- Kelas Tempik dan Pipeline (Inti Eksekusi) ---
# Direstrukturisasi untuk alur kerja yang lebih jelas dan modular

class TempikInstructionPipeline:
    """
    Pipeline Pemrosesan Instruksi untuk satu Tempik.
    Mengelola siklus 5 tahap: Fetch, Decode, Execute, Memory Access, Write Back.
    """
    def __init__(self, tempik_ref: 'Tempik', asu_program_body: List[InstruksiEksekusi]):
        self._tempik = tempik_ref # Referensi ke Tempik induk
        self._program = asu_program_body
        self._current_pipeline_stage: Optional[PipelineStage] = None
        
        # State antar tahap pipeline
        self._fetched_instr_obj: Optional[InstruksiEksekusi] = None
        self._decoded_instr_obj: Optional[InstruksiEksekusi] = None # Hasil dari InstructionObjectDecoder
        self._execution_output: Any = None # Hasil dari handler instruksi
        self._memory_access_output: Any = None # Hasil dari operasi Memory/VFS
        
        self._pc_override_next_cycle: Optional[int] = None # Untuk JUMP, CALL, IF/ELSE skip
        logger.debug(f"[{self._tempik.tempik_id_str}] TempikInstructionPipeline diinisialisasi.")

    async def _stage_fetch_instruction(self) -> bool:
        """Tahap 1: Mengambil instruksi berikutnya dari program berdasarkan PC."""
        self._current_pipeline_stage = PipelineStage.FETCH_INSTRUCTION
        self._tempik.current_status = TempikStatus.FETCHING
        self._tempik.control_signal_unit.issue_fetch_signal(self._tempik.registers.pc)

        if self._pc_override_next_cycle is not None:
            target_pc = self._pc_override_next_cycle
            if 0 <= target_pc < len(self._program):
                self._tempik.program_counter.jump_to(target_pc)
                logger.debug(f"[{self._tempik.tempik_id_str}] Pipeline Fetch: PC di-override ke {target_pc}.")
            else:
                logger.warning(f"[{self._tempik.tempik_id_str}] Pipeline Fetch: Override PC ke {target_pc} di luar batas program. Mengarah ke EOF.")
                self._tempik.program_counter.jump_to(len(self._program)) # EOF
            self._pc_override_next_cycle = None # Reset setelah digunakan

        current_pc = self._tempik.program_counter.current_address
        if current_pc >= len(self._program):
            logger.info(f"[{self._tempik.tempik_id_str}] Pipeline Fetch: Akhir program tercapai di PC={current_pc}.")
            self._fetched_instr_obj = None
            return False # Akhir program

        # Coba ambil dari cache instruksi
        cached = self._tempik.instruction_cache_mgr.get_instruction(current_pc)
        if cached:
            self._fetched_instr_obj = cached
        else:
            self._fetched_instr_obj = self._program[current_pc]
            self._tempik.instruction_cache_mgr.store_instruction(current_pc, self._fetched_instr_obj)
        
        logger.debug(f"[{self._tempik.tempik_id_str}] Pipeline Fetch: Diambil PC={current_pc}, Instr: {self._fetched_instr_obj.instruksi.value}")
        self._tempik.program_counter.advance() # Maju ke instruksi berikutnya secara default
        return True # Instruksi berhasil diambil

    async def _stage_decode_instruction(self) -> bool:
        """Tahap 2: Mendekode instruksi yang sudah di-fetch."""
        if not self._fetched_instr_obj: return False # Tidak ada instruksi untuk didekode
        self._current_pipeline_stage = PipelineStage.DECODE_INSTRUCTION
        self._tempik.current_status = TempikStatus.DECODING
        self._tempik.control_signal_unit.issue_decode_signal(self._fetched_instr_obj.instruksi.value)

        try:
            # Gunakan InstructionObjectDecoder untuk validasi dan pembuatan objek
            self._decoded_instr_obj = self._tempik.instruction_decoder.decode_from_dict(self._fetched_instr_obj.to_dict())
            logger.debug(f"[{self._tempik.tempik_id_str}] Pipeline Decode: Instruksi '{self._decoded_instr_obj.instruksi.value}' berhasil didekode.")
            return True
        except ValueError as e:
            logger.error(f"[{self._tempik.tempik_id_str}] Pipeline Decode: Gagal mendekode instruksi. Error: {e}")
            self._tempik.current_status = TempikStatus.FAILED # Error decode adalah fatal
            # Catat ke audit log
            self._tempik.audit_logger.record_event(datetime.now(timezone.utc).isoformat(), self._tempik.tempik_id_str, "DECODE_ERROR", "FAILED", 0, self._tempik.current_asu_file_hash, str(e))
            return False

    async def _stage_execute_operation(self) -> bool:
        """Tahap 3: Mengeksekusi operasi dari instruksi yang sudah didekode."""
        if not self._decoded_instr_obj: return False
        self._current_pipeline_stage = PipelineStage.EXECUTE_OPERATION
        self._tempik.current_status = TempikStatus.EXECUTING
        
        instr = self._decoded_instr_obj
        self._tempik.control_signal_unit.issue_execute_dispatch_signal(instr.instruksi.value)
        logger.info(f"[{self._tempik.tempik_id_str}] Pipeline Execute: Memulai '{instr.instruksi.value}' dengan params: {instr.parameter}")

        # Penanganan skip untuk blok ELSE
        if instr.instruksi == InstruksiASU.ELSE and self._tempik.registers.get_flag("COND"):
            logger.debug(f"[{self.tempik.tempik_id_str}] Pipeline Execute: Skip blok ELSE karena flag COND (hasil IF sebelumnya) adalah True.")
            self._pc_override_next_cycle = self._tempik.find_matching_control_label(self._tempik.program_counter.current_address -1 , [InstruksiASU.ENDIF], skip_current_block=True)
            self._execution_output = {"status": "skipped", "reason": "IF condition was true"}
            return True # Operasi skip dianggap "sukses" untuk pipeline lanjut

        # Penanganan skip untuk instruksi dalam blok IF yang False (lebih kompleks)
        # Jika kita berada dalam blok IF yang kondisinya False, semua instruksi hingga ELSE atau ENDIF harus di-skip.
        # Ini memerlukan state tambahan di Tempik atau Pipeline untuk melacak "apakah saat ini sedang skipping".
        # Untuk V3, kita sederhanakan: instruksi IF akan mengatur flag COND, dan jika False,
        # ia juga akan mencoba set _pc_override_next_cycle ke ELSE atau ENDIF.

        handler = self._tempik.get_instruction_handler(instr.instruksi)
        if not handler:
            err_msg = f"Tidak ada handler yang terdaftar untuk instruksi: {instr.instruksi.value}"
            logger.error(f"[{self._tempik.tempik_id_str}] Pipeline Execute: {err_msg}")
            self._execution_output = {"status": "failed", "error": err_msg}
            self._tempik.current_status = TempikStatus.FAILED
            self._tempik.audit_logger.record_event(datetime.now(timezone.utc).isoformat(), self._tempik.tempik_id_str, instr.instruksi.value, "HANDLER_NOT_FOUND", 0, self._tempik.current_asu_file_hash, err_msg)
            return False # Gagal eksekusi

        start_time_mono = time.monotonic()
        try:
            # Timeout per instruksi dari InstruksiEksekusi atau default dari ExecutionContext
            instr_timeout = instr.timeout_seconds
            max_instr_timeout_from_context = self._tempik.context_manager.resource_limits.get("max_instruction_timeout_seconds", 60)
            actual_timeout = min(instr_timeout, max_instr_timeout_from_context)

            self._execution_output = await asyncio.wait_for(handler(instr.parameter), timeout=actual_timeout)
            
            # Jika handler mengembalikan None (misal untuk instruksi tanpa output eksplisit), set status sukses
            if self._execution_output is None: self._execution_output = {"status": "success"}
            # Pastikan ada status di output
            if isinstance(self._execution_output, dict) and "status" not in self._execution_output:
                self._execution_output["status"] = "success" # Default status sukses jika tidak ada

            duration_ms = int((time.monotonic() - start_time_mono) * 1000)
            
            # Logika untuk JUMP, CALL, dan IF yang mempengaruhi PC
            if instr.instruksi == InstruksiASU.JUMP and isinstance(self._execution_output, dict) and self._execution_output.get("status") == "success":
                self._pc_override_next_cycle = self._execution_output.get("target_pc_absolute")
            elif instr.instruksi == InstruksiASU.CALL and isinstance(self._execution_output, dict) and self._execution_output.get("status") == "success":
                self._pc_override_next_cycle = self._execution_output.get("target_pc_absolute")
            elif instr.instruksi == InstruksiASU.RET and isinstance(self._execution_output, dict) and self._execution_output.get("status") == "success":
                self._pc_override_next_cycle = self._execution_output.get("return_to_pc_absolute")
            elif instr.instruksi == InstruksiASU.IF and isinstance(self._execution_output, dict):
                condition_was_true = self._execution_output.get("condition_result", False)
                self._tempik.registers.set_flag("COND", condition_was_true)
                if not condition_was_true: # Jika IF False, cari ELSE atau ENDIF berikutnya
                    self._pc_override_next_cycle = self._tempik.find_matching_control_label(
                        self._tempik.program_counter.current_address - 1, # PC dari IF
                        [InstruksiASU.ELSE, InstruksiASU.ENDIF],
                        skip_current_block=False # Kita ingin targetnya, bukan setelahnya
                    )
            
            # Audit log untuk SUCCESS
            self._tempik.audit_logger.record_event(
                datetime.now(timezone.utc).isoformat(), self._tempik.tempik_id_str, instr.instruksi.value,
                "SUCCESS", duration_ms, self._tempik.current_asu_file_hash,
                json.dumps(self._execution_output, default=str, ensure_ascii=False) if isinstance(self._execution_output, dict) else str(self._execution_output)
            )
            return True

        except asyncio.TimeoutError:
            duration_ms = int(actual_timeout * 1000)
            err_msg = f"Eksekusi instruksi '{instr.instruksi.value}' timeout setelah {actual_timeout:.2f} detik."
            logger.error(f"[{self._tempik.tempik_id_str}] Pipeline Execute: {err_msg}")
            self._execution_output = {"status": "timeout", "error": err_msg}
            # await self._tempik.interrupt_handler.signal_interrupt("instruction_timeout", {"instruction": instr.instruksi.value, "timeout_seconds": actual_timeout})
            self._tempik.current_status = TempikStatus.FAILED # Timeout dianggap FAILED
            self._tempik.audit_logger.record_event(datetime.now(timezone.utc).isoformat(), self._tempik.tempik_id_str, instr.instruksi.value, "TIMEOUT", duration_ms, self._tempik.current_asu_file_hash, err_msg)
            return False # Gagal karena timeout
        
        except AssertionError as ae: # Khusus untuk instruksi ASSERT
            duration_ms = int((time.monotonic() - start_time_mono) * 1000)
            err_msg = f"AssertionError pada instruksi '{instr.instruksi.value}': {ae}"
            logger.error(f"[{self._tempik.tempik_id_str}] Pipeline Execute: {err_msg}")
            self._execution_output = {"status": "assertion_failed", "error": str(ae)}
            self._tempik.current_status = TempikStatus.FAILED
            self._tempik.audit_logger.record_event(datetime.now(timezone.utc).isoformat(), self._tempik.tempik_id_str, instr.instruksi.value, "ASSERTION_FAILED", duration_ms, self._tempik.current_asu_file_hash, str(ae))
            return False

        except Exception as e: # Error lain dari handler
            duration_ms = int((time.monotonic() - start_time_mono) * 1000)
            err_msg = f"Error saat eksekusi instruksi '{instr.instruksi.value}': {e}"
            logger.error(f"[{self._tempik.tempik_id_str}] Pipeline Execute: {err_msg}", exc_info=True)
            self._execution_output = {"status": "failed", "error": str(e)}
            # await self._tempik.interrupt_handler.signal_interrupt("execution_error", {"instruction": instr.instruksi.value, "error": str(e)})
            self._tempik.current_status = TempikStatus.FAILED
            self._tempik.audit_logger.record_event(datetime.now(timezone.utc).isoformat(), self._tempik.tempik_id_str, instr.instruksi.value, "FAILED", duration_ms, self._tempik.current_asu_file_hash, str(e))
            return False # Gagal karena error

    async def _stage_access_memory_or_vfs(self) -> bool:
        """Tahap 4: Melakukan operasi akses memori (stack) atau VFS jika diperlukan oleh instruksi."""
        if not self._decoded_instr_obj: return False
        # Jika tahap EXECUTE gagal, mungkin tidak perlu lanjut ke sini kecuali untuk cleanup
        if isinstance(self._execution_output, dict) and self._execution_output.get("status") not in ["success", "success_simulated", "skipped"]:
             logger.debug(f"[{self._tempik.tempik_id_str}] Pipeline Memory: Dilewati karena status eksekusi sebelumnya adalah '{self._execution_output.get('status')}'.")
             self._memory_access_output = self._execution_output # Teruskan hasil error/timeout
             return True # Anggap "sukses" untuk pipeline lanjut, status FAILED sudah di-set

        self._current_pipeline_stage = PipelineStage.ACCESS_MEMORY_OR_VFS
        self._tempik.current_status = TempikStatus.MEMORY_ACCESS
        
        # Kebanyakan operasi VFS (read/write file) sudah dilakukan di handler instruksi pada tahap EXECUTE.
        # Tahap ini bisa digunakan untuk:
        # 1. Operasi stack implisit (misal, setelah CALL menyimpan return address).
        # 2. Commit transaksi VFS jika VFS mendukung transaksi.
        # 3. Akses DataCacheManager jika ada data yang perlu di-cache/retrieve pasca-eksekusi.
        
        logger.debug(f"[{self._tempik.tempik_id_str}] Pipeline Memory: Tahap akses memori/VFS (umumnya NOP jika operasi sudah di EXECUTE).")
        self._memory_access_output = self._execution_output # Teruskan hasil dari tahap eksekusi
        return True

    async def _stage_write_back_result(self) -> bool:
        """Tahap 5: Menulis kembali hasil operasi ke register atau state Tempik lainnya."""
        if not self._decoded_instr_obj: return False
        if isinstance(self._memory_access_output, dict) and self._memory_access_output.get("status") not in ["success", "success_simulated", "skipped"]:
             logger.debug(f"[{self._tempik.tempik_id_str}] Pipeline WriteBack: Dilewati karena status sebelumnya adalah '{self._memory_access_output.get('status')}'.")
             return True

        self._current_pipeline_stage = PipelineStage.WRITE_BACK_RESULT
        self._tempik.current_status = TempikStatus.WRITING_BACK
        
        # Contoh: Jika instruksi EXECUTE menghasilkan output yang perlu disimpan ke GPR
        # output_reg_target = self._decoded_instr_obj.parameter.get("output_gpr")
        # if output_reg_target and isinstance(self._memory_access_output, dict):
        #     value_to_write = self._memory_access_output.get("stdout", self._memory_access_output.get("result"))
        #     if value_to_write is not None:
        #         self._tempik.registers.set_gpr(output_reg_target, value_to_write)
        
        logger.debug(f"[{self._tempik.tempik_id_str}] Pipeline WriteBack: Tahap penulisan hasil (jika ada).")
        # Hasil akhir dari siklus ini adalah self._memory_access_output
        return True

    async def run_single_cycle(self) -> Tuple[bool, Any]:
        """Menjalankan satu siklus pipeline lengkap dan mengembalikan status serta hasilnya."""
        self._tempik.context_manager.resource_usage["cpu_time_elapsed_seconds"] += (time.monotonic() - getattr(self._tempik, '_cycle_start_time_mono', time.monotonic()))
        setattr(self._tempik, '_cycle_start_time_mono', time.monotonic())


        if not await self._stage_fetch_instruction(): # Tahap Fetch gagal (EOF)
            self._tempik.current_status = TempikStatus.COMPLETED
            return False, None # Akhir program, hentikan eksekusi Tempik

        if not await self._stage_decode_instruction(): # Tahap Decode gagal
            # Status FAILED sudah di-set di dalam stage
            return False, self._execution_output # Kembalikan info error jika ada

        if not await self._stage_execute_operation(): # Tahap Execute gagal
            # Status FAILED sudah di-set
            return False, self._execution_output

        # Jika instruksi HALT atau SHUTDOWN dieksekusi dan berhasil
        if self._decoded_instr_obj and self._decoded_instr_obj.instruksi in [InstruksiASU.HALT, InstruksiASU.SHUTDOWN]:
            if isinstance(self._execution_output, dict) and self._execution_output.get("status") in ["halt_requested", "shutdown_requested"]:
                self._tempik.current_status = TempikStatus.HALTED # Tempik berhenti
                logger.info(f"[{self._tempik.tempik_id_str}] Siklus dihentikan karena {self._decoded_instr_obj.instruksi.value}.")
                return False, self._execution_output # Hentikan eksekusi Tempik

        if not await self._stage_access_memory_or_vfs(): # Tahap Memory gagal (jarang terjadi jika EXECUTE sukses)
            return False, self._memory_access_output
        
        if not await self._stage_write_back_result(): # Tahap WriteBack gagal (jarang terjadi)
            return False, self._memory_access_output

        # Jika semua tahap berhasil, Tempik kembali ke IDLE (atau status lain jika instruksi WAIT)
        if self._tempik.current_status not in [TempikStatus.WAITING, TempikStatus.HALTED, TempikStatus.FAILED, TempikStatus.COMPLETED]:
            self._tempik.current_status = TempikStatus.IDLE
        
        return True, self._memory_access_output # Kembalikan True untuk lanjut, dan hasil akhir siklus


class TempikUnit: # Menggantikan Tempik
    """
    Unit Eksekusi Tempik.
    Merepresentasikan satu inti pemrosesan virtual dalam UTEK 963-Tempik Executor.
    Setiap Tempik memiliki komponen modular sendiri dan menjalankan instruksi .asu
    melalui pipeline internal.
    """
    def __init__(self, tempik_id: int, central_audit_logger: CentralAuditLogger, 
                 utek_executor_ref: 'UTEKVirtualExecutor', global_config: Optional[Dict] = None):
        self.tempik_id = tempik_id
        self.tempik_id_str = f"TempikUnit-{tempik_id:03d}"
        self.utek_executor_ref = utek_executor_ref # Untuk DELEGATE_TO dan info global
        self.current_status: TempikStatus = TempikStatus.IDLE
        self.current_asu_file_hash: str = "N/A" # Diisi saat program dimuat
        
        # Inisialisasi Komponen Modular Utama (sesuai daftar audit)
        self.registers = RegisterStorage()
        self.program_counter = ProgramCounterManager(self.registers)
        self.control_signal_unit = ControlSignalUnit(self.tempik_id_str) # Konseptual
        self.exec_logic_unit = ArithmeticLogicExecutionUnit(self.registers) # Dulu ALU
        self.runtime_data_storage = RuntimeDataStorage(self.registers) # Dulu MemoryUnit (stack)
        self.instruction_cache_mgr = InstructionCacheManager()
        self.data_cache_mgr = DataCacheManager() # Untuk data VFS kecil

        self.context_manager = ExecutionContextCoreManager(self.tempik_id_str)
        self.io_handler = InputOutputOperationHandler(self.tempik_id_str, central_audit_logger)
        self.vfs = IsolatedVirtualFileSystem(self.tempik_id_str) # VFS terisolasi
        
        self.security_policy_module = SecurityPolicyModule(self.tempik_id_str, []) # Flags diisi dari header
        self.network_unit = SecureNetworkUnit(self.tempik_id_str, self.context_manager, self.security_policy_module)
        self.crypto_engine = CryptographicEngine(self.tempik_id_str)
        
        self.audit_logger = central_audit_logger # Referensi ke logger audit terpusat
        self.instruction_decoder = InstructionObjectDecoder(self.tempik_id_str)
        
        self.interrupt_handler = InterruptHandlingController(self) # Beri referensi Tempik ke controller
        # Daftarkan handler interupsi dasar
        # await self.interrupt_handler.register_interrupt_handler("instruction_timeout", self._handle_timeout_interrupt)

        self._pipeline: Optional[TempikInstructionPipeline] = None
        self._program_body: List[InstruksiEksekusi] = []
        self._label_to_pc_map: Dict[str, int] = {} # Peta label ke alamat PC (indeks)

        self._instruction_handler_map: Dict[InstruksiASU, Callable[[Dict[str,Any]], Coroutine[Any, Any, Dict[str,Any]]]] = self._initialize_instruction_handlers()
        logger.info(f"{self.tempik_id_str} (Arsitektur Audit V3) diinisialisasi.")

    def _initialize_instruction_handlers(self) -> Dict[InstruksiASU, Callable[[Dict[str,Any]], Coroutine[Any, Any, Dict[str,Any]]]]:
        """Memetakan Enum InstruksiASU ke metode handler asinkron yang sesuai."""
        # Ini adalah pemetaan inti dari ISA ke implementasi fungsionalnya.
        return {
            InstruksiASU.INIT_ENV: self._instr_handler_init_env,
            InstruksiASU.SET_ENV: self._instr_handler_set_env,
            InstruksiASU.LOG: self._instr_handler_log,
            InstruksiASU.EXECUTE: self._instr_handler_execute,
            InstruksiASU.FETCH_REPO: self._instr_handler_fetch_repo,
            InstruksiASU.CHECKOUT: self._instr_handler_checkout,
            InstruksiASU.INSTALL: self._instr_handler_install,
            InstruksiASU.UNPACK: self._instr_handler_unpack,
            InstruksiASU.INJECT: self._instr_handler_inject,
            InstruksiASU.CLEANUP: self._instr_handler_cleanup,
            InstruksiASU.ASSERT: self._instr_handler_assert,
            InstruksiASU.IF: self._instr_handler_if,
            InstruksiASU.ELSE: self._instr_handler_else, # Handler ELSE mungkin hanya NOP
            InstruksiASU.ENDIF: self._instr_handler_endif, # Handler ENDIF mungkin hanya NOP
            InstruksiASU.JUMP: self._instr_handler_jump,
            InstruksiASU.CALL: self._instr_handler_call,
            InstruksiASU.RET: self._instr_handler_ret,
            InstruksiASU.HALT: self._instr_handler_halt,
            InstruksiASU.SHUTDOWN: self._instr_handler_shutdown,
            InstruksiASU.WAIT: self._instr_handler_wait,
            InstruksiASU.VERIFY_HASH: self._instr_handler_verify_hash,
            InstruksiASU.SIGN: self._instr_handler_sign,
            InstruksiASU.VERIFY: self._instr_handler_verify,
            InstruksiASU.ENCRYPT: self._instr_handler_encrypt, # Tambahan dari audit (CryptoEngine)
            InstruksiASU.DECRYPT: self._instr_handler_decrypt,
            InstruksiASU.LOCK_EXEC: self._instr_handler_lock_exec,
            InstruksiASU.AUDIT_LOG: self._instr_handler_audit_log,
            InstruksiASU.EMIT_EVENT: self._instr_handler_emit_event,
            InstruksiASU.NETWORK_UP: self._instr_handler_network_up,
            InstruksiASU.MAP_PORT: self._instr_handler_map_port,
            InstruksiASU.INVOKE_REMOTE: self._instr_handler_invoke_remote,
            InstruksiASU.PUSH_RESULT: self._instr_handler_push_result,
            InstruksiASU.EXPORT: self._instr_handler_export,
            InstruksiASU.DELEGATE_TO: self._instr_handler_delegate_to,
            InstruksiASU.SET_CONTEXT: self._instr_handler_set_context,
            InstruksiASU.AUTH: self._instr_handler_auth,
            InstruksiASU.SYNC_CLOCK: self._instr_handler_sync_clock,
            InstruksiASU.MOUNT: self._instr_handler_mount,
            InstruksiASU.COMPILE: self._instr_handler_compile,
            InstruksiASU.SPAWN_THREAD: self._instr_handler_spawn_thread, # Konseptual
            InstruksiASU.NOP: self._instr_handler_nop,
        }

    def get_instruction_handler(self, instruksi_enum: InstruksiASU) -> Optional[Callable[[Dict[str,Any]], Coroutine[Any, Any, Dict[str,Any]]]]:
        """Mengembalikan handler asinkron untuk enum instruksi yang diberikan."""
        return self._instruction_handler_map.get(instruksi_enum)

    def _pre_run_setup(self, asu_file_content: FileASU, inherited_context_params: Optional[Dict] = None):
        """Setup internal Tempik sebelum memulai eksekusi pipeline."""
        self.current_status = TempikStatus.INITIALIZING
        self.current_asu_file_hash = asu_file_content.content_hash_sha256
        
        # Reset state internal Tempik untuk eksekusi baru
        self.registers = RegisterStorage() # Register bersih
        self.program_counter = ProgramCounterManager(self.registers) # PC baru
        self.runtime_data_storage = RuntimeDataStorage(self.registers) # Stack bersih
        self.vfs = IsolatedVirtualFileSystem(self.tempik_id_str) # VFS bersih
        
        # Inisialisasi ulang konteks, terapkan dari header, lalu dari warisan jika ada
        self.context_manager = ExecutionContextCoreManager(self.tempik_id_str, initial_header=asu_file_content.header)
        if inherited_context_params: # Misal dari DELEGATE_TO
            # Terapkan parameter warisan dengan hati-hati
            # self.context_manager.apply_inherited_parameters(inherited_context_params)
            logger.info(f"[{self.tempik_id_str}] Konteks warisan diterapkan (placeholder): {inherited_context_params}")

        self.security_policy_module.update_flags(self.context_manager.current_security_flags)
        
        self._program_body = list(asu_file_content.body) # Salin program body
        self._build_label_map() # Buat peta label untuk JUMP/CALL
        self._pipeline = TempikInstructionPipeline(self, self._program_body)
        
        logger.info(f"[{self.tempik_id_str}] Pre-run setup selesai. Siap menjalankan {self.current_asu_file_hash}.")

    def _build_label_map(self):
        """Membuat peta dari label instruksi ke alamat PC (indeks dalam _program_body)."""
        self._label_to_pc_map.clear()
        for idx, instr_obj in enumerate(self._program_body):
            if instr_obj.label:
                # Validasi nama label (misal, alphanumeric, underscore)
                safe_label = instr_obj.label.strip()
                if not safe_label: continue

                if safe_label in self._label_to_pc_map:
                    logger.warning(f"[{self.tempik_id_str}] Label duplikat '{safe_label}' di PC={idx} (sebelumnya di PC={self._label_to_pc_map[safe_label]}). Menggunakan yang pertama.")
                else:
                    self._label_to_pc_map[safe_label] = idx
        logger.debug(f"[{self.tempik_id_str}] Peta label program dibangun: {len(self._label_to_pc_map)} label ditemukan.")

    async def execute_program(self, asu_file_obj: FileASU, inherited_ctx_params: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        Metode utama untuk menjalankan seluruh program .asu yang sudah dimuat.
        Mengelola siklus pipeline hingga program selesai, gagal, atau dihentikan.
        """
        self._pre_run_setup(asu_file_obj, inherited_ctx_params)
        if not self._pipeline or not self._program_body:
            logger.error(f"[{self.tempik_id_str}] Program tidak dimuat dengan benar. Eksekusi dibatalkan.")
            self.current_status = TempikStatus.FAILED
            return [{"status": "error", "message": "Program load failed"}]

        overall_execution_results: List[Dict[str, Any]] = []
        
        # Dapatkan batas waktu total eksekusi dari konteks
        max_total_duration_seconds = self.context_manager.resource_limits.get("max_cpu_time_seconds_total", 300)
        execution_start_time_mono = time.monotonic()
        setattr(self, '_cycle_start_time_mono', execution_start_time_mono) # Untuk perhitungan CPU time per siklus

        max_cycles_limit = 10000 # Batas pengaman untuk loop tak terbatas
        current_cycle_count = 0

        while self.current_status not in [TempikStatus.COMPLETED, TempikStatus.FAILED, TempikStatus.HALTED] \
              and current_cycle_count < max_cycles_limit:
            
            # 1. Cek Batas Waktu Eksekusi Total
            elapsed_time_seconds = time.monotonic() - execution_start_time_mono
            self.context_manager.resource_usage["cpu_time_elapsed_seconds"] = elapsed_time_seconds # Update penggunaan CPU time
            if elapsed_time_seconds > max_total_duration_seconds:
                err_msg = f"Batas waktu eksekusi total Tempik ({max_total_duration_seconds}s) tercapai."
                logger.error(f"[{self.tempik_id_str}] {err_msg}")
                self.current_status = TempikStatus.FAILED
                self.audit_logger.record_event(datetime.now(timezone.utc).isoformat(), self.tempik_id_str, "GLOBAL_EXEC_TIMEOUT", "FAILED", int(max_total_duration_seconds*1000), self.current_asu_file_hash, err_msg)
                overall_execution_results.append({"status": "global_timeout", "error": err_msg, "duration_seconds": elapsed_time_seconds})
                break # Keluar dari loop eksekusi

            # 2. Jalankan Satu Siklus Pipeline
            can_continue, cycle_output = await self._pipeline.run_single_cycle()
            current_cycle_count += 1
            if cycle_output: # Catat output siklus (bisa berupa hasil instruksi atau status error)
                overall_execution_results.append(cycle_output if isinstance(cycle_output, dict) else {"result": cycle_output})

            if not can_continue: # Pipeline meminta berhenti (EOF, error fatal, HALT)
                logger.info(f"[{self.tempik_id_str}] Pipeline meminta penghentian eksekusi. Status akhir Tempik: {self.current_status.value}")
                break # Keluar dari loop eksekusi
            
            # Jika status WAITING (misal dari instruksi WAIT), pipeline akan pause.
            # Kita perlu loop lagi untuk cek timeout global atau event eksternal (jika ada).
            if self.current_status == TempikStatus.WAITING:
                # Jika ada instruksi WAIT, handler-nya akan melakukan asyncio.sleep.
                # Di sini, kita hanya memastikan loop berlanjut untuk cek timeout global.
                await asyncio.sleep(0.01) # Yield kecil agar tidak memblokir total

        if current_cycle_count >= max_cycles_limit and self.current_status not in [TempikStatus.COMPLETED, TempikStatus.FAILED, TempikStatus.HALTED]:
            err_msg = f"Eksekusi mencapai batas maksimum siklus ({max_cycles_limit}). Dihentikan."
            logger.warning(f"[{self.tempik_id_str}] {err_msg}")
            self.current_status = TempikStatus.FAILED
            overall_execution_results.append({"status": "max_cycles_reached", "error": err_msg})
            self.audit_logger.record_event(datetime.now(timezone.utc).isoformat(), self.tempik_id_str, "MAX_CYCLES_LIMIT", "FAILED", int(elapsed_time_seconds*1000), self.current_asu_file_hash, err_msg)

        # Cleanup pasca-eksekusi (misal, tutup session jaringan)
        await self.network_unit.close_session()
        logger.info(f"[{self.tempik_id_str}] Eksekusi program '{self.current_asu_file_hash}' selesai. Status akhir: {self.current_status.value}. Total siklus: {current_cycle_count}.")
        return overall_execution_results

    def find_matching_control_label(self, pc_of_current_if_or_else: int, target_labels: List[InstruksiASU], skip_current_block: bool) -> int:
        """
        Mencari PC dari instruksi kontrol berikutnya (ELSE atau ENDIF) yang cocok.
        - pc_of_current_if_or_else: PC dari instruksi IF atau ELSE saat ini.
        - target_labels: Daftar jenis instruksi target (misal, [InstruksiASU.ELSE, InstruksiASU.ENDIF]).
        - skip_current_block: Jika True, dan kita menemukan ENDIF, kembalikan PC setelah ENDIF.
                              Jika False, kembalikan PC dari target itu sendiri.
        """
        level = 0 # Untuk menangani blok IF/ELSE bersarang
        search_pc = pc_of_current_if_or_else + 1 # Mulai cari dari instruksi berikutnya

        while search_pc < len(self._program_body):
            instr_enum_at_search_pc = self._program_body[search_pc].instruksi
            
            if instr_enum_at_search_pc == InstruksiASU.IF:
                level += 1
            elif instr_enum_at_search_pc == InstruksiASU.ENDIF:
                if level == 0: # Ini adalah ENDIF yang cocok untuk IF/ELSE saat ini
                    if InstruksiASU.ENDIF in target_labels:
                        return search_pc + 1 if skip_current_block else search_pc
                    # Jika targetnya ELSE dan kita ketemu ENDIF dulu, berarti tidak ada ELSE yang cocok
                    # Dalam kasus ini, jika ENDIF adalah target, kita sudah menemukannya.
                    # Jika targetnya hanya ELSE, dan kita ketemu ENDIF, berarti ELSE tidak ada.
                    # Perilaku default jika target tidak ketemu adalah EOF, jadi ini mungkin OK.
                else: # ENDIF dari blok inner
                    level -= 1
            elif instr_enum_at_search_pc in target_labels and level == 0:
                # Menemukan target (ELSE atau ENDIF) di level yang sama
                return search_pc + 1 if skip_current_block and instr_enum_at_search_pc == InstruksiASU.ENDIF else search_pc
            
            search_pc += 1
        
        logger.warning(f"[{self.tempik_id_str}] Tidak menemukan label kontrol {target_labels} yang cocok setelah PC={pc_of_current_if_or_else}. Mengarah ke EOF.")
        return len(self._program_body) # EOF jika tidak ditemukan

    # --- Implementasi Handler Instruksi .asu (Metode Asinkron) ---
    # Setiap handler menerima `params: Dict[str, Any]` dan mengembalikan `Dict[str, Any]`
    # yang minimal berisi `{"status": "success/failed/etc", ...}`.

    async def _instr_handler_init_env(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handler untuk INIT_ENV: Menginisialisasi direktori kerja di VFS."""
        vfs_cwd_path = params.get("working_dir", "/") # Default ke root VFS
        try:
            self.vfs.mkdir(vfs_cwd_path, self.context_manager, make_parents=True)
            self.context_manager.set_current_working_directory(vfs_cwd_path, self.vfs)
            return {"status": "success", "working_directory_vfs": vfs_cwd_path}
        except Exception as e:
            return {"status": "failed", "error": f"Gagal INIT_ENV ke VFS '{vfs_cwd_path}': {str(e)}"}

    async def _instr_handler_set_env(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handler untuk SET_ENV: Menetapkan variabel lingkungan."""
        vars_actually_set = {}
        for key, value in params.items():
            # Validasi sederhana untuk nama variabel
            if key and isinstance(key, str) and (key.isalnum() or '_' in key or '-' in key or '.' in key) :
                self.context_manager.set_environment_variable(key, str(value))
                vars_actually_set[key.upper()] = str(value)
            else:
                logger.warning(f"[{self.tempik_id_str}] SET_ENV: Nama variabel '{key}' tidak valid, dilewati.")
        return {"status": "success", "environment_variables_set": vars_actually_set}

    async def _instr_handler_log(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handler untuk LOG: Mencatat pesan ke output standar Tempik."""
        message = str(params.get("message", ""))
        level = str(params.get("level", "INFO")).upper()
        self.io_handler.standard_log(message, level, source_instruction="LOG", current_file_hash=self.current_asu_file_hash)
        return {"status": "success", "message_logged": message, "log_level": level}

    async def _instr_handler_execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handler untuk EXECUTE: Menjalankan perintah (internal VFS atau subproses host dengan sandbox)."""
        command_str_or_list = params.get("command", "")
        args_list = params.get("args", [])
        # output_gpr = params.get("output_gpr") # GPR untuk menyimpan stdout
        # error_gpr = params.get("error_gpr")   # GPR untuk menyimpan stderr

        full_command_parts: List[str] = []
        if isinstance(command_str_or_list, str) and command_str_or_list:
            full_command_parts.extend(shlex.split(command_str_or_list)) # Gunakan shlex untuk parsing aman
        elif isinstance(command_str_or_list, list):
            full_command_parts.extend(str(item) for item in command_str_or_list)
        
        if isinstance(args_list, list):
            full_command_parts.extend(str(item) for item in args_list)

        if not full_command_parts:
            return {"status": "failed", "error": "Perintah eksekusi tidak valid atau kosong."}

        # 1. Periksa Kebijakan Keamanan
        if not self.security_policy_module.is_command_allowed(full_command_parts, self.context_manager):
            return {"status": "failed", "error": "Eksekusi perintah diblokir oleh kebijakan keamanan."}

        # 2. Coba eksekusi sebagai perintah internal VFS
        # (Implementasi ini dipindahkan ke V2, bisa disalin/disesuaikan)
        # ...

        # 3. Jika bukan internal, dan diizinkan, coba eksekusi sebagai subproses host (DENGAN SANDBOX NYATA!)
        # Kode di bawah ini adalah placeholder dan SANGAT TIDAK AMAN tanpa sandbox.
        if self.security_policy_module._flags.intersection({"allow-host-subprocess", "debug-unsafe-exec"}): # Flag berbahaya untuk debug
            try:
                # Dapatkan CWD dari VFS. Jika ini adalah path host yang di-mount, gunakan itu.
                # Jika tidak, eksekusi dari temporary dir yang aman.
                # Ini sangat kompleks untuk diimplementasikan dengan benar.
                effective_cwd_host = self.context_manager.current_working_directory # Placeholder, harus path host nyata
                if not os.path.exists(effective_cwd_host) or not os.path.isdir(effective_cwd_host):
                    effective_cwd_host = tempfile.gettempdir() # Fallback sangat tidak aman

                # Kumpulkan env vars dari konteks
                current_env = self.context_manager.environment_vars.copy()

                logger.warning(f"[{self.tempik_id_str}] EXECUTE: Menjalankan subproses host (MODE TIDAK AMAN): {' '.join(full_command_parts)} di CWD host: {effective_cwd_host}")
                
                # Gunakan asyncio.create_subprocess_exec untuk non-blocking
                process = await asyncio.create_subprocess_exec(
                    *full_command_parts,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=effective_cwd_host, # Harus path host yang valid
                    env=current_env
                )
                stdout_bytes, stderr_bytes = await process.communicate() # Tunggu selesai
                return_code = process.returncode if process.returncode is not None else -1

                stdout_str = stdout_bytes.decode('utf-8', errors='replace')
                stderr_str = stderr_bytes.decode('utf-8', errors='replace')

                # if output_gpr: self.registers.set_gpr(output_gpr, stdout_str)
                # if error_gpr: self.registers.set_gpr(error_gpr, stderr_str)
                
                exec_status = "success" if return_code == 0 else "failed"
                if return_code != 0:
                     logger.error(f"[{self.tempik_id_str}] EXECUTE subproses gagal (rc={return_code}): {stderr_str or stdout_str}")
                
                return {"status": exec_status, "return_code": return_code, "stdout": stdout_str, "stderr": stderr_str}

            except FileNotFoundError:
                return {"status": "failed", "error": f"Perintah tidak ditemukan: {full_command_parts[0]}"}
            except Exception as e:
                return {"status": "failed", "error": f"Error eksekusi subproses: {str(e)}"}
        else:
            return {"status": "failed", "error": "Eksekusi subproses host tidak diizinkan oleh kebijakan keamanan."}

    async def _instr_handler_if(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handler untuk IF: Mengevaluasi kondisi dan mengatur flag COND."""
        condition_expression = str(params.get("condition_str", "True"))
        evaluation_result = self.exec_logic_unit.evaluate_condition(condition_expression, self.context_manager)
        # Flag COND akan di-set oleh pipeline berdasarkan hasil ini
        return {"status": "success", "condition_expression": condition_expression, "condition_result": evaluation_result}

    async def _instr_handler_jump(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handler untuk JUMP: Melompat ke label tertentu."""
        target_label_name = params.get("target_label")
        if not target_label_name or not isinstance(target_label_name, str):
            return {"status": "failed", "error": "Parameter 'target_label' (string) diperlukan untuk JUMP."}
        
        target_pc_address = self._label_to_pc_map.get(target_label_name)
        if target_pc_address is None:
            return {"status": "failed", "error": f"Label JUMP '{target_label_name}' tidak ditemukan dalam program."}
        
        # Pipeline akan menggunakan "target_pc_absolute" untuk mengoverride PC
        return {"status": "success", "jump_to_label": target_label_name, "target_pc_absolute": target_pc_address}

    async def _instr_handler_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handler untuk CALL: Memanggil sub-program (label) dan menyimpan return address."""
        target_label_name = params.get("target_label")
        if not target_label_name or not isinstance(target_label_name, str):
            return {"status": "failed", "error": "Parameter 'target_label' (string) diperlukan untuk CALL."}

        target_pc_address = self._label_to_pc_map.get(target_label_name)
        if target_pc_address is None:
            return {"status": "failed", "error": f"Label CALL '{target_label_name}' tidak ditemukan."}

        # PC saat ini (di RegisterStorage) sudah menunjuk ke instruksi SETELAH CALL (karena diincrement di Fetch)
        return_address_pc = self.program_counter.current_address
        self.registers.lr = return_address_pc # Simpan ke Link Register
        self.runtime_data_storage.push_to_stack(return_address_pc) # Simpan juga ke stack untuk nested calls
        
        logger.debug(f"[{self.tempik_id_str}] CALL ke '{target_label_name}' (PC={target_pc_address}). Return Addr PC={return_address_pc} disimpan.")
        return {"status": "success", "call_to_label": target_label_name, "target_pc_absolute": target_pc_address}

    async def _instr_handler_ret(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handler untuk RET: Kembali dari sub-program menggunakan return address dari stack."""
        try:
            return_address_pc = self.runtime_data_storage.pop_from_stack()
            if not isinstance(return_address_pc, int) or return_address_pc < 0:
                return {"status": "failed", "error": "Alamat kembali tidak valid di stack."}
            
            logger.debug(f"[{self.tempik_id_str}] RET: Kembali ke PC={return_address_pc} dari stack.")
            # Pipeline akan menggunakan "return_to_pc_absolute"
            return {"status": "success", "return_to_pc_absolute": return_address_pc}
        except IndexError: # Stack underflow
            return {"status": "failed", "error": "RET gagal: Stack kosong, tidak ada alamat kembali."}
        except Exception as e:
            return {"status": "failed", "error": f"Error saat RET: {str(e)}"}
            
    # Handler lain akan mengikuti pola serupa, menggunakan komponen modular.
    # ... (Implementasi handler lain yang lebih detail dan fungsional) ...
    async def _instr_handler_nop(self, params: Dict[str, Any]) -> Dict[str, Any]: return {"status": "success"}
    async def _instr_handler_else(self, params: Dict[str, Any]) -> Dict[str, Any]: return {"status": "success"} # Logika skip di pipeline
    async def _instr_handler_endif(self, params: Dict[str, Any]) -> Dict[str, Any]: return {"status": "success"} # Hanya penanda
    async def _instr_handler_halt(self, params: Dict[str, Any]) -> Dict[str, Any]: return {"status": "halt_requested", "reason": params.get("reason", "HALT")}
    async def _instr_handler_shutdown(self, params: Dict[str, Any]) -> Dict[str, Any]: return {"status": "shutdown_requested", "reason": params.get("reason", "SHUTDOWN")}
    # ... (Tambahkan implementasi fungsional untuk handler lain sesuai kebutuhan audit) ...
    # Contoh untuk beberapa handler yang belum diisi:
    async def _instr_handler_wait(self, params: Dict[str, Any]) -> Dict[str, Any]:
        duration_s = float(params.get("time_seconds", 1.0))
        if duration_s < 0: return {"status": "failed", "error": "Durasi WAIT harus positif."}
        self.current_status = TempikStatus.WAITING
        await asyncio.sleep(duration_s)
        # Status akan direset oleh pipeline setelah sleep
        return {"status": "success", "waited_seconds": duration_s}

    async def _instr_handler_verify_hash(self, params: Dict[str, Any]) -> Dict[str, Any]:
        vfs_file_path = params.get("file_vfs_path")
        expected_hash_val = params.get("hash_value")
        algo = params.get("algorithm", "sha256")
        if not vfs_file_path or not expected_hash_val:
            return {"status": "failed", "error": "file_vfs_path dan hash_value diperlukan."}
        
        file_data = self.vfs.read_file(vfs_file_path, self.context_manager)
        if file_data is None:
            return {"status": "failed", "error": f"File VFS '{vfs_file_path}' tidak ditemukan."}
        
        is_valid = self.crypto_engine.verify_data_hash(file_data, expected_hash_val, algo)
        return {"status": "success", "verified": is_valid, "algorithm": algo, "file": vfs_file_path, "expected": expected_hash_val, "actual": self.crypto_engine.calculate_hash(file_data, algo) if not is_valid else expected_hash_val}


class UTEKSystemExecutor: # Menggantikan UTEKVirtualExecutor
    """
    Executor Sistem UTEK.
    Bertanggung jawab untuk mengelola pool TempikUnit, mem-parsing file .asu,
    menjadwalkan eksekusi, dan menangani siklus hidup keseluruhan.
    """
    def __init__(self, max_tempik_units: int = 5, audit_log_filepath: Optional[str] = "utek_system_audit_v3.log"):
        self.max_tempik_units = max_tempik_units
        self.central_audit_logger = CentralAuditLogger(audit_log_filepath)
        
        # Pool TempikUnit, setiap TempikUnit memiliki referensi ke Executor ini (untuk DELEGATE_TO)
        self.tempik_unit_pool: List[TempikUnit] = [
            TempikUnit(i, self.central_audit_logger, self) for i in range(max_tempik_units)
        ]
        self.task_scheduler = TaskScheduler(self.tempik_unit_pool)
        
        self._globally_locked_asu_hashes: Set[str] = set() # Hash file .asu yang dikunci global
        self._parsed_asu_cache: Dict[str, FileASU] = {} # Cache FileASU yang sudah diparsing (key: content_hash)
        self._is_shutting_down_system: bool = False
        self._active_tempik_tasks: List[asyncio.Task] = []
        logger.info(f"UTEKSystemExecutor (V3 Audit Aligned) diinisialisasi dengan {max_tempik_units} TempikUnit.")

    def _load_and_parse_asu_file(self, file_path_on_host: str) -> FileASU:
        """Memuat dan mem-parsing file .asu dari path host."""
        # Validasi dasar path
        if not os.path.exists(file_path_on_host):
            raise FileNotFoundError(f"File .asu tidak ditemukan di path host: {file_path_on_host}")
        if not file_path_on_host.endswith(".asu"):
            raise ValueError("Nama file harus berakhiran .asu")

        # Cek cache berdasarkan nama file (yang seharusnya hash konten)
        filename_hash_candidate = Path(file_path_on_host).stem.lower()
        if filename_hash_candidate in self._parsed_asu_cache:
            cached_asu = self._parsed_asu_cache[filename_hash_candidate]
            # Verifikasi ulang hash konten jika perlu, atau asumsikan cache valid jika nama file = hash
            if cached_asu.content_hash_sha256 == filename_hash_candidate:
                logger.debug(f"FileASU untuk '{filename_hash_candidate}' diambil dari cache.")
                return cached_asu
        
        # Baca file, dekompresi, parse JSON
        try:
            with open(file_path_on_host, 'rb') as f_compressed:
                compressed_content = f_compressed.read()
            
            # Dekompresi (asumsi gzip jika tidak ada info lain, atau deteksi magic number)
            # Ini bisa lebih canggih dengan membaca header.compression_info dulu jika formatnya memungkinkan.
            decompressed_content: bytes
            if compressed_content.startswith(b'\x1f\x8b'): # Gzip magic
                decompressed_content = gzip.decompress(compressed_content)
            elif compressed_content.startswith(b'\x04\x22\x4d\x18'): # LZ4 magic
                decompressed_content = lz4.frame.decompress(compressed_content)
            else: # Asumsikan tidak terkompresi atau format lain
                decompressed_content = compressed_content
            
            json_content_dict = json.loads(decompressed_content.decode('utf-8'))
        except Exception as e:
            logger.error(f"Gagal membaca atau dekompresi file .asu '{file_path_on_host}': {e}")
            raise ValueError(f"Error parsing file .asu: {e}") from e

        # Validasi struktur dasar
        if 'header' not in json_content_dict or 'body' not in json_content_dict:
            raise ValueError("Struktur file .asu tidak valid: 'header' atau 'body' tidak ditemukan.")

        header_obj = HeaderASU(**json_content_dict['header']) # Inisialisasi HeaderASU dari dict
        
        instr_decoder = InstructionObjectDecoder() # Decoder instruksi
        body_instr_objects = [instr_decoder.decode_from_dict(raw_instr) for raw_instr in json_content_dict['body']]
        
        asu_file_obj = FileASU(header=header_obj, body=body_instr_objects)
        asu_file_obj.generate_content_hash() # Hitung hash konten (header+body)
        
        # Validasi nama file dengan hash konten
        if asu_file_obj.content_hash_sha256 != filename_hash_candidate:
            logger.warning(f"Nama file .asu '{filename_hash_candidate}' tidak cocok dengan hash konten terhitung '{asu_file_obj.content_hash_sha256}'.")
            # Tetap lanjutkan, tapi ini bisa jadi indikasi masalah integritas atau penamaan.

        # Verifikasi checksum_signature dari header (hash dari file terkompresi atau signature digital)
        if header_obj.checksum_signature:
            # Implementasi verifikasi checksum/signature di sini menggunakan CryptographicEngine
            # Contoh: jika checksum_signature adalah hash SHA256 dari file terkompresi
            # crypto_temp = CryptographicEngine("temp_verifier")
            # if not crypto_temp.verify_data_hash(compressed_content, header_obj.checksum_signature, "sha256"):
            #     raise ValueError(f"Verifikasi checksum_signature file .asu '{file_path_on_host}' GAGAL.")
            # logger.info(f"Checksum_signature file .asu '{file_path_on_host}' BERHASIL diverifikasi.")
            pass # Placeholder untuk implementasi verifikasi

        self._parsed_asu_cache[asu_file_obj.content_hash_sha256] = asu_file_obj # Cache dengan hash konten
        return asu_file_obj

    async def schedule_and_execute_asu(self, host_file_path: str, 
                                     is_delegated_execution: bool = False, 
                                     inherited_context_parameters: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Menjadwalkan dan mengeksekusi file .asu.
        Mengembalikan dictionary yang berisi laporan hasil eksekusi.
        """
        if self._is_shutting_down_system:
            return {"status": "system_shutdown", "error": "UTEKSystemExecutor sedang dalam proses shutdown."}

        try:
            asu_file_object = self._load_and_parse_asu_file(host_file_path)
        except Exception as e:
            logger.error(f"Gagal memuat/parsing file .asu '{host_file_path}': {e}", exc_info=True)
            return {"status": "parsing_error", "file_path": host_file_path, "error_details": str(e)}

        content_hash = asu_file_object.content_hash_sha256
        
        # Cek penguncian global (hanya untuk eksekusi utama, bukan delegasi)
        if not is_delegated_execution and content_hash in self._globally_locked_asu_hashes:
            msg = f"Eksekusi file .asu hash '{content_hash}' terkunci secara global."
            logger.warning(msg)
            return {"status": "execution_locked", "asu_hash": content_hash, "message": msg}

        selected_tempik_unit = self.task_scheduler.request_available_tempik()
        if not selected_tempik_unit:
            msg = f"Tidak ada TempikUnit yang tersedia untuk menjalankan .asu hash '{content_hash}'."
            logger.warning(msg)
            # TODO: Implementasi antrian tugas jika semua Tempik sibuk
            return {"status": "no_tempik_available", "asu_hash": content_hash, "message": msg}

        logger.info(f"Memulai eksekusi .asu '{content_hash}' pada {selected_tempik_unit.tempik_id_str}{' (sebagai delegasi)' if is_delegated_execution else ''}.")
        
        # Buat task asyncio untuk menjalankan TempikUnit.execute_program()
        # Ini memungkinkan beberapa TempikUnit berjalan secara bersamaan (concurrently).
        tempik_task = asyncio.create_task(
            selected_tempik_unit.execute_program(asu_file_object, inherited_ctx_params=inherited_context_parameters),
            name=f"Task-{selected_tempik_unit.tempik_id_str}-{content_hash[:8]}"
        )
        self._active_tempik_tasks.append(tempik_task)

        try:
            raw_execution_outputs = await tempik_task # Tunggu hasil dari satu TempikUnit
        except Exception as e: # Error tak terduga dari dalam TempikUnit.execute_program
            logger.error(f"Error kritis saat menjalankan task untuk {selected_tempik_unit.tempik_id_str} dengan .asu '{content_hash}': {e}", exc_info=True)
            selected_tempik_unit.current_status = TempikStatus.FAILED # Pastikan status FAILED
            raw_execution_outputs = [{"status": "critical_tempik_error", "error_details": str(e)}]
        finally:
            self._active_tempik_tasks.remove(tempik_task) # Hapus dari daftar task aktif

        # Cek apakah ada permintaan shutdown sistem dari hasil eksekusi
        # (Ini perlu diperiksa di hasil setiap instruksi jika SHUTDOWN bisa dari mana saja)
        # Untuk sekarang, asumsikan hasil akhir Tempik bisa menandakan ini.
        # Atau, TempikUnit bisa langsung memanggil metode shutdown di UTEKSystemExecutor.
        if selected_tempik_unit.current_status == TempikStatus.HALTED and \
           any(isinstance(res, dict) and res.get("status") == "shutdown_requested" for res in raw_execution_outputs):
            if not self._is_shutting_down_system: # Hanya proses sekali
                await self.initiate_system_shutdown()

        # Buat laporan eksekusi akhir
        execution_report = {
            "asu_content_hash": content_hash,
            "executed_on_tempik_id": selected_tempik_unit.tempik_id_str,
            "final_tempik_status": selected_tempik_unit.current_status.value,
            "total_instructions_in_asu": len(asu_file_object.body),
            "instruction_execution_outputs": raw_execution_outputs, # Daftar hasil dari setiap siklus/instruksi
            "is_delegated": is_delegated_execution
        }
        return execution_report

    async def initiate_system_shutdown(self):
        """Memulai proses shutdown UTEKSystemExecutor secara terkendali."""
        if self._is_shutting_down_system: return # Sudah dalam proses
        
        logger.critical("UTEKSystemExecutor: Menerima permintaan SHUTDOWN. Memulai penghentian sistem...")
        self._is_shutting_down_system = True

        # 1. Hentikan penjadwalan tugas baru (sudah otomatis karena flag _is_shutting_down_system)
        # 2. Tunggu atau batalkan task Tempik yang sedang berjalan
        if self._active_tempik_tasks:
            logger.info(f"Menunggu {len(self._active_tempik_tasks)} task Tempik aktif untuk selesai atau timeout...")
            # Beri waktu bagi task untuk selesai secara normal
            done, pending = await asyncio.wait(self._active_tempik_tasks, timeout=15.0) # Timeout 15 detik
            
            for task in pending:
                task_name = task.get_name() if hasattr(task, 'get_name') else "UnknownTask"
                logger.warning(f"Task Tempik '{task_name}' tidak selesai tepat waktu saat shutdown, mencoba membatalkan...")
                task.cancel()
                try:
                    await task # Tunggu pembatalan selesai (atau exception jika tidak bisa dibatalkan)
                except asyncio.CancelledError:
                    logger.info(f"Task Tempik '{task_name}' berhasil dibatalkan.")
                except Exception as e:
                    logger.error(f"Error saat menunggu pembatalan task '{task_name}': {e}")
            self._active_tempik_tasks.clear()

        # 3. Cleanup sumber daya lain (misal, tutup file log audit)
        self.central_audit_logger.close_log_file()
        logger.info("UTEKSystemExecutor: Proses shutdown selesai.")

    # Metode utilitas lain (validasi, lock, status, cleanup) perlu disesuaikan
    # ... (Implementasi validasi_integritas_file, lock_global_execution, dll. dari V2 bisa disesuaikan di sini) ...


# --- CLI Interface (Contoh Penggunaan) ---
async def main_cli_v3_audit():
    """CLI interface contoh untuk UTEKSystemExecutor V3."""
    import argparse
    parser = argparse.ArgumentParser(description="UTEK System Executor (V3 Audit Aligned) untuk file .asu")
    parser.add_argument("command", choices=["run", "create-sample", "validate-hash"], help="Perintah yang akan dijalankan.")
    parser.add_argument("--file", "-f", help="Path ke file .asu untuk perintah 'run' atau 'validate-hash'.")
    parser.add_argument("--output-dir", "-o", default=".", help="Direktori output untuk 'create-sample'.")
    parser.add_argument("--max-tempiks", "-m", type=int, default=3, help="Jumlah maksimum TempikUnit yang akan digunakan.")
    parser.add_argument("--audit-file", default="utek_audit_main_v3.log", help="Path untuk file audit log utama.")
    
    args = parser.parse_args()

    # Inisialisasi Executor Utama
    system_executor = UTEKSystemExecutor(
        max_tempik_units=args.max_tempiks,
        audit_log_filepath=args.audit_file
    )

    try:
        if args.command == "run":
            if not args.file:
                print("Error: Argumen --file diperlukan untuk perintah 'run'.")
                return
            
            logger.info(f"CLI: Meminta eksekusi file .asu: {args.file}")
            report = await system_executor.schedule_and_execute_asu(args.file)
            
            print("\n=== Laporan Eksekusi Akhir (V3 Audit) ===")
            # Gunakan default=str untuk menangani objek non-serializable seperti datetime
            print(json.dumps(report, indent=2, ensure_ascii=False, default=str)) 

        elif args.command == "create-sample":
            # Buat contoh file .asu menggunakan metode dari UTEKSystemExecutor (jika ada)
            # atau fungsi utilitas terpisah.
            # Untuk sekarang, kita panggil fungsi utilitas yang dimodifikasi.
            # Ini memerlukan instance sementara dari executor hanya untuk membuat file.
            temp_header = HeaderASU(asu_build_info="sample-cli-v3")
            temp_instr = [
                InstruksiEksekusi(instruksi=InstruksiASU.INIT_ENV, parameter={"working_dir":"/sample"}),
                InstruksiEksekusi(instruksi=InstruksiASU.LOG, parameter={"message":"Contoh file .asu V3 dibuat dari CLI."}),
                InstruksiEksekusi(instruksi=InstruksiASU.HALT)
            ]
            # Untuk create_asu_file, kita mungkin perlu instance sementara atau metode statis
            # Karena create_asu_file di V1/V2 ada di UTEKVirtualExecutor, kita tiru strukturnya.
            # Ini bisa jadi metode di UTEKSystemExecutor atau fungsi utilitas.
            # Untuk contoh ini, kita asumsikan ada fungsi utilitas:
            # file_path = create_sample_asu_file_utility_v3(temp_header, temp_instr, args.output_dir)
            # print(f"Contoh file .asu V3 berhasil dibuat di: {file_path}")
            print("Fungsi 'create-sample' perlu implementasi utilitas pembuatan file .asu V3.")


        elif args.command == "validate-hash":
            # ... (Implementasi validasi hash nama file vs konten) ...
            print("Fungsi 'validate-hash' belum diimplementasikan di CLI V3 ini.")

    except Exception as e:
        print(f"Error fatal pada CLI: {e}")
        logger.critical(f"Error fatal pada CLI UTEKSystemExecutor: {e}", exc_info=True)
    finally:
        if not system_executor._is_shutting_down_system:
            await system_executor.initiate_system_shutdown()

if __name__ == "__main__":
    # Menjalankan event loop asyncio
    try:
        asyncio.run(main_cli_v3_audit())
    except KeyboardInterrupt:
        logger.info("CLI dihentikan oleh pengguna (KeyboardInterrupt).")
    except Exception as main_err:
        logger.critical(f"Error tidak tertangani di level main: {main_err}", exc_info=True)

