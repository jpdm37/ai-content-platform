import { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Check, X, Zap } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { Spinner } from '../../components/ui';

export default function VerifyEmail() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  const [status, setStatus] = useState('loading'); // loading, success, error
  const [message, setMessage] = useState('');
  const { verifyEmail } = useAuth();

  useEffect(() => {
    if (!token) { setStatus('error'); setMessage('Invalid verification link'); return; }
    
    const verify = async () => {
      try {
        await verifyEmail(token);
        setStatus('success');
        setMessage('Your email has been verified!');
      } catch (error) {
        setStatus('error');
        setMessage(error.response?.data?.detail || 'Verification failed');
      }
    };
    verify();
  }, [token, verifyEmail]);

  return (
    <div className="min-h-screen gradient-bg flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <Link to="/" className="inline-flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-accent to-accent-dark flex items-center justify-center shadow-glow"><Zap className="w-6 h-6 text-white" /></div>
            <span className="font-display font-bold text-2xl text-pearl">AI Content</span>
          </Link>
        </div>
        <div className="card p-8 text-center">
          {status === 'loading' && (
            <>
              <Spinner size="lg" className="mx-auto mb-6" />
              <h1 className="text-2xl font-display font-bold text-pearl mb-4">Verifying your email...</h1>
              <p className="text-silver">Please wait while we verify your email address.</p>
            </>
          )}
          {status === 'success' && (
            <>
              <div className="w-16 h-16 rounded-full bg-success/20 flex items-center justify-center mx-auto mb-6"><Check className="w-8 h-8 text-success" /></div>
              <h1 className="text-2xl font-display font-bold text-pearl mb-4">Email Verified!</h1>
              <p className="text-silver mb-6">{message}</p>
              <Link to="/" className="btn-primary">Go to Dashboard</Link>
            </>
          )}
          {status === 'error' && (
            <>
              <div className="w-16 h-16 rounded-full bg-error/20 flex items-center justify-center mx-auto mb-6"><X className="w-8 h-8 text-error" /></div>
              <h1 className="text-2xl font-display font-bold text-pearl mb-4">Verification Failed</h1>
              <p className="text-silver mb-6">{message}</p>
              <Link to="/login" className="btn-primary">Go to Login</Link>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
