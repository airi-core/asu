# File Extension .ASU - Native Library Implementation

## Header Structure (128 bytes)

### Primary Header Block (0x0000 - 0x007F)

```c
// Native Library Structure Definition
typedef struct ASU_HEADER {
    // Magic & Version Block (0x0000 - 0x000F)
    uint8_t     magic[8];           // 0x0000: "ASUMAGIC" - File identification
    uint16_t    version_major;      // 0x0008: Major version number
    uint16_t    version_minor;      // 0x000A: Minor version number
    uint32_t    format_revision;    // 0x000C: Format revision number
    
    // File Metadata Block (0x0010 - 0x002F)
    uint64_t    file_size;          // 0x0010: Total file size in bytes
    uint64_t    header_size;        // 0x0018: Header section size
    uint64_t    metadata_offset;    // 0x0020: Metadata section offset
    uint64_t    payload_offset;     // 0x0028: Payload section offset
    
    // Compression & Security Block (0x0030 - 0x004F)
    uint32_t    compression_type;   // 0x0030: 0=None, 1=GZIP, 2=ZSTD, 3=LZ4
    uint32_t    compression_level;  // 0x0034: Compression level (0-9)
    uint32_t    encryption_type;    // 0x0038: 0=None, 1=AES256, 2=ChaCha20
    uint32_t    encryption_mode;    // 0x003C: 0=ECB, 1=CBC, 2=GCM, 3=CTR
    uint8_t     encryption_key[16]; // 0x0040: Key derivation salt/hash
    
    // Integrity & Validation Block (0x0050 - 0x006F)
    uint32_t    checksum_type;      // 0x0050: 0=None, 1=CRC32, 2=SHA256, 3=BLAKE3
    uint8_t     checksum_hash[32];  // 0x0054: Checksum/hash value (padded)
    uint32_t    signature_type;     // 0x0074: 0=None, 1=RSA, 2=ECDSA, 3=EdDSA
    
    // Extended Attributes Block (0x0078 - 0x007F)
    uint32_t    feature_flags;      // 0x0078: Feature bitmask
    uint32_t    reserved;           // 0x007C: Reserved for future use
} ASU_HEADER;
```

## Metadata Section (Variable Length)

### Offset Calculation: header_size (typically 0x0080)

```c
// Metadata Structure
typedef struct ASU_METADATA {
    // Metadata Header (0x0000 - 0x001F)
    uint32_t    metadata_version;   // 0x0000: Metadata format version
    uint32_t    total_entries;      // 0x0004: Number of metadata entries
    uint64_t    metadata_size;      // 0x0008: Total metadata section size
    uint64_t    next_section_offset;// 0x0010: Offset to next section
    uint64_t    reserved[2];        // 0x0018: Reserved space
    
    // Dynamic Metadata Entries (Variable)
    ASU_METADATA_ENTRY entries[];   // Variable length entries
} ASU_METADATA;

typedef struct ASU_METADATA_ENTRY {
    uint16_t    entry_type;         // Entry type identifier
    uint16_t    entry_size;         // Size of this entry
    uint32_t    flags;              // Entry-specific flags
    uint8_t     data[];             // Variable data based on type
} ASU_METADATA_ENTRY;

// Metadata Entry Types
#define ASU_META_FILENAME       0x0001  // Original filename
#define ASU_META_TIMESTAMP      0x0002  // Creation/modification timestamps
#define ASU_META_AUTHOR         0x0003  // Author information
#define ASU_META_DESCRIPTION    0x0004  // File description
#define ASU_META_DEPENDENCIES   0x0005  // Dependency list
#define ASU_META_PLATFORM       0x0006  // Target platform info
#define ASU_META_LICENSE        0x0007  // License information
#define ASU_META_DOCKER_CONFIG  0x0008  // Docker configuration
#define ASU_META_GIT_INFO       0x0009  // Git repository info
#define ASU_META_EXECUTION      0x000A  // Execution parameters
#define ASU_META_ENVIRONMENT    0x000B  // Environment variables
```

## Payload Section (Variable Length)

### Offset Calculation: payload_offset (from header)

