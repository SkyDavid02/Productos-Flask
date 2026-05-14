from werkzeug.security import generate_password_hash

from extensions import get_db


DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin123"


def row_to_dict(row):
    if row is None:
        return None
    return dict(row)


def init_db():
    db = get_db()
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        )
        """
    )
    db.commit()

    if obtener_usuario_por_username(DEFAULT_USERNAME) is None:
        crear_usuario(DEFAULT_USERNAME, DEFAULT_PASSWORD)

    usuario_admin = obtener_usuario_por_username(DEFAULT_USERNAME)

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            nombre TEXT NOT NULL,
            descripcion TEXT NOT NULL,
            precio REAL NOT NULL CHECK(precio >= 0),
            stock INTEGER NOT NULL CHECK(stock >= 0),
            FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
        )
        """
    )
    db.commit()

    migrar_productos_a_usuario(usuario_admin["id"])


def migrar_productos_a_usuario(usuario_id):
    db = get_db()
    columnas = db.execute("PRAGMA table_info(productos)").fetchall()
    nombres_columnas = [columna["name"] for columna in columnas]

    if "usuario_id" not in nombres_columnas:
        db.execute("ALTER TABLE productos ADD COLUMN usuario_id INTEGER")

    db.execute(
        "UPDATE productos SET usuario_id = ? WHERE usuario_id IS NULL",
        (usuario_id,),
    )
    db.commit()


def obtener_productos(usuario_id):
    db = get_db()
    productos = db.execute(
        """
        SELECT id, nombre, descripcion, precio, stock
        FROM productos
        WHERE usuario_id = ?
        ORDER BY id DESC
        """,
        (usuario_id,),
    ).fetchall()
    return [row_to_dict(producto) for producto in productos]


def obtener_producto(producto_id, usuario_id):
    db = get_db()
    producto = db.execute(
        """
        SELECT id, nombre, descripcion, precio, stock
        FROM productos
        WHERE id = ? AND usuario_id = ?
        """,
        (producto_id, usuario_id),
    ).fetchone()
    return row_to_dict(producto)


def crear_producto(data, usuario_id):
    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO productos (usuario_id, nombre, descripcion, precio, stock)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            usuario_id,
            data["nombre"],
            data["descripcion"],
            data["precio"],
            data["stock"],
        ),
    )
    db.commit()
    return obtener_producto(cursor.lastrowid, usuario_id)


def actualizar_producto(producto_id, data, usuario_id):
    db = get_db()
    db.execute(
        """
        UPDATE productos
        SET nombre = ?, descripcion = ?, precio = ?, stock = ?
        WHERE id = ? AND usuario_id = ?
        """,
        (
            data["nombre"],
            data["descripcion"],
            data["precio"],
            data["stock"],
            producto_id,
            usuario_id,
        ),
    )
    db.commit()
    return obtener_producto(producto_id, usuario_id)


def eliminar_producto(producto_id, usuario_id):
    db = get_db()
    db.execute(
        "DELETE FROM productos WHERE id = ? AND usuario_id = ?",
        (producto_id, usuario_id),
    )
    db.commit()


def obtener_usuario_por_username(username):
    db = get_db()
    usuario = db.execute(
        "SELECT id, username, password_hash FROM usuarios WHERE username = ?",
        (username,),
    ).fetchone()
    return row_to_dict(usuario)


def crear_usuario(username, password):
    db = get_db()
    cursor = db.execute(
        "INSERT INTO usuarios (username, password_hash) VALUES (?, ?)",
        (username, generate_password_hash(password)),
    )
    db.commit()
    return {
        "id": cursor.lastrowid,
        "username": username,
    }
