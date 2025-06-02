const { spawn } = require('child_process');
const fs = require('fs').promises;
const path = require('path');
const tmp = require('tmp-promise');
const winston = require('winston');
const tar = require('tar');

class GitService {
  constructor(storageDir, maxContainerSize = 1024 * 1024 * 1024 * 1024) {
    this.storageDir = storageDir;
    this.maxContainerSize = maxContainerSize;
    this.logger = winston.createLogger({
      level: 'info',
      format: winston.format.combine(
        winston.format.timestamp(),
        winston.format.json()
      ),
      transports: [new winston.transports.Console()],
    });
  }

  async verifyRepository(url) {
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

  async cloneRepository(url, targetDir, versionType = null, versionValue = null) {
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error('Timeout: Git clone took too long (>10 minutes)'));
      }, 600000);

      const args = ['clone', '--depth', '1'];
      
      if (versionType === 'branch') {
        args.push('--branch', versionValue);
      }
      
      args.push(url, targetDir);

      const gitProcess = spawn('git', args, {
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

  async createContainerArchive(sourceDir, containerHash, gitUrl, versionType, versionValue) {
    const containerPath = path.join(this.storageDir, `${containerHash}.asu`);
    
    const metadata = {
      id: containerHash,
      git_url: gitUrl,
      version_type: versionType,
      version_value: versionValue,
      created: new Date().toISOString(),
      version: '1.0.0',
      type: 'git-repository',
      safe_extensions: [
        '.js', '.ts', '.py', '.java', '.c', '.cpp', '.h', '.hpp',
        '.md', '.txt', '.json', '.yml', '.yaml', '.html', '.css'
      ]
    };

    const metadataPath = path.join(sourceDir, 'metadata.json');
    await fs.writeFile(metadataPath, JSON.stringify(metadata, null, 2));

    await tar.create({
      gzip: true,
      file: containerPath,
      cwd: path.dirname(sourceDir),
    }, [path.basename(sourceDir)]);

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
}

module.exports = GitService;