```c
// Payload Structure
typedef struct ASU_PAYLOAD {
    // Payload Header (0x0000 - 0x001F)
    uint32_t    payload_version;    // 0x0000: Payload format version
    uint32_t    chunk_count;        // 0x0004: Number of data chunks
    uint64_t    uncompressed_size;  // 0x0008: Original payload size
    uint64_t    compressed_size;    // 0x0010: Compressed payload size
    uint64_t    reserved;           // 0x0018: Reserved space
    
    // Chunk Directory (Variable)
    ASU_CHUNK_ENTRY chunks[];       // Chunk information array
    
    // Compressed Data (Variable)
    uint8_t     compressed_data[];  // Actual compressed payload
} ASU_PAYLOAD;

typedef struct ASU_CHUNK_ENTRY {
    uint64_t    offset;             // Offset within compressed data
    uint64_t    compressed_size;    // Compressed chunk size
    uint64_t    uncompressed_size;  // Uncompressed chunk size
    uint32_t    chunk_type;         // Chunk type identifier
    uint32_t    checksum;           // Chunk checksum
} ASU_CHUNK_ENTRY;

// Chunk Types
#define ASU_CHUNK_DOCKERFILE    0x0001  // Docker configuration
#define ASU_CHUNK_SOURCE_CODE   0x0002  // Source code files
#define ASU_CHUNK_BINARY        0x0003  // Binary executables
#define ASU_CHUNK_DEPENDENCIES  0x0004  // Dependency packages
#define ASU_CHUNK_SCRIPTS       0x0005  // Installation/execution scripts
#define ASU_CHUNK_RESOURCES     0x0006  // Resource files
#define ASU_CHUNK_CONFIG        0x0007  // Configuration files
```

## Index Section (Optional)

### Offset Calculation: Dynamic based on payload end

```c
// Index Structure for Fast Access
typedef struct ASU_INDEX {
    // Index Header (0x0000 - 0x001F)
    uint32_t    index_version;      // 0x0000: Index format version
    uint32_t    entry_count;        // 0x0004: Number of index entries
    uint64_t    index_size;         // 0x0008: Total index section size
    uint64_t    reserved[2];        // 0x0010: Reserved space
    
    // Index Entries (Variable)
    ASU_INDEX_ENTRY entries[];      // Index entry array
} ASU_INDEX;

typedef struct ASU_INDEX_ENTRY {
    uint64_t    name_hash;          // Hash of entry name
    uint64_t    offset;             // Offset to actual data
    uint64_t    size;               // Size of data
    uint32_t    type;               // Entry type
    uint32_t    flags;              // Entry flags
} ASU_INDEX_ENTRY;
```

## Footer Section (64 bytes)

### Offset Calculation: file_size - 64

```c
// Footer Structure
typedef struct ASU_FOOTER {
    // Footer Magic & Validation (0x0000 - 0x001F)
    uint8_t     footer_magic[8];    // 0x0000: "ASUFOOTR" - Footer identification
    uint64_t    header_offset;      // 0x0008: Offset back to header
    uint64_t    total_file_size;    // 0x0010: Total file size verification
    uint64_t    creation_timestamp; // 0x0018: File creation timestamp
    
    // Integrity Verification (0x0020 - 0x003F)
    uint8_t     master_hash[32];    // 0x0020: Master file hash (SHA256)
    
    // Footer End Marker (0x0040 - 0x003F)
    uint8_t     end_marker[8];      // 0x0040: "ASUENDMK" - End marker
    uint64_t    reserved;           // 0x0048: Reserved space
} ASU_FOOTER;
```

## Implementation Requirements

### Native Library Functions

