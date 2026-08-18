from django.contrib import admin

from .models import Territorio


@admin.register(Territorio)
class TerritorioAdmin(admin.ModelAdmin):
    list_display = ["nome", "ativo"]
    list_filter = ["ativo"]
    search_fields = ["nome"]
