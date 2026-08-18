"""Validação e normalização de CPF e telefone.

Usados tanto no formulário de cadastro (mensagem de erro amigável, o quanto
antes) quanto como `validators=` nos próprios campos do model (defesa em
profundidade — cobre edições feitas direto pelo Django Admin, que não passa
pelo `EstudanteForm`).
"""

import re

from django.core.exceptions import ValidationError

TELEFONE_RE = re.compile(r"^[1-9][0-9](?:9\d{8}|\d{8})$")


def normalizar_cpf(cpf: str) -> str:
    """Remove tudo que não for dígito (pontos, traço, espaços)."""
    return "".join(c for c in cpf if c.isdigit())


def validar_cpf(value) -> None:
    """Valida um CPF (com ou sem máscara). Levanta ValidationError se inválido.

    Verifica: 11 dígitos, não ser uma sequência repetida (000.000.000-00 etc.)
    e os dois dígitos verificadores pelo algoritmo oficial (módulo 11).
    """
    digitos = normalizar_cpf(str(value))

    if len(digitos) != 11:
        raise ValidationError("CPF deve conter 11 dígitos.")
    if digitos == digitos[0] * 11:
        raise ValidationError("CPF inválido.")

    def _digito_verificador(parcial: str, peso_inicial: int) -> str:
        soma = sum(int(d) * peso for d, peso in zip(parcial, range(peso_inicial, 1, -1)))
        resto = soma % 11
        return "0" if resto < 2 else str(11 - resto)

    d1 = _digito_verificador(digitos[:9], 10)
    d2 = _digito_verificador(digitos[:9] + d1, 11)
    if digitos[9:] != d1 + d2:
        raise ValidationError("CPF inválido (dígito verificador não confere).")


def normalizar_telefone(telefone: str) -> str:
    """Remove tudo que não for dígito e o código do país (+55), se presente."""
    digitos = "".join(c for c in telefone if c.isdigit())
    if len(digitos) in (12, 13) and digitos.startswith("55"):
        digitos = digitos[2:]
    return digitos


def validar_telefone(value) -> None:
    """Valida um telefone brasileiro: DDD (11-99) + 8 dígitos (fixo) ou 9
    dígitos começando com 9 (celular)."""
    digitos = normalizar_telefone(str(value))
    if not TELEFONE_RE.match(digitos):
        raise ValidationError(
            "Telefone inválido. Informe o DDD + número, com 10 ou 11 dígitos "
            "(ex.: 51999998888)."
        )
