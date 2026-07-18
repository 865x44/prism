# Prism

**Prism — усилитель мышления.** Даёшь ему черновик, пост, идею или любой текст —
получаешь 2–3 неочевидных, но рабочих угла, которые ты сам бы не увидел.

Это standalone-дистрибутив Beerlight Runtime v1: ноль зависимостей (чистый stdlib
Python ≥3.11), один CLI, никаких лишних сущностей.

## Как это работает

Один прогон = два LLM-вызова:

1. **Генератор** придумывает пул из 4–6 кандидатов-углов.
2. **Judge** жёстко оценивает каждого: новизна (real/partial/false),
   groundedness (grounded/mixed/distorted), действие (keep/merge/rescue/drop).

Тебе показываются **не более 3 финальных карточек**. Каждая карточка:

- **Сдвиг** — в чём новый угол;
- **На чём держится** — что в твоём тексте это подтверждает;
- **Что с этим сделать** — практический следующий шаг;
- **Граница** — чего карточка НЕ покрывает.

Если сильных углов нет, Prism честно скажет `NO_USEFUL_OUTPUT` вместо
натяжек. Полный пул и решения judge всегда доступны через `inspect`.

## Установка

```bash
git clone <этот репо>
cd prism
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

Или без клонирования: `pip install "git+https://github.com/<owner>/prism.git"`.

## Настройка LLM

Нужен любой OpenAI-compatible endpoint (OpenAI, OpenRouter и т.п.):

```bash
export PRISM_API_KEY="sk-..."                 # или OPENAI_API_KEY
export PRISM_BASE_URL="https://api.openai.com/v1"   # опционально
export PRISM_GENERATOR_MODEL="gpt-4o-mini"    # опционально
export PRISM_JUDGE_MODEL="gpt-4o-mini"        # опционально
```

| Переменная | Дефолт | Зачем |
|---|---|---|
| `PRISM_API_KEY` | — (fallback `OPENAI_API_KEY`) | ключ для HTTP-транспорта |
| `PRISM_BASE_URL` | `https://api.openai.com/v1` | любой OpenAI-compatible endpoint |
| `PRISM_GENERATOR_MODEL` | `gpt-4o-mini` | модель генератора |
| `PRISM_JUDGE_MODEL` | `gpt-4o-mini` | модель judge (можно сильнее) |
| `PRISM_TRANSPORT` | `auto` | `auto` / `http` / `opencode` |

Если ключа нет, Prism попробует fallback-транспорт `opencode` (CLI должен быть
установлен и залогинен; дефолтная модель `opencode-go/deepseek-v4-pro`).

## Быстрый старт

```bash
prism run draft.md --task "найди неочевидные углы для этого поста"
```

Прогон занимает 2–5 минут (2 LLM-вызова). Результат — на stdout, трассы —
в `beerlight-runs/<run_id>/`.

## Команды

```text
prism run <file> --task "..." [--mode normal|360] [--session <dir>]
prism run-json <request.json>          машинный вызов, JSON на stdout
prism inspect <run_id> [--show-pool] [--show-judge] [--calibrate]
prism session create <file> [dir]      начать сессию по тексту
prism session run <dir> --task "..."   прогон по текущему тексту сессии
prism session update <dir> "новый текст" | --file f.md
prism session event <dir> <run_id> <candidate_id> selected|applied|retained|reverted
prism session outcomes <dir>           сводка: что выбрано/применено/удержалось
prism session show <dir>
prism trajectory show <dir>            траектория мышления по сессии
prism handoff <dir> --output <dir>     экспорт сессии
```

## Сессии и 360

Сессия — это первоклассный контекст: текст, прогоны, выбранные углы, события,
траектория. Режим **360** (`--mode 360`) ищет углы ВНЕ уже исследованного
ландшафта — запускай его после пары обычных прогонов по сессии:

```bash
prism session create draft.md my-session
prism session run my-session --task "углы для поста"
# ...читаешь карточки, выбираешь:
prism session event my-session <run_id> c2 selected
# ...правишь текст:
prism session update my-session --file draft-v2.md
prism session run my-session --task "углы" --mode 360
prism session outcomes my-session
```

## Честность и ограничения

- Один run — 2 LLM-вызова по 2–5 минут; это фича (думать — долго), не баг.
- Результаты недетерминированы: та же входная пара может дать другой пул.
- Judge и генератор — одна модель в двух ролях; `inspect --calibrate` покажет
  «сильных отброшенных» (потенциальные false negatives).
- Prism не редактирует твой текст и не пишет за тебя — он находит углы.
  Разворот угла в текст — твоя работа (или отдельный инструмент).
