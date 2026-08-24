"""Tests for Perspective Core v0 SessionStore.

Covers:
- Atomic session creation with source snapshot
- Source hash verification
- Session persistence and reload
- Constraint ledger integration
- Error atomicity (no partial writes)
"""

import hashlib
import json
import tempfile
from pathlib import Path

import pytest

from prism.perspective_core import SessionStore


# ─────────────────────────────────────────────────────────────────────────────
# Session creation (§6.10, requirement 3)
# ─────────────────────────────────────────────────────────────────────────────


def test_session_create_stores_source_snapshot():
    """SessionStore.create stores source.md alongside session.json."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = SessionStore(Path(tmpdir))
        source_text = "Test source material for analysis"
        objective = "Analyze this material"

        session = store.create(
            session_id="test_session",
            source=source_text,
            objective=objective,
        )

        # Verify session object
        assert session.session_id == "test_session"
        assert session.objective == objective
        expected_hash = hashlib.sha256(source_text.encode()).hexdigest()
        assert session.source_hash == expected_hash

        # Verify files exist
        session_dir = Path(tmpdir) / "test_session"
        assert (session_dir / "session.json").exists()
        assert (session_dir / "source.md").exists()

        # Verify source.md content
        stored_source = (session_dir / "source.md").read_text()
        assert stored_source == source_text

        # Verify session.json structure
        session_data = json.loads((session_dir / "session.json").read_text())
        assert session_data["session_id"] == "test_session"
        assert session_data["objective"] == objective
        assert session_data["source_hash"] == session.source_hash

def test_session_create_initializes_missing_canonical_root(tmp_path):
    """First use creates the canonical session root before the atomic rename."""
    base_dir = tmp_path / "prism-sessions" / "perspective-core"
    store = SessionStore(base_dir)

    store.create(
        session_id="test_session",
        source="Source",
        objective="Objective",
    )

    assert (base_dir / "test_session" / "source.md").read_text() == "Source"
    assert (base_dir / "test_session" / "session.json").exists()


def test_session_create_fails_if_exists():
    """SessionStore.create fails atomically if session already exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = SessionStore(Path(tmpdir))

        # Create first session
        store.create(
            session_id="test_session",
            source="Source 1",
            objective="Objective 1",
        )

        # Attempt to create again with same ID
        with pytest.raises(FileExistsError, match="already exists"):
            store.create(
                session_id="test_session",
                source="Source 2",
                objective="Objective 2",
            )


def test_session_create_atomicity():
    """SessionStore.create is atomic - no partial state on failure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = SessionStore(Path(tmpdir))

        # Create first session
        store.create(
            session_id="test_session",
            source="Source 1",
            objective="Objective 1",
        )

        # Attempt duplicate creation
        with pytest.raises(FileExistsError):
            store.create(
                session_id="test_session",
                source="Source 2",
                objective="Objective 2",
            )

        # Verify original session unchanged
        session = store.load("test_session")
        assert session.objective == "Objective 1"

        # Verify source hash matches original
        source = store.load_verified_source(session)
        assert source == "Source 1"


# ─────────────────────────────────────────────────────────────────────────────
# Source hash verification (requirement 3)
# ─────────────────────────────────────────────────────────────────────────────


def test_session_load_verified_source_success():
    """load_verified_source succeeds when hash matches."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = SessionStore(Path(tmpdir))
        source_text = "Test source material"

        session = store.create(
            session_id="test_session",
            source=source_text,
            objective="Test objective",
        )

        # Load and verify
        loaded_source = store.load_verified_source(session)
        assert loaded_source == source_text


def test_session_load_verified_source_hash_mismatch():
    """load_verified_source fails when source.md hash doesn't match session."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = SessionStore(Path(tmpdir))
        source_text = "Original source"

        session = store.create(
            session_id="test_session",
            source=source_text,
            objective="Test objective",
        )

        # Tamper with source.md
        session_dir = Path(tmpdir) / "test_session"
        (session_dir / "source.md").write_text("Tampered source")

        # Attempt to load should fail
        with pytest.raises(RuntimeError, match="Source hash mismatch"):
            store.load_verified_source(session)


# ─────────────────────────────────────────────────────────────────────────────
# Session persistence
# ─────────────────────────────────────────────────────────────────────────────


def test_session_save_and_load():
    """SessionStore.save and load preserve all session state."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = SessionStore(Path(tmpdir))

        # Create session
        session = store.create(
            session_id="test_session",
            source="Test source",
            objective="Test objective",
        )

        # Add constraint
        session.constraint_ledger.add(
            constraint_id="c1",
            value="Must be clear",
            kind="hard",
        )

        # Save
        store.save(session)

        # Load
        loaded = store.load("test_session")

        # Verify state preserved
        assert loaded.session_id == session.session_id
        assert loaded.objective == session.objective
        assert loaded.source_hash == session.source_hash
        active = loaded.constraint_ledger.active_entries()
        assert len(active) == 1
        assert active[0].constraint_id == "c1"
        assert active[0].value == "Must be clear"
        assert active[0].kind == "hard"


