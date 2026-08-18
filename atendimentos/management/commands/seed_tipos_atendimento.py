from django.core.management.base import BaseCommand

from atendimentos.models import TipoAtendimento

TIPOS = [
    "Psicologia",
    "Nutrição",
    "Fonoaudiologia",
    "Psiquiatria Infantil",
    "Terapia Ocupacional",
    "Neurologia Pediátrica",
    "Assistência Social",
    "Fisioterapia",
    "Odontologia",
    "Pediatria / Clínica Geral",
]


class Command(BaseCommand):
    help = (
        "Popula uma lista inicial de tipos de atendimento (Psicologia, Nutrição, etc.). "
        "A lista pode ser editada, ampliada ou reduzida depois pelo admin."
    )

    def handle(self, *args, **options):
        criados = 0
        for nome in TIPOS:
            _, created = TipoAtendimento.objects.get_or_create(nome=nome)
            criados += int(created)
        self.stdout.write(
            self.style.SUCCESS(f"{criados} tipo(s) de atendimento novo(s) cadastrado(s).")
        )
