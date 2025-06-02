# Arsitektur Directory File Ekstensi .ASU

## Struktur Directory Utama

```
asu-extension/
├── src/
│   ├── core/
│   │   ├── header.c                    # Magic header & metadata processor
│   │   ├── header.h                    # Header definitions & constants
│   │   ├── payload.c                   # Payload data handler
│   │   ├── payload.h                   # Payload structures
│   │   ├── footer.c                    # Footer & checksum validator
│   │   ├── footer.h                    # Footer definitions
│   │   ├── compression.c               # Compression algorithms (LZ4/ZSTD)
│   │   ├── compression.h               # Compression interfaces
│   │   ├── encryption.c                # AES-256 encryption implementation
│   │   ├── encryption.h                # Encryption definitions
│   │   ├── checksum.c                  # SHA-256/CRC32 implementations
│   │   ├── checksum.h                  # Checksum interfaces
│   │   ├── validator.c                 # File integrity validator
│   │   └── validator.h                 # Validation interfaces
│   │
│   ├── io/
│   │   ├── file_reader.c               # Binary file reading operations
│   │   ├── file_reader.h               # Reader function declarations
│   │   ├── file_writer.c               # Binary file writing operations
│   │   ├── file_writer.h               # Writer function declarations
│   │   ├── stream_handler.c            # Stream processing for large files
│   │   ├── stream_handler.h            # Stream interface definitions
│   │   ├── buffer_manager.c            # Memory buffer management
│   │   └── buffer_manager.h            # Buffer management interfaces
│   │
│   ├── parser/
│   │   ├── asu_parser.c                # Main .asu file parser
│   │   ├── asu_parser.h                # Parser interface definitions
│   │   ├── metadata_parser.c           # Metadata section parser
│   │   ├── metadata_parser.h           # Metadata parsing interfaces
│   │   ├── hex_dump.c                  # Hex dump generator
│   │   ├── hex_dump.h                  # Hex dump interfaces
│   │   ├── binary_analyzer.c           # Binary data analysis
│   │   └── binary_analyzer.h           # Analysis function declarations
│   │
│   ├── creator/
│   │   ├── asu_creator.c               # .asu file creation engine
│   │   ├── asu_creator.h               # Creator interface definitions
│   │   ├── template_generator.c        # Template file generator
│   │   ├── template_generator.h        # Template interfaces
│   │   ├── dependency_resolver.c       # Dependency management
│   │   ├── dependency_resolver.h       # Dependency interfaces
│   │   ├── docker_integrator.c         # Docker image integration
│   │   └── docker_integrator.h         # Docker integration interfaces
│   │
│   ├── crypto/
│   │   ├── aes_native.c                # AES encryption native implementation
│   │   ├── aes_native.h                # AES function declarations
│   │   ├── sha256_native.c             # SHA-256 native implementation
│   │   ├── sha256_native.h             # SHA-256 interfaces
│   │   ├── rsa_native.c                # RSA signature implementation
│   │   ├── rsa_native.h                # RSA function declarations
│   │   ├── random_generator.c          # Cryptographically secure RNG
│   │   └── random_generator.h          # RNG interfaces
│   │
│   ├── utils/
│   │   ├── endian_converter.c          # Big/Little endian conversion
│   │   ├── endian_converter.h          # Endian conversion interfaces
│   │   ├── string_utils.c              # String manipulation utilities
│   │   ├── string_utils.h              # String utility interfaces
│   │   ├── memory_pool.c               # Memory pool allocator
│   │   ├── memory_pool.h               # Memory pool interfaces
│   │   ├── error_handler.c             # Error handling & logging
│   │   ├── error_handler.h             # Error handling interfaces
│   │   ├── platform_detect.c           # OS/Architecture detection
│   │   └── platform_detect.h           # Platform detection interfaces
│   │
│   ├── api/
│   │   ├── asu_api.c                   # Public API implementation
│   │   ├── asu_api.h                   # Public API declarations
│   │   ├── c_bindings.c                # C language bindings
│   │   ├── c_bindings.h                # C binding interfaces
│   │   ├── python_bindings.c           # Python C extension module
│   │   ├── node_bindings.c             # Node.js native addon
│   │   └── java_bindings.c             # JNI bindings for Java
│   │
│   └── main.c                          # Main entry point & CLI interface
│
├── include/
│   ├── asu_types.h                     # Core data type definitions
│   ├── asu_constants.h                 # Magic numbers & constants
│   ├── asu_errors.h                    # Error code definitions
│   ├── asu_config.h                    # Configuration macros
│   └── asu.h                           # Main header file
│
├── lib/
│   ├── native/
│   │   ├── linux/
│   │   │   ├── x86_64/
│   │   │   │   └── libasu.so           # Linux x64 shared library
│   │   │   ├── aarch64/
│   │   │   │   └── libasu.so           # Linux ARM64 shared library
│   │   │   └── riscv64/
│   │   │       └── libasu.so           # Linux RISC-V shared library
│   │   ├── windows/
│   │   │   ├── x64/
│   │   │   │   └── asu.dll             # Windows x64 DLL
│   │   │   └── arm64/
│   │   │       └── asu.dll             # Windows ARM64 DLL
│   │   ├── macos/
│   │   │   ├── x86_64/
│   │   │   │   └── libasu.dylib        # macOS Intel shared library
│   │   │   └── arm64/
│   │   │       └── libasu.dylib        # macOS Apple Silicon shared library
│   │   └── freebsd/
│   │       └── x86_64/
│   │           └── libasu.so           # FreeBSD shared library
│   │
│   └── static/
│       ├── libasu.a                    # Static library for linking
│       └── libasu_debug.a              # Debug version static library
│
├── tests/
│   ├── unit/
│   │   ├── test_header.c               # Header parsing unit tests
│   │   ├── test_payload.c              # Payload handling unit tests
│   │   ├── test_footer.c               # Footer validation unit tests
│   │   ├── test_compression.c          # Compression algorithm tests
│   │   ├── test_encryption.c           # Encryption/decryption tests
│   │   ├── test_checksum.c             # Checksum calculation tests
│   │   ├── test_parser.c               # Parser functionality tests
│   │   ├── test_creator.c              # File creation tests
│   │   └── test_validator.c            # File validation tests
│   │
│   ├── integration/
│   │   ├── test_full_cycle.c           # Create -> Parse -> Validate tests
│   │   ├── test_docker_integration.c   # Docker integration tests
│   │   ├── test_cross_platform.c       # Cross-platform compatibility tests
│   │   └── test_performance.c          # Performance benchmark tests
│   │
│   ├── fixtures/
│   │   ├── sample_valid.asu            # Valid test files
│   │   ├── sample_corrupted.asu        # Corrupted test files
│   │   ├── sample_encrypted.asu        # Encrypted test files
│   │   └── sample_compressed.asu       # Compressed test files
│   │
│   └── scripts/
│       ├── run_tests.sh                # Test execution script
│       ├── generate_fixtures.py        # Test file generator
│       └── benchmark.py                # Performance testing script
│
├── tools/
│   ├── asu_inspector.c                 # File inspection tool
│   ├── asu_converter.c                 # Format conversion tool
│   ├── asu_validator.c                 # Standalone validator
│   ├── hex_viewer.c                    # Hex dump viewer
│   └── benchmark_tool.c                # Performance measurement tool
│
├── bindings/
│   ├── python/
│   │   ├── setup.py                    # Python package setup
│   │   ├── asu/__init__.py             # Python module init
│   │   ├── asu/core.py                 # Python wrapper classes
│   │   └── asu/exceptions.py           # Python-specific exceptions
│   │
│   ├── node/
│   │   ├── package.json                # Node.js package configuration
│   │   ├── binding.gyp                 # Node.js native build config
│   │   ├── index.js                    # Node.js main module
│   │   └── lib/asu.js                  # JavaScript wrapper
│   │
│   ├── java/
│   │   ├── pom.xml                     # Maven build configuration
│   │   ├── src/main/java/com/asu/     # Java package structure
│   │   │   ├── ASUFile.java            # Main Java class
│   │   │   ├── ASUParser.java          # Parser class
│   │   │   └── ASUException.java       # Java exceptions
│   │   └── src/main/resources/         # Native library resources
│   │
│   └── rust/
│       ├── Cargo.toml                  # Rust package configuration
│       ├── src/lib.rs                  # Rust FFI bindings
│       └── build.rs                    # Rust build script
│
├── docs/
│   ├── specification/
│   │   ├── file_format.md              # .ASU file format specification
│   │   ├── header_structure.md         # Header format documentation
│   │   ├── compression_spec.md         # Compression algorithm specs
│   │   └── encryption_spec.md          # Encryption implementation details
│   │
│   ├── api/
│   │   ├── c_api.md                    # C API documentation
│   │   ├── python_api.md               # Python API documentation
│   │   ├── node_api.md                 # Node.js API documentation
│   │   └── java_api.md                 # Java API documentation
│   │
│   └── examples/
│       ├── basic_usage.c               # Basic C usage examples
│       ├── advanced_features.c         # Advanced feature examples
│       ├── python_examples.py          # Python usage examples
│       └── docker_integration.md       # Docker integration guide
│
├── build/
│   ├── cmake/
│   │   ├── CMakeLists.txt              # Main CMake configuration
│   │   ├── FindASU.cmake               # CMake find module
│   │   └── cross_compile/              # Cross-compilation configs
│   │       ├── linux-arm64.cmake       # ARM64 Linux cross-compile
│   │       ├── windows-x64.cmake       # Windows x64 cross-compile
│   │       └── macos-universal.cmake   # macOS universal binary
│   │
│   ├── make/
│   │   ├── Makefile                    # Main Makefile
│   │   ├── Makefile.linux              # Linux-specific rules
│   │   ├── Makefile.windows            # Windows-specific rules
│   │   └── Makefile.macos              # macOS-specific rules
│   │
│   └── scripts/
│       ├── build.sh                    # Main build script
│       ├── cross_compile.sh            # Cross-compilation script
│       ├── package.sh                  # Package creation script
│       └── install.sh                  # Installation script
│
├── examples/
│   ├── basic/
│   │   ├── create_asu.c                # Basic file creation example
│   │   ├── parse_asu.c                 # Basic parsing example
│   │   └── validate_asu.c              # Basic validation example
│   │
│   ├── advanced/
│   │   ├── encrypted_asu.c             # Encryption example
│   │   ├── compressed_asu.c            # Compression example
│   │   ├── streaming_parse.c           # Large file streaming example
│   │   └── docker_container.c          # Docker integration example
│   │
│   └── bindings/
│       ├── python_example.py           # Python binding usage
│       ├── node_example.js             # Node.js binding usage
│       ├── java_example.java           # Java binding usage
│       └── rust_example.rs             # Rust binding usage
│
├── scripts/
│   ├── setup_env.sh                    # Development environment setup
│   ├── install_deps.sh                 # Dependency installation
│   ├── format_code.sh                  # Code formatting script
│   ├── lint_check.sh                   # Code linting script
│   ├── run_benchmarks.sh               # Performance benchmarking
│   └── package_release.sh              # Release packaging script
│
├── docker/
│   ├── Dockerfile.dev                  # Development container
│   ├── Dockerfile.build                # Build container
│   ├── Dockerfile.test                 # Testing container
│   └── docker-compose.yml              # Multi-container setup
│
├── .github/
│   └── workflows/
│       ├── ci.yml                      # Continuous integration
│       ├── cross_platform_build.yml    # Multi-platform builds
│       ├── security_scan.yml           # Security vulnerability scan
│       └── release.yml                 # Release automation
│
├── CMakeLists.txt                      # Root CMake configuration
├── Makefile                            # Root Makefile
├── configure                           # Autotools configure script
├── README.md                           # Project documentation
├── LICENSE                             # Software license
├── CHANGELOG.md                        # Version history
├── CONTRIBUTORS.md                     # Contributor list
└── .gitignore                          # Git ignore rules
```

