from django import forms

from escolas.models import Escola
from territorios.models import Territorio
from usuarios.forms import BootstrapFormMixin

from .models import Estudante
from .validators import normalizar_cpf, normalizar_telefone, validar_cpf, validar_telefone


class BuscaCPFForm(BootstrapFormMixin, forms.Form):
    cpf = forms.CharField(
        label="CPF da Criança/Adolescente",
        max_length=14,
        widget=forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "off"}),
    )


class EstudanteForm(BootstrapFormMixin, forms.ModelForm):
    data_nascimento = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}), label="Data de Nascimento"
    )

    class Meta:
        model = Estudante
        fields = [
            "nome",
            "cpf",
            "data_nascimento",
            "nome_responsavel",
            "telefone",
            "escola",
            "ano_turma",
            "territorio_esf",
        ]
        widgets = {
            # O campo do model tem max_length=400 (tamanho do texto
            # criptografado em repouso, não do CPF) — no formulário o limite
            # visível ao usuário precisa ser o de um CPF com máscara.
            "cpf": forms.TextInput(attrs={"maxlength": 14, "inputmode": "numeric"}),
        }

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        perfil = getattr(usuario, "perfil", None) if usuario is not None else None

        # Trava a escola/território ao escopo do usuário logado — sem isso,
        # um usuário do perfil "Educação" da Escola A podia cadastrar um
        # estudante em qualquer outra escola do município. `disabled=True`
        # não é só cosmético: o Django ignora o que vier no POST para um
        # campo desabilitado e usa sempre o `initial`, então isso protege
        # mesmo que alguém edite o <select> pelas ferramentas do navegador.
        if perfil and perfil.perfil == "educacao" and perfil.escola_id:
            self.fields["escola"].queryset = Escola.objects.filter(pk=perfil.escola_id)
            self.fields["escola"].initial = perfil.escola_id
            self.fields["escola"].disabled = True
        if perfil and perfil.perfil == "saude" and perfil.territorio_esf_id:
            self.fields["territorio_esf"].queryset = Territorio.objects.filter(
                pk=perfil.territorio_esf_id
            )
            self.fields["territorio_esf"].initial = perfil.territorio_esf_id
            self.fields["territorio_esf"].disabled = True

    def clean_cpf(self):
        cpf = self.cleaned_data["cpf"]
        validar_cpf(cpf)
        cpf_normalizado = normalizar_cpf(cpf)
        existente = Estudante.buscar_por_cpf(cpf_normalizado)
        if existente and existente.pk != self.instance.pk:
            raise forms.ValidationError(
                "Já existe um estudante cadastrado com este CPF. Use a busca por "
                "CPF para encontrar o registro existente."
            )
        return cpf_normalizado

    def clean_telefone(self):
        telefone = self.cleaned_data["telefone"]
        validar_telefone(telefone)
        return normalizar_telefone(telefone)


TAMANHO_MAXIMO_CSV = 2 * 1024 * 1024  # 2MB


class EstudanteImportForm(BootstrapFormMixin, forms.Form):
    """Escola de destino do lote inteiro + arquivo CSV. A escola é escolhida
    uma vez para todo o arquivo (não é uma coluna do CSV) — o objetivo é
    "esta escola importa a lista dela", não misturar escolas num arquivo só.
    """

    escola = forms.ModelChoiceField(
        queryset=Escola.objects.filter(ativo=True), label="Escola"
    )
    arquivo = forms.FileField(
        label="Arquivo CSV",
        help_text=(
            "Colunas esperadas: nome, cpf, data_nascimento, nome_responsavel, "
            "telefone, ano_turma, territorio_esf."
        ),
    )

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        perfil = getattr(usuario, "perfil", None) if usuario is not None else None
        # Mesma trava do EstudanteForm: perfil Educação só importa pra
        # própria escola.
        if perfil and perfil.perfil == "educacao" and perfil.escola_id:
            self.fields["escola"].queryset = Escola.objects.filter(pk=perfil.escola_id)
            self.fields["escola"].initial = perfil.escola_id
            self.fields["escola"].disabled = True

    def clean_arquivo(self):
        arquivo = self.cleaned_data["arquivo"]
        if not arquivo.name.lower().endswith(".csv"):
            raise forms.ValidationError("Envie um arquivo .csv.")
        if arquivo.size > TAMANHO_MAXIMO_CSV:
            raise forms.ValidationError("Arquivo muito grande (máximo 2MB).")
        return arquivo
