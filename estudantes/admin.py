from django.contrib import admin

from usuarios.permissions import escopo_estudantes

from .models import Estudante


@admin.register(Estudante)
class EstudanteAdmin(admin.ModelAdmin):
    list_display = ["nome", "escola", "ano_turma", "territorio_esf", "cpf_mascarado_admin"]
    list_filter = ["escola", "territorio_esf"]
    search_fields = ["nome", "nome_responsavel"]
    readonly_fields = ["data_registro", "cpf_hash"]

    @admin.display(description="CPF")
    def cpf_mascarado_admin(self, obj):
        return obj.cpf_mascarado

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return escopo_estudantes(request.user, qs)
