import { useEffect, useRef } from 'react';
import MessageBubble from './MessageBubble';
import type { Mensaje } from '../types/chat';

interface Props {
  mensajes: Mensaje[];
}

export default function MessageList({ mensajes }: Props) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [mensajes]);

  if (mensajes.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-gray-400">
        <p>Enviá un mensaje para comenzar</p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-3">
      {mensajes.map((m) => (
        <MessageBubble key={m.id} mensaje={m} />
      ))}
      <div ref={endRef} />
    </div>
  );
}
