from pydantic import BaseModel


class LoginRequest(BaseModel):
    legajo: str
    password: str


class Perfil(BaseModel):
    id_alumno: int
    nombre: str
    apellido: str
    legajo: str
    carrera: str
    estado: str


class LoginResponse(BaseModel):
    token: str
    perfil: Perfil


class ChatRequest(BaseModel):
    mensaje: str


class SessionContext(BaseModel):
    id_alumno: int
    perfil: Perfil
