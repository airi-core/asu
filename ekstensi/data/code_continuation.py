if val_loss < best_val_loss_in_tscv:
                best_val_loss_in_tscv = val_loss
                trained_fold_model.save(temp_model_path)
                logging.info(f"💾 Fold {fold+1} menjadi model terbaik sejauh ini. Model disimpan.")

        logging.info(f"✅ Time Series Cross-Validation selesai.")

        # Memuat model terbaik dari TSCV untuk evaluasi dan inferensi
        logging.info(f"⏳ Memuat model terbaik dari cross-validation...")
        print(f"📊 VISUALISASI: Memuat model terbaik dari {N_SPLITS_TSCV} fold TSCV")
        model = tf.keras.models.load_model(
            temp_model_path, 
            custom_objects={'Subtract': Subtract}
        )
        logging.info(f"✅ Model terbaik dari cross-validation berhasil dimuat.")

        # Evaluasi model pada set Test
        preds_test, y_test_original, y_time_test, test_metrics = evaluate_model(
            model, X_test, y_test, scaler_y, y_time_test, "Test"
        )

        # Visualisasi hasil prediksi test set
        if len(preds_test) > 0:
            plt.figure(figsize=(14, 7))
            plt.subplot(3, 1, 1)
            plt.plot(y_time_test, y_test_original[:, 0], 'b-', label='Aktual High')
            plt.plot(y_time_test, preds_test[:, 0], 'r--', label='Prediksi High')
            plt.title('Prediksi vs Aktual (High)')
            plt.legend()
            plt.grid(True)
            
            plt.subplot(3, 1, 2)
            plt.plot(y_time_test, y_test_original[:, 1], 'g-', label='Aktual Low')
            plt.plot(y_time_test, preds_test[:, 1], 'r--', label='Prediksi Low')
            plt.title('Prediksi vs Aktual (Low)')
            plt.legend()
            plt.grid(True)
            
            plt.subplot(3, 1, 3)
            plt.plot(y_time_test, y_test_original[:, 2], 'k-', label='Aktual Close')
            plt.plot(y_time_test, preds_test[:, 2], 'r--', label='Prediksi Close')
            plt.title('Prediksi vs Aktual (Close)')
            plt.legend()
            plt.grid(True)
            
            plt.tight_layout()
            plt.savefig(os.path.join(ARTIFACTS_DIR, "test_set_predictions.png"))
            print("📊 VISUALISASI: Grafik prediksi vs aktual pada test set disimpan")

        # Simpan model akhir
        logging.info("⏳ Menyimpan model akhir dan artefak terkait...")
        model.save(os.path.join(ARTIFACTS_DIR, "final_model.h5"))
        
        # Simpan metrik evaluasi akhir
        metrics_dict = {
            "test_metrics": test_metrics
        }
        
        with open(os.path.join(ARTIFACTS_DIR, "evaluation_metrics.json"), "w") as f:
            # Konversi np.float32 ke float untuk JSON serialization
            metrics_dict_serializable = {}
            for key, val_dict in metrics_dict.items():
                metrics_dict_serializable[key] = {k: float(v) if not np.isnan(v) else None for k, v in val_dict.items()}
            
            json.dump(metrics_dict_serializable, f, indent=4)
        
        logging.info("✅ Model akhir dan artefak terkait berhasil disimpan.")
        print("📊 VISUALISASI: Model akhir berhasil disimpan")

        return model, metadata, test_metrics

    except Exception as e:
        logging.error(f"❌ Terjadi kesalahan dalam proses training: {e}")
        print(f"📊 VISUALISASI: ERROR - Proses training terhenti karena kesalahan")
        import traceback
        logging.error(traceback.format_exc())
        sys.exit(1)

