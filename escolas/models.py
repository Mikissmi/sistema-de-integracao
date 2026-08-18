from django.db import models


class Escola(models.Model):
    class Tipo(models.TextChoices):
        MUNICIPAL_EF = "municipal_ef", "Municipal - Ensino Fundamental"
        MUNICIPAL_EI = "municipal_ei", "Municipal - Educação Infantil"
        ESTADUAL = "estadual", "Estadual"
        ESPECIAL = "especial", "Educação Especial"

    nome = models.CharField(max_length=200, unique=True)
    tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.MUNICIPAL_EF)
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "Escola"
        verbose_name_plural = "Escolas"

    def __str__(self):
        return self.nome
