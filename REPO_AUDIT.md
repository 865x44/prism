# REPO_AUDIT.md — Beerlight / Prism forensic audit

**Дата:** 2026-08-09
**Режим:** read-only (единственное изменение дерева — этот файл)
**Команды:** `git fetch origin`, `git rev-list --left-right --count main...origin/main`, `git diff --stat main origin/main`, `git status -sb`, `git log --all --oneline`, `git reflog`, `git ls-tree -r origin/docs/*`, `python3 -m venv /tmp/prism-venv && pip install -e . && pip install pytest && python -m pytest -q -rs` (в /tmp venv), чтение исходников и доков.

Маркировка: **[OBSERVED]** — найдено в репо; **[INFERRED]** — вывод по структуре; **[RECOMMENDED]** — предложение.

---

## 1. Executive summary

Prism — это **публичный рекат** внутреннего Beerlight Terminal: runtime/slice-слой скопирован из `beerlight-terminal-wt-chat-edition`, переименован в `prism`, вычищен до нулевых зависимостей, расширен RIFT-профилем и снабжён демо-фикстурой. На машине три репозитория семейства (см. §2); текущий — `prism` (единственный с remote = `865x44/prism`, единственный публично выпущенный).

Ключевые факты:

- Код-субстрат для acceptance harness'а — **сильный**: детерминированная валидация JSON, bounded repair, версионированные промпты, трейсы v1 с полной провенанс-информацией, инспектируемость (shown / kept-hidden / dropped), 165 зелёных тестов.
- Eval-инфраструктура (`evals/`, `harness/`, `mock_provider`) **существует, но в соседних репозиториях** и нацелена на другой продукт: rubric/golden-набор — для `narrative-build-engine`, harness/ — для стилевого дрейфа Beerlight Terminal. Для семантического acceptance Prism их можно только адаптировать по образцу.
- Продуктовая конституция (контракты Explore: NORMAL/RIFT/360/TRANSFER; Deep: DEEPEN/RETURN_TO_EXPLORE/LEVER; разделение Explore/Deep) **написана, но не в `main`** — лежит в неслитой remote-ветке `docs/master-state-v0`. Код с доками расходится: в коде есть только NORMAL/360/RIFT, ни одного Deep-контракта.
- В самом Prism **нет** mock-провайдера, batch-раннера, скоринга, корпуса — это и есть минимальный дефицит для acceptance harness'а.

**Verdict: REPO_NEEDS_SMALL_ADAPTATION** — см. §13.

## 2. Repository identity

### Текущий репозиторий — `/home/alx/projects/prism` **[OBSERVED]**

| Параметр | Значение |
|---|---|
| remote | `origin https://github.com/865x44/prism.git` |
| branch | `main` (плюс локальная `release/shareable-rift`, уже влитая) |
| HEAD | `f8315e8` — Merge PR #1 `865x44/release/shareable-rift` |
| tags | нет |
| tracked files | 54 |
| язык | Python 3.11+ (pyproject `requires-python >=3.11`) |
| package | `prism` 0.1.0, setuptools, **runtime-зависимостей ноль**; dev: pytest |
| package manager | pip / setuptools |
| CI | `.github/workflows/ci.yml`: pytest на 3.11/3.12/3.13, `python -m build`, установка wheel в чистый venv |

### Карта семейства Beerlight/Prism на машине **[OBSERVED]**

| Репозиторий | Remote | Ветка | Статус | Что это |
|---|---|---|---|---|
| `~/projects/prism` | `865x44/prism` | `main` | чисто | **текущий** — публичный Prism Runtime v1 + RIFT |
| `~/projects/beerlight-terminal` | нет | `slice/beerlight-v0` | **dirty** (`.ai/STATE.md`, `.ai/SESSION_LOG.md` — изменены) | оригинал: TUI/textual, spark, timuroki, harness/, llm/, evals/, dogfood/, ~40 тестовых файлов |
| `~/projects/beerlight-terminal-wt-chat-edition` | нет | `feat/chatgpt-adapter-pack` | чисто | продолжение: тот же runtime/slice + `harness/`, `llm/mock_provider.py`, custom GPT adapter pack (`chatgpt/`), `docs/decisions/`, `docs/future/`, `.ai/` |

