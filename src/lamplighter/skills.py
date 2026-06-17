"""Skill installation for the Lamplighter agent harness.

Installs orchestrator-managed skills into the local skills directory. Each
skill is a single ``SKILL.md`` file written under ``<skills_dir>/<name>/``.

Writes are atomic (temp file in the target directory, then :func:`os.replace`)
so a partially written ``SKILL.md`` is never observable, and skill names are
validated strictly so nothing is ever written outside the install root.
"""

import os
import tempfile
from pathlib import Path

SKILL_FILENAME = "SKILL.md"


class SkillInstallError(Exception):
    """Raised when a skill cannot be installed (e.g. invalid name)."""


class SkillInstaller:
    """Installs skills under a fixed install root.

    The install root (``skills_dir``) is typically ``~/.claude/skills``. Each
    installed skill lives at ``<skills_dir>/<name>/SKILL.md``.
    """

    def __init__(self, skills_dir: Path) -> None:
        """Create an installer rooted at ``skills_dir``.

        Args:
            skills_dir: The install root, e.g. ``~/.claude/skills``.
        """
        self._skills_dir = skills_dir

    def install(self, name: str, text: str) -> Path:
        """Write ``text`` to ``<skills_dir>/<name>/SKILL.md`` atomically.

        Creates ``<skills_dir>/<name>/`` (and parents) if missing, overwrites an
        existing ``SKILL.md`` in place (idempotent), and writes atomically by
        writing to a temp file in the SAME directory then calling
        :func:`os.replace`. The written content is exactly ``text`` with no
        added trailing newline.

        Args:
            name: The skill name; becomes the subdirectory under ``skills_dir``.
            text: The full contents to write to ``SKILL.md``.

        Returns:
            The absolute path to the written ``SKILL.md``.

        Raises:
            SkillInstallError: If ``name`` is empty, contains a path separator
                or ``..`` traversal, is absolute, or is ``.``/``..``. Validation
                happens before any filesystem changes are made.
        """
        self._validate_name(name)

        skill_dir = self._skills_dir / name
        skill_dir.mkdir(parents=True, exist_ok=True)

        final_path = skill_dir / SKILL_FILENAME
        self._atomic_write(skill_dir, final_path, text)
        return final_path.resolve()

    @staticmethod
    def _validate_name(name: str) -> None:
        """Reject any name that could escape the install root.

        Args:
            name: The candidate skill name.

        Raises:
            SkillInstallError: If the name is unsafe (empty/whitespace, contains
                ``/``, ``\\``, or the OS separator, contains ``..``, is absolute,
                or equals ``.`` or ``..``).
        """
        if not name or not name.strip():
            raise SkillInstallError("Skill name must not be empty.")
        if name in {".", ".."}:
            raise SkillInstallError(f"Skill name must not be {name!r}.")
        if ".." in name:
            raise SkillInstallError(f"Skill name must not contain '..': {name!r}.")
        if "/" in name or "\\" in name or os.sep in name or (os.altsep and os.altsep in name):
            raise SkillInstallError(f"Skill name must not contain a path separator: {name!r}.")
        if Path(name).is_absolute():
            raise SkillInstallError(f"Skill name must not be absolute: {name!r}.")

    @staticmethod
    def _atomic_write(directory: Path, final_path: Path, text: str) -> None:
        """Write ``text`` to ``final_path`` atomically via a temp file.

        Writes to a temporary file in ``directory`` (the same directory as
        ``final_path`` so :func:`os.replace` stays on one filesystem), then
        replaces ``final_path``. On any error the temp file is removed so no
        stray temp file is left behind.

        Args:
            directory: The skill directory holding the temp file and target.
            final_path: The destination ``SKILL.md`` path.
            text: The full contents to write.
        """
        tmp = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=directory,
            delete=False,
        )
        tmp_path = Path(tmp.name)
        try:
            tmp.write(text)
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp.close()
            os.replace(tmp_path, final_path)
        except BaseException:
            tmp.close()
            tmp_path.unlink(missing_ok=True)
            raise
