#pragma pack(push, 1)

/**
 * HEADER FIXED SECTION (64 bytes)
 * Semua offset dihitung dari awal file
 */
typedef struct {
    // === IDENTIFICATION (16 bytes) ===
    uint8_t magic[8];        // 0x00: "WASUENT" + null terminator
    uint16_t version_major;  // 0x08: Major version
    uint16_t version_minor;  // 0x0A: Minor version
    uint32_t format_type;    // 0x0C: File type identifier
    
    // === FILE STRUCTURE (32 bytes) ===
    uint64_t header_size;    // 0x10: Total header size
    uint64_t metadata_size;  // 0x18: Metadata section size
    uint64_t payload_size;   // 0x20: Payload section size
    uint64_t footer_offset;  // 0x28: Offset to footer
    
    // === FLAGS & FEATURES (16 bytes) ===
    uint8_t compression_type; // 0x30: 0=None, 1=LZ4, 2=ZSTD
    uint8_t encryption_type;  // 0x31: 0=None, 1=AES128, 2=AES256
    uint8_t integrity_type;   // 0x32: 0=None, 1=CRC32, 2=SHA256
    uint8_t reserved;         // 0x33: Alignment
    uint32_t feature_flags;   // 0x34: Bit flags for features
    uint64_t creation_time;   // 0x38: File creation time (ns)
} WasuCoreHeader;

/**
 * HEADER EXTENDED SECTION (variabel)
 * Diisi berdasarkan kebutuhan
 */
typedef struct {
    uint32_t section_type;   // Jenis section
    uint32_t section_size;   // Ukuran section
    uint8_t data[];          // Data section
} WasuExtendedSection;

/**
 * METADATA SECTION (variabel)
 */
typedef struct {
    uint32_t metadata_type;  // Tipe metadata
    uint32_t metadata_size;  // Ukuran metadata
    uint8_t data[];          // Data metadata
} WasuMetadata;

/**
 * PAYLOAD SECTION (variabel)
 */
typedef struct {
    uint64_t payload_offset; // Offset payload sebenarnya
    uint64_t payload_size;   // Ukuran payload terkompresi
    uint8_t data[];          // Data payload
} WasuPayload;

/**
 * FOOTER (32 bytes)
 */
typedef struct {
    uint8_t magic[8];        // "WASUFTR" + null terminator
    uint64_t file_size;      // Total file size
    uint8_t checksum[16];    // SHA-128 checksum
    uint64_t end_marker;     // End of file marker
} WasuFooter;

#pragma pack(pop)