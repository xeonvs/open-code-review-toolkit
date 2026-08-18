"""Explicit identities created by one GitLab posting transaction."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class PostingTransaction:
    """Provider-returned or author-bound recovered identities from this run."""

    _draft_note_ids: list[int] = field(default_factory=list, init=False)
    _plain_note_ids: list[int] = field(default_factory=list, init=False)
    _discussion_note_refs: list[tuple[str, int]] = field(default_factory=list, init=False)
    _draft_publish_cursor: int = field(default=0, init=False)

    @property
    def draft_note_ids(self) -> tuple[int, ...]:
        """Return immutable current-run draft identities in creation order."""

        return tuple(self._draft_note_ids)

    @property
    def plain_note_ids(self) -> tuple[int, ...]:
        """Return immutable current-run plain-note identities in creation order."""

        return tuple(self._plain_note_ids)

    @property
    def discussion_note_refs(self) -> tuple[tuple[str, int], ...]:
        """Return immutable current-run direct-discussion identities."""

        return tuple(self._discussion_note_refs)

    @staticmethod
    def _positive_id(value: int) -> bool:
        return isinstance(value, int) and not isinstance(value, bool) and value > 0

    def record_draft(self, note_id: int) -> bool:
        """Record one draft exactly once, rejecting invalid or duplicate identity."""

        if not self._positive_id(note_id) or note_id in self._draft_note_ids:
            return False
        self._draft_note_ids.append(note_id)
        return True

    def record_plain(self, note_id: int) -> bool:
        """Record one direct plain note exactly once."""

        if not self._positive_id(note_id) or note_id in self._plain_note_ids:
            return False
        self._plain_note_ids.append(note_id)
        return True

    def consume_drafts_for_publication(self) -> tuple[int, ...]:
        """Return each recorded draft for publication at most once."""

        pending = tuple(self._draft_note_ids[self._draft_publish_cursor :])
        self._draft_publish_cursor = len(self._draft_note_ids)
        return pending

    def record_discussion(self, discussion_id: str, note_id: int) -> bool:
        """Record one direct discussion identity exactly once."""

        ref = (discussion_id, note_id)
        if not discussion_id or not self._positive_id(note_id) or ref in self._discussion_note_refs:
            return False
        self._discussion_note_refs.append(ref)
        return True
