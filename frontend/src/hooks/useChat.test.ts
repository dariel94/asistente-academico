import { describe, expect, it } from 'vitest'

import { chatReducer, initialState, mensajeBienvenida } from './useChat'
import type { ChatState, Perfil } from '../types/chat'

const perfil: Perfil = {
  id_alumno: 1,
  nombre: 'María',
  apellido: 'González',
  legajo: 'SIS-1001',
  carrera: 'Ingeniería en Sistemas',
  estado: 'regular',
}

describe('mensajeBienvenida', () => {
  it('saluda al alumno por su nombre', () => {
    expect(mensajeBienvenida(perfil)).toContain('María')
    expect(mensajeBienvenida(perfil)).toContain('Selene')
  })
})

describe('initialState', () => {
  it('arranca con el mensaje de bienvenida y estado idle', () => {
    const state = initialState(perfil)
    expect(state.estadoAgente).toBe('idle')
    expect(state.error).toBeNull()
    expect(state.herramientaActiva).toBeNull()
    expect(state.mensajes).toHaveLength(1)
    expect(state.mensajes[0].rol).toBe('assistant')
    expect(state.mensajes[0].contenido).toContain(perfil.nombre)
  })
})

describe('chatReducer', () => {
  const base: ChatState = initialState(perfil)

  it('ENVIAR_MENSAJE agrega un mensaje del usuario y pasa a procesando', () => {
    const next = chatReducer(base, {
      type: 'ENVIAR_MENSAJE',
      contenido: '¿qué notas tengo?',
    })
    expect(next.mensajes.at(-1)).toMatchObject({
      rol: 'user',
      contenido: '¿qué notas tengo?',
    })
    expect(next.estadoAgente).toBe('procesando')
    expect(next.error).toBeNull()
  })

  it('SET_ESTADO actualiza estadoAgente y herramientaActiva', () => {
    const next = chatReducer(base, {
      type: 'SET_ESTADO',
      estado: 'consultando_db',
      herramienta: 'obtener_historia_academica',
    })
    expect(next.estadoAgente).toBe('consultando_db')
    expect(next.herramientaActiva).toBe('obtener_historia_academica')
  })

  it('SET_ESTADO sin herramienta resetea herramientaActiva a null', () => {
    const conTool: ChatState = {
      ...base,
      estadoAgente: 'consultando_db',
      herramientaActiva: 'foo',
    }
    const next = chatReducer(conTool, { type: 'SET_ESTADO', estado: 'generando' })
    expect(next.estadoAgente).toBe('generando')
    expect(next.herramientaActiva).toBeNull()
  })

  it('INICIAR_RESPUESTA agrega un mensaje en streaming del asistente', () => {
    const next = chatReducer(base, { type: 'INICIAR_RESPUESTA' })
    const ultimo = next.mensajes.at(-1)!
    expect(ultimo.rol).toBe('assistant')
    expect(ultimo.streaming).toBe(true)
    expect(ultimo.contenido).toBe('')
  })

  it('AGREGAR_CHUNK concatena al último mensaje en streaming', () => {
    let s = chatReducer(base, { type: 'INICIAR_RESPUESTA' })
    s = chatReducer(s, { type: 'AGREGAR_CHUNK', chunk: 'Hola ' })
    s = chatReducer(s, { type: 'AGREGAR_CHUNK', chunk: 'mundo' })
    expect(s.mensajes.at(-1)!.contenido).toBe('Hola mundo')
    expect(s.mensajes.at(-1)!.streaming).toBe(true)
  })

  it('AGREGAR_CHUNK no toca mensajes que no están en streaming', () => {
    const next = chatReducer(base, { type: 'AGREGAR_CHUNK', chunk: 'algo' })
    // El mensaje de bienvenida no es streaming → no se modifica
    expect(next.mensajes.at(-1)!.contenido).toBe(base.mensajes[0].contenido)
  })

  it('FINALIZAR_RESPUESTA cierra el streaming y vuelve a idle', () => {
    let s = chatReducer(base, { type: 'INICIAR_RESPUESTA' })
    s = chatReducer(s, { type: 'AGREGAR_CHUNK', chunk: 'respuesta' })
    s = chatReducer(s, { type: 'FINALIZAR_RESPUESTA' })
    expect(s.mensajes.at(-1)!.streaming).toBeFalsy()
    expect(s.estadoAgente).toBe('idle')
    expect(s.herramientaActiva).toBeNull()
  })

  it('SET_ERROR registra el mensaje y vuelve a idle', () => {
    const ocupado: ChatState = {
      ...base,
      estadoAgente: 'consultando_db',
      herramientaActiva: 'x',
    }
    const next = chatReducer(ocupado, { type: 'SET_ERROR', mensaje: 'Timeout' })
    expect(next.error).toBe('Timeout')
    expect(next.estadoAgente).toBe('idle')
    expect(next.herramientaActiva).toBeNull()
  })

  it('acción desconocida devuelve el mismo state (sin mutación)', () => {
    // @ts-expect-error — provocamos una acción inválida a propósito
    const next = chatReducer(base, { type: '__NO_EXISTE__' })
    expect(next).toBe(base)
  })
})
