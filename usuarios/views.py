from django.conf import settings
from django.core.management import call_command
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

# Este app não tem views de UI próprias: perfis são gerenciados pelo admin
# (login/logout ficam em config/urls.py, usando as views prontas do Django).
# A única view daqui é a tarefa agendada de limpeza do log de auditoria,
# disparada pela Vercel Cron (ver vercel.json) — não é uma tela.


@csrf_exempt
@require_GET
def limpar_log_auditoria_view(request):
    """Endpoint chamado pela Vercel Cron para rodar a limpeza do log de
    auditoria periodicamente (não há processo persistente em serverless para
    rodar isso como um cron tradicional). Protegido por CRON_SECRET: a Vercel
    envia "Authorization: Bearer <CRON_SECRET>" automaticamente quando essa
    variável de ambiente está configurada no projeto.
    """
    if not settings.CRON_SECRET:
        return HttpResponse("CRON_SECRET não configurado.", status=503)

    auth = request.headers.get("Authorization", "")
    if auth != f"Bearer {settings.CRON_SECRET}":
        return HttpResponseForbidden("Não autorizado.")

    call_command("limpar_log_auditoria")
    return JsonResponse({"ok": True})
