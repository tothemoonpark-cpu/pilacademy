"""4단계: 자막 굽기. 잘라낸 클립에 한글 자막을 입힌다.

작가님 규칙(반드시 지킬 것):
  1. 어절 단위 줄바꿈: 단어(어절) 중간에서 줄을 바꾸지 않는다.
  2. 글자가 화면 밖으로 나가지 않게: 줄 폭이 안전영역(좌우 여백)을 넘으면 줄을 더 나누거나 글자 크기를 줄인다.
  3. 자막 위치 일관: 모든 클립에서 같은 위치(하단 중앙, 고정 y좌표)와 같은 글꼴·크기를 쓴다.
"""
from __future__ import annotations

from pathlib import Path

# 규칙 3: 위치·스타일 상수는 한 곳에서만 정의한다 (값은 이식 시 원본 기준으로 확정).
SUBTITLE_STYLE: dict = {}


def wrap_korean_by_eojeol(text: str, max_chars: int, max_lines: int = 2) -> list[str]:
    """text를 어절(공백) 단위로만 끊어 한 줄 max_chars 이하, 최대 max_lines줄로 나눠 반환한다."""
    raise NotImplementedError("원본 코드 이식 전")


def fits_in_frame(lines: list[str], font_px: int, frame_width_px: int, margin_px: int) -> bool:
    """줄들이 좌우 여백을 뺀 폭 안에 모두 들어가면 True (규칙 2 검증용)."""
    raise NotImplementedError("원본 코드 이식 전")


def burn_subtitles(clip_path: Path, segments: list[dict], out_path: Path) -> Path:
    """clip_path에 segments(클립 기준 시간)의 자막을 위 규칙대로 구워 out_path에 저장하고 경로를 반환한다."""
    raise NotImplementedError("원본 코드 이식 전")
