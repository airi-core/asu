#!/usr/bin/env python3
"""
Implementasi File Ekstensi .wasu
Sistem file executable dengan Docker integration
Author: WASU Development Team
"""

import struct
import hashlib
import json
import zlib
import os
import time
import subprocess
import tempfile
import shutil
from typing import Dict, Any, Optional, List
from pathlib import Path

# Konstanta Magic Numbers
WASU_MAGIC_HEADER = b'WASUENT\x00'
WASU_MAGIC_FOOTER = b'WASUFTR\x00'
WASU_END_MARKER = b'WASUEND\x00'

# Format Types
FORMAT_DOCKER_APP = 0x00000001
FORMAT_PYTHON_APP = 0x00000002
FORMAT_NODE_APP = 0x00000003
FORMAT_GENERIC_APP = 0x00000004

# Compression Types
COMPRESSION_NONE = 0x00
COMPRESSION_ZLIB = 0x01
COMPRESSION_GZIP = 0x02

# Encryption Types
ENCRYPTION_NONE = 0x00
ENCRYPTION_AES256 = 0x01

# Integrity Types
INTEGRITY_SHA256 = 0x00
INTEGRITY_MD5 = 0x01

class WasuFileBuilder:
    """Builder untuk membuat file .wasu"""
    
    def __init__(self):
        self.version_major = 1
        self.version_minor = 0
        self.format_type = FORMAT_DOCKER_APP
        self.compression_type = COMPRESSION_ZLIB
        self.encryption_type = ENCRYPTION_NONE
        self.integrity_type = INTEGRITY_SHA256
        self.feature_flags = 0x00000000
        self.metadata = {}
        self.payload_data = b''
        
    def set_docker_config(self, image: str, dockerfile_content: str = None, 
                         git_repo: str = None, dependencies: List[str] = None):
        """Set konfigurasi Docker"""
        self.format_type = FORMAT_DOCKER_APP
        self.metadata.update({
            'docker': {
                'image': image,
                'dockerfile': dockerfile_content,
                'git_repo': git_repo,
                'dependencies': dependencies or [],
                'auto_build': True,
                'auto_run': True
            }
        })
        
    def set_payload(self, data: bytes):
        """Set payload data"""
        if self.compression_type == COMPRESSION_ZLIB:
            self.payload_data = zlib.compress(data, level=9)
        else:
            self.payload_data = data
            
    def build(self, output_path: str):
        """Build file .wasu"""
        metadata_json = json.dumps(self.metadata, separators=(',', ':')).encode('utf-8')
        creation_time = int(time.time())
        
        # Hitung ukuran
        header_size = 64
        metadata_size = len(metadata_json)
        payload_size = len(self.payload_data)
        footer_offset = header_size + metadata_size + payload_size
        footer_size = 32
        total_size = footer_offset + footer_size
        
        with open(output_path, 'wb') as f:
            # Write Header (64 bytes)
            header = struct.pack(
                '<8s H H I Q Q Q Q B B B x I Q',
                WASU_MAGIC_HEADER,      # Magic number
                self.version_major,      # Version major
                self.version_minor,      # Version minor
                self.format_type,        # Format type
                header_size,            # Header size
                metadata_size,          # Metadata size
                payload_size,           # Payload size
                footer_offset,          # Footer offset
                self.compression_type,   # Compression type
                self.encryption_type,    # Encryption type
                self.integrity_type,     # Integrity type
                                        # 1 byte padding
                self.feature_flags,     # Feature flags
                creation_time           # Creation time
            )
            f.write(header)
            
            # Write Metadata
            f.write(metadata_json)
            
            # Write Payload
            f.write(self.payload_data)
            
            # Calculate checksum untuk header + metadata + payload
            f.seek(0)
            file_data = f.read(footer_offset)
            checksum = hashlib.sha256(file_data).digest()[:16]
            
            # Write Footer (32 bytes)
            footer = struct.pack(
                '<8s Q 16s 8s',
                WASU_MAGIC_FOOTER,  # Magic footer
                total_size,         # Total file size
                checksum,           # SHA256 checksum (16 bytes)
                WASU_END_MARKER     # End marker
            )
            f.write(footer)

