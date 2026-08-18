from django.db import models
from django.urls import reverse

from escolas.models import Escola
from territorios.models import Territorio

from .fields import CPFCriptografadoField, hash_cpf
from .validators import normalizar_cpf, normalizar_telefone, validar_cpf, validar_telefone


class Estudante(models.Model):
    data_registro = models.DateTimeField(auto_now_add=True)
    nome = models.CharField("Nome da Criança ou Adolescente", max_length=200)
    # validators=[validar_cpf]/[validar_telefone] são a defesa em profundidade:
    # cobrem edições feitas direto pelo Django Admin, que não passa pelo
    # EstudanteForm.clean_cpf/clean_telefone.
    cpf = CPFCriptografadoField("CPF", validators=[validar_cpf])
    cpf_hash = models.CharField(max_length=64, unique=True, editable=False)
    data_nascimento = models.DateField("Data de Nascimento")
    nome_responsavel = models.CharField("Nome do Responsável", max_length=200)
    telefone = models.CharField(max_length=20, validators=[validar_telefone])
    escola = models.ForeignKey(Escola, on_delete=models.PROTECT, related_name="estudantes")
    ano_turma = models.CharField("Ano/Turma", max_length=50)
    territorio_esf = models.ForeignKey(
        Territorio,
        on_delete=models.PROTECT,
        related_name="estudantes",
        verbose_name="Território/ESF de referência",
    )

    class Meta:
        ordering = ["nome"]
        verbose_name = "Estudante"
        verbose_name_plural = "Estudantes"

    def __str__(self):
        return f"{self.nome} ({self.escola})"

    def save(self, *args, **kwargs):
        # Normaliza antes de gravar: garante que o CPF/telefone fiquem
        # sempre só com dígitos no banco, independente de terem vindo do
        # EstudanteForm (que já normaliza) ou de uma edição direta no Admin.
        self.cpf = normalizar_cpf(self.cpf)
        self.telefone = normalizar_telefone(self.telefone)
        self.cpf_hash = hash_cpf(self.cpf)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("estudantes:detalhe", args=[self.pk])

    @property
    def cpf_mascarado(self):
        digitos = "".join(c for c in self.cpf if c.isdigit())
        if len(digitos) != 11:
            return "***"
        return f"{digitos[:3]}.***.***-{digitos[9:]}"

    @property
    def telefone_formatado(self):
        """Telefone é armazenado só com dígitos; formata para exibição."""
        digitos = "".join(c for c in self.telefone if c.isdigit())
        if len(digitos) == 11:
            return f"({digitos[:2]}) {digitos[2:7]}-{digitos[7:]}"
        if len(digitos) == 10:
            return f"({digitos[:2]}) {digitos[2:6]}-{digitos[6:]}"
        return self.telefone

    @classmethod
    def buscar_por_cpf(cls, cpf: str):
        return cls.objects.filter(cpf_hash=hash_cpf(cpf)).first()
