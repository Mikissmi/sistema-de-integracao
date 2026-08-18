# Política de Privacidade e Termo de Tratamento de Dados

> ⚠️ **Rascunho técnico, não é um documento jurídico pronto para uso.** Este
> texto foi redigido para servir de ponto de partida para o contrato entre a
> empresa desenvolvedora do sistema e a Prefeitura de Nova Santa Rita (ou
> entre as Secretarias de Educação e Saúde). **Precisa ser revisado por um
> advogado antes de ser assinado, publicado ou usado como base de qualquer
> obrigação contratual**, especialmente porque o sistema trata dado de saúde
> de crianças e adolescentes — a categoria de maior proteção na LGPD e no
> ECA. Os campos entre colchetes (`[...]`) precisam ser preenchidos com
> informações reais da prefeitura antes de qualquer uso.

**Sistema:** Acompanhamento Intersetorial Educação-Saúde
**Município:** Nova Santa Rita
**Última atualização deste rascunho:** 18/08/2026

---

## 1. Quem trata os dados (papéis)

- **Controladora dos dados:** Prefeitura Municipal de Nova Santa Rita (Secretarias de Educação e de Saúde), responsável por decidir quais dados são coletados e para quê.
- **Operadora dos dados:** [nome da empresa desenvolvedora/mantenedora do sistema], responsável por hospedar, processar e proteger tecnicamente os dados conforme instrução da controladora.
- **Encarregado de Dados (DPO):** [nome e contato do encarregado designado pela prefeitura — obrigatório indicar um, LGPD Art. 41].

Recomenda-se formalizar essa relação por instrumento próprio (convênio, portaria ou cláusula específica no contrato de prestação de serviço), incluindo Educação e Saúde como controladoras conjuntas quando aplicável (LGPD Art. 7º).

## 2. Quais dados são tratados

| Categoria | Exemplos | Classificação LGPD |
|---|---|---|
| Identificação do estudante | Nome, data de nascimento, CPF | Dado pessoal comum + CPF (identificador único, tratamento reforçado) |
| Dados do responsável | Nome, telefone de contato | Dado pessoal comum |
| Dados escolares | Escola, ano/turma | Dado pessoal comum |
| Dados de encaminhamento e acompanhamento de saúde/assistência social | Serviço encaminhado, situação, gravidade, evoluções, anexos | **Dado sensível** (saúde, LGPD Art. 5º, II) |
| Todos os dados acima, pertencentes a menores de 18 anos | — | **Dado de criança e adolescente** (proteção reforçada, LGPD Art. 14 + ECA) |

O sistema **não coleta e-mail nem outro dado de contato do estudante** — apenas do responsável (telefone) — e o CPF é armazenado sempre criptografado, nunca em texto puro no banco de dados.

## 3. Finalidade do tratamento

Os dados são tratados exclusivamente para:

1. Registrar e acompanhar encaminhamentos de estudantes da rede municipal de ensino para serviços da rede de saúde/assistência social;
2. Permitir que os profissionais de Educação e Saúde envolvidos no caso acompanhem sua evolução;
3. Gerar indicadores agregados para a gestão municipal (sem uso para nenhuma outra finalidade, como marketing, pesquisa não relacionada, ou repasse comercial).

## 4. Base legal (LGPD)

- **Execução de políticas públicas** pela administração pública, no âmbito de suas atribuições legais (Art. 7º, III e Art. 23);
- **Tutela da saúde**, em procedimento realizado por profissionais de saúde (Art. 11, II, "f", para o dado sensível de saúde);
- **Proteção da vida e da incolumidade física** e melhor interesse da criança e do adolescente (Art. 14, combinado com o ECA), quando aplicável ao caso concreto.

Recomenda-se que a prefeitura formalize essa base legal junto à sua assessoria jurídica e, quando pertinente, obtenha consentimento específico do responsável legal, sem prejuízo da base legal de execução de política pública.

## 5. Como os dados são protegidos (medidas já implementadas no sistema)

- **CPF criptografado em repouso** (Fernet/AES) no banco de dados, nunca armazenado em texto puro; exibido sempre mascarado (`123.***.***-45`) nas telas e relatórios;
- **Controle de acesso por perfil e escopo**: cada usuário só acessa os registros da própria escola/território, exceto Gestão; usuário sem perfil configurado não acessa nenhum dado (nunca acesso total por omissão);
- **Log de auditoria** de criação, visualização e alteração de registros, com retenção configurável (ver seção 6);
- **Senhas** armazenadas com hash seguro (nunca em texto puro), com bloqueio temporário de acesso após tentativas repetidas de senha incorreta;
- **HTTPS obrigatório** e cabeçalhos de segurança (HSTS) em produção;
- **CSRF e XSS**: proteção padrão do framework em todos os formulários;
- **Backups**: dependem do plano de banco de dados contratado (Neon Postgres) — a prefeitura deve confirmar a política de backup/recuperação com o provedor de hospedagem.

## 6. Retenção e descarte

- **Log de auditoria**: retido por `RETENCAO_LOG_AUDITORIA_DIAS` (padrão: 365 dias), apagado automaticamente depois desse prazo por rotina agendada.
- **Dados de estudantes e casos**: **este sistema ainda não implementa expurgo automático** dos registros principais (Estudante, Caso, Evolução). A prefeitura precisa definir, junto à Secretaria de Educação/Saúde e ao Encarregado de Dados, por quanto tempo um registro permanece ativo após o encerramento do caso, e formalizar essa política — o sistema pode ser adaptado para aplicá-la automaticamente depois que a regra for definida.

## 7. Direitos dos titulares

Por se tratar majoritariamente de dados de crianças e adolescentes, os direitos abaixo (LGPD Art. 18) são exercidos pelo responsável legal, mediante solicitação formal à prefeitura:

- Confirmação da existência de tratamento e acesso aos dados;
- Correção de dados incompletos, inexatos ou desatualizados;
- Eliminação dos dados tratados com base em consentimento (quando aplicável);
- Informação sobre com quem os dados foram compartilhados.

[Definir aqui o canal oficial pelo qual o responsável legal pode fazer essa solicitação — e-mail, protocolo presencial, etc.]

## 8. Incidentes de segurança

Em caso de incidente de segurança (vazamento, acesso não autorizado, perda de dados) envolvendo os dados tratados por este sistema, a operadora deve comunicar a controladora **imediatamente** após a detecção, para que a prefeitura possa avaliar a comunicação à Autoridade Nacional de Proteção de Dados (ANPD) e aos titulares afetados, conforme LGPD Art. 48.

## 9. Vigência e revisão

Este documento deve ser revisado sempre que houver mudança relevante no sistema (novos dados coletados, nova finalidade, novo prestador de serviço) e, no mínimo, anualmente.
