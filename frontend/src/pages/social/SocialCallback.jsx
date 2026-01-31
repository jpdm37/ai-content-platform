import { useEffect, useState } from 'react';
import { useParams, useSearchParams, useNavigate } from 'react-router-dom';
import { socialApi } from '../../services/api';
import { Spinner } from '../../components/ui';
import toast from 'react-hot-toast';

export default function SocialCallback() {
  const { platform } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState('connecting');

  useEffect(() => {
    const code = searchParams.get('code');
    const state = searchParams.get('state');
    const error = searchParams.get('error');

    if (error) {
      toast.error('Connection cancelled');
      navigate('/social/accounts');
      return;
    }

    if (!code) {
      toast.error('Invalid callback');
      navigate('/social/accounts');
      return;
    }

    const connect = async () => {
      try {
        const res = await socialApi.connectCallback(platform, { code, state });
        toast.success(`Connected @${res.data.username}!`);
        navigate('/social/accounts');
      } catch (err) {
        toast.error(err.response?.data?.detail || 'Connection failed');
        navigate('/social/accounts');
      }
    };

    connect();
  }, [platform, searchParams, navigate]);

  return (
    <div className="min-h-screen gradient-bg flex items-center justify-center">
      <div className="text-center">
        <Spinner size="lg" className="mx-auto mb-4" />
        <p className="text-pearl font-medium">Connecting your {platform} account...</p>
        <p className="text-silver text-sm mt-2">Please wait while we complete the connection.</p>
      </div>
    </div>
  );
}
