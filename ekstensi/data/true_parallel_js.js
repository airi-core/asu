/**
 * TRUE PARALLEL PROCESSING dalam JavaScript
 * Implementasi nyata untuk menangani 963 operasi paralel
 * 
 * JavaScript adalah single-threaded, tapi kita bisa mencapai paralelisme melalui:
 * 1. Web Workers (true parallelism)
 * 2. Concurrency dengan async/await
 * 3. Batch processing dengan optimal scheduling
 */

// ========================================
// METODE 1: WEB WORKERS (TRUE PARALLELISM)
// ========================================

class TrueParallelProcessor {
    constructor(maxWorkers = navigator.hardwareConcurrency || 4) {
        this.maxWorkers = maxWorkers;
        this.workers = [];
        this.taskQueue = [];
        this.results = new Map();
        this.completedTasks = 0;
        
        console.log(`🔧 Initialized with ${maxWorkers} CPU cores`);
    }

    // Worker code sebagai string (karena tidak bisa import file eksternal di artifacts)
    getWorkerCode() {
        return `
            self.onmessage = function(e) {
                const { taskId, data, operation } = e.data;
                
                let result;
                const startTime = performance.now();
                
                switch(operation) {
                    case 'heavy_computation':
                        // Simulasi komputasi berat
                        result = heavyComputation(data);
                        break;
                    case 'data_processing':
                        // Simulasi processing data
                        result = processData(data);
                        break;
                    case 'crypto_hash':
                        // Simulasi hashing
                        result = simpleCrypto(data);
                        break;
                    default:
                        result = data * Math.random();
                }
                
                const endTime = performance.now();
                
                self.postMessage({
                    taskId,
                    result,
                    processingTime: endTime - startTime,
                    workerId: self.name || 'worker'
                });
            };
            
            function heavyComputation(n) {
                let result = 0;
                for (let i = 0; i < n * 1000; i++) {
                    result += Math.sqrt(i) * Math.sin(i / 100);
                }
                return result;
            }
            
            function processData(data) {
                return data.map(x => x * x + Math.random()).reduce((a, b) => a + b, 0);
            }
            
            function simpleCrypto(data) {
                let hash = 0;
                const str = data.toString();
                for (let i = 0; i < str.length; i++) {
                    const char = str.charCodeAt(i);
                    hash = ((hash << 5) - hash) + char;
                    hash = hash & hash; // Convert to 32-bit integer
                }
                return Math.abs(hash);
            }
        `;
    }

    // Inisialisasi workers
    initializeWorkers() {
        const workerCode = this.getWorkerCode();
        const blob = new Blob([workerCode], { type: 'application/javascript' });
        const workerUrl = URL.createObjectURL(blob);

        for (let i = 0; i < this.maxWorkers; i++) {
            const worker = new Worker(workerUrl);
            worker.workerId = i;
            worker.isIdle = true;
            
            worker.onmessage = (e) => {
                const { taskId, result, processingTime } = e.data;
                
                this.results.set(taskId, {
                    result,
                    processingTime,
                    workerId: worker.workerId
                });
                
                worker.isIdle = true;
                this.completedTasks++;
                
                console.log(`✅ Task ${taskId} completed by Worker ${worker.workerId} (${processingTime.toFixed(2)}ms)`);
                
                // Process next task in queue
                this.processNextTask();
            };
            
            worker.onerror = (error) => {
                console.error(`❌ Worker ${i} error:`, error);
                worker.isIdle = true;
                this.processNextTask();
            };
            
            this.workers.push(worker);
        }
        
        console.log(`🚀 ${this.maxWorkers} workers initialized`);
    }

    // Process 963 tasks dengan true parallelism
    async process963Tasks() {
        console.log('\n🎯 Starting TRUE PARALLEL processing of 963 tasks...\n');
        
        if (this.workers.length === 0) {
            this.initializeWorkers();
        }

        // Generate 963 tasks
        const tasks = [];
        for (let i = 0; i < 963; i++) {
            tasks.push({
                taskId: i,
                data: this.generateTaskData(i),
                operation: this.selectOperation(i)
            });
        }

        this.taskQueue = [...tasks];
        this.results.clear();
        this.completedTasks = 0;
        
        const startTime = performance.now();
        
        // Start processing dengan available workers
        this.processNextTask();
        
        // Wait untuk semua tasks selesai
        await this.waitForCompletion(963);
        
        const endTime = performance.now();
        const totalTime = endTime - startTime;
        
        this.displayResults(totalTime);
        
        return {
            totalTime,
            results: Array.from(this.results.entries()),
            workersUsed: this.maxWorkers,
            tasksCompleted: this.completedTasks
        };
    }

