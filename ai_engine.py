# ai_engine.py (Versi 3 - Single Model / One-Hot Encoding)
# Script ini berjalan sebagai daemon untuk memproses data baru.
# Script ini memuat SATU model dan membuat fitur
# one-hot-encoding secara dinamis untuk prediksi.

import psycopg2
import psycopg2.extras
import joblib
import pandas as pd
import numpy as np
import time
import os
from datetime import datetime

# --- KONFIGURASI ---
DB_HOST = "127.0.0.1"
DB_NAME = "safe_db"       # Pastikan nama DB benar
DB_USER = "postgres"
DB_PASS = "Naufal"        # Pastikan password benar

# --- KONFIGURASI MODEL BARU ---
# Nama file model tunggal Anda
MODEL_FILE_PATH = 'safe_anomaly_model_multidevice.joblib' 

# Interval polling (dalam detik)
POLL_INTERVAL = 5

# --- VARIABEL GLOBAL MODEL ---
# Variabel ini akan diisi saat skrip dimulai
MODEL = None
# Ini adalah daftar LENGKAP fitur yang diharapkan model
# (cth: ['temp', 'hum', 'hour', 'dev_id_A', 'dev_id_B', ...])
MODEL_FEATURES_LIST = []

# --- KONEKSI DATABASE ---
def get_db_connection():
    """Membuat koneksi DB dan mengembalikan cursor sebagai dictionary."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        return conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    except psycopg2.Error as e:
        print(f"[ERROR] Gagal koneksi ke database: {e}")
        return None, None

# --- MANAJEMEN MODEL ---
def load_model_and_features():
    """
    Memuat model tunggal dan daftar fitur yang disimpannya.
    """
    global MODEL, MODEL_FEATURES_LIST
    
    print(f"[INFO] Memuat model AI dari file: {MODEL_FILE_PATH}...")
    try:
        if not os.path.exists(MODEL_FILE_PATH):
            print(f"[FATAL ERROR] File model tidak ditemukan di: '{MODEL_FILE_PATH}'")
            return False
            
        MODEL = joblib.load(MODEL_FILE_PATH)
        
        # Ini adalah bagian terpenting:
        # Mengambil daftar fitur yang disimpan di dalam model
        MODEL_FEATURES_LIST = MODEL.feature_names_
        
        print(f"[SUCCESS] Model '{MODEL_FILE_PATH}' berhasil dimuat.")
        print(f"[INFO] Model ini dilatih dengan {len(MODEL_FEATURES_LIST)} fitur:")
        print(f"       {MODEL_FEATURES_LIST}")
        return True
        
    except AttributeError:
        print(f"[FATAL ERROR] Gagal memuat daftar fitur (feature_names_).")
        print("       Pastikan Anda menyimpan model dengan 'trained_model.feature_names_ = ...' di skrip training Anda.")
        return False
    except Exception as e:
        print(f"[FATAL ERROR] Gagal memuat model: {e}")
        return False

# --- FEATURE ENGINEERING (BARU) ---
def create_features_for_prediction(data_row):
    """
    Membuat DataFrame 1 baris yang cocok dengan fitur yang diharapkan model,
    termasuk One-Hot Encoding untuk device_id.
    """
    global MODEL_FEATURES_LIST
    
    try:
        # 1. Ambil data mentah dari baris database
        device_id = data_row['device_id']
        dt_object = data_row['timestamp_utc']

        # 2. Buat dictionary fitur, mulai dengan SEMUA fitur = 0
        feature_dict = {feature: 0 for feature in MODEL_FEATURES_LIST}
        
        # 3. Isi fitur-fitur dasar (Time-based dan sensor)
        # Gunakan 'if' untuk jaga-jaga jika model tidak dilatih dengan fitur tsb
        if 'temperature' in feature_dict:
            feature_dict['temperature'] = data_row['temperature']
        if 'humidity' in feature_dict:
            feature_dict['humidity'] = data_row['humidity']
        if 'hour' in feature_dict:
            feature_dict['hour'] = dt_object.hour
        if 'dayofweek' in feature_dict:
            feature_dict['dayofweek'] = dt_object.weekday()
        if 'minute' in feature_dict:
            feature_dict['minute'] = dt_object.minute

        # 4. Buat dan set fitur One-Hot Encoding
        one_hot_feature_name = f"device_id_{device_id}"
        
        # Set kolom 'device_id_xxxx' yang relevan menjadi 1
        if one_hot_feature_name in feature_dict:
            feature_dict[one_hot_feature_name] = 1
        else:
            # Ini terjadi jika data datang dari device_id baru
            # yang tidak ada saat model dilatih.
            print(f"[WARN] Device '{device_id}' (dari baris ID {data_row['id']}) tidak dikenal oleh model.")
            print("       Hasil prediksi mungkin tidak akurat.")

        # 5. Konversi ke DataFrame, pastikan urutan kolomnya BENAR
        features_df = pd.DataFrame([feature_dict], columns=MODEL_FEATURES_LIST)
        return features_df

    except Exception as e:
        print(f"[ERROR] Gagal saat feature engineering (ID: {data_row.get('id')}): {e}")
        return None

# --- FUNGSI UTAMA AI ENGINE ---
def run_ai_engine():
    """Fungsi utama untuk memproses data baru."""
    
    # Muat model saat start. Jika gagal, skrip berhenti.
    if not load_model_and_features():
        print("[INFO] AI Engine berhenti karena model gagal dimuat.")
        return

    print("\n[INFO] AI Engine (Single-Model) dimulai. Menunggu data baru...")

    while True:
        conn, cur = None, None
        try:
            conn, cur = get_db_connection()
            if not conn:
                print("[WARN] Koneksi DB gagal, mencoba lagi...")
                time.sleep(POLL_INTERVAL)
                continue

            # Ambil data yang belum diproses (HARUS menyertakan 'device_id')
            cur.execute("""
                SELECT id, timestamp_utc, temperature, humidity, device_id
                FROM sensor_readings
                WHERE is_anomaly IS NULL
                ORDER BY timestamp_utc ASC
                LIMIT 100;
            """)
            new_rows = cur.fetchall()

            if not new_rows:
                print(f"Tidak ada data baru. Tidur selama {POLL_INTERVAL} detik...", end="\r")
                time.sleep(POLL_INTERVAL)
                continue

            print(f"\n[INFO] Ditemukan {len(new_rows)} data baru. Memproses...")

            for row in new_rows:
                # Cek jika device_id ada
                if not row['device_id']:
                    print(f"[WARN] Melewatkan data (ID: {row['id']}) karena 'device_id' kosong (NULL).")
                    continue
                    
                # Buat Fitur (Metode One-Hot Encoding)
                features_df = create_features_for_prediction(row)
                if features_df is None:
                    print(f"Melewatkan data (ID: {row['id']}) karena error feature engineering.")
                    continue

                # Lakukan Prediksi (Menggunakan model tunggal)
                prediction = MODEL.predict(features_df)[0]
                is_anomaly_bool = True if prediction == -1 else False

                # Update Database
                cur.execute("""
                    UPDATE sensor_readings
                    SET is_anomaly = %s
                    WHERE id = %s;
                """, (is_anomaly_bool, row['id']))
            
            conn.commit()
            print(f"[SUCCESS] Berhasil memproses dan update {len(new_rows)} baris data.")

        except psycopg2.Error as db_err:
            print(f"\n[ERROR] Database error: {db_err}")
            if conn: conn.rollback()
        except Exception as e:
            print(f"\n[ERROR] Terjadi error tidak terduga: {e}")
        finally:
            if cur: cur.close()
            if conn: conn.close()
            time.sleep(2) 

# --- Titik Masuk Script ---
if __name__ == "__main__":
    run_ai_engine()