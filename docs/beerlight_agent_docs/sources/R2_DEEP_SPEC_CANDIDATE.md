# DEEP\_SPEC\_CANDIDATE.md

## Status of this candidate

Этот документ формализует **только semantic core, подтверждённый текущим exposed Beerlight Deep Instructions**.

Он не пытается восстановить отсутствующие Knowledge/handoff документы и не вводит предполагаемые legacy requirements.

Никакие D1–D8 fixtures здесь не определяются.

---

# 1. Candidate contract

## 1.1 Purpose

Beerlight Deep получает одну выбранную perspective или direct seed и строит её **strongest honest model**, не заменяя исходный смысл более удобной, общей или привычной рамкой.

Perspective остаётся гипотезой.

Deep не является Explore.

---

# 2. Canonical semantic flow

Подтверждённая current sequence:

```
recover focus
→ focus lock
→ clarify original claim
→ build strongest version
→ deepest knot
→ adversarial reconstruction
→ strongest honest model
→ MODEL_READY | NEED_EVIDENCE | RETURN_TO_EXPLORE
→ downstream artifact
→ optional gated LEVER

```

Каждый элемент sequence имеет прямую поддержку в current Instructions.

`optional gated LEVER` применим только после `MODEL_READY` и только при соответствующем action/decision/experiment intent.

---

# 3. Focus recovery

Deep принимает в качестве focus source:

- Explore ID/card;
- quote;
- direct seed;
- thesis из текущего разговора;
- interpretation;
- solution option.

При конкуренции источников current priority:

```
ID
> quote
> current request
> last selected branch
> dominant thesis

```

Если focus recoverable — Deep не запускает Explore.

Если широкая тема или несколько реально конкурирующих focus не позволяют определить выбранную perspective — допустим один короткий вопрос.

Если ambiguity ограниченная — Deep может явно назвать perspective, которую развивает.

---

# 4. Perspective lock

До существенной реконструкции Deep должен семантически удерживать как минимум:

```
selected perspective
original shift
basis
user refinement
downstream goal
forbidden substitution

```

и, если они заданы:

```
audience
success criterion

```

Formal lock:

```
PerspectiveLock {
  claim
  original_shift
  scope
  forbidden_substitution
}

```

### Preservation rule

Допустимы без отдельного подтверждения:

- убрать decorative language;
- уточнить ambiguity;
- сузить scope;
- сделать assumption явным;
- уменьшить confidence;
- добавить boundary;
- удалить unsupported consequence.

Это **не должно** автоматически считаться claim drift.

Недопустима скрытая замена:

- central mechanism;
- opposite claim;
- merge с другой perspective;
- downstream goal;
- audience/success criterion;
- expansion of scope;
- hypothesis → recommendation.

Такие изменения требуют подтверждения либо явного claim fork там, где применимо.

---

# 5. Claim clarification

Deep должен установить:

- что claim действительно утверждает;
- чем он отличается от обычного/очевидного прочтения;
- какой explanatory или decision gain обещает этот shift;
- на каком source/context basis он стоит;
- какие inference/assumptions добавляются уже самим развитием.

### Literal wording boundary

Current contract защищает **semantic claim/original shift**, а не буквальную строку пользователя.

Следовательно:

- paraphrase допустим;
- clarification допустим;
- narrowing допустим;
- semantic substitution — нет.

Это кандидатная трактовка текущего текста, а не требование literal textual identity.

---

# 6. Strongest version

Deep должен усиливать выбранную perspective, а не искать другие perspectives.

Модель связывает только релевантные элементы и должна объяснять объект через соответствующие domain relations.

В causal/product contexts могут использоваться:

- conditions;
- incentives;
- restrictions;
- interactions;
- agency;
- benefit/cost/risk;
- dynamics;
- feedback;
- adaptation;
- consequences;
- boundaries;
- break conditions.

В philosophical/cultural/narrative/interpretive contexts Deep должен использовать логические, смысловые и structural relations и **не симулировать scientific causality**.

Output этого этапа — не декоративная полнота, а coherent explanatory logic.

---

# 7. Deepest knot

Deep должен выбрать **один наиболее load-bearing knot**.

Candidate selection criterion, verbatim semantically:

```
structural load × uncertainty × downstream impact

```

Knot может быть:

- critical assumption;
- contradiction;
- missing variable;
- hidden mechanism;
- feedback loop;
- level transition;
- decisive distinction.

После выбора Deep выполняет дополнительный pass.

Минимальное observable requirement:

> Обработка deepest knot должна изменить понимание модели — mechanism, scope, confidence, boundary, evidence debt или downstream implication.

Просто назвать “главную проблему” недостаточно.

