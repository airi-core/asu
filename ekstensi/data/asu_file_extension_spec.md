# Spesifikasi Teknis File Extension .ASU

## 1. Native Library Requirements

### Core Dependencies
```c
// Required system libraries
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#include <time.h>

// Compression libraries
#include <zlib.h>        // gzip compression
#include <lz4.h>         // LZ4 fast compression
#include <zstd.h>        // Zstandard compression

// Crypto libraries
#include <openssl/evp.h>  // Encryption/Decryption
#include <openssl/aes.h>  // AES encryption
#include <openssl/sha.h>  // SHA hashing
#include <openssl/rand.h> // Random generation

// JSON parsing (for metadata)
#include <cjson/cJSON.h>

// Memory mapping
#include <sys/mman.h>
```

### Build System (CMakeLists.txt)
```cmake
cmake_minimum_required(VERSION 3.16)
project(libasu VERSION 1.0.0 LANGUAGES C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Find required packages
find_package(PkgConfig REQUIRED)
pkg_check_modules(ZLIB REQUIRED zlib)
pkg_check_modules(LZ4 REQUIRED liblz4)
pkg_check_modules(ZSTD REQUIRED libzstd)
pkg_check_modules(OPENSSL REQUIRED openssl)
pkg_check_modules(CJSON REQUIRED libcjson)

# Source files
set(SOURCES
    src/asu_core.c
    src/asu_header.c
    src/asu_compression.c
    src/asu_encryption.c
    src/asu_metadata.c
    src/asu_validation.c
    src/asu_io.c
)

# Create shared library
add_library(asu SHARED ${SOURCES})
target_link_libraries(asu ${ZLIB_LIBRARIES} ${LZ4_LIBRARIES} 
                         ${ZSTD_LIBRARIES} ${OPENSSL_LIBRARIES} ${CJSON_LIBRARIES})

# Create static library
add_library(asu_static STATIC ${SOURCES})
set_target_properties(asu_static PROPERTIES OUTPUT_NAME asu)
```

## 2. File Format Structure

### Magic Numbers & Constants
```c
// asu_constants.h
#define ASU_MAGIC_HEADER    0x4153554D41474943ULL  // "ASUMAGIC"
#define ASU_MAGIC_FOOTER    0x4153554641545221ULL  // "ASUFATR!"
#define ASU_VERSION_MAJOR   1
#define ASU_VERSION_MINOR   0
#define ASU_HEADER_SIZE     128
#define ASU_FOOTER_SIZE     64
#define ASU_MAX_METADATA    65536
#define ASU_CHECKSUM_SIZE   32

// Compression types
typedef enum {
    ASU_COMPRESS_NONE = 0,
    ASU_COMPRESS_ZLIB = 1,
    ASU_COMPRESS_LZ4  = 2,
    ASU_COMPRESS_ZSTD = 3
} asu_compression_t;

// Encryption types
typedef enum {
    ASU_ENCRYPT_NONE   = 0,
    ASU_ENCRYPT_AES128 = 1,
    ASU_ENCRYPT_AES256 = 2
} asu_encryption_t;
```

### Header Structure
```c
// asu_header.h
#pragma pack(push, 1)
typedef struct {
    uint64_t magic;              // Magic number (8 bytes)
    uint16_t version_major;      // Major version (2 bytes)
    uint16_t version_minor;      // Minor version (2 bytes)
    uint32_t format_type;        // Format type (4 bytes)
    uint64_t header_size;        // Header size (8 bytes)
    uint64_t metadata_size;      // Metadata size (8 bytes)
    uint64_t payload_size;       // Payload size (8 bytes)
    uint64_t footer_offset;      // Footer offset (8 bytes)
    uint8_t  compression_type;   // Compression type (1 byte)
    uint8_t  encryption_type;    // Encryption type (1 byte)
    uint8_t  integrity_type;     // Integrity check type (1 byte)
    uint8_t  reserved1;          // Reserved (1 byte)
    uint32_t feature_flags;      // Feature flags (4 bytes)
    uint64_t creation_time;      // Creation timestamp (8 bytes)
    uint64_t modification_time;  // Modification timestamp (8 bytes)
    uint8_t  file_hash[32];      // File hash (32 bytes)
    uint8_t  reserved2[16];      // Reserved space (16 bytes)
} asu_header_t;
#pragma pack(pop)
```

