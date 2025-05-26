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

Refactored based on Enterprise Audit.
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
from concurrent.futures import ThreadPoolExecutor # AUDIT POINT 1
import sys # For Profiler
import random # For VirtualFS latency simulation
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable, Tuple, Coroutine

import gzip
import lz4.frame  # pip install lz4
# import requests # Digunakan oleh NetworkUnit nantinya
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding as rsa_padding
from cryptography.exceptions import InvalidSignature
# from pyfakefs.fake_filesystem_unittest import TestCase
# from flask import Flask, request, jsonify

# Konfigurasi Logging Dasar
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(module)s:%(lineno)d | %(message)s', # Added module and lineno
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
    BUSY = "busy" 
    FAILED = "failed"
    COMPLETED = "completed"
    HALTED = "halted"
    WAITING_FOR_RESOURCE = "waiting_for_resource" # AUDIT POINT 1, 2
    PROFILING = "profiling" # AUDIT POINT 16


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
    INSTALL = "INSTALL" # AUDIT POINT 3
    UNPACK = "UNPACK"  
    MOUNT = "MOUNT"
    INJECT = "INJECT"
    COMPILE = "COMPILE" # AUDIT POINT 3
    
    # EKSEKUSI & THREADING
    EXECUTE = "EXECUTE"
    CALL = "CALL" # AUDIT POINT 3, 4
    RET = "RET" # AUDIT POINT 4 (New)
    SPAWN_THREAD = "SPAWN_THREAD" # AUDIT POINT 3
    WAIT = "WAIT"
    DELEGATE_TO = "DELEGATE_TO" # AUDIT POINT 3
    INVOKE_REMOTE = "INVOKE_REMOTE"
    HALT = "HALT"
    SHUTDOWN = "SHUTDOWN"
    
    # KEAMANAN & VERIFIKASI
    VERIFY_HASH = "VERIFY_HASH"
    VERIFY = "VERIFY" 
    SIGN = "SIGN" 
    DECRYPT = "DECRYPT"
    LOCK_EXEC = "LOCK_EXEC" 
    
    # AUDIT, LOGGING & EVENTS
    AUDIT_LOG = "AUDIT_LOG"
    LOG = "LOG"
    EMIT_EVENT = "EMIT_EVENT"
    
    # JARINGAN & DISTRIBUSI
    NETWORK_UP = "NETWORK_UP"
    MAP_PORT = "MAP_PORT"
    PUSH_RESULT = "PUSH_RESULT" # AUDIT POINT 3
    
    # LOGIKA & KONTROL
    IF = "IF"
    ELSE = "ELSE"
    ENDIF = "ENDIF"
    ASSERT = "ASSERT"
    
    # EKSPOR & PEMBERSIHAN
    EXPORT = "EXPORT"
    CLEANUP = "CLEANUP"

    # Operasi ALU (diperluas - AUDIT POINT 5)
    ADD = "ADD"
    SUB = "SUB"
    MUL = "MUL" # New
    DIV = "DIV" # New
    MOD = "MOD" # New
    AND = "AND"
    OR = "OR"
    XOR = "XOR"
    NOT = "NOT" # New
    NEG = "NEG" # New
    SHL = "SHL" # New (Shift Left)
    SHR = "SHR" # New (Shift Right logical)
    SAR = "SAR" # New (Shift Right arithmetic)
    CMP = "CMP" 
    # Floating point (contoh)
    FADD = "FADD" # New
    FSUB = "FSUB" # New
    FMUL = "FMUL" # New
    FDIV = "FDIV" # New
    FCMP = "FCMP" # New

    JMP = "JMP" 
    JZ = "JZ" 
    JNZ = "JNZ" 

# AUDIT POINT 6: Virtual IRQ / Event Types
class InterruptType(Enum):
    TIMER_EXPIRED = "TIMER_EXPIRED" # Untuk Watchdog (AUDIT POINT 11)
    IO_COMPLETED = "IO_COMPLETED"
    EXTERNAL_SIGNAL = "EXTERNAL_SIGNAL" # Misal dari .asu lain atau host
    DEADLINE_MISSED = "DEADLINE_MISSED"
    RESOURCE_LIMIT_EXCEEDED = "RESOURCE_LIMIT_EXCEEDED"
    ASSERTION_FAILURE = "ASSERTION_FAILURE" # Sudah ada di InterruptController
    INVALID_INSTRUCTION = "INVALID_INSTRUCTION"
    MEMORY_FAULT = "MEMORY_FAULT"
    SECURITY_VIOLATION = "SECURITY_VIOLATION"
    MAX_INSTRUCTIONS_REACHED = "MAX_INSTRUCTIONS_REACHED" # Sudah ada
    HALT_REQUESTED = "HALT_REQUESTED" # Sudah ada
    INVALID_JUMP_LABEL = "INVALID_JUMP_LABEL" # Sudah ada
    ARITHMETIC_ERROR = "ARITHMETIC_ERROR" # Misal divide by zero

# AUDIT POINT 15: Execution Modes
class ExecutionMode(Enum):
    BATCH = "batch"
    INTERACTIVE = "interactive"
    SERVICE = "service"
    DRY_RUN = "dry-run"

from dataclasses import dataclass, field

@dataclass
class HeaderASU:
    """Header struktur file .asu sesuai spesifikasi ASU1"""
    processor_spec: str = "963-Tempik"
    protocol_version: str = "v1.0.4-beta" # Akan diupdate jika ada perubahan signifikan
    execution_environment: str = "python3.10"
    memory_profile: str = "512MiB" # e.g., "256MiB", "1GiB"
    filesystem_scheme: str = "overlayfs"
    security_flags: str = "sandboxed"
    time_budget: str = "max-exec-time=60s" # AUDIT POINT 11
    checksum_signature: str = "" 
    compression_info: str = "gzip" # gzip, lz4, none
    asu_build_info: str = ""
    
    dependency_manifest_hash: str = ""  
    target_platform: str = "any"        
    execution_mode: str = ExecutionMode.BATCH.value # AUDIT POINT 15
    networking_mode: str = "isolated"   
    license_access_info: str = "proprietary" 
    max_size: str = "1GB" # AUDIT POINT 9, e.g., "10MB", "2GB"
    
    def to_dict(self) -> Dict[str, str]:
        return self.__dict__

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HeaderASU':
        # Pastikan execution_mode adalah string yang valid dari Enum jika perlu
        if 'execution_mode' in data and isinstance(data['execution_mode'], ExecutionMode):
            data['execution_mode'] = data['execution_mode'].value
        return cls(**data)

    # AUDIT POINT 9: Helper untuk max_size
    def get_max_size_bytes(self) -> int:
        size_str = self.max_size.upper()
        if size_str.endswith("KB") or size_str.endswith("KIB"):
            return int(size_str.replace("KB", "").replace("KIB", "")) * 1024
        elif size_str.endswith("MB") or size_str.endswith("MIB"):
            return int(size_str.replace("MB", "").replace("MIB", "")) * 1024 * 1024
        elif size_str.endswith("GB") or size_str.endswith("GIB"):
            return int(size_str.replace("GB", "").replace("GIB", "")) * 1024 * 1024 * 1024
        try:
            return int(size_str) # Asumsi bytes jika tidak ada unit
        except ValueError:
            logger.warning(f"Format max_size tidak valid: {self.max_size}. Default ke 1GB.")
            return 1 * 1024 * 1024 * 1024 # Default 1GB

    # AUDIT POINT 11: Helper untuk time_budget
    def get_max_exec_time_seconds(self) -> Optional[float]:
        if "max-exec-time=" in self.time_budget:
            try:
                time_str = self.time_budget.split("max-exec-time=")[1].split('s')[0]
                return float(time_str)
            except (IndexError, ValueError):
                logger.warning(f"Format time_budget tidak valid: {self.time_budget}. Tidak ada batas waktu global.")
        return None


@dataclass
class InstruksiEksekusi:
    """Representasi instruksi dalam body file .asu"""
    instruksi: InstruksiASU
    label: Optional[str] = None 
    parameter: Dict[str, Any] = field(default_factory=dict)
    timeout: float = 30.0 # Timeout per instruksi
    retry_count: int = 1 
    
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
            # AUDIT POINT 3: Penanganan instruksi tidak dikenal
            logger.error(f"Instruksi tidak dikenal dalam file .asu: {data['instruksi']}")
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
    virtual_fs_structure: Dict[str, Any] = field(default_factory=dict) 
    hash_sha256: str = "" # Hash dari (header_json_string_sorted + body_json_string_sorted + vfs_json_string_sorted)
    
    def generate_hash(self, for_signing: bool = False) -> str:
        # for_signing=True berarti hash ini akan di-sign, jadi checksum_signature di header harus kosong
        header_dict_for_hash = self.header.to_dict()
        if for_signing and 'checksum_signature' in header_dict_for_hash:
            # Kosongkan signature saat menghitung hash yang akan di-sign
            # agar verifikasi konsisten
            original_sig = header_dict_for_hash['checksum_signature']
            header_dict_for_hash['checksum_signature'] = ""

        body_list = [instr.to_dict() for instr in self.body]
        
        # Sort keys untuk konsistensi JSON string
        content_for_hash = {
            "header": {k: header_dict_for_hash[k] for k in sorted(header_dict_for_hash.keys())},
            "body": body_list, 
            "virtual_fs_structure": {k: self.virtual_fs_structure[k] for k in sorted(self.virtual_fs_structure.keys())}
        }
        
        content_str = json.dumps(content_for_hash, sort_keys=True, separators=(',', ':')) # Compact JSON
        hash_obj = hashlib.sha256(content_str.encode('utf-8'))
        
        if for_signing: # Kembalikan signature asli jika ada
            header_dict_for_hash['checksum_signature'] = original_sig
            return hash_obj.hexdigest() # Ini adalah hash yang akan di-sign
        
        self.hash_sha256 = hash_obj.hexdigest()
        return self.hash_sha256

    # AUDIT POINT 13: Method untuk menandatangani file .asu (dipanggil oleh UTEKVirtualExecutor)
    def sign_file(self, crypto_engine: 'CryptoEngine'):
        if not crypto_engine.private_key:
            raise ValueError("Private key tidak tersedia di CryptoEngine untuk menandatangani file .asu.")
        
        hash_to_sign = self.generate_hash(for_signing=True)
        signature_bytes = crypto_engine.sign_data(hash_to_sign.encode('utf-8'))
        self.header.checksum_signature = signature_bytes.hex()
        # Setelah ditandatangani, hash_sha256 file (yang menyertakan signature) mungkin berbeda.
        # Biasanya, hash_sha256 adalah hash dari konten *sebelum* signature ditambahkan ke header.
        # Atau, signature adalah bagian dari metadata, bukan konten yang di-hash untuk identifikasi file.
        # Untuk konsistensi, kita akan generate ulang hash_sha256 setelah signature ada di header.
        self.generate_hash() # Ini akan menjadi hash dari file yang sudah ditandatangani.
        logger.info(f"FileASU ditandatangani. Signature: {self.header.checksum_signature[:16]}..., Final hash: {self.hash_sha256}")


# --- Komponen Arsitektur Mikro (Low-Level) ---

class RegisterFile:
    """Mewakili register seperti r0–r15, pc, sp, fp dan flags."""
    def __init__(self, num_general_registers: int = 16, stack_size_registers: int = 1024): # AUDIT POINT 4
        self.general_registers = [0] * num_general_registers  # r0-r15
        self.float_registers = [0.0] * num_general_registers # f0-f15 (AUDIT POINT 5)
        self.pc = 0  # Program Counter
        self.sp = stack_size_registers -1 # Stack Pointer, tumbuh ke bawah (AUDIT POINT 4)
        self.fp = stack_size_registers -1 # Frame Pointer (AUDIT POINT 4)
        self.flags = {
            "ZF": False, "CF": False, "SF": False, "OF": False, # Zero, Carry, Sign, Overflow
            "PF": False, "AF": False # Parity, Auxiliary Carry (AUDIT POINT 5)
        }
        self.instruction_register: Optional[InstruksiEksekusi] = None 
        self.status_register: int = 0 # Untuk status Tempik, mode, dll.

    def read_register(self, index: int) -> int:
        if 0 <= index < len(self.general_registers):
            return self.general_registers[index]
        raise ValueError(f"Indeks register umum tidak valid: {index}")

    def write_register(self, index: int, value: int):
        if 0 <= index < len(self.general_registers):
            self.general_registers[index] = value
        else:
            raise ValueError(f"Indeks register umum tidak valid: {index}")

    def read_float_register(self, index: int) -> float: # AUDIT POINT 5
        if 0 <= index < len(self.float_registers):
            return self.float_registers[index]
        raise ValueError(f"Indeks register float tidak valid: {index}")

    def write_float_register(self, index: int, value: float): # AUDIT POINT 5
        if 0 <= index < len(self.float_registers):
            self.float_registers[index] = value
        else:
            raise ValueError(f"Indeks register float tidak valid: {index}")

    def get_flag(self, flag_name: str) -> bool:
        return self.flags.get(flag_name, False)

    def set_flag(self, flag_name: str, value: bool):
        if flag_name in self.flags:
            self.flags[flag_name] = value
        else:
            raise ValueError(f"Nama flag tidak valid: {flag_name}")

    def reset_flags(self): # AUDIT POINT 5
        for flag in self.flags:
            self.flags[flag] = False


class ProgramCounter: # Sebagian besar sudah terintegrasi dengan RegisterFile.pc
    def __init__(self, initial_address: int = 0):
        self._address = initial_address

    @property
    def value(self) -> int:
        return self._address

    def increment(self, amount: int = 1): # Bisa increment lebih dari 1 jika instruksi variabel length
        self._address += amount

    def set(self, new_address: int):
        self._address = new_address

class ALU: # AUDIT POINT 5: Perluasan ALU
    """Arithmetic Logic Unit virtual yang diperluas."""
    def __init__(self, register_file: RegisterFile):
        self.register_file = register_file

    def _update_flags(self, result: Union[int, float], operand1: Union[int, float], operand2: Union[int, float], operation: str):
        is_float_op = isinstance(result, float)
        
        # ZF: Zero Flag
        self.register_file.set_flag("ZF", result == 0)
        
        # SF: Sign Flag (untuk integer)
        if not is_float_op:
            self.register_file.set_flag("SF", result < 0)
        
        # Untuk operasi integer
        if not is_float_op:
            # OF: Overflow Flag (contoh sederhana untuk ADD/SUB 32-bit signed)
            # Implementasi OF yang akurat lebih kompleks dan tergantung representasi angka.
            # Ini adalah placeholder.
            if operation in ["ADD", "SUB"]:
                # Simple check for signed 32-bit overflow
                if result > 2**31 - 1 or result < -(2**31):
                    self.register_file.set_flag("OF", True)
            
            # CF: Carry Flag (contoh untuk ADD/SUB unsigned)
            # Untuk ADD: carry jika hasil > max unsigned. Untuk SUB: borrow jika op1 < op2.
            # Ini juga placeholder.
            if operation == "ADD" and (operand1 + operand2) > 2**32 -1 : # Asumsi unsigned 32-bit
                 self.register_file.set_flag("CF", True)
            if operation == "SUB" and operand1 < operand2: # Asumsi unsigned 32-bit
                 self.register_file.set_flag("CF", True)

            # PF: Parity Flag (jumlah bit 1 genap)
            if isinstance(result, int):
                parity = bin(result & 0xFF).count('1') % 2 == 0 # Parity of LSB
                self.register_file.set_flag("PF", parity)

        # AF: Auxiliary Carry Flag (carry dari bit 3 ke bit 4) - untuk BCD
        # ... implementasi AF jika diperlukan ...

    def execute(self, operation: InstruksiASU, operand1: Union[int, float], operand2: Union[int, float]) -> Union[int, float]:
        self.register_file.reset_flags() # Reset flags sebelum operasi
        result: Union[int, float] = 0

        op_str = operation.value # Misal "ADD", "FSUB"

        try:
            if op_str == "ADD": result = int(operand1) + int(operand2)
            elif op_str == "SUB": result = int(operand1) - int(operand2)
            elif op_str == "MUL": result = int(operand1) * int(operand2)
            elif op_str == "DIV":
                if int(operand2) == 0: raise ZeroDivisionError("ALU DIV: Pembagian dengan nol.")
                result = int(operand1) // int(operand2) # Integer division
            elif op_str == "MOD":
                if int(operand2) == 0: raise ZeroDivisionError("ALU MOD: Pembagian dengan nol.")
                result = int(operand1) % int(operand2)
            elif op_str == "AND": result = int(operand1) & int(operand2)
            elif op_str == "OR":  result = int(operand1) | int(operand2)
            elif op_str == "XOR": result = int(operand1) ^ int(operand2)
            elif op_str == "NOT": result = ~int(operand1)
            elif op_str == "NEG": result = -int(operand1)
            elif op_str == "SHL": result = int(operand1) << int(operand2)
            elif op_str == "SHR": result = int(operand1) >> int(operand2) # Logical shift
            elif op_str == "SAR": # Arithmetic shift (mempertahankan sign bit)
                op1_int = int(operand1)
                op2_int = int(operand2)
                if op1_int < 0: # Jika negatif, perlu penanganan khusus untuk >> Python
                    result = ~( (~op1_int) >> op2_int ) 
                else:
                    result = op1_int >> op2_int
            elif op_str == "CMP":
                cmp_res = int(operand1) - int(operand2)
                self._update_flags(cmp_res, operand1, operand2, op_str)
                return cmp_res # CMP tidak menyimpan hasil, hanya set flags

            # Floating point operations
            elif op_str == "FADD": result = float(operand1) + float(operand2)
            elif op_str == "FSUB": result = float(operand1) - float(operand2)
            elif op_str == "FMUL": result = float(operand1) * float(operand2)
            elif op_str == "FDIV":
                if float(operand2) == 0.0: raise ZeroDivisionError("ALU FDIV: Pembagian float dengan nol.")
                result = float(operand1) / float(operand2)
            elif op_str == "FCMP":
                cmp_res = float(operand1) - float(operand2)
                # Float comparison flags (ZF, SF for <0)
                self.register_file.set_flag("ZF", cmp_res == 0.0)
                self.register_file.set_flag("SF", cmp_res < 0.0)
                # CF dan OF biasanya tidak relevan untuk float CMP seperti di x86
                return cmp_res
            else:
                raise ValueError(f"Operasi ALU tidak dikenal: {op_str}")

            self._update_flags(result, operand1, operand2, op_str)
            return result
        except ZeroDivisionError as zde:
            logger.error(f"ALU Error: {zde}")
            self.register_file.set_flag("ZF", False) # Indikasi error
            # Bisa set flag khusus untuk arithmetic error atau trigger interrupt
            # self.interrupt_controller.raise_interrupt(InterruptType.ARITHMETIC_ERROR, details=str(zde))
            raise # Re-raise untuk ditangani pipeline
        except Exception as e:
            logger.error(f"ALU Exception: {e} saat operasi {op_str}")
            raise

class MemoryUnit: # AUDIT POINT 4: Stack support
    """Bentuk nyata WADAEH. Menyimpan data runtime .asu, termasuk stack."""
    def __init__(self, size_bytes: int = 1024 * 1024, register_file_ref: Optional[RegisterFile] = None):
        self.memory = bytearray(size_bytes)
        self.size = size_bytes
        self.register_file = register_file_ref # Untuk akses SP dan FP

        # Batas stack (contoh, bisa dinamis)
        self.stack_base_address = size_bytes -1 # Stack tumbuh ke bawah dari alamat tertinggi
        self.stack_limit_address = size_bytes // 2 # Batas bawah stack (misal, setengah memori)
        if self.register_file:
            self.register_file.sp = self.stack_base_address
            self.register_file.fp = self.stack_base_address


    def read(self, address: int, num_bytes: int = 4) -> bytes:
        if 0 <= address and address + num_bytes <= self.size:
            return self.memory[address : address + num_bytes]
        logger.error(f"Memory read out of bounds: addr={address}, num_bytes={num_bytes}, size={self.size}")
        raise MemoryError(f"Alamat memori tidak valid atau di luar batas: {address}")

    def write(self, address: int, value: bytes):
        if 0 <= address and address + len(value) <= self.size:
            self.memory[address : address + len(value)] = value
        else:
            logger.error(f"Memory write out of bounds: addr={address}, len_val={len(value)}, size={self.size}")
            raise MemoryError(f"Alamat memori tidak valid atau di luar batas saat menulis: {address}")
    
    # AUDIT POINT 4: Stack operations
    def push_stack(self, value_bytes: bytes):
        if not self.register_file: raise RuntimeError("RegisterFile tidak terhubung ke MemoryUnit untuk operasi stack.")
        
        new_sp = self.register_file.sp - len(value_bytes) + 1 # SP menunjuk ke item terakhir yang di-push
        actual_write_addr = new_sp - (len(value_bytes)-1) # Alamat awal data
        
        if actual_write_addr < self.stack_limit_address:
            raise MemoryError("Stack overflow!")
        
        self.write(actual_write_addr, value_bytes)
        self.register_file.sp = actual_write_addr # SP menunjuk ke alamat awal data yang di-push
        # logger.debug(f"PUSH: {value_bytes.hex()} to stack addr {self.register_file.sp}. New SP: {self.register_file.sp}")


    def pop_stack(self, num_bytes: int) -> bytes:
        if not self.register_file: raise RuntimeError("RegisterFile tidak terhubung ke MemoryUnit untuk operasi stack.")

        if self.register_file.sp + num_bytes > self.stack_base_address +1 : # +1 karena SP menunjuk ke awal data
             raise MemoryError("Stack underflow atau SP tidak valid!")
        
        value = self.read(self.register_file.sp, num_bytes)
        self.register_file.sp += num_bytes # SP sekarang menunjuk ke lokasi kosong berikutnya (lebih tinggi)
        # logger.debug(f"POP: {value.hex()} from stack. New SP: {self.register_file.sp}")
        return value

    def peek_stack(self, offset_from_sp: int, num_bytes: int) -> bytes:
        if not self.register_file: raise RuntimeError("RegisterFile tidak terhubung ke MemoryUnit.")
        address = self.register_file.sp + offset_from_sp
        return self.read(address, num_bytes)

