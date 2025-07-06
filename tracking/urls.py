from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'devices', views.DeviceViewSet)
router.register(r'telemetry', views.TelemetryDataViewSet)
router.register(r'events', views.DeviceEventViewSet)
router.register(r'stats', views.SystemStatsViewSet)

app_name = 'tracking'

urlpatterns = [
    path('api/', include(router.urls)),
] 