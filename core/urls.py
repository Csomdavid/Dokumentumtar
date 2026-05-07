from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Admin felület útvonala
    path('admin/', admin.site.urls),
    
    # A Django beépített, biztonságos bejelentkezési/kijelentkezési útvonalai
    path('accounts/', include('django.contrib.auth.urls')),
    
    # A dokumentumtár útvonalainak becsatolása a gyökérkönyvtárba
    path('', include('dokumentumtar.urls')),
]
