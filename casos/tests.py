from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from atendimentos.models import TipoAtendimento
from escolas.models import Escola
from estudantes.models import Estudante
from territorios.models import Territorio
from usuarios.models import PerfilUsuario
from usuarios.permissions import escopo_casos

from .models import Caso

CPF_VALIDO = "111.444.777-35"


class CasoTestBase(TestCase):
    def setUp(self):
        self.escola_a = Escola.objects.create(nome="Escola A")
        self.escola_b = Escola.objects.create(nome="Escola B")
        self.territorio = Territorio.objects.create(nome="ESF Teste")
        self.tipo_atendimento = TipoAtendimento.objects.create(nome="Psicologia")
        self.estudante = Estudante.objects.create(
            nome="Estudante Teste",
            cpf=CPF_VALIDO,
            data_nascimento="2015-01-01",
            nome_responsavel="Responsável",
            telefone="51999998888",
            escola=self.escola_a,
            ano_turma="3º ano",
            territorio_esf=self.territorio,
        )

    def _criar_caso(self, dias_atras, situacao=Caso.Situacao.AGUARDANDO, retorno_previsto=None):
        return Caso.objects.create(
            estudante=self.estudante,
            servico_encaminhado=self.tipo_atendimento,
            data_encaminhamento=timezone.localdate() - timedelta(days=dias_atras),
            profissional_responsavel="Prof. Teste",
            situacao=situacao,
            retorno_previsto=retorno_previsto,
        )


class NivelAlertaTests(CasoTestBase):
    """Cobre a lógica de alerta (settings.DIAS_ALERTA_AGUARDANDO=10,
    DIAS_CRITICO_AGUARDANDO=15, DIAS_CRITICO_SEM_EVOLUCAO=30 por padrão)."""

    def test_aguardando_recente_fica_ok(self):
        caso = self._criar_caso(dias_atras=2)
        self.assertEqual(caso.nivel_alerta, "ok")

    def test_aguardando_acima_do_limite_de_atencao_fica_atencao(self):
        caso = self._criar_caso(dias_atras=11)
        self.assertEqual(caso.nivel_alerta, "atencao")

    def test_aguardando_acima_do_limite_critico_fica_critico(self):
        caso = self._criar_caso(dias_atras=16)
        self.assertEqual(caso.nivel_alerta, "critico")

    def test_encerrado_nao_gera_alerta(self):
        caso = self._criar_caso(dias_atras=100, situacao=Caso.Situacao.ENCERRADO)
        self.assertIsNone(caso.dias_sem_retorno)
        self.assertEqual(caso.nivel_alerta, "ok")

    def test_retorno_previsto_vencido_e_sempre_critico(self):
        caso = self._criar_caso(
            dias_atras=1, retorno_previsto=timezone.localdate() - timedelta(days=1)
        )
        self.assertEqual(caso.nivel_alerta, "critico")

    def test_nivel_alerta_usa_cache_de_prefetch_related_sem_query_extra(self):
        """Regressão do N+1: com prefetch_related('evolucoes'), acessar
        nivel_alerta não deve disparar uma query nova por caso."""
        self._criar_caso(dias_atras=2)
        casos = list(Caso.objects.prefetch_related("evolucoes").all())
        with self.assertNumQueries(0):
            for caso in casos:
                caso.nivel_alerta  # noqa: B018 - acesso proposital, é a asserção


class EscopoCasosTests(CasoTestBase):
    def test_usuario_sem_perfil_nao_ve_nenhum_caso(self):
        caso = self._criar_caso(dias_atras=1)
        user = User.objects.create_user("sem.perfil", password="senha-teste-123")
        self.assertEqual(escopo_casos(user, Caso.objects.all()).count(), 0)

    def test_perfil_educacao_ve_so_casos_da_propria_escola(self):
        caso_a = self._criar_caso(dias_atras=1)
        user = User.objects.create_user("prof.educacao", password="senha-teste-123")
        PerfilUsuario.objects.create(usuario=user, perfil="educacao", escola=self.escola_a)
        self.assertEqual(list(escopo_casos(user, Caso.objects.all())), [caso_a])


class AtualizarSituacaoViewTests(CasoTestBase):
    def test_usuario_no_escopo_consegue_atualizar_situacao(self):
        caso = self._criar_caso(dias_atras=1)
        user = User.objects.create_user("prof.educacao", password="senha-teste-123")
        PerfilUsuario.objects.create(usuario=user, perfil="educacao", escola=self.escola_a)
        self.client.force_login(user)

        response = self.client.post(
            reverse("casos:atualizar_situacao", args=[caso.pk]),
            {"situacao": Caso.Situacao.EM_ACOMPANHAMENTO},
        )
        self.assertRedirects(response, reverse("casos:detalhe", args=[caso.pk]))
        caso.refresh_from_db()
        self.assertEqual(caso.situacao, Caso.Situacao.EM_ACOMPANHAMENTO)

    def test_usuario_fora_do_escopo_nao_consegue_atualizar(self):
        caso = self._criar_caso(dias_atras=1)  # pertence à Escola A
        user = User.objects.create_user("prof.outra.escola", password="senha-teste-123")
        PerfilUsuario.objects.create(usuario=user, perfil="educacao", escola=self.escola_b)
        self.client.force_login(user)

        response = self.client.post(
            reverse("casos:atualizar_situacao", args=[caso.pk]),
            {"situacao": Caso.Situacao.EM_ACOMPANHAMENTO},
        )
        self.assertEqual(response.status_code, 404)
        caso.refresh_from_db()
        self.assertEqual(caso.situacao, Caso.Situacao.AGUARDANDO)
