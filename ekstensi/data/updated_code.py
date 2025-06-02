# SanClass Trading Labs - Quantailine V.6

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import tensorflow as tf
from tensorflow.keras import Model, Input
from tensorflow.keras.layers import LSTM, Dense, Dropout, MultiHeadAttention, LayerNormalization, GlobalAveragePooling1D
from tensorflow.keras.layers import Concatenate, Add
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, mean_squared_error, mean_absolute_percentage_error
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import os
import logging
import joblib
import matplotlib.pyplot as plt
import json
import sys
import random
import time

# ============ Reproducibility ============
np.random.seed(42)
tf.random.set_seed(42)
random.seed(42)
os.environ['TF_DETERMINISTIC_OPS'] = '1'

# ============ Load Env & Logging ============
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ============ MetaTrader5 Setup ============
def connect_mt5():
    login_str = os.getenv("MT5_LOGIN")
    server = os.getenv("MT5_SERVER")
    password = os.getenv("MT5_PASSWORD")

    if not login_str or not server or not password:
        logging.error("❌ Kredensial MT5 (MT5_LOGIN, MT5_SERVER, MT5_PASSWORD) tidak ditemukan.")
        sys.exit(1)

    try:
        login = int(login_str)
    except ValueError:
        logging.error(f"❌ Nilai MT5_LOGIN di .env bukan angka: '{login_str}'")
        sys.exit(1)

    max_retries = 5
    retry_delay_sec = 5

    for i in range(max_retries):
        logging.info(f"⏳ Mencoba koneksi MT5 (Percobaan {i+1}/{max_retries})...")
        if mt5.initialize(login=login, server=server, password=password):
            logging.info("✅ Berhasil login ke MetaTrader5")
            return
        last_error = mt5.last_error()
        logging.warning(f"⚠️ Gagal koneksi MT5 (Percobaan {i+1}/{max_retries}). Kode error: {last_error}")
        if i < max_retries - 1:
             time.sleep(retry_delay_sec)

    logging.error(f"❌ Gagal koneksi MT5 setelah {max_retries} percobaan.")
    raise ConnectionError(f"Gagal koneksi MT5: {last_error}")

def acquire_data(symbol, timeframe, start, end):
    connect_mt5()
    logging.info(f"⏳ Mengambil data {symbol} dari {start} hingga {end} dengan timeframe {timeframe}...")
    print(f"📊 VISUALISASI: Memulai pengambilan data historis {symbol}")

    try:
        rates = mt5.copy_rates_range(symbol, timeframe, start, end)
        if rates is None:
             raise Exception(f"mt5.copy_rates_range mengembalikan None. Error: {mt5.last_error()}")

    except Exception as e:
        logging.error(f"❌ Error saat memanggil copy_rates_range: {e}")
        rates = None
    finally:
        mt5.shutdown()
        logging.info("✅ Koneksi MT5 di-shutdown.")

    if rates is None or len(rates) == 0:
        error_msg = f"❌ Gagal mengambil data dari MT5 untuk {symbol} ({start} to {end}). Data kosong atau terjadi kesalahan."
        logging.error(error_msg)
        return pd.DataFrame()

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df = df.sort_values('time').reset_index(drop=True)
    logging.info(f"✅ Berhasil mengambil {len(df)} baris data.")
    print(f"📊 VISUALISASI: Data historis berhasil diambil: {len(df)} candle")

    return df[['time', 'open', 'high', 'low', 'close', 'tick_volume']]

# ============ Preprocessing ============
def calculate_atr(df, period):
    """Menghitung Average True Range (ATR)"""
    high_low = df['high'] - df['low']
    high_close_prev = abs(df['high'] - df['close'].shift(1))
    low_close_prev = abs(df['low'] - df['close'].shift(1))
    
    tr = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    
    return atr

