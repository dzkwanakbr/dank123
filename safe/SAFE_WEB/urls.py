from django.urls import path
from . import views
from .views import (
    SensorDataListView, 
    AnomalyAlertUpdateView, 
    SensorLocationCreateView,
    SensorLocationListView 
)

urlpatterns = [
    path('', SensorLocationListView.as_view(), name='location_list'), 
    path('location/register/', SensorLocationCreateView.as_view(), name='location_register'),
    path('location/<int:location_id>/detail/', SensorDataListView.as_view(), name='location_detail'), 
    path('alert/<int:pk>/update/', AnomalyAlertUpdateView.as_view(), name='alert_update'),
    path('location/<int:pk>/edit/', views.SensorLocationUpdateView.as_view(), name='location_update'),
    path('location/<int:pk>/delete/', views.SensorLocationDeleteView.as_view(), name='location_delete'),
    path('fetcher/status/', views.fetcher_status, name='fetcher_status'),
    path('location/<int:location_id>/data.json', views.location_data_json, name='location_data_json'),
    path('location/<int:location_id>/export.csv', views.export_location_csv, name='export_location_csv'),
    path('data/all.json', views.all_data_json, name='all_data_json'),
]