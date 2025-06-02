const sqlite3 = require('sqlite3').verbose();
const { promisify } = require('util');
const path = require('path');
const winston = require('winston');

class Database {
  constructor(dbPath = path.join(__dirname, 'asu-container.db')) {
    this.db = new sqlite3.Database(dbPath);
    this.logger = winston.createLogger({
      level: 'info',
      format: winston.format.combine(
        winston.format.timestamp(),
        winston.format.json()
      ),
      transports: [new winston.transports.Console()],
    });

    // Promisify database methods
    this.run = promisify(this.db.run.bind(this.db));
    this.get = promisify(this.db.get.bind(this.db));
    this.all = promisify(this.db.all.bind(this.db));
  }

  async initialize() {
    try {
      await this.run(`
        CREATE TABLE IF NOT EXISTS containers (
          id TEXT PRIMARY KEY,
          git_url TEXT NOT NULL,
          version_type TEXT,
          version_value TEXT,
          created TEXT NOT NULL,
          size INTEGER NOT NULL,
          path TEXT NOT NULL,
          last_accessed TEXT,
          expires_at TEXT,
          status TEXT DEFAULT 'active'
        )
      `);

      await this.run(`
        CREATE TABLE IF NOT EXISTS container_stats (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          container_id TEXT,
          command_executed TEXT,
          execution_time TEXT,
          exit_code INTEGER,
          FOREIGN KEY(container_id) REFERENCES containers(id)
        )
      `);

      this.logger.info('Database initialized successfully');
    } catch (error) {
      this.logger.error('Database initialization failed:', error);
      throw error;
    }
  }

  async close() {
    return new Promise((resolve) => {
      this.db.close((err) => {
        if (err) {
          this.logger.error('Error closing database:', err);
        } else {
          this.logger.info('Database connection closed');
        }
        resolve();
      });
    });
  }
}

module.exports = Database;