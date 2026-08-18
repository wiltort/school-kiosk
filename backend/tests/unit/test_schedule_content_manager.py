"""Юнит-тесты для ScheduleContentManager операций."""

import pytest
from src.apps.schedule.managers import ScheduleContentManager
from src.apps.schedule.schemas import (
    AddColumnToScheduleTable,
    AddLessonToScheduleColumn,
)


@pytest.mark.asyncio
async def test_add_schedule_column(manager_factory, schedule_table_sample):
    """Проверка создания колонки таблицы расписания."""
    manager = manager_factory(ScheduleContentManager)

    column = await manager.create_column(
        AddColumnToScheduleTable(
            schedule_table_id=schedule_table_sample.id, number=3, header="test_column"
        )
    )

    assert column.model_dump() == {
        "id": column.id,
        "number": 3,
        "header": "test_column",
        "schedule_table_id": schedule_table_sample.id,
        "lessons": [],
    }


@pytest.mark.asyncio
async def test_add_column_with_nonunique_number(manager_factory, schedule_table_sample):
    """Проверка создания колонки с неуникальным номером."""
    manager = manager_factory(ScheduleContentManager)

    with pytest.raises(Exception) as excinfo:
        await manager.create_column(
            AddColumnToScheduleTable(
                schedule_table_id=schedule_table_sample.id,
                number=1,
                header="test_column",
            )
        )
    assert excinfo.value.status_code == 400
    assert excinfo.value.detail == "Нарушение целостности данных"


@pytest.mark.asyncio
async def test_add_lesson(manager_factory, schedule_table_sample):
    """Проверка создания урока в колонке расписания."""
    manager = manager_factory(ScheduleContentManager)

    lesson = await manager.create_lesson(
        AddLessonToScheduleColumn(
            schedule_column_id=schedule_table_sample.schedule_columns[0].id,
            number=3,
            name="test_lesson",
        )
    )

    assert lesson.model_dump() == {
        "id": lesson.id,
        "number": 3,
        "name": "test_lesson",
        "schedule_column_id": schedule_table_sample.schedule_columns[0].id,
    }


@pytest.mark.asyncio
async def test_add_lesson_with_nonunique_number(manager_factory, schedule_table_sample):
    """Проверка создания урока с неуникальным номером."""
    manager = manager_factory(ScheduleContentManager)

    with pytest.raises(Exception) as excinfo:
        await manager.create_lesson(
            AddLessonToScheduleColumn(
                schedule_column_id=schedule_table_sample.schedule_columns[0].id,
                number=1,
                name="test_lesson",
            )
        )
    assert excinfo.value.status_code == 400
    assert excinfo.value.detail == "Нарушение целостности данных"
