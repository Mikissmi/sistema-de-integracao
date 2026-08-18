# Changelog

Histórico de mudanças do sistema, documentado para acompanhar a preparação do
produto para venda. Cada entrada referencia o achado da auditoria técnica que
originou a mudança (quando aplicável) e o(s) arquivo(s) afetado(s).

## [Não lançado] — 18/08/2026 — Itens opcionais da auditoria + importação por CSV

Implementa os itens "opcionais" da auditoria que a usuária decidiu priorizar
agora (deixando CI, Sentry e favicon/identidade para depois), mais uma
funcionalidade nova pedida na conversa: importação de estudantes em lote por
CSV, por escola.

### ⚠️ Mudança de comportamento (leia antes de fazer deploy)

- **A chave de cifra do CPF e a chave do hash de busca deixaram de ser a
  mesma.** `estudantes/fields.py` agora deriva duas subchaves de
  `FIELD_ENCRYPTION_KEY` via HKDF (uma para Fernet, outra para o HMAC). Isso
  muda os bytes reais usados para cifrar/decifrar — **CPFs já criptografados
  com o esquema antigo (chave crua) ficariam ilegíveis** depois desta
  mudança. Só é seguro aplicar isso porque, até onde sabemos, **não existe
  dado real em produção ainda**. Se este código for aplicado sobre um banco
  com CPFs reais já cadastrados, é preciso migrar os dados antes (decifrar
  com o esquema antigo, recifrar com o novo) — não faça esse deploy sem
  confirmar isso primeiro.
- **Login agora tem limite de tentativas**: 5 tentativas erradas para a
  combinação usuário+IP bloqueiam o acesso por 1h30 (`django-axes`). Isso
  vale também para contas de teste/desenvolvimento — se você errar a senha
  repetidamente testando, vai se bloquear igual a um usuário real.
- **Nova dependência de banco**: `django-axes` traz suas próprias tabelas
  (tentativas de login). Rode `manage.py migrate` depois de atualizar.

### 🔴 Segurança

| Mudança | Arquivos |
|---|---|
| Rate limiting no login: 5 tentativas erradas (usuário+IP) → bloqueio de 1h30, com tela de bloqueio no estilo do projeto | `config/settings.py`, `templates/registration/bloqueado.html` (novo) |
| `|safe` trocado por `{% json_script %}` nos dados do gráfico do painel — fechava uma brecha de XSS de baixo risco (nome de escola cadastrado no Admin com `</script>` no meio) | `indicadores/views.py`, `templates/indicadores/painel.html` |
| Chave de cifra (Fernet) e de hash de busca (HMAC) do CPF derivadas separadamente via HKDF, em vez de reaproveitar a mesma `FIELD_ENCRYPTION_KEY` crua para os dois propósitos | `estudantes/fields.py` |
| Fallback silencioso de "token inválido" ao decifrar CPF agora gera um aviso no log, em vez de mascarar o problema sem registro | `estudantes/fields.py` |

### 🟢 Operação / produção

| Mudança | Arquivos |
|---|---|
| Lockfile de dependências (versões exatas + hashes, via pip-tools) — builds reprodutíveis | `requirements.in` (novo), `requirements.txt` |
| Retenção do log de auditoria: comando `limpar_log_auditoria` (apaga registros mais antigos que `RETENCAO_LOG_AUDITORIA_DIAS`, padrão 365 dias, com `--dry-run`) + endpoint protegido por `CRON_SECRET` + agendamento semanal via Vercel Cron | `usuarios/management/commands/limpar_log_auditoria.py` (novo), `usuarios/views.py`, `config/urls.py`, `vercel.json` |
| Rascunho de política de privacidade / termo de tratamento de dados (LGPD/ECA) — documento, precisa revisão jurídica antes de uso contratual real | `docs/politica-privacidade-tratamento-dados.md` (novo) |

### 🟠 Funcionalidade nova: importação de estudantes por CSV

