import os
import sys

import mongomock
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import app as modulo_app


@pytest.fixture
def client():
    # se reemplaza la base real por una falsa en memoria
    modulo_app.db = mongomock.MongoClient()["tienda_test"]
    modulo_app.app.config["TESTING"] = True
    return modulo_app.app.test_client()


def crear_producto(client, stock=10, precio=100):
    respuesta = client.post("/productos", json={
        "nombre": "Mouse", "categoria": "Perifericos", "precio": precio, "stock": stock
    })
    return respuesta.get_json()


def crear_cliente(client):
    return client.post("/clientes", json={"nombre": "Maria", "apellido": "Gomez"}).get_json()


def test_crear_y_obtener_producto(client):
    producto = crear_producto(client)
    assert producto["nombre"] == "Mouse"

    respuesta = client.get("/productos/" + producto["_id"])
    assert respuesta.status_code == 200
    assert respuesta.get_json()["stock"] == 10

    assert len(client.get("/productos").get_json()) == 1


def test_producto_invalido(client):
    respuesta = client.post("/productos", json={"nombre": "Mouse"})
    assert respuesta.status_code == 400

    respuesta = client.post("/productos", json={
        "nombre": "Mouse", "categoria": "X", "precio": -5, "stock": 1
    })
    assert respuesta.status_code == 400


def test_producto_inexistente(client):
    assert client.get("/productos/abc").status_code == 400
    assert client.get("/productos/6650f1c2a1b2c3d4e5f60099").status_code == 404


def test_modificar_producto(client):
    producto = crear_producto(client)
    url = "/productos/" + producto["_id"]

    assert client.patch(url, json={"precio": 250}).get_json()["precio"] == 250
    assert client.patch(url, json={"nombre": "Mouse gamer"}).get_json()["nombre"] == "Mouse gamer"
    assert client.patch(url, json={"stock": 3}).get_json()["stock"] == 3
    assert client.patch(url, json={}).status_code == 400


def test_eliminar_producto(client):
    producto = crear_producto(client)
    url = "/productos/" + producto["_id"]

    assert client.delete(url).status_code == 200
    assert client.get(url).status_code == 404
    assert client.delete(url).status_code == 404


def test_clientes(client):
    crear_cliente(client)
    assert len(client.get("/clientes").get_json()) == 1
    assert client.post("/clientes", json={"nombre": "Solo nombre"}).status_code == 400


def test_crear_pedido_descuenta_stock(client):
    producto = crear_producto(client, stock=10, precio=100)
    cliente = crear_cliente(client)

    respuesta = client.post("/pedidos", json={
        "cliente_id": cliente["_id"],
        "items": [{"producto_id": producto["_id"], "cantidad": 3}],
    })
    assert respuesta.status_code == 201
    pedido = respuesta.get_json()
    assert pedido["total"] == 300
    assert pedido["items"][0]["precio_unitario"] == 100

    stock = client.get("/productos/" + producto["_id"]).get_json()["stock"]
    assert stock == 7


def test_pedido_sin_stock(client):
    producto = crear_producto(client, stock=2)
    cliente = crear_cliente(client)

    respuesta = client.post("/pedidos", json={
        "cliente_id": cliente["_id"],
        "items": [{"producto_id": producto["_id"], "cantidad": 5}],
    })
    assert respuesta.status_code == 409
    assert client.get("/productos/" + producto["_id"]).get_json()["stock"] == 2


def test_pedido_cliente_inexistente(client):
    producto = crear_producto(client)
    respuesta = client.post("/pedidos", json={
        "cliente_id": "6650f1c2a1b2c3d4e5f60099",
        "items": [{"producto_id": producto["_id"], "cantidad": 1}],
    })
    assert respuesta.status_code == 404
