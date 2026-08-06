from fastapi import Depends, HTTPException
from sqlalchemy import insert
from sqlalchemy.exc import IntegrityError
from src.core.database import DBDependency
from src.models import ScheduleImage
from src.apps.schedule.schemas import ScheduleImageCreate, ScheduleImageGet


class ScheduleImageManager:

    def __init__(self, db: DBDependency = Depends(DBDependency)) -> None:
        self.db = db
        self.model = ScheduleImage

    async def create(self, schedule: ScheduleImageCreate) -> ScheduleImageGet:
        async with self.db.db_session as session:
            query = insert(self.model).values(**schedule.model_dump()).returning(self.model)

            try:
                result = await session.execute(query)
            except IntegrityError as e:
                raise HTTPException(status_code=400, detail=str(e))
            await session.commit()
            schedule_data = result.scalar_one()
            return ScheduleImageGet.model_validate(schedule_data)
