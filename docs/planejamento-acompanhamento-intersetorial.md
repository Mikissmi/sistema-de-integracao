# Planejamento Técnico — Sistema de Acompanhamento Intersetorial (Educação ↔ Saúde)

> Município de Nova Santa Rita. Substitui o modelo de "21 planilhas físicas" por um sistema web único, com banco de dados relacional, mantendo (e melhorando) a separação por escola exigida no documento de solicitação.

## 1. Resumo Executivo

O documento de solicitação pede uma "planilha" por escola para acompanhar encaminhamentos de estudantes da Educação para a Saúde. Uma planilha por unidade (21 arquivos) gera duplicidade, dificulta consolidar indicadores municipais e não escala. A recomendação técnica é construir um **sistema web único** (não 21 arquivos separados) com:

- **1 banco de dados relacional**, com a escola como um campo/relacionamento — cada usuário da Educação só enxerga e edita os registros da sua escola (o resultado prático é idêntico a "ter uma planilha por escola", só que sem duplicar estrutura nem perder a visão consolidada da gestão);
- **Login por perfil** (Educação por escola, Saúde por território/ESF, Gestão municipal com visão geral);
- **Histórico único por estudante** (sem duplicidade), com linha do tempo de evoluções;
- **Painel de indicadores** e alertas automáticos de atraso;
- **Exportação em Excel/PDF por escola**, para quem precisar do formato "planilha" tradicional em reuniões ou ofícios.

Isso atende a todos os requisitos funcionais do documento, com a vantagem adicional de rastreabilidade, permissões e auditoria — coisas que uma planilha (Excel/Google Sheets) não garante com segurança para dados de saúde de crianças e adolescentes.

## 2. Stack Tecnológica

| Camada | Tecnologia | Por quê |
|---|---|---|
| Backend | **Python 3.12 + Django 5** | Framework maduro, "baterias inclusas" (admin, autenticação, ORM, formulários), curva de aprendizado baixa para manutenção futura pela equipe do município |
| Frontend | **Django Templates + Bootstrap 5 + HTMX** | Sem necessidade de build separado (React/Vue); interatividade (filtros, tabelas dinâmicas) sem exigir um frontend complexo |
| Banco de dados | **PostgreSQL serverless via Neon** (integração nativa Vercel — antigo "Vercel Postgres") | Único banco relacional com bom suporte a serverless (pooling de conexões), integração de 1 clique na Vercel, plano gratuito suficiente para o volume municipal |
| Armazenamento de arquivos (PDFs) | **Vercel Blob** (ou S3-compatível via `django-storages`) | Vercel não tem disco persistente; upload de PDF do encaminhamento precisa de storage externo |
| Hospedagem | **Vercel** (Serverless Functions com runtime Python `@vercel/python`) | Requisito do pedido; deploy automático a cada push no GitHub |
| Autenticação | Django `auth` nativo + grupos/perfis (`Educação`, `Saúde`, `Gestão`) | Dispensa serviços externos, mais fácil de auditar |
| Gráficos do painel | Chart.js (via CDN, sem build) | Simplicidade |

### 2.1 Por que Postgres (Neon) e não outra opção

| Opção | Compatível com Vercel | Observação |
|---|---|---|
| **Neon Postgres** (recomendado) | Sim, integração nativa no painel da Vercel | Serverless, autoscaling, connection pooling pronto para funções serverless (essencial: sem pooling, cada função abre uma conexão nova e o banco satura) |
| Supabase Postgres | Sim, via Marketplace da Vercel | Boa alternativa; agrega Auth/Storage prontos, mas não precisamos (Django já resolve isso) |
| SQLite | Não recomendado | Sem disco persistente na Vercel; SQLite não sobrevive entre execuções serverless |
| MySQL gerenciado externo (PlanetScale etc.) | Parcial | Funciona, mas Django + Postgres tem melhor suporte a JSONField, full-text search e é o caminho mais testado |

## 3. Modelo de Dados

