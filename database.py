from sqlmodel import SQLModel, Field, create_engine, Session
from pydantic import BaseModel

DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(DATABASE_URL)

class Product(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    name: str
    price: float

class ProductIn(BaseModel):
    name: str
    price: float

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

def delete_all_data(session: Session):
    session.query(Product).delete()
    session.commit()
