import type { ReactNode } from 'react';

interface Props {
  isAuthenticated: boolean;
  loginPage: ReactNode;
  children: ReactNode;
}

export default function AuthGuard({ isAuthenticated, loginPage, children }: Props) {
  return <>{isAuthenticated ? children : loginPage}</>;
}
