from pydantic import BaseModel, Field, field_validator
from pydantic_core import PydanticCustomError
from schemas.books import ReturnedBook

__all__ = ["IncomingSaller", "ReturnedAllSaller", "ReturnedSaller"]

# Базовый класс "Продавцы", содержащий поля, которые есть во всех классах-наследниках.
class BaseSaller(BaseModel):
    first_name: str
    last_name: str
    e_mail: str

    class Config:
        from_attributes = True

class BaseSallerPassword(BaseSaller):
    password: str

# Класс для валидации входящих данных. Не содержит id так как его присваивает БД.
class IncomingSaller(BaseSallerPassword):
    e_mail: str = "defolt@gmail.com"  # Пример присваивания дефолтного значения
    # password: str = Field(
    #     default="qwerty",
    # )
    # @field_validator("year")  # Валидатор, проверяет что дата не слишком древняя
    # @staticmethod
    # def validate_year(val: int):
    #     if val < 1900:
    #         raise PydanticCustomError("Validation error", "Year is wrong!")
    #     return val


class ReturnedSaller(BaseSaller):
    id: int

class ReturnedSallerID(BaseSaller):
    id: int
    books: list[ReturnedBook]

# Класс для возврата массива объектов "Книга"
class ReturnedAllSaller(BaseModel):
    sallers: list[ReturnedSaller]