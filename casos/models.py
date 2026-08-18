from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property

from atendimentos.models import TipoAtendimento
from estudantes.models import Estudante


class Caso(models.Model):
    class Situacao(models.TextChoices):
        AGUARDANDO = "aguardando", "Aguardando Atendimento"
        EM_ACOMPANHAMENTO = "em_acompanhamento", "Em Acompanhamento"
        ENCERRADO = "encerrado", "Encerrado"

    class Gravidade(models.TextChoices):
        BAIXA = "baixa", "Baixa"
        MEDIA = "media", "Média"
        ALTA = "alta", "Alta"
        URGENTE = "urgente", "Urgente"

    estudante = models.ForeignKey(Estudante, on_delete=models.PROTECT, related_name="casos")
    data_registro = models.DateTimeField(auto_now_add=True)
    servico_encaminhado = models.ForeignKey(
        TipoAtendimento,
        on_delete=models.PROTECT,
        related_name="casos",
        verbose_name="Serviço Encaminhado",
    )
    data_encaminhamento = models.DateField("Data do Encaminhamento")
    profissional_responsavel = models.CharField(
        "Profissional Responsável (Educação)", max_length=150
    )
    data_atendimento = models.DateField("Data do Atendimento", null=True, blank=True)
    retorno_previsto = models.DateField("Retorno Previsto", null=True, blank=True)
    situacao = models.CharField(
        max_length=20, choices=Situacao.choices, default=Situacao.AGUARDANDO, db_index=True
    )
    gravidade = models.CharField(
        "Gravidade do Caso",
        max_length=10,
        choices=Gravidade.choices,
        default=Gravidade.MEDIA,
        db_index=True,
        help_text="Prioridade clínica/administrativa avaliada pelos profissionais, independente do tempo de espera.",
    )
    observacoes = models.TextField(blank=True)
    anexo_encaminhamento = models.FileField(
        "Anexo do Encaminhamento (PDF)",
        upload_to="encaminhamentos/%Y/%m/",
        null=True,
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=["pdf"])],
        help_text=(
            "Apenas arquivos PDF. Atenção: em produção na Vercel isso ainda não "
            "tem armazenamento persistente configurado — ver CHANGELOG.md."
        ),
    )

    class Meta:
        ordering = ["-data_registro"]
        verbose_name = "Caso / Encaminhamento"
        verbose_name_plural = "Casos / Encaminhamentos"

    def __str__(self):
        return f"Caso #{self.pk} - {self.estudante.nome}"

    def get_absolute_url(self):
        return reverse("casos:detalhe", args=[self.pk])

    @cached_property
    def data_referencia_alerta(self):
        """Data da última movimentação conhecida (última evolução, ou o encaminhamento).

        Usa `self.evolucoes.all()` (não `.order_by(...).first()` de propósito:
        um `.order_by()` explícito sempre dispara uma query nova, ignorando o
        cache de `prefetch_related("evolucoes")` das views de listagem/painel.
        `Evolucao.Meta.ordering` já ordena por `-data_movimentacao, -criado_em`,
        então o primeiro item de `.all()` já é a evolução mais recente — e
        `@cached_property` evita recalcular a cada acesso dentro do mesmo caso.
        """
        evolucoes = list(self.evolucoes.all())
        return evolucoes[0].data_movimentacao if evolucoes else self.data_encaminhamento

    @cached_property
    def dias_sem_retorno(self):
        if self.situacao == self.Situacao.ENCERRADO:
            return None
        return (timezone.localdate() - self.data_referencia_alerta).days

    @cached_property
    def nivel_alerta(self):
        """ok / atencao / critico - ver seção 5 do planejamento."""
        dias = self.dias_sem_retorno
        if dias is None:
            return "ok"
        if self.retorno_previsto and self.retorno_previsto < timezone.localdate():
            return "critico"
        if self.situacao == self.Situacao.AGUARDANDO:
            if dias >= settings.DIAS_CRITICO_AGUARDANDO:
                return "critico"
            if dias >= settings.DIAS_ALERTA_AGUARDANDO:
                return "atencao"
        if self.situacao == self.Situacao.EM_ACOMPANHAMENTO:
            if dias >= settings.DIAS_CRITICO_SEM_EVOLUCAO:
                return "critico"
        return "ok"


class Evolucao(models.Model):
    caso = models.ForeignKey(Caso, on_delete=models.CASCADE, related_name="evolucoes")
    data_movimentacao = models.DateField(default=timezone.localdate)
    servico_responsavel = models.CharField(max_length=150)
    profissional_responsavel = models.CharField(max_length=150)
    acao_realizada = models.TextField()
    encaminhamento_efetuado = models.TextField(blank=True)
    retorno_recebido = models.TextField(blank=True)
    observacoes = models.TextField(blank=True)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-data_movimentacao", "-criado_em"]
        verbose_name = "Evolução do Caso"
        verbose_name_plural = "Evoluções do Caso"

    def __str__(self):
        return f"Evolução de {self.caso} em {self.data_movimentacao:%d/%m/%Y}"
