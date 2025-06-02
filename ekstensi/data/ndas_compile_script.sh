#!/bin/bash
# Script kompilasi untuk NDAS_963 Mining System

echo "=== NDAS_963 Compilation Script ==="
echo "Preparing compilation environment..."

# Check if numa is available
if ! ldconfig -p | grep -q libnuma; then
    echo "ERROR: libnuma tidak ditemukan. Install dengan:"
    echo "Ubuntu/Debian: sudo apt install libnuma-dev"
    echo "RHEL/CentOS: sudo yum install numactl-devel"
    exit 1
fi

# Create build directory
mkdir -p build
cd build

# Compile dengan optimasi maksimal
echo "Compiling NDAS_963 with maximum optimization..."

g++ -std=c++17 \
    -O3 \
    -march=native \
    -mtune=native \
    -funroll-loops \
    -ffast-math \
    -flto \
    -DNDEBUG \
    -pthread \
    -lnuma \
    -o ndas_963 \
    ../ndas_963_fixed.txt

if [ $? -eq 0 ]; then
    echo "✅ Kompilasi berhasil!"
    echo "Executable: ./build/ndas_963"
    
    # Set permissions
    chmod +x ndas_963
    
    # Show file info
    echo ""
    echo "=== Binary Information ==="
    ls -la ndas_963
    file ndas_963
    ldd ndas_963
else
    echo "❌ Kompilasi gagal!"
    exit 1
fi

echo ""
echo "=== Persiapan Deployment ==="
echo "1. Pastikan sistem memiliki akses root"
echo "2. Validasi hardware PCIe tersedia"
echo "3. Monitor suhu sistem selama operasi"
echo "4. Siapkan sistem cooling yang memadai"