## Deskripsi Detail Setiap Komponen

### Core Components (`src/core/`)

#### `header.c/h`
- **Fungsi**: Parsing dan validasi magic header "WASUENT"
- **Implementasi**: Binary parsing dengan struct packing
- **Fitur**: Version checking, format type validation
- **Dependencies**: endian_converter.h, error_handler.h

#### `payload.c/h`
- **Fungsi**: Handling data payload utama
- **Implementasi**: Stream processing untuk file besar
- **Fitur**: Chunked reading, memory management
- **Dependencies**: compression.h, encryption.h

#### `footer.c/h`
- **Fungsi**: Footer validation dan checksum verification
- **Implementasi**: SHA-256 checksum calculation
- **Fitur**: Integrity checking, magic footer validation
- **Dependencies**: checksum.h, validator.h

#### `compression.c/h`
- **Fungsi**: LZ4/ZSTD compression algorithms
- **Implementasi**: Native implementation tanpa external libs
- **Fitur**: Multiple compression levels, streaming compression
- **Performance**: Optimized assembly untuk x86_64/ARM64

#### `encryption.c/h`
- **Fungsi**: AES-256-GCM encryption/decryption
- **Implementasi**: Native crypto implementation
- **Fitur**: Key derivation, IV generation, authentication
- **Security**: Constant-time operations, secure memory clearing

