from django.db import models

# =========================================================
# MODEL BARU: SensorLocation
# =========================================================
class SensorLocation(models.Model):
    location_name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Nama Lokasi/Sensor"
    )
    # Endpoint API publik (misal via ngrok) untuk menarik data real-time
    api_endpoint = models.URLField(
        max_length=500,
        verbose_name="API Endpoint",
        db_column='api_url',  # Kolom DB bernama 'api_url'
        help_text="Contoh: https://xxxxx.ngrok-free.app/api/v1/latest_data"
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="Deskripsi/Catatan"
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name="Aktif"
    )
    
    def __str__(self):
        return self.location_name
        
    class Meta:
        verbose_name = "Lokasi Sensor"
        verbose_name_plural = "Daftar Lokasi Sensor"


class SensorDevice(models.Model):
    """Optional model to register physical devices associated with a SensorLocation."""
    location = models.ForeignKey(SensorLocation, on_delete=models.CASCADE, related_name='devices')
    device_id = models.CharField(max_length=100, verbose_name='Device ID')
    name = models.CharField(max_length=150, blank=True, null=True, verbose_name='Nama Device')

    class Meta:
        unique_together = ('location', 'device_id')
        verbose_name = 'Device Sensor'
        verbose_name_plural = 'Perangkat Sensor'

    def __str__(self):
        return f"{self.device_id} ({self.name or self.location.location_name})"


# =========================================================
# MODIFIKASI: SensorData 
# =========================================================
class SensorData(models.Model):
    # Foreign Key ke Model SensorLocation yang baru
    location = models.ForeignKey(
        SensorLocation, 
        on_delete=models.CASCADE,
        verbose_name="Lokasi Sensor"
    )
    # Optional raw device identifier from payload (kept as separate field to avoid FK name clash)
    raw_device_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="Device ID")
    # Optional structured device model to register known devices per location
    # Use a different db_column name to avoid clash with the device_id CharField
    device = models.ForeignKey(
        'SensorDevice', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Device', db_column='device_obj_id')

    timestamp = models.DateTimeField(auto_now_add=True)
    temperature = models.DecimalField(max_digits=5, decimal_places=2)
    humidity = models.DecimalField(max_digits=5, decimal_places=2)
    is_anomaly = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.location.location_name} - {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"

    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Data Sensor"
        verbose_name_plural = "Data Sensor Historis"


class AnomalyAlert(models.Model):
    """
    Model terpisah untuk mencatat detail setiap kali anomali terdeteksi.
    """
    data_point = models.ForeignKey(
        SensorData, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="Titik Data Pemicu"
    )
    
    alert_time = models.DateTimeField(
        auto_now_add=True, 
        verbose_name="Waktu Deteksi"
    )
    
    anomaly_type = models.CharField(
        max_length=100, 
        verbose_name="Jenis Anomali"
    ) 

    recommendation = models.TextField(
        verbose_name="Rekomendasi Tindakan", 
        blank=True,
        help_text="Saran yang diberikan sistem kepada pengguna."
    )
    
    is_resolved = models.BooleanField(
        default=False,
        verbose_name="Sudah Diatasi"
    )

    notes = models.TextField(
        blank=True, 
        null=True, 
        verbose_name="Catatan Penanganan Operator"
    )

    class Meta:
        verbose_name = "Peringatan Anomali"
        verbose_name_plural = "Peringatan Anomali"
        ordering = ['-alert_time']

    def __str__(self):
        return f"ANOMALI: {self.anomaly_type} pada {self.alert_time.strftime('%Y-%m-%d %H:%M:%S')}"