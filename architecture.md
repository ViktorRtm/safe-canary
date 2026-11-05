# Схема deployment

```mermaid
flowchart TD
  CI[GitHub Actions ephemeral staging] --> G[Nginx :8080]
  G -->|95%| A[Stable v1 :8000]
  G -->|5%| B[Canary v2 :8000]
  A --> MA[JSON logs / metrics v1]
  B --> MB[JSON logs / metrics v2]
  MA --> C[Compare technical + ML metrics]
  MB --> C
  C -->|PASS after sufficient evidence| P[Promote 25 → 50 → 100%]
  C -->|FAIL| R[Rollback: Nginx weights 100/0]
  R --> G
```

**Замечание:** GitHub-hosted runner не является постоянной средой. Схема пригодна для учебного испытания и локального запуска, но для production нужен стабильный внешний runtime, доступ к мониторингу и проверка SLA на реальном трафике.
