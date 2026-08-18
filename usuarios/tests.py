import re
from datetime import timedelta

from django.contrib.auth.models import User
from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from escolas.models import Escola

from .models import LogAuditoria, PerfilUsuario

LINK_RESET_RE = re.compile(r"https?://[^\s]+/resetar-senha/(?P<uidb64>[\w-]+)/(?P<token>[\w-]+)/")


class PerfilUsuarioTests(TestCase):
    def test_str_mostra_usuario_e_perfil(self):
        user = User.objects.create_user("prof.educacao", password="senha-teste-123")
        escola = Escola.objects.create(nome="Escola Teste")
        perfil = PerfilUsuario.objects.create(usuario=user, perfil="educacao", escola=escola)
        self.assertIn("prof.educacao", str(perfil))
        self.assertIn("Educação", str(perfil))


class LogoutViewTests(TestCase):
    """Regressão: o botão 'Sair' era um <a> (GET), e o LogoutView do Django
    exige POST — um link GET para /logout/ resultava em 405, não em logout."""

    def test_logout_via_post_encerra_a_sessao(self):
        user = User.objects.create_user("usuario", password="senha-teste-123")
        self.client.force_login(user)
        response = self.client.post(reverse("logout"))
        self.assertEqual(response.status_code, 302)
        response = self.client.get(reverse("indicadores:painel"))
        self.assertRedirects(
            response, f"{reverse('login')}?next={reverse('indicadores:painel')}"
        )

    def test_logout_via_get_nao_e_mais_suportado_pelo_django(self):
        """Documenta o comportamento do Django 5 que motivou a correção: uma
        requisição GET para /logout/ não desloga, retorna 405."""
        user = User.objects.create_user("usuario", password="senha-teste-123")
        self.client.force_login(user)
        response = self.client.get(reverse("logout"))
        self.assertEqual(response.status_code, 405)


