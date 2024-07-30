from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings
from home import views

urlpatterns = [
    path('', views.home, name='home'),
    path('admin/', admin.site.urls),
    path('cliente/', include('clients.urls')),
    path('reserva/', include('reservations.urls')),
    path('agendar/', include('schedules.urls')),
    path('pagamento/', include('payments.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
