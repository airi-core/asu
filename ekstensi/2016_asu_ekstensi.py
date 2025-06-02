# unified_architecture_definition_v2_complete.py

UNIFIED_PROJECT_ARCHITECTURE = {
    # ==================================================================================
    # ROOT CONFIGURATION FILES & PROJECT SETUP
    # ==================================================================================
    "README.md": {
        "scope": "Root Configuration",
        "status": "Defined",
        "description": "Dokumen utama yang menjelaskan proyek, tujuan, arsitektur tingkat tinggi, cara setup, menjalankan, dan berkontribusi.",
        "production_proven": "Praktik standar untuk semua proyek perangkat lunak.",
        "requirements": [
            "Gambaran umum proyek.",
            "Struktur direktori.",
            "Prasyarat instalasi.",
            "Instruksi build dan deployment.",
            "Cara menjalankan tes.",
            "Panduan kontribusi.",
            "Informasi lisensi."
        ],
        "dependencies": [],
        "implementation": {"format": "Markdown"},
        "optimization": {"clarity": "Mudah dipahami oleh anggota tim baru dan stakeholder."},
        "compaction_strategy": "Ringkas namun informatif.",
        "nist_alignment_notes": "Dokumentasi yang baik mendukung transparansi dan reproduktifitas, aspek penting bagi NIST."
    },
    "requirements.txt": {
        "scope": "Root Configuration",
        "status": "Defined",
        "description": "Manajemen dependensi Python dengan version pinning untuk reproducible builds. Struktur: library==version # comment.",
        "production_proven": "Poetry/pip-tools pattern (Netflix, Spotify).",
        "requirements": [
            "Exact version specification (==) untuk production dependencies.",
            "Compatible release (~=) untuk development tools.",
            "Integrasi vulnerability scanning (misalnya, safety/bandit).",
            "Dukungan multi-environment (dev/staging/prod).",
            "Pengecekan kepatuhan lisensi.",
            # Semua dependensi dari 'asu_ekstensi_untuk_nist_20150114.py' akan dikonsolidasikan di sini.
            # Contoh: "pyiceberg==0.4.1", "pyarrow>=12.0.1", "numpy<2.0", "lxml>=5.1.0",
            # "liboqs-python>=0.8.0", "intel-ipp-crypto>=2021.10.0",
            # "aws-encryption-sdk==2.3.1", "boto3>=1.28.45", "cryptography>=41.0.7",
            # "fastavro>=1.8.2", "requests-oauthlib>=1.3.1", "protobuf>=4.25.3",
            # "wine>=8.0", "winetricks>=20230212", "dxvk>=2.3", "vkd3d-proton>=2.10", "mangohud>=0.6.9.1",
            # "s3transfer>=0.8.0", "minio>=7.1.16",
            # "pygit2>=1.12.2", "zstandard>=0.22.0", "blake3>=0.4.1",
            # "duckdb>=0.10.0",
            # "fastapi>=0.109.0", "python-magic>=0.4.27",
            # "polars>=0.20.3",
            # "pyjwt>=2.8.0", "python-jose>=3.3.0",
            # "redis>=5.0.3", "geoip2>=4.8.0", "cloudflare>=2.11.0", # Tergantung implementasi spesifik
            # "prometheus-client>=0.20.0", "scikit-learn>=1.4.0",
            # "opentelemetry-sdk>=1.24.0", "opentelemetry-instrumentation>=0.45b0",
            # "fluent-logger>=0.10.0", "opensearch-py>=2.4.2", "presidio-analyzer>=2.2.36",
            # "aws-fis>=2.21.0", "dnspython>=2.4.2", # Untuk DR
            # "pycasbin>=1.26.1", # Untuk access control
            # "prowler>=4.10.0", "cloud-custodian>=0.9.36", # Untuk compliance
            # "chaostoolkit>=1.17.0", "kubernetes>=29.0.0", # Untuk chaos engineering
            # "argocd>=2.10.0", "kustomize>=5.4.0", "helm>=3.14.0", # Untuk GitOps
            # "chaosmesh>=2.6.1", "grafana-api>=1.7.0" # Untuk chaos testing
        ],
        "dependencies": [], # Akan diisi dengan daftar gabungan yang sebenarnya
        "implementation": {
            "header_format": "# Production Dependencies - DO NOT MODIFY WITHOUT APPROVAL\n# Development Dependencies",
            "version_policy": "Semantic versioning dengan security patch auto-update (jika aman). Pinning versi spesifik untuk produksi.",
            "update_frequency": "Monthly security scan, quarterly major updates (setelah pengujian)."
        },
        "optimization": {"build_cache": "pip cache dengan Docker layer optimization.", "install_time": "< 2 menit untuk full dependency install.", "size_limit": "< 100MB total package size (target)."},
        "compaction_strategy": "Minimal viable dependency set, konsolidasi shared dependencies.",
        "nist_alignment_notes": "Manajemen dependensi yang ketat mendukung keandalan, keamanan, dan reproduktifitas build, aspek penting bagi NIST."
    },
    "pyproject.toml": {
        "scope": "Root Configuration",
        "status": "Defined",
        "description": "PEP 518/621 compliant build configuration dengan metadata lengkap, tool configuration (linting, formatting, testing), dan build backend specification.",
        "production_proven": "Standard modern Python packaging (FastAPI, Pydantic, Django 4.2+).",
        "requirements": [
            "[build-system] dengan setuptools atau poetry backend.",
            "[project] metadata sesuai PEP 621 (name, version, description, authors, license, classifiers, urls, entry_points).",
            "[tool.*] configuration untuk black, isort, mypy, pytest, coverage, ruff, dll.",
            "Optional dependencies untuk feature flags atau fungsionalitas tambahan."
        ],
        "dependencies": [],
        "implementation": {
            "build_backend": "setuptools.build_meta", # Atau poetry.core.masonry.api
            "metadata_fields_example": ["name = \"unified_nist_project\"", "version = \"0.1.0\""],
            "tool_configs_example": ["[tool.black]", "line-length = 88"],
        },
        "optimization": {"build_time": "< 30 detik untuk wheel generation.", "metadata_validation": "Automated dengan pre-commit hooks.", "dependency_resolution": "< 10 detik untuk lock file generation (jika pakai Poetry/PDM)."},
        "compaction_strategy": "Single source of truth untuk project metadata, consolidated tool configuration.",
        "nist_alignment_notes": "Packaging standar dan konfigurasi build yang modern mendukung reproducibility, maintenance, dan kualitas kode, selaras dengan praktik rekayasa perangkat lunak yang baik yang dihargai NIST."
    },
    "Dockerfile": {
        "scope": "Root Configuration",
        "status": "Defined",
        "description": "Multi-stage containerization dengan security hardening, non-root user, dan penggunaan base image yang minimal (distroless/alpine) untuk mengurangi attack surface.",
        "production_proven": "Google distroless, Netflix Titus containerization patterns.",
        "requirements": [
            "Multi-stage build (misalnya, 'builder' stage untuk kompilasi/instalasi dependensi, 'runtime' stage untuk aplikasi).",
            "Penggunaan non-root user dengan permissions minimal dalam runtime stage.",
            "Integrasi security scanning (misalnya, trivy, snyk) dalam pipeline CI/CD.",
            "Konfigurasi health check endpoint (HEALTHCHECK instruction).",
            "Proper signal handling untuk graceful shutdown aplikasi dalam container (misalnya, menangani SIGTERM, SIGINT)."
        ],
        "dependencies": ["requirements.txt", "pyproject.toml", "src/"], # Tergantung apa yang di-copy ke image
        "implementation": {
            "base_image_builder": "python:3.11-slim-bullseye AS builder",
            "base_image_runtime": "python:3.11-slim-bullseye", # Atau gcr.io/distroless/python3-debian11
            "security_user_setup": "RUN groupadd -r appuser && useradd --no-log-init -r -g appuser appuser \nUSER appuser",
            "layer_organization": "Optimalkan urutan layer untuk caching (OS deps, Python deps, App code).",
            "health_check_example": "HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 CMD curl -f http://localhost:8000/api/health || exit 1"
        },
        "optimization": {"image_size": "< 150MB final image (target, bisa lebih kecil dengan distroless).", "build_time": "< 5 menit dengan cache hits.", "security_scan": "Zero critical/high vulnerabilities (target)."},
        "compaction_strategy": "Minimal system packages, shared base layers, .dockerignore optimization, multi-stage builds.",
        "nist_alignment_notes": "Containerization yang aman dan minimalis mendukung deployment yang aman, efisien, dan portabel, penting untuk sistem kritikal dan selaras dengan praktik DevSecOps."
    },
    "fly.toml": { # Atau konfigurasi deployment platform lain (Kubernetes YAML, dll.)
        "scope": "Root Configuration / Deployment",
        "status": "Defined",
        "description": "Konfigurasi deployment untuk platform Fly.io, mencakup definisi aplikasi, region, auto-scaling, health checks, environment variables, dan volume.",
        "production_proven": "Fly.io production deployment pattern.",
        "requirements": [
            "Konfigurasi multi-region deployment untuk high availability dan low latency.",
            "Aturan auto-scaling berdasarkan metrik (CPU/memory thresholds, request queue).",
            "Definisi health check endpoint yang akurat dengan timeout dan interval yang sesuai.",
            "Manajemen environment variable yang aman (menggunakan secrets untuk data sensitif).",
            "Konfigurasi volume mounting untuk persistent data jika diperlukan oleh aplikasi."
        ],
        "dependencies": ["Dockerfile"], # Image yang akan di-deploy
        "implementation": {
            "app_name_format": "unified-nist-project-{env}",
            "target_regions": "['sin', 'nrt', 'iad'] (contoh untuk global availability).",
            "scaling_rules": "min=1, max=10 (contoh), concurrency atau CPU/memory based.",
            "health_checks_config": "HTTP /api/health, interval=30s, timeout=10s, grace_period=60s.",
            "env_vars_source": "Fly.io secrets management."
        },
        "optimization": {"cold_start_target": "< 2 detik untuk instance startup.", "auto_scale_response": "Scale up/down dalam < 1 menit under load/idle.", "health_recovery_action": "Auto-restart unhealthy instances dalam < 60 detik."},
        "compaction_strategy": "Minimal resource allocation per instance (sesuai kebutuhan), efficient health check intervals, penggunaan region yang optimal.",
        "nist_alignment_notes": "Deployment yang terotomatisasi, dapat diskalakan, dan tangguh mendukung ketersediaan layanan yang tinggi, aspek penting untuk sistem yang diandalkan."
    },

    # ==================================================================================
    # .github/workflows/main_ci_cd.yml
    # ==================================================================================
    ".github/workflows/main_ci_cd.yml": {
        "scope": "DevOps - CI/CD",
        "status": "Defined",
        "description": "Pipeline CI/CD menggunakan GitHub Actions untuk otomatisasi build, test, security scan, dan deployment.",
        "production_proven": "GitHub Actions untuk CI/CD di berbagai skala proyek.",
        "requirements": [
            "Trigger pada push ke main/develop dan pada pull request.",
            "Jobs untuk linting dan formatting (misalnya, black, ruff, isort, mypy).",
            "Jobs untuk unit testing dan integration testing (pytest).",
            "Jobs untuk security scanning (dependensi: safety/trivy; kode: bandit/snyk code).",
            "Jobs untuk building Docker image.",
            "Jobs untuk pushing Docker image ke registry (misalnya, GHCR, Docker Hub).",
            "Jobs untuk deployment ke environment staging dan production (dengan approval manual untuk production).",
            "Notifikasi status build/deployment."
        ],
        "dependencies": ["Dockerfile", "requirements.txt", "pyproject.toml", "tests/"],
        "implementation": {
            "trigger_events": "on: [push, pull_request]",
            "job_matrix_strategy": "Untuk testing di berbagai versi Python (jika perlu).",
            "caching_mechanisms": "Cache dependensi Python, Docker layers.",
            "secret_management": "Menggunakan GitHub Secrets untuk API keys, token registry.",
            "deployment_targets": "Fly.io, Kubernetes, dll. (sesuai fly.toml atau konfigurasi lain)."
        },
        "optimization": {"pipeline_duration": "Target < 10 menit untuk build dan test lengkap.", "feedback_loop": "Cepat untuk PR checks."},
        "compaction_strategy": "Reusable workflows, parallel jobs, efficient caching.",
        "nist_alignment_notes": "CI/CD yang terotomatisasi dan aman mendukung Secure Software Development Framework (SSDF) NIST SP 800-218, memastikan kualitas dan keamanan kode secara berkelanjutan."
    },

    # ==================================================================================
    # API LAYER
    # ==================================================================================
    "api/__init__.py": {
        "scope": "API Layer",
        "status": "Defined",
        "description": "File inisialisasi untuk package 'api'.",
        "production_proven": "Standard Python package structure.",
        "requirements": ["Kosong atau berisi impor level package jika diperlukan."],
        "dependencies": [], "implementation": {}, "optimization": {}, "compaction_strategy": {},
        "nist_alignment_notes": "Struktur kode yang baik mendukung maintainability."
    },
    "api/app.py": {
        "scope": "API Layer",
        "status": "Defined",
        "description": "Aplikasi utama FastAPI yang menginisialisasi semua rute, middleware, event handlers, dan konfigurasi aplikasi.",
        "production_proven": "FastAPI (digunakan oleh Netflix, Uber) untuk API berperforma tinggi.",
        "requirements": [
            "Inisialisasi FastAPI app instance.",
            "Registrasi semua routers dari subdirektori 'routes'.",
            "Pemasangan middleware (CORS, auth, logging, error handling, rate limiting, protection).",
            "Konfigurasi event handlers (startup, shutdown) untuk tasks seperti koneksi DB, cleanup.",
            "Integrasi dokumentasi OpenAPI 3.0 otomatis.",
            "Konfigurasi global aplikasi (misalnya, dari environment variables)."
        ],
        "dependencies": ["fastapi", "uvicorn", "api/routes/", "api/middleware/", "src/"], # Bergantung pada layanan yang dipanggil
        "implementation": {
            "async_framework": "FastAPI dengan server ASGI seperti Uvicorn atau Hypercorn.",
            "middleware_stack_order": "Urutan middleware yang logis (misalnya, error handling paling luar, logging, CORS, auth, rate limiting).",
            "documentation_config": "Konfigurasi judul, versi, deskripsi untuk OpenAPI.",
            "startup_events_example": ["Inisialisasi koneksi database pool", "Memuat model ML (jika ada)."],
            "shutdown_events_example": ["Menutup koneksi database pool", "Melakukan graceful shutdown services."]
        },
        "optimization": {"request_latency_target": "< 50ms p95 untuk API calls umum.", "throughput_target": "> 10,000 requests/second (tergantung hardware dan kompleksitas).", "memory_usage_target": "< 100MB base + overhead per request minimal.", "startup_time_target": "< 5 detik."},
        "compaction_strategy": "Efficient middleware ordering, minimal request overhead, optimized serialization/deserialization (misalnya, Pydantic).",
        "nist_alignment_notes": "API yang terstruktur, aman, dan berperforma tinggi adalah komponen kunci dari sistem modern yang andal, sejalan dengan fokus NIST pada keamanan aplikasi."
    },
    "api/routes/__init__.py": {
        "scope": "API Layer - Routes",
        "status": "Defined",
        "description": "File inisialisasi untuk package 'routes'.",
        "production_proven": "Standard Python package structure.",
        "requirements": ["Kosong atau berisi impor level package jika diperlukan."],
        "dependencies": [], "implementation": {}, "optimization": {}, "compaction_strategy": {},
        "nist_alignment_notes": "Struktur kode yang baik."
    },
    "api/routes/files.py": {
        "scope": "API Layer - Routes",
        "status": "Defined",
        "description": "Endpoint API RESTful untuk manajemen file, mengintegrasikan fungsionalitas dari 'asu_ekstensi' (presigned URLs, S3-like operations) dan 'research_architecture' (streaming, resumable transfers, metadata).",
        "production_proven": "AWS S3 API, Google Cloud Storage API patterns.",
        "requirements": [
            # Dari asu_ekstensi (api/endpoints/files.py)
            "Pembuatan dan validasi Presigned URL (v4) untuk upload/download aman dengan expiry (15-60 menit).",
            "Enforcement header Content-SHA256.",
            "CORS policy yang ketat (strict-origin-when-cross-origin).",
            "Verifikasi checksum upload (SHA-256).",
            "Manajemen multi-part upload.",
            "Dukungan download byte-range.",
            "Integrasi virus scanning (asinkron untuk tidak memblokir).",
            "Download throttling.",
            # Dari research_architecture (api/routes/files.py)
            "Streaming file upload/download dengan progress tracking.",
            "Resumable transfer dengan dukungan range request.",
            "Ekstraksi metadata otomatis (dengan extractor berbasis plugin).",
            "Kontrol akses fine-grained dengan pewarisan permission (integrasi dengan `src/security/access_controller.py`).",
            "Mekanisme karantina untuk file yang terdeteksi virus."
        ],
        "dependencies": ["fastapi", "pydantic", "src/core/file_format_manager.py", "src/storage/object_storage_adapter.py", "src/security/access_controller.py", "src/security/crypto_services.py", "boto3", "python-magic"], # Contoh
        "implementation": {
            "streaming_handler": "Async generators FastAPI untuk transfer memory-efficient.",
            "presigned_url_logic": "Menggunakan SDK cloud provider (misalnya, Boto3 untuk S3) atau implementasi kustom jika multi-cloud.",
            "resumable_protocol": "Implementasi standar seperti TUS atau custom berbasis HTTP range requests.",
            "metadata_extraction_engine": "Sistem plugin untuk mengekstrak metadata dari berbagai tipe file (misalnya, EXIF untuk gambar, ID3 untuk audio).",
            "access_control_integration": "Memanggil `access_controller.py` untuk validasi permission sebelum operasi file."
        },
        "optimization": {"upload_speed_target": "> 100MB/s.", "download_speed_target": "> 200MB/s.", "metadata_extraction_time": "< 500ms untuk format umum.", "permission_check_latency": "< 10ms."},
        "compaction_strategy": "Efficient transfer protocols, minimal metadata overhead, caching permission jika relevan.",
        "mitigation_strategy": { # Dari mitigasi_kekurangan_modul.md untuk api/endpoints/files.py
            "identified_shortcomings": ["Potensi single cloud provider dependency untuk presigned URLs.", "Limit upload 5TB mungkin kurang.", "Latensi integrasi virus scanning.", "Kompleksitas CORS policy."],
            "working_prototype_requirements": ["Abstraksi layer multi-cloud presigned URL.", "Implementasi resumable upload dengan chunked transfers.", "Virus scanning asinkron dengan callback.", "Auto-generasi CORS policy berdasarkan pola request."],
            "security_audit_requirements": ["Assessment keamanan verifikasi signature presigned URL.", "Pengujian bypass validasi upload.", "Review policy keamanan cross-origin request.", "Verifikasi efektivitas validasi tipe file."],
            "performance_benchmarking_methodology": "Throughput upload/download, dampak latensi virus scanning, performa concurrent upload, efisiensi byte-range download.",
            "reference_implementation_verification": ["Analisis arsitektur upload Dropbox/Google Drive/Box/WeTransfer."]
        },
        "nist_alignment_notes": "Manajemen file yang aman dengan kontrol akses ketat dan verifikasi integritas penting untuk banyak aplikasi NIST. Dukungan standar industri untuk transfer data besar juga relevan."
    },
    "api/routes/queries.py": {
        "scope": "API Layer - Routes",
        "status": "Defined",
        "description": "Endpoint API untuk mengeksekusi query terhadap data yang tersimpan, mengintegrasikan query engine dari 'asu_ekstensi' (Athena-like) dan 'research_architecture' (jika ada fungsionalitas query spesifik).",
        "production_proven": "AWS Athena Engine v3, Presto/Trino patterns.",
        "requirements": [
            # Dari asu_ekstensi (api/endpoints/queries.py)
            "Predicate pushdown ke storage layer untuk optimasi.",
            "Vectorized execution untuk query berperforma tinggi.",
            "Paginasi hasil query dengan continuation tokens.",
            "Manajemen query timeout (configurable, target awal max 30 menit, bisa adaptif).",
            "Isolasi sumber daya per tenant/user untuk query.",
            "Middleware caching hasil query.",
            "Dukungan User Defined Table Functions (UDTF).",
            "Cost-based optimizer (CBO).",
            "Kompresi hasil query.",
            "Prioritisasi antrian query."
        ],
        "dependencies": ["fastapi", "pydantic", "src/processing_engine/analyzer.py", "src/storage/query_cache_manager.py", "duckdb", "polars", "pyarrow"], # Contoh
        "implementation": {
            "execution_engine_integration": "Integrasi dengan DuckDB, Polars, atau engine lain yang dipilih. Kemungkinan routing ke engine berbeda berdasarkan tipe query.",
            "query_optimization_logic": "Implementasi CBO dengan statistik kolumnar atau integrasi dengan fitur optimizer dari engine yang digunakan.",
            "resource_isolation_method": "Menggunakan cgroups dan namespace Linux jika query dieksekusi dalam proses terpisah, atau mekanisme internal engine.",
            "caching_strategy": "Integrasi dengan `query_cache_manager.py`, dengan kunci cache berdasarkan query dan parameter, serta TTL yang dapat dikonfigurasi."
        },
        "optimization": {"query_execution_time_target": "Sesuai kompleksitas, target optimal untuk query umum.", "resource_utilization_efficiency": "Tinggi.", "concurrent_query_handling": "Skalabilitas tinggi."},
        "compaction_strategy": "Optimasi query plan, efisiensi eksekusi engine, caching yang efektif.",
        "mitigation_strategy": { # Dari mitigasi_kekurangan_modul.md untuk api/endpoints/queries.py
            "identified_shortcomings": ["Timeout query 30 menit mungkin kurang.", "Dependensi pada satu query engine.", "Kompleksitas implementasi isolasi resource.", "Efektivitas CBO bervariasi."],
            "working_prototype_requirements": ["Routing query multi-engine (DuckDB + Polars + Arrow).", "Timeout query adaptif berdasarkan estimasi kompleksitas.", "Isolasi resource dengan cgroups/namespace.", "Optimasi query plan dengan estimasi biaya berbasis ML."],
            "security_audit_requirements": ["Verifikasi mekanisme pencegahan SQL injection.", "Assessment keamanan isolasi resource query.", "Validasi keamanan paginasi hasil.", "Review implikasi keamanan UDTF."],
            "performance_benchmarking_methodology": "Perbandingan waktu eksekusi query antar engine, efisiensi penggunaan resource, performa query konkuren, optimasi penggunaan memori.",
            "reference_implementation_verification": ["Arsitektur Presto/Trino, Apache Drill, ClickHouse, BigQuery."]
        },
        "nist_alignment_notes": "Kemampuan query data yang aman, efisien, dan dapat diskalakan penting untuk analisis data dan pengambilan keputusan, area yang relevan bagi NIST."
    },
    "api/middleware/__init__.py": {
        "scope": "API Layer - Middleware",
        "status": "Defined",
        "description": "File inisialisasi untuk package 'middleware'.",
        "production_proven": "Standard Python package structure.",
        "requirements": ["Kosong atau berisi impor level package jika diperlukan."],
        "dependencies": [], "implementation": {}, "optimization": {}, "compaction_strategy": {},
        "nist_alignment_notes": "Struktur kode yang baik."
    },
    "api/middleware/auth.py": {
        "scope": "API Layer - Middleware",
        "status": "Defined",
        "description": "Middleware untuk autentikasi dan otorisasi Zero-Trust dengan Attribute-Based Access Control (ABAC), mengintegrasikan OIDC dan JWT.",
        "production_proven": "OpenTDF (Virtru), Keycloak, Auth0 patterns.",
        "requirements": [
            # Dari asu_ekstensi (api/middleware/auth.py)
            "Integrasi OpenID Connect (OIDC) dengan provider identitas (IdP).",
            "Verifikasi JSON Web Token (JWT) (signature, expiry, audience, issuer).",
            "Implementasi Attribute-Based Access Control (ABAC) untuk otorisasi fine-grained.",
            "Penggunaan short-lived credentials (misalnya, access token dengan expiry max 1 jam, refresh token).",
            "Policy Decision Point (PDP) terdistribusi atau terpusat dengan caching.",
            "Dukungan step-up authentication untuk operasi sensitif.",
            "Versioning kebijakan otorisasi.",
            "Session binding ke atribut device atau sesi (jika relevan).",
            "Mekanisme Credential Revocation List (CRL) atau Online Certificate Status Protocol (OCSP) jika menggunakan sertifikat, atau mekanisme pencabutan token.",
            "Sandbox untuk pengujian kebijakan otorisasi."
        ],
        "dependencies": ["fastapi", "pyjwt[crypto]", "python-jose[cryptography]", "requests-oauthlib"], # Contoh
        "implementation": {
            "oidc_flow": "Authorization Code Flow atau Client Credentials Flow (tergantung use case).",
            "jwt_verification_steps": "Validasi signature (dengan public key IdP), `exp`, `nbf`, `aud`, `iss` claims.",
            "abac_engine_integration": "Integrasi dengan `src/security/access_controller.py` atau library ABAC seperti PyCasbin.",
            "token_refresh_logic": "Implementasi refresh token flow yang aman.",
            "policy_evaluation_cache": "Cache lokal (misalnya, LRU cache) untuk hasil evaluasi kebijakan PDP."
        },
        "optimization": {"auth_latency_target": "< 20ms untuk verifikasi token (dengan caching).", "policy_evaluation_throughput": "Tinggi."},
        "compaction_strategy": "Caching token/public key, evaluasi kebijakan yang efisien.",
        "mitigation_strategy": { # Dari mitigasi_kekurangan_modul.md untuk api/middleware/auth.py
            "identified_shortcomings": ["Single point of failure OIDC provider.", "Overhead komputasi verifikasi JWT.", "Tantangan konsistensi PDP terdistribusi.", "Kompleksitas UX step-up authentication."],
            "working_prototype_requirements": ["Implementasi failover multi-OIDC provider.", "Caching verifikasi JWT dengan pengecekan pencabutan.", "PDP terdistribusi dengan jaminan eventual consistency.", "Alur autentikasi adaptif berdasarkan penilaian risiko."],
            "security_audit_requirements": ["Verifikasi kepatuhan keamanan implementasi OIDC.", "Assessment keamanan validasi signature JWT.", "Review keamanan engine evaluasi kebijakan.", "Pengujian efektivitas keamanan session binding."],
            "performance_benchmarking_methodology": "Latensi autentikasi, throughput evaluasi kebijakan, overhead manajemen sesi, dampak performa alur step-up authentication.",
            "reference_implementation_verification": ["Arsitektur Auth0/Okta/Ping Identity/Azure AD B2C."]
        },
        "nist_alignment_notes": "Autentikasi dan otorisasi yang kuat berdasarkan Zero Trust Architecture (NIST SP 800-207) adalah fundamental untuk keamanan sistem, sangat selaras dengan prioritas NIST."
    },
    "api/middleware/protection.py": {
        "scope": "API Layer - Middleware",
        "status": "Defined",
        "description": "Middleware untuk mitigasi DDoS, proteksi bot, dan keamanan API tingkat lanjut.",
        "production_proven": "Cloudflare Advanced Protection, AWS WAF, Akamai Kona Site Defender patterns.",
        "requirements": [
            # Dari asu_ekstensi (api/middleware/protection.py)
            "Rate limiting berbasis IP, user, atau token (misalnya, 5k RPM normal, dengan burst allowance).",
            "JIT (Just-In-Time) challenge tanpa CAPTCHA yang mengganggu (misalnya, computational challenge, proof-of-work).",
            "Pemblokiran berdasarkan reputasi IP (integrasi dengan threat intelligence feeds).",
            "Behavioral fingerprinting untuk deteksi anomali dan bot.",
            "Normalisasi path API untuk mencegah bypass.",
            "TLS fingerprinting untuk identifikasi klien.",
            "Kemampuan Geo-fencing (blokir/izinkan berdasarkan lokasi geografis).",
            "Deteksi anomali berbasis AI/ML (jika memungkinkan dan terbukti).",
            "Enforcement penandatanganan request (request signing) untuk API tertentu.",
            "Integrasi skor bot dari layanan eksternal."
        ],
        "dependencies": ["fastapi", "redis"], # Redis untuk rate limiting, dll.
        "implementation": {
            "rate_limiting_storage": "Redis (atau in-memory untuk skala kecil) dengan algoritma seperti token bucket atau leaky bucket.",
            "ip_reputation_source": "Integrasi dengan daftar blokir publik atau komersial.",
            "behavioral_analysis_engine": "Logika kustom atau integrasi dengan layanan pihak ketiga.",
            "jit_challenge_type": "Computational challenge (misalnya, hashcash) yang diselesaikan oleh klien."
        },
        "optimization": {"protection_overhead_target": "Minimal (< 5ms) untuk request yang sah.", "false_positive_rate_target": "Sangat rendah."},
        "compaction_strategy": "Aturan proteksi yang efisien, caching reputasi IP.",
        "mitigation_strategy": { # Dari mitigasi_kekurangan_modul.md untuk api/middleware/protection.py
            "identified_shortcomings": ["Threshold rate limiting normal mungkin terlalu restriktif.", "False positive rate deteksi anomali AI.", "Kompleksitas implementasi geofencing.", "Akurasi deteksi bot terhadap serangan canggih."],
            "working_prototype_requirements": ["Rate limiting dinamis berdasarkan pola perilaku pengguna.", "Deteksi bot multi-layer dengan analisis perilaku.", "Geofencing dengan manajemen pengecualian whitelist.", "Implementasi JIT challenge tanpa friksi pengguna."],
            "security_audit_requirements": ["Pengujian efektivitas mitigasi DDoS.", "Assessment akurasi deteksi bot dengan berbagai vektor serangan.", "Verifikasi upaya bypass rate limiting.", "Review implikasi privasi TLS fingerprinting."],
            "performance_benchmarking_methodology": "Pengukuran false positive rate traffic sah, analisis waktu respons mitigasi DDoS, kuantifikasi tingkat akurasi deteksi bot, penilaian dampak latensi routing geografis.",
            "reference_implementation_verification": ["Pola implementasi Akamai/Cloudflare/AWS WAF/Fastly."]
        },
        "nist_alignment_notes": "Perlindungan proaktif terhadap serangan siber dan penyalahgunaan API mendukung ketahanan sistem dan keamanan informasi, sejalan dengan NIST Cybersecurity Framework."
    },

    # ==================================================================================
    # SRC - CORE MODULES (Lanjutan)
    # ==================================================================================
    "src/core/__init__.py": {
        "scope": "Core Library",
        "status": "Defined",
        "description": "File inisialisasi untuk package 'core' dalam 'src'. Mengimpor atau mendefinisikan antarmuka publik dari modul-modul inti.",
        "production_proven": "Standard Python package structure.",
        "requirements": [
            "Mendefinisikan `__all__` untuk mengekspos API publik dari package `core`.",
            "Inisialisasi konfigurasi level package jika ada.",
            "Potensi registrasi plugin atau ekstensi untuk modul inti."
        ],
        "dependencies": ["src/core/file_format_manager.py", "src/core/metadata_registry.py"],
        "implementation": {
            "public_api_exports_example": "__all__ = ['FileFormatManager', 'MetadataRegistry']"
        },
        "optimization": {"import_time": "Minimal untuk menghindari pelambatan startup aplikasi."},
        "compaction_strategy": "Hanya ekspor antarmuka yang benar-benar publik dan stabil.",
        "nist_alignment_notes": "Struktur kode yang modular dan terdefinisi dengan baik mendukung maintainability dan kualitas perangkat lunak, aspek yang dihargai dalam rekayasa sistem."
    },
    # file_format_manager.py sudah didefinisikan di atas
    "src/core/metadata_registry.py": { # Berdasarkan core/metadata.py dari asu_ekstensi
        "scope": "Core Library - Metadata Management",
        "status": "Defined",
        "description": "Schema registry terpusat untuk mengelola skema data, mendukung evolusi skema yang aman, validasi, dan interoperabilitas metadata (termasuk Dublin Core).",
        "production_proven": "Confluent Schema Registry, Apache Avro/Protobuf schema management.",
        "requirements": [
            "Penyimpanan dan versioning skema data (misalnya, JSON Schema, Avro, Protobuf).",
            "Dukungan evolusi skema dengan aturan kompatibilitas (backward, forward, full).",
            "Validasi data terhadap skema terdaftar.",
            "Fingerprint skema (misalnya, SHA-256) untuk identifikasi unik.",
            "Dukungan penuh untuk set metadata Dublin Core dengan pemetaan otomatis dari format internal (misalnya, JSON).",
            "API HTTP (RESTful) untuk manajemen skema dengan autentikasi OAuth2.",
            "Replikasi metadata multi-AZ untuk ketersediaan tinggi.",
            "Point-in-time recovery untuk metadata (target 14 hari).",
            "Dukungan referensi skema untuk tipe data bersarang atau terstruktur kompleks.",
            "Visualisasi perbedaan (diff) antar versi skema."
        ],
        "dependencies": ["fastavro>=1.8.2", "requests-oauthlib>=1.3.1", "protobuf>=4.25.3", "jsonschema"], # Contoh
        "implementation": {
            "storage_backend_options": "Database (misalnya, PostgreSQL), atau sistem file terdistribusi dengan locking.",
            "schema_evolution_rules_engine": "Implementasi logika untuk memeriksa kompatibilitas (misalnya, tambah field opsional, hapus field deprecated).",
            "dublin_core_mapper": "Logika untuk memetakan field dari skema internal ke term Dublin Core dan sebaliknya.",
            "api_endpoints_schema_management": "CRUD operations untuk skema dan versi skema.",
            "replication_strategy_details": "Sinkronisasi multi-AZ untuk metadata kritis."
        },
        "optimization": {"schema_validation_latency": "< 1ms per record untuk skema umum.", "replication_lag_target": "Minimal (< 1 detik).", "concurrent_schema_registrations": "Tinggi."},
        "compaction_strategy": "Caching skema yang sering diakses, representasi skema yang efisien.",
        "mitigation_strategy": { # Dari mitigasi_kekurangan_modul.md untuk core/metadata.py
            "identified_shortcomings": ["Potensi single point of failure schema registry.", "Kompleksitas otomatisasi mapping Dublin Core.", "Limitasi point-in-time recovery 14 hari.", "Masalah kompatibilitas evolusi skema Protobuf."],
            "working_prototype_requirements": ["Schema registry multi-AZ dengan replikasi sinkron.", "Mapping metadata Dublin Core dengan validasi otomatis.", "Pengujian evolusi skema untuk perubahan breaking/non-breaking.", "Validasi JSON Schema dengan error reporting komprehensif."],
            "security_audit_requirements": ["Review keamanan implementasi OAuth2.", "Verifikasi kontrol akses schema registry.", "Assessment keamanan replikasi metadata.", "Validasi integritas point-in-time recovery."],
            "performance_benchmarking_methodology": "Latensi validasi skema, monitoring lag replikasi, throughput registrasi skema konkuren, performa visualisasi diff skema.",
            "reference_implementation_verification": ["Deployment multi-datacenter schema registry LinkedIn/Netflix/Airbnb/Twitter."]
        },
        "nist_alignment_notes": "Manajemen metadata dan skema yang robust mendukung tata kelola data, interoperabilitas, dan kualitas data, yang merupakan fokus penting NIST."
    },

    # ==================================================================================
    # SRC - PROCESSING ENGINE (dari research_architecture)
    # ==================================================================================
    "src/processing_engine/__init__.py": {
        "scope": "Processing Engine",
        "status": "Defined",
        "description": "File inisialisasi untuk package 'processing_engine'.",
        "production_proven": "Standard Python package structure.",
        "requirements": ["Kosong atau impor publik."],
        "dependencies": [], "implementation": {}, "optimization": {}, "compaction_strategy": {},
        "nist_alignment_notes": "Struktur kode yang baik."
    },
    "src/processing_engine/analyzer.py": {
        "scope": "Processing Engine - Analytics",
        "status": "Defined",
        "description": "Statistical analysis engine dengan distributed computing, machine learning integration, dan real-time analytics untuk research data insights.",
        "production_proven": "Apache Spark, Dask distributed analytics patterns.",
        "requirements": [
            "Distributed computing dengan task parallelization.",
            "Integrasi pustaka analisis statistik (NumPy, SciPy, Pandas).",
            "Machine learning pipeline dengan model versioning dan MLOps practices.",
            "Real-time streaming analytics dengan event processing (misalnya, integrasi dengan Kafka/Flink).",
            "Result caching dengan intelligent invalidation."
        ],
        "dependencies": ["numpy", "scipy", "pandas", "scikit-learn", "pytorch", "redis"], # Contoh
        "implementation": {
            "compute_engine_type": "Task graph execution dengan work stealing scheduler (mirip Dask atau custom).",
            "ml_integration_details": "Integrasi dengan scikit-learn, PyTorch/TensorFlow melalui model registry (misalnya, MLflow).",
            "streaming_processor_config": "Event-driven processing dengan back-pressure handling dan windowing functions.",
            "result_cache_backend": "Redis-backed result caching dengan TTL management dan invalidasi berbasis event."
        },
        "optimization": {"processing_speed_target": "> 1GB/s untuk vectorized operations.", "parallel_efficiency_target": "> 80% CPU utilization pada multi-core.", "memory_usage_target": "< 50% available RAM untuk in-memory.", "cache_hit_rate_target": "> 70%."},
        "compaction_strategy": "Vectorized operations, efficient memory layout, optimized computation graphs, lazy evaluation.",
        "mitigation_strategy": { # Ditambahkan placeholder, perlu diisi jika ada kekurangan spesifik
            "identified_shortcomings": ["Skalabilitas model ML tertentu.", "Latensi pada streaming data volume sangat tinggi.", "Kompleksitas manajemen state dalam distributed computing."],
            "working_prototype_requirements": ["Benchmark skalabilitas model ML.", "Tes latensi streaming dengan data sintetis.", "Prototipe manajemen state terdistribusi."],
            "security_audit_requirements": ["Audit keamanan data dalam pipeline ML.", "Verifikasi isolasi data antar tenant jika multi-tenant.", "Keamanan endpoint inferensi model."],
            "performance_benchmarking_methodology": "Benchmarking end-to-end pipeline analitik, termasuk data ingestion, preprocessing, training (jika ada), dan inferensi.",
            "reference_implementation_verification": ["Studi kasus penggunaan Spark/Dask/Flink di industri serupa untuk analitik skala besar."]
        },
        "nist_alignment_notes": "Kemampuan analisis data yang kuat, terukur, dan dapat direproduksi mendukung pengambilan keputusan berbasis data dan penelitian ilmiah, yang relevan untuk banyak aplikasi yang diminati NIST."
    },
    "src/processing_engine/workflow.py": {
        "scope": "Processing Engine - Orchestration",
        "status": "Defined",
        "description": "Advanced workflow orchestration dengan DAG scheduling, fault tolerance, resource management, dan research pipeline automation.",
        "production_proven": "Apache Airflow, Prefect, Kubeflow Pipelines workflow patterns.",
        "requirements": [
            "Definisi workflow berbasis DAG (Directed Acyclic Graph) dengan resolusi dependensi.",
            "Fault tolerance dengan mekanisme retry otomatis (configurable backoff).",
            "Manajemen sumber daya dengan prioritisasi antrian dan alokasi dinamis.",
            "Persistensi state workflow dengan histori eksekusi dan audit trail.",
            "Kemampuan generasi workflow dinamis berdasarkan data atau parameter.",
            "Integrasi dengan `analyzer.py` dan modul lain dalam sistem."
        ],
        "dependencies": ["src/utils/state_machine.py"], # Contoh dependensi internal
        "implementation": {
            "scheduler_type": "Priority queue scheduler dengan alokasi sadar sumber daya.",
            "fault_tolerance_pattern": "Circuit breaker pattern dengan exponential backoff dan dead-letter queues.",
            "state_management_backend": "Database (misalnya, PostgreSQL) atau sistem file terdistribusi untuk state workflow.",
            "resource_allocation_model": "Resource pools dengan algoritma fair scheduling atau prioritas."
        },
        "optimization": {"workflow_latency_initiation": "< 100ms.", "task_throughput_target": "> 1000 tasks/minute (lightweight).", "fault_recovery_time": "< 30s untuk retry task.", "resource_efficiency_target": "> 90% utilitas untuk batch processing."},
        "compaction_strategy": "Efficient task scheduling, minimal state overhead, optimized dependency resolution, parallel task execution.",
        "mitigation_strategy": { # Ditambahkan placeholder
            "identified_shortcomings": ["Kompleksitas debugging workflow DAG.", "Potensi deadlock dalam dependensi kompleks.", "Manajemen state untuk workflow yang berjalan sangat lama."],
            "working_prototype_requirements": ["UI visualisasi DAG dan status eksekusi.", "Deteksi deadlock statis/dinamis.", "Strategi checkpointing untuk workflow panjang."],
            "security_audit_requirements": ["Kontrol akses ke definisi dan eksekusi workflow.", "Keamanan variabel/parameter yang dilewatkan antar task.", "Auditabilitas eksekusi workflow."],
            "performance_benchmarking_methodology": "Benchmarking throughput scheduler, latensi task, dan overhead orkestrasi.",
            "reference_implementation_verification": ["Studi kasus penggunaan Airflow/Prefect/Kubeflow di lingkungan produksi."]
        },
        "nist_alignment_notes": "Orkestrasi workflow yang andal dan dapat diaudit mendukung proses ilmiah dan operasional yang kompleks dan reproduktif, penting untuk penelitian dan kepatuhan."
    },

    # ==================================================================================
    # SRC - SECURITY MODULES (Lanjutan)
    # ==================================================================================
    "src/security/__init__.py": {
        "scope": "Security Library",
        "status": "Defined",
        "description": "File inisialisasi untuk package 'security'.",
        "production_proven": "Standard Python package structure.",
        "requirements": ["Kosong atau impor publik."],
        "dependencies": [], "implementation": {}, "optimization": {}, "compaction_strategy": {},
        "nist_alignment_notes": "Struktur kode yang baik."
    },
    "src/security/access_controller.py": { # Berdasarkan security/access_control.py dari asu_ekstensi
        "scope": "Security Library - Access Control",
        "status": "Defined",
        "description": "Policy engine berbasis atribut (ABAC) untuk kontrol akses fine-grained, mendukung prinsip least privilege dan just-in-time (JIT) elevation.",
        "production_proven": "AWS IAM ABAC Model, Google Cloud IAM, Open Policy Agent (OPA).",
        "requirements": [
            "Implementasi prinsip policy minimization (least privilege).",
            "Mekanisme Just-in-Time (JIT) elevation untuk hak akses sementara dengan approval workflow.",
            "Audit log yang immutable untuk semua keputusan akses dan perubahan kebijakan (target retensi 7 tahun, WORM storage).",
            "Policy simulation engine untuk menguji dampak perubahan kebijakan sebelum diterapkan.",
            "Prosedur 'break-glass' untuk akses darurat dengan audit ketat.",
            "Dukungan resource-based policies selain identity-based policies.",
            "Mode 'dry-run' untuk penerapan kebijakan.",
            "Dukungan batasan temporal (misalnya, akses hanya selama jam kerja).",
            "Mekanisme delegasi permission dengan rantai kepercayaan yang jelas."
        ],
        "dependencies": ["boto3", "pycasbin>=1.26.1", "python-jose>=3.3.0", "cryptography"], # Contoh, sesuaikan dengan implementasi
        "implementation": {
            "policy_language": "Menggunakan bahasa kebijakan standar (misalnya, Rego untuk OPA) atau DSL kustom.",
            "policy_decision_point_architecture": "PDP terdistribusi dengan caching lokal atau PDP terpusat.",
            "audit_log_storage_config": "Penyimpanan WORM (Write-Once-Read-Many) dengan enkripsi dan cryptographic sealing (integrasi HSM jika memungkinkan).",
            "jit_approval_workflow_integration": "Integrasi dengan sistem ticketing atau notifikasi untuk approval JIT."
        },
        "optimization": {"policy_evaluation_latency_target": "< 10ms (dengan caching).", "jit_approval_time_target": "Sesuai SLA."},
        "compaction_strategy": "Caching hasil evaluasi kebijakan, representasi kebijakan yang efisien.",
        "mitigation_strategy": { # Dari mitigasi_kekurangan_modul.md untuk security/access_control.py
            "identified_shortcomings": ["Kompleksitas kebijakan dapat menyebabkan akses tidak sengaja.", "Latensi approval JIT elevation.", "Biaya penyimpanan audit log 7 tahun.", "Akurasi simulasi kebijakan untuk skenario kompleks."],
            "working_prototype_requirements": ["Analisis dampak kebijakan dengan pengujian simulasi.", "Approval JIT otomatis untuk skenario risiko rendah.", "Penyimpanan audit yang dioptimalkan biaya dengan kompresi.", "Framework pengujian kebijakan dengan skenario komprehensif."],
            "security_audit_requirements": ["Verifikasi efektivitas kebijakan kontrol akses.", "Assessment keamanan JIT elevation.", "Validasi integritas kriptografis audit log.", "Pengujian akurasi simulasi kebijakan."],
            "performance_benchmarking_methodology": "Latensi evaluasi kebijakan, waktu approval JIT, performa query audit log, tingkat akurasi verifikasi simulasi kebijakan.",
            "reference_implementation_verification": ["Implementasi Google Cloud IAM ABAC, Microsoft Azure RBAC, Okta, AWS IAM."]
        },
        "nist_alignment_notes": "Kontrol akses yang kuat dan berbasis atribut adalah pilar keamanan informasi (NIST SP 800-53, SP 800-162 ABAC). Auditabilitas dan JIT access mendukung Zero Trust."
    },
    "src/security/compliance_checker.py": { # Berdasarkan security/compliance.py dari asu_ekstensi
        "scope": "Security Library - Compliance",
        "status": "Defined",
        "description": "Modul untuk pemeriksaan kepatuhan otomatis terhadap berbagai standar (misalnya, GDPR, HIPAA) dan kebijakan internal, dengan auto-remediation dan koleksi bukti audit.",
        "production_proven": "AWS Config Managed Rules, Prowler, Cloud Custodian.",
        "requirements": [
            "Dukungan untuk compliance packs/profiles (misalnya, GDPR, HIPAA, PCI DSS, NIST CSF).",
            "Kemampuan auto-remediation yang terjadwal atau event-driven (dengan approval/dry-run mode).",
            "Koleksi bukti (evidence) otomatis untuk keperluan audit.",
            "Notifikasi dan alerting untuk pelanggaran kebijakan.",
            "Framework Compliance as Code (CaC) untuk mendefinisikan aturan kepatuhan.",
            "Rantai hashing bukti (evidence hashing chain) untuk integritas.",
            "Templating laporan regulatori.",
            "Deteksi penyimpangan (drift) kepatuhan.",
            "Pelacakan perubahan regulatori (jika memungkinkan, integrasi dengan feed).",
            "Enforcement kedaulatan data (data sovereignty).",
            "Enforcement legal hold untuk data dan metadata."
        ],
        "dependencies": ["prowler>=4.10.0", "cloud-custodian>=0.9.36"], # Contoh, atau library kustom
        "implementation": {
            "rule_engine": "Mesin aturan yang dapat diperluas untuk mendefinisikan checks kepatuhan.",
            "remediation_workflows": "Workflow untuk remediasi otomatis dengan langkah-langkah approval.",
            "evidence_storage_config": "Penyimpanan bukti yang aman dan WORM, dengan Merkle tree dan timestamp HSM untuk integritas.",
            "legal_hold_mechanism": "Aktivasi via API dengan audit trail lengkap dan penyimpanan WORM untuk data yang di-hold."
        },
        "optimization": {"compliance_scan_performance": "Cepat dan efisien.", "auto_remediation_success_rate": "Tinggi dengan minimal false positives."},
        "compaction_strategy": "Aturan kepatuhan yang efisien, koleksi bukti yang terarah.",
        "mitigation_strategy": { # Dari mitigasi_kekurangan_modul.md untuk security/compliance.py
            "identified_shortcomings": ["Cakupan compliance pack mungkin kurang untuk kebutuhan spesifik industri.", "Auto-remediation bisa mengganggu sistem produksi.", "Verifikasi kelengkapan koleksi bukti.", "Limitasi otomatisasi pelacakan perubahan regulatori."],
            "working_prototype_requirements": ["Framework kepatuhan kustom dengan aturan yang dapat diperluas.", "Auto-remediation bertahap dengan penilaian dampak.", "Verifikasi integritas bukti berbasis blockchain.", "Integrasi update regulatori otomatis."],
            "security_audit_requirements": ["Analisis celah cakupan kepatuhan.", "Verifikasi mekanisme keamanan auto-remediation.", "Assessment kelengkapan koleksi bukti.", "Pengujian efektivitas enforcement legal hold."],
            "performance_benchmarking_methodology": "Pengukuran performa scan kepatuhan, analisis tingkat keberhasilan auto-remediation, verifikasi efisiensi koleksi bukti, pengukuran waktu pembuatan laporan regulatori.",
            "reference_implementation_verification": ["Framework otomatisasi PCI DSS/HIPAA/SOC 2/GDPR."]
        },
        "nist_alignment_notes": "Otomatisasi kepatuhan dan audit mendukung tata kelola risiko dan pemenuhan regulasi, area penting bagi NIST (misalnya, RMF - NIST SP 800-37)."
    },
    "src/security/crypto_services.py": { # Gabungan core/crypto.py (asu_ekstensi) & security/encryption.py (research)
        "scope": "Security Library - Cryptographic Services",
        "status": "Defined",
        "description": "Layanan kriptografi enterprise-grade untuk enkripsi end-to-end data at-rest dan in-transit, dengan manajemen kunci yang kuat, rotasi kunci, dan dukungan HSM.",
        "production_proven": "AWS KMS Multi-Region Keys, HashiCorp Vault, AWS Encryption SDK.",
        "requirements": [
            # Dari asu_ekstensi (core/crypto.py)
            "Envelope encryption dengan data key caching dan algoritma kuat (AES-256-GCM).",
            "Rotasi kunci otomatis zero-downtime (target setiap 90 hari, configurable) dengan grace period (target 7 hari).",
            "Integrasi CloudTrail (atau logging audit setara) untuk semua operasi kunci.",
            "Kepatuhan FIPS 140-2 Level 3 (melalui integrasi HSM atau modul kripto tersertifikasi).",
            "Penyimpanan kunci master berbasis HSM (Hardware Security Module) atau layanan KMS setara.",
            "Audit penggunaan kunci (key usage auditing).",
            "Mekanisme pencabutan kunci darurat (emergency key revocation).",
            "Manajemen alias kunci untuk berbagai environment (dev/staging/prod).",
            "Client-side encryption hooks.",
            "Otomatisasi pembuatan kebijakan KMS (jika menggunakan AWS KMS).",
            "Enkripsi level field (field-level encryption) menggunakan envelope pattern dengan unique IV per field.",
            # Dari research_architecture (src/security/encryption.py)
            "AES-256-GCM dengan authenticated encryption (AEAD).", # Sudah tercakup
            "Derivasi kunci menggunakan PBKDF2 (atau standar kuat lainnya).",
            "Struktur kunci hirarkis (master keys, data encryption keys - DEKs).",
            "Zero-knowledge encryption (jika memungkinkan dan relevan untuk use case tertentu, perlu analisis mendalam).",
            "Integrasi HSM melalui antarmuka standar (misalnya, PKCS#11)."
        ],
        "dependencies": ["aws-encryption-sdk==2.3.1", "boto3>=1.28.45", "cryptography>=41.0.7", "src/utils/key_manager.py"], # Contoh
        "implementation": {
            "encryption_algorithm_suite": "AES-256-GCM sebagai standar utama.",
            "key_derivation_function": "PBKDF2-HMAC-SHA256 atau Argon2.",
            "key_rotation_scheduler_logic": "Jadwal otomatis dengan fallback mechanism (kunci lama valid selama grace period).",
            "hsm_interface_details": "Menggunakan PKCS#11 atau SDK spesifik vendor HSM/KMS.",
            "field_encryption_implementation": "Strategi enkripsi per field dengan metadata yang tidak terenkripsi untuk query (jika perlu, dengan hati-hati terhadap kebocoran informasi)."
        },
        "optimization": {"encryption_speed_target": "> 500MB/s untuk bulk data.", "key_rotation_time_target": "< 100ms (zero-downtime).", "hsm_latency_target": "< 10ms untuk operasi HSM.", "memory_security_practices": "Secure memory clearing untuk material kunci sensitif."},
        "compaction_strategy": "Pemilihan cipher yang efisien, penyimpanan material kunci minimal, skema padding yang optimal.",
        "mitigation_strategy": { # Dari mitigasi_kekurangan_modul.md untuk core/crypto.py
            "identified_shortcomings": ["Dependensi pada satu cloud provider (vendor lock-in) untuk KMS.", "Grace period 7 hari mungkin kurang untuk skenario darurat.", "Kompleksitas verifikasi kepatuhan FIPS 140-2 Level 3.", "Overhead performa enkripsi level field."],
            "working_prototype_requirements": ["Layer abstraksi KMS multi-cloud (AWS + Azure + GCP).", "Pengujian pencabutan kunci darurat dengan propagasi <1 menit.", "Implementasi envelope encryption dengan rotasi kunci otomatis.", "Benchmarking enkripsi level field untuk berbagai tipe data."],
            "security_audit_requirements": ["Verifikasi integrasi HSM FIPS 140-2 Level 3.", "Assessment kelengkapan audit trail rotasi kunci.", "Pengujian pencabutan darurat dengan skenario kompromi simulasi.", "Review keamanan integrasi CloudTrail."],
            "performance_benchmarking_methodology": "Throughput enkripsi/dekripsi, pengukuran downtime rotasi kunci (target: nol), analisis latensi replikasi multi-region, kuantifikasi overhead envelope encryption.",
            "reference_implementation_verification": ["Arsitektur manajemen kunci multi-region Netflix/Uber/Square/Salesforce."]
        },
        "nist_alignment_notes": "Enkripsi data yang kuat dan manajemen kunci yang aman adalah fundamental bagi keamanan informasi (NIST SP 800-57, FIPS 140-2/3). Melindungi data sensitif sesuai dengan standar NIST."
    },
    # pqc_services.py sudah didefinisikan di atas

    # ==================================================================================
    # SRC - STORAGE MODULES
    # ==================================================================================
    "src/storage/__init__.py": {
        "scope": "Storage Library",
        "status": "Defined",
        "description": "File inisialisasi untuk package 'storage'.",
        "production_proven": "Standard Python package structure.",
        "requirements": ["Kosong atau impor publik."],
        "dependencies": [], "implementation": {}, "optimization": {}, "compaction_strategy": {},
        "nist_alignment_notes": "Struktur kode yang baik."
    },
    "src/storage/backup_system.py": { # Dari research_architecture
        "scope": "Storage Library - Backup",
        "status": "Defined",
        "description": "Enterprise backup system dengan incremental backups, point-in-time recovery (PITR), cross-region replication, dan automated disaster recovery.",
        "production_proven": "Bacula, Amanda backup patterns, AWS Backup, Azure Backup.",
        "requirements": [
            "Incremental backup dengan deduplikasi level blok atau file.",
            "Point-in-time recovery dengan konsistensi snapshot (aplikasi dan data).",
            "Replikasi backup cross-region untuk disaster recovery.",
            "Penjadwalan backup otomatis dengan kebijakan retensi yang dapat dikonfigurasi.",
            "Verifikasi backup otomatis dan pengujian integritas (misalnya, trial restore).",
            "Enkripsi data backup (at-rest dan in-transit).",
            "Pelaporan status backup dan alerting."
        ],
        "dependencies": ["src/utils/checksum.py", "src/utils/compression.py"], # Contoh
        "implementation": {
            "backup_engine_choice": "Menggunakan rsync-based incremental dengan optimasi hardlink, atau integrasi dengan layanan backup cloud (AWS Backup, Azure Backup) atau tools seperti Restic/BorgBackup.",
            "snapshot_mechanism": "Copy-on-write snapshots (jika didukung filesystem/storage) atau mekanisme quiescing aplikasi.",
            "replication_protocol_details": "Replikasi multi-master dengan resolusi konflik atau replikasi async ke region DR.",
            "verification_process": "Automated restore testing ke environment terisolasi dengan validasi checksum."
        },
        "optimization": {"backup_speed_target_incremental": "> 100MB/s.", "deduplication_ratio_target": "> 80% untuk dataset serupa.", "recovery_time_objective_rto": "< 1 jam (tergantung volume, target awal).", "recovery_point_objective_rpo": "< 15 menit (target awal).", "bandwidth_usage_backup": "Minimal, dapat dijadwalkan saat off-peak."},
        "compaction_strategy": "Algoritma deduplikasi efisien, penyimpanan backup terkompresi, ukuran chunk optimal.",
        "mitigation_strategy": { # Placeholder, perlu diisi jika ada kekurangan spesifik
            "identified_shortcomings": ["Kompleksitas memastikan konsistensi aplikasi saat snapshot.", "Biaya penyimpanan backup jangka panjang.", "Waktu restore untuk dataset sangat besar."],
            "working_prototype_requirements": ["Prototipe snapshot konsisten aplikasi.", "Analisis biaya vs retensi.", "Pengujian restore skala besar."],
            "security_audit_requirements": ["Keamanan kunci enkripsi backup.", "Kontrol akses ke data backup.", "Integritas proses restore."],
            "performance_benchmarking_methodology": "Benchmarking RTO/RPO aktual, efisiensi deduplikasi, throughput backup/restore.",
            "reference_implementation_verification": ["Studi kasus penggunaan AWS Backup, Azure Backup, Veeam, Commvault."]
        },
        "nist_alignment_notes": "Backup dan recovery yang andal adalah bagian penting dari perencanaan kontinjensi (NIST SP 800-34), memastikan ketersediaan dan integritas data."
    },
    "src/storage/local_fs_adapter.py": { # Dari research_architecture
        "scope": "Storage Library - Local Filesystem",
        "status": "Defined",
        "description": "High-performance local filesystem storage adapter dengan atomic operations, ACID-like compliance untuk operasi tertentu, dan filesystem optimization.",
        "production_proven": "RocksDB, LevelDB local storage patterns, SQLite.",
        "requirements": [
            "ACID-like transactions untuk operasi data konsisten (jika diimplementasikan di atas FS, mungkin memerlukan WAL).",
            "Atomic file operations (rename sebagai commit).",
            "Optimasi filesystem (misalnya, block alignment, buffering yang bijak, O_DIRECT jika perlu).",
            "Pengindeksan metadata dengan struktur efisien (misalnya, B-tree via SQLite atau custom).",
            "Penanganan akses konkuren dengan mekanisme file locking (advisory locking).",
            "Dukungan untuk file besar (>4GB)."
        ],
        "dependencies": ["src/utils/indexer.py", "sqlite3"], # Contoh
        "implementation": {
            "transaction_log_wal": "Implementasi Write-Ahead Logging sederhana untuk atomicity operasi multi-step.",
            "file_operations_flags": "Penggunaan flag `O_DIRECT` secara selektif untuk bypass OS cache pada skenario tertentu (misalnya, database-like workloads).",
            "indexing_system_details": "Penggunaan SQLite untuk metadata index dengan kemampuan full-text search jika diperlukan.",
            "locking_mechanism_choice": "Advisory file locking (`fcntl.flock`) dengan timeout handling untuk mencegah deadlock."
        },
        "optimization": {"write_throughput_target_seq": "> 200MB/s.", "read_throughput_target_cache": "> 500MB/s.", "index_lookup_latency": "< 1ms.", "concurrent_ops_support": "100+ concurrent readers, 10+ writers (target)."},
        "compaction_strategy": "Deduplikasi level blok (jika diimplementasikan), penyimpanan metadata efisien, ukuran buffer optimal.",
        "mitigation_strategy": { # Placeholder
            "identified_shortcomings": ["Skalabilitas terbatas pada satu node.", "Kompleksitas implementasi ACID di atas filesystem generik.", "Manajemen locking untuk konkurensi tinggi."],
            "working_prototype_requirements": ["Prototipe WAL.", "Benchmark konkurensi.", "Pengujian integritas data di bawah kegagalan."],
            "security_audit_requirements": ["Keamanan file permission.", "Potensi race condition dalam locking."],
            "performance_benchmarking_methodology": "Benchmarking I/O throughput, latensi, dan skalabilitas konkuren.",
            "reference_implementation_verification": ["Desain internal SQLite, LMDB."]
        },
        "nist_alignment_notes": "Penyimpanan lokal yang efisien dan andal bisa menjadi dasar untuk komponen sistem lain atau untuk caching, mendukung performa sistem secara keseluruhan."
    },
    "src/storage/object_storage_adapter.py": { # Gabungan storage/s3.py dari asu_ekstensi
        "scope": "Storage Library - Object Storage",
        "status": "Defined",
        "description": "Adapter untuk interaksi dengan layanan object storage (seperti AWS S3, Google Cloud Storage, Azure Blob Storage), mendukung intelligent tiering, enkripsi, versioning, dan WORM compliance.",
        "production_proven": "Spotify S3 Cost Optimizer, AWS S3, GCS, Azure Blob SDKs.",
        "requirements": [
            "Abstraksi untuk operasi CRUD objek (Create, Read, Update, Delete, List).",
            "Dukungan untuk multi-cloud (AWS S3, GCS, Azure Blob) melalui konfigurasi atau adapter pattern.",
            "Implementasi atau integrasi dengan intelligent tiering (misalnya, S3 Intelligent-Tiering) untuk optimasi biaya.",
            "Enkripsi server-side (SSE-S3, SSE-KMS, SSE-C) dan client-side encryption.",
            "Dukungan Object Lock untuk WORM (Write-Once-Read-Many) compliance.",
            "Enforcement versioning bucket/container.",
            "Replikasi cross-region (RTO <1h target awal, bisa lebih baik).",
            "Pembuatan Presigned URLs dengan kebijakan kustom (integrasi dengan `api/routes/files.py`).",
            "Integrasi dengan storage analytics (misalnya, S3 Storage Lens) untuk analisis biaya dan penggunaan.",
            "Dukungan S3 batch operations (atau setara) untuk operasi massal.",
            "Replikasi cross-account yang terenkripsi."
        ],
        "dependencies": ["boto3>=1.28.45", "s3transfer>=0.8.0", "minio>=7.1.16", "google-cloud-storage", "azure-storage-blob"], # Tergantung provider yang didukung
        "implementation": {
            "multi_cloud_abstraction_layer": "Desain adapter pattern untuk menyembunyikan detail SDK spesifik provider.",
            "lifecycle_policy_config_example_s3": "[{'access_days': 30, 'class': 'INTELLIGENT_TIERING'}, {'access_days': 90, 'class': 'GLACIER_DEEP_ARCHIVE'}] (dapat dikonfigurasi).",
            "default_encryption_setting": "AES-256 server-side encryption (SSE-S3 atau SSE-KMS).",
            "presigned_url_generation_logic": "Menggunakan SDK provider untuk generate URL dengan parameter keamanan."
        },
        "optimization": {"cost_optimization_target": "Pengurangan biaya signifikan melalui tiering.", "access_latency_tier_aware": "Sesuai dengan SLA tier penyimpanan.", "rto_rpo_replication": "RTO <1h, RPO <15 menit (target awal)."},
        "compaction_strategy": "Penggunaan tier penyimpanan yang tepat, kompresi objek sebelum upload (jika relevan).",
        "mitigation_strategy": { # Dari mitigasi_kekurangan_modul.md untuk storage/s3.py
            "identified_shortcomings": ["Intelligent tiering bisa agresif untuk data yang sering diakses.", "RTO replikasi cross-region <1jam mungkin kurang.", "Dependensi pada satu cloud provider (jika tidak ada abstraksi).", "Analisis storage lens bisa menghasilkan optimasi biaya palsu."],
            "working_prototype_requirements": ["Abstraksi penyimpanan multi-cloud (S3 + GCS + Azure Blob).", "Algoritma optimasi biaya dengan prediksi ML.", "Analisis pola akses dengan rekomendasi tiering otomatis.", "Implementasi replikasi cross-cloud dengan resolusi konflik."],
            "security_audit_requirements": ["Verifikasi kepatuhan WORM Object Lock.", "Assessment keamanan replikasi cross-account.", "Validasi kebijakan keamanan presigned URL.", "Verifikasi enkripsi end-to-end penyimpanan."],
            "performance_benchmarking_methodology": "Pengukuran efektivitas optimasi biaya (12 bulan), perbandingan latensi akses antar tier, pengukuran RTO/RPO replikasi, pengujian throughput untuk berbagai ukuran objek.",
            "reference_implementation_verification": ["Arsitektur penyimpanan multi-cloud Dropbox/Pinterest/Airbnb/Netflix."]
        },
        "nist_alignment_notes": "Penyimpanan objek yang aman, tahan lama, dan hemat biaya penting untuk data skala besar. Kepatuhan WORM dan enkripsi mendukung persyaratan keamanan dan regulasi NIST."
    },
    "src/storage/query_cache_manager.py": { # Dari storage/query_cache.py dari asu_ekstensi
        "scope": "Storage Library - Query Cache",
        "status": "Defined",
        "description": "Manajer cache untuk materialized view dan hasil query, bertujuan untuk mempercepat query yang sering dieksekusi.",
        "production_proven": "Firebolt Materialized Views, Presto/Trino caching, Redis.",
        "requirements": [
            "Penyimpanan hasil query atau materialized view dalam format kolumnar (misalnya, Parquet, Arrow).",
            "Mekanisme auto-refresh cache ketika data sumber berubah (misalnya, berbasis CDC, trigger, atau terjadwal).",
            "Kebijakan invalidasi cache (misalnya, TTL berdasarkan waktu akses terakhir - target 30 hari, atau berbasis event).",
            "Invalidasi cache yang atomik untuk menjaga konsistensi.",
            "Kemampuan query rewrite otomatis untuk menggunakan hasil cache jika memungkinkan.",
            "Persistensi cache setelah restart sistem (jika relevan).",
            "Kompresi data cache (misalnya, Zstd, Snappy).",
            "Strategi cache warming (misalnya, pre-populating cache untuk query umum).",
            "Auto-tuning ukuran cache berdasarkan penggunaan memori/disk.",
            "Dukungan untuk caching hasil query parsial."
        ],
        "dependencies": ["duckdb>=0.10.0", "pyarrow>=12.0.1", "zstandard>=0.22.0", "redis"], # Contoh
        "implementation": {
            "cache_storage_backend": "Penyimpanan lokal (misalnya, DuckDB file), atau distributed cache (Redis, Memcached), atau object storage untuk cache besar.",
            "refresh_trigger_mechanism": "Integrasi dengan sistem CDC (Change Data Capture) atau polling terjadwal ke data sumber.",
            "invalidation_logic": "Berdasarkan TTL, atau pesan invalidasi dari sistem update data.",
            "query_rewrite_integration": "Hook ke dalam `api/routes/queries.py` atau query planner."
        },
        "optimization": {"cache_hit_ratio_target": "> 70% untuk query yang dapat di-cache.", "query_response_time_improvement": "Signifikan (target >5x lebih cepat).", "memory_usage_efficiency": "Optimal."},
        "compaction_strategy": "Format penyimpanan cache yang efisien, kompresi, kebijakan eviction yang cerdas (LRU, LFU).",
        "mitigation_strategy": { # Dari mitigasi_kekurangan_modul.md untuk storage/query_cache.py
            "identified_shortcomings": ["Mekanisme auto-refresh bisa menyebabkan cache thrashing.", "TTL 30 hari berdasarkan akses terakhir mungkin terlalu agresif.", "Kompleksitas implementasi invalidasi cache atomik.", "Limitasi DuckDB single-node untuk workload terdistribusi (jika DuckDB digunakan sebagai backend cache terdistribusi)."],
            "working_prototype_requirements": ["Caching query terdistribusi dengan jaminan konsistensi.", "Strategi cache warming dengan prefetching prediktif.", "Algoritma auto-tuning untuk optimasi ukuran cache.", "Caching hasil parsial dengan kemampuan query rewrite."],
            "security_audit_requirements": ["Assessment keamanan isolasi cache untuk lingkungan multi-tenant.", "Review implikasi keamanan query rewrite.", "Verifikasi keamanan persistensi cache.", "Validasi kontrol akses hasil query."],
            "performance_benchmarking_methodology": "Pengukuran optimasi cache hit ratio, kuantifikasi peningkatan waktu respons query, analisis efisiensi penggunaan memori, pengukuran latensi invalidasi cache.",
            "reference_implementation_verification": ["Arsitektur caching query terdistribusi Pinterest/Uber/LinkedIn/Twitter."]
        },
        "nist_alignment_notes": "Caching query meningkatkan performa akses data, yang penting untuk sistem analitik dan interaktif. Konsistensi cache adalah aspek kunci."
    },
    "src/storage/versioning_system.py": { # Dari storage/versioning.py dari asu_ekstensi
        "scope": "Storage Library - Data Versioning",
        "status": "Defined",
        "description": "Sistem versioning data immutable, mendukung content-addressable storage, deduplikasi, dan verifikasi kriptografis.",
        "production_proven": "Git LFS, Microsoft Azure Repos (untuk biner), Databricks Delta Lake, Apache Hudi/Iceberg (untuk tabel data).",
        "requirements": [
            "Penyimpanan content-addressable (CAS) dimana ID objek adalah hash dari kontennya.",
            "Deduplikasi data (level blok atau file).",
            "Verifikasi integritas kriptografis (misalnya, SHA-256, BLAKE3) untuk setiap versi data dan metadata.",
            "Snapshot data yang atomik.",
            "Garbage collection (GC) otomatis untuk versi lama dengan kebijakan retensi yang dapat dikonfigurasi (target awal 365 hari, kecuali legal hold).",
            "Dukungan untuk branching dan merging histori versi (jika relevan untuk use case).",
            "Deduplikasi cross-repository/dataset (jika memungkinkan).",
            "Content-defined chunking untuk deduplikasi yang lebih efektif.",
            "API untuk garbage collection versi.",
            "Delta encoding untuk menyimpan perubahan kecil secara efisien."
        ],
        "dependencies": ["pygit2>=1.12.2", "zstandard>=0.22.0", "blake3>=0.4.1"], # Contoh, atau library CAS kustom
        "implementation": {
            "cas_backend": "Bisa berupa object storage atau filesystem lokal yang dioptimalkan untuk CAS.",
            "deduplication_algorithm_choice": "Rabin fingerprinting dengan sliding window untuk chunking, atau fixed-size chunking dengan hash.",
            "metadata_versioning": "Menggunakan Merkle DAG untuk merepresentasikan histori versi.",
            "gc_policy_engine": "Logika untuk menentukan versi mana yang aman untuk dihapus berdasarkan retensi dan legal hold."
        },
        "optimization": {"deduplication_effectiveness_target": "Pengurangan storage signifikan.", "version_retrieval_latency": "Cepat.", "storage_efficiency_comparison": "Lebih baik dari versioning tradisional."},
        "compaction_strategy": "Algoritma deduplikasi dan chunking yang efisien, delta encoding.",
        "mitigation_strategy": { # Dari mitigasi_kekurangan_modul.md untuk storage/versioning.py
            "identified_shortcomings": ["Biaya penyimpanan Git LFS untuk file biner besar.", "Efektivitas deduplikasi untuk file yang sangat terkompresi.", "Kompleksitas deduplikasi cross-repo.", "Kebijakan GC 365 hari mungkin kurang untuk kebutuhan kepatuhan."],
            "working_prototype_requirements": ["Implementasi CAS dengan Merkle DAG.", "Pengujian algoritma binary diff untuk berbagai tipe file.", "Deduplikasi cross-repository dengan isolasi namespace.", "GC otomatis dengan kebijakan retensi yang dapat dikonfigurasi."],
            "security_audit_requirements": ["Assessment integritas verifikasi kriptografis.", "Review keamanan kontrol akses versi.", "Verifikasi kepatuhan implementasi legal hold.", "Analisis implikasi keamanan delta encoding."],
            "performance_benchmarking_methodology": "Pengukuran efektivitas deduplikasi, analisis latensi pengambilan versi, perbandingan efisiensi penyimpanan, pengujian performa akses konkuren.",
            "reference_implementation_verification": ["Analisis skala implementasi Git LFS GitHub/GitLab/Bitbucket/Azure Repos."]
        },
        "nist_alignment_notes": "Versioning data yang immutable dengan integritas terjamin mendukung auditabilitas, reproduktifitas, dan tata kelola data, penting untuk penelitian dan kepatuhan (NIST SP 800-188 Data Integrity)."
    },

    # ==================================================================================
    # SRC - UTILS (dari research_architecture, beberapa mungkin tumpang tindih dengan kebutuhan modul lain)
    # ==================================================================================
    "src/utils/__init__.py": {"scope": "Utilities", "status": "Defined", "description": "Package utilitas umum.", "requirements": [], "dependencies": [], "implementation": {}, "optimization": {}, "compaction_strategy": {}, "nist_alignment_notes": "Kode utilitas yang baik mendukung kualitas kode secara keseluruhan."},
    "src/utils/checksum.py": {"scope": "Utilities", "status": "Defined", "description": "Utilitas untuk kalkulasi dan verifikasi checksum (misalnya, SHA-256, CRC32).", "requirements": ["Dukungan berbagai algoritma checksum.", "Streaming checksum calculation."], "dependencies": ["hashlib"], "implementation": {}, "optimization": {}, "compaction_strategy": {}, "nist_alignment_notes": "Verifikasi integritas data."},
    "src/utils/compression.py": {"scope": "Utilities", "status": "Defined", "description": "Utilitas untuk kompresi dan dekompresi data (gzip, lz4, zstd).", "requirements": ["Dukungan berbagai algoritma kompresi.", "Streaming compression/decompression."], "dependencies": ["gzip", "lz4", "zstandard"], "implementation": {}, "optimization": {}, "compaction_strategy": {}, "nist_alignment_notes": "Efisiensi penyimpanan dan transfer data."},
    "src/utils/indexer.py": {"scope": "Utilities", "status": "Defined", "description": "Utilitas untuk membuat dan mengelola indeks metadata (misalnya, untuk local_fs_adapter).", "requirements": ["Pembuatan indeks efisien.", "Query indeks cepat."], "dependencies": ["sqlite3"], "implementation": {}, "optimization": {}, "compaction_strategy": {}, "nist_alignment_notes": "Akses data cepat."},
    "src/utils/key_manager.py": {"scope": "Utilities", "status": "Defined", "description": "Utilitas untuk manajemen kunci kriptografi internal (jika tidak semua ditangani oleh KMS/HSM eksternal).", "requirements": ["Pembuatan kunci aman.", "Penyimpanan kunci aman (enkripsi).", "Rotasi kunci internal."], "dependencies": ["cryptography"], "implementation": {}, "optimization": {}, "compaction_strategy": {}, "nist_alignment_notes": "Manajemen kunci yang aman."},
    "src/utils/logger.py": { # Digunakan oleh metrics.py dari research_architecture
        "scope": "Utilities",
        "status": "Defined",
        "description": "Konfigurasi logging terpusat untuk aplikasi, mendukung structured logging (JSON), level log, dan output ke berbagai handler (console, file, Fluentd).",
        "production_proven": "Python logging module, structlog.",
        "requirements": [
            "Structured logging (misalnya, format JSON).",
            "Konfigurasi level log per modul atau global.",
            "Dukungan multiple handlers (console, file, network - Fluentd/Logstash).",
            "Penambahan konteks otomatis ke log (misalnya, request ID, user ID).",
            "Integrasi dengan `observability/logging_config.py`."
        ],
        "dependencies": ["logging", "python-json-logger"], # Contoh
        "implementation": {"logger_name": "unified_nist_project_logger"},
        "optimization": {"logging_overhead": "Minimal."},
        "compaction_strategy": "Konfigurasi logging yang efisien.",
        "nist_alignment_notes": "Logging yang baik mendukung audit, troubleshooting, dan pemantauan keamanan (NIST SP 800-92)."
    },
    "src/utils/state_machine.py": {"scope": "Utilities", "status": "Defined", "description": "Utilitas untuk implementasi state machine (misalnya, untuk workflow.py).", "requirements": ["Definisi state dan transisi.", "Event handling."], "dependencies": [], "implementation": {}, "optimization": {}, "compaction_strategy": {}, "nist_alignment_notes": "Manajemen state yang jelas."},

    # ==================================================================================
    # SRC - VIRTUALIZATION
    # ==================================================================================
    "src/virtualization/__init__.py": {
        "scope": "Virtualization",
        "status": "Defined",
        "description": "File inisialisasi untuk package 'virtualization'.",
        "production_proven": "Standard Python package structure.",
        "requirements": ["Kosong atau impor publik."],
        "dependencies": [], "implementation": {}, "optimization": {}, "compaction_strategy": {},
        "nist_alignment_notes": "Struktur kode yang baik."
    },
    "src/virtualization/wine_executor.py": { # Dari virtualization/wine_execution.py dari asu_ekstensi
        "scope": "Virtualization",
        "status": "Defined",
        "description": "Modul untuk menjalankan aplikasi Windows di Linux tanpa virtualisasi hardware penuh, menggunakan Wine dengan patch staging, DXVK, Vulkan, dan sandboxing.",
        "production_proven": "Steam Proton (kompatibilitas 75%), CodeWeavers CrossOver.",
        "requirements": [
            "Dukungan Wine 8.0+ dengan staging patches.",
            "DXVK untuk translasi DirectX ke Vulkan.",
            "Instalasi driver Vulkan yang sesuai.",
            "Manajemen paket font Windows (misalnya, via winetricks corefonts).",
            "Konfigurasi sistem audio (misalnya, PulseAudio dengan setting winetricks).",
            "Setup environment registry Wine.",
            "Manajemen DLL override (WINEDLLOVERRIDES).",
            "Isolasi prefix Wine per aplikasi (WINEPREFIX).",
            "Integrasi alat monitoring performa (misalnya, MangoHUD).",
            "Akses ke database kompatibilitas (misalnya, ProtonDB API).",
            "Sandboxing Wine prefix (misalnya, menggunakan bubblewrap) dan pembatasan sumber daya (cgroups)."
        ],
        "dependencies": ["wine>=8.0", "winetricks>=20230212", "dxvk>=2.3", "vkd3d-proton>=2.10", "mangohud>=0.6.9.1", "bubblewrap"], # bubblewrap sebagai contoh sandboxing
        "implementation": {
            "wine_version_management": "Menggunakan versi Wine yang stabil dan teruji.",
            "graphics_stack_config": "DXVK 2.3 + VKD3D-Proton 2.10.",
            "font_setup_script": "Otomatisasi instalasi font umum via winetricks.",
            "audio_system_integration": "Konfigurasi PulseAudio atau PipeWire.",
            "registry_setup_method": "Aplikasi file .reg kustom saat pembuatan prefix.",
            "dll_override_strategy": "Manajemen via variabel environment WINEDLLOVERRIDES atau konfigurasi Wine.",
            "prefix_isolation_mechanism": "Setiap aplikasi berjalan dalam WINEPREFIX terpisah.",
            "performance_monitoring_tool": "Integrasi MangoHUD untuk metrik Vulkan/OpenGL.",
            "safety_controls_details": "Sandboxing prefix Wine menggunakan bubblewrap dengan profil seccomp dan pembatasan cgroups untuk CPU/memori."
        },
        "optimization": {"compatibility_rate_target": ">85% untuk aplikasi target.", "performance_overhead_target": "Minimal dibandingkan native Windows.", "security_isolation": "Kuat."},
        "compaction_strategy": "Prefix Wine yang minimalis, shared Wine runtime jika aman.",
        "mitigation_strategy": { # Dari mitigasi_kekurangan_modul.md untuk virtualization/wine_execution.py
            "identified_shortcomings": ["Rate kompatibilitas 75% masih menyisakan 25% aplikasi bermasalah.", "Overhead performa translasi DirectX.", "Isolasi prefix Wine mungkin kurang untuk keamanan.", "Frekuensi testing mingguan mungkin kurang untuk aplikasi kritikal."],
            "working_prototype_requirements": ["Suite pengujian kompatibilitas otomatis dengan 1000+ sampel aplikasi.", "Perbandingan performa native vs Wine untuk aplikasi CPU-intensif.", "Pengujian isolasi sandbox menggunakan bubblewrap dan cgroups.", "Benchmarking performa DXVK/VKD3D untuk berbagai workload grafis."],
            "security_audit_requirements": ["Assessment keamanan isolasi prefix Wine.", "Review implikasi keamanan manipulasi registry.", "Analisis kerentanan keamanan DLL override.", "Pengujian penetrasi efektivitas sandboxing."],
            "performance_benchmarking_methodology": "Perbandingan performa Native Windows vs Wine, pengujian performa rendering grafis, analisis penggunaan memori, validasi efektivitas pembatasan sumber daya.",
            "reference_implementation_verification": ["Analisis database kompatibilitas Steam Proton, studi kasus CodeWeavers CrossOver, implementasi Bottles/PlayOnLinux."]
        },
        "nist_alignment_notes": "Menyediakan solusi interoperabilitas untuk aplikasi legacy, yang bisa penting untuk transisi sistem di lingkungan pemerintah atau enterprise. Fokus pada isolasi dan keamanan dalam virtualisasi ringan ini positif."
    },

    # ==================================================================================
    # OBSERVABILITY LAYER
    # ==================================================================================
    "observability/__init__.py": {"scope": "Observability", "status": "Defined", "description": "Package untuk modul observabilitas.", "requirements": [], "dependencies": [], "implementation": {}, "optimization": {}, "compaction_strategy": {}, "nist_alignment_notes": "Struktur kode."},
    "observability/health_checker.py": { # Gabungan dari research_architecture (monitoring/health_check.py) dan kebutuhan umum
        "scope": "Observability",
        "status": "Defined",
        "description": "Sistem health check komprehensif dengan pemeriksaan sistem mendalam, validasi dependensi, pengumpulan metrik performa, dan alerting otomatis.",
        "production_proven": "Kubernetes liveness/readiness probes, Netflix health check patterns (misalnya, Hystrix).",
        "requirements": [
            "Health checks multi-level (shallow: status aplikasi dasar; deep: konektivitas DB, layanan eksternal; dependency: status layanan pihak ketiga).",
            "Pengumpulan metrik performa kunci sebagai bagian dari health status (misalnya, latensi, error rate).",
            "Integrasi dengan mekanisme circuit breaker untuk validasi kesehatan dependensi.",
            "Alerting otomatis (ke Prometheus Alertmanager, PagerDuty, Slack, dll.) dengan kebijakan eskalasi.",
            "Dashboard health status real-time (integrasi dengan Grafana).",
            "Endpoint HTTP standar untuk health checks (misalnya, /health, /live, /ready)."
        ],
        "dependencies": ["fastapi", "prometheus_client", "requests"], # Contoh
        "implementation": {
            "health_levels_definition": "Shallow (<100ms, cek internal app), Deep (<1s, cek koneksi dasar DB/cache), Full (<5s, cek dependensi eksternal kritis).",
            "metrics_collection_integration": "Ekspos metrik Prometheus dari endpoint health check atau secara terpisah.",
            "dependency_check_logic": "Pemeriksaan periodik atau on-demand ke layanan eksternal dengan timeout dan retry.",
            "alerting_system_integration": "Webhook ke Alertmanager atau sistem notifikasi lain."
        },
        "optimization": {"check_latency_target_shallow": "< 50ms.", "metrics_collection_overhead": "< 1% CPU.", "alert_delivery_time_critical": "< 30s.", "dashboard_load_time": "< 2s."},
        "compaction_strategy": "Algoritma health check efisien, caching status dependensi (dengan TTL pendek), agregasi metrik yang bijak.",
        "mitigation_strategy": { # Placeholder, karena ini gabungan, perlu analisis kekurangan spesifik dari implementasi gabungan
            "identified_shortcomings": ["Potensi false positive/negative dari health checks.", "Overhead pemeriksaan dependensi eksternal yang sering."],
            "working_prototype_requirements": ["Health checks dengan logika threshold adaptif.", "Caching status dependensi dengan invalidasi cerdas."],
            "security_audit_requirements": ["Keamanan endpoint health check (jangan ekspos info sensitif)."],
            "performance_benchmarking_methodology": ["Benchmarking latensi dan overhead health check."],
            "reference_implementation_verification": ["Pola health check di sistem terdistribusi besar."]
        },
        "nist_alignment_notes": "Pemantauan kesehatan sistem proaktif mendukung ketersediaan dan keandalan, penting untuk layanan kritikal (NIST SP 800-137 Continuous Monitoring)."
    },
    "observability/logging_config.py": { # Dari asu_ekstensi (observability/logging.py)
        "scope": "Observability",
        "status": "Defined",
        "description": "Konfigurasi dan manajemen logging terstruktur dengan enrichment, PII redaction, dan integrasi dengan sistem logging terpusat.",
        "production_proven": "Fluentd + Elasticsearch (ELK/EFK Stack), OpenTelemetry Logging.",
        "requirements": [
            "Logging terstruktur (misalnya, format JSON) dengan skema log yang ketat.",
            "Redaksi PII (Personally Identifiable Information) otomatis dari log.",
            "Injeksi konteks trace (trace ID, span ID) ke dalam log untuk korelasi.",
            "Pengarsipan log ke cold storage (dengan kebijakan retensi).",
            "Versioning skema log untuk evolusi.",
            "Deteksi data sensitif (selain PII) dalam log.",
            "Kemampuan log replay untuk debugging (jika memungkinkan).",
            "Pemrosesan log real-time untuk alerting atau analisis cepat.",
            "Deteksi anomali dalam log.",
            "Sampling log adaptif untuk volume tinggi."
        ],
        "dependencies": ["fluent-logger>=0.10.0", "opensearch-py>=2.4.2", "presidio-analyzer>=2.2.36", "python-json-logger", "src/utils/logger.py"], # Contoh
        "implementation": {
            "log_shipper_integration": "Konfigurasi untuk mengirim log ke Fluentd, Logstash, atau langsung ke OpenSearch/Elasticsearch.",
            "pii_redaction_engine": "Menggunakan Presidio Analyzer atau library NLP lain untuk deteksi dan redaksi PII.",
            "log_retention_policy_config": "Hot storage (misalnya, 30 hari di OpenSearch), cold storage (misalnya, 7 tahun di S3 Glacier).",
            "trace_context_injector": "Integrasi dengan OpenTelemetry SDK untuk mendapatkan konteks trace."
        },
        "optimization": {"log_ingestion_throughput": "Tinggi.", "pii_detection_accuracy": "Tinggi dengan false positive/negative rendah.", "search_performance_archived_logs": "Dapat diterima."},
        "compaction_strategy": "Format log yang ringkas, sampling cerdas, indeks yang dioptimalkan di backend logging.",
        "mitigation_strategy": { # Dari mitigasi_kekurangan_modul.md untuk observability/logging.py
            "identified_shortcomings": ["Akurasi redaksi PII untuk berbagai format data.", "Kompatibilitas mundur versioning skema log.", "Latensi pengambilan cold storage.", "Limitasi skalabilitas pemrosesan real-time."],
            "working_prototype_requirements": ["Deteksi PII multi-format dengan model NLP.", "Evolusi skema dengan jaminan kompatibilitas mundur.", "Tiered storage dengan archiving cerdas.", "Stream processing dengan integrasi Apache Kafka."],
            "security_audit_requirements": ["Verifikasi efektivitas redaksi PII.", "Validasi kriptografis integritas log.", "Assessment granularitas kontrol akses.", "Verifikasi enkripsi cold storage."],
            "performance_benchmarking_methodology": "Pengukuran throughput ingest log, kuantifikasi tingkat akurasi deteksi PII, analisis performa pencarian log yang diarsipkan, pengukuran latensi pemrosesan real-time.",
            "reference_implementation_verification": ["Arsitektur logging terpusat Netflix/Uber/LinkedIn/Twitter."]
        },
        "nist_alignment_notes": "Logging yang komprehensif, aman, dan terstruktur adalah fundamental untuk audit, investigasi insiden, dan pemantauan keamanan (NIST SP 800-92)."
    },
    "observability/metrics_collector.py": { # Gabungan dari asu_ekstensi (observability/metrics.py) dan research_architecture (monitoring/metrics.py)
        "scope": "Observability",
        "status": "Defined",
        "description": "Pengumpulan metrik produksi komprehensif, termasuk metrik bisnis, indikator performa (RED), analitik riset, dan analisis tren dengan deteksi anomali.",
        "production_proven": "Prometheus, Datadog, New Relic APM patterns.",
        "requirements": [
            # Dari asu_ekstensi
            "Agregasi metrik RED (Rate, Errors, Duration) untuk semua layanan/endpoint.",
            "Definisi dan pelacakan Service Level Objectives (SLO).",
            "Auto-dashboarding (integrasi dengan Grafana).",
            "Korelasi metrik antar layanan.",
            "Kontrol kardinalitas (target max 100 tag/metrik, bisa adaptif).",
            "Isolasi metrik multi-tenant (jika aplikasi multi-tenant).",
            "Deteksi anomali berbasis ML pada metrik.",
            "Kemampuan forecasting berdasarkan data metrik historis.",
            "Validasi SLO berkelanjutan.",
            "Metric exemplars untuk korelasi dengan trace.",
            # Dari research_architecture
            "Pelacakan metrik bisnis (pola penggunaan, workflow riset).",
            "Indikator performa (latensi, throughput, error rates) - sudah tercakup RED.",
            "Metrik riset kustom dengan KPI domain-spesifik.",
            "Analisis tren dengan deteksi anomali (sudah tercakup).",
            "Agregasi metrik dengan kebijakan retensi yang dapat dikonfigurasi."
        ],
        "dependencies": ["prometheus_client>=0.20.0", "scikit-learn>=1.4.0"], # Contoh
        "implementation": {
            "metrics_backend_integration": "Ekspos metrik dalam format Prometheus untuk di-scrape, atau push ke backend lain (Datadog). Visualisasi dengan Grafana.",
            "slo_definition_framework": "Mendefinisikan SLO dalam kode atau konfigurasi, dengan alerting pada burn rate.",
            "anomaly_detection_model": "Menggunakan Isolation Forest, Prophet, atau model statistik lain untuk deteksi anomali pada time-series data.",
            "business_metrics_instrumentation": "Instrumentasi kode kustom untuk melacak event bisnis penting."
        },
        "optimization": {"collection_overhead_per_metric": "< 5ms.", "storage_efficiency_timeseries": "> 90% kompresi.", "query_performance_dashboard": "< 100ms.", "alerting_latency_slo": "< 1 menit."},
        "compaction_strategy": "Agregasi metrik yang efisien, pemilihan label/tag yang bijak untuk mengontrol kardinalitas, penyimpanan time-series yang dioptimalkan.",
        "mitigation_strategy": { # Dari mitigasi_kekurangan_modul.md untuk observability/metrics.py
            "identified_shortcomings": ["Kontrol kardinalitas 100 tag/metrik mungkin kurang.", "Limitasi penyimpanan single node Prometheus.", "Akurasi model ML deteksi anomali.", "Kompleksitas otomatisasi validasi SLO."],
            "working_prototype_requirements": ["Prometheus federasi dengan agregasi cross-cluster.", "Manajemen kardinalitas adaptif dengan reduksi tag otomatis.", "Deteksi anomali berbasis ML dengan supervised learning.", "Implementasi alerting burn rate SLO otomatis."],
            "security_audit_requirements": ["Assessment keamanan pengumpulan metrik.", "Verifikasi isolasi metrik cross-tenant.", "Evaluasi bias model deteksi anomali.", "Review implikasi privasi metric exemplar."],
            "performance_benchmarking_methodology": "Pengukuran throughput ingest metrik, analisis performa query untuk metrik kardinalitas tinggi, verifikasi optimasi efisiensi penyimpanan, pengukuran latensi alerting.",
            "reference_implementation_verification": ["Arsitektur sistem monitoring Google Borgmon/Uber M3/Pinterest/Twitter."]
        },
        "nist_alignment_notes": "Pemantauan metrik yang efektif mendukung deteksi dini masalah, perencanaan kapasitas, dan pemahaman perilaku sistem, penting untuk keandalan dan keamanan (NIST SP 800-137)."
    },
    "observability/tracing_setup.py": { # Dari asu_ekstensi (observability/tracing.py)
        "scope": "Observability",
        "status": "Defined",
        "description": "Setup dan konfigurasi distributed tracing end-to-end menggunakan OpenTelemetry untuk melacak request lintas layanan.",
        "production_proven": "OpenTelemetry, Jaeger, Zipkin, AWS X-Ray.",
        "requirements": [
            "Propagasi konteks trace (W3C Trace Context, B3) secara otomatis lintas layanan (HTTP, gRPC, message queues).",
            "Sampling trace (misalnya, tail-based sampling: 5% normal, 100% error, atau head-based adaptif).",
            "Pembuatan graf dependensi layanan otomatis.",
            "Korelasi trace-to-log (menyertakan trace ID dan span ID dalam log).",
            "Penangkapan query database dalam span trace.",
            "Deteksi trace yang berjalan lama (long-running).",
            "Integrasi dengan sistem error tracking.",
            "Pembuatan metrik berbasis span (misalnya, latensi per operasi).",
            "Deteksi anomali dalam data trace.",
            "Pembuatan service maps berbasis data trace."
        ],
        "dependencies": ["opentelemetry-api", "opentelemetry-sdk>=1.24.0", "opentelemetry-instrumentation>=0.45b0", "opentelemetry-exporter-otlp"], # Contoh
        "implementation": {
            "trace_exporter_config": "Konfigurasi exporter untuk mengirim trace ke backend (Jaeger, Zipkin, OpenTelemetry Collector, Datadog).",
            "auto_instrumentation_libraries": "Penggunaan library instrumentasi otomatis OpenTelemetry untuk framework umum (FastAPI, Requests, gRPC).",
            "manual_instrumentation_points": "Instrumentasi manual untuk bagian kode kustom yang penting.",
            "sampling_strategy_config": "Konfigurasi sampler (misalnya, ParentBased(TraceIdRatioBasedSampler), atau custom sampler)."
        },
        "optimization": {"tracing_overhead_target": "< 5% pada latensi request.", "trace_query_performance": "Cepat untuk analisis.", "storage_cost_optimization_trace": "Efisiensi penyimpanan trace."},
        "compaction_strategy": "Sampling yang cerdas, agregasi data trace jika memungkinkan, retensi data trace yang bijak.",
        "mitigation_strategy": { # Dari mitigasi_kekurangan_modul.md untuk observability/tracing.py
            "identified_shortcomings": ["Kompleksitas tail-based sampling untuk sistem terdistribusi.", "Biaya penyimpanan retensi trace.", "Overhead propagasi konteks untuk sistem throughput tinggi.", "Akurasi graf dependensi layanan dengan layanan dinamis."],
            "working_prototype_requirements": ["Sampling adaptif berdasarkan kritikalitas layanan.", "Penyimpanan trace terdistribusi dengan optimasi biaya.", "Implementasi propagasi konteks beroverhead rendah.", "Penemuan topologi layanan real-time."],
            "security_audit_requirements": ["Assessment privasi data trace.", "Review keamanan propagasi konteks cross-service.", "Evaluasi dampak bias sampling.", "Verifikasi akurasi service map."],
            "performance_benchmarking_methodology": "Pengukuran overhead tracing, analisis performa query trace, efektivitas optimasi biaya penyimpanan, penilaian dampak latensi propagasi konteks.",
            "reference_implementation_verification": ["Analisis arsitektur Jaeger/Zipkin/AWS X-Ray/Google Cloud Trace."]
        },
        "nist_alignment_notes": "Distributed tracing memberikan visibilitas mendalam terhadap alur request, penting untuk troubleshooting, analisis performa, dan pemahaman interaksi sistem yang kompleks."
    },

    # ==================================================================================
    # INFRASTRUCTURE CONFIGURATION (IaC & Deployment)
    # ==================================================================================
    "infra_config/__init__.py": {"scope": "Infrastructure Configuration", "status": "Defined", "description": "Package untuk konfigurasi infrastruktur.", "requirements": [], "dependencies": [], "implementation": {}, "optimization": {}, "compaction_strategy": {}, "nist_alignment_notes": "Struktur kode."},
    "infra_config/terraform/main.tf": { # Dari asu_ekstensi (infra/main.tf)
        "scope": "Infrastructure Configuration - IaC",
        "status": "Defined",
        "description": "Konfigurasi Infrastructure as Code (IaC) menggunakan Terraform untuk provisioning sumber daya multi-cloud (AWS, GCP, Azure) secara otomatis dan konsisten.",
        "production_proven": "Terraform Cloud (HashiCorp), praktik IaC di enterprise.",
        "requirements": [
            "Prinsip immutable infrastructure.",
            "Deteksi penyimpangan (drift) konfigurasi otomatis dengan alerting.",
            "Implementasi Policy as Code (PaC) menggunakan Open Policy Agent (OPA) atau Sentinel untuk validasi dan enforcement kebijakan keamanan/kepatuhan.",
            "Estimasi biaya pra-deployment (misalnya, menggunakan `terraform plan` dengan cost estimation tools).",
            "Pinning versi modul Terraform untuk stabilitas.",
            "Dukungan untuk pembuatan environment ephemeral (untuk testing, staging).",
            "Visualisasi graf dependensi sumber daya.",
            "Enkripsi state Terraform at-rest (misalnya, menggunakan S3 backend dengan SSE).",
            "Dukungan referensi cross-provider (jika diperlukan dalam arsitektur multi-cloud yang kompleks)."
        ],
        "dependencies": ["hashicorp/aws>=5.40.0", "hashicorp/google>=5.23.0", "hashicorp/azurerm>=3.95.0"], # Contoh provider
        "implementation": {
            "state_management_backend_config": "Backend S3 dengan enkripsi server-side dan locking (DynamoDB untuk AWS).",
            "module_structure": "Penggunaan modul Terraform yang reusable untuk komponen infrastruktur umum.",
            "policy_enforcement_integration": "Integrasi OPA/Sentinel dalam pipeline CI/CD untuk validasi `terraform plan`."
        },
        "optimization": {"deployment_time_infra": "Cepat dan reliable.", "drift_detection_accuracy": "Tinggi.", "policy_evaluation_performance": "Cepat."},
        "compaction_strategy": "Modul Terraform yang efisien, penggunaan variabel dan workspace yang baik.",
        "mitigation_strategy": { # Dari mitigasi_kekurangan_modul.md untuk infra/main.tf
            "identified_shortcomings": ["Kompleksitas manajemen state multi-cloud.", "False positive rate deteksi drift.", "Konsistensi enforcement policy as code.", "Akurasi estimasi biaya untuk deployment kompleks."],
            "working_prototype_requirements": ["Resolusi dependensi sumber daya cross-cloud.", "Remediasi drift otomatis dengan workflow approval.", "Remediasi otomatis pelanggaran kebijakan.", "Pelacakan biaya real-time dengan budget alerts."],
            "security_audit_requirements": ["Assessment keamanan state infrastruktur.", "Verifikasi efektivitas enforcement kebijakan.", "Review manajemen kredensial cross-provider.", "Validasi kepatuhan immutable infrastructure."],
            "performance_benchmarking_methodology": "Pengukuran waktu deployment, analisis tingkat akurasi deteksi drift, pengujian performa evaluasi kebijakan, verifikasi akurasi estimasi biaya.",
            "reference_implementation_verification": ["Manajemen infrastruktur multi-cloud Netflix/Spotify/Airbnb, penggunaan Terraform enterprise HashiCorp."]
        },
        "nist_alignment_notes": "Infrastructure as Code mendukung provisioning yang aman, konsisten, dan dapat diaudit, sejalan dengan NIST SP 800-209 (Security-Enhanced Virtualization) dan praktik DevSecOps."
    },
    "infra_config/deployment_pipelines/argocd_apps.yaml": { # Dari asu_ekstensi (deployments/argocd_apps.yaml)
        "scope": "Infrastructure Configuration - GitOps",
        "status": "Defined",
        "description": "Konfigurasi aplikasi ArgoCD untuk continuous delivery berbasis GitOps, memastikan state deployment sinkron dengan konfigurasi di Git.",
        "production_proven": "ArgoCD (digunakan oleh Intuit, Red Hat).",
        "requirements": [
            "Definisi Aplikasi ArgoCD (AppProject, Application).",
            "Health checks aplikasi yang akurat dan komprehensif.",
            "Strategi deployment (misalnya, rolling update, blue-green, canary) dengan analisis canary otomatis.",
            "Sinkronisasi otomatis atau manual dengan opsi self-heal untuk drift detection.",
            "Penandatanganan (signing) provenance rilis untuk integritas.",
            "Pengurutan resource hook (misalnya, PreSync, Sync, PostSync) untuk dependensi deployment.",
            "Histori rollback aplikasi.",
            "Deployment verification hooks (misalnya, menjalankan tes setelah sync).",
            "Workflow approval perubahan (integrasi dengan sistem notifikasi atau manual).",
            "Webhook status sinkronisasi."
        ],
        "dependencies": ["argocd>=2.10.0", "kustomize>=5.4.0", "helm>=3.14.0", "Kubernetes manifests"], # Tergantung target deployment
        "implementation": {
            "application_source_repo": "URL ke repositori Git yang berisi manifest Kubernetes/Helm/Kustomize.",
            "target_cluster_config": "Konfigurasi cluster Kubernetes tujuan.",
            "sync_policy_options": "{automated: {prune: true, selfHeal: true}} (contoh).",
            "promotion_strategy_details": "Staging: auto-promote on test pass. Production: manual approval + auto-rollback on failure."
        },
        "optimization": {"sync_time": "Cepat.", "health_check_accuracy": "Tinggi.", "canary_analysis_effectiveness": "Mendeteksi regresi dengan baik."},
        "compaction_strategy": "Struktur manifest yang efisien, penggunaan tool templating (Helm/Kustomize) yang optimal.",
        "mitigation_strategy": { # Dari mitigasi_kekurangan_modul.md untuk deployments/argocd_apps.yaml
            "identified_shortcomings": ["Akurasi health check aplikasi untuk microservices kompleks.", "False positive/negative rate analisis canary.", "Kompleksitas manajemen dependensi sync wave.", "Manajemen kunci penandatanganan provenance rilis."],
            "working_prototype_requirements": ["Health checking multi-dimensi dengan metrik kustom.", "Analisis canary berbasis ML dengan deteksi anomali.", "Resolusi dependensi otomatis dengan deteksi konflik.", "Penandatanganan terdistribusi dengan dukungan rotasi kunci."],
            "security_audit_requirements": ["Assessment postur keamanan GitOps.", "Verifikasi integritas provenance rilis.", "Review keamanan workflow approval deployment.", "Analisis implikasi keamanan sync hook."],
            "performance_benchmarking_methodology": "Pengukuran waktu deployment, verifikasi tingkat akurasi health check, pengukuran efektivitas analisis canary, optimasi performa sync wave.",
            "reference_implementation_verification": ["Pola implementasi GitOps GitLab/Flux CD/Spinnaker/Jenkins X."]
        },
        "nist_alignment_notes": "GitOps mendukung deployment yang konsisten, dapat diaudit, dan aman, selaras dengan praktik DevSecOps dan NIST SSDF (SP 800-218)."
    },
    "infra_config/deployment_pipelines/deploy_fly_io.py": { # Dari research_architecture (scripts/deploy.py)
        "scope": "Infrastructure Configuration - Deployment Script",
        "status": "Defined",
        "description": "Skrip deployment otomatis ke Fly.io, mendukung strategi blue-green, verifikasi kesehatan, mekanisme rollback, dan zero-downtime updates.",
        "production_proven": "Praktik deployment ke Fly.io, Kubernetes rolling updates, AWS CodeDeploy patterns.",
        "requirements": [
            "Implementasi strategi blue-green deployment dengan traffic switching yang aman.",
            "Verifikasi kesehatan otomatis setelah deployment stage baru (menggunakan health check endpoint aplikasi).",
            "Rollback otomatis ke versi stabil sebelumnya jika verifikasi kesehatan gagal.",
            "Zero-downtime updates dengan connection draining dan gradual traffic cutover.",
            "Logging metrik dan audit trail untuk setiap proses deployment.",
            "Integrasi dengan pipeline CI/CD (misalnya, dipanggil oleh GitHub Actions)."
        ],
        "dependencies": ["flyctl (CLI Fly.io)", "python (untuk skrip)", "requests (untuk health check)"], # Contoh
        "implementation": {
            "deployment_strategy_logic": "Skrip akan mengelola dua versi aplikasi (biru dan hijau), memvalidasi versi baru sebelum mengalihkan traffic utama.",
            "health_verification_script": "Fungsi untuk melakukan ping ke endpoint health check dan mengevaluasi status.",
            "rollback_trigger_conditions": "Kegagalan health check, error rate tinggi pasca-deployment.",
            "traffic_management_tool": "Menggunakan fitur routing dan traffic splitting Fly.io (atau load balancer eksternal jika ada)."
        },
        "optimization": {"deployment_cycle_time_target": "< 10 menit.", "health_verification_duration": "< 2 menit.", "rollback_speed_target": "< 1 menit.", "zero_downtime_assurance": "99.99% uptime selama deployment."},
        "compaction_strategy": "Orkestrasi deployment yang efisien, sekuens health check yang dioptimalkan, minimalisasi periode downtime (idealnya nol).",
        "mitigation_strategy": { # Placeholder, karena ini skrip operasional, mitigasi lebih ke error handling dalam skrip
            "identified_shortcomings": ["Kompleksitas manajemen state blue-green.", "Potensi kegagalan saat traffic switching.", "Ketergantungan pada CLI `flyctl`."],
            "working_prototype_requirements": ["Skrip deployment yang robust dengan error handling.", "Pengujian menyeluruh traffic switching.", "Fallback jika `flyctl` gagal."],
            "security_audit_requirements": ["Keamanan kredensial deployment.", "Kontrol akses ke skrip deployment."],
            "performance_benchmarking_methodology": ["Benchmarking durasi setiap tahap deployment."],
            "reference_implementation_verification": ["Skrip deployment standar untuk platform PaaS."]
        },
        "nist_alignment_notes": "Deployment otomatis yang aman dan andal mendukung rilis software yang cepat dan berkualitas, sejalan dengan SSDF."
    },
    "infra_config/disaster_recovery/dr_plan_and_scripts.py": { # Dari asu_ekstensi (infra/disaster_recovery.py)
        "scope": "Infrastructure Configuration - Disaster Recovery",
        "status": "Defined",
        "description": "Rencana dan skrip untuk disaster recovery (DR) active-active multi-region, mencakup failover/failback otomatis, replikasi data, dan chaos engineering.",
        "production_proven": "AWS Multi-Region Architecture, Netflix global failover.",
        "requirements": [
            "Target RTO (Recovery Time Objective) <30 menit (idealnya lebih rendah, sub-menit).",
            "Target RPO (Recovery Point Objective) <5 menit (idealnya lebih rendah, <1 menit dengan replikasi kontinu).",
            "Traffic shifting otomatis berbasis latensi dan kesehatan regional.",
            "Integrasi Chaos Engineering untuk pengujian DR secara berkala.",
            "Prosedur failback otomatis atau semi-otomatis yang teruji.",
            "Failover DNS otomatis (misalnya, menggunakan AWS Route 53, Cloudflare DNS).",
            "Health checks regional yang komprehensif.",
            "Replikasi data stateful service (database, message queues, dll.) antar region.",
            "Pemeriksaan konsistensi data setelah failover.",
            "Verifikasi integritas backup dengan checksum dan restore sampling otomatis.",
            "Kemampuan failover dry-run.",
            "Dukungan Geosharding (jika relevan untuk skala data dan latensi pengguna)."
        ],
        "dependencies": ["aws-fis>=2.21.0", "boto3>=1.28.45", "dnspython>=2.4.2", "terraform (untuk infrastruktur DR)"], # Contoh
        "implementation": {
            "target_dr_regions": "Minimal 2 region geografis terpisah (misalnya, us-west-2, eu-central-1, ap-southeast-1).",
            "health_check_interval_dr": "15 detik (atau lebih sering untuk layanan kritis).",
            "failover_strategy_details": "Weighted routing berbasis latensi dan hasil health check, dengan prioritas region.",
            "data_replication_technology": "Tergantung jenis data (misalnya, replikasi native DB, Kafka MirrorMaker, S3 CRR).",
            "backup_validation_process": "Verifikasi checksum harian dan uji restore sampling bulanan ke environment terisolasi."
        },
        "optimization": {"failover_time_actual": "Sesuai target RTO.", "data_loss_actual": "Sesuai target RPO.", "failback_reliability": "Tinggi."},
        "compaction_strategy": "Infrastruktur DR yang efisien (misalnya, warm standby), replikasi data yang dioptimalkan.",
        "mitigation_strategy": { # Dari mitigasi_kekurangan_modul.md untuk infra/disaster_recovery.py
            "identified_shortcomings": ["RTO 30 menit mungkin kurang.", "Potensi kehilangan data RPO 5 menit.", "Dampak latensi traffic shifting.", "Mekanisme keamanan failback otomatis."],
            "working_prototype_requirements": ["Failover sub-menit dengan infrastruktur pre-warmed.", "Replikasi data kontinu dengan RPO <1 menit.", "Routing traffic cerdas dengan prediksi kesehatan.", "Failback otomatis dengan safety checks."],
            "security_audit_requirements": ["Assessment postur keamanan DR.", "Verifikasi keamanan replikasi data cross-region.", "Validasi kontinuitas autentikasi failover.", "Review implikasi keamanan pengujian recovery."],
            "performance_benchmarking_methodology": "Pengukuran waktu failover, verifikasi konsistensi data pasca-failover, analisis dampak latensi routing traffic, validasi akurasi recovery point.",
            "reference_implementation_verification": ["Arsitektur failover global Netflix/Uber/LinkedIn/Google."]
        },
        "nist_alignment_notes": "Ketahanan sistem terhadap bencana adalah aspek kritikal dari keamanan dan ketersediaan (NIST SP 800-34 Contingency Planning)."
    },

    # ==================================================================================
    # OPERATIONS SCRIPTS
    # ==================================================================================
    "operations_scripts/__init__.py": {"scope": "Operations Scripts", "status": "Defined", "description": "Package untuk skrip operasional.", "requirements": [], "dependencies": [], "implementation": {}, "optimization": {}, "compaction_strategy": {}, "nist_alignment_notes": "Struktur kode."},
    "operations_scripts/chaos_engineering/core_scenarios.py": { # Dari asu_ekstensi (scripts/chaos_engineering.py)
        "scope": "Operations Scripts - Chaos Engineering",
        "status": "Defined",
        "description": "Skrip dan definisi untuk menjalankan skenario chaos engineering secara otomatis untuk menguji ketahanan sistem.",
        "production_proven": "Netflix Chaos Automation Platform (ChAP), Gremlin.",
        "requirements": [
            "Katalog template GameDay scenario (misalnya, AZ outage, DB failure, KMS degradation, traffic surge).",
            "Kontrol blast radius yang ketat untuk membatasi dampak eksperimen.",
            "Mekanisme auto-rollback jika terjadi kegagalan kritikal (misalnya, error rate >5% atau pelanggaran SLO).",
            "Database injeksi kegagalan (menyimpan tipe kegagalan, target, parameter).",
            "Simulasi partisi jaringan, latensi, packet loss.",
            "Injeksi kegagalan pada stateful service.",
            "Kemampuan replay chaos experiment.",
            "Forecasting dampak SLO sebelum eksperimen dijalankan.",
            "Versioning eksperimen chaos.",
            "Skenario chaos keamanan (misalnya, simulasi kompromi kredensial)."
        ],
        "dependencies": ["chaostoolkit>=1.17.0", "kubernetes>=29.0.0", "prometheus_client>=0.20.0", "boto3"], # Contoh
        "implementation": {
            "example_scenarios_defined": "['AZ outage simulation', '200% traffic surge', 'KMS degradation', 'Database read replica failure'].",
            "safety_mechanism_details": "Auto-rollback berdasarkan pemantauan SLO real-time dan threshold error rate.",
            "failure_injection_methods": "Menggunakan API cloud provider (AWS FIS), tools chaos (Chaos Mesh), atau skrip kustom.",
            "blast_radius_control_logic": "Targeting spesifik (node, pod, service) dengan konfirmasi sebelum eksekusi."
        },
        "optimization": {"experiment_setup_time": "Cepat.", "impact_assessment_accuracy": "Tinggi.", "rollback_speed_chaos": "Cepat."},
        "compaction_strategy": "Skenario chaos yang modular dan reusable.",
        "mitigation_strategy": { # Dari mitigasi_kekurangan_modul.md untuk scripts/chaos_engineering.py
            "identified_shortcomings": ["Kontrol blast radius mungkin kurang untuk kegagalan berantai.", "Threshold auto-rollback 5% error rate mungkin terlalu konservatif.", "Limitasi cakupan skenario chaos keamanan.", "Overhead maintenance template skenario GameDay."],
            "working_prototype_requirements": ["Kontrol blast radius multi-layer dengan analisis dependensi.", "Threshold rollback adaptif berdasarkan kritikalitas layanan.", "Framework pengujian chaos keamanan komprehensif.", "Generasi skenario otomatis dengan pola berbasis ML."],
            "security_audit_requirements": ["Verifikasi mekanisme keamanan eksperimen chaos.", "Assessment efektivitas skenario chaos keamanan.", "Review implementasi kontrol blast radius.", "Validasi kelengkapan audit trail eksperimen."],
            "performance_benchmarking_methodology": "Pengukuran dampak eksperimen chaos, verifikasi efektivitas mekanisme rollback, analisis cakupan skenario chaos keamanan, pengukuran tingkat keberhasilan latihan GameDay.",
            "reference_implementation_verification": ["Platform Gremlin, Litmus, Chaos Monkey, Principles of Chaos Engineering."]
        },
        "nist_alignment_notes": "Chaos engineering secara proaktif mengidentifikasi kelemahan sistem dan meningkatkan ketahanan, sejalan dengan NIST SP 800-160 (Systems Security Engineering)."
    },
    "operations_scripts/chaos_engineering/ci_cd_tests.yaml": { # Dari asu_ekstensi (deployments/chaos_tests.yaml)
        "scope": "Operations Scripts - Chaos Engineering",
        "status": "Defined",
        "description": "Konfigurasi untuk menjalankan tes chaos engineering sebagai bagian dari pipeline CI/CD untuk validasi ketahanan berkelanjutan.",
        "production_proven": "Gremlin in CI/CD, Chaos Mesh/Litmus dalam pipeline.",
        "requirements": [
            "Injeksi kegagalan di environment pra-produksi (staging, testing).",
            "Pengukuran dampak terhadap SLO selama tes chaos.",
            "Laporan eksperimen otomatis yang terintegrasi dengan hasil CI/CD.",
            "Verifikasi steady-state sebelum dan sesudah eksperimen.",
            "Validasi hipotesis otomatis (apakah sistem bereaksi seperti yang diharapkan).",
            "Pengujian chaos keamanan dalam pipeline.",
            "Eksperimen yang aman untuk produksi (jika dijalankan di prod, dengan blast radius sangat terbatas).",
            "Versioning tes chaos (sinkron dengan versi kode).",
            "Visualisasi blast radius (jika memungkinkan).",
            "Integrasi metrik chaos dengan dashboard observabilitas."
        ],
        "dependencies": ["chaosmesh>=2.6.1", "prometheus_client>=0.20.0", "grafana-api>=1.7.0", "CI/CD platform (misalnya, GitHub Actions, Jenkins)"],
        "implementation": {
            "test_frequency_in_cicd": "Per rilis kandidat ke staging, atau terjadwal (misalnya, nightly).",
            "safety_controls_in_cicd": "Blast radius terbatas pada environment non-prod, auto-abort jika SLO kritis dilanggar.",
            "reporting_integration": "Publikasi hasil tes chaos ke sistem pelaporan CI/CD atau dashboard."
        },
        "optimization": {"test_execution_time_cicd": "Cepat agar tidak memperlambat pipeline.", "sl_impact_correlation_accuracy": "Tinggi."},
        "compaction_strategy": "Skenario tes chaos yang ringan dan terfokus untuk CI/CD.",
        "mitigation_strategy": { # Dari mitigasi_kekurangan_modul.md untuk deployments/chaos_tests.yaml
            "identified_shortcomings": ["Limitasi realisme injeksi kegagalan pra-produksi.", "Akurasi pengukuran dampak SLO.", "Definisi batas eksperimen aman produksi.", "Kompleksitas versioning tes chaos."],
            "working_prototype_requirements": ["Environment pengujian production-mirror.", "Korelasi dampak SLO real-time.", "Enforcement batas keamanan otomatis.", "Spesifikasi eksperimen chaos yang ter-version control."],
            "security_audit_requirements": ["Verifikasi batas keamanan pengujian chaos.", "Assessment efektivitas isolasi produksi.", "Review konfigurasi eksperimen keamanan.", "Validasi privasi data pengukuran dampak."],
            "performance_benchmarking_methodology": "Pengukuran waktu eksekusi tes chaos, verifikasi akurasi korelasi dampak SLO, analisis efektivitas kontrol keamanan, validasi reproduktifitas eksperimen.",
            "reference_implementation_verification": ["Chaos Mesh, PowerfulSeal, Chaos Toolkit, Steadybit."]
        },
        "nist_alignment_notes": "Mengintegrasikan pengujian ketahanan dalam CI/CD memastikan bahwa sistem tetap tangguh seiring dengan perubahan kode, mendukung SSDF."
    },
    "operations_scripts/key_rotation_manager.py": { # Dari asu_ekstensi (scripts/key_rotation.py)
        "scope": "Operations Scripts - Security",
        "status": "Defined",
        "description": "Skrip untuk rotasi kunci kriptografi otomatis dengan zero-downtime, validasi, dan audit trail.",
        "production_proven": "AWS KMS Rotation, HashiCorp Vault transit secret engine rotation.",
        "requirements": [
            "Rotasi kunci zero-downtime (data yang dienkripsi dengan kunci lama masih bisa didekripsi selama periode transisi).",
            "Validasi pra-rotasi (misalnya, memastikan kunci baru dapat digunakan untuk enkripsi/dekripsi).",
            "Pemeriksaan integritas pasca-rotasi (misalnya, memverifikasi sejumlah kecil data dapat didekripsi dengan kunci baru).",
            "Audit trail lengkap untuk semua aktivitas rotasi kunci.",
            "Verifikasi material kunci (memastikan kunci baru valid dan sesuai standar).",
            "Aliasing versi kunci (misalnya, `current_key` selalu menunjuk ke versi terbaru).",
            "Monitoring kesehatan kunci (misalnya, status, tanggal kadaluarsa).",
            "Prosedur pencabutan darurat untuk kunci yang terkompromi.",
            "Dukungan dual-layer key wrapping (jika menggunakan KEK dan DEK)."
        ],
        "dependencies": ["aws-encryption-sdk==2.3.1", "boto3>=1.28.45", "cryptography>=41.0.7", "src/security/crypto_services.py"], # Contoh
        "implementation": {
            "rotation_window_config": "Dapat dikonfigurasi, target awal 00:00-04:00 akhir pekan (disesuaikan dengan zona waktu operasional global).",
            "validation_checks_detailed": "Pra-rotasi: enkripsi/dekripsi data sampel. Pasca-rotasi: verifikasi integritas data yang baru dienkripsi dan data lama.",
            "key_versioning_scheme": "Menggunakan alias atau mekanisme pointer untuk menunjuk ke kunci aktif saat ini.",
            "emergency_revocation_steps": "Prosedur terdokumentasi dan skrip otomatis (jika mungkin) untuk menonaktifkan kunci terkompromi dan mempromosikan kunci cadangan."
        },
        "optimization": {"rotation_downtime_target": "Nol.", "validation_coverage": "Komprehensif.", "emergency_revocation_time": "Sub-menit."},
        "compaction_strategy": "Proses rotasi yang efisien, logging audit yang ringkas namun lengkap.",
        "mitigation_strategy": { # Dari mitigasi_kekurangan_modul.md untuk scripts/key_rotation.py
            "identified_shortcomings": ["Jendela rotasi akhir pekan mungkin kurang untuk operasi global.", "Celah cakupan validasi pra-rotasi.", "Delay propagasi pencabutan darurat.", "Overhead komputasi verifikasi material kunci."],
            "working_prototype_requirements": ["Penjadwalan rotasi follow-the-sun dengan kesadaran zona waktu.", "Pengujian validasi komprehensif dengan workload sintetis.", "Propagasi pencabutan darurat sub-menit.", "Verifikasi kunci yang dioptimalkan dengan pemrosesan paralel."],
            "security_audit_requirements": ["Assessment postur keamanan rotasi kunci.", "Verifikasi efektivitas pengujian validasi.", "Review prosedur darurat keamanan.", "Validasi kepatuhan penanganan material kunci."],
            "performance_benchmarking_methodology": "Pengukuran downtime rotasi (target: nol), analisis cakupan pengujian validasi, verifikasi waktu propagasi pencabutan darurat, optimasi performa verifikasi kunci.",
            "reference_implementation_verification": ["Rotasi otomatis Google Cloud KMS/Azure Key Vault/HashiCorp Vault, pola rotasi kunci multi-region AWS KMS."]
        },
        "nist_alignment_notes": "Rotasi kunci kriptografi secara berkala adalah praktik keamanan fundamental untuk membatasi dampak jika kunci terkompromi (NIST SP 800-57)."
    },

    # ==================================================================================
    # TESTS
    # ==================================================================================
    "tests/__init__.py": {"scope": "Testing", "status": "Defined", "description": "Package untuk semua jenis tes.", "requirements": [], "dependencies": [], "implementation": {}, "optimization": {}, "compaction_strategy": {}, "nist_alignment_notes": "Struktur kode."},
    "tests/conftest.py": { # Dari research_architecture
        "scope": "Testing - Configuration",
        "status": "Defined",
        "description": "Konfigurasi PyTest global, shared fixtures, manajemen data tes, dan isolasi environment untuk pengujian yang komprehensif dan reliable.",
        "production_proven": "pytest patterns dari Django, FastAPI test suites.",
        "requirements": [
            "Definisi shared fixtures dengan scope management (session, module, function, class).",
            "Setup dan teardown test database otomatis dengan isolasi data antar tes.",
            "Konfigurasi mock service untuk dependensi eksternal (misalnya, API pihak ketiga, layanan cloud).",
            "Fixtures untuk performance benchmarking dengan analisis statistik (integrasi dengan pytest-benchmark).",
            "Dukungan eksekusi tes paralel dengan manajemen sumber daya (pytest-xdist).",
            "Manajemen data tes (misalnya, data PII yang di-generate secara acak dan aman, dataset sampel)."
        ],
        "dependencies": ["pytest", "pytest-cov", "pytest-benchmark", "pytest-xdist", "requests-mock", "faker"], # Contoh
        "implementation": {
            "fixture_management_style": "Penggunaan factory pattern untuk generasi data tes dinamis.",
            "database_isolation_strategy": "Penggunaan database tes terpisah per sesi tes atau per tes dengan transaction rollback.",
            "mock_service_library": "Menggunakan `requests-mock` atau `unittest.mock` untuk HTTP mocks.",
            "benchmark_fixture_usage": "Dekorator `@pytest.mark.benchmark` untuk fungsi yang akan di-benchmark."
        },
        "optimization": {"test_setup_time_target": "< 1s untuk inisialisasi fixture umum.", "data_generation_speed": "Cepat untuk dataset besar.", "parallel_execution_scaling": "Linear hingga jumlah core CPU.", "test_worker_memory_usage": "< 50MB per proses worker."},
        "compaction_strategy": "Berbagi fixture secara efisien, generasi data tes minimal yang diperlukan, optimasi eksekusi paralel.",
        "nist_alignment_notes": "Infrastruktur pengujian yang baik mendukung kualitas dan keandalan perangkat lunak, penting untuk SSDF (NIST SP 800-218)."
    },
    "tests/performance/test_large_file_operations.py": { # Dari research_architecture
        "scope": "Testing - Performance",
        "status": "Defined",
        "description": "Tes performa untuk operasi file besar, termasuk memory profiling, benchmarking throughput, dan validasi skalabilitas untuk workload enterprise.",
        "production_proven": "Apache Hadoop, Spark performance testing patterns.",
        "requirements": [
            "Memory profiling dengan deteksi kebocoran memori (memory leak) untuk operasi pada file besar.",
            "Benchmarking throughput (MB/s atau GB/s) dengan pengujian signifikansi statistik.",
            "Pengujian skalabilitas dengan berbagai ukuran file (misalnya, 1MB hingga 10GB+).",
            "Pemantauan utilisasi sumber daya sistem (CPU, memori, I/O) selama tes.",
            "Deteksi regresi performa dengan perbandingan terhadap baseline historis.",
            "Pengujian untuk modul `src/core/file_format_manager.py` dan `src/storage/*` yang menangani file besar."
        ],
        "dependencies": ["pytest", "pytest-benchmark", "memory_profiler", "psutil", "src/"],
        "implementation": {
            "memory_profiling_tool": "Integrasi dengan `memory_profiler` atau alat profiling Python lainnya.",
            "benchmark_framework_usage": "Menggunakan `pytest-benchmark` dengan metrik kustom jika perlu.",
            "large_file_generation_method": "Generasi file besar secara deterministik (dengan konten yang dapat diprediksi atau acak terkontrol) untuk konsistensi pengujian.",
            "resource_monitoring_integration": "Menggunakan `psutil` untuk melacak penggunaan sumber daya sistem selama eksekusi tes."
        },
        "optimization": {"test_execution_duration_target": "< 5 menit untuk suite performa penuh (bisa lebih lama tergantung kompleksitas).", "memory_accuracy_measurement": "±1MB.", "throughput_precision_measurement": "±5%."},
        "compaction_strategy": "Generasi file tes yang efisien, overhead monitoring minimal, eksekusi benchmark yang dioptimalkan.",
        "nist_alignment_notes": "Memastikan performa sistem sesuai dengan kebutuhan dan tidak mengalami regresi adalah penting untuk keandalan operasional."
    },
    "tests/unit/": {
        "scope": "Testing - Unit",
        "status": "Placeholder - Requires Specific Test Files",
        "description": "Direktori untuk semua unit test. Setiap modul di `src/` harus memiliki file tes unit yang sesuai (misalnya, `tests/unit/core/test_file_format_manager.py`).",
        "requirements": ["Cakupan kode tinggi.", "Tes independen dan cepat."],
        "dependencies": ["pytest", "src/"],
        "implementation": {"naming_convention": "`test_*.py` untuk file, `test_*` untuk fungsi tes."},
        "nist_alignment_notes": "Unit testing adalah dasar untuk memastikan kualitas kode."
    },
    "tests/integration/": {
        "scope": "Testing - Integration",
        "status": "Placeholder - Requires Specific Test Files",
        "description": "Direktori untuk integration test, menguji interaksi antar modul atau dengan layanan eksternal (yang di-mock).",
        "requirements": ["Memvalidasi alur kerja end-to-end antar komponen."],
        "dependencies": ["pytest", "src/", "api/"],
        "implementation": {"focus": "Interaksi antar modul, kontrak API."},
        "nist_alignment_notes": "Memastikan komponen sistem bekerja sama dengan benar."
    },
    "tests/security/": {
        "scope": "Testing - Security",
        "status": "Placeholder - Requires Specific Test Files/Procedures",
        "description": "Direktori atau placeholder untuk skrip dan prosedur pengujian keamanan, termasuk yang terkait dengan 'Independent Security Audit Requirements' dari file mitigasi.",
        "requirements": ["Pengujian penetrasi.", "Analisis kerentanan.", "Verifikasi implementasi kontrol keamanan."],
        "dependencies": [], # Bisa tools eksternal
        "implementation": {"methodology": "Sesuai standar OWASP, NIST SP 800-115."},
        "nist_alignment_notes": "Pengujian keamanan proaktif sangat penting (NIST SP 800-115 Technical Guide to Information Security Testing and Assessment)."
    },
    # ... (File-file lain di root seperti .dockerignore, .gitignore, LICENSE akan dibuat secara manual sesuai kebutuhan standar proyek) ...
    "unified_architecture_definition.py": {
        "scope": "Root Configuration",
        "status": "Self-Referential",
        "description": "File ini sendiri, yang mendefinisikan arsitektur terpadu dari proyek.",
        "production_proven": "N/A",
        "requirements": ["Menjadi sumber kebenaran tunggal untuk deskripsi arsitektur modul."],
        "dependencies": [], "implementation": {}, "optimization": {}, "compaction_strategy": {},
        "nist_alignment_notes": "Dokumentasi arsitektur yang jelas dan terpusat mendukung pemahaman dan pengembangan proyek."
    }
}

