# Prática 3 – Consenso replicado em um serviço de pagamentos

**Plataformas e Sistemas de Alto Desempenho**

**Aluno:** Ian Pedro Ferreira de Paula · **Matrícula:** 1220104020

Este repositório reúne o código-fonte, os resultados e o roteiro da Prática 3. O programa simula um serviço de pagamentos replicado em cinco servidores e compara duas políticas de consenso diante de falhas, partições de rede e repetição de requisições.

---

## Sumário

1. [Conceitos envolvidos](#1-conceitos-envolvidos)
2. [Estrutura do repositório](#2-estrutura-do-repositório)
3. [Requisitos e execução](#3-requisitos-e-execução)
4. [Como o simulador funciona](#4-como-o-simulador-funciona)
5. [Roteiro de cenários](#5-roteiro-de-cenários)
6. [Etapas do trabalho](#6-etapas-do-trabalho)
7. [Resultados obtidos](#7-resultados-obtidos)
8. [Como ler o CSV](#8-como-ler-o-csv)
9. [Perguntas discutidas em sala](#9-perguntas-discutidas-em-sala)
10. [Limitações](#10-limitações)
11. [Checklist da entrega](#11-checklist-da-entrega)
12. [Referências](#12-referências)

---

## 1. Conceitos envolvidos

| Conceito | Significado nesta prática |
|---|---|
| **Réplica** | Cada um dos cinco servidores (N1 a N5). Cada réplica guarda seu próprio log de pagamentos. |
| **Quórum** | Número mínimo de réplicas que precisam concordar para que um pagamento seja efetivado. |
| **UNANIMIDADE** | Política em que as 5 réplicas precisam votar SIM (quórum = 5). |
| **MAIORIA** | Política em que basta `N // 2 + 1` réplicas votarem SIM (quórum = 3). |
| **Partição de rede** | A rede se divide em grupos isolados. O coordenador só alcança as réplicas do próprio grupo. |
| **Detector de falhas** | Usa heartbeats para marcar como SUSPEITO o nó que demora mais que o limite para responder. |
| **Recuperação** | Quando a rede é reparada, as réplicas atrasadas copiam do log os pagamentos que perderam. |
| **Idempotência** | Repetir o mesmo pagamento (mesmo identificador) não gera uma segunda cobrança. |

---

## 2. Estrutura do repositório

```
pratica3-consenso-pagamentos/
├── pratica3_consenso_pagamentos.py   # simulador
├── README.md                          # este arquivo
└── resultados/
    ├── resultados_consenso.csv        # Etapa 1 – execução completa
    ├── exec2_maioria.csv              # Etapa 2 – apenas maioria
    ├── exec3_p002_150.csv             # Etapa 3 – P002 alterado para R$ 150
    └── exec4_particao_3+2.csv         # Etapa 4 – partição 3+2
```

A pasta `resultados/` é criada automaticamente na primeira execução.

---

## 3. Requisitos e execução

**Requisitos:** Python 3.8 ou superior. O programa usa apenas a biblioteca padrão (`argparse`, `csv` e `os`), então não é preciso instalar nada com `pip`.

**Download:**

```bash
git clone https://github.com/ianpedrof-afk/pratica3-consenso-pagamentos.git
cd pratica3-consenso-pagamentos
```

**Execução no Windows (terminal do VS Code, com a pasta do projeto aberta):**

```bash
py pratica3_consenso_pagamentos.py
```

No Linux ou macOS, use `python3` no lugar de `py`.

**Opções de linha de comando:**

| Opção | Padrão | Função |
|---|---|---|
| `--politica {ambas, unanimidade, maioria}` | `ambas` | Escolhe quais políticas executar |
| `--valor-p002 <inteiro>` | `110` | Define o valor do pagamento P002 |
| `--particao <ex.: 2+3>` | `2+3` | Define a partição usada no pagamento P004 |
| `--saida <caminho.csv>` | `resultados/resultados_consenso.csv` | Define onde o CSV será gravado |

Os mesmos valores padrão podem ser alterados diretamente nas constantes do início do arquivo (`VALOR_P002` e `PARTICAO_P004`).

---

## 4. Como o simulador funciona

1. **Coordenador:** o nó N1 recebe cada pagamento e pede o voto das réplicas que consegue alcançar.
2. **Voto:** uma réplica vota SIM quando está ativa e ainda não registrou aquele identificador.
3. **Decisão:** o quórum é calculado pela função abaixo.

   ```python
   def quorum(politica, n):
       return n if politica == "UNANIMIDADE" else n // 2 + 1
   ```

   Se os votos SIM atingem o quórum, o pagamento é gravado em todas as réplicas que votaram (**APROVADO**). Caso contrário, nenhuma réplica o grava (**BLOQUEADO**), então não existe pagamento gravado pela metade.
4. **Partições:** a string da partição (por exemplo, `2+2+1`) distribui os nós em grupos, na ordem N1 a N5. O coordenador só recebe votos do próprio grupo.
5. **Detector de falhas:** um nó cujo heartbeat demora mais de 1,5 s simulado é marcado como `SUSPEITO`.
6. **Recuperação:** quando a rede é reparada, cada réplica compara seu log com o log efetivado do cluster e reaplica o que estiver faltando.
7. **Idempotência:** antes de abrir uma votação, o coordenador verifica se o identificador já foi efetivado. Se já foi, a requisição recebe a decisão **DUPLICADO_IGNORADO** e não é cobrada de novo.

---

## 5. Roteiro de cenários

O mesmo roteiro é executado para cada política, sempre começando com réplicas vazias:

| Passo | Evento | Pagamento | Valor |
|---|---|---|---|
| 1 | Todos os nós ativos | P001 | R$ 40 |
| 2 | N4 fora do ar | P002 | R$ 110 |
| 3 | Partição 2+2+1: {N1,N2} {N3,N4} {N5} | P003 | R$ 30 |
| 4 | Partição 2+3: {N1,N2} {N3,N4,N5} | P004 | R$ 25 |
| 5 | Heartbeat: N2 responde em 1,8 s (limite 1,5 s) | – | – |
| 6 | Rede reparada e N4 de volta: recuperação pelo log | – | – |
| 7 | P005 enviado e depois reenviado pelo cliente | P005 (2x) | R$ 20 |

N4 fica fora do ar do passo 2 até o passo 6.

---

## 6. Etapas do trabalho

A atividade prática guiada foi feita em cinco etapas.

### Etapa 1 – Rodar o programa completo

```bash
py pratica3_consenso_pagamentos.py
```

**O que observar:** a saída mostra os blocos `POLITICA: UNANIMIDADE` e `POLITICA: MAIORIA`, o estado final das réplicas e o resumo. O arquivo `resultados/resultados_consenso.csv` é gerado.

**Resultado:** UNANIMIDADE cobrou **R$ 60** (P001 + P005) e MAIORIA cobrou **R$ 170** (P001 + P002 + P005).

### Etapa 2 – Rodar apenas a política de maioria

```bash
py pratica3_consenso_pagamentos.py --politica maioria --saida resultados/exec2_maioria.csv
```

**O que observar:** apenas o bloco MAIORIA é executado.

**Resultado:** as decisões e o total de R$ 170 são iguais aos da Etapa 1. As políticas não compartilham estado, então o resultado de uma não interfere no da outra.

### Etapa 3 – Alterar o valor de P002 e executar novamente

```bash
py pratica3_consenso_pagamentos.py --valor-p002 150 --saida resultados/exec3_p002_150.csv
```

Também é possível editar `VALOR_P002 = 150` no início do arquivo.

**Resultado:** UNANIMIDADE continua em **R$ 60**, porque P002 segue bloqueado. MAIORIA passa para **R$ 210** (R$ 40 a mais). O valor muda o total, mas não a decisão: quem decide é a contagem de votos.

### Etapa 4 – Alterar a partição 2+3 para 3+2

```bash
py pratica3_consenso_pagamentos.py --particao 3+2 --saida resultados/exec4_particao_3+2.csv
```

Também é possível editar `PARTICAO_P004 = "3+2"` no início do arquivo.

**O que muda:** na partição 2+3, N1 fica em {N1, N2} e recebe só 2 votos. Na partição 3+2, ele fica em {N1, N2, N3} e recebe 3.

**Resultado:** MAIORIA aprova P004 e o total sobe para **R$ 195**. UNANIMIDADE continua em **R$ 60**. Na recuperação, N4 reaplica P002 e P004, e N5, que estava isolado na minoria, reaplica P004. As cinco réplicas terminam com o mesmo log.

### Etapa 5 – Interpretar os resultados com base no CSV

Os CSVs gerados nas etapas anteriores foram usados para montar a tabela comparativa e a discussão do relatório. Veja a seção [8](#8-como-ler-o-csv).

---

## 7. Resultados obtidos

| Execução | Política | P001 | P002 | P003 | P004 | P005 | Total |
|---|---|---|---|---|---|---|---|
| 1. Completo | Unanimidade | Aprov. | Bloq. | Bloq. | Bloq. | Aprov. | **R$ 60** |
| 1. Completo | Maioria | Aprov. | Aprov. | Bloq. | Bloq. | Aprov. | **R$ 170** |
| 2. Só maioria | Maioria | Aprov. | Aprov. | Bloq. | Bloq. | Aprov. | R$ 170 |
| 3. P002 = R$ 150 | Unanimidade | Aprov. | Bloq. | Bloq. | Bloq. | Aprov. | R$ 60 |
| 3. P002 = R$ 150 | Maioria | Aprov. | Aprov. | Bloq. | Bloq. | Aprov. | R$ 210 |
| 4. Partição 3+2 | Unanimidade | Aprov. | Bloq. | Bloq. | Bloq. | Aprov. | R$ 60 |
| 4. Partição 3+2 | Maioria | Aprov. | Aprov. | Bloq. | Aprov. | Aprov. | R$ 195 |

Em todas as execuções, a segunda tentativa de P005 foi registrada como `DUPLICADO_IGNORADO`.

Trecho da saída da Etapa 1 (política MAIORIA):

```
POLITICA: MAIORIA  (quorum = 3 de 5)
P001 (tentativa 1) R$   40 | votos SIM: 5 (quorum 3) -> APROVADO
P002 (tentativa 1) R$  110 | votos SIM: 4 (quorum 3) -> APROVADO
P003 (tentativa 1) R$   30 | votos SIM: 2 (quorum 3) -> BLOQUEADO
P004 (tentativa 1) R$   25 | votos SIM: 2 (quorum 3) -> BLOQUEADO
   heartbeat N2:         1.8s -> SUSPEITO
   heartbeat N4: sem resposta -> SUSPEITO
   N4: reaplicou P002
P005 (tentativa 1) R$   20 | votos SIM: 5 (quorum 3) -> APROVADO
P005 (tentativa 2) R$   20 | votos SIM: 0 (quorum 3) -> DUPLICADO_IGNORADO
TOTAL COBRADO (MAIORIA): R$ 170
```

---

## 8. Como ler o CSV

Cada linha corresponde a uma tentativa de pagamento.

| Coluna | Descrição |
|---|---|
| `politica` | UNANIMIDADE ou MAIORIA |
| `pagamento` / `tentativa` | Identificador do pagamento e número da tentativa |
| `valor` | Valor solicitado |
| `cenario` / `particao` | Situação simulada no momento do pedido |
| `nos_ativos` | Réplicas ligadas (detecta servidor parado) |
| `nos_alcancaveis` | Réplicas no mesmo grupo de rede do coordenador (detecta partição) |
| `votos_sim` / `quorum` | Votos recebidos e votos exigidos |
| `decisao` | APROVADO, BLOQUEADO ou DUPLICADO_IGNORADO |
| `valor_aplicado` | Quanto foi efetivamente cobrado nessa linha |
| `total_cobrado` | Total acumulado da política após essa linha |

**Leituras principais:**

- `total_cobrado` só aumenta nas linhas APROVADO, sempre pelo valor de `valor_aplicado`.
- Quando `nos_ativos` é menor que 5 e `nos_alcancaveis` é 5, o problema é um servidor parado. Quando `nos_alcancaveis` é menor que `nos_ativos`, o problema é a rede.
- A segunda tentativa de P005 tem `votos_sim = 0`, `valor_aplicado = 0` e `total_cobrado` inalterado, o que comprova que não houve cobrança em dobro.

---

## 9. Perguntas discutidas em sala

**Com 5 réplicas, qual é o menor quórum de maioria?**
É 3, porque `5 // 2 + 1 = 3`. Dois quóruns de 3 sempre compartilham pelo menos uma réplica (3 + 3 > 5), o que impede decisões conflitantes.

**Por que N4 fora do ar não impede a política de maioria?**
Sem N4, ainda restam 4 réplicas ativas, e o quórum é 3. Um cluster com N = 2f + 1 réplicas tolera f falhas; com 5 réplicas, tolera 2.

**Por que uma partição 2 + 2 + 1 bloqueia os pagamentos?**
O maior grupo tem só 2 nós, menos que o quórum de 3. O bloqueio impede que cada lado aprove pagamentos por conta própria e crie históricos divergentes (*split brain*).

**O que prova que repetir P005 não duplicou a cobrança?**
No CSV, a segunda tentativa aparece como `DUPLICADO_IGNORADO`, com `valor_aplicado = 0` e total mantido em R$ 170. Além disso, o log de cada réplica contém P005 uma única vez.

**Por que "suspeito" não é sinônimo de "servidor quebrado"?**
O detector só mede atraso, não a causa. N2 foi marcado como SUSPEITO por responder em 1,8 s, mas continuou ativo e votou em P005. Lentidão, congestionamento e pausas parecem iguais a uma falha para quem observa de fora.

---

## 10. Limitações

- Roda em um único processo, de forma determinística, sem rede nem mensagens reais.
- O coordenador é sempre N1 e nunca falha: não há eleição de líder nem queda durante uma votação.
- A votação e a gravação acontecem em um único passo, sem as fases de preparação e confirmação de um protocolo real.
- A recuperação usa uma visão global do log, que um nó real não teria.
- Os identificadores processados ficam só na memória, sem persistência em disco.
- Não há concorrência entre pagamentos.

Protocolos de produção, como **Paxos** e **Raft**, exigem provas formais, verificação de modelos e testes com injeção de falhas. **Uma simulação não valida um algoritmo real.**

---

## 11. Checklist da entrega

- [x] Python instalado e arquivo `.py` na pasta aberta
- [x] Comando `py pratica3_consenso_pagamentos.py` funcional
- [x] Saída mostra as políticas UNANIMIDADE e MAIORIA
- [x] CSV gerado em `resultados/`
- [x] Valores finais de R$ 60 e R$ 170
- [x] Ressalva de que uma simulação não valida um algoritmo real
- [x] Relatório exportado como `AVA3_IANPEDRO.pdf`

---

## 12. Referências

- CHANDRA, T. D.; TOUEG, S. Unreliable failure detectors for reliable distributed systems. *Journal of the ACM*, v. 43, n. 2, p. 225–267, 1996.
- FISCHER, M. J.; LYNCH, N. A.; PATERSON, M. S. Impossibility of distributed consensus with one faulty process. *Journal of the ACM*, v. 32, n. 2, p. 374–382, 1985.
- LAMPORT, L. Paxos made simple. *ACM SIGACT News*, v. 32, n. 4, p. 51–58, 2001.
- ONGARO, D.; OUSTERHOUT, J. In search of an understandable consensus algorithm. *USENIX Annual Technical Conference*, 2014.
- TANENBAUM, A. S.; VAN STEEN, M. *Distributed systems*. 3. ed., 2017.
