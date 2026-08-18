from django.contrib import admin

from .models import TipoAtendimento


@admin.register(TipoAtendimento)
class TipoAtendimentoAdmin(admin.ModelAdmin):
    list_display = ["nome", "ativo"]
    list_filter = ["ativo"]
    search_fields = ["nome"]
