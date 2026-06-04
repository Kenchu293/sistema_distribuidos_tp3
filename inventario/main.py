
import asyncio
import grpc
import inventory_pb2
import inventory_pb2_grpc
from fastapi import FastAPI, HTTPException
import redis
app = FastAPI(title="inventario")
r = redis.Redis(host="redis", port=6379)
cantidad_inventario={1: 20, 2: 40, 3: 30, 4: 30,}
class inventari(inventory_pb2_grpc.InventoryServiceServicer):
   
    
    
    async def ReserveStock(self, request, context):
        producto_id = request.producto_id
        cantidad = request.cantidad

        if producto_id not in cantidad_inventario:
            return inventory_pb2.ReserveStockResponse(
                success=False,
                message="El Producto no Existe"
            )

        if cantidad_inventario[producto_id] < cantidad:
            return inventory_pb2.ReserveStockResponse(
                success=False,
                message="Producto insuficiente"
            )

        cantidad_inventario[producto_id] -= cantidad

        return inventory_pb2.ReserveStockResponse(
            success=True,
            message=f"cantidad reservado. cantidad restante: {cantidad_inventario[producto_id]}"
        )
async def start_grpc_server():
    server = grpc.aio.server()
    inventory_pb2_grpc.add_InventoryServiceServicer_to_server(
        inventari(), server
    )
    server.add_insecure_port("[::]:50051")
    await server.start()
    await server.wait_for_termination()

 
@app.post("/reservar")
def reserve(producto_id: int, cantidad: int):

    lock = r.set(
        f"lock:{producto_id}",
        "reserved",
        nx=True,
        ex=5
    )

    if not lock:
        raise HTTPException(
            status_code=503,
            detail="Otro usuario está comprando, reintentá"
        )

    try:
        # Leer stock desde Redis
        stock = int(r.get(f"stock:{producto_id}") or 0)

        # Verificar stock
        if stock < cantidad:
            raise HTTPException(
                status_code=400,
                detail="Sin stock"
            )

        # Descontar stock
        nuevo_stock = stock - cantidad

        r.set(
            f"stock:{producto_id}",
            nuevo_stock
        )

        return {
            "status": "reservado",
            "stock restante": nuevo_stock
        }

    finally:
        r.delete(f"lock:{producto_id}")
    # ---------------------------------------------------------




@app.on_event("startup")
async def startup_event():
    for producto, stock in cantidad_inventario.items():
        r.set(f"stock:{producto}", stock)

    asyncio.create_task(start_grpc_server())

@app.get("/conexion")
def conexion():
    return {"status": "ok", "service": "inventorio"}

@app.get("/cantidad")
def get_cantidad():
    return cantidad_inventario
    
@app.post("/reset_stock")
def reset_stock(producto_id: int, stock: int):
    r.set(f"stock:{producto_id}", stock)
    return {"ok": True}

@app.get("/stock/{producto_id}")
def stock(producto_id: int):
    return {"stock": int(r.get(f"stock:{producto_id}") or 0)}