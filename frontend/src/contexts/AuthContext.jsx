import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';

const AuthContext = createContext(null);

const TOKEN_KEY = 'auth_tokens';

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  const getStoredTokens = () => {
    try {
      const tokens = localStorage.getItem(TOKEN_KEY);
      return tokens ? JSON.parse(tokens) : null;
    } catch {
      return null;
    }
  };

  const storeTokens = (tokens) => {
    localStorage.setItem(TOKEN_KEY, JSON.stringify(tokens));
  };

  const clearTokens = () => {
    localStorage.removeItem(TOKEN_KEY);
  };

  const setAuthHeader = (token) => {
    if (token) {
      api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    } else {
      delete api.defaults.headers.common['Authorization'];
    }
  };

  const fetchUser = useCallback(async () => {
    try {
      const response = await api.get('/auth/me');
      setUser(response.data);
      return response.data;
    } catch (error) {
      setUser(null);
      clearTokens();
      setAuthHeader(null);
      return null;
    }
  }, []);

  const refreshToken = useCallback(async () => {
    const tokens = getStoredTokens();
    if (!tokens?.refresh_token) return false;

    try {
      const response = await api.post('/auth/refresh', {
        refresh_token: tokens.refresh_token
      });
      storeTokens(response.data);
      setAuthHeader(response.data.access_token);
      return true;
    } catch (error) {
      clearTokens();
      setAuthHeader(null);
      setUser(null);
      return false;
    }
  }, []);

  useEffect(() => {
    const initAuth = async () => {
      const tokens = getStoredTokens();
      if (tokens?.access_token) {
        setAuthHeader(tokens.access_token);
        try {
          await fetchUser();
        } catch (error) {
          const refreshed = await refreshToken();
          if (refreshed) await fetchUser();
        }
      }
      setLoading(false);
    };
    initAuth();
  }, [fetchUser, refreshToken]);

  const register = async (email, password, fullName) => {
    const response = await api.post('/auth/register', {
      email, password, full_name: fullName
    });
    return response.data;
  };

  const login = async (email, password) => {
    const response = await api.post('/auth/login', { email, password });
    storeTokens(response.data);
    setAuthHeader(response.data.access_token);
    await fetchUser();
    return response.data;
  };

  const logout = async () => {
    const tokens = getStoredTokens();
    if (tokens?.refresh_token) {
      try {
        await api.post('/auth/logout', { refresh_token: tokens.refresh_token });
      } catch (error) {}
    }
    clearTokens();
    setAuthHeader(null);
    setUser(null);
    navigate('/login');
  };

  const oauthLogin = async (provider, code) => {
    const response = await api.post(`/auth/oauth/${provider}/callback`, null, {
      params: { code }
    });
    storeTokens(response.data);
    setAuthHeader(response.data.access_token);
    await fetchUser();
    return response.data;
  };

  const getOAuthUrl = async (provider) => {
    const response = await api.get(`/auth/oauth/${provider}`);
    return response.data.auth_url;
  };

  const sendVerificationEmail = async (email) => {
    const response = await api.post('/auth/verify-email/send', { email });
    return response.data;
  };

  const verifyEmail = async (token) => {
    const response = await api.post('/auth/verify-email/confirm', { token });
    if (user) setUser({ ...user, is_verified: true });
    return response.data;
  };

  const requestPasswordReset = async (email) => {
    const response = await api.post('/auth/password-reset/request', { email });
    return response.data;
  };

  const confirmPasswordReset = async (token, newPassword) => {
    const response = await api.post('/auth/password-reset/confirm', {
      token, new_password: newPassword
    });
    return response.data;
  };

  const updateProfile = async (data) => {
    const response = await api.put('/auth/me', data);
    setUser(response.data);
    return response.data;
  };

  const updatePassword = async (currentPassword, newPassword) => {
    const response = await api.put('/auth/me/password', {
      current_password: currentPassword, new_password: newPassword
    });
    return response.data;
  };

  const updateApiKeys = async (keys) => {
    const response = await api.put('/auth/me/api-keys', keys);
    await fetchUser();
    return response.data;
  };

  const value = {
    user, loading,
    isAuthenticated: !!user,
    isVerified: user?.is_verified ?? false,
    register, login, logout,
    oauthLogin, getOAuthUrl,
    sendVerificationEmail, verifyEmail,
    requestPasswordReset, confirmPasswordReset,
    updateProfile, updatePassword, updateApiKeys,
    refreshUser: fetchUser
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within an AuthProvider');
  return context;
}

export default AuthContext;
