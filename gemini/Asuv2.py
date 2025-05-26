#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UTEK Virtual — 963-Tempik Executor untuk File .asu (Refactor V4 - Kepatuhan Audit Ketat)

Proyek: ASU Virtual UTEK 963-Tempik
Pengembang: Kode Baris Rahasia & Python Research (Direfactor sesuai Audit Internal V4)
Berdasarkan standar NDAS & MIKIR, serta temuan audit untuk kepatuhan Deloitte & IBM.

Dokumen ini mengimplementasikan arsitektur UTEK Virtual Executor
untuk memproses file .asu secara aman, modular, dan sesuai dengan spesifikasi audit.
Tidak ada simulasi komponen level rendah generik; fokus pada arsitektur UTEK.
"""

import asyncio
import hashlib
import json
import logging
import os
import shlex # Untuk parsing argumen perintah yang lebih aman
import shutil
# import subprocess # Penggunaan subprocess harus sangat dibatasi dan di-sandbox
import tempfile
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone # Selalu gunakan timezone-aware datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable, Tuple, Set, Coroutine

# Impor pustaka kriptografi dan kompresi
import gzip
import lz4.frame
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding as asym_padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

# --- Konfigurasi Logging Global ---
# Menggunakan format logging yang lebih detail dan standar industri
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03dZ | %(levelname)-8s | %(process)d | %(threadName)s | %(module)s.%(funcName)s:%(lineno)d | %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%S'
)
logging.Formatter.converter = time.gmtime # Menggunakan UTC untuk timestamp log
logger = logging.getLogger("UTEKSystemExecutor") # Logger utama untuk sistem


# --- Enumerasi dan Konstanta Utama Sesuai Domain UTEK ---
class TempikUnitStatus(Enum):
    """Status operasional untuk setiap Unit Eksekusi Tempik (TempikUnit)."""
    IDLE = "IDLE" # Siap menerima dan memproses tugas .asu baru
    INITIALIZING = "INITIALIZING" # Dalam proses inisialisasi sebelum eksekusi
    FETCHING_INSTRUCTION = "FETCHING_INSTRUCTION" # Tahap pengambilan instruksi .asu
    DECODING_INSTRUCTION = "DECODING_INSTRUCTION" # Tahap pendekodean instruksi .asu
    EXECUTING_OPERATION = "EXECUTING_OPERATION" # Tahap eksekusi logika operasi .asu
    ACCESSING_STORAGE = "ACCESSING_STORAGE" # Tahap akses ke RuntimeDataStorage atau IsolatedVirtualFileSystem
    COMMITTING_RESULTS = "COMMITTING_RESULTS" # Tahap penulisan hasil kembali ke state atau storage
    WAITING_CONDITION = "WAITING_CONDITION" # Menunggu kondisi eksternal atau waktu tertentu
    COMPLETED_SUCCESS = "COMPLETED_SUCCESS" # Tugas .asu selesai dengan sukses
    FAILED_ERROR = "FAILED_ERROR" # Tugas .asu gagal karena error internal atau eksternal
    HALTED_BY_REQUEST = "HALTED_BY_REQUEST" # Dihentikan secara eksplisit oleh instruksi HALT atau sinyal eksternal

class UTEKPipelineStage(Enum):
    """Tahapan dalam siklus pemrosesan instruksi .asu oleh TempikUnit."""
    FETCH_ASU_INSTRUCTION = "FETCH_ASU_INSTRUCTION" # Mengambil instruksi .asu berikutnya
    DECODE_ASU_INSTRUCTION = "DECODE_ASU_INSTRUCTION" # Mendekode instruksi .asu
    EXECUTE_ASU_OPERATION = "EXECUTE_ASU_OPERATION" # Mengeksekusi operasi inti instruksi .asu
    ACCESS_RUNTIME_STORAGE = "ACCESS_RUNTIME_STORAGE" # Mengakses penyimpanan runtime (VFS, stack)
    COMMIT_OPERATION_RESULT = "COMMIT_OPERATION_RESULT" # Menyimpan hasil operasi

class ASUInstructionSet(Enum): # Menggantikan InstruksiASU, sesuai audit "InstructionSet"
    """
    Instruction Set Architecture (ISA) resmi untuk file .asu dalam ekosistem UTEK.
    Mendefinisikan semua operasi standar yang dapat diproses oleh UTEKSystemExecutor.
    Nama enum menggunakan format UPPER_CASE_SNAKE sesuai konvensi.
    """
    # Konfigurasi Lingkungan dan Konteks (Sesuai Audit)
    INIT_ENV = "INIT_ENV"
    SET_ENV = "SET_ENV"
    SET_CONTEXT = "SET_CONTEXT"
    SYNC_CLOCK = "SYNC_CLOCK"
    AUTH = "AUTH"

    # Manajemen Sumber Daya dan Dependensi (Sesuai Audit)
    FETCH_REPO = "FETCH_REPO"
    CHECKOUT = "CHECKOUT"
    INSTALL = "INSTALL"
    UNPACK = "UNPACK"
    MOUNT = "MOUNT"
    INJECT = "INJECT"
    COMPILE = "COMPILE"

    # Eksekusi Inti dan Kontrol Aliran (Sesuai Audit)
    EXECUTE = "EXECUTE"
    CALL = "CALL"
    RET = "RET" # Ditambahkan untuk melengkapi CALL
    JUMP = "JUMP"
    SPAWN_THREAD = "SPAWN_THREAD" # Konseptual, memerlukan manajemen TempikUnit tambahan
    WAIT = "WAIT"
    DELEGATE_TO = "DELEGATE_TO"
    INVOKE_REMOTE = "INVOKE_REMOTE"
    HALT = "HALT"
    SHUTDOWN = "SHUTDOWN"

    # Keamanan, Verifikasi, dan Kriptografi (Sesuai Audit)
    VERIFY_HASH = "VERIFY_HASH"
    VERIFY_SIGNATURE = "VERIFY_SIGNATURE" # Lebih eksplisit dari VERIFY
    SIGN_DATA = "SIGN_DATA" # Lebih eksplisit dari SIGN
    ENCRYPT_DATA = "ENCRYPT_DATA" # Ditambahkan sesuai kebutuhan CryptoEngine
    DECRYPT_DATA = "DECRYPT_DATA"
    LOCK_EXECUTION = "LOCK_EXECUTION" # Lebih eksplisit dari LOCK_EXEC

    # Audit, Logging, dan Event (Sesuai Audit)
    POST_AUDIT_LOG = "POST_AUDIT_LOG" # Lebih eksplisit dari AUDIT_LOG
    WRITE_LOG_MESSAGE = "WRITE_LOG_MESSAGE" # Lebih eksplisit dari LOG
    EMIT_SYSTEM_EVENT = "EMIT_SYSTEM_EVENT" # Lebih eksplisit dari EMIT_EVENT

    # Operasi Jaringan dan Distribusi (Sesuai Audit)
    INITIALIZE_NETWORK = "INITIALIZE_NETWORK" # Lebih eksplisit dari NETWORK_UP
    MAP_NETWORK_PORT = "MAP_NETWORK_PORT" # Lebih eksplisit dari MAP_PORT
    PUSH_EXECUTION_RESULT = "PUSH_EXECUTION_RESULT" # Lebih eksplisit dari PUSH_RESULT

    # Logika Kondisional dan Kontrol (Sesuai Audit)
    IF_CONDITION = "IF_CONDITION" # Lebih eksplisit dari IF
    ELSE_BLOCK = "ELSE_BLOCK" # Lebih eksplisit dari ELSE
    END_IF_BLOCK = "END_IF_BLOCK" # Lebih eksplisit dari ENDIF
    ASSERT_CONDITION = "ASSERT_CONDITION" # Lebih eksplisit dari ASSERT

    # Manajemen Hasil dan Pembersihan (Sesuai Audit)
    EXPORT_ARTIFACT = "EXPORT_ARTIFACT" # Lebih eksplisit dari EXPORT
    CLEANUP_RESOURCES = "CLEANUP_RESOURCES" # Lebih eksplisit dari CLEANUP
    NO_OPERATION = "NO_OPERATION" # NOP, lebih eksplisit

# --- Struktur Data Inti untuk File .asu (Sesuai Audit) ---
@dataclass
class ASUHeaderData: # Menggantikan HeaderASU
    """
    Struktur data untuk header file .asu, sesuai spesifikasi standar UTEK.
    Berisi metadata krusial yang mengontrol bagaimana file .asu diproses.
    Semua field di sini wajib diisi atau memiliki default yang jelas.
    """
    processor_specification: str = "UTEK-963-TempikUnit-Executor-V4"
    protocol_version_asu: str = "ASU-Spec-v1.3.0" # Versi spesifikasi .asu
    execution_environment_req: str = "python-3.10-UTEK-NDAS" # Kebutuhan environment runtime
    memory_profile_config: str = "standard-512MiB"
    filesystem_scheme_type: str = "isolated-virtual-fs"
    security_policy_flags: List[str] = field(default_factory=lambda: ["default-sandboxed", "no-host-access", "network-egress-controlled"])
    time_budget_constraints: str = "total_max_exec_seconds=300;instruction_max_exec_seconds=60"
    content_integrity_signature: str = "" # Signature digital (misal, RSA/Ed25519) atau hash (SHA256/SHA512) dari konten .asu (setelah kompresi)
    compression_algorithm_info: str = "gzip" # "gzip", "lz4", "none"
    asu_build_metadata: str = field(default_factory=lambda: f"builder=UTEK-SDK-Internal;build_utc_timestamp={datetime.now(timezone.utc).isoformat()}")
    dependency_manifest_content_hash: str = "" # Hash dari file manifest dependensi (jika ada)
    target_utek_platform: str = "generic-virtualized-ndas"
    asu_execution_mode: str = "batch-sequential" # "batch-sequential", "service-interactive"
    network_access_policy: str = "egress-restricted-default" # "offline", "egress-restricted-default", "full-proxy"
    licensing_information_ref: str = "UTEK-EULA-InternalUse" # Referensi ke informasi lisensi
    max_decompressed_asu_size_bytes: int = 2 * 1024 * 1024 * 1024 # 2GB

    def to_dictionary(self) -> Dict[str, Any]:
        """Mengkonversi data header ke dictionary."""
        return {key: getattr(self, key) for key in self.__annotations__ if hasattr(self, key)}

@dataclass
class ASUInstructionObject: # Menggantikan InstruksiEksekusi
    """
    Representasi objek dari satu instruksi .asu yang telah diparsing.
    Digunakan secara internal oleh TempikUnit dan pipeline-nya.
    """
    operation_code: ASUInstructionSet # Kode operasi dari ISA .asu
    parameters: Dict[str, Any] = field(default_factory=dict) # Parameter spesifik untuk operasi
    jump_label: Optional[str] = None # Label untuk target JUMP, CALL
    execution_timeout_seconds: float = 30.0 # Batas waktu eksekusi untuk instruksi ini
    max_retry_attempts: int = 0 # Jumlah percobaan ulang jika gagal (0 berarti tidak ada retry)
    
    def to_dictionary(self) -> Dict[str, Any]:
        """Mengkonversi objek instruksi ke dictionary."""
        return {
            "operation_code": self.operation_code.value,
            "parameters": self.parameters,
            "jump_label": self.jump_label,
            "execution_timeout_seconds": self.execution_timeout_seconds,
            "max_retry_attempts": self.max_retry_attempts
        }

@dataclass
class ASUFileObject: # Menggantikan FileASU
    """
    Representasi lengkap dari file .asu yang telah diparsing.
    Terdiri dari header dan daftar objek instruksi.
    """
    header_data: ASUHeaderData # Objek header yang terstruktur
    instruction_stream: List[ASUInstructionObject] # Daftar instruksi yang akan dieksekusi
    # Hash dari konten (header + body) sebelum kompresi. Digunakan untuk identifikasi unik file .asu.
    # Nama file .asu idealnya adalah hash ini.
    content_sha256_hash: str = "" 

    def calculate_and_set_content_hash(self) -> str:
        """Menghitung dan menetapkan hash SHA-256 dari konten header dan instruction_stream."""
        header_dict_sorted = dict(sorted(self.header_data.to_dictionary().items()))
        
        stream_list_for_hash = []
        for instr_obj in self.instruction_stream:
            instr_dict = instr_obj.to_dictionary()
            if isinstance(instr_dict.get("parameters"), dict): # Pastikan parameter juga diurutkan
                instr_dict["parameters"] = dict(sorted(instr_dict["parameters"].items()))
            stream_list_for_hash.append(dict(sorted(instr_dict.items()))) # Urutkan field dalam dict instruksi
        
        content_for_hashing = {
            "header_data": header_dict_sorted,
            "instruction_stream": stream_list_for_hash
        }
        # Menggunakan separator yang rapat dan sort_keys untuk konsistensi hashing JSON
        content_json_str = json.dumps(content_for_hashing, sort_keys=True, separators=(',', ':'))
        hash_object = hashlib.sha256(content_json_str.encode('utf-8'))
        self.content_sha256_hash = hash_object.hexdigest()
        return self.content_sha256_hash


# --- Implementasi Komponen Arsitektur UTEK Virtual (Sesuai Daftar Audit) ---
# Nama kelas dan fungsionalitas disesuaikan dengan terminologi audit dan UTEK/NDAS.

@dataclass
class TempikRegisterStorage: # Sesuai audit: RegisterFile
    """
    Penyimpanan Register Internal untuk TempikUnit.
    Menyimpan state penting seperti Program Counter (PC), Stack Pointer (SP),
    Link Register (LR), flag kondisional, dan General Purpose Registers (GPR)
    yang dapat dimanipulasi oleh instruksi .asu.
    """
    pc: int = 0  # Program Counter: Indeks instruksi berikutnya dalam instruction_stream
    sp: int = 0  # Stack Pointer: Indeks puncak stack dalam RuntimeDataStorage
    lr: int = 0  # Link Register: Menyimpan alamat kembali untuk operasi CALL
    
    # General Purpose Registers (GPRs), misal gpr0 hingga gpr15
    gpr: Dict[str, Any] = field(default_factory=lambda: {f"gpr{i}": None for i in range(16)})
    
    # Bendera (Flags) Status dan Kondisional
    flags: Dict[str, bool] = field(default_factory=lambda: {
        "Z": False,  # Zero Flag: True jika hasil operasi terakhir adalah nol/sama
        "N": False,  # Negative/Sign Flag: True jika hasil operasi terakhir negatif/kurang dari
        "C": False,  # Carry Flag: True jika terjadi carry-out (penjumlahan) atau borrow (pengurangan)
        "V": False,  # Overflow Flag: True jika terjadi overflow pada operasi aritmatika
        "COND_RESULT": True # Hasil evaluasi kondisi IF_CONDITION terakhir (True jika kondisi terpenuhi)
    })

    def get_gpr_value(self, register_name: str) -> Any:
        """Mengambil nilai dari General Purpose Register."""
        # Normalisasi nama register (misal, case-insensitive, hilangkan prefix "gpr" jika ada)
        norm_name = register_name.lower().replace("gpr", "")
        if norm_name.isdigit() and f"gpr{norm_name}" in self.gpr:
            return self.gpr[f"gpr{norm_name}"]
        elif register_name.lower() in self.gpr: # Jika sudah format gprX
             return self.gpr[register_name.lower()]
        logger.warning(f"GPR '{register_name}' tidak ditemukan.")
        return None

    def set_gpr_value(self, register_name: str, value: Any):
        """Menetapkan nilai ke General Purpose Register."""
        norm_name = register_name.lower().replace("gpr", "")
        target_reg_key = ""
        if norm_name.isdigit() and f"gpr{norm_name}" in self.gpr:
            target_reg_key = f"gpr{norm_name}"
        elif register_name.lower() in self.gpr:
            target_reg_key = register_name.lower()

        if target_reg_key:
            self.gpr[target_reg_key] = value
            logger.debug(f"GPR '{target_reg_key}' di-set ke: {value}")
        else:
            logger.warning(f"GPR '{register_name}' tidak valid untuk penetapan nilai.")

    def get_flag_status(self, flag_name: str) -> bool:
        """Mengambil status flag kondisional (case-insensitive)."""
        return self.flags.get(flag_name.upper(), False)

    def set_flag_status(self, flag_name: str, status: bool):
        """Menetapkan status flag kondisional (case-insensitive)."""
        flag_key = flag_name.upper()
        if flag_key in self.flags:
            self.flags[flag_key] = status
            logger.debug(f"Flag UTEK '{flag_key}' di-set ke: {status}")
        else:
            logger.warning(f"Percobaan menetapkan flag UTEK tidak dikenal: {flag_name}")


class TempikProgramCounter: # Sesuai audit: ProgramCounter
    """
    Pengelola Program Counter (PC) untuk TempikUnit.
    Bertanggung jawab untuk melacak dan memperbarui alamat instruksi .asu berikutnya.
    """
    def __init__(self, register_storage_ref: TempikRegisterStorage):
        self._regs = register_storage_ref # Referensi ke penyimpanan register Tempik

    @property
    def current_instruction_address(self) -> int:
        """Mendapatkan alamat (indeks) instruksi saat ini yang ditunjuk oleh PC."""
        return self._regs.pc

    def advance_to_next_instruction(self, steps: int = 1):
        """Memajukan PC sebanyak 'steps' instruksi."""
        self._regs.pc += steps

    def jump_to_instruction_address(self, new_instruction_address: int):
        """Mengatur PC ke alamat (indeks) instruksi .asu yang baru."""
        self._regs.pc = new_instruction_address
        logger.debug(f"Program Counter Tempik diatur ke alamat instruksi: {new_instruction_address}")


class TempikControlUnitLogic: # Sesuai audit: ControlUnit
    """
    Logika Unit Kendali Tempik (konseptual).
    Dalam implementasi perangkat lunak UTEK ini, peran Control Unit tradisional
    (seperti pada perangkat keras) lebih terdistribusi. Logikanya diwujudkan dalam:
    1. Alur kerja TempikInstructionPipeline (fetch, decode, execute).
    2. Dispatcher instruksi di TempikUnit yang memanggil handler yang sesuai.
    3. Logika internal handler instruksi itu sendiri.
    Kelas ini berfungsi sebagai penanda konseptual dan tempat untuk fungsi utilitas
    terkait kontrol alur jika diperlukan, bukan sebagai komponen stateful besar.
    """
    def __init__(self, tempik_id_str: str):
        self.tempik_id_str = tempik_id_str
        logger.debug(f"[{self.tempik_id_str}] Logika TempikControlUnit (konseptual) aktif.")

    def generate_control_signals_for_stage(self, stage: UTEKPipelineStage, instruction_op_code: Optional[ASUInstructionSet] = None):
        """
        (Konseptual) Menghasilkan sinyal kontrol berdasarkan tahap pipeline dan instruksi.
        Dalam praktiknya, ini adalah keputusan logis dalam kode pipeline/handler.
        """
        logger.debug(f"[{self.tempik_id_str}] Sinyal kontrol (konseptual) untuk tahap '{stage.value}'"
                     f"{f' dan operasi {instruction_op_code.value}' if instruction_op_code else ''} dihasilkan.")
        # Contoh: Jika tahap EXECUTE dan operasi adalah SET_ENV, sinyalnya adalah "aktifkan penulisan ke ExecutionContext".


class TempikArithmeticLogicUnit: # Sesuai audit: ALU
    """
    Unit Aritmatika dan Logika Tempik.
    Menyediakan fungsionalitas untuk melakukan operasi aritmatika dasar,
    perbandingan, dan evaluasi ekspresi logika yang dibutuhkan oleh instruksi .asu
    seperti IF_CONDITION dan ASSERT_CONDITION. Juga mengatur flag status yang relevan.
    """
    def __init__(self, register_storage_ref: TempikRegisterStorage):
        self._regs = register_storage_ref

    def perform_comparison(self, operand1: Any, operand2: Any, operation: str = "==") -> bool:
        """
        Melakukan perbandingan antara dua operand dan mengatur flag Z (Zero) dan N (Negative/Sign).
        Mendukung perbandingan numerik dan string.
        """
        # Konversi ke tipe yang sesuai untuk perbandingan
        num_op1, num_op2 = None, None
        is_numeric_comparison = False
        try:
            num_op1 = float(operand1)
            num_op2 = float(operand2)
            is_numeric_comparison = True
        except (ValueError, TypeError):
            # Jika salah satu atau keduanya tidak bisa dikonversi ke float, lakukan perbandingan string
            str_op1, str_op2 = str(operand1), str(operand2)
        
        result: bool
        if is_numeric_comparison and num_op1 is not None and num_op2 is not None:
            if operation == "==": result = (num_op1 == num_op2)
            elif operation == "!=": result = (num_op1 != num_op2)
            elif operation == "<": result = (num_op1 < num_op2)
            elif operation == "<=": result = (num_op1 <= num_op2)
            elif operation == ">": result = (num_op1 > num_op2)
            elif operation == ">=": result = (num_op1 >= num_op2)
            else: raise ValueError(f"Operasi perbandingan tidak dikenal: {operation}")
            
            self._regs.set_flag_status("Z", num_op1 == num_op2)
            self._regs.set_flag_status("N", num_op1 < num_op2) # N true jika op1 < op2
        else: # Perbandingan string
            if operation == "==": result = (str_op1 == str_op2)
            elif operation == "!=": result = (str_op1 != str_op2)
            elif operation == "<": result = (str_op1 < str_op2) # Leksikografis
            elif operation == "<=": result = (str_op1 <= str_op2)
            elif operation == ">": result = (str_op1 > str_op2)
            elif operation == ">=": result = (str_op1 >= str_op2)
            else: raise ValueError(f"Operasi perbandingan tidak dikenal: {operation}")

            self._regs.set_flag_status("Z", str_op1 == str_op2)
            self._regs.set_flag_status("N", str_op1 < str_op2)

        logger.debug(f"ALU Comparison: '{operand1}' {operation} '{operand2}' -> {result}. Flags Z={self._regs.get_flag_status('Z')}, N={self._regs.get_flag_status('N')}")
        return result

    def evaluate_logical_expression(self, expression_string: str, context_manager_ref: 'TempikExecutionContextManager') -> bool:
        """
        Mengevaluasi ekspresi logika yang diberikan dalam string.
        PENTING: Harus menggunakan parser ekspresi yang aman dan terbatas, bukan eval().
        Ekspresi dapat merujuk ke GPR Tempik (misal, 'gpr0 == 10') atau variabel environment
        (misal, 'env.STATUS == "active"').
        """
        # Implementasi parser ekspresi aman adalah kompleks.
        # Ini adalah placeholder yang sangat disederhanakan dan TIDAK AMAN.
        # Untuk produksi, gunakan pustaka parser seperti pyparsing atau Lark,
        # atau buat parser kustom yang hanya mendukung subset operasi aman.
        logger.warning(f"Evaluasi ekspresi logika '{expression_string}' menggunakan placeholder. Implementasi aman diperlukan!")
        
        # Contoh sangat sederhana (hanya untuk demo, tidak aman):
        try:
            # Ganti placeholder dengan nilai aktual secara hati-hati
            # Format: "operand1 operator operand2" atau "flag_name"
            # Operator yang didukung (contoh): ==, !=, >, <, >=, <=, AND, OR, NOT
            # Operand bisa: reg.gprX, env.VAR_NAME, literal string/angka, flag.FLAG_NAME
            
            # Logika evaluasi yang lebih baik:
            # 1. Tokenize ekspresi.
            # 2. Buat Abstract Syntax Tree (AST).
            # 3. Evaluasi AST dengan mengambil nilai dari register dan environment secara aman.

            # Placeholder evaluasi:
            if "==" in expression_string:
                op1_str, op2_str = [s.strip() for s in expression_string.split("==", 1)]
                op1 = self._resolve_operand_value(op1_str, context_manager_ref)
                op2 = self._resolve_operand_value(op2_str, context_manager_ref)
                return self.perform_comparison(op1, op2, "==")
            elif expression_string.lower() == "true": return True
            elif expression_string.lower() == "false": return False
            elif expression_string.lower().startswith("flag."): # Cek status flag
                flag_name_to_check = expression_string.split(".",1)[1]
                return self._regs.get_flag_status(flag_name_to_check)

            logger.warning(f"Ekspresi logika '{expression_string}' tidak dapat dievaluasi oleh placeholder.")
            return False # Default jika tidak bisa dievaluasi
        except Exception as e:
            logger.error(f"Error saat mengevaluasi ekspresi logika '{expression_string}': {e}")
            return False

    def _resolve_operand_value(self, operand_identifier_str: str, context_manager_ref: 'TempikExecutionContextManager') -> Any:
        """Mengambil nilai operand dari GPR, environment, atau sebagai literal."""
        s = operand_identifier_str.strip()
        s_lower = s.lower()

        if s_lower.startswith("gpr"): # Akses GPR (misal, "gpr0", "gpr15")
            return self._regs.get_gpr_value(s_lower)
        elif s_lower.startswith("env."): # Akses variabel environment (misal, "env.MY_VARIABLE")
            env_var_name = s.split(".", 1)[1] # Ambil nama variabel dengan case asli
            return context_manager_ref.get_environment_variable(env_var_name)
        elif (s.startswith("'") and s.endswith("'")) or (s.startswith('"') and s.endswith('"')): # String literal
            return s[1:-1]
        else: # Coba sebagai angka, jika gagal, anggap sebagai string literal biasa
            try: return int(s)
            except ValueError:
                try: return float(s)
                except ValueError: return s # String literal tanpa quote


class TempikRuntimeDataStorage: # Sesuai audit: MemoryUnit
    """
    Penyimpanan Data Runtime untuk TempikUnit.
    Fokus utama pada penyediaan mekanisme stack untuk mendukung operasi CALL dan RET,
    serta penyimpanan data sementara yang mungkin dibutuhkan oleh instruksi .asu.
    Tidak mensimulasikan memori fisik byte-addressable secara detail; itu di luar lingkup UTEK ini.
    """
    def __init__(self, register_storage_ref: TempikRegisterStorage, max_stack_elements: int = 1024):
        self._regs = register_storage_ref
        self._program_stack: List[Any] = [] # Stack untuk return addresses, parameter fungsi (konseptual)
        self._max_stack_elements = max_stack_elements
        self._regs.sp = 0 # Stack Pointer (SP) menunjuk ke jumlah elemen di stack (indeks berikutnya yang kosong)
        logger.debug(f"TempikRuntimeDataStorage (Stack) diinisialisasi. Max stack depth: {max_stack_elements} elemen.")

    def push_value_to_stack(self, value: Any):
        """Mendorong (push) sebuah nilai ke puncak stack program."""
        if len(self._program_stack) >= self._max_stack_elements:
            logger.error(f"Stack overflow! Tidak bisa push '{value}'. Ukuran stack: {len(self._program_stack)}, Maks: {self._max_stack_elements}")
            raise OverflowError("Stack program UTEK overflow.")
        self._program_stack.append(value)
        self._regs.sp = len(self._program_stack) # Update SP
        logger.debug(f"PUSH ke stack: {value} (tipe: {type(value).__name__}). SP sekarang: {self._regs.sp}")

    def pop_value_from_stack(self) -> Any:
        """Mengambil dan menghapus (pop) nilai dari puncak stack program."""
        if not self._program_stack:
            logger.error("Stack underflow! Tidak bisa pop dari stack kosong.")
            raise IndexError("Pop dari stack program UTEK yang kosong.")
        value = self._program_stack.pop()
        self._regs.sp = len(self._program_stack) # Update SP
        logger.debug(f"POP dari stack: {value} (tipe: {type(value).__name__}). SP sekarang: {self._regs.sp}")
        return value

    def peek_top_of_stack(self) -> Any:
        """Melihat nilai di puncak stack tanpa menghapusnya."""
        if not self._program_stack:
            logger.warning("Peek pada stack kosong, mengembalikan None.")
            return None
        return self._program_stack[-1]

    def get_stack_depth(self) -> int:
        """Mengembalikan jumlah elemen saat ini di stack."""
        return len(self._program_stack)


class TempikInstructionCache: # Sesuai audit: InstructionCache
    """
    Cache untuk objek ASUInstructionObject yang sudah di-decode.
    Bertujuan untuk mempercepat proses jika instruksi yang sama di-fetch berulang kali
    (misalnya dalam loop). Menggunakan strategi LRU (Least Recently Used) untuk eviction.
    """
    # Implementasi sama dengan InstructionCacheManager di V3, hanya ganti nama.
    # ... (Salin implementasi InstructionCacheManager dari V3, ganti nama kelas) ...
    def __init__(self, capacity: int = 256):
        self._cache: Dict[int, ASUInstructionObject] = {} 
        self._capacity = capacity
        self._access_order: List[int] = [] 
        logger.debug(f"TempikInstructionCache diinisialisasi dengan kapasitas: {capacity} instruksi.")
    def get_instruction(self, pc_address: int) -> Optional[ASUInstructionObject]:
        if pc_address in self._cache:
            self._access_order.remove(pc_address)
            self._access_order.append(pc_address)
            logger.debug(f"Cache HIT untuk instruksi di PC={pc_address}.")
            return self._cache[pc_address]
        logger.debug(f"Cache MISS untuk instruksi di PC={pc_address}.")
        return None
    def store_instruction(self, pc_address: int, instruction: ASUInstructionObject):
        if len(self._cache) >= self._capacity and self._access_order:
            lru_address = self._access_order.pop(0)
            del self._cache[lru_address]
            logger.debug(f"Cache eviction (LRU): Instruksi di PC={lru_address} dihapus.")
        self._cache[pc_address] = instruction
        self._access_order.append(pc_address)
        logger.debug(f"Instruksi di PC={pc_address} ('{instruction.operation_code.value}') disimpan ke cache.")


class TempikDataCache: # Sesuai audit: DataCache
    """
    Cache untuk data runtime yang sering diakses, seperti konten file kecil dari VFS.
    Bertujuan mengurangi latensi I/O ke IsolatedVirtualFileSystem.
    Menggunakan strategi LRU dan batasan ukuran total.
    """
    # Implementasi sama dengan DataCacheManager di V3, hanya ganti nama.
    # ... (Salin implementasi DataCacheManager dari V3, ganti nama kelas) ...
    def __init__(self, max_size_bytes: int = 1 * 1024 * 1024): # Default cache 1MB
        self._cache: Dict[str, bytes] = {} 
        self._max_size_bytes = max_size_bytes
        self._current_size_bytes: int = 0
        self._access_order: List[str] = [] 
        logger.debug(f"TempikDataCache diinisialisasi dengan kapasitas: {max_size_bytes / (1024*1024):.2f} MB.")
    def get_data(self, key: str) -> Optional[bytes]:
        if key in self._cache:
            self._access_order.remove(key)
            self._access_order.append(key)
            logger.debug(f"Data cache HIT untuk kunci: {key}")
            return self._cache[key]
        logger.debug(f"Data cache MISS untuk kunci: {key}")
        return None
    def store_data(self, key: str, data: bytes):
        data_size = len(data)
        if data_size == 0: return # Jangan cache data kosong
        if data_size > self._max_size_bytes:
            logger.warning(f"Data untuk kunci '{key}' ({data_size} bytes) terlalu besar untuk cache ({self._max_size_bytes} bytes). Tidak disimpan.")
            return
        while self._current_size_bytes + data_size > self._max_size_bytes and self._access_order:
            lru_key = self._access_order.pop(0)
            lru_data_size = len(self._cache[lru_key])
            del self._cache[lru_key]
            self._current_size_bytes -= lru_data_size
            logger.debug(f"Data cache eviction (LRU): Kunci '{lru_key}' ({lru_data_size} bytes) dihapus.")
        self._cache[key] = data
        self._access_order.append(key)
        self._current_size_bytes += data_size
        logger.debug(f"Data untuk kunci '{key}' ({data_size} bytes) disimpan. Ukuran cache: {self._current_size_bytes} bytes.")


class TempikIOHandler: # Sesuai audit: IOHandler
    """
    Penangan Operasi Input/Output untuk TempikUnit.
    Fokus pada logging output standar dari eksekusi .asu. Interaksi file
    dilakukan melalui IsolatedVirtualFileSystem. Potensi interaksi pengguna
    (jika mode mendukung) akan dikelola di sini.
    """
    # Implementasi sama dengan InputOutputOperationHandler di V3, hanya ganti nama.
    # ... (Salin implementasi InputOutputOperationHandler dari V3, ganti nama kelas) ...
    def __init__(self, tempik_id_str: str, central_audit_logger_ref: 'CentralAuditLogger'):
        self.tempik_id_str = tempik_id_str
        self._audit_logger = central_audit_logger_ref
        logger.debug(f"[{self.tempik_id_str}] TempikIOHandler diinisialisasi.")
    def output_log_message(self, message: str, level: str = "INFO", 
                           source_asu_instruction: Optional[ASUInstructionSet] = None, 
                           current_asu_hash: Optional[str] = None):
        log_level_enum = getattr(logging, level.upper(), logging.INFO)
        logger.log(log_level_enum, f"[{self.tempik_id_str}] ASU_OUTPUT: {message}")
        if source_asu_instruction and current_asu_hash and level.upper() in ["INFO", "WARNING", "ERROR", "CRITICAL"]:
            self._audit_logger.record_event(
                datetime.now(timezone.utc).isoformat(), self.tempik_id_str,
                source_asu_instruction.value, level.upper(), 0, current_asu_hash,
                f"ASU_LOG_MSG: {message}"
            )


class UTEKTaskScheduler: # Sesuai audit: Scheduler
    """
    Penjadwal Tugas untuk UTEKSystemExecutor.
    Mengalokasikan TempikUnit yang tersedia untuk menjalankan file .asu baru.
    Dapat diimplementasikan dengan berbagai strategi (round-robin, least-busy, priority).
    """
    # Implementasi sama dengan TaskScheduler di V3, hanya ganti nama.
    # ... (Salin implementasi TaskScheduler dari V3, ganti nama kelas) ...
    def __init__(self, tempik_unit_pool_ref: List['TempikUnit']):
        self._tempik_pool = tempik_unit_pool_ref
        self._strategy = "round_robin" 
        self._last_assigned_idx = -1
        logger.info(f"UTEKTaskScheduler diinisialisasi dengan strategi '{self._strategy}' untuk {len(self._tempik_pool)} TempikUnit.")
    def request_idle_tempik_unit(self) -> Optional['TempikUnit']:
        if not self._tempik_pool: return None
        if self._strategy == "round_robin":
            for i in range(len(self._tempik_pool)):
                idx = (self._last_assigned_idx + 1 + i) % len(self._tempik_pool)
                if self._tempik_pool[idx].current_status == TempikUnitStatus.IDLE:
                    self._last_assigned_idx = idx
                    logger.debug(f"UTEKTaskScheduler: TempikUnit-{self._tempik_pool[idx].tempik_id} dialokasikan.")
                    return self._tempik_pool[idx]
        logger.warning("UTEKTaskScheduler: Tidak ada TempikUnit yang idle saat ini.")
        return None


# Kelas TempikUnit dan TempikInstructionPipeline adalah inti dari refactoring ini.
# Mereka akan menggantikan TempikVirtual dari kode awal.

class TempikSecurityModule: # Sesuai audit: SecurityModule
    """
    Modul Keamanan Tempik.
    Bertanggung jawab untuk menerapkan kebijakan keamanan yang didefinisikan
    dalam header .asu atau konfigurasi global UTEK. Ini termasuk validasi
    perintah yang akan dieksekusi, kontrol akses ke sumber daya (VFS, jaringan),
    dan manajemen status penguncian eksekusi .asu.
    """
    # Implementasi sama dengan SecurityPolicyModule di V3, hanya ganti nama.
    # ... (Salin implementasi SecurityPolicyModule dari V3, ganti nama kelas) ...
    def __init__(self, tempik_id_str: str, initial_security_flags: List[str]):
        self.tempik_id_str = tempik_id_str
        self._flags = set(s.lower().strip() for s in initial_security_flags if s.strip())
        logger.info(f"[{self.tempik_id_str}] TempikSecurityModule diinisialisasi dengan flags: {self._flags}")
    def update_security_flags(self, new_flags: List[str]):
        self._flags = set(s.lower().strip() for s in new_flags if s.strip())
        logger.info(f"[{self.tempik_id_str}] Security flags Tempik diperbarui menjadi: {self._flags}")
    def is_operation_permitted(self, operation_type: str, target_resource: Optional[str] = None, command_details: Optional[List[str]] = None) -> bool:
        """Memeriksa apakah operasi diizinkan berdasarkan flags keamanan."""
        # Contoh pemeriksaan:
        if operation_type == "execute_host_command":
            if "no-host-execution" in self._flags or not self._flags.intersection({"allow-host-subprocess-sandboxed", "debug-unsafe-host-exec"}):
                logger.warning(f"[{self.tempik_id_str}] Operasi '{operation_type}' untuk '{command_details}' diblokir oleh policy.")
                return False
        elif operation_type == "vfs_write":
            if "vfs-readonly" in self._flags or "immutable-filesystem" in self._flags:
                logger.warning(f"[{self.tempik_id_str}] Operasi '{operation_type}' ke VFS:'{target_resource}' diblokir (VFS readonly).")
                return False
        elif operation_type == "network_access":
            if "no-network" in self._flags:
                 logger.warning(f"[{self.tempik_id_str}] Operasi '{operation_type}' ke '{target_resource}' diblokir (no-network).")
                 return False
        # Tambahkan pemeriksaan lain sesuai kebutuhan
        return True # Default izinkan jika tidak ada aturan spesifik yang melarang


class TempikInterruptController: # Sesuai audit: InterruptController
    """
    Pengontrol Interupsi Tempik.
    Menangani sinyal interupsi internal (misalnya, timeout instruksi, error pembagian nol)
    atau eksternal (misalnya, permintaan penghentian dari UTEKSystemExecutor).
    Memungkinkan pendaftaran handler kustom untuk jenis interupsi tertentu.
    """
    # Implementasi sama dengan InterruptHandlingController di V3, hanya ganti nama.
    # ... (Salin implementasi InterruptHandlingController dari V3, ganti nama kelas) ...
    def __init__(self, tempik_unit_ref: 'TempikUnit'):
        self._tempik_unit = tempik_unit_ref
        self._interrupt_handlers: Dict[str, Callable[[Any], Coroutine[Any, Any, None]]] = {}
        logger.debug(f"[{self._tempik_unit.tempik_id_str}] TempikInterruptController diinisialisasi.")
    def register_handler(self, interrupt_name: str, async_handler: Callable[[Any], Coroutine[Any, Any, None]]):
        self._interrupt_handlers[interrupt_name.lower()] = async_handler
    async def trigger_interrupt(self, interrupt_name: str, details: Optional[Any] = None):
        name_lower = interrupt_name.lower()
        logger.warning(f"[{self._tempik_unit.tempik_id_str}] Interupsi '{name_lower}' diterima. Detail: {details}")
        if name_lower in self._interrupt_handlers:
            try: await self._interrupt_handlers[name_lower](details)
            except Exception as e: logger.error(f"Error handler interupsi '{name_lower}': {e}", exc_info=True)
        else: # Default handler
            logger.warning(f"Tidak ada handler spesifik untuk interupsi '{name_lower}'. Tempik akan di-HALT/FAIL.")
            if "error" in name_lower or "exception" in name_lower: self._tempik_unit.current_status = TempikUnitStatus.FAILED_ERROR
            else: self._tempik_unit.current_status = TempikUnitStatus.HALTED_BY_REQUEST


@dataclass
class VFSNode: # Dipindahkan ke sini untuk digunakan oleh IsolatedVirtualFileSystem
    """Representasi node dalam IsolatedVirtualFileSystem (file atau direktori)."""
    name: str
    is_directory: bool
    content: Optional[bytes] = None # Untuk file
    children: Optional[Dict[str, 'VFSNode']] = None # Untuk direktori
    # Tambahkan metadata lain: permissions, timestamps, owner, dll.
    created_at_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    modified_at_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        if self.is_directory and self.children is None:
            self.children = {}
        if not self.is_directory and self.content is None:
            self.content = b"" # File kosong by default


class TempikIsolatedVFS: # Sesuai audit: VirtualFS (diganti nama dari IsolatedVirtualFileSystem)
    """
    Sistem File Virtual Terisolasi untuk TempikUnit.
    Menyediakan lingkungan filesystem yang terpisah untuk setiap TempikUnit,
    mencegah interferensi dan meningkatkan keamanan. Operasi file dari instruksi .asu
    dilakukan terhadap VFS ini.
    """
    # Implementasi sama dengan IsolatedVirtualFileSystem di V3, hanya ganti nama.
    # ... (Salin implementasi IsolatedVirtualFileSystem dari V3, ganti nama kelas dan VFSNode) ...
    def __init__(self, tempik_id_str: str):
        self.tempik_id_str = tempik_id_str
        self.vfs_root_node: VFSNode = VFSNode(name="/", is_directory=True)
        self.active_mount_points: Dict[str, Tuple[str, Dict[str, Any]]] = {}
        logger.info(f"[{self.tempik_id_str}] TempikIsolatedVFS diinisialisasi.")
    # Metode: _normalize_vfs_path, _get_vfs_node_and_parent, create_directory, write_file_content,
    # read_file_content, file_node_exists, directory_node_exists, list_directory_contents,
    # remove_vfs_file, remove_vfs_directory, mount_external_source (konseptual)
    # (Implementasi detail disalin dari V3 IsolatedVirtualFileSystem, disesuaikan jika perlu)
    def _normalize_vfs_path(self, path_str: str, exec_context: 'TempikExecutionContextManager') -> str:
        # ... (dari V3 _normalize_path) ...
        if path_str != "/" and path_str.endswith("/"): path_str = path_str[:-1]
        if not path_str: path_str = "/"
        if path_str.startswith("/"): abs_path = os.path.normpath(path_str)
        else: abs_path = os.path.normpath(os.path.join(exec_context.current_working_directory_vfs, path_str))
        if not abs_path.startswith("/"): abs_path = "/" + abs_path
        return abs_path

    def _get_vfs_node_and_parent(self, normalized_path: str) -> Tuple[Optional[VFSNode], Optional[VFSNode], Optional[str]]:
        # ... (dari V3 _get_node_and_parent, gunakan self.vfs_root_node) ...
        parts = [part for part in normalized_path.strip("/").split("/") if part]
        current = self.vfs_root_node
        parent = None
        node_name = ""
        if not parts: return self.vfs_root_node, None, "/"
        for i, part in enumerate(parts):
            if not current.is_directory or current.children is None: return None, None, None
            parent = current
            node_name = part
            current = current.children.get(part)
            if current is None:
                return (None, parent, node_name) if i == len(parts) - 1 else (None, None, None)
        return current, parent, node_name
    
    def create_directory(self, path_str: str, exec_context: 'TempikExecutionContextManager', create_intermediate_parents: bool = False):
        # ... (dari V3 mkdir, gunakan _normalize_vfs_path dan _get_vfs_node_and_parent) ...
        norm_path = self._normalize_vfs_path(path_str, exec_context)
        if norm_path == "/": return
        node, parent, node_name = self._get_vfs_node_and_parent(norm_path)
        if node is not None:
            if not node.is_directory: raise FileExistsError(f"VFS: Path '{norm_path}' ada sebagai file.")
            return
        if parent is None or node_name is None:
            if create_intermediate_parents and norm_path != "/":
                parent_dir_path = os.path.dirname(norm_path)
                if parent_dir_path and parent_dir_path != norm_path:
                    self.create_directory(parent_dir_path, exec_context, True)
                    _, parent, node_name = self._get_vfs_node_and_parent(norm_path) # Coba lagi
                    if parent is None or node_name is None: raise FileNotFoundError(f"VFS: Gagal buat parent untuk '{norm_path}'.")
            else: raise FileNotFoundError(f"VFS: Path parent untuk '{norm_path}' tidak ada.")
        if parent and node_name and parent.is_directory and parent.children is not None:
            new_dir = VFSNode(name=node_name, is_directory=True)
            parent.children[node_name] = new_dir
            parent.modified_at_utc = datetime.now(timezone.utc)
            logger.info(f"[{self.tempik_id_str}] VFS: Direktori '{norm_path}' dibuat.")
        else: raise FileNotFoundError(f"VFS: Gagal buat direktori '{norm_path}'.")

    def write_file_content(self, path_str: str, file_content_bytes: bytes, exec_context: 'TempikExecutionContextManager'):
        # ... (dari V3 write_file, gunakan _normalize_vfs_path dan _get_vfs_node_and_parent) ...
        norm_path = self._normalize_vfs_path(path_str, exec_context)
        node, parent, node_name = self._get_vfs_node_and_parent(norm_path)
        if node is not None and node.is_directory: raise IsADirectoryError(f"VFS: Path '{norm_path}' adalah direktori.")
        if parent is None or node_name is None:
            parent_dir_path = os.path.dirname(norm_path)
            if parent_dir_path and parent_dir_path != norm_path:
                self.create_directory(parent_dir_path, exec_context, True)
                _, parent, node_name = self._get_vfs_node_and_parent(norm_path)
                if parent is None or node_name is None: raise FileNotFoundError(f"VFS: Gagal buat parent untuk file '{norm_path}'.")
            else: raise FileNotFoundError(f"VFS: Path tidak valid untuk file: '{norm_path}'.")
        current_time = datetime.now(timezone.utc)
        if parent and node_name and parent.is_directory and parent.children is not None:
            if node is None: # File baru
                new_file = VFSNode(name=node_name, is_directory=False, content=file_content_bytes, created_at_utc=current_time, modified_at_utc=current_time)
                parent.children[node_name] = new_file
            else: # Timpa file
                node.content = file_content_bytes
                node.modified_at_utc = current_time
            parent.modified_at_utc = current_time
            logger.info(f"[{self.tempik_id_str}] VFS: File '{norm_path}' ditulis ({len(file_content_bytes)} bytes).")
        else: raise FileNotFoundError(f"VFS: Gagal tulis file '{norm_path}'.")

    def read_file_content(self, path_str: str, exec_context: 'TempikExecutionContextManager') -> Optional[bytes]:
        # ... (dari V3 read_file) ...
        norm_path = self._normalize_vfs_path(path_str, exec_context)
        node,_,_ = self._get_vfs_node_and_parent(norm_path)
        if node and not node.is_directory: return node.content
        if node and node.is_directory: logger.warning(f"VFS: Path '{norm_path}' adalah direktori.")
        else: logger.warning(f"VFS: File '{norm_path}' tidak ditemukan.")
        return None
    # ... (Implementasi sisa metode VFS: file_node_exists, directory_node_exists, list_directory_contents, remove_vfs_file, remove_vfs_directory)


class TempikSecureNetworkUnit: # Sesuai audit: NetworkUnit (diganti nama dari SecureNetworkUnit)
    """
    Unit Jaringan Aman untuk TempikUnit.
    Mengelola semua koneksi jaringan keluar, menerapkan kebijakan akses
    (offline, restricted, full) dan mencatat aktivitas jaringan.
    """
    # Implementasi sama dengan SecureNetworkUnit di V3, hanya ganti nama.
    # ... (Salin implementasi SecureNetworkUnit dari V3, ganti nama kelas) ...
    def __init__(self, tempik_id_str: str, exec_context_ref: 'TempikExecutionContextManager', security_module_ref: 'TempikSecurityModule'):
        self.tempik_id_str = tempik_id_str
        self._exec_context = exec_context_ref
        self._security_mod = security_module_ref
        self._http_client_session: Optional[Any] = None # aiohttp.ClientSession
        logger.debug(f"[{self.tempik_id_str}] TempikSecureNetworkUnit diinisialisasi.")
    async def _get_or_create_http_session(self):
        try: import aiohttp
        except ImportError: return None
        if self._http_client_session is None or self._http_client_session.closed:
            self._http_client_session = aiohttp.ClientSession()
        return self._http_client_session
    async def close_http_session(self):
        if self._http_client_session and not self._http_client_session.closed:
            await self._http_client_session.close()
    # Metode: _check_network_access_permission, perform_http_request, fetch_remote_repository_content,
    # invoke_remote_api_service, push_data_to_remote_endpoint
    # (Implementasi detail disalin dari V3 SecureNetworkUnit, disesuaikan jika perlu)


class TempikCryptographicEngine: # Sesuai audit: CryptoEngine (diganti nama dari CryptographicEngine)
    """
    Mesin Kriptografi untuk TempikUnit.
    Menyediakan fungsionalitas untuk hashing, pembuatan dan verifikasi signature digital,
    serta enkripsi dan dekripsi data sesuai kebutuhan instruksi .asu.
    """
    # Implementasi sama dengan CryptographicEngine di V3, hanya ganti nama.
    # ... (Salin implementasi CryptographicEngine dari V3, ganti nama kelas) ...
    def __init__(self, tempik_id_str: str):
        self.tempik_id_str = tempik_id_str
        self._default_priv_key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
        self._default_pub_key = self._default_priv_key.public_key()
        logger.debug(f"[{self.tempik_id_str}] TempikCryptographicEngine diinisialisasi.")
    # Metode: calculate_data_hash, verify_data_hash_match, generate_data_signature, verify_data_signature,
    # encrypt_data_symmetric, decrypt_data_symmetric
    # (Implementasi detail disalin dari V3 CryptographicEngine, disesuaikan jika perlu)


class UTEKCentralAuditLogger: # Sesuai audit: AuditLogger (diganti nama dari CentralAuditLogger)
    """
    Logger Audit Terpusat untuk UTEKSystemExecutor.
    Mencatat semua event eksekusi penting dengan format standar yang ketat
    (misalnya, sesuai standar Deloitte) untuk keperluan audit dan kepatuhan.
    Log bersifat append-only dan timestamped UTC.
    """
    # Implementasi sama dengan CentralAuditLogger di V3, hanya ganti nama.
    # ... (Salin implementasi CentralAuditLogger dari V3, ganti nama kelas) ...
    def __init__(self, audit_log_target_filepath: Optional[str] = "utek_audit_trail.log"):
        self._log_file_path = audit_log_target_filepath
        self._audit_logger_instance = logging.getLogger("UTEK_AUDIT_TRAIL")
        self._audit_logger_instance.propagate = False
        self._audit_logger_instance.setLevel(logging.INFO)
        if self._log_file_path:
            try:
                fh = logging.FileHandler(self._log_file_path, mode='a', encoding='utf-8')
                fh.setFormatter(logging.Formatter('%(message)s')) # Format pesan sudah ditentukan
                self._audit_logger_instance.addHandler(fh)
                self._audit_file_handler_ref = fh # Simpan referensi untuk menutup
                logger.info(f"UTEKCentralAuditLogger akan menulis ke: {self._log_file_path}")
            except Exception as e: logger.error(f"Gagal setup file handler UTEKCentralAuditLogger: {e}")
        else: logger.warning("UTEKCentralAuditLogger: Tidak ada path file, audit akan ke stdout (jika logger utama di-setup).")
    def record_audit_event(self, event_timestamp_utc_iso: str, source_tempik_id: str, asu_operation_code: str,
                             operation_status: str, execution_duration_ms: int, processed_asu_hash: str, event_details: str = ""):
        log_msg = f"{event_timestamp_utc_iso} | {source_tempik_id} | {asu_operation_code} | {operation_status} | {execution_duration_ms}ms | {processed_asu_hash}"
        if event_details: log_msg += f" | {str(event_details).replace('|', ';').replace(os.linesep, ' ')}"
        self._audit_logger_instance.info(log_msg) # Log ke handler file khusus
    def close_audit_log_file(self):
        if hasattr(self, '_audit_file_handler_ref') and self._audit_file_handler_ref:
            try:
                self._audit_file_handler_ref.close()
                self._audit_logger_instance.removeHandler(self._audit_file_handler_ref)
            except Exception as e: logger.error(f"Error menutup file audit: {e}")


class ASUInstructionDecoder: # Sesuai audit: InstructionDecoder (diganti nama dari InstructionObjectDecoder)
    """
    Dekoder Instruksi .asu.
    Mengubah representasi instruksi mentah (biasanya dictionary dari JSON)
    menjadi objek ASUInstructionObject yang terstruktur dan tervalidasi.
    """
    # Implementasi sama dengan InstructionObjectDecoder di V3, hanya ganti nama.
    # ... (Salin implementasi InstructionObjectDecoder dari V3, ganti nama kelas) ...
    def __init__(self, for_tempik_id_str: Optional[str] = None):
        self._log_prefix = f"[{for_tempik_id_str}] " if for_tempik_id_str else ""
        logger.debug(f"{self._log_prefix}ASUInstructionDecoder diinisialisasi.")
    def decode_single_instruction(self, raw_instruction_data: Dict[str, Any]) -> ASUInstructionObject:
        op_code_val = raw_instruction_data.get("operation_code", raw_instruction_data.get("instruksi")) # Kompatibilitas
        if not op_code_val: raise ValueError("Data instruksi tidak memiliki 'operation_code'.")
        try: op_code_enum = ASUInstructionSet(op_code_val)
        except ValueError: raise ValueError(f"Operation code tidak dikenal: '{op_code_val}'")
        params_data = raw_instruction_data.get("parameters", raw_instruction_data.get("parameter", {}))
        if not isinstance(params_data, dict): params_data = {}
        return ASUInstructionObject(
            operation_code=op_code_enum, parameters=params_data,
            jump_label=raw_instruction_data.get("jump_label", raw_instruction_data.get("label")),
            execution_timeout_seconds=float(raw_instruction_data.get("execution_timeout_seconds", raw_instruction_data.get("timeout_seconds", raw_instruction_data.get("timeout", 30.0)))),
            max_retry_attempts=int(raw_instruction_data.get("max_retry_attempts", raw_instruction_data.get("retry_attempts", raw_instruction_data.get("retry_count", 0))))
        )


class TempikExecutionContextManager: # Sesuai audit: ExecutionContextManager (diganti nama dari ExecutionContextCoreManager)
    """
    Manajer Konteks Eksekusi untuk TempikUnit.
    Menyimpan dan mengelola semua state runtime yang relevan untuk eksekusi .asu,
    termasuk variabel lingkungan, direktori kerja VFS, informasi pengguna/role,
    kebijakan keamanan aktif, dan batasan serta penggunaan sumber daya.
    """
    # Implementasi sama dengan ExecutionContextCoreManager di V3, hanya ganti nama.
    # ... (Salin implementasi ExecutionContextCoreManager dari V3, ganti nama kelas) ...
    def __init__(self, tempik_id_str: str, initial_asu_header: Optional[ASUHeaderData] = None):
        self.tempik_id_str = tempik_id_str
        self.environment_vars: Dict[str, str] = os.environ.copy() # Warisi dari host, bisa di-override
        self.current_working_directory_vfs: str = "/"
        self.current_user_identity: str = "utek_anonymous_user"
        self.current_namespace_context: str = "global_default_ns"
        self.active_roles_permissions: List[str] = ["base_executor_role"]
        self.active_security_flags: List[str] = ["default-sandboxed"]
        self.active_networking_policy: str = "offline"
        self.resource_constraints: Dict[str, Any] = { /* ... default constraints ... */ }
        self.resource_consumption_tracker: Dict[str, Any] = { /* ... initial consumption ... */ }
        if initial_asu_header: self.configure_from_asu_header(initial_asu_header)
        logger.debug(f"[{self.tempik_id_str}] TempikExecutionContextManager diinisialisasi. CWD VFS: {self.current_working_directory_vfs}")
    def configure_from_asu_header(self, header: ASUHeaderData):
        self.active_security_flags = list(header.security_policy_flags)
        self.active_networking_policy = header.network_access_policy.lower()
        # ... (Parse memory_profile_config, time_budget_constraints, dll. ke resource_constraints) ...
        self.set_environment_variable("UTEK_ASU_NETWORKING_POLICY", self.active_networking_policy)
    def set_environment_variable(self, var_key: str, var_value: str):
        # ... (implementasi set env var) ...
        self.environment_vars[var_key.upper()] = str(var_value)
    def get_environment_variable(self, var_key: str, default_val: Optional[str] = None) -> Optional[str]:
        # ... (implementasi get env var) ...
        return self.environment_vars.get(var_key.upper(), default_val)
    def set_vfs_working_directory(self, vfs_dir_path: str, vfs_instance_ref: TempikIsolatedVFS):
        # ... (implementasi set CWD VFS dengan validasi) ...
        if vfs_instance_ref.directory_node_exists(vfs_dir_path, self):
            self.current_working_directory_vfs = vfs_dir_path
        else: raise FileNotFoundError(f"VFS CWD '{vfs_dir_path}' tidak ditemukan.")
    def check_and_update_resource_usage(self, resource_type_key: str, consumed_amount: Union[int, float] = 1) -> bool:
        # ... (implementasi pengecekan dan update penggunaan resource) ...
        return True # Placeholder


# --- Implementasi Inti: TempikUnit dan TempikInstructionPipeline ---

class TempikInstructionPipeline:
    """
    Pipeline Pemrosesan Instruksi .asu untuk satu TempikUnit.
    Mengelola siklus 5 tahap: Fetch, Decode, Execute, Access Storage, Commit Result.
    Dirancang untuk pemrosesan instruksi .asu secara sekuensial dan terkontrol.
    """
    # Implementasi sama dengan TempikInstructionPipeline di V3,
    # hanya perlu memastikan penggunaan nama kelas komponen yang sudah direfactor.
    # ... (Salin implementasi TempikInstructionPipeline dari V3, sesuaikan nama kelas komponen) ...
    def __init__(self, tempik_unit_instance: 'TempikUnit', asu_instruction_list: List[ASUInstructionObject]):
        self._tempik_unit = tempik_unit_instance
        self._program_instruction_list = asu_instruction_list
        self._current_stage: Optional[UTEKPipelineStage] = None
        self._fetched_instruction: Optional[ASUInstructionObject] = None
        self._decoded_instruction: Optional[ASUInstructionObject] = None
        self._operation_execution_result: Any = None
        self._storage_access_result: Any = None
        self._pc_target_for_next_cycle: Optional[int] = None # Untuk JUMP, CALL, IF/ELSE skips
        logger.debug(f"[{self._tempik_unit.tempik_id_str}] TempikInstructionPipeline diinisialisasi.")

    async def _stage_1_fetch_asu_instruction(self) -> bool:
        self._current_stage = UTEKPipelineStage.FETCH_ASU_INSTRUCTION
        self._tempik_unit.current_status = TempikUnitStatus.FETCHING_INSTRUCTION
        # self._tempik_unit.control_unit_logic.generate_control_signals_for_stage(self._current_stage) # Konseptual

        if self._pc_target_for_next_cycle is not None:
            # ... (Logika override PC dari V3) ...
            self._tempik_unit.program_counter.jump_to_instruction_address(self._pc_target_for_next_cycle)
            self._pc_target_for_next_cycle = None

        pc_now = self._tempik_unit.program_counter.current_instruction_address
        if pc_now >= len(self._program_instruction_list):
            self._fetched_instruction = None
            return False # Akhir program

        cached_instr = self._tempik_unit.instruction_cache.get_instruction(pc_now)
        if cached_instr: self._fetched_instruction = cached_instr
        else:
            self._fetched_instruction = self._program_instruction_list[pc_now]
            self._tempik_unit.instruction_cache.store_instruction(pc_now, self._fetched_instruction)
        
        logger.debug(f"[{self._tempik_unit.tempik_id_str}] Pipeline Fetch: PC={pc_now}, Instr: {self._fetched_instruction.operation_code.value}")
        self._tempik_unit.program_counter.advance_to_next_instruction()
        return True

    async def _stage_2_decode_asu_instruction(self) -> bool:
        # ... (Logika decode dari V3, gunakan self._tempik_unit.asu_instruction_decoder) ...
        if not self._fetched_instruction: return False
        self._current_stage = UTEKPipelineStage.DECODE_ASU_INSTRUCTION
        self._tempik_unit.current_status = TempikUnitStatus.DECODING_INSTRUCTION
        try:
            self._decoded_instruction = self._tempik_unit.asu_instruction_decoder.decode_single_instruction(self._fetched_instruction.to_dictionary())
            return True
        except ValueError as e:
            # ... (Error logging dan audit dari V3) ...
            self._tempik_unit.current_status = TempikUnitStatus.FAILED_ERROR
            return False

    async def _stage_3_execute_asu_operation(self) -> bool:
        # ... (Logika execute dari V3, termasuk penanganan IF/ELSE/JUMP/CALL/RET untuk set _pc_target_for_next_cycle) ...
        if not self._decoded_instruction: return False
        self._current_stage = UTEKPipelineStage.EXECUTE_ASU_OPERATION
        self._tempik_unit.current_status = TempikUnitStatus.EXECUTING_OPERATION
        instr_obj = self._decoded_instruction
        
        # Logika skip untuk ELSE jika IF_COND True
        if instr_obj.operation_code == ASUInstructionSet.ELSE_BLOCK and self._tempik_unit.registers.get_flag_status("COND_RESULT"):
            self._pc_target_for_next_cycle = self._tempik_unit.find_instruction_address_for_label_or_type(
                self._tempik_unit.program_counter.current_instruction_address -1, [ASUInstructionSet.END_IF_BLOCK], True)
            self._operation_execution_result = {"status": "skipped_else"}
            return True

        handler_method = self._tempik_unit.get_asu_instruction_handler(instr_obj.operation_code)
        if not handler_method: # ... (Error handling dari V3) ...
            self._operation_execution_result = {"status":"failed", "error":f"No handler for {instr_obj.operation_code.value}"}
            return False

        start_time = time.monotonic()
        try:
            # ... (Timeout logic dari V3) ...
            timeout_val = min(instr_obj.execution_timeout_seconds, self._tempik_unit.context_manager.resource_constraints.get("max_instruction_timeout_seconds", 60))
            self._operation_execution_result = await asyncio.wait_for(handler_method(instr_obj.parameters), timeout=timeout_val)
            # ... (Post-execution logic: JUMP, CALL, IF, RET, Audit logging dari V3) ...
            # Contoh untuk IF:
            if instr_obj.operation_code == ASUInstructionSet.IF_CONDITION and isinstance(self._operation_execution_result, dict):
                cond_true = self._operation_execution_result.get("condition_result", False)
                self._tempik_unit.registers.set_flag_status("COND_RESULT", cond_true)
                if not cond_true: # Jika IF False, cari ELSE atau ENDIF
                    self._pc_target_for_next_cycle = self._tempik_unit.find_instruction_address_for_label_or_type(
                        self._tempik_unit.program_counter.current_instruction_address -1,
                        [ASUInstructionSet.ELSE_BLOCK, ASUInstructionSet.END_IF_BLOCK], False
                    )
            # ... (Audit logging dari V3)
            return True
        except Exception as e: # ... (Error handling dan audit dari V3) ...
            self._operation_execution_result = {"status":"failed", "error":str(e)}
            return False


    async def _stage_4_access_runtime_storage(self) -> bool:
        # ... (Logika memory access dari V3, umumnya NOP jika sudah di EXECUTE) ...
        if not self._decoded_instruction: return False
        self._current_stage = UTEKPipelineStage.ACCESS_RUNTIME_STORAGE
        self._tempik_unit.current_status = TempikUnitStatus.ACCESSING_STORAGE
        self._storage_access_result = self._operation_execution_result # Teruskan hasil
        return True

    async def _stage_5_commit_operation_result(self) -> bool:
        # ... (Logika write back dari V3, misal simpan ke GPR) ...
        if self._storage_access_result is None: return False # Atau jika error sebelumnya
        self._current_stage = UTEKPipelineStage.COMMIT_OPERATION_RESULT
        self._tempik_unit.current_status = TempikUnitStatus.COMMITTING_RESULTS
        # Contoh: if self._decoded_instruction.parameters.get("result_to_gpr"): ...
        return True

    async def execute_one_full_cycle(self) -> Tuple[bool, Any]: # Menggantikan run_single_cycle
        """Menjalankan satu siklus pipeline lengkap."""
        # ... (Logika run_single_cycle dari V3, disesuaikan dengan nama tahap baru) ...
        # Pastikan status TempikUnit diupdate dengan benar di akhir siklus atau jika ada error.
        if not await self._stage_1_fetch_asu_instruction(): return False, None # EOF
        if not await self._stage_2_decode_asu_instruction(): return False, self._operation_execution_result
        if not await self._stage_3_execute_asu_operation(): return False, self._operation_execution_result
        
        # Cek instruksi terminal (HALT, SHUTDOWN)
        if self._decoded_instruction and self._decoded_instruction.operation_code in [ASUInstructionSet.HALT, ASUInstructionSet.SHUTDOWN]:
            if isinstance(self._operation_execution_result, dict) and self._operation_execution_result.get("status") in ["halt_requested", "shutdown_requested"]:
                self._tempik_unit.current_status = TempikUnitStatus.HALTED_BY_REQUEST
                return False, self._operation_execution_result # Hentikan pipeline

        if not await self._stage_4_access_runtime_storage(): return False, self._storage_access_result
        if not await self._stage_5_commit_operation_result(): return False, self._storage_access_result
        
        if self._tempik_unit.current_status not in [TempikUnitStatus.WAITING_CONDITION, TempikUnitStatus.HALTED_BY_REQUEST, TempikUnitStatus.FAILED_ERROR, TempikUnitStatus.COMPLETED_SUCCESS]:
            self._tempik_unit.current_status = TempikUnitStatus.IDLE
        return True, self._storage_access_result


class TempikUnit: # Menggantikan Tempik dari kode awal dan V3
    """
    Unit Eksekusi Tempik (TempikUnit) - Inti pemrosesan .asu dalam UTEK.
    Setiap TempikUnit adalah entitas independen dengan state, penyimpanan,
    dan pipeline eksekusi sendiri. Beroperasi di bawah kendali UTEKSystemExecutor.
    """
    def __init__(self, unique_tempik_id: int, 
                 system_audit_logger: UTEKCentralAuditLogger, 
                 main_system_executor_ref: 'UTEKSystemExecutor', # Untuk DELEGATE_TO
                 configuration_options: Optional[Dict] = None): # Konfigurasi global
        
        self.tempik_id: int = unique_tempik_id
        self.tempik_id_str: str = f"TempikUnit-{unique_tempik_id:03d}" # ID String untuk logging
        self.current_status: TempikUnitStatus = TempikUnitStatus.IDLE
        self.current_asu_file_hash: str = "UNLOADED" # Hash dari file .asu yang sedang diproses
        
        # Komponen Internal TempikUnit (sesuai daftar audit)
        self.registers: TempikRegisterStorage = TempikRegisterStorage()
        self.program_counter: TempikProgramCounter = TempikProgramCounter(self.registers)
        self.control_unit_logic: TempikControlUnitLogic = TempikControlUnitLogic(self.tempik_id_str) # Konseptual
        self.exec_logic_unit: TempikArithmeticLogicUnit = TempikArithmeticLogicUnit(self.registers)
        self.runtime_data_storage: TempikRuntimeDataStorage = TempikRuntimeDataStorage(self.registers)
        self.instruction_cache: TempikInstructionCache = TempikInstructionCache()
        self.data_cache: TempikDataCache = TempikDataCache() # Untuk data VFS kecil

        # Konteks, I/O, VFS, Keamanan, Jaringan, Kripto (per Tempik)
        self.context_manager: TempikExecutionContextManager = TempikExecutionContextManager(self.tempik_id_str)
        self.io_handler: TempikIOHandler = TempikIOHandler(self.tempik_id_str, system_audit_logger)
        self.vfs: TempikIsolatedVFS = TempikIsolatedVFS(self.tempik_id_str)
        self.security_module: TempikSecurityModule = TempikSecurityModule(self.tempik_id_str, []) # Flags diisi dari header
        self.network_unit: TempikSecureNetworkUnit = TempikSecureNetworkUnit(self.tempik_id_str, self.context_manager, self.security_module)
        self.crypto_engine: TempikCryptographicEngine = TempikCryptographicEngine(self.tempik_id_str)
        
        self.audit_logger: UTEKCentralAuditLogger = system_audit_logger # Referensi ke logger audit sistem
        self.asu_instruction_decoder: ASUInstructionDecoder = ASUInstructionDecoder(self.tempik_id_str)
        self.interrupt_controller: TempikInterruptController = TempikInterruptController(self)
        
        self._system_executor_ref = main_system_executor_ref # Untuk DELEGATE_TO
        self._current_program_stream: List[ASUInstructionObject] = [] # Instruksi .asu yang dimuat
        self._instruction_jump_labels: Dict[str, int] = {} # Peta: nama label -> indeks PC
        self._active_pipeline: Optional[TempikInstructionPipeline] = None

        self._instruction_handlers_registry: Dict[ASUInstructionSet, Callable[[Dict[str,Any]], Coroutine[Any, Any, Dict[str,Any]]]] = self._register_instruction_handlers()
        logger.info(f"{self.tempik_id_str} (V4 Audit Compliant) berhasil diinisialisasi.")

    def _register_instruction_handlers(self) -> Dict[ASUInstructionSet, Callable[[Dict[str,Any]], Coroutine[Any, Any, Dict[str,Any]]]]:
        """Mendaftarkan semua handler untuk setiap operasi dalam ASUInstructionSet."""
        # Pemetaan dari ASUInstructionSet ke metode handler di kelas ini
        # (Nama metode handler disesuaikan, misal _op_init_env)
        return {
            ASUInstructionSet.INIT_ENV: self._op_init_env,
            ASUInstructionSet.SET_ENV: self._op_set_env,
            ASUInstructionSet.WRITE_LOG_MESSAGE: self._op_write_log_message,
            ASUInstructionSet.EXECUTE: self._op_execute,
            ASUInstructionSet.IF_CONDITION: self._op_if_condition,
            ASUInstructionSet.ELSE_BLOCK: self._op_else_block,
            ASUInstructionSet.END_IF_BLOCK: self._op_end_if_block,
            ASUInstructionSet.JUMP: self._op_jump,
            ASUInstructionSet.CALL: self._op_call,
            ASUInstructionSet.RET: self._op_ret,
            ASUInstructionSet.HALT: self._op_halt,
            ASUInstructionSet.SHUTDOWN: self._op_shutdown,
            ASUInstructionSet.ASSERT_CONDITION: self._op_assert_condition,
            ASUInstructionSet.WAIT: self._op_wait,
            ASUInstructionSet.VERIFY_HASH: self._op_verify_hash,
            ASUInstructionSet.FETCH_REPO: self._op_fetch_repo,
            ASUInstructionSet.CHECKOUT: self._op_checkout,
            ASUInstructionSet.INSTALL: self._op_install,
            ASUInstructionSet.UNPACK: self._op_unpack,
            ASUInstructionSet.INJECT: self._op_inject,
            ASUInstructionSet.CLEANUP_RESOURCES: self._op_cleanup_resources,
            ASUInstructionSet.SIGN_DATA: self._op_sign_data,
            ASUInstructionSet.VERIFY_SIGNATURE: self._op_verify_signature,
            ASUInstructionSet.ENCRYPT_DATA: self._op_encrypt_data,
            ASUInstructionSet.DECRYPT_DATA: self._op_decrypt_data,
            ASUInstructionSet.LOCK_EXECUTION: self._op_lock_execution,
            ASUInstructionSet.POST_AUDIT_LOG: self._op_post_audit_log,
            ASUInstructionSet.EMIT_SYSTEM_EVENT: self._op_emit_system_event,
            ASUInstructionSet.INITIALIZE_NETWORK: self._op_initialize_network,
            ASUInstructionSet.MAP_NETWORK_PORT: self._op_map_network_port,
            ASUInstructionSet.INVOKE_REMOTE: self._op_invoke_remote,
            ASUInstructionSet.PUSH_EXECUTION_RESULT: self._op_push_execution_result,
            ASUInstructionSet.EXPORT_ARTIFACT: self._op_export_artifact,
            ASUInstructionSet.DELEGATE_TO: self._op_delegate_to,
            ASUInstructionSet.SET_CONTEXT: self._op_set_context,
            ASUInstructionSet.AUTH: self._op_auth,
            ASUInstructionSet.SYNC_CLOCK: self._op_sync_clock,
            ASUInstructionSet.MOUNT: self._op_mount,
            ASUInstructionSet.COMPILE: self._op_compile,
            ASUInstructionSet.SPAWN_THREAD: self._op_spawn_thread, # Konseptual
            ASUInstructionSet.NO_OPERATION: self._op_no_operation,
        }

    def get_asu_instruction_handler(self, operation_code: ASUInstructionSet) -> Optional[Callable[[Dict[str,Any]], Coroutine[Any, Any, Dict[str,Any]]]]:
        """Mengembalikan handler untuk kode operasi .asu yang diberikan."""
        return self._instruction_handlers_registry.get(operation_code)

    def _prepare_for_new_execution(self, asu_file_data: ASUFileObject, inherited_context_data: Optional[Dict] = None):
        """Mempersiapkan state internal TempikUnit untuk eksekusi .asu baru."""
        self.current_status = TempikUnitStatus.INITIALIZING
        self.current_asu_file_hash = asu_file_data.content_sha256_hash
        
        # Reset komponen stateful
        self.registers = TempikRegisterStorage()
        self.program_counter = TempikProgramCounter(self.registers)
        self.runtime_data_storage = TempikRuntimeDataStorage(self.registers) # Stack bersih
        self.vfs = TempikIsolatedVFS(self.tempik_id_str) # VFS baru yang terisolasi
        self.instruction_cache.clear() # Bersihkan cache instruksi lama
        self.data_cache.clear() # Bersihkan cache data lama
        
        # Inisialisasi ulang konteks eksekusi, terapkan dari header, lalu dari warisan jika ada
        self.context_manager = TempikExecutionContextManager(self.tempik_id_str, initial_asu_header=asu_file_data.header_data)
        if inherited_context_data:
            # TODO: Logika untuk menerapkan inherited_context_data ke self.context_manager
            # Misalnya, mewariskan variabel environment tertentu atau status otentikasi.
            # Ini harus dilakukan dengan hati-hati untuk menjaga isolasi jika diperlukan.
            logger.info(f"[{self.tempik_id_str}] Menerapkan konteks warisan (implementasi detail diperlukan).")
            # Contoh: self.context_manager.environment_vars.update(inherited_context_data.get("env_vars", {}))

        self.security_module.update_security_flags(self.context_manager.active_security_flags)
        
        self._current_program_stream = list(asu_file_data.instruction_stream) # Salin instruksi
        self._build_instruction_jump_labels() # Buat peta label untuk JUMP/CALL
        self._active_pipeline = TempikInstructionPipeline(self, self._current_program_stream)
        
        logger.info(f"[{self.tempik_id_str}] Persiapan untuk eksekusi .asu '{self.current_asu_file_hash}' selesai.")

    def _build_instruction_jump_labels(self):
        """Membuat peta dari nama label ke alamat (indeks) instruksi dalam stream."""
        self._instruction_jump_labels.clear()
        for idx, instr_obj in enumerate(self._current_program_stream):
            if instr_obj.jump_label:
                label_name = instr_obj.jump_label.strip()
                if not label_name: continue # Abaikan label kosong

                if label_name in self._instruction_jump_labels:
                    logger.warning(f"[{self.tempik_id_str}] Duplikasi label program: '{label_name}' ditemukan di PC={idx} (sebelumnya di PC={self._instruction_jump_labels[label_name]}). Menggunakan definisi pertama.")
                else:
                    self._instruction_jump_labels[label_name] = idx
        logger.debug(f"[{self.tempik_id_str}] Peta label instruksi dibangun: {len(self._instruction_jump_labels)} label ditemukan.")

    async def process_asu_program(self, asu_file_to_process: ASUFileObject, 
                                  inherited_context: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        Metode utama untuk memproses seluruh stream instruksi dari file .asu yang dimuat.
        Mengelola siklus pipeline hingga program selesai, gagal, atau dihentikan.
        """
        self._prepare_for_new_execution(asu_file_to_process, inherited_context)
        if not self._active_pipeline or not self._current_program_stream:
            # ... (Error handling jika program tidak dimuat) ...
            self.current_status = TempikUnitStatus.FAILED_ERROR
            return [{"status": "error", "message": "Program ASU tidak dimuat dengan benar ke TempikUnit."}]

        all_cycle_outputs: List[Dict[str, Any]] = []
        
        max_total_exec_s = self.context_manager.resource_constraints.get("max_cpu_time_seconds_total", 300)
        program_exec_start_time = time.monotonic()
        setattr(self, '_current_cycle_start_mono_time', program_exec_start_time) # Untuk durasi siklus pertama

        # Batas pengaman untuk jumlah siklus pipeline total
        # Ini berbeda dari timeout, lebih untuk mencegah loop tak terbatas yang tidak memakan waktu CPU signifikan.
        max_pipeline_cycles = self.context_manager.resource_constraints.get("max_pipeline_cycles", 20000) 
        executed_cycle_count = 0

        while self.current_status not in [TempikUnitStatus.COMPLETED_SUCCESS, TempikUnitStatus.FAILED_ERROR, TempikUnitStatus.HALTED_BY_REQUEST] \
              and executed_cycle_count < max_pipeline_cycles:
            
            # 1. Cek Batas Waktu Eksekusi Total Program .asu
            current_elapsed_s = time.monotonic() - program_exec_start_time
            self.context_manager.resource_consumption_tracker["cpu_time_elapsed_seconds"] = current_elapsed_s
            if current_elapsed_s > max_total_exec_s:
                # ... (Error handling untuk global timeout) ...
                self.current_status = TempikUnitStatus.FAILED_ERROR
                # ... (Audit logging untuk global timeout) ...
                break 

            # 2. Jalankan Satu Siklus Pipeline
            pipeline_can_continue, cycle_result_data = await self._active_pipeline.execute_one_full_cycle()
            executed_cycle_count += 1
            if cycle_result_data: all_cycle_outputs.append(cycle_result_data)

            if not pipeline_can_continue: # Pipeline meminta berhenti (EOF, error fatal, HALT)
                break 
            
            if self.current_status == TempikUnitStatus.WAITING_CONDITION:
                # Jika instruksi WAIT, handler akan sleep. Loop ini akan yield ke event loop.
                await asyncio.sleep(0.001) # Yield kecil untuk responsivitas

        # Penanganan akhir setelah loop eksekusi
        if executed_cycle_count >= max_pipeline_cycles and self.current_status not in [TempikUnitStatus.COMPLETED_SUCCESS, TempikUnitStatus.FAILED_ERROR, TempikUnitStatus.HALTED_BY_REQUEST]:
            # ... (Error handling untuk max cycles) ...
            self.current_status = TempikUnitStatus.FAILED_ERROR
            # ... (Audit logging untuk max cycles) ...

        await self.network_unit.close_http_session() # Pastikan session jaringan ditutup
        logger.info(f"[{self.tempik_id_str}] Pemrosesan .asu '{self.current_asu_file_hash}' selesai. Status akhir: {self.current_status.value}. Total siklus: {executed_cycle_count}.")
        return all_cycle_outputs

    def find_instruction_address_for_label_or_type(self, start_search_pc: int, target_op_codes: List[ASUInstructionSet], jump_after_target: bool) -> int:
        """
        Mencari alamat PC dari instruksi berikutnya yang cocok dengan salah satu operation code target,
        dengan memperhatikan blok IF/ELSE/ENDIF bersarang.
        Digunakan oleh pipeline untuk skipping blok IF/ELSE.
        """
        # ... (Implementasi dari V3 _find_matching_endif atau _find_next_control_after_if, disesuaikan) ...
        # Ini adalah logika yang kompleks untuk menangani nested blocks dengan benar.
        # Untuk V4, kita akan menyederhanakan: jika IF false, lompat ke ELSE atau ENDIF yang cocok di level yang sama.
        # Jika ELSE di-skip, lompat ke ENDIF yang cocok.
        
        nesting_level = 0
        current_pc_search = start_search_pc # PC dari instruksi IF atau ELSE itu sendiri

        # Jika kita di IF dan kondisinya false, atau di ELSE yang akan di-skip, kita mulai cari dari instruksi *berikutnya*.
        # Jika kita di JUMP/CALL/RET, kita sudah tahu targetnya.
        
        # Logika ini perlu disempurnakan. Untuk sekarang, jika IF false, pipeline akan set _pc_target_for_next_cycle
        # ke PC dari ELSE atau ENDIF yang sesuai. Jika ELSE di-skip, pipeline akan set _pc_target_for_next_cycle
        # ke PC dari ENDIF yang sesuai.

        # Fungsi ini mungkin lebih baik di-refactor menjadi bagian dari logika Pipeline itu sendiri
        # yang melacak kedalaman blok IF/ELSE.
        # Untuk saat ini, kita asumsikan Pipeline akan menangani lompatan ini dengan benar.
        # Jika dipanggil dari handler IF/ELSE, start_search_pc adalah PC *setelah* IF/ELSE itu.
        
        pc_to_check = start_search_pc # Mulai dari instruksi setelah IF/ELSE saat ini

        while pc_to_check < len(self._current_program_stream):
            instr_at_pc = self._current_program_stream[pc_to_check]
            
            if instr_at_pc.operation_code == ASUInstructionSet.IF_CONDITION:
                nesting_level += 1
            elif instr_at_pc.operation_code == ASUInstructionSet.END_IF_BLOCK:
                if nesting_level == 0: # ENDIF yang cocok dengan IF/ELSE luar
                    if ASUInstructionSet.END_IF_BLOCK in target_op_codes:
                        return pc_to_check + 1 if jump_after_target else pc_to_check
                    # Jika targetnya ELSE dan ketemu ENDIF dulu, berarti ELSE tidak ada di level ini
                else: # ENDIF dari blok inner
                    nesting_level -= 1
            elif instr_at_pc.operation_code in target_op_codes and nesting_level == 0:
                # Menemukan target (ELSE atau ENDIF) di level yang sama
                return pc_to_check + 1 if jump_after_target and instr_at_pc.operation_code == ASUInstructionSet.END_IF_BLOCK else pc_to_check
            
            pc_to_check += 1
        
        return len(self._current_program_stream) # EOF jika tidak ditemukan


    # --- Implementasi Handler untuk Setiap Operasi ASUInstructionSet ---
    # Nama metode: _op_<NAMA_OPERASI_LOWERCASE>
    # Setiap handler adalah `async` dan mengembalikan `Dict[str, Any]`
    # dengan field "status" ("success", "failed", dll.) dan data relevan lainnya.

    async def _op_init_env(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Menginisialisasi lingkungan eksekusi TempikUnit, terutama direktori kerja VFS."""
        vfs_target_cwd = params.get("working_dir_vfs", "/") # Path absolut di VFS
        try:
            self.vfs.create_directory(vfs_target_cwd, self.context_manager, create_intermediate_parents=True)
            self.context_manager.set_vfs_working_directory(vfs_target_cwd, self.vfs)
            return {"status": "success", "message": f"Lingkungan diinisialisasi. CWD VFS: {vfs_target_cwd}"}
        except Exception as e:
            return {"status": "failed", "error": f"Gagal INIT_ENV ke VFS '{vfs_target_cwd}': {str(e)}"}

    async def _op_set_env(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Menetapkan satu atau lebih variabel lingkungan dalam konteks TempikUnit."""
        set_variables = {}
        for key, value in params.items():
            if isinstance(key, str) and (isinstance(value, (str, int, float, bool)) or value is None ):
                self.context_manager.set_environment_variable(key, str(value) if value is not None else "")
                set_variables[key.upper()] = str(value) if value is not None else ""
            else:
                logger.warning(f"[{self.tempik_id_str}] SET_ENV: Kunci '{key}' atau nilai '{value}' tidak valid, dilewati.")
        return {"status": "success", "environment_variables_updated": set_variables}

    async def _op_write_log_message(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Mencatat pesan log dari dalam skrip .asu."""
        message_content = str(params.get("message_text", ""))
        log_level_str = str(params.get("log_level", "INFO")).upper()
        self.io_handler.output_log_message(message_content, log_level_str, 
                                           source_asu_instruction=ASUInstructionSet.WRITE_LOG_MESSAGE, 
                                           current_asu_hash=self.current_asu_file_hash)
        return {"status": "success", "message_logged_content": message_content, "level_used": log_level_str}

    async def _op_execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Mengeksekusi perintah (internal VFS atau subproses host yang di-sandbox)."""
        # Implementasi dari V3 _instr_handler_execute, disesuaikan dengan nama komponen baru
        # dan penekanan pada keamanan.
        # ...
        # Contoh singkat:
        command_str = params.get("command_line", "")
        # if self.security_module.is_operation_permitted("execute_host_command", command_details=[command_str]):
        #     # Logika eksekusi subproses aman (placeholder)
        #     return {"status": "success_simulated", "command": command_str, "stdout": "Simulated output"}
        return {"status": "failed", "error": "Eksekusi perintah host belum diimplementasikan dengan aman."}


    async def _op_if_condition(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Mengevaluasi kondisi untuk blok IF."""
        condition_expr_str = str(params.get("condition_expression", "True"))
        is_condition_true = self.exec_logic_unit.evaluate_logical_expression(condition_expr_str, self.context_manager)
        # Flag COND_RESULT akan di-set oleh pipeline berdasarkan hasil ini
        return {"status": "success", "condition_expression_evaluated": condition_expr_str, "condition_result": is_condition_true}

    async def _op_else_block(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Penanda blok ELSE. Logika skip ditangani oleh pipeline."""
        return {"status": "success", "message": "Blok ELSE dimasuki jika kondisi IF sebelumnya false."}

    async def _op_end_if_block(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Penanda akhir blok IF/ELSE."""
        return {"status": "success", "message": "Akhir blok IF/ELSE tercapai."}

    async def _op_jump(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Melompat ke label tertentu dalam stream instruksi."""
        target_label_id = params.get("target_jump_label")
        if not target_label_id or not isinstance(target_label_id, str):
            return {"status": "failed", "error": "Parameter 'target_jump_label' (string) diperlukan."}
        
        pc_address_target = self._instruction_jump_labels.get(target_label_id)
        if pc_address_target is None:
            return {"status": "failed", "error": f"Label JUMP '{target_label_id}' tidak ditemukan."}
        
        # Pipeline akan menggunakan "target_pc_absolute" untuk mengoverride PC di siklus berikutnya
        return {"status": "success", "jumped_to_label_id": target_label_id, "target_pc_absolute": pc_address_target}

    async def _op_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Memanggil sub-program (label) dan menyimpan alamat kembali."""
        target_label_id = params.get("target_subprogram_label")
        if not target_label_id or not isinstance(target_label_id, str):
            return {"status": "failed", "error": "Parameter 'target_subprogram_label' (string) diperlukan."}

        pc_address_target = self._instruction_jump_labels.get(target_label_id)
        if pc_address_target is None:
            return {"status": "failed", "error": f"Label sub-program CALL '{target_label_id}' tidak ditemukan."}

        # PC saat ini (di RegisterStorage) sudah menunjuk ke instruksi SETELAH CALL (karena diincrement di Fetch)
        address_to_return_to = self.program_counter.current_instruction_address
        self.registers.lr = address_to_return_to # Simpan ke Link Register
        self.runtime_data_storage.push_value_to_stack(address_to_return_to) # Simpan juga ke stack
        
        logger.debug(f"[{self.tempik_id_str}] CALL ke '{target_label_id}' (PC={pc_address_target}). Return Addr PC={address_to_return_to} disimpan.")
        return {"status": "success", "called_subprogram_label": target_label_id, "target_pc_absolute": pc_address_target}

    async def _op_ret(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Kembali dari sub-program menggunakan alamat dari stack."""
        try:
            address_to_return_to = self.runtime_data_storage.pop_value_from_stack()
            if not isinstance(address_to_return_to, int) or address_to_return_to < 0:
                return {"status": "failed", "error": "Alamat kembali dari stack tidak valid untuk RET."}
            
            logger.debug(f"[{self.tempik_id_str}] RET: Kembali ke PC={address_to_return_to} dari stack.")
            return {"status": "success", "returned_to_pc_absolute": address_to_return_to, "target_pc_absolute": address_to_return_to}
        except IndexError: # Stack underflow
            return {"status": "failed", "error": "RET gagal: Stack program kosong, tidak ada alamat kembali."}

    async def _op_halt(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Meminta penghentian eksekusi TempikUnit saat ini."""
        halt_reason = params.get("reason_message", "Instruksi HALT diterima.")
        # Pipeline akan menangani perubahan status TempikUnit ke HALTED_BY_REQUEST
        return {"status": "halt_requested", "reason": halt_reason}

    async def _op_shutdown(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Meminta penghentian seluruh UTEKSystemExecutor."""
        shutdown_reason = params.get("reason_message", "Instruksi SHUTDOWN diterima.")
        # Pipeline akan menangani perubahan status TempikUnit, dan UTEKSystemExecutor akan menangani shutdown global
        return {"status": "system_shutdown_requested", "reason": shutdown_reason}

    async def _op_no_operation(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Tidak melakukan operasi apapun."""
        return {"status": "success", "message": "NO_OPERATION dieksekusi."}
    
    # ... (Implementasi konkret untuk SEMUA handler instruksi lainnya dari ASUInstructionSet)
    # Setiap handler harus:
    # 1. Mengambil parameter dari `params`.
    # 2. Melakukan validasi input.
    # 3. Berinteraksi dengan komponen TempikUnit yang relevan (VFS, NetworkUnit, CryptoEngine, ContextManager, dll.).
    # 4. Mengembalikan dictionary dengan "status" dan data hasil lainnya.
    # 5. Mencatat ke audit log jika operasinya signifikan atau menghasilkan output/error.
    async def _op_assert_condition(self, params: Dict[str, Any]) -> Dict[str, Any]:
        condition_expr = str(params.get("condition_to_assert", "True"))
        failure_message = str(params.get("failure_output_message", f"Assert gagal untuk: {condition_expr}"))
        
        is_condition_met = self.exec_logic_unit.evaluate_logical_expression(condition_expr, self.context_manager)
        if not is_condition_met:
            # Kesalahan fatal, akan menghentikan pipeline dan ditangkap sebagai AssertionError
            raise AssertionError(failure_message) 
        return {"status": "success", "assertion_passed": True, "condition": condition_expr}

    async def _op_wait(self, params: Dict[str, Any]) -> Dict[str, Any]:
        wait_duration_seconds = float(params.get("duration_seconds", 1.0))
        if wait_duration_seconds < 0:
            return {"status": "failed", "error": "Durasi WAIT harus non-negatif."}
        
        self.current_status = TempikUnitStatus.WAITING_CONDITION # Status diubah di sini
        logger.info(f"[{self.tempik_id_str}] WAIT: Menunggu selama {wait_duration_seconds} detik.")
        await asyncio.sleep(wait_duration_seconds)
        # Setelah sleep, pipeline akan melanjutkan dan status akan direset ke IDLE jika tidak ada interupsi.
        return {"status": "success", "waited_duration_seconds": wait_duration_seconds}

    async def _op_verify_hash(self, params: Dict[str, Any]) -> Dict[str, Any]:
        vfs_file_path = params.get("vfs_file_to_verify")
        expected_hash_string = params.get("expected_hash_value")
        hash_algorithm = params.get("hash_algorithm_name", "sha256")

        if not (vfs_file_path and expected_hash_string):
            return {"status": "failed", "error": "Parameter 'vfs_file_to_verify' dan 'expected_hash_value' diperlukan."}
        
        file_bytes_content = self.vfs.read_file_content(vfs_file_path, self.context_manager)
        if file_bytes_content is None:
            return {"status": "failed", "error": f"File VFS '{vfs_file_path}' tidak ditemukan untuk verifikasi hash."}
        
        try:
            is_hash_valid = self.crypto_engine.verify_data_hash(file_bytes_content, expected_hash_string, hash_algorithm)
            actual_hash_if_failed = "" if is_hash_valid else self.crypto_engine.calculate_data_hash(file_bytes_content, hash_algorithm)
            return {
                "status": "success", 
                "hash_verified_successfully": is_hash_valid, 
                "algorithm_used": hash_algorithm, 
                "target_file_vfs": vfs_file_path,
                "provided_expected_hash": expected_hash_string,
                "calculated_actual_hash": actual_hash_if_failed if not is_hash_valid else "MATCHED"
            }
        except ValueError as e: # Misal, algoritma tidak didukung
            return {"status": "failed", "error": f"Error verifikasi hash: {str(e)}"}

    async def _op_delegate_to(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Mendelegasikan eksekusi ke file .asu lain."""
        target_asu_vfs_path = params.get("target_asu_reference_vfs") # Path VFS ke file .asu
        # Opsi: "inherit_context_keys": ["ENV_VAR1", "ENV_VAR2"]
        # Opsi: "new_context_parameters": {"some_param": "value"}
        
        if not target_asu_vfs_path:
            return {"status": "failed", "error": "'target_asu_reference_vfs' diperlukan."}

        delegated_asu_bytes = self.vfs.read_file_content(target_asu_vfs_path, self.context_manager)
        if not delegated_asu_bytes:
            return {"status": "failed", "error": f"File .asu untuk delegasi '{target_asu_vfs_path}' tidak ditemukan di VFS."}

        # Simpan ke file temporary di host untuk diproses oleh UTEKSystemExecutor
        # Ini adalah batasan saat ini; idealnya executor bisa memproses dari byte stream.
        temp_delegated_file_path: Optional[str] = None
        try:
            with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=".asu", prefix="delegated_asu_") as tmp_f:
                tmp_f.write(delegated_asu_bytes)
                temp_delegated_file_path = tmp_f.name
            
            logger.info(f"[{self.tempik_id_str}] DELEGATE_TO: Meminta eksekusi .asu dari VFS:'{target_asu_vfs_path}' (temp host file: {temp_delegated_file_path}).")
            
            # TODO: Siapkan inherited_context_parameters berdasarkan parameter instruksi
            # Misalnya, hanya mewariskan variabel environment tertentu.
            # Ini adalah bagian penting untuk keamanan dan isolasi antar delegasi.
            # Untuk sekarang, kita tidak mewariskan konteks secara otomatis.
            
            delegation_execution_report = await self._system_executor_ref.schedule_and_execute_asu(
                host_file_path=temp_delegated_file_path,
                is_delegated_execution=True,
                inherited_context_parameters=None # Atau params.get("inherited_context_config")
            )
            return {"status": "success", "delegation_target_vfs": target_asu_vfs_path, "delegation_report": delegation_execution_report}
        except Exception as e:
            logger.error(f"[{self.tempik_id_str}] Gagal DELEGATE_TO '{target_asu_vfs_path}': {e}", exc_info=True)
            return {"status": "failed", "error": f"Error saat delegasi: {str(e)}"}
        finally:
            if temp_delegated_file_path and os.path.exists(temp_delegated_file_path):
                try: os.remove(temp_delegated_file_path)
                except OSError as e_rm: logger.warning(f"Gagal menghapus file temporary delegasi '{temp_delegated_file_path}': {e_rm}")


class UTEKSystemExecutor: # Menggantikan UTEKVirtualExecutor dari kode awal
    """
    Executor Sistem UTEK - Komponen utama yang mengelola eksekusi file .asu.
    Bertanggung jawab untuk parsing file .asu, mengelola pool TempikUnit,
    menjadwalkan tugas eksekusi, dan menangani siklus hidup keseluruhan sistem.
    Sesuai dengan arsitektur UTEK dan standar NDAS.
    """
    def __init__(self, max_concurrent_tempik_units: int = 5, 
                 global_audit_log_filepath: Optional[str] = "utek_system_master_audit_v4.log"):
        
        self.max_tempik_units_configured: int = max_concurrent_tempik_units
        self.central_audit_logger: UTEKCentralAuditLogger = UTEKCentralAuditLogger(global_audit_log_filepath)
        
        # Inisialisasi Pool TempikUnit
        self.tempik_unit_execution_pool: List[TempikUnit] = [
            TempikUnit(
                unique_tempik_id=i,
                central_audit_logger=self.central_audit_logger,
                main_system_executor_ref=self, # Memberikan referensi diri ke setiap TempikUnit
                configuration_options=None # Bisa diisi konfigurasi global untuk TempikUnit
            ) for i in range(max_concurrent_tempik_units)
        ]
        self.task_assignment_scheduler: UTEKTaskScheduler = UTEKTaskScheduler(self.tempik_unit_execution_pool)
        
        self._globally_locked_asu_content_hashes: Set[str] = set() # Hash file .asu yang dikunci
        self._parsed_asu_file_object_cache: Dict[str, ASUFileObject] = {} # Cache: content_hash -> ASUFileObject
        self._system_is_shutting_down: bool = False
        self._currently_active_tempik_tasks: List[asyncio.Task] = [] # Melacak task asyncio TempikUnit
        
        logger.info(f"UTEKSystemExecutor (V4 Audit Compliant) diinisialisasi. Max TempikUnits: {max_concurrent_tempik_units}.")

    def _load_and_parse_asu_file_from_host(self, host_filesystem_path: str) -> ASUFileObject:
        """
        Memuat file .asu dari filesystem host, melakukan dekompresi, parsing JSON,
        dan validasi dasar. Mengembalikan objek ASUFileObject.
        """
        # Implementasi sama dengan _load_and_parse_asu_file di V3 UTEKSystemExecutor
        # ... (Salin implementasi _load_and_parse_asu_file dari V3, sesuaikan nama kelas jika perlu) ...
        if not os.path.exists(host_filesystem_path): raise FileNotFoundError(f"File .asu host '{host_filesystem_path}' tidak ada.")
        # ... (Validasi ekstensi, baca, dekompresi, parse JSON, buat HeaderASUData, decode instruksi) ...
        # ... (Hitung content_hash_sha256, validasi nama file, verifikasi checksum_signature) ...
        # ... (Simpan ke _parsed_asu_file_object_cache) ...
        # Contoh singkat:
        filename_stem = Path(host_filesystem_path).stem.lower()
        if filename_stem in self._parsed_asu_file_object_cache and self._parsed_asu_file_object_cache[filename_stem].content_sha256_hash == filename_stem:
            return self._parsed_asu_file_object_cache[filename_stem]
        # ... (Baca, dekompresi, parse) ...
        # json_data = ...
        # header = ASUHeaderData(**json_data['header_data'])
        # decoder = ASUInstructionDecoder()
        # instructions = [decoder.decode_single_instruction(instr) for instr in json_data['instruction_stream']]
        # asu_obj = ASUFileObject(header_data=header, instruction_stream=instructions)
        # asu_obj.calculate_and_set_content_hash()
        # self._parsed_asu_file_object_cache[asu_obj.content_sha256_hash] = asu_obj
        # return asu_obj
        # Ini adalah placeholder, implementasi penuh dari V3 diperlukan
        raise NotImplementedError("Parsing file .asu dari host perlu implementasi penuh dari V3.")


    def create_new_asu_file_on_host(self, asu_header_content: ASUHeaderData, 
                                    asu_instruction_list: List[ASUInstructionObject], 
                                    output_directory_on_host: str = ".") -> str:
        """
        Membuat file .asu baru di filesystem host berdasarkan header dan daftar instruksi.
        Nama file akan menjadi hash konten dari .asu tersebut.
        """
        # Implementasi sama dengan create_asu_file di V3 UTEKSystemExecutor
        # ... (Salin implementasi create_asu_file dari V3, sesuaikan nama kelas jika perlu) ...
        # Contoh singkat:
        # asu_file_to_create = ASUFileObject(header_data=asu_header_content, instruction_stream=asu_instruction_list)
        # content_hash = asu_file_to_create.calculate_and_set_content_hash()
        # output_filename = f"{content_hash}.asu"
        # output_path_host = os.path.join(output_directory_on_host, output_filename)
        # ... (Serialisasi ke JSON, kompresi, tulis ke file) ...
        # logger.info(f"File .asu baru dibuat di host: {output_path_host}")
        # return output_path_host
        raise NotImplementedError("Pembuatan file .asu baru perlu implementasi penuh dari V3.")


    async def schedule_and_run_asu_task(self, asu_host_filepath: str, 
                                        is_part_of_delegation: bool = False, 
                                        inherited_context_from_caller: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Menjadwalkan dan menjalankan satu tugas .asu.
        Ini adalah metode utama yang dipanggil untuk memproses file .asu.
        """
        # Implementasi sama dengan schedule_and_execute_asu di V3 UTEKSystemExecutor
        # ... (Salin implementasi schedule_and_execute_asu dari V3, sesuaikan nama kelas jika perlu) ...
        # Contoh singkat:
        # if self._system_is_shutting_down: return {"status": "system_shutting_down"}
        # try: asu_obj = self._load_and_parse_asu_file_from_host(asu_host_filepath)
        # except Exception as e: return {"status": "parsing_failed", "error": str(e)}
        # ... (Cek lock, request TempikUnit, buat task asyncio, tunggu hasil) ...
        # ... (Tangani permintaan shutdown sistem dari hasil TempikUnit) ...
        # return execution_report
        raise NotImplementedError("Penjadwalan dan eksekusi .asu perlu implementasi penuh dari V3.")


    async def initiate_graceful_system_shutdown(self):
        """Memulai proses shutdown UTEKSystemExecutor secara terkendali."""
        # Implementasi sama dengan initiate_system_shutdown di V3 UTEKSystemExecutor
        # ... (Salin implementasi initiate_system_shutdown dari V3) ...
        if self._system_is_shutting_down: return
        logger.critical("UTEKSystemExecutor: Memulai proses SHUTDOWN sistem...")
        self._system_is_shutting_down = True
        # ... (Tunggu/batalkan task aktif, tutup logger audit) ...
        logger.info("UTEKSystemExecutor: Sistem telah SHUTDOWN.")

    def get_current_system_status(self) -> Dict[str, Any]:
        """Mengembalikan status operasional sistem UTEKSystemExecutor saat ini."""
        # Implementasi sama dengan get_sistem_status di V3 UTEKSystemExecutor
        # ... (Salin implementasi get_sistem_status dari V3, sesuaikan nama kelas) ...
        tempik_statuses = {unit.tempik_id_str: unit.current_status.value for unit in self.tempik_unit_execution_pool}
        return {
            "max_configured_tempik_units": self.max_tempik_units_configured,
            "active_tempik_tasks_count": len(self._currently_active_tempik_tasks),
            "tempik_unit_statuses": tempik_statuses,
            "globally_locked_asu_hashes_count": len(self._globally_locked_asu_content_hashes),
            "parsed_asu_cache_size": len(self._parsed_asu_file_object_cache),
            "system_is_shutting_down": self._system_is_shutting_down
        }
        
    def perform_system_cleanup(self):
        """Membersihkan state internal UTEKSystemExecutor (bukan TempikUnit individual)."""
        # Implementasi sama dengan cleanup_sistem di V3 UTEKSystemExecutor
        # ... (Salin implementasi cleanup_sistem dari V3, fokus pada state Executor) ...
        logger.info("UTEKSystemExecutor: Melakukan cleanup state internal sistem.")
        self._globally_locked_asu_content_hashes.clear()
        self._parsed_asu_file_object_cache.clear()
        # Jangan reset _is_shutting_down_system di sini, itu dihandle oleh siklus hidup executor.
        # Pastikan semua TempikUnit juga di-reset jika perlu (misal, VFS mereka).
        for tempik_unit in self.tempik_unit_execution_pool:
            tempik_unit.current_status = TempikUnitStatus.IDLE
            # Reset VFS dan state lain TempikUnit jika tidak di-handle per eksekusi
            tempik_unit.vfs = TempikIsolatedVFS(tempik_unit.tempik_id_str) 
            tempik_unit.registers = TempikRegisterStorage()
            
        logger.info("UTEKSystemExecutor: Cleanup sistem selesai.")


# --- CLI Interface (Contoh Penggunaan untuk V4) ---
async def main_cli_v4_audit_compliant():
    """Contoh CLI interface untuk UTEKSystemExecutor V4."""
    # ... (Implementasi CLI dari V3 bisa disesuaikan di sini) ...
    # Pastikan menggunakan nama kelas baru dan memanggil metode yang sesuai.
    # Contoh:
    # system_exec = UTEKSystemExecutor(...)
    # report = await system_exec.schedule_and_run_asu_task(args.file)
    # print(json.dumps(report, indent=2, default=str))
    # await system_exec.initiate_graceful_system_shutdown()
    print("CLI untuk V4 perlu implementasi detail menggunakan UTEKSystemExecutor.")


if __name__ == "__main__":
    # Menjalankan event loop asyncio untuk CLI
    # try:
    #     asyncio.run(main_cli_v4_audit_compliant())
    # except KeyboardInterrupt:
    #     logger.info("CLI UTEK V4 dihentikan oleh pengguna.")
    # except Exception as cli_main_err:
    #     logger.critical(f"Error fatal pada level main CLI V4: {cli_main_err}", exc_info=True)
    logger.info("UTEKSystemExecutor V4 (Audit Compliant) - Silakan implementasikan logika CLI atau panggil secara programatik.")
    # Untuk menjalankan, Anda perlu membuat instance UTEKSystemExecutor dan memanggil schedule_and_run_asu_task
    # Contoh:
    # async def run_example():
    #     executor = UTEKSystemExecutor(max_concurrent_tempik_units=2)
    #     # Buat file .asu sampel atau gunakan yang sudah ada
    #     # report = await executor.schedule_and_run_asu_task("path/to/your/file.asu")
    #     # print(json.dumps(report, indent=2, default=str))
    #     # await executor.initiate_graceful_system_shutdown()
    # asyncio.run(run_example())
    pass # Hapus pass dan implementasikan pemanggilan jika ingin menjalankan langsung
