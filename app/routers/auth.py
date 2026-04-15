from fastapi import APIRouter, HTTPException, Request

from app.models.schemas import LoginRequest, LoginResponse, Perfil
from app.services.auth import create_token, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, request: Request):
    pool = request.app.state.db_pool
    row = await pool.fetchrow(
        """
        SELECT a.id_alumno, a.nombre, a.apellido, a.legajo, a.estado,
               a.password_hash, c.nombre AS carrera
        FROM alumnos a
        JOIN carreras c ON c.id_carrera = a.id_carrera
        WHERE a.legajo = $1
        """,
        body.legajo,
    )

    if not row or not verify_password(body.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    # Limpiar memoria de sesiones anteriores
    id_alumno = row["id_alumno"]
    await pool.execute("DELETE FROM conversaciones WHERE id_alumno = $1", id_alumno)
    await pool.execute("DELETE FROM resumenes WHERE id_alumno = $1", id_alumno)

    token = create_token(id_alumno)
    perfil = Perfil(
        id_alumno=row["id_alumno"],
        nombre=row["nombre"],
        apellido=row["apellido"],
        legajo=row["legajo"],
        carrera=row["carrera"],
        estado=row["estado"],
    )
    return LoginResponse(token=token, perfil=perfil)
