import math
from functools import wraps

from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from extensions import init_app
from models.tablaDB import (
    actualizar_producto,
    crear_producto,
    eliminar_producto,
    init_db,
    obtener_usuario_por_username,
    obtener_producto,
    obtener_productos,
)


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        DATABASE="database.db",
        SECRET_KEY="mysecretkey",
        JSON_SORT_KEYS=False,
    )

    if test_config is not None:
        app.config.update(test_config)

    init_app(app)

    with app.app_context():
        init_db()

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "")
            password = request.form.get("password", "")

            if validar_credenciales(username, password):
                usuario = obtener_usuario_por_username(username)
                session.clear()
                session["usuario_id"] = usuario["id"]
                session["username"] = usuario["username"]
                flash("Sesión iniciada correctamente")
                return redirect(url_for("Index"))

            flash("Usuario o contraseña incorrectos")

        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        session.clear()
        flash("Sesión cerrada correctamente")
        return redirect(url_for("login"))

    @app.route("/")
    @login_required
    def Index():
        productos = obtener_productos()
        return render_template("index.html", productos=productos)

    @app.route("/add_product", methods=["POST"])
    @login_required
    def add_product():
        data = {
            "nombre": request.form.get("nombre", ""),
            "descripcion": request.form.get("descripcion", ""),
            "precio": request.form.get("precio", ""),
            "stock": request.form.get("stock", ""),
        }
        error = validar_producto(data)

        if error:
            flash(error)
            return redirect(url_for("Index"))

        crear_producto(data)
        flash("Producto agregado correctamente")
        return redirect(url_for("Index"))

    @app.route("/edit/<int:id>", methods=["GET", "POST"])
    @login_required
    def edit_product(id):
        producto = obtener_producto(id)

        if producto is None:
            flash("Producto no encontrado")
            return redirect(url_for("Index"))

        if request.method == "POST":
            data = {
                "nombre": request.form.get("nombre", ""),
                "descripcion": request.form.get("descripcion", ""),
                "precio": request.form.get("precio", ""),
                "stock": request.form.get("stock", ""),
            }
            error = validar_producto(data)

            if error:
                flash(error)
                return render_template("edit.html", producto=producto)

            actualizar_producto(id, data)
            flash("Producto actualizado correctamente")
            return redirect(url_for("Index"))

        return render_template("edit.html", producto=producto)

    @app.route("/delete/<int:id>")
    @login_required
    def delete_product(id):
        if obtener_producto(id) is None:
            flash("Producto no encontrado")
            return redirect(url_for("Index"))

        eliminar_producto(id)
        flash("Producto eliminado correctamente")
        return redirect(url_for("Index"))

    @app.get("/productos")
    @app.get("/api/productos")
    @api_auth_required
    def api_get_productos():
        return jsonify(obtener_productos()), 200

    @app.get("/productos/<int:id>")
    @app.get("/api/productos/<int:id>")
    @api_auth_required
    def api_get_producto(id):
        producto = obtener_producto(id)

        if producto is None:
            return jsonify({"error": "Producto no encontrado"}), 404

        return jsonify(producto), 200

    @app.post("/productos")
    @app.post("/api/productos")
    @api_auth_required
    def api_create_producto():
        data = request.get_json(silent=True)
        error = validar_producto(data)

        if error:
            return jsonify({"error": error}), 400

        producto = crear_producto(data)
        return jsonify(producto), 201

    @app.put("/productos/<int:id>")
    @app.put("/api/productos/<int:id>")
    @api_auth_required
    def api_update_producto(id):
        if obtener_producto(id) is None:
            return jsonify({"error": "Producto no encontrado"}), 404

        data = request.get_json(silent=True)
        error = validar_producto(data)

        if error:
            return jsonify({"error": error}), 400

        producto = actualizar_producto(id, data)
        return jsonify(producto), 200

    @app.delete("/productos/<int:id>")
    @app.delete("/api/productos/<int:id>")
    @api_auth_required
    def api_delete_producto(id):
        if obtener_producto(id) is None:
            return jsonify({"error": "Producto no encontrado"}), 404

        eliminar_producto(id)
        return "", 204

    @app.errorhandler(404)
    def route_not_found(error):
        if es_ruta_api():
            return jsonify({"error": "Ruta no encontrada"}), 404
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def server_error(error):
        if es_ruta_api():
            return jsonify({"error": "Error interno del servidor"}), 500
        return "Error interno del servidor", 500

    return app


def validar_producto(data):
    if not isinstance(data, dict):
        return "La solicitud debe enviar un objeto JSON válido"

    campos_requeridos = ["nombre", "descripcion", "precio", "stock"]
    campos_faltantes = [campo for campo in campos_requeridos if campo not in data]

    if campos_faltantes:
        return f"Faltan campos requeridos: {', '.join(campos_faltantes)}"

    if not isinstance(data["nombre"], str) or not data["nombre"].strip():
        return "El nombre no puede estar vacío"

    if not isinstance(data["descripcion"], str) or not data["descripcion"].strip():
        return "La descripción no puede estar vacía"

    if isinstance(data["precio"], bool):
        return "El precio debe ser numérico"

    try:
        precio = float(data["precio"])
    except (TypeError, ValueError):
        return "El precio debe ser numérico"

    if not math.isfinite(precio):
        return "El precio debe ser un número válido"

    if precio < 0:
        return "El precio no puede ser negativo"

    if isinstance(data["stock"], bool):
        return "Las existencias deben ser un número entero"

    if isinstance(data["stock"], float) and not data["stock"].is_integer():
        return "Las existencias deben ser un número entero"

    try:
        stock = int(data["stock"])
    except (TypeError, ValueError):
        return "Las existencias deben ser un número entero"

    if stock < 0:
        return "Las existencias no pueden ser negativas"

    data["nombre"] = str(data["nombre"]).strip()
    data["descripcion"] = str(data["descripcion"]).strip()
    data["precio"] = precio
    data["stock"] = stock
    return None


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "usuario_id" not in session:
            flash("Inicia sesión para continuar")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped_view


def api_auth_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "usuario_id" in session:
            return view(*args, **kwargs)

        auth = request.authorization

        if auth and validar_credenciales(auth.username, auth.password):
            return view(*args, **kwargs)

        return (
            jsonify({"error": "Autenticación requerida"}),
            401,
            {"WWW-Authenticate": 'Basic realm="Inventario API"'},
        )

    return wrapped_view


def validar_credenciales(username, password):
    if not username or password is None:
        return False

    usuario = obtener_usuario_por_username(username)

    if usuario is None:
        return False

    return check_password_hash(usuario["password_hash"], password)


def es_ruta_api():
    return request.path.startswith("/api/") or request.path.startswith("/productos")


app = create_app()


if __name__ == "__main__":
    app.run(port=3000, debug=True)
