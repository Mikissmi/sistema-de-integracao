"""
Configurações do projeto Acompanhamento Intersetorial (Educação-Saúde).

Local/dev: usa SQLite automaticamente.
Produção (Vercel): defina a variável de ambiente DATABASE_URL (Postgres/Neon).
"""

import os
from datetime import timedelta
from pathlib import Path

import dj_database_url
from cryptography.fernet import Fernet
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Carrega o .env local (se existir) para os.environ. Em produção (Vercel) não
# existe esse arquivo — load_dotenv() simplesmente não faz nada nesse caso, e
# as variáveis vêm direto do ambiente configurado na plataforma.
load_dotenv(BASE_DIR / ".env")

# Em desenvolvimento local, o padrão deve ser um ambiente funcional sem exigir
# variáveis de produção antes do primeiro boot. Somente quando explicitamente
# configurado como False é que a aplicação passa a exigir SECRET_KEY e banco de
# dados de produção.
DEBUG = os.environ.get("DEBUG", "True") == "True"

SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "django-insecure-somente-para-desenvolvimento-local"
    else:
        raise ImproperlyConfigured(
            "SECRET_KEY é obrigatória em produção (DEBUG=False). Gere uma chave com: "
            "python3 -c \"from django.core.management.utils import get_random_secret_key; "
            'print(get_random_secret_key())"'
        )

ALLOWED_HOSTS = [
    h.strip() for h in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()
]
CSRF_TRUSTED_ORIGINS = [f"https://{h}" for h in ALLOWED_HOSTS if h not in ("localhost", "127.0.0.1")]

# A Vercel define VERCEL=1 em toda implantação. O domínio de produção
# (ex.: escolasaude.vercel.app) é diferente do domínio único de cada deploy
# (VERCEL_URL), por isso liberamos qualquer subdomínio *.vercel.app em vez de
# tentar adivinhar o domínio exato - evita esse erro a cada novo deploy/preview.
if os.environ.get("VERCEL"):
    ALLOWED_HOSTS.append(".vercel.app")
    CSRF_TRUSTED_ORIGINS.append("https://*.vercel.app")


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "axes",
    "escolas",
    "territorios",
    "atendimentos",
    "usuarios",
    "estudantes",
    "casos",
    "indicadores",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Precisa ser o último (exigência do django-axes): registra tentativas de
    # login processadas por todos os middlewares anteriores.
    "axes.middleware.AxesMiddleware",
]

# django-axes precisa vir antes do backend padrão do Django para poder
# bloquear a autenticação antes dela ser concluída.
AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Banco de dados: SQLite localmente; Postgres (Neon/Vercel) em produção via DATABASE_URL.
# Fora de DEBUG, exigimos DATABASE_URL explicitamente: cair silenciosamente para
# SQLite em produção (ex.: Vercel, sem disco persistente) resulta em perda de
# dados a cada cold start, sem nenhum aviso.
if not DEBUG and not os.environ.get("DATABASE_URL"):
    raise ImproperlyConfigured(
        "DATABASE_URL é obrigatória em produção (DEBUG=False) — configure o "
        "Postgres (Neon) antes de fazer deploy."
    )

DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
    )
}


AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Uploads (anexos de encaminhamento em PDF).
# Em produção (Vercel) não há disco persistente: configure MEDIA_URL/armazenamento
# externo (Vercel Blob ou S3 via django-storages) antes de ir para produção.
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "indicadores:painel"
LOGOUT_REDIRECT_URL = "login"

# Chave para criptografia do CPF em repouso (ver estudantes/fields.py).
# Em produção é obrigatória via variável de ambiente: sem uma chave própria e
# secreta, o CPF criptografado no banco pode ser decifrado por qualquer pessoa
# que tenha acesso ao código-fonte (nunca use um valor hardcoded aqui).
FIELD_ENCRYPTION_KEY = os.environ.get("FIELD_ENCRYPTION_KEY")
if not FIELD_ENCRYPTION_KEY:
    if DEBUG:
        # Só em desenvolvimento: chave nova a cada start, dados cifrados não
        # sobrevivem a um restart do servidor local — isso é intencional.
        FIELD_ENCRYPTION_KEY = Fernet.generate_key().decode()
    else:
        raise ImproperlyConfigured(
            "FIELD_ENCRYPTION_KEY é obrigatória em produção (DEBUG=False). Gere uma "
            "chave com: python3 -c \"from cryptography.fernet import Fernet; "
            'print(Fernet.generate_key().decode())"'
        )

