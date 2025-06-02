# ASU Container System: Transformasi Paradigmatik Container-Based Git Repository Management

## Metadata Proyek
- **Nama:** Susanto
- **NIM:** 206181  
- **Universitas:** Hidden Investor
- **Pembimbing:** Suwardjono
- **Rektor:** Martin

---

## Abstraksi Filosofis: Dari Binary ke Dynamic Ecosystem

Proyek ASU Container System merepresentasikan evolusi conceptual dalam domain containerization technology, di mana traditional static storage bertransformasi menjadi dynamic, executable ecosystem. Sistem ini tidak sekadar menyimpan repository Git, namun menciptakan isolated execution environment yang memungkinkan kode untuk "hidup" dalam sandbox yang aman dan terkontrol.

### Paradigma Arsitektural: Container-as-a-Service Philosophy

Dalam konsepsi mendalam, ASU Container System mengadopsi philosophical approach yang memandang setiap Git repository sebagai **living entity** yang dapat diinstansiasi, dieksekusi, dan dikelola dalam lingkungan yang completely isolated. Pendekatan ini mentransendensikan batasan konvensional static file storage menuju dynamic computational environment.

---

## Arsitektur Sistem: Structural Intelligence

### Core Components Hierarchy

```
ASU Container System
├── API Gateway Layer (Express.js + Security Middleware)
├── Container Management Engine
│   ├── Git Repository Cloning Service
│   ├── Archive Compression Engine (.asu format)
│   └── Metadata Management System
├── Sandboxed Execution Environment
│   ├── Command Sanitization Engine
│   ├── Resource Isolation Layer
│   └── Security Validation Framework
└── Storage Management System
    ├── Hash-based Identification (SHA256)
    ├── File System Abstraction
    └── Lifecycle Management
```

### Technological Philosophy: Security-First Architecture

Setiap aspek dari sistem ini dibangun dengan **security-centric mindset**, di mana setiap input validation, command execution, dan resource access melalui multiple layers of verification dan sanitization. Pendekatan ini tidak hanya melindungi sistem dari potensi malicious attacks, namun juga menciptakan trustworthy environment untuk execution berbagai kode dari external repositories.

---

## Prerequisites: Environmental Dependencies

### System Requirements
- **Node.js**: >= 18.0.0 (untuk native ES6+ support dan performance optimization)
- **NPM**: >= 8.0.0 (untuk modern package management)
- **Git**: >= 2.30.0 (untuk repository cloning capabilities)
- **Operating System**: Linux/macOS (direkomendasikan untuk optimal security)
- **Available Storage**: Minimum 10GB (untuk container storage)
- **Memory**: Minimum 4GB RAM (untuk concurrent container execution)

### Optional Dependencies
- **Docker**: >= 20.10.0 (untuk advanced containerization)
- **PM2**: Untuk production process management
- **Nginx**: Untuk reverse proxy dan load balancing

---

## Installation Guide: Step-by-Step Implementation

### 1. Repository Initialization
```bash
# Clone project repository
git clone <your-repository-url>
cd asu-container-system

# Install dependencies
npm install

# Verify installation
npm run test
```

### 2. Environment Configuration
```bash
# Create environment configuration
cp .env.example .env

# Edit configuration (optional)
nano .env
```

### 3. Directory Structure Preparation
```bash
# Create storage directory
mkdir -p storage

# Set appropriate permissions (Linux/macOS)
chmod 755 storage
```

### 4. Development Server Launch
```bash
# Development mode dengan hot-reload
npm run dev

# Production mode
npm start
```

### 5. Docker Deployment (Recommended)
```bash
# Build Docker image
npm run docker:build

# Run container
npm run docker:run
```

---

## API Documentation: RESTful Interface Specification

### Base URL
```
http://localhost:3000/api
```

### Authentication
Currently implementing **open access** untuk development phase. Production deployment akan mengintegrasikan **JWT-based authentication** dan **role-based access control**.

### Endpoint Specifications

