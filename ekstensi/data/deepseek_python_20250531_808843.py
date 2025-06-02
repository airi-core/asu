#!/usr/bin/env python3
"""
WASU File Format v3.0 - Enterprise Implementation (Fixed)
Author: WASU Core Team
"""

import os
import sys
import struct
import hashlib
import json
import zlib
import time
import tarfile
import io
import tempfile
import shutil
import subprocess
import mmap
import argparse
from typing import Dict, List, Tuple, Optional
from pathlib import Path
from enum import IntEnum
from dataclasses import dataclass

# ====================== KONSTANTA & KONFIGURASI ======================
WASU_MAGIC_HEADER = b'WASU_ENT\x00'  # 8 byte
WASU_MAGIC_FOOTER = b'WASU_FTR\x00'  # 8 byte
WASU_END_MARKER = b'WASU_END\x00'    # 8 byte

VERSION_MAJOR = 3
VERSION_MINOR = 0

MAX_FILE_SIZE = 68 * 1024**4  # 68 TB
CHUNK_SIZE = 1024 * 1024 * 64  # 64 MB

# Enum untuk tipe data
class ContentType(IntEnum):
    DOCKER_IMAGE = 1
    AI_MODEL = 2
    DATASET = 3
    RESEARCH_DATA = 4
    EXECUTABLE = 5

class CompressionType(IntEnum):
    NONE = 0
    ZLIB = 1
    ZSTD = 2

class EncryptionType(IntEnum):
    NONE = 0
    AES256 = 1

# ====================== STRUKTUR FILE PRESISI ======================
@dataclass
class WasuHeader:
    magic: bytes = WASU_MAGIC_HEADER
    version_major: int = VERSION_MAJOR
    version_minor: int = VERSION_MINOR
    content_type: ContentType = ContentType.DOCKER_IMAGE
    header_size: int = 128
    metadata_size: int = 0
    payload_size: int = 0
    footer_offset: int = 0
    compression: CompressionType = CompressionType.ZSTD
    encryption: EncryptionType = EncryptionType.NONE
    integrity_hash: bytes = b''
    feature_flags: int = 0
    creation_time: int = int(time.time())
    content_id: bytes = b''
    
    def pack(self) -> bytes:
        return struct.pack(
            '<8s H H I Q Q Q Q B B 32s I Q 32s',
            self.magic,
            self.version_major,
            self.version_minor,
            int(self.content_type),
            self.header_size,
            self.metadata_size,
            self.payload_size,
            self.footer_offset,
            int(self.compression),
            int(self.encryption),
            self.integrity_hash,
            self.feature_flags,
            self.creation_time,
            self.content_id
        )
    
    @classmethod
    def unpack(cls, data: bytes) -> 'WasuHeader':
        unpacked = struct.unpack('<8s H H I Q Q Q Q B B 32s I Q 32s', data)
        return cls(
            magic=unpacked[0],
            version_major=unpacked[1],
            version_minor=unpacked[2],
            content_type=ContentType(unpacked[3]),
            header_size=unpacked[4],
            metadata_size=unpacked[5],
            payload_size=unpacked[6],
            footer_offset=unpacked[7],
            compression=CompressionType(unpacked[8]),
            encryption=EncryptionType(unpacked[9]),
            integrity_hash=unpacked[10],
            feature_flags=unpacked[11],
            creation_time=unpacked[12],
            content_id=unpacked[13]
        )

@dataclass
class WasuFooter:
    magic: bytes = WASU_MAGIC_FOOTER
    file_size: int = 0
    content_hash: bytes = b''
    end_marker: bytes = WASU_END_MARKER
    
    def pack(self) -> bytes:
        return struct.pack(
            '<8s Q 32s 8s',
            self.magic,
            self.file_size,
            self.content_hash,
            self.end_marker
        )
    
    @classmethod
    def unpack(cls, data: bytes) -> 'WasuFooter':
        unpacked = struct.unpack('<8s Q 32s 8s', data)
        return cls(
            magic=unpacked[0],
            file_size=unpacked[1],
            content_hash=unpacked[2],
            end_marker=unpacked[3]
        )

