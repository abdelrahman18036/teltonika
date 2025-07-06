"""
URL configuration for teltonika_db project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

def api_info(request):
    """API information endpoint"""
    return JsonResponse({
        'name': 'Teltonika Tracking API',
        'version': '1.0',
        'endpoints': {
            'devices': '/api/devices/',
            'telemetry': '/api/telemetry/',
            'events': '/api/events/',
            'stats': '/api/stats/',
            'telemetry_by_imei': '/api/telemetry/by_imei/?imei=DEVICE_IMEI',
            'live_tracking': '/api/telemetry/live_tracking/',
            'admin': '/admin/',
        }
    })

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', api_info),
    path('', include('tracking.urls')),
]
