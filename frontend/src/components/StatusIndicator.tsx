import type { EstadoAgente } from '../types/chat';

interface Props {
  estado: EstadoAgente;
  herramienta: string | null;
}

function getLabel(estado: EstadoAgente, herramienta: string | null): string | null {
  switch (estado) {
    case 'idle':
      return null;
    case 'procesando':
      return 'Analizando tu consulta...';
    case 'consultando_db':
      return `Consultando base de datos académica${herramienta ? `: ${herramienta}` : ''}`;
    case 'buscando_docs':
      return 'Buscando en documentos institucionales';
    case 'generando':
      return 'Redactando respuesta...';
  }
}

export default function StatusIndicator({ estado, herramienta }: Props) {
  const label = getLabel(estado, herramienta);
  if (!label) return null;

  return (
    <div className="flex items-center gap-2 px-4 py-2 text-sm text-blue-600">
      <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
      {label}
    </div>
  );
}
