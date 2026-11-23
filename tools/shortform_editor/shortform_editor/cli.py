"""명령행 진입점: python -m shortform_editor.cli <롱폼.mp4> [옵션]"""
from __future__ import annotations

import argparse
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    """인자 정의: 입력 mp4, --subs(자막 json, 선택), --out(출력 폴더), --max-clips, --model."""
    raise NotImplementedError("원본 코드 이식 전")


def run(video: Path, subs_json: Path | None, out_dir: Path, max_clips: int = 5) -> list[Path]:
    """전체 파이프라인(음성 인식 -> 선별 -> 자르기 -> 자막 굽기 -> 세로 변환)을 실행하고
    생성된 숏폼 mp4 경로 목록을 반환한다. 클립마다 같은 이름의 캡션 txt도 만든다."""
    raise NotImplementedError("원본 코드 이식 전")


def main(argv: list[str] | None = None) -> int:
    """종료 코드를 반환하는 main."""
    raise NotImplementedError("원본 코드 이식 전")


if __name__ == "__main__":
    raise SystemExit(main())
