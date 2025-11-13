from django.apps import AppConfig
from django.conf import settings
import os
import logging


class SafeWebConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'SAFE_WEB'

    def ready(self):
        # Start an in-process background fetcher if enabled in settings.
        if not getattr(settings, 'SAFE_FETCHER_LIVE', False):
            return

        # Avoid starting in the autoreloader parent process. Only start when
        # RUN_MAIN is not set or is 'true' (Django's autoreloader sets RUN_MAIN='true')
        run_main = os.environ.get('RUN_MAIN')
        if run_main is not None and run_main.lower() not in ('true', '1'):
            return

        logger = logging.getLogger(__name__)
        try:
            from .services.fetcher import start_background_fetcher
            interval = int(getattr(settings, 'SAFE_FETCHER_INTERVAL', 10))
            start_background_fetcher(interval=interval)
            logger.info('SAFE_WEB: background fetcher requested at startup (interval=%s)', interval)
        except Exception:
            logger.exception('SAFE_WEB: failed to start background fetcher')
