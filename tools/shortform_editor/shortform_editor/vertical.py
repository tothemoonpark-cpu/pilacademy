"""5단계: 세로 변환. 16:9 클립을 9:16(1080x1920)으로 바꾼다."""
from __future__ import annotations

from pathlib import Path


def to_vertical(clip_path: Path, out_path: Path, width: int = 1080, height: int = 1920) -> Path:
    """clip_path를 width x height 세로 영상으로 변환(중앙 크롭 또는 블러 배경 합성)해 out_path에 저장한다.

    자막 위치가 클립마다 흔들리지 않도록 변환 후 자막 안전영역은 고정이다.
    """
    raise NotImplementedError("원본 코드 이식 전")
