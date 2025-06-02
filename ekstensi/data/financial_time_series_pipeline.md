# SanClass Trading Labs

# Pipeline Analisis Deret Waktu untuk Model AI di Pasar Keuangan

## Daftar Isi
1. [Pendahuluan](#pendahuluan)
2. [Pipeline Standar Industri](#pipeline-standar-industri)
3. [Tahapan Pipeline](#tahapan-pipeline)
   - [Pengumpulan Data](#pengumpulan-data)
   - [Pembersihan Data](#pembersihan-data)
   - [Analisis Eksploratori](#analisis-eksploratori)
   - [Rekayasa Fitur](#rekayasa-fitur)
   - [Pemodelan](#pemodelan)
   - [Evaluasi Model](#evaluasi-model)
   - [Penerapan Model](#penerapan-model)
   - [Pemantauan dan Pemeliharaan](#pemantauan-dan-pemeliharaan)
4. [Implementasi dengan Keras](#implementasi-dengan-keras)
   - [Komponen-Komponen Keras untuk Analisis Deret Waktu](#komponen-komponen-keras-untuk-analisis-deret-waktu)
   - [Arsitektur Model Sukses](#arsitektur-model-sukses)
   - [Optimasi dan Efisiensi](#optimasi-dan-efisiensi)
5. [Studi Kasus dan Implementasi Nyata](#studi-kasus-dan-implementasi-nyata)
6. [Implikasi Keamanan](#implikasi-keamanan)
7. [Kesimpulan](#kesimpulan)

## Pendahuluan

Analisis deret waktu menggunakan model AI telah menjadi pendekatan yang sangat penting dalam menganalisis dan memprediksi pergerakan harga di pasar keuangan. Dokumen ini menyajikan pipeline komprehensif untuk mengembangkan model deret waktu yang efektif dengan fokus pada penggunaan Keras sebagai kerangka kerja utama.

Pipeline yang kita bahas mengintegrasikan praktik terbaik industri dengan penekanan khusus pada optimasi data, efisiensi pelatihan, dan evaluasi model yang ketat sesuai standar industri keuangan. Kita akan meneliti setiap tahapan proses dari pengumpulan data mentah hingga implementasi model yang terlatih untuk prediksi pasar keuangan.

## Pipeline Standar Industri

Pipeline analisis deret waktu untuk model AI di pasar keuangan mengikuti alur kerja terstruktur yang telah menjadi standar dalam industri fintech dan trading algoritmik. Pendekatan ini memastikan proses pengembangan yang sistematis dan hasil yang dapat diandalkan.

```
┌────────────────┐    ┌────────────────┐    ┌────────────────┐    ┌────────────────┐
│  Pengumpulan   │ ─> │  Pembersihan   │ ─> │    Analisis    │ ─> │   Rekayasa     │
│     Data       │    │     Data       │    │  Eksploratori  │    │    Fitur       │
└────────────────┘    └────────────────┘    └────────────────┘    └────────────────┘
         │                                                                │
         │                                                                ▼
┌────────────────┐    ┌────────────────┐    ┌────────────────┐    ┌────────────────┐
│  Pemantauan &  │ <─ │   Penerapan    │ <─ │    Evaluasi    │ <─ │   Pemodelan    │
│  Pemeliharaan  │    │     Model      │    │     Model      │    │                │
└────────────────┘    └────────────────┘    └────────────────┘    └────────────────┘
```

## Tahapan Pipeline

### Pengumpulan Data

Pengumpulan data yang efektif dan efisien merupakan landasan dari keseluruhan pipeline. Untuk pasar keuangan, kita menggunakan API MetaTrader 5 sebagai sumber data utama.

```python
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
import pytz

def collect_market_data(symbol, timeframe, start_date, end_date):
    """
    Mengumpulkan data historis pasar menggunakan API MetaTrader 5
    
    Parameters:
    -----------
    symbol : str
        Simbol instrumen keuangan (misal: "XAUUSD")
    timeframe : int
        Timeframe data (misalnya mt5.TIMEFRAME_H1 untuk data per jam)
    start_date : datetime
        Tanggal awal pengumpulan data
    end_date : datetime
        Tanggal akhir pengumpulan data
    
    Returns:
    --------
    pandas.DataFrame
        Data historis dalam format pandas DataFrame
    """
    # Inisialisasi koneksi dengan MetaTrader 5
    if not mt5.initialize():
        print(f"Inisialisasi gagal, kode error: {mt5.last_error()}")
        return None
    
    # Mengatur timezone ke UTC untuk konsistensi
    timezone = pytz.timezone("Etc/UTC")
    start_date = datetime(start_date.year, start_date.month, start_date.day, tzinfo=timezone)
    end_date = datetime(end_date.year, end_date.month, end_date.day, tzinfo=timezone)
    
    # Mengambil data historis
    rates = mt5.copy_rates_range(symbol, timeframe, start_date, end_date)
    
    # Menutup koneksi dengan MetaTrader 5
    mt5.shutdown()
    
    if rates is None or len(rates) == 0:
        print("Tidak ada data yang diterima")
        return None
    
    # Konversi ke DataFrame
    df = pd.DataFrame(rates)
    
    # Konversi timestamp menjadi format datetime
    df['time'] = pd.to_datetime(df['time'], unit='s')
    
    return df

# Contoh penggunaan
if __name__ == "__main__":
    # Definiskan parameter
    symbol = "XAUUSD"  # Gold/USD
    timeframe = mt5.TIMEFRAME_H1  # Data per jam
    
    # Tanggal untuk pengumpulan data
    start = datetime(2023, 1, 1)
    end = datetime(2024, 1, 1)
    
    # Dapatkan data
    gold_data = collect_market_data(symbol, timeframe, start, end)
    
    if gold_data is not None:
        print(f"Berhasil mengumpulkan {len(gold_data)} data poin")
        print(gold_data.head())
```

Praktik keamanan yang diimplementasikan:
- Penutupan koneksi setelah pengambilan data
- Validasi keberhasilan operasi
- Penanganan kesalahan untuk kegagalan koneksi
- Penggunaan timezone yang konsisten (UTC)

### Pembersihan Data

Pembersihan data melibatkan penanganan nilai yang hilang, outlier, dan memastikan konsistensi data. Langkah ini krusial untuk memastikan kualitas model.

```python
def clean_market_data(df):
    """
    Membersihkan data pasar keuangan
    
    Parameters:
    -----------
    df : pandas.DataFrame
        DataFrame yang berisi data pasar
    
    Returns:
    --------
    pandas.DataFrame
        DataFrame yang telah dibersihkan
    """
    # Membuat salinan data untuk menghindari modifikasi pada data asli
    df_clean = df.copy()
    
    # Menetapkan indeks waktu
    df_clean.set_index('time', inplace=True)
    
    # Deteksi nilai yang hilang
    missing_values = df_clean.isnull().sum()
    print(f"Nilai yang hilang sebelum pembersihan:\n{missing_values}")
    
    # Mengisi nilai yang hilang dengan metode forward fill
    # Forward fill lebih disukai untuk data deret waktu
    df_clean.fillna(method='ffill', inplace=True)
    
    # Jika masih ada nilai yang hilang di awal data, gunakan backward fill
    df_clean.fillna(method='bfill', inplace=True)
    
    # Deteksi dan penanganan outlier menggunakan metode IQR
    for column in ['open', 'high', 'low', 'close']:
        if column in df_clean.columns:
            Q1 = df_clean[column].quantile(0.25)
            Q3 = df_clean[column].quantile(0.75)
            IQR = Q3 - Q1
            
            # Definisikan batas untuk outlier
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            # Identifikasi outlier
            outliers = ((df_clean[column] < lower_bound) | 
                        (df_clean[column] > upper_bound))
            
            print(f"Jumlah outlier di kolom {column}: {outliers.sum()}")
            
            # Untuk data keuangan, kita biasanya tidak menghapus outlier
            # karena dapat mewakili peristiwa pasar penting
            # Namun, kita dapat menandainya untuk analisis selanjutnya
            df_clean[f'{column}_outlier'] = outliers
    
    # Memeriksa keseragaman data
    # Pastikan data memiliki interval yang konsisten
    time_diff = df_clean.index.to_series().diff().value_counts()
    if len(time_diff) > 1:
        print("Peringatan: Data memiliki interval waktu yang tidak konsisten")
        print(time_diff)
    
    # Hapus duplikasi jika ada
    duplicates = df_clean.index.duplicated()
    if duplicates.any():
        print(f"Menemukan {duplicates.sum()} data duplikat. Menghapus...")
        df_clean = df_clean[~duplicates]
    
    return df_clean
```

Praktik keamanan yang diimplementasikan:
- Menggunakan salinan data untuk menghindari modifikasi data asli
- Validasi dan pelaporan untuk masalah data
- Pendekatan konservatif terhadap outlier dalam data keuangan
- Pengecekan konsistensi interval waktu

### Analisis Eksploratori

Analisis eksploratori data (EDA) membantu kita memahami karakteristik data dan mendapatkan wawasan awal untuk rekayasa fitur dan pemodelan.

```python
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

def perform_eda(df):
    """
    Melakukan analisis eksploratori pada data pasar keuangan
    
    Parameters:
    -----------
    df : pandas.DataFrame
        DataFrame yang berisi data pasar
    """
    # Statistik deskriptif
    print("Statistik Deskriptif:")
    print(df.describe())
    
    # Plot harga penutupan
    plt.figure(figsize=(14, 7))
    plt.plot(df.index, df['close'])
    plt.title('Harga Penutupan dari Waktu ke Waktu')
    plt.xlabel('Tanggal')
    plt.ylabel('Harga')
    plt.grid(True)
    plt.tight_layout()
    plt.savefig('close_price_time_series.png', dpi=300)
    plt.close()
    
    # Analisis perubahan harga harian
    df['daily_return'] = df['close'].pct_change() * 100
    
    plt.figure(figsize=(14, 7))
    plt.plot(df.index, df['daily_return'])
    plt.title('Perubahan Harga Harian (%)')
    plt.xlabel('Tanggal')
    plt.ylabel('Perubahan (%)')
    plt.grid(True)
    plt.tight_layout()
    plt.savefig('daily_returns.png', dpi=300)
    plt.close()
    
    # Distribusi perubahan harian
    plt.figure(figsize=(14, 7))
    sns.histplot(df['daily_return'].dropna(), kde=True)
    plt.title('Distribusi Perubahan Harga Harian')
    plt.xlabel('Perubahan (%)')
    plt.ylabel('Frekuensi')
    plt.grid(True)
    plt.tight_layout()
    plt.savefig('daily_returns_distribution.png', dpi=300)
    plt.close()
    
    # Analisis volatilitas dengan rolling window
    df['volatility'] = df['daily_return'].rolling(window=20).std()
    
    plt.figure(figsize=(14, 7))
    plt.plot(df.index, df['volatility'])
    plt.title('Volatilitas 20-Hari')
    plt.xlabel('Tanggal')
    plt.ylabel('Volatilitas (%)')
    plt.grid(True)
    plt.tight_layout()
    plt.savefig('volatility.png', dpi=300)
    plt.close()
    
    # Plot heatmap korelasi
    corr_matrix = df[['open', 'high', 'low', 'close', 'daily_return', 'volatility']].corr()
    plt.figure(figsize=(10, 8))
    sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', fmt='.2f')
    plt.title('Matriks Korelasi')
    plt.tight_layout()
    plt.savefig('correlation_matrix.png', dpi=300)
    plt.close()
    
    # Analisis autocorrelation untuk memeriksa dependensi temporal
    from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
    
    plt.figure(figsize=(14, 7))
    plot_acf(df['close'].dropna(), lags=40, ax=plt.gca())
    plt.title('Fungsi Autokorelasi untuk Harga Penutupan')
    plt.grid(True)
    plt.tight_layout()
    plt.savefig('acf_close.png', dpi=300)
    plt.close()
    
    plt.figure(figsize=(14, 7))
    plot_pacf(df['close'].dropna(), lags=40, ax=plt.gca())
    plt.title('Fungsi Autokorelasi Parsial untuk Harga Penutupan')
    plt.grid(True)
    plt.tight_layout()
    plt.savefig('pacf_close.png', dpi=300)
    plt.close()
    
    return df
```

Praktik keamanan yang diimplementasikan:
- Penyimpanan gambar dengan kualitas tinggi untuk analisis
- Penanganan nilai yang hilang dalam perhitungan
- Pemisahan visualisasi untuk memastikan memanfaatkan sumber daya komputer secara efisien

### Rekayasa Fitur

Rekayasa fitur adalah proses mengubah data mentah menjadi fitur yang lebih bermakna bagi model. Untuk analisis deret waktu pada pasar keuangan, kita akan menerapkan rekayasa fitur berdasarkan formula SanClass Trading Labs.

```python
def engineer_features(df):
    """
    Melakukan rekayasa fitur berdasarkan formula SanClass Trading Labs
    
    Parameters:
    -----------
    df : pandas.DataFrame
        DataFrame yang berisi data pasar
    
    Returns:
    --------
    pandas.DataFrame
        DataFrame dengan fitur baru
    """
    # Pastikan data terurut berdasarkan waktu
    df = df.sort_index()
    
    # 1. Analisis Trend
    # Asia: open 1mt saat ini - close 14mt hari sebelumnya
    df['as_diff'] = df['open'].diff()
    df['as_trend'] = df['as_diff'].apply(lambda x: 'bullish' if x > 0 else 'bearish' if x < 0 else 'sideway')
    
    # Eropa: open 9mt saat ini - close 23mt hari sebelumnya
    # Implementasi sederhana menggunakan shift
    df['eu_diff'] = df['open'].shift(-8) - df['close'].shift(1)
    df['eu_trend'] = df['eu_diff'].apply(lambda x: 'bullish' if x > 0 else 'bearish' if x < 0 else 'sideway')
    
    # Amerika: open 15mt saat ini - close 8mt hari ini
    df['am_diff'] = df['open'].shift(-14) - df['close'].shift(-7)
    df['am_trend'] = df['am_diff'].apply(lambda x: 'bullish' if x > 0 else 'bearish' if x < 0 else 'sideway')
    
    # 2. Volatilitas Basic
    # Menghitung range harian (high - low)
    df['daily_range'] = df['high'] - df['low']
    
    # Kategorikan volatilitas
    def categorize_volatility(x):
        if x > 10:
            return 'tinggi'
        elif x > 5:
            return 'sedang'
        else:
            return 'rendah'
    
    df['volatility_category'] = df['daily_range'].apply(categorize_volatility)
    
    # 3. Volatilitas Sesi
    # Asia
    df['t_u_as'] = df['high'].shift(1) - 21  # high amrik kemarin - 21
    df['t_d_as'] = df['low'].shift(1) + 21   # low amrik kemarin + 21
    
    # Eropa
    # Asumsikan 'high asia' adalah high dari 8 periode sebelumnya
    df['t_u_eu'] = df['high'] - 8            # high asia sekarang - 8
    df['t_d_eu'] = df['low'] + 8             # low asia sekarang + 8
    
    # Amerika
    # Asumsikan 'high eropa' adalah high dari 6 periode sebelumnya
    df['t_u_am'] = df['high'].shift(-6) - 13 # high eropa sekarang - 13
    df['t_d_am'] = df['low'].shift(-6) + 13  # low eropa sekarang + 13
    
    # 4. Sentimen
    # Fungsi untuk menganalisis sentimen berdasarkan close dan trigger
    def analyze_sentiment(row):
        close = row['close']
        t_u = row['t_u_as'] if pd.notna(row['t_u_as']) else (row['t_u_eu'] if pd.notna(row['t_u_eu']) else row['t_u_am'])
        t_d = row['t_d_as'] if pd.notna(row['t_d_as']) else (row['t_d_eu'] if pd.notna(row['t_d_eu']) else row['t_d_am'])
        
        if pd.notna(t_u) and pd.notna(t_d):
            if close > t_u and close > t_d:
                return 'bullish'
            elif close < t_u and close < t_d:
                return 'bearish'
            elif close < t_u and close > t_d:
                return 'consolidation'
        return None
    
    df['sentiment'] = df.apply(analyze_sentiment, axis=1)
    
    # 5. Signals
    # Fungsi untuk menganalisis sinyal berdasarkan close dan trigger
    def analyze_signal(row):
        close = row['close']
        t_u = row['t_u_as'] if pd.notna(row['t_u_as']) else (row['t_u_eu'] if pd.notna(row['t_u_eu']) else row['t_u_am'])
        t_d = row['t_d_as'] if pd.notna(row['t_d_as']) else (row['t_d_eu'] if pd.notna(row['t_d_eu']) else row['t_d_am'])
        
        if pd.notna(t_u) and pd.notna(t_d):
            if t_u > t_d and close > t_u and close > t_d:
                return 'bullish'
            elif t_d < t_u and close < t_d and close < t_u:
                return 'bearish'
            elif t_u < t_d and close > t_u and close < t_d:
                return 'consolidation'
        return None
    
    df['signal'] = df.apply(analyze_signal, axis=1)
    
    # Tambahan fitur teknikal umum untuk memperkaya model
    
    # Moving Average
    df['MA5'] = df['close'].rolling(window=5).mean()
    df['MA20'] = df['close'].rolling(window=20).mean()
    df['MA50'] = df['close'].rolling(window=50).mean()
    
    # MACD
    df['EMA12'] = df['close'].ewm(span=12, adjust=False).mean()
    df['EMA26'] = df['close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = df['EMA12'] - df['EMA26']
    df['MACD_signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_hist'] = df['MACD'] - df['MACD_signal']
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    RS = gain / loss
    df['RSI'] = 100 - (100 / (1 + RS))
    
    # Bollinger Bands
    df['BB_middle'] = df['close'].rolling(window=20).mean()
    df['BB_std'] = df['close'].rolling(window=20).std()
    df['BB_upper'] = df['BB_middle'] + (df['BB_std'] * 2)
    df['BB_lower'] = df['BB_middle'] - (df['BB_std'] * 2)
    
    # Hapus baris dengan nilai NaN karena perhitungan rolling window
    df = df.dropna()
    
    return df
```

Praktik keamanan yang diimplementasikan:
- Penanganan nilai yang hilang secara eksplisit
- Validasi data sebelum operasi matematika
- Perhitungan indikator teknikal dengan metode standar industri

### Pemodelan

Pada tahap pemodelan, kita menggunakan Keras untuk membangun model deret waktu seperti LSTM atau GRU yang cocok untuk analisis pasar keuangan. Komponen Keras sangat optimal untuk analisis deret waktu di pasar keuangan karena kemampuannya untuk menangkap dependensi temporal jangka panjang dalam data.

#### Komponen-Komponen Keras untuk Analisis Deret Waktu

Keras menyediakan berbagai lapisan dan komponen yang sangat bermanfaat untuk pemodelan deret waktu di pasar keuangan:

1. **Lapisan LSTM (Long Short-Term Memory)**
   - Ideal untuk menangkap dependensi jangka panjang dalam data deret waktu
   - Memiliki gerbang yang mengontrol aliran informasi yang memungkinkan model "mengingat" atau "melupakan" informasi yang relevan
   - Sangat efektif untuk data pasar keuangan yang memiliki pola musiman atau tren jangka panjang

2. **Lapisan GRU (Gated Recurrent Unit)**
   - Alternatif yang lebih ringan untuk LSTM dengan jumlah parameter yang lebih sedikit
   - Lebih cepat untuk dilatih
   - Sering memberikan kinerja yang sebanding dengan LSTM, terutama untuk dataset yang lebih kecil

3. **Lapisan BatchNormalization**
   - Mempercepat pelatihan dengan menormalkan aktivasi dari lapisan sebelumnya
   - Membuat model lebih stabil dan mengurangi overfitting
   - Sangat berguna untuk data keuangan dengan volatilitas tinggi

4. **Lapisan Dropout**
   - Mencegah overfitting dengan secara acak menonaktifkan neuron selama pelatihan
   - Membantu model untuk generalisasi ke data baru
   - Penting dalam konteks keuangan di mana terlalu mengandalkan kebiasaan historis bisa berbahaya

5. **Fungsi Aktivasi**
   - ReLU (Rectified Linear Unit): Mengatasi masalah vanishing gradient, memungkinkan pelatihan lebih cepat
   - Sigmoid: Berguna untuk output biner (misalnya, prediksi naik/turun)
   - Tanh: Sering digunakan dalam lapisan LSTM/GRU untuk memberi batasan pada nilai dalam rentang [-1, 1]

6. **Callbacks**
   - EarlyStopping: Menghentikan pelatihan ketika model berhenti membaik, menghemat waktu dan mencegah overfitting
   - ModelCheckpoint: Menyimpan model terbaik berdasarkan metrik yang dipilih
   - ReduceLROnPlateau: Mengurangi learning rate ketika kinerja model stagnan

```python
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, GRU, Dense, Dropout, BatchNormalization
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau
from tensorflow.keras.optimizers import Adam
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import TimeSeriesSplit

def prepare_time_series_data(df, target_col='close', feature_cols=None, n_steps=60, n_features=None, test_size=0.2):
    """
    Mempersiapkan data deret waktu untuk model prediktif
    
    Parameters:
    -----------
    df : pandas.DataFrame
        DataFrame dengan fitur yang sudah direkayasa
    target_col : str
        Kolom target untuk diprediksi
    feature_cols : list
        Daftar kolom fitur yang akan digunakan
    n_steps : int
        Jumlah langkah waktu untuk prediksi (lookback window)
    n_features : int
        Jumlah fitur untuk digunakan (jika None, gunakan semua feature_cols)
    test_size : float
        Proporsi data untuk pengujian
    
    Returns:
    --------
    tuple
        (X_train, y_train, X_test, y_test, scaler_X, scaler_y)
    """
    # Jika feature_cols tidak disediakan, gunakan semua kolom numerik
    if feature_cols is None:
        feature_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        # Hapus target_col dari feature_cols jika ada
        if target_col in feature_cols:
            feature_cols.remove(target_col)
    
    # Jika n_features tidak disediakan, gunakan semua feature_cols
    if n_features is None:
        n_features = len(feature_cols)
    elif n_features > len(feature_cols):
        n_features = len(feature_cols)
    
    # Pilih fitur teratas berdasarkan korelasi dengan target
    if len(feature_cols) > n_features:
        corr = df[feature_cols + [target_col]].corr()[target_col].abs().sort_values(ascending=False)
        feature_cols = corr.index[1:n_features+1].tolist()  # Excludes target_col itself
    
    # Normalisasi fitur
    scaler_X = MinMaxScaler(feature_range=(0, 1))
    scaler_y = MinMaxScaler(feature_range=(0, 1))
    
    # Fit scaler pada seluruh dataset untuk menghindari data leakage
    X_scaled = scaler_X.fit_transform(df[feature_cols])
    y_scaled = scaler_y.fit_transform(df[[target_col]])
    
    # Membuat dataset dengan sliding window
    X, y = [], []
    for i in range(n_steps, len(df)):
        X.append(X_scaled[i-n_steps:i])
        y.append(y_scaled[i])
    
    X, y = np.array(X), np.array(y)
    
    # Split data menjadi training dan testing
    split_idx = int(len(X) * (1 - test_size))
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    
    print(f"Bentuk X_train: {X_train.shape}, y_train: {y_train.shape}")
    print(f"Bentuk X_test: {X_test.shape}, y_test: {y_test.shape}")
    
    return X_train, y_train, X_test, y_test, scaler_X, scaler_y, feature_cols

def build_lstm_model(input_shape, dropout_rate=0.2):
    """
    Membangun model LSTM untuk prediksi deret waktu
    
    Parameters:
    -----------
    input_shape : tuple
        Bentuk input (n_steps, n_features)
    dropout_rate : float
        Tingkat dropout untuk mencegah overfitting
    
    Returns:
    --------
    tensorflow.keras.models.Sequential
        Model LSTM yang dikonfigurasi
    """
    model = Sequential([
        # Layer LSTM pertama dengan return sequences untuk layer LSTM berikutnya
        LSTM(100, return_sequences=True, input_shape=input_shape, 
             recurrent_dropout=0.1, activation='tanh'),
        BatchNormalization(),
        Dropout(dropout_rate),
        
        # Layer LSTM kedua
        LSTM(50, return_sequences=False, recurrent_dropout=0.1),
        BatchNormalization(),
        Dropout(dropout_rate),
        
        # Layer Dense dengan aktivasi ReLU
        Dense(50, activation='relu'),
        BatchNormalization(),
        Dropout(dropout_rate/2),  # Dropout lebih rendah di layer akhir
        
        # Layer output
        Dense(1)
    ])
    
    # Kompilasi model
    optimizer = Adam(learning_rate=0.001)
    model.compile(optimizer=optimizer, loss='mean_squared_error')
    
    return model

def build_gru_model(input_shape, dropout_rate=0.2):
    """
    Membangun model GRU untuk prediksi deret waktu
    
    Parameters:
    -----------
    input_shape : tuple
        Bentuk input (n_steps, n_features)
    dropout_rate : float
        Tingkat dropout untuk mencegah overfitting
    
    Returns:
    --------
    tensorflow.keras.models.Sequential
        Model GRU yang dikonfigurasi
    """
    model = Sequential([
        # Layer GRU pertama dengan return sequences untuk layer GRU berikutnya
        GRU(100, return_sequences=True, input_shape=input_shape,
            recurrent_dropout=0.1, activation='tanh'),
        BatchNormalization(),
        Dropout(dropout_rate),
        
        # Layer GRU kedua
        GRU(50, return_sequences=False, recurrent_dropout=0.1),
        BatchNormalization(),
        Dropout(dropout_rate),
        
        # Layer Dense dengan aktivasi ReLU
        Dense(50, activation='relu'),
        BatchNormalization(),
        Dropout(dropout_rate/2),  # Dropout lebih rendah di layer akhir
        
        # Layer output
        Dense(1)
    ])
    
    # Kompilasi model
    optimizer = Adam(learning_rate=0.001)
    model.compile(optimizer=optimizer, loss='mean_squared_error')
    
    return model

def train_model(model, X_train, y_train, X_test, y_test, epochs=100, batch_size=32):
    """
    Melatih model dan menerapkan teknik untuk mempercepat pelatihan dan mencegah overfitting
    
    Parameters:
    -----------
    model : tensorflow.keras.models.Sequential
        Model yang akan dilatih
    X_train, y_train : numpy.ndarray
        Data pelatihan
    X_test, y_test : numpy.ndarray
        Data pengujian
    epochs : int
        Jumlah epoch untuk pelatihan
    batch_size : int
        Ukuran batch untuk pelatihan
    
    Returns:
    --------
    tuple
        (model terlatih, riwayat pelatihan)
    """
    # Mengonfigurasi callbacks untuk meningkatkan pelatihan
    callbacks = [
        # Early stopping untuk mencegah overfitting
        EarlyStopping(
            monitor='val_loss',
            patience=15,
            restore_best_weights=True,
            verbose=1
        ),
        
        # Model checkpoint untuk menyimpan model terbaik
        ModelCheckpoint(
            filepath='best_model.h5',
            monitor='val_loss',
            save_best_only=True,
            verbose=1
        ),
        
        # Reduce learning rate ketika model mencapai plateau
        ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.5,
            patience=5,
            min_lr=1e-6,
            verbose=1
        )
    ]
    
    # Menggunakan mixed precision untuk mempercepat pelatihan pada GPU
    try:
        policy = tf.keras.mixed_precision.Policy('mixed_float16')
        tf.keras.mixed_precision.set_global_policy(policy)
        print("Mixed precision diaktifkan")
    except:
        print("Mixed precision tidak tersedia, melanjutkan dengan presisi default")
    
    # Mengatur distribusi pelatihan jika GPU tersedia
    strategy = tf.distribute.MirroredStrategy() if len(tf.config.list_physical_devices('GPU')) > 1 else None
    
    if strategy:
        print(f"Melatih menggunakan {strategy.num_replicas_in_sync} GPU")
        with strategy.scope():
            # Recompile model to ensure it's compatible with the strategy
            model.compile(optimizer=model.optimizer, loss=model.loss)
    
    # Melatih model
    history = model.fit(
        X_train, y_train,
        epochs=epochs,
        batch_size=batch_size,
        validation_data=(X_test, y_test),
        callbacks=callbacks,
        verbose=1,
        shuffle=False  # Penting untuk deret waktu
    )
    
    return model, history

def evaluate_model(model, X_test, y_test, scaler_y, target_col):
    """
    Mengevaluasi kinerja model pada dataset pengujian
    
    Parameters:
    -----------
    model : tensorflow.keras.models.Model
        Model terlatih untuk dievaluasi
    X_test : numpy.ndarray
        Data pengujian fitur
    y_test : numpy.ndarray
        Data pengujian target
    scaler_y : sklearn.preprocessing.MinMaxScaler
        Scaler yang digunakan untuk mendenormalisasi prediksi
    target_col : str
        Nama kolom target
    
    Returns:
    --------
    dict
        Metrik evaluasi model
    """
    # Prediksi pada data pengujian
    y_pred = model.predict(X_test)
    
    # Denormalisasi hasil
    y_test_denorm = scaler_y.inverse_transform(y_test)
    y_pred_denorm = scaler_y.inverse_transform(y_pred)
    
    # Hitung metrik evaluasi
    from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
    import math
    
    mse = mean_squared_error(y_test_denorm, y_pred_denorm)
    rmse = math.sqrt(mse)
    mae = mean_absolute_error(y_test_denorm, y_pred_denorm)
    r2 = r2_score(y_test_denorm, y_pred_denorm)
    
    # Hitung metrik khusus keuangan
    # MAPE (Mean Absolute Percentage Error)
    mape = np.mean(np.abs((y_test_denorm - y_pred_denorm) / y_test_denorm)) * 100
    
    # Directional Accuracy (akurasi arah pergerakan harga)
    y_test_direction = np.diff(y_test_denorm.flatten())
    y_pred_direction = np.diff(y_pred_denorm.flatten())
    
    direction_accuracy = np.mean((y_test_direction > 0) == (y_pred_direction > 0)) * 100
    
    # Visualisasi hasil prediksi
    plt.figure(figsize=(14, 7))
    plt.plot(y_test_denorm, label='Aktual')
    plt.plot(y_pred_denorm, label='Prediksi')
    plt.title(f'Prediksi vs Aktual untuk {target_col}')
    plt.xlabel('Periode Waktu')
    plt.ylabel(target_col)
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig('prediction_vs_actual.png', dpi=300)
    plt.close()
    
    # Visualisasi scatter plot prediksi vs aktual
    plt.figure(figsize=(10, 10))
    plt.scatter(y_test_denorm, y_pred_denorm, alpha=0.5)
    plt.plot([y_test_denorm.min(), y_test_denorm.max()], 
             [y_test_denorm.min(), y_test_denorm.max()], 'r--')
    plt.title('Scatter Plot Prediksi vs Aktual')
    plt.xlabel('Aktual')
    plt.ylabel('Prediksi')
    plt.grid(True)
    plt.tight_layout()
    plt.savefig('prediction_scatter.png', dpi=300)
    plt.close()
    
    # Kumpulkan dan cetak semua metrik
    metrics = {
        'MSE': mse,
        'RMSE': rmse,
        'MAE': mae,
        'R²': r2,
        'MAPE (%)': mape,
        'Directional Accuracy (%)': direction_accuracy
    }
    
    print("Evaluasi Model:")
    for metric, value in metrics.items():
        print(f"{metric}: {value:.4f}")
    
    return metrics

def save_model_with_metadata(model, feature_cols, scaler_X, scaler_y, n_steps, target_col, metrics, model_path='saved_model'):
    """
    Menyimpan model bersama dengan metadata yang diperlukan untuk inferensi
    
    Parameters:
    -----------
    model : tensorflow.keras.models.Model
        Model terlatih
    feature_cols : list
        Daftar nama kolom fitur
    scaler_X : sklearn.preprocessing.MinMaxScaler
        Scaler untuk fitur
    scaler_y : sklearn.preprocessing.MinMaxScaler
        Scaler untuk target
    n_steps : int
        Jumlah langkah waktu (lookback window)
    target_col : str
        Nama kolom target
    metrics : dict
        Metrik evaluasi model
    model_path : str
        Direktori untuk menyimpan model
    """
    import os
    import pickle
    import json
    from datetime import datetime
    
    # Buat direktori jika tidak ada
    if not os.path.exists(model_path):
        os.makedirs(model_path)
    
    # Buat timestamp untuk versioning
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Simpan model Keras
    model_file = f"{model_path}/model_{timestamp}.h5"
    model.save(model_file, save_format='h5')
    
    # Simpan scaler
    with open(f"{model_path}/scaler_X_{timestamp}.pkl", 'wb') as f:
        pickle.dump(scaler_X, f)
    
    with open(f"{model_path}/scaler_y_{timestamp}.pkl", 'wb') as f:
        pickle.dump(scaler_y, f)
    
    # Simpan metadata
    metadata = {
        'feature_columns': feature_cols,
        'target_column': target_col,
        'n_steps': n_steps,
        'metrics': metrics,
        'model_architecture': model.to_json(),
        'timestamp': timestamp,
        'model_file': model_file
    }
    
    with open(f"{model_path}/metadata_{timestamp}.json", 'w') as f:
        json.dump(metadata, f, indent=4)
    
    print(f"Model dan metadata berhasil disimpan di {model_path}")
    
    return model_path

def model_inference(model_path, new_data, target_col='close', future_steps=10):
    """
    Melakukan inferensi dengan model terlatih untuk data baru dan membuat prediksi untuk beberapa langkah ke depan
    
    Parameters:
    -----------
    model_path : str
        Path ke direktori yang berisi model dan metadata
    new_data : pandas.DataFrame
        Data baru untuk prediksi
    target_col : str
        Nama kolom target
    future_steps : int
        Jumlah langkah ke depan untuk diprediksi
    
    Returns:
    --------
    pandas.DataFrame
        DataFrame berisi prediksi untuk future_steps
    """
    import os
    import pickle
    import json
    import glob
    from tensorflow.keras.models import load_model
    
    # Temukan file metadata terbaru
    metadata_files = glob.glob(f"{model_path}/metadata_*.json")
    latest_metadata = max(metadata_files, key=os.path.getctime)
    
    # Muat metadata
    with open(latest_metadata, 'r') as f:
        metadata = json.load(f)
    
    # Muat model
    model = load_model(metadata['model_file'])
    
    # Muat scaler
    scaler_X_file = f"{model_path}/scaler_X_{metadata['timestamp']}.pkl"
    scaler_y_file = f"{model_path}/scaler_y_{metadata['timestamp']}.pkl"
    
    with open(scaler_X_file, 'rb') as f:
        scaler_X = pickle.load(f)
    
    with open(scaler_y_file, 'rb') as f:
        scaler_y = pickle.load(f)
    
    # Persiapkan data untuk prediksi
    feature_cols = metadata['feature_columns']
    n_steps = metadata['n_steps']
    
    # Pastikan semua kolom fitur ada dalam data baru
    missing_cols = [col for col in feature_cols if col not in new_data.columns]
    if missing_cols:
        raise ValueError(f"Kolom berikut tidak ditemukan dalam data baru: {missing_cols}")
    
    # Normalisasi data baru
    X_scaled = scaler_X.transform(new_data[feature_cols].iloc[-n_steps:])
    
    # Reshape untuk LSTM/GRU (1 sampel, n_steps, n_features)
    X_reshaped = X_scaled.reshape(1, n_steps, len(feature_cols))
    
    # Prediksi pertama
    y_pred = model.predict(X_reshaped)
    predictions = scaler_y.inverse_transform(y_pred)
    
    # Untuk prediksi berkelanjutan (next steps)
    all_predictions = [predictions[0, 0]]
    
    # Persiapkan data untuk iterasi berikutnya
    last_sequence = X_scaled.copy()
    
    # Prediksi untuk langkah-langkah berikutnya
    for i in range(1, future_steps):
        # Update sequence dengan menghapus elemen pertama dan menambahkan prediksi terakhir di akhir
        # Asumsi fitur terakhir adalah target_col
        target_idx = feature_cols.index(target_col) if target_col in feature_cols else -1
        
        # Buat data input baru dengan menambahkan prediksi sebelumnya
        if target_idx >= 0:
            # Normalisasi prediksi terakhir
            normalized_pred = scaler_y.transform(predictions.reshape(1, -1))
            
            # Update last sequence (geser dan tambahkan prediksi)
            last_sequence = np.roll(last_sequence, -1, axis=0)
            last_sequence[-1, target_idx] = normalized_pred[0, 0]
        
        # Reshape untuk model
        X_next = last_sequence.reshape(1, n_steps, len(feature_cols))
        
        # Prediksi langkah berikutnya
        y_pred = model.predict(X_next)
        predictions = scaler_y.inverse_transform(y_pred)
        all_predictions.append(predictions[0, 0])
    
    # Buat DataFrame untuk output
    future_dates = pd.date_range(start=new_data.index[-1], periods=future_steps+1)[1:]
    forecast_df = pd.DataFrame({
        'date': future_dates,
        f'predicted_{target_col}': all_predictions
    })
    forecast_df.set_index('date', inplace=True)
    
    # Visualisasi hasil prediksi
    plt.figure(figsize=(14, 7))
    
    # Plot data historis
    hist_dates = new_data.index[-30:]  # Tampilkan 30 titik data terakhir
    plt.plot(hist_dates, new_data[target_col].iloc[-30:], label='Historis')
    
    # Plot prediksi
    plt.plot(forecast_df.index, forecast_df[f'predicted_{target_col}'], label='Prediksi', color='red')
    
    plt.title(f'Prediksi {target_col} untuk {future_steps} langkah ke depan')
    plt.xlabel('Tanggal')
    plt.ylabel(target_col)
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig('future_predictions.png', dpi=300)
    plt.close()
    
    return forecast_df

def complete_trading_pipeline(symbol, timeframe, start_date, end_date, target_col='close', n_steps=60, model_type='lstm'):
    """
    Menjalankan seluruh pipeline trading dari pengumpulan data hingga prediksi
    
    Parameters:
    -----------
    symbol : str
        Simbol instrumen keuangan
    timeframe : int
        Timeframe data
    start_date : datetime
        Tanggal mulai
    end_date : datetime
        Tanggal akhir
    target_col : str
        Kolom target untuk diprediksi
    n_steps : int
        Jumlah langkah untuk lookback window
    model_type : str
        Jenis model ('lstm' atau 'gru')
    
    Returns:
    --------
    dict
        Hasil dari setiap tahap pipeline
    """
    # Pengumpulan data
    print("1. Mengumpulkan data...")
    df = collect_market_data(symbol, timeframe, start_date, end_date)
    
    if df is None or len(df) < n_steps + 50:  # Pastikan cukup data
        print("Data tidak mencukupi. Memperluas rentang waktu...")
        # Perluas rentang waktu jika perlu
        extended_start = start_date - pd.DateOffset(months=6)
        df = collect_market_data(symbol, timeframe, extended_start, end_date)
        
        if df is None or len(df) < n_steps + 50:
            raise ValueError("Tidak cukup data tersedia bahkan setelah memperluas rentang waktu.")
    
    # Pembersihan data
    print("2. Membersihkan data...")
    df_clean = clean_market_data(df)
    
    # Analisis eksploratori
    print("3. Melakukan analisis eksploratori...")
    df_explored = perform_eda(df_clean)
    
    # Rekayasa fitur
    print("4. Melakukan rekayasa fitur...")
    df_featured = engineer_features(df_clean)
    
    # Persiapan data untuk pemodelan
    print("5. Mempersiapkan data untuk pemodelan...")
    X_train, y_train, X_test, y_test, scaler_X, scaler_y, feature_cols = prepare_time_series_data(
        df_featured, target_col=target_col, n_steps=n_steps
    )
    
    # Membangun model
    print(f"6. Membangun model {model_type.upper()}...")
    input_shape = (X_train.shape[1], X_train.shape[2])
    
    if model_type.lower() == 'lstm':
        model = build_lstm_model(input_shape)
    else:  # GRU
        model = build_gru_model(input_shape)
    
    # Melatih model
    print("7. Melatih model...")
    model, history = train_model(model, X_train, y_train, X_test, y_test)
    
    # Evaluasi model
    print("8. Mengevaluasi model...")
    metrics = evaluate_model(model, X_test, y_test, scaler_y, target_col)
    
    # Simpan model
    print("9. Menyimpan model...")
    model_path = save_model_with_metadata(
        model, feature_cols, scaler_X, scaler_y, n_steps, target_col, metrics
    )
    
    # Prediksi masa depan
    print("10. Membuat prediksi...")
    future_steps = 14  # Prediksi 14 periode ke depan
    forecast = model_inference(model_path, df_featured, target_col, future_steps)
    
    print("Pipeline selesai!")
    
    return {
        'data': df,
        'cleaned_data': df_clean,
        'featured_data': df_featured,
        'model': model,
        'history': history,
        'metrics': metrics,
        'forecast': forecast,
        'model_path': model_path
    }

## Evaluasi Model

Evaluasi model yang menyeluruh sangat penting dalam konteks keuangan, di mana kesalahan dapat berdampak signifikan. Tahap evaluasi melibatkan perhitungan berbagai metrik untuk menilai kualitas prediksi model dan kelayakannya untuk pengambilan keputusan trading.

### Metrik Evaluasi Standar

1. **RMSE (Root Mean Squared Error)**
   - Mengukur akar rata-rata kesalahan kuadrat antara nilai aktual dan prediksi
   - Memberikan bobot lebih besar pada kesalahan besar
   - Ideal untuk nilai RMSE yang rendah, yang menunjukkan akurasi prediksi yang lebih baik

2. **MAE (Mean Absolute Error)**
   - Mengukur rata-rata nilai absolut dari kesalahan
   - Lebih mudah diinterpretasi dibandingkan RMSE
   - Tidak memberikan penalti berlebih pada kesalahan besar

3. **MAPE (Mean Absolute Percentage Error)**
   - Mengukur rata-rata persentase kesalahan absolut
   - Memungkinkan perbandingan kinerja model di berbagai skala
   - Ideal untuk nilai di bawah 10% untuk model prediksi keuangan yang baik

4. **R² (Coefficient of Determination)**
   - Mengukur proporsi variansi dalam variabel dependen yang dapat dijelaskan oleh model
   - Nilai berkisar antara 0 dan 1, dengan nilai yang lebih tinggi menunjukkan model yang lebih baik
   - Namun, berhati-hatilah dengan overreliance pada R² dalam konteks deret waktu

### Metrik Khusus Keuangan

1. **Directional Accuracy**
   - Mengukur seberapa baik model memprediksi arah pergerakan harga (naik atau turun)
   - Krusial untuk strategi trading yang bergantung pada arah pergerakan pasar
   - Model yang baik harus mencapai akurasi direktional minimal 60% di pasar keuangan

2. **Profit & Loss Simulation**
   - Mengevaluasi kinerja model dalam simulasi trading nyata
   - Mengukur potensi keuntungan atau kerugian berdasarkan sinyal yang dihasilkan oleh model
   - Mempertimbangkan biaya transaksi dan slippage untuk simulasi yang realistis

3. **Maximum Drawdown**
   - Mengukur penurunan maksimum dari puncak ke lembah dalam kurva equity
   - Indikator penting dari risiko model
   - Model yang baik harus memiliki drawdown yang relatif rendah

4. **Sharpe Ratio**
   - Mengukur return rata-rata di atas risk-free rate dibagi dengan standar deviasi return
   - Mengevaluasi kinerja model yang disesuaikan dengan risiko
   - Nilai di atas 1.0 umumnya dianggap baik, di atas 2.0 sangat baik

## Penerapan Model

Setelah model dievaluasi dan dianggap memadai, tahap selanjutnya melibatkan penerapan model tersebut dalam lingkungan produksi. Penerapan yang efektif memastikan bahwa model dapat menghasilkan prediksi yang tepat waktu dan dapat diandalkan untuk pengambilan keputusan trading.

### Optimasi Deployment

1. **Konversi Model ke Format Ringan**
   - Menggunakan TensorFlow Lite untuk deployment pada perangkat dengan sumber daya terbatas
   - Mengoptimalkan model untuk inferensi yang lebih cepat
   - Mengurangi ukuran model dengan teknik seperti pruning dan quantization

```python
import tensorflow as tf

def convert_to_tflite(model_path, optimized_path):
    """
    Mengkonversi model Keras ke format TensorFlow Lite yang dioptimalkan
    """
    # Muat model
    model = tf.keras.models.load_model(model_path)
    
    # Konverter TFLite
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    
    # Aktifkan optimasi
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    
    # Mengkonversi model
    tflite_model = converter.convert()
    
    # Simpan model teroptimasi
    with open(optimized_path, 'wb') as f:
        f.write(tflite_model)
    
    print(f"Model dioptimalkan dan disimpan ke {optimized_path}")
    