### Footer Structure
```c
// asu_footer.h
#pragma pack(push, 1)
typedef struct {
    uint64_t magic;              // Magic number (8 bytes)
    uint64_t total_file_size;    // Total file size (8 bytes)
    uint8_t  file_checksum[32];  // File checksum (32 bytes)
    uint64_t end_marker;         // End marker (8 bytes)
    uint8_t  reserved[8];        // Reserved (8 bytes)
} asu_footer_t;
#pragma pack(pop)
```

## 3. Core Implementation

### Main API Interface
```c
// asu_core.h
typedef struct asu_file {
    FILE *fp;
    asu_header_t header;
    asu_footer_t footer;
    char *metadata;
    uint8_t *payload;
    size_t payload_allocated;
    int is_open;
    int is_modified;
} asu_file_t;

// Core functions
asu_file_t* asu_create(const char *filename);
asu_file_t* asu_open(const char *filename, const char *mode);
int asu_close(asu_file_t *file);
int asu_validate(asu_file_t *file);
int asu_save(asu_file_t *file);

// Data manipulation
int asu_set_metadata(asu_file_t *file, const char *json_metadata);
char* asu_get_metadata(asu_file_t *file);
int asu_set_payload(asu_file_t *file, const uint8_t *data, size_t size);
uint8_t* asu_get_payload(asu_file_t *file, size_t *size);

// Compression
int asu_set_compression(asu_file_t *file, asu_compression_t type);
int asu_compress_payload(asu_file_t *file);
int asu_decompress_payload(asu_file_t *file);

// Encryption
int asu_set_encryption(asu_file_t *file, asu_encryption_t type, const char *password);
int asu_encrypt_payload(asu_file_t *file);
int asu_decrypt_payload(asu_file_t *file, const char *password);
```

### Core Implementation
```c
// asu_core.c
#include "asu_core.h"
#include "asu_constants.h"

asu_file_t* asu_create(const char *filename) {
    asu_file_t *file = calloc(1, sizeof(asu_file_t));
    if (!file) return NULL;
    
    file->fp = fopen(filename, "wb+");
    if (!file->fp) {
        free(file);
        return NULL;
    }
    
    // Initialize header
    file->header.magic = ASU_MAGIC_HEADER;
    file->header.version_major = ASU_VERSION_MAJOR;
    file->header.version_minor = ASU_VERSION_MINOR;
    file->header.header_size = ASU_HEADER_SIZE;
    file->header.creation_time = time(NULL);
    file->header.modification_time = file->header.creation_time;
    
    file->is_open = 1;
    file->is_modified = 1;
    
    return file;
}

asu_file_t* asu_open(const char *filename, const char *mode) {
    asu_file_t *file = calloc(1, sizeof(asu_file_t));
    if (!file) return NULL;
    
    file->fp = fopen(filename, mode);
    if (!file->fp) {
        free(file);
        return NULL;
    }
    
    // Read and validate header
    if (fread(&file->header, sizeof(asu_header_t), 1, file->fp) != 1) {
        fclose(file->fp);
        free(file);
        return NULL;
    }
    
    if (file->header.magic != ASU_MAGIC_HEADER) {
        fclose(file->fp);
        free(file);
        return NULL;
    }
    
    // Read metadata if present
    if (file->header.metadata_size > 0) {
        file->metadata = malloc(file->header.metadata_size + 1);
        fseek(file->fp, ASU_HEADER_SIZE, SEEK_SET);
        fread(file->metadata, file->header.metadata_size, 1, file->fp);
        file->metadata[file->header.metadata_size] = '\0';
    }
    
    file->is_open = 1;
    return file;
}

int asu_close(asu_file_t *file) {
    if (!file) return -1;
    
    if (file->is_modified) {
        asu_save(file);
    }
    
    if (file->fp) fclose(file->fp);
    if (file->metadata) free(file->metadata);
    if (file->payload) free(file->payload);
    free(file);
    
    return 0;
}
```

