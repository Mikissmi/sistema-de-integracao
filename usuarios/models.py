from django.conf import settings
from django.db import models

from escolas.models import Escola
from territorios.models import Territorio


class PerfilUsuario(models.Model):
    class Perfil(models.TextChoices):
        EDUCACAO = "educacao", "Educação"
        SAUDE = "saude", "Saúde"
        GESTAO = "gestao", "Gestão Municipal"

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="perfil"
    )
    perfil = models.CharField(max_length=10, choices=Perfil.choices)
    escola = models.ForeignKey(
        Escola,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Obrigatório para perfil Educação.",
    )
    territorio_esf = models.ForeignKey(
        Territorio,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text=(
            "Território/ESF de referência (perfil Saúde). "
            "Deixe em branco se este profissional acompanha todas as escolas/territórios."
        ),
    )

    class Meta:
        verbose_name = "Perfil de Usuário"
        verbose_name_plural = "Perfis de Usuário"

    def __str__(self):
        return f"{self.usuario.get_username()} ({self.get_perfil_display()})"


class LogAuditoria(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    data_hora = models.DateTimeField(auto_now_add=True)
    acao = models.CharField(max_length=100)
    objeto = models.CharField(max_length=200)

    class Meta:
        verbose_name = "Log de Auditoria"
        verbose_name_plural = "Logs de Auditoria"
        ordering = ["-data_hora"]
        indexes = [models.Index(fields=["usuario", "-data_hora"])]

    def __str__(self):
        return f"{self.data_hora:%d/%m/%Y %H:%M} - {self.usuario} - {self.acao}"
