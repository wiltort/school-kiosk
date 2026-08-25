import uuid
from datetime import datetime

import pytest
from src.models import ScheduleColumn


@pytest.mark.asyncio
async def test_schedule_table_model(schedule_table_sample):
    schedule = schedule_table_sample
    assert schedule.id is not None
    assert isinstance(schedule.id, uuid.UUID)
    assert schedule.name == "Untitled"
    assert schedule.is_active is False
    assert schedule.day_of_week.value == 1
    assert schedule.created_at is not None
    assert isinstance(schedule.created_at, datetime)
    assert schedule.updated_at is not None
    assert isinstance(schedule.updated_at, datetime)
    assert schedule.schedule_columns is not None
    assert isinstance(schedule.schedule_columns, list)
    assert len(schedule.schedule_columns) == 2
    assert isinstance(schedule.schedule_columns[0], ScheduleColumn)

    column = schedule.schedule_columns[0]
    assert column.id is not None
