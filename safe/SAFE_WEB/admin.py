from django.contrib import admin
from .models import SensorData, AnomalyAlert, SensorLocation

admin.site.register(SensorLocation)

# --- Konfigurasi Admin untuk SensorData ---
@admin.register(SensorData)
class SensorDataAdmin(admin.ModelAdmin):
    # Kolom yang akan ditampilkan di daftar Admin
    list_display = ('timestamp', 'temperature', 'humidity', 'is_anomaly')
    # Filter samping
    list_filter = ('is_anomaly', 'timestamp')
    # Kolom untuk pencarian
    search_fields = ('timestamp', 'temperature')
    # Memastikan kolom timestamp selalu menampilkan data terbaru di atas
    ordering = ('-timestamp',)
    # Menambahkan read-only field untuk data yang otomatis terisi
    readonly_fields = ('timestamp', 'is_anomaly',)


# --- Konfigurasi Admin untuk AnomalyAlert ---
@admin.register(AnomalyAlert)
class AnomalyAlertAdmin(admin.ModelAdmin):
    list_display = ('alert_time', 'anomaly_type', 'is_resolved')
    list_filter = ('is_resolved', 'anomaly_type', 'alert_time')
    search_fields = ('anomaly_type', 'recommendation')
    ordering = ('-alert_time',)
    # Menambahkan tombol aksi untuk menandai alert sudah diatasi
    actions = ['mark_resolved']

    def mark_resolved(self, request, queryset):
        queryset.update(is_resolved=True)
    mark_resolved.short_description = "Tandai terpilih sebagai Sudah Diatasi"