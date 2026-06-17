"""Tests for :mod:`lamplighter.skills`."""

from pathlib import Path

import pytest

from lamplighter.skills import SkillInstaller, SkillInstallError


def test_install_writes_skill_md(tmp_path: Path) -> None:
    """install writes SKILL.md with exact content and returns its path."""
    installer = SkillInstaller(tmp_path)

    result = installer.install("tdd", "body")

    expected = tmp_path / "tdd" / "SKILL.md"
    assert expected.exists()
    assert expected.read_text(encoding="utf-8") == "body"
    assert result == expected.resolve()


def test_install_creates_parent_dirs(tmp_path: Path) -> None:
    """install creates a missing nested skills_dir (and parents)."""
    skills_dir = tmp_path / "deeply" / "nested" / "skills"
    installer = SkillInstaller(skills_dir)

    installer.install("tdd", "body")

    assert (skills_dir / "tdd" / "SKILL.md").read_text(encoding="utf-8") == "body"


def test_reinstall_overwrites(tmp_path: Path) -> None:
    """Installing twice overwrites the first content with the second."""
    installer = SkillInstaller(tmp_path)

    installer.install("tdd", "first")
    installer.install("tdd", "second")

    assert (tmp_path / "tdd" / "SKILL.md").read_text(encoding="utf-8") == "second"


def test_install_is_atomic(tmp_path: Path) -> None:
    """No leftover temp files remain after install; only SKILL.md is present."""
    installer = SkillInstaller(tmp_path)

    installer.install("tdd", "body")

    skill_dir = tmp_path / "tdd"
    contents = sorted(p.name for p in skill_dir.iterdir())
    assert contents == ["SKILL.md"]


@pytest.mark.parametrize("name", ["../evil", "a/b", "..", "", "/abs", "a\\b"])
def test_install_rejects_path_traversal(tmp_path: Path, name: str) -> None:
    """Unsafe names raise SkillInstallError and write nothing anywhere."""
    installer = SkillInstaller(tmp_path)

    with pytest.raises(SkillInstallError):
        installer.install(name, "body")

    # Nothing was created inside the install root...
    assert list(tmp_path.iterdir()) == []
    # ...and nothing escaped to a traversal target outside it.
    assert not (tmp_path.parent / "evil" / "SKILL.md").exists()
