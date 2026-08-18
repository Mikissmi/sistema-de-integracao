"""Importação de estudantes em lote por CSV (uma escola por arquivo).

Processa linha a linha: uma linha inválida (CPF errado, duplicado, coluna
faltando, território não encontrado) é pulada e reportada, sem derrubar o
restante do lote. Reaproveita o EstudanteForm para a validação — mesma regra
de CPF/telefone/escopo do cadastro manual, não um caminho paralelo mais
frouxo.
"""

import csv
import io
from datetime import datetime

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from territorios.models import Territorio
from usuarios.models import LogAuditoria

from .forms import EstudanteForm

COLUNAS_ESPERADAS = [
    "nome",
    "cpf",
    "data_nascimento",
    "nome_responsavel",
    "telefone",
    "ano_turma",
    "territorio_esf",
]
MAX_LINHAS = 500
FORMATOS_DATA = ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y")
CODIFICACOES = ("utf-8-sig", "utf-8", "cp1252", "latin-1")


class LinhaInvalida(Exception):
    """Erro de uma linha específica do CSV — não interrompe o restante do lote."""


def _decodificar(conteudo_bruto: bytes) -> str:
    for codificacao in CODIFICACOES:
        try:
            return conteudo_bruto.decode(codificacao)
        except UnicodeDecodeError:
            continue
    raise ValidationError(
        "Não foi possível ler o arquivo — salve o CSV como UTF-8 ou "
        "\"CSV (separado por vírgulas)\" no Excel e tente novamente."
    )


def _detectar_delimitador(texto: str) -> str:
    # Excel em português costuma exportar CSV separado por ";" em vez de ",".
    primeira_linha = texto.splitlines()[0] if texto.splitlines() else ""
    return ";" if primeira_linha.count(";") > primeira_linha.count(",") else ","


def _parse_data(valor: str):
    valor = valor.strip()
    for formato in FORMATOS_DATA:
        try:
            return datetime.strptime(valor, formato).date()
        except ValueError:
            continue
    raise LinhaInvalida(f"Data de nascimento inválida: \"{valor}\" (use dd/mm/aaaa).")


def processar_csv(arquivo, escola, usuario):
    """Lê o CSV e cria os estudantes válidos.

    Retorna (total_importados, lista_de_erros); cada erro é um dict
    {"linha": N, "motivo": "..."}. Levanta ValidationError só para problemas
    do arquivo inteiro (codificação ilegível, cabeçalho sem as colunas
    esperadas) — nunca por causa de uma linha ruim.
    """
    texto = _decodificar(arquivo.read())
    delimitador = _detectar_delimitador(texto)
    leitor = csv.DictReader(io.StringIO(texto), delimiter=delimitador)

    if not leitor.fieldnames:
        raise ValidationError("Arquivo CSV vazio ou sem linha de cabeçalho.")

    colunas = {c.strip().lower(): c for c in leitor.fieldnames}
    faltando = [c for c in COLUNAS_ESPERADAS if c not in colunas]
    if faltando:
        raise ValidationError(
            "Colunas faltando no CSV: " + ", ".join(faltando) + ". "
            "Baixe o modelo para conferir o formato esperado."
        )

    importados = 0
    erros = []

    for numero_linha, linha_bruta in enumerate(leitor, start=2):  # linha 1 = cabeçalho
        if numero_linha - 1 > MAX_LINHAS:
            erros.append(
                {"linha": numero_linha, "motivo": f"Ignorada: limite de {MAX_LINHAS} linhas por arquivo."}
            )
            continue

        linha = {chave: (linha_bruta.get(coluna) or "").strip() for chave, coluna in colunas.items()}

        try:
            if not linha["nome"]:
                raise LinhaInvalida("Nome em branco.")

            territorio = Territorio.objects.filter(nome__iexact=linha["territorio_esf"]).first()
            if territorio is None:
                raise LinhaInvalida(
                    f"Território/ESF \"{linha['territorio_esf']}\" não encontrado — "
                    "confira a grafia ou cadastre-o antes pelo Admin."
                )

            data_nascimento = _parse_data(linha["data_nascimento"])

            form = EstudanteForm(
                data={
                    "nome": linha["nome"],
                    "cpf": linha["cpf"],
                    "data_nascimento": data_nascimento.isoformat(),
                    "nome_responsavel": linha["nome_responsavel"],
                    "telefone": linha["telefone"],
                    "ano_turma": linha["ano_turma"],
                    "escola": escola.pk,
                    "territorio_esf": territorio.pk,
                },
                usuario=usuario,
            )
            if not form.is_valid():
                primeiro_erro = next(iter(form.errors.values()))[0]
                raise LinhaInvalida(primeiro_erro)

            with transaction.atomic():
                estudante = form.save()
            LogAuditoria.objects.create(
                usuario=usuario, acao="criar_estudante", objeto=str(estudante)
            )
            importados += 1
        except LinhaInvalida as e:
            erros.append({"linha": numero_linha, "motivo": str(e)})
        except IntegrityError:
            erros.append({"linha": numero_linha, "motivo": "CPF já cadastrado (conflito ao salvar)."})

    return importados, erros
