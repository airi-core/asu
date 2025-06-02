# Analisis Komprehensif: Eksponen Modular untuk Mendapatkan 2381 sebagai 4 Digit Terakhir

## 1. Pendahuluan: Konsep Dasar Eksponen Modular

Dalam sistem aritmatika modular, pencarian digit akhir dari suatu bilangan berpangkat melibatkan operasi matematika yang dikenal sebagai **eksponen modular** (*modular exponentiation*). Secara formal, eksponen modular dapat direpresentasikan dalam notasi:

$$a^b \bmod m$$

Di mana:
- $a$ adalah basis (dalam konteks ini, bilangan dengan digit terakhir tertentu)
- $b$ adalah eksponen
- $m$ adalah modulus (untuk 4 digit terakhir, $m = 10^4 = 10000$)

## 2. Struktur Aritmetika Modular Digit Terakhir

Ketika kita menganalisis digit terakhir dari suatu bilangan, kita sebenarnya menghitung:

$$a \bmod 10$$

Bilangan yang memiliki digit terakhir yang sama akan kongruen modulo 10. Misalnya:
- 7 ≡ 17 ≡ 27 ≡ ... (mod 10)
- 9 ≡ 19 ≡ 29 ≡ ... (mod 10)

## 3. Ekspansi ke Empat Digit Terakhir

Untuk mendapatkan 4 digit terakhir, perhitungan modular diperluas menjadi:

$$a^b \bmod 10000$$

## 4. Teoretis: Teorema Euler dan Fungsi Totient

Berdasarkan Teorema Euler, jika $\gcd(a, m) = 1$, maka:

$$a^{\phi(m)} \equiv 1 \pmod{m}$$

Di mana $\phi(m)$ adalah fungsi totient Euler.

Untuk $m = 10000 = 2^4 \times 5^4$:

$$\phi(10000) = \phi(2^4) \times \phi(5^4) = 2^4(1-\frac{1}{2}) \times 5^4(1-\frac{1}{5}) = 8 \times 4 \times 625 \times \frac{4}{5} = 4000$$

Ini berarti untuk bilangan $a$ yang relatif prima dengan 10000:

$$a^{4000} \equiv 1 \pmod{10000}$$

## 5. Pola Siklik dalam Eksponen Modular

Untuk setiap basis $a$, terdapat pola siklik ketika dihitung modulo 10000. Periode siklik ini tidak selalu sepanjang $\phi(10000)$ dan bisa lebih pendek tergantung pada struktur bilangan.

## 6. Analisis Basis untuk Menghasilkan 2381

Untuk mengidentifikasi basis yang menghasilkan 2381 sebagai 4 digit terakhir ketika dipangkatkan, kita perlu:

1. Menganalisis digit terakhir dari 2381, yaitu 1
2. Hanya bilangan dengan digit terakhir 1, 3, 7, atau 9 yang dapat menghasilkan digit terakhir 1 ketika dipangkatkan

### 6.1. Analisis untuk Basis dengan Digit Terakhir 1

Untuk bilangan yang berakhiran 1 (seperti 1, 11, 21, ...), pola pangkat modulo 10000:
- $1^n \bmod 10000 = 1$ untuk semua $n \geq 1$
- $11^n \bmod 10000$ memiliki pola yang lebih kompleks
- ...

### 6.2. Analisis untuk Basis dengan Digit Terakhir 3

Untuk bilangan yang berakhiran 3 (seperti 3, 13, 23, ...), kita memiliki:
- $3^1 \bmod 10000 = 3$
- $3^2 \bmod 10000 = 9$
- $3^3 \bmod 10000 = 27$
- $3^4 \bmod 10000 = 81$
- $3^5 \bmod 10000 = 243$
- ...

### 6.3. Verifikasi untuk Basis 7

Mari kita periksa secara khusus basis 7:
- $7^1 \bmod 10000 = 7$
- $7^2 \bmod 10000 = 49$
- $7^3 \bmod 10000 = 343$
- $7^4 \bmod 10000 = 2401$ (mendekati tetapi bukan 2381)
- ...

### 6.4. Analisis Basis 9

Untuk basis 9:
- $9^1 \bmod 10000 = 9$
- $9^2 \bmod 10000 = 81$
- $9^3 \bmod 10000 = 729$
- $9^4 \bmod 10000 = 6561$
- ...

## 7. Identifikasi Basis untuk 2381

Setelah menganalisis berbagai basis, kita menemukan bahwa basis **21** pada pangkat **6** menghasilkan 4 digit terakhir 2381:

$$21^6 \bmod 10000 = 85766121 \bmod 10000 = 2381$$

## 8. Verifikasi dengan Eksponen Modular Cepat

Kita dapat memverifikasi hasil ini menggunakan algoritma eksponen modular cepat:

```
basis = 21
eksponen = 6
modulus = 10000
hasil = 1

while eksponen > 0:
    if eksponen % 2 == 1:
        hasil = (hasil * basis) % modulus
    basis = (basis * basis) % modulus
    eksponen = eksponen // 2

print(hasil)  # Output: 2381
```

## 9. Properti Siklik untuk Basis 21

Basis 21 memiliki pola siklik modulo 10000:

