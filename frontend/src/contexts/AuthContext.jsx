import { createContext, useContext, useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

const AuthContext = createContext(null);

// Get API URL from environment or use default
const API_URL = import.meta.env.VITE_API_URL || '/api/v1';

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [onboardingComplete, setOnboardingComplete] = useState(true);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    const token = localStorage.getItem('token');
    if (!token) {
      setLoading(false);
      return;
    }

    try {
      const res = await fetch(`${API_URL}/auth/me`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (res.ok) {
        const userData = await res.json();
        setUser(userData);
        
        // Check onboarding status
        await checkOnboardingStatus(token);
      } else {
        localStorage.removeItem('token');
      }
    } catch (err) {
      console.error('Auth check failed:', err);
      localStorage.removeItem('token');
    }
    
    setLoading(false);
  };

  const checkOnboardingStatus = async (token) => {
    try {
      const res = await fetch(`${API_URL}/onboarding/status`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (res.ok) {
        const status = await res.json();
        setOnboardingComplete(status.is_complete);
        
        // Redirect to onboarding if not complete and not already there
        if (!status.is_complete && 
            !location.pathname.startsWith('/onboarding') &&
            !location.pathname.startsWith('/auth')) {
          navigate('/onboarding');
        }
      }
    } catch (err) {
      // If onboarding check fails, assume complete
      setOnboardingComplete(true);
    }
  };

  const login = async (email, password) => {
    const res = await fetch(`${API_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });

    if (!res.ok) {
      const error = await res.json();
      throw new Error(error.detail || 'Login failed');
    }

    const data = await res.json();
    
    // Store the token
    localStorage.setItem('token', data.access_token);
    
    // Fetch user data since login response doesn't include it
    const userRes = await fetch(`${API_URL}/auth/me`, {
      headers: { 'Authorization': `Bearer ${data.access_token}` }
    });
    
    if (!userRes.ok) {
      localStorage.removeItem('token');
      throw new Error('Failed to fetch user data');
    }
    
    const userData = await userRes.json();
    setUser(userData);
    
    // Check onboarding status and navigate
    try {
      const onboardingRes = await fetch(`${API_URL}/onboarding/status`, {
        headers: { 'Authorization': `Bearer ${data.access_token}` }
      });
      
      if (onboardingRes.ok) {
        const status = await onboardingRes.json();
        setOnboardingComplete(status.is_complete);
        
        if (!status.is_complete) {
          navigate('/onboarding');
        } else {
          navigate('/');
        }
      } else {
        navigate('/');
      }
    } catch (err) {
      // If onboarding check fails, go to dashboard
      navigate('/');
    }
    
    return data;
  };

  const register = async (email, password, fullName) => {
    const res = await fetch(`${API_URL}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        email, 
        password, 
        full_name: fullName
      })
    });

    if (!res.ok) {
      const error = await res.json();
      throw new Error(error.detail || 'Registration failed');
    }

    const data = await res.json();
    
    // After registration, login to get token
    // (Registration might not return a token)
    if (data.access_token) {
      localStorage.setItem('token', data.access_token);
      setUser(data);
    } else {
      // Need to login after registration
      await login(email, password);
      return data;
    }
    
    // New users always go to onboarding
    setOnboardingComplete(false);
    navigate('/onboarding');
    
    return data;
  };

  const logout = () => {
    localStorage.removeItem('token');
    setUser(null);
    setOnboardingComplete(true);
    navigate('/login');
  };

  const completeOnboarding = () => {
    setOnboardingComplete(true);
  };

  const value = {
    user,
    loading,
    onboardingComplete,
    login,
    register,
    logout,
    completeOnboarding,
    isAuthenticated: !!user
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}

export default AuthContext;
