"""3단계: 자르기. 선별된 구간을 롱폼에서 잘라낸다."""
from __future__ import annotations

from pathlib import Path


def cut_clip(video_path: Path, start: float, end: float, out_path: Path) -> Path:
    """ffmpeg로 video_path의 start~end(초) 구간을 out_path로 잘라 저장하고 경로를 반환한다."""
    raise NotImplementedError("원본 코드 이식 전")
