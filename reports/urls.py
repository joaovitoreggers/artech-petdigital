from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("novo/", views.PeriodReportCreateView.as_view(), name="create"),
]
