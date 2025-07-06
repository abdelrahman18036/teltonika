"""
URL configuration for teltonika_tracker project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
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

def api_root(request):
    """Root API endpoint"""
    return JsonResponse({
        'message': 'Teltonika GPS Tracker API',
        'version': '1.0',
        'endpoints': {
            'devices': '/api/devices/',
            'gps_records': '/api/gps-records/',
            'events': '/api/events/',
            'io_parameters': '/api/io-parameters/',
            'statistics': '/api/statistics/',
            'live_status': '/api/devices/live-status/',
            'create_gps': '/api/gps/create/',
            'bulk_create_gps': '/api/gps/bulk-create/',
        }
    })

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', api_root, name='api-root'),
    path('', include('gps_tracking.urls')),
    path('api-auth/', include('rest_framework.urls')),
]
