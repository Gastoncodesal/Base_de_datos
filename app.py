import os
from datetime import datetime

from bson import ObjectId
from bson.errors import InvalidId
from flask import Flask, jsonify, request
from pymongo import MongoClient

app = Flask(__name__)

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
db = MongoClient(MONGO_URI)["tienda_online"]


# ---------- funciones auxiliares ----------

def convertir_id(texto):
    """Devuelve un ObjectId o None si el texto no es un id valido."""
    try:
        return ObjectId(texto)
    except (InvalidId, TypeError):
        return None


def serializar(doc):
    """Pasa los ObjectId a texto para poder devolver el documento como JSON."""
    resultado = {}
    for clave, valor in doc.items():
        if isinstance(valor, ObjectId):
            resultado[clave] = str(valor)
        elif isinstance(valor, datetime):
            resultado[clave] = valor.isoformat()
        elif isinstance(valor, list):
            resultado[clave] = [serializar(v) if isinstance(v, dict) else v for v in valor]
        else:
            resultado[clave] = valor
    return resultado


def error(mensaje, codigo):
    return jsonify({"error": mensaje}), codigo


def es_texto(valor):
    return isinstance(valor, str) and valor.strip() != ""


def es_numero(valor):
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def es_entero(valor):
    return isinstance(valor, int) and not isinstance(valor, bool)


# ---------- productos ----------

@app.route("/productos", methods=["POST"])
def crear_producto():
    datos = request.get_json(silent=True) or {}

    if not es_texto(datos.get("nombre")):
        return error("El nombre es obligatorio", 400)
    if not es_texto(datos.get("categoria")):
        return error("La categoria es obligatoria", 400)
    if not es_numero(datos.get("precio")) or datos["precio"] < 0:
        return error("El precio debe ser un numero mayor o igual a 0", 400)
    if not es_entero(datos.get("stock")) or datos["stock"] < 0:
        return error("El stock debe ser un entero mayor o igual a 0", 400)

    producto = {
        "nombre": datos["nombre"].strip(),
        "categoria": datos["categoria"].strip(),
        "precio": datos["precio"],
        "stock": datos["stock"],
    }
    resultado = db.productos.insert_one(producto)
    producto["_id"] = resultado.inserted_id
    return jsonify(serializar(producto)), 201


@app.route("/productos", methods=["GET"])
def obtener_productos():
    productos = [serializar(p) for p in db.productos.find()]
    return jsonify(productos), 200


@app.route("/productos/<id>", methods=["GET"])
def obtener_producto(id):
    oid = convertir_id(id)
    if oid is None:
        return error("Id invalido", 400)

    producto = db.productos.find_one({"_id": oid})
    if producto is None:
        return error("Producto no encontrado", 404)
    return jsonify(serializar(producto)), 200


@app.route("/productos/<id>", methods=["PATCH", "PUT"])
def modificar_producto(id):
    oid = convertir_id(id)
    if oid is None:
        return error("Id invalido", 400)

    datos = request.get_json(silent=True) or {}
    cambios = {}

    # solo se pueden modificar nombre, precio y stock
    if "nombre" in datos:
        if not es_texto(datos["nombre"]):
            return error("El nombre no puede estar vacio", 400)
        cambios["nombre"] = datos["nombre"].strip()
    if "precio" in datos:
        if not es_numero(datos["precio"]) or datos["precio"] < 0:
            return error("El precio debe ser un numero mayor o igual a 0", 400)
        cambios["precio"] = datos["precio"]
    if "stock" in datos:
        if not es_entero(datos["stock"]) or datos["stock"] < 0:
            return error("El stock debe ser un entero mayor o igual a 0", 400)
        cambios["stock"] = datos["stock"]

    if not cambios:
        return error("Hay que enviar al menos nombre, precio o stock", 400)

    resultado = db.productos.update_one({"_id": oid}, {"$set": cambios})
    if resultado.matched_count == 0:
        return error("Producto no encontrado", 404)

    return jsonify(serializar(db.productos.find_one({"_id": oid}))), 200


