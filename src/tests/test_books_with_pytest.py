import pytest
from fastapi import status
from sqlalchemy import select

from src.models import books
from src.models import sallers
from configurations.database import create_db_and_tables, delete_db_and_tables, global_init
from jose import JWTError, jwt
import time

import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

result = {
    "books": [
        {"author": "fdhgdh", "title": "jdhdj", "year": 1997},
        {"author": "fdhgdfgfrh", "title": "jrrgdhdj", "year": 2001},
    ]
}
def setup_module(module):
    global_init()


@pytest.mark.asyncio
async def test_create_saller(async_client):
    data = {"first_name": "Иван", "last_name": "Иванов", "e_mail": "email@gmail.com", "password": "qwerty"}
    response = await async_client.post("/api/v1/saller/", json=data)

    assert response.status_code == status.HTTP_201_CREATED

    result_data = response.json()

    assert result_data == {
        "id": 1,
        "first_name": "Иван",
        "last_name": "Иванов",
        "e_mail": "email@gmail.com"
    }

@pytest.mark.asyncio
async def test_token(db_session, async_client):
    saller = sallers.Saller(first_name="Петя", last_name="Петров", e_mail="email2@gmail.com", password="qwerty2")

    db_session.add_all([saller])
    await db_session.commit()
    data = {"e_mail": "email2@gmail.com", "password": "qwerty2"}
    response = await async_client.post("/api/v1/saller/token", params=data)

    assert response.status_code == status.HTTP_200_OK

    result_data = response.json()

    assert "access_token" in result_data
    assert "token_type" in result_data
    assert result_data["token_type"] == "Bearer"

# Тест на ручку создающую книгу
@pytest.mark.asyncio
async def test_create_book(db_session, async_client):
    saller = sallers.Saller(first_name="Рома", last_name="Романов", e_mail="email3@gmail.com", password="qwerty3")
    db_session.add_all([saller])
    await db_session.commit()

    data_token = {"e_mail": "email3@gmail.com", "password": "qwerty3"}
    response_token = await async_client.post("/api/v1/saller/token", params=data_token)
    result_data = response_token.json()
    token = "Bearer " + result_data["access_token"]

    payload = jwt.decode(result_data["access_token"], SECRET_KEY, algorithms=[ALGORITHM])
    id: int = payload.get("user_id")

    data = {"title": "Wrong Code", "author": "Robert Martin", "count_pages": 104, "year": 2007, "saller_id": id}
    response = await async_client.post("/api/v1/books/", json=data, params={"token": token})

    assert response.status_code == status.HTTP_201_CREATED

    result_data = response.json()

    assert result_data == {
        "id": 1,
        "title": "Wrong Code",
        "author": "Robert Martin",
        "count_pages": 104,
        "year": 2007,
        "saller_id": id
    }

# Тест на ручку получения списка книг
@pytest.mark.asyncio
async def test_get_books(db_session, async_client):

    saller = sallers.Saller(first_name="Кирилл", last_name="Кириллов", e_mail="email4@gmail.com", password="qwerty4")
    db_session.add_all([saller])
    await db_session.commit()

    book = books.Book(author="Pushkin", title="Eugeny Onegin", year=2001, count_pages=104, saller_id=saller.id)
    book_2 = books.Book(author="Lermontov", title="Mziri", year=1997, count_pages=104, saller_id=saller.id)
    db_session.add_all([book, book_2])
    await db_session.commit()


    response = await async_client.get("/api/v1/books/")

    assert response.status_code == status.HTTP_200_OK
    expected_books = [
        {"title": "Eugeny Onegin", "author": "Pushkin", "year": 2001, "id": book.id, "count_pages": 104, "saller_id": saller.id},
        {"title": "Mziri", "author": "Lermontov", "year": 1997, "id": book_2.id, "count_pages": 104, "saller_id": saller.id},
    ]

    response_books = response.json()["books"]

    # Проверяем поочередно каждый элемент массива
    for expected_book in expected_books:
        # Проверяем, что текущий элемент expected_book присутствует в response_books
        assert expected_book in response_books


# Тест на ручку получения одной книги
@pytest.mark.asyncio
async def test_get_single_book(db_session, async_client):
    saller = sallers.Saller(first_name="Игнат", last_name="Игнатьев", e_mail="email5@gmail.com", password="qwerty5")
    db_session.add_all([saller])
    await db_session.commit()

    book = books.Book(author="Pushkin", title="Eugeny Onegin", year=2001, count_pages=104, saller_id = saller.id)

    db_session.add_all([book])
    await db_session.commit()

    response = await async_client.get(f"/api/v1/books/{book.id}")

    assert response.status_code == status.HTTP_200_OK

    # Проверяем интерфейс ответа, на который у нас есть контракт.
    assert response.json() == {
        "title": "Eugeny Onegin",
        "author": "Pushkin",
        "year": 2001,
        "count_pages": 104,
        "id": book.id,
        "saller_id":saller.id
    }


# Тест на ручку удаления книги
@pytest.mark.asyncio
async def test_delete_book(db_session, async_client):
    saller = sallers.Saller(first_name="Михаил", last_name="Михайлов", e_mail="email6@gmail.com", password="qwerty6")
    db_session.add_all([saller])
    await db_session.commit()

    book = books.Book(author="Pushkin", title="Eugeny Onegin", year=2001, count_pages=104, saller_id=saller.id)
    db_session.add_all([book])
    await db_session.commit()

    response = await async_client.delete(f"/api/v1/books/{book.id}")

    assert response.status_code == status.HTTP_204_NO_CONTENT
    await db_session.commit()

    all_books = await db_session.execute(select(books.Book))
    res = all_books.scalars().all()
    for re in res:
        assert re.id != book.id


