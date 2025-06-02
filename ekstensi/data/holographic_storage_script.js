/**
 * SIMULASI HOLOGRAPHIC STORAGE - PEREKAMAN PARALEL
 * Implementasi algoritma untuk sistem penyimpanan hologram dengan pemrosesan paralel
 * 
 * Dibuat untuk tugas kampus - Teknologi Penyimpanan Data
 * Mengimplementasikan konsep dari paper holographic storage
 */

// =================================================================
// KELAS UTAMA UNTUK MEDIUM PENYIMPANAN HOLOGRAM
// =================================================================
class HolographicMedium {
    constructor(dimensions = { width: 10, height: 10, depth: 2 }) {
        this.dimensions = dimensions; // Dimensi dalam mm
        this.volume = dimensions.width * dimensions.height * dimensions.depth; // Volume dalam mm³
        this.refractiveIndex = 2.3; // Indeks bias LiNbO₃
        this.wavelength = 532e-6; // Panjang gelombang laser (532 nm dalam mm)
        this.deltaRefractiveIndex = 1e-4; // Perubahan indeks bias
        this.hologramDatabase = new Map(); // Database hologram tersimpan
        this.maxCapacity = this.calculateTheoreticalCapacity();
        
        console.log(`[MEDIUM] Inisialisasi medium hologram:`);
        console.log(`- Dimensi: ${dimensions.width}×${dimensions.height}×${dimensions.depth} mm`);
        console.log(`- Volume: ${this.volume} mm³`);
        console.log(`- Kapasitas teoritis: ${(this.maxCapacity / 1e9).toFixed(2)} GB`);
    }

    /**
     * Menghitung kapasitas teoritis berdasarkan formula dari paper
     * C = (V × λ³) / (8π × n³ × Δn)
     */
    calculateTheoreticalCapacity() {
        const volumeM3 = this.volume * 1e-9; // Konversi mm³ ke m³
        const wavelengthM = this.wavelength * 1e-3; // Konversi mm ke m
        
        const capacity = (volumeM3 * Math.pow(wavelengthM, 3)) / 
                        (8 * Math.PI * Math.pow(this.refractiveIndex, 3) * this.deltaRefractiveIndex);
        
        return capacity; // dalam bit
    }

    /**
     * Menyimpan hologram ke dalam medium
     */
    storeHologram(hologramId, hologramData) {
        if (this.hologramDatabase.size >= this.getMaxHolograms()) {
            throw new Error('Medium penyimpanan penuh!');
        }
        
        this.hologramDatabase.set(hologramId, {
            data: hologramData,
            timestamp: Date.now(),
            position: this.calculateOptimalPosition(hologramId),
            interferencePattern: this.generateInterferencePattern(hologramData)
        });
        
        return true;
    }

    /**
     * Menghitung posisi optimal untuk hologram baru
     */
    calculateOptimalPosition(hologramId) {
        const totalSlots = this.getMaxHolograms();
        const slotIndex = this.hologramDatabase.size;
        
        // Distribusi spasial dalam 3D
        const x = (slotIndex % 10) * (this.dimensions.width / 10);
        const y = Math.floor(slotIndex / 10) % 10 * (this.dimensions.height / 10);
        const z = Math.floor(slotIndex / 100) * (this.dimensions.depth / Math.ceil(totalSlots / 100));
        
        return { x, y, z };
    }

    /**
     * Generate pola interferensi untuk hologram
     */
    generateInterferencePattern(data) {
        // Simulasi pola interferensi berdasarkan data
        const pattern = [];
        const dataHash = this.simpleHash(JSON.stringify(data));
        
        for (let i = 0; i < 100; i++) {
            // Simulasi gelombang referensi dan objek
            const referenceWave = Math.sin(i * 0.1 + dataHash);
            const objectWave = Math.cos(i * 0.15 + dataHash * 0.7);
            const interference = (referenceWave + objectWave) / 2;
            pattern.push(interference);
        }
        
        return pattern;
    }

