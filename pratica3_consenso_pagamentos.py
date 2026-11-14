"""
Pratica 3 - Consenso replicado para pagamentos (simulacao didatica)
Disciplina: Plataformas e Sistemas de Alto Desempenho

Simula 5 replicas (N1..N5) de um servico de pagamentos. Cada pagamento so
e efetivado quando o coordenador (N1) reune o quorum exigido pela politica:

  UNANIMIDADE -> todas as 5 replicas precisam confirmar
  MAIORIA     -> pelo menos N // 2 + 1 replicas (3 de 5)

Cenarios: falha de N4, particao 2+2+1, particao 2+3, deteccao de no
"suspeito" por heartbeat, recuperacao de N4 e repeticao do pagamento P005
(idempotencia). Os resultados sao gravados em resultados/*.csv.

Uso:
  py pratica3_consenso_pagamentos.py
  py pratica3_consenso_pagamentos.py --politica maioria
  py pratica3_consenso_pagamentos.py --valor-p002 150
  py pratica3_consenso_pagamentos.py --particao 3+2

ATENCAO: e uma simulacao deterministica em um unico processo. Ela ilustra
as regras de quorum, mas NAO valida um algoritmo de consenso real.
"""
import argparse
import csv
import os

NOS = ["N1", "N2", "N3", "N4", "N5"]
COORDENADOR = "N1"
TIMEOUT_HEARTBEAT = 1.5   # segundos simulados sem heartbeat -> SUSPEITO
PRAZO_VOTO = 3.0          # segundos simulados para o coordenador aguardar votos

# Valores padrao (podem ser alterados aqui ou pela linha de comando)
VALOR_P002 = 110
PARTICAO_P004 = "2+3"


class Replica:
    def __init__(self, nome):
        self.nome = nome
        self.ativa = True
        self.latencia = 0.2          # tempo de resposta simulado (s)
        self.log = []                # [(id, valor)] pagamentos efetivados
        self.processados = set()     # ids ja aplicados (idempotencia)

    def votar(self, pid):
        """Responde SIM se estiver ativa e nao tiver aplicado pid antes."""
        return self.ativa and pid not in self.processados

    def aplicar(self, pid, valor):
        if pid in self.processados:
            return False
        self.log.append((pid, valor))
        self.processados.add(pid)
        return True

    def saldo_cobrado(self):
        return sum(v for _, v in self.log)


def quorum(politica, n):
    return n if politica == "UNANIMIDADE" else n // 2 + 1


def grupos_da_particao(texto):
    tamanhos = [int(x) for x in texto.split("+")]
    if sum(tamanhos) != len(NOS):
        raise ValueError(f"particao {texto} nao soma {len(NOS)} nos")
    grupos, i = [], 0
    for t in tamanhos:
        grupos.append(NOS[i:i + t])
        i += t
    return grupos


def alcancaveis(grupos):
    """Nos que estao no mesmo grupo de rede que o coordenador."""
    if not grupos:
        return list(NOS)
    for g in grupos:
        if COORDENADOR in g:
            return g
    return []