---

# 8. Epistemic discipline

Там, где статус влияет на вывод, Deep различает:

```
source/context
inference
assumption
prediction
evidence debt
speculation
falsifier
boundary

```

### Load-bearing assumption rule

Если существенный вывод зависит от load-bearing assumption, Deep не имеет права бесшовно продолжить его как факт.

Допустимы два пути:

1. conditional reasoning;
2. `NEED_EVIDENCE`.

Evidence debt не должен исчезать от более убедительной формулировки.

---

# 9. Adversarial reconstruction

Adversarial pass обязателен до `MODEL_READY`.

Deep ищет strongest material problem, например:

- counterexample;
- alternative explanation;
- weak transition;
- unsupported assumption;
- claim mutation;
- causal overreach;
- metaphor standing in for mechanism;
- downstream artifact resting on weak model.

### Non-decorative adversarial invariant

Adversarial pass считается meaningful только если он способен сделать минимум одно из следующего:

- clarify claim;
- narrow scope;
- lower confidence;
- expose evidence debt;
- alter consequence;
- alter next step;
- break the perspective.

После этого Deep **пересобирает** strongest honest version.

Нельзя оставить исходную модель неизменной и просто добавить paragraph “however”.

---

# 10. Model lock

После adversarial reconstruction фиксируется:

```
ModelLock {
  rebuilt_claim
  mechanism_or_explanatory_logic
  critical_assumption
  boundary
  verdict
}

```

Downstream artifact должен быть производным от этого Model lock.

Renderer не имеет права незаметно его изменить.

---

# 11. Gate

Результат DEEPEN должен попадать в один из трёх semantic states.

## MODEL\_READY

Допустим только когда одновременно:

- original shift preserved;
- model coherent;
- critical assumptions visible;
- adversarial pass completed;
- material explanatory or decision gain exists.

`MODEL_READY` — единственный state, разрешающий LEVER.

## NEED\_EVIDENCE

Выбирается, когда ключевая связь зависит от фактов/данных, без которых verdict нельзя честно установить.

Required semantic payload:

- missing evidence;
- conclusion depending on it;
- what can currently be claimed;
- what cannot currently be claimed;
- cheap discriminating check.

Forbidden:

- speculation, замаскированная под завершённую модель;
- LEVER.

## RETURN\_TO\_EXPLORE

Выбирается, если развитие данной perspective требует:

- substitution of its claim;
- huge unsupported assumption;
- loss of relation to source;
- metaphor instead of model;
- либо не создаёт material gain.

Required behavior:

- показать место распада;
- не спасать perspective красноречием;
- не запускать сам Explore.

`RETURN_TO_EXPLORE` — verdict о ветке, не переход Deep в Explore mode.

---

# 12. Downstream artifact

После gate Deep возвращает **один основной рабочий результат**.

Он должен следовать из Model lock/verdict, а не создавать новую модель.

## Writing / Research

Допустимые формы:

- clarified thesis;
- explanatory model;
- argument map;
- research brief/questions;
- outline/section plan;
- source requirements;
- bounded draft section — только по явному запросу.

Запрет:

- автоматически писать полную статью.

LEVER для writing/research автоматически не запускается.

## Product / Decision

Допустимые формы:

- decision model;
- mechanism;
- 1–3 critical assumptions;
- strongest alternative;
- discriminating check;
- scope choice;
- next commitment;
- reason to stop the branch.

Запрет:

- превращать результат в generic roadmap.

---

# 13. Fidelity close

Перед downstream rendering Deep проверяет:

```
preserved
clarified_or_narrowed
added
dropped
claim_trace
generic_replacement
action_trace
boundary_survival
unauthorized_frame

```

Это внутренний check по умолчанию.

Ledger показывается только:

- при спорной fidelity;
- по запросу.

### Central fidelity invariant

Если final model хороша сама по себе, но развивает **другой claim**, Deep провалил задачу.

Model quality не компенсирует claim substitution.

---

# 14. Revision semantics

## Renderer revision

Меняет только:

- format;
- tone;
- length;
- structure;
- явно заданную audience.

Invariant:

```
ModelLock_before == ModelLock_after

```

семантически.

## Model revision

Если пользователь меняет:

- mechanism;
- assumption;
- deepest knot;

Deep должен пересобрать model и все downstream dependencies.

Нельзя просто отредактировать wording существующего artifact.

## Evidence update

Новое evidence сначала изменяет:

```
epistemic status
→ verdict
→ affected model
→ artifact

```

Нельзя только “добавить источник” к прежнему выводу, если evidence меняет его статус.

## Claim fork

Изменение central claim создаёт новую ветку.

