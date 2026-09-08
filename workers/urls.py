from django.urls import path

from . import views

app_name = "workers"

urlpatterns = [
    path("", views.WorkerListView.as_view(), name="list"),
    path("novo/", views.WorkerCreateView.as_view(), name="create"),
    path("<int:pk>/cracha/", views.WorkerBadgeView.as_view(), name="badge"),
]
