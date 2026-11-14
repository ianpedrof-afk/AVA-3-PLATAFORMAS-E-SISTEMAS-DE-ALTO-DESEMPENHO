# Prática 3 – Consenso replicado em pagamentos

Simulação didática de 5 réplicas (N1–N5) comparando as políticas UNANIMIDADE e MAIORIA.

```
py pratica3_consenso_pagamentos.py                     # completo
py pratica3_consenso_pagamentos.py --politica maioria  # só maioria
py pratica3_consenso_pagamentos.py --valor-p002 150    # altera P002
py pratica3_consenso_pagamentos.py --particao 3+2      # altera a partição
```

Os resultados são gravados em `resultados/`. Totais esperados: R$ 60 (unanimidade) e R$ 170 (maioria).

