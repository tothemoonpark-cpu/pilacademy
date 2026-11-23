"""뼈대 단계 시험: 모듈이 import되고, 본문은 아직 NotImplementedError인지 확인한다."""
import importlib
from pathlib import Path

import pytest

MODULES = ["transcribe", "select", "cut", "burn_subs", "vertical", "cli"]


@pytest.mark.parametrize("name", MODULES)
def test_import(name):
    importlib.import_module(f"shortform_editor.{name}")


def test_select_does_not_shadow_stdlib():
    import select as stdlib_select

    assert "shortform_editor" not in stdlib_select.__name__


def test_stubs_not_implemented():
    from shortform_editor import cut, select

    with pytest.raises(NotImplementedError):
        cut.cut_clip(Path("a.mp4"), 0, 1, Path("b.mp4"))
    with pytest.raises(NotImplementedError):
        select.select_highlights([])
