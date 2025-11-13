from flask import Flask, jsonify, request
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta, timezone 
# CORS dihapus sesuai permintaan

app = Flask(__name__)

# --- KONFIGURASI DATABASE ---
DB_HOST = "127.0.0.1" 
DB_NAME = "safe_db"
DB_USER = "postgres"
DB_PASS = "Naufal"
client_encoding='UTF8'

def get_db_connection():
    """Membuat koneksi DB dan mengembalikan cursor sebagai dictionary."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        return conn, conn.cursor(cursor_factory=RealDictCursor)
    except psycopg2.Error as e:
        print(f"ERROR: Gagal koneksi ke database: {e}") 
        return None, None

# ----------------------------------------------------------------------
# --- ENDPOINT 1: DATA TERBARU (Live Data) ---
# ----------------------------------------------------------------------
@app.route('/api/v1/latest_data', methods=['GET'])
def get_latest_data():
    conn, cur = None, None
    try:
        conn, cur = get_db_connection()
        if not conn:
            return jsonify({"status": "error", "message": "Failed to connect to database"}), 500
        
        target_device = request.args.get('device_id') 
        
        where_clause = ""
        params = []
        if target_device:
            where_clause = "WHERE device_id = %s"
            params = [target_device] 
            
        sql = f"""
        SELECT 
            EXTRACT(EPOCH FROM timestamp_utc) AS timestamp, 
            temperature, 
            humidity, 
            device_id,
            is_anomaly
        FROM 
            sensor_readings
        {where_clause} 
        ORDER BY 
            id DESC -- ✅ PERBAIKAN: Prioritaskan ID sebagai penunjuk baris terbaru
        LIMIT 1;
        """
        cur.execute(sql, params) 
        record = cur.fetchone()

        if record:
            temp_float = float(record['temperature'])
            hum_float = float(record['humidity'])
            is_anomaly_value = record.get('is_anomaly') 
            
            return jsonify({
                "status": "success",
                "data": {
                    "timestamp": int(record['timestamp']), 
                    "temperature": temp_float,
                    "humidity": hum_float,
                    "device_id": record['device_id'],
                    "is_anomaly": is_anomaly_value
                }
            })
        else:
            return jsonify({"status": "error", "message": "No data found"}), 404

    except psycopg2.Error as e:
        print(f"Database Error: {e}")
        return jsonify({"status": "error", "message": "Database query failed"}), 500
    except Exception as e:
        print(f"General Error in latest_data: {e}")
        return jsonify({"status": "error", "message": "Server processing error"}), 500
    finally:
        if cur: cur.close()
        if conn: conn.close()

# ----------------------------------------------------------------------
# --- ENDPOINT 2: DATA HISTORIS (Untuk Grafik) ---
# ----------------------------------------------------------------------
@app.route('/api/v1/historical_data', methods=['GET'])
def get_historical_data():
    conn, cur = None, None
    try:
        conn, cur = get_db_connection()
        if not conn:
            return jsonify({"status": "error", "message": "Failed to connect to database"}), 500
            
        target_device = request.args.get('device_id')
        
        # Menggunakan 24 jam terakhir dari sekarang
        time_24_hours_ago = datetime.now(timezone.utc) - timedelta(hours=24) 
        
        params = [time_24_hours_ago]
        device_filter = ""

        if target_device:
            device_filter = "AND device_id = %s"
            params.append(target_device) 
        
        sql = f"""
        SELECT 
            EXTRACT(EPOCH FROM timestamp_utc) AS timestamp, 
            temperature, 
            humidity,
            is_anomaly
        FROM 
            sensor_readings
        WHERE 
            timestamp_utc >= %s 
            {device_filter} 
        ORDER BY 
            timestamp_utc ASC
        LIMIT 500; -- Batasan 500 baris tetap dipertahankan untuk menghindari timeout di emulator
        """
        cur.execute(sql, params)
        records = cur.fetchall()

        historical_data = []
        for record in records:
            historical_data.append({
                "timestamp": int(record['timestamp']), 
                "temperature": float(record['temperature']), 
                "humidity": float(record['humidity']),
                "is_anomaly": record.get('is_anomaly')
            })

        if historical_data:
            return jsonify({
                "status": "success",
                "data": historical_data
            })
        else:
            return jsonify({"status": "error", "message": "No historical data found"}), 404

    except psycopg2.Error as e:
        print(f"Database Error: {e}")
        return jsonify({"status": "error", "message": "Database query failed"}), 500
    except Exception as e:
        print(f"General Error in historical_data: {e}")
        return jsonify({"status": "error", "message": "Server processing error"}), 500
    finally:
        if cur: cur.close()
        if conn: conn.close()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