def add_technical_features(df):
    # Menambahkan indikator teknikal yang diminta
    df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['ema_89'] = df['close'].ewm(span=89, adjust=False).mean()
    
    # Menghitung ATR
    df['atr_9'] = calculate_atr(df, 9)
    df['atr_45'] = calculate_atr(df, 45)
    
    # Tambahkan indikator yang sudah ada sebelumnya untuk backward compatibility
    df['sma_5'] = df['close'].rolling(window=5, min_periods=1).mean()
    df['ema_5'] = df['close'].ewm(span=5, adjust=False).mean()
    
    # Tambahkan fitur volatilitas relatif
    df['volatility_ratio'] = df['atr_9'] / df['atr_45'].rolling(window=3).mean()
    
    # Tambahkan fitur arah tren (trend direction)
    df['trend_direction'] = np.where(df['ema_21'] > df['ema_89'], 1, -1)
    
    # Tambahkan fitur momentum
    df['momentum'] = df['close'] - df['close'].shift(5)
    
    print(f"📊 VISUALISASI: Indikator teknikal berhasil ditambahkan (ATR 9, ATR 45, EMA 21, EMA 89)")
    return df

def preprocess_for_training(df):
    # Membersihkan data awal dari NaN (misalnya dari data akuisisi)
    df = df.dropna().reset_index(drop=True)
    if df.empty:
         raise ValueError("DataFrame kosong setelah menghapus NaN awal.")

    # Menambahkan fitur teknikal ke SELURUH DataFrame historis
    df = add_technical_features(df)

    # Menghapus baris yang memiliki NaN setelah penambahan fitur teknikal
    df = df.dropna().reset_index(drop=True)
    if df.empty:
         raise ValueError("DataFrame kosong setelah menambahkan fitur teknikal dan menghapus NaN lagi.")

    # Mendefinisikan fitur yang akan digunakan (perbarui dengan fitur baru)
    features = ['open', 'high', 'low', 'close', 'tick_volume', 
                'ema_21', 'ema_89', 'atr_9', 'atr_45', 
                'sma_5', 'ema_5', 'volatility_ratio', 'trend_direction', 'momentum']

    # Validasi apakah semua kolom fitur yang diharapkan ada
    if not all(f in df.columns for f in features):
         missing_features = [f for f in features if f not in df.columns]
         raise ValueError(f"Fitur yang diharapkan tidak ada di DataFrame setelah pra-pemrosesan: {missing_features}")

    logging.info(f"✅ Data diproses untuk training. Menggunakan {len(features)} fitur: {features}")
    print(f"📊 VISUALISASI: Fitur untuk training siap: {len(features)} fitur")

    # Melakukan scaling pada fitur input (X) menggunakan MinMaxScaler
    scaler_X = MinMaxScaler()
    df_scaled_features = scaler_X.fit_transform(df[features])
    df[features] = df_scaled_features
    logging.info("✅ Fitur input (X) untuk training berhasil di-scale.")

    return df, scaler_X, features

def create_dataset(df, window_size, feature_cols):
    X, y = [], []
    y_time = []

    # Pastikan ada cukup data untuk membuat setidaknya satu sampel
    if len(df) <= window_size:
        logging.warning(f"Tidak cukup data ({len(df)} bar) untuk membuat dataset dengan window_size={window_size}. Butuh setidaknya {window_size + 1} bar.")
        return np.array([]), np.array([]), pd.DatetimeIndex([])

    # Perbaikan: Iterasi untuk membuat dataset dengan jendela geser
    for i in range(len(df) - window_size):
        window = df.iloc[i : i + window_size][feature_cols].values
        target = df.iloc[i + window_size][['high', 'low', 'close']].values
        target_time = df.iloc[i + window_size]['time']

        # Cek apakah ada NaN/Inf di jendela atau target
        if not np.isfinite(window).all() or not np.isfinite(target).all():
            logging.warning(f"⚠️ NaN/Inf terdeteksi di jendela atau target pada index awal {i}. Melompati sampel ini.")
            continue

        X.append(window)
        y.append(target)
        y_time.append(target_time)

    X = np.array(X)
    y = np.array(y)
    y_time = pd.to_datetime(y_time)

    if len(X) == 0 and len(df) > window_size:
         logging.warning(f"Tidak ada sampel valid yang dibuat meskipun data awal cukup. Mungkin ada NaN/Inf di data setelah pra-pemrosesan yang terlewat.")

    logging.info(f"✅ Dataset dibuat. Shape X: {X.shape}, Shape y: {y.shape}")
    print(f"📊 VISUALISASI: Dataset siap dengan {len(X)} sampel training")
    return X, y, y_time