    /**
     * Hash sederhana untuk data
     */
    simpleHash(str) {
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            const char = str.charCodeAt(i);
            hash = ((hash << 5) - hash) + char;
            hash = hash & hash; // Konversi ke 32bit integer
        }
        return Math.abs(hash) / 1000000;
    }

    getMaxHolograms() {
        return Math.floor(this.maxCapacity / (1024 * 8)); // Asumsi 1KB per hologram
    }

    getStorageStatus() {
        return {
            used: this.hologramDatabase.size,
            total: this.getMaxHolograms(),
            utilizationPercent: (this.hologramDatabase.size / this.getMaxHolograms() * 100).toFixed(2)
        };
    }
}

// =================================================================
// KELAS UNTUK SIMULASI LASER DAN OPTICAL SYSTEM
// =================================================================
class OpticalSystem {
    constructor() {
        this.laserPower = 10; // mW
        this.wavelength = 532; // nm
        this.beamDiameter = 2; // mm
        this.stability = 0.99; // 99% stability
        this.multiplexingTechnique = 'angular';
        
        console.log(`[OPTICAL] Sistem optik diinisialisasi:`);
        console.log(`- Daya laser: ${this.laserPower} mW`);
        console.log(`- Panjang gelombang: ${this.wavelength} nm`);
        console.log(`- Stabilitas: ${(this.stability * 100).toFixed(1)}%`);
    }

    /**
     * Simulasi proses perekaman dengan laser
     */
    recordHologram(pageData, multiplexingAngle = 0) {
        const recordingTime = this.calculateRecordingTime(pageData.size);
        const laserEnergy = this.calculateRequiredEnergy(pageData.size);
        const interferenceQuality = this.calculateInterferenceQuality(multiplexingAngle);
        
        // Simulasi proses perekaman
        const recordingResult = {
            success: interferenceQuality > 0.8,
            recordingTime: recordingTime,
            energyUsed: laserEnergy,
            quality: interferenceQuality,
            multiplexingAngle: multiplexingAngle,
            timestamp: Date.now()
        };
        
        console.log(`[OPTICAL] Perekaman hologram:`);
        console.log(`- Waktu: ${recordingTime.toFixed(2)} ms`);
        console.log(`- Energi: ${laserEnergy.toFixed(3)} mJ`);
        console.log(`- Kualitas: ${(interferenceQuality * 100).toFixed(1)}%`);
        console.log(`- Status: ${recordingResult.success ? 'BERHASIL' : 'GAGAL'}`);
        
        return recordingResult;
    }

    /**
     * Hitung waktu perekaman berdasarkan ukuran data
     */
    calculateRecordingTime(dataSize) {
        // Base time 100ms, tambahan 10ms per KB
        const baseTime = 100;
        const additionalTime = (dataSize / 1024) * 10;
        return baseTime + additionalTime;
    }

    /**
     * Hitung energi laser yang diperlukan
     */
    calculateRequiredEnergy(dataSize) {
        // Energi = Daya × Waktu
        const recordingTime = this.calculateRecordingTime(dataSize) / 1000; // konversi ke detik
        return this.laserPower * recordingTime;
    }

    /**
     * Hitung kualitas interferensi berdasarkan sudut multiplexing
     */
    calculateInterferenceQuality(angle) {
        // Kualitas menurun dengan sudut yang lebih besar
        const optimalAngle = 15; // derajat
        const angleDifference = Math.abs(angle - optimalAngle);
        const qualityReduction = angleDifference * 0.02;
        return Math.max(0.5, this.stability - qualityReduction);
    }

    /**
     * Set teknik multiplexing
     */
    setMultiplexingTechnique(technique) {
        const validTechniques = ['angular', 'wavelength', 'shift', 'hybrid'];
        if (validTechniques.includes(technique)) {
            this.multiplexingTechnique = technique;
            console.log(`[OPTICAL] Multiplexing diatur ke: ${technique}`);
        } else {
            console.error(`[OPTICAL] Teknik multiplexing tidak valid: ${technique}`);
        }
    }
}