**Определение текущего репо по evidence:** единственный с remote, совпадающим с запросом; единственный с публичным релизным циклом (PR #1, CI, LICENSE); sibling-репозитории — предки/форки без remote. Beerlight — кодовое имя из первого коммита (`5ee1a79 prism: Beerlight Runtime v1 standalone`), не отдельный репо.

**[INFERRED]** `prism` = рекат runtime/slice из chat-edition: `diff` показывает почти побайтовое совпадение `runtime/service.py` (различие — добавленный параметр `profile` для RIFT и переименование пакета). Отсечены: TUI/web/spark/storage/timuroki/harness/llm-слой с pydantic-зависимостями.

## 3. Working-tree state

- `prism`: **чисто** — `git status --porcelain` пуст до и после прогона тестов (`__pycache__`, `.pytest_cache`, `prism-runs/`, `prism-sessions/` в `.gitignore`). **[OBSERVED]**
- `beerlight-terminal`: грязно — изменены `.ai/STATE.md`, `.ai/SESSION_LOG.md` (отслеживаемые). **Не тронуты, сохранены как есть.** **[OBSERVED]**
- `beerlight-terminal-wt-chat-edition`: чисто. **[OBSERVED]**
- В `prism` нет `prism-runs/` (артефакты заигнорены); единственная закоммиченная запись прогона — фикстура `src/prism/demo_fixtures/demo_run/` (v1-трейс: metadata/request/candidates/judge/output). **[OBSERVED]**

## 4. Existing architecture

Двухслойная структура `src/prism/` **[OBSERVED]**:

```
prism.slice   — «проверенное ядро»: provider.py (транспорт), validate.py (JSON-схемы,
                извлечение, repair-промпты), prompts.py (загрузка шаблонов), prompts/*.md
prism.runtime — оркестрация: service (run/run_json), generator, judge, session,
                trajectory, events, outcomes, trace, models, contracts, cli, inspect,
                doctor, demo
```

Поток прогона (service.run): чтение входа → resolve контекста (trajectory/full) → `build_generator_prompt` → `generate_with_repair` (1 repair) → запись `candidates.json` → `build_judge_prompt` → `judge_with_repair` (1 repair, обязательное покрытие всех id) → resolve (cap 3) → запись трейса v1 → обновление trajectory (если session) → stdout.

Инварианты, заявленные в коде и соблюдаемые: `MAX_CARDS = 3`; карты пользователю ≤3, полный пул и решения судьи сохраняются; абстенция — статус, а не исключение; сбой судьи → degraded с сохранением пула; сбой записи трейса → warning. **[OBSERVED]**

## 5. Provider layer

### Prism (`src/prism/slice/provider.py`) **[OBSERVED]**

- Два транспорта: `http` — OpenAI-совместимый Chat Completions на stdlib `urllib` (OpenAI/OpenRouter/gateway); `opencode` — subprocess к CLI `opencode run --model ...`.
- Конфигурация env: `PRISM_TRANSPORT` (auto/http/opencode), `PRISM_API_KEY`/`OPENAI_API_KEY`, `PRISM_BASE_URL`, `PRISM_GENERATOR_MODEL`, `PRISM_JUDGE_MODEL`. Дефолт модели зависит от транспорта: http → `gpt-4o-mini`, opencode → `opencode-go/deepseek-v4-pro`.
- Retry: 1 повтор при TransportError, пауза 10 с, таймаут 600 с. Ошибки — структурированный `TransportError` с контекстом.
- Structured output: **не через API** — JSON форсируется промптом + валидацией (`slice/validate.py`) + bounded repair. `expected_ids` в судейской валидации заставляет покрывать всех кандидатов.
- Token/latency: **только эвристика** `chars // 4` в `token_usage_estimate` и `duration_sec` в metadata; поле `usage` из API-ответа не читается. **[OBSERVED]**
- Provider injection отсутствует: модели берутся модульными функциями `get_generator_model()`/`get_judge_model()` из env — для harness'а достаточно env-переопределения на прогон. **[INFERRED]**

### Соседние репо **[OBSERVED]**

`beerlight/llm/`: `provider.py` (Protocol `LLMProvider`, pydantic `Message`/`LLMConfig`), `mock_provider.py` (детерминированный canned-провайдер, fingerprint по sha256 последнего user-сообщения, триггер `overdose`), `openai_provider.py`, `openrouter_provider.py` (httpx/openai libs). Богаче по возможностям, но тянет pydantic/httpx/openai — в prism намеренно срезано до нуля зависимостей.

## 6. Prompt infrastructure

Prism **[OBSERVED]**:

- 6 версионированных шаблонов в `src/prism/slice/prompts/` (имя файла = версия): `generator-v1`, `generator-rift-v0`, `judge-v1`, `judge-rift-v0`, `360-v1`, `360-rift-v0`.
- Загрузка: `slice/prompts.py` — извлекает ```text-блок с плейсхолдерами `{source} {task} {trajectory} {candidates}`; шаблоны в package-data.
- Выбор шаблона захардкожен в `generator.py`/`judge.py` по `(mode, profile)`; там же дублируются 4 почти идентичных блока «ФОРМАТ ОТВЕТА» (копипаста ~120 строк). **[OBSERVED]**
- Профили: practical (по умолчанию), RIFT (концептуальная дистанция, source anchor, механизм). Режимы: normal, 360.
- **Explore/Deep-промптов в коде нет.** Контракты Explore (NORMAL/RIFT/360/TRANSFER) и Deep (DEEPEN/RETURN_TO_EXPLORE/LEVER) описаны только в `docs/BEERLIGHT-PRISM-MASTER-STATE.md` из неслитой ветки `origin/docs/master-state-v0`. **[OBSERVED]**

## 7. Runtime infrastructure

- CLI (`cli.py`, 644 строки): `run`, `run-json`, `inspect` (--show-pool/--show-judge/--show-errors/--calibrate), `session create/run/update/event/outcomes/show`, `trajectory show/apply`, `handoff`, `doctor` (--smoke), `demo`. **[OBSERVED]**
- Вход: файл через CLI; машиночитаемый JSON через `run-json` (контракт v0, детерминированные exit-коды 0–7). HTTP-сервера нет. **[OBSERVED]**
- Состояние сессии: `original.md` (иммутабельный), `current.md`, `trajectory.md` (6-секционный шаблон), `session.json`, `events.jsonl` (append-only, fsync), `runs/<run_id>/`. **[OBSERVED]**
- Артефакты прогона (`prism-runs/<run_id>/`): `metadata.json` (v1), `request.json`, `input.md`, `candidates.json`, `judge.json`, `output.md`, при full-уровне `raw-generator.txt`, `raw-judge.txt`, `prompt-generator.txt`, `prompt-judge.txt`, `prompt-repair.txt`; плюс `trajectory-input.md`, `trajectory-update.md`. **[OBSERVED]**
- Логирование: **отсутствует** (print-based вывод); сериализация: JSON + markdown, атомарные записи через `os.replace`. **[OBSERVED]**
- Инспектируемость: `inspect.py` различает три множества (shown из `output.md`, kept-hidden, dropped) + `calibration_report` («strong dropped» = drop/merge при novelty=real и fidelity=grounded). **[OBSERVED]**

## 8. Test / eval infrastructure

### Prism (запущено) **[OBSERVED]**

- Команда: `/tmp/prism-venv/bin/python -m pytest -q -rs` (venv вне репо).
- Результат: **165 passed, 1 skipped** (0.3–0.5 с). Skip: `tests/test_runtime_trace.py:33 — "No legacy smoke traces available"` (условный тест чтения v0-трейсов, фикстур нет).
- 13 файлов тестов: runtime service/contracts/events/outcomes/session/trace/trajectory/rift/demo/doctor, provider http/opencode, slice validate. Детерминированные: fake-транспорт через monkeypatch, без сетевых вызовов.
- Фикстуры: `src/prism/demo_fixtures/demo_run/` — записанный v1-трейс для `prism demo` (без LLM).
- Чего нет: mock-провайдера как модуля, batch-раннера, golden-тестов, рубрик, скоринга, генерации отчётов (кроме `calibration_report`), корпуса входов.

### Соседние репо (НЕ запускалось) **[OBSERVED]**

- Причина: требуют установки зависимостей (textual/httpx/openai/pydantic/respx) и/или могут писать артефакты; в `beerlight-terminal` к тому же грязное дерево. В рамках read-only аудита — пропущено осознанно.
- `evals/` в обоих beerlight-репо: `evals.json` (манифест + `pass_condition`), `rubric.md` (критерии 1/5/9), `golden_outputs.md`, `vibe_checks.md`, `failure_modes.md`, `weak_outputs.md`, `trace_codes.md`, `score_log.csv`. **Но `evals.json` объявляет `"package": "narrative-build-engine"`**, rubric — про фазы билда/Bukowski-режим: это eval-инфраструктура другого продукта (Aylett/narrative engine), не Prism. Структура — переиспользуемый образец, содержимое — нет.
- `harness/` в beerlight-репо: `drift_detector.py` (218 стр.), `waffle_analyzer.py`, `fantikometer.py`, `overdose.py`, `bestiary_builder.py` — оценка **стилевого дрейфа** текста (hedge/repetition/verdict), не семантического acceptance.
- `llm/mock_provider.py` — готовый детерминированный mock (canned по hash-фингерпринту) — кандидат на порт в prism. **[INFERRED: пригодность]**
- Тесты beerlight-terminal (~40 файлов): drift_detector, overdose, waffle_analyzer, providers, provider_error_isolation, bestiary_*, chaos, gates, slice_validate и др. — есть чему учиться, но это другой контур.

## 9. Legacy map

| Элемент | Где | Используется execution path? |
|---|---|---|
| `MAX_CARDS = 3` | `service.py`, `inspect.py`, `session.py` | **Да** — кап показа, инвариант |
| top-3 selection | `service.py` (`cards_out = raw_cards[:MAX_CARDS]`) | **Да** |
| `inspect` | CLI + `inspect.py` | **Да** — публичная команда |
| `trajectory` | `session.py`/`trajectory.py` + CLI `trajectory show/apply` | **Да** — вход для 360, накопление в сессии |
| `export`/`handoff` | CLI `handoff`, `export_trajectory` | **Да** (команда handoff) |
| session-команды | `session create/run/update/event/outcomes/show` | **Да** |
| видимый внутренний пул | `inspect --show-pool`, `candidates.json` всегда пишется | **Да** — по дизайну |
| Chat Edition | в prism **отсутствует** | —; существует как sibling-репо `beerlight-terminal-wt-chat-edition` (+ `chatgpt/` adapter pack) |
| automatic Deep | в коде **отсутствует**; только контракты в master-state доке (неслитая ветка) | Нет |
| старые schemas | trace v0 — read-only совместимость (`read_trace_metadata`), писателя v0 нет | Только чтение старых трейсов |
| старые runtime-артефакты | `demo_fixtures` (v1), `beerlight-runs/`/`beerlight-sessions/` в .gitignore «для совместимости» | Нет (только demo) |
| remote-ветки с доками, не влитые в main | `docs/master-state-v0` (конституция), `docs/three-model-analysis-prompts` (цепочка GPT/Kimi/Fable), `docs/chat-summary-current-state` (**== main, пустая**) | Нет — код их не видит |

Вывод: legacy в execution path почти нет — v0-чтение и «показанный пул» — осознанный дизайн, не долг. **[OBSERVED]**

## 10. Классификация для acceptance harness

**Open question:** целевая семантика «Explore acceptance harness / Deep acceptance harness / local AUTO profile harness» в репо не определена (см. §12). Классификация ниже — по пригодности как тестово-оценочного субстрата.

### REUSE

| Компонент | Зачем harness'у |
|---|---|
| `slice/validate.py` (extract_json, схемы, repair-промпты, expected_ids) | детерминированный разбор/проверка выходов моделей — ядро любой проверки |
| `slice/provider.py` (http/opencode, retry, TransportError) | гонять реальные модели из harness'а без переписывания транспорта |
| `service.run()`/`run_json` + exit-коды | единая точка запуска прогона, артефакты на диск |
| trace v1 + `inspect.py` (shown/kept-hidden/dropped, calibration) | сбор и сравнение исходов прогонов, базовый отчёт о ложных срезах |
| session + trajectory | состояние между прогонами для acceptance 360/Deep-семантики |
| demo_fixtures + `demo.py` | офлайн-прогон без API — прототип recorded-replay для harness'а |
| `doctor.py` | preflight для batch-прогонов (транспорт/модели/директории) |
| `llm/mock_provider.py` (chat-edition) | детерминированный mock — см. ADAPT |

### ADAPT

| Компонент | Адаптация |
|---|---|
| `mock_provider.py` | порт в `prism.slice` без pydantic: canned-ответы по hash-фингерпринту + генеративные кандидаты для разных profile/mode; даст offline harness |
| evals/-структура (beerlight) | образец: manifest + rubric + golden + vibe_checks + score_log + pass_condition; контент переписать под семантику Prism (source-anchor, operator diversity, RIFT distance, 360 non-repeat) |
| `harness/drift_detector` + `waffle_analyzer` | если acceptance включает «не декоративный RIFT»/«no waffle» — метрики стилевого дрейфа применимы к карточкам |
| `calibration_report` (inspect) | расширить до регулярного eval-отчёта по корпусу |
| `run-json` + exit-коды | субстрат batch-раннера: цикл по inputs × profile × mode |

### IGNORE_LEGACY

- trace v0 read-path — читать старые трейсы, не строить на нём;
- TUI/web/spark/storage/timuroki/app_legacy (beerlight-репо) — другой продукт (стилевой харнесс), не субстрат;
- evals/-контент narrative-build-engine — содержимое чужое, брать только структуру;
- remote-ветка `docs/chat-summary-current-state` — пустой указатель (== main), не трогать.

### MISSING

- mock/recorded транспорт **внутри prism**;
- batch runner (inputs × profiles × modes → трейсы → отчёт);
- golden-корпус и рубрика acceptance для Prism-семантики;
- генерация eval-отчёта (сейчас только `calibration_report`);
- захват `usage`/токенов из API-ответа (только `chars//4`);
- логирование;
- Deep-контракты (DEEPEN/RETURN_TO_EXPLORE/LEVER) в коде;
- AUTO profile — отсутствует полностью;
- определение «acceptance» для Explore/Deep/AUTO.

## 11. Risks

1. **Конституция вне main.** Продуктовые контракты (Explore/Deep) существуют только в неслитой ветке `origin/docs/master-state-v0`; код и доки уже расходятся (в доке — TRANSFER/DEEPEN/LEVER, в коде — только normal/360/rift). Если ветки не влить/не архивировать — harness будет строиться по устаревшей теории. **[OBSERVED]**
2. **Eval-инфраструктура в непубличных sibling-репо без remote.** Риск потери/расхождения; единственная копия `mock_provider` и harness-метрик живёт там. **[OBSERVED]**
3. **`beerlight-terminal` — грязное дерево** (`.ai/STATE.md`, `.ai/SESSION_LOG.md`). Любая работа в нём обязана сохранять эти изменения. **[OBSERVED]**
4. **Нет injection-точки провайдера** — только env; для batch-прогонов с разными моделями на один запуск это ограничение (обход: env на подпроцесс). **[INFERRED]**
5. **Дублирование** (repair-логика generator/judge, JSON-формат-блоки ×4) — при расширении на Explore/Deep-промпты копипаста вырастет. **[OBSERVED]**
6. **Cost/usage-слепок** — без чтения `usage` нельзя контролировать бюджет batch-прогонов; эвристика `chars//4` систематически врёт на длинных промптах. **[OBSERVED]**
7. Хардкод дефолтной модели `opencode-go/deepseek-v4-pro` и отсутствие HTTP-сервера (вход только файлом) — ограничения, не дефекты; для harness'а достаточно. **[OBSERVED]**

## 12. Minimal substrate for Explore acceptance harness

**[RECOMMENDED]** (по приоритету):

1. **Зафиксировать семантику acceptance** — влить или заархивировать doc-ветки; утвердить, что проверяем: (a) структурную валидность, (b) source-anchor (basis реально опирается на текст), (c) разнообразие операторов, (d) для RIFT — наличие механизма и расстояния, (e) для 360 — неповторение траектории. Без этого пункта harness — каркас без критериев.
2. **Офлайн-субстрат:** порт `mock_provider` (или recorded-replay по образцу demo_fixtures) → прогоны без API.
3. **Batch runner:** цикл inputs × profile (practical/rift) × mode (normal/360) через `run_json`; сбор `trace_dir`; exit-коды как сигналы.
4. **Проверки поверх трейса:** reuse `validate.py`; anchor-проверка (лексемы basis в источнике, старт с substring-метрики); diversity (операторы/семейства в пуле); 360-неповторение (overlap с trajectory.md).
5. **Отчёт:** по образцу `evals/`: score_log.csv + pass_condition + «strong dropped» из `calibration_report`.

Всё это — без новых runtime-зависимостей и без правки ядра (надстройка над `run_json`/`inspect`).

## 13. Exact next implementation boundary

**Следующий минимальный безопасный срез (после решения по §12.1):**

- в `prism`: новый модуль `slice/mock.py` (canned-провайдер по образцу chat-edition, без pydantic) + загрузка через `PRISM_TRANSPORT=mock` или тестовый хук — **или** recorded-replay на demo_fixtures, если mock откладывается;
- скрипт/команда `prism harness dry-run <inputs.json>` — прогон корпуса через существующий `run_json`, трейсы в `prism-runs/`;
- отчёт-таблица: input × profile × mode → status, cards, anchor-fail, diversity, calibration-подозрительные;
- тесты на новое: dry-run с mock на 2–3 фикстурах.

Граница: **не** трогать service/prompts/контракты; **не** добавлять Deep/AUTO; **не** мигрировать beerlight-репо.

## 14. Explicit non-work

- Миграция/слияние beerlight-terminal/chat-edition в prism;
- реализация Deep-контрактов и AUTO profile;
- TUI/web/серверные транспорты;
- редизайн промптов;
- удаление legacy (v0-чтение, gitignore-пути, пустые ветки);
- commit/push/PR — единственное изменение дерева: этот файл.

---

## Verdict

**REPO_NEEDS_SMALL_ADAPTATION.**

Код-субстрат (транспорт, валидация, трейсы, инспектируемость, тесты) готов и здоров; для Explore acceptance harness'а не хватает малого и несложного: mock/recorded-транспорт, batch-раннер, рубрика и отчёт — всё надстройкой, без правок ядра. Основной риск — не код, а процесс: продуктовая конституция и eval-образцы лежат вне публичного репо, а семантика «acceptance» нигде не утверждена. Deep и AUTO — не «адаптация», а отдельные продуктовые волны.
