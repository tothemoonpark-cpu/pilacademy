"""1단계: 음성 인식. 롱폼 mp4에서 어절/구간 단위 자막 json을 만든다."""
from __future__ import annotations

from pathlib import Path


def transcribe(video_path: Path, out_json: Path, model: str = "medium", language: str = "ko") -> Path:
    """whisper로 video_path를 인식해 구간별 {start, end, text} 목록을 out_json에 저장하고 경로를 반환한다.

    이미 자막 json이 있으면 cli에서 이 단계를 건너뛴다.
    """
    raise NotImplementedError("원본 코드 이식 전")


def load_segments(json_path: Path) -> list[dict]:
    """자막 json을 읽어 [{"start": float, "end": float, "text": str}, ...]로 반환한다."""
    raise NotImplementedError("원본 코드 이식 전")