// =================================================================
// KELAS UNTUK PEMROSESAN PARALEL
// =================================================================
class ParallelProcessor {
    constructor(threadCount = 4) {
        this.threadCount = threadCount;
        this.activeThreads = [];
        this.completedTasks = [];
        this.totalTasksProcessed = 0;
        this.startTime = null;
        
        console.log(`[PARALLEL] Processor paralel diinisialisasi dengan ${threadCount} thread`);
    }

    /**
     * Memproses daftar halaman secara paralel
     */
    async processPages(pages, opticalSystem, medium) {
        this.startTime = Date.now();
        console.log(`[PARALLEL] Memulai pemrosesan ${pages.length} halaman dengan ${this.threadCount} thread`);
        
        // Bagi halaman ke dalam batch untuk setiap thread
        const batches = this.createBatches(pages, this.threadCount);
        const promises = [];
        
        // Buat promise untuk setiap thread
        for (let threadId = 0; threadId < batches.length; threadId++) {
            const batch = batches[threadId];
            if (batch.length > 0) {
                promises.push(this.processThread(threadId, batch, opticalSystem, medium));
            }
        }
        
        // Tunggu semua thread selesai
        const results = await Promise.all(promises);
        
        // Compile hasil
        const finalResult = this.compileResults(results);
        console.log(`[PARALLEL] Pemrosesan selesai dalam ${finalResult.totalTime} ms`);
        
        return finalResult;
    }

    /**
     * Membagi halaman ke dalam batch untuk pemrosesan paralel
     */
    createBatches(pages, threadCount) {
        const batches = Array.from({ length: threadCount }, () => []);
        
        pages.forEach((page, index) => {
            const threadIndex = index % threadCount;
            batches[threadIndex].push(page);
        });
        
        return batches;
    }

    /**
     * Memproses satu thread
     */
    async processThread(threadId, pages, opticalSystem, medium) {
        console.log(`[THREAD-${threadId}] Memproses ${pages.length} halaman`);
        
        const threadResults = {
            threadId: threadId,
            processedPages: [],
            errors: [],
            totalTime: 0,
            startTime: Date.now()
        };

        for (let i = 0; i < pages.length; i++) {
            const page = pages[i];
            try {
                // Simulasi perekaman hologram
                const multiplexingAngle = this.calculateMultiplexingAngle(threadId, i);
                const recordingResult = opticalSystem.recordHologram(page, multiplexingAngle);
                
                if (recordingResult.success) {
                    // Simpan ke medium
                    const hologramId = `thread${threadId}_page${i}_${Date.now()}`;
                    medium.storeHologram(hologramId, {
                        pageId: page.id,
                        data: page.data,
                        size: page.size,
                        threadId: threadId,
                        recordingResult: recordingResult
                    });
                    
                    threadResults.processedPages.push({
                        pageId: page.id,
                        hologramId: hologramId,
                        recordingTime: recordingResult.recordingTime,
                        quality: recordingResult.quality
                    });
                    
                    console.log(`[THREAD-${threadId}] Halaman ${page.id} berhasil diproses`);
                } else {
                    throw new Error(`Perekaman gagal untuk halaman ${page.id}`);
                }
                
                // Simulasi waktu pemrosesan
                await this.delay(recordingResult.recordingTime);
                
            } catch (error) {
                console.error(`[THREAD-${threadId}] Error pada halaman ${page.id}: ${error.message}`);
                threadResults.errors.push({
                    pageId: page.id,
                    error: error.message
                });
            }
        }
        
        threadResults.totalTime = Date.now() - threadResults.startTime;
        console.log(`[THREAD-${threadId}] Selesai dalam ${threadResults.totalTime} ms`);
        
        return threadResults;
    }

    /**
     * Hitung sudut multiplexing untuk thread dan halaman tertentu
     */
    calculateMultiplexingAngle(threadId, pageIndex) {
        // Distribusi sudut untuk menghindari interferensi antar hologram
        const baseAngle = 10; // derajat
        const threadOffset = threadId * 5;
        const pageOffset = pageIndex * 0.5;
        return baseAngle + threadOffset + pageOffset;
    }

