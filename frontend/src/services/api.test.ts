import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { login, sendMessage } from './api'

function makeStreamResponse(chunks: string[]): Response {
  const encoder = new TextEncoder()
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const c of chunks) {
        controller.enqueue(encoder.encode(c))
      }
      controller.close()
    },
  })
  return new Response(stream, {
    status: 200,
    headers: { 'Content-Type': 'text/event-stream' },
  })
}

describe('login', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('devuelve la respuesta JSON ante un 2xx', async () => {
    const data = { token: 'abc', perfil: { id_alumno: 1, nombre: 'M' } }
    ;(fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      new Response(JSON.stringify(data), { status: 200 })
    )
    const res = await login('SIS-1001', 'password')
    expect(res).toMatchObject(data)
  })

  it('lanza "Credenciales inválidas" ante un 401', async () => {
    ;(fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      new Response('', { status: 401 })
    )
    await expect(login('x', 'y')).rejects.toThrow('Credenciales inválidas')
  })

  it('lanza "Error del servidor" ante otros errores', async () => {
    ;(fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      new Response('', { status: 500 })
    )
    await expect(login('x', 'y')).rejects.toThrow('Error del servidor')
  })
})

describe('sendMessage — manejo de status', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('lanza SESSION_EXPIRED ante 401', async () => {
    ;(fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      new Response('', { status: 401 })
    )
    await expect(sendMessage('tk', 'hola', () => {})).rejects.toThrow(
      'SESSION_EXPIRED'
    )
  })

  it('lanza mensaje específico ante 429 (rate limit)', async () => {
    ;(fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      new Response('', { status: 429 })
    )
    await expect(sendMessage('tk', 'hola', () => {})).rejects.toThrow(
      /Demasiadas solicitudes/
    )
  })

  it('lanza "Error del servidor" ante 500', async () => {
    ;(fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      new Response('', { status: 500 })
    )
    await expect(sendMessage('tk', 'hola', () => {})).rejects.toThrow(
      'Error del servidor'
    )
  })
})

describe('sendMessage — parseo SSE', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('parsea eventos data: con JSON válido y los pasa al callback', async () => {
    const body = [
      'data: {"tipo":"estado","valor":"procesando"}\n\n',
      'data: {"tipo":"chunk","contenido":"Hola "}\n\n',
      'data: {"tipo":"chunk","contenido":"mundo"}\n\n',
      'data: {"tipo":"fin"}\n\n',
    ]
    ;(fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      makeStreamResponse(body)
    )

    const events: Record<string, string>[] = []
    await sendMessage('tk', 'hola', (e) => events.push(e))

    expect(events).toEqual([
      { tipo: 'estado', valor: 'procesando' },
      { tipo: 'chunk', contenido: 'Hola ' },
      { tipo: 'chunk', contenido: 'mundo' },
      { tipo: 'fin' },
    ])
  })

  it('trata como chunk de texto plano lo que no parsea como JSON', async () => {
    ;(fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      makeStreamResponse(['data: texto-no-json\n\n'])
    )

    const events: Record<string, string>[] = []
    await sendMessage('tk', 'hola', (e) => events.push(e))
    expect(events).toEqual([{ tipo: 'chunk', contenido: 'texto-no-json' }])
  })

  it('arma eventos partidos en múltiples reads del stream', async () => {
    // La línea SSE llega cortada en dos chunks de red
    ;(fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      makeStreamResponse([
        'data: {"tipo":"chu',
        'nk","contenido":"hola"}\n\n',
      ])
    )

    const events: Record<string, string>[] = []
    await sendMessage('tk', 'hola', (e) => events.push(e))
    expect(events).toEqual([{ tipo: 'chunk', contenido: 'hola' }])
  })

  it('procesa el último evento aunque no haya \\n\\n final', async () => {
    ;(fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      makeStreamResponse(['data: {"tipo":"fin"}'])
    )

    const events: Record<string, string>[] = []
    await sendMessage('tk', 'hola', (e) => events.push(e))
    expect(events).toEqual([{ tipo: 'fin' }])
  })

  it('ignora líneas que no empiezan con "data: "', async () => {
    ;(fetch as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce(
      makeStreamResponse([
        ': comentario SSE\n',
        'event: estado\n',
        'data: {"tipo":"chunk","contenido":"x"}\n\n',
      ])
    )

    const events: Record<string, string>[] = []
    await sendMessage('tk', 'hola', (e) => events.push(e))
    expect(events).toEqual([{ tipo: 'chunk', contenido: 'x' }])
  })
})
