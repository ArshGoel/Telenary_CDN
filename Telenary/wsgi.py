import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Telenary.settings')

application = get_wsgi_application()

# Auto-migrate database tables on deployment cold-start (Vercel / Cloud)
try:
    from django.core.management import call_command
    call_command('migrate', interactive=False)
except Exception as e:
    print("Auto-migration notice:", e)

app = application