import type { LoginResponse } from '../types/chat';

export async function login(legajo: string, password: string): Promise<LoginResponse> {
  const resp = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ legajo, password }),
  });

  if (resp.status === 401) {
    throw new Error('Credenciales inválidas');
  }
  if (!resp.ok) {
    throw new Error('Error del servidor');
  }

  return resp.json();
}

export async function sendMessage(
  token: string,
  mensaje: string,
  onEvent: (event: Record<string, string>) => void,
): Promise<void> {
  const resp = await fetch('/api/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ mensaje }),
  });

  if (resp.status === 401) {
    throw new Error('SESSION_EXPIRED');
  }
  if (resp.status === 429) {
    throw new Error('Demasiadas solicitudes. Esperá un momento antes de enviar otro mensaje.');
  }
  if (!resp.ok) {
    throw new Error('Error del servidor');
  }

  const reader = resp.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    // Mantener la última línea incompleta en el buffer
    buffer = lines.pop() || '';

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed.startsWith('data: ')) continue;

      const payload = trimmed.slice(6);
      try {
        const parsed = JSON.parse(payload);
        onEvent(parsed);
      } catch {
        // No es JSON → chunk de texto plano
        onEvent({ tipo: 'chunk', contenido: payload });
      }
    }
  }

  // Procesar lo que quede en el buffer
  if (buffer.trim().startsWith('data: ')) {
    const payload = buffer.trim().slice(6);
    try {
      const parsed = JSON.parse(payload);
      onEvent(parsed);
    } catch {
      onEvent({ tipo: 'chunk', contenido: payload });
    }
  }
}