    generateTaskData(taskId) {
        // Generate different types of data based on task ID
        if (taskId % 3 === 0) {
            return taskId * 100; // Heavy computation
        } else if (taskId % 3 === 1) {
            return Array.from({length: 100}, () => Math.random() * taskId); // Data processing
        } else {
            return taskId * Math.random() * 1000; // Crypto hash
        }
    }

    selectOperation(taskId) {
        const operations = ['heavy_computation', 'data_processing', 'crypto_hash'];
        return operations[taskId % 3];
    }

    processNextTask() {
        if (this.taskQueue.length === 0) return;
        
        // Find idle worker
        const idleWorker = this.workers.find(w => w.isIdle);
        if (!idleWorker) return;
        
        const task = this.taskQueue.shift();
        idleWorker.isIdle = false;
        
        console.log(`🔄 Assigning task ${task.taskId} to Worker ${idleWorker.workerId}`);
        idleWorker.postMessage(task);
        
        // Process more tasks if there are more idle workers
        setTimeout(() => this.processNextTask(), 0);
    }

    waitForCompletion(expectedTasks) {
        return new Promise((resolve) => {
            const checkCompletion = () => {
                if (this.completedTasks >= expectedTasks) {
                    resolve();
                } else {
                    setTimeout(checkCompletion, 100);
                }
            };
            checkCompletion();
        });
    }

    displayResults(totalTime) {
        console.log('\n📊 === HASIL TRUE PARALLEL PROCESSING ===');
        console.log(`✅ Tasks completed: ${this.completedTasks}/963`);
        console.log(`⏱️  Total time: ${(totalTime/1000).toFixed(2)} seconds`);
        console.log(`🚀 Tasks per second: ${(963/(totalTime/1000)).toFixed(2)}`);
        console.log(`🧵 Workers used: ${this.maxWorkers}`);
        
        // Analisis per worker
        const workerStats = new Array(this.maxWorkers).fill(0);
        this.results.forEach(result => {
            workerStats[result.workerId]++;
        });
        
        console.log('\n📈 Worker Distribution:');
        workerStats.forEach((count, index) => {
            console.log(`  Worker ${index}: ${count} tasks`);
        });
        
        // Average processing time
        const avgTime = Array.from(this.results.values())
            .reduce((sum, r) => sum + r.processingTime, 0) / this.results.size;
        console.log(`⚡ Average processing time: ${avgTime.toFixed(2)}ms per task`);
        
        console.log('==========================================\n');
    }

    cleanup() {
        this.workers.forEach(worker => worker.terminate());
        this.workers = [];
        console.log('🧹 Workers cleaned up');
    }
}

// ========================================
// METODE 2: CONCURRENCY DENGAN BATCH PROCESSING
// ========================================

class ConcurrentBatchProcessor {
    constructor(batchSize = 50, maxConcurrent = 10) {
        this.batchSize = batchSize;
        this.maxConcurrent = maxConcurrent;
    }

    async process963TasksConcurrent() {
        console.log('\n🎯 Starting CONCURRENT batch processing of 963 tasks...\n');
        
        const startTime = performance.now();
        const tasks = this.generate963Tasks();
        const batches = this.createBatches(tasks, this.batchSize);
        
        console.log(`📦 Created ${batches.length} batches of ~${this.batchSize} tasks each`);
        
        const results = [];
        
        // Process batches dengan limited concurrency
        for (let i = 0; i < batches.length; i += this.maxConcurrent) {
            const batchGroup = batches.slice(i, i + this.maxConcurrent);
            
            console.log(`🔄 Processing batch group ${Math.floor(i/this.maxConcurrent) + 1}/${Math.ceil(batches.length/this.maxConcurrent)}`);
            
            const batchPromises = batchGroup.map((batch, batchIndex) => 
                this.processBatch(batch, i + batchIndex)
            );
            
            const batchResults = await Promise.all(batchPromises);
            results.push(...batchResults.flat());
        }
        
        const endTime = performance.now();
        const totalTime = endTime - startTime;
        
        this.displayConcurrentResults(totalTime, results);
        
        return { totalTime, results, method: 'concurrent_batch' };
    }