class PasswordResetFlowTests(TestCase):
    def test_fluxo_completo_de_recuperacao_de_senha(self):
        user = User.objects.create_user(
            "usuario", email="usuario@example.com", password="senha-antiga-123"
        )

        response = self.client.post(reverse("password_reset"), {"email": "usuario@example.com"})
        self.assertRedirects(response, reverse("password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("usuario@example.com", mail.outbox[0].to)

        match = LINK_RESET_RE.search(mail.outbox[0].body)
        self.assertIsNotNone(match, "link de redefinição não encontrado no corpo do e-mail")
        url_confirmacao = reverse(
            "password_reset_confirm",
            kwargs={"uidb64": match.group("uidb64"), "token": match.group("token")},
        )

        # 1º GET troca o token pela sessão e redireciona para a URL "set-password"
        # (comportamento padrão do Django, evita o token vazar via Referer).
        response = self.client.get(url_confirmacao, follow=True)
        self.assertEqual(response.status_code, 200)
        url_definir_senha = response.redirect_chain[-1][0]

        response = self.client.post(
            url_definir_senha,
            {"new_password1": "senha-nova-456", "new_password2": "senha-nova-456"},
        )
        self.assertRedirects(response, reverse("password_reset_complete"))

        user.refresh_from_db()
        self.assertTrue(user.check_password("senha-nova-456"))
        self.assertFalse(user.check_password("senha-antiga-123"))

    def test_email_nao_cadastrado_nao_revela_se_conta_existe(self):
        """Mesma resposta (redirect + tela genérica) para e-mail existente ou
        não — evita que alguém descubra quais e-mails têm conta no sistema."""
        response = self.client.post(reverse("password_reset"), {"email": "naoexiste@example.com"})
        self.assertRedirects(response, reverse("password_reset_done"))
        self.assertEqual(len(mail.outbox), 0)

    def test_link_invalido_nao_permite_redefinir(self):
        User.objects.create_user("usuario2", password="senha-antiga-123")
        url = reverse("password_reset_confirm", kwargs={"uidb64": "abc", "token": "token-invalido"})
        response = self.client.get(url)
        self.assertContains(response, "Link inválido ou expirado")


class PasswordChangeViewTests(TestCase):
    def test_usuario_logado_troca_a_propria_senha(self):
        user = User.objects.create_user("usuario3", password="senha-antiga-123")
        self.client.force_login(user)
        response = self.client.post(
            reverse("password_change"),
            {
                "old_password": "senha-antiga-123",
                "new_password1": "senha-nova-789",
                "new_password2": "senha-nova-789",
            },
        )
        self.assertRedirects(response, reverse("password_change_done"))
        user.refresh_from_db()
        self.assertTrue(user.check_password("senha-nova-789"))

    def test_usuario_anonimo_e_redirecionado_ao_login(self):
        response = self.client.get(reverse("password_change"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('password_change')}")


class LogAuditoriaTests(TestCase):
    def test_log_e_somente_leitura_no_admin(self):
        admin = User.objects.create_superuser("admin", password="senha-teste-123")
        LogAuditoria.objects.create(usuario=admin, acao="teste", objeto="Objeto Teste")
        self.client.force_login(admin)
        response = self.client.get(reverse("admin:usuarios_logauditoria_add"))
        # has_add_permission=False -> o Admin redireciona/nega em vez de mostrar o form
        self.assertNotEqual(response.status_code, 200)


class RateLimitingLoginTests(TestCase):
    """django-axes: AXES_FAILURE_LIMIT=5, AXES_COOLOFF_TIME=1h30."""

    def test_bloqueia_apos_5_tentativas_erradas_mesmo_com_senha_certa_depois(self):
        User.objects.create_user("travauser", password="senha-correta-123")
        for _ in range(5):
            self.client.post(reverse("login"), {"username": "travauser", "password": "senha-errada"})
        response = self.client.post(
            reverse("login"), {"username": "travauser", "password": "senha-correta-123"}
        )
        self.assertEqual(response.status_code, 429)
        self.assertContains(response, "bloqueado", status_code=429)

    def test_login_correto_antes_do_limite_reseta_o_contador(self):
        User.objects.create_user("resetuser", password="senha-correta-123")
        for _ in range(3):
            self.client.post(reverse("login"), {"username": "resetuser", "password": "senha-errada"})

        response = self.client.post(
            reverse("login"), {"username": "resetuser", "password": "senha-correta-123"}
        )
        self.assertEqual(response.status_code, 302)  # login OK, contador reseta (AXES_RESET_ON_SUCCESS)
        self.client.logout()

        for _ in range(3):  # abaixo do limite de novo, já que resetou
            self.client.post(reverse("login"), {"username": "resetuser", "password": "senha-errada"})
        response = self.client.post(
            reverse("login"), {"username": "resetuser", "password": "senha-correta-123"}
        )
        self.assertEqual(response.status_code, 302)  # ainda consegue logar


class LimparLogAuditoriaCommandTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser("admin.retencao", password="senha-teste-123")

    def _criar_log_com_idade(self, dias, objeto):
        log = LogAuditoria.objects.create(usuario=self.user, acao="teste", objeto=objeto)
        LogAuditoria.objects.filter(pk=log.pk).update(data_hora=timezone.now() - timedelta(days=dias))

    def test_apaga_so_registros_mais_antigos_que_a_retencao(self):
        self._criar_log_com_idade(400, "antigo")
        self._criar_log_com_idade(1, "recente")

        call_command("limpar_log_auditoria")

        self.assertEqual(LogAuditoria.objects.count(), 1)
        self.assertEqual(LogAuditoria.objects.get().objeto, "recente")

    def test_dry_run_nao_apaga_nada(self):
        self._criar_log_com_idade(400, "antigo")
        call_command("limpar_log_auditoria", "--dry-run")
        self.assertEqual(LogAuditoria.objects.count(), 1)

    def test_parametro_dias_sobrescreve_a_retencao_padrao(self):
        self._criar_log_com_idade(10, "dez-dias")
        call_command("limpar_log_auditoria", "--dias", "5")
        self.assertEqual(LogAuditoria.objects.count(), 0)


class LimparLogAuditoriaViewTests(TestCase):
    """Endpoint chamado pela Vercel Cron — protegido por CRON_SECRET."""

    @override_settings(CRON_SECRET="segredo-teste")
    def test_sem_cabecalho_de_autorizacao_e_negado(self):
        response = self.client.get(reverse("limpar_log_auditoria"))
        self.assertEqual(response.status_code, 403)

    @override_settings(CRON_SECRET="segredo-teste")
    def test_com_segredo_correto_roda_a_limpeza(self):
        response = self.client.get(
            reverse("limpar_log_auditoria"), headers={"authorization": "Bearer segredo-teste"}
        )
        self.assertEqual(response.status_code, 200)

    @override_settings(CRON_SECRET=None)
    def test_sem_cron_secret_configurado_fica_desativado(self):
        response = self.client.get(reverse("limpar_log_auditoria"))
        self.assertEqual(response.status_code, 503)
