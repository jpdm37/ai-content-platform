import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Mail, Lock, Eye, EyeOff, User, Zap, ArrowRight, Check } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { Spinner } from '../../components/ui';
import toast from 'react-hot-toast';

export default function Register() {
  const [formData, setFormData] = useState({ email: '', password: '', confirmPassword: '', fullName: '' });
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const { register } = useAuth();

  const handleChange = (e) => setFormData({ ...formData, [e.target.name]: e.target.value });

  const passwordChecks = {
    minLength: formData.password.length >= 8,
    hasNumber: /\d/.test(formData.password),
    hasLetter: /[a-zA-Z]/.test(formData.password)
  };
  const isPasswordValid = Object.values(passwordChecks).every(Boolean);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!isPasswordValid) { toast.error('Password does not meet requirements'); return; }
    if (formData.password !== formData.confirmPassword) { toast.error('Passwords do not match'); return; }
    
    setLoading(true);
    try {
      await register(formData.email, formData.password, formData.fullName);
      setSuccess(true);
      toast.success('Account created! Please check your email.');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="min-h-screen gradient-bg flex items-center justify-center p-4">
        <div className="w-full max-w-md card p-8 text-center">
          <div className="w-16 h-16 rounded-full bg-success/20 flex items-center justify-center mx-auto mb-6">
            <Check className="w-8 h-8 text-success" />
          </div>
          <h1 className="text-2xl font-display font-bold text-pearl mb-4">Check your email</h1>
          <p className="text-silver mb-6">We've sent a verification link to <strong className="text-pearl">{formData.email}</strong>.</p>
          <Link to="/login" className="btn-primary inline-flex items-center gap-2">Go to Login <ArrowRight className="w-4 h-4" /></Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen gradient-bg flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <Link to="/" className="inline-flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-accent to-accent-dark flex items-center justify-center shadow-glow">
              <Zap className="w-6 h-6 text-white" />
            </div>
            <span className="font-display font-bold text-2xl text-pearl">AI Content</span>
          </Link>
        </div>
        <div className="card p-8">
          <h1 className="text-2xl font-display font-bold text-pearl text-center mb-2">Create an account</h1>
          <p className="text-silver text-center mb-8">Get started with AI-powered content creation</p>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="label">Full Name</label>
              <div className="relative">
                <User className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-silver" />
                <input type="text" name="fullName" value={formData.fullName} onChange={handleChange} placeholder="John Doe" className="input-field pl-12" />
              </div>
            </div>
            <div>
              <label className="label">Email *</label>
              <div className="relative">
                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-silver" />
                <input type="email" name="email" value={formData.email} onChange={handleChange} placeholder="you@example.com" className="input-field pl-12" required />
              </div>
            </div>
            <div>
              <label className="label">Password *</label>
              <div className="relative">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-silver" />
                <input type={showPassword ? 'text' : 'password'} name="password" value={formData.password} onChange={handleChange} placeholder="••••••••" className="input-field pl-12 pr-12" required />
                <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-4 top-1/2 -translate-y-1/2 text-silver hover:text-pearl">
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
              <div className="mt-2 space-y-1">
                {[{ key: 'minLength', label: '8+ characters' }, { key: 'hasLetter', label: 'Has letter' }, { key: 'hasNumber', label: 'Has number' }].map(({ key, label }) => (
                  <div key={key} className="flex items-center gap-2 text-xs">
                    <div className={`w-4 h-4 rounded-full flex items-center justify-center ${passwordChecks[key] ? 'bg-success/20 text-success' : 'bg-slate text-silver'}`}>
                      {passwordChecks[key] && <Check className="w-3 h-3" />}
                    </div>
                    <span className={passwordChecks[key] ? 'text-success' : 'text-silver'}>{label}</span>
                  </div>
                ))}
              </div>
            </div>
            <div>
              <label className="label">Confirm Password *</label>
              <div className="relative">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-silver" />
                <input type={showPassword ? 'text' : 'password'} name="confirmPassword" value={formData.confirmPassword} onChange={handleChange} placeholder="••••••••" className="input-field pl-12" required />
              </div>
            </div>
            <button type="submit" disabled={loading} className="w-full btn-primary py-3 flex items-center justify-center gap-2">
              {loading ? <Spinner size="sm" /> : <>Create Account <ArrowRight className="w-4 h-4" /></>}
            </button>
          </form>
          <p className="mt-6 text-center text-silver">Already have an account? <Link to="/login" className="text-accent hover:text-accent-light font-medium">Sign in</Link></p>
        </div>
      </div>
    </div>
  );
}
