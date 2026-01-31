import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Mail, Zap, ArrowLeft, Check } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { Spinner } from '../../components/ui';
import toast from 'react-hot-toast';

export default function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const { requestPasswordReset } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email) { toast.error('Please enter your email'); return; }
    setLoading(true);
    try {
      await requestPasswordReset(email);
      setSuccess(true);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send reset email');
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="min-h-screen gradient-bg flex items-center justify-center p-4">
        <div className="w-full max-w-md card p-8 text-center">
          <div className="w-16 h-16 rounded-full bg-success/20 flex items-center justify-center mx-auto mb-6"><Check className="w-8 h-8 text-success" /></div>
          <h1 className="text-2xl font-display font-bold text-pearl mb-4">Check your email</h1>
          <p className="text-silver mb-6">If an account exists for <strong className="text-pearl">{email}</strong>, you'll receive a password reset link.</p>
          <Link to="/login" className="btn-primary inline-flex items-center gap-2">Back to Login</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen gradient-bg flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <Link to="/" className="inline-flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-accent to-accent-dark flex items-center justify-center shadow-glow"><Zap className="w-6 h-6 text-white" /></div>
            <span className="font-display font-bold text-2xl text-pearl">AI Content</span>
          </Link>
        </div>
        <div className="card p-8">
          <Link to="/login" className="inline-flex items-center gap-2 text-silver hover:text-pearl mb-6"><ArrowLeft className="w-4 h-4" /> Back to login</Link>
          <h1 className="text-2xl font-display font-bold text-pearl mb-2">Forgot password?</h1>
          <p className="text-silver mb-8">Enter your email and we'll send you a reset link.</p>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="label">Email</label>
              <div className="relative"><Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-silver" /><input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" className="input-field pl-12" required /></div>
            </div>
            <button type="submit" disabled={loading} className="w-full btn-primary py-3 flex items-center justify-center gap-2">{loading ? <Spinner size="sm" /> : 'Send Reset Link'}</button>
          </form>
        </div>
      </div>
    </div>
  );
}
