from __future__ import annotations

from datetime import datetime
from pathlib import Path
import secrets
from flask import Flask, jsonify, request, session, render_template

from .db import init_db
from .models import CalculationInput
from .repositories import (
    ConceptRepository,
    InterestRateRepository,
    ParameterRepository,
    UnitValueRepository,
    UserRepository,
)
from .services import LiquidationError, LiquidationService

BASE_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIR = BASE_DIR / "frontend"

app = Flask(
    __name__,
    template_folder=str(FRONTEND_DIR / "templates"),
    static_folder=str(FRONTEND_DIR / "static"),
    static_url_path="/static",
)
app.secret_key = secrets.token_hex(24)

# Asegurar que las tablas estén inicializadas
init_db()


def create_app() -> Flask:
    return app


# Middleware de autenticación simple
def get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    
    # Recargar datos del usuario para tener estado fresco
    users = {u["id"]: u for u in UserRepository.list_all()}
    return users.get(user_id)


# Decorador para requerir inicio de sesión
def require_auth(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({"success": False, "message": "No autorizado. Inicie sesión."}), 401
        return f(*args, **kwargs)
    return decorated


# Decorador para requerir rol admin
def require_admin(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user or user["rol"] != "admin":
            return jsonify({"success": False, "message": "Acceso denegado. Se requieren permisos de administrador."}), 403
        return f(*args, **kwargs)
    return decorated


# --- RUTAS FRONTEND ---

@app.route("/")
def index():
    return render_template("index.html")


# --- RUTAS DE LA API DE AUTENTICACIÓN ---

@app.route("/api/auth/login", methods=["POST"])
def api_login():
    data = request.json or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    
    if not username or not password:
        return jsonify({"success": False, "message": "Usuario y contraseña son requeridos."}), 400
        
    user = UserRepository.authenticate(username, password)
    if not user:
        return jsonify({"success": False, "message": "Usuario o contraseña inválidos."}), 401
        
    UserRepository.mark_login(int(user["id"]))
    
    session["user_id"] = user["id"]
    session.permanent = True
    
    # Quitar password_hash del dict retornado por seguridad
    user_data = dict(user)
    user_data.pop("password_hash", None)
    
    return jsonify({"success": True, "user": user_data})


@app.route("/api/auth/logout", methods=["POST"])
def api_logout():
    session.pop("user_id", None)
    return jsonify({"success": True, "message": "Sesión cerrada correctamente."})


@app.route("/api/auth/me", methods=["GET"])
def api_me():
    user = get_current_user()
    if not user:
        return jsonify({"logged_in": False}), 401
        
    user_data = dict(user)
    user_data.pop("password_hash", None)
    return jsonify({"logged_in": True, "user": user_data})


@app.route("/api/auth/change-password", methods=["POST"])
@require_auth
def api_change_password():
    user = get_current_user()
    data = request.json or {}
    old_password = data.get("old_password", "").strip()
    new_password = data.get("new_password", "").strip()
    confirm = data.get("confirm_password", "").strip()
    
    if not old_password or not new_password or not confirm:
        return jsonify({"success": False, "message": "Complete todos los campos de contraseña."}), 400
    if len(new_password) < 6:
        return jsonify({"success": False, "message": "La nueva contraseña debe tener al menos 6 caracteres."}), 400
    if new_password != confirm:
        return jsonify({"success": False, "message": "La confirmación de la contraseña no coincide."}), 400
        
    ok, msg = UserRepository.change_password(int(user["id"]), old_password, new_password)
    if not ok:
        return jsonify({"success": False, "message": msg}), 400
        
    return jsonify({"success": True, "message": "Contraseña actualizada correctamente."})


# --- ENDPOINTS DE CONCEPTOS Y LIQUIDACIÓN ---

@app.route("/api/concepts", methods=["GET"])
@require_auth
def api_concepts():
    concepts = ConceptRepository.list_active()
    return jsonify(concepts)


@app.route("/api/calculate", methods=["POST"])
@require_auth
def api_calculate():
    data = request.json or {}
    concept_id = data.get("concept_id")
    fecha_multa_str = data.get("fecha_multa", "").strip()
    fecha_liq_str = data.get("fecha_liquidacion", "").strip()
    cantidad_unidades = data.get("cantidad_unidades")
    valor_manual = data.get("valor_manual")
    tiene_programa = bool(data.get("tiene_programa_comunitario", False))
    
    if not concept_id or not fecha_multa_str or not fecha_liq_str:
        return jsonify({"success": False, "message": "Faltan datos requeridos para liquidar."}), 400
        
    try:
        # Convertir fechas
        fecha_multa = datetime.strptime(fecha_multa_str, "%d-%m-%Y").date()
        fecha_liq = datetime.strptime(fecha_liq_str, "%d-%m-%Y").date()
        
        # Validar y parsear cantidad de unidades y valor manual
        qty = float(cantidad_unidades) if cantidad_unidades is not None and str(cantidad_unidades).strip() != "" else None
        val_man = float(valor_manual) if valor_manual is not None and str(valor_manual).strip() != "" else None
        
        calc_input = CalculationInput(
            concept_id=int(concept_id),
            fecha_multa=fecha_multa,
            fecha_liquidacion=fecha_liq,
            cantidad_unidades=qty,
            valor_manual=val_man,
            tiene_programa_comunitario=tiene_programa
        )
        
        result = LiquidationService.calcular(calc_input)
        
        # Serializar resultado a JSON
        return jsonify({
            "success": True,
            "result": {
                "concept_name": result.concept_name,
                "unidad_aplicada": result.unidad_aplicada,
                "valor_unidad": result.valor_unidad,
                "cantidad_unidades": result.cantidad_unidades,
                "valor_base": result.valor_base,
                "dias_transcurridos": result.dias_transcurridos,
                "dias_mora": result.dias_mora,
                "aplica_descuento": result.aplica_descuento,
                "porcentaje_descuento": result.porcentaje_descuento,
                "valor_descuento": result.valor_descuento,
                "metodo_interes": result.metodo_interes,
                "tasa_interes_anual": result.tasa_interes_anual,
                "valor_interes": result.valor_interes,
                "total_pagar": result.total_pagar,
                "regla_aplicada": result.regla_aplicada
            }
        })
        
    except ValueError as exc:
        return jsonify({"success": False, "message": f"Dato numérico o de fecha inválido: {exc}"}), 400
    except LiquidationError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400
    except Exception as exc:
        return jsonify({"success": False, "message": f"Error inesperado al calcular: {exc}"}), 500


# --- ENDPOINTS DE ADMINISTRACIÓN DE PARÁMETROS GENERALES ---

@app.route("/api/parameters", methods=["GET", "POST"])
@require_auth
def api_parameters():
    if request.method == "GET":
        params = ParameterRepository.get_active()
        return jsonify(params)
    else:
        # POST requiere admin
        user = get_current_user()
        if user["rol"] != "admin":
            return jsonify({"success": False, "message": "No autorizado para guardar parámetros."}), 403
            
        data = request.json or {}
        try:
            dias_gracia = int(data.get("dias_gracia_descuento", 8))
            porcentaje_desc = float(data.get("porcentaje_descuento", 50.0))
            tasa_nt = float(data.get("tasa_no_tributaria", 12.0))
            permitir_editar_fecha = bool(data.get("permitir_editar_fecha_liquidacion", False))
            
            ParameterRepository.update(
                dias_gracia=dias_gracia,
                porcentaje_descuento=porcentaje_desc,
                tasa_no_tributaria=tasa_nt,
                permitir_editar_fecha_liquidacion=permitir_editar_fecha
            )
            return jsonify({"success": True, "message": "Parámetros guardados y aplicados correctamente."})
        except ValueError:
            return jsonify({"success": False, "message": "Los parámetros deben ser valores numéricos correctos."}), 400


# --- ENDPOINTS DE VALORES DE UNIDAD ---

@app.route("/api/units", methods=["GET", "POST"])
@require_auth
def api_units():
    if request.method == "GET":
        units = UnitValueRepository.list_all()
        return jsonify(units)
    else:
        # POST requiere admin
        user = get_current_user()
        if user["rol"] != "admin":
            return jsonify({"success": False, "message": "No autorizado para actualizar valores de unidad."}), 403
            
        data = request.json or {}
        try:
            anio = int(data.get("anio"))
            tipo_unidad = data.get("tipo_unidad").strip().upper()
            valor = float(data.get("valor"))
            
            if tipo_unidad not in ("PESOS", "SMMLV", "SMDLV", "UVB"):
                return jsonify({"success": False, "message": "Tipo de unidad inválido."}), 400
                
            UnitValueRepository.upsert(anio, tipo_unidad, valor)
            return jsonify({"success": True, "message": "Valor de unidad actualizado con éxito."})
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": "Verifique el año y el valor ingresado."}), 400


# --- ENDPOINTS DE TASAS DE INTERÉS HISTÓRICAS ---

@app.route("/api/rates", methods=["GET", "POST"])
@require_auth
def api_rates():
    if request.method == "GET":
        rates = InterestRateRepository.list_all()
        return jsonify(rates)
    else:
        # POST requiere admin
        user = get_current_user()
        if user["rol"] != "admin":
            return jsonify({"success": False, "message": "No autorizado para actualizar tasas de interés."}), 403
            
        data = request.json or {}
        try:
            metodo = data.get("metodo_interes").strip().upper()
            anio = int(data.get("anio"))
            mes = int(data.get("mes"))
            tasa = float(data.get("tasa_anual"))
            
            methods = [
                'TABLA_HISTORICA_GENERAL',
                'TABLA_HISTORICA_EVENTOS',
                'TABLA_HISTORICA_VISUAL',
                'TABLA_HISTORICA_URBANISMO',
                'TABLA_HISTORICA_OTRAS',
            ]
            if metodo not in methods:
                return jsonify({"success": False, "message": "Método de interés no válido."}), 400
            if not (1 <= mes <= 12):
                return jsonify({"success": False, "message": "El mes debe estar entre 1 y 12."}), 400
                
            InterestRateRepository.upsert(metodo, anio, mes, tasa)
            return jsonify({"success": True, "message": "Tasa de interés histórica guardada con éxito."})
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": "Verifique los valores de año, mes y tasa."}), 400


# --- ENDPOINTS DE VALORES DE UNIDAD ---

@app.route("/api/units/<int:unit_id>", methods=["PUT", "DELETE"])
@require_admin
def api_unit_detail(unit_id: int):
    if request.method == "PUT":
        data = request.json or {}
        try:
            anio = int(data.get("anio"))
            tipo_unidad = data.get("tipo_unidad").strip().upper()
            valor = float(data.get("valor"))
            
            if tipo_unidad not in ("PESOS", "SMMLV", "SMDLV", "UVB"):
                return jsonify({"success": False, "message": "Tipo de unidad inválido."}), 400
            
            UnitValueRepository.upsert(anio, tipo_unidad, valor)
            return jsonify({"success": True, "message": "Valor de unidad actualizado con éxito."})
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": "Verifique el año y el valor ingresado."}), 400
    else:
        # DELETE - soft delete
        UnitValueRepository.soft_delete(unit_id)
        return jsonify({"success": True, "message": "Valor de unidad eliminado correctamente."})


# --- ENDPOINTS DE TASAS DE INTERÉS HISTÓRICAS ---

@app.route("/api/rates/<int:rate_id>", methods=["PUT", "DELETE"])
@require_admin
def api_rate_detail(rate_id: int):
    if request.method == "PUT":
        data = request.json or {}
        try:
            metodo = data.get("metodo_interes").strip().upper()
            anio = int(data.get("anio"))
            mes = int(data.get("mes"))
            tasa = float(data.get("tasa_anual"))
            
            methods = [
                'TABLA_HISTORICA_GENERAL',
                'TABLA_HISTORICA_EVENTOS',
                'TABLA_HISTORICA_VISUAL',
                'TABLA_HISTORICA_URBANISMO',
                'TABLA_HISTORICA_OTRAS',
            ]
            if metodo not in methods:
                return jsonify({"success": False, "message": "Método de interés no válido."}), 400
            if not (1 <= mes <= 12):
                return jsonify({"success": False, "message": "El mes debe estar entre 1 y 12."}), 400
            
            InterestRateRepository.upsert(metodo, anio, mes, tasa)
            return jsonify({"success": True, "message": "Tasa de interés histórica actualizada con éxito."})
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": "Verifique los valores de año, mes y tasa."}), 400
    else:
        # DELETE - soft delete
        InterestRateRepository.soft_delete(rate_id)
        return jsonify({"success": True, "message": "Tasa de interés eliminada correctamente."})


# --- ENDPOINTS DE GESTIÓN DE USUARIOS (SOLO ADMIN) ---

@app.route("/api/users/<int:user_id>", methods=["PUT", "DELETE"])
@require_admin
def api_user_detail(user_id: int):
    if request.method == "PUT":
        data = request.json or {}
        nombre = data.get("nombre", "").strip()
        rol = data.get("rol", "").strip().lower()
        activo = bool(data.get("activo", True))
        
        if rol not in ("admin", "liquidador"):
            return jsonify({"success": False, "message": "El rol debe ser admin o liquidador."}), 400
        
        UserRepository.update_user(user_id, nombre=nombre, rol=rol, activo=activo)
        return jsonify({"success": True, "message": "Usuario actualizado correctamente."})
    else:
        # DELETE - soft delete
        UserRepository.soft_delete(user_id)
        return jsonify({"success": True, "message": "Usuario eliminado correctamente."})

@app.route("/api/users", methods=["GET", "POST"])
@require_admin
def api_users():
    if request.method == "GET":
        users = UserRepository.list_all()
        # Quitar password_hash por seguridad
        users_data = []
        for u in users:
            ud = dict(u)
            ud.pop("password_hash", None)
            users_data.append(ud)
        return jsonify(users_data)
    else:
        data = request.json or {}
        username = data.get("username", "").strip()
        nombre = data.get("nombre", "").strip()
        password = data.get("password", "").strip()
        rol = data.get("rol", "liquidador").strip()
        activo = bool(data.get("activo", True))
        force_change = bool(data.get("debe_cambiar_clave", True))
        
        if not username or not password:
            return jsonify({"success": False, "message": "Nombre de usuario y clave provisional son obligatorios."}), 400
        if len(password) < 6:
            return jsonify({"success": False, "message": "La contraseña provisional debe tener al menos 6 caracteres."}), 400
        if rol not in ("admin", "liquidador"):
            return jsonify({"success": False, "message": "El rol debe ser admin o liquidador."}), 400
            
        try:
            UserRepository.create_user(
                username=username,
                password=password,
                rol=rol,
                nombre=nombre,
                activo=activo,
                debe_cambiar_clave=force_change
            )
            return jsonify({"success": True, "message": f"Usuario '{username}' creado correctamente."})
        except Exception as exc:
            return jsonify({"success": False, "message": f"No se pudo crear el usuario: {exc}"}), 400


@app.route("/api/users/toggle", methods=["POST"])
@require_admin
def api_users_toggle():
    data = request.json or {}
    user_id = data.get("id")
    activo = bool(data.get("activo", True))
    
    if not user_id:
        return jsonify({"success": False, "message": "ID de usuario requerido."}), 400
        
    UserRepository.set_active(int(user_id), activo)
    return jsonify({"success": True, "message": "Estado de activación actualizado."})


@app.route("/api/users/role", methods=["POST"])
@require_admin
def api_users_role():
    data = request.json or {}
    user_id = data.get("id")
    rol = data.get("rol", "").strip().lower()
    
    if not user_id or rol not in ("admin", "liquidador"):
        return jsonify({"success": False, "message": "Verifique ID de usuario y rol (admin/liquidador)."}), 400
        
    UserRepository.update_role(int(user_id), rol)
    return jsonify({"success": True, "message": "Rol del usuario actualizado correctamente."})


@app.route("/api/users/reset-password", methods=["POST"])
@require_admin
def api_users_reset_password():
    data = request.json or {}
    user_id = data.get("id")
    provisional = data.get("provisional_password", "").strip()
    
    if not user_id or not provisional:
        return jsonify({"success": False, "message": "ID y contraseña provisional requeridos."}), 400
    if len(provisional) < 6:
        return jsonify({"success": False, "message": "La contraseña provisional debe tener al menos 6 caracteres."}), 400
        
    UserRepository.reset_password(int(user_id), provisional)
    return jsonify({"success": True, "message": "Contraseña reseteada provisionalmente con éxito."})


# --- EJECUCIÓN DEL SERVIDOR ---

if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000, debug=True)
