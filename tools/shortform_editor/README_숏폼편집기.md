# 숏폼편집기 설계서

강연 롱폼 mp4를 9:16 숏폼 mp4로 자동 편집하는 파이썬 도구입니다.
**현재는 뼈대 단계입니다.** 원본 코드는 작가님 노트북에만 있어 아직 이 저장소에 없으며, 모든 함수 본문은 `NotImplementedError`입니다. 원본 코드 이식은 다음 단계입니다.

## 입력
| 항목 | 설명 |
|---|---|
| 롱폼 mp4 | 강연 녹화본 (필수) |
| 자막 json | 구간별 `{start, end, text}` 목록 (선택). 없으면 1단계에서 whisper로 생성 |

## 출력
| 항목 | 설명 |
|---|---|
| 숏폼 mp4 | 1080x1920 (9:16), 자막 구움 |
| 캡션 txt | 숏폼마다 같은 이름으로 1개 (게시용 문구) |

## 처리 단계
| 단계 | 모듈 | 하는 일 |
|---|---|---|
| 1. 음성 인식 | `transcribe.py` | whisper로 한국어 자막 json 생성 (자막 json이 있으면 건너뜀) |
| 2. 하이라이트 선별 | `select.py` | 문장 경계에 맞춰 30~60초 구간을 최대 N개 선택, 제목·캡션 초안 |
| 3. 자르기 | `cut.py` | ffmpeg로 구간 절단 |
| 4. 자막 굽기 | `burn_subs.py` | 한글 자막 번인 (아래 자막 규칙 적용) |
| 5. 세로 변환 | `vertical.py` | 16:9 -> 9:16 (중앙 크롭 또는 블러 배경) |

진입점은 `cli.py`이며 위 5단계를 순서대로 호출합니다.

## 자막 규칙 (작가님 규칙)
1. **어절 단위 줄바꿈**: 어절(공백) 중간에서 줄을 바꾸지 않습니다. 한 줄 글자 수와 최대 줄 수(기본 2줄)는 상수로 둡니다.
2. **글자가 화면 밖으로 나가지 않게**: 좌우 안전 여백을 뺀 폭을 넘으면 줄을 더 나누고, 그래도 넘으면 글자 크기를 줄입니다. 구현 후 `fits_in_frame`으로 검증합니다.
3. **자막 위치 일관**: 모든 클립에서 하단 중앙, 같은 y좌표·글꼴·크기를 씁니다. 스타일 값은 `burn_subs.SUBTITLE_STYLE` 한 곳에서만 정의합니다.

## 의존성
- Python 3.11
- ffmpeg (시스템 설치 필요, pip 아님): `sudo apt install ffmpeg` 또는 `brew install ffmpeg`
- openai-whisper (`requirements.txt`)
- 한글 글꼴 1종 (자막용, 이식 시 원본 사용 글꼴 확인)
- 시험: pytest

## 폴더 구조
```
tools/shortform_editor/
├─ README_숏폼편집기.md
├─ requirements.txt
├─ pytest.ini
├─ shortform_editor/
│  ├─ transcribe.py  select.py  cut.py
│  ├─ burn_subs.py   vertical.py  cli.py
└─ tests/test_smoke.py
```

## 실행 예시 (이식 완료 후 목표 형태)
```bash
cd tools/shortform_editor
pip install -r requirements.txt
python -m shortform_editor.cli 강연_롱폼.mp4 --subs 강연_자막.json --out out/ --max-clips 5
# 자막 json이 없으면 --subs 생략 (whisper가 먼저 실행됨)
```
시험: `python -m pytest -q`

## 한계 및 주의
- 현재 실제 편집 기능은 없습니다(뼈대). 원본 코드와 설정값(자막 크기·위치·선별 기준)은 다음 단계에서 이식하며, 그때 이 문서의 값도 원본 기준으로 확정합니다.
- 하이라이트 선별은 자막 텍스트 기반이라 표정·청중 반응·화면 자료는 판단하지 못합니다. 최종 선택은 사람이 확인합니다.
- whisper 인식 오류(고유명사·전문용어)는 자막에 그대로 반영되므로 굽기 전 검수가 필요합니다.
- 긴 영상은 whisper 처리 시간이 오래 걸립니다(GPU 없으면 특히).
- `select.py`는 표준 라이브러리 `select`와 이름이 같습니다. 패키지로 import하고 `python -m`으로 실행하며, 이 파일을 직접 실행하지 않습니다.
- 원본 영상·결과물(mp4)은 용량 때문에 저장소에 올리지 않습니다.
