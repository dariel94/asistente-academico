from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request

from app import config
from app.models.schemas import Perfil, SessionContext


def create_token(id_alumno: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(id_alumno),
        "iat": now,
        "exp": now + timedelta(hours=config.JWT_EXPIRATION_HOURS),
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)


def verify_token(token: str) -> int:
    try:
        payload = jwt.decode(
            token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM]
        )
        return int(payload["sub"])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Token inválido o expirado")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


async def get_current_user(request: Request) -> SessionContext:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token inválido o expirado")

    token = auth_header.split(" ", 1)[1]
    id_alumno = verify_token(token)

    pool = request.app.state.db_pool
    row = await pool.fetchrow(
        """
        SELECT a.id_alumno, a.nombre, a.apellido, a.legajo, a.estado,
               c.nombre AS carrera
        FROM alumnos a
        JOIN carreras c ON c.id_carrera = a.id_carrera
        WHERE a.id_alumno = $1
        """,
        id_alumno,
    )

    if not row:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")

    perfil = Perfil(
        id_alumno=row["id_alumno"],
        nombre=row["nombre"],
        apellido=row["apellido"],
        legajo=row["legajo"],
        carrera=row["carrera"],
        estado=row["estado"],
    )
    return SessionContext(id_alumno=id_alumno, perfil=perfil)
