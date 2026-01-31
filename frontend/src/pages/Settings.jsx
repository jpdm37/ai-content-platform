import { useState, useEffect } from 'react';
import { Settings as SettingsIcon, Key, User, Shield, ExternalLink, Check, Eye, EyeOff, LogOut } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { statusApi } from '../services/api';
import { Card, LoadingState, Badge, Spinner } from '../components/ui';
import toast from 'react-hot-toast';

export default function Settings() {
  const { user, updateProfile, updatePassword, updateApiKeys, logout } = useAuth();
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('profile');

  // Profile form
  const [profileData, setProfileData] = useState({ full_name: '', avatar_url: '' });
  const [profileLoading, setProfileLoading] = useState(false);

  // Password form
  const [passwordData, setPasswordData] = useState({ current_password: '', new_password: '', confirm_password: '' });
  const [showPasswords, setShowPasswords] = useState(false);
  const [passwordLoading, setPasswordLoading] = useState(false);

  // API Keys form
  const [apiKeysData, setApiKeysData] = useState({ openai_api_key: '', replicate_api_token: '' });
  const [apiKeysLoading, setApiKeysLoading] = useState(false);

  useEffect(() => {
    if (user) {
      setProfileData({ full_name: user.full_name || '', avatar_url: user.avatar_url || '' });
    }
  }, [user]);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await statusApi.status();
        setStatus(res.data);
      } catch (err) {}
      setLoading(false);
    };
    fetchStatus();
  }, []);

  const handleProfileSubmit = async (e) => {
    e.preventDefault();
    setProfileLoading(true);
    try {
      await updateProfile(profileData);
      toast.success('Profile updated!');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to update profile');
    }
    setProfileLoading(false);
  };

  const handlePasswordSubmit = async (e) => {
    e.preventDefault();
    if (passwordData.new_password !== passwordData.confirm_password) {
      toast.error('Passwords do not match');
      return;
    }
    if (passwordData.new_password.length < 8) {
      toast.error('Password must be at least 8 characters');
      return;
    }
    setPasswordLoading(true);
    try {
      await updatePassword(passwordData.current_password, passwordData.new_password);
      toast.success('Password updated!');
      setPasswordData({ current_password: '', new_password: '', confirm_password: '' });
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to update password');
    }
    setPasswordLoading(false);
  };

  const handleApiKeysSubmit = async (e) => {
    e.preventDefault();
    setApiKeysLoading(true);
    try {
      await updateApiKeys(apiKeysData);
      toast.success('API keys updated!');
      setApiKeysData({ openai_api_key: '', replicate_api_token: '' });
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to update API keys');
    }
    setApiKeysLoading(false);
  };

  if (loading) return <LoadingState message="Loading settings..." />;

  const tabs = [
    { id: 'profile', label: 'Profile', icon: User },
    { id: 'security', label: 'Security', icon: Shield },
    { id: 'api-keys', label: 'API Keys', icon: Key },
  ];

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="page-title flex items-center gap-3"><SettingsIcon className="w-8 h-8 text-accent" />Settings</h1>
        <p className="text-silver mt-1">Manage your account and preferences</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 p-1 bg-slate rounded-xl w-fit">
        {tabs.map((tab) => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)} className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-sm transition-all ${activeTab === tab.id ? 'bg-accent text-white shadow-lg' : 'text-silver hover:text-pearl'}`}>
            <tab.icon className="w-4 h-4" />{tab.label}
          </button>
        ))}
      </div>

      {/* Profile Tab */}
      {activeTab === 'profile' && (
        <Card className="p-6">
          <h2 className="section-title mb-6">Profile Information</h2>
          <form onSubmit={handleProfileSubmit} className="space-y-4">
            <div>
              <label className="label">Email</label>
              <input type="email" value={user?.email || ''} disabled className="input-field bg-slate/50" />
              <p className="text-silver text-xs mt-1">Email cannot be changed</p>
            </div>
            <div>
              <label className="label">Full Name</label>
              <input type="text" value={profileData.full_name} onChange={(e) => setProfileData({ ...profileData, full_name: e.target.value })} placeholder="Your name" className="input-field" />
            </div>
            <div>
              <label className="label">Avatar URL</label>
              <input type="url" value={profileData.avatar_url} onChange={(e) => setProfileData({ ...profileData, avatar_url: e.target.value })} placeholder="https://..." className="input-field" />
            </div>
            <div className="flex items-center gap-4">
              <span className="text-silver">Account Status:</span>
              <Badge variant={user?.is_verified ? 'success' : 'warning'}>{user?.is_verified ? 'Verified' : 'Unverified'}</Badge>
              <Badge variant="info">{user?.auth_provider}</Badge>
            </div>
            <button type="submit" disabled={profileLoading} className="btn-primary flex items-center gap-2">{profileLoading ? <Spinner size="sm" /> : <Check className="w-4 h-4" />}Save Changes</button>
          </form>
          <hr className="border-graphite my-6" />
          <button onClick={logout} className="btn-danger flex items-center gap-2"><LogOut className="w-4 h-4" />Sign Out</button>
        </Card>
      )}

      {/* Security Tab */}
      {activeTab === 'security' && (
        <Card className="p-6">
          <h2 className="section-title mb-6">Change Password</h2>
          {user?.auth_provider !== 'LOCAL' ? (
            <p className="text-silver">Password management is not available for {user?.auth_provider} accounts.</p>
          ) : (
            <form onSubmit={handlePasswordSubmit} className="space-y-4">
              <div>
                <label className="label">Current Password</label>
                <input type={showPasswords ? 'text' : 'password'} value={passwordData.current_password} onChange={(e) => setPasswordData({ ...passwordData, current_password: e.target.value })} className="input-field" required />
              </div>
              <div>
                <label className="label">New Password</label>
                <input type={showPasswords ? 'text' : 'password'} value={passwordData.new_password} onChange={(e) => setPasswordData({ ...passwordData, new_password: e.target.value })} className="input-field" required />
              </div>
              <div>
                <label className="label">Confirm New Password</label>
                <input type={showPasswords ? 'text' : 'password'} value={passwordData.confirm_password} onChange={(e) => setPasswordData({ ...passwordData, confirm_password: e.target.value })} className="input-field" required />
              </div>
              <label className="flex items-center gap-2 text-silver cursor-pointer">
                <input type="checkbox" checked={showPasswords} onChange={(e) => setShowPasswords(e.target.checked)} className="rounded" />
                Show passwords
              </label>
              <button type="submit" disabled={passwordLoading} className="btn-primary flex items-center gap-2">{passwordLoading ? <Spinner size="sm" /> : 'Update Password'}</button>
            </form>
          )}
        </Card>
      )}

      {/* API Keys Tab */}
      {activeTab === 'api-keys' && (
        <Card className="p-6">
          <h2 className="section-title mb-2">Personal API Keys</h2>
          <p className="text-silver text-sm mb-6">Add your own API keys to use instead of the system defaults. Your keys are encrypted and stored securely.</p>
          
          <div className="space-y-4 mb-6">
            <div className="flex items-center justify-between p-4 bg-slate rounded-xl">
              <div><p className="font-medium text-pearl">OpenAI API</p><p className="text-silver text-sm">For caption generation</p></div>
              <Badge variant={user?.has_openai_key ? 'success' : status?.openai_configured ? 'info' : 'error'}>{user?.has_openai_key ? 'Personal Key' : status?.openai_configured ? 'System Key' : 'Not Configured'}</Badge>
            </div>
            <div className="flex items-center justify-between p-4 bg-slate rounded-xl">
              <div><p className="font-medium text-pearl">Replicate API</p><p className="text-silver text-sm">For image generation</p></div>
              <Badge variant={user?.has_replicate_key ? 'success' : status?.replicate_configured ? 'info' : 'error'}>{user?.has_replicate_key ? 'Personal Key' : status?.replicate_configured ? 'System Key' : 'Not Configured'}</Badge>
            </div>
          </div>

          <form onSubmit={handleApiKeysSubmit} className="space-y-4">
            <div>
              <label className="label">OpenAI API Key</label>
              <input type="password" value={apiKeysData.openai_api_key} onChange={(e) => setApiKeysData({ ...apiKeysData, openai_api_key: e.target.value })} placeholder="sk-..." className="input-field" />
              <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener noreferrer" className="text-accent text-xs flex items-center gap-1 mt-1">Get key <ExternalLink className="w-3 h-3" /></a>
            </div>
            <div>
              <label className="label">Replicate API Token</label>
              <input type="password" value={apiKeysData.replicate_api_token} onChange={(e) => setApiKeysData({ ...apiKeysData, replicate_api_token: e.target.value })} placeholder="r8_..." className="input-field" />
              <a href="https://replicate.com/account/api-tokens" target="_blank" rel="noopener noreferrer" className="text-accent text-xs flex items-center gap-1 mt-1">Get token <ExternalLink className="w-3 h-3" /></a>
            </div>
            <p className="text-silver text-xs">Leave fields empty to keep existing keys. Enter new values to update.</p>
            <button type="submit" disabled={apiKeysLoading} className="btn-primary flex items-center gap-2">{apiKeysLoading ? <Spinner size="sm" /> : 'Save API Keys'}</button>
          </form>
        </Card>
      )}
    </div>
  );
}
