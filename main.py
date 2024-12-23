import json
import asyncio

from fastapi import FastAPI, Depends, HTTPException, WebSocket
from starlette.websockets import WebSocketDisconnect
from sqlmodel import Session, select
from typing import List
from database import create_db_and_tables, get_session, delete_all_data, Product, ProductIn
from parser import background_parser

app = FastAPI()

class ConnectionManager:
    def __init__(self):
        self.connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.connections.append(websocket)

    async def disconnect(self, websocket: WebSocket):
        self.connections.remove(websocket)

    async def broadcast(self, event: str, payload: dict):
        message = {"event": event, "payload": payload}
        for connection in self.connections:
            await connection.send_text(json.dumps(message))

manager = ConnectionManager()

@app.on_event("startup")
async def startup():
    create_db_and_tables()
    session = next(get_session())
    delete_all_data(session)
    asyncio.create_task(background_parser("https://steampay.com/games", session))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            print(f"Received data: {data}")
            await websocket.send_text(f"Echo: {data}")
    except WebSocketDisconnect as e:
        await manager.disconnect(websocket)

@app.get("/products", response_model=List[ProductIn])
async def get_products(session: Session = Depends(get_session)):
    products = session.exec(select(Product)).all()
    await manager.broadcast("get_products", {"products": [product.dict() for product in products]})
    return products

@app.get("/products/{product_id}", response_model=ProductIn)
async def get_product(product_id: int, session: Session = Depends(get_session)):
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    await manager.broadcast("get_product", {"product": product.dict()})
    return product

@app.post("/products", response_model=ProductIn)
async def create_product(product: ProductIn, session: Session = Depends(get_session)):
    db_product = Product(name=product.name, price=product.price)
    session.add(db_product)
    session.commit()
    session.refresh(db_product)
    await manager.broadcast("create_product", {"product": db_product.dict()})
    return db_product

@app.put("/products/{product_id}", response_model=ProductIn)
async def update_product(product_id: int, product: ProductIn, session: Session = Depends(get_session)):
    db_product = session.get(Product, product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    db_product.name = product.name
    db_product.price = product.price
    session.add(db_product)
    session.commit()
    session.refresh(db_product)
    await manager.broadcast("update_product", {"product": db_product.dict()})
    return db_product

@app.delete("/products/{product_id}")
async def delete_product(product_id: int, session: Session = Depends(get_session)):
    db_product = session.get(Product, product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    session.delete(db_product)
    session.commit()
    await manager.broadcast("delete_product", {"product_id": product_id})
    return {"message": "Product deleted successfully"}