#### 1. Create Container
**POST** `/containers`

**Philosophical Context**: Mentransformasi Git repository menjadi executable container entity.

**Request Body**:
```json
{
  "gitUrl": "https://github.com/example/repository.git"
}
```

**Response Success (201)**:
```json
{
  "success": true,
  "data": {
    "id": "a1b2c3d4e5f6789...",
    "gitUrl": "https://github.com/example/repository.git",
    "created": "2025-05-28T10:30:00.000Z",
    "size": 15728640
  }
}
```

**Security Validations**:
- URL format validation menggunakan `validator.js`
- Git repository accessibility verification
- Malicious URL pattern detection
- Size limitation enforcement (max 1TB)

#### 2. Container Information Retrieval
**GET** `/containers/{id}`

**Philosophical Context**: Mengeksplorasi metadata dan characteristics dari container entity.

**Response Success (200)**:
```json
{
  "success": true,
  "data": {
    "id": "a1b2c3d4e5f6789...",
    "gitUrl": "https://github.com/example/repository.git",
    "created": "2025-05-28T10:30:00.000Z",
    "size": 15728640,
    "path": "/storage/a1b2c3d4e5f6789....asu"
  }
}
```

#### 3. Sandboxed Command Execution
**POST** `/containers/{id}/execute`

**Philosophical Context**: Memberikan "kehidupan" kepada kode dalam isolated, secure environment.

**Request Body**:
```json
{
  "command": "node",
  "args": ["--version"],
  "timeout": 30000
}
```

**Response Success (200)**:
```json
{
  "success": true,
  "data": {
    "exitCode": 0,
    "stdout": "v18.17.0",
    "stderr": "",
    "executedAt": "2025-05-28T10:35:00.000Z"
  }
}
```

**Security Features**:
- Command blacklisting untuk dangerous operations
- Argument sanitization
- Execution timeout protection
- Output size limitation
- Environment variable restriction

#### 4. Container Lifecycle Management
**DELETE** `/containers/{id}`

**Philosophical Context**: Graceful termination dan cleanup dari container entity.

**Response Success (200)**:
```json
{
  "success": true,
  "message": "Container berhasil dihapus"
}
```

#### 5. Container Inventory
**GET** `/containers`

**Response Success (200)**:
```json
{
  "success": true,
  "data": {
    "containers": [...],
    "total": 5
  }
}
```

---

## Security Architecture: Defense-in-Depth Strategy

### Multi-Layer Security Implementation

#### 1. Input Validation Layer
- **URL Sanitization**: Comprehensive validation untuk Git URLs
- **Command Sanitization**: Blacklist-based filtering untuk malicious commands
- **Argument Validation**: Type checking dan dangerous character removal

#### 2. Execution Isolation Layer
- **Sandboxed Environment**: Restricted environment variables
- **Resource Limitations**: Memory, CPU, dan disk usage limits
- **Network Isolation**: Limited network access untuk executed commands

#### 3. File System Security
- **Temporary Directory Isolation**: Setiap execution menggunakan isolated temp directory
- **Automatic Cleanup**: Guaranteed cleanup setelah execution completion
- **Path Traversal Prevention**: Strict path validation

#### 4. Application Security
- **Rate Limiting**: Request throttling untuk DoS protection
- **Helmet.js**: Security headers untuk web vulnerabilities
- **Error Handling**: Secure error messages tanpa information disclosure

### Threat Model Mitigation

#### Command Injection Prevention
```javascript
// Blacklisted commands
const blacklistedCommands = [
  'rm', 'del', 'sudo', 'wget', 'curl', 
  'ssh', 'kill', 'mount', 'dd'
];

// Argument sanitization
const dangerous = /[;&|`$(){}[\]<>]/;
if (dangerous.test(arg)) {
  throw new Error('Dangerous characters detected');
}
```

#### Resource Exhaustion Protection
- Maximum container size: 1TB
- Execution timeout: 30 seconds (configurable