from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from collections.abc import Iterable
from contextlib import closing
import csv
import json
import sqlite3
from io import StringIO
from datetime import datetime, UTC


@dataclass(frozen=True)
class FeedbackEntry:
    scope: str
    label: str
    sentiment: str
    dietary_pattern: str
    weight_goal: str
    avoid_terms: list[str] = field(default_factory=list)
    timestamp_utc: str | None = None

    def normalized(self) -> FeedbackEntry:
        timestamp = self.timestamp_utc or datetime.now(UTC).isoformat()
        sentiment = self.sentiment.strip().lower()
        if sentiment not in {"liked", "not_liked"}:
            raise ValueError("sentiment must be liked or not_liked")
        return FeedbackEntry(
            scope=self.scope.strip().lower(),
            label=self.label.strip(),
            sentiment=sentiment,
            dietary_pattern=self.dietary_pattern.strip().lower(),
            weight_goal=self.weight_goal.strip().lower(),
            avoid_terms=[term.strip().lower() for term in self.avoid_terms if term.strip()],
            timestamp_utc=timestamp,
        )


class FeedbackStore:
    def __init__(self, path: Path | str, max_entries: int = 1000):
        self.path = Path(path)
        self.max_entries = max(1, max_entries)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def add(self, entry: FeedbackEntry) -> int:
        normalized = entry.normalized()
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO feedback
                    (timestamp_utc, scope, label, sentiment, dietary_pattern, weight_goal, avoid_terms_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    normalized.timestamp_utc,
                    normalized.scope,
                    normalized.label,
                    normalized.sentiment,
                    normalized.dietary_pattern,
                    normalized.weight_goal,
                    json.dumps(normalized.avoid_terms),
                ),
            )
            self._trim(connection)
            connection.commit()
            return int(connection.execute("SELECT COUNT(*) FROM feedback").fetchone()[0])

    def list_entries(self) -> list[FeedbackEntry]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT timestamp_utc, scope, label, sentiment, dietary_pattern, weight_goal, avoid_terms_json
                FROM feedback
                ORDER BY id
                """
            ).fetchall()
        return [
            FeedbackEntry(
                timestamp_utc=row[0],
                scope=row[1],
                label=row[2],
                sentiment=row[3],
                dietary_pattern=row[4],
                weight_goal=row[5],
                avoid_terms=json.loads(row[6] or "[]"),
            )
            for row in rows
        ]

    def count(self) -> int:
        with closing(self._connect()) as connection:
            return int(connection.execute("SELECT COUNT(*) FROM feedback").fetchone()[0])

    def to_csv(self, entries: Iterable[FeedbackEntry] | None = None) -> str:
        output = StringIO()
        fieldnames = ["scope", "label", "sentiment", "dietary_pattern", "weight_goal", "avoid_terms", "timestamp_utc"]
        writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for entry in entries or self.list_entries():
            writer.writerow(
                {
                    "scope": entry.scope,
                    "label": entry.label,
                    "sentiment": entry.sentiment,
                    "dietary_pattern": entry.dietary_pattern,
                    "weight_goal": entry.weight_goal,
                    "avoid_terms": ", ".join(entry.avoid_terms),
                    "timestamp_utc": entry.timestamp_utc or "",
                }
            )
        return output.getvalue()

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp_utc TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    label TEXT NOT NULL,
                    sentiment TEXT NOT NULL,
                    dietary_pattern TEXT NOT NULL,
                    weight_goal TEXT NOT NULL,
                    avoid_terms_json TEXT NOT NULL
                )
                """
            )
            connection.commit()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.execute("PRAGMA secure_delete = ON")
        return connection

    def _trim(self, connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            DELETE FROM feedback
            WHERE id NOT IN (
                SELECT id
                FROM feedback
                ORDER BY id DESC
                LIMIT ?
            )
            """,
            (self.max_entries,),
        )