### I/O Operations (`src/io/`)

#### `file_reader.c/h`
- **Fungsi**: Binary file reading dengan error handling
- **Implementasi**: Platform-specific optimizations
- **Fitur**: Memory-mapped I/O, async reading
- **Performance**: Zero-copy operations where possible

#### `stream_handler.c/h`
- **Fungsi**: Large file streaming processing
- **Implementasi**: Chunked processing dengan configurable buffer
- **Fitur**: Progress callbacks, pause/resume capability
- **Memory**: Constant memory usage regardless file size

### Parser Engine (`src/parser/`)

#### `asu_parser.c/h`
- **Fungsi**: Main parsing engine untuk .asu files
- **Implementasi**: State machine parser
- **Fitur**: Streaming parser, error recovery
- **Validation**: Format compliance checking

#### `hex_dump.c/h`
- **Fungsi**: Human-readable hex dump generation
- **Implementasi**: Configurable output format
- **Fitur**: ASCII representation, address offsets
- **Output**: Compatible dengan standard hex viewers

### Creator Engine (`src/creator/`)

#### `asu_creator.c/h`
- **Fungsi**: .asu file creation dari input data
- **Implementasi**: Template-based generation
- **Fitur**: Metadata injection, dependency bundling
- **Optimization**: Compression ratio optimization

