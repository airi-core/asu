// ========================================
// REPRESENTASI 16 YOTTABYTE DALAM JAVASCRIPT
// ========================================

// 1. MENGGUNAKAN BigInt (Rekomendasi untuk angka besar)
const yottabyteInBytes = 16n * (10n ** 24n);
console.log("16 Yottabyte (BigInt):", yottabyteInBytes.toString());
console.log("Panjang digit:", yottabyteInBytes.toString().length);

// 2. MENGGUNAKAN Number (Terbatas akurasi untuk angka sangat besar)
const yottabyteNumber = 16 * Math.pow(10, 24);
console.log("16 Yottabyte (Number):", yottabyteNumber);
console.log("Dalam notasi ilmiah:", yottabyteNumber.toExponential());

// 3. MENGGUNAKAN String untuk representasi tepat
const yottabyteString = "16000000000000000000000000"; // 16 + 24 nol
console.log("16 Yottabyte (String):", yottabyteString);

// ========================================
// KONSTANTA UNIT PENYIMPANAN
// ========================================

const STORAGE_UNITS = {
    BYTE: 1n,
    KILOBYTE: 1000n,
    MEGABYTE: 1000n ** 2n,
    GIGABYTE: 1000n ** 3n,
    TERABYTE: 1000n ** 4n,
    PETABYTE: 1000n ** 5n,
    EXABYTE: 1000n ** 6n,
    ZETTABYTE: 1000n ** 7n,
    YOTTABYTE: 1000n ** 8n
};

// Alternatif binary (1024 basis)
const BINARY_UNITS = {
    BYTE: 1n,
    KIBIBYTE: 1024n,
    MEBIBYTE: 1024n ** 2n,
    GIBIBYTE: 1024n ** 3n,
    TEBIBYTE: 1024n ** 4n,
    PEBIBYTE: 1024n ** 5n,
    EXBIBYTE: 1024n ** 6n,
    ZEBIBYTE: 1024n ** 7n,
    YOBIBYTE: 1024n ** 8n
};

// ========================================
// FUNGSI KONVERSI BYTE
// ========================================

function convertBytes(bytes, unit = 'auto') {
    const bytesBI = BigInt(bytes);
    
    if (unit === 'auto') {
        // Auto-detect unit terbaik
        if (bytesBI >= STORAGE_UNITS.YOTTABYTE) {
            return {
                value: Number(bytesBI / STORAGE_UNITS.YOTTABYTE),
                unit: 'YB',
                exact: `${bytesBI / STORAGE_UNITS.YOTTABYTE} YB`
            };
        } else if (bytesBI >= STORAGE_UNITS.ZETTABYTE) {
            return {
                value: Number(bytesBI / STORAGE_UNITS.ZETTABYTE),
                unit: 'ZB',
                exact: `${bytesBI / STORAGE_UNITS.ZETTABYTE} ZB`
            };
        }
        // ... dst untuk unit lainnya
    }
    
    const unitValue = STORAGE_UNITS[unit.toUpperCase()] || STORAGE_UNITS.BYTE;
    return {
        value: Number(bytesBI / unitValue),
        unit: unit,
        exact: `${bytesBI / unitValue} ${unit}`
    };
}

// ========================================
// CLASS UNTUK MENGELOLA STORAGE SIZE
// ========================================

class StorageSize {
    constructor(value, unit = 'BYTE') {
        this.bytes = BigInt(value) * (STORAGE_UNITS[unit.toUpperCase()] || 1n);
    }
    
    // Getter untuk berbagai unit
    get bytes() { return this._bytes; }
    set bytes(value) { this._bytes = BigInt(value); }
    
    get kilobytes() { return this.bytes / STORAGE_UNITS.KILOBYTE; }
    get megabytes() { return this.bytes / STORAGE_UNITS.MEGABYTE; }
    get gigabytes() { return this.bytes / STORAGE_UNITS.GIGABYTE; }
    get terabytes() { return this.bytes / STORAGE_UNITS.TERABYTE; }
    get petabytes() { return this.bytes / STORAGE_UNITS.PETABYTE; }
    get exabytes() { return this.bytes / STORAGE_UNITS.EXABYTE; }
    get zettabytes() { return this.bytes / STORAGE_UNITS.ZETTABYTE; }
    get yottabytes() { return this.bytes / STORAGE_UNITS.YOTTABYTE; }
    
