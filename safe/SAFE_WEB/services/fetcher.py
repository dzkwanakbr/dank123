import threading
import time
import logging
import requests
import json
from SAFE_WEB.models import SensorLocation, SensorData

logger = logging.getLogger(__name__)

_fetcher_thread = None
_fetcher_stop_event = None


def fetch_once():
    """Fetch sensor data once for all active SensorLocation entries."""
    # Hanya ambil data dari lokasi yang statusnya AKTIF
    active_locations = SensorLocation.objects.filter(is_active=True)
    inactive_locations = SensorLocation.objects.filter(is_active=False)
    
    # Log lokasi yang di-skip
    if inactive_locations.exists():
        inactive_names = ', '.join([loc.location_name for loc in inactive_locations])
        logger.info('Skipping INACTIVE locations: %s', inactive_names)
    
    if not active_locations.exists():
        logger.debug('No active SensorLocation found for fetch.')
        return
    
    locations = active_locations

    for location in locations:
        # Menggunakan atribut api_endpoint dari model
        url = getattr(location, 'api_endpoint', None)
        if not url:
            logger.warning('Location %s has no api_endpoint; skipping.', getattr(location, 'location_name', str(location.id)))
            continue

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            payload = response.json()
        except requests.exceptions.RequestException as e:
            logger.error('[%s] Failed to fetch %s: %s', getattr(location, 'location_name', location.id), url, e)
            continue
        except json.JSONDecodeError:
            logger.error('[%s] Response from %s is not valid JSON', getattr(location, 'location_name', location.id), url)
            continue

        data = payload.get('data') or payload
        temperature = data.get('temperature') if isinstance(data, dict) else None
        humidity = data.get('humidity') if isinstance(data, dict) else None
        device_id = data.get('device_id') if isinstance(data, dict) else None
        is_anomaly = data.get('is_anomaly') if isinstance(data, dict) else False

        if temperature is None or humidity is None:
            logger.warning('[%s] temperature/humidity not found in payload: %s', getattr(location, 'location_name', location.id), payload)
            continue

        try:
            device_obj = None
            if device_id:
                from SAFE_WEB.models import SensorDevice
                device_obj, _ = SensorDevice.objects.get_or_create(location=location, device_id=device_id)

            SensorData.objects.create(
                location=location,
                raw_device_id=device_id,
                device=device_obj,
                temperature=temperature,
                humidity=humidity,
                is_anomaly=bool(is_anomaly),
            )
            logger.info('[%s] Saved device=%s temperature=%s humidity=%s anomaly=%s', getattr(location, 'location_name', location.id), device_id, temperature, humidity, bool(is_anomaly))
        except Exception:
            logger.exception('[%s] Failed to save fetched sensor data to DB', getattr(location, 'location_name', location.id))


def run_loop(interval=10, stop_event=None):
    if stop_event is None:
        stop_event = threading.Event()

    logger.info('Starting fetcher loop (interval=%s)', interval)
    try:
        while not stop_event.is_set():
            fetch_once()
            stop_event.wait(interval)
    except Exception:
        logger.exception('Unhandled exception in fetcher loop')
    finally:
        logger.info('Fetcher loop exiting')


def start_background_fetcher(interval=10):
    """Start the fetch loop in a daemon thread and return (thread, stop_event)."""
    global _fetcher_thread, _fetcher_stop_event
    stop_event = threading.Event()
    t = threading.Thread(target=run_loop, args=(interval, stop_event), daemon=True, name='safe-fetcher')
    t.start()
    _fetcher_thread = t
    _fetcher_stop_event = stop_event
    logger.info('Background fetcher thread started: %s', t.name)
    return t, stop_event


def is_running():
    """Return True if a background fetcher thread was started and is alive."""
    t = globals().get('_fetcher_thread')
    return t is not None and t.is_alive()