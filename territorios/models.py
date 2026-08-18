from django.db import models


class Territorio(models.Model):
    """Território/ESF (Estratégia de Saúde da Família) de referência.

    Cadastro fechado (e não texto livre) para que o nome usado no perfil do
    profissional de Saúde seja sempre idêntico ao usado no cadastro do
    estudante — do contrário o escopo de permissões por território falharia
    silenciosamente por causa de pequenas diferenças de grafia.
    """

    nome = models.CharField(max_length=150, unique=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "Território/ESF"
        verbose_name_plural = "Territórios/ESF"

    def __str__(self):
        return self.nome
