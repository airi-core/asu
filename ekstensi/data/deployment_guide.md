# NDAS_963 Bitcoin Mining Accelerator - Deployment Guide

## Prerequisites

### System Requirements
- **OS**: Linux (Ubuntu 18.04+), Windows 10+, macOS 10.14+
- **CPU**: Multi-core processor (minimum 4 cores recommended)
- **RAM**: Minimum 4GB, recommended 8GB+
- **Compiler**: GCC 7.0+ or Clang 10.0+ with C++17 support

### Required Software
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install build-essential g++ cmake

# CentOS/RHEL
sudo yum groupinstall "Development Tools"
sudo yum install gcc-c++ cmake

# macOS (with Homebrew)
brew install gcc cmake

# Windows (with MinGW-w64)
# Download from: https://www.mingw-w64.org/
```

## Deployment Options

### Option 1: Quick Compile and Run

1. **Save the code** to `ndas_963.cpp`

2. **Compile**:
```bash
g++ -std=c++17 -pthread -O3 -Wall ndas_963.cpp -o ndas_963
```

3. **Run**:
```bash
./ndas_963
```

### Option 2: CMake Build System

Create `CMakeLists.txt`:
```cmake
cmake_minimum_required(VERSION 3.10)
project(NDAS963 VERSION 1.0)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find required packages
find_package(Threads REQUIRED)

# Add executable
add_executable(ndas_963 ndas_963.cpp)

# Link libraries
target_link_libraries(ndas_963 Threads::Threads)

# Compiler-specific options
if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
    target_compile_options(ndas_963 PRIVATE -O3 -Wall -Wextra)
elseif(CMAKE_CXX_COMPILER_ID STREQUAL "Clang")
    target_compile_options(ndas_963 PRIVATE -O3 -Wall -Wextra)
elseif(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
    target_compile_options(ndas_963 PRIVATE /O2 /W3)
endif()
```

Build commands:
```bash
mkdir build && cd build
cmake ..
make -j$(nproc)
./ndas_963
```

### Option 3: Docker Deployment

Create `Dockerfile`:
```dockerfile
FROM ubuntu:20.04

# Install dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    g++ \
    cmake \
    && rm -rf /var/lib/apt/lists/*

# Copy source code
COPY ndas_963.cpp /app/
WORKDIR /app

# Compile
RUN g++ -std=c++17 -pthread -O3 ndas_963.cpp -o ndas_963

# Run
CMD ["./ndas_963"]
```

Docker commands:
```bash
docker build -t ndas_963 .
docker run -it ndas_963
```

## Performance Tuning

### Compiler Optimizations
```bash
# Maximum optimization
g++ -std=c++17 -pthread -O3 -march=native -mtune=native -flto ndas_963.cpp -o ndas_963

# Debug build
g++ -std=c++17 -pthread -g -DDEBUG ndas_963.cpp -o ndas_963_debug
```

### Runtime Configuration
Modify constants in code for different configurations:
```cpp
// In NDASConfig class
static const int NDAS_CORE_COUNT = 963;     // Total cores
static const int CLUSTER_SIZE = 321;        // Cores per cluster  
static const int NUM_CLUSTERS = 3;          // Number of clusters
static const int MAX_TEMP_THRESHOLD = 85;   // Temperature limit
```

## Production Deployment

### 1. System Service (Linux)

Create `/etc/systemd/system/ndas_963.service`:
```ini
[Unit]
Description=NDAS_963 Bitcoin Mining Service
After=network.target

[Service]
Type=simple
User=miner
WorkingDirectory=/opt/ndas_963
ExecStart=/opt/ndas_963/ndas_963
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable ndas_963
sudo systemctl start ndas_963
sudo systemctl status ndas_963
```

### 2. Process Management with PM2 (Node.js)
```bash
npm install -g pm2
pm2 start ndas_963 --name "mining_system"
pm2 startup
pm2 save
```

### 3. Monitoring Setup
```bash
# Install monitoring tools
sudo apt install htop iotop nethogs

# Monitor during runtime
htop                    # CPU/Memory usage
sudo iotop             # Disk I/O
nethogs                # Network usage
```

## Integration with IBM Systems

### API Integration Points
```cpp
// Add these methods to NDAS963System class
class NDAS963System {
public:
    // REST API endpoints
    std::string getStatusJSON() const;
    bool setMiningParameters(const std::string& json_config);
    std::string getMetricsJSON() const;
    
    // IBM Watson IoT Platform integration
    void sendTelemetryData();
    void receiveMiningCommands();
};
```

### Configuration Files
Create `config.json`:
```json
{
    "mining": {
        "cores": 963,
        "clusters": 3,
        "max_temperature": 85,
        "power_limit": 2500
    },
    "network": {
        "pool_url": "stratum+tcp://pool.example.com:4444",
        "wallet_address": "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2"
    },
    "monitoring": {
        "telemetry_interval": 30,
        "log_level": "INFO"
    }
}
```

## Troubleshooting

### Common Issues

1. **Compilation Errors**:
```bash
# Missing C++17 support
g++ --version  # Check GCC version >= 7.0

# Missing pthread
sudo apt install libpthread-stubs0-dev
```

2. **Runtime Issues**:
```bash
# Check available cores
nproc

# Monitor resource usage
top -H -p $(pidof ndas_963)
```

3. **Performance Issues**:
```bash
# Increase thread priority
sudo nice -n -20 ./ndas_963

# CPU affinity setting
taskset -c 0-15 ./ndas_963
```

### Log Analysis
```bash
# Run with logging
./ndas_963 2>&1 | tee mining.log

# Monitor log in real-time
tail -f mining.log

# Analyze performance
grep "Hash Count" mining.log | tail -20
```

## Security Considerations

### 1. User Permissions
```bash
# Create dedicated mining user
sudo useradd -r -s /bin/false miner
sudo chown -R miner:miner /opt/ndas_963
```

### 2. Firewall Configuration
```bash
# Allow only necessary ports
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 4444/tcp  # Mining pool
```

### 3. Resource Limits
Edit `/etc/security/limits.conf`:
```
miner soft nproc 65536
miner hard nproc 65536
miner soft nofile 65536
miner hard nofile 65536
```

## IBM Integration Checklist

- [ ] Code compiles without warnings
- [ ] All 963 cores operational
- [ ] Temperature monitoring functional  
- [ ] Hash rate reporting accurate
- [ ] Multi-threading stable
- [ ] Memory usage optimized
- [ ] Error handling implemented
- [ ] Logging system active
- [ ] Configuration management ready
- [ ] Documentation complete

## Support and Maintenance

### Regular Maintenance Tasks
```bash
# Weekly system health check
./ndas_963 --self-test

# Monthly performance analysis  
./ndas_963 --benchmark

# Log rotation
logrotate /etc/logrotate.d/ndas_963
```

### Update Procedure
```bash
# Backup current version
cp ndas_963 ndas_963.backup

# Compile new version
g++ -std=c++17 -pthread -O3 ndas_963_v2.cpp -o ndas_963_new

# Test new version
./ndas_963_new --test-mode

# Deploy if tests pass
mv ndas_963_new ndas_963
systemctl restart ndas_963
```
