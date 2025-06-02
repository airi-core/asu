/**
 * ASU Container System - Core Implementation
 * 
 * Metadata Proyek:
 * Nama: Susanto
 * NIM: 206181
 * Universitas: Hidden Investor
 * Pembimbing: Suwardjono
 * Rektor: Martin
 */

const express = require('express');
const { spawn, execFile } = require('child_process');
const fs = require('fs').promises;
const path = require('path');
const crypto = require('crypto');
const tar = require('tar');
const tmp = require('tmp-promise');
const validator = require('validator');
const rateLimit = require('express-rate-limit');
const helmet = require('helmet');

class ASUContainerSystem {
    constructor() {
        this.app = express();
        this.containers = new Map(); // In-memory storage untuk metadata containers
        this.storageDir = path.join(__dirname, 'storage');
        this.maxContainerSize = 1024 * 1024 * 1024 * 1024; // 1TB
        
        this.initializeMiddleware();
        this.initializeRoutes();
        this.ensureStorageDirectory();
    }

    async ensureStorageDirectory() {
        try {
            await fs.mkdir(this.storageDir, { recursive: true });
            console.log(`Storage directory initialized: ${this.storageDir}`);
        } catch (error) {
            console.error('Failed to initialize storage directory:', error);
            throw error;
        }
    }

    initializeMiddleware() {
        // Security middleware
        this.app.use(helmet());
        
        // Rate limiting
        const limiter = rateLimit({
            windowMs: 15 * 60 * 1000, // 15 minutes
            max: 100 // limit each IP to 100 requests per windowMs
        });
        this.app.use(limiter);
        
        this.app.use(express.json({ limit: '10mb' }));
        this.app.use(express.urlencoded({ extended: true }));
    }

    initializeRoutes() {
        // Create container from Git repository
        this.app.post('/api/containers', this.createContainer.bind(this));
        
        // Get container information
        this.app.get('/api/containers/:id', this.getContainer.bind(this));
        
        // Execute command in container
        this.app.post('/api/containers/:id/execute', this.executeInContainer.bind(this));
        
        // Delete container
        this.app.delete('/api/containers/:id', this.deleteContainer.bind(this));
        
        // List all containers
        this.app.get('/api/containers', this.listContainers.bind(this));
        
        // Health check
        this.app.get('/health', (req, res) => {
            res.json({ status: 'healthy', timestamp: new Date().toISOString() });
        });
    }

    /**
     * Validasi URL Git dengan pendekatan defensive programming
     */
    async validateGitUrl(url) {
        if (!url || typeof url !== 'string') {
            throw new Error('URL Git tidak valid: URL harus berupa string non-empty');
        }

        // Sanitasi URL
        const sanitizedUrl = validator.escape(url.trim());
        
        // Validasi format URL
        if (!validator.isURL(sanitizedUrl, { 
            protocols: ['http', 'https', 'git'],
            require_protocol: true 
        })) {
            throw new Error('Format URL Git tidak valid');
        }

        // Blacklist untuk protokol dan domain berbahaya
        const blacklistedPatterns = [
            /^file:\/\//i,
            /localhost/i,
            /127\.0\.0\.1/i,
            /192\.168\./i,
            /10\./i,
            /172\.(1[6-9]|2\d|3[01])\./i
        ];

        for (const pattern of blacklistedPatterns) {
            if (pattern.test(sanitizedUrl)) {
                throw new Error('URL Git mengandung alamat yang tidak diizinkan');
            }
        }

        return sanitizedUrl;
    }