```
Escola (21 registros pré-cadastrados)
 └── Estudante (1:N)
      └── Caso/Encaminhamento (1:N)   ← 1 estudante pode ter mais de 1 encaminhamento ao longo do tempo
           └── Evolução (1:N)          ← histórico cronológico de movimentações do caso
Usuário (perfil: Educação/Saúde/Gestão, vinculado a 1 Escola ou 1 Território/ESF)
LogAuditoria (quem acessou/alterou qual registro e quando)
```

### 3.1 `Escola` e `Território/ESF`
`Escola`: `nome`, `tipo` (Municipal/Estadual/CEI), `ativo`. As 21 unidades do pedido entram como **carga inicial (fixture)** — não como 21 bancos/planilhas separados. Novas escolas são cadastradas pelo admin, sem alterar código.

`Território/ESF` é um cadastro próprio (`nome`, `ativo`), e não texto livre digitado a cada estudante: o nome usado no perfil do profissional de Saúde precisa ser idêntico ao usado no cadastro do estudante para o escopo de permissões funcionar, e um cadastro fechado evita divergência de grafia. Novos territórios também são cadastrados pelo admin.

### 3.2 `Estudante` (cadastro único, sem duplicidade)
`número de registro` (autoincremento), `nome`, `CPF` (armazenado criptografado), `data de nascimento`, `nome do responsável`, `telefone`, `escola` (FK), `ano/turma`, `território/ESF de referência`.

### 3.3 `Caso` (o encaminhamento)
`estudante` (FK), `data do registro`, `serviço encaminhado` (FK para o cadastro `Tipo de Atendimento` — Psicologia, Nutrição, Fonoaudiologia etc., também ampliável pelo admin), `data do encaminhamento`, `profissional responsável (Educação)`, `data do atendimento`, `retorno previsto`, `situação` (Aguardando / Em acompanhamento / Encerrado), `gravidade do caso` (Baixa/Média/Alta/Urgente — prioridade definida pelo profissional, independente do cálculo automático de atraso), `observações`, `anexo PDF do encaminhamento`.

Campos **calculados automaticamente** (não digitados):
- `dias sem retorno` = hoje − data do encaminhamento (ou última evolução, o que for mais recente);
- `atrasado / crítico` = regra configurável pela gestão, ex.: "Aguardando" há mais de 15 dias, ou "Em acompanhamento" sem evolução registrada há mais de 30 dias.

### 3.4 `Evolução` (histórico do caso — múltiplos registros por caso)
`caso` (FK), `data da movimentação`, `serviço responsável`, `profissional responsável`, `ação realizada`, `encaminhamento efetuado`, `retorno recebido`, `observações`. Sempre inserido, nunca substituído — garante o histórico cronológico completo pedido no documento.

### 3.5 `Usuário` / Perfis de acesso
- **Educação (por escola):** vê e edita apenas estudantes/casos da própria escola.
- **Saúde (por território/ESF ou serviço):** vê os casos encaminhados ao seu serviço, registra evolução e retorno.
- **Gestão municipal (Educação e Saúde):** visão consolidada de todas as escolas, indicadores, sem necessariamente editar cadastros individuais.

### 3.6 `LogAuditoria`
Toda visualização/edição de um registro de estudante grava usuário, data/hora e ação — exigência de boas práticas para dado sensível de criança/adolescente (ver seção 6).

## 4. Funcionalidades por Módulo

1. **Login e controle de acesso** por perfil e por escola/território.
2. **Cadastro do estudante + encaminhamento inicial** (formulário único, evita duplicidade — busca por CPF/nome antes de criar novo registro).
3. **Linha do tempo do caso** — lista cronológica das evoluções, sempre visível junto do cadastro do estudante.
4. **Painel de casos** com filtros (escola, território, situação, profissional, faixa de data) e busca rápida por nome/CPF.
5. **Alertas visuais automáticos** (cores/badges: verde = em dia, amarelo = próximo do prazo, vermelho = atrasado/crítico).
6. **Upload do encaminhamento em PDF**, vinculado ao caso.
7. **Painel de indicadores (dashboard)** por escola e consolidado:
   - total de registros por escola;
   - casos ativos, encerrados, aguardando atendimento;
   - tempo médio de espera (encaminhamento → atendimento);
   - número de casos críticos.