# ============ Inference ============
def process_new_data_for_prediction(new_data, scaler_X, feature_cols, window_size):
    """Memproses data baru untuk prediksi."""
    logging.info(f"⏳ Memproses data baru untuk prediksi...")
    print(f"📊 VISUALISASI: Memproses {len(new_data)} bar data baru untuk prediksi")
    
    # Pastikan new_data memiliki minimal window_size + max_feature_lookback data points
    if len(new_data) < window_size:
        raise ValueError(f"⚠️ Data tidak cukup untuk prediksi dengan window_size={window_size}. Butuh min. {window_size} bar.")
    
    # Tambahkan fitur teknikal
    new_data = add_technical_features(new_data)
    new_data = new_data.dropna().reset_index(drop=True)  # Hapus NaN setelah tambah fitur
    
    if len(new_data) < window_size:
        raise ValueError(f"⚠️ Data tidak cukup setelah penambahan indikator teknikal dan pembersihan NaN. Tersisa {len(new_data)} dari {window_size} yang dibutuhkan.")
    
    # Ambil sampel data terakhir sesuai window_size
    recent_data = new_data.iloc[-window_size:].copy()
    
    # Validasi keberadaan semua kolom
    for col in feature_cols:
        if col not in recent_data.columns:
            raise ValueError(f"⚠️ Kolom {col} tidak ditemukan di data yang diproses")
    
    # Scaling fitur X menggunakan scaler yang sudah di-fit di training
    if recent_data.empty:
        raise ValueError("⚠️ Data setelah pra-pemrosesan kosong.")
        
    recent_features = scaler_X.transform(recent_data[feature_cols])
    
    # Reshape untuk input model
    X_pred = np.array([recent_features])
    
    logging.info(f"✅ Data baru berhasil diproses untuk prediksi. Shape: {X_pred.shape}")
    return X_pred

def predict_next_bar(model, new_data, scaler_X, scaler_y, feature_cols, window_size):
    """Memprediksi bar berikutnya dari data terbaru"""
    try:
        print(f"📊 VISUALISASI: Prediksi bar berikutnya dimulai")
        # Persiapkan data untuk prediksi
        X_pred = process_new_data_for_prediction(new_data, scaler_X, feature_cols, window_size)
        
        # Prediksi dalam skala yang di-scale
        pred_scaled = model.predict(X_pred, verbose=0)[0]
        
        # Inverse transform untuk mendapatkan prediksi dalam skala asli
        pred_original = scaler_y.inverse_transform(pred_scaled.reshape(1, -1)).reshape(-1)
        
        # Bentuk output yang berarti
        prediction = {
            'high': float(pred_original[0]),
            'low': float(pred_original[1]),
            'close': float(pred_original[2])
        }
        
        logging.info(f"✅ Prediksi bar berikutnya: High={prediction['high']:.5f}, Low={prediction['low']:.5f}, Close={prediction['close']:.5f}")
        print(f"📊 VISUALISASI: Prediksi bar berikutnya berhasil - High={prediction['high']:.5f}, Low={prediction['low']:.5f}, Close={prediction['close']:.5f}")
        
        return prediction
    
    except Exception as e:
        logging.error(f"❌ Gagal memprediksi bar berikutnya: {e}")
        print(f"📊 VISUALISASI: ERROR - Prediksi bar berikutnya gagal")
        import traceback
        logging.error(traceback.format_exc())
        return None

