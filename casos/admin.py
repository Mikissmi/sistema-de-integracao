from django.contrib import admin

from usuarios.permissions import escopo_casos

from .models import Caso, Evolucao


class EvolucaoInline(admin.TabularInline):
    model = Evolucao
    extra = 1
    fields = [
        "data_movimentacao",
        "servico_responsavel",
        "profissional_responsavel",
        "acao_realizada",
        "encaminhamento_efetuado",
        "retorno_recebido",
        "observacoes",
    ]


@admin.register(Caso)
class CasoAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "estudante",
        "servico_encaminhado",
        "situacao",
        "gravidade",
        "dias_sem_retorno",
        "nivel_alerta_admin",
    ]
    list_filter = ["situacao", "gravidade", "servico_encaminhado", "estudante__escola"]
    search_fields = ["estudante__nome"]
    date_hierarchy = "data_encaminhamento"
    inlines = [EvolucaoInline]

    @admin.display(description="Alerta")
    def nivel_alerta_admin(self, obj):
        return obj.nivel_alerta

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return escopo_casos(request.user, qs)