### Compression Implementation
```c
// asu_compression.c
#include "asu_compression.h"

int asu_compress_zlib(const uint8_t *input, size_t input_size, 
                      uint8_t **output, size_t *output_size) {
    z_stream stream = {0};
    
    if (deflateInit(&stream, Z_DEFAULT_COMPRESSION) != Z_OK) {
        return -1;
    }
    
    size_t max_output = compressBound(input_size);
    *output = malloc(max_output);
    
    stream.next_in = (Bytef*)input;
    stream.avail_in = input_size;
    stream.next_out = *output;
    stream.avail_out = max_output;
    
    int ret = deflate(&stream, Z_FINISH);
    if (ret != Z_STREAM_END) {
        free(*output);
        deflateEnd(&stream);
        return -1;
    }
    
    *output_size = stream.total_out;
    deflateEnd(&stream);
    
    return 0;
}

int asu_compress_lz4(const uint8_t *input, size_t input_size,
                     uint8_t **output, size_t *output_size) {
    size_t max_output = LZ4_compressBound(input_size);
    *output = malloc(max_output);
    
    int compressed_size = LZ4_compress_default((const char*)input, 
                                               (char*)*output, 
                                               input_size, max_output);
    
    if (compressed_size <= 0) {
        free(*output);
        return -1;
    }
    
    *output_size = compressed_size;
    return 0;
}

int asu_compress_zstd(const uint8_t *input, size_t input_size,
                      uint8_t **output, size_t *output_size) {
    size_t max_output = ZSTD_compressBound(input_size);
    *output = malloc(max_output);
    
    size_t compressed_size = ZSTD_compress(*output, max_output,
                                           input, input_size, 1);
    
    if (ZSTD_isError(compressed_size)) {
        free(*output);
        return -1;
    }
    
    *output_size = compressed_size;
    return 0;
}
```

### Encryption Implementation
```c
// asu_encryption.c
#include "asu_encryption.h"

int asu_encrypt_aes256(const uint8_t *input, size_t input_size,
                       const char *password, uint8_t **output, size_t *output_size) {
    EVP_CIPHER_CTX *ctx = EVP_CIPHER_CTX_new();
    if (!ctx) return -1;
    
    // Derive key from password
    uint8_t key[32], iv[16];
    uint8_t salt[8] = {0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0};
    
    if (!PKCS5_PBKDF2_HMAC(password, strlen(password), salt, 8, 
                           10000, EVP_sha256(), 32, key)) {
        EVP_CIPHER_CTX_free(ctx);
        return -1;
    }
    
    RAND_bytes(iv, 16);
    
    if (EVP_EncryptInit_ex(ctx, EVP_aes_256_cbc(), NULL, key, iv) != 1) {
        EVP_CIPHER_CTX_free(ctx);
        return -1;
    }
    
    size_t max_output = input_size + EVP_CIPHER_block_size(EVP_aes_256_cbc()) + 16;
    *output = malloc(max_output);
    
    // Copy IV to beginning of output
    memcpy(*output, iv, 16);
    
    int len;
    int ciphertext_len = 0;
    
    if (EVP_EncryptUpdate(ctx, *output + 16, &len, input, input_size) != 1) {
        free(*output);
        EVP_CIPHER_CTX_free(ctx);
        return -1;
    }
    ciphertext_len = len;
    
    if (EVP_EncryptFinal_ex(ctx, *output + 16 + len, &len) != 1) {
        free(*output);
        EVP_CIPHER_CTX_free(ctx);
        return -1;
    }
    ciphertext_len += len;
    
    *output_size = ciphertext_len + 16; // +16 for IV
    EVP_CIPHER_CTX_free(ctx);
    
    return 0;
}

int asu_decrypt_aes256(const uint8_t *input, size_t input_size,
                       const char *password, uint8_t **output, size_t *output_size) {
    if (input_size < 16) return -1; // Must have IV
    
    EVP_CIPHER_CTX *ctx = EVP_CIPHER_CTX_new();
    if (!ctx) return -1;
    
    // Derive key from password
    uint8_t key[32];
    uint8_t salt[8] = {0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0};
    
    if (!PKCS5_PBKDF2_HMAC(password, strlen(password), salt, 8,
                           10000, EVP_sha256(), 32, key)) {
        EVP_CIPHER_CTX_free(ctx);
        return -1;
    }
    
    // Extract IV from input
    uint8_t iv[16];
    memcpy(iv, input, 16);
    
    if (EVP_DecryptInit_ex(ctx, EVP_aes_256_cbc(), NULL, key, iv) != 1) {
        EVP_CIPHER_CTX_free(ctx);
        return -1;
    }
    
    *output = malloc(input_size);
    
    int len;
    int plaintext_len = 0;
    
    if (EVP_DecryptUpdate(ctx, *output, &len, input + 16, input_size - 16) != 1) {
        free(*output);
        EVP_CIPHER_CTX_free(ctx);
        return -1;
    }
    plaintext_len = len;
    
    if (EVP_DecryptFinal_ex(ctx, *output + len, &len) != 1) {
        free(*output);
        EVP_CIPHER_CTX_free(ctx);
        return -1;
    }
    plaintext_len += len;
    
    *output_size = plaintext_len;
    EVP_CIPHER_CTX_free(ctx);
    
    return 0;
}
```