# ============ Implementasi Rolling Window Backtest ============
def perform_rolling_window_backtest(df, model, scaler_X, scaler_y, feature_cols, window_size, backtest_window=30):
    """Melakukan backtesting dengan rolling window approach"""
    logging.info(f"⏳ Memulai backtest dengan rolling window {backtest_window} candle...")
    print(f"📊 VISUALISASI: Backtest rolling window ({backtest_window} candle) dimulai")
    
    # Memastikan data cukup untuk backtest
    if len(df) < window_size + backtest_window:
        logging.error(f"❌ Data tidak cukup untuk backtest. Butuh min {window_size + backtest_window} candle, tersedia {len(df)}.")
        return None
    
    actuals = []
    predictions = []
    timestamps = []
    
    df_processed = add_technical_features(df.copy())
    df_processed = df_processed.dropna()
    
    # Rolling window backtest
    for i in range(len(df_processed) - window_size - backtest_window, len(df_processed) - window_size):
        # Data hingga titik i untuk prediksi
        historical_data = df_processed.iloc[:i+1].copy()
        
        # Proses data untuk prediksi
        try:
            X_pred = process_new_data_for_prediction(historical_data, scaler_X, feature_cols, window_size)
            
            # Prediksi
            pred_scaled = model.predict(X_pred, verbose=0)[0]
            pred_original = scaler_y.inverse_transform(pred_scaled.reshape(1, -1)).reshape(-1)
            
            # Ambil nilai aktual
            actual_next = df_processed.iloc[i+1][['high', 'low', 'close']].values
            timestamp = df_processed.iloc[i+1]['time']
            
            # Simpan hasil
            predictions.append(pred_original)
            actuals.append(actual_next)
            timestamps.append(timestamp)
            
            if (i - (len(df_processed) - window_size - backtest_window)) % 5 == 0:
                logging.info(f"⏳ Backtest progress: {i - (len(df_processed) - window_size - backtest_window) + 1}/{backtest_window} candle")
        
        except Exception as e:
            logging.error(f"❌ Error pada backtest candle ke-{i}: {e}")
            continue
    
    if not predictions:
        logging.warning("⚠️ Tidak ada prediksi yang dihasilkan dalam backtest.")
        return None
    
    # Konversi ke array numpy
    predictions = np.array(predictions)
    actuals = np.array(actuals)
    timestamps = np.array(timestamps)
    
    # Hitung metrik evaluasi
    mae = mean_absolute_error(actuals, predictions)
    rmse = np.sqrt(mean_squared_error(actuals, predictions))
    
    # Hitung MAPE dengan penanganan division by zero
    mape_values = np.abs((actuals - predictions) / np.maximum(np.abs(actuals), 1e-10)) * 100
    mape = np.mean(mape_values)
    
    # Hitung directional accuracy untuk close price
    direction_actual = np.sign(actuals[1:, 2] - actuals[:-1, 2])
    direction_pred = np.sign(predictions[1:, 2] - predictions[:-1, 2])
    directional_accuracy = np.mean(direction_actual == direction_pred) * 100 if len(direction_actual) > 0 else np.nan
    
    logging.info(f"📊 Hasil Backtest ({backtest_window} candle):")
    logging.info(f"  MAE : {mae:.4f}")
    logging.info(f"  RMSE: {rmse:.4f}")
    logging.info(f"  MAPE: {mape:.2f}%")
    logging.info(f"  Directional Accuracy: {directional_accuracy:.2f}%")
    
    print(f"📊 VISUALISASI: Backtest selesai - MAE={mae:.4f}, RMSE={rmse:.4f}, MAPE={mape:.2f}%, DIR_ACC={directional_accuracy:.2f}%")
    
    # Plot hasil backtest
    plt.figure(figsize=(14, 10))
    
    # Plot untuk High
    plt.subplot(3, 1, 1)
    plt.plot(timestamps, actuals[:, 0], 'b-', label='Aktual High')
    plt.plot(timestamps, predictions[:, 0], 'r--', label='Prediksi High')
    plt.title('Backtest Prediksi vs Aktual (High)')
    plt.legend()
    plt.grid(True)
    
    # Plot untuk Low
    plt.subplot(3, 1, 2)
    plt.plot(timestamps, actuals[:, 1], 'g-', label='Aktual Low')
    plt.plot(timestamps, predictions[:, 1], 'r--', label='Prediksi Low')
    plt.title('Backtest Prediksi vs Aktual (Low)')
    plt.legend()
    plt.grid(True)
    
    # Plot untuk Close
    plt.subplot(3, 1, 3)
    plt.plot(timestamps, actuals[:, 2], 'k-', label='Aktual Close')
    plt.plot(timestamps, predictions[:, 2], 'r--', label='Prediksi Close')
    plt.title('Backtest Prediksi vs Aktual (Close)')
    plt.legend()
    plt.grid(True)
    
    plt.tight_layout()
    plt.savefig('model_artifacts/backtest_results.png')
    print("📊 VISUALISASI: Grafik hasil backtest disimpan")
    
    return {
        'mae': mae,
        'rmse': rmse,
        'mape': mape,
        'directional_accuracy': directional_accuracy,
        'timestamps': timestamps,
        'actuals': actuals,
        'predictions': predictions
    }

