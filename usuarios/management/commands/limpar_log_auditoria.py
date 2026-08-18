from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from usuarios.models import LogAuditoria


class Command(BaseCommand):
    help = (
        "Remove registros de LogAuditoria mais antigos que "
        "RETENCAO_LOG_AUDITORIA_DIAS (padrão: settings.RETENCAO_LOG_AUDITORIA_DIAS). "
        "Sem retenção definida, o log cresce para sempre e fica caro de consultar."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dias",
            type=int,
            default=None,
            help="Sobrescreve RETENCAO_LOG_AUDITORIA_DIAS só para esta execução.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Mostra quantos registros seriam apagados, sem apagar de fato.",
        )

    def handle(self, *args, **options):
        dias = options["dias"] if options["dias"] is not None else settings.RETENCAO_LOG_AUDITORIA_DIAS
        limite = timezone.now() - timezone.timedelta(days=dias)
        antigos = LogAuditoria.objects.filter(data_hora__lt=limite)
        total = antigos.count()

        if options["dry_run"]:
            self.stdout.write(
                f"[dry-run] {total} registro(s) de LogAuditoria anteriores a "
                f"{limite:%d/%m/%Y} seriam apagados (retenção: {dias} dias)."
            )
            return

        antigos.delete()
        self.stdout.write(
            self.style.SUCCESS(
                f"{total} registro(s) de LogAuditoria anteriores a {limite:%d/%m/%Y} "
                f"apagados (retenção: {dias} dias)."
            )
        )