## 4. Validation & Integrity

### Checksum Implementation
```c
// asu_validation.c
#include "asu_validation.h"

int asu_calculate_checksum(asu_file_t *file) {
    if (!file || !file->fp) return -1;
    
    SHA256_CTX ctx;
    SHA256_Init(&ctx);
    
    // Hash header (excluding checksum field)
    asu_header_t temp_header = file->header;
    memset(temp_header.file_hash, 0, 32);
    SHA256_Update(&ctx, &temp_header, sizeof(asu_header_t));
    
    // Hash metadata
    if (file->metadata) {
        SHA256_Update(&ctx, file->metadata, file->header.metadata_size);
    }
    
    // Hash payload
    if (file->payload) {
        SHA256_Update(&ctx, file->payload, file->header.payload_size);
    }
    
    SHA256_Final(file->header.file_hash, &ctx);
    return 0;
}

int asu_validate_structure(asu_file_t *file) {
    if (!file) return -1;
    
    // Check magic numbers
    if (file->header.magic != ASU_MAGIC_HEADER) return -1;
    
    // Check version compatibility
    if (file->header.version_major > ASU_VERSION_MAJOR) return -1;
    
    // Check file size consistency
    fseek(file->fp, 0, SEEK_END);
    long actual_size = ftell(file->fp);
    
    long expected_size = file->header.header_size + 
                        file->header.metadata_size + 
                        file->header.payload_size + 
                        ASU_FOOTER_SIZE;
    
    if (actual_size != expected_size) return -1;
    
    // Validate footer
    fseek(file->fp, file->header.footer_offset, SEEK_SET);
    asu_footer_t footer;
    fread(&footer, sizeof(footer), 1, file->fp);
    
    if (footer.magic != ASU_MAGIC_FOOTER) return -1;
    if (footer.total_file_size != actual_size) return -1;
    
    return 0;
}

int asu_validate_integrity(asu_file_t *file) {
    uint8_t stored_hash[32];
    memcpy(stored_hash, file->header.file_hash, 32);
    
    // Recalculate checksum
    asu_calculate_checksum(file);
    
    // Compare checksums
    if (memcmp(stored_hash, file->header.file_hash, 32) != 0) {
        return -1;
    }
    
    return 0;
}
```

## 5. Command Line Tools