| Mudança | Arquivos |
|---|---|
| Upload de um `.csv` com vários estudantes de uma vez, associados a uma única escola escolhida no formulário (trava pra própria escola em perfil Educação, igual ao cadastro manual) | `estudantes/importacao.py` (novo), `estudantes/forms.py`, `estudantes/views.py`, `estudantes/urls.py` |
| Processamento linha a linha: uma linha com erro (CPF inválido/duplicado, território não encontrado, data inválida) é pulada e reportada com o motivo — não derruba o restante do lote. Reaproveita o `EstudanteForm` (mesma validação do cadastro manual, não um caminho paralelo) | `estudantes/importacao.py` |
| Aceita `,` ou `;` como separador e detecta automaticamente UTF-8 ou `cp1252`/`latin-1` — cobre o caso comum de CSV exportado do Excel em português/Windows | `estudantes/importacao.py` |
| Limite de 2MB e 500 linhas por arquivo (timeout de função na Vercel) | `estudantes/importacao.py`, `estudantes/forms.py` |
| Modelo de CSV para download, link a partir da listagem de estudantes, tela de resultado com contagem de sucesso/erro por linha | `estudantes/views.py`, `templates/estudantes/importar.html`, `templates/estudantes/importar_resultado.html` (novos) |

### ✅ Testes automatizados

24 testes novos: HKDF (subchaves diferentes, cifrar/decifrar continua funcionando), rate limiting (bloqueio na 5ª tentativa, reset do contador após login correto), retenção do log (apaga só o antigo, `--dry-run`, `--dias`), endpoint do cron (nega sem segredo, roda com segredo, desativado sem `CRON_SECRET`), e a importação CSV (linhas válidas/inválidas misturadas, CPF duplicado dentro do próprio arquivo e já existente no banco, separador `;` + `cp1252`, coluna faltando, data inválida, escola travada por perfil, arquivo que não é CSV, modelo para download).

## [Não lançado] — 16/08/2026 — Recuperação e troca de senha por e-mail

Resolve a primeira das duas pendências deixadas na rodada anterior (a outra,
storage de PDF, segue adiada por decisão explícita — ver "Pendências" abaixo).

| Mudança | Arquivos |
|---|---|
| Configuração de e-mail genérica via SMTP (funciona com qualquer provedor — Gmail, SendGrid, Resend, AWS SES etc. — trocando só variáveis de ambiente); em `DEBUG=True` sem `EMAIL_HOST`, cai para o backend de console, sem exigir provedor real para testar localmente; obrigatória em produção (mesma lógica de fail-loud das outras chaves) | `config/settings.py` |
| `PASSWORD_RESET_TIMEOUT` reduzido para 24h (padrão do Django é 3 dias) — mais adequado a um sistema com dado sensível de crianças/adolescentes | `config/settings.py` |
| Rotas de recuperação (`/password_reset/...`) e troca de senha logada (`/trocar-senha/`) usando as views prontas do `django.contrib.auth`, com forms e templates no estilo Bootstrap já usado no resto do projeto | `config/urls.py`, `usuarios/forms.py`, `templates/registration/*.html` (novos) |
| Link "Esqueci minha senha" na tela de login; link "Trocar senha" na navbar para usuários logados | `templates/registration/login.html`, `templates/base.html` |
| E-mail de recuperação não revela se o endereço tem conta cadastrada (mesma resposta genérica nos dois casos) — evita enumeração de usuários | `templates/registration/password_reset_done.html` |
| 5 testes novos: fluxo completo de recuperação (solicitar → e-mail → link → nova senha → login), e-mail não cadastrado não vaza informação, link inválido/expirado rejeitado, troca de senha logada, acesso anônimo redireciona ao login | `usuarios/tests.py` |

## [Não lançado] — 15/08/2026 — Rodada de correções pós-auditoria

Esta rodada implementa todos os itens classificados como **crítico**, **fazer
antes da venda** e **recomendado** na auditoria técnica, com exceção de dois
itens adiados por decisão explícita (ver "Pendências" no fim deste arquivo).

### ⚠️ Mudança de comportamento (leia antes de fazer deploy)

