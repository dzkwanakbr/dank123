from django import forms
from .models import SensorData, AnomalyAlert, SensorLocation
from django.core.exceptions import ValidationError

# =========================================================
# 1. FORM SensorLocation (BARU)
# =========================================================
class SensorLocationForm(forms.ModelForm):
    """
    Formulir untuk mendaftarkan Lokasi Sensor Baru dan API Bling.
    """
    # Field tambahan untuk device_id (tidak ada di model, tapi digunakan untuk create/update device)
    initial_device_id = forms.CharField(
        required=False, 
        max_length=100, 
        label='Device ID (opsional)',
        help_text='Isi jika ingin langsung mendaftarkan device awal untuk lokasi ini.'
    )
    
    class Meta:
        model = SensorLocation
        fields = ['location_name', 'api_endpoint', 'is_active', 'description']
        labels = {
            'location_name': 'Nama Lokasi',
            'api_endpoint': 'Masukkan Endpoint Perangkat',
            'is_active': 'Status',
            'description': 'Deskripsi',
        }
        help_texts = {
            'location_name': 'Contoh: Kamar Dzakwan, Ruang Server',
            'api_endpoint': 'Endpoint akan divalidasi otomatis oleh sistem',
            'description': 'Opsional: Informasi tambahan tentang lokasi ini',
        }
        widgets = {
            'description': forms.HiddenInput(),  # Hide deskripsi di form edit
        }
    
    def clean_api_endpoint(self):
        """Validasi format URL saja (tidak test koneksi untuk menghindari timeout)"""
        endpoint = self.cleaned_data.get('api_endpoint')
        
        if not endpoint:
            return endpoint
        
        # Validasi format URL
        if not endpoint.startswith(('http://', 'https://')):
            raise ValidationError('❌ Endpoint harus dimulai dengan http:// atau https://')
        
        # URL format valid, biarkan background fetcher yang test koneksi
        return endpoint

# =========================================================
# 2. FORM AnomalyAlert (WAJIB ADA UNTUK VIEWS.PY)
# Kita membutuhkannya untuk fitur Update Alert!
# =========================================================
class AnomalyAlertForm(forms.ModelForm):
    """
    Formulir untuk mengubah status Anomaly Alert.
    """
    class Meta:
        model = AnomalyAlert
        fields = ['is_resolved', 'notes'] 
        
        labels = {
            'is_resolved': 'Tandai sudah diatasi?',
            'notes': 'Catatan Penanganan',
        }