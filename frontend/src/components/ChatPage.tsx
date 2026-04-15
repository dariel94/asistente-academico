import ChatWindow from './ChatWindow';
import Sidebar from './Sidebar';
import { useChat } from '../hooks/useChat';
import type { Perfil } from '../types/chat';

interface Props {
  token: string;
  perfil: Perfil;
  onLogout: () => void;
  onSessionExpired: () => void;
}

export default function ChatPage({ token, perfil, onLogout, onSessionExpired }: Props) {
  const { state, enviarMensaje } = useChat(token, perfil, onSessionExpired);

  return (
    <div className="h-screen flex">
      <Sidebar perfil={perfil} onLogout={onLogout} />
      <ChatWindow state={state} onSend={enviarMensaje} />
    </div>
  );
}
