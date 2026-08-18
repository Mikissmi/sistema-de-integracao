from io import BytesIO

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from escolas.models import Escola
from territorios.models import Territorio
from usuarios.models import PerfilUsuario
from usuarios.permissions import escopo_estudantes

from .fields import _derive_key, _fernet, hash_cpf
from .forms import EstudanteForm
from .importacao import processar_csv
from .models import Estudante
from .validators import normalizar_cpf, normalizar_telefone, validar_cpf, validar_telefone

CPF_VALIDO = "111.444.777-35"  # CPF de teste matematicamente válido (uso padrão de mercado)


class ValidarCPFTests(TestCase):
    def test_aceita_cpf_valido_com_ou_sem_mascara(self):
        validar_cpf(CPF_VALIDO)
        validar_cpf("11144477735")
        validar_cpf("  111.444.777-35  ")

    def test_rejeita_digito_verificador_incorreto(self):
        with self.assertRaises(ValidationError):
            validar_cpf("111.444.777-30")

    def test_rejeita_sequencia_repetida(self):
        with self.assertRaises(ValidationError):
            validar_cpf("000.000.000-00")
        with self.assertRaises(ValidationError):
            validar_cpf("11111111111")

    def test_rejeita_quantidade_incorreta_de_digitos(self):
        with self.assertRaises(ValidationError):
            validar_cpf("123456")

    def test_rejeita_caracteres_nao_numericos(self):
        with self.assertRaises(ValidationError):
            validar_cpf("abc.def.ghi-jk")

    def test_normalizar_cpf_remove_mascara_e_espacos(self):
        self.assertEqual(normalizar_cpf(" 111.444.777-35 "), "11144477735")


class HashCPFTests(TestCase):
    def test_mesmo_cpf_com_formatacao_diferente_gera_o_mesmo_hash(self):
        """Regressão: antes da normalização, '111.444.777-35' e '11144477735'
        geravam hashes diferentes e burlavam a checagem de duplicidade."""
        self.assertEqual(hash_cpf("111.444.777-35"), hash_cpf("11144477735"))
        self.assertEqual(hash_cpf(" 111.444.777-35 "), hash_cpf("11144477735"))


class HKDFTests(TestCase):
    """Achado #31 da auditoria: a mesma FIELD_ENCRYPTION_KEY não deve ser
    usada crua tanto para cifrar (Fernet) quanto para o HMAC de busca."""

    def test_subchaves_de_fernet_e_hmac_sao_diferentes(self):
        chave_fernet = _derive_key(b"cpf-fernet-encryption-v1")
        chave_hmac = _derive_key(b"cpf-search-hmac-v1")
        self.assertNotEqual(chave_fernet, chave_hmac)

    def test_cifrar_e_decifrar_ainda_funciona_com_chave_derivada(self):
        token = _fernet().encrypt(b"11144477735")
        self.assertEqual(_fernet().decrypt(token), b"11144477735")


class ValidarTelefoneTests(TestCase):
    def test_aceita_fixo_e_celular_com_ou_sem_mascara(self):
        validar_telefone("(51) 99999-8888")
        validar_telefone("51999998888")
        validar_telefone("5133334444")

    def test_rejeita_quantidade_incorreta_de_digitos(self):
        with self.assertRaises(ValidationError):
            validar_telefone("123")
        with self.assertRaises(ValidationError):
            validar_telefone("519999988899")

    def test_normalizar_telefone_remove_codigo_do_pais(self):
        self.assertEqual(normalizar_telefone("+55 51 99999-8888"), "51999998888")


