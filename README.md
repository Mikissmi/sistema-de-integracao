# Acompanhamento Intersetorial — Educação e Saúde (Nova Santa Rita)

Sistema web para acompanhamento dos estudantes encaminhados pela rede escolar aos serviços de saúde, substituindo o modelo de planilhas por unidade escolar. Ver o planejamento completo em [`docs/planejamento-acompanhamento-intersetorial.md`](docs/planejamento-acompanhamento-intersetorial.md).

Stack: Python + Django 5, Postgres (Neon) em produção / SQLite em desenvolvimento, hospedagem na Vercel.

## Rodando localmente

```bash
pip install -r requirements.txt
cp .env.example .env   # ajuste se necessário
python3 manage.py migrate
python3 manage.py seed_escolas             # cadastra as 21 escolas e os grupos de perfil
python3 manage.py seed_tipos_atendimento   # cadastra tipos de atendimento comuns (Psicologia, Nutrição...)
python3 manage.py createsuperuser          # usuário administrador
python3 manage.py runserver
```

`requirements.txt` é um lockfile (versões exatas + hashes, gerado com
[pip-tools](https://pip-tools.readthedocs.io/)) — não edite esse arquivo à
mão. Para adicionar/atualizar uma dependência, edite `requirements.in` e
rode:
```bash
pip install pip-tools
pip-compile --generate-hashes -o requirements.txt requirements.in
```

Acesse `http://localhost:8000/` (login) e `http://localhost:8000/admin/` (administração completa).

Após criar usuários (`/admin/auth/user/`), vincule o **Perfil de Usuário** (Educação/Saúde/Gestão) e, se for perfil Educação, a escola correspondente — isso é o que restringe cada usuário aos registros da própria unidade/território. **Um usuário sem Perfil de Usuário vinculado não vê nenhum registro** (exceto superusuários, que sempre veem tudo) — não esqueça esse passo ao criar uma conta nova.

### Rodando os testes automatizados

```bash
python3 manage.py test
```

## Como adicionar uma nova escola

Não precisa mexer em código nem em migração — é um cadastro comum:

1. Acesse `/admin/escolas/escola/add/`
2. Preencha **Nome** e **Tipo** (Municipal EF, Municipal EI, Estadual ou Educação Especial)
3. Salve

A escola aparece imediatamente nos formulários de cadastro de estudante e nos filtros do painel/lista de casos.

## Como adicionar um novo Território/ESF

Também é só um cadastro pelo admin, sem alterar código:

1. Acesse `/admin/territorios/territorio/add/`
2. Preencha o **Nome** (ex.: "ESF Centro", "ESF Nova Santa Rita II")
3. Salve

O território passa a ficar disponível para selecionar no cadastro do estudante e no perfil dos profissionais de Saúde. Por isso o território é um cadastro (e não um campo de texto livre): assim o nome usado no perfil do profissional é sempre idêntico ao usado no cadastro do estudante, evitando que um erro de digitação faça alguém deixar de ver os casos do próprio território.

## Como adicionar um novo Tipo de Atendimento (Psicólogo, Nutricionista, etc.)

Mesma lógica de Escola e Território — cadastro pelo admin, sem editar código:

1. Acesse `/admin/atendimentos/tipoatendimento/add/`
2. Preencha o **Nome** (ex.: "Psicologia", "Nutrição", "Fonoaudiologia")
3. Salve

O comando `seed_tipos_atendimento` já cadastra uma lista inicial (Psicologia, Nutrição, Fonoaudiologia, Psiquiatria Infantil, Terapia Ocupacional, Neurologia Pediátrica, Assistência Social, Fisioterapia, Odontologia, Pediatria/Clínica Geral) — edite, renomeie ou desative pelo admin conforme a realidade do município.

## Quem vê o quê (escopo por perfil)

Isso já funciona em **todas** as páginas (painel, lista de casos, cadastro), não é uma tela separada:

- **Educação**: só vê estudantes/casos da escola vinculada ao seu perfil — inclusive ao **cadastrar** um novo estudante, o campo Escola fica travado na escola do próprio perfil (não é possível cadastrar em outra escola trocando a opção do formulário). Acesso direto a um registro de outra escola retorna "não encontrado".
- **Saúde com Território/ESF definido no perfil**: só vê os casos de estudantes daquele território — não vê os de outros territórios (mesma trava no cadastro).
- **Saúde sem Território/ESF definido** (perfil em branco): vê os casos de todas as escolas/territórios — para o profissional que acompanha a rede toda.
- **Gestão Municipal** e superusuário: veem tudo, sem restrição.
- **Usuário autenticado sem Perfil de Usuário vinculado**: não vê nada — um cadastro de usuário incompleto nunca deve equivaler a acesso total.

O vínculo é feito em `/admin/auth/user/<id>/` → seção **Perfil de Usuário**.

## Recuperação e troca de senha

Qualquer usuário pode redefinir a própria senha por e-mail em `/password_reset/`
(link "Esqueci minha senha" na tela de login), e trocar a senha estando logado em
`/trocar-senha/` (link no menu superior). Isso depende de `EMAIL_HOST` estar
configurado (ver `.env.example`) — funciona com qualquer provedor SMTP. Em
desenvolvimento (`DEBUG=True`) sem `EMAIL_HOST`, os e-mails aparecem no console
em vez de serem enviados de verdade, então dá para testar o fluxo sem ter conta
em nenhum provedor.

Depois de 5 tentativas de senha erradas para o mesmo usuário (`django-axes`), o
login fica bloqueado por 1h30 — vale para contas de teste também.

## Importando estudantes em lote (CSV)

Em vez de cadastrar um por um, uma escola pode importar vários estudantes de
uma vez em `/estudantes/importar/` (link na listagem de Estudantes),
enviando um `.csv` com as colunas `nome, cpf, data_nascimento,
nome_responsavel, telefone, ano_turma, territorio_esf` — tem um modelo para
baixar na própria tela. Aceita separador `,` ou `;` e arquivos em UTF-8 ou
`cp1252`/`latin-1` (cobre o CSV que o Excel em português costuma gerar).

Cada linha é validada com as mesmas regras do cadastro manual (CPF, telefone,
duplicidade). Uma linha com erro não cancela o arquivo inteiro — ela é pulada
e reportada, com o motivo, ao final da importação. Limite: 2MB e 500 linhas
por arquivo.

## Gravidade do caso

Cada encaminhamento tem um campo **Gravidade** (Baixa/Média/Alta/Urgente), definido pelo profissional no cadastro ou na edição do caso — é uma prioridade clínica/administrativa, independente do cálculo automático de atraso (**Nível de Alerta**, que é sobre tempo de espera). Os dois aparecem lado a lado na tela do caso, e o painel mostra a contagem de casos Altos/Urgentes em aberto.

A **Situação** do caso (Aguardando → Em Acompanhamento → Encerrado) pode ser atualizada direto na tela do caso, sem precisar do Django Admin.

## Estrutura

- `escolas/` — cadastro das unidades escolares
- `territorios/` — cadastro dos Territórios/ESF
- `atendimentos/` — cadastro dos tipos de atendimento (Psicologia, Nutrição, etc.)
- `usuarios/` — perfis de acesso (Educação/Saúde/Gestão), escopo de permissões e log de auditoria
- `estudantes/` — cadastro único do estudante (CPF criptografado em repouso)
- `casos/` — encaminhamentos e evoluções (histórico cronológico, gravidade)
- `indicadores/` — painel de indicadores da gestão
- `api/index.py` — entrypoint WSGI usado pela Vercel

Todo o código (nomes de campos, funções, telas e mensagens) está em português. Os únicos termos em inglês são convenções do próprio framework Django (nomes de arquivo como `models.py`, `views.py`, `admin.py`, `urls.py`, `forms.py` — mantidos assim de propósito, pois é como a documentação e os tutoriais de Django em português também os chamam).

## Deploy na Vercel

1. Importe o repositório em vercel.com/new.
2. Na aba **Storage**, provisione um banco **Neon Postgres** — a variável `DATABASE_URL` é injetada automaticamente.
3. Configure as demais variáveis de ambiente do projeto (ver `.env.example`): `SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS` (domínio da Vercel), `FIELD_ENCRYPTION_KEY` (gere uma chave nova e mantenha em segredo — **nunca reutilize um valor de exemplo**) e `EMAIL_HOST`/`EMAIL_HOST_USER`/`EMAIL_HOST_PASSWORD` (provedor SMTP para recuperação de senha). Sem `DEBUG=False` a aplicação **recusa subir** faltando qualquer uma dessas variáveis — é proposital: melhor um deploy que não sobe do que um rodando com chave insegura, sem e-mail funcional, ou perdendo dados no SQLite local. Configure também `CRON_SECRET` (ver seção de retenção do log abaixo) — sem ele a aplicação sobe normalmente, mas a limpeza agendada do log de auditoria fica desativada.
4. Rode as migrações apontando para o banco de produção (uma vez, localmente ou via pipeline):
   ```bash
   DATABASE_URL="<url do Neon>" python3 manage.py migrate
   DATABASE_URL="<url do Neon>" python3 manage.py seed_escolas
   DATABASE_URL="<url do Neon>" python3 manage.py seed_tipos_atendimento
   DATABASE_URL="<url do Neon>" python3 manage.py createsuperuser
   ```
5. Gere os arquivos estáticos antes do deploy (a Vercel não roda `collectstatic` automaticamente para o runtime Python):
   ```bash
   python3 manage.py collectstatic --noinput
   ```
   e garanta que a pasta `staticfiles/` esteja incluída no deploy (referenciada em `vercel.json`).
6. **Uploads de PDF:** a Vercel não tem disco persistente. Antes de ir para produção, configure `django-storages` com Vercel Blob (ou S3) para o campo `anexo_encaminhamento` — em desenvolvimento os arquivos ficam em `media/` local.
7. **Retenção do log de auditoria:** `vercel.json` já registra uma Vercel Cron semanal chamando `/tasks/limpar-log-auditoria/`, que apaga registros de `LogAuditoria` mais antigos que `RETENCAO_LOG_AUDITORIA_DIAS` (padrão 365 dias). Só funciona com `CRON_SECRET` configurado (passo 3). Pode rodar manualmente a qualquer momento com `python3 manage.py limpar_log_auditoria` (ou `--dry-run` para só ver quantos registros seriam apagados).
8. Push no branch conectado à Vercel para disparar o deploy automático.

**Pendência conhecida antes de vender/operar em produção com dados reais** (ver `CHANGELOG.md` para o histórico completo de correções já aplicadas):
- Armazenamento externo dos anexos em PDF (item 6 acima) ainda não está implementado em código — adiado por decisão explícita, upload continua indisponível de forma persistente em produção até isso ser resolvido.

Detalhes completos de arquitetura, modelo de dados, regras de alerta e considerações de LGPD estão no documento de planejamento. Um rascunho de política de privacidade/termo de tratamento de dados (precisa revisão jurídica antes de uso real) está em [`docs/politica-privacidade-tratamento-dados.md`](docs/politica-privacidade-tratamento-dados.md).
