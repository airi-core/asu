const express = require('express');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const cors = require('cors');
const winston = require('winston');
const cron = require('node-cron');
const Database = require('./database');
const GitService = require('./gitService');
const ContainerService = require('./containerService');
const Security = require('./security');

class ASUContainerSystem {
  constructor() {
    this.app = express();
    this.logger = winston.createLogger({
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

    this.storageDir = path.join(__dirname, 'storage');
    this.sandboxBasePath = path.join(__dirname, 'sandbox');
    this.maxContainerSize = 1024 * 1024 * 1024 * 1024; // 1TB

    this.initializeMiddleware();
    this.initializeRoutes();
  }

  async initialize() {
    try {
      this.db = new Database();
      await this.db.initialize();
      
      this.gitService = new GitService(this.storageDir, this.maxContainerSize);
      this.containerService = new ContainerService(this.storageDir, this.sandboxBasePath);
      
      await this.ensureStorageDirectories();
      this.initializeMaintenanceTasks();
      
      this.logger.info('ASU Container System initialized successfully');
    } catch (error) {
      this.logger.error('Initialization failed:', error);
      throw error;
    }
  }

  async ensureStorageDirectories() {
    try {
      await fs.mkdir(this.storageDir, { recursive: true });
      await fs.mkdir(this.sandboxBasePath, { recursive: true });
      this.logger.info(`Storage directories initialized: ${this.storageDir} and ${this.sandboxBasePath}`);
    } catch (error) {
      this.logger.error('Failed to initialize storage directories:', error);
      throw error;
    }
  }

  initializeMiddleware() {
    this.app.use(helmet());
    
    const limiter = rateLimit({
      windowMs: 15 * 60 * 1000,
      max: 100,
      message: 'Too many requests from this IP, please try again later'
    });
    this.app.use(limiter);
    
    this.app.use(express.json({ limit: '10mb' }));
    this.app.use(express.urlencoded({ extended: true }));
    this.app.use(cors());
    
    this.app.use((req, res, next) => {
      this.logger.info(`${req.method} ${req.path}`);
      next();
    });
  }

  initializeRoutes() {
    this.app.post('/api/containers', this.createContainer.bind(this));
    this.app.get('/api/containers/:id', this.getContainer.bind(this));
    this.app.post('/api/containers/:id/execute', this.executeInContainer.bind(this));
    this.app.delete('/api/containers/:id', this.deleteContainer.bind(this));
    this.app.get('/api/containers', this.listContainers.bind(this));
    this.app.get('/api/containers/:id/stats', this.getContainerStats.bind(this));
    this.app.get('/api/system/info', this.getSystemInfo.bind(this));
    this.app.get('/health', this.healthCheck.bind(this));
  }

  initializeMaintenanceTasks() {
    cron.schedule('0 2 * * *', async () => {
      this.logger.info('Running daily maintenance tasks');
      try {
        await this.performMaintenance();
      } catch (error) {
        this.logger.error('Maintenance task failed:', error);
      }
    });
    
    cron.schedule('0 * * * *', async () => {
      this.logger.info('Running hourly cleanup check');
      try {
        await this.cleanupExpiredContainers();
      } catch (error) {
        this.logger.error('Cleanup task failed:', error);
      }
    });
  }

  // API endpoint implementations...
  // (Implementation similar to original but using the new service classes)
  
  async performMaintenance() {
    this.logger.info('Starting system maintenance');
    await this.cleanupExpiredContainers();
    await this.db.run('REINDEX containers');
    await this.db.run('REINDEX container_stats');
    await this.db.run('VACUUM');
    this.logger.info('System maintenance completed');
  }

  async cleanupExpiredContainers() {
    this.logger.info('Checking for expired containers');
    
    const expiredContainers = await this.db.all(
      'SELECT * FROM containers WHERE expires_at < ? AND status = "active"',
      [new Date().toISOString()]
    );
    
    if (expiredContainers.length === 0) {
      this.logger.info('No expired containers found');
      return;
    }
    
    this.logger.info(`Found ${expiredContainers.length} expired containers, cleaning up...`);
    
    for (const container of expiredContainers) {
      try {
        await fs.unlink(container.path);
        await this.db.run(
          'UPDATE containers SET status = "expired" WHERE id = ?',
          [container.id]
        );
        this.logger.info(`Cleaned up expired container ${container.id}`);
      } catch (error) {
        this.logger.error(`Failed to cleanup container ${container.id}:`, error);
      }
    }
    
    this.logger.info('Expired containers cleanup completed');
  }

  async start(port = 3000) {
    return new Promise((resolve) => {
      this.server = this.app.listen(port, async () => {
        await this.initialize();
        this.logger.info(`ASU Container System server running on port ${port}`);
        resolve();
      });
    });
  }

  async stop() {
    return new Promise((resolve) => {
      if (this.server) {
        this.server.close(async () => {
          if (this.db) {
            await this.db.close();
          }
          this.logger.info('Server stopped');
          resolve();
        });
      } else {
        resolve();
      }
    });
  }
}

module.exports = ASUContainerSystem;

if (require.main === module) {
  const system = new ASUContainerSystem();
  const port = process.env.PORT || 3000;
  
  system.start(port).catch(error => {
    console.error('Failed to start server:', error);
    process.exit(1);
  });
  
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