    generate963Tasks() {
        return Array.from({length: 963}, (_, i) => ({
            id: i,
            data: Math.random() * 1000,
            complexity: Math.floor(Math.random() * 3) + 1
        }));
    }

    createBatches(tasks, batchSize) {
        const batches = [];
        for (let i = 0; i < tasks.length; i += batchSize) {
            batches.push(tasks.slice(i, i + batchSize));
        }
        return batches;
    }

    async processBatch(batch, batchIndex) {
        const batchStartTime = performance.now();
        
        // Process all tasks in batch concurrently
        const taskPromises = batch.map(task => this.processTask(task));
        const results = await Promise.all(taskPromises);
        
        const batchEndTime = performance.now();
        const batchTime = batchEndTime - batchStartTime;
        
        console.log(`✅ Batch ${batchIndex} completed: ${batch.length} tasks in ${batchTime.toFixed(2)}ms`);
        
        return results;
    }

    async processTask(task) {
        // Simulate processing time based on complexity
        const processingTime = task.complexity * 20 + Math.random() * 30;
        
        await new Promise(resolve => setTimeout(resolve, processingTime));
        
        return {
            taskId: task.id,
            result: task.data * Math.random(),
            processingTime
        };
    }

    displayConcurrentResults(totalTime, results) {
        console.log('\n📊 === HASIL CONCURRENT BATCH PROCESSING ===');
        console.log(`✅ Tasks completed: ${results.length}/963`);
        console.log(`⏱️  Total time: ${(totalTime/1000).toFixed(2)} seconds`);
        console.log(`🚀 Tasks per second: ${(963/(totalTime/1000)).toFixed(2)}`);
        console.log(`📦 Batch size: ${this.batchSize}`);
        console.log(`🔄 Max concurrent batches: ${this.maxConcurrent}`);
        
        const avgProcessingTime = results.reduce((sum, r) => sum + r.processingTime, 0) / results.length;
        console.log(`⚡ Average task time: ${avgProcessingTime.toFixed(2)}ms`);
        console.log('=============================================\n');
    }
}

// ========================================
// METODE 3: OPTIMIZED ASYNC PROCESSING
// ========================================

class OptimizedAsyncProcessor {
    constructor(concurrencyLimit = 20) {
        this.concurrencyLimit = concurrencyLimit;
        this.activePromises = new Set();
    }

    async process963TasksOptimized() {
        console.log('\n🎯 Starting OPTIMIZED async processing of 963 tasks...\n');
        
        const startTime = performance.now();
        const tasks = Array.from({length: 963}, (_, i) => ({
            id: i,
            priority: i % 3, // 0 = high, 1 = medium, 2 = low
            data: Math.random() * (i + 1)
        }));
        
        // Sort by priority
        tasks.sort((a, b) => a.priority - b.priority);
        
        const results = [];
        let processedCount = 0;
        
        console.log(`🔄 Processing with concurrency limit: ${this.concurrencyLimit}`);
        
        for (const task of tasks) {
            // Wait if we've hit the concurrency limit
            if (this.activePromises.size >= this.concurrencyLimit) {
                await Promise.race(this.activePromises);
            }
            
            const taskPromise = this.processOptimizedTask(task)
                .then(result => {
                    results.push(result);
                    processedCount++;
                    
                    if (processedCount % 100 === 0) {
                        console.log(`📈 Progress: ${processedCount}/963 tasks completed`);
                    }
                    
                    return result;
                })
                .finally(() => {
                    this.activePromises.delete(taskPromise);
                });
            
            this.activePromises.add(taskPromise);
        }
        
        // Wait for all remaining tasks
        await Promise.all(this.activePromises);
        
        const endTime = performance.now();
        const totalTime = endTime - startTime;
        
        this.displayOptimizedResults(totalTime, results);
        
        return { totalTime, results, method: 'optimized_async' };
    }

