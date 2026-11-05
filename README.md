# Безопасный canary deployment для ML: учебный пример

**Цель:** показать gradual rollout, технический и ML quality gates, два одновременно работающих модельных экземпляра и rollback без пересборки образа. Пример использует синтетические данные и не рассчитан на принятие реальных бизнес-решений.

## Схема

`Client → Nginx gateway:8080 → Stable v1 (95%) / Canary v2 (5%) → versioned response + JSON logs + Prometheus metrics`.

- `stable` — модель `models/v1.json`, корректно решает синтетическую задачу.
- `canary` — модель `models/v2.json`, намеренно выдаёт неверные предсказания на положительном классе.
- **Оба контейнера работают на основе одного собранного Docker image**, с разным `MODEL_FILE`. Файлы моделей помещаются в образ при сборке, и `MODEL_VERSION` проверяется при запуске. При rollback приложение и модель не пересобираются.
- Nginx применяет weighted round robin; для canary 5/25/50/100% используется `scripts/route.py`.
- JSON-логи приложений содержат `model_version`, `request_id`, `latency_ms`, `status`, но не признаки пользователя.

## Быстрый запуск локально

Требуются Docker с Compose v2, Python 3.12+, `pytest` (для unit tests).

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m pytest -q tests
python3 scripts/generate_fixture.py
python3 scripts/evaluate.py

python3 scripts/route.py 0 --no-reload
docker compose build stable
docker compose up -d --no-build
python3 scripts/smoke.py
python3 scripts/route.py 5
python3 scripts/probe_traffic.py --requests 500 --workers 12
python3 scripts/assess_canary.py --expect-rejection
python3 scripts/rollback_check.py

docker compose logs --no-color stable canary | tail -n 30
docker compose down
```

**Проверка негативного сценария:** `python3 scripts/assess_canary.py` без `--expect-rejection` возвращает код 1 при нарушении порогов. Флаг `--expect-rejection` используется **только** внутри учебной демонстрации: он проверяет, что защита действительно сработала. Он не разрешает promotion.

## Запуск в GitHub Actions без VPS

Скопируйте весь проект в каталог `safe-canary/` вашего репозитория и расположите файл workflow из архива по адресу `.github/workflows/safe-canary.yml` в **корне репозитория**, а не внутри `safe-canary/`. Затем GitHub → Actions → `Safe model deployment - canary demonstration` → Run workflow. Скрипт не использует GHCR, SSH, секреты или внешнее развёртывание: Docker выполняется на временной GitHub-hosted VM.

Workflow построит Docker-образ **один раз**, запустит stable и canary одновременно, установит вес 95/5, измерит модельные и HTTP-метрики, обнаружит искусственную деградацию canary, выполнит rollback 100/0, соберёт отчёты в artifact `safe-canary-reports` и удалит контейнеры. Безопасность production всё равно требует отдельного постоянного окружения и gate/approval.

**Внимание:** В исходном проекте `.github/workflows/safe-canary.yml` лежит в привычном месте. После копирования проекта в подпапку репозитория нужно вынести workflow на уровень `.github/workflows/` репозитория.

## Проверка действий отдельно

```bash
curl -fsS http://127.0.0.1:18081/version # v1
curl -fsS http://127.0.0.1:18082/version # v2
curl -fsS http://127.0.0.1:8080/ready
python3 scripts/route.py 5
python3 scripts/probe_traffic.py
python3 scripts/route.py 0
python3 scripts/probe_traffic.py --requests 100 --output reports/post_rollback_traffic.json
```

## Отчёты и приёмка

- `architecture.md` — схема.
- `compose.yaml`, `routing/`, `Dockerfile`, `models/` — конфигурация и две модели.
- `reports/quality.json` — offline Precision / Recall / F1 (те же фиксированные labels для двух версий).
- `reports/canary_traffic.json` — фактическое распределение запросов, error rate, p50/p95/p99.
- `reports/canary_assessment.json` — решение `ROLLBACK` и конкретные stop conditions.
- `reports/rollback_proof.json` — результаты запросов во время reload и после: успешность, уникальные request IDs, отсутствие маршрутизации на v2 после rollback.
- `runbook.md` — процедура инцидента.

## Интерпретация и ограничения

1. Ошибка v2 **ML-качества**, а не доступности: canary может давать HTTP 200 при неверных прогнозах.
2. Offline ground truth синтетический и доступен сразу. В реальном fraud detection Precision/Recall появляются с задержкой; при отсутствии меток **нельзя автоматически продвигать версию до 100%**.
3. Nginx weighted round robin не задаёт точный процент для маленького числа запросов; фактическую долю измеряем на выборке.
4. `rollback_check.py` проверяет отсутствие потерь *в наблюдаемом наборе* запросов в тестовом окружении. Это не доказательство абсолютной непрерывности и exactly-once delivery.
5. Gateway при rollback остаётся работающим, обе модели доступны. Устойчивость к отказу stable-экземпляра здесь не моделируется.
6. Реальный production следует собирать с полностью проверенными version/digest pins и сканированием зависимостей; учебный образ не является подтверждением production security.
# safe_deploy
