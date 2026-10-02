
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('accounts/', include('django.contrib.auth.urls')),
    path('', include('payments.urls')),
    path('admin/', admin.site.urls),
]
