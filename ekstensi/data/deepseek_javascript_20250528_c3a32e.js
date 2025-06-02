const validator = require('validator');
const crypto = require('crypto');

class Security {
  static sanitizedEnv() {
    return {
      PATH: '/usr/bin:/bin',
      HOME: '/tmp',
      USER: 'sandbox',
      SHELL: '/bin/sh',
      LANG: 'en_US.UTF-8',
      TZ: 'UTC'
    };
  }

  static validateGitUrl(url) {
    if (!url || typeof url !== 'string') {
      throw new Error('Invalid Git URL: URL must be a non-empty string');
    }

    const sanitizedUrl = validator.escape(url.trim());
    
    if (!validator.isURL(sanitizedUrl, { 
      protocols: ['http', 'https', 'git'],
      require_protocol: true 
    })) {
      throw new Error('Invalid Git URL format');
    }

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

  static sanitizeCommand(command, args = []) {
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

    const sanitizedArgs = args.map(arg => {
      if (typeof arg !== 'string') {
        throw new Error('All arguments must be strings');
      }
      
      const dangerous = /[;&|`$(){}[\]<>]/;
      if (dangerous.test(arg)) {
        throw new Error(`Argument contains dangerous characters: ${arg}`);
      }
      
      return arg.trim();
    });

    return { command: baseCommand, args: sanitizedArgs };
  }

  static generateContainerHash() {
    const timestamp = Date.now().toString();
    const randomBytes = crypto.randomBytes(16).toString('hex');
    return crypto.createHash('sha256')
      .update(timestamp + randomBytes)
      .digest('hex');
  }
}

module.exports = Security;