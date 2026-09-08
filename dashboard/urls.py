from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.DashboardHomeView.as_view(), name="home"),
    path("historico/", views.HistoryView.as_view(), name="history"),
    path("pets/<int:pk>/evacuar/", views.TriggerEvacuationView.as_view(), name="trigger_evacuation"),
    path("alerta/acionar/", views.TriggerGeneralAlertView.as_view(), name="trigger_general_alert"),
    path("alerta/status/", views.ActiveAlertStatusView.as_view(), name="alert_status"),
    path("evacuacoes/<int:pk>/silenciar/", views.SilenceSirenView.as_view(), name="silence_siren"),
    path("evacuacoes/<int:pk>/encerrar/", views.EndEvacuationView.as_view(), name="end_evacuation"),
]
