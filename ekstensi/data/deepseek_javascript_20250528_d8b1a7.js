const validator = require('validator');
const crypto = require('crypto');
const express = require('express');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const cors = require('cors');
const winston = require('winston');
const cron = require('node-cron');
const { spawn } = require('child_process');
const fs = require('fs').promises;
const path = require('path');
const { v4: uuidv4 } = require('uuid');
const tar = require('tar');
const tmp = require('tmp-promise');
const sqlite3 = require('sqlite3').verbose();
const { promisify } = require('util');

// ============== MODUL KEAMANAN ==============
class Keamanan {
  static envBersih() {
    return {
      PATH: '/usr/bin:/bin',
      HOME: '/tmp',
      USER: 'sandbox',
      SHELL: '/bin/sh',
      LANG: 'en_US.UTF-8',
      TZ: 'UTC'
    };
  }

  static validasiUrlGit(url) {
    if (!url || typeof url !== 'string') {
      throw new Error('URL Git tidak valid: URL harus berupa string tidak kosong');
    }

    const urlBersih = validator.escape(url.trim());
    
    if (!validator.isURL(urlBersih, { 
      protocols: ['http', 'https', 'git'],
      require_protocol: true 
    })) {
      throw new Error('Format URL Git tidak valid');
    }

    const polaTerlarang = [
      /^file:\/\//i,
      /localhost/i,
      /127\.0\.0\.1/i,
      /192\.168\./i,
      /10\./i,
      /172\.(1[6-9]|2\d|3[01])\./i
    ];

    for (const pola of polaTerlarang) {
      if (pola.test(urlBersih)) {
        throw new Error('URL Git mengandung alamat yang tidak diizinkan');
      }
    }

    return urlBersih;
  }

