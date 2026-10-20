# Windows 설치 가이드 (local_watch)

Claude 토큰을 쓰지 않는 로컬 감시 프로그램입니다. Python 3.10 이상이 필요합니다.

## 1. 준비

```bat
cd C:\Users\본인\pilacademy\tools\local_watch
python -m pip install -r requirements.txt
python -m playwright install chromium
```

알림·`watch_runner.py` 만 쓸 거라면 pip 설치 없이도 동작합니다(표준 라이브러리만 사용).

## 2. 설정 파일 만들기 (비밀값은 커밋되지 않습니다)

```bat
copy config\notify.example.json config\notify.json
copy config\watch.example.json config\watch.json
```

- `config\notify.json` : ntfy 토픽(앱 `ntfy` 에서 같은 토픽 구독) 또는 텔레그램 토큰·chat_id 입력. 둘 다 비우면 Windows 토스트로 대체됩니다.
- `config\watch.json` : `workdir` 와 `jobs`(실행할 명령·주기)를 본인 경로로 수정.
- 알림 점검: `python notify.py "테스트" "도착하나요" alert`

## 3. 숨고 로그인 상태(storage_state.json) 만들기 — 1회

```bat
python -m playwright codegen --save-storage=storage_state.json https://soomgo.com
```

열린 브라우저에서 **직접 로그인**하고(2단계 인증 포함) 창을 닫으면 `storage_state.json` 이 저장됩니다.
이 파일은 로그인 쿠키이므로 **절대 커밋·공유하지 마세요**(`.gitignore` 처리됨). 로그인이 풀리면
"숨고 감시 오류: 로그인 만료" 알림이 오니 이 단계를 다시 하면 됩니다.

## 4. 셀렉터 점검 (처음 1회 필수)

`config\selectors.json` 의 값은 실제 화면을 못 보고 만든 **미검증 초기값**입니다.

```bat
python soomgo_watch.py --check-selectors --headed
```

각 셀렉터가 몇 개 잡히는지 출력됩니다(0 이면 틀린 것). 실패 시 `results\fail_*.png/.html` 이 남으니
그 HTML 을 보고 `selectors.json` 을 고치세요. 저장된 HTML 로 파서만 시험하려면
`chats.html`/`requests.html` 이 든 폴더를 `--html-dir 폴더` 로 지정합니다.

## 5. 작업 스케줄러 등록 (schtasks 예시)

경로의 `python` 은 `where python` 으로 나온 전체 경로를 쓰는 것이 안전합니다.

```bat
:: 숨고 감시: 5분마다 (콘솔 창이 안 뜨게 pythonw 사용)
schtasks /Create /TN "local_watch\soomgo" /SC MINUTE /MO 5 /TR "pythonw C:\Users\본인\pilacademy\tools\local_watch\soomgo_watch.py" /F

:: 명령 감시: 10분마다 점검(각 작업의 interval_minutes 가 도래했을 때만 실제 실행)
schtasks /Create /TN "local_watch\runner" /SC MINUTE /MO 10 /TR "pythonw C:\Users\본인\pilacademy\tools\local_watch\watch_runner.py" /F

:: 확인·즉시 실행·삭제
schtasks /Query /TN "local_watch\soomgo" /V /FO LIST
schtasks /Run /TN "local_watch\soomgo"
schtasks /Delete /TN "local_watch\soomgo" /F
```

주의: pythonw 는 콘솔이 없어 오류가 안 보입니다. 처음엔 `python` 으로 직접 돌려 확인한 뒤 등록하세요.
노트북이 절전이면 작업이 돌지 않습니다(전원 설정 확인). `--send` 는 등록 명령에 넣지 마세요(수동 시험용).