- **Permissões agora são fail-closed.** Um usuário autenticado **sem** Perfil
  de Usuário vinculado deixou de enxergar todos os dados do município (antes
  equivalia a "Gestão") e passou a não ver **nenhum** registro. Superusuários
  continuam vendo tudo, com ou sem perfil. Se houver alguma conta de uso
  interno sem perfil configurado, ela vai parar de ver dados até que um
  Perfil de Usuário seja vinculado em `/admin/auth/user/<id>/`.
- **`DEBUG` agora tem default `False`, e `SECRET_KEY`/`FIELD_ENCRYPTION_KEY`
  não têm mais fallback funcional em produção.** Se alguma dessas variáveis
  faltar com `DEBUG=False`, a aplicação **recusa subir** (erro claro no boot,
  em vez de rodar insegura ou com uma chave pública). Local/dev não é afetado
  na prática, desde que o `.env` esteja configurado (ver próximo item).
- **`.env` agora é carregado de verdade.** O projeto instruía `cp .env.example
  .env`, mas nada lia esse arquivo — funcionava por acaso porque `DEBUG` tinha
  default `True`. Adicionado `python-dotenv` para isso realmente funcionar.
- **Telefone agora é armazenado só com dígitos** (ex.: `51999998888`, sem
  máscara) — a exibição usa a nova propriedade `telefone_formatado`. Se
  algum uso futuro (relatório, integração) ler `estudante.telefone`
  diretamente do banco, vai receber a versão sem máscara.

### 🔴 Segurança

| Mudança | Achado | Arquivos |
|---|---|---|
| Removido fallback hardcoded de `FIELD_ENCRYPTION_KEY` — obrigatória em produção, gerada automaticamente (efêmera) em dev | #1 | `config/settings.py` |
| Removido fallback hardcoded de `SECRET_KEY` em produção | #12 | `config/settings.py` |
| `DEBUG` agora tem default seguro (`False`) | #7 | `config/settings.py` |
| Aplicação recusa subir em produção sem `DATABASE_URL` (evita SQLite silencioso em ambiente serverless efêmero) | #8 | `config/settings.py` |
| Adicionado `SECURE_HSTS_SECONDS` (começa em 1h, com instrução para subir gradualmente) | — | `config/settings.py` |
| `IntegrityError` de CPF duplicado tratado com mensagem de formulário, não mais erro 500 cru | #5 | `estudantes/views.py` |
| Corrigido fail-open em `escopo_casos`/`escopo_estudantes`: perfil ausente agora nega acesso em vez de conceder | #6 | `usuarios/permissions.py` |
| Cadastro de estudante trava Escola/Território ao escopo do usuário logado (campo `disabled`, o servidor ignora valor manipulado no POST) | #3 | `estudantes/forms.py` |
| Upload de anexo restrito a `.pdf` (`FileExtensionValidator`) | #16 | `casos/models.py` |
| Botão "Sair" corrigido para POST (o Django 5 não aceita mais GET no `LogoutView`) | #10 | `templates/base.html` |

### 🟡 Validação de dados (CPF, telefone)

| Mudança | Achado | Arquivos |
|---|---|---|
| Validação matemática completa de CPF (dígitos verificadores, módulo 11, rejeita sequência repetida) | #2 | `estudantes/validators.py` (novo) |
| `hash_cpf()` normaliza antes de gerar o hash — CPF com/sem máscara não escapa mais da checagem de duplicidade | #4 | `estudantes/fields.py` |
| `Estudante.save()` normaliza CPF e telefone (só dígitos) antes de gravar, independente da origem (form ou Admin) | #4 | `estudantes/models.py` |
| `EstudanteForm.clean_cpf` valida e checa duplicidade antes do submit; `validators=[validar_cpf]` no model como defesa em profundidade (cobre edição via Admin) | #2, #3 | `estudantes/models.py`, `estudantes/forms.py` |
| Validação de telefone (DDD + 8/9 dígitos), mesma abordagem form + model | #13 | `estudantes/validators.py`, `estudantes/models.py`, `estudantes/forms.py` |
| `maxlength` do campo CPF no formulário corrigido de 400 (tamanho do texto cifrado) para 14 (tamanho de um CPF mascarado) | — | `estudantes/forms.py` |

