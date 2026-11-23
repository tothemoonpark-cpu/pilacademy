"""2단계: 하이라이트 선별. 자막 구간에서 숏폼으로 쓸 구간을 고른다.

주의: 모듈 이름이 표준 라이브러리 `select`와 같다. 반드시 패키지로 import
(`from shortform_editor import select`)하거나 `python -m shortform_editor.cli`로 실행하고,
이 폴더 안에서 `python select.py`처럼 직접 실행하지 않는다.
"""
from __future__ import annotations


def select_highlights(
    segments: list[dict],
    min_sec: float = 30.0,
    max_sec: float = 60.0,
    max_clips: int = 5,
) -> list[dict]:
    """segments에서 길이 min_sec~max_sec의 하이라이트 최대 max_clips개를 골라
    [{"start": float, "end": float, "title": str, "caption": str}, ...]로 반환한다.

    문장 중간에서 끊지 않고 문장 경계에 맞춘다.
    """
    raise NotImplementedError("원본 코드 이식 전")