### ASU Utility Program
```c
// asu_tool.c
#include <stdio.h>
#include <getopt.h>
#include "asu_core.h"

void print_usage(const char *program_name) {
    printf("Usage: %s [OPTIONS] COMMAND FILE\n", program_name);
    printf("\nCommands:\n");
    printf("  create FILE           Create new ASU file\n");
    printf("  info FILE            Show file information\n");
    printf("  validate FILE        Validate file integrity\n");
    printf("  extract FILE DIR     Extract file contents\n");
    printf("  compress FILE TYPE   Set compression (none|zlib|lz4|zstd)\n");
    printf("  encrypt FILE PASS    Encrypt file with password\n");
    printf("\nOptions:\n");
    printf("  -m, --metadata JSON  Set metadata from JSON file\n");
    printf("  -d, --data FILE      Set payload data from file\n");
    printf("  -v, --verbose        Verbose output\n");
    printf("  -h, --help           Show this help\n");
}

int cmd_create(const char *filename, const char *metadata_file, const char *data_file) {
    asu_file_t *file = asu_create(filename);
    if (!file) {
        fprintf(stderr, "Failed to create ASU file\n");
        return 1;
    }
    
    if (metadata_file) {
        FILE *mf = fopen(metadata_file, "r");
        if (mf) {
            fseek(mf, 0, SEEK_END);
            long size = ftell(mf);
            fseek(mf, 0, SEEK_SET);
            
            char *metadata = malloc(size + 1);
            fread(metadata, size, 1, mf);
            metadata[size] = '\0';
            
            asu_set_metadata(file, metadata);
            free(metadata);
            fclose(mf);
        }
    }
    
    if (data_file) {
        FILE *df = fopen(data_file, "rb");
        if (df) {
            fseek(df, 0, SEEK_END);
            long size = ftell(df);
            fseek(df, 0, SEEK_SET);
            
            uint8_t *data = malloc(size);
            fread(data, size, 1, df);
            
            asu_set_payload(file, data, size);
            free(data);
            fclose(df);
        }
    }
    
    asu_close(file);
    printf("ASU file created: %s\n", filename);
    return 0;
}

int cmd_info(const char *filename) {
    asu_file_t *file = asu_open(filename, "rb");
    if (!file) {
        fprintf(stderr, "Failed to open ASU file\n");
        return 1;
    }
    
    printf("ASU File Information\n");
    printf("===================\n");
    printf("Filename: %s\n", filename);
    printf("Version: %d.%d\n", file->header.version_major, file->header.version_minor);
    printf("Header size: %lu bytes\n", file->header.header_size);
    printf("Metadata size: %lu bytes\n", file->header.metadata_size);
    printf("Payload size: %lu bytes\n", file->header.payload_size);
    printf("Compression: %d\n", file->header.compression_type);
    printf("Encryption: %d\n", file->header.encryption_type);
    printf("Created: %s", ctime((time_t*)&file->header.creation_time));
    printf("Modified: %s", ctime((time_t*)&file->header.modification_time));
    
    if (file->metadata) {
        printf("\nMetadata:\n%s\n", file->metadata);
    }
    
    asu_close(file);
    return 0;
}

int main(int argc, char *argv[]) {
    if (argc < 3) {
        print_usage(argv[0]);
        return 1;
    }
    
    const char *command = argv[1];
    const char *filename = argv[2];
    
    if (strcmp(command, "create") == 0) {
        return cmd_create(filename, NULL, NULL);
    } else if (strcmp(command, "info") == 0) {
        return cmd_info(filename);
    } else if (strcmp(command, "validate") == 0) {
        asu_file_t *file = asu_open(filename, "rb");
        if (!file) return 1;
        
        int result = asu_validate(file);
        asu_close(file);
        
        if (result == 0) {
            printf("File validation: PASSED\n");
            return 0;
        } else {
            printf("File validation: FAILED\n");
            return 1;
        }
    }
    
    print_usage(argv[0]);
    return 1;
}
```

## 6. Language Bindings

