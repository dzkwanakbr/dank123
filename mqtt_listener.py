import paho.mqtt.client as mqtt
import psycopg2
import json
from datetime import datetime

# --- KONFIGURASI DATABASE ---
DB_HOST = "127.0.0.1"  # Ganti dengan 'test_db' jika di lingkungan Docker test
DB_NAME = "safe_db"    # Ganti dengan nama DB Anda
DB_USER = "postgres"
DB_PASS = "Naufal"

# --- KONFIGURASI MQTT ---
MQTT_BROKER = "broker.emqx.io" # Mosquitto berjalan di VPS yang sama
MQTT_PORT = 1883
MQTT_TOPIC = "dht/sensor_data"

def connect_db():
    """Membuat koneksi ke database PostgreSQL."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        return conn
    except psycopg2.Error as e:
        print(f"ERROR: Gagal koneksi ke database: {e}")
        return None

def insert_data(conn, data):
    """Menyimpan data sensor ke tabel database."""
    # Pastikan data memiliki timestamp, temperature, dan humidity
    sql = """
    INSERT INTO sensor_readings (timestamp_utc, temperature, humidity, device_id)
    VALUES (to_timestamp(%s), %s, %s, %s);
    """
    
    # Data dari ESP8266 menggunakan Unix Epoch Time (detik)
    timestamp_epoch = data.get('timestamp')
    temp = data.get('temperature')
    hum = data.get('humidity')
    device = data.get('device_id')
    
    if not all([timestamp_epoch, temp, hum, device]):
        print("Data tidak lengkap, mengabaikan.")
        return
        
    try:
        cur = conn.cursor()
        cur.execute(sql, (timestamp_epoch, temp, hum, device))
        conn.commit()
        print(f"Data tersimpan: T={temp}C, H={hum}%")
    except psycopg2.Error as e:
        print(f"ERROR: Gagal insert data: {e}")
        conn.rollback()
    finally:
        cur.close()

# --- FUNGSI MQTT CALLBACKS ---

def on_connect(client, userdata, flags, rc):
    """Callback saat berhasil terhubung ke broker."""
    if rc == 0:
        print(f"Terhubung ke MQTT Broker: {MQTT_BROKER}")
        client.subscribe(MQTT_TOPIC)
    else:
        print(f"Gagal koneksi, kode error: {rc}")

def on_message(client, userdata, msg):
    """Callback saat menerima pesan."""
    conn = userdata['db_conn']
    try:
        payload = msg.payload.decode()
        data = json.loads(payload)
        insert_data(conn, data)
    except json.JSONDecodeError:
        print("ERROR: Gagal decode JSON.")
    except Exception as e:
        print(f"ERROR umum saat memproses pesan: {e}")


def run_mqtt_listener():
    conn = connect_db()
    if not conn:
        return

    # UserData untuk membawa koneksi DB ke dalam fungsi on_message
    client = mqtt.Client(userdata={"db_conn": conn})
    client.on_connect = on_connect
    client.on_message = on_message

    print(f"Mencoba koneksi ke broker di {MQTT_BROKER}:{MQTT_PORT}...")
    client.connect(MQTT_BROKER, MQTT_PORT, 60)

    # Loop untuk menjaga koneksi tetap hidup
    client.loop_forever()

if __name__ == '__main__':
    # Pastikan tabel sudah ada sebelum menjalankan listener
    # Anda perlu menjalankan script setup DB (CREATE TABLE) secara terpisah
    print("Memulai MQTT Listener...")
    run_mqtt_listener()