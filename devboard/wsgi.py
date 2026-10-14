"""
WSGI config for devboard project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'devboard.settings')

# One-time boot initialization for Render (the free plan has no shell):
# run migrations and seed demo data before the app starts serving.
# Guarded by a timeout + catch-all so a seed failure can never silently
# hang or kill the deploy - the traceback is printed to the Render
# runtime log instead, and the app keeps booting.
if os.environ.get('RENDER'):
    import signal
    import traceback

    import django
    from django.core.management import call_command

    class _BootTimeout(Exception):
        pass

    def _on_alarm(signum, frame):
        raise _BootTimeout('boot hook exceeded 180s')

    django.setup()
    signal.signal(signal.SIGALRM, _on_alarm)
    signal.alarm(180)
    try:
        call_command('migrate', verbosity=0)
        if os.environ.get('SEED_DEMO', '1') == '1':
            call_command('seed_demo')
    except Exception:
        traceback.print_exc()
    finally:
        signal.alarm(0)

application = get_wsgi_application()