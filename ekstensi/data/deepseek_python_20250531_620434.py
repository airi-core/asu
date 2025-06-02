def validate_wasu_file(file_path: str):
    with open(file_path, "rb") as f:
        # Periksa magic header
        magic = f.read(8)
        if magic != WASU_MAGIC_HEADER:
            return False
        
        # Baca header lengkap
        f.seek(0)
        header = f.read(64)
        
        # Ekstrak ukuran file dari header
        _, _, _, _, _, _, payload_size, footer_offset, _, _, _, _, _, _ = struct.unpack(
            "<8s H H I Q Q Q Q B B B x I Q", header)
        
        # Periksa ukuran file
        f.seek(0, 2)
        actual_size = f.tell()
        if actual_size != (footer_offset + 32):
            return False
        
        # Periksa magic footer
        f.seek(footer_offset)
        footer_magic = f.read(8)
        if footer_magic != WASU_MAGIC_FOOTER:
            return False
        
        # Validasi checksum
        f.seek(0)
        file_data = f.read(footer_offset)
        calc_checksum = hashlib.sha256(file_data).digest()[:16]
        
        f.seek(footer_offset + 8)
        stored_checksum = f.read(16)
        
        return calc_checksum == stored_checksum