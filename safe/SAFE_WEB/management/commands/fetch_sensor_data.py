# SAFE_WEB/management/commands/fetch_sensor_data.py

from django.core.management.base import BaseCommand
from SAFE_WEB.models import SensorLocation, SensorData, AnomalyAlert
from django.utils import timezone
import requests
import json  
import time

class Command(BaseCommand):
    help = 'Mengambil data sensor terbaru dari API endpoint milik setiap lokasi dan menyimpannya ke database lokal.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--loop', action='store_true', default=False,
            help='Jalankan perulangan terus-menerus.'
        )
        parser.add_argument(
            '--interval', type=int, default=10,
            help='Jeda detik antar pengambilan data saat loop (default: 10 detik).'
        )
        parser.add_argument(
            '--max-runs', type=int, default=0,
            help='Batas jumlah iterasi saat loop untuk pengujian (0 = tanpa batas).'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Memulai proses pengambilan data sensor...'))

        def fetch_once():
            # Ambil semua lokasi aktif dan fetch endpoint-nya masing-masing
            locations = SensorLocation.objects.filter(is_active=True)
            if not locations.exists():
                self.stdout.write(self.style.WARNING('Tidak ada lokasi aktif untuk diambil datanya.'))
                return

            for location in locations:
                url = getattr(location, 'api_endpoint', None)
                if not url:
                    self.stdout.write(self.style.WARNING(f'Lokasi {location.location_name} tidak memiliki API Endpoint. Lewati.'))
                    continue

                try:
                    response = requests.get(url, timeout=10)
                    response.raise_for_status()
                    payload = response.json()
                except requests.exceptions.RequestException as e:
                    self.stdout.write(self.style.ERROR(f'[{location.location_name}] Gagal fetch {url}: {e}'))
                    continue
                except json.JSONDecodeError:
                    self.stdout.write(self.style.ERROR(f'[{location.location_name}] Response bukan JSON valid dari {url}'))
                    continue

                # Expected structure:
                # { "data": {"device_id": "sensor_002", "humidity": 71.0, "temperature": 29.1, "timestamp": 2086003755}, "status": "success" }
                data = payload.get('data') or payload
                temperature = data.get('temperature') if isinstance(data, dict) else None
                humidity = data.get('humidity') if isinstance(data, dict) else None
                # ts = data.get('timestamp') if isinstance(data, dict) else None  # optional future use

                if temperature is None or humidity is None:
                    self.stdout.write(self.style.WARNING(f'[{location.location_name}] Field temperature/humidity tidak ditemukan pada payload: {payload}'))
                    continue

                try:
                    SensorData.objects.create(
                        location=location,
                        temperature=temperature,
                        humidity=humidity,
                    )
                    self.stdout.write(self.style.SUCCESS(f'[{location.location_name}] Simpan data suhu={temperature}, humidity={humidity}'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'[{location.location_name}] Gagal simpan ke DB: {e}'))

        # Looping mode support
        loop = getattr(self, 'options', None) and options.get('loop') if False else None
        # NOTE: Django passes options to handle; use the provided options argument

        # Use the options passed into handle
        loop = options.get('loop', False)
        interval = max(1, int(options.get('interval', 10)))
        max_runs = int(options.get('max_runs', 0))

        if loop:
            runs = 0
            self.stdout.write(self.style.SUCCESS(f'Mulai loop fetch setiap {interval} detik. Tekan Ctrl+C untuk berhenti.'))
            try:
                while True:
                    fetch_once()
                    runs += 1
                    if max_runs > 0 and runs >= max_runs:
                        self.stdout.write(self.style.SUCCESS(f'Loop selesai setelah {runs} iterasi.'))
                        break
                    time.sleep(interval)
            except KeyboardInterrupt:
                self.stdout.write(self.style.WARNING('Dihentikan oleh pengguna.'))
        else:
            fetch_once()
            self.stdout.write(self.style.SUCCESS('Proses pengambilan data selesai.'))