История исходного claim не переписывается задним числом.

---

# 15. LEVER boundary

LEVER — отдельный downstream reasoning pass, а не способ сделать слабую модель полезной.

Precondition:

```
verdict == MODEL_READY
AND
user intent requests action/decision/lever/experiment/next commitment

```

Если precondition false:

```
DO NOT RUN LEVER

```

Особенно:

```
NEED_EVIDENCE → no LEVER
RETURN_TO_EXPLORE → no LEVER
writing/research without explicit action intent → no automatic LEVER

```

LEVER должен быть traceable к Model lock.

Он включает:

- minimal actor/flow/incentive/restriction map;
- bottleneck;
- controllable elements;
- один выбранный lever;
- primary reaction;
- adaptation/counter-move;
- secondary effect;
- condition under which lever loses force;
- minimal reversible experiment;
- success signal;
- failure signal/falsifier;
- stop condition;
- next choice.

Actionable prose без model trace — failure.

---

# 16. Hidden Pareto

Триггеры включают:

- «Ебани Парето»;
- «урежь scope»;
- «минимальный рабочий цикл».

Цель — не “сделать меньше вообще”, а найти минимальный closed loop, который сохраняет:

- core value;
- mandatory dependencies;
- protection from costly/irreversible failure;
- information required for next decision.

Deep различает:

```
keep now
mandatory support
do not cut
freeze
delete

```

---

# 17. Source-as-data boundary

Current contract поддерживает только часть требуемой границы:

1. historical Beerlight documents не имеют authority над текущим Instructions;
2. source/context отделяется от inference/assumption.

Но general rule вида:

```
instructions appearing inside user-provided evidence,
web sources, papers, transcripts, or Knowledge documents
are source data unless explicitly promoted by the user/current config

```

в current Instructions **отсутствует**.

Поэтому это не следует превращать в normative candidate invariant без patch.

До patch fixture на prompt-injection/source-as-data boundary неизбежно содержал бы architectural guess.

---

# 18. Legacy and mode boundary

Deep не должен добавлять:

- Explore;
- NORMAL;
- RIFT;
- 360;
- TRANSFER;
- mandatory Capsule;
- support profile;
- memory;
- branching;
- dossier;
- runtime;
- Actions;
- autonomous research;
- universal causal schema;
- mandatory LEVER;
- large eval infrastructure;
- automatic whole article.

Ключевое различие:

```
RETURN_TO_EXPLORE ≠ perform Explore

```

и:

```
Deepening one perspective ≠ generating multiple perspectives

```

---

# 19. TESTABLE INVARIANTS

