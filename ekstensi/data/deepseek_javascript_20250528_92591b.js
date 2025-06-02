const { spawn } = require('child_process');
const fs = require('fs').promises;
const path = require('path');
const { v4: uuidv4 } = require('uuid');
const tar = require('tar');
const winston = require('winston');

class ContainerService {
  constructor(storageDir, sandboxBasePath) {
    this.storageDir = storageDir;
    this.sandboxBasePath = sandboxBasePath;
    this.logger = winston.createLogger({
      level: 'info',
      format: winston.format.combine(
        winston.format.timestamp(),
        winston.format.json()
      ),
      transports: [new winston.transports.Console()],
    });
  }

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

  async extractContainer(containerHash) {
    const containerPath = path.join(this.storageDir, `${containerHash}.asu`);
    
    try {
      await fs.access(containerPath);
    } catch (error) {
      throw new Error(`Container ${containerHash} not found`);
    }

    const tempDirPath = path.join(this.sandboxBasePath, `exec-${uuidv4()}`);
    await fs.mkdir(tempDirPath, { recursive: true });
    
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
          this.logger.warn(`Failed to cleanup temp dir ${tempDirPath}:`, error);
        }
      }
    };
  }

  async setupVirtualEnvironment(envPath, language) {
    try {
      switch (language.toLowerCase()) {
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
          this.logger.info(`No specific environment setup needed for ${language}`);
          return true;
      }
    } catch (error) {
      this.logger.error('Virtual environment setup failed:', error);
      throw error;
    }
  }

  async executeCommandInSandbox(command, args, workingDir, timeout = 30000) {
    return new Promise((resolve, reject) => {
      const timeoutHandle = setTimeout(() => {
        reject(new Error(`Execution timeout after ${timeout}ms`));
      }, timeout);

      const childProcess = spawn(command, args, {
        cwd: workingDir,
        env: Security.sanitizedEnv(),
        stdio: ['ignore', 'pipe', 'pipe'],
        timeout: timeout
      });

      let stdout = '';
      let stderr = '';

      childProcess.stdout.on('data', (data) => {
        stdout += data.toString();
        if (stdout.length > 1024 * 1024) {
          childProcess.kill('SIGTERM');
          reject(new Error('Output size limit exceeded'));
        }
      });

      childProcess.stderr.on('data', (data) => {
        stderr += data.toString();
        if (stderr.length > 1024 * 1024) {
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
}

module.exports = ContainerService;