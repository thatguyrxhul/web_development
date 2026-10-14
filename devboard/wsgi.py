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
if os.environ.get('RENDER'):
    import django
    from django.core.management import call_command

    django.setup()
    call_command('migrate', verbosity=0)
    if os.environ.get('SEED_DEMO', '1') == '1':
        call_command('seed_demo')

application = get_wsgi_application()