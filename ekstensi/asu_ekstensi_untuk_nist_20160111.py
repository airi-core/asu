asu_file_extension_architecture = {
    # ===== CORE LAYER (PRODUCTION-GRADE) =====
    "core/file_format.py": {
        "description": "Format kolumnar dengan performa petabyte-scale",
        "production_proven": "Apache Iceberg (Netflix)",
        "requirements": [
            "Z-Order Clustering untuk 2-3 dimensi (terbukti di produksi Netflix)",
            "Partisi temporal otomatis (YYYY/MM/DD)",
            "Schema evolution tanpa rewrite untuk perubahan backward-compatible",
            "ACID transactions dengan isolation level snapshot",
            "Time travel queries dengan retention 7 hari",
            "Data compaction otomatis berbasis ukuran file",
            "Column-level statistics (min/max/null count)",
            "Hidden partitioning untuk abstraksi user",
            "Positional delete files untuk soft delete",
            "File pruning berdasarkan stats metadata"
        ],
        "dependencies": ["pyiceberg==0.4.1", "pyarrow>=12.0.1", "numpy<2.0"],
        "implementation": {
            "partition_spec": "days(event_time), bucket(16, research_id)",
            "optimization": "VACUUM SNAPSHOTS RETAIN 7 DAYS",
            "compaction_strategy": "Berdasarkan ukuran file & umur data"
        }
    },
    

"core/post_quantum_crypto.py": {

"description": "Quantum-safe cryptography with massive parallelism",

"production_proven": "LibOQS (Open Quantum Safe) & Intel IPP-Crypto",

"requirements": [

"Hybrid key exchange (Kyber + ECDH)",

"Hybrid signatures (Dilithium + ECDSA)",

"Parallel execution with thread pool (1024-9216 threads)",

"CPU acceleration using AVX-512 and SHA-NI extensions",

"NIST PQC Standard compliance (draft)",

"Side-channel attack resistance",

"Key encapsulation mechanism (KEM)",

"Cryptographic agility",

"Hardware acceleration support",

"Thread-safe context management"

],

"dependencies": ["liboqs-python>=0.8.0", "intel-ipp-crypto>=2021.10.0", "numpy<2.0"],

"implementation": {

"key_exchange": "Kyber-1024 + ECDH secp384r1",

"signature": "Dilithium5 + ECDSA secp384r1",

"thread_pool": "Dynamic thread pool (min=1024, max=9216)",

"acceleration": "AVX-512 for vectorization, SHA-NI for hashing",

"compliance": "NIST SP 800-208, NIST PQC Project"

},
    "core/crypto.py": {
        "description": "Enkripsi end-to-end dengan rotasi kunci zero-downtime",
        "production_proven": "AWS KMS Multi-Region Keys",
        "requirements": [
            "Envelope encryption dengan data key caching",
            "Key rotation dengan grace period 7 hari",
            "Integrasi CloudTrail untuk audit",
            "FIPS 140-2 Level 3 compliance",
            "HSM-backed key storage",
            "Key usage auditing",
            "Emergency key revocation",
            "Key alias management untuk environment",
            "Client-side encryption hooks",
            "KMS policy auto-generation"
        ],
        "dependencies": ["aws-encryption-sdk==2.3.1", "boto3>=1.28.45", "cryptography>=41.0.7"],
        "implementation": {
            "key_rotation_schedule": "Otomatis setiap 90 hari",
            "fallback_mechanism": "Kunci lama valid 7 hari pasca-rotasi",
            "audit_log_integration": "CloudTrail + S3 bucket terenkripsi"
        }
    },
    
    "core/metadata.py": {
        "description": "Schema registry dengan evolusi aman",
        "production_proven": "Confluent Schema Registry",
        "requirements": [
            "Backward/forward compatibility",
            "SHA-256 schema fingerprint",
            "HTTP API dengan OAuth2 authentication",
            "Metadata replication multi-AZ",
            "Point-in-time recovery 14 hari",
            "Schema validation menggunakan JSON Schema",
            "Schema references untuk nested types",
            "Protobuf schema support",
            "Schema diff visualization"
        ],
        "dependencies": ["fastavro>=1.8.2", "requests-oauthlib>=1.3.1", "protobuf>=4.25.3"],
        "implementation": {
            "schema_evolution_rules": [
                "Tambah field: selalu optional dengan default null",
                "Hapus field: hanya jika deprecated >180 hari"
            ],
            "replication_strategy": "Multi-AZ synchronous replication"
        }
    },
    "virtualization/wine_execution.py": {

"description": "Windows applications on Linux without hardware virtualization",

"production_proven": "Steam Proton with 75% game compatibility",

"requirements": [

"Wine 8.0+ with staging patches",

"DXVK for DirectX translation",

"Vulkan drivers installation",

"Windows fonts package",

"Audio system configuration",

"Registry environment setup",

"DLL override management",

"Prefix isolation per application",

"Performance monitoring tools",

"Compatibility database access"

],

"dependencies": ["wine>=8.0", "winetricks>=20230212", "dxvk>=2.3", "vkd3d-proton>=2.10", "mangohud>=0.6.9.1"],

"implementation": {

"wine_version": "8.0 with staging patches",

"graphics_stack": "DXVK 2.3 + VKD3D-Proton 2.10",

"font_setup": "winetricks corefonts",

"audio_system": "PulseAudio with winetricks settings",

"registry_setup": "Custom .reg files applied during prefix creation",

"dll_overrides": "Managed via WINEDLLOVERRIDES environment variable",

"prefix_isolation": "Separate WINEPREFIX per application",

"performance_monitoring": "MANGOHUD for Vulkan/OpenGL metrics",

"compatibility_database": "Access via ProtonDB API",

"test_frequency": "Per application deployment + weekly",

"safety_controls": "Sandboxed wine prefixes (via bubblewrap) + resource limiting (via cgroups)"

}
    
    # ===== STORAGE LAYER (MULTI-CLOUD) =====
    "storage/s3.py": {
        "description": "Intelligent tiering dengan cost optimization",
        "production_proven": "Spotify S3 Cost Optimizer",
        "requirements": [
            "Auto-transition: Standard → IA → Glacier",
            "Access logging terenkripsi",
            "Object lock WORM compliance",
            "Bucket versioning enforcement",
            "Cross-region replication RTO <1h",
            "Presigned URL custom policies",
            "Storage lens untuk cost analytics",
            "S3 batch operations wrapper",
            "Cross-account replication encrypted",
            "Storage class analytics"
        ],
        "dependencies": ["boto3>=1.28.45", "s3transfer>=0.8.0", "minio>=7.1.16"],
        "implementation": {
            "lifecycle_policy": [
                {"access_days": 30, "class": "INTELLIGENT_TIERING"},
                {"access_days": 90, "class": "GLACIER_DEEP_ARCHIVE"}
            ],
            "encryption": "AES-256 server-side encryption"
        }
    },
    
    "storage/versioning.py": {
        "description": "Immutable data versioning",
        "production_proven": "Git LFS at Scale (Microsoft)",
        "requirements": [
            "Content-addressable storage",
            "Deduplikasi blok biner",
            "Cryptographic verification (SHA-256)",
            "Snapshot atomicity",
            "GC otomatis dengan retention policy",
            "Branching support",
            "Cross-repo deduplication",
            "Content-defined chunking",
            "Version garbage collection API",
            "Delta encoding untuk perubahan kecil"
        ],
        "dependencies": ["pygit2>=1.12.2", "zstandard>=0.22.0", "blake3>=0.4.1"],
        "implementation": {
            "retention_policy": "Versi dipertahankan 365 hari kecuali legal hold",
            "deduplication_algorithm": "Rabin fingerprinting + sliding window"
        }
    },
    
    "storage/query_cache.py": {
        "description": "Materialized view untuk percepatan query",
        "production_proven": "Firebolt Materialized Views",
        "requirements": [
            "Auto-refresh pada data baru",
            "TTL berdasarkan last access time (30 hari)",
            "Columnar storage format",
            "Cache invalidation atomic",
            "Query rewrite otomatis",
            "Cache persistence setelah restart",
            "Cache compression Zstd",
            "Cache warming strategi",
            "Cache size auto-tuning",
            "Result set caching partial"
        ],
        "dependencies": ["duckdb>=0.10.0", "pyarrow>=12.0.1", "zstandard>=0.22.0"],
        "implementation": {
            "refresh_mechanism": "CDC-based dengan trigger perubahan data",
            "compression_ratio": "3:1 menggunakan Zstd level 3"
        }
    },
    
    # ===== API LAYER (FAULT-TOLERANT) =====
    "api/endpoints/files.py": {
        "description": "Secure file operations dengan presigned URL",
        "production_proven": "AWS S3 Presigned URL v4",
        "requirements": [
            "URL expiry 15-60 menit",
            "Signature verification V4",
            "Content-SHA256 header enforcement",
            "CORS strict-origin-when-cross-origin",
            "Upload resumable (hingga 5TB)",
            "Upload checksum verification",
            "Multi-part upload management",
            "Download byte-range support",
            "Virus scanning integration",
            "Download throttling"
        ],
        "dependencies": ["fastapi>=0.109.0", "boto3>=1.28.45", "python-magic>=0.4.27"],
        "implementation": {
            "security_mechanisms": {
                "transport": "TLS 1.3+ required",
                "validation": "HMAC-SHA256 signature"
            },
            "upload_validation": "SHA-256 checksum + ClamAV scanning"
        }
    },
    
    "api/endpoints/queries.py": {
        "description": "Query engine kolumnar real-time",
        "production_proven": "AWS Athena Engine v3",
        "requirements": [
            "Predicate pushdown ke storage",
            "Vectorized execution",
            "Result pagination dengan continuation tokens",
            "Query timeout management (max 30 menit)",
            "Resource isolation per tenant",
            "Result caching middleware",
            "UDTF (User Defined Table Functions)",
            "Cost-based optimizer",
            "Result compression",
            "Query queue prioritization"
        ],
        "dependencies": ["duckdb>=0.10.0", "polars>=0.20.3", "pyarrow>=12.0.1"],
        "implementation": {
            "execution_engine": "Vectorized SIMD + multi-threading",
            "query_optimization": "Cost-based optimizer dengan statistik kolumnar"
        }
    },
    
    "api/middleware/auth.py": {
        "description": "Zero-trust authentication dengan ABAC",
        "production_proven": "OpenTDF (Virtru)",
        "requirements": [
            "OIDC dengan JWT verification",
            "Attribute-based access control",
            "Short-lived credentials (max 1 jam)",
            "Policy decision point terdistribusi",
            "Step-up authentication",
            "Policy versioning",
            "Session binding ke device ID",
            "Credential revocation list",
            "Policy testing sandbox"
        ],
        "dependencies": ["pyjwt>=2.8.0", "python-jose>=3.3.0", "cryptography>=41.0.7"],
        "implementation": {
            "token_flow": "mTLS untuk token refresh",
            "policy_evaluation": "Distributed PDP dengan cache lokal"
        }
    },
    
    "api/middleware/protection.py": {
        "description": "DDoS & bot mitigation",
        "production_proven": "Cloudflare Advanced Protection",
        "requirements": [
            "Rate limiting berbasis IP (5k RPM normal)",
            "JIT challenge tanpa CAPTCHA",
            "IP reputation blocking",
            "Behavioral fingerprinting",
            "API path normalization",
            "TLS fingerprinting",
            "Geo-fencing capabilities",
            "AI-based anomaly detection",
            "Request signing enforcement",
            "Bot score integration"
        ],
        "dependencies": ["redis>=5.0.3", "geoip2>=4.8.0", "cloudflare>=2.11.0"],
        "implementation": {
            "mitigation_strategy": {
                "normal_threshold": "5k RPM",
                "burst_threshold": "50k RPM selama 10 detik",
                "adaptive_mechanism": "AI-based anomaly detection + behavioral fingerprinting"
            }
        }
    },
    
    # ===== OBSERVABILITY (SRE-GRADE) =====
    "observability/metrics.py": {
        "description": "Unified monitoring dashboard",
        "production_proven": "Prometheus",
        "requirements": [
            "RED metrics aggregation",
            "Service level objectives (SLO)",
            "Auto-dashboarding",
            "Metric correlation",
            "Cardinality control (max 100 tags/metric)",
            "Multi-tenant metrics isolation",
            "Anomaly detection berbasis ML",
            "Forecasting capability",
            "Continuous SLO validation",
            "Metric exemplars untuk tracing"
        ],
        "dependencies": ["prometheus-client>=0.20.0", "scikit-learn>=1.4.0"],
        "implementation": {
            "export_interval": "60 detik",
            "anomaly_detection": "Isolation Forest + threshold-based alerting"
        }
    },
    
    "observability/tracing.py": {
        "description": "Distributed tracing end-to-end",
        "production_proven": "OpenTelemetry",
        "requirements": [
            "Context propagation lintas service",
            "Tail-based sampling (5% normal, 100% error)",
            "Service dependency graph",
            "Trace-to-log correlation",
            "Database query capture",
            "Long-running trace detection",
            "Integration error tracking",
            "Span-based metrics",
            "Anomaly detection di traces",
            "Trace-based service maps"
        ],
        "dependencies": ["opentelemetry-sdk>=1.24.0", "opentelemetry-instrumentation>=0.45b0"],
        "implementation": {
            "sampling_strategy": "Tail-based sampling dengan adaptive rates",
            "trace_retention": "7 hari hot storage, 30 hari cold storage"
        }
    },
    
    "observability/logging.py": {
        "description": "Structured logging dengan enrichment",
        "production_proven": "Fluentd + Elasticsearch",
        "requirements": [
            "Log as events dengan schema ketat",
            "PII redaction otomatis",
            "Trace context injection",
            "Cold storage archiving",
            "Log schema versioning",
            "Sensitive data detection",
            "Log replay untuk debugging",
            "Real-time log processing",
            "Anomaly detection di logs",
            "Log sampling adaptif"
        ],
        "dependencies": ["fluent-logger>=0.10.0", "opensearch-py>=2.4.2", "presidio-analyzer>=2.2.36"],
        "implementation": {
            "retention_policy": "30 hari hot storage, 7 tahun cold storage",
            "pii_detection": "Named Entity Recognition + pattern matching"
        }
    },
    
    # ===== INFRASTRUCTURE (GITOPS) =====
    "infra/main.tf": {
        "description": "Multi-cloud provisioning",
        "production_proven": "Terraform Cloud (HashiCorp)",
        "requirements": [
            "Immutable infrastructure",
            "Drift detection otomatis",
            "Policy as code (OPA)",
            "Cost estimation pre-deploy",
            "Module version pinning",
            "Ephemeral environment support",
            "Resource dependency graph",
            "State encryption at rest",
            "Infrastructure visualization",
            "Cross-provider references"
        ],
        "dependencies": ["hashicorp/aws>=5.40.0", "hashicorp/google>=5.23.0", "hashicorp/azurerm>=3.95.0"],
        "implementation": {
            "state_management": {
                "backend": "S3 dengan enkripsi + locking",
                "versioning": "Enabled dengan retention 90 hari"
            },
            "policy_enforcement": "Open Policy Agent (OPA) dengan Sentinel"
        }
    },
    
    "infra/disaster_recovery.py": {
        "description": "Active-active multi-region",
        "production_proven": "AWS Multi-Region Architecture",
        "requirements": [
            "RTO <30 menit, RPO <5 menit",
            "Traffic shifting berbasis latency",
            "Chaos engineering terintegrasi",
            "Automated failback",
            "DNS failover otomatis",
            "Regional health checks",
            "Stateful service replication",
            "Data consistency checks",
            "Failover dry-run capability",
            "Geosharding support"
        ],
        "dependencies": ["aws-fis>=2.21.0", "boto3>=1.28.45", "dnspython>=2.4.2"],
        "implementation": {
            "regions": ["us-west-2", "eu-central-1", "ap-southeast-1"],
            "health_check_interval": "15 detik",
            "failover_strategy": "Weighted routing berbasis latency + health check"
        }
    },
    
    # ===== SECURITY & GOVERNANCE =====
    "security/access_control.py": {
        "description": "Policy engine berbasis atribut",
        "production_proven": "AWS IAM ABAC Model",
        "requirements": [
            "Policy minimization (least privilege)",
            "Just-in-time elevation",
            "Audit log immutable (7 tahun)",
            "Policy simulation engine",
            "Break-glass access procedure",
            "Resource-based policies",
            "Policy dry-run mode",
            "Temporal constraints",
            "Permission delegation chain"
        ],
        "dependencies": ["boto3>=1.28.45", "pycasbin>=1.26.1", "python-jose>=3.3.0"],
        "implementation": {
            "audit_storage": {
                "retention": "7 tahun WORM storage",
                "integrity": "Cryptographic sealing dengan HSM"
            },
            "policy_evaluation": "Attribute-based decision point dengan caching"
        }
    },
    
    "security/compliance.py": {
        "description": "Automated compliance checks",
        "production_proven": "AWS Config Managed Rules",
        "requirements": [
            "GDPR/HIPAA compliance packs",
            "Auto-remediation terjadwal",
            "Evidence collection untuk audit",
            "Policy violation alerts",
            "Compliance as code framework",
            "Evidence hashing chain",
            "Regulatory report templating",
            "Compliance drift detection",
            "Regulatory change tracking",
            "Data sovereignty enforcement"
        ],
        "dependencies": ["prowler>=4.10.0", "cloud-custodian>=0.9.36"],
        "implementation": {
            "scan_schedule": "Harian + event-driven",
            "evidence_chain": "Merkle tree dengan timestamp dari HSM"
        }
    },
    
    # ===== DATA OPERATIONS =====
    "scripts/key_rotation.py": {
        "description": "Automated cryptographic rotation",
        "production_proven": "AWS KMS Rotation",
        "requirements": [
            "Zero-downtime rotation",
            "Pre-rotation validation",
            "Post-rotation integrity check",
            "Rotation audit trail",
            "Key material verification",
            "Key version aliasing",
            "Key health monitoring",
            "Revocation emergency",
            "Dual-layer key wrapping"
        ],
        "dependencies": ["aws-encryption-sdk==2.3.1", "boto3>=1.28.45", "cryptography>=41.0.7"],
        "implementation": {
            "rotation_window": "00:00-04:00 weekend",
            "validation_checks": [
                "Pre-rotation: test encryption/decryption",
                "Post-rotation: data integrity check"
            ]
        }
    },
    
    "scripts/chaos_engineering.py": {
        "description": "Automated resilience testing",
        "production_proven": "Netflix Chaos Automation",
        "requirements": [
            "GameDay scenario templates",
            "Blast radius control",
            "Auto-rollback on critical failure (>5% error)",
            "Failure injection database",
            "Network partition simulation",
            "Stateful service fault injection",
            "Chaos experiment replay",
            "SLO impact forecasting",
            "Experiment versioning",
            "Security chaos scenarios"
        ],
        "dependencies": ["chaostoolkit>=1.17.0", "kubernetes>=29.0.0", "prometheus-client>=0.20.0"],
        "implementation": {
            "scenarios": [
                "AZ outage simulation",
                "200% traffic surge",
                "KMS degradation"
            ],
            "safety_mechanisms": "Auto-rollback berdasarkan SLO violation"
        }
    },
    
    # ===== DEPLOYMENT PIPELINE =====
    "deployments/argocd_apps.yaml": {
        "description": "GitOps continuous delivery",
        "production_proven": "ArgoCD (Intuit)",
        "requirements": [
            "Application health checks",
            "Automated canary analysis",
            "Sync wave sequencing",
            "Drift detection self-heal",
            "Release provenance signing",
            "Resource hook ordering",
            "Application rollback history",
            "Deployment verification hooks",
            "Change approval workflows",
            "Sync status webhooks"
        ],
        "dependencies": ["argocd>=2.10.0", "kustomize>=5.4.0", "helm>=3.14.0"],
        "implementation": {
            "promotion_policy": {
                "staging": "Auto-promote on test pass",
                "production": "Manual approval + auto-rollback"
            },
            "sync_strategy": "Wave-based sequencing dengan hook dependencies"
        }
    },
    
    "deployments/chaos_tests.yaml": {
        "description": "Continuous resilience validation",
        "production_proven": "Gremlin in CI/CD",
        "requirements": [
            "Pre-production failure injection",
            "SLO impact measurement",
            "Automated experiment reports",
            "Steady-state verification",
            "Automatic hypothesis validation",
            "Security chaos testing",
            "Production-safe experimentation",
            "Chaos test versioning",
            "Blast radius visualization",
            "Chaos metrics integration"
        ],
        "dependencies": ["chaosmesh>=2.6.1", "prometheus-client>=0.20.0", "grafana-api>=1.7.0"],
        "implementation": {
            "test_frequency": "Per release + monthly",
            "safety_controls": "Blast radius limitation + auto-abort"
        }
    }
}