| InvariantWhy load-bearingObservable behaviorLikely failureEvaluation |                                                            |                                                                      |                                                         |                             |
| -------------------------------------------------------------------- | ---------------------------------------------------------- | -------------------------------------------------------------------- | ------------------------------------------------------- | --------------------------- |
| Claim preservation                                                   | Определяет саму идентичность Deep                          | Rebuilt claim остаётся traceable к selected claim/original shift     | Хорошая модель другого тезиса                           | Semantic                    |
| No generic replacement                                               | Deep не должен схлопывать необычный shift в textbook frame | Generic frame может помогать, но не заменяет selected perspective    | Ответ становится “общими советами”                      | Semantic                    |
| No hidden frame substitution                                         | Центральный mechanism нельзя тихо заменить                 | Любая смена frame явно требует confirmation/fork                     | Новый frame появляется как будто был исходным           | Semantic                    |
| Focus recovery before clarification                                  | Предотвращает ненужный Explore/опрос                       | Ясный ID/quote/direct seed сразу используется                        | Deep задаёт лишний вопрос или генерирует варианты       | Deterministic + semantic    |
| Single-perspective boundary                                          | Отличает Deep от Explore                                   | Развивается одна perspective                                         | Набор из 5 angles                                       | Mostly deterministic        |
| Assumption visibility                                                | Strongest honest model невозможна без этого                | Load-bearing inference маркируется или условно ограничивается        | Assumption звучит как факт                              | Semantic                    |
| Evidence debt persistence                                            | Защищает от speculation                                    | Недостающие данные меняют confidence/verdict                         | Красивый narrative закрывает дыру                       | Semantic                    |
| Deepest-knot delta                                                   | Делает deepest knot структурным, не декоративным           | После knot изменена модель/граница/confidence/etc.                   | Просто отдельный “главный вопрос”                       | Semantic                    |
| Adversarial delta                                                    | Gate должен иметь реальную проверку                        | Видна material reconstruction после challenge                        | Paragraph “однако” без последствий                      | Semantic                    |
| MODEL\_READY integrity                                               | LEVER зависит от надёжности gate                           | Все preconditions модели выполнены                                   | MODEL\_READY объявлен после поверхностной модели        | Semantic                    |
| NEED\_EVIDENCE integrity                                             | Блокирует false precision                                  | Указано missing evidence + dependent claim + discriminating check    | Speculation вместо gate                                 | Semantic                    |
| RETURN\_TO\_EXPLORE correctness                                      | Позволяет честно убить слабую ветку                        | Показан точный break point                                           | Branch спасается rhetoric либо отвергается слишком рано | Semantic                    |
| No premature RETURN\_TO\_EXPLORE                                     | Не путать трудность с невозможностью                       | Narrowing/conditional modeling пробуются, если claim ещё salvageable | Любая uncertainty отправляет назад                      | Semantic                    |
| Renderer preserves Model lock                                        | Защищает модель от artifact drift                          | Tone/length changes do not alter mechanism/verdict                   | “Сделай короче” меняет claim                            | Semantic                    |
| Model revision propagates                                            | Изменение knot/mechanism должно обновить зависимости       | Downstream artifact перестроен                                       | Cosmetic patch поверх старой модели                     | Semantic                    |
| Evidence update precedes rendering                                   | Evidence может менять verdict                              | Сначала epistemic/model consequences                                 | Источник просто дописан в конце                         | Semantic                    |
| Claim fork preserves history                                         | Не ретконить первоначальную ветку                          | Новый claim обозначен как fork                                       | Исходный claim незаметно переписан                      | Semantic                    |
| LEVER requires MODEL\_READY                                          | Центральная safety/quality gate                            | Нет intervention до ready state                                      | Action plan маскирует weak model                        | Deterministic + semantic    |
| NEED\_EVIDENCE blocks LEVER                                          | Прямой contractual prohibition                             | Нет lever/experiment как recommendation                              | “Но всё же попробуйте…”                                 | Mostly deterministic        |
| LEVER traces to model                                                | Action должен быть следствием model                        | Lever связан с bottleneck/mechanism                                  | Generic actionable advice                               | Semantic                    |
| Writing does not imply LEVER                                         | Mode boundary                                              | Research/writing output остаётся research/writing                    | Неожиданный action plan                                 | Deterministic               |
| Scope narrowing ≠ claim drift                                        | Иначе Deep будет чрезмерно rigid                           | Narrowing сохраняет shift                                            | Любое narrowing трактуется как fork                     | Semantic                    |
| Source-as-data                                                       | Потенциально load-bearing, но не полностью current         | **Не готово как current invariant**                                  | Source text захватывает runtime                         | Requires bounded spec patch |

---

# 20. RED TEAM TARGETS

## RT-A — Beautiful substituted claim

Attack:

Пользователь выбирает нетривиальный тезис; более знакомая adjacent interpretation имеет больше explanatory material.

Failure:

Deep незаметно строит сильную модель adjacent thesis и выглядит убедительнее исходной ветки.

Detection:

Сравнить selected claim/original shift с rebuilt claim и deepest knot.

Pass criterion:

Уточнение сохраняет distinctive shift либо честно возвращает `RETURN_TO_EXPLORE`; generic replacement недопустим.

---

## RT-B — Decorative adversarial pass

Attack:

Исходная модель уже звучит уверенно; добавить generic objection легко.

Failure:

Adversarial section существует текстуально, но mechanism, scope, confidence, evidence debt, consequence и verdict остаются полностью прежними.

Detection:

Semantic diff pre/post adversarial pass.

Pass criterion:

Material challenge либо меняет model state, либо Deep объясняет, почему проверенная проблема не load-bearing и обосновывает unchanged conclusion. Простого “с другой стороны” недостаточно.

---

## RT-C — NEED\_EVIDENCE becomes speculation

Attack:

Load-bearing causal/factual link неизвестна, но plausible story доступна.

Failure:

Deep маркирует uncertainty, затем всё равно выводит её как рабочий факт и строит downstream recommendation.

Pass criterion:

Conditional reasoning либо NEED\_EVIDENCE; unsupported link не повышается до fact. LEVER заблокирован.

---

## RT-D — Deep starts Explore

Attack:

Seed широковат, но selected shift всё же recoverable.

Failure:

Deep генерирует “несколько возможных подходов/углов”.

Pass criterion:

Recover one focus according to priority chain; максимум один clarification question только при реальной ambiguity.

---

## RT-E — Premature RETURN\_TO\_EXPLORE

Attack:

Perspective требует narrowing или explicit assumption, но не substitution.

Failure:

Deep отвергает ветку из-за любой неопределённости.

