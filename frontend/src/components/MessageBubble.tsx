import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Mensaje } from '../types/chat';

interface Props {
  mensaje: Mensaje;
}

export default function MessageBubble({ mensaje }: Props) {
  const isUser = mensaje.rol === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[75%] rounded-2xl px-4 py-3 ${
          isUser
            ? 'bg-blue-600 text-white'
            : 'bg-gray-100 text-gray-800'
        }`}
      >
        {isUser ? (
          <p className="text-sm whitespace-pre-wrap">{mensaje.contenido}</p>
        ) : (
          <div className="text-sm max-w-none markdown-body">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{mensaje.contenido}</ReactMarkdown>
            {mensaje.streaming && (
              <span className="inline-block w-1.5 h-4 bg-gray-400 animate-pulse ml-0.5 align-text-bottom" />
            )}
          </div>
        )}
      </div>
    </div>
  );
}