class EstudanteModelTests(TestCase):
    def setUp(self):
        self.escola = Escola.objects.create(nome="Escola Teste")
        self.territorio = Territorio.objects.create(nome="ESF Teste")

    def _criar_estudante(self, cpf, telefone="(51) 99999-8888"):
        return Estudante.objects.create(
            nome="Criança Teste",
            cpf=cpf,
            data_nascimento="2015-01-01",
            nome_responsavel="Responsável Teste",
            telefone=telefone,
            escola=self.escola,
            ano_turma="3º ano",
            territorio_esf=self.territorio,
        )

    def test_save_normaliza_cpf_e_telefone(self):
        estudante = self._criar_estudante(CPF_VALIDO)
        estudante.refresh_from_db()
        self.assertEqual(estudante.cpf, "11144477735")
        self.assertEqual(estudante.telefone, "51999998888")

    def test_buscar_por_cpf_encontra_independente_da_formatacao_usada(self):
        self._criar_estudante(CPF_VALIDO)
        self.assertIsNotNone(Estudante.buscar_por_cpf("11144477735"))
        self.assertIsNotNone(Estudante.buscar_por_cpf("111.444.777-35"))

    def test_cpf_mascarado_nao_expoe_cpf_completo(self):
        estudante = self._criar_estudante(CPF_VALIDO)
        self.assertEqual(estudante.cpf_mascarado, "111.***.***-35")

    def test_telefone_formatado_para_exibicao(self):
        estudante = self._criar_estudante(CPF_VALIDO, telefone="51999998888")
        self.assertEqual(estudante.telefone_formatado, "(51) 99999-8888")


class EstudanteFormTests(TestCase):
    def setUp(self):
        self.escola_a = Escola.objects.create(nome="Escola A")
        self.escola_b = Escola.objects.create(nome="Escola B")
        self.territorio = Territorio.objects.create(nome="ESF Teste")

    def _dados_validos(self, escola):
        return {
            "nome": "Criança Teste",
            "cpf": CPF_VALIDO,
            "data_nascimento": "2015-01-01",
            "nome_responsavel": "Responsável Teste",
            "telefone": "51999998888",
            "escola": escola.pk,
            "ano_turma": "3º ano",
            "territorio_esf": self.territorio.pk,
        }

    def test_formulario_valido_normaliza_cpf(self):
        form = EstudanteForm(data=self._dados_validos(self.escola_a))
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["cpf"], "11144477735")

    def test_rejeita_cpf_matematicamente_invalido(self):
        dados = self._dados_validos(self.escola_a)
        dados["cpf"] = "111.444.777-30"
        form = EstudanteForm(data=dados)
        self.assertFalse(form.is_valid())
        self.assertIn("cpf", form.errors)

    def test_rejeita_cpf_duplicado_mesmo_com_formatacao_diferente(self):
        Estudante.objects.create(
            nome="Já cadastrado",
            cpf=CPF_VALIDO,
            data_nascimento="2015-01-01",
            nome_responsavel="Responsável",
            telefone="51999998888",
            escola=self.escola_a,
            ano_turma="3º ano",
            territorio_esf=self.territorio,
        )
        dados = self._dados_validos(self.escola_a)
        dados["cpf"] = "11144477735"  # mesmo CPF, sem máscara
        form = EstudanteForm(data=dados)
        self.assertFalse(form.is_valid())
        self.assertIn("cpf", form.errors)

    def test_rejeita_telefone_invalido(self):
        dados = self._dados_validos(self.escola_a)
        dados["telefone"] = "123"
        form = EstudanteForm(data=dados)
        self.assertFalse(form.is_valid())
        self.assertIn("telefone", form.errors)

    def test_usuario_perfil_educacao_nao_consegue_cadastrar_em_outra_escola(self):
        """Regressão do achado crítico: perfil Educação da Escola A não pode
        atribuir o cadastro à Escola B, mesmo manipulando o valor enviado."""
        user = User.objects.create_user("prof.educacao", password="senha-teste-123")
        PerfilUsuario.objects.create(usuario=user, perfil="educacao", escola=self.escola_a)

        dados = self._dados_validos(self.escola_b)  # tenta submeter a Escola B
        form = EstudanteForm(data=dados, usuario=user)
        self.assertTrue(form.is_valid(), form.errors)
        estudante = form.save()
        self.assertEqual(estudante.escola_id, self.escola_a.pk)  # trava venceu, não a Escola B


