import { useCallback, useState } from 'react';
import AuthGuard from './components/AuthGuard';
import ChatPage from './components/ChatPage';
import LoginPage from './components/LoginPage';
import type { Perfil } from './types/chat';

export default function App() {
  const [token, setToken] = useState<string | null>(null);
  const [perfil, setPerfil] = useState<Perfil | null>(null);
  const [sessionMessage, setSessionMessage] = useState<string | null>(null);

  const handleLogin = useCallback((newToken: string, newPerfil: Perfil) => {
    setToken(newToken);
    setPerfil(newPerfil);
    setSessionMessage(null);
  }, []);

  const handleLogout = useCallback(() => {
    setToken(null);
    setPerfil(null);
    setSessionMessage(null);
  }, []);

  const handleSessionExpired = useCallback(() => {
    setToken(null);
    setPerfil(null);
    setSessionMessage('Tu sesión ha expirado. Por favor, iniciá sesión nuevamente.');
  }, []);

  return (
    <AuthGuard
      isAuthenticated={!!token && !!perfil}
      loginPage={
        <>
          {sessionMessage && (
            <div className="fixed top-4 left-1/2 -translate-x-1/2 bg-amber-50 border border-amber-300 text-amber-800 px-6 py-3 rounded-lg shadow-md text-sm z-50">
              {sessionMessage}
            </div>
          )}
          <LoginPage onLogin={handleLogin} />
        </>
      }
    >
      <ChatPage
        token={token!}
        perfil={perfil!}
        onLogout={handleLogout}
        onSessionExpired={handleSessionExpired}
      />
    </AuthGuard>
  );
}