# ============ Meningkatkan Performa Model ============
def build_optimized_hybrid_model(input_shape, output_dim, n_blocks=3, dropout_rate=0.2, l2_reg=0.0005):
    """Membangun model hibrida dengan optimasi arsitektur"""
    print(f"📊 VISUALISASI: Membangun model hibrida teroptimasi dengan {n_blocks} blok N-BEATS")
    
    # Input shape: (window_size, num_features)
    inputs = Input(shape=input_shape)
    
    # === LSTM + Attention Path ===
    # Bidirectional LSTM untuk meningkatkan performa
    lstm_forward = LSTM(128, return_sequences=True, kernel_regularizer=tf.keras.regularizers.l2(l2_reg))(inputs)
    lstm_backward = LSTM(128, return_sequences=True, go_backwards=True, kernel_regularizer=tf.keras.regularizers.l2(l2_reg))(inputs)
    lstm_bidirectional = Concatenate()([lstm_forward, lstm_backward])
    lstm_out = Dropout(dropout_rate)(lstm_bidirectional)

    # Layer MultiHeadAttention dengan peningkatan jumlah heads dan dimensi
    attention_output = MultiHeadAttention(
        num_heads=8, key_dim=64, dropout=dropout_rate)(lstm_out, lstm_out)

    # Residual connection dan layer normalization
    lstm_out = Add()([lstm_out, attention_output])
    lstm_out = LayerNormalization()(lstm_out)
    
    # GlobalAveragePooling untuk mereduksi dimensi waktu
    lstm_out = GlobalAveragePooling1D()(lstm_out)
    
    # Dense layer dengan ukuran meningkat
    lstm_out = Dense(128, activation='swish', kernel_regularizer=tf.keras.regularizers.l2(l2_reg))(lstm_out)
    lstm_out = Dropout(dropout_rate)(lstm_out)
    
    # === N-BEATS Path ===
    # Residual stacking dengan multiple blocks dan ukuran meningkat
    backcast = inputs
    forecast = None
    units = 192
    theta_dim = 64
    
    for i in range(n_blocks):
        # Penggunaan share_theta yang cerdas - blok awal lebih interpretable, blok akhir lebih poweful
        use_share_theta = True if i < n_blocks // 2 else False
        
        # Pass dimensi input yang benar ke blok N-BEATS
        block_input = backcast
        b, f = create_nbeats_block(
            block_input, 
            units=units, 
            theta_dim=theta_dim, 
            share_theta=use_share_theta,  
            layer_norm=True
        )
        
        # Residual connection untuk backcast (perbaikan logika)
        backcast = Subtract()([backcast, b])
        
        # Akumulasi ramalan dengan pembobotan dinamis
        # Blok terakhir mendapat bobot lebih tinggi
        weight = 1.0 + 0.2 * i / (n_blocks - 1)  # Bobot meningkat dari 1.0 hingga 1.2
        weighted_f = tf.multiply(f, weight)
        
        if forecast is None:
            forecast = weighted_f
        else:
            forecast = Add()([forecast, weighted_f])
    
    # Self-attention pada output forecasting untuk meningkatkan integrasi fitur
    forecast_reshaped = tf.expand_dims(forecast, axis=1)  # Tambahkan dimensi sekuens (batch, 1, features)
    forecast_attention = MultiHeadAttention(num_heads=4, key_dim=16)(forecast_reshaped, forecast_reshaped)
    forecast_attention = tf.squeeze(forecast_attention, axis=1)  # Hapus dimensi sekuens
    
    # Menggabungkan output dari kedua path dengan layer gabungan
    combined = Concatenate()([lstm_out, forecast, forecast_attention])
    
    # Layer terakhir dengan dropout untuk mencegah overfitting
    combined = Dense(64, activation='swish')(combined)
    combined = Dropout(0.1)(combined)
    
    # Final dense layer
    outputs = Dense(output_dim)(combined)
    
    model = Model(inputs=inputs, outputs=outputs)
    logging.info("✅ Model Hibrida Teroptimasi berhasil dibangun.")
    model.summary(print_fn=lambda msg: logging.info(msg))
    
    return model

# ============ Adaptive Batch Size dan Learning Rate ============
def adaptive_learning_params(dataset_size):
    """Menentukan parameter adaptif berdasarkan ukuran dataset"""
    
    # Batch size adaptif (lebih besar untuk dataset lebih besar)
    if dataset_size < 1000:
        batch_size = 16
    elif dataset_size < 5000:
        batch_size = 32
    elif dataset_size < 10000:
        batch_size = 64
    else:
        batch_size = 128
    
    # Learning rate adaptif (lebih kecil untuk dataset lebih kecil)
    if dataset_size < 1000:
        learning_rate = 0.0005
    elif dataset_size < 5000:
        learning_rate = 0.001
    elif dataset_size < 10000:
        learning_rate = 0.002
    else:
        learning_rate = 0.003
    
    print(f"📊 VISUALISASI: Parameter adaptif - Batch size={batch_size}, Learning rate={learning_rate}")
    return batch_size, learning_rate

# ============ Flask API ============
app = Flask(__name__)
model = None
scaler_X = None
scaler_y = None
model_info = None

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "UP", "model_loaded": model is not None})

@app.route('/info', methods=['GET'])
def model_information():
    global model_info
    if model_info is None:
        return jsonify({"error": "Model belum dimuat"}), 503
    
    return jsonify(model_info)