```c
// Core Library Functions
typedef struct ASU_CONTEXT {
    FILE*       file_handle;
    ASU_HEADER* header;
    ASU_METADATA* metadata;
    ASU_PAYLOAD* payload;
    ASU_INDEX*  index;
    ASU_FOOTER* footer;
    uint32_t    flags;
    void*       user_data;
} ASU_CONTEXT;

// Required API Functions
ASU_CONTEXT* asu_create(const char* filename, uint32_t flags);
int asu_open(ASU_CONTEXT* ctx, const char* filename, uint32_t mode);
int asu_close(ASU_CONTEXT* ctx);
int asu_validate(ASU_CONTEXT* ctx);

// Header Operations
int asu_write_header(ASU_CONTEXT* ctx, const ASU_HEADER* header);
int asu_read_header(ASU_CONTEXT* ctx, ASU_HEADER* header);
int asu_update_header_field(ASU_CONTEXT* ctx, uint32_t field_id, const void* data);

// Metadata Operations
int asu_add_metadata(ASU_CONTEXT* ctx, uint16_t type, const void* data, uint16_t size);
int asu_get_metadata(ASU_CONTEXT* ctx, uint16_t type, void* buffer, uint16_t* size);
int asu_remove_metadata(ASU_CONTEXT* ctx, uint16_t type);

// Payload Operations
int asu_write_payload(ASU_CONTEXT* ctx, const void* data, uint64_t size);
int asu_read_payload(ASU_CONTEXT* ctx, void* buffer, uint64_t size);
int asu_add_chunk(ASU_CONTEXT* ctx, uint32_t type, const void* data, uint64_t size);
int asu_extract_chunk(ASU_CONTEXT* ctx, uint32_t type, void* buffer, uint64_t* size);

// Compression Operations
int asu_set_compression(ASU_CONTEXT* ctx, uint32_t type, uint32_t level);
int asu_compress_data(const void* input, uint64_t input_size, void* output, uint64_t* output_size);
int asu_decompress_data(const void* input, uint64_t input_size, void* output, uint64_t* output_size);

// Encryption Operations
int asu_set_encryption(ASU_CONTEXT* ctx, uint32_t type, const uint8_t* key, uint32_t key_size);
int asu_encrypt_data(ASU_CONTEXT* ctx, const void* input, uint64_t size, void* output);
int asu_decrypt_data(ASU_CONTEXT* ctx, const void* input, uint64_t size, void* output);

// Index Operations
int asu_build_index(ASU_CONTEXT* ctx);
int asu_find_entry(ASU_CONTEXT* ctx, const char* name, ASU_INDEX_ENTRY* entry);
int asu_list_entries(ASU_CONTEXT* ctx, ASU_INDEX_ENTRY* entries, uint32_t* count);

// Validation Operations
int asu_calculate_checksum(ASU_CONTEXT* ctx, uint32_t type, uint8_t* hash);
int asu_verify_integrity(ASU_CONTEXT* ctx);
int asu_sign_file(ASU_CONTEXT* ctx, const uint8_t* private_key, uint32_t key_size);
int asu_verify_signature(ASU_CONTEXT* ctx, const uint8_t* public_key, uint32_t key_size);
```

### Docker Integration Specific Offsets

```c
// Docker-specific metadata structure
typedef struct ASU_DOCKER_CONFIG {
    uint32_t    config_version;     // Docker config version
    uint32_t    base_image_hash;    // Hash of base image name
    uint32_t    port_count;         // Number of exposed ports
    uint32_t    volume_count;       // Number of volumes
    uint32_t    env_count;          // Number of environment variables
    uint32_t    command_offset;     // Offset to command string
    uint32_t    workdir_offset;     // Offset to working directory
    uint32_t    user_offset;        // Offset to user specification
    uint16_t    ports[16];          // Exposed ports array
    uint64_t    volume_offsets[8];  // Offsets to volume paths
    uint64_t    env_offsets[32];    // Offsets to env variables
} ASU_DOCKER_CONFIG;

// Git integration metadata
typedef struct ASU_GIT_INFO {
    uint8_t     commit_hash[20];    // Git commit SHA-1
    uint64_t    repository_url_offset; // Offset to repository URL
    uint64_t    branch_name_offset; // Offset to branch name
    uint64_t    tag_name_offset;    // Offset to tag name
    uint32_t    commit_timestamp;   // Commit timestamp
    uint32_t    dirty_flag;         // Working directory dirty flag
} ASU_GIT_INFO;

// Execution configuration
typedef struct ASU_EXECUTION_CONFIG {
    uint32_t    execution_type;     // 0=Script, 1=Binary, 2=Docker, 3=VM
    uint32_t    platform_mask;      // Supported platforms bitmask
    uint64_t    entry_point_offset; // Offset to entry point
    uint64_t    args_offset;        // Offset to arguments
    uint64_t    pre_exec_offset;    // Offset to pre-execution script
    uint64_t    post_exec_offset;   // Offset to post-execution script
    uint32_t    timeout_seconds;    // Execution timeout
    uint32_t    memory_limit_mb;    // Memory limit in MB
} ASU_EXECUTION_CONFIG;
```

