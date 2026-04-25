import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import StatusIndicator from './StatusIndicator'

describe('StatusIndicator', () => {
  it('no renderiza nada cuando el estado es idle', () => {
    const { container } = render(<StatusIndicator estado="idle" herramienta={null} />)
    expect(container.firstChild).toBeNull()
  })

  it('muestra "Analizando tu consulta..." en estado procesando', () => {
    render(<StatusIndicator estado="procesando" herramienta={null} />)
    expect(screen.getByText('Analizando tu consulta...')).toBeInTheDocument()
  })

  it('muestra "Buscando en documentos institucionales" en estado buscando_docs', () => {
    render(<StatusIndicator estado="buscando_docs" herramienta={null} />)
    expect(
      screen.getByText('Buscando en documentos institucionales')
    ).toBeInTheDocument()
  })

  it('muestra "Redactando respuesta..." en estado generando', () => {
    render(<StatusIndicator estado="generando" herramienta={null} />)
    expect(screen.getByText('Redactando respuesta...')).toBeInTheDocument()
  })

  it('en consultando_db sin herramienta muestra etiqueta base', () => {
    render(<StatusIndicator estado="consultando_db" herramienta={null} />)
    expect(
      screen.getByText('Consultando base de datos académica')
    ).toBeInTheDocument()
  })

  it('en consultando_db con herramienta la incluye en la etiqueta', () => {
    render(
      <StatusIndicator
        estado="consultando_db"
        herramienta="obtener_historia_academica"
      />
    )
    expect(
      screen.getByText(
        'Consultando base de datos académica: obtener_historia_academica'
      )
    ).toBeInTheDocument()
  })
})
