from sqlalchemy import Boolean, String, Text  
from sqlalchemy.orm import Mapped, mapped_column  

from src.models.base import Base
from src.models.mixins import IDMixin, TimestampMixin


class User(IDMixin, TimestampMixin, Base):  
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(Text, unique=False, nullable=False)  
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    