class EscopoEstudantesTests(TestCase):
    def setUp(self):
        self.escola_a = Escola.objects.create(nome="Escola A")
        self.escola_b = Escola.objects.create(nome="Escola B")
        self.territorio = Territorio.objects.create(nome="ESF Teste")
        self.estudante_a = Estudante.objects.create(
            nome="Estudante A",
            cpf=CPF_VALIDO,
            data_nascimento="2015-01-01",
            nome_responsavel="Responsável",
            telefone="51999998888",
            escola=self.escola_a,
            ano_turma="3º ano",
            territorio_esf=self.territorio,
        )

    def test_usuario_sem_perfil_nao_ve_nenhum_registro(self):
        """Regressão do fail-open: antes, perfil ausente enxergava tudo."""
        user = User.objects.create_user("sem.perfil", password="senha-teste-123")
        self.assertEqual(escopo_estudantes(user, Estudante.objects.all()).count(), 0)

    def test_superusuario_ve_tudo_mesmo_sem_perfil(self):
        user = User.objects.create_superuser("admin", password="senha-teste-123")
        self.assertEqual(escopo_estudantes(user, Estudante.objects.all()).count(), 1)

    def test_perfil_educacao_ve_so_a_propria_escola(self):
        user = User.objects.create_user("prof.educacao", password="senha-teste-123")
        PerfilUsuario.objects.create(usuario=user, perfil="educacao", escola=self.escola_a)
        resultado = escopo_estudantes(user, Estudante.objects.all())
        self.assertEqual(list(resultado), [self.estudante_a])


class BuscarViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("usuario", password="senha-teste-123")
        self.client.force_login(self.user)

    def test_busca_por_cpf_responde_ok(self):
        response = self.client.get(reverse("estudantes:buscar"), {"cpf": CPF_VALIDO})
        self.assertEqual(response.status_code, 200)


CSV_CABECALHO = "nome,cpf,data_nascimento,nome_responsavel,telefone,ano_turma,territorio_esf\n"


