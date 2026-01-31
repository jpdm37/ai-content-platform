import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { LoadingState } from './ui';

export default function ProtectedRoute({ children, requireVerified = false }) {
  const { isAuthenticated, isVerified, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return <LoadingState message="Loading..." />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (requireVerified && !isVerified) {
    return (
      <div className="min-h-screen gradient-bg flex items-center justify-center p-4">
        <div className="card p-8 text-center max-w-md">
          <h1 className="text-xl font-display font-bold text-pearl mb-4">Email Verification Required</h1>
          <p className="text-silver mb-6">Please verify your email address to access this feature.</p>
        </div>
      </div>
    );
  }

  return children;
}
