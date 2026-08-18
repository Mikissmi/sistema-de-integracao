import base64
import hashlib
import hmac
import logging

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from django.conf import settings
from django.db import models

logger = logging.getLogger(__name__)


def _derive_key(info: bytes) -> bytes:
    """Deriva uma subchave de 32 bytes a partir de FIELD_ENCRYPTION_KEY via
    HKDF-SHA256, com um `info` (contexto) diferente por uso.

    Isso evita reaproveitar a mesma chave crua para dois propósitos
    criptográficos distintos: cifrar o CPF (Fernet) e gerar o hash de busca
    (HMAC) passam a usar subchaves diferentes, ainda que derivadas do mesmo
    segredo original.
    """
    hkdf = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=info)
    return hkdf.derive(settings.FIELD_ENCRYPTION_KEY.encode())


def _fernet():
    chave_fernet = base64.urlsafe_b64encode(_derive_key(b"cpf-fernet-encryption-v1"))
    return Fernet(chave_fernet)


def hash_cpf(cpf: str) -> str:
    """Hash determinístico (HMAC-SHA256) usado para busca/unicidade, já que o
    valor criptografado (Fernet) não é determinístico e não pode ser indexado.

    Normaliza (mantém só os dígitos) antes de calcular o hash: sem isso, o
    mesmo CPF digitado com e sem máscara ("111.444.777-35" vs "11144477735")
    gerava hashes diferentes e escapava da checagem de duplicidade.
    """
    digitos = "".join(c for c in cpf if c.isdigit())
    chave_hmac = _derive_key(b"cpf-search-hmac-v1")
    return hmac.new(chave_hmac, digitos.encode(), hashlib.sha256).hexdigest()


class CPFCriptografadoField(models.CharField):
    """Armazena o CPF criptografado (Fernet) no banco; em memória o valor é o CPF em texto puro."""

    description = "CPF armazenado criptografado em repouso"

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 400)
        super().__init__(*args, **kwargs)

    def get_prep_value(self, value):
        if value in (None, ""):
            return value
        return _fernet().encrypt(value.encode()).decode()

    def from_db_value(self, value, expression, connection):
        if value in (None, ""):
            return value
        try:
            return _fernet().decrypt(value.encode()).decode()
        except InvalidToken:
            # Não deveria acontecer em uso normal — indica dado gravado com
            # uma chave diferente da atual (ex.: FIELD_ENCRYPTION_KEY trocada
            # sem migrar os dados existentes) ou corrupção. Antes isso
            # retornava o valor bruto (ainda cifrado) em silêncio; agora pelo
            # menos fica registrado, para não mascarar um problema real.
            logger.warning(
                "CPFCriptografadoField: falha ao decifrar valor do banco "
                "(token inválido) — retornando valor bruto sem decifrar."
            )
            return value