# ============ N-BEATS Block ============
def create_nbeats_block(x, units, theta_dim, share_theta=False, layer_norm=True):
    """Membuat blok N-BEATS"""
    # Fully connected layers dengan layer normalization
    for i in range(4):  # Gunakan 4 layer FC
        x = Dense(units, activation='relu')(x)
        if layer_norm:
            x = LayerNormalization()(x)
    
    # Theta layer
    theta = Dense(theta_dim)(x)
    
    # Backward dan forward projection
    backcast_size = x.shape[1]
    forecast_size = 3  # High, Low, Close
    
    if share_theta:
        backcast = Dense(backcast_size, name='backcast')(theta)
        forecast = Dense(forecast_size, name='forecast')(theta)
    else:
        backcast_theta, forecast_theta = tf.split(theta, 2, axis=-1)
        backcast = Dense(backcast_size, name='backcast')(backcast_theta)
        forecast = Dense(forecast_size, name='forecast')(forecast_theta)
    
    return backcast, forecast

# ============ Model (LSTM + Attention + N-BEATS) ============
def build_hybrid_model(input_shape, output_dim, n_blocks=3):
    """Membangun model hibrida dengan LSTM+Attention dan N-BEATS"""
    print(f"📊 VISUALISASI: Membangun model hibrida dengan {n_blocks} blok N-BEATS")
    
    # Input shape: (window_size, num_features)
    inputs = Input(shape=input_shape)
    
    # === LSTM + Attention Path ===
    # Layer LSTM dengan regularisasi
    lstm_out = LSTM(128, return_sequences=True, kernel_regularizer=tf.keras.regularizers.l2(0.0005))(inputs)
    lstm_out = Dropout(0.2)(lstm_out)

    # Layer MultiHeadAttention
    attention_output = MultiHeadAttention(
        num_heads=4, key_dim=32, dropout=0.1)(lstm_out, lstm_out)

    # Residual connection dan normalization
    lstm_out = Add()([lstm_out, attention_output])
    lstm_out = LayerNormalization()(lstm_out)
    
    # GlobalAveragePooling untuk mereduksi dimensi waktu
    lstm_out = GlobalAveragePooling1D()(lstm_out)
    
    # Dense layer
    lstm_out = Dense(64, activation='relu', kernel_regularizer=tf.keras.regularizers.l2(0.0005))(lstm_out)
    lstm_out = Dropout(0.3)(lstm_out)
    
    # === N-BEATS Path ===
    # Residual stacking dengan multiple blocks
    backcast = inputs
    forecast = None
    units = 128
    theta_dim = 32
    
    for i in range(n_blocks):
        # Perbaikan: pass dimensi input yang benar ke blok N-BEATS
        block_input = backcast
        b, f = create_nbeats_block(
            block_input, 
            units=units, 
            theta_dim=theta_dim, 
            share_theta=(i % 2 == 0),  # Alternating sharing untuk variasi
            layer_norm=True
        )
        
        # Residual connection untuk backcast
        backcast = Subtract()([backcast, b]) if i > 0 else b
        
        # Akumulasi ramalan
        if forecast is None:
            forecast = f
        else:
            forecast = Add()([forecast, f])
    
    # Menggabungkan output dari kedua path
    combined = Concatenate()([lstm_out, forecast])
    
    # Final dense layer
    outputs = Dense(output_dim)(combined)
    
    model = Model(inputs=inputs, outputs=outputs)
    logging.info("✅ Model Hibrida LSTM + Attention + N-BEATS berhasil dibangun.")
    model.summary(print_fn=lambda msg: logging.info(msg))
    
    return model

