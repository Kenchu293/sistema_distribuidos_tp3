import requests
import time
from concurrent.futures import ThreadPoolExecutor

BASE_URL = "http://localhost:8002"


# ==========================
# Funciones auxiliares
# ==========================

def reset_stock(producto_id, stock):
    response = requests.post(
        f"{BASE_URL}/reset_stock",
        params={
            "producto_id": producto_id,
            "stock": stock
        }
    )

    assert response.status_code == 200


def obtener_stock(producto_id):
    response = requests.get(
        f"{BASE_URL}/stock/{producto_id}"
    )

    assert response.status_code == 200

    return response.json()["stock"]


def comprar(producto_id=1, cantidad=1):
    return requests.post(
        f"{BASE_URL}/reservar",
        params={
            "producto_id": producto_id,
            "cantidad": cantidad
        }
    )


# ==========================
# TEST 1
# Dos usuarios compran
# el mismo producto
# ==========================

def test_dos_usuarios_mismo_producto():

    print("\n=== TEST 1 ===")

    reset_stock(1, 1)

    with ThreadPoolExecutor(max_workers=2) as executor:

        respuestas = list(
            executor.map(
                lambda _: comprar(),
                range(2)
            )
        )

    exitos = sum(
        1 for r in respuestas
        if r.status_code == 200
    )

    errores = len(respuestas) - exitos

    stock_final = obtener_stock(1)

    print("Compras exitosas:", exitos)
    print("Errores:", errores)
    print("Stock final:", stock_final)

    assert exitos == 1
    assert errores == 1
    assert stock_final == 0


# ==========================
# TEST 2
# 50 usuarios
# stock = 10
# ==========================

def test_50_usuarios_stock_10():

    print("\n=== TEST 2 ===")

    reset_stock(1, 10)

    with ThreadPoolExecutor(max_workers=50) as executor:

        respuestas = list(
            executor.map(
                lambda _: comprar(),
                range(50)
            )
        )

    exitos = sum(
        1 for r in respuestas
        if r.status_code == 200
    )

    errores = len(respuestas) - exitos

    stock_final = obtener_stock(1)

    print("Compras exitosas:", exitos)
    print("Errores:", errores)
    print("Stock final:", stock_final)

    assert exitos <= 10
    assert stock_final >= 0

    # Overselling nunca permitido
    assert stock_final == 0


# ==========================
# TEST 3
# Redis caído o lento
# ==========================

def test_redis_caido():

    print("\n=== TEST 3 ===")

    inicio = time.time()

    try:

        response = requests.post(
            f"{BASE_URL}/reservar",
            params={
                "producto_id": 1,
                "cantidad": 1
            },
            timeout=5
        )

        duracion = time.time() - inicio

        print("Status:", response.status_code)
        print("Tiempo:", duracion)

        assert duracion < 5

    except requests.exceptions.RequestException:

        duracion = time.time() - inicio

        print("Tiempo:", duracion)

        assert duracion < 5