from django.urls import path

from . import views

urlpatterns = [
    path("topup/", views.topup, name="topup"),
    path("click/webhook/", views.click_webhook, name="click_webhook"),
]
