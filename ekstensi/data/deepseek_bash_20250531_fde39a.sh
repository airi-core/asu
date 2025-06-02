# 1. Buat metadata.json
{
  "name": "My Research App",
  "type": "docker",
  "docker": {
    "image": "python:3.9",
    "git_repo": "https://github.com/myresearch/app.git",
    "dockerfile": "FROM python:3.9\nWORKDIR /app\nCOPY . .\nRUN pip install -r requirements.txt\nCMD [\"python\", \"main.py\"]",
    "dependencies": ["numpy", "pandas"],
    "environment": {
      "ENV": "production"
    },
    "volumes": ["/data:/app/data"]
  }
}

# 2. Buat file WASU
wasu create metadata.json ./app myresearch.wasu

# 3. Verifikasi integritas
wasu verify myresearch.wasu

# 4. Eksekusi
wasu execute myresearch.wasu

# 5. Ekstrak payload
wasu extract myresearch.wasu extracted.tar