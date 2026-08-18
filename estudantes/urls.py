from django.urls import path

from . import views

app_name = "estudantes"

urlpatterns = [
    path("buscar/", views.buscar, name="buscar"),
    path("novo/", views.novo, name="novo"),
    path("lista/", views.lista, name="lista"),
    path("importar/", views.importar_csv, name="importar_csv"),
    path("importar/modelo.csv", views.modelo_csv, name="modelo_csv"),
    path("<int:pk>/", views.detalhe, name="detalhe"),
]
