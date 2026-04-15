import { useCallback, useReducer } from 'react';
import { sendMessage } from '../services/api';
import type { ChatState, ChatAction, EstadoAgente, Perfil } from '../types/chat';

function mensajeBienvenida(perfil: Perfil): string {
  return `¡Hola ${perfil.nombre}! Soy **Selene**, tu asistente universitaria. Puedo ayudarte a consultar tu información académica o institucional. ¿En qué puedo ayudarte hoy?`;
}

function initialState(perfil: Perfil): ChatState {
  return {
    mensajes: [
      {
        id: crypto.randomUUID(),
        rol: 'assistant',
        contenido: mensajeBienvenida(perfil),
      },
    ],
    estadoAgente: 'idle',
    herramientaActiva: null,
    error: null,
  };
}

function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case 'ENVIAR_MENSAJE':
      return {
        ...state,
        mensajes: [
          ...state.mensajes,
          {
            id: crypto.randomUUID(),
            rol: 'user',
            contenido: action.contenido,
          },
        ],
        estadoAgente: 'procesando',
        error: null,
      };

    case 'SET_ESTADO':
      return {
        ...state,
        estadoAgente: action.estado,
        herramientaActiva: action.herramienta ?? null,
      };

    case 'INICIAR_RESPUESTA':
      return {
        ...state,
        mensajes: [
          ...state.mensajes,
          {
            id: crypto.randomUUID(),
            rol: 'assistant',
            contenido: '',
            streaming: true,
          },
        ],
      };

    case 'AGREGAR_CHUNK': {
      const mensajes = [...state.mensajes];
      const ultimo = mensajes[mensajes.length - 1];
      if (ultimo && ultimo.rol === 'assistant' && ultimo.streaming) {
        mensajes[mensajes.length - 1] = {
          ...ultimo,
          contenido: ultimo.contenido + action.chunk,
        };
      }
      return { ...state, mensajes };
    }

    case 'FINALIZAR_RESPUESTA': {
      const mensajes = state.mensajes.map((m) =>
        m.streaming ? { ...m, streaming: false } : m,
      );
      return {
        ...state,
        mensajes,
        estadoAgente: 'idle',
        herramientaActiva: null,
      };
    }

    case 'SET_ERROR':
      return {
        ...state,
        error: action.mensaje,
        estadoAgente: 'idle',
        herramientaActiva: null,
      };

    default:
      return state;
  }
}

export function useChat(token: string, perfil: Perfil, onSessionExpired: () => void) {
  const [state, dispatch] = useReducer(chatReducer, perfil, initialState);

  const enviarMensaje = useCallback(
    async (contenido: string) => {
      if (!contenido.trim() || state.estadoAgente !== 'idle') return;

      dispatch({ type: 'ENVIAR_MENSAJE', contenido });

      let respuestaIniciada = false;

      try {
        await sendMessage(token, contenido, (event) => {
          switch (event.tipo) {
            case 'estado':
              dispatch({
                type: 'SET_ESTADO',
                estado: event.valor as EstadoAgente,
                herramienta: event.herramienta,
              });
              break;

            case 'chunk':
              if (!respuestaIniciada) {
                dispatch({ type: 'INICIAR_RESPUESTA' });
                respuestaIniciada = true;
              }
              dispatch({ type: 'AGREGAR_CHUNK', chunk: event.contenido });
              break;

            case 'fin':
              dispatch({ type: 'FINALIZAR_RESPUESTA' });
              break;

            case 'error':
              dispatch({ type: 'SET_ERROR', mensaje: event.mensaje });
              break;
          }
        });

        // Si el stream se cerró sin evento 'fin' explícito
        if (state.estadoAgente !== 'idle') {
          dispatch({ type: 'FINALIZAR_RESPUESTA' });
        }
      } catch (err) {
        if (err instanceof Error && err.message === 'SESSION_EXPIRED') {
          onSessionExpired();
        } else {
          dispatch({
            type: 'SET_ERROR',
            mensaje: err instanceof Error ? err.message : 'Error desconocido',
          });
        }
      }
    },
    [token, state.estadoAgente, onSessionExpired],
  );

  return { state, enviarMensaje };
}
