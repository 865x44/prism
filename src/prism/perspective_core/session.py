"""Session persistence for Perspective Core v0.

Implements replan §6.10 and execution contract frozen APIs.
Atomic session creation with source snapshot and hash verification.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path

from .models import (
    ConstraintLedger,
    PerspectiveSession,
    compute_source_hash,
)


# ─────────────────────────────────────────────────────────────────────────────
# Session store
# ─────────────────────────────────────────────────────────────────────────────


class SessionStore:
    """Manages session persistence with atomic operations.

    Session directory layout:
        prism-sessions/perspective-core/<session_id>/
        ├── session.json
        └── source.md
    """

    def __init__(self, base_dir: Path | None = None):
        """Initialize session store.

        Args:
            base_dir: Base directory for sessions. Defaults to prism-sessions/perspective-core/
        """
        if base_dir is None:
            base_dir = Path("prism-sessions/perspective-core")
        self._base_dir = base_dir

    def create(
        self,
        *,
        session_id: str,
        source: str,
        objective: str,
    ) -> PerspectiveSession:
        """Create new session with atomic directory write.

        Fails if target directory already exists (never overwrite or reuse).

        Args:
            session_id: Unique session identifier
            source: Source material text
            objective: Session objective (immutable in v0)

        Returns:
            Newly created PerspectiveSession

        Raises:
            FileExistsError: If session directory already exists
        """
        session_dir = self._base_dir / session_id
        self._base_dir.mkdir(parents=True, exist_ok=True)

        # Check if target exists
        if session_dir.exists():
            raise FileExistsError(f"Session directory already exists: {session_dir}")

        # Create session object
        source_hash = compute_source_hash(source)
        session = PerspectiveSession(
            session_id=session_id,
            source_hash=source_hash,
            objective=objective,
            constraint_ledger=ConstraintLedger(),
            next_p_number=1,
            perspectives={},
            passes=[],
            deep_runs=[],
        )

        # Write atomically using temp directory
        with tempfile.TemporaryDirectory(dir=self._base_dir.parent) as tmpdir:
            tmp_path = Path(tmpdir) / session_id

            # Create directory structure
            tmp_path.mkdir(parents=True)

            # Write source.md
            source_file = tmp_path / "source.md"
            source_file.write_text(source, encoding="utf-8")

            # Write session.json
            session_file = tmp_path / "session.json"
            session_file.write_text(
                json.dumps(session.to_dict(), indent=2),
                encoding="utf-8",
            )

            # Verify hash matches
            written_source = source_file.read_text(encoding="utf-8")
            written_hash = compute_source_hash(written_source)
            if written_hash != source_hash:
                raise RuntimeError("Source hash mismatch during atomic write")

            # Atomic rename
            os.rename(tmp_path, session_dir)

        return session

    def load(self, session_id: str) -> PerspectiveSession:
        """Load existing session from disk.

        Args:
            session_id: Session identifier

        Returns:
            Loaded PerspectiveSession

        Raises:
            FileNotFoundError: If session does not exist
        """
        session_file = self._base_dir / session_id / "session.json"
        if not session_file.exists():
            raise FileNotFoundError(f"Session not found: {session_id}")

        with open(session_file, encoding="utf-8") as f:
            data = json.load(f)

        return PerspectiveSession.from_dict(data)

    def save(self, session: PerspectiveSession) -> None:
        """Atomically save session to disk.

        Args:
            session: Session to save
        """
        session_dir = self._base_dir / session.session_id
        session_file = session_dir / "session.json"

        # Write atomically using temp file
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=session_dir,
            delete=False,
            encoding="utf-8",
            suffix=".tmp",
        ) as tmp:
            json.dump(session.to_dict(), tmp, indent=2)
            tmp_path = Path(tmp.name)

        # Atomic rename
        os.rename(tmp_path, session_file)

    def load_verified_source(self, session: PerspectiveSession) -> str:
        """Load and verify source material from session directory.

        Verifies SHA-256 hash matches session.source_hash.

        Args:
            session: Session to load source for

        Returns:
            Verified source text

        Raises:
            FileNotFoundError: If source.md does not exist
            RuntimeError: If source hash does not match
        """
        source_file = self._base_dir / session.session_id / "source.md"
        if not source_file.exists():
            raise FileNotFoundError(f"Source file not found: {source_file}")

        source_text = source_file.read_text(encoding="utf-8")
        actual_hash = compute_source_hash(source_text)

        if actual_hash != session.source_hash:
            raise RuntimeError(
                f"Source hash mismatch: expected {session.source_hash}, got {actual_hash}"
            )

        return source_text

    def exists(self, session_id: str) -> bool:
        """Check if session exists.

        Args:
            session_id: Session identifier

        Returns:
            True if session directory exists
        """
        return (self._base_dir / session_id).exists()
