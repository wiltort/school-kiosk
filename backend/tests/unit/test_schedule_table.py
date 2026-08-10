"""Unit tests for ScheduleTable"""

import uuid
from datetime import datetime

from src.models.schedule import Lesson, ScheduleRow, ScheduleTable


def test_schedule_table_model(session):
    schedule = ScheduleTable(
        schedule_rows=[
            ScheduleRow(
                number=1,
                header="1",
                lessons=[
                    Lesson(number=1, name="History"),
                    Lesson(number=2, name="Math"),
                ],
            ),
            ScheduleRow(
                number=2,
                header="2",
                lessons=[
                    Lesson(number=1, name="History"),
                    Lesson(number=2, name="Math"),
                ],
            ),
        ]
    )
    session.add(schedule)
    session.flush()

    assert schedule.id is not None
    assert isinstance(schedule.id, uuid.UUID)
    assert schedule.name == "Untitled"
    assert schedule.is_active is False
    assert schedule.day_of_week.value == 1
    assert schedule.created_at is not None
    assert isinstance(schedule.created_at, datetime)
    assert schedule.updated_at is not None
    assert isinstance(schedule.updated_at, datetime)
    assert schedule.schedule_rows is not None
    assert isinstance(schedule.schedule_rows, list)
    assert len(schedule.schedule_rows) == 2
    assert isinstance(schedule.schedule_rows[0], ScheduleRow)

    row = schedule.schedule_rows[0]
    assert row.id is not None