    /**
     * Verifikasi repository Git secara remote
     */
    async verifyGitRepository(url) {
        return new Promise((resolve, reject) => {
            const timeout = setTimeout(() => {
                reject(new Error('Timeout: Verifikasi repository Git terlalu lama'));
            }, 30000);

            const gitProcess = spawn('git', ['ls-remote', '--heads', url], {
                stdio: ['ignore', 'pipe', 'pipe']
            });

            let stdout = '';
            let stderr = '';

            gitProcess.stdout.on('data', (data) => {
                stdout += data.toString();
            });

            gitProcess.stderr.on('data', (data) => {
                stderr += data.toString();
            });

            gitProcess.on('close', (code) => {
                clearTimeout(timeout);
                if (code === 0 && stdout.trim()) {
                    resolve(true);
                } else {
                    reject(new Error(`Repository tidak dapat diakses: ${stderr || 'Unknown error'}`));
                }
            });

            gitProcess.on('error', (error) => {
                clearTimeout(timeout);
                reject(new Error(`Error verifikasi Git: ${error.message}`));
            });
        });
    }

    /**
     * Generate SHA256 hash unik untuk nama file container
     */
    generateContainerHash() {
        const timestamp = Date.now().toString();
        const randomBytes = crypto.randomBytes(16).toString('hex');
        return crypto.createHash('sha256')
            .update(timestamp + randomBytes)
            .digest('hex');
    }

    /**
     * Clone repository Git ke temporary directory
     */
    async cloneRepository(url, targetDir) {
        return new Promise((resolve, reject) => {
            const timeout = setTimeout(() => {
                reject(new Error('Timeout: Git clone terlalu lama (>10 menit)'));
            }, 600000); // 10 minutes timeout

            const gitProcess = spawn('git', ['clone', '--depth', '1', url, targetDir], {
                stdio: ['ignore', 'pipe', 'pipe']
            });

            let stderr = '';

            gitProcess.stderr.on('data', (data) => {
                stderr += data.toString();
            });

            gitProcess.on('close', (code) => {
                clearTimeout(timeout);
                if (code === 0) {
                    resolve();
                } else {
                    reject(new Error(`Git clone failed: ${stderr}`));
                }
            });

            gitProcess.on('error', (error) => {
                clearTimeout(timeout);
                reject(new Error(`Git clone error: ${error.message}`));
            });
        });
    }

    /**
     * Create compressed archive (.asu file) dari cloned repository
     */
    async createContainerArchive(sourceDir, containerHash) {
        const containerPath = path.join(this.storageDir, `${containerHash}.asu`);
        
        // Create metadata
        const metadata = {
            id: containerHash,
            created: new Date().toISOString(),
            version: '1.0.0',
            type: 'git-repository'
        };

        // Add metadata to source directory
        const metadataPath = path.join(sourceDir, 'metadata.json');
        await fs.writeFile(metadataPath, JSON.stringify(metadata, null, 2));

        // Create tar.gz archive
        await tar.create({
            gzip: true,
            file: containerPath,
            cwd: path.dirname(sourceDir),
        }, [path.basename(sourceDir)]);

        // Check file size
        const stats = await fs.stat(containerPath);
        if (stats.size > this.maxContainerSize) {
            await fs.unlink(containerPath);
            throw new Error(`Container size (${stats.size}) exceeds maximum limit (${this.maxContainerSize})`);
        }

        return {
            path: containerPath,
            size: stats.size,
            metadata
        };
    }

    /**
     * Extract container archive ke temporary directory
     */
    async extractContainer(containerHash) {
        const containerPath = path.join(this.storageDir, `${containerHash}.asu`);
        
        // Verify container exists
        try {
            await fs.access(containerPath);
        } catch (error) {
            throw new Error(`Container ${containerHash} tidak ditemukan`);
        }

        // Create temporary directory
        const tempDir = await tmp.dir({ unsafeCleanup: true });
        
        // Extract archive
        await tar.extract({
            file: containerPath,
            cwd: tempDir.path
        });

        return tempDir;
    }