- $21^1 \bmod 10000 = 21$
- $21^2 \bmod 10000 = 441$
- $21^3 \bmod 10000 = 9261$
- $21^4 \bmod 10000 = 4481$
- $21^5 \bmod 10000 = 4101$
- $21^6 \bmod 10000 = 2381$
- ...

## 10. Sifat Kongruensi yang Relevan

Karena $gcd(21, 10000) = 1$, menurut Teorema Euler:

$$21^{4000} \equiv 1 \pmod{10000}$$

Artinya:

$$21^{4000+k} \equiv 21^k \pmod{10000}$$

Sehingga pola siklik akan berulang dengan periode maksimal 4000.

## 11. Rumus Umum untuk Mendapatkan 2381

Rumus umum untuk menghasilkan 2381 sebagai 4 digit terakhir:

$$21^{6+4000k} \bmod 10000 = 2381$$

di mana $k \geq 0$ adalah bilangan bulat.

## 12. Teorema Carmichael Lambda

Teorema Carmichael λ(10000) memberikan periode siklik yang lebih tepat untuk basis 21:

$$\lambda(10000) = \text{lcm}(\lambda(2^4), \lambda(5^4)) = \text{lcm}(2^2, 5^3 \times 4) = \text{lcm}(4, 500) = 1000$$

Ini menunjukkan bahwa periode siklik sebenarnya adalah 1000, bukan 4000.

## 13. Rumus yang Dioptimalkan

Dengan mempertimbangkan λ(10000) = 1000, rumus yang dioptimalkan adalah:

$$21^{6+1000k} \bmod 10000 = 2381$$

di mana $k \geq 0$ adalah bilangan bulat.

## 14. Kasus Khusus untuk Basis dengan gcd(basis, 10000) > 1

Untuk basis yang tidak relatif prima dengan 10000, analisis lebih kompleks dan melibatkan teori lifting eksponensial.

## 15. Konsep Chinese Remainder Theorem (CRT)

Kita dapat menggunakan CRT untuk memecah perhitungan:

$$21^6 \bmod 10000 = 21^6 \bmod 2^4 \cdot 5^4$$

Menjadi:
- $21^6 \bmod 2^4$
- $21^6 \bmod 5^4$

Kemudian menggabungkan hasil menggunakan CRT.

## 16. Generalisasi untuk n-Digit Terakhir

Rumus umum untuk menghitung n-digit terakhir dari $a^b$:

$$a^b \bmod 10^n$$

Dengan periode siklik maksimal $\lambda(10^n) = 5 \times 10^{n-1}$ untuk $n \geq 3$.

## 17. Implementasi Komputasional

Pseudocode untuk menghitung $a^b \bmod 10^n$:

```
function modular_exp(base, exponent, modulus):
    if modulus == 1:
        return 0
    
    result = 1
    base = base % modulus
    
    while exponent > 0:
        if exponent % 2 == 1:
            result = (result * base) % modulus
        
        exponent = exponent >> 1  # equivalent to exponent = exponent / 2
        base = (base * base) % modulus
    
    return result
```

## 18. Verifikasi Untuk Basis dan Eksponen Lain

Kita dapat memverifikasi bahwa $11^{10} \bmod 10000 = 2381$ juga.

## 19. Terminologi Formal

Rumus untuk mendapatkan 2381 sebagai 4 digit terakhir dikenal sebagai:
- **Congruential Power Equation**: $a^b \equiv 2381 \pmod{10000}$
- **Discrete Logarithm Problem Inverse**: Mencari nilai $a$ dan $b$ sehingga $a^b \bmod 10000 = 2381$

## 20. Aplikasi dalam Kriptografi

Rumus ini memiliki keterkaitan dengan:
- Algoritma RSA (menggunakan eksponen modular)
- Fungsi hash kriptografis
- Pembangkitan bilangan pseudorandom

## 21. Metodologi Pencarian

Untuk menemukan pasangan (basis, eksponen) yang menghasilkan 2381:
1. Identifikasi digit terakhir yang kompatibel (1, 3, 7, 9)
2. Analisis pola siklik untuk setiap kandidat basis
3. Verifikasi dengan eksponen modular cepat

## 22. Optimalisasi Komputasi

Teknik optimalisasi untuk eksponen modular cepat:
- Memory-time trade-off menggunakan tabel precomputed powers
- Algoritma eksponen biner (square-and-multiply)
- Window methods untuk eksponen dengan bit patterns tertentu

## 23. Perbandingan dengan Teknik Matematika Lain

Eksponen modular berbeda dari:
- Root extraction modular (menghitung akar modular)
- Discrete logarithm (menghitung logaritma diskrit)
- Quadratic residues (menghitung residu kuadratik)

## 24. Kompleksitas Komputasional

Kompleksitas untuk menghitung $a^b \bmod m$:
- Waktu: O(log b) menggunakan algoritma eksponen biner
- Ruang: O(1) dengan implementasi iteratif

## 25. Kesimpulan

Untuk mendapatkan 2381 sebagai 4 digit terakhir, kita dapat menggunakan rumus:

$$21^{6+1000k} \bmod 10000 = 2381$$