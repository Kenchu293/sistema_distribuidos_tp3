import json
import grpc
import pika
import inventory_pb2
import inventory_pb2_grpc
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx

app = FastAPI(title="ordenes")

class OrderRequest(BaseModel):
    producto_id: int
    cantidad: int


@app.get("/conexion")
def conexion():
    return {"status": "ok", "service": "ordenes"}

async def get_producto(producto_id: int):

    async with httpx.AsyncClient() as client:

        response = await client.get(
            f"http://productos:8000/productos/{producto_id}"
        )

        if response.status_code != 200:
            return None

        return response.json()
    

async def reserve_stock(producto_id: int, cantidad: int):
    async with grpc.aio.insecure_channel("inventario:50051") as channel:
        stub = inventory_pb2_grpc.InventoryServiceStub(channel)

        response = await stub.ReserveStock(
            inventory_pb2.ReserveStockRequest(
                producto_id=producto_id,
                cantidad=cantidad
            ),
            timeout=5
        )

        return response

def publish_order_event(order_data: dict):
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host="rabbitmq")
    )
    channel = connection.channel()

    channel.queue_declare(queue="order_created", durable=True)

    channel.basic_publish(
        exchange="",
        routing_key="order_created",
        body=json.dumps(order_data),
        properties=pika.BasicProperties(
            delivery_mode=2
        )
    )

    connection.close()

@app.post("/ordenes")
async def crear_orden(orden: OrderRequest):
    try:
        producto = await get_producto(orden.producto_id)

        if not producto:
            raise HTTPException(
                status_code=404,
                detail="Producto no encontrado"
            )

        stock_response = await reserve_stock(
            orden.producto_id,
            orden.cantidad
        )
    except grpc.aio.AioRpcError:
        raise HTTPException(
            status_code=503,
            detail="No se pudo conectar con inventory-service"
        )

    if not stock_response.success:
        raise HTTPException(
            status_code=400,
            detail=stock_response.message
        )

    orden_data = {
        "orden_id": 1,
        "producto_id": orden.producto_id,
        "cantidad": orden.cantidad,
        "producto": producto,
        "status": "created"
    }

    publish_order_event(orden_data)

    return {
        "message": "Pedido Hecho correctamente",
        "inventory_message": stock_response.message,
        "order": orden_data
    }