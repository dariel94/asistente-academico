import InputBar from './InputBar';
import MessageList from './MessageList';
import StatusIndicator from './StatusIndicator';
import type { ChatState } from '../types/chat';

interface Props {
  state: ChatState;
  onSend: (mensaje: string) => void;
}

export default function ChatWindow({ state, onSend }: Props) {
  const isBusy = state.estadoAgente !== 'idle';

  return (
    <div className="flex-1 flex flex-col min-w-0">
      <div className="px-6 py-4 border-b border-gray-200">
        <h1 className="text-lg font-semibold text-gray-800">Asistente Académico</h1>
      </div>

      <MessageList mensajes={state.mensajes} />

      {state.error && (
        <div className="mx-4 mb-2 bg-red-50 border border-red-200 text-red-700 px-4 py-2 rounded-lg text-sm">
          {state.error}
        </div>
      )}

      <StatusIndicator
        estado={state.estadoAgente}
        herramienta={state.herramientaActiva}
      />

      <InputBar disabled={isBusy} onSend={onSend} />
    </div>
  );
}