class ProcessarCSVTests(TestCase):
    """Cobre estudantes/importacao.py: processamento linha a linha, sem
    derrubar o lote inteiro por causa de uma linha ruim."""

    def setUp(self):
        self.escola = Escola.objects.create(nome="Escola CSV")
        self.territorio = Territorio.objects.create(nome="ESF Centro")
        self.user = User.objects.create_superuser("admin.csv", password="senha-teste-123")

    def _arquivo(self, conteudo: str, codificacao="utf-8"):
        return BytesIO(conteudo.encode(codificacao))

    def test_importa_linhas_validas_e_reporta_as_invalidas_sem_parar_o_lote(self):
        conteudo = CSV_CABECALHO + (
            "Aluno Um,111.444.777-35,15/03/2015,Resp Um,51999998888,5º ano,ESF Centro\n"
            "CPF Invalido,111.444.777-30,10/01/2016,Resp Dois,51988887777,3º ano,ESF Centro\n"
            "Territorio Errado,529.982.247-25,01/01/2014,Resp Tres,51988887777,4º ano,ESF Inexistente\n"
        )
        importados, erros = processar_csv(self._arquivo(conteudo), self.escola, self.user)
        self.assertEqual(importados, 1)
        self.assertEqual(len(erros), 2)
        self.assertEqual(Estudante.objects.count(), 1)
        self.assertEqual(Estudante.objects.first().escola, self.escola)

    def test_cpf_duplicado_dentro_do_proprio_arquivo_e_pulado_e_reportado(self):
        conteudo = CSV_CABECALHO + (
            "Aluno Um,111.444.777-35,15/03/2015,Resp Um,51999998888,5º ano,ESF Centro\n"
            "Aluno Repetido,111.444.777-35,15/03/2015,Resp Um,51999998888,5º ano,ESF Centro\n"
        )
        importados, erros = processar_csv(self._arquivo(conteudo), self.escola, self.user)
        self.assertEqual(importados, 1)
        self.assertEqual(len(erros), 1)
        self.assertIn("já existe um estudante cadastrado", erros[0]["motivo"].lower())

    def test_cpf_ja_existente_no_banco_e_pulado_e_reportado(self):
        Estudante.objects.create(
            nome="Já existe", cpf=CPF_VALIDO, data_nascimento="2015-01-01",
            nome_responsavel="Resp", telefone="51999998888",
            escola=self.escola, ano_turma="3º ano", territorio_esf=self.territorio,
        )
        conteudo = CSV_CABECALHO + "Outro Nome,111.444.777-35,15/03/2015,Resp,51999998888,5º ano,ESF Centro\n"
        importados, erros = processar_csv(self._arquivo(conteudo), self.escola, self.user)
        self.assertEqual(importados, 0)
        self.assertEqual(len(erros), 1)

    def test_aceita_separador_ponto_e_virgula_e_codificacao_cp1252(self):
        conteudo = (
            "nome;cpf;data_nascimento;nome_responsavel;telefone;ano_turma;territorio_esf\r\n"
            "João Ção;111.444.777-35;15/03/2015;Responsável;51999998888;5º ano;ESF Centro\r\n"
        )
        importados, erros = processar_csv(self._arquivo(conteudo, "cp1252"), self.escola, self.user)
        self.assertEqual(importados, 1)
        self.assertEqual(erros, [])
        self.assertEqual(Estudante.objects.first().nome, "João Ção")

    def test_coluna_faltando_levanta_erro_do_arquivo_inteiro(self):
        conteudo = "nome,cpf,data_nascimento\nFulano,111.444.777-35,15/03/2015\n"
        with self.assertRaises(ValidationError):
            processar_csv(self._arquivo(conteudo), self.escola, self.user)

    def test_data_em_formato_invalido_e_reportada_como_erro_de_linha(self):
        conteudo = CSV_CABECALHO + "Fulano,111.444.777-35,não-é-uma-data,Resp,51999998888,3º ano,ESF Centro\n"
        importados, erros = processar_csv(self._arquivo(conteudo), self.escola, self.user)
        self.assertEqual(importados, 0)
        self.assertEqual(len(erros), 1)
        self.assertIn("data", erros[0]["motivo"].lower())


class ImportarCSVViewTests(TestCase):
    def setUp(self):
        self.escola_a = Escola.objects.create(nome="Escola A")
        self.escola_b = Escola.objects.create(nome="Escola B")
        Territorio.objects.create(nome="ESF Centro")

    def test_perfil_educacao_nao_consegue_importar_para_outra_escola(self):
        """Mesma trava do cadastro manual, agora para o lote inteiro."""
        user = User.objects.create_user("prof.educacao", password="senha-teste-123")
        PerfilUsuario.objects.create(usuario=user, perfil="educacao", escola=self.escola_a)
        self.client.force_login(user)

        conteudo = CSV_CABECALHO + "Aluno,111.444.777-35,15/03/2015,Resp,51999998888,5º ano,ESF Centro\n"
        arquivo = SimpleUploadedFile("alunos.csv", conteudo.encode(), content_type="text/csv")
        response = self.client.post(
            reverse("estudantes:importar_csv"), {"escola": self.escola_b.pk, "arquivo": arquivo}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Estudante.objects.get().escola, self.escola_a)  # travou na escola do perfil

    def test_arquivo_que_nao_e_csv_e_rejeitado(self):
        user = User.objects.create_superuser("admin.csv2", password="senha-teste-123")
        self.client.force_login(user)
        arquivo = SimpleUploadedFile("alunos.txt", b"conteudo qualquer", content_type="text/plain")
        response = self.client.post(
            reverse("estudantes:importar_csv"), {"escola": self.escola_a.pk, "arquivo": arquivo}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "csv")
        self.assertEqual(Estudante.objects.count(), 0)

    def test_modelo_csv_disponivel_para_download(self):
        user = User.objects.create_superuser("admin.csv3", password="senha-teste-123")
        self.client.force_login(user)
        response = self.client.get(reverse("estudantes:modelo_csv"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
