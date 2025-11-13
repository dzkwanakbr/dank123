from django.views.generic import CreateView, ListView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy
from .models import SensorData, AnomalyAlert, SensorLocation
from .forms import SensorLocationForm, AnomalyAlertForm 
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404 
from django.db.models import Count
from django.http import JsonResponse
from django.http import HttpResponse
import csv
import json

# lightweight status endpoint for background fetcher
def fetcher_status(request):
    try:
        from .services.fetcher import is_running
        running = is_running()
    except Exception:
        running = False
    return JsonResponse({'fetcher_running': running})


def location_data_json(request, location_id):
    """Return latest sensor readings for a location as JSON. Optional ?device_id=xxx"""
    device = request.GET.get('device_id')
    qs = SensorData.objects.filter(location_id=location_id).order_by('-timestamp')
    if device:
        qs = qs.filter(raw_device_id=device)
    # Support ?limit=N to control how many rows to return, and ?all=1 to return everything.
    # Default limit is 1000 to keep payloads reasonable while allowing >100 items.
    export_all = request.GET.get('all') == '1'
    if export_all:
        latest = qs
    else:
        try:
            limit = int(request.GET.get('limit')) if request.GET.get('limit') else 1000
            if limit < 0:
                limit = 1000
        except (TypeError, ValueError):
            limit = 1000
        latest = qs[:limit]
    # compute totals on the matching queryset (not just the sliced latest)
    total_anomaly = qs.filter(is_anomaly=True).count()
    total_normal = qs.filter(is_anomaly=False).count()
    total_count = qs.count()

    data = [
        {
            'id': r.id,
            'timestamp': r.timestamp.isoformat(),
            'device_id': r.raw_device_id,
            'temperature': float(r.temperature),
            'humidity': float(r.humidity),
            'is_anomaly': bool(r.is_anomaly),
        }
        for r in latest
    ]
    return JsonResponse({
        'location_id': location_id,
        'count': len(data),
        'data': data,
        'total_anomaly_count': total_anomaly,
        'total_normal_count': total_normal,
        'total_count': total_count,
    })


def export_location_csv(request, location_id):
    """Export sensor readings for a location as CSV. Optional ?device_id=... & ?all=1"""
    device = request.GET.get('device_id')
    export_all = request.GET.get('all') == '1'
    qs = SensorData.objects.filter(location_id=location_id).order_by('-timestamp')
    if device:
        qs = qs.filter(raw_device_id=device)
    # Support ?limit=N for export size and ?all=1 for everything
    if not export_all:
        try:
            limit = int(request.GET.get('limit')) if request.GET.get('limit') else 1000
            if limit < 0:
                limit = 1000
        except (TypeError, ValueError):
            limit = 1000
        qs = qs[:limit]

    filename = f'location_{location_id}_data.csv'
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(['id','timestamp','device_id','temperature','humidity','is_anomaly','location'])
    for r in qs:
        writer.writerow([r.id, r.timestamp.isoformat(), r.raw_device_id or '', float(r.temperature), float(r.humidity), int(bool(r.is_anomaly)), r.location.location_name])
    return response


def all_data_json(request):
    """Return latest sensor readings across all locations/devices. Optional ?limit=N or ?all=1"""
    device = request.GET.get('device_id')
    qs = SensorData.objects.all().order_by('-timestamp')
    if device:
        qs = qs.filter(raw_device_id=device)
    export_all = request.GET.get('all') == '1'
    if not export_all:
        try:
            limit = int(request.GET.get('limit')) if request.GET.get('limit') else 1000
            if limit < 0:
                limit = 1000
        except (TypeError, ValueError):
            limit = 1000
        qs = qs[:limit]

    total_anomaly = SensorData.objects.filter(is_anomaly=True).count()
    total_normal = SensorData.objects.filter(is_anomaly=False).count()

    data = [
        {
            'id': r.id,
            'timestamp': r.timestamp.isoformat(),
            'device_id': r.raw_device_id,
            'temperature': float(r.temperature),
            'humidity': float(r.humidity),
            'is_anomaly': bool(r.is_anomaly),
            'location_name': r.location.location_name if r.location else ''
        }
        for r in qs
    ]
    return JsonResponse({ 'count': len(data), 'data': data, 'total_anomaly_count': total_anomaly, 'total_normal_count': total_normal })