class InstructionCache:
    def __init__(self, capacity: int = 128): 
        self.cache: Dict[int, InstruksiEksekusi] = {} 
        self.capacity = capacity
        self.access_order: List[int] = [] 

    def get(self, address: int) -> Optional[InstruksiEksekusi]:
        if address in self.cache:
            self.access_order.remove(address)
            self.access_order.append(address)
            return self.cache[address]
        return None

    def put(self, address: int, instruction: InstruksiEksekusi):
        if len(self.cache) >= self.capacity:
            lru_address = self.access_order.pop(0)
            del self.cache[lru_address]
        
        self.cache[address] = instruction
        self.access_order.append(address)

class DataCache:
    def __init__(self, capacity_bytes: int = 1024 * 64): # 64KB cache
        self.cache: Dict[int, bytes] = {} 
        self.capacity = capacity_bytes
        self.current_size = 0
        self.access_order: List[int] = []

    def get(self, address: int, num_bytes: int) -> Optional[bytes]:
        if address in self.cache: 
            self.access_order.remove(address)
            self.access_order.append(address)
            cached_block = self.cache[address]
            # Ini asumsi sederhana. Cache nyata akan menangani cache lines dan partial hits.
            # Jika num_bytes > len(cached_block), ini adalah cache miss parsial.
            if len(cached_block) >= num_bytes:
                 return cached_block[:num_bytes]
            # else: return None # Atau handle partial hit
        return None

    def put(self, address: int, data: bytes):
        data_len = len(data)
        if data_len > self.capacity: # Data terlalu besar untuk cache
            return

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
    def __init__(self, register_file: RegisterFile):
        self.register_file = register_file

    def decode(self, raw_instruction: InstruksiEksekusi) -> InstruksiEksekusi:
        self.register_file.instruction_register = raw_instruction
        # AUDIT POINT 3: Validasi parameter instruksi bisa ditambahkan di sini
        # Contoh: if raw_instruction.instruksi == InstruksiASU.ADD:
        #             if "dest_reg" not in raw_instruction.parameter or \
        #                ("operand1_reg" not in raw_instruction.parameter and \
        #                 "operand1_val" not in raw_instruction.parameter):
        #                 raise ValueError("Parameter tidak lengkap untuk ADD")
        logger.debug(f"Decoding instruction: {raw_instruction.instruksi.value} with params {raw_instruction.parameter}")
        return raw_instruction

class AuditLogger:
    def __init__(self, log_file_path: Optional[str] = "audit_log.txt"):
        self.log_file_path = log_file_path
        if self.log_file_path:
            os.makedirs(os.path.dirname(self.log_file_path) or '.', exist_ok=True)

    def log(self, tempik_id: str, instruction_name: str, result_status: str, duration_ms: int, current_file_hash: Optional[str], details: str = ""):
        timestamp = datetime.now().isoformat()
        log_entry = f"{timestamp} | {tempik_id} | {instruction_name} | {result_status} | {duration_ms}ms"
        if current_file_hash:
             log_entry += f" | file_hash={current_file_hash}"
        if details:
            log_entry += f" | details={details.replace('|', ';')}" # Hindari konflik delimiter
        
        logger.info(f"AUDIT: {log_entry}") 
        if self.log_file_path:
            try:
                with open(self.log_file_path, 'a', encoding='utf-8') as f:
                    f.write(log_entry + "\n")
            except Exception as e:
                logger.error(f"Gagal menulis ke audit log file {self.log_file_path}: {e}")

class IOHandler:
    def __init__(self, virtual_fs: 'VirtualFS', tempik_id: str):
        self.virtual_fs = virtual_fs
        self.tempik_id = tempik_id

    def read_file(self, path: str) -> bytes:
        logger.debug(f"{self.tempik_id}: Reading file from VFS: {path}")
        return self.virtual_fs.read_file(path) # VirtualFS akan handle latency (AUDIT POINT 7)

    def write_file(self, path: str, content: bytes, mode: str = 'wb'): # AUDIT POINT 7 (mode)
        logger.debug(f"{self.tempik_id}: Writing file to VFS: {path} (mode: {mode})")
        # Mode 'ab' (append) bisa diimplementasikan di VirtualFS
        self.virtual_fs.write_file(path, content, mode=mode)

    def log_to_terminal(self, message: str, level: str = "INFO"):
        log_level = getattr(logging, level.upper(), logging.INFO)
        logger.log(log_level, f"TEMPİK_IO [{self.tempik_id}]: {message}")

    def get_user_input(self, prompt: str, tempik: 'Tempik') -> str: # AUDIT POINT 15 (interactive)
        if tempik.execution_mode == ExecutionMode.INTERACTIVE:
            # Implementasi nyata memerlukan cara untuk berkomunikasi dengan user (misal, via UTEKVirtualExecutor)
            # Untuk simulasi:
            logger.info(f"TEMPİK_IO [{self.tempik_id}] INTERACTIVE INPUT: {prompt}")
            # response = input(f"Tempik-{self.tempik_id} Input for '{prompt}': ")
            # return response
            # Dalam lingkungan non-CLI, ini harus di-pipe atau disimulasikan
            return f"simulated_input_for_{prompt.replace(' ','_')}"
        logger.warning(f"{self.tempik_id}: Permintaan input pengguna '{prompt}' tidak didukung dalam mode {tempik.execution_mode.value}.")
        return "" 

class ExecutionContextManager: # AUDIT POINT 8 (sudah OK, isolasi per Tempik)
    def __init__(self, tempik_id: str, initial_env_vars: Optional[Dict[str, str]] = None):
        self.tempik_id = tempik_id
        self.env_vars: Dict[str, str] = initial_env_vars or {}
        self.current_working_directory: str = "/" 
        self.role: Optional[str] = None
        self.namespace: Optional[str] = "default" # Untuk isolasi lebih lanjut jika diperlukan
        self.timeout_profile: float = 60.0 
        self.resource_limits: Dict[str, Any] = {"max_vfs_size_bytes": 100 * 1024 * 1024} # AUDIT POINT 7 (quota)
        self.current_user: Optional[str] = None 
        self.security_policy: Dict[str, Any] = {} 
        self.conditional_flags = {"last_if_condition": False, "in_else_block": False, "last_if_condition_evaluated": False, "currently_skipping_if_block": False}

    def set_env_var(self, key: str, value: str):
        self.env_vars[key] = value
        logger.debug(f"{self.tempik_id}: ENV_VAR set: {key}={value}")

    def get_env_var(self, key: str) -> Optional[str]:
        return self.env_vars.get(key)

    def set_working_directory(self, path: str, virtual_fs: 'VirtualFS'):
        if virtual_fs.dir_exists(path):
            self.current_working_directory = path
            logger.debug(f"{self.tempik_id}: CWD set to: {path}")
        else:
            raise FileNotFoundError(f"Direktori tidak ditemukan di VFS: {path}")

    def resolve_path(self, path: str) -> str:
        """Resolve path relatif terhadap CWD di VFS. Mendukung '..'."""
        if not path: return self.current_working_directory # Path kosong berarti CWD

        # Handle path absolut
        if path.startswith('/'):
            # Normalisasi path (menghilangkan '//' dan menangani '.' serta '..')
            return os.path.normpath(path).replace('\\', '/')

        # Handle path relatif
        # Gabungkan CWD dengan path relatif, lalu normalisasi
        # Path.join tidak bekerja baik dengan VFS style, jadi manual
        current_parts = [p for p in self.current_working_directory.strip('/').split('/') if p]
        relative_parts = [p for p in path.strip('/').split('/') if p]
        
        final_parts = list(current_parts) # Salin
        for part in relative_parts:
            if part == ".":
                continue
            elif part == "..":
                if final_parts:
                    final_parts.pop()
            else:
                final_parts.append(part)
        
        return "/" + "/".join(final_parts) if final_parts else "/"


# AUDIT POINT 7: VirtualFS dengan simulasi storage level
@dataclass
class VFSNodeMetadata:
    size: int = 0
    owner_user: str = "root"
    owner_group: str = "root"
    permissions: int = 0o755  # rwxr-xr-x (Okta)
    creation_time: float = field(default_factory=time.time)
    modification_time: float = field(default_factory=time.time)
    access_time: float = field(default_factory=time.time)
    node_type: str = "file" # "file" atau "dir"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "size": self.size, "owner_user": self.owner_user, "owner_group": self.owner_group,
            "permissions": oct(self.permissions), "creation_time": datetime.fromtimestamp(self.creation_time).isoformat(),
            "modification_time": datetime.fromtimestamp(self.modification_time).isoformat(),
            "access_time": datetime.fromtimestamp(self.access_time).isoformat(), "type": self.node_type
        }

class VirtualFS:
    def __init__(self, tempik_id: str, context_manager_ref: Optional[ExecutionContextManager] = None):
        self.tempik_id = tempik_id
        # Struktur: {'/path/to/file': (b'content', VFSNodeMetadata), '/path/to/dir/': ({'subdir_file': (...) }, VFSNodeMetadata)}
        self.fs_root: Dict[str, Any] = {"/": ({}, VFSNodeMetadata(node_type="dir", permissions=0o755))}
        self.mount_points: Dict[str, str] = {} 
        self.context_manager = context_manager_ref # Untuk cek quota

        # Simulasi latency (AUDIT POINT 7)
        self.simulate_latency = True # Bisa dikontrol oleh config
        self.min_latency_ms = 1
        self.max_latency_ms = 10

        self._create_dir_recursive("/scripts", permissions=0o755)
        self._create_dir_recursive("/deps", permissions=0o755)
        self._create_dir_recursive("/output", permissions=0o777) # Lebih permisif untuk output
        self._create_dir_recursive("/temp", permissions=0o777)

    async def _latency(self):
        if self.simulate_latency:
            await asyncio.sleep(random.uniform(self.min_latency_ms, self.max_latency_ms) / 1000.0)

    def _get_node_and_parent(self, path: str) -> Tuple[Optional[Dict], Optional[str], Optional[Any]]:
        """Helper: Mengembalikan (parent_dict, item_name, item_node_content_and_meta)."""
        parts = [part for part in path.strip('/').split('/') if part]
        current_dict_level = self.fs_root["/"][0] # Akses dict konten dari root
        parent_dict = self.fs_root["/"][0] # Default parent adalah root itu sendiri
        
        if not parts: # Root path
            return self.fs_root, "/", self.fs_root["/"] # Parent adalah fs_root, item_name adalah "/", item_node adalah tuple root

        item_name = parts[-1]
        for i, part_name in enumerate(parts[:-1]): # Iterasi hingga parent dari target
            if part_name not in current_dict_level or not isinstance(current_dict_level[part_name][0], dict):
                return None, None, None # Path tidak valid atau bukan direktori
            parent_dict = current_dict_level # Simpan parent sebelum turun
            current_dict_level = current_dict_level[part_name][0] # Turun ke dict konten berikutnya
        
        # Setelah loop, current_dict_level adalah direktori parent dari item_name
        # dan parent_dict adalah parent dari current_dict_level (atau root jika path pendek)
        if item_name in current_dict_level:
            return current_dict_level, item_name, current_dict_level[item_name]
        else: # Item tidak ada, tapi parent ada
            return current_dict_level, item_name, None


    def _check_permissions(self, node_meta: VFSNodeMetadata, access_type: str) -> bool:
        # access_type: "read", "write", "execute"
        # Implementasi pemeriksaan permission sederhana (owner, group, other)
        # Untuk saat ini, kita asumsikan user adalah "owner"
        # TODO: Implementasi ACL yang lebih detail jika diperlukan
        if access_type == "read": required_perm = 0o4 # Bit read
        elif access_type == "write": required_perm = 0o2 # Bit write
        elif access_type == "execute": required_perm = 0o1 # Bit execute
        else: return False
        
        # Cek owner permission (asumsi digit pertama untuk owner)
        owner_perms = (node_meta.permissions >> 6) & 0o7
        if (owner_perms & required_perm) == required_perm:
            return True
        # Bisa ditambahkan cek group dan other
        return False

    def _create_dir_recursive(self, path: str, permissions: int = 0o755):
        parts = [part for part in path.strip('/').split('/') if part]
        current_dict_level = self.fs_root["/"][0]
        current_path_str = "/"
        for part in parts:
            current_path_str = os.path.join(current_path_str, part).replace('\\', '/')
            if part not in current_dict_level:
                new_dir_meta = VFSNodeMetadata(node_type="dir", permissions=permissions, modification_time=time.time(), access_time=time.time())
                current_dict_level[part] = ({}, new_dir_meta)
            elif not isinstance(current_dict_level[part][0], dict): # Ada file dengan nama sama
                raise FileExistsError(f"Path '{current_path_str}' konflik dengan file yang ada.")
            current_dict_level = current_dict_level[part][0]

    def get_node_metadata(self, path: str) -> Optional[VFSNodeMetadata]: # AUDIT POINT 7 (stat)
        parent_dict, item_name, node_content_and_meta = self._get_node_and_parent(path)
        if node_content_and_meta:
            return node_content_and_meta[1] # Metadata adalah elemen kedua
        return None

    def dir_exists(self, path: str) -> bool:
        meta = self.get_node_metadata(path)
        return meta is not None and meta.node_type == "dir"

    def file_exists(self, path: str) -> bool:
        meta = self.get_node_metadata(path)
        return meta is not None and meta.node_type == "file"

    async def write_file(self, path: str, content: bytes, mode: str = 'wb', create_dirs: bool = True):
        await self._latency()
        if not path or path.strip() == "/":
            raise ValueError("Tidak dapat menulis file ke root path '/' secara langsung.")

        dir_path = os.path.dirname(path).replace('\\', '/')
        filename = os.path.basename(path)
        if not filename: raise ValueError(f"Nama file tidak valid dari path: {path}")

        if create_dirs and dir_path and not self.dir_exists(dir_path):
            self._create_dir_recursive(dir_path)
        
        parent_dict, _, parent_node_content_and_meta = self._get_node_and_parent(dir_path)
        if not parent_dict or not parent_node_content_and_meta or parent_node_content_and_meta[1].node_type != "dir":
            raise FileNotFoundError(f"Direktori parent '{dir_path}' tidak ditemukan untuk menulis file '{filename}'.")

        if not self._check_permissions(parent_node_content_and_meta[1], "write"):
            raise PermissionError(f"Tidak ada izin tulis di direktori '{dir_path}'.")

        # Quota check (AUDIT POINT 7)
        if self.context_manager:
            current_vfs_size = self.get_total_vfs_size()
            max_size = self.context_manager.resource_limits.get("max_vfs_size_bytes", float('inf'))
            # Perkirakan ukuran baru (jika file sudah ada, hitung deltanya)
            existing_file_meta = self.get_node_metadata(path)
            delta_size = len(content) - (existing_file_meta.size if existing_file_meta and mode == 'wb' else 0)
            if current_vfs_size + delta_size > max_size:
                raise MemoryError(f"VFS Quota terlampaui. Size: {current_vfs_size + delta_size}, Max: {max_size}")

        target_dir_dict = parent_node_content_and_meta[0]
        current_time = time.time()
        
        if mode == 'wb' or filename not in target_dir_dict: # Tulis baru atau timpa
            file_meta = VFSNodeMetadata(size=len(content), node_type="file", permissions=0o644, modification_time=current_time, access_time=current_time)
            target_dir_dict[filename] = (content, file_meta)
        elif mode == 'ab': # Append
            if filename not in target_dir_dict or target_dir_dict[filename][1].node_type != "file":
                raise FileNotFoundError(f"File '{filename}' tidak ditemukan untuk append di '{dir_path}'.")
            
            existing_content, existing_meta = target_dir_dict[filename]
            if not self._check_permissions(existing_meta, "write"):
                 raise PermissionError(f"Tidak ada izin tulis ke file '{path}'.")
            
            new_content = existing_content + content
            existing_meta.size = len(new_content)
            existing_meta.modification_time = current_time
            existing_meta.access_time = current_time
            target_dir_dict[filename] = (new_content, existing_meta)
        else:
            raise ValueError(f"Mode tulis tidak didukung: {mode}")
        
        parent_node_content_and_meta[1].modification_time = current_time # Update mod time direktori parent
        logger.debug(f"{self.tempik_id} VFS: File '{path}' ditulis ({len(content)} bytes, mode {mode}).")

    async def read_file(self, path: str) -> bytes:
        await self._latency()
        parent_dict, item_name, node_content_and_meta = self._get_node_and_parent(path)
        
        if node_content_and_meta and node_content_and_meta[1].node_type == "file":
            if not self._check_permissions(node_content_and_meta[1], "read"):
                raise PermissionError(f"Tidak ada izin baca untuk file '{path}'.")
            
            node_content_and_meta[1].access_time = time.time() # Update access time
            logger.debug(f"{self.tempik_id} VFS: File '{path}' dibaca.")
            return node_content_and_meta[0] # Konten file
        raise FileNotFoundError(f"File tidak ditemukan di VFS: {path}")

    async def list_dir(self, path: str) -> List[str]:
        await self._latency()
        parent_dict, item_name, node_content_and_meta = self._get_node_and_parent(path)
        
        if node_content_and_meta and node_content_and_meta[1].node_type == "dir":
            if not self._check_permissions(node_content_and_meta[1], "read"): # Perlu izin baca untuk list
                 # Beberapa sistem mengizinkan execute untuk cd, read untuk ls. Kita pakai read.
                raise PermissionError(f"Tidak ada izin baca untuk direktori '{path}'.")
            
            node_content_and_meta[1].access_time = time.time()
            return list(node_content_and_meta[0].keys())
        raise NotADirectoryError(f"Path bukan direktori atau tidak ditemukan di VFS: {path}")

    async def remove_file(self, path: str):
        await self._latency()
        parent_dict, item_name, node_content_and_meta = self._get_node_and_parent(path)
        
        if parent_dict and item_name and node_content_and_meta and node_content_and_meta[1].node_type == "file":
            dir_path = os.path.dirname(path).replace('\\', '/')
            _, _, parent_dir_node_and_meta = self._get_node_and_parent(dir_path)
            if not parent_dir_node_and_meta or not self._check_permissions(parent_dir_node_and_meta[1], "write"):
                 raise PermissionError(f"Tidak ada izin tulis di direktori parent '{dir_path}' untuk menghapus file.")

            del parent_dict[item_name]
            parent_dir_node_and_meta[1].modification_time = time.time()
            logger.debug(f"{self.tempik_id} VFS: File '{path}' dihapus.")
        else:
            raise FileNotFoundError(f"File tidak ditemukan di VFS untuk dihapus: {path}")

    async def remove_dir(self, path: str, recursive: bool = False):
        await self._latency()
        parent_dict, item_name, node_content_and_meta = self._get_node_and_parent(path)

        if parent_dict and item_name and node_content_and_meta and node_content_and_meta[1].node_type == "dir":
            dir_path = os.path.dirname(path).replace('\\', '/')
            _, _, parent_dir_node_and_meta = self._get_node_and_parent(dir_path)
            if not parent_dir_node_and_meta or not self._check_permissions(parent_dir_node_and_meta[1], "write"):
                 raise PermissionError(f"Tidak ada izin tulis di direktori parent '{dir_path}' untuk menghapus direktori.")

            if node_content_and_meta[0] and not recursive: # Direktori tidak kosong
                raise OSError(f"Direktori tidak kosong: {path}")
            
            # Jika rekursif, hapus semua isi dulu (belum diimplementasikan secara penuh di sini)
            # Untuk simulasi, kita hanya hapus entry direktori.
            # Implementasi rekursif yang benar perlu iterasi dan hapus semua child.
            if recursive and node_content_and_meta[0]:
                logger.warning(f"Penghapusan direktori rekursif untuk {path} disimulasikan (konten tidak dihapus satu per satu).")


            del parent_dict[item_name]
            parent_dir_node_and_meta[1].modification_time = time.time()
            logger.debug(f"{self.tempik_id} VFS: Direktori '{path}' dihapus.")
        else:
            raise FileNotFoundError(f"Direktori tidak ditemukan di VFS untuk dihapus: {path}")

    def mount_host_path(self, vfs_path: str, host_path: str):
        if not os.path.exists(host_path) or not os.path.isdir(host_path):
            logger.warning(f"Host path untuk mount tidak ada atau bukan direktori: {host_path}")
        
        self._create_dir_recursive(vfs_path) 
        self.mount_points[vfs_path] = host_path
        logger.info(f"{self.tempik_id} VFS: Host path '{host_path}' di-mount ke VFS path '{vfs_path}' (simulasi).")

    def unmount_host_path(self, vfs_path: str):
        if vfs_path in self.mount_points:
            del self.mount_points[vfs_path]
            logger.info(f"{self.tempik_id} VFS: Host path di-unmount dari VFS path '{vfs_path}' (simulasi).")
        else:
            logger.warning(f"{self.tempik_id} VFS: Tidak ada mount point di '{vfs_path}' untuk di-unmount.")

    async def populate_from_dict(self, structure: Dict[str, Any], base_path: str = "/"):
        for name, content_or_struct in structure.items():
            current_path = os.path.join(base_path, name).replace('\\', '/')
            if isinstance(content_or_struct, str): 
                await self.write_file(current_path, content_or_struct.encode('utf-8'), create_dirs=True)
            elif isinstance(content_or_struct, bytes):
                await self.write_file(current_path, content_or_struct, create_dirs=True)
            elif isinstance(content_or_struct, dict): 
                self._create_dir_recursive(current_path)
                await self.populate_from_dict(content_or_struct, base_path=current_path)
            else:
                logger.warning(f"Tipe konten tidak didukung untuk VFS population di '{current_path}': {type(content_or_struct)}")
    
    def get_total_vfs_size(self) -> int:
        """Hitung total ukuran file dalam VFS."""
        total_size = 0
        
        def _calculate_size_recursive(current_dir_dict: Dict[str, Tuple[Any, VFSNodeMetadata]]):
            nonlocal total_size
            for item_name, (item_content, item_meta) in current_dir_dict.items():
                if item_meta.node_type == "file":
                    total_size += item_meta.size
                elif item_meta.node_type == "dir":
                    _calculate_size_recursive(item_content) # item_content adalah dict untuk direktori

        _calculate_size_recursive(self.fs_root["/"][0]) # Mulai dari konten root
        return total_size


