from pydantic import BaseModel, Field, field_validator
from pydantic_core import PydanticCustomError

__all__ = ["IncomingBook", "ReturnedAllBooks", "ReturnedBook"]\

# Базовый класс "Книги", содержащий поля, которые есть во всех классах-наследниках.
class BaseBook(BaseModel):
    title: str
    author: str
    year: int
    saller_id: int
    class Config:
        from_attributes = True

# Класс для валидации входящих данных. Не содержит id так как его присваивает БД.
class IncomingBook(BaseBook):
    year: int = 2024  # Пример присваивания дефолтного значения
    count_pages: int = Field(
    #    alias="pages",
    )  # Пример использования тонкой настройки полей. Передачи в них метаинформации.
    #saller_id: int = 1
    class Config:
        from_attributes = True

    @field_validator("year")  # Валидатор, проверяет что дата не слишком древняя
    @staticmethod
    def validate_year(val: int):
        if val < 1900:
            raise PydanticCustomError("Validation error", "Year is wrong!")
        return val



# Класс, валидирующий исходящие данные. Он уже содержит id
class ReturnedBook(BaseBook):
    id: int
    count_pages: int

    class Config:
        from_attributes = True


# Класс для возврата массива объектов "Книга"
class ReturnedAllBooks(BaseModel):
    books: list[ReturnedBook]