    /**
     * Sanitasi command untuk mencegah command injection
     */
    sanitizeCommand(command, args = []) {
        // Blacklist perintah berbahaya
        const blacklistedCommands = [
            'rm', 'del', 'format', 'fdisk', 'mkfs',
            'sudo', 'su', 'chmod', 'chown',
            'wget', 'curl', 'nc', 'netcat',
            'ssh', 'scp', 'ftp', 'telnet',
            'ps', 'kill', 'killall', 'pkill',
            'mount', 'umount', 'dd'
        ];

        const baseCommand = command.toLowerCase().split(' ')[0];
        
        if (blacklistedCommands.includes(baseCommand)) {
            throw new Error(`Perintah '${baseCommand}' tidak diizinkan untuk alasan keamanan`);
        }

        // Sanitasi arguments
        const sanitizedArgs = args.map(arg => {
            if (typeof arg !== 'string') {
                throw new Error('Semua argumen harus berupa string');
            }
            
            // Remove potentially dangerous characters
            const dangerous = /[;&|`$(){}[\]<>]/;
            if (dangerous.test(arg)) {
                throw new Error(`Argumen mengandung karakter berbahaya: ${arg}`);
            }
            
            return arg.trim();
        });

        return { command: baseCommand, args: sanitizedArgs };
    }

    /**
     * API Endpoint: Create new container
     */
    async createContainer(req, res) {
        try {
            const { gitUrl } = req.body;

            if (!gitUrl) {
                return res.status(400).json({
                    success: false,
                    error: 'Parameter gitUrl diperlukan'
                });
            }

            // Validate Git URL
            const validatedUrl = await this.validateGitUrl(gitUrl);
            
            // Verify repository accessibility
            await this.verifyGitRepository(validatedUrl);

            // Generate unique container hash
            const containerHash = this.generateContainerHash();

            // Create temporary directory for cloning
            const tempDir = await tmp.dir({ unsafeCleanup: true });
            const cloneDir = path.join(tempDir.path, 'repo');

            try {
                // Clone repository
                await this.cloneRepository(validatedUrl, cloneDir);

                // Create container archive
                const containerInfo = await this.createContainerArchive(cloneDir, containerHash);

                // Store container metadata
                const containerMetadata = {
                    id: containerHash,
                    gitUrl: validatedUrl,
                    created: new Date().toISOString(),
                    size: containerInfo.size,
                    path: containerInfo.path
                };

                this.containers.set(containerHash, containerMetadata);

                res.status(201).json({
                    success: true,
                    data: {
                        id: containerHash,
                        gitUrl: validatedUrl,
                        created: containerMetadata.created,
                        size: containerInfo.size
                    }
                });

            } finally {
                // Cleanup temporary directory
                await tempDir.cleanup();
            }

        } catch (error) {
            console.error('Create container error:', error);
            res.status(500).json({
                success: false,
                error: error.message
            });
        }
    }

    /**
     * API Endpoint: Get container information
     */
    async getContainer(req, res) {
        try {
            const { id } = req.params;

            if (!this.containers.has(id)) {
                return res.status(404).json({
                    success: false,
                    error: 'Container tidak ditemukan'
                });
            }

            const container = this.containers.get(id);
            
            res.json({
                success: true,
                data: container
            });

        } catch (error) {
            console.error('Get container error:', error);
            res.status(500).json({
                success: false,
                error: error.message
            });
        }
    }

    /**
     * API Endpoint: Execute command in container
     */
    async executeInContainer(req, res) {
        try {
            const { id } = req.params;
            const { command, args = [], timeout = 30000 } = req.body;

            if (!this.containers.has(id)) {
                return res.status(404).json({
                    success: false,
                    error: 'Container tidak ditemukan'
                });
            }

            if (!command) {
                return res.status(400).json({
                    success: false,
                    error: 'Parameter command diperlukan'
                });
            }

            // Sanitize command
            const { command: sanitizedCommand, args: sanitizedArgs } = this.sanitizeCommand(command, args);

            // Extract container to temporary directory
            const tempDir = await this.extractContainer(id);

            try {
                // Find the actual repository directory
                const entries = await fs.readdir(tempDir.path);
                const repoDir = path.join(tempDir.path, entries[0]);

                // Execute command in sandboxed environment
                const result = await this.executeCommandInSandbox(
                    sanitizedCommand, 
                    sanitizedArgs, 
                    repoDir, 
                    timeout
                );

                res.json({
                    success: true,
                    data: result
                });

            } finally {
                // Cleanup
                await tempDir.cleanup();
            }

        } catch (error) {
            console.error('Execute command error:', error);
            res.status(500).json({
                success: false,
                error: error.message
            });
        }
    }

    /**
     * Execute command dalam sandboxed environment
     */
    async executeCommandInSandbox(command, args, workingDir, timeout) {
        return new Promise((resolve, reject) => {
            const timeoutHandle = setTimeout(() => {
                reject(new Error(`Execution timeout after ${timeout}ms`));
            }, timeout);

            // Restricted environment variables
            const sandboxEnv = {
                PATH: '/usr/bin:/bin',
                HOME: '/tmp',
                USER: 'sandbox',
                SHELL: '/bin/sh'
            };

            const childProcess = spawn(command, args, {
                cwd: workingDir,
                env: sandboxEnv,
                stdio: ['ignore', 'pipe', 'pipe'],
                timeout: timeout
            });

            let stdout = '';
            let stderr = '';

            childProcess.stdout.on('data', (data) => {
                stdout += data.toString();
                // Limit output size to prevent memory issues
                if (stdout.length > 1024 * 1024) { // 1MB limit
                    childProcess.kill('SIGTERM');
                    reject(new Error('Output size limit exceeded'));
                }
            });

            childProcess.stderr.on('data', (data) => {
                stderr += data.toString();
                if (stderr.length > 1024 * 1024) { // 1MB limit
                    childProcess.kill('SIGTERM');
                    reject(new Error('Error output size limit exceeded'));
                }
            });

            childProcess.on('close', (code) => {
                clearTimeout(timeoutHandle);
                resolve({
                    exitCode: code,
                    stdout: stdout.trim(),
                    stderr: stderr.trim(),
                    executedAt: new Date().toISOString()
                });
            });

            childProcess.on('error', (error) => {
                clearTimeout(timeoutHandle);
                reject(new Error(`Execution error: ${error.message}`));
            });
        });
    }

    /**
     * API Endpoint: Delete container
     */
    async deleteContainer(req, res) {
        try {
            const { id } = req.params;

            if (!this.containers.has(id)) {
                return res.status(404).json({
                    success: false,
                    error: 'Container tidak ditemukan'
                });
            }

            const container = this.containers.get(id);
            
            // Delete container file
            try {
                await fs.unlink(container.path);
            } catch (error) {
                console.warn(`Failed to delete container file: ${error.message}`);
            }

            // Remove from memory
            this.containers.delete(id);

            res.json({
                success: true,
                message: 'Container berhasil dihapus'
            });

        } catch (error) {
            console.error('Delete container error:', error);
            res.status(500).json({
                success: false,
                error: error.message
            });
        }
    }

    /**
     * API Endpoint: List all containers
     */
    async listContainers(req, res) {
        try {
            const containersList = Array.from(this.containers.values());
            
            res.json({
                success: true,
                data: {
                    containers: containersList,
                    total: containersList.length
                }
            });

        } catch (error) {
            console.error('List containers error:', error);
            res.status(500).json({
                success: false,
                error: error.message
            });
        }
    }

    /**
     * Start server
     */
    start(port = 3000) {
        this.app.listen(port, () => {
            console.log(`ASU Container System server running on port ${port}`);
            console.log(`Storage directory: ${this.storageDir}`);
        });
    }
}

// Export untuk testing dan modularitas
module.exports = ASUContainerSystem;

// Start server jika file dijalankan langsung
if (require.main === module) {
    const system = new ASUContainerSystem();
    system.start(process.env.PORT || 3000);
}