class CryptoEngine:
    def __init__(self):
        self.private_key: Optional[rsa.RSAPrivateKey] = None
        self.public_key: Optional[rsa.RSAPublicKey] = None

    def generate_key_pair_if_needed(self): # Diubah dari _generate_key_pair
        if not self.private_key:
            self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            self.public_key = self.private_key.public_key()
            logger.info("CryptoEngine: Key pair baru digenerate.")

    def load_private_key(self, key_bytes: bytes, password: Optional[bytes] = None):
        self.private_key = serialization.load_pem_private_key(key_bytes, password=password)
        self.public_key = self.private_key.public_key()

    def load_public_key(self, key_bytes: bytes):
        self.public_key = serialization.load_pem_public_key(key_bytes)

    def sign_data(self, data: bytes) -> bytes:
        self.generate_key_pair_if_needed() # Pastikan ada kunci
        if not self.private_key:
            raise ValueError("Private key tidak di-load untuk signing.")
        return self.private_key.sign(
            data,
            rsa_padding.PSS(mgf=rsa_padding.MGF1(hashes.SHA256()), salt_length=rsa_padding.PSS.MAX_LENGTH),
            hashes.SHA256()
        )

    def verify_signature(self, data: bytes, signature: bytes, public_key_override: Optional[rsa.RSAPublicKey] = None) -> bool:
        key_to_use = public_key_override if public_key_override else self.public_key
        if not key_to_use:
            # Coba generate jika tidak ada sama sekali (meskipun ini aneh untuk verify)
            # self.generate_key_pair_if_needed() 
            # key_to_use = self.public_key
            # if not key_to_use:
            raise ValueError("Public key tidak di-load/tersedia untuk verifikasi.")
        try:
            key_to_use.verify(
                signature, data,
                rsa_padding.PSS(mgf=rsa_padding.MGF1(hashes.SHA256()), salt_length=rsa_padding.PSS.MAX_LENGTH),
                hashes.SHA256()
            )
            return True
        except InvalidSignature:
            logger.warning("Verifikasi signature gagal: InvalidSignature.")
            return False
        except Exception as e:
            logger.error(f"Error saat verifikasi signature: {e}")
            return False


    def encrypt_data(self, data: bytes) -> bytes:
        self.generate_key_pair_if_needed()
        if not self.public_key:
             raise ValueError("Public key tidak di-load untuk enkripsi.")
        return self.public_key.encrypt(
            data,
            rsa_padding.OAEP(mgf=rsa_padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
        )

    def decrypt_data(self, ciphertext: bytes) -> bytes:
        self.generate_key_pair_if_needed()
        if not self.private_key:
            raise ValueError("Private key tidak di-load untuk dekripsi.")
        return self.private_key.decrypt(
            ciphertext,
            rsa_padding.OAEP(mgf=rsa_padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
        )

    @staticmethod
    def calculate_hash(data: bytes, algorithm: str = "sha256") -> str:
        h = None
        if algorithm.lower() == "sha256": h = hashlib.sha256()
        elif algorithm.lower() == "sha512": h = hashlib.sha512()
        else: raise ValueError(f"Algoritma hash tidak didukung: {algorithm}")
        h.update(data)
        return h.hexdigest()

class NetworkUnit:
    def __init__(self, context_manager: ExecutionContextManager, tempik_id_str: str):
        self.context_manager = context_manager
        self.tempik_id_str = tempik_id_str
        # import requests # Pindahkan ke atas jika global, atau lazy import
        # import aiohttp # Untuk async

    async def _check_network_policy(self) -> bool:
        policy = self.context_manager.security_policy.get("networking_mode", "isolated")
        if policy == "isolated":
            logger.warning(f"{self.tempik_id_str} NetworkUnit: Operasi jaringan diblokir (mode isolated).")
            return False
        # "restricted" bisa punya whitelist domain/IP (belum diimplementasikan)
        return True

    async def fetch_repo(self, url: str, target_dir_vfs: str, io_handler: IOHandler) -> Dict[str, Any]:
        if not await self._check_network_policy():
            return {"status": "failed", "error": "Operasi jaringan tidak diizinkan (mode isolated)."}

        logger.info(f"{self.tempik_id_str} NetworkUnit: Fetching repo from {url} to VFS:{target_dir_vfs}")
        try:
            # Simulasi:
            # Dalam implementasi nyata, gunakan subprocess.run(['git', 'clone', url, host_temp_dir])
            # lalu salin hasilnya ke VFS.
            # Untuk sekarang, kita buat file placeholder.
            await io_handler.virtual_fs._create_dir_recursive(target_dir_vfs) 
            readme_content = f"# Simulated repo from {url}\nTimestamp: {datetime.now()}".encode('utf-8')
            await io_handler.write_file(os.path.join(target_dir_vfs, "README.md").replace('\\', '/'), readme_content)
            return {"status": "success", "message": f"Simulated fetch to VFS:{target_dir_vfs}"}
        except Exception as e:
            logger.error(f"{self.tempik_id_str} NetworkUnit: Gagal simulasi fetch_repo: {e}")
            return {"status": "failed", "error": str(e)}

    async def invoke_remote(self, endpoint: str, method: str = "POST", data: Optional[Dict] = None, headers: Optional[Dict]=None) -> Dict[str, Any]:
        if not await self._check_network_policy():
             return {"status": "failed", "error": "Operasi jaringan tidak diizinkan."}
        
        logger.info(f"{self.tempik_id_str} NetworkUnit: Invoking remote {method} {endpoint}")
        # Contoh dengan aiohttp (perlu diinstal: pip install aiohttp)
        # try:
        #     import aiohttp
        #     async with aiohttp.ClientSession(headers=headers) as session:
        #         async with session.request(method, endpoint, json=data if method in ["POST", "PUT"] else None, 
        #                                    params=data if method in ["GET", "DELETE"] else None) as response:
        #             return {
        #                 "status_code": response.status,
        #                 "response_body": await response.json() if response.content_type == 'application/json' else await response.text()
        #             }
        # except Exception as e:
        #     logger.error(f"{self.tempik_id_str} NetworkUnit: Gagal invoke_remote: {e}")
        #     return {"status_code": 500, "error": str(e)}
        return {"status": "simulated_success", "endpoint": endpoint, "message": "Remote invocation simulated."}

    async def push_result(self, destination_url: str, data: Any, tempik: 'Tempik') -> Dict[str, Any]: # AUDIT POINT 3
        if not await self._check_network_policy():
            return {"status": "failed", "error": "Operasi jaringan tidak diizinkan."}

        logger.info(f"{self.tempik_id_str} NetworkUnit: Pushing result to {destination_url}")
        # Mirip invoke_remote, tapi biasanya POST dengan payload hasil
        payload = {"source_tempik": tempik.tempik_id, "file_hash": tempik.current_file_hash, "result_data": data}
        # return await self.invoke_remote(destination_url, method="POST", data=payload)
        return {"status": "simulated_push_success", "url": destination_url, "data_pushed_summary": str(data)[:100]}


class SecurityModule:
    def __init__(self, context_manager: ExecutionContextManager, crypto_engine: CryptoEngine):
        self.context_manager = context_manager
        self.crypto_engine = crypto_engine

    def verify_asu_signature(self, file_asu: FileASU, public_key_pem_bytes: Optional[bytes] = None) -> bool:
        if not file_asu.header.checksum_signature:
            logger.warning("Tidak ada checksum_signature di header .asu untuk diverifikasi.")
            return True # Atau False jika signature wajib

        # Load public key jika disediakan, atau gunakan yang sudah ada di engine
        key_to_use = self.crypto_engine.public_key
        if public_key_pem_bytes:
            try:
                temp_pub_key = serialization.load_pem_public_key(public_key_pem_bytes)
                key_to_use = temp_pub_key
            except Exception as e:
                logger.error(f"Gagal load public key PEM untuk verifikasi .asu: {e}")
                return False
        
        if not key_to_use:
            logger.error("Public key tidak tersedia untuk verifikasi signature .asu.")
            return False

        # Data yang di-sign adalah hash dari konten file (sebelum signature ditambahkan ke header)
        data_to_verify_hash = file_asu.generate_hash(for_signing=True)
        signature_bytes = bytes.fromhex(file_asu.header.checksum_signature)

        return self.crypto_engine.verify_signature(data_to_verify_hash.encode('utf-8'), signature_bytes, public_key_override=key_to_use)

    def check_instruction_policy(self, instruction: InstruksiEksekusi, tempik: 'Tempik') -> bool: # AUDIT POINT 15 (dry-run)
        if tempik.execution_mode == ExecutionMode.DRY_RUN:
            # Untuk dry-run, log instruksi tapi jangan blokir kecuali sangat berbahaya
            logger.info(f"DRY_RUN Policy Check: Instruction {instruction.instruksi.value} with params {instruction.parameter}")
            # Beberapa instruksi mungkin tetap perlu diblokir bahkan dalam dry-run jika sangat berbahaya
            # if instruction.instruksi == InstruksiASU.SHUTDOWN: return False 
            return True # Umumnya, dry-run tidak melakukan aksi destruktif

        if instruction.instruksi == InstruksiASU.FETCH_REPO and \
           self.context_manager.security_policy.get("networking_mode") == "isolated":
            logger.warning(f"Instruksi {instruction.instruksi.value} diblokir oleh policy jaringan.")
            return False
        
        is_readonly_mode = "readonly" in self.context_manager.security_policy.get("flags", [])
        write_instructions = [InstruksiASU.INJECT, InstruksiASU.EXPORT] # Tambahkan instruksi tulis VFS lainnya
        # Perlu cara untuk tahu apakah EXECUTE akan menulis
        if is_readonly_mode and instruction.instruksi in write_instructions:
            logger.warning(f"Instruksi {instruction.instruksi.value} diblokir oleh policy readonly.")
            return False
            
        if instruction.instruksi == InstruksiASU.EXECUTE:
            command_str = "".join(map(str,instruction.parameter.get("command", ""))) 
            # Filter command berbahaya (contoh sederhana)
            dangerous_commands = ["rm -rf", "curl | sh", "mkfs", ":(){ :|:& };:"] # Fork bomb
            if any(dc in command_str for dc in dangerous_commands):
                logger.error(f"Potensi command berbahaya terdeteksi dan diblokir: {command_str}")
                return False
        return True

    def apply_resource_limits(self, tempik: 'Tempik'): # AUDIT POINT 7, 11
        # Cek VFS quota
        max_vfs_size = tempik.execution_context_manager.resource_limits.get("max_vfs_size_bytes")
        if max_vfs_size is not None:
            current_vfs_size = tempik.virtual_fs.get_total_vfs_size()
            if current_vfs_size > max_vfs_size:
                logger.error(f"Tempik-{tempik.tempik_id}: VFS Quota terlampaui ({current_vfs_size}/{max_vfs_size}).")
                tempik.interrupt_controller.raise_interrupt(InterruptType.RESOURCE_LIMIT_EXCEEDED, 
                                                            details=f"VFS Quota: {current_vfs_size}/{max_vfs_size}")
        
        # Cek max_exec_time (ditangani oleh Watchdog atau loop utama Tempik)


class InterruptController: # AUDIT POINT 6 (diperluas)
    def __init__(self):
        self.pending_interrupts: List[Tuple[InterruptType, Optional[Callable], Optional[Dict]]] = [] # (type, handler, details)
        self.interrupt_vector_table: Dict[InterruptType, Callable] = {} # Handler default

    def register_handler(self, interrupt_type: InterruptType, handler: Callable[['Tempik', InterruptType, Optional[Dict]], None]):
        self.interrupt_vector_table[interrupt_type] = handler

    def raise_interrupt(self, interrupt_type: InterruptType, handler: Optional[Callable] = None, details: Optional[Dict] = None):
        self.pending_interrupts.append((interrupt_type, handler, details))
        logger.warning(f"INTERRUPT: {interrupt_type.value} diajukan. Details: {details}")

    def clear_interrupts(self): # Mungkin tidak diperlukan jika ditangani satu per satu
        self.pending_interrupts.clear()

    def handle_interrupt_if_pending(self, tempik: 'Tempik'): 
        if not self.pending_interrupts:
            return

        interrupt_type, custom_handler, details = self.pending_interrupts.pop(0) # FIFO
        
        handler_to_call = custom_handler
        if not handler_to_call and interrupt_type in self.interrupt_vector_table:
            handler_to_call = self.interrupt_vector_table[interrupt_type]
        
        if handler_to_call:
            logger.info(f"Tempik-{tempik.tempik_id}: Menangani interrupt {interrupt_type.value}")
            try:
                handler_to_call(tempik, interrupt_type, details)
            except Exception as e:
                logger.error(f"Error saat menangani interrupt {interrupt_type.value} di Tempik-{tempik.tempik_id}: {e}")
                tempik.set_status(TempikStatus.FAILED) # Gagal jika handler error
        else:
            logger.warning(f"Tempik-{tempik.tempik_id}: Tidak ada handler untuk interrupt {interrupt_type.value}. Mengabaikan.")
        
        # Interrupt mungkin sudah mengubah status Tempik (misal, ke HALTED atau FAILED)


# AUDIT POINT 16: Profiler
class Profiler:
    def __init__(self, tempik_id_str: str):
        self.tempik_id_str = tempik_id_str
        self.instruction_timings: Dict[str, List[float]] = {} # instruction_name -> [durations_ms]
        self.instruction_memory_usage: Dict[str, List[int]] = {} # instruction_name -> [mem_bytes_delta]
        self.instruction_utek_units: Dict[str, List[int]] = {} # instruction_name -> [utek_units]
        self.active_timers: Dict[str, float] = {} # key -> start_time

    def start_timer(self, key: str = "instruction"):
        self.active_timers[key] = time.perf_counter()

    def stop_timer(self, key: str = "instruction") -> float: # return duration_ms
        end_time = time.perf_counter()
        start_time = self.active_timers.pop(key, end_time) # Default ke end_time jika key tidak ada
        return (end_time - start_time) * 1000

    def record_instruction_metric(self, instruction_name: str, duration_ms: float, mem_delta: int = 0, utek_units: int = 1):
        self.instruction_timings.setdefault(instruction_name, []).append(duration_ms)
        self.instruction_memory_usage.setdefault(instruction_name, []).append(mem_delta)
        self.instruction_utek_units.setdefault(instruction_name, []).append(utek_units)

    def get_summary(self) -> Dict[str, Any]:
        summary = {}
        for instr, timings in self.instruction_timings.items():
            summary[instr] = {
                "count": len(timings),
                "avg_duration_ms": sum(timings) / len(timings) if timings else 0,
                "max_duration_ms": max(timings) if timings else 0,
                "avg_mem_delta": sum(self.instruction_memory_usage.get(instr, [0])) / len(self.instruction_memory_usage.get(instr, [1])) if self.instruction_memory_usage.get(instr) else 0,
                "total_utek_units": sum(self.instruction_utek_units.get(instr, [0]))
            }
        return summary

    def get_memory_usage_platform(self) -> int: # Perkiraan memori proses (platform-dependent)
        try:
            if sys.platform == "win32":
                # import psutil # Perlu psutil
                # return psutil.Process(os.getpid()).memory_info().rss
                return 0 # Placeholder
            else:
                import resource
                return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 # ru_maxrss dalam KB di Linux
        except Exception:
            return 0 # Gagal mendapatkan info memori


# AUDIT POINT 17: Bus (Konsep Dasar)
class Bus:
    """Kelas dasar untuk Bus (InstructionBus, MemoryBus)."""
    def __init__(self, name: str):
        self.name = name
        self.subscribers: List[Callable] = [] # Komponen yang listen ke bus
        logger.info(f"{name} initialized.")

    def publish(self, message: Any, source_component: str):
        logger.debug(f"{self.name} from {source_component}: {message}")
        for subscriber in self.subscribers:
            try:
                subscriber(message, source_component)
            except Exception as e:
                logger.error(f"Error pada subscriber {self.name}: {e}")
    
    def subscribe(self, callback: Callable):
        self.subscribers.append(callback)

# --- Komponen Pipeline dan Kontrol ---

class Pipeline:
    def __init__(self, tempik: 'Tempik'): 
        self.tempik = tempik 
        self.stages = {
            TempikStatus.FETCH: self._fetch_stage,
            TempikStatus.DECODE: self._decode_stage,
            TempikStatus.EXECUTE: self._execute_stage,
            TempikStatus.MEMORY_ACCESS: self._memory_access_stage,
            TempikStatus.WRITE_BACK: self._write_back_stage,
        }
        self.current_stage_data: Dict[str, Any] = {} 

    async def _fetch_stage(self) -> Optional[InstruksiEksekusi]:
        pc_value = self.tempik.program_counter.value
        instruction = self.tempik.instruction_cache.get(pc_value)
        if not instruction:
            if 0 <= pc_value < len(self.tempik.program_memory):
                instruction = self.tempik.program_memory[pc_value]
                self.tempik.instruction_cache.put(pc_value, instruction)
                logger.debug(f"TEMPİK-{self.tempik.tempik_id_str} FETCH: Instruction at PC={pc_value} from memory.")
            else:
                logger.info(f"TEMPİK-{self.tempik.tempik_id_str} FETCH: Program Counter ({pc_value}) di luar batas ({len(self.tempik.program_memory)}). Program selesai atau error.")
                self.tempik.set_status(TempikStatus.COMPLETED if not self.tempik.program_memory else TempikStatus.FAILED)
                return None
        else:
            logger.debug(f"TEMPİK-{self.tempik.tempik_id_str} FETCH: Instruction at PC={pc_value} from cache.")
        
        self.current_stage_data['fetched_instruction'] = instruction
        # PC increment dipindah setelah validasi instruksi dan sebelum eksekusi,
        # terutama untuk JMP/CALL agar PC menunjuk ke instruksi *setelah* JMP/CALL sebelum target address di-load.
        # Namun, untuk pipeline sederhana, increment di sini umum. Kita akan sesuaikan jika perlu.
        # self.tempik.program_counter.increment() # PC akan diupdate oleh ControlUnit setelah instruksi selesai
        return instruction

    async def _decode_stage(self) -> Optional[InstruksiEksekusi]:
        fetched_instruction = self.current_stage_data.get('fetched_instruction')
        if not fetched_instruction: return None

        try:
            decoded_instruction = self.tempik.instruction_decoder.decode(fetched_instruction)
            self.current_stage_data['decoded_instruction'] = decoded_instruction
            logger.debug(f"TEMPİK-{self.tempik.tempik_id_str} DECODE: {decoded_instruction.instruksi.value}")
            return decoded_instruction
        except ValueError as ve: # AUDIT POINT 3 (Instruksi tidak dikenal)
            logger.error(f"TEMPİK-{self.tempik.tempik_id_str} DECODE ERROR: {ve}")
            self.tempik.interrupt_controller.raise_interrupt(InterruptType.INVALID_INSTRUCTION, details={"instruction": str(fetched_instruction)})
            self.tempik.set_status(TempikStatus.FAILED)
            return None


    async def _execute_stage(self) -> Optional[Dict[str, Any]]:
        decoded_instruction = self.current_stage_data.get('decoded_instruction')
        if not decoded_instruction: return None

        if not self.tempik.security_module.check_instruction_policy(decoded_instruction, self.tempik): # AUDIT POINT 15 (dry-run)
            error_msg = f"Pelanggaran policy keamanan untuk instruksi {decoded_instruction.instruksi.value}"
            logger.error(f"TEMPİK-{self.tempik.tempik_id_str} EXECUTE: {error_msg}")
            self.current_stage_data['execution_result'] = {"status": "failed", "error": error_msg}
            self.tempik.interrupt_controller.raise_interrupt(InterruptType.SECURITY_VIOLATION, details={"instruction": decoded_instruction.instruksi.value})
            self.tempik.set_status(TempikStatus.FAILED)
            return self.current_stage_data['execution_result']

        ctx_mgr = self.tempik.execution_context_manager
        # Logika IF/ELSE/ENDIF sudah ada dan tampak cukup baik.
        # ... (kode IF/ELSE/ENDIF yang sudah ada dipertahankan) ...
        if decoded_instruction.instruksi == InstruksiASU.ELSE:
            if not ctx_mgr.conditional_flags.get("last_if_condition_evaluated", False):
                 raise RuntimeError("ELSE tanpa IF yang sesuai.") # Ini harusnya jadi interrupt
            if ctx_mgr.conditional_flags["last_if_condition"]: 
                logger.debug(f"TEMPİK-{self.tempik.tempik_id_str} EXECUTE: Skipping ELSE block (IF was true).")
                self.current_stage_data['execution_result'] = {"status": "skipped_else", "skipped": True}
                return self.current_stage_data['execution_result']
            else: 
                ctx_mgr.conditional_flags["in_else_block"] = True
                self.current_stage_data['execution_result'] = {"status": "entering_else", "skipped": False}
                return self.current_stage_data['execution_result']
        elif decoded_instruction.instruksi == InstruksiASU.ENDIF:
            ctx_mgr.conditional_flags["last_if_condition"] = False
            ctx_mgr.conditional_flags["in_else_block"] = False
            ctx_mgr.conditional_flags["last_if_condition_evaluated"] = False
            ctx_mgr.conditional_flags["currently_skipping_if_block"] = False # Pastikan reset
            self.current_stage_data['execution_result'] = {"status": "endif_processed"}
            return self.current_stage_data['execution_result']
        
        # Cek apakah kita sedang skip karena IF sebelumnya false dan belum masuk ELSE
        if ctx_mgr.conditional_flags.get("last_if_condition_evaluated") and \
           not ctx_mgr.conditional_flags.get("last_if_condition") and \
           not ctx_mgr.conditional_flags.get("in_else_block") and \
           decoded_instruction.instruksi not in [InstruksiASU.ELSE, InstruksiASU.ENDIF]:
            
            logger.debug(f"TEMPİK-{self.tempik.tempik_id_str} EXECUTE: Skipping instruction due to prior IF=false: {decoded_instruction.instruksi.value}")
            ctx_mgr.conditional_flags["currently_skipping_if_block"] = True
            self.current_stage_data['execution_result'] = {"status": "skipped_due_to_if", "skipped": True}
            return self.current_stage_data['execution_result']
        
        # Jika kita sampai di sini, berarti kita tidak sedang skip karena IF false
        # atau kita sudah di dalam blok ELSE yang benar.
        ctx_mgr.conditional_flags["currently_skipping_if_block"] = False


        handler = self.tempik.instruction_set.get_handler(decoded_instruction.instruksi)
        if not handler:
            # AUDIT POINT 3: Handler tidak ditemukan
            logger.error(f"Handler tidak ditemukan untuk instruksi: {decoded_instruction.instruksi.value}")
            self.tempik.interrupt_controller.raise_interrupt(InterruptType.INVALID_INSTRUCTION, details={"instruction": decoded_instruction.instruksi.value, "error": "Handler not found"})
            self.current_stage_data['execution_result'] = {"status": "failed", "error": f"Handler tidak ditemukan untuk {decoded_instruction.instruksi.value}"}
            self.tempik.set_status(TempikStatus.FAILED)
            return self.current_stage_data['execution_result']


        logger.debug(f"TEMPİK-{self.tempik.tempik_id_str} EXECUTE: Running handler for {decoded_instruction.instruksi.value}")
        
        execution_result = None
        last_exception = None
        for attempt in range(decoded_instruction.retry_count + 1): 
            try:
                # AUDIT POINT 15 (dry-run): Handler harus sadar mode dry-run
                if self.tempik.execution_mode == ExecutionMode.DRY_RUN and \
                   decoded_instruction.instruksi not in [InstruksiASU.LOG, InstruksiASU.IF, InstruksiASU.ELSE, InstruksiASU.ENDIF, InstruksiASU.ASSERT, InstruksiASU.VERIFY_HASH, InstruksiASU.VERIFY]: # Instruksi non-mutating
                    logger.info(f"DRY_RUN: Simulating execution of {decoded_instruction.instruksi.value}")
                    execution_result = {"status": "dry_run_simulated", "instruction": decoded_instruction.instruksi.value}
                else:
                    execution_result = await asyncio.wait_for(
                        handler(self.tempik, decoded_instruction.parameter), 
                        timeout=decoded_instruction.timeout
                    )
                
                if decoded_instruction.instruksi == InstruksiASU.IF:
                    condition_result = execution_result.get("condition_met", False)
                    ctx_mgr.conditional_flags["last_if_condition"] = condition_result
                    ctx_mgr.conditional_flags["in_else_block"] = False 
                    ctx_mgr.conditional_flags["last_if_condition_evaluated"] = True
                    if not condition_result:
                        logger.debug(f"TEMPİK-{self.tempik.tempik_id_str} EXECUTE: IF condition FALSE. Skipping to next ELSE/ENDIF.")
                break 
            except asyncio.TimeoutError:
                last_exception = TimeoutError(f"Instruksi {decoded_instruction.instruksi.value} timeout setelah {decoded_instruction.timeout}s pada attempt {attempt+1}")
                logger.warning(str(last_exception))
            except AssertionError as ae: # Dari instruksi ASSERT
                last_exception = ae
                logger.error(f"TEMPİK-{self.tempik.tempik_id_str} EXECUTE: Assertion failed for {decoded_instruction.instruksi.value}: {ae}")
                # Interrupt sudah di-raise oleh handler ASSERT
                break # Tidak perlu retry assertion
            except ZeroDivisionError as zde: # Dari ALU
                last_exception = zde
                logger.error(f"TEMPİK-{self.tempik.tempik_id_str} EXECUTE: Arithmetic error for {decoded_instruction.instruksi.value}: {zde}")
                self.tempik.interrupt_controller.raise_interrupt(InterruptType.ARITHMETIC_ERROR, details={"instruction": decoded_instruction.instruksi.value, "error": str(zde)})
                break # Tidak perlu retry error aritmatika
            except Exception as e:
                last_exception = e
                logger.error(f"TEMPİK-{self.tempik.tempik_id_str} EXECUTE: Error pada attempt {attempt+1} untuk {decoded_instruction.instruksi.value}: {e}", exc_info=True)
            
            if attempt < decoded_instruction.retry_count:
                await asyncio.sleep(0.1 * (2 ** attempt)) # Exponential backoff
            elif last_exception: 
                execution_result = {"status": "failed", "error": str(last_exception)}
                if not self.tempik.status == TempikStatus.FAILED: # Jika interrupt belum set FAILED
                    self.tempik.set_status(TempikStatus.FAILED)

        self.current_stage_data['execution_result'] = execution_result
        return execution_result

    async def _memory_access_stage(self) -> Optional[Any]:
        # Tahap ini lebih relevan untuk arsitektur CPU level rendah.
        # Untuk instruksi ASU level tinggi, akses memori (VFS, context) biasanya terjadi di tahap EXECUTE.
        # Namun, jika ada instruksi LOAD/STORE ke MemoryUnit (RAM Tempik), ini tempatnya.
        execution_result = self.current_stage_data.get('execution_result', {})
        decoded_instruction = self.current_stage_data.get('decoded_instruction')
        
        # Contoh: jika ada instruksi LOAD_MEM atau STORE_MEM
        # if decoded_instruction and decoded_instruction.instruksi == InstruksiASU.LOAD_MEM:
        #    addr = execution_result.get("memory_address")
        #    num_bytes = execution_result.get("num_bytes", 4)
        #    data_from_mem = self.tempik.memory_unit.read(addr, num_bytes)
        #    # Simpan data_from_mem ke register atau teruskan ke write_back
        #    execution_result["data_loaded"] = data_from_mem

        logger.debug(f"TEMPİK-{self.tempik.tempik_id_str} MEMORY_ACCESS: Result from EXECUTE: {execution_result.get('status', 'N/A') if isinstance(execution_result,dict) else 'OK'}")
        self.current_stage_data['data_for_writeback'] = execution_result 
        return execution_result

    async def _write_back_stage(self) -> Optional[Any]:
        data_to_write = self.current_stage_data.get('data_for_writeback')
        decoded_instruction = self.current_stage_data.get('decoded_instruction')
        
        # Contoh: jika hasil EXECUTE perlu ditulis ke register
        # if isinstance(data_to_write, dict) and "register_write" in data_to_write:
        #    reg_idx = data_to_write["register_write"]["index"]
        #    reg_val = data_to_write["register_write"]["value"]
        #    self.tempik.register_file.write_register(reg_idx, reg_val)

        logger.debug(f"TEMPİK-{self.tempik.tempik_id_str} WRITE_BACK: Data: {str(data_to_write)[:200]}") # Log ringkasan
        
        final_status = "unknown"
        if isinstance(data_to_write, dict):
            final_status = data_to_write.get("status", "completed")
            # Jika ada error dari execute stage, pastikan status Tempik FAILED
            if final_status == "failed" and self.tempik.status != TempikStatus.FAILED:
                self.tempik.set_status(TempikStatus.FAILED)
        elif data_to_write is not None: # Jika bukan dict tapi ada hasil
            final_status = "completed"

        if decoded_instruction:
            duration_ms = self.tempik.profiler.stop_timer("current_instruction")
            error_details = data_to_write.get("error", "") if isinstance(data_to_write, dict) else ""
            
            self.tempik.audit_logger.log(
                tempik_id=self.tempik.tempik_id_str,
                instruction_name=decoded_instruction.instruksi.value,
                result_status=final_status.upper(),
                duration_ms=int(duration_ms),
                current_file_hash=self.tempik.current_file_hash,
                details=error_details
            )
            # AUDIT POINT 16: Record ke profiler Tempik
            self.tempik.profiler.record_instruction_metric(
                instruction_name=decoded_instruction.instruksi.value,
                duration_ms=duration_ms
                # mem_delta dan utek_units bisa ditambahkan jika diukur
            )
        
        self.current_stage_data.clear()
        return data_to_write 

    async def run_cycle(self) -> Optional[Dict[str, Any]]:
        self.tempik.set_status(TempikStatus.FETCH)
        if not await self.stages[TempikStatus.FETCH](): 
            # Jika fetch gagal (EOF atau error), status Tempik sudah diatur di _fetch_stage
            return None 
        
        self.tempik.set_status(TempikStatus.DECODE)
        decoded_instruction = await self.stages[TempikStatus.DECODE]()
        if not decoded_instruction: 
            # Jika decode gagal, status Tempik sudah diatur di _decode_stage
            return None 
        
        self.tempik.set_status(TempikStatus.EXECUTE)
        execution_result = await self.stages[TempikStatus.EXECUTE]()
        # Jika eksekusi gagal, status Tempik sudah diatur di _execute_stage atau oleh interrupt
        # dan result mungkin berisi info error.

        # Jika instruksi adalah HALT, atau status FAILED/HALTED karena interrupt/error
        current_instr_obj = self.tempik.register_file.instruction_register
        if (current_instr_obj and current_instr_obj.instruksi == InstruksiASU.HALT) or \
           self.tempik.status in [TempikStatus.FAILED, TempikStatus.HALTED]:
            
            # Langsung ke write_back untuk logging, skip memory_access jika tidak relevan
            self.current_stage_data['data_for_writeback'] = execution_result
            self.tempik.set_status(TempikStatus.WRITE_BACK) # Status sementara untuk logging
            final_output = await self.stages[TempikStatus.WRITE_BACK]()
            
            # Set status final Tempik jika belum (misal, HALT instruction)
            if current_instr_obj and current_instr_obj.instruksi == InstruksiASU.HALT and self.tempik.status != TempikStatus.FAILED:
                self.tempik.set_status(TempikStatus.HALTED)
            logger.info(f"TEMPİK-{self.tempik.tempik_id_str} execution ended early. Status: {self.tempik.status.value}")
            return final_output


        self.tempik.set_status(TempikStatus.MEMORY_ACCESS)
        await self.stages[TempikStatus.MEMORY_ACCESS]()
        
        self.tempik.set_status(TempikStatus.WRITE_BACK)
        final_output = await self.stages[TempikStatus.WRITE_BACK]()
        
        return final_output


class ControlUnit:
    def __init__(self, tempik: 'Tempik'): 
        self.tempik = tempik
        self.pipeline = Pipeline(tempik)
        self.is_running = False

    async def start_execution(self, program: List[InstruksiEksekusi], initial_pc: int = 0):
        self.tempik.load_program(program, initial_pc)
        self.is_running = True
        logger.info(f"TEMPİK-{self.tempik.tempik_id_str} ControlUnit: Execution started. Mode: {self.tempik.execution_mode.value}")
        
        instruction_count = 0
        # Batas instruksi bisa dari config atau header .asu
        max_instructions = self.tempik.execution_context_manager.resource_limits.get("max_instructions", 100000) 
        
        self.tempik.global_execution_start_time = time.time() # AUDIT POINT 11 (Watchdog)

        while self.is_running and \
              self.tempik.status not in [TempikStatus.COMPLETED, TempikStatus.FAILED, TempikStatus.HALTED] and \
              self.tempik.program_counter.value < len(self.tempik.program_memory) and \
              instruction_count < max_instructions:
            
            # AUDIT POINT 11: Watchdog check
            self.tempik.check_global_timeout() 
            if self.tempik.status == TempikStatus.FAILED: # Jika timeout menyebabkan FAILED
                logger.warning(f"Tempik-{self.tempik.tempik_id_str} halted due to global execution timeout.")
                break

            self.tempik.interrupt_controller.handle_interrupt_if_pending(self.tempik)
            if self.tempik.status in [TempikStatus.FAILED, TempikStatus.HALTED]: 
                break

            self.tempik.profiler.start_timer("current_instruction") # AUDIT POINT 16
            
            # Simpan PC sebelum eksekusi untuk JMP/CALL relatif
            pc_before_execute = self.tempik.program_counter.value

            result = await self.pipeline.run_cycle()
            instruction_count +=1

            # Update PC
            instr_obj = self.tempik.register_file.instruction_register
            if self.tempik.status not in [TempikStatus.FAILED, TempikStatus.HALTED]: # Hanya update PC jika tidak ada error fatal
                if instr_obj:
                    params = instr_obj.parameter
                    # Jika JMP/CALL/RET, PC sudah diatur oleh handler atau logika di bawah
                    is_branch_or_call = instr_obj.instruksi in [InstruksiASU.JMP, InstruksiASU.JZ, InstruksiASU.JNZ, InstruksiASU.CALL, InstruksiASU.RET]
                    
                    if is_branch_or_call:
                        # Logika JMP/CALL/RET akan set PC
                        if instr_obj.instruksi == InstruksiASU.JMP and "target_label" in params:
                            self.tempik.jump_to_label(params["target_label"])
                        elif instr_obj.instruksi == InstruksiASU.JZ and "target_label" in params and self.tempik.register_file.get_flag("ZF"):
                            self.tempik.jump_to_label(params["target_label"])
                        elif instr_obj.instruksi == InstruksiASU.JNZ and "target_label" in params and not self.tempik.register_file.get_flag("ZF"):
                            self.tempik.jump_to_label(params["target_label"])
                        # CALL dan RET akan dihandle oleh instruction handler mereka untuk memanipulasi PC & stack
                        # Jika CALL/RET berhasil, PC sudah di target_address / return_address
                    else: # Bukan branch/call/ret, increment PC biasa
                        self.tempik.program_counter.increment() 
                else: # Tidak ada instruction_register (misal, fetch gagal)
                     self.tempik.program_counter.increment() # Coba increment, mungkin EOF
                
                self.tempik.register_file.pc = self.tempik.program_counter.value # Sinkronkan


            if result is None and self.tempik.status not in [TempikStatus.COMPLETED, TempikStatus.FAILED, TempikStatus.HALTED] : 
                logger.info(f"TEMPİK-{self.tempik.tempik_id_str} ControlUnit: No result from pipeline cycle, assuming end of program or fetch error.")
                if self.tempik.program_counter.value >= len(self.tempik.program_memory):
                    self.tempik.set_status(TempikStatus.COMPLETED)
                else: # Jika bukan EOF tapi result None, mungkin error fetch
                    self.tempik.set_status(TempikStatus.FAILED) 
                break
            
            if self.tempik.status in [TempikStatus.FAILED, TempikStatus.HALTED]:
                break 

        if instruction_count >= max_instructions and self.tempik.status not in [TempikStatus.COMPLETED, TempikStatus.FAILED, TempikStatus.HALTED]:
            logger.warning(f"TEMPİK-{self.tempik.tempik_id_str} ControlUnit: Max instruction limit ({max_instructions}) reached.")
            self.tempik.interrupt_controller.raise_interrupt(InterruptType.MAX_INSTRUCTIONS_REACHED, details={"limit": max_instructions})
            self.tempik.set_status(TempikStatus.FAILED)


        if self.tempik.status not in [TempikStatus.FAILED, TempikStatus.HALTED]:
             self.tempik.set_status(TempikStatus.COMPLETED)
        logger.info(f"TEMPİK-{self.tempik.tempik_id_str} ControlUnit: Execution finished. Final status: {self.tempik.status.value}. Instructions executed: {instruction_count}.")
        self.is_running = False


    def halt_execution(self, reason: str = "External Halt"):
        if self.is_running:
            self.is_running = False
            # InterruptController akan menangani perubahan status Tempik
            self.tempik.interrupt_controller.raise_interrupt(
                InterruptType.HALT_REQUESTED, 
                handler=lambda t, type, det: t.set_status(TempikStatus.HALTED), # Handler sederhana untuk set status
                details={"reason": reason}
            )
            logger.info(f"TEMPİK-{self.tempik.tempik_id_str} ControlUnit: Execution halt requested. Reason: {reason}")
        else:
            logger.info(f"TEMPİK-{self.tempik.tempik_id_str} ControlUnit: Halt requested, but not running.")


# --- Definisi InstructionSet dan Handler ---
InstructionHandler = Callable[['Tempik', Dict[str, Any]], Coroutine[Any, Any, Dict[str, Any]]]

class InstructionSet: # AUDIT POINT 3 (kelengkapan handler)
    def __init__(self):
        self.handlers: Dict[InstruksiASU, InstructionHandler] = {}
        self._register_default_handlers()

    def _register_default_handlers(self):
        # Environment & Konfigurasi
        self.handlers[InstruksiASU.SET_ENV] = self._handle_set_env
        self.handlers[InstruksiASU.INIT_ENV] = self._handle_init_env
        self.handlers[InstruksiASU.SET_CONTEXT] = self._handle_set_context
        self.handlers[InstruksiASU.AUTH] = self._handle_auth
        # Pengambilan Sumber & Dependensi
        self.handlers[InstruksiASU.FETCH_REPO] = self._handle_fetch_repo
        self.handlers[InstruksiASU.CHECKOUT] = self._handle_checkout 
        self.handlers[InstruksiASU.INSTALL] = self._handle_install # AUDIT POINT 3
        self.handlers[InstruksiASU.UNPACK] = self._handle_unpack
        self.handlers[InstruksiASU.MOUNT] = self._handle_mount
        self.handlers[InstruksiASU.INJECT] = self._handle_inject
        self.handlers[InstruksiASU.COMPILE] = self._handle_compile # AUDIT POINT 3
        # Eksekusi & Threading
        self.handlers[InstruksiASU.EXECUTE] = self._handle_execute
        self.handlers[InstruksiASU.CALL] = self._handle_call # AUDIT POINT 3, 4
        self.handlers[InstruksiASU.RET] = self._handle_ret   # AUDIT POINT 4
        self.handlers[InstruksiASU.SPAWN_THREAD] = self._handle_spawn_thread # AUDIT POINT 3
        self.handlers[InstruksiASU.WAIT] = self._handle_wait # Placeholder
        self.handlers[InstruksiASU.DELEGATE_TO] = self._handle_delegate_to # AUDIT POINT 3
        self.handlers[InstruksiASU.INVOKE_REMOTE] = self._handle_invoke_remote
        self.handlers[InstruksiASU.HALT] = self._handle_halt
        self.handlers[InstruksiASU.SHUTDOWN] = self._handle_shutdown
        # Keamanan & Verifikasi
        self.handlers[InstruksiASU.VERIFY_HASH] = self._handle_verify_hash
        self.handlers[InstruksiASU.VERIFY] = self._handle_verify 
        self.handlers[InstruksiASU.SIGN] = self._handle_sign
        self.handlers[InstruksiASU.DECRYPT] = self._handle_decrypt
        self.handlers[InstruksiASU.LOCK_EXEC] = self._handle_lock_exec
        # Audit, Logging & Events
        self.handlers[InstruksiASU.LOG] = self._handle_log
        self.handlers[InstruksiASU.EMIT_EVENT] = self._handle_emit_event
        # Jaringan & Distribusi
        self.handlers[InstruksiASU.MAP_PORT] = self._handle_map_port
        self.handlers[InstruksiASU.PUSH_RESULT] = self._handle_push_result # AUDIT POINT 3
        # Logika & Kontrol
        self.handlers[InstruksiASU.IF] = self._handle_if
        self.handlers[InstruksiASU.ELSE] = self._handle_else 
        self.handlers[InstruksiASU.ENDIF] = self._handle_endif
        self.handlers[InstruksiASU.ASSERT] = self._handle_assert
        # Ekspor & Pembersihan
        self.handlers[InstruksiASU.EXPORT] = self._handle_export
        self.handlers[InstruksiASU.CLEANUP] = self._handle_cleanup
        # ALU Operations (AUDIT POINT 5)
        alu_ops = [
            InstruksiASU.ADD, InstruksiASU.SUB, InstruksiASU.MUL, InstruksiASU.DIV, InstruksiASU.MOD,
            InstruksiASU.AND, InstruksiASU.OR, InstruksiASU.XOR, InstruksiASU.NOT, InstruksiASU.NEG,
            InstruksiASU.SHL, InstruksiASU.SHR, InstruksiASU.SAR, InstruksiASU.CMP,
            InstruksiASU.FADD, InstruksiASU.FSUB, InstruksiASU.FMUL, InstruksiASU.FDIV, InstruksiASU.FCMP
        ]
        for op in alu_ops:
            self.handlers[op] = self._handle_alu_op
        # JMP, JZ, JNZ ditangani oleh ControlUnit setelah eksekusi CMP atau instruksi lain yang set flag

    def get_handler(self, instruksi: InstruksiASU) -> Optional[InstructionHandler]:
        return self.handlers.get(instruksi)

    # --- Implementasi Handler (disesuaikan dan ditambahkan) ---
    
    async def _handle_set_env(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        # ... (kode yang ada dipertahankan) ...
        for key, value in params.items():
            tempik.execution_context_manager.set_env_var(key, str(value))
        return {"status": "success", "vars_set": len(params)}

    async def _handle_init_env(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        # ... (kode yang ada dipertahankan) ...
        vfs_working_dir = params.get("working_dir", "/")
        try:
            tempik.execution_context_manager.set_working_directory(vfs_working_dir, tempik.virtual_fs)
            initial_structure = params.get("initial_fs_structure")
            if isinstance(initial_structure, dict):
                await tempik.virtual_fs.populate_from_dict(initial_structure, base_path=vfs_working_dir)
            return {"status": "success", "working_dir_vfs": vfs_working_dir}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    async def _handle_execute(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        # ... (kode yang ada dipertahankan, dengan penyesuaian untuk VFS async) ...
        command_param = params.get("command", "")
        args = params.get("args", [])
        cmd_str_list = []
        if isinstance(command_param, list): cmd_str_list.extend(command_param)
        else: cmd_str_list.append(str(command_param))
        cmd_str_list.extend(map(str, args))
        full_command_str = " ".join(cmd_str_list)
        
        logger.info(f"TEMPİK-{tempik.tempik_id_str} EXECUTE (simulated): {full_command_str} in VFS CWD: {tempik.execution_context_manager.current_working_directory}")
        
        if tempik.execution_mode == ExecutionMode.DRY_RUN:
            return {"status": "dry_run_simulated", "command": full_command_str, "output": "Command execution simulated (dry-run)."}

        # Contoh eksekusi skrip Python dari VFS (SANGAT BERBAHAYA TANPA SANDBOX KUAT)
        if cmd_str_list[0] == "python" and len(cmd_str_list) > 1:
            script_path_vfs = tempik.execution_context_manager.resolve_path(cmd_str_list[1])
            if await tempik.virtual_fs.file_exists(script_path_vfs): # VFS methods are now async
                # script_content = (await tempik.virtual_fs.read_file(script_path_vfs)).decode('utf-8')
                # Eksekusi Python code (TIDAK AMAN, HANYA UNTUK DEMO TERBATAS)
                logger.warning(f"Direct Python script execution from VFS '{script_path_vfs}' is highly insecure and only for limited demo.")
                return {"status": "simulated_python_execution", "script": script_path_vfs, "output": "Python script executed (simulated)."}
            else:
                return {"status": "failed", "error": f"Script VFS tidak ditemukan: {script_path_vfs}"}
        
        # Simulasi eksekusi command umum
        # Di dunia nyata, ini akan menggunakan subprocess dengan isolasi ketat (namespaces, cgroups)
        # atau WebAssembly runtime.
        # Untuk sekarang, hanya log.
        return {"status": "simulated_success", "command": full_command_str, "output": "Command executed (simulated)."}


    async def _handle_log(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        # ... (kode yang ada dipertahankan) ...
        message = params.get("message", "")
        level = params.get("level", "INFO").upper()
        tempik.io_handler.log_to_terminal(message, level)
        return {"status": "success", "logged_message": message}

    async def _handle_fetch_repo(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        # ... (kode yang ada dipertahankan) ...
        url = params.get("url")
        target_vfs_path = params.get("target", f"/deps/{os.path.basename(url or 'default_repo')}")
        if not url: return {"status": "failed", "error": "URL repository diperlukan"}
        if tempik.execution_mode == ExecutionMode.DRY_RUN:
            return {"status": "dry_run_simulated", "action": "FETCH_REPO", "url": url, "target": target_vfs_path}
        return await tempik.network_unit.fetch_repo(url, target_vfs_path, tempik.io_handler)


    async def _handle_verify_hash(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        # ... (kode yang ada dipertahankan, dengan penyesuaian untuk VFS async) ...
        file_vfs_path = params.get("file")
        expected_hash = params.get("hash", "").lower()
        algorithm = params.get("algorithm", "sha256").lower()
        if not file_vfs_path: return {"status": "failed", "error": "Path file VFS diperlukan"}

        try:
            resolved_path = tempik.execution_context_manager.resolve_path(file_vfs_path)
            file_content = await tempik.io_handler.read_file(resolved_path)
            actual_hash = tempik.crypto_engine.calculate_hash(file_content, algorithm)
            verified = actual_hash == expected_hash
            if not verified:
                logger.warning(f"VERIFY_HASH gagal untuk {resolved_path}. Expected: {expected_hash}, Actual: {actual_hash}")
            return {"status": "success", "file": resolved_path, "verified": verified, "actual_hash": actual_hash, "expected_hash": expected_hash}
        except FileNotFoundError:
            return {"status": "failed", "error": f"File tidak ditemukan di VFS: {file_vfs_path}"}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    async def _handle_cleanup(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        # ... (kode yang ada dipertahankan, dengan penyesuaian untuk VFS async) ...
        target_vfs_path = params.get("dir", tempik.execution_context_manager.current_working_directory)
        resolved_path = tempik.execution_context_manager.resolve_path(target_vfs_path)
        
        if tempik.execution_mode == ExecutionMode.DRY_RUN:
            return {"status": "dry_run_simulated", "action": "CLEANUP", "path": resolved_path}

        try:
            if await tempik.virtual_fs.dir_exists(resolved_path):
                if resolved_path == "/" : return {"status": "failed", "error": "Tidak dapat cleanup root VFS."}
                items_to_delete = await tempik.virtual_fs.list_dir(resolved_path)
                for item in items_to_delete:
                    item_path = os.path.join(resolved_path, item).replace('\\','/')
                    if await tempik.virtual_fs.file_exists(item_path): await tempik.virtual_fs.remove_file(item_path)
                    elif await tempik.virtual_fs.dir_exists(item_path): await tempik.virtual_fs.remove_dir(item_path, recursive=True)
                if resolved_path != tempik.execution_context_manager.current_working_directory and await tempik.virtual_fs.dir_exists(resolved_path):
                     await tempik.virtual_fs.remove_dir(resolved_path, recursive=True)
                return {"status": "success", "cleaned_vfs_path": resolved_path}
            elif await tempik.virtual_fs.file_exists(resolved_path):
                await tempik.virtual_fs.remove_file(resolved_path)
                return {"status": "success", "cleaned_vfs_file": resolved_path}
            else:
                return {"status": "warning", "message": f"Path VFS tidak ditemukan untuk cleanup: {resolved_path}"}
        except Exception as e:
            return {"status": "failed", "error": f"Error saat cleanup VFS {resolved_path}: {e}"}

    async def _handle_if(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        # ... (kode yang ada dipertahankan, dengan evaluasi kondisi yang lebih aman) ...
        condition_str = str(params.get("condition", "false")) # Tidak di .lower() agar bisa case-sensitive jika perlu
        condition_met = False
        try:
            # Evaluasi kondisi yang lebih aman:
            # 1. Cek boolean literal
            if condition_str.lower() == "true": condition_met = True
            elif condition_str.lower() == "false": condition_met = False
            # 2. Cek perbandingan env var (contoh: "env['MY_VAR'] == 'expected_value'")
            elif "env[" in condition_str and ("==" in condition_str or "!=" in condition_str):
                # Ini masih sederhana, perlu parser yang lebih kuat untuk ekspresi kompleks
                import re
                match = re.match(r"env\['(.*?)'\]\s*(==|!=)\s*'(.*?)'", condition_str)
                if match:
                    var_name, operator, expected_val_str = match.groups()
                    actual_val = tempik.execution_context_manager.get_env_var(var_name)
                    if operator == "==": condition_met = (actual_val == expected_val_str)
                    elif operator == "!=": condition_met = (actual_val != expected_val_str)
                else: logger.warning(f"Format kondisi IF tidak dikenal: {condition_str}")
            # 3. Cek perbandingan register (contoh: "reg[0] > 10")
            elif "reg[" in condition_str:
                 # Contoh: reg[idx] op val -> reg[0] > 10
                 # Perlu parser yang lebih baik. Untuk sekarang, tidak diimplementasikan penuh.
                 logger.warning(f"Evaluasi kondisi register di IF belum diimplementasikan penuh: {condition_str}")
            else:
                logger.warning(f"Kondisi IF tidak dapat dievaluasi secara aman: {condition_str}. Dianggap false.")
        except Exception as e:
            logger.error(f"Error evaluasi kondisi IF '{condition_str}': {e}")
            condition_met = False
        return {"status": "success", "condition_met": condition_met, "condition_str": condition_str}


    async def _handle_else(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "success", "message": "ELSE block encountered"}
    async def _handle_endif(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "success", "message": "ENDIF block encountered"}

    async def _handle_assert(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        # ... (kode yang ada dipertahankan, gunakan evaluasi kondisi dari _handle_if) ...
        condition_str = str(params.get("condition", "false"))
        message = params.get("message", f"Assertion failed: {condition_str}")
        
        # Gunakan logika evaluasi yang sama dengan IF untuk konsistensi
        if_result = await self._handle_if(tempik, {"condition": condition_str})
        condition_met = if_result.get("condition_met", False)
        
        if not condition_met:
            logger.error(f"ASSERTION FAILED: {message} (Condition: '{condition_str}')")
            tempik.interrupt_controller.raise_interrupt(InterruptType.ASSERTION_FAILURE, details={"message": message, "condition": condition_str})
            # Tidak raise error di sini, biarkan interrupt yang mengubah status Tempik
            return {"status": "failed", "error": f"Assertion failed: {message}"} # Hasil untuk pipeline
        return {"status": "success", "assertion_passed": True}


    async def _handle_halt(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        reason = params.get("reason", "HALT instruction executed")
        # ControlUnit akan dihentikan oleh status HALTED Tempik
        # tempik.control_unit.halt_execution(reason) # Tidak perlu panggil langsung
        tempik.set_status(TempikStatus.HALTED) # Langsung set status
        logger.info(f"Tempik-{tempik.tempik_id_str} HALTED. Reason: {reason}")
        return {"status": "halted", "reason": reason} 

    async def _handle_shutdown(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        reason = params.get("reason", "SHUTDOWN instruction executed")
        logger.critical(f"TEMPİK-{tempik.tempik_id_str} requested UTEK SHUTDOWN. Reason: {reason}")
        if tempik.parent_executor: # Beri sinyal ke parent executor
            asyncio.create_task(tempik.parent_executor.shutdown(f"Requested by Tempik-{tempik.tempik_id_str}: {reason}"))
        else: # Jika tidak ada parent, halt diri sendiri
            tempik.set_status(TempikStatus.HALTED)
        return {"status": "shutdown_requested", "reason": reason}

    async def _handle_set_context(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        # ... (kode yang ada dipertahankan) ...
        ctx_mgr = tempik.execution_context_manager
        if "role" in params: ctx_mgr.role = params["role"]
        if "namespace" in params: ctx_mgr.namespace = params["namespace"]
        if "timeout_profile" in params: ctx_mgr.timeout_profile = float(params["timeout_profile"])
        if "resource_limits" in params: ctx_mgr.resource_limits.update(params["resource_limits"])
        if "current_user" in params: ctx_mgr.current_user = params["current_user"]
        if "security_policy" in params: ctx_mgr.security_policy.update(params["security_policy"])
        if "working_directory" in params:
            try: ctx_mgr.set_working_directory(params["working_directory"], tempik.virtual_fs)
            except FileNotFoundError as e: return {"status": "failed", "error": str(e), "context_updated": False}
        logger.info(f"TEMPİK-{tempik.tempik_id_str} context updated.")
        return {"status": "success", "context_updated": True}

    async def _handle_auth(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        # ... (kode yang ada dipertahankan) ...
        service = params.get("service")
        # auth_type = params.get("type", "token") 
        credentials = params.get("credentials", {}) 
        if not service: return {"status": "failed", "error": "Nama service diperlukan untuk AUTH."}
        user = credentials.get("user") or credentials.get("token_value")
        if user:
            tempik.execution_context_manager.current_user = user
            logger.info(f"TEMPİK-{tempik.tempik_id_str} AUTH: User '{user}' authenticated for service '{service}' (simulated).")
            return {"status": "success", "authenticated_service": service, "user": user}
        else:
            return {"status": "failed", "error": "User/token tidak disediakan.", "authenticated_service": service}


    async def _handle_mount(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        # ... (kode yang ada dipertahankan) ...
        vfs_path = params.get("target_vfs_path")
        host_path = params.get("source_host_path")
        if not vfs_path or not host_path:
            return {"status": "failed", "error": "source_host_path dan target_vfs_path diperlukan untuk MOUNT."}
        if tempik.execution_mode == ExecutionMode.DRY_RUN:
            return {"status": "dry_run_simulated", "action": "MOUNT", "vfs_path": vfs_path, "host_path": host_path}
        try:
            tempik.virtual_fs.mount_host_path(vfs_path, host_path)
            return {"status": "success", "mounted_vfs": vfs_path, "host_path": host_path}
        except Exception as e: return {"status": "failed", "error": str(e)}


    async def _handle_inject(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        # ... (kode yang ada dipertahankan, dengan penyesuaian untuk VFS async) ...
        vfs_path = params.get("path")
        content_str = params.get("content", "") 
        encoding = params.get("encoding", "utf-8")
        if not vfs_path: return {"status": "failed", "error": "Path VFS diperlukan untuk INJECT."}
        
        content_bytes = b''
        if encoding == "base64":
            import base64
            content_bytes = base64.b64decode(content_str)
        else: content_bytes = content_str.encode(encoding)
            
        resolved_vfs_path = tempik.execution_context_manager.resolve_path(vfs_path)
        if tempik.execution_mode == ExecutionMode.DRY_RUN:
            return {"status": "dry_run_simulated", "action": "INJECT", "path": resolved_vfs_path, "size": len(content_bytes)}
        
        try:
            await tempik.io_handler.write_file(resolved_vfs_path, content_bytes)
            return {"status": "success", "injected_to_vfs": resolved_vfs_path, "size": len(content_bytes)}
        except Exception as e: return {"status": "failed", "error": str(e)}


    async def _handle_export(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        # ... (kode yang ada dipertahankan, dengan penyesuaian untuk VFS async) ...
        source_vfs_path = params.get("source_vfs_path")
        target_name_or_host_path = params.get("target") 
        if not source_vfs_path or not target_name_or_host_path:
            return {"status": "failed", "error": "source_vfs_path dan target diperlukan untuk EXPORT."}

        resolved_source_vfs = tempik.execution_context_manager.resolve_path(source_vfs_path)
        if tempik.execution_mode == ExecutionMode.DRY_RUN:
            return {"status": "dry_run_simulated", "action": "EXPORT", "source": resolved_source_vfs, "target": target_name_or_host_path}

        try:
            if not await tempik.virtual_fs.file_exists(resolved_source_vfs) and not await tempik.virtual_fs.dir_exists(resolved_source_vfs):
                raise FileNotFoundError(f"Source VFS path tidak ditemukan: {resolved_source_vfs}")

            if os.path.isabs(target_name_or_host_path) or target_name_or_host_path.startswith(("./", "../")):
                logger.warning(f"Ekspor ke host path '{target_name_or_host_path}' tidak diimplementasikan langsung oleh Tempik. Akan dikembalikan sebagai data.")
                if await tempik.virtual_fs.file_exists(resolved_source_vfs):
                    content = await tempik.virtual_fs.read_file(resolved_source_vfs)
                    import base64
                    return {"status": "success_data_returned", "export_name": target_name_or_host_path, "data_base64": base64.b64encode(content).decode(), "source_vfs": resolved_source_vfs}
                else: return {"status": "failed", "error": "Ekspor direktori sebagai data belum didukung penuh."}

            if await tempik.virtual_fs.file_exists(resolved_source_vfs):
                content = await tempik.virtual_fs.read_file(resolved_source_vfs)
                tempik.exported_data[target_name_or_host_path] = content
                return {"status": "success", "exported_as_name": target_name_or_host_path, "source_vfs": resolved_source_vfs, "size": len(content)}
            elif await tempik.virtual_fs.dir_exists(resolved_source_vfs):
                # TODO: Implementasi zip VFS direktori
                logger.info(f"Exporting VFS directory {resolved_source_vfs} as {target_name_or_host_path} (simulated zip).")
                return {"status": "pending_zip", "message": "Zip export untuk direktori belum diimplementasikan."}
        except Exception as e: return {"status": "failed", "error": str(e)}
        return {"status": "failed", "error": "Logika export belum lengkap."}


    async def _handle_unpack(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        # ... (kode yang ada dipertahankan, dengan penyesuaian untuk VFS async) ...
        source_vfs_file = params.get("file")
        target_vfs_dir = params.get("target_dir", "/")
        format_type = params.get("format", "auto") # zip, tar.gz, auto-detect

        if not source_vfs_file: return {"status": "failed", "error": "File VFS sumber diperlukan untuk UNPACK."}
        
        resolved_source_vfs = tempik.execution_context_manager.resolve_path(source_vfs_file)
        resolved_target_vfs = tempik.execution_context_manager.resolve_path(target_vfs_dir)

        if tempik.execution_mode == ExecutionMode.DRY_RUN:
            return {"status": "dry_run_simulated", "action": "UNPACK", "source": resolved_source_vfs, "target_dir": resolved_target_vfs}

        try:
            if not await tempik.virtual_fs.file_exists(resolved_source_vfs):
                raise FileNotFoundError(f"File arsip tidak ditemukan di VFS: {resolved_source_vfs}")
            if not await tempik.virtual_fs.dir_exists(resolved_target_vfs):
                tempik.virtual_fs._create_dir_recursive(resolved_target_vfs) # Not async, VFS internal

            archive_bytes = await tempik.virtual_fs.read_file(resolved_source_vfs)
            
            if format_type == "auto":
                if resolved_source_vfs.endswith(".zip"): format_type = "zip"
                elif resolved_source_vfs.endswith((".tar.gz", ".tgz")): format_type = "tar.gz"
                else: return {"status": "failed", "error": "Tidak dapat mendeteksi format arsip."}

            if format_type == "zip":
                import io
                with zipfile.ZipFile(io.BytesIO(archive_bytes), 'r') as zip_ref:
                    for member_name in zip_ref.namelist():
                        member_path_vfs = os.path.join(resolved_target_vfs, member_name).replace('\\', '/')
                        # Pastikan path aman (tidak keluar dari target_vfs_dir)
                        if not os.path.normpath(member_path_vfs).startswith(os.path.normpath(resolved_target_vfs)):
                            logger.warning(f"Potensi Zip Slip terdeteksi: {member_name}. Dilewati.")
                            continue
                        if member_name.endswith('/'): 
                            tempik.virtual_fs._create_dir_recursive(member_path_vfs)
                        else: 
                            dir_of_member = os.path.dirname(member_path_vfs)
                            if dir_of_member and dir_of_member != "/": tempik.virtual_fs._create_dir_recursive(dir_of_member)
                            await tempik.virtual_fs.write_file(member_path_vfs, zip_ref.read(member_name))
                return {"status": "success", "unpacked_to_vfs": resolved_target_vfs}
            # Implementasi tar.gz jika perlu
            else: return {"status": "failed", "error": f"Format arsip tidak didukung: {format_type}"}
        except Exception as e: return {"status": "failed", "error": str(e)}

    # AUDIT POINT 3: Handler baru dan yang diperbaiki
    async def _handle_install(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        package_name = params.get("package")
        version = params.get("version")
        target_dir_vfs = params.get("target_dir", "/deps/installed_pkgs") # Instalasi ke VFS
        
        if not package_name: return {"status": "failed", "error": "Nama package diperlukan untuk INSTALL."}
        logger.info(f"TEMPİK-{tempik.tempik_id_str} INSTALL (simulated): package='{package_name}', version='{version}' to VFS '{target_dir_vfs}'.")
        
        if tempik.execution_mode == ExecutionMode.DRY_RUN:
            return {"status": "dry_run_simulated", "action": "INSTALL", "package": package_name, "version": version}

        # Simulasi: Buat folder package di VFS
        try:
            pkg_path = os.path.join(target_dir_vfs, package_name, version or "latest").replace('\\', '/')
            tempik.virtual_fs._create_dir_recursive(pkg_path) # Not async, VFS internal
            await tempik.virtual_fs.write_file(os.path.join(pkg_path, "installed.marker").replace('\\', '/'), b"installed")
            return {"status": "simulated_success", "message": f"INSTALL {package_name} simulated to {pkg_path}."}
        except Exception as e:
            return {"status": "failed", "error": f"Simulasi INSTALL gagal: {e}"}


    async def _handle_compile(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        source_path_vfs = params.get("source") # Bisa file atau direktori di VFS
        output_name_vfs = params.get("output", "compiled_output") # Nama output di VFS
        compiler_options = params.get("options", "")
        
        if not source_path_vfs: return {"status": "failed", "error": "Path source VFS diperlukan untuk COMPILE."}
        logger.info(f"TEMPİK-{tempik.tempik_id_str} COMPILE (simulated): source='{source_path_vfs}', output='{output_name_vfs}', options='{compiler_options}'.")

        if tempik.execution_mode == ExecutionMode.DRY_RUN:
            return {"status": "dry_run_simulated", "action": "COMPILE", "source": source_path_vfs, "output": output_name_vfs}
        
        # Simulasi: Buat file output placeholder di VFS
        try:
            resolved_source = tempik.execution_context_manager.resolve_path(source_path_vfs)
            if not await tempik.virtual_fs.file_exists(resolved_source) and not await tempik.virtual_fs.dir_exists(resolved_source):
                return {"status": "failed", "error": f"Source VFS tidak ditemukan: {resolved_source}"}

            # Asumsi output adalah file di CWD VFS
            resolved_output = tempik.execution_context_manager.resolve_path(output_name_vfs)
            await tempik.virtual_fs.write_file(resolved_output, f"compiled_content_for_{source_path_vfs}".encode())
            return {"status": "simulated_success", "message": f"COMPILE {source_path_vfs} simulated to {resolved_output}."}
        except Exception as e:
            return {"status": "failed", "error": f"Simulasi COMPILE gagal: {e}"}

    async def _handle_checkout(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        # Biasanya setelah FETCH_REPO, untuk checkout branch/commit tertentu
        repo_vfs_path = params.get("repo_path", "/deps/default_repo") # Path VFS ke repo yang sudah di-fetch
        branch_or_commit = params.get("ref", "main") # Branch, tag, atau commit hash
        logger.info(f"TEMPİK-{tempik.tempik_id_str} CHECKOUT (simulated): repo='{repo_vfs_path}', ref='{branch_or_commit}'.")
        
        if tempik.execution_mode == ExecutionMode.DRY_RUN:
            return {"status": "dry_run_simulated", "action": "CHECKOUT", "repo": repo_vfs_path, "ref": branch_or_commit}

        # Simulasi: Ubah file marker di VFS repo
        try:
            resolved_repo_path = tempik.execution_context_manager.resolve_path(repo_vfs_path)
            if not await tempik.virtual_fs.dir_exists(resolved_repo_path):
                return {"status": "failed", "error": f"Repo VFS tidak ditemukan: {resolved_repo_path}"}
            
            await tempik.virtual_fs.write_file(os.path.join(resolved_repo_path, ".git_ref").replace('\\','/'), branch_or_commit.encode())
            return {"status": "simulated_success", "message": f"CHECKOUT to '{branch_or_commit}' in {resolved_repo_path} simulated."}
        except Exception as e:
            return {"status": "failed", "error": f"Simulasi CHECKOUT gagal: {e}"}

    # AUDIT POINT 3, 4: CALL dan RET
    async def _handle_call(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        target_label = params.get("target_label")
        if not target_label: return {"status": "failed", "error": "Target label diperlukan untuk CALL."}

        if target_label not in tempik.label_map:
            return {"status": "failed", "error": f"Label '{target_label}' tidak ditemukan untuk CALL."}

        if tempik.execution_mode == ExecutionMode.DRY_RUN:
            return {"status": "dry_run_simulated", "action": "CALL", "target": target_label}

        try:
            # 1. Push return address (PC saat ini + 1, karena PC akan increment setelah instruksi CALL selesai dieksekusi oleh pipeline)
            #    Namun, PC di ControlUnit diupdate *setelah* instruksi. Jadi, PC saat ini adalah instruksi *setelah* CALL.
            return_address = tempik.program_counter.value # PC sudah menunjuk ke instruksi berikutnya
            tempik.memory_unit.push_stack(return_address.to_bytes(4, 'big')) # Asumsi alamat 4 byte

            # 2. (Opsional) Push current Frame Pointer (FP)
            current_fp = tempik.register_file.fp
            tempik.memory_unit.push_stack(current_fp.to_bytes(4, 'big'))

            # 3. Set new Frame Pointer (FP) ke Stack Pointer (SP) saat ini
            tempik.register_file.fp = tempik.register_file.sp

            # 4. Jump to target_label
            target_address = tempik.label_map[target_label]
            tempik.program_counter.set(target_address)
            tempik.register_file.pc = target_address # Sinkronkan
            
            logger.debug(f"CALL to {target_label} (addr {target_address}). Return addr {return_address} pushed. New FP: {tempik.register_file.fp}")
            return {"status": "success", "called_label": target_label}
        except MemoryError as me: # Stack overflow
            logger.error(f"Stack overflow saat CALL: {me}")
            tempik.interrupt_controller.raise_interrupt(InterruptType.MEMORY_FAULT, details={"error": "Stack overflow"})
            return {"status": "failed", "error": "Stack overflow"}


    async def _handle_ret(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        if tempik.execution_mode == ExecutionMode.DRY_RUN:
            return {"status": "dry_run_simulated", "action": "RET"}
        try:
            # 1. Restore Stack Pointer (SP) dari Frame Pointer (FP)
            #    Ini membersihkan local variables dari stack frame saat ini.
            #    Jika ada parameter yang di-pass di stack, SP mungkin perlu disesuaikan lebih lanjut.
            tempik.register_file.sp = tempik.register_file.fp 

            # 2. Pop old Frame Pointer (FP)
            old_fp_bytes = tempik.memory_unit.pop_stack(4)
            tempik.register_file.fp = int.from_bytes(old_fp_bytes, 'big')

            # 3. Pop return address dan jump
            return_address_bytes = tempik.memory_unit.pop_stack(4)
            return_address = int.from_bytes(return_address_bytes, 'big')
            
            tempik.program_counter.set(return_address)
            tempik.register_file.pc = return_address # Sinkronkan
            
            logger.debug(f"RET to addr {return_address}. Restored FP: {tempik.register_file.fp}, SP: {tempik.register_file.sp}")
            return {"status": "success", "returned_to_address": return_address}
        except MemoryError as me: # Stack underflow
            logger.error(f"Stack underflow atau error saat RET: {me}")
            tempik.interrupt_controller.raise_interrupt(InterruptType.MEMORY_FAULT, details={"error": "Stack underflow/error on RET"})
            return {"status": "failed", "error": "Stack underflow/error on RET"}

    # AUDIT POINT 3: SPAWN_THREAD
    async def _handle_spawn_thread(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        target_label = params.get("target_label") # Label fungsi yang akan dijalankan di thread baru
        thread_params = params.get("params", {}) # Parameter untuk fungsi thread
        
        if not target_label: return {"status": "failed", "error": "Target label diperlukan untuk SPAWN_THREAD."}
        if target_label not in tempik.label_map:
            return {"status": "failed", "error": f"Label '{target_label}' tidak ditemukan untuk SPAWN_THREAD."}

        logger.info(f"TEMPİK-{tempik.tempik_id_str} SPAWN_THREAD request for label '{target_label}' (simulated).")
        
        if tempik.execution_mode == ExecutionMode.DRY_RUN:
            return {"status": "dry_run_simulated", "action": "SPAWN_THREAD", "target": target_label}

        # Simulasi:
        # Implementasi nyata bisa berarti:
        # 1. Jika Tempik mendukung multithreading internal: buat task asyncio baru yang memulai eksekusi dari target_label
        #    dengan context (register, stack) yang terisolasi atau dibagi secara hati-hati.
        # 2. Jika UTEK level: minta UTEKVirtualExecutor untuk membuat Tempik baru (atau menggunakan yang idle)
        #    untuk menjalankan sub-program ini. Ini lebih mirip DELEGATE_TO tapi mungkin lebih ringan.
        
        # Untuk saat ini, kita simulasikan dengan log dan tidak ada eksekusi paralel nyata di dalam satu Tempik.
        # Bisa juga menggunakan ThreadPoolExecutor jika operasinya CPU-bound.
        # tempik.parent_executor.schedule_sub_task(tempik_id=tempik.tempik_id, 
        #                                          start_label=target_label, 
        #                                          params=thread_params)
        
        # Placeholder:
        tempik.background_tasks_info.append({"label": target_label, "params": thread_params, "status": "spawned_simulated"})
        return {"status": "simulated_thread_spawned", "target_label": target_label}

    async def _handle_wait(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        duration_s = params.get("duration_seconds", 1.0)
        # event_to_wait_for = params.get("event_name") # Menunggu event tertentu
        logger.info(f"TEMPİK-{tempik.tempik_id_str} WAIT for {duration_s}s (simulated).")
        if tempik.execution_mode != ExecutionMode.DRY_RUN:
            await asyncio.sleep(float(duration_s))
        return {"status": "success", "waited_seconds": duration_s}


    async def _handle_delegate_to(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        # ... (kode yang ada dipertahankan) ...
        asu_file_vfs_path = params.get("asu_file_vfs_path") 
        input_params = params.get("input_params", {}) 
        if not asu_file_vfs_path: return {"status": "failed", "error": "asu_file_vfs_path diperlukan."}
        
        resolved_path = tempik.execution_context_manager.resolve_path(asu_file_vfs_path)
        if tempik.execution_mode == ExecutionMode.DRY_RUN:
            return {"status": "dry_run_simulated", "action": "DELEGATE_TO", "target_asu": resolved_path}

        if not await tempik.virtual_fs.file_exists(resolved_path):
            return {"status": "failed", "error": f"File .asu untuk delegasi tidak ditemukan di VFS: {resolved_path}"}

        tempik.delegation_request = {"asu_vfs_path": resolved_path, "params": input_params, "source_tempik_id": tempik.tempik_id}
        logger.info(f"TEMPİK-{tempik.tempik_id_str} DELEGATE_TO request: {resolved_path} with params {input_params}.")
        # Tempik saat ini akan menunggu (atau bisa juga tidak, tergantung behavior yang diinginkan)
        # Untuk membuatnya menunggu, status Tempik bisa diubah dan Scheduler akan menghindarinya.
        # tempik.set_status(TempikStatus.WAITING_FOR_DELEGATION)
        return {"status": "delegation_requested", "target_asu": resolved_path}

    # AUDIT POINT 3: PUSH_RESULT
    async def _handle_push_result(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        destination_url = params.get("destination_url")
        data_to_push = params.get("data") # Bisa dict, atau path VFS ke file yang kontennya akan di-push
        
        if not destination_url: return {"status": "failed", "error": "destination_url diperlukan untuk PUSH_RESULT."}
        if data_to_push is None: return {"status": "failed", "error": "Data diperlukan untuk PUSH_RESULT."}

        logger.info(f"TEMPİK-{tempik.tempik_id_str} PUSH_RESULT to '{destination_url}'.")

        if tempik.execution_mode == ExecutionMode.DRY_RUN:
            return {"status": "dry_run_simulated", "action": "PUSH_RESULT", "destination": destination_url}

        actual_data = data_to_push
        if isinstance(data_to_push, str): # Cek apakah ini path VFS
            resolved_path = tempik.execution_context_manager.resolve_path(data_to_push)
            if await tempik.virtual_fs.file_exists(resolved_path):
                try:
                    actual_data = (await tempik.virtual_fs.read_file(resolved_path)).decode('utf-8') # Asumsi teks
                except Exception as e:
                    return {"status": "failed", "error": f"Gagal baca data dari VFS {resolved_path} untuk PUSH_RESULT: {e}"}
        
        return await tempik.network_unit.push_result(destination_url, actual_data, tempik)


    async def _handle_map_port(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        # ... (kode yang ada dipertahankan) ...
        internal_port = params.get("internal_port")
        external_port_suggestion = params.get("external_port_suggestion")
        protocol = params.get("protocol", "tcp")
        if not internal_port: return {"status": "failed", "error": "internal_port diperlukan."}
        
        logger.info(f"TEMPİK-{tempik.tempik_id_str} MAP_PORT request: internal={internal_port}, suggested_external={external_port_suggestion}, proto={protocol} (simulated).")
        
        if tempik.execution_mode == ExecutionMode.DRY_RUN:
             return {"status": "dry_run_simulated", "action": "MAP_PORT", "params": params}

        tempik.port_mapping_requests.append(params)
        return {"status": "success", "port_mapping_requested": params}

    async def _handle_invoke_remote(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        # ... (kode yang ada dipertahankan) ...
        endpoint = params.get("endpoint")
        method = params.get("method", "POST")
        payload = params.get("payload") 
        headers = params.get("headers")
        if not endpoint: return {"status": "failed", "error": "Endpoint diperlukan."}
        
        if tempik.execution_mode == ExecutionMode.DRY_RUN:
            return {"status": "dry_run_simulated", "action": "INVOKE_REMOTE", "endpoint": endpoint, "method": method}
        
        return await tempik.network_unit.invoke_remote(endpoint, method, payload, headers)


    async def _handle_emit_event(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        # ... (kode yang ada dipertahankan) ...
        event_type = params.get("type", "custom_event")
        event_data = params.get("data", {})
        logger.info(f"EVENT EMITTED by TEMPİK-{tempik.tempik_id_str}: Type='{event_type}', Data={event_data}")
        if tempik.parent_executor:
            tempik.parent_executor.publish_event(tempik.tempik_id_str, event_type, event_data)
        return {"status": "success", "event_type": event_type, "event_data": event_data}

    async def _handle_sign(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        # ... (kode yang ada dipertahankan, dengan penyesuaian untuk VFS async) ...
        data_to_sign_str_or_path = params.get("data") 
        key_id_or_vfs_path = params.get("private_key_ref") # Opsional, jika tidak, gunakan kunci default Tempik
        output_variable_name = params.get("output_env_var") # Simpan signature ke env var Tempik
        
        if not data_to_sign_str_or_path: return {"status": "failed", "error": "Data untuk di-sign diperlukan."}
        
        data_bytes = b''
        resolved_data_path = tempik.execution_context_manager.resolve_path(str(data_to_sign_str_or_path))
        if await tempik.virtual_fs.file_exists(resolved_data_path):
            data_bytes = await tempik.virtual_fs.read_file(resolved_data_path)
        else: data_bytes = str(data_to_sign_str_or_path).encode('utf-8')

        # Load private key jika spesifik atau pastikan default ada
        active_crypto_engine = tempik.crypto_engine
        if key_id_or_vfs_path: # Jika kunci spesifik diminta
            # Ini bisa jadi rumit, mungkin perlu engine kripto terpisah atau manajemen kunci yang lebih baik
            # Untuk sekarang, kita asumsikan ini me-load ke engine utama Tempik (bisa berbahaya jika tidak diisolasi)
            try:
                key_pem_bytes = await tempik.virtual_fs.read_file(tempik.execution_context_manager.resolve_path(key_id_or_vfs_path))
                active_crypto_engine.load_private_key(key_pem_bytes) # Password jika ada
            except Exception as e: return {"status": "failed", "error": f"Gagal load private key dari VFS {key_id_or_vfs_path}: {e}"}
        else: # Gunakan kunci default Tempik (pastikan ada)
            active_crypto_engine.generate_key_pair_if_needed() 
        
        if not active_crypto_engine.private_key:
            return {"status": "failed", "error": "Private key tidak tersedia untuk SIGN."}

        if tempik.execution_mode == ExecutionMode.DRY_RUN:
            return {"status": "dry_run_simulated", "action": "SIGN", "data_hash_preview": hashlib.sha256(data_bytes).hexdigest()[:16]}

        try:
            signature_bytes = active_crypto_engine.sign_data(data_bytes)
            signature_hex = signature_bytes.hex()
            result = {"status": "success", "data_signed_hash": hashlib.sha256(data_bytes).hexdigest(), "signature_hex": signature_hex}
            if output_variable_name:
                tempik.execution_context_manager.set_env_var(output_variable_name, signature_hex)
                result["output_env_var_set"] = output_variable_name
            return result
        except Exception as e: return {"status": "failed", "error": f"Gagal melakukan signing: {e}"}


    async def _handle_decrypt(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        # ... (kode yang ada dipertahankan, dengan penyesuaian untuk VFS async) ...
        ciphertext_hex_or_vfs_path = params.get("ciphertext")
        key_id_or_vfs_path = params.get("private_key_ref")
        output_vfs_path = params.get("output_vfs_path") 
        output_env_var = params.get("output_env_var")

        if not ciphertext_hex_or_vfs_path: return {"status": "failed", "error": "Ciphertext diperlukan."}

        ciphertext_bytes = b''
        resolved_cipher_path = tempik.execution_context_manager.resolve_path(str(ciphertext_hex_or_vfs_path))
        if await tempik.virtual_fs.file_exists(resolved_cipher_path):
            ciphertext_bytes = await tempik.virtual_fs.read_file(resolved_cipher_path)
        else:
            try: ciphertext_bytes = bytes.fromhex(str(ciphertext_hex_or_vfs_path))
            except ValueError: return {"status": "failed", "error": "Ciphertext bukan hex string yang valid atau path VFS."}
        
        active_crypto_engine = tempik.crypto_engine
        if key_id_or_vfs_path:
            try:
                key_pem_bytes = await tempik.virtual_fs.read_file(tempik.execution_context_manager.resolve_path(key_id_or_vfs_path))
                active_crypto_engine.load_private_key(key_pem_bytes)
            except Exception as e: return {"status": "failed", "error": f"Gagal load private key dari VFS {key_id_or_vfs_path}: {e}"}
        else: active_crypto_engine.generate_key_pair_if_needed()

        if not active_crypto_engine.private_key:
            return {"status": "failed", "error": "Private key tidak tersedia untuk DECRYPT."}
        
        if tempik.execution_mode == ExecutionMode.DRY_RUN:
            return {"status": "dry_run_simulated", "action": "DECRYPT"}
            
        try:
            plaintext_bytes = active_crypto_engine.decrypt_data(ciphertext_bytes)
            result_payload = {}
            if output_vfs_path:
                resolved_output_path = tempik.execution_context_manager.resolve_path(output_vfs_path)
                await tempik.io_handler.write_file(resolved_output_path, plaintext_bytes)
                result_payload = {"status": "success", "decrypted_to_vfs": resolved_output_path}
            elif output_env_var:
                try:
                    plaintext_str = plaintext_bytes.decode('utf-8')
                    tempik.execution_context_manager.set_env_var(output_env_var, plaintext_str)
                    result_payload = {"status": "success", "decrypted_to_env_var": output_env_var}
                except UnicodeDecodeError:
                    import base64
                    tempik.execution_context_manager.set_env_var(output_env_var, base64.b64encode(plaintext_bytes).decode())
                    result_payload = {"status": "success", "decrypted_to_env_var_base64": output_env_var}
            else: # Kembalikan sebagai string (jika aman) atau base64
                try: result_payload = {"status": "success", "plaintext": plaintext_bytes.decode('utf-8')}
                except UnicodeDecodeError:
                    import base64
                    result_payload = {"status": "success", "plaintext_base64": base64.b64encode(plaintext_bytes).decode()}
            return result_payload
        except Exception as e: return {"status": "failed", "error": f"Gagal melakukan dekripsi: {e}"}


    async def _handle_verify(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        # ... (kode yang ada dipertahankan, dengan penyesuaian untuk VFS async) ...
        data_str_or_vfs_path = params.get("data")
        signature_hex = params.get("signature_hex")
        public_key_ref = params.get("public_key_ref") 

        if not data_str_or_vfs_path or not signature_hex:
            return {"status": "failed", "error": "Data dan signature_hex diperlukan."}

        data_bytes = b''
        resolved_data_path = tempik.execution_context_manager.resolve_path(str(data_str_or_vfs_path))
        if await tempik.virtual_fs.file_exists(resolved_data_path):
            data_bytes = await tempik.virtual_fs.read_file(resolved_data_path)
        else: data_bytes = str(data_str_or_vfs_path).encode('utf-8')
        
        try: signature_bytes = bytes.fromhex(signature_hex)
        except ValueError: return {"status": "failed", "error": "Signature bukan hex string yang valid."}

        active_crypto_engine = tempik.crypto_engine
        if public_key_ref: 
            try:
                key_pem_bytes = await tempik.virtual_fs.read_file(tempik.execution_context_manager.resolve_path(public_key_ref))
                active_crypto_engine.load_public_key(key_pem_bytes)
            except Exception as e: return {"status": "failed", "error": f"Gagal load public key dari VFS {public_key_ref}: {e}"}
        else: active_crypto_engine.generate_key_pair_if_needed() # Pastikan ada public key (meski mungkin dari private)
        
        if not active_crypto_engine.public_key:
            return {"status": "failed", "error": "Public key tidak tersedia untuk VERIFY."}

        is_valid = active_crypto_engine.verify_signature(data_bytes, signature_bytes)
        if not is_valid:
            logger.warning(f"VERIFY signature GAGAL untuk data (hash: {hashlib.sha256(data_bytes).hexdigest()[:16]}), signature: {signature_hex[:16]}")
        return {"status": "success", "signature_verified": is_valid}


    async def _handle_lock_exec(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        # ... (kode yang ada dipertahankan) ...
        file_hash_to_lock = params.get("file_hash", tempik.current_file_hash) 
        if tempik.parent_executor:
            tempik.parent_executor.lock_execution(file_hash_to_lock)
        else: tempik.lock_requests.append(file_hash_to_lock) # Jika tidak ada parent, catat saja
        logger.info(f"TEMPİK-{tempik.tempik_id_str} LOCK_EXEC request for hash: {file_hash_to_lock}.")
        return {"status": "success", "lock_requested_for_hash": file_hash_to_lock}

    async def _handle_alu_op(self, tempik: 'Tempik', params: Dict[str, Any]) -> Dict[str, Any]:
        # ... (kode yang ada dipertahankan, dengan penyesuaian untuk InstruksiASU dan float) ...
        instr_obj = tempik.register_file.instruction_register
        if not instr_obj: return {"status": "failed", "error": "Instruction register kosong untuk operasi ALU."}
        
        op_name_enum = instr_obj.instruksi
        
        op1_src = params.get("operand1_reg", params.get("operand1_freg"))
        op1_val_src = params.get("operand1_val", params.get("operand1_fval"))
        op2_src = params.get("operand2_reg", params.get("operand2_freg"))
        op2_val_src = params.get("operand2_val", params.get("operand2_fval"))
        dest_reg_idx = params.get("dest_reg", params.get("dest_freg"))

        is_float_op = op_name_enum.value.startswith("F")

        op1: Union[int, float]
        op2: Union[int, float]

        try:
            if op1_src is not None:
                op1 = tempik.register_file.read_float_register(op1_src) if is_float_op else tempik.register_file.read_register(op1_src)
            elif op1_val_src is not None:
                op1 = float(op1_val_src) if is_float_op else int(op1_val_src)
            else: return {"status": "failed", "error": "Operand 1 tidak ditemukan untuk operasi ALU."}

            if op2_src is not None:
                op2 = tempik.register_file.read_float_register(op2_src) if is_float_op else tempik.register_file.read_register(op2_src)
            elif op2_val_src is not None:
                op2 = float(op2_val_src) if is_float_op else int(op2_val_src)
            else: return {"status": "failed", "error": "Operand 2 tidak ditemukan untuk operasi ALU."}
        except ValueError as ve:
             return {"status": "failed", "error": f"Error konversi operand ALU: {ve}"}


        if tempik.execution_mode == ExecutionMode.DRY_RUN and op_name_enum not in [InstruksiASU.CMP, InstruksiASU.FCMP]:
            return {"status": "dry_run_simulated", "action": op_name_enum.value, "operands": [op1, op2]}

        try:
            result = tempik.alu.execute(op_name_enum, op1, op2)
        except ZeroDivisionError:
            return {"status": "failed", "error": "Pembagian dengan nol di ALU."}
        except Exception as e:
            return {"status": "failed", "error": f"Error ALU: {e}"}


        if op_name_enum not in [InstruksiASU.CMP, InstruksiASU.FCMP]: 
            if dest_reg_idx is not None:
                if is_float_op: tempik.register_file.write_float_register(dest_reg_idx, float(result))
                else: tempik.register_file.write_register(dest_reg_idx, int(result))
                return {"status": "success", "result": result, "dest_reg": dest_reg_idx, "flags": tempik.register_file.flags}
            else: 
                return {"status": "success", "result_no_dest": result, "flags": tempik.register_file.flags}
        else: # Untuk CMP/FCMP
             return {"status": "success", "comparison_result": result, "flags": tempik.register_file.flags}


# --- Kelas Tempik (Refactored) ---

class Tempik: # AUDIT POINT 8 (Isolasi sudah baik dengan instance terpisah)
    def __init__(self, tempik_id: int, audit_logger: AuditLogger, 
                 parent_executor: Optional['UTEKVirtualExecutor'] = None, # AUDIT POINT 2
                 global_config: Optional[Dict] = None): # AUDIT POINT 1, 2
        self.tempik_id = tempik_id
        self.tempik_id_str = f"Tempik-{tempik_id:03d}" # Untuk logging
        self.parent_executor = parent_executor 
        self.status = TempikStatus.IDLE
        self.current_file_hash: Optional[str] = None 
        self.current_instruction_start_time: float = 0.0
        self.global_execution_start_time: float = 0.0 # AUDIT POINT 11
        self.max_exec_time_seconds: Optional[float] = None # AUDIT POINT 11

        # Komponen Inti
        self.register_file = RegisterFile()
        self.program_counter = ProgramCounter() 
        self.alu = ALU(self.register_file)
        # MemoryUnit dan RegisterFile dihubungkan untuk stack
        self.memory_unit = MemoryUnit(register_file_ref=self.register_file) 
        self.instruction_cache = InstructionCache()
        self.data_cache = DataCache() 

        # Modul Fungsional
        self.execution_context_manager = ExecutionContextManager(self.tempik_id_str)
        self.virtual_fs = VirtualFS(self.tempik_id_str, context_manager_ref=self.execution_context_manager) # AUDIT POINT 7
        self.io_handler = IOHandler(self.virtual_fs, self.tempik_id_str)
        self.instruction_decoder = InstructionDecoder(self.register_file)
        self.crypto_engine = CryptoEngine() 
        self.network_unit = NetworkUnit(self.execution_context_manager, self.tempik_id_str)
        self.security_module = SecurityModule(self.execution_context_manager, self.crypto_engine)
        self.audit_logger = audit_logger 
        self.interrupt_controller = InterruptController() # AUDIT POINT 6
        self.profiler = Profiler(self.tempik_id_str) # AUDIT POINT 16
        
        # Kontrol dan Program
        self.instruction_set = InstructionSet() 
        self.control_unit = ControlUnit(self) 
        self.program_memory: List[InstruksiEksekusi] = []
        self.label_map: Dict[str, int] = {} 

        # Hasil dan Permintaan Antar Komponen
        self.exported_data: Dict[str, bytes] = {} 
        self.port_mapping_requests: List[Dict] = [] 
        self.delegation_request: Optional[Dict] = None 
        self.lock_requests: List[str] = [] 
        self.background_tasks_info: List[Dict] = [] # Untuk SPAWN_THREAD (AUDIT POINT 3)

        self.execution_mode: ExecutionMode = ExecutionMode.BATCH # Default (AUDIT POINT 15)

        # AUDIT POINT 17: Bus (opsional, untuk arsitektur mikro lebih detail)
        # self.instruction_bus = Bus(f"{self.tempik_id_str}-InstructionBus")
        # self.memory_bus = Bus(f"{self.tempik_id_str}-MemoryBus")
        # self.memory_unit.bus = self.memory_bus # MemoryUnit bisa publish/listen ke MemoryBus

        self._setup_default_interrupt_handlers() # AUDIT POINT 6

    def _setup_default_interrupt_handlers(self):
        # AUDIT POINT 6: Handler default untuk interrupt umum
        def _handle_failure_interrupt(tempik_ref: 'Tempik', type: InterruptType, details: Optional[Dict]):
            logger.error(f"Tempik-{tempik_ref.tempik_id} FAILED due to {type.value}. Details: {details}")
            tempik_ref.set_status(TempikStatus.FAILED)
        
        def _handle_halt_interrupt(tempik_ref: 'Tempik', type: InterruptType, details: Optional[Dict]):
            logger.info(f"Tempik-{tempik_ref.tempik_id} HALTED by {type.value}. Details: {details}")
            tempik_ref.set_status(TempikStatus.HALTED)

        failure_types = [
            InterruptType.INVALID_INSTRUCTION, InterruptType.MEMORY_FAULT, 
            InterruptType.SECURITY_VIOLATION, InterruptType.MAX_INSTRUCTIONS_REACHED,
            InterruptType.ASSERTION_FAILURE, InterruptType.ARITHMETIC_ERROR,
            InterruptType.RESOURCE_LIMIT_EXCEEDED, InterruptType.TIMER_EXPIRED # Timer expired juga FAILED
        ]
        forftype in failure_types:
            self.interrupt_controller.register_handler(ftype, _handle_failure_interrupt)
        
        self.interrupt_controller.register_handler(InterruptType.HALT_REQUESTED, _handle_halt_interrupt)
        # Handler lain bisa ditambahkan (IO_COMPLETED, etc.)


    def load_program(self, program_instructions: List[InstruksiEksekusi], initial_pc: int = 0):
        self.program_memory = program_instructions
        self.program_counter.set(initial_pc)
        self.register_file.pc = initial_pc 
        self.label_map.clear()
        for i, instr in enumerate(program_instructions):
            if instr.label:
                if instr.label in self.label_map:
                    logger.warning(f"Label duplikat ditemukan: {instr.label} di alamat {i} dan {self.label_map[instr.label]}")
                self.label_map[instr.label] = i
        logger.info(f"{self.tempik_id_str}: Program ({len(program_instructions)} instructions) loaded. PC set to {initial_pc}.")

    def jump_to_label(self, label: str):
        if label in self.label_map:
            target_address = self.label_map[label]
            self.program_counter.set(target_address)
            self.register_file.pc = target_address
            logger.debug(f"{self.tempik_id_str}: Jumping to label '{label}' (address {target_address}).")
        else:
            logger.error(f"{self.tempik_id_str}: Label '{label}' tidak ditemukan untuk JMP/BRANCH.")
            self.interrupt_controller.raise_interrupt(InterruptType.INVALID_JUMP_LABEL, details={"label": label})
            # Status akan diubah oleh handler interrupt


    async def run(self, file_asu: FileASU):
        self.set_status(TempikStatus.BUSY) 
        self.current_file_hash = file_asu.hash_sha256
        self.execution_context_manager.env_vars.clear() 
        self.execution_context_manager.current_working_directory = "/" 
        self.virtual_fs = VirtualFS(self.tempik_id_str, context_manager_ref=self.execution_context_manager) # Reset VFS
        if file_asu.virtual_fs_structure: 
            await self.virtual_fs.populate_from_dict(file_asu.virtual_fs_structure)

        # Apply header info ke context
        self.execution_context_manager.security_policy["flags"] = file_asu.header.security_flags.split(',')
        self.execution_context_manager.security_policy["networking_mode"] = file_asu.header.networking_mode
        self.max_exec_time_seconds = file_asu.header.get_max_exec_time_seconds() # AUDIT POINT 11
        try: # AUDIT POINT 15
            self.execution_mode = ExecutionMode(file_asu.header.execution_mode)
        except ValueError:
            logger.warning(f"Execution mode tidak valid: {file_asu.header.execution_mode}. Default ke BATCH.")
            self.execution_mode = ExecutionMode.BATCH
        
        # Parse memory_profile dan set ukuran MemoryUnit jika perlu (belum diimplementasikan dinamis)
        # self.memory_unit.resize(parse_memory_profile(file_asu.header.memory_profile))

        # Verifikasi signature .asu jika ada kunci publik global (AUDIT POINT 13)
        if self.parent_executor and self.parent_executor.global_public_key_for_verification_pem:
           if not self.security_module.verify_asu_signature(file_asu, self.parent_executor.global_public_key_for_verification_pem):
               logger.error(f"{self.tempik_id_str}: Verifikasi signature file .asu GAGAL.")
               self.set_status(TempikStatus.FAILED)
               return # Jangan jalankan jika signature gagal

        logger.info(f"{self.tempik_id_str} memulai eksekusi file .asu: {self.current_file_hash[:12]}...")
        await self.control_unit.start_execution(file_asu.body)
        logger.info(f"{self.tempik_id_str} selesai eksekusi file .asu: {self.current_file_hash[:12]}. Status akhir: {self.status.value}")
        
        # Jika service mode, mungkin tidak langsung COMPLETED
        if self.execution_mode == ExecutionMode.SERVICE and self.status == TempikStatus.COMPLETED:
            logger.info(f"{self.tempik_id_str} dalam mode SERVICE, tetap running (simulasi).")
            # Di sini bisa masuk ke loop event atau tunggu sinyal shutdown
            # self.status = TempikStatus.IDLE # Atau status khusus SERVICE_RUNNING

    def set_status(self, new_status: TempikStatus):
        if self.status != new_status: # Hanya log jika ada perubahan
            logger.debug(f"{self.tempik_id_str}: Status changed from {self.status.value} to {new_status.value}")
            self.status = new_status
            if self.parent_executor: # Notifikasi TempikManager/Scheduler (AUDIT POINT 2)
                self.parent_executor.notify_tempik_status_change(self.tempik_id, new_status)


    def get_status_summary(self) -> Dict[str, Any]:
        instr_val = "N/A"
        if self.register_file.instruction_register and self.register_file.instruction_register.instruksi:
            instr_val = self.register_file.instruction_register.instruksi.value
        return {
            "tempik_id": self.tempik_id,
            "status": self.status.value,
            "pc": self.program_counter.value,
            "sp": self.register_file.sp, # AUDIT POINT 4
            "fp": self.register_file.fp, # AUDIT POINT 4
            "flags": self.register_file.flags,
            "current_instruction": instr_val,
            "cwd_vfs": self.execution_context_manager.current_working_directory,
            "execution_mode": self.execution_mode.value, # AUDIT POINT 15
            "profiler_summary_sample": list(self.profiler.get_summary().keys())[:3] # AUDIT POINT 16
        }

    def check_global_timeout(self): # AUDIT POINT 11 (Watchdog)
        if self.max_exec_time_seconds is not None and self.global_execution_start_time > 0:
            elapsed_time = time.time() - self.global_execution_start_time
            if elapsed_time > self.max_exec_time_seconds:
                logger.warning(f"{self.tempik_id_str}: Global execution timeout ({elapsed_time:.2f}s > {self.max_exec_time_seconds}s).")
                self.interrupt_controller.raise_interrupt(InterruptType.TIMER_EXPIRED, 
                                                            details={"type": "global_watchdog", "limit_s": self.max_exec_time_seconds})
                # Handler interrupt akan set status FAILED


# --- Scheduler dan TempikManager (Bagian dari UTEKVirtualExecutor) ---
# AUDIT POINT 1 & 2: Scheduler dan TempikManager
# UTEKVirtualExecutor akan berperan sebagai TempikManager/TempikFarm.
# Scheduler akan menjadi komponen di dalamnya.

class Scheduler: # AUDIT POINT 1 (Multi-Tempik Scheduling)
    def __init__(self, tempik_pool: List[Tempik], parent_executor: 'UTEKVirtualExecutor'):
        self.tempik_pool = tempik_pool
        self.parent_executor = parent_executor
        self.task_queue: asyncio.Queue[Tuple[FileASU, Optional[int]]] = asyncio.Queue() # (file_asu, optional_target_tempik_id)
        self.tempik_assignment: Dict[int, Optional[FileASU]] = {t.tempik_id: None for t in tempik_pool}
        # Untuk ThreadPoolExecutor (jika ada instruksi CPU-bound yang perlu di-offload dari event loop utama Tempik)
        self.cpu_bound_executor = ThreadPoolExecutor(max_workers=max(1, os.cpu_count() // 2 if os.cpu_count() else 1))


    async def submit_task(self, file_asu: FileASU, target_tempik_id: Optional[int] = None):
        await self.task_queue.put((file_asu, target_tempik_id))
        logger.info(f"SCHEDULER: File .asu {file_asu.hash_sha256[:12]} ditambahkan ke antrian (target: {target_tempik_id}).")

    async def run_scheduler_loop(self):
        logger.info(f"SCHEDULER: Loop dimulai. Mengelola {len(self.tempik_pool)} Tempik.")
        while not self.parent_executor.is_shutting_down: # Loop utama scheduler
            try:
                file_asu_to_run, target_tempik_id = await asyncio.wait_for(self.task_queue.get(), timeout=0.5) # Tunggu task baru
                
                assigned_tempik: Optional[Tempik] = None
                if target_tempik_id is not None: # Jika ada target spesifik
                    tempik = next((t for t in self.tempik_pool if t.tempik_id == target_tempik_id), None)
                    if tempik and tempik.status == TempikStatus.IDLE:
                        assigned_tempik = tempik
                    else:
                        logger.warning(f"SCHEDULER: Target Tempik-{target_tempik_id} tidak tersedia atau tidak idle. Mencari Tempik lain.")
                
                if not assigned_tempik: # Cari Tempik idle jika tidak ada target atau target tidak tersedia
                    # Strategi load balancing sederhana: round-robin atau cari yang pertama idle
                    idle_tempiks = [t for t in self.tempik_pool if t.status == TempikStatus.IDLE]
                    if idle_tempiks:
                        assigned_tempik = random.choice(idle_tempiks) # Atau strategi lain
                
                if assigned_tempik:
                    logger.info(f"SCHEDULER: Menugaskan {file_asu_to_run.hash_sha256[:12]} ke {assigned_tempik.tempik_id_str}.")
                    self.tempik_assignment[assigned_tempik.tempik_id] = file_asu_to_run
                    assigned_tempik.set_status(TempikStatus.BUSY) # Tandai BUSY sebelum task dimulai
                    # Jalankan Tempik.run dalam task asyncio terpisah (non-blocking)
                    asyncio.create_task(assigned_tempik.run(file_asu_to_run)) 
                else:
                    logger.warning(f"SCHEDULER: Tidak ada Tempik idle. Mengembalikan {file_asu_to_run.hash_sha256[:12]} ke antrian.")
                    await self.task_queue.put((file_asu_to_run, target_tempik_id)) # Kembalikan ke antrian
                
                self.task_queue.task_done()

            except asyncio.TimeoutError:
                # Tidak ada task baru, bisa lakukan housekeeping atau cek status Tempik
                pass 
            except Exception as e:
                logger.error(f"SCHEDULER: Error dalam loop: {e}", exc_info=True)
            
            await asyncio.sleep(0.01) # Cek berkala, jangan terlalu sering agar tidak membebani CPU

    def shutdown(self):
        self.cpu_bound_executor.shutdown(wait=True)
        logger.info("Scheduler CPU-bound executor shutdown.")


# --- UTEKVirtualExecutor (Refactored sebagai TempikManager/TempikFarm) ---
# AUDIT POINT 2: UTEKVirtualExecutor sebagai TempikManager
class UTEKVirtualExecutor:
    def __init__(self, num_tempik_engines: int = 8): # AUDIT POINT 1 (jumlah Tempik)
        if not 1 <= num_tempik_engines <= 963: # Batas sesuai konsep 963-Tempik
            logger.warning(f"Jumlah Tempik ({num_tempik_engines}) di luar rentang aman (1-963). Disesuaikan ke 8.")
            num_tempik_engines = 8
            
        self.num_tempik_engines = num_tempik_engines
        self.audit_logger = AuditLogger() 
        
        # AUDIT POINT 8: Isolasi sudah ditangani di Tempik (tiap Tempik punya VFS & Context sendiri)
        self.tempik_pool: List[Tempik] = [Tempik(i, self.audit_logger, self) for i in range(num_tempik_engines)]
        self.scheduler = Scheduler(self.tempik_pool, self)
        
        self.locked_executions: Set[str] = set() 
        self.global_private_key_for_signing_pem: Optional[bytes] = None # Untuk menandatangani .asu yang dibuat
        self.global_public_key_for_verification_pem: Optional[bytes] = None # Untuk verifikasi .asu yang diterima
        self.crypto_engine_for_asu_mgnt = CryptoEngine() # Untuk sign/verify .asu oleh executor

        self.is_shutting_down = False
        self.event_listeners: Dict[str, List[Callable]] = {} # AUDIT POINT 6 (event listener global)

        # AUDIT POINT 12: Bootloader / Entry Point Executor (CLI/API akan menggunakan metode di kelas ini)
        logger.info(f"UTEKVirtualExecutor (TempikManager) initialized with {num_tempik_engines} Tempik engines.")

    def load_global_keys(self, private_key_path: Optional[str] = None, public_key_path: Optional[str] = None):
        # AUDIT POINT 13: Signature signing saat generate .asu
        if private_key_path and os.path.exists(private_key_path):
            with open(private_key_path, 'rb') as f:
                self.global_private_key_for_signing_pem = f.read()
                self.crypto_engine_for_asu_mgnt.load_private_key(self.global_private_key_for_signing_pem)
            logger.info(f"Global private key untuk signing .asu di-load dari {private_key_path}.")
        
        if public_key_path and os.path.exists(public_key_path):
            with open(public_key_path, 'rb') as f:
                self.global_public_key_for_verification_pem = f.read()
                # Crypto engine untuk verifikasi bisa berbeda, atau gunakan yang sama jika public key juga di-load ke sana
                # self.crypto_engine_for_asu_mgnt.load_public_key(self.global_public_key_for_verification_pem)
            logger.info(f"Global public key untuk verifikasi .asu di-load dari {public_key_path}.")


    def parse_asu_file(self, file_path: str) -> FileASU: # AUDIT POINT 10 (load_from_file)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File .asu tidak ditemukan: {file_path}")
        if not file_path.endswith('.asu'):
            raise ValueError("File harus memiliki ekstensi .asu")

        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read() # Baca seluruh file dulu untuk validasi ukuran
            
            # AUDIT POINT 9: Validasi Ukuran Maksimum .asu (sebelum dekompresi)
            # Header belum bisa dibaca untuk max_size sebelum dekompresi.
            # Ini adalah batasan. Validasi ukuran sebenarnya dilakukan setelah dekompresi
            # berdasarkan header.max_size. Ukuran file mentah bisa dicek terhadap batas global jika ada.
            # global_max_raw_size = 100 * 1024 * 1024 # Misal, 100MB untuk file terkompresi
            # if len(raw_data) > global_max_raw_size:
            #    raise ValueError(f"Ukuran file .asu terkompresi ({len(raw_data)} bytes) melebihi batas global.")

            data = b''
            compression_type = "none"
            if raw_data.startswith(b'\x1f\x8b'):  # gzip
                data = gzip.decompress(raw_data)
                compression_type = "gzip"
            elif raw_data.startswith(b'\x04\x22\x4d\x18'):  # lz4
                data = lz4.frame.decompress(raw_data)
                compression_type = "lz4"
            else: data = raw_data 
            
            content = json.loads(data.decode('utf-8'))
            
            if 'header' not in content or 'body' not in content:
                raise ValueError("Struktur file .asu tidak valid - header dan body diperlukan")
            
            header = HeaderASU.from_dict(content['header'])

            # AUDIT POINT 9: Validasi ukuran dekompresi terhadap header.max_size
            max_size_bytes_from_header = header.get_max_size_bytes()
            if len(data) > max_size_bytes_from_header:
                raise ValueError(f"Ukuran konten .asu ({len(data)} bytes) melebihi batas max_size di header ({max_size_bytes_from_header} bytes).")

            # Konsistensi info kompresi
            if header.compression_info != compression_type and header.compression_info != "none" and compression_type != "none":
                 logger.warning(f"Mismatch info kompresi: header '{header.compression_info}', actual '{compression_type}'.")


            body_instructions = []
            vfs_structure_from_body = {}
            # Penanganan body yang bisa list (lama) atau dict (baru dengan VFS)
            if isinstance(content['body'], list): 
                for instr_data in content['body']:
                    body_instructions.append(InstruksiEksekusi.from_dict(instr_data))
            elif isinstance(content['body'], dict): 
                main_seq_data = content['body'].get('main_sequence', content['body'].get('instructions', []))
                for instr_data in main_seq_data:
                     body_instructions.append(InstruksiEksekusi.from_dict(instr_data))
                vfs_structure_from_body = content['body'].get('virtual_fs', {})

            file_asu = FileASU(header=header, body=body_instructions, virtual_fs_structure=vfs_structure_from_body)
            file_asu.generate_hash() # Hitung hash konten (tanpa signature di header)
            
            # Verifikasi signature jika ada (AUDIT POINT 13)
            if file_asu.header.checksum_signature and self.global_public_key_for_verification_pem:
                temp_security_module = SecurityModule(ExecutionContextManager("verifier"), self.crypto_engine_for_asu_mgnt)
                if not temp_security_module.verify_asu_signature(file_asu, self.global_public_key_for_verification_pem):
                    raise InvalidSignature("Verifikasi signature file .asu GAGAL saat parsing.")
                logger.info(f"Signature file .asu {file_path} berhasil diverifikasi.")
            elif file_asu.header.checksum_signature:
                logger.warning(f"File .asu {file_path} punya signature tapi tidak ada global public key untuk verifikasi.")


            return file_asu
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Format JSON tidak valid dalam file .asu: {e}")
        except InvalidSignature as ise:
            logger.error(f"Error parsing file .asu '{file_path}': Signature tidak valid. {ise}")
            raise
        except Exception as e:
            logger.error(f"Error parsing file .asu '{file_path}': {e}", exc_info=True)
            raise RuntimeError(f"Error parsing file .asu: {e}")
    
    def create_asu_file(self, header: HeaderASU, instructions: List[InstruksiEksekusi], 
                        virtual_fs_structure: Optional[Dict[str,Any]] = None,
                        output_dir: str = ".", sign_if_possible: bool = True) -> str: # AUDIT POINT 10 (save_to_file)
        
        file_asu = FileASU(header=header, body=instructions, virtual_fs_structure=virtual_fs_structure or {})
        
        # AUDIT POINT 13: Signature signing
        if sign_if_possible and self.crypto_engine_for_asu_mgnt.private_key:
            file_asu.sign_file(self.crypto_engine_for_asu_mgnt) # Ini akan set header.checksum_signature dan re-hash
        else:
            file_asu.generate_hash() # Generate hash tanpa signature jika tidak bisa sign

        file_hash_for_name = file_asu.hash_sha256 # Gunakan hash final (setelah sign jika ada)
        filename = f"{file_hash_for_name}.asu" 
        output_path = os.path.join(output_dir, filename)
        
        current_time_iso = datetime.now().isoformat()
        file_asu.header.asu_build_info = f"build-date={current_time_iso}, asu-sdk=refactored-audit-v1"
        
        # Struktur body bisa jadi dict jika ada VFS
        body_content_for_json: Union[List[Dict], Dict[str, Any]]
        if file_asu.virtual_fs_structure:
            body_content_for_json = {
                "main_sequence": [instr.to_dict() for instr in file_asu.body],
                "virtual_fs": file_asu.virtual_fs_structure
            }
        else:
            body_content_for_json = [instr.to_dict() for instr in file_asu.body]

        content_to_serialize = {
            "header": file_asu.header.to_dict(), # Header sudah termasuk signature jika di-sign
            "body": body_content_for_json
        }

        json_data = json.dumps(content_to_serialize, indent=2, ensure_ascii=False, sort_keys=True)
        
        compressed_data = b''
        if header.compression_info == "gzip":
            compressed_data = gzip.compress(json_data.encode('utf-8'))
        elif header.compression_info == "lz4":
            compressed_data = lz4.frame.compress(json_data.encode('utf-8'))
        else: compressed_data = json_data.encode('utf-8')
        
        os.makedirs(output_dir, exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(compressed_data)
        
        logger.info(f"File .asu berhasil dibuat: {output_path} (Hash Konten: {file_asu.hash_sha256})")
        return output_path

    async def execute_asu_file_async(self, file_path: str, target_tempik_id: Optional[int] = None): # AUDIT POINT 12
        if self.is_shutting_down:
            logger.warning("UTEK sedang shutdown, tidak menerima task baru.")
            return {"status": "failed", "error": "UTEK is shutting down."}
            
        try:
            file_asu = self.parse_asu_file(file_path) # Sudah termasuk validasi ukuran & signature
            
            if file_asu.hash_sha256 in self.locked_executions:
                logger.error(f"Eksekusi file {file_asu.hash_sha256} terkunci.")
                return {"status": "failed", "error": "Execution locked."}

            await self.scheduler.submit_task(file_asu, target_tempik_id)
            return {"status": "submitted", "file_hash": file_asu.hash_sha256}
        except Exception as e:
            logger.error(f"Gagal mengirim file .asu {file_path} ke scheduler: {e}", exc_info=True)
            return {"status": "failed", "error": str(e)}

    def lock_execution(self, file_hash: str):
        self.locked_executions.add(file_hash)
        logger.info(f"Eksekusi untuk file hash {file_hash} telah dikunci.")
    
    def unlock_execution(self, file_hash: str):
        self.locked_executions.discard(file_hash)
        logger.info(f"Lock eksekusi untuk file hash {file_hash} telah dibuka.")

    async def start(self): # AUDIT POINT 1, 2, 12
        logger.info(f"UTEKVirtualExecutor (TempikManager) starting with {self.num_tempik_engines} Tempiks...")
        self.scheduler_task = asyncio.create_task(self.scheduler.run_scheduler_loop())
        logger.info("UTEKVirtualExecutor (TempikManager) started. Scheduler is running.")

    async def shutdown(self, reason: str = "Shutdown requested"): # AUDIT POINT 2
        if self.is_shutting_down: return
        logger.info(f"UTEKVirtualExecutor (TempikManager) shutting down... Reason: {reason}")
        self.is_shutting_down = True
        
        if hasattr(self, 'scheduler_task') and self.scheduler_task:
            self.scheduler_task.cancel()
            try: await self.scheduler_task
            except asyncio.CancelledError: logger.info("Scheduler loop cancelled.")
        
        self.scheduler.shutdown() # Shutdown ThreadPoolExecutor di scheduler

        # Halt semua Tempik yang aktif
        halt_tasks = []
        for tempik in self.tempik_pool:
            if tempik.status not in [TempikStatus.IDLE, TempikStatus.COMPLETED, TempikStatus.FAILED, TempikStatus.HALTED]:
                logger.info(f"Requesting HALT for active {tempik.tempik_id_str}")
                # tempik.control_unit.halt_execution("UTEK Shutdown") # Ini bisa jadi sync
                # Lebih baik trigger interrupt yang akan dihandle oleh loop Tempik jika masih jalan
                tempik.interrupt_controller.raise_interrupt(InterruptType.HALT_REQUESTED, 
                                                            details={"reason": "UTEK Shutdown"})
                # Jika Tempik.run adalah task, kita bisa menunggunya.
                # Untuk sekarang, kita asumsikan interrupt akan menghentikannya.
        
        # Beri waktu untuk Tempik menyelesaikan/halt (opsional)
        # await asyncio.sleep(1) 
        
        logger.info("UTEKVirtualExecutor (TempikManager) shutdown complete.")

    def get_sistem_status(self) -> Dict[str, Any]: # AUDIT POINT 2
        tempik_statuses = [t.get_status_summary() for t in self.tempik_pool]
        return {
            "total_tempik_engines": self.num_tempik_engines,
            "scheduler_queue_size": self.scheduler.task_queue.qsize(),
            "active_tempik_assignments": {tid: (f.hash_sha256[:12] if f else None) for tid, f in self.scheduler.tempik_assignment.items() if f},
            "locked_executions_count": len(self.locked_executions),
            "is_shutting_down": self.is_shutting_down,
            "tempik_details": tempik_statuses
        }

    # AUDIT POINT 2: Notifikasi dari Tempik ke Manager
    def notify_tempik_status_change(self, tempik_id: int, new_status: TempikStatus):
        logger.debug(f"TempikManager: Tempik-{tempik_id:03d} status changed to {new_status.value}.")
        if new_status in [TempikStatus.COMPLETED, TempikStatus.FAILED, TempikStatus.HALTED]:
            # Jika Tempik selesai, kosongkan assignment di scheduler
            if self.scheduler.tempik_assignment.get(tempik_id) is not None:
                logger.info(f"TempikManager: Tempik-{tempik_id:03d} (assigned {self.scheduler.tempik_assignment[tempik_id].hash_sha256[:12] if self.scheduler.tempik_assignment[tempik_id] else 'N/A'}) is now free.")
                self.scheduler.tempik_assignment[tempik_id] = None
            # Set Tempik kembali ke IDLE agar bisa dijadwalkan lagi
            tempik = next((t for t in self.tempik_pool if t.tempik_id == tempik_id), None)
            if tempik and tempik.status != TempikStatus.IDLE: # Hindari rekursi jika sudah IDLE
                tempik.set_status(TempikStatus.IDLE) # Ini akan log lagi, tapi OK.

    # AUDIT POINT 6: Event bus global
    def subscribe_to_event(self, event_type: str, callback: Callable):
        self.event_listeners.setdefault(event_type, []).append(callback)
        logger.info(f"Callback {callback.__name__} subscribed to event type '{event_type}'.")

    def publish_event(self, source_id: str, event_type: str, event_data: Dict):
        logger.info(f"Global Event Published by {source_id}: Type='{event_type}', Data={event_data}")
        if event_type in self.event_listeners:
            for callback in self.event_listeners[event_type]:
                try:
                    # Bisa async atau sync callback
                    if asyncio.iscoroutinefunction(callback):
                        asyncio.create_task(callback(source_id, event_type, event_data))
                    else:
                        callback(source_id, event_type, event_data)
                except Exception as e:
                    logger.error(f"Error in event listener for '{event_type}': {e}")
        # AUDIT POINT 6: Jika event adalah sinyal eksternal untuk Tempik lain
        if event_type == InterruptType.EXTERNAL_SIGNAL.value and "target_tempik_id" in event_data:
            target_id = event_data["target_tempik_id"]
            target_tempik = next((t for t in self.tempik_pool if t.tempik_id == target_id), None)
            if target_tempik:
                logger.info(f"Forwarding EXTERNAL_SIGNAL to Tempik-{target_id}.")
                target_tempik.interrupt_controller.raise_interrupt(InterruptType.EXTERNAL_SIGNAL, details=event_data)


# --- Fungsi utilitas dan CLI (disesuaikan) ---
def create_sample_asu_file_audited(output_dir: str = ".", executor_ref_for_signing: Optional[UTEKVirtualExecutor] = None) -> str:
    header = HeaderASU(
        processor_spec="963-Tempik-AuditCompliant",
        protocol_version="v1.2.0",
        time_budget="max-exec-time=45s", # AUDIT POINT 11
        dependency_manifest_hash=hashlib.sha256(b"sample_deps_v2").hexdigest(),
        target_platform="any/virtual",
        execution_mode=ExecutionMode.BATCH.value, # AUDIT POINT 15
        networking_mode="restricted", 
        license_access_info="UTEK Internal Use",
        max_size="15MB", # AUDIT POINT 9
        compression_info="gzip" # AUDIT POINT 10
    )
    
    instructions = [
        InstruksiEksekusi(InstruksiASU.INIT_ENV, parameter={"working_dir": "/home/app"}),
        InstruksiEksekusi(InstruksiASU.SET_ENV, parameter={"APP_VERSION": "2.1", "DEBUG_MODE": "false"}),
        InstruksiEksekusi(InstruksiASU.LOG, parameter={"message": "Starting audited ASU execution."}),
        InstruksiEksekusi(InstruksiASU.INJECT, parameter={"path": "/home/app/data.txt", "content": "Initial data for processing."}),
        InstruksiEksekusi(InstruksiASU.ADD, parameter={"operand1_val": 10, "operand2_val": 5, "dest_reg": 0}), # r0 = 15 (AUDIT POINT 5)
        InstruksiEksekusi(InstruksiASU.CMP, parameter={"operand1_reg": 0, "operand2_val": 15}), # r0 vs 15, ZF=true
        InstruksiEksekusi(InstruksiASU.JZ, label="skip_mul", parameter={"target_label": "after_mul"}), # Jump if Zero Flag is set
        InstruksiEksekusi(InstruksiASU.MUL, parameter={"operand1_reg":0, "operand2_val":2, "dest_reg":0}, label="do_mul"), # r0 = r0 * 2 (skipped)
        InstruksiEksekusi(InstruksiASU.LOG, parameter={"message": "Multiplication was done (should be skipped)."}, label="after_mul"),
        InstruksiEksekusi(InstruksiASU.CALL, parameter={"target_label": "my_subroutine"}), # AUDIT POINT 4
        InstruksiEksekusi(InstruksiASU.LOG, parameter={"message": "Returned from subroutine."}),
        InstruksiEksekusi(InstruksiASU.EXPORT, parameter={"source_vfs_path": "/home/app/data.txt", "target": "output_data_file"}),
        InstruksiEksekusi(InstruksiASU.CLEANUP, parameter={"dir": "/home/app"}),
        InstruksiEksekusi(InstruksiASU.HALT, parameter={"reason": "Audited sample execution finished."}),
        # Subroutine example (AUDIT POINT 4)
        InstruksiEksekusi(InstruksiASU.LOG, parameter={"message": "Inside my_subroutine."}, label="my_subroutine"),
        InstruksiEksekusi(InstruksiASU.SET_ENV, parameter={"SUB_VAR": "sub_value"}),
        InstruksiEksekusi(InstruksiASU.RET) 
    ]

    vfs_struct = {
        "config": { "settings.json": "{ \"theme\": \"dark\" }" },
        "scripts": { "init.sh": "echo 'VFS init script (simulated)'" }
    }
    
    # Gunakan executor yang ada jika disediakan (untuk signing key)
    temp_executor = executor_ref_for_signing if executor_ref_for_signing else UTEKVirtualExecutor(num_tempik_engines=1)
    # Jika executor_ref_for_signing punya kunci, file akan ditandatangani
    return temp_executor.create_asu_file(header, instructions, virtual_fs_structure=vfs_struct, output_dir=output_dir)


async def main_cli_audited(): # AUDIT POINT 12 (Bootloader/CLI)
    import argparse
    parser = argparse.ArgumentParser(description="UTEK Virtual 963-Tempik Executor (Audited & Refactored)")
    parser.add_argument("command", choices=["run", "create", "validate", "status", "run_multiple"], help="Command to execute")
    parser.add_argument("--file", "-f", help="Path to .asu file for 'run' or 'validate'")
    parser.add_argument("--files", nargs='+', help="Paths to multiple .asu files for 'run_multiple'")
    parser.add_argument("--output_dir", "-o", default=".", help="Output directory for 'create'")
    parser.add_argument("--num_tempik", "-n", type=int, default=3, help="Number of Tempik engines (1-963)") # AUDIT POINT 1
    parser.add_argument("--private_key", help="Path to PEM private key for signing created .asu files.") # AUDIT POINT 13
    parser.add_argument("--public_key", help="Path to PEM public key for verifying received .asu files.") # AUDIT POINT 13
    
    args = parser.parse_args()
    
    executor = UTEKVirtualExecutor(num_tempik_engines=args.num_tempik)
    executor.load_global_keys(private_key_path=args.private_key, public_key_path=args.public_key) # AUDIT POINT 13
    
    if args.command == "create":
        print(f"Creating sample audited .asu file in {args.output_dir}...")
        file_path = create_sample_asu_file_audited(args.output_dir, executor_ref_for_signing=executor)
        print(f"Sample audited .asu file created: {file_path}")
        return

    await executor.start() # Mulai scheduler dan TempikManager
    
    try:
        if args.command == "run":
            if not args.file: parser.error("--file is required for 'run' command.")
            print(f"Submitting .asu file for execution: {args.file}")
            result = await executor.execute_asu_file_async(args.file)
            print(f"Submission result: {result}")
        
        elif args.command == "run_multiple": # AUDIT POINT 1
            if not args.files: parser.error("--files are required for 'run_multiple' command.")
            submission_results = []
            for file_path_multi in args.files:
                print(f"Submitting .asu file for execution: {file_path_multi}")
                result_multi = await executor.execute_asu_file_async(file_path_multi)
                submission_results.append(result_multi)
                print(f"Submission result for {file_path_multi}: {result_multi}")
            print(f"\nAll multiple files submitted. Results: {submission_results}")


        elif args.command == "validate": # AUDIT POINT 10 (validasi)
            if not args.file: parser.error("--file is required for 'validate' command.")
            print(f"Validating .asu file: {args.file}")
            try:
                file_asu_obj = executor.parse_asu_file(args.file)
                print(f"File .asu parsed successfully. Hash: {file_asu_obj.hash_sha256}")
                print(f"Header: {file_asu_obj.header.to_dict()}")
                print("Basic validation successful (parsing, hash, signature if key provided).")
            except Exception as e:
                print(f"Validation failed: {e}")

        elif args.command == "status": # AUDIT POINT 2 (monitoring)
            pass # Status akan ditampilkan di loop di bawah

        if args.command in ["run", "run_multiple", "status"]:
            print("Executor running. Monitor logs or status. Press Ctrl+C to stop executor.")
            while not executor.is_shutting_down: 
                await asyncio.sleep(5)
                status_info = executor.get_sistem_status()
                print("\n=== UTEK VIRTUAL SYSTEM STATUS (Update) ===")
                print(json.dumps(status_info, indent=2, default=str)) # default=str untuk Enum, dll.
                
                # Cek apakah semua task selesai (jika bukan mode status murni)
                if args.command != "status" and executor.scheduler.task_queue.empty():
                    all_tempik_idle_or_done = all(
                        t.status in [TempikStatus.IDLE, TempikStatus.COMPLETED, TempikStatus.FAILED, TempikStatus.HALTED] 
                        for t in executor.tempik_pool
                    )
                    if all_tempik_idle_or_done:
                        logger.info("All tasks processed and Tempiks are idle/done. CLI will exit shortly.")
                        await asyncio.sleep(2) # Beri waktu untuk log terakhir
                        break


    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received by CLI.")
    finally:
        await executor.shutdown("CLI session ended.")

if __name__ == "__main__":
    # os.environ['PYTHONASYNCIODEBUG'] = '1'
    # logging.getLogger('asyncio').setLevel(logging.DEBUG)
    try:
        asyncio.run(main_cli_audited())
    except KeyboardInterrupt:
        logger.info("UTEK Executor CLI terminated by user.")

