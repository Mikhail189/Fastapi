from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from icecream import ic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# from src.configurations.database import get_async_session
# from src.models.books import Book
# from src.schemas import IncomingBook, ReturnedAllBooks, ReturnedBook
from configurations.database import get_async_session
from models.books import Book
from schemas import IncomingBook, ReturnedAllBooks, ReturnedBook
from jose import JWTError, jwt

import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))

books_router = APIRouter(tags=["books"], prefix="/books")


# Больше не симулируем хранилище данных. Подключаемся к реальному, через сессию.
DBSession = Annotated[AsyncSession, Depends(get_async_session)]

# Ручка для создания записи о книге в БД. Возвращает созданную книгу.
@books_router.post("/", response_model=ReturnedBook, status_code=status.HTTP_201_CREATED)  # Прописываем модель ответа
async def create_book(
    book: IncomingBook, token: str, session: DBSession
):  # прописываем модель валидирующую входные данные и сессию как зависимость.
    # это - бизнес логика. Обрабатываем данные, сохраняем, преобразуем и т.д.
    token = token.replace("Bearer ", "")
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    e_mail: str = payload.get("sub")
    id: int = payload.get("user_id")
    if book.saller_id == id:
        new_book = Book(
            title=book.title,
            author=book.author,
            year=book.year,
            count_pages=book.count_pages,
            saller_id=book.saller_id,
        )
        session.add(new_book)
        await session.flush()

        return new_book
    else:
        raise HTTPException(
                          status_code=status.HTTP_403_FORBIDDEN,
                          detail="You do not have access to create book for this saller",
                      )


# Ручка, возвращающая все книги
@books_router.get("/", response_model=ReturnedAllBooks)
async def get_all_books(session: DBSession):
    # Хотим видеть формат:
    # books: [{"id": 1, "title": "Blabla", ...}, {"id": 2, ...}]
    query = select(Book)
    res = await session.execute(query)
    books = res.scalars().all()
    return {"books": books}


# Ручка для получения книги по ее ИД
@books_router.get("/{book_id}", response_model=ReturnedBook)
async def get_book(book_id: int, session: DBSession):
    res = await session.get(Book, book_id)
    return res


# Ручка для удаления книги
@books_router.delete("/{book_id}")
async def delete_book(book_id: int, session: DBSession):
    deleted_book = await session.get(Book, book_id)
    ic(deleted_book)  # Красивая и информативная замена для print. Полезна при отладке.
    if deleted_book:
        await session.delete(deleted_book)

    return Response(status_code=status.HTTP_204_NO_CONTENT)  # Response может вернуть текст и метаданные.


# Ручка для обновления данных о книге
@books_router.put("/{book_id}")
async def update_book(book_id: int, token: str, new_data: ReturnedBook, session: DBSession):
    token = token.replace("Bearer ", "")
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    e_mail: str = payload.get("sub")
    id: int = payload.get("user_id")
    # Оператор "морж", позволяющий одновременно и присвоить значение и проверить его.
    if updated_book := await session.get(Book, book_id):
            if updated_book.saller_id == id:
                updated_book.author = new_data.author
                updated_book.title = new_data.title
                updated_book.year = new_data.year
                updated_book.count_pages = new_data.count_pages

                await session.flush()

                return updated_book
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have access to update this book",
                )


    return Response(status_code=status.HTTP_404_NOT_FOUND)