### Memory Layout Requirements

```c
// Memory alignment requirements
#define ASU_ALIGNMENT           8       // 8-byte alignment for all structures
#define ASU_HEADER_SIZE         128     // Fixed header size
#define ASU_FOOTER_SIZE         64      // Fixed footer size
#define ASU_MIN_METADATA_SIZE   32      // Minimum metadata section size
#define ASU_CHUNK_ALIGNMENT     4096    // Chunk alignment for performance

// Size calculation macros
#define ASU_ALIGN_SIZE(size)    (((size) + ASU_ALIGNMENT - 1) & ~(ASU_ALIGNMENT - 1))
#define ASU_HEADER_OFFSET       0
#define ASU_METADATA_OFFSET     ASU_HEADER_SIZE
#define ASU_PAYLOAD_OFFSET(ctx) ((ctx)->header->payload_offset)
#define ASU_FOOTER_OFFSET(ctx)  ((ctx)->header->file_size - ASU_FOOTER_SIZE)

// Buffer size requirements
#define ASU_MIN_BUFFER_SIZE     8192    // Minimum I/O buffer size
#define ASU_MAX_CHUNK_SIZE      (64 * 1024 * 1024)  // Maximum chunk size (64MB)
#define ASU_MAX_METADATA_SIZE   (1 * 1024 * 1024)   // Maximum metadata size (1MB)
```

### Error Codes & Constants

```c
// Error codes
#define ASU_SUCCESS             0       // Success
#define ASU_ERROR_INVALID_FILE  -1      // Invalid file format
#define ASU_ERROR_CORRUPT_DATA  -2      // Corrupted data
#define ASU_ERROR_UNSUPPORTED   -3      // Unsupported feature
#define ASU_ERROR_MEMORY        -4      // Memory allocation error
#define ASU_ERROR_IO            -5      // I/O error
#define ASU_ERROR_CRYPTO        -6      // Cryptographic error
#define ASU_ERROR_COMPRESSION   -7      // Compression error
#define ASU_ERROR_VALIDATION    -8      // Validation error

// Feature flags
#define ASU_FEATURE_COMPRESSION 0x00000001  // Compression support
#define ASU_FEATURE_ENCRYPTION  0x00000002  // Encryption support
#define ASU_FEATURE_SIGNATURE   0x00000004  // Digital signature support
#define ASU_FEATURE_INDEX       0x00000008  // Index support
#define ASU_FEATURE_DOCKER      0x00000010  // Docker integration
#define ASU_FEATURE_GIT         0x00000020  // Git integration
#define ASU_FEATURE_STREAMING   0x00000040  // Streaming support

// Magic constants
#define ASU_HEADER_MAGIC        "ASUMAGIC"  // Header magic bytes
#define ASU_FOOTER_MAGIC        "ASUFOOTR"  // Footer magic bytes
#define ASU_END_MARKER          "ASUENDMK"  // End marker bytes
```

## Implementation Notes

### Critical Requirements
1. **Byte Order**: All multi-byte values stored in little-endian format
2. **Alignment**: All structures must be 8-byte aligned
3. **Validation**: Every section must have integrity verification
4. **Versioning**: Forward/backward compatibility through version fields
5. **Streaming**: Support for streaming read/write operations
6. **Memory Safety**: Bounds checking for all buffer operations
7. **Thread Safety**: Thread-safe operations with proper locking

### Platform Dependencies
- **Windows**: Use Win32 API for file operations
- **Linux/Unix**: Use POSIX file operations
- **macOS**: Use BSD/Darwin specific optimizations
- **Embedded**: Reduced memory footprint variants

### Cryptographic Dependencies
- **OpenSSL**: For AES encryption and SHA hashing
- **libsodium**: For ChaCha20 and modern cryptography
- **BLAKE3**: For high-performance hashing

### Compression Dependencies
- **zlib**: For GZIP compression
- **zstd**: For Zstandard compression
- **lz4**: For LZ4 compression