def test_session_load_nonexistent():
    """SessionStore.load fails for non-existent session."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = SessionStore(Path(tmpdir))

        with pytest.raises(FileNotFoundError, match="Session not found"):
            store.load("nonexistent_session")


# ─────────────────────────────────────────────────────────────────────────────
# Constraint ledger integration (§6.1, requirement 2)
# ─────────────────────────────────────────────────────────────────────────────


def test_session_constraint_supersession_by_id():
    """Constraints supersede by constraint_id, not value."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = SessionStore(Path(tmpdir))

        session = store.create(
            session_id="test_session",
            source="Test source",
            objective="Test objective",
        )

        # Add initial constraint
        session.constraint_ledger.add(
            constraint_id="c1",
            value="Version 1",
            kind="hard",
        )

        # Add different constraint with same ID (supersedes)
        session.constraint_ledger.add(
            constraint_id="c1",
            value="Version 2",
            kind="hard",
        )

        # Add different constraint with different ID
        session.constraint_ledger.add(
            constraint_id="c2",
            value="Different constraint",
            kind="preference",
        )

        store.save(session)
        loaded = store.load("test_session")

        # Should have all 3 entries
        assert len(loaded.constraint_ledger.entries) == 3

        # Only c1 v2 and c2 are active
        active = loaded.constraint_ledger.active_entries()
        assert len(active) == 2
        assert any(c.constraint_id == "c1" and c.value == "Version 2" for c in active)
        assert any(c.constraint_id == "c2" for c in active)

        # c1 v1 is superseded
        superseded = [c for c in loaded.constraint_ledger.entries if c.status == "superseded"]
        assert len(superseded) == 1
        assert superseded[0].constraint_id == "c1"
        assert superseded[0].value == "Version 1"


def test_session_constraint_different_ids_same_value():
    """Constraints with different IDs but same value coexist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = SessionStore(Path(tmpdir))

        session = store.create(
            session_id="test_session",
            source="Test source",
            objective="Test objective",
        )

        # Add two constraints with same value but different IDs
        session.constraint_ledger.add(
            constraint_id="c1",
            value="Same value",
            kind="hard",
        )
        session.constraint_ledger.add(
            constraint_id="c2",
            value="Same value",
            kind="preference",
        )

        store.save(session)
        loaded = store.load("test_session")

        # Both should be active
        assert len(loaded.constraint_ledger.entries) == 2
        assert all(c.status == "active" for c in loaded.constraint_ledger.entries)


# ─────────────────────────────────────────────────────────────────────────────
# Error handling and edge cases
# ─────────────────────────────────────────────────────────────────────────────


def test_session_load_verified_source_missing_source_file():
    """load_verified_source fails if source.md is missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = SessionStore(Path(tmpdir))

        session = store.create(
            session_id="test_session",
            source="Test source",
            objective="Test objective",
        )

        # Delete source.md
        session_dir = Path(tmpdir) / "test_session"
        (session_dir / "source.md").unlink()

        with pytest.raises(FileNotFoundError, match="Source file not found"):
            store.load_verified_source(session)


def test_session_directory_structure():
    """SessionStore creates correct directory structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = SessionStore(Path(tmpdir))

        store.create(
            session_id="test_session",
            source="Test source",
            objective="Test objective",
        )

        session_dir = Path(tmpdir) / "test_session"
        assert session_dir.is_dir()

        # Check required files
        files = list(session_dir.iterdir())
        file_names = {f.name for f in files}
        assert "session.json" in file_names
        assert "source.md" in file_names


def test_session_empty_constraints():
    """Session can be created with no constraints."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = SessionStore(Path(tmpdir))

        session = store.create(
            session_id="test_session",
            source="Test source",
            objective="Test objective",
        )

        assert len(session.constraint_ledger.entries) == 0

        store.save(session)
        loaded = store.load("test_session")
        assert len(loaded.constraint_ledger.entries) == 0


def test_session_multiple_saves():
    """Multiple saves preserve latest state."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = SessionStore(Path(tmpdir))

        session = store.create(
            session_id="test_session",
            source="Test source",
            objective="Test objective",
        )

        # First save
        session.constraint_ledger.add(
            constraint_id="c1",
            value="First",
            kind="hard",
        )
        store.save(session)

        # Second save
        session.constraint_ledger.add(
            constraint_id="c2",
            value="Second",
            kind="preference",
        )
        store.save(session)

        # Load and verify
        loaded = store.load("test_session")
        assert len(loaded.constraint_ledger.entries) == 2


def test_session_exists():
    """SessionStore.exists correctly checks session existence."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = SessionStore(Path(tmpdir))

        assert not store.exists("test_session")

        store.create(
            session_id="test_session",
            source="Test source",
            objective="Test objective",
        )

        assert store.exists("test_session")