# ====================== CORE FILE OPERATIONS ======================
class WasuFileBuilder:
    def __init__(self):
        self.header = WasuHeader()
        self.metadata = {}
        self.payload_path = None
        self.content_id = b''
    
    def set_metadata(self, metadata: Dict):
        self.metadata = metadata
    
    def set_payload(self, payload_path: str):
        if not Path(payload_path).exists():
            raise FileNotFoundError(f"Payload not found: {payload_path}")
        
        file_size = Path(payload_path).stat().st_size
        if file_size > MAX_FILE_SIZE:
            raise ValueError(f"Payload exceeds 68TB limit")
        
        self.payload_path = payload_path
        self.header.payload_size = file_size
    
    def _calculate_content_id(self) -> bytes:
        """Hitung ID konten untuk deduplikasi"""
        hasher = hashlib.blake2b()
        
        # Hash metadata
        metadata_json = json.dumps(self.metadata, sort_keys=True).encode()
        hasher.update(metadata_json)
        
        # Hash payload
        if self.payload_path:
            with open(self.payload_path, 'rb') as f:
                while chunk := f.read(CHUNK_SIZE):
                    hasher.update(chunk)
        
        return hasher.digest()
    
    def build(self, output_path: str) -> str:
        # Hitung ID konten untuk deduplikasi
        self.content_id = self._calculate_content_id()
        self.header.content_id = self.content_id
        
        # Serialisasi metadata
        metadata_json = json.dumps(self.metadata).encode()
        self.header.metadata_size = len(metadata_json)
        
        # Hitung offset footer
        self.header.footer_offset = (
            self.header.header_size +
            self.header.metadata_size +
            self.header.payload_size
        )
        
        # Tulis file dengan chunk processing
        with open(output_path, 'wb') as f_out:
            # 1. Tulis header
            f_out.write(self.header.pack())
            
            # 2. Tulis metadata
            f_out.write(metadata_json)
            
            # 3. Tulis payload (chunked untuk 68TB)
            if self.payload_path:
                with open(self.payload_path, 'rb') as f_in:
                    while chunk := f_in.read(CHUNK_SIZE):
                        f_out.write(chunk)
            
            # 4. Hitung hash integritas
            f_out.flush()
            file_size = f_out.tell()
            content_hasher = hashlib.blake2b()
            
            # Baca ulang file untuk hash (efisien untuk file besar)
            f_out.seek(0)
            while chunk := f_out.read(CHUNK_SIZE):
                content_hasher.update(chunk)
            
            content_hash = content_hasher.digest()
            
            # 5. Tulis footer
            footer = WasuFooter(
                file_size=file_size + 48,  # Ukuran footer
                content_hash=content_hash
            )
            f_out.write(footer.pack())
        
        return self.content_id.hex()

class WasuFileReader:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.header = None
        self.metadata = {}
        self.content_id = b''
    
    def load_header(self) -> WasuHeader:
        with open(self.file_path, 'rb') as f:
            header_data = f.read(128)
            self.header = WasuHeader.unpack(header_data)
            
            if self.header.magic != WASU_MAGIC_HEADER:
                raise ValueError("Invalid WASU file")
            
            self.content_id = self.header.content_id
            return self.header
    
    def verify_integrity(self) -> bool:
        self.load_header()
        
        # Hitung hash konten
        hasher = hashlib.blake2b()
        with open(self.file_path, 'rb') as f:
            # Baca hingga footer
            bytes_to_read = self.header.footer_offset
            while bytes_to_read > 0:
                chunk_size = min(bytes_to_read, CHUNK_SIZE)
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                hasher.update(chunk)
                bytes_to_read -= len(chunk)
            
            calculated_hash = hasher.digest()
        
        # Baca footer
        f.seek(self.header.footer_offset)
        footer_data = f.read(48)
        footer = WasuFooter.unpack(footer_data)
        
        # Validasi
        return (
            footer.magic == WASU_MAGIC_FOOTER and
            footer.content_hash == calculated_hash and
            footer.end_marker == WASU_END_MARKER
        )
    
    def load_metadata(self) -> Dict:
        if not self.verify_integrity():
            raise ValueError("File integrity check failed")
        
        with open(self.file_path, 'rb') as f:
            f.seek(self.header.header_size)
            metadata_data = f.read(self.header.metadata_size)
            self.metadata = json.loads(metadata_data.decode())
            return self.metadata
    
    def extract_payload(self, output_path: str) -> str:
        self.load_metadata()
        
        with open(self.file_path, 'rb') as f_in:
            payload_offset = self.header.header_size + self.header.metadata_size
            f_in.seek(payload_offset)
            
            with open(output_path, 'wb') as f_out:
                bytes_left = self.header.payload_size
                while bytes_left > 0:
                    chunk_size = min(bytes_left, CHUNK_SIZE)
                    chunk = f_in.read(chunk_size)
                    if not chunk:
                        break
                    f_out.write(chunk)
                    bytes_left -= len(chunk)
        
        return output_path