class WasuFileReader:
    """Reader untuk membaca file .wasu"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.header = None
        self.metadata = None
        self.payload = None
        
    def read(self):
        """Baca file .wasu"""
        with open(self.file_path, 'rb') as f:
            # Baca dan validasi header
            header_data = f.read(64)
            if len(header_data) < 64:
                raise ValueError("File terlalu kecil")
                
            self.header = struct.unpack('<8s H H I Q Q Q Q B B B x I Q', header_data)
            
            if self.header[0] != WASU_MAGIC_HEADER:
                raise ValueError("Bukan file .wasu yang valid")
                
            # Extract header info
            (magic, version_major, version_minor, format_type, header_size,
             metadata_size, payload_size, footer_offset, compression_type,
             encryption_type, integrity_type, feature_flags, creation_time) = self.header
            
            # Baca metadata
            metadata_raw = f.read(metadata_size)
            self.metadata = json.loads(metadata_raw.decode('utf-8'))
            
            # Baca payload
            payload_raw = f.read(payload_size)
            if compression_type == COMPRESSION_ZLIB:
                self.payload = zlib.decompress(payload_raw)
            else:
                self.payload = payload_raw
                
            # Validasi footer
            f.seek(footer_offset)
            footer_data = f.read(32)
            footer = struct.unpack('<8s Q 16s 8s', footer_data)
            
            if footer[0] != WASU_MAGIC_FOOTER:
                raise ValueError("Footer tidak valid")
                
            if footer[3] != WASU_END_MARKER:
                raise ValueError("End marker tidak valid")
                
            # Validasi checksum
            f.seek(0)
            file_data = f.read(footer_offset)
            calc_checksum = hashlib.sha256(file_data).digest()[:16]
            
            if calc_checksum != footer[2]:
                raise ValueError("Checksum tidak cocok")
                
        return True

class WasuExecutor:
    """Executor untuk menjalankan file .wasu"""
    
    def __init__(self, wasu_file: str):
        self.wasu_file = wasu_file
        self.reader = WasuFileReader(wasu_file)
        self.temp_dir = None
        
    def execute(self):
        """Execute file .wasu"""
        self.reader.read()
        
        if 'docker' not in self.reader.metadata:
            raise ValueError("Bukan file Docker .wasu")
            
        docker_config = self.reader.metadata['docker']
        
        # Buat temporary directory
        self.temp_dir = tempfile.mkdtemp(prefix='wasu_')
        
        try:
            # Extract payload ke temp directory
            if docker_config.get('git_repo'):
                self._clone_repository(docker_config['git_repo'])
            else:
                self._extract_payload()
                
            # Build Docker image jika ada Dockerfile
            if docker_config.get('dockerfile'):
                self._build_docker_image(docker_config)
            
            # Install dependencies
            if docker_config.get('dependencies'):
                self._install_dependencies(docker_config['dependencies'])
                
            # Run Docker container
            if docker_config.get('auto_run', True):
                self._run_docker_container(docker_config)
                
        finally:
            # Cleanup
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                
    def _clone_repository(self, git_repo: str):
        """Clone Git repository"""
        cmd = ['git', 'clone', git_repo, self.temp_dir]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Git clone gagal: {result.stderr}")
            
    def _extract_payload(self):
        """Extract payload ke temporary directory"""
        payload_file = os.path.join(self.temp_dir, 'payload.tar.gz')
        with open(payload_file, 'wb') as f:
            f.write(self.reader.payload)
            
        # Extract tar.gz
        cmd = ['tar', '-xzf', payload_file, '-C', self.temp_dir]
        subprocess.run(cmd, check=True)
        
    def _build_docker_image(self, docker_config: dict):
        """Build Docker image"""
        dockerfile_path = os.path.join(self.temp_dir, 'Dockerfile')
        
        # Write Dockerfile jika disediakan
        if docker_config.get('dockerfile'):
            with open(dockerfile_path, 'w') as f:
                f.write(docker_config['dockerfile'])
                
        # Build image
        image_tag = f"wasu-app-{int(time.time())}"
        cmd = ['docker', 'build', '-t', image_tag, self.temp_dir]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"Docker build gagal: {result.stderr}")
            
        docker_config['built_image'] = image_tag
        
    def _install_dependencies(self, dependencies: List[str]):
        """Install dependencies dalam container"""
        # Implement dependency installation logic
        pass
        
    def _run_docker_container(self, docker_config: dict):
        """Run Docker container"""
        image = docker_config.get('built_image', docker_config['image'])
        
        cmd = [
            'docker', 'run', '--rm', 
            '-v', f"{self.temp_dir}:/app",
            image
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"Docker run gagal: {result.stderr}")
            
        print("Output:", result.stdout)

def create_wasu_file(config: Dict[str, Any], payload_path: str, output_path: str):
    """Helper function untuk membuat file .wasu"""
    builder = WasuFileBuilder()
    
    # Set Docker config
    if 'docker' in config:
        docker_cfg = config['docker']
        builder.set_docker_config(
            image=docker_cfg.get('image', 'ubuntu:latest'),
            dockerfile_content=docker_cfg.get('dockerfile'),
            git_repo=docker_cfg.get('git_repo'),
            dependencies=docker_cfg.get('dependencies', [])
        )
    
    # Load payload
    if os.path.exists(payload_path):
        with open(payload_path, 'rb') as f:
            payload_data = f.read()
        builder.set_payload(payload_data)
    
    # Build file
    builder.build(output_path)
    
def execute_wasu_file(wasu_path: str):
    """Helper function untuk execute file .wasu"""
    executor = WasuExecutor(wasu_path)
    executor.execute()

# Contoh penggunaan
if __name__ == "__main__":
    # Contoh membuat file .wasu
    config = {
        'docker': {
            'image': 'python:3.9-slim',
            'dockerfile': '''
FROM python:3.9-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "app.py"]
            ''',
            'git_repo': 'https://github.com/user/repo.git',
            'dependencies': ['flask', 'requests', 'numpy']
        }
    }
    
    # Buat file .wasu (payload bisa kosong jika menggunakan git clone)
    create_wasu_file(config, '/dev/null', 'example.wasu')
    
    # Execute file .wasu
    execute_wasu_file('example.wasu')