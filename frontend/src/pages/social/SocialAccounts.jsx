import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Share2, Plus, Trash2, RefreshCw, ExternalLink, Twitter, Instagram, Linkedin, Calendar, BarChart3 } from 'lucide-react';
import { socialApi, brandsApi } from '../../services/api';
import { Card, Badge, LoadingState, EmptyState, ConfirmDialog, Spinner, Modal } from '../../components/ui';
import toast from 'react-hot-toast';

const platformConfig = {
  twitter: { name: 'Twitter / X', icon: Twitter, color: 'bg-sky-500', connectColor: 'hover:bg-sky-600' },
  instagram: { name: 'Instagram', icon: Instagram, color: 'bg-gradient-to-br from-purple-500 to-pink-500', connectColor: 'hover:bg-pink-600' },
  linkedin: { name: 'LinkedIn', icon: Linkedin, color: 'bg-blue-600', connectColor: 'hover:bg-blue-700' },
  tiktok: { name: 'TikTok', icon: Share2, color: 'bg-black', connectColor: 'hover:bg-gray-800' },
  facebook: { name: 'Facebook', icon: Share2, color: 'bg-blue-500', connectColor: 'hover:bg-blue-600' },
};

export default function SocialAccounts() {
  const [accounts, setAccounts] = useState([]);
  const [brands, setBrands] = useState([]);
  const [loading, setLoading] = useState(true);
  const [connectModal, setConnectModal] = useState(false);
  const [connecting, setConnecting] = useState(null);
  const [disconnectAccount, setDisconnectAccount] = useState(null);
  const [selectedBrand, setSelectedBrand] = useState('');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [accountsRes, brandsRes] = await Promise.all([
        socialApi.listAccounts(),
        brandsApi.list()
      ]);
      setAccounts(accountsRes.data);
      setBrands(brandsRes.data);
    } catch (err) {
      toast.error('Failed to load accounts');
    }
    setLoading(false);
  };

  const handleConnect = async (platform) => {
    setConnecting(platform);
    try {
      const res = await socialApi.getConnectUrl(platform, selectedBrand || undefined);
      window.location.href = res.data.oauth_url;
    } catch (err) {
      toast.error(err.response?.data?.detail || `Failed to connect ${platform}`);
      setConnecting(null);
    }
  };

  const handleDisconnect = async () => {
    if (!disconnectAccount) return;
    try {
      await socialApi.disconnectAccount(disconnectAccount.id);
      toast.success('Account disconnected');
      fetchData();
    } catch (err) {
      toast.error('Failed to disconnect');
    }
    setDisconnectAccount(null);
  };

  const handleUpdateBrand = async (accountId, brandId) => {
    try {
      await socialApi.updateAccountBrand(accountId, brandId || undefined);
      toast.success('Brand updated');
      fetchData();
    } catch (err) {
      toast.error('Failed to update');
    }
  };

  if (loading) return <LoadingState message="Loading social accounts..." />;

  const availablePlatforms = ['twitter', 'instagram', 'linkedin'];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title flex items-center gap-3">
            <Share2 className="w-8 h-8 text-accent" />
            Social Accounts
          </h1>
          <p className="text-silver mt-1">Connect and manage your social media accounts</p>
        </div>
        <button onClick={() => setConnectModal(true)} className="btn-primary flex items-center gap-2">
          <Plus className="w-4 h-4" /> Connect Account
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="p-4">
          <p className="text-silver text-sm">Connected</p>
          <p className="text-2xl font-bold text-pearl">{accounts.length}</p>
        </Card>
        <Card className="p-4">
          <p className="text-silver text-sm">Scheduled Posts</p>
          <p className="text-2xl font-bold text-warning">
            {accounts.reduce((acc, a) => acc + (a.scheduled_count || 0), 0)}
          </p>
        </Card>
        <Card className="p-4">
          <p className="text-silver text-sm">Published</p>
          <p className="text-2xl font-bold text-success">
            {accounts.reduce((acc, a) => acc + (a.published_count || 0), 0)}
          </p>
        </Card>
        <Card className="p-4">
          <p className="text-silver text-sm">Total Posts</p>
          <p className="text-2xl font-bold text-accent">
            {accounts.reduce((acc, a) => acc + (a.posts_count || 0), 0)}
          </p>
        </Card>
      </div>

      {/* Accounts List */}
      {accounts.length === 0 ? (
        <EmptyState
          icon={Share2}
          title="No accounts connected"
          description="Connect your social media accounts to start scheduling posts"
          action={<button onClick={() => setConnectModal(true)} className="btn-primary">Connect Account</button>}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {accounts.map((account) => {
            const platform = platformConfig[account.platform] || platformConfig.twitter;
            const Icon = platform.icon;

            return (
              <Card key={account.id} className="p-5">
                <div className="flex items-start gap-4">
                  {/* Avatar */}
                  <div className={`w-14 h-14 rounded-xl ${platform.color} flex items-center justify-center flex-shrink-0`}>
                    {account.profile_image_url ? (
                      <img src={account.profile_image_url} alt="" className="w-full h-full rounded-xl object-cover" />
                    ) : (
                      <Icon className="w-7 h-7 text-white" />
                    )}
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-pearl truncate">
                      {account.platform_display_name || account.platform_username}
                    </h3>
                    <p className="text-silver text-sm">@{account.platform_username}</p>
                    <div className="flex items-center gap-2 mt-2">
                      <Badge variant={account.is_active ? 'success' : 'error'}>
                        {account.is_active ? 'Connected' : 'Disconnected'}
                      </Badge>
                      {account.last_error && (
                        <Badge variant="warning" title={account.last_error}>Error</Badge>
                      )}
                    </div>
                  </div>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-3 gap-2 mt-4 py-3 border-t border-graphite">
                  <div className="text-center">
                    <p className="text-lg font-semibold text-pearl">{account.scheduled_count || 0}</p>
                    <p className="text-xs text-silver">Scheduled</p>
                  </div>
                  <div className="text-center">
                    <p className="text-lg font-semibold text-pearl">{account.published_count || 0}</p>
                    <p className="text-xs text-silver">Published</p>
                  </div>
                  <div className="text-center">
                    <p className="text-lg font-semibold text-pearl">
                      {account.platform_data?.followers_count?.toLocaleString() || '-'}
                    </p>
                    <p className="text-xs text-silver">Followers</p>
                  </div>
                </div>

                {/* Brand Assignment */}
                <div className="mt-3">
                  <label className="text-xs text-silver">Assigned Brand</label>
                  <select
                    value={account.brand_id || ''}
                    onChange={(e) => handleUpdateBrand(account.id, e.target.value)}
                    className="input-field text-sm mt-1"
                  >
                    <option value="">No brand assigned</option>
                    {brands.map((brand) => (
                      <option key={brand.id} value={brand.id}>{brand.name}</option>
                    ))}
                  </select>
                </div>

                {/* Actions */}
                <div className="flex gap-2 mt-4">
                  <Link
                    to={`/social/schedule?account=${account.id}`}
                    className="btn-secondary flex-1 text-center text-sm py-2"
                  >
                    <Calendar className="w-4 h-4 inline mr-1" /> Schedule
                  </Link>
                  <Link
                    to={`/social/accounts/${account.id}/analytics`}
                    className="btn-secondary px-3"
                    title="Analytics"
                  >
                    <BarChart3 className="w-4 h-4" />
                  </Link>
                  <button
                    onClick={() => setDisconnectAccount(account)}
                    className="p-2 text-silver hover:text-error transition-colors"
                    title="Disconnect"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {/* Connect Modal */}
      <Modal isOpen={connectModal} onClose={() => setConnectModal(false)} title="Connect Social Account">
        <div className="space-y-4">
          <div>
            <label className="label">Assign to Brand (optional)</label>
            <select
              value={selectedBrand}
              onChange={(e) => setSelectedBrand(e.target.value)}
              className="input-field"
            >
              <option value="">No brand</option>
              {brands.map((brand) => (
                <option key={brand.id} value={brand.id}>{brand.name}</option>
              ))}
            </select>
          </div>

          <div className="space-y-3">
            {availablePlatforms.map((platformKey) => {
              const platform = platformConfig[platformKey];
              const Icon = platform.icon;
              const isConnecting = connecting === platformKey;

              return (
                <button
                  key={platformKey}
                  onClick={() => handleConnect(platformKey)}
                  disabled={isConnecting}
                  className={`w-full flex items-center gap-4 p-4 rounded-xl ${platform.color} text-white font-medium transition-all ${platform.connectColor} disabled:opacity-50`}
                >
                  {isConnecting ? (
                    <Spinner size="sm" />
                  ) : (
                    <Icon className="w-6 h-6" />
                  )}
                  <span>Connect {platform.name}</span>
                </button>
              );
            })}
          </div>

          <p className="text-silver text-sm text-center">
            More platforms coming soon: TikTok, Facebook, Threads
          </p>
        </div>
      </Modal>

      {/* Disconnect Confirmation */}
      <ConfirmDialog
        isOpen={!!disconnectAccount}
        onClose={() => setDisconnectAccount(null)}
        onConfirm={handleDisconnect}
        title="Disconnect Account?"
        message={`Disconnect @${disconnectAccount?.platform_username}? Scheduled posts will be cancelled.`}
        confirmText="Disconnect"
        danger
      />
    </div>
  );
}
