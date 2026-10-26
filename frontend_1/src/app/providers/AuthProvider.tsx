import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import apiClient from '../../services/api/client';

interface AuthContextType {
  token: string | null;
  isAuthenticated: boolean;
  isAuthModalOpen: boolean;
  openAuthModal: () => void;
  closeAuthModal: () => void;
  setAuthToken: (token: string) => void;
  logout: () => void;
  verifyToken: (token: string) => Promise<boolean>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setTokenState] = useState<string | null>(() => localStorage.getItem('api_auth_token'));
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);

  const setAuthToken = useCallback((newToken: string) => {
    localStorage.setItem('api_auth_token', newToken);
    setTokenState(newToken);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('api_auth_token');
    setTokenState(null);
  }, []);

  const verifyToken = async (testToken: string): Promise<boolean> => {
    try {
      await apiClient.get('/api/agents', {
        headers: {
          Authorization: `Bearer ${testToken}`,
          'X-API-Token': testToken,
        },
      });
      return true;
    } catch (err: any) {
      if (err.response?.status === 401) {
        return false;
      }
      // If backend is unreachable or returns other status, permit storing token
      return true;
    }
  };

  useEffect(() => {
    const handleAuthRequired = () => {
      setIsAuthModalOpen(true);
    };

    window.addEventListener('voxora:auth_required', handleAuthRequired);
    return () => window.removeEventListener('voxora:auth_required', handleAuthRequired);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        token,
        isAuthenticated: !!token,
        isAuthModalOpen,
        openAuthModal: () => setIsAuthModalOpen(true),
        closeAuthModal: () => setIsAuthModalOpen(false),
        setAuthToken,
        logout,
        verifyToken,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
};
