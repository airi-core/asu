/**
 * ASU Container System - Core Implementation (Refactored)
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
const sqlite3 = require('sqlite3').verbose();
const { promisify } = require('util');
const winston = require('winston');
const cron = require('node-cron');
const { v4: uuidv4 } = require('uuid');

// Configure logging
const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  transports: [
    new winston.transports.Console(),
    new winston.transports.File({ filename: 'asu-container.log' })
  ]
});

class ASUContainerSystem {
    constructor() {
        this.app = express();
        this.db = null;
        this.storageDir = path.join(__dirname, 'storage');
        this.maxContainerSize = 1024 * 1024 * 1024 * 1024; // 1TB
        this.sandboxBasePath = path.join(__dirname, 'sandbox');
        this.databasePath = path.join(__dirname, 'asu-container.db');
        
        this.initializeMiddleware();
        this.initializeDatabase();
        this.initializeRoutes();
        this.initializeMaintenanceTasks();
    }

    async initializeDatabase() {
        // Create database connection
        this.db = new sqlite3.Database(this.databasePath);
        
        // Promisify database methods
        this.db.run = promisify(this.db.run.bind(this.db));
        this.db.get = promisify(this.db.get.bind(this.db));
        this.db.all = promisify(this.db.all.bind(this.db));
        
        // Create tables if they don't exist
        await this.db.run(`
            CREATE TABLE IF NOT EXISTS containers (
                id TEXT PRIMARY KEY,
                git_url TEXT NOT NULL,
                created TEXT NOT NULL,
                size INTEGER NOT NULL,
                path TEXT NOT NULL,
                last_accessed TEXT,
                expires_at TEXT,
                status TEXT DEFAULT 'active'
            )
        `);
        
        await this.db.run(`
            CREATE TABLE IF NOT EXISTS container_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                container_id TEXT,
                command_executed TEXT,
                execution_time TEXT,
                exit_code INTEGER,
                FOREIGN KEY(container_id) REFERENCES containers(id)
            )
        `);
        
        logger.info('Database initialized successfully');
    }

    async ensureStorageDirectory() {
        try {
            await fs.mkdir(this.storageDir, { recursive: true });
            await fs.mkdir(this.sandboxBasePath, { recursive: true });
            logger.info(`Storage directories initialized: ${this.storageDir} and ${this.sandboxBasePath}`);
        } catch (error) {
            logger.error('Failed to initialize storage directories:', error);
            throw error;
        }
    }

    initializeMiddleware() {
        // Security middleware
        this.app.use(helmet());
        
        // Rate limiting
        const limiter = rateLimit({
            windowMs: 15 * 60 * 1000, // 15 minutes
            max: 100,
            message: 'Too many requests from this IP, please try again later'
        });
        this.app.use(limiter);
        
        this.app.use(express.json({ limit: '10mb' }));
        this.app.use(express.urlencoded({ extended: true }));
        
        // Logging middleware
        this.app.use((req, res, next) => {
            logger.info(`${req.method} ${req.path}`);
            next();
        });
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
        
        // Get container stats
        this.app.get('/api/containers/:id/stats', this.getContainerStats.bind(this));
        
        // System info
        this.app.get('/api/system/info', this.getSystemInfo.bind(this));
        
        // Health check
        this.app.get('/health', (req, res) => {
            res.json({ 
                status: 'healthy', 
                timestamp: new Date().toISOString(),
                storage: this.storageDir,
                database: this.databasePath
            });
        });
    }

    initializeMaintenanceTasks() {
        // Daily maintenance at 2 AM
        cron.schedule('0 2 * * *', async () => {
            logger.info('Running daily maintenance tasks');
            try {
                await this.performMaintenance();
            } catch (error) {
                logger.error('Maintenance task failed:', error);
            }
        });
        
        // Hourly cleanup check
        cron.schedule('0 * * * *', async () => {
            logger.info('Running hourly cleanup check');
            try {
                await this.cleanupExpiredContainers();
            } catch (error) {
                logger.error('Cleanup task failed:', error);
            }
        });
    }

    /**
     * Validate Git URL with defensive programming approach
     */
    async validateGitUrl(url) {
        if (!url || typeof url !== 'string') {
            throw new Error('Invalid Git URL: URL must be a non-empty string');
        }

        // Sanitize URL
        const sanitizedUrl = validator.escape(url.trim());
        
        // Validate URL format
        if (!validator.isURL(sanitizedUrl, { 
            protocols: ['http', 'https', 'git'],
            require_protocol: true 
        })) {
            throw new Error('Invalid Git URL format');
        }

        // Blacklist for dangerous protocols and domains
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
                throw new Error('Git URL contains disallowed address');
            }
        }

        return sanitizedUrl;
    }

    /**
     * Verify remote Git repository
     */
    async verifyGitRepository(url) {
        return new Promise((resolve, reject) => {
            const timeout = setTimeout(() => {
                reject(new Error('Timeout: Git repository verification took too long'));
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
                    reject(new Error(`Repository not accessible: ${stderr || 'Unknown error'}`));
                }
            });

            gitProcess.on('error', (error) => {
                clearTimeout(timeout);
                reject(new Error(`Git verification error: ${error.message}`));
            });
        });
    }

    /**
     * Generate unique SHA256 hash for container file name
     */
    generateContainerHash() {
        const timestamp = Date.now().toString();
        const randomBytes = crypto.randomBytes(16).toString('hex');
        return crypto.createHash('sha256')
            .update(timestamp + randomBytes)
            .digest('hex');
    }

    /**
     * Clone Git repository to temporary directory
     */
    async cloneRepository(url, targetDir) {
        return new Promise((resolve, reject) => {
            const timeout = setTimeout(() => {
                reject(new Error('Timeout: Git clone took too long (>10 minutes)'));
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
     * Validate repository content for safe file extensions
     */
    async validateRepositoryContent(repoPath) {
        const safeExtensions = [
            '.js', '.ts', '.py', '.java', '.c', '.cpp', '.h', '.hpp',
            '.md', '.txt', '.json', '.yml', '.yaml', '.html', '.css',
            '.go', '.rs', '.rb', '.php', '.sh'
        ];
        
        const dangerousFiles = [];
        
        const walkDir = async (dir) => {
            const entries = await fs.readdir(dir, { withFileTypes: true });
            
            for (const entry of entries) {
                const fullPath = path.join(dir, entry.name);
                
                if (entry.isDirectory()) {
                    await walkDir(fullPath);
                } else {
                    const ext = path.extname(entry.name).toLowerCase();
                    if (!safeExtensions.includes(ext)) {
                        dangerousFiles.push({
                            path: fullPath,
                            extension: ext
                        });
                    }
                }
            }
        };
        
        await walkDir(repoPath);
        
        if (dangerousFiles.length > 0) {
            const dangerousExtensions = [...new Set(dangerousFiles.map(f => f.extension))];
            throw new Error(
                `Repository contains files with potentially dangerous extensions: ${dangerousExtensions.join(', ')}. ` +
                `Found ${dangerousFiles.length} files with these extensions.`
            );
        }
        
        return true;
    }

    /**
     * Create compressed archive (.asu file) from cloned repository
     */
    async createContainerArchive(sourceDir, containerHash) {
        const containerPath = path.join(this.storageDir, `${containerHash}.asu`);
        
        // Create metadata
        const metadata = {
            id: containerHash,
            created: new Date().toISOString(),
            version: '1.0.0',
            type: 'git-repository',
            safe_extensions: [
                '.js', '.ts', '.py', '.java', '.c', '.cpp', '.h', '.hpp',
                '.md', '.txt', '.json', '.yml', '.yaml', '.html', '.css'
            ]
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
     * Extract container archive to temporary directory
     */
    async extractContainer(containerHash) {
        const containerPath = path.join(this.storageDir, `${containerHash}.asu`);
        
        // Verify container exists
        try {
            await fs.access(containerPath);
        } catch (error) {
            throw new Error(`Container ${containerHash} not found`);
        }

        // Create temporary directory in sandbox
        const tempDirPath = path.join(this.sandboxBasePath, `exec-${uuidv4()}`);
        await fs.mkdir(tempDirPath, { recursive: true });
        
        // Extract archive
        await tar.extract({
            file: containerPath,
            cwd: tempDirPath
        });

        return {
            path: tempDirPath,
            cleanup: async () => {
                try {
                    await fs.rm(tempDirPath, { recursive: true, force: true });
                } catch (error) {
                    logger.warn(`Failed to cleanup temp dir ${tempDirPath}:`, error);
                }
            }
        };
    }

    /**
     * Setup virtual environment for execution
     */
    async setupVirtualEnvironment(envPath, language) {
        try {
            switch (language) {
                case 'python':
                    return new Promise((resolve, reject) => {
                        const venvProcess = spawn('python3', ['-m', 'venv', path.join(envPath, 'venv')], {
                            stdio: 'inherit'
                        });
                        
                        venvProcess.on('close', (code) => {
                            if (code === 0) {
                                resolve(true);
                            } else {
                                reject(new Error(`Python virtual environment setup failed with code ${code}`));
                            }
                        });
                        
                        venvProcess.on('error', (error) => {
                            reject(new Error(`Python virtual environment setup error: ${error.message}`));
                        });
                    });
                
                case 'node':
                    return new Promise((resolve, reject) => {
                        const npmProcess = spawn('npm', ['install'], {
                            cwd: envPath,
                            stdio: 'inherit'
                        });
                        
                        npmProcess.on('close', (code) => {
                            if (code === 0) {
                                resolve(true);
                            } else {
                                reject(new Error(`npm install failed with code ${code}`));
                            }
                        });
                        
                        npmProcess.on('error', (error) => {
                            reject(new Error(`npm install error: ${error.message}`));
                        });
                    });
                
                default:
                    logger.info(`No specific environment setup needed for ${language}`);
                    return true;
            }
        } catch (error) {
            logger.error('Virtual environment setup failed:', error);
            throw error;
        }
    }

    /**
     * Sanitize command to prevent command injection
     */
    sanitizeCommand(command, args = []) {
        // Blacklist dangerous commands
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
            throw new Error(`Command '${baseCommand}' is not allowed for security reasons`);
        }

        // Sanitize arguments
        const sanitizedArgs = args.map(arg => {
            if (typeof arg !== 'string') {
                throw new Error('All arguments must be strings');
            }
            
            // Remove potentially dangerous characters
            const dangerous = /[;&|`$(){}[\]<>]/;
            if (dangerous.test(arg)) {
                throw new Error(`Argument contains dangerous characters: ${arg}`);
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
                    error: 'gitUrl parameter is required'
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
                
                // Validate repository content
                await this.validateRepositoryContent(cloneDir);

                // Create container archive
                const containerInfo = await this.createContainerArchive(cloneDir, containerHash);

                // Store container metadata in database
                const createdAt = new Date().toISOString();
                const expiresAt = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(); // 30 days from now
                
                await this.db.run(
                    'INSERT INTO containers (id, git_url, created, size, path, expires_at) VALUES (?, ?, ?, ?, ?, ?)',
                    [containerHash, validatedUrl, createdAt, containerInfo.size, containerInfo.path, expiresAt]
                );

                res.status(201).json({
                    success: true,
                    data: {
                        id: containerHash,
                        gitUrl: validatedUrl,
                        created: createdAt,
                        size: containerInfo.size,
                        expiresAt: expiresAt
                    }
                });

            } finally {
                // Cleanup temporary directory
                await tempDir.cleanup();
            }

        } catch (error) {
            logger.error('Create container error:', error);
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

            const container = await this.db.get(
                'SELECT * FROM containers WHERE id = ?',
                [id]
            );

            if (!container) {
                return res.status(404).json({
                    success: false,
                    error: 'Container not found'
                });
            }
            
            // Update last accessed time
            await this.db.run(
                'UPDATE containers SET last_accessed = ? WHERE id = ?',
                [new Date().toISOString(), id]
            );
            
            res.json({
                success: true,
                data: container
            });

        } catch (error) {
            logger.error('Get container error:', error);
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
            const { command, args = [], timeout = 30000, language } = req.body;

            // Verify container exists
            const container = await this.db.get(
                'SELECT * FROM containers WHERE id = ? AND status = "active"',
                [id]
            );

            if (!container) {
                return res.status(404).json({
                    success: false,
                    error: 'Container not found or inactive'
                });
            }

            if (!command) {
                return res.status(400).json({
                    success: false,
                    error: 'command parameter is required'
                });
            }

            // Sanitize command
            const { command: sanitizedCommand, args: sanitizedArgs } = this.sanitizeCommand(command, args);

            // Extract container to temporary directory
            const { path: tempDirPath, cleanup } = await this.extractContainer(id);

            try {
                // Find the actual repository directory
                const entries = await fs.readdir(tempDirPath);
                const repoDir = path.join(tempDirPath, entries[0]);

                // Setup virtual environment if specified
                if (language) {
                    await this.setupVirtualEnvironment(repoDir, language);
                }

                // Execute command in sandboxed environment
                const result = await this.executeCommandInSandbox(
                    sanitizedCommand, 
                    sanitizedArgs, 
                    repoDir, 
                    timeout
                );

                // Log execution stats
                await this.db.run(
                    'INSERT INTO container_stats (container_id, command_executed, execution_time, exit_code) VALUES (?, ?, ?, ?)',
                    [id, command, new Date().toISOString(), result.exitCode]
                );

                res.json({
                    success: true,
                    data: result
                });

            } finally {
                // Cleanup
                await cleanup();
            }

        } catch (error) {
            logger.error('Execute command error:', error);
            res.status(500).json({
                success: false,
                error: error.message
            });
        }
    }

    /**
     * Execute command in sandboxed environment
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
                SHELL: '/bin/sh',
                ...process.env
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

            // Verify container exists
            const container = await this.db.get(
                'SELECT * FROM containers WHERE id = ?',
                [id]
            );

            if (!container) {
                return res.status(404).json({
                    success: false,
                    error: 'Container not found'
                });
            }
            
            // Delete container file
            try {
                await fs.unlink(container.path);
            } catch (error) {
                logger.warn(`Failed to delete container file: ${error.message}`);
            }

            // Update database
            await this.db.run(
                'UPDATE containers SET status = "deleted" WHERE id = ?',
                [id]
            );

            res.json({
                success: true,
                message: 'Container successfully deleted'
            });

        } catch (error) {
            logger.error('Delete container error:', error);
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
            const containers = await this.db.all(
                'SELECT id, git_url, created, size FROM containers WHERE status = "active"'
            );
            
            const totalSize = await this.db.get(
                'SELECT SUM(size) as total FROM containers WHERE status = "active"'
            );
            
            res.json({
                success: true,
                data: {
                    containers: containers,
                    total: containers.length,
                    totalSize: totalSize.total || 0
                }
            });

        } catch (error) {
            logger.error('List containers error:', error);
            res.status(500).json({
                success: false,
                error: error.message
            });
        }
    }

    /**
     * API Endpoint: Get container execution stats
     */
    async getContainerStats(req, res) {
        try {
            const { id } = req.params;

            const stats = await this.db.all(
                'SELECT * FROM container_stats WHERE container_id = ? ORDER BY execution_time DESC LIMIT 100',
                [id]
            );

            res.json({
                success: true,
                data: stats
            });

        } catch (error) {
            logger.error('Get container stats error:', error);
            res.status(500).json({
                success: false,
                error: error.message
            });
        }
    }

    /**
     * API Endpoint: Get system information
     */
    async getSystemInfo(req, res) {
        try {
            // Get container count and total size
            const containerStats = await this.db.get(
                'SELECT COUNT(*) as count, SUM(size) as totalSize FROM containers WHERE status = "active"'
            );
            
            // Get execution stats
            const executionStats = await this.db.get(
                'SELECT COUNT(*) as totalExecutions, AVG(exit_code) as avgExitCode FROM container_stats'
            );
            
            // Get disk usage
            let storageUsage;
            try {
                const stats = await fs.stat(this.storageDir);
                storageUsage = stats.size;
            } catch (error) {
                storageUsage = 0;
            }
            
            res.json({
                success: true,
                data: {
                    containerCount: containerStats.count || 0,
                    totalContainerSize: containerStats.totalSize || 0,
                    totalExecutions: executionStats.totalExecutions || 0,
                    averageExitCode: executionStats.avgExitCode || 0,
                    storageUsage: storageUsage,
                    maxContainerSize: this.maxContainerSize,
                    systemTime: new Date().toISOString()
                }
            });

        } catch (error) {
            logger.error('Get system info error:', error);
            res.status(500).json({
                success: false,
                error: error.message
            });
        }
    }

    /**
     * Perform system maintenance tasks
     */
    async performMaintenance() {
        logger.info('Starting system maintenance');
        
        // Cleanup expired containers
        await this.cleanupExpiredContainers();
        
        // Rebuild database indexes
        await this.db.run('REINDEX containers');
        await this.db.run('REINDEX container_stats');
        
        // Vacuum database
        await this.db.run('VACUUM');
        
        logger.info('System maintenance completed');
    }

    /**
     * Cleanup expired containers
     */
    async cleanupExpiredContainers() {
        logger.info('Checking for expired containers');
        
        const expiredContainers = await this.db.all(
            'SELECT * FROM containers WHERE expires_at < ? AND status = "active"',
            [new Date().toISOString()]
        );
        
        if (expiredContainers.length === 0) {
            logger.info('No expired containers found');
            return;
        }
        
        logger.info(`Found ${expiredContainers.length} expired containers, cleaning up...`);
        
        for (const container of expiredContainers) {
            try {
                // Delete container file
                await fs.unlink(container.path);
                
                // Update database
                await this.db.run(
                    'UPDATE containers SET status = "expired" WHERE id = ?',
                    [container.id]
                );
                
                logger.info(`Cleaned up expired container ${container.id}`);
            } catch (error) {
                logger.error(`Failed to cleanup container ${container.id}:`, error);
            }
        }
        
        logger.info('Expired containers cleanup completed');
    }

    /**
     * Get total storage usage
     */
    async getTotalStorageUsage() {
        try {
            const result = await this.db.get(
                'SELECT SUM(size) as total FROM containers WHERE status = "active"'
            );
            return result.total || 0;
        } catch (error) {
            logger.error('Error getting total storage usage:', error);
            return 0;
        }
    }

    /**
     * Start server
     */
    start(port = 3000) {
        return new Promise((resolve) => {
            this.server = this.app.listen(port, async () => {
                await this.ensureStorageDirectory();
                logger.info(`ASU Container System server running on port ${port}`);
                logger.info(`Storage directory: ${this.storageDir}`);
                logger.info(`Database path: ${this.databasePath}`);
                resolve();
            });
        });
    }

    /**
     * Stop server
     */
    stop() {
        return new Promise((resolve) => {
            if (this.server) {
                this.server.close(() => {
                    if (this.db) {
                        this.db.close();
                    }
                    logger.info('Server stopped');
                    resolve();
                });
            } else {
                resolve();
            }
        });
    }
}

// Export for testing and modularity
module.exports = ASUContainerSystem;

// Start server if file is run directly
if (require.main === module) {
    const system = new ASUContainerSystem();
    
    const port = process.env.PORT || 3000;
    system.start(port).catch(error => {
        console.error('Failed to start server:', error);
        process.exit(1);
    });
    
    // Handle shutdown gracefully
    process.on('SIGINT', async () => {
        console.log('\nShutting down server...');
        await system.stop();
        process.exit(0);
    });
    
    process.on('SIGTERM', async () => {
        console.log('\nShutting down server...');
        await system.stop();
        process.exit(0);
    });
}