# ============ Training ============
def train_model(model, train_ds, val_ds, name):
    logging.info(f"⏳ Memulai training model fold: {name}...")
    print(f"📊 VISUALISASI: Training model fold {name} dimulai")
    
    # Compile model dengan optimizer efektif
    optimizer = tf.keras.optimizers.Adam(learning_rate=0.001)
    model.compile(
        optimizer=optimizer, 
        loss='mse', 
        metrics=['mae', 'mse']
    )

    checkpoint_path = f"model_artifacts/{name}_checkpoint.h5"

    # Callbacks untuk early stopping dan checkpoint
    callbacks = [
        EarlyStopping(
            patience=15, 
            restore_best_weights=True, 
            verbose=1, 
            monitor='val_loss'
        ),
        ModelCheckpoint(
            checkpoint_path, 
            save_best_only=True, 
            verbose=1, 
            monitor='val_loss'
        ),
        # Tambahkan ReduceLROnPlateau untuk adaptasi learning rate
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor='val_loss', 
            factor=0.5, 
            patience=5, 
            verbose=1, 
            min_lr=0.00001
        )
    ]

    # Melatih model dengan jumlah epoch yang cukup
    history = model.fit(
        train_ds, 
        validation_data=val_ds, 
        epochs=300, 
        callbacks=callbacks, 
        verbose=1
    )
    
    print(f"📊 VISUALISASI: Training model fold {name} selesai")
    
    # Plotting history training
    plt.figure(figsize=(12, 5))
    plt.subplot(1, 2, 1)
    plt.plot(history.history['loss'], label='Training Loss')
    plt.plot(history.history['val_loss'], label='Validation Loss')
    plt.title(f'Training & Validation Loss - {name}')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.legend()
    
    plt.subplot(1, 2, 2)
    plt.plot(history.history['mae'], label='Training MAE')
    plt.plot(history.history['val_mae'], label='Validation MAE')
    plt.title(f'Training & Validation MAE - {name}')
    plt.xlabel('Epoch')
    plt.ylabel('MAE')
    plt.legend()
    
    plt.tight_layout()
    plt.savefig(f"model_artifacts/{name}_training_history.png")
    print(f"📊 VISUALISASI: Grafik history training model fold {name} disimpan")

    return model, history

# ============ Evaluation ============
def evaluate_model(model, X_set, y_set_scaled, scaler_y, y_set_time, set_name="Test"):
    logging.info(f"⏳ Mengevaluasi model pada set {set_name} ({len(X_set)} sampel)...")
    print(f"📊 VISUALISASI: Evaluasi model pada {set_name} dimulai")

    if len(X_set) == 0:
         logging.warning(f"⚠️ Tidak ada data di set {set_name} untuk dievaluasi.")
         return np.array([]), np.array([]), pd.DatetimeIndex([]), {'mae': np.nan, 'rmse': np.nan, 'mape': np.nan}

    preds_scaled = model.predict(X_set, verbose=0)

    try:
        y_set_original = scaler_y.inverse_transform(y_set_scaled)
        preds_original = scaler_y.inverse_transform(preds_scaled)
    except Exception as e:
        logging.error(f"❌ Gagal inverse transform data untuk set {set_name}: {e}")
        return preds_scaled, y_set_scaled, y_set_time, {'mae': np.nan, 'rmse': np.nan, 'mape': np.nan}

    # Hitung metrik dalam skala asli
    mae = mean_absolute_error(y_set_original, preds_original)
    rmse = np.sqrt(mean_squared_error(y_set_original, preds_original))

    if np.all(y_set_original < 1e-6): # Cek jika nilai aktual sangat kecil
         mape = np.nan
         logging.warning(f"⚠️ Semua nilai aktual di set {set_name} mendekati nol. MAPE tidak dihitung.")
    else:
         # Hitung MAPE per output (High, Low, Close) lalu rata-ratakan
         # Menambah epsilon untuk menghindari pembagian nol
         mape_per_output = np.abs((y_set_original - preds_original) / (y_set_original + 1e-8)) * 100
         # Hilangkan Inf atau nilai sangat besar yang mungkin muncul dari pembagian nilai kecil
         mape_per_output = mape_per_output[np.isfinite(mape_per_output)]
         mape = np.mean(mape_per_output) if mape_per_output.size > 0 else np.nan

    # Tambahkan metrik directional accuracy
    direction_actual = np.sign(y_set_original[1:, 2] - y_set_original[:-1, 2])
    direction_pred = np.sign(preds_original[1:, 2] - preds_original[:-1, 2])
    directional_accuracy = np.mean(direction_actual == direction_pred) * 100 if len(direction_actual) > 0 else np.nan

    logging.info(f"📊 Hasil Evaluasi {set_name}:")
    logging.info(f"  MAE  (skala asli): {mae:.4f}")
    logging.info(f"  RMSE (skala asli): {rmse:.4f}")
    logging.info(f"  Directional Accuracy: {directional_accuracy:.2f}%")
    
    if not np.isnan(mape):
         logging.info(f"  MAPE (skala asli): {mape:.2f}%")
    else:
         logging.info("  MAPE (skala asli): N/A")
    
    print(f"📊 VISUALISASI: Evaluasi model pada {set_name} selesai")
    print(f"📊 VISUALISASI: MAE={mae:.4f}, RMSE={rmse:.4f}, DIR_ACC={directional_accuracy:.2f}%")

    return preds_original, y_set_original, y_set_time, {
        'mae': mae, 
        'rmse': rmse, 
        'mape': mape,
        'directional_accuracy': directional_accuracy
    }

