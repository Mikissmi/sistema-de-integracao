from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from escolas.models import Escola

ESCOLAS = [
    ("Pestalozzi de Canoas", Escola.Tipo.ESPECIAL),
    ("Escola Municipal de Ensino Fundamental Vasconcelos Jardim", Escola.Tipo.MUNICIPAL_EF),
    ("Escola Estadual de Ensino Fundamental Barão de Teresópolis", Escola.Tipo.ESTADUAL),
    ("Escola Municipal de Ensino Fundamental Álvaro Almeida", Escola.Tipo.MUNICIPAL_EF),
    ("Escola Municipal de Ensino Fundamental Campos Salles", Escola.Tipo.MUNICIPAL_EF),
    ("Escola Municipal de Ensino Fundamental Bilíngue para Surdos Vitória", Escola.Tipo.ESPECIAL),
    ("EMEF Alfredo Antonio Amorim", Escola.Tipo.MUNICIPAL_EF),
    ("Escola Municipal de Ensino Fundamental José Bonifácio", Escola.Tipo.MUNICIPAL_EF),
    ("Escola Municipal de Ensino Fundamental Miguel Couto", Escola.Tipo.MUNICIPAL_EF),
    ("EMEF Rui Barbosa", Escola.Tipo.MUNICIPAL_EF),
    ("Escola Municipal de Ensino Fundamental Tiradentes", Escola.Tipo.MUNICIPAL_EF),
    ("Escola Municipal de Ensino Fundamental Treze de Maio", Escola.Tipo.MUNICIPAL_EF),
    ("Escola Municipal de Ensino Fundamental Janaína", Escola.Tipo.MUNICIPAL_EF),
    ("Escola Municipal de Ensino Fundamental Hélio Fraga", Escola.Tipo.MUNICIPAL_EF),
    ("EMEF Santa Rita de Cássia", Escola.Tipo.MUNICIPAL_EF),
    ("Escola Municipal de Educação Infantil Rainer", Escola.Tipo.MUNICIPAL_EI),
    ("Escola Municipal de Educação Infantil Paulo Freire", Escola.Tipo.MUNICIPAL_EI),
    ("Escola Municipal de Educação Infantil Vó Enedina", Escola.Tipo.MUNICIPAL_EI),
    ("Escola Municipal de Educação Infantil Vó Luiza", Escola.Tipo.MUNICIPAL_EI),
    ("Escola Municipal de Ensino Fundamental Victor Aggens", Escola.Tipo.MUNICIPAL_EF),
    ("Escola Municipal de Educação Infantil Vó Edith", Escola.Tipo.MUNICIPAL_EI),
]

GRUPOS = ["Educação", "Saúde", "Gestão Municipal"]


class Command(BaseCommand):
    help = "Popula o cadastro das 21 unidades escolares e cria os grupos de perfil (Educação/Saúde/Gestão)."

    def handle(self, *args, **options):
        criadas = 0
        for nome, tipo in ESCOLAS:
            _, created = Escola.objects.get_or_create(nome=nome, defaults={"tipo": tipo})
            criadas += int(created)
        self.stdout.write(self.style.SUCCESS(f"{criadas} escola(s) nova(s) cadastrada(s) (total {len(ESCOLAS)})."))

        for nome_grupo in GRUPOS:
            Group.objects.get_or_create(name=nome_grupo)
        self.stdout.write(self.style.SUCCESS("Grupos de perfil (Educação/Saúde/Gestão Municipal) prontos."))