    /**
     * Compile hasil dari semua thread
     */
    compileResults(threadResults) {
        const totalTime = Date.now() - this.startTime;
        let totalProcessed = 0;
        let totalErrors = 0;
        let totalRecordingTime = 0;
        let averageQuality = 0;
        
        threadResults.forEach(result => {
            totalProcessed += result.processedPages.length;
            totalErrors += result.errors.length;
            
            result.processedPages.forEach(page => {
                totalRecordingTime += page.recordingTime;
                averageQuality += page.quality;
            });
        });
        
        if (totalProcessed > 0) {
            averageQuality = averageQuality / totalProcessed;
        }
        
        const throughput = (totalProcessed / totalTime) * 1000; // halaman per detik
        const parallelEfficiency = this.calculateParallelEfficiency(threadResults);
        
        return {
            totalTime: totalTime,
            totalProcessed: totalProcessed,
            totalErrors: totalErrors,
            throughput: throughput,
            averageQuality: averageQuality,
            parallelEfficiency: parallelEfficiency,
            threadResults: threadResults
        };
    }

    /**
     * Hitung efisiensi paralel
     */
    calculateParallelEfficiency(threadResults) {
        if (threadResults.length === 0) return 0;
        
        // Waktu thread terlama
        const maxThreadTime = Math.max(...threadResults.map(r => r.totalTime));
        
        // Total waktu jika diproses serial
        const totalSerialTime = threadResults.reduce((sum, r) => sum + r.totalTime, 0);
        
        // Speedup aktual
        const actualSpeedup = totalSerialTime / maxThreadTime;
        
        // Speedup teoritis
        const theoreticalSpeedup = this.threadCount;
        
        // Efisiensi = Speedup aktual / Speedup teoritis
        return (actualSpeedup / theoreticalSpeedup) * 100;
    }

    /**
     * Utility function untuk delay
     */
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

// =================================================================
// KELAS UTAMA UNTUK SIMULASI HOLOGRAPHIC STORAGE
// =================================================================
class HolographicStorageSystem {
    constructor(config = {}) {
        this.medium = new HolographicMedium(config.mediumDimensions);
        this.opticalSystem = new OpticalSystem();
        this.parallelProcessor = new ParallelProcessor(config.threadCount || 4);
        
        // Statistik sistem
        this.stats = {
            totalPagesRecorded: 0,
            totalDataStored: 0, // dalam bytes
            totalRecordingTime: 0,
            averageQuality: 0,
            errorRate: 0
        };
        
        console.log(`[SYSTEM] Holographic Storage System diinisialisasi`);
        console.log(`[SYSTEM] Konfigurasi: ${JSON.stringify(config, null, 2)}`);
    }

    /**
     * Simulasi perekaman batch halaman data
     */
    async recordPages(pagesData) {
        console.log(`\n[SYSTEM] === MEMULAI PEREKAMAN ${pagesData.length} HALAMAN ===`);
        
        const startTime = Date.now();
        
        try {
            // Proses paralel
            const result = await this.parallelProcessor.processPages(
                pagesData, 
                this.opticalSystem, 
                this.medium
            );
            
            // Update statistik sistem
            this.updateSystemStats(result);
            
            console.log(`\n[SYSTEM] === PEREKAMAN SELESAI ===`);
            this.printFinalReport(result);
            
            return result;
            
        } catch (error) {
            console.error(`[SYSTEM] Error dalam perekaman: ${error.message}`);
            throw error;
        }
    }

    /**
     * Update statistik sistem
     */
    updateSystemStats(result) {
        this.stats.totalPagesRecorded += result.totalProcessed;
        this.stats.totalRecordingTime += result.totalTime;
        this.stats.averageQuality = result.averageQuality;
        this.stats.errorRate = (result.totalErrors / (result.totalProcessed + result.totalErrors)) * 100;
        
        // Hitung total data yang disimpan
        const storageStatus = this.medium.getStorageStatus();
        this.stats.totalDataStored = storageStatus.used * 1024; // asumsi 1KB per hologram
    }