8. **Exportação** (Excel/CSV/PDF) por escola ou por território, para uso em reuniões/ofícios — atende ao formato "planilha por unidade" pedido, sem exigir 21 arquivos mantidos manualmente.
9. **Auditoria** — histórico de acessos por registro, visível à gestão.

## 5. Regras de Alerta de Atraso (proposta inicial, parametrizável)

| Situação | Regra sugerida | Cor |
|---|---|---|
| Aguardando atendimento | > 15 dias sem `data do atendimento` | Amarelo aos 10 dias, vermelho aos 15 |
| Em acompanhamento | > 30 dias sem nova evolução registrada | Vermelho |
| Retorno previsto vencido | `retorno previsto` < hoje e situação ≠ Encerrado | Vermelho |

Esses limiares ficam em uma tela de configuração acessível à Gestão, para ajuste sem precisar alterar código.

## 6. Segurança, Privacidade e Conformidade (LGPD/ECA)

Dado que o sistema trata **dados de saúde de crianças e adolescentes** (categoria sensível pela LGPD, art. 5º e 11), o planejamento deve prever, desde o início:

- **HTTPS obrigatório** (padrão automático na Vercel);
- **CPF armazenado criptografado** no banco (não em texto puro), exibido parcialmente mascarado na interface;
- **Permissão mínima necessária**: Educação não vê detalhes clínicos de saúde além do necessário ao fluxo; Saúde não vê dados pedagógicos além do necessário;
- **Log de auditoria** de todo acesso/alteração a registro de estudante;
- **Política de retenção** de dados definida junto às Secretarias (por quanto tempo os registros ficam ativos após encerramento do caso);
- **Base legal e governança**: recomenda-se instrumento formal (convênio/portaria) entre Secretaria de Educação e de Saúde definindo responsabilidade conjunta pelo tratamento dos dados (controladoras conjuntas, LGPD art. 7º), com ciência do Encarregado de Dados (DPO) do município;
- **Backups automáticos** do banco (Neon oferece point-in-time recovery).

Isso deve estar refletido tanto no sistema quanto em um termo de uso interno assinado pelos profissionais com acesso.

## 7. Infraestrutura e Deploy na Vercel

### 7.1 Como o Django roda na Vercel (pontos de atenção)

A Vercel não hospeda Django "nativamente" como hospeda Next.js — o Django roda como uma **função serverless Python** (runtime `@vercel/python`), com um `vercel.json` redirecionando todas as rotas para o `wsgi` do Django. Implicações práticas do planejamento:

- **Sem disco persistente** → uploads de PDF vão para storage externo (Vercel Blob), nunca para pasta local `media/`.
- **Sem processo contínuo** → nada de tarefas em segundo plano de longa duração; cálculos (como "dias sem retorno") são feitos na hora da consulta, não por um processo rodando o tempo todo.
- **Conexões de banco** → obrigatório usar a *connection string com pooling* do Neon (não a conexão direta), senão o banco satura com múltiplas funções abrindo conexões simultâneas.
- **Migrações não rodam automaticamente no deploy** → executar `python manage.py migrate` via GitHub Actions (ou manualmente) apontando para o banco de produção, como etapa do pipeline.
- **Arquivos estáticos (CSS/JS do admin, Bootstrap)** → servidos via `WhiteNoise`, com `collectstatic` rodando no passo de build.
- **Limite de tamanho de upload por requisição** (~4,5 MB nas funções da Vercel) → para PDFs maiores, usar upload direto do navegador para o Vercel Blob (URL assinada), sem passar o arquivo pela função Django.
- **Timeout de função** (10s no plano gratuito, configurável no Pro) → sem problema para este sistema (operações são CRUD simples e leituras de painel), só requer atenção se algum relatório muito pesado for gerado sob demanda.

### 7.2 Passo a passo de implantação

