export type EstadoAgente =
  | 'idle'
  | 'procesando'
  | 'consultando_db'
  | 'buscando_docs'
  | 'generando';

export interface Mensaje {
  id: string;
  rol: 'user' | 'assistant';
  contenido: string;
  streaming?: boolean;
}

export interface ChatState {
  mensajes: Mensaje[];
  estadoAgente: EstadoAgente;
  herramientaActiva: string | null;
  error: string | null;
}

export type ChatAction =
  | { type: 'ENVIAR_MENSAJE'; contenido: string }
  | { type: 'SET_ESTADO'; estado: EstadoAgente; herramienta?: string }
  | { type: 'INICIAR_RESPUESTA' }
  | { type: 'AGREGAR_CHUNK'; chunk: string }
  | { type: 'FINALIZAR_RESPUESTA' }
  | { type: 'SET_ERROR'; mensaje: string };

export interface Perfil {
  id_alumno: number;
  nombre: string;
  apellido: string;
  legajo: string;
  carrera: string;
  estado: string;
}

export interface LoginResponse {
  token: string;
  perfil: Perfil;
}