    /**
     * Cetak laporan akhir
     */
    printFinalReport(result) {
        console.log(`\n[REPORT] === LAPORAN AKHIR PEREKAMAN ===`);
        console.log(`- Total halaman diproses: ${result.totalProcessed}`);
        console.log(`- Total waktu: ${result.totalTime} ms`);
        console.log(`- Throughput: ${result.throughput.toFixed(2)} halaman/detik`);
        console.log(`- Kualitas rata-rata: ${(result.averageQuality * 100).toFixed(1)}%`);
        console.log(`- Efisiensi paralel: ${result.parallelEfficiency.toFixed(1)}%`);
        console.log(`- Error rate: ${this.stats.errorRate.toFixed(2)}%`);
        
        const storageStatus = this.medium.getStorageStatus();
        console.log(`- Utilisasi storage: ${storageStatus.utilizationPercent}%`);
        console.log(`- Kapasitas tersisa: ${storageStatus.total - storageStatus.used} hologram`);
    }

    /**
     * Generate data halaman untuk testing
     */
    generateTestPages(count = 16, sizeKB = 512) {
        const pages = [];
        
        for (let i = 0; i < count; i++) {
            pages.push({
                id: `page_${i + 1}`,
                size: sizeKB * 1024, // konversi ke bytes
                data: this.generateRandomData(sizeKB * 1024),
                timestamp: Date.now(),
                checksum: this.calculateChecksum(i)
            });
        }
        
        console.log(`[SYSTEM] Generated ${count} test pages (${sizeKB} KB each)`);
        return pages;
    }

    /**
     * Generate random data untuk testing
     */
    generateRandomData(size) {
        const data = new Array(Math.floor(size / 4));
        for (let i = 0; i < data.length; i++) {
            data[i] = Math.floor(Math.random() * 256);
        }
        return data;
    }

    /**
     * Hitung checksum sederhana
     */
    calculateChecksum(pageId) {
        return (pageId * 31 + 17) % 65536;
    }

    /**
     * Dapatkan status sistem lengkap
     */
    getSystemStatus() {
        return {
            medium: this.medium.getStorageStatus(),
            optical: {
                laserPower: this.opticalSystem.laserPower,
                wavelength: this.opticalSystem.wavelength,
                stability: this.opticalSystem.stability,
                multiplexing: this.opticalSystem.multiplexingTechnique
            },
            parallel: {
                threadCount: this.parallelProcessor.threadCount,
                totalTasksProcessed: this.parallelProcessor.totalTasksProcessed
            },
            stats: this.stats
        };
    }
}

// =================================================================
// FUNGSI MAIN UNTUK MENJALANKAN SIMULASI
// =================================================================
async function runHolographicStorageSimulation() {
    console.log("=".repeat(80));
    console.log("SIMULASI HOLOGRAPHIC STORAGE - PEREKAMAN PARALEL");
    console.log("=".repeat(80));
    
    try {
        // Konfigurasi sistem
        const config = {
            mediumDimensions: { width: 12, height: 12, depth: 3 }, // mm
            threadCount: 4
        };
        
        // Inisialisasi sistem
        const storageSystem = new HolographicStorageSystem(config);
        
        // Generate data test
        const testPages = storageSystem.generateTestPages(32, 1024); // 32 halaman, 1MB each
        
        // Set multiplexing technique
        storageSystem.opticalSystem.setMultiplexingTechnique('shift');
        
        // Jalankan simulasi perekaman
        const result = await storageSystem.recordPages(testPages);
        
        // Tampilkan status sistem final
        console.log(`\n[FINAL] Status sistem:`);
        console.log(JSON.stringify(storageSystem.getSystemStatus(), null, 2));
        
    } catch (error) {
        console.error(`[ERROR] Simulasi gagal: ${error.message}`);
        console.error(error.stack);
    }
}

// =================================================================
// EKSEKUSI SIMULASI
// =================================================================
// Jalankan simulasi jika script dieksekusi langsung
if (typeof require !== 'undefined' && require.main === module) {
    runHolographicStorageSimulation();
}

// Export untuk penggunaan sebagai module
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        HolographicStorageSystem,
        HolographicMedium,
        OpticalSystem,
        ParallelProcessor,
        runHolographicStorageSimulation
    };
}