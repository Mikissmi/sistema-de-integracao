from django import forms

from usuarios.forms import BootstrapFormMixin

from .models import Caso, Evolucao


class CasoForm(BootstrapFormMixin, forms.ModelForm):
    data_encaminhamento = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    data_atendimento = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}), required=False
    )
    retorno_previsto = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}), required=False
    )

    class Meta:
        model = Caso
        fields = [
            "servico_encaminhado",
            "data_encaminhamento",
            "profissional_responsavel",
            "data_atendimento",
            "retorno_previsto",
            "situacao",
            "gravidade",
            "observacoes",
            "anexo_encaminhamento",
        ]


class CasoSituacaoForm(BootstrapFormMixin, forms.ModelForm):
    """Formulário mínimo para avançar a situação de um caso (Aguardando →
    Em acompanhamento → Encerrado) sem precisar do Django Admin."""

    class Meta:
        model = Caso
        fields = ["situacao"]


class EvolucaoForm(BootstrapFormMixin, forms.ModelForm):
    data_movimentacao = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))

    class Meta:
        model = Evolucao
        fields = [
            "data_movimentacao",
            "servico_responsavel",
            "profissional_responsavel",
            "acao_realizada",
            "encaminhamento_efetuado",
            "retorno_recebido",
            "observacoes",
        ]
