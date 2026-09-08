from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("entrar/", views.LoginView.as_view(), name="login"),
    path("sair/", views.LogoutView.as_view(), name="logout"),
    path("pins/", views.PinManagementView.as_view(), name="pin_management"),
    path("pins/<int:pk>/gerar/", views.GeneratePinView.as_view(), name="generate_pin"),
]