@app.route("/productos/<id>", methods=["DELETE"])
def eliminar_producto(id):
    oid = convertir_id(id)
    if oid is None:
        return error("Id invalido", 400)

    resultado = db.productos.delete_one({"_id": oid})
    if resultado.deleted_count == 0:
        return error("Producto no encontrado", 404)
    return jsonify({"mensaje": "Producto eliminado"}), 200


# ---------- clientes ----------

@app.route("/clientes", methods=["POST"])
def crear_cliente():
    datos = request.get_json(silent=True) or {}

    if not es_texto(datos.get("nombre")):
        return error("El nombre es obligatorio", 400)
    if not es_texto(datos.get("apellido")):
        return error("El apellido es obligatorio", 400)

    cliente = {
        "nombre": datos["nombre"].strip(),
        "apellido": datos["apellido"].strip(),
    }
    resultado = db.clientes.insert_one(cliente)
    cliente["_id"] = resultado.inserted_id
    return jsonify(serializar(cliente)), 201


@app.route("/clientes", methods=["GET"])
def obtener_clientes():
    clientes = [serializar(c) for c in db.clientes.find()]
    return jsonify(clientes), 200


# ---------- pedidos ----------

@app.route("/pedidos", methods=["POST"])
def crear_pedido():
    datos = request.get_json(silent=True) or {}

    cliente_id = convertir_id(datos.get("cliente_id"))
    if cliente_id is None:
        return error("cliente_id invalido", 400)
    if db.clientes.find_one({"_id": cliente_id}) is None:
        return error("Cliente no encontrado", 404)

    items_pedidos = datos.get("items")
    if not isinstance(items_pedidos, list) or len(items_pedidos) == 0:
        return error("El pedido necesita al menos un item", 400)

    # primero se validan todos los items, recien despues se toca el stock
    items = []
    total = 0
    for item in items_pedidos:
        if not isinstance(item, dict):
            return error("Cada item debe ser un objeto", 400)

        producto_id = convertir_id(item.get("producto_id"))
        cantidad = item.get("cantidad")
        if producto_id is None:
            return error("producto_id invalido", 400)
        if not es_entero(cantidad) or cantidad <= 0:
            return error("La cantidad debe ser un entero mayor a 0", 400)

        producto = db.productos.find_one({"_id": producto_id})
        if producto is None:
            return error("Producto no encontrado: " + str(producto_id), 404)
        if producto["stock"] < cantidad:
            return error("Stock insuficiente para " + producto["nombre"], 409)

        subtotal = producto["precio"] * cantidad
        total += subtotal
        # se guarda una copia del nombre y del precio al momento de la compra
        items.append({
            "producto_id": producto_id,
            "nombre": producto["nombre"],
            "precio_unitario": producto["precio"],
            "cantidad": cantidad,
            "subtotal": subtotal,
        })

    # se descuenta el stock; la condicion evita que quede negativo
    descontados = []
    for item in items:
        resultado = db.productos.update_one(
            {"_id": item["producto_id"], "stock": {"$gte": item["cantidad"]}},
            {"$inc": {"stock": -item["cantidad"]}},
        )
        if resultado.modified_count == 0:
            # alguien se quedo con el stock en el medio: se devuelve lo descontado
            for anterior in descontados:
                db.productos.update_one(
                    {"_id": anterior["producto_id"]},
                    {"$inc": {"stock": anterior["cantidad"]}},
                )
            return error("Stock insuficiente para " + item["nombre"], 409)
        descontados.append(item)

    pedido = {
        "cliente_id": cliente_id,
        "fecha": datetime.now(),
        "items": items,
        "total": total,
    }
    resultado = db.pedidos.insert_one(pedido)
    pedido["_id"] = resultado.inserted_id
    return jsonify(serializar(pedido)), 201


@app.route("/pedidos", methods=["GET"])
def obtener_pedidos():
    pedidos = [serializar(p) for p in db.pedidos.find()]
    return jsonify(pedidos), 200


if __name__ == "__main__":
    app.run(debug=True, port=5000)
