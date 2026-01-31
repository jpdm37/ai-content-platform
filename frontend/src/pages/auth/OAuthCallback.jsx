import { useEffect, useState } from 'react';
import { useParams, useSearchParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { Spinner } from '../../components/ui';
import toast from 'react-hot-toast';

export default function OAuthCallback() {
  const { provider } = useParams();
  const [searchParams] = useSearchParams();
  const code = searchParams.get('code');
  const error = searchParams.get('error');
  const navigate = useNavigate();
  const { oauthLogin } = useAuth();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (error) {
      toast.error('OAuth login cancelled');
      navigate('/login');
      return;
    }

    if (!code) {
      toast.error('Invalid OAuth callback');
      navigate('/login');
      return;
    }

    const handleCallback = async () => {
      try {
        await oauthLogin(provider, code);
        toast.success('Welcome!');
        navigate('/');
      } catch (err) {
        toast.error(err.response?.data?.detail || 'OAuth login failed');
        navigate('/login');
      } finally {
        setLoading(false);
      }
    };

    handleCallback();
  }, [code, error, provider, oauthLogin, navigate]);

  return (
    <div className="min-h-screen gradient-bg flex items-center justify-center">
      <div className="text-center">
        <Spinner size="lg" className="mx-auto mb-4" />
        <p className="text-pearl">Completing sign in...</p>
      </div>
    </div>
  );
}
