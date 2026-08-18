from django.db import models


class TipoAtendimento(models.Model):
    """Serviço/especialidade para o qual o estudante é encaminhado
    (ex.: Psicologia, Nutrição, Fonoaudiologia). Cadastro fechado, como
    Escola e Território/ESF, para manter os relatórios e filtros
    padronizados em toda a Rede Municipal."""

    nome = models.CharField(max_length=150, unique=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "Tipo de Atendimento"
        verbose_name_plural = "Tipos de Atendimento"

    def __str__(self):
        return self.nome
