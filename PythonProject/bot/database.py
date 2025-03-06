from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, TIMESTAMP, func, BigInteger

# Подключение к базе данных PostgreSQL
DATABASE_URL = "postgresql+asyncpg://postgres:Volodinn@localhost:5432/mydatabase"

# Создаём асинхронный движок SQLAlchemy
engine = create_async_engine(DATABASE_URL, echo=False)

# Создаём сессии
AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

# Базовый класс для моделей
Base = declarative_base()

# Модель стихотворений
class Poem(Base):
    __tablename__ = "poems"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    title =  Column(String(255), nullable=False)  # Добавляем название стиха
    text = Column(String, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())  # Добавляем дату создания

class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True)  # Telegram ID пользователя
    username = Column(String, nullable=True)  # Никнейм (@username)
    first_name = Column(String, nullable=True)  # Имя
    last_name = Column(String, nullable=True)  # Фамилия

async def init_db():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("База данных инициализирована")
    except Exception as e:
        print(f"Ошибка при создании базы данных: {e}")