# Тест на ручку обновления книги
@pytest.mark.asyncio
async def test_update_book(db_session, async_client):
    saller = sallers.Saller(first_name="Никита", last_name="Никитов", e_mail="email7@gmail.com", password="qwerty7")
    db_session.add_all([saller])
    await db_session.commit()

    data_token = {"e_mail": "email7@gmail.com", "password": "qwerty7"}
    response_token = await async_client.post("/api/v1/saller/token", params=data_token)
    result_data = response_token.json()
    token = "Bearer " + result_data["access_token"]

    payload = jwt.decode(result_data["access_token"], SECRET_KEY, algorithms=[ALGORITHM])
    id: int = payload.get("user_id")

    book = books.Book(author="Pushkin", title="Eugeny Onegin", year=2001, count_pages=104, saller_id=id)
    db_session.add_all([book])
    await db_session.commit()

    response = await async_client.put(
        f"/api/v1/books/{book.id}",
        json={"title": "Mziri", "author": "Lermontov", "count_pages": 100, "year": 2007, "id": book.id, "saller_id": saller.id},
        params = {"token": token}
    )

    assert response.status_code == status.HTTP_200_OK
    await db_session.flush()

    assert response.json()["title"] == "Mziri"
    assert response.json()["author"] == "Lermontov"
    assert response.json()["count_pages"] == 100
    assert response.json()["year"] == 2007
    assert response.json()["id"] == book.id

@pytest.mark.asyncio
async def test_get_all_sallers(db_session, async_client):
    saller = sallers.Saller(first_name="Филипп", last_name="Филлипов", e_mail="email8@gmail.com", password="qwerty8")
    saller2 = sallers.Saller(first_name="Павел", last_name="Павлов", e_mail="email9@gmail.com", password="qwerty9")
    db_session.add_all([saller,saller2])
    await db_session.commit()

    response = await async_client.get("/api/v1/saller/")

    assert response.status_code == status.HTTP_200_OK
    expected_sallers = [
        {"first_name": "Филипп", "last_name": "Филлипов", "e_mail": "email8@gmail.com", "id": saller.id},
        {"first_name": "Павел", "last_name": "Павлов", "e_mail": "email9@gmail.com", "id": saller2.id},
    ]

    response_sallers = response.json()["sallers"]

    # Проверяем поочередно каждый элемент массива
    for expected_saller in expected_sallers:
        # Проверяем, что текущий элемент expected_book присутствует в response_books
        assert expected_saller in response_sallers


@pytest.mark.asyncio
async def test_get_single_saller(db_session, async_client):
    saller = sallers.Saller(first_name="Матвей", last_name="Матвеев", e_mail="email10@gmail.com", password="qwerty10")
    db_session.add_all([saller])
    await db_session.commit()

    data_token = {"e_mail": "email10@gmail.com", "password": "qwerty10"}
    response_token = await async_client.post("/api/v1/saller/token", params=data_token)
    result_data = response_token.json()
    token = "Bearer " + result_data["access_token"]

    payload = jwt.decode(result_data["access_token"], SECRET_KEY, algorithms=[ALGORITHM])
    id: int = payload.get("user_id")

    book = books.Book(author="Pushkin", title="Eugeny Onegin", year=2005, count_pages=104, saller_id = id)

    db_session.add_all([book])
    await db_session.commit()

    response = await async_client.get(f"/api/v1/saller/{saller.id}", params = {"token": token})

    assert response.status_code == status.HTTP_200_OK

    # Проверяем интерфейс ответа, на который у нас есть контракт.
    assert response.json() == {
        "id": id,
        "first_name": "Матвей",
        "last_name": "Матвеев",
        "e_mail": "email10@gmail.com",
        "books":[
            {
            "id": book.id,
            "title": "Eugeny Onegin",
            "author": "Pushkin",
            "year": 2005,
            "count_pages": 104,
            "saller_id": saller.id
            }
        ]
    }

@pytest.mark.asyncio
async def test_delete_saller(db_session, async_client):
    saller = sallers.Saller(first_name="Денис", last_name="Денисов", e_mail="email11@gmail.com", password="qwerty11")
    db_session.add_all([saller])
    await db_session.commit()

    book = books.Book(author="Pushkin", title="Eugeny Onegin", year=2011, count_pages=104, saller_id=saller.id)
    db_session.add_all([book])
    await db_session.commit()

    response = await async_client.delete(f"/api/v1/saller/{saller.id}")

    assert response.status_code == status.HTTP_204_NO_CONTENT
    await db_session.commit()

    all_books = await db_session.execute(select(books.Book))
    res = all_books.scalars().all()
    for re in res:
        assert re.id != book.id

    all_sallers = await db_session.execute(select(sallers.Saller))
    res = all_sallers.scalars().all()
    for re in res:
        assert re.id != saller.id


@pytest.mark.asyncio
async def test_update_saller(db_session, async_client):
    saller = sallers.Saller(first_name="Юра", last_name="Юриев", e_mail="email12@gmail.com", password="qwerty12")
    db_session.add_all([saller])
    await db_session.commit()

    response = await async_client.put(
        f"/api/v1/saller/{saller.id}",
        json={"first_name": "Иполит", "last_name": "Иполитов", "e_mail": "email120@gmail.com"}
    )

    assert response.status_code == status.HTTP_200_OK
    await db_session.flush()

    assert response.json()["first_name"] == "Иполит"
    assert response.json()["last_name"] == "Иполитов"
    assert response.json()["e_mail"] == "email120@gmail.com"