    // Metode untuk formatting
    toString() {
        return this.bytes.toString() + ' bytes';
    }
    
    toHumanReadable() {
        const units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
        let size = Number(this.bytes);
        let unitIndex = 0;
        
        while (size >= 1000 && unitIndex < units.length - 1) {
            size /= 1000;
            unitIndex++;
        }
        
        return `${size.toFixed(2)} ${units[unitIndex]}`;
    }
}

// ========================================
// CONTOH PENGGUNAAN
// ========================================

// Membuat instance 16 Yottabyte
const sixteenYB = new StorageSize(16, 'YOTTABYTE');

console.log("\n=== REPRESENTASI 16 YOTTABYTE ===");
console.log("Dalam bytes:", sixteenYB.toString());
console.log("Human readable:", sixteenYB.toHumanReadable());
console.log("Dalam Zettabytes:", sixteenYB.zettabytes.toString(), "ZB");
console.log("Dalam Exabytes:", sixteenYB.exabytes.toString(), "EB");

// ========================================
// FUNGSI UTILITY UNTUK OPERASI BYTE
// ========================================

function addStorage(size1, size2) {
    return size1.bytes + size2.bytes;
}

function compareStorage(size1, size2) {
    if (size1.bytes > size2.bytes) return 1;
    if (size1.bytes < size2.bytes) return -1;
    return 0;
}

function formatBytes(bytes) {
    const bytesBI = BigInt(bytes);
    const units = [
        { name: 'YB', value: STORAGE_UNITS.YOTTABYTE },
        { name: 'ZB', value: STORAGE_UNITS.ZETTABYTE },
        { name: 'EB', value: STORAGE_UNITS.EXABYTE },
        { name: 'PB', value: STORAGE_UNITS.PETABYTE },
        { name: 'TB', value: STORAGE_UNITS.TERABYTE },
        { name: 'GB', value: STORAGE_UNITS.GIGABYTE },
        { name: 'MB', value: STORAGE_UNITS.MEGABYTE },
        { name: 'KB', value: STORAGE_UNITS.KILOBYTE },
        { name: 'B', value: STORAGE_UNITS.BYTE }
    ];
    
    for (const unit of units) {
        if (bytesBI >= unit.value) {
            const value = bytesBI / unit.value;
            return `${value} ${unit.name}`;
        }
    }
    
    return `${bytesBI} B`;
}

// ========================================
// VALIDASI DAN ERROR HANDLING
// ========================================

function validateStorageInput(value, unit) {
    try {
        const numValue = BigInt(value);
        if (numValue < 0n) {
            throw new Error("Storage size tidak boleh negatif");
        }
        
        if (!STORAGE_UNITS[unit.toUpperCase()]) {
            throw new Error(`Unit '${unit}' tidak dikenali`);
        }
        
        return true;
    } catch (error) {
        console.error("Error validasi:", error.message);
        return false;
    }
}

// ========================================
// DEMO PERHITUNGAN
// ========================================

console.log("\n=== DEMO PERHITUNGAN ===");

// Contoh perhitungan kapasitas
const oneYB = new StorageSize(1, 'YOTTABYTE');
const sixteenYB_calc = new StorageSize(16, 'YOTTABYTE');

console.log("1 Yottabyte =", formatBytes(oneYB.bytes));
console.log("16 Yottabyte =", formatBytes(sixteenYB_calc.bytes));

// Perbandingan dengan data real
const currentInternet = new StorageSize(120, 'ZETTABYTE'); // Estimasi data internet 2023
const ratio = sixteenYB_calc.bytes / currentInternet.bytes;
console.log(`16 YB adalah ${ratio}x lebih besar dari seluruh internet`);

// ========================================
// LIMITASI JAVASCRIPT
// ========================================

console.log("\n=== LIMITASI JAVASCRIPT ===");
console.log("Number.MAX_SAFE_INTEGER:", Number.MAX_SAFE_INTEGER);
console.log("16 YB lebih besar dari MAX_SAFE_INTEGER:", 
           sixteenYB.bytes > BigInt(Number.MAX_SAFE_INTEGER));
console.log("Gunakan BigInt untuk akurasi penuh!");

// Export untuk penggunaan module
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        StorageSize,
        STORAGE_UNITS,
        BINARY_UNITS,
        convertBytes,
        formatBytes,
        validateStorageInput
    };
}