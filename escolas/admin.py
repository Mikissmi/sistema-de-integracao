from django.contrib import admin

from .models import Escola


@admin.register(Escola)
class EscolaAdmin(admin.ModelAdmin):
    list_display = ["nome", "tipo", "ativo"]
    list_filter = ["tipo", "ativo"]
    search_fields = ["nome"]