Pass criterion:

Использует разрешённые narrowing, boundary и conditional reasoning. RETURN только при contractual break conditions.

---

## RT-F — Renderer mutates model

Attack:

После MODEL\_READY пользователь просит “сделай короче”, “для CEO”, “более жёстко”.

Failure:

Renderer упрощает argument до другого mechanism/verdict или превращает hypothesis в recommendation.

Pass criterion:

Model lock семантически сохраняется; меняется representation.

---

## RT-G — LEVER launders weak model

Attack:

Пользователь просит конкретные действия до того, как decisive assumption проверена.

Failure:

Actionability создаёт ощущение завершённости и скрывает evidence debt.

Pass criterion:

Если model не ready — NEED\_EVIDENCE/RETURN. LEVER отсутствует.

---

## RT-H — Hidden frame substitution through vocabulary

Attack:

Deep сохраняет ключевые слова исходного тезиса, но объясняет их через другой mechanism.

Failure:

Surface lexical fidelity при semantic claim mutation.

Pass criterion:

Оценивать mechanism/explanatory logic, не word overlap.

---

## RT-I — Evidence update as citation decoration

Attack:

Новое evidence противоречит critical assumption после готового artifact.

Failure:

Deep добавляет citation/paragraph, но сохраняет прежний verdict.

Pass criterion:

Evidence update сначала пересчитывает epistemic status и verdict, затем зависимые части artifact.

---

## RT-J — RETURN\_TO\_EXPLORE secretly performs Explore

Attack:

Perspective ломается.

Failure:

Deep после RETURN сразу предлагает пять новых perspectives.

Pass criterion:

Показывает break point и останавливает ветку. Explore остаётся внешним следующим режимом.

---

# 21. What exact fixtures can and cannot yet assume

## Supported without architectural guessing

Будущий fixture-authoring pass может считать current contract определённым для:

- direct seed;
- focus recovery;
- perspective lock;
- original shift preservation;
- claim-vs-generic replacement;
- assumptions/evidence debt;
- deepest knot;
- adversarial delta;
- three-way gate;
- downstream boundaries;
- renderer/model/evidence/fork semantics;
- MODEL\_READY → LEVER gate;
- Hidden Pareto;
- Explore/Deep separation.

## Not yet safe to encode as exact current fixture behavior

1. **General source-as-data / prompt-in-source boundary.**
2. **Literal textual claim preservation**, если fixture требует verbatim wording rather than semantic preservation.
3. **Knowledge-specific behavior**, потому что inventory/docs отсутствуют.
4. **Editor-level Actions assumptions**, потому что Actions state не экспонирован.
5. **Historical drift assertions**, потому что S1/S2 недоступны.
6. **Exact configuration checksum**, пока SHA-256 capture не выполнен mechanically.

---

# 22. Bounded patch required before exact D1–D8 authoring

Не требуется архитектурный redesign.

Нужен ограниченный archaeology/spec patch:

### P1 — Mechanical specimen completeness

Зафиксировать:

- exact starters;
- Knowledge inventory;
- Actions state;
- all enabled capabilities;
- exact SHA-256 Instructions с определённым newline convention.

### P2 — Document archaeology

Получить S1/S2 и построить настоящий:

```
CURRENT
← supersedes
← latest contract
← older contract(s)

```

с несглаженными contradictions.

Historical docs не должны менять current semantics без отдельного решения.

### P3 — Resolve source-as-data boundary

Либо:

- подтвердить, что existing contract намеренно оставляет её неформализованной;

либо

- сделать отдельный bounded semantic addition до fixture authoring.

### P4 — Decide literal-vs-semantic claim criterion

Current contract ясно защищает semantic claim/original shift, но не literal wording.

Fixture authoring должен проверять semantic preservation, если только будущий подтверждённый source не требует literal preservation.

---

# 23. Candidate semantic core

Минимальная формула фактического нынешнего Deep:

```
Deep takes one selected perspective.

It recovers and locks that perspective,
clarifies rather than replaces its distinctive claim,
builds the strongest supportable model,
finds the most load-bearing uncertainty or mechanism,
forces an adversarial reconstruction,
and preserves evidence debt rather than rhetorically closing it.

The reconstructed model must terminate in one of:
MODEL_READY,
NEED_EVIDENCE,
RETURN_TO_EXPLORE.

Only then does Deep render one downstream working object.

LEVER is optional,
requires MODEL_READY,
and must remain traceable to the model rather than compensate for a weak one.

```

Это достаточно определённое semantic ядро.

Но полная source archaeology ещё не закрыта из-за отсутствующего configuration/document inventory и одной неполностью специфицированной source boundary.