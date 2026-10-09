# Sistema de gestion de pedidos - Tienda online

API REST hecha con Flask y MongoDB (base de datos documental).

## Como ejecutarlo

1. Tener MongoDB corriendo en `localhost:27017` (o definir la variable `MONGO_URI`).
2. Instalar dependencias:

```
pip install -r requirements.txt
```

3. Levantar la API:

```
python app.py
```

La API queda en `http://localhost:5000`. La base se llama `tienda_online`.

## Modelo documental

Se usan tres colecciones: `clientes`, `productos` y `pedidos`.

### clientes

```json
{
  "_id": "6650f1c2a1b2c3d4e5f60001",
  "nombre": "Maria",
  "apellido": "Gomez"
}
```

### productos

```json
{
  "_id": "6650f1c2a1b2c3d4e5f60002",
  "nombre": "Teclado mecanico",
  "categoria": "Perifericos",
  "precio": 45000,
  "stock": 20
}
```

### pedidos

```json
{
  "_id": "6650f1c2a1b2c3d4e5f60003",
  "cliente_id": "6650f1c2a1b2c3d4e5f60001",
  "fecha": "2026-10-08T21:30:00",
  "items": [
    {
      "producto_id": "6650f1c2a1b2c3d4e5f60002",
      "nombre": "Teclado mecanico",
      "precio_unitario": 45000,
      "cantidad": 2,
      "subtotal": 90000
    }
  ],
  "total": 90000
}
```

### Decisiones de diseno

- **Clientes y productos son colecciones separadas** porque existen por si solos y se consultan por su cuenta.
- **El pedido referencia al cliente con `cliente_id`** (referencia), ya que un cliente puede tener muchos pedidos y no conviene duplicar sus datos en cada uno.
- **Los items van embebidos dentro del pedido**, porque no tienen sentido fuera de el y siempre se leen junto con el pedido (una sola consulta).
- **Dentro de cada item se copian `nombre` y `precio_unitario`** del producto al momento de comprar. Asi, si despues se cambia el precio o se elimina el producto, el pedido historico no se altera.
- El `total` se guarda calculado para no tener que recorrer los items cada vez.

## Endpoints

| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| POST | `/productos` | Crear un producto |
| GET | `/productos` | Obtener todos los productos |
| GET | `/productos/<id>` | Obtener un producto |
| PATCH | `/productos/<id>` | Modificar nombre, precio y/o stock |
| DELETE | `/productos/<id>` | Eliminar un producto |
| POST | `/clientes` | Crear un cliente |
| GET | `/clientes` | Obtener todos los clientes |
| POST | `/pedidos` | Crear un pedido |
| GET | `/pedidos` | Listar pedidos (extra, para verificar) |

### Ejemplo: crear un pedido

```json
POST /pedidos
{
  "cliente_id": "6650f1c2a1b2c3d4e5f60001",
  "items": [
    { "producto_id": "6650f1c2a1b2c3d4e5f60002", "cantidad": 2 }
  ]
}
```

Al crear un pedido se valida que el cliente y los productos existan y que haya stock suficiente (error 409 si no). Si todo esta bien, se descuenta el stock de cada producto.

## Postman

La coleccion esta en `postman/tienda_online.postman_collection.json`. Se importa desde Postman con *Import*. Usa la variable `base_url` (por defecto `http://localhost:5000`) y guarda automaticamente los ids de producto, cliente y pedido para encadenar las requests en orden.

## Tests

```
pytest
```

Los tests usan `mongomock`, asi que no hace falta tener MongoDB corriendo.
