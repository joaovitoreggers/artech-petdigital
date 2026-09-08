from django.urls import path

from . import views

app_name = "permits"

urlpatterns = [
    path("", views.PermitHomeView.as_view(), name="home"),
    path("nova/", views.PermitCreateView.as_view(), name="create"),
    path("<int:pk>/", views.PermitDetailView.as_view(), name="detail"),
    path("<int:pk>/emitida/", views.PermitIssuedView.as_view(), name="issued"),
    path("<int:pk>/encerrar/", views.PermitCloseView.as_view(), name="close"),
    path("<int:pk>/passo/area/", views.WizardAreaView.as_view(), name="wizard_area"),
    path("<int:pk>/passo/atividade/", views.WizardActivityView.as_view(), name="wizard_activity"),
    path("<int:pk>/passo/gases/", views.WizardGasView.as_view(), name="wizard_gas"),
    path("<int:pk>/passo/equipe/", views.WizardTeamView.as_view(), name="wizard_team"),
    path("<int:pk>/passo/equipe/ler-cracha/", views.WizardTeamScanView.as_view(), name="wizard_team_scan"),
    path("<int:pk>/passo/epi/", views.WizardPPEView.as_view(), name="wizard_ppe"),
    path("<int:pk>/passo/checklist/", views.WizardChecklistView.as_view(), name="wizard_checklist"),
    path("<int:pk>/passo/assinaturas/", views.WizardSignaturesView.as_view(), name="wizard_signatures"),
    path("aprovacoes/", views.ApprovalQueueView.as_view(), name="approval_queue"),
    path("<int:pk>/aprovar/", views.ApprovePermitView.as_view(), name="approve"),
    path("<int:pk>/rejeitar/", views.RejectPermitView.as_view(), name="reject"),
]