# Rate limiting de login (django-axes). Bloqueia por 1h30 depois de 5
# tentativas erradas para a combinação usuário+IP — não só por IP, porque
# escolas/unidades de saúde costumam compartilhar uma única rede (NAT):
# bloquear só por IP travaria todo mundo daquele prédio por causa de uma
# pessoa errando a senha.
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(hours=1, minutes=30)
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
AXES_RESET_ON_SUCCESS = True
AXES_LOCKOUT_TEMPLATE = "registration/bloqueado.html"

# Regras de alerta de atraso (parametrizáveis conforme seção 5 do planejamento).
DIAS_ALERTA_AGUARDANDO = int(os.environ.get("DIAS_ALERTA_AGUARDANDO", 10))
DIAS_CRITICO_AGUARDANDO = int(os.environ.get("DIAS_CRITICO_AGUARDANDO", 15))
DIAS_CRITICO_SEM_EVOLUCAO = int(os.environ.get("DIAS_CRITICO_SEM_EVOLUCAO", 30))

# Retenção do log de auditoria (LGPD: não guardar dado além do necessário).
# Usado por `manage.py limpar_log_auditoria` e pela rotina agendada via
# Vercel Cron (ver usuarios/views.py:limpar_log_auditoria_view e vercel.json).
RETENCAO_LOG_AUDITORIA_DIAS = int(os.environ.get("RETENCAO_LOG_AUDITORIA_DIAS", 365))

# Segredo compartilhado que autoriza a Vercel Cron a chamar endpoints de
# tarefa agendada (ex.: limpeza do log de auditoria). A Vercel envia esse
# valor automaticamente como "Authorization: Bearer <CRON_SECRET>" quando a
# variável de ambiente CRON_SECRET está configurada no projeto.
# Sem essa variável, o endpoint de tarefa agendada fica desativado (retorna
# 503) em vez de aceitar chamadas sem autenticação.
CRON_SECRET = os.environ.get("CRON_SECRET")

# E-mail (recuperação e troca de senha). Backend SMTP genérico — funciona com
# qualquer provedor (Gmail, SendGrid, Resend, AWS SES, etc.), basta preencher
# as variáveis de ambiente correspondentes. Em desenvolvimento (DEBUG=True)
# sem EMAIL_HOST configurado, os e-mails só são impressos no console — não é
# preciso ter um provedor real para testar o fluxo localmente.
if os.environ.get("EMAIL_HOST"):
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = os.environ["EMAIL_HOST"]
    EMAIL_PORT = int(os.environ.get("EMAIL_PORT", 587))
    EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
    EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "True") == "True"
elif DEBUG:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
else:
    raise ImproperlyConfigured(
        "EMAIL_HOST é obrigatória em produção (DEBUG=False) — sem ela, a "
        "recuperação de senha por e-mail não funciona."
    )

DEFAULT_FROM_EMAIL = os.environ.get(
    "DEFAULT_FROM_EMAIL", "Acompanhamento Escola-Saúde <nao-responda@example.com>"
)

# Prazo de validade do link de redefinição de senha (padrão do Django é 3
# dias — reduzido aqui por lidar com dado sensível de crianças/adolescentes).
PASSWORD_RESET_TIMEOUT = int(os.environ.get("PASSWORD_RESET_TIMEOUT", 24 * 60 * 60))

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

    # HSTS: começa em 1 hora para não travar o domínio caso o HTTPS tenha algum
    # problema no primeiro deploy; depois de confirmar que está estável, suba
    # gradualmente até 31536000 (1 ano) e ative as duas linhas comentadas.
    SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", 3600))
    # SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    # SECURE_HSTS_PRELOAD = True