### Python Binding (ctypes)
```python
# asu_python.py
import ctypes
from ctypes import Structure, c_uint64, c_uint32, c_uint16, c_uint8, c_char_p, POINTER

class ASUHeader(Structure):
    _fields_ = [
        ("magic", c_uint64),
        ("version_major", c_uint16),
        ("version_minor", c_uint16),
        ("format_type", c_uint32),
        ("header_size", c_uint64),
        ("metadata_size", c_uint64),
        ("payload_size", c_uint64),
        ("footer_offset", c_uint64),
        ("compression_type", c_uint8),
        ("encryption_type", c_uint8),
        ("integrity_type", c_uint8),
        ("reserved1", c_uint8),
        ("feature_flags", c_uint32),
        ("creation_time", c_uint64),
        ("modification_time", c_uint64),
        ("file_hash", c_uint8 * 32),
        ("reserved2", c_uint8 * 16),
    ]

class ASUFile:
    def __init__(self, library_path="./libasu.so"):
        self.lib = ctypes.CDLL(library_path)
        
        # Define function prototypes
        self.lib.asu_create.argtypes = [c_char_p]
        self.lib.asu_create.restype = ctypes.c_void_p
        
        self.lib.asu_open.argtypes = [c_char_p, c_char_p]
        self.lib.asu_open.restype = ctypes.c_void_p
        
        self.lib.asu_close.argtypes = [ctypes.c_void_p]
        self.lib.asu_close.restype = ctypes.c_int
        
        self.lib.asu_set_metadata.argtypes = [ctypes.c_void_p, c_char_p]
        self.lib.asu_set_metadata.restype = ctypes.c_int
        
        self.lib.asu_get_metadata.argtypes = [ctypes.c_void_p]
        self.lib.asu_get_metadata.restype = c_char_p
        
        self.file_ptr = None
    
    def create(self, filename):
        self.file_ptr = self.lib.asu_create(filename.encode())
        return self.file_ptr is not None
    
    def open(self, filename, mode="rb"):
        self.file_ptr = self.lib.asu_open(filename.encode(), mode.encode())
        return self.file_ptr is not None
    
    def close(self):
        if self.file_ptr:
            result = self.lib.asu_close(self.file_ptr)
            self.file_ptr = None
            return result == 0
        return True
    
    def set_metadata(self, metadata_json):
        if self.file_ptr:
            return self.lib.asu_set_metadata(self.file_ptr, metadata_json.encode()) == 0
        return False
    
    def get_metadata(self):
        if self.file_ptr:
            result = self.lib.asu_get_metadata(self.file_ptr)
            return result.decode() if result else None
        return None

# Usage example
if __name__ == "__main__":
    asu = ASUFile()
    
    # Create new ASU file
    if asu.create("test.asu"):
        asu.set_metadata('{"name": "test", "version": "1.0"}')
        asu.close()
        print("ASU file created successfully")
    
    # Open and read ASU file
    if asu.open("test.asu"):
        metadata = asu.get_metadata()
        print(f"Metadata: {metadata}")
        asu.close()
```

## 7. Testing Framework

### Unit Tests
```c
// test_asu.c
#include <assert.h>
#include <string.h>
#include "asu_core.h"

void test_file_creation() {
    printf("Testing file creation...\n");
    
    asu_file_t *file = asu_create("test_create.asu");
    assert(file != NULL);
    assert(file->is_open == 1);
    assert(file->header.magic == ASU_MAGIC_HEADER);
    
    asu_close(file);
    printf("✓ File creation test passed\n");
}

void test_metadata_operations() {
    printf("Testing metadata operations...\n");
    
    asu_file_t *file = asu_create("test_metadata.asu");
    assert(file != NULL);
    
    const char *test_metadata = "{\"test\": \"data\", \"version\": 1}";
    assert(asu_set_metadata(file, test_metadata) == 0);
    
    char *retrieved = asu_get_metadata(file);
    assert(strcmp(retrieved, test_metadata) == 0);
    free(retrieved);
    
    asu_close(file);
    printf("✓ Metadata operations test passed\n");
}

void test_compression() {
    printf("Testing compression...\n");
    
    asu_file_t *file = asu_create("test_compression.asu");
    assert(file != NULL);
    
    const char *test_data = "This is test data for compression testing. "
                           "It should compress well with repetitive content. "
                           "This is test data for compression testing.";
    
    assert(asu_set_payload(file, (const uint8_t*)test_data, strlen(test_data)) == 0);
    assert(asu_set_compression(file, ASU_COMPRESS_ZLIB) == 0);
    assert(asu_compress_payload(file) == 0);
    
    asu_close(file);
    printf("✓ Compression test passed\n");
}