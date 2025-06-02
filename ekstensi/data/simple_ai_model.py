"""
Rancangan Model AI Sederhana dengan Arsitektur Modular
=====================================================

Arsitektur: Neural Network Sederhana tanpa Dataset Eksternal
Penyimpanan: Format .h5 (HDF5) untuk kompatibilitas lintas platform
Metodologi: Pendekatan pembelajaran mandiri dengan modul terpisah
"""

import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
import json
import os
from datetime import datetime
import pickle

class SimpleAIModel:
    """
    Model AI sederhana dengan kemampuan pembelajaran adaptif
    Dirancang untuk adopsi fungsi dari repositori GitHub
    """
    
    def __init__(self, input_dim=10, hidden_dim=64, output_dim=1, model_name="simple_ai"):
        """
        Inisialisasi Model AI
        
        Parameters:
        -----------
        input_dim : int
            Dimensi input layer
        hidden_dim : int
            Dimensi hidden layer
        output_dim : int
            Dimensi output layer
        model_name : str
            Nama model untuk penyimpanan
        """
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        self.model_name = model_name
        self.model = None
        self.history = None
        self.metadata = {
            'created_at': datetime.now().isoformat(),
            'architecture': 'Simple Neural Network',
            'version': '1.0.0'
        }
        
        # Inisialisasi arsitektur model
        self._build_architecture()
        
    def _build_architecture(self):
        """
        Membangun arsitektur neural network sederhana
        Metodologi: Layer-by-layer construction dengan aktivasi optimal
        """
        self.model = keras.Sequential([
            # Input Layer dengan normalisasi
            layers.Dense(
                self.hidden_dim, 
                input_shape=(self.input_dim,),
                activation='relu',
                kernel_initializer='he_normal',
                name='input_hidden_layer'
            ),
            
            # Dropout untuk regularisasi
            layers.Dropout(0.3, name='regularization_dropout'),
            
            # Hidden Layer kedua untuk kompleksitas bertingkat
            layers.Dense(
                self.hidden_dim // 2,
                activation='relu',
                kernel_initializer='he_normal',
                name='secondary_hidden_layer'
            ),
            
            # Batch Normalization untuk stabilitas training
            layers.BatchNormalization(name='batch_normalization'),
            
            # Output Layer dengan aktivasi sesuai kebutuhan
            layers.Dense(
                self.output_dim,
                activation='sigmoid' if self.output_dim == 1 else 'softmax',
                name='output_layer'
            )
        ])
        
        # Kompilasi model dengan optimizer adaptif
        self.model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.001),
            loss='binary_crossentropy' if self.output_dim == 1 else 'categorical_crossentropy',
            metrics=['accuracy', 'precision', 'recall']
        )
        
        print(f"✓ Arsitektur model berhasil dibangun")
        print(f"  - Input Dimension: {self.input_dim}")
        print(f"  - Hidden Dimension: {self.hidden_dim}")
        print(f"  - Output Dimension: {self.output_dim}")
        
    def generate_synthetic_data(self, num_samples=1000):
        """
        Menghasilkan data sintetis untuk pelatihan
        Metodologi: Pattern-based data generation tanpa dataset eksternal
        """
        np.random.seed(42)  # Reproducibility
        
        # Generasi data input dengan pola matematis
        X = np.random.randn(num_samples, self.input_dim)
        
        # Generasi target berdasarkan pola logis
        if self.output_dim == 1:
            # Binary classification pattern
            y = (np.sum(X[:, :3], axis=1) > 0).astype(int)
        else:
            # Multi-class pattern
            y = np.random.randint(0, self.output_dim, num_samples)
            y = keras.utils.to_categorical(y, self.output_dim)
            
        return X, y
    
    def train_model(self, epochs=50, validation_split=0.2, verbose=1):
        """
        Pelatihan model dengan data sintetis
        Metodologi: Progressive learning dengan early stopping
        """
        print("🚀 Memulai pelatihan model...")
        
        # Generate data pelatihan
        X_train, y_train = self.generate_synthetic_data(1000)
        
        # Callback untuk optimasi pelatihan
        callbacks = [
            keras.callbacks.EarlyStopping(
                monitor='val_loss',
                patience=10,
                restore_best_weights=True,
                verbose=1
            ),
            keras.callbacks.ReduceLROnPlateau(
                monitor='val_loss',
                factor=0.5,
                patience=5,
                min_lr=1e-7,
                verbose=1
            )
        ]
        
        # Pelatihan model
        self.history = self.model.fit(
            X_train, y_train,
            epochs=epochs,
            validation_split=validation_split,
            callbacks=callbacks,
            verbose=verbose
        )
        
        print("✓ Pelatihan model selesai")
        return self.history
    
    def save_model_h5(self, filepath=None):
        """
        Menyimpan model dalam format .h5
        Metodologi: Comprehensive model serialization
        """
        if filepath is None:
            filepath = f"{self.model_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.h5"
        
        # Simpan model utama
        self.model.save(filepath)
        
        # Simpan metadata terpisah
        metadata_path = filepath.replace('.h5', '_metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(self.metadata, f, indent=2)
        
        # Simpan history training jika ada
        if self.history:
            history_path = filepath.replace('.h5', '_history.pkl')
            with open(history_path, 'wb') as f:
                pickle.dump(self.history.history, f)
        
        print(f"✓ Model berhasil disimpan:")
        print(f"  - Model: {filepath}")
        print(f"  - Metadata: {metadata_path}")
        if self.history:
            print(f"  - History: {history_path}")
            
        return filepath
    
    @staticmethod
    def load_model_h5(filepath):
        """
        Memuat model dari file .h5
        Metodologi: Complete model reconstruction
        """
        print(f"📂 Memuat model dari: {filepath}")
        
        # Load model utama
        loaded_model = keras.models.load_model(filepath)
        
        # Load metadata jika tersedia
        metadata_path = filepath.replace('.h5', '_metadata.json')
        metadata = {}
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
        
        # Load history jika tersedia
        history_path = filepath.replace('.h5', '_history.pkl')
        history = None
        if os.path.exists(history_path):
            with open(history_path, 'rb') as f:
                history = pickle.load(f)
        
        print("✓ Model berhasil dimuat")
        print(f"  - Arsitektur: {metadata.get('architecture', 'Unknown')}")
        print(f"  - Versi: {metadata.get('version', 'Unknown')}")
        print(f"  - Dibuat: {metadata.get('created_at', 'Unknown')}")
        
        return loaded_model, metadata, history
    
    def predict_with_confidence(self, X):
        """
        Prediksi dengan tingkat kepercayaan
        Metodologi: Probabilistic prediction with uncertainty quantification
        """
        predictions = self.model.predict(X)
        
        if self.output_dim == 1:
            confidence = np.abs(predictions - 0.5) * 2  # Confidence for binary
            binary_pred = (predictions > 0.5).astype(int)
            return binary_pred, confidence
        else:
            confidence = np.max(predictions, axis=1)  # Max probability as confidence
            class_pred = np.argmax(predictions, axis=1)
            return class_pred, confidence
    
    def get_model_summary(self):
        """
        Menampilkan ringkasan arsitektur model
        """
        print("📊 Ringkasan Arsitektur Model:")
        print("=" * 50)
        self.model.summary()
        print("=" * 50)
        return self.model.summary()

# Fungsi utilitas untuk adopsi dari repositori GitHub
class GitHubAdapterUtils:
    """
    Utility class untuk mengadopsi fungsi dari repositori GitHub
    Metodologi: Modular function integration
    """
    
    @staticmethod
    def adapt_preprocessing_function(github_function):
        """
        Mengadaptasi fungsi preprocessing dari GitHub
        """
        def adapted_function(data):
            # Wrapper untuk fungsi GitHub
            try:
                return github_function(data)
            except Exception as e:
                print(f"⚠️ Error in GitHub function: {e}")
                return data  # Return original data if error
        return adapted_function
    
    @staticmethod
    def integrate_custom_layer(layer_class):
        """
        Mengintegrasikan custom layer dari repositori GitHub
        """
        # Registrasi custom layer untuk Keras
        keras.utils.get_custom_objects()[layer_class.__name__] = layer_class
        return layer_class

# Demonstrasi penggunaan
def demo_implementasi():
    """
    Demonstrasi implementasi lengkap model AI
    """
    print("🔬 Demo Implementasi Model AI Sederhana")
    print("=" * 60)
    
    # 1. Inisialisasi model
    model = SimpleAIModel(input_dim=8, hidden_dim=32, output_dim=1, model_name="demo_ai")
    
    # 2. Tampilkan arsitektur
    model.get_model_summary()
    
    # 3. Pelatihan model
    history = model.train_model(epochs=30, verbose=0)
    
    # 4. Simpan model
    saved_path = model.save_model_h5()
    
    # 5. Load model untuk verifikasi
    loaded_model, metadata, loaded_history = SimpleAIModel.load_model_h5(saved_path)
    
    # 6. Test prediksi
    test_data = np.random.randn(5, 8)
    predictions, confidence = model.predict_with_confidence(test_data)
    
    print("\n📈 Hasil Prediksi Test:")
    for i, (pred, conf) in enumerate(zip(predictions, confidence)):
        print(f"  Sample {i+1}: Prediksi={pred[0]:.0f}, Kepercayaan={conf[0]:.3f}")
    
    return model, saved_path

if __name__ == "__main__":
    # Jalankan demonstrasi
    model, filepath = demo_implementasi()
    
    print(f"\n✅ Demo selesai. Model tersimpan di: {filepath}")
    print("🔧 Siap untuk integrasi dengan repositori GitHub Anda!")