  static bersihkanPerintah(perintah, args = []) {
    const perintahTerlarang = [
      'rm', 'del', 'format', 'fdisk', 'mkfs',
      'sudo', 'su', 'chmod', 'chown',
      'wget', 'curl', 'nc', 'netcat',
      'ssh', 'scp', 'ftp', 'telnet',
      'ps', 'kill', 'killall', 'pkill',
      'mount', 'umount', 'dd'
    ];

    const perintahDasar = perintah.toLowerCase().split(' ')[0];
    
    if (perintahTerlarang.includes(perintahDasar)) {
      throw new Error(`Perintah '${perintahDasar}' tidak diizinkan untuk alasan keamanan`);
    }

    const argsBersih = args.map(arg => {
      if (typeof arg !== 'string') {
        throw new Error('Semua argumen harus berupa string');
      }
      
      const berbahaya = /[;&|`$(){}[\]<>]/;
      if (berbahaya.test(arg)) {
        throw new Error(`Argumen mengandung karakter berbahaya: ${arg}`);
      }
      
      return arg.trim();
    });

    return { perintah: perintahDasar, args: argsBersih };
  }

  static buatHashKontainer() {
    const timestamp = Date.now().toString();
    const randomBytes = crypto.randomBytes(16).toString('hex');
    return crypto.createHash('sha256')
      .update(timestamp + randomBytes)
      .digest('hex');
  }
}

// ============== MODUL BASIS DATA ==============
class BasisData {
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

    this.run = promisify(this.db.run.bind(this.db));
    this.get = promisify(this.db.get.bind(this.db));
    this.all = promisify(this.db.all.bind(this.db));
  }

  async inisialisasi() {
    try {
      await this.run(`
        CREATE TABLE IF NOT EXISTS kontainer (
          id TEXT PRIMARY KEY,
          git_url TEXT NOT NULL,
          tipe_versi TEXT,
          nilai_versi TEXT,
          dibuat TEXT NOT NULL,
          ukuran INTEGER NOT NULL,
          path TEXT NOT NULL,
          terakhir_diakses TEXT,
          kadaluarsa TEXT,
          status TEXT DEFAULT 'aktif'
        )
      `);

      await this.run(`
        CREATE TABLE IF NOT EXISTS statistik_kontainer (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          id_kontainer TEXT,
          perintah_dijalankan TEXT,
          waktu_eksekusi TEXT,
          kode_keluar INTEGER,
          FOREIGN KEY(id_kontainer) REFERENCES kontainer(id)
        )
      `);

      this.logger.info('Basis data berhasil diinisialisasi');
    } catch (error) {
      this.logger.error('Gagal menginisialisasi basis data:', error);
      throw error;
    }
  }

  async tutup() {
    return new Promise((resolve) => {
      this.db.close((err) => {
        if (err) {
          this.logger.error('Gagal menutup basis data:', err);
        } else {
          this.logger.info('Koneksi basis data ditutup');
        }
        resolve();
      });
    });
  }
}

// ============== MODUL LAYANAN GIT ==============
class LayananGit {
  constructor(dirPenyimpanan, ukuranMaksKontainer = 1024 * 1024 * 1024 * 1024) {
    this.dirPenyimpanan = dirPenyimpanan;
    this.ukuranMaksKontainer = ukuranMaksKontainer;
    this.logger = winston.createLogger({
      level: 'info',
      format: winston.format.combine(
        winston.format.timestamp(),
        winston.format.json()
      ),
      transports: [new winston.transports.Console()],
    });
  }

  async verifikasiRepositori(url) {
    return new Promise((resolve, reject) => {
      const gitProses = spawn('git', ['ls-remote', '--heads', url], {
        stdio: ['ignore', 'pipe', 'pipe']
      });

      let stdout = '';
      let stderr = '';

      gitProses.stdout.on('data', (data) => {
        stdout += data.toString();
      });

      gitProses.stderr.on('data', (data) => {
        stderr += data.toString();
      });

      gitProses.on('close', (code) => {
        if (code === 0 && stdout.trim()) {
          resolve(true);
        } else {
          reject(new Error(`Repositori tidak dapat diakses: ${stderr || 'Error tidak diketahui'}`));
        }
      });

      gitProses.on('error', (error) => {
        reject(new Error(`Error verifikasi Git: ${error.message}`));
      });
    });
  }

  async klonRepositori(url, dirTarget, tipeVersi = null, nilaiVersi = null) {
    return new Promise((resolve, reject) => {
      const args = ['clone', '--depth', '1'];
      
      if (tipeVersi === 'branch') {
        args.push('--branch', nilaiVersi);
      }
      
      args.push(url, dirTarget);

      const gitProses = spawn('git', args, {
        stdio: ['ignore', 'pipe', 'pipe']
      });

      let stderr = '';

      gitProses.stderr.on('data', (data) => {
        stderr += data.toString();
      });

      gitProses.on('close', (code) => {
        if (code === 0) {
          resolve();
        } else {
          reject(new Error(`Gagal mengklon Git: ${stderr}`));
        }
      });

      gitProses.on('error', (error) => {
        reject(new Error(`Error kloning Git: ${error.message}`));
      });
    });
  }

  async buatArsipKontainer(dirSumber, hashKontainer, urlGit, tipeVersi, nilaiVersi) {
    const pathKontainer = path.join(this.dirPenyimpanan, `${hashKontainer}.asu`);
    
    const metadata = {
      id: hashKontainer,
      git_url: urlGit,
      tipe_versi: tipeVersi,
      nilai_versi: nilaiVersi,
      dibuat: new Date().toISOString(),
      versi: '1.0.0',
      tipe: 'git-repository',
      ekstensi_aman: [
        '.js', '.ts', '.py', '.java', '.c', '.cpp', '.h', '.hpp',
        '.md', '.txt', '.json', '.yml', '.yaml', '.html', '.css'
      ]
    };

    const pathMetadata = path.join(dirSumber, 'metadata.json');
    await fs.writeFile(pathMetadata, JSON.stringify(metadata, null, 2));

    await tar.create({
      gzip: true,
      file: pathKontainer,
      cwd: path.dirname(dirSumber),
    }, [path.basename(dirSumber)]);

    const stats = await fs.stat(pathKontainer);
    if (stats.size > this.ukuranMaksKontainer) {
      await fs.unlink(pathKontainer);
      throw new Error(`Ukuran kontainer (${stats.size}) melebihi batas maksimum (${this.ukuranMaksKontainer})`);
    }

    return {
      path: pathKontainer,
      ukuran: stats.size,
      metadata
    };
  }
}

// ============== MODUL LAYANAN KONTAINER ==============
class LayananKontainer {
  constructor(dirPenyimpanan, pathBaseSandbox) {
    this.dirPenyimpanan = dirPenyimpanan;
    this.pathBaseSandbox = pathBaseSandbox;
    this.logger = winston.createLogger({
      level: 'info',
      format: winston.format.combine(
        winston.format.timestamp(),
        winston.format.json()
      ),
      transports: [new winston.transports.Console()],
    });
  }

  async validasiKontenRepositori(pathRepo) {
    const ekstensiAman = [
      '.js', '.ts', '.py', '.java', '.c', '.cpp', '.h', '.hpp',
      '.md', '.txt', '.json', '.yml', '.yaml', '.html', '.css',
      '.go', '.rs', '.rb', '.php', '.sh'
    ];
    
    const fileBerbahaya = [];
    
    const jelajahDir = async (dir) => {
      const entries = await fs.readdir(dir, { withFileTypes: true });
      
      for (const entry of entries) {
        const pathLengkap = path.join(dir, entry.name);
        
        if (entry.isDirectory()) {
          await jelajahDir(pathLengkap);
        } else {
          const ekstensi = path.extname(entry.name).toLowerCase();
          if (!ekstensiAman.includes(ekstensi)) {
            fileBerbahaya.push({
              path: pathLengkap,
              ekstensi: ekstensi
            });
          }
        }
      }
    };
    
    await jelajahDir(pathRepo);
    
    if (fileBerbahaya.length > 0) {
      const ekstensiBerbahaya = [...new Set(fileBerbahaya.map(f => f.ekstensi))];
      throw new Error(
        `Repositori mengandung file dengan ekstensi berpotensi berbahaya: ${ekstensiBerbahaya.join(', ')}. ` +
        `Ditemukan ${fileBerbahaya.length} file dengan ekstensi ini.`
      );
    }
    
    return true;
  }

  async ekstrakKontainer(hashKontainer) {
    const pathKontainer = path.join(this.dirPenyimpanan, `${hashKontainer}.asu`);
    
    try {
      await fs.access(pathKontainer);
    } catch (error) {
      throw new Error(`Kontainer ${hashKontainer} tidak ditemukan`);
    }

    const pathDirSementara = path.join(this.pathBaseSandbox, `exec-${uuidv4()}`);
    await fs.mkdir(pathDirSementara, { recursive: true });
    
    await tar.extract({
      file: pathKontainer,
      cwd: pathDirSementara
    });

    return {
      path: pathDirSementara,
      bersihkan: async () => {
        try {
          await fs.rm(pathDirSementara, { recursive: true, force: true });
        } catch (error) {
          this.logger.warn(`Gagal membersihkan direktori sementara ${pathDirSementara}:`, error);
        }
      }
    };
  }

  async siapkanLingkunganVirtual(pathEnv, bahasa) {
    try {
      switch (bahasa.toLowerCase()) {
        case 'python':
          return new Promise((resolve, reject) => {
            const prosesVenv = spawn('python3', ['-m', 'venv', path.join(pathEnv, 'venv')], {
              stdio: 'inherit'
            });
            
            prosesVenv.on('close', (code) => {
              if (code === 0) {
                resolve(true);
              } else {
                reject(new Error(`Gagal menyiapkan lingkungan virtual Python dengan kode ${code}`));
              }
            });
            
            prosesVenv.on('error', (error) => {
              reject(new Error(`Error penyiapan lingkungan virtual Python: ${error.message}`));
            });
          });
        
        case 'node':
          return new Promise((resolve, reject) => {
            const prosesNpm = spawn('npm', ['install'], {
              cwd: pathEnv,
              stdio: 'inherit'
            });
            
            prosesNpm.on('close', (code) => {
              if (code === 0) {
                resolve(true);
              } else {
                reject(new Error(`Gagal npm install dengan kode ${code}`));
              }
            });
            
            prosesNpm.on('error', (error) => {
              reject(new Error(`Error npm install: ${error.message}`));
            });
          });
        
        default:
          this.logger.info(`Tidak perlu penyiapan lingkungan khusus untuk ${bahasa}`);
          return true;
      }
    } catch (error) {
      this.logger.error('Gagal menyiapkan lingkungan virtual:', error);
      throw error;
    }
  }

  async jalankanPerintahDiSandbox(perintah, args, dirKerja, timeout = 30000) {
    return new Promise((resolve, reject) => {
      const handleTimeout = setTimeout(() => {
        reject(new Error(`Timeout eksekusi setelah ${timeout}ms`));
      }, timeout);

      const prosesAnak = spawn(perintah, args, {
        cwd: dirKerja,
        env: Keamanan.envBersih(),
        stdio: ['ignore', 'pipe', 'pipe'],
        timeout: timeout
      });

      let stdout = '';
      let stderr = '';

      prosesAnak.stdout.on('data', (data) => {
        stdout += data.toString();
        if (stdout.length > 1024 * 1024) {
          prosesAnak.kill('SIGTERM');
          reject(new Error('Batas ukuran output terlampaui'));
        }
      });

      prosesAnak.stderr.on('data', (data) => {
        stderr += data.toString();
        if (stderr.length > 1024 * 1024) {
          prosesAnak.kill('SIGTERM');
          reject(new Error('Batas ukuran error output terlampaui'));
        }
      });

      prosesAnak.on('close', (code) => {
        clearTimeout(handleTimeout);
        resolve({
          kodeKeluar: code,
          stdout: stdout.trim(),
          stderr: stderr.trim(),
          dijalankanPada: new Date().toISOString()
        });
      });

      prosesAnak.on('error', (error) => {
        clearTimeout(handleTimeout);
        reject(new Error(`Error eksekusi: ${error.message}`));
      });
    });
  }
}

// ============== SISTEM UTAMA ==============
class SistemKontainerASU {
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

    this.dirPenyimpanan = path.join(__dirname, 'penyimpanan');
    this.pathBaseSandbox = path.join(__dirname, 'sandbox');
    this.ukuranMaksKontainer = 1024 * 1024 * 1024 * 1024;

    this.inisialisasiMiddleware();
    this.inisialisasiRute();
  }

  async inisialisasi() {
    try {
      this.basisData = new BasisData();
      await this.basisData.inisialisasi();
      
      this.layananGit = new LayananGit(this.dirPenyimpanan, this.ukuranMaksKontainer);
      this.layananKontainer = new LayananKontainer(this.dirPenyimpanan, this.pathBaseSandbox);
      
      await this.pastikanDirektoriPenyimpanan();
      this.inisialisasiTugasPemeliharaan();
      
      this.logger.info('Sistem Kontainer ASU berhasil diinisialisasi');
    } catch (error) {
      this.logger.error('Gagal inisialisasi:', error);
      throw error;
    }
  }

  async pastikanDirektoriPenyimpanan() {
    try {
      await fs.mkdir(this.dirPenyimpanan, { recursive: true });
      await fs.mkdir(this.pathBaseSandbox, { recursive: true });
      this.logger.info(`Direktori penyimpanan diinisialisasi: ${this.dirPenyimpanan} dan ${this.pathBaseSandbox}`);
    } catch (error) {
      this.logger.error('Gagal menginisialisasi direktori penyimpanan:', error);
      throw error;
    }
  }

  inisialisasiMiddleware() {
    this.app.use(helmet());
    
    const pembatas = rateLimit({
      windowMs: 15 * 60 * 1000,
      max: 100,
      message: 'Terlalu banyak permintaan dari IP ini, silakan coba lagi nanti'
    });
    this.app.use(pembatas);
    
    this.app.use(express.json({ limit: '10mb' }));
    this.app.use(express.urlencoded({ extended: true }));
    this.app.use(cors());
    
    this.app.use((req, res, next) => {
      this.logger.info(`${req.method} ${req.path}`);
      next();
    });
  }

  inisialisasiRute() {
    this.app.post('/api/kontainer', this.buatKontainer.bind(this));
    this.app.get('/api/kontainer/:id', this.dapatkanKontainer.bind(this));
    this.app.post('/api/kontainer/:id/eksekusi', this.eksekusiDiKontainer.bind(this));
    this.app.delete('/api/kontainer/:id', this.hapusKontainer.bind(this));
    this.app.get('/api/kontainer', this.daftarKontainer.bind(this));
    this.app.get('/api/kontainer/:id/statistik', this.dapatkanStatistikKontainer.bind(this));
    this.app.get('/api/sistem/info', this.dapatkanInfoSistem.bind(this));
    this.app.get('/kesehatan', this.cekKesehatan.bind(this));
  }

  inisialisasiTugasPemeliharaan() {
    cron.schedule('0 2 * * *', async () => {
      this.logger.info('Menjalankan tugas pemeliharaan harian');
      try {
        await this.lakukanPemeliharaan();
      } catch (error) {
        this.logger.error('Gagal tugas pemeliharaan:', error);
      }
    });
    
    cron.schedule('0 * * * *', async () => {
      this.logger.info('Menjalankan pemeriksaan pembersihan per jam');
      try {
        await this.bersihkanKontainerKadaluarsa();
      } catch (error) {
        this.logger.error('Gagal tugas pembersihan:', error);
      }
    });
  }

  async lakukanPemeliharaan() {
    this.logger.info('Memulai pemeliharaan sistem');
    await this.bersihkanKontainerKadaluarsa();
    await this.basisData.run('REINDEX kontainer');
    await this.basisData.run('REINDEX statistik_kontainer');
    await this.basisData.run('VACUUM');
    this.logger.info('Pemeliharaan sistem selesai');
  }

  async bersihkanKontainerKadaluarsa() {
    this.logger.info('Memeriksa kontainer kadaluarsa');
    
    const kontainerKadaluarsa = await this.basisData.all(
      'SELECT * FROM kontainer WHERE kadaluarsa < ? AND status = "aktif"',
      [new Date().toISOString()]
    );
    
    if (kontainerKadaluarsa.length === 0) {
      this.logger.info('Tidak ditemukan kontainer kadaluarsa');
      return;
    }
    
    this.logger.info(`Ditemukan ${kontainerKadaluarsa.length} kontainer kadaluarsa, membersihkan...`);
    
    for (const kontainer of kontainerKadaluarsa) {
      try {
        await fs.unlink(kontainer.path);
        await this.basisData.run(
          'UPDATE kontainer SET status = "kadaluarsa" WHERE id = ?',
          [kontainer.id]
        );
        this.logger.info(`Membersihkan kontainer kadaluarsa ${kontainer.id}`);
      } catch (error) {
        this.logger.error(`Gagal membersihkan kontainer ${kontainer.id}:`, error);
      }
    }
    
    this.logger.info('Pembersihan kontainer kadaluarsa selesai');
  }

  async mulai(port = 3000) {
    return new Promise((resolve) => {
      this.server = this.app.listen(port, async () => {
        await this.inisialisasi();
        this.logger.info(`Server Sistem Kontainer ASU berjalan di port ${port}`);
        resolve();
      });
    });
  }

  async berhenti() {
    return new Promise((resolve) => {
      if (this.server) {
        this.server.close(async () => {
          if (this.basisData) {
            await this.basisData.tutup();
          }
          this.logger.info('Server berhenti');
          resolve();
        });
      } else {
        resolve();
      }
    });
  }

  // Implementasi endpoint API...
  async buatKontainer(req, res) {
    try {
      const { urlGit, tipeVersi, nilaiVersi } = req.body;
      
      const urlValid = Keamanan.validasiUrlGit(urlGit);
      await this.layananGit.verifikasiRepositori(urlValid);
      
      const hashKontainer = Keamanan.buatHashKontainer();
      const dirSementara = await tmp.dir({ unsafeCleanup: true });
      
      try {
        await this.layananGit.klonRepositori(urlValid, dirSementara.path, tipeVersi, nilaiVersi);
        await this.layananKontainer.validasiKontenRepositori(dirSementara.path);
        
        const hasil = await this.layananGit.buatArsipKontainer(
          dirSementara.path, 
          hashKontainer, 
          urlValid, 
          tipeVersi, 
          nilaiVersi
        );
        
        await this.basisData.run(
          'INSERT INTO kontainer (id, git_url, tipe_versi, nilai_versi, dibuat, ukuran, path) VALUES (?, ?, ?, ?, ?, ?, ?)',
          [hashKontainer, urlValid, tipeVersi, nilaiVersi, new Date().toISOString(), hasil.ukuran, hasil.path]
        );
        
        res.status(201).json({
          id: hashKontainer,
          metadata: hasil.metadata,
          ukuran: hasil.ukuran
        });
      } finally {
        await dirSementara.cleanup();
      }
    } catch (error) {
      this.logger.error('Gagal membuat kontainer:', error);
      res.status(400).json({ error: error.message });
    }
  }

  async dapatkanKontainer(req, res) {
    try {
      const { id } = req.params;
      const kontainer = await this.basisData.get(
        'SELECT * FROM kontainer WHERE id = ?',
        [id]
      );
      
      if (!kontainer) {
        return res.status(404).json({ error: 'Kontainer tidak ditemukan' });
      }
      
      res.json(kontainer);
    } catch (error) {
      this.logger.error('Gagal mendapatkan kontainer:', error);
      res.status(500).json({ error: error.message });
    }
  }

  async eksekusiDiKontainer(req, res) {
    try {
      const { id } = req.params;
      const { perintah, args, bahasa } = req.body;
      
      const kontainer = await this.basisData.get(
        'SELECT * FROM kontainer WHERE id = ? AND status = "aktif"',
        [id]
      );
      
      if (!kontainer) {
        return res.status(404).json({ error: 'Kontainer tidak ditemukan atau tidak aktif' });
      }
      
      const perintahBersih = Keamanan.bersihkanPerintah(perintah, args);
      const ekstraksi = await this.layananKontainer.ekstrakKontainer(id);
      
      try {
        await this.layananKontainer.siapkanLingkunganVirtual(ekstraksi.path, bahasa);
        
        const hasil = await this.layananKontainer.jalankanPerintahDiSandbox(
          perintahBersih.perintah,
          perintahBersih.args,
          ekstraksi.path
        );
        
        await this.basisData.run(
          'INSERT INTO statistik_kontainer (id_kontainer, perintah_dijalankan, waktu_eksekusi, kode_keluar) VALUES (?, ?, ?, ?)',
          [id, perintah, hasil.dijalankanPada, hasil.kodeKeluar]
        );
        
        res.json(hasil);
      } finally {
        await ekstraksi.bersihkan();
      }
    } catch (error) {
      this.logger.error('Gagal mengeksekusi perintah di kontainer:', error);
      res.status(400).json({ error: error.message });
    }
  }

  async hapusKontainer(req, res) {
    try {
      const { id } = req.params;
      
      const kontainer = await this.basisData.get(
        'SELECT * FROM kontainer WHERE id = ?',
        [id]
      );
      
      if (!kontainer) {
        return res.status(404).json({ error: 'Kontainer tidak ditemukan' });
      }
      
      await fs.unlink(kontainer.path);
      await this.basisData.run(
        'UPDATE kontainer SET status = "dihapus" WHERE id = ?',
        [id]
      );
      
      res.status(204).end();
    } catch (error) {
      this.logger.error('Gagal menghapus kontainer:', error);
      res.status(500).json({ error: error.message });
    }
  }

  async daftarKontainer(req, res) {
    try {
      const kontainer = await this.basisData.all(
        'SELECT id, git_url, tipe_versi, nilai_versi, dibuat, ukuran, status FROM kontainer'
      );
      res.json(kontainer);
    } catch (error) {
      this.logger.error('Gagal mendapatkan daftar kontainer:', error);
      res.status(500).json({ error: error.message });
    }
  }

  async dapatkanStatistikKontainer(req, res) {
    try {
      const { id } = req.params;
      const statistik = await this.basisData.all(
        'SELECT * FROM statistik_kontainer WHERE id_kontainer = ?',
        [id]
      );
      res.json(statistik);
    } catch (error) {
      this.logger.error('Gagal mendapatkan statistik kontainer:', error);
      res.status(500).json({ error: error.message });
    }
  }

  async dapatkanInfoSistem(req, res) {
    try {
      const totalKontainer = await this.basisData.get(
        'SELECT COUNT(*) as total FROM kontainer'
      );
      
      const totalUkuran = await this.basisData.get(
        'SELECT SUM(ukuran) as total FROM kontainer'
      );
      
      res.json({
        versi: '1.0.0',
        total_kontainer: totalKontainer.total,
        total_ukuran: totalUkuran.total || 0,
        status: 'aktif'
      });
    } catch (error) {
      this.logger.error('Gagal mendapatkan info sistem:', error);
      res.status(500).json({ error: error.message });
    }
  }

  async cekKesehatan(req, res) {
    try {
      await this.basisData.get('SELECT 1');
      res.json({ status: 'sehat' });
    } catch (error) {
      this.logger.error('Pemeriksaan kesehatan gagal:', error);
      res.status(500).json({ status: 'tidak sehat', error: error.message });
    }
  }
}

// ============== JALANKAN SERVER ==============
if (require.main === module) {
  const sistem = new SistemKontainerASU();
  const port = process.env.PORT || 3000;
  
  sistem.mulai(port).catch(error => {
    console.error('Gagal memulai server:', error);
    process.exit(1);
  });
  
  process.on('SIGINT', async () => {
    console.log('\nMenghentikan server...');
    await sistem.berhenti();
    process.exit(0);
  });
  
  process.on('SIGTERM', async () => {
    console.log('\nMenghentikan server...');
    await sistem.berhenti();
    process.exit(0);
  });
}

module.exports = {
  Keamanan,
  BasisData,
  LayananGit,
  LayananKontainer,
  SistemKontainerASU
};