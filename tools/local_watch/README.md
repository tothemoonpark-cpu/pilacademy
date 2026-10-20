# local_watch — 로컬 감시·알림 (Claude 토큰 불필요)

박근필 작가 Windows 노트북에서 Python 만으로 도는 감시 도구입니다. 외부 유료 서비스는 쓰지 않습니다(ntfy.sh·텔레그램 봇은 무료).

| 파일 | 역할 |
|---|---|
| `notify.py` | `notify(title, body, level)` — ntfy.sh / 텔레그램 / 설정 없으면 Windows 토스트 |
| `watch_runner.py` | 설정의 명령들을 주기대로 실행 → 출력에 `⛔`·`🔴`·`ALERT:` 가 있으면 알림. 같은 경보는 4시간에 1회 |
| `soomgo_watch.py` | 숨고 채팅(고객 차례 방)·받은 요청 5조건 판정 |
| `soomgo_parser.py` | HTML 파서·판정 함수(브라우저 없이 시험 가능) |
| `dedupe.py` | 중복 억제·상태 파일·`--send` 일일 상한 |
| `config/` | `*.example.json`(복사해 사용), `selectors.json`, `rules.json` |
| `install_windows.md` | 설치·schtasks 등록·로그인 상태 만들기 |
| `tests/` | 네트워크 없는 단위 테스트 |

## 테스트

```bash
python -m unittest discover -s tests -v     # pytest 불필요
```

## 알아둘 점 (솔직한 한계)

- **셀렉터는 미검증입니다.** 클라우드에서 숨고가 403이라 실제 화면을 본 적이 없습니다. `config/selectors.json` 은 초기값이고 `tests/fixtures/` 는 **합성 샘플**입니다. 처음 한 번 `--check-selectors` 로 맞춰야 합니다. 맞기 전까지 오탐/미탐이 날 수 있습니다.
- 채팅 목록 화면에 "누가 마지막에 말했는지" 표시가 없으면 `last_side` 가 `unknown` 이 되어 **알림에서 제외**됩니다(오탐 방지). 이 경우 `selectors.json` 의 마커를 맞추거나 `bubble` 을 지정하세요.
- 판정이 읽지 못한 조건(경과 시간·견적 수 등)은 **통과시키지 않습니다**(보수적).
- 5조건의 "구체 2개"(분량/납기/용도)는 `config/rules.json` 의 정규식 휴리스틱입니다. 실제 요청서를 보며 조정하세요.
- `--send` 는 기본 꺼짐이며, 켜도 `selectors.json` 의 `send.open_button` 을 눌러 견적 화면을 여는 데까지만 합니다(최종 제출 미구현, 하루 3건 상한·중복 방지). 견적 자동 발송은 숨고 약관·계정 리스크가 있어 의도적으로 넣지 않았습니다.
- 로그인 쿠키(`storage_state.json`)와 `config/notify.json` 은 비밀값이라 `.gitignore` 로 커밋되지 않습니다.