class Cluster:
    def __init__(self, politica):
        self.politica = politica
        self.replicas = {n: Replica(n) for n in NOS}
        self.efetivados = []          # ids confirmados pelo cluster
        self.linhas = []              # registros para o CSV

    def detector(self, atrasos):
        """Detector de falhas por heartbeat: atraso > timeout -> SUSPEITO."""
        estados = {}
        for n in NOS:
            atraso = atrasos.get(n, 0.3)
            r = self.replicas[n]
            if not r.ativa:
                atraso = float("inf")
            estados[n] = "SUSPEITO" if atraso > TIMEOUT_HEARTBEAT else "OK"
            txt = "sem resposta" if atraso == float("inf") else f"{atraso:.1f}s"
            print(f"   heartbeat {n}: {txt:>12} -> {estados[n]}")
        return estados

    def pagar(self, pid, valor, cenario, particao=None, tentativa=1):
        grupos = grupos_da_particao(particao) if particao else []
        visiveis = alcancaveis(grupos)
        q = quorum(self.politica, len(NOS))

        if pid in self.efetivados:
            decisao, votos = "DUPLICADO_IGNORADO", []
            aplicado = 0
        else:
            votos = []
            for n in visiveis:
                r = self.replicas[n]
                if r.votar(pid) and r.latencia <= PRAZO_VOTO:
                    votos.append(n)
            if len(votos) >= q:
                for n in votos:
                    self.replicas[n].aplicar(pid, valor)
                self.efetivados.append(pid)
                decisao, aplicado = "APROVADO", valor
            else:
                decisao, aplicado = "BLOQUEADO", 0

        total = sum(v for p, v in self._log_cluster())
        ativos = [n for n in NOS if self.replicas[n].ativa]
        print(f"   {pid} (tentativa {tentativa}) R$ {valor:>4} | "
              f"votos SIM: {len(votos)} (quorum {q}) {votos} -> {decisao}")
        self.linhas.append({
            "politica": self.politica, "pagamento": pid,
            "tentativa": tentativa, "valor": valor, "cenario": cenario,
            "particao": particao or "-", "nos_ativos": len(ativos),
            "nos_alcancaveis": len(visiveis), "votos_sim": len(votos),
            "quorum": q, "decisao": decisao, "valor_aplicado": aplicado,
            "total_cobrado": total,
        })
        return decisao

    def _log_cluster(self):
        """Log efetivado do cluster (ordem de confirmacao)."""
        valores = {}
        for r in self.replicas.values():
            valores.update(dict(r.log))
        return [(p, valores[p]) for p in self.efetivados]

    def recuperar(self, nome):
        """Replica volta (ou rede e reparada) e copia o que perdeu do log."""
        r = self.replicas[nome]
        r.ativa = True
        faltando = [(p, v) for p, v in self._log_cluster()
                    if p not in r.processados]
        for p, v in faltando:
            r.aplicar(p, v)
        ids = [p for p, _ in faltando] or ["nada"]
        print(f"   {nome}: reaplicou {', '.join(ids)}")

    def estado(self):
        for n in NOS:
            r = self.replicas[n]
            ids = ",".join(p for p, _ in r.log) or "-"
            print(f"   {n}: cobrado R$ {r.saldo_cobrado():>4} | log [{ids}]")


def executar(politica, valor_p002, particao_p004):
    print("=" * 66)
    print(f"POLITICA: {politica}  (quorum = {quorum(politica, len(NOS))} de "
          f"{len(NOS)})")
    print("=" * 66)
    c = Cluster(politica)

    print("\n[1] Todos os nos ativos")
    c.pagar("P001", 40, "todos_ativos")

    print("\n[2] N4 fora do ar")
    c.replicas["N4"].ativa = False
    c.pagar("P002", valor_p002, "N4_fora")

    print("\n[3] Particao de rede 2+2+1")
    c.pagar("P003", 30, "particao_2+2+1", particao="2+2+1")

    print(f"\n[4] Particao de rede {particao_p004}")
    c.pagar("P004", 25, f"particao_{particao_p004}", particao=particao_p004)

    print("\n[5] Detector de falhas (heartbeat, timeout "
          f"{TIMEOUT_HEARTBEAT}s)")
    c.replicas["N2"].latencia = 1.8          # N2 lento, mas vivo
    c.detector({"N2": 1.8})
    print("   -> N2 esta SUSPEITO, mas continua ativo e respondendo")

    print("\n[6] Rede reparada e N4 de volta: recuperacao pelo log")
    for n in NOS:
        c.recuperar(n)

    print("\n[7] Pagamento P005 e repeticao (cliente reenviou)")
    c.pagar("P005", 20, "todos_ativos")
    c.pagar("P005", 20, "repeticao_cliente", tentativa=2)

    print("\nEstado final das replicas:")
    c.estado()
    total = sum(v for _, v in c._log_cluster())
    print(f"\nTOTAL COBRADO ({politica}): R$ {total}")
    return c, total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--politica", choices=["ambas", "unanimidade", "maioria"],
                    default="ambas")
    ap.add_argument("--valor-p002", type=int, default=VALOR_P002)
    ap.add_argument("--particao", default=PARTICAO_P004,
                    help="particao usada em P004, ex.: 2+3 ou 3+2")
    ap.add_argument("--saida", default="resultados/resultados_consenso.csv")
    a = ap.parse_args()

    politicas = (["UNANIMIDADE", "MAIORIA"] if a.politica == "ambas"
                 else [a.politica.upper()])
    linhas, resumo = [], []
    for p in politicas:
        c, total = executar(p, a.valor_p002, a.particao)
        linhas += c.linhas
        resumo.append((p, total))
        print()

    os.makedirs(os.path.dirname(a.saida) or ".", exist_ok=True)
    with open(a.saida, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0].keys()))
        w.writeheader()
        w.writerows(linhas)

    print("RESUMO")
    for p, t in resumo:
        print(f"   {p:<12} total cobrado: R$ {t}")
    print(f"CSV gravado em: {a.saida}")
    print("Obs.: simulacao didatica; nao valida um algoritmo de consenso real.")


if __name__ == "__main__":
    main()