### 🟠 Funcionalidade / UX

| Mudança | Achado | Arquivos |
|---|---|---|
| Mensagens de sucesso/erro (`django.contrib.messages`) em cadastro de estudante, criação de caso, evolução e mudança de situação | #20 | `estudantes/views.py`, `casos/views.py` |
| Paginação (25 itens/página) nas listagens de Estudantes e Casos | #19 | `estudantes/views.py`, `casos/views.py`, `templates/_paginacao.html` (novo) |
| Nova tela/rota para mudar a **situação** de um caso (Aguardando → Em Acompanhamento → Encerrado) sem depender do Django Admin | #26 | `casos/forms.py`, `casos/views.py`, `casos/urls.py`, `templates/casos/detalhe.html` |
| Páginas 404 e 500 customizadas (500 é standalone de propósito — não depende de context processors) | #25 | `templates/404.html`, `templates/500.html` (novos) |

### 🟢 Performance

| Mudança | Achado | Arquivos |
|---|---|---|
| `nivel_alerta`/`dias_sem_retorno`/`data_referencia_alerta` viraram `@cached_property` e passaram a reaproveitar `prefetch_related("evolucoes")` em vez de disparar uma query por caso | #17 | `casos/models.py`, `casos/views.py`, `estudantes/views.py`, `indicadores/views.py` |
| Índices adicionados em `Caso.situacao`, `Caso.gravidade` (filtrados a cada listagem) e `LogAuditoria` (`usuario`, `-data_hora`) | #18 | `casos/models.py`, `usuarios/models.py` |

### 🟢 Acessibilidade / Responsividade

| Mudança | Achado | Arquivos |
|---|---|---|
| Tabelas envolvidas em `.table-responsive` (Casos, Estudantes) | #23 | `templates/casos/lista.html`, `templates/estudantes/lista.html`, `templates/estudantes/detalhe.html` |
| Linhas de tabela navegáveis só por `onclick` trocadas por links reais (`<a>`), operáveis por teclado/leitor de tela | #24 | `templates/casos/lista.html`, `templates/estudantes/lista.html` |
| `<label for="...">` associado corretamente aos campos em todos os formulários | #27, #28 | `templates/estudantes/form.html`, `templates/casos/form.html`, `templates/casos/detalhe.html`, `templates/estudantes/buscar.html` |

### ✅ Testes automatizados

37 testes novos cobrindo especificamente as regressões dos achados críticos/altos:
validação de CPF (dígitos verificadores, normalização, duplicidade mesmo com
formatação diferente), validação de telefone, escopo fail-closed sem perfil,
trava de escola/território no cadastro, cálculo de nível de alerta, view de
atualizar situação (dentro/fora do escopo) e o comportamento do logout via
POST. Ver `estudantes/tests.py`, `casos/tests.py`, `usuarios/tests.py`.

### Outras mudanças

- Adicionado `python-dotenv` ao `requirements.txt` (necessário para o `.env`
  ser carregado de verdade — ver "Mudança de comportamento" acima).
- `.env.example`: `FIELD_ENCRYPTION_KEY` deixou de trazer um valor funcional
  (era o mesmo hardcoded em `settings.py` — o problema #1 em si).
- `README.md` atualizado: instruções de teste, comportamento fail-closed,
  variáveis obrigatórias em produção, mudança de situação do caso pela UI.

## Pendências (adiadas por decisão explícita)

- **Armazenamento externo dos anexos em PDF** (Vercel Blob ou S3 via
  `django-storages`). Sem isso, anexos enviados em produção na Vercel não
  sobrevivem (disco efêmero) — problema já documentado no `settings.py` e no
  README, ainda não resolvido em código a pedido explícito (foco priorizado
  em recuperação de senha nesta rodada).

## Itens conscientemente fora de escopo (por decisão explícita)

- **CI** (GitHub Actions rodando os testes a cada push) — não pedido nesta rodada.
- **Monitoramento de erro** (Sentry ou similar) — não pedido nesta rodada.
- **Favicon e identidade visual própria** (hoje é Bootstrap padrão) — decisão adiada para mais pra frente.