# ====================== DOCKER EXECUTION ENGINE ======================
class DockerExecutionEngine:
    """Mesin eksekusi Docker yang presisi"""
    
    def __init__(self, metadata: Dict, payload_path: str):
        self.metadata = metadata
        self.payload_path = payload_path
        self.temp_dir = Path(tempfile.mkdtemp(prefix="wasu_"))
        self.image_name = f"wasu-{time.strftime('%Y%m%d%H%M%S')}"
    
    def prepare_environment(self):
        """Siapkan lingkungan eksekusi"""
        docker_cfg = self.metadata.get('docker', {})
        
        # Ekstrak payload jika ada
        if self.payload_path:
            self.extract_payload()
        
        # Clone Git repo jika ada
        if 'git_repo' in docker_cfg:
            self.clone_repository(docker_cfg['git_repo'])
        
        # Tulis Dockerfile jika ada
        if 'dockerfile' in docker_cfg:
            dockerfile_path = self.temp_dir / 'Dockerfile'
            with open(dockerfile_path, 'w') as f:
                f.write(docker_cfg['dockerfile'])
    
    def extract_payload(self):
        """Ekstrak payload ke direktori kerja"""
        if tarfile.is_tarfile(self.payload_path):
            with tarfile.open(self.payload_path) as tar:
                tar.extractall(self.temp_dir)
        else:
            # Jika bukan archive, salin langsung
            shutil.copy(self.payload_path, self.temp_dir)
    
    def clone_repository(self, repo_url: str):
        """Clone repository Git"""
        result = subprocess.run(
            ['git', 'clone', repo_url, self.temp_dir],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"Git clone failed: {result.stderr}")
    
    def install_dependencies(self):
        """Instal dependensi jika ada"""
        docker_cfg = self.metadata.get('docker', {})
        if 'dependencies' not in docker_cfg:
            return
        
        # Untuk Docker, dependensi diinstal selama build
        # Implementasi untuk tipe lain bisa ditambahkan di sini
        pass
    
    def build_image(self):
        """Build Docker image"""
        build_cmd = [
            'docker', 'build',
            '-t', self.image_name,
            str(self.temp_dir)
        ]
        
        result = subprocess.run(
            build_cmd,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Docker build failed: {result.stderr}")
    
    def run_container(self):
        """Jalankan Docker container"""
        docker_cfg = self.metadata.get('docker', {})
        run_cmd = ['docker', 'run', '--rm']
        
        # Tambahkan volume jika ada
        if 'volumes' in docker_cfg:
            for vol in docker_cfg['volumes']:
                run_cmd.extend(['-v', vol])
        
        # Tambahkan environment variables
        if 'environment' in docker_cfg:
            for key, value in docker_cfg['environment'].items():
                run_cmd.extend(['-e', f"{key}={value}"])
        
        # Tambahkan nama image
        run_cmd.append(self.image_name)
        
        # Tambahkan perintah khusus
        if 'command' in docker_cfg:
            run_cmd.extend(docker_cfg['command'])
        
        # Jalankan container
        result = subprocess.run(
            run_cmd,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Docker run failed: {result.stderr}")
        
        # Output hasil eksekusi
        print("=" * 80)
        print("DOCKER EXECUTION OUTPUT")
        print("=" * 80)
        print(result.stdout)
        if result.stderr:
            print("\nERRORS:")
            print(result.stderr)
        print("=" * 80)
    
    def cleanup(self):
        """Bersihkan sumber daya"""
        # Hapus image Docker
        subprocess.run(
            ['docker', 'rmi', '-f', self.image_name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # Hapus direktori sementara
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def execute(self):
        """Eksekusi end-to-end"""
        try:
            self.prepare_environment()
            self.install_dependencies()
            self.build_image()
            self.run_container()
        finally:
            self.cleanup()

# ====================== WASU CLI ======================
class WasuCLI:
    def __init__(self):
        self.parser = argparse.ArgumentParser(
            description="WASU File Management System"
        )
        self.subparsers = self.parser.add_subparsers(
            dest='command',
            required=True
        )
        
        # Perintah create
        create_parser = self.subparsers.add_parser(
            'create',
            help='Create a new WASU file'
        )
        create_parser.add_argument(
            'metadata',
            help='Path to metadata JSON file'
        )
        create_parser.add_argument(
            'payload',
            help='Path to payload file/directory'
        )
        create_parser.add_argument(
            'output',
            help='Output WASU file path'
        )
        
        # Perintah verify
        verify_parser = self.subparsers.add_parser(
            'verify',
            help='Verify WASU file integrity'
        )
        verify_parser.add_argument(
            'file',
            help='WASU file to verify'
        )
        
        # Perintah extract
        extract_parser = self.subparsers.add_parser(
            'extract',
            help='Extract payload from WASU file'
        )
        extract_parser.add_argument(
            'file',
            help='WASU file to extract'
        )
        extract_parser.add_argument(
            'output',
            help='Output path for payload'
        )
        
        # Perintah execute
        execute_parser = self.subparsers.add_parser(
            'execute',
            help='Execute WASU file'
        )
        execute_parser.add_argument(
            'file',
            help='WASU file to execute'
        )
        
        # Perintah info
        info_parser = self.subparsers.add_parser(
            'info',
            help='Show WASU file information'
        )
        info_parser.add_argument(
            'file',
            help='WASU file to inspect'
        )
    
    def run(self, args):
        parsed = self.parser.parse_args(args)
        
        if parsed.command == 'create':
            self.handle_create(parsed)
        elif parsed.command == 'verify':
            self.handle_verify(parsed)
        elif parsed.command == 'extract':
            self.handle_extract(parsed)
        elif parsed.command == 'execute':
            self.handle_execute(parsed)
        elif parsed.command == 'info':
            self.handle_info(parsed)
    
    def handle_create(self, parsed):
        # Muat metadata
        with open(parsed.metadata, 'r') as f:
            metadata = json.load(f)
        
        # Buat payload archive jika direktori
        payload_path = parsed.payload
        if os.path.isdir(payload_path):
            temp_payload = tempfile.mktemp(suffix='.tar')
            with tarfile.open(temp_payload, 'w') as tar:
                tar.add(payload_path, arcname='')
            payload_path = temp_payload
        else:
            temp_payload = None
        
        # Bangun file WASU
        builder = WasuFileBuilder()
        builder.set_metadata(metadata)
        builder.set_payload(payload_path)
        
        content_id = builder.build(parsed.output)
        
        print(f"WASU file created: {parsed.output}")
        print(f"Content ID: {content_id}")
        
        # Hapus payload sementara jika ada
        if temp_payload:
            os.unlink(temp_payload)
    
    def handle_verify(self, parsed):
        reader = WasuFileReader(parsed.file)
        if reader.verify_integrity():
            print("✅ File integrity verified")
            print(f"Content ID: {reader.content_id.hex()}")
        else:
            print("❌ File integrity check failed")
            sys.exit(1)
    
    def handle_extract(self, parsed):
        reader = WasuFileReader(parsed.file)
        if not reader.verify_integrity():
            print("Integrity check failed, cannot extract")
            sys.exit(1)
        
        extracted = reader.extract_payload(parsed.output)
        print(f"Payload extracted to: {extracted}")
    
    def handle_execute(self, parsed):
        # Verifikasi dan ekstrak terlebih dahulu
        reader = WasuFileReader(parsed.file)
        if not reader.verify_integrity():
            print("Integrity verification failed")
            sys.exit(1)
        
        metadata = reader.load_metadata()
        
        # Ekstrak payload ke file sementara
        temp_payload = tempfile.mktemp()
        reader.extract_payload(temp_payload)
        
        # Eksekusi berdasarkan tipe konten
        if reader.header.content_type == ContentType.DOCKER_IMAGE:
            executor = DockerExecutionEngine(metadata, temp_payload)
            executor.execute()
        else:
            print(f"Content type not supported: {reader.header.content_type}")
            sys.exit(1)
        
        # Bersihkan payload sementara
        os.unlink(temp_payload)
    
    def handle_info(self, parsed):
        reader = WasuFileReader(parsed.file)
        try:
            header = reader.load_header()
            metadata = reader.load_metadata()
            
            print("=" * 80)
            print(f"WASU FILE INFO: {parsed.file}")
            print("=" * 80)
            print(f"Version:     {header.version_major}.{header.version_minor}")
            print(f"Content ID:  {header.content_id.hex()}")
            print(f"Type:        {header.content_type.name}")
            print(f"Created:     {time.ctime(header.creation_time)}")
            print(f"Size:        {os.path.getsize(parsed.file) / (1024**3):.2f} GB")
            print(f"Metadata:    {header.metadata_size} bytes")
            print(f"Payload:     {header.payload_size} bytes")
            print("\nMETADATA:")
            print(json.dumps(metadata, indent=2))
            print("=" * 80)
        except Exception as e:
            print(f"Error: {str(e)}")
            sys.exit(1)

# ====================== RUNNER UTAMA ======================
def main():
    cli = WasuCLI()
    cli.run(sys.argv[1:])

if __name__ == "__main__":
    main()