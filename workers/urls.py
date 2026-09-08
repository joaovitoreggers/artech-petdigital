from django.urls import path

from . import views

app_name = "workers"

urlpatterns = [
    path("", views.WorkerListView.as_view(), name="list"),
    path("novo/", views.WorkerCreateView.as_view(), name="create"),
    path(
        "documentos/extrair-validade/",
        views.DocumentValidityExtractView.as_view(),
        name="extract_document_validity",
    ),
    path("<int:pk>/cracha/", views.WorkerBadgeView.as_view(), name="badge"),
    path("<int:pk>/cracha/qrcode.png", views.WorkerBadgeQRView.as_view(), name="badge_qr"),
]