    async processOptimizedTask(task) {
        const startTime = performance.now();
        
        // Variable processing time based on priority
        const baseTime = 10;
        const priorityMultiplier = task.priority === 0 ? 0.5 : task.priority === 1 ? 1 : 1.5;
        const processingTime = baseTime * priorityMultiplier + Math.random() * 20;
        
        await new Promise(resolve => setTimeout(resolve, processingTime));
        
        // Simulate different operations
        let result;
        switch(task.priority) {
            case 0: // High priority - simple operation
                result = task.data * 2;
                break;
            case 1: // Medium priority - moderate operation
                result = Math.sqrt(task.data) * Math.PI;
                break;
            case 2: // Low priority - complex operation
                result = task.data * Math.sin(task.data) + Math.cos(task.data);
                break;
        }
        
        const endTime = performance.now();
        
        return {
            taskId: task.id,
            priority: task.priority,
            result,
            processingTime: endTime - startTime
        };
    }

    displayOptimizedResults(totalTime, results) {
        console.log('\n📊 === HASIL OPTIMIZED ASYNC PROCESSING ===');
        console.log(`✅ Tasks completed: ${results.length}/963`);
        console.log(`⏱️  Total time: ${(totalTime/1000).toFixed(2)} seconds`);
        console.log(`🚀 Tasks per second: ${(963/(totalTime/1000)).toFixed(2)}`);
        console.log(`🔄 Concurrency limit: ${this.concurrencyLimit}`);
        
        // Priority analysis
        const priorityStats = {0: 0, 1: 0, 2: 0};
        results.forEach(r => priorityStats[r.priority]++);
        
        console.log('\n📊 Priority Distribution:');
        console.log(`  High priority (0): ${priorityStats[0]} tasks`);
        console.log(`  Medium priority (1): ${priorityStats[1]} tasks`);
        console.log(`  Low priority (2): ${priorityStats[2]} tasks`);
        
        const avgTime = results.reduce((sum, r) => sum + r.processingTime, 0) / results.length;
        console.log(`⚡ Average processing time: ${avgTime.toFixed(2)}ms per task`);
        console.log('===========================================\n');
    }
}

// ========================================
// DEMO RUNNER
// ========================================

async function demonstrateParallelProcessing() {
    console.log('🌟 === DEMONSTRASI TRUE PARALLEL PROCESSING ===\n');
    console.log('Akan menjalankan 963 operasi dengan 3 metode berbeda:\n');
    
    const results = {};
    
    try {
        // Method 1: True Parallel dengan Web Workers
        console.log('1️⃣ TRUE PARALLEL PROCESSING (Web Workers)');
        const trueParallel = new TrueParallelProcessor();
        results.trueParallel = await trueParallel.process963Tasks();
        trueParallel.cleanup();
        
        await new Promise(resolve => setTimeout(resolve, 1000)); // Pause
        
        // Method 2: Concurrent Batch Processing
        console.log('2️⃣ CONCURRENT BATCH PROCESSING');
        const batchProcessor = new ConcurrentBatchProcessor();
        results.concurrent = await batchProcessor.process963TasksConcurrent();
        
        await new Promise(resolve => setTimeout(resolve, 1000)); // Pause
        
        // Method 3: Optimized Async Processing
        console.log('3️⃣ OPTIMIZED ASYNC PROCESSING');
        const optimizedProcessor = new OptimizedAsyncProcessor();
        results.optimized = await optimizedProcessor.process963TasksOptimized();
        
        // Comparison
        console.log('\n🏆 === PERBANDINGAN HASIL ===');
        console.log(`True Parallel: ${(results.trueParallel.totalTime/1000).toFixed(2)}s`);
        console.log(`Concurrent Batch: ${(results.concurrent.totalTime/1000).toFixed(2)}s`);
        console.log(`Optimized Async: ${(results.optimized.totalTime/1000).toFixed(2)}s`);
        
        const fastest = Object.entries(results)
            .sort((a, b) => a[1].totalTime - b[1].totalTime)[0];
        
        console.log(`\n🥇 Fastest method: ${fastest[0]} (${(fastest[1].totalTime/1000).toFixed(2)}s)`);
        console.log('\n✨ Demo completed successfully!');
        
    } catch (error) {
        console.error('❌ Error during demonstration:', error);
    }
    
    return results;
}

// Run the demonstration
demonstrateParallelProcessing();