class SensorLocationListView(LoginRequiredMixin, ListView):
    model = SensorLocation
    template_name = 'SAFE_WEB/location_list.html' 
    context_object_name = 'locations'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['location_form'] = SensorLocationForm()
        context['total_locations'] = self.get_queryset().count() 
        return context

class SensorLocationCreateView(LoginRequiredMixin, CreateView):
    model = SensorLocation
    form_class = SensorLocationForm
    template_name = 'SAFE_WEB/location_list.html' 
    success_url = reverse_lazy('location_list')

    def form_valid(self, form):
        # Simpan lokasi dulu
        response = super().form_valid(form)
        
        # Ambil initial_device_id dari POST data
        initial_device_id = self.request.POST.get('initial_device_id')
        if initial_device_id:
            from .models import SensorDevice
            # get_or_create akan membuat baru atau ambil yang sudah ada (tidak error jika sudah ada)
            SensorDevice.objects.get_or_create(
                location=self.object, 
                device_id=initial_device_id
            )
        
        return response


class SensorDataListView(LoginRequiredMixin, ListView):
    model = SensorData
    template_name = 'SAFE_WEB/location_detail.html'
    context_object_name = 'sensor_readings'
    paginate_by = 10  # show 10 readings per page

    def get_queryset(self):
        location_id = self.kwargs.get('location_id')
        device = self.request.GET.get('device_id')
        qs = SensorData.objects.filter(location_id=location_id).order_by('-timestamp')
        if device:
            qs = qs.filter(raw_device_id=device)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        location_id = self.kwargs.get('location_id')
        current_location = get_object_or_404(SensorLocation, id=location_id)
        context['current_location'] = current_location
        
        context['alerts'] = AnomalyAlert.objects.filter(
            data_point__location__id=location_id 
        ).order_by('-alert_time') 
        context['location_form'] = SensorLocationForm() 
        # Statistik sederhana - use the unsliced queryset to avoid "slice then filter" errors
        full_qs = self.get_queryset().order_by('-timestamp')
        
        # PERBAIKAN: Hitung anomaly/normal dari SEMUA data (bukan hanya 50)
        context['anomaly_count'] = full_qs.filter(is_anomaly=True).count()
        context['normal_count'] = full_qs.filter(is_anomaly=False).count()
        
        # Data untuk grafik (labels, suhu, kelembaban) - ambil 30 terakhir untuk chart (default)
        # We want the last 30 points in chronological order
        last30 = list(full_qs[:30])[::-1]
        context['chart_labels'] = [r.timestamp.strftime('%H:%M:%S') for r in last30]
        context['chart_temps'] = [float(r.temperature) for r in last30]
        context['chart_humids'] = [float(r.humidity) for r in last30]
        # Provide JSON-serialized strings so templates can safely read them without json_script
        context['chart_labels_json'] = json.dumps(context['chart_labels'])
        context['chart_temps_json'] = json.dumps(context['chart_temps'])
        context['chart_humids_json'] = json.dumps(context['chart_humids'])
        context['anomaly_count_json'] = json.dumps(context['anomaly_count'])
        context['normal_count_json'] = json.dumps(context['normal_count'])
        context['current_location_id_json'] = json.dumps(current_location.id)
        return context

class AnomalyAlertUpdateView(LoginRequiredMixin, UpdateView):
    model = AnomalyAlert
    form_class = AnomalyAlertForm
    template_name = 'SAFE_WEB/anomalyalert_update.html'
    success_url = reverse_lazy('location_list') 
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class SensorLocationUpdateView(LoginRequiredMixin, UpdateView):
    model = SensorLocation
    form_class = SensorLocationForm
    # KOREKSI INI: Ganti ke nama template yang ADA
    template_name = 'SAFE_WEB/anomalyalert_update.html' 
    success_url = reverse_lazy('location_list')


class SensorLocationDeleteView(LoginRequiredMixin, DeleteView):
    model = SensorLocation
    template_name = 'SAFE_WEB/location_confirm_delete.html' # Buat template ini di Langkah 3
    context_object_name = 'location'
    # Arahkan kembali ke daftar lokasi setelah berhasil
    success_url = reverse_lazy('location_list')