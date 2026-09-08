from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.HomeRedirectView.as_view(), name="home"),
    path("empresas/", views.OrganizationListView.as_view(), name="organization_list"),
    path("empresas/nova/", views.OrganizationCreateView.as_view(), name="organization_create"),
]
