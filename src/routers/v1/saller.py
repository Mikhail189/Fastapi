from typing import Annotated
from fastapi import Header
from fastapi import APIRouter, Depends, Response, status, Security
from icecream import ic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from configurations.database import get_async_session
from models.sallers import Saller
from models.books import Book
from schemas.saller import IncomingSaller, ReturnedAllSaller, ReturnedSaller, ReturnedSallerID, BaseSaller
from schemas.books import BaseBook, ReturnedBook

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta

import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES"))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

saller_router = APIRouter(tags=["saller"], prefix="/saller")

# Больше не симулируем хранилище данных. Подключаемся к реальному, через сессию.
DBSession = Annotated[AsyncSession, Depends(get_async_session)]

@saller_router.post("/token")
async def login_for_access_token(
    e_mail: str,
    password: str,
    session: DBSession
):
    seller = await session.execute(
        select(Saller).where(Saller.e_mail == e_mail, Saller.password == password)
    )
    seller_list = seller.scalars().all()

    if seller_list:
        seller_ = seller_list[0]
        seller_id = seller_.id
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        expires = datetime.utcnow() + expires_delta
        to_encode = {"sub": e_mail, "user_id": seller_id, "exp": expires}
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return {"access_token": encoded_jwt, "token_type": "Bearer"}
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Ручка для создания записи о книге в БД. Возвращает созданную книгу.
@saller_router.post("/", response_model=ReturnedSaller, status_code=status.HTTP_201_CREATED)  # Прописываем модель ответа
async def create_saller(
    saller: IncomingSaller, session: DBSession
):  # прописываем модель валидирующую входные данные и сессию как зависимость.
    # это - бизнес логика. Обрабатываем данные, сохраняем, преобразуем и т.д.
    new_saller = Saller(
        first_name=saller.first_name,
        last_name=saller.last_name,
        e_mail=saller.e_mail,
        password=saller.password,
    )
    session.add(new_saller)
    await session.flush()

    return new_saller

# Ручка, возвращающая все книги
@saller_router.get("/", response_model=ReturnedAllSaller)
async def get_all_sallers(session: DBSession):
    query = select(Saller)
    res = await session.execute(query)
    sallers = res.scalars().all()
    return {"sallers": sallers}

# Ручка для получения книги по ее ИД
@saller_router.get("/{saller_id}", response_model=ReturnedSallerID)
async def get_saller(saller_id: int, token: str, session: DBSession):
    token = token.replace("Bearer ", "")
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    e_mail: str = payload.get("sub")
    id: int = payload.get("user_id")
    if saller_id == id:
        saller = await session.get(Saller, saller_id)
        books = await session.execute(
            select(Book).where(Book.saller_id == saller_id)
        )
        books_list = books.scalars().all()
        return ReturnedSallerID(
            id=saller.id,
            first_name=saller.first_name,
            last_name=saller.last_name,
            e_mail=saller.e_mail,
            books=[ReturnedBook.from_orm(book) for book in books_list]  # Преобразуем каждую книгу в Pydantic модель
        )
    else:
        raise HTTPException(
                          status_code=status.HTTP_403_FORBIDDEN,
                          detail="You do not have access to this seller's information",
                      )

# Ручка для обновления данных о книге
@saller_router.put("/{saller_id}")
async def update_saller(saller_id: int, new_data: BaseSaller, session: DBSession):
    # Оператор "морж", позволяющий одновременно и присвоить значение и проверить его.
    if updated_saller := await session.get(Saller, saller_id):
        updated_saller.first_name = new_data.first_name
        updated_saller.last_name = new_data.last_name
        updated_saller.e_mail = new_data.e_mail

        await session.flush()
        #updates = [updated_saller.first_name, updated_saller.last_name, updated_saller.e_mail]
        #return [BaseSaller.from_orm(updated) for updated in updates]
        return {"first_name": updated_saller.first_name, "last_name": updated_saller.last_name, "e_mail": updated_saller.e_mail}

    return Response(status_code=status.HTTP_404_NOT_FOUND)

# Ручка для удаления книги
@saller_router.delete("/{saller_id}")
async def delete_saller(saller_id: int, session: DBSession):
    deleted_saller = await session.get(Saller, saller_id)
    deleted_books = await session.execute(
        select(Book).where(Book.saller_id == saller_id)
    )
    deleted_books = deleted_books.scalars().all()

    if deleted_books:
        # Удаляем все книги
        for book in deleted_books:
            await session.delete(book)
    if deleted_saller:
        await session.delete(deleted_saller)

    return Response(status_code=status.HTTP_204_NO_CONTENT)  # Response может вернуть текст и метаданные.