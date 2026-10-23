# api_pipeline — 매달 API 크레딧으로 돌리는 반복 생산 엔진

PubMed 논문 후보를 찾고 → Message Batches API(50% 할인)로 초안을 한꺼번에 쓰고 → 편별 md 로 저장하고 → 초록 원문과 대조해 어긋난 곳만 알려 줍니다.
파이썬 3.9 이상, 외부 패키지 없이 표준 라이브러리만 씁니다.

## 준비

```bash
export ANTHROPIC_API_KEY=...     # 키는 이 환경변수에서만 읽습니다. 파일·로그에 쓰지 않습니다.
export NCBI_API_KEY=...          # 선택. 있으면 PubMed 조회가 빨라집니다.
```

처음 한 번, 지금까지 쓴 글의 PMID 를 `exclude_pmids.txt` 에 한 줄에 하나씩 적어 주세요.

## 한 번에 돌리기

```bash
python3 run_queue.py             # 보충 → 제출 → (끝난 배치) 수집 → 검수
python3 run_queue.py --wait      # 배치가 끝날 때까지 기다렸다가 수집·검수까지
python3 run_queue.py --steps collect,factcheck   # 제출해 둔 배치를 나중에 수집
python3 run_queue.py --test      # 키 없이 전체 흐름 시험
```

배치는 보통 몇 분~몇 시간(최대 24시간) 걸립니다. 처리 중인 배치가 있으면 새로 제출하지 않으므로 같은 명령을 여러 번 실행해도 됩니다.

## 단계별 스크립트 (모두 `--test` 시험 모드 있음)

| 단계 | 스크립트 | 하는 일 | 결과물 |
|---|---|---|---|
| 1 | `topic_refill.py` | 강아지·고양이·펫로스 최근 2년 논문을 esearch·efetch 로 찾아 제외 목록을 거르고, 주제별 미사용 후보가 `pool_per_topic` 보다 모자랄 때만 채움 | `out/candidates.md`, `out/abstracts/<PMID>.json` |
| 2 | `batch_submit.py` | 후보 × 종류별 프롬프트를 Batches API 로 제출 | `out/state.json` |
| 3 | `batch_collect.py` | 끝난 배치 결과를 편별 md 로 저장, 저장한 PMID 를 제외 목록에 덧붙임 | `out/drafts/<PMID>/<종류>.md` |
| 4 | `fact_check.py` | 숫자·용량·약 이름·강한 단정을 초록과 대조, 어긋난 곳만 목록화 (`--llm` 으로 연구 주장 대조 추가) | `out/factcheck/report_<날짜>.md` |
| 5 | `run_queue.py` | `queue.json` 하나로 1~4 연결 | — |

`--test` 는 `out/_test/` 에만 씁니다(실제 `exclude_pmids.txt` 는 읽기만 함). `batch_submit.py --test` 는 API 를 부르지 않고 요청 구성만 보여 주며, 수집기·검수기를 시험할 가짜 결과(일부러 틀린 숫자·약 용량 포함)를 만듭니다. `batch_submit.py --dry-run` 은 실제 후보로 요청만 구성해 보고 아무것도 기록하지 않습니다.

## queue.json

| 키 | 뜻 |
|---|---|
| `model` | 초안·`--llm` 검수에 쓸 모델 ID |
| `topics.queries` | 주제별 PubMed 검색식(`label`은 프롬프트에 들어가는 이름). 주제를 늘리려면 항목을 추가 |
| `topics.years`, `pool_per_topic` | 검색 기간(년), 주제별 미사용 후보 목표 개수 |
| `kinds` | 만들 글 종류와 종류별 `max_tokens`. 이름은 `prompts/<이름>.md` 와 일치해야 함 |
| `take` | 한 번에 제출할 논문(PMID) 수 — 요청 수는 `take × 종류 수` |
| `items` | 비어 있으면 후보에서 자동 선택. PMID 를 직접 적으면 그것만 제출 |

## 프롬프트와 규칙

`prompts/_rules.md` 는 모든 요청의 system 프롬프트입니다. 경어체, **초록에 없는 숫자 금지**, **초록에 없는 약 이름·용량 금지**, 관찰 연구의 인과 단정 금지, 의료 조언 금지, 근거 부족 시 `[작성 보류]` 를 박아 두었습니다. 종류별 형식은 `prompts/<종류>.md` 에서 고칩니다. 종류를 늘리려면 프롬프트 파일을 만들고 `queue.json` 의 `kinds` 에 이름을 추가하면 됩니다. 프롬프트 자리표시자: `{{TOPIC_LABEL}} {{TITLE}} {{JOURNAL}} {{YEAR}} {{PMID}} {{ABSTRACT}}`.

## 사실검수가 보는 것과 한계

- 숫자: 초안의 숫자가 초록에 없으면 표시. 허용: PMID, 발행연도, 줄머리 순번(`1/9`), 해시태그·URL·타임코드·목록 번호 안의 숫자.
- 용량: `5mg/kg` 같은 숫자+단위 조합이 초록에 없으면 표시.
- 약 이름: `drug_terms.txt` 의 이름(영문·한글)과 영문 약 접미사(-cillin, -azole 등)가 초록에 없으면 표시. 목록에 없는 한글 약 이름은 못 잡으니 `drug_terms.txt` 에 계속 보태 주세요.
- 강한 단정: 초록이 관찰·설문 연구인데 '증명·입증' 등이 있으면 표시.
- 초록의 숫자 표현(`one in three`)과 초안의 `3분의 1` 처럼 서로 다른 표기는 어긋남으로 표시됩니다. 표시된 곳은 사람이 확인하는 목록이지 자동 수정이 아닙니다.
- 문장 단위 연구 주장 대조는 `--llm` 으로만 합니다. 동기 호출이라 배치 할인이 적용되지 않습니다.

초안은 사람이 읽고 초록 원문과 한 번 더 확인한 뒤 쓰세요. 검수기가 아무것도 표시하지 않았다는 것은 위 항목에서 어긋남이 없다는 뜻이지, 글 전체가 사실이라는 보증은 아닙니다.