@app.route('/predict', methods=['POST'])
def predict():
    global model, scaler_X, scaler_y, model_info
    
    if model is None or scaler_X is None or scaler_y is None:
        return jsonify({"error": "Model atau scaler belum dimuat"}), 503
    
    try:
        data = request.json
        if not data or 'data' not in data:
            return jsonify({"error": "Format data tidak valid. Membutuhkan array data dengan OHLCV"}), 400
        
        # Ekstrak data dari request
        json_data = data['data']
        df = pd.DataFrame(json_data)
        
        # Validasi kolom minimum yang diperlukan
        required_cols = ['time', 'open', 'high', 'low', 'close', 'tick_volume']
        if not all(col in df.columns for col in required_cols):
            return jsonify({"error": f"Data harus memiliki kolom: {required_cols}"}), 400
        
        # Konversi kolom waktu
        if 'time' in df.columns:
            df['time'] = pd.to_datetime(df['time'])
        
        window_size = model_info['window_size']
        features = model_info['features_used']
        
        # Prediksi
        prediction = predict_next_bar(model, df, scaler_X, scaler_y, features, window_size)
        
        if prediction is None:
            return jsonify({"error": "Gagal membuat prediksi"}), 500
        
        return jsonify({
            "prediction": prediction,
            "timestamp": pd.Timestamp.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"Error saat prediksi API: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route('/backtest', methods=['POST'])
def backtest():
    global model, scaler_X, scaler_y, model_info
    
    if model is None or scaler_X is None or scaler_y is None:
        return jsonify({"error": "Model atau scaler belum dimuat"}), 503
    
    try:
        data = request.json
        if not data or 'data' not in data:
            return jsonify({"error": "Format data tidak valid. Membutuhkan array data dengan OHLCV"}), 400
        
        backtest_window = data.get('window', 30)
        
        # Ekstrak data dari request
        json_data = data['data']
        df = pd.DataFrame(json_data)
        
        # Validasi kolom minimum yang diperlukan
        required_cols = ['time', 'open', 'high', 'low', 'close', 'tick_volume']
        if not all(col in df.columns for col in required_cols):
            return jsonify({"error": f"Data harus memiliki kolom: {required_cols}"}), 400
        
        # Konversi kolom waktu
        if 'time' in df.columns:
            df['time'] = pd.to_datetime(df['time'])
        
        window_size = model_info['window_size']
        features = model_info['features_used']
        
        # Menjalankan backtest
        backtest_results = perform_rolling_window_backtest(
            df, model, scaler_X, scaler_y, features, window_size, backtest_window
        )
        
        if backtest_results is None:
            return jsonify({"error": "Gagal melakukan backtest"}), 500
        
        # Convert numpy values to Python native types for JSON serialization
        serializable_results = {
            'mae': float(backtest_results['mae']),
            'rmse': float(backtest_results['rmse']),
            'mape': float(backtest_results['mape']),
            'directional_accuracy': float(backtest_results['directional_accuracy'])
        }
        
        return jsonify({
            "backtest_metrics": serializable_results,
            "window_size": backtest_window,
            "timestamp": pd.Timestamp.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"Error saat backtest API: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

def load_model_artifacts():
    global model, scaler_X, scaler_y, model_info
    
    artifacts_dir = "model_artifacts"
    
    try:
        # Memuat scaler
        scaler_X = joblib.load(os.path.join(artifacts_dir, "scaler_X.save"))
        scaler_y = joblib.load(os.path.join(artifacts_dir, "scaler_y.save"))
        
        # Memuat metadata model
        with open(os.path.join(artifacts_dir, "model_info.json"), "r") as f:
            model_info = json.load(f)
        
        # Memuat model
        model = tf.keras.models.load_model(
            os.path.join(artifacts_dir, "final_model.h5"),
            custom_objects={'Subtract': Subtract}
        )
        
        logging.info("✅ Model dan artefak pendukung berhasil dimuat.")
        return True
        
    except Exception as e:
        logging.error(f"❌ Gagal memuat model dan artefak: {e}")
        return False

# ============ Main Function ============
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--train":
        logging.info("🚀 Mode: Training")
        model, model_info, test_metrics = main_training()
        print("📊 VISUALISASI: Training selesai. Running API server...")
        app.run(host='0.0.0.0', port=5000)
    else:
        logging.info("🚀 Mode: API Server")
        if load_model_artifacts():
            logging.info("🌐 Menjalankan API server di port 5000...")
            app.run(host='0.0.0.0', port=5000)
        else:
            logging.error("❌ API server tidak dapat dijalankan karena gagal memuat model.")
            sys.exit(1)