if __name__ == "__main__":
    # Contoh cara mengakses deskripsi modul
    # print("Deskripsi PQC Services:", UNIFIED_PROJECT_ARCHITECTURE.get("src/security/pqc_services.py", {}).get("description"))
    # print("Persyaratan Mitigasi File Format:", UNIFIED_PROJECT_ARCHITECTURE.get("src/core/file_format_manager.py", {}).get("mitigation_strategy", {}).get("working_prototype_requirements"))
    
    module_count = 0
    for key, value in UNIFIED_PROJECT_ARCHITECTURE.items():
        if isinstance(value, dict) and "scope" in value: # Menghitung modul utama, bukan sub-kunci
            module_count +=1
            # Validasi dasar bahwa field utama ada
            # assert "description" in value, f"Modul {key} tidak memiliki deskripsi."
            # assert "requirements" in value, f"Modul {key} tidak memiliki persyaratan."
            # assert "nist_alignment_notes" in value, f"Modul {key} tidak memiliki catatan keselarasan NIST."

    print(f"Definisi arsitektur terpadu dimuat. Jumlah modul/file utama yang didefinisikan: {module_count}")
    
    # Validasi kelengkapan sederhana (hanya contoh, bisa lebih canggih)
    defined_modules_in_code = set(UNIFIED_PROJECT_ARCHITECTURE.keys())
    
    # Daftar modul dari struktur direktori yang diusulkan (perlu disesuaikan agar cocok dengan kunci di dictionary)
    # Ini adalah daftar yang lebih sederhana untuk perbandingan.
    # Struktur direktori yang kompleks memerlukan pemetaan yang lebih cermat ke kunci dictionary.
    expected_top_level_components = [
        "README.md", "requirements.txt", "pyproject.toml", "Dockerfile", "fly.toml",
        ".github/workflows/main_ci_cd.yml",
        "api/__init__.py", "api/app.py", "api/routes/__init__.py", "api/routes/files.py", "api/routes/queries.py",
        "api/middleware/__init__.py", "api/middleware/auth.py", "api/middleware/protection.py",
        "src/core/__init__.py", "src/core/file_format_manager.py", "src/core/metadata_registry.py",
        "src/security/pqc_services.py", "src/security/crypto_services.py", 
        "src/security/access_controller.py", "src/security/compliance_checker.py",
        "src/virtualization/wine_executor.py",
        # Tambahkan semua modul lain yang diharapkan di sini untuk validasi yang lebih baik
    ]
    # Anda bisa menambahkan validasi lebih lanjut di sini jika diperlukan.
    pass
