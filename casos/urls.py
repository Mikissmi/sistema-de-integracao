from django.urls import path

from . import views

app_name = "casos"

urlpatterns = [
    path("", views.lista, name="lista"),
    path("exportar/", views.exportar_csv, name="exportar_csv"),
    path("novo/<int:estudante_id>/", views.novo, name="novo"),
    path("<int:pk>/", views.detalhe, name="detalhe"),
    path("<int:pk>/situacao/", views.atualizar_situacao, name="atualizar_situacao"),
]