1. Criar o projeto Django localmente com os apps: `escolas`, `estudantes`, `casos`, `indicadores`, `usuarios`.
2. Adicionar `whitenoise` para estáticos e `django-storages` (+ Vercel Blob) para uploads.
3. Criar `vercel.json` com build Python e rota catch-all para o `wsgi.py`.
4. Criar o projeto na Vercel e conectar ao repositório GitHub (deploy automático a cada push).
5. Na aba **Storage** da Vercel, provisionar **Neon Postgres** — a `DATABASE_URL` (com pooling) é injetada automaticamente nas variáveis de ambiente.
6. Provisionar **Vercel Blob** para os anexos PDF.
7. Configurar variáveis de ambiente (`SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS`, `DATABASE_URL`, credenciais do Blob).
8. Rodar as migrações e o script de carga inicial das 21 escolas (fixture) apontando para o banco de produção.
9. Deploy (push na branch principal → build automático na Vercel).
10. Testes pós-deploy (login por perfil, cadastro, upload, indicadores, alertas).
11. Capacitação dos profissionais de Educação e Saúde para uso do sistema.

## 8. As 21 Unidades Escolares (carga inicial do cadastro `Escola`)

Pestalozzi de Canoas; EMEF Vasconcelos Jardim; EEEF Barão de Teresópolis; EMEF Álvaro Almeida; EMEF Campos Salles; EMEF Bilíngue para Surdos Vitória; EMEF Alfredo Antonio Amorim; EMEF José Bonifácio; EMEF Miguel Couto; EMEF Rui Barbosa; EMEF Tiradentes; EMEF Treze de Maio; EMEF Janaína; EMEF Hélio Fraga; EMEF Santa Rita de Cássia; EMEI Rainer; EMEI Paulo Freire; EMEI Vó Enedina; EMEI Vó Luiza; EMEF Victor Aggens; EMEI Vó Edith.

Essa lista entra como **fixture/seed** no banco (script único), não como 21 arquivos a manter manualmente.

## 9. Estrutura de Pastas do Projeto (referência)

```
projeto/
├── api/
│   └── index.py          # entrypoint WSGI para a Vercel
├── config/                # settings, urls, wsgi
├── escolas/
├── estudantes/
├── casos/                 # encaminhamentos + evoluções
├── indicadores/           # painel/dashboard
├── usuarios/               # perfis e permissões
├── templates/
├── static/
├── vercel.json
├── requirements.txt
└── manage.py
```

## 10. Fases e Cronograma Sugerido

| Fase | Escopo | Duração estimada |
|---|---|---|
| 1 | Levantamento fino de regras com Educação e Saúde + modelagem final | 1–2 semanas |
| 2 | MVP: cadastro de estudante, encaminhamento, evolução, login por perfil | 3–4 semanas |
| 3 | Painel de indicadores + alertas automáticos de atraso | 1–2 semanas |
| 4 | Segurança/LGPD, auditoria, exportação por escola | 1–2 semanas |
| 5 | Piloto em 2–3 escolas + ajustes com usuários reais | 2 semanas |
| 6 | Expansão às 21 unidades + capacitação das equipes | 2 semanas |

## 11. Custos Estimados

- **Vercel:** plano Hobby (gratuito) cobre uso interno de baixo tráfego; se precisar de domínio próprio com múltiplos ambientes (homologação + produção) e mais execuções, considerar plano Pro (pago).
- **Neon Postgres:** plano gratuito cobre volumes municipais típicos (milhares de registros); acompanhar limite de armazenamento/computação conforme a base cresce.
- **Vercel Blob:** cobrança por armazenamento/transferência dos PDFs — estimar volume anual de anexos para dimensionar.

## 12. Próximos Passos

1. Validar com as Secretarias de Educação e Saúde os campos e regras de alerta (seção 5) antes de iniciar o desenvolvimento.
2. Definir formalmente a governança de dados (quem é o controlador, retenção, DPO) — seção 6.
3. Aprovar este planejamento e iniciar a Fase 1.
