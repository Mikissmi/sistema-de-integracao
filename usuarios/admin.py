from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from .models import LogAuditoria, PerfilUsuario


class PerfilUsuarioInline(admin.StackedInline):
    model = PerfilUsuario
    can_delete = False


class CustomUserAdmin(UserAdmin):
    inlines = [PerfilUsuarioInline]
    list_display = ["username", "first_name", "last_name", "is_active", "get_perfil"]

    @admin.display(description="Perfil")
    def get_perfil(self, obj):
        return getattr(obj, "perfil", None)


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@admin.register(LogAuditoria)
class LogAuditoriaAdmin(admin.ModelAdmin):
    list_display = ["data_hora", "usuario", "acao", "objeto"]
    list_filter = ["acao"]
    search_fields = ["objeto", "usuario__username"]
    readonly_fields = [f.name for f in LogAuditoria._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