# ============ Kelas Subtract (untuk N-BEATS) ============
class Subtract(tf.keras.layers.Layer):
    """Layer untuk operasi pengurangan"""
    def __init__(self, **kwargs):
        super(Subtract, self).__init__(**kwargs)
        
    def call(self, inputs):
        return inputs[0] - inputs[1]

# ============ Main Training ============
def main_training():
    logging.info("--- Memulai Proses Training Model ---")
    print("📊 VISUALISASI: Proses training model dimulai")
    
    try:
        # Range data training yang lebih luas
        df = acquire_data('XAUUSD', mt5.TIMEFRAME_D1, pd.Timestamp(2008,1,1), pd.Timestamp(2024,12,31))

        if df.empty:
             logging.error("❌ Akuisisi data gagal atau mengembalikan data kosong.")
             sys.exit(1)

        # Pra-pemrosesan data untuk training
        df_processed, scaler_X, feature_cols = preprocess_for_training(df.copy())

        # Ukuran jendela
        WINDOW_SIZE = 10
        max_feature_lookback = 89  # Diubah karena EMA 89 membutuhkan 89 bar

        # Membuat dataset jendela (X, y) dan waktu target (y_time)
        X_all, y_raw_all, y_time_all = create_dataset(df_processed, window_size=WINDOW_SIZE, feature_cols=feature_cols)

        # Jika create_dataset mengembalikan data kosong, hentikan proses.
        if len(X_all) == 0:
            logging.error(f"❌ Gagal membuat dataset training dari data yang diproses dengan window_size={WINDOW_SIZE}. Tidak cukup sampel valid.")
            sys.exit(1)

        # Scaling target y
        scaler_y = MinMaxScaler()
        y_all = scaler_y.fit_transform(y_raw_all)
        logging.info("✅ Target output (y) berhasil di-scale.")

        # Setup direktori artefak
        ARTIFACTS_DIR = "model_artifacts"
        os.makedirs(ARTIFACTS_DIR, exist_ok=True)
        logging.info(f"✅ Direktori artefak '{ARTIFACTS_DIR}' siap.")

        # Simpan scaler dan metadata
        joblib.dump(scaler_X, os.path.join(ARTIFACTS_DIR, "scaler_X.save"))
        joblib.dump(scaler_y, os.path.join(ARTIFACTS_DIR, "scaler_y.save"))
        logging.info(f"✅ Scaler X dan Y disimpan di '{ARTIFACTS_DIR}'.")

        metadata = {
            "model_architecture": "Hybrid: LSTM + Attention + N-BEATS",
            "features_used": feature_cols,
            "outputs_predicted": ["high", "low", "close"],
            "window_size": WINDOW_SIZE,
            "feature_lookback": max_feature_lookback,
            "training_data_range": f"{df['time'].iloc[0].strftime('%Y-%m-%d')} to {df['time'].iloc[-1].strftime('%Y-%m-%d')}" if not df.empty else "N/A",
            "notes": "Model hibrida dengan N-BEATS, LSTM, dan Attention mechanism. Menggunakan indikator ATR 9, ATR 45, EMA 21, dan EMA 89.",
            "hyperparameters": {
                "lstm_units": 128,
                "attention_heads": 4,
                "attention_key_dim": 32,
                "dropout_rate_lstm": 0.2,
                "dropout_rate_dense": 0.3,
                "l2_regularization": 0.0005,
                "optimizer": "Adam",
                "learning_rate": 0.001,
                "batch_size": 32,
                "early_stopping_patience": 15,
                "tscv_splits": 5,
                "n_beats_blocks": 3,
                "n_beats_units": 128,
                "n_beats_theta_dim": 32
            }
        }
        METADATA_PATH = os.path.join(ARTIFACTS_DIR, "model_info.json")
        with open(METADATA_PATH, "w") as f:
            json.dump(metadata, f, indent=4)
        logging.info(f"✅ Metadata model disimpan di '{METADATA_PATH}'")

        # Split data trainval vs Test
        TEST_SET_SIZE_PERCENT = 0.2
        split_idx = int(len(X_all) * (1 - TEST_SET_SIZE_PERCENT))

        # Validasi ukuran split
        if split_idx <= WINDOW_SIZE:
             logging.error(f"❌ Ukuran data trainval ({split_idx} sampel) tidak cukup untuk window_size={WINDOW_SIZE}. Butuh minimal {WINDOW_SIZE + 1} sampel.")
             sys.exit(1)

        if len(X_all) - split_idx < 1:
             logging.error(f"❌ Ukuran data test ({len(X_all) - split_idx} sampel) tidak cukup. Butuh minimal 1 sampel.")
             sys.exit(1)

        X_trainval, y_trainval = X_all[:split_idx], y_all[:split_idx]
        X_test, y_test = X_all[split_idx:], y_all[split_idx:]
        y_time_test = y_time_all[split_idx:]

        logging.info(f"✅ Data dibagi: Training+Validation ({len(X_trainval)} sampel), Test ({len(X_test)} sampel)")

        # Time Series Cross-Validation (TSCV)
        N_SPLITS_TSCV = 5
        tscv = TimeSeriesSplit(n_splits=N_SPLITS_TSCV)

        best_val_loss_in_tscv = float('inf')
        temp_model_path = os.path.join(ARTIFACTS_DIR, "temp_best_model_fold_tscv.h5")

        logging.info(f"⏳ Memulai Time Series Cross-Validation dengan {tscv.n_splits} fold pada data Training+Validation...")
        print(f"📊 VISUALISASI: Time Series Cross-Validation dengan {tscv.n_splits} fold dimulai")

        for fold, (train_idx, val_idx) in enumerate(tscv.split(X_trainval)):
            logging.info(f"--- 🔁 Fold {fold+1}/{tscv.n_splits} ---")

            X_train, y_train = X_trainval[train_idx], y_trainval[train_idx]
            X_val, y_val = X_trainval[val_idx], y_trainval[val_idx]

            if len(X_train) == 0 or len(X_val) == 0:
                 logging.warning(f"⚠️ Fold {fold+1}: Ukuran data train ({len(X_train)}) atau validasi ({len(X_val)}) kosong. Melewati fold ini.")
                 continue

            # Set seed lagi sebelum membuat model dan training per fold
            np.random.seed(42 + fold)
            tf.random.set_seed(42 + fold)
            random.seed(42 + fold)

            train_ds = tf.data.Dataset.from_tensor_slices((X_train, y_train)).shuffle(len(X_train), seed=42).batch(32).prefetch(tf.data.AUTOTUNE)
            val_ds = tf.data.Dataset.from_tensor_slices((X_val, y_val)).batch(32).prefetch(tf.data.AUTOTUNE)

            # Bangun model hibrida
            fold_model = build_hybrid_model(
                X_trainval.shape[1:], 
                y_trainval.shape[1],
                n_blocks=3
            )

            trained_fold_model, history = train_model(fold_model, train_ds, val_ds, name=f"fold_{fold+1}")

            val_loss, val_mae, val_mse = trained_fold_model.evaluate(val_ds, verbose=0)

            logging.info(f"✅ Fold {fold+1} selesai. Val Loss (scaled): {val_loss:.4f}, Val MAE (scaled): {val_mae:.4f}")

            if val_loss < best_val_loss_in_tscv:
                best_val_