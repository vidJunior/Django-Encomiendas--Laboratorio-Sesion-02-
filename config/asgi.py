import os
import django
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Importar DESPUES de django.setup() para evitar errores de inicializacion
from envios.routing import websocket_urlpatterns
from config.channels_middleware import JWTAuthMiddlewareStack

application = ProtocolTypeRouter({
    # Peticiones HTTP normales: Django las maneja igual que antes
    'http': get_asgi_application(),
    # Conexiones WebSocket: las maneja Channels
    'websocket': AllowedHostsOriginValidator(
        # JWTAuthMiddlewareStack: permite autenticacion via Cookies (Django) 
        # o via Token JWT (en el query string ?token=...)
        JWTAuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        )
    ),
})
