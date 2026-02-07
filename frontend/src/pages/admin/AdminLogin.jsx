import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield, LogIn } from 'lucide-react';
import { adminApi } from '../../services/api';
import { Card, Spinner } from '../../components/ui';
import toast from 'react-hot-toast';

export default function AdminLogin() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      const res = await adminApi.login({ email, password });
      localStorage.setItem('adminToken', res.data.access_token);
      localStorage.setItem('adminUser', JSON.stringify(res.data.admin));
      toast.success('Welcome to Admin Dashboard');
      navigate('/admin/dashboard');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Login failed');
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen gradient-bg flex items-center justify-center p-4">
      <Card className="w-full max-w-md p-8">
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-accent/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <Shield className="w-8 h-8 text-accent" />
          </div>
          <h1 className="text-2xl font-bold text-pearl">Admin Login</h1>
          <p className="text-silver mt-2">Access the admin dashboard</p>
        </div>

        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="label">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="input-field"
              placeholder="admin@example.com"
              required
            />
          </div>
          <div>
            <label className="label">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="input-field"
              placeholder="••••••••"
              required
            />
          </div>
          <button type="submit" disabled={loading} className="btn-primary w-full flex items-center justify-center gap-2">
            {loading ? <Spinner size="sm" /> : <LogIn className="w-4 h-4" />}
            {loading ? 'Logging in...' : 'Login'}
          </button>
        </form>

        <p className="text-xs text-silver text-center mt-6">
          First time? Use <code className="bg-slate px-1 rounded">/api/v1/admin/setup</code> to create your admin account.
        </p>
      </Card>
    </div>
  );
}