#### `docker_integrator.c/h`
- **Fungsi**: Docker image integration
- **Implementasi**: Docker API interfacing
- **Fitur**: Container creation, git clone automation
- **Dependency**: libcurl untuk Docker REST API

### Cryptographic Functions (`src/crypto/`)

#### `aes_native.c/h`
- **Fungsi**: AES encryption native implementation
- **Implementasi**: Optimized assembly routines
- **Fitur**: Hardware AES-NI support when available
- **Security**: Side-channel attack resistant

#### `sha256_native.c/h`
- **Fungsi**: SHA-256 hashing implementation
- **Implementasi**: RFC 6234 compliant
- **Fitur**: Streaming hashing, HMAC support
- **Performance**: SIMD optimizations

### API Bindings (`src/api/`)

#### `asu_api.c/h`
- **Fungsi**: Public C API interface
- **Implementasi**: Thread-safe operations
- **Fitur**: Reference counting, error propagation
- **ABI**: Stable ABI dengan version management

#### Language Bindings
- **Python**: CPython C extension module
- **Node.js**: N-API native addon
- **Java**: JNI implementation
- **Rust**: FFI safe wrapper

### Build System

#### CMake Configuration
- **Cross-platform**: Windows, Linux, macOS, FreeBSD
- **Architecture**: x86_64, ARM64, RISC-V
- **Optimization**: -O3, LTO, PGO support
- **Static/Dynamic**: Configurable library type

#### Native Library Output
- **Linux**: .so shared libraries
- **Windows**: .dll dynamic libraries  
- **macOS**: .dylib shared libraries
- **Static**: .a archive files

### Testing Framework

#### Unit Tests
- **Coverage**: 95%+ code coverage target
- **Framework**: Custom lightweight test framework
- **Isolation**: Each test in separate process
- **Automation**: Continuous integration ready

#### Integration Tests
- **End-to-end**: Complete workflow testing
- **Performance**: Benchmark regression testing
- **Compatibility**: Cross-platform validation
- **Docker**: Container integration testing

### Requirements

#### System Dependencies
```bash
# Build tools
gcc >= 9.0 atau clang >= 10.0
cmake >= 3.16
make >= 4.0

# Development libraries
libc6-dev
linux-headers (Linux)
xcode-command-line-tools (macOS)
```

#### Performance Requirements
- **Memory**: Maximum 64MB RAM usage
- **Speed**: Sub-second parsing untuk file <100MB
- **Compression**: >70% ratio untuk text files
- **Throughput**: >500MB/s pada modern hardware

#### Security Requirements
- **Encryption**: AES-256-GCM mandatory
- **Hashing**: SHA-256 untuk integrity
- **Random**: Cryptographically secure RNG
- **Memory**: Secure memory clearing

#### Compatibility Requirements
- **C Standard**: C11 compliant
- **Endianness**: Big/Little endian support
- **Architecture**: 32-bit/64-bit support
- **Thread Safety**: Full thread safety

Arsitektur ini memungkinkan implementasi real .asu file extension yang production-ready dengan native performance dan cross-platform compatibility.