import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Users, Settings, BarChart3, Shield, Bell, Activity,
  Plus, Search, RefreshCw, CheckCircle, XCircle, Eye,
  DollarSign, Server, Zap, X, Edit, Trash2
} from 'lucide-react';
import toast from 'react-hot-toast';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const adminFetch = async (endpoint, options = {}) => {
  const token = localStorage.getItem('admin_token');
  const res = await fetch(`${API_URL}/api/v1${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
      ...options.headers
    }
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Request failed');
  }
  return res.json();
};

export default function AdminDashboard() {
  const [activeTab, setActiveTab] = useState('overview');
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null);
  const [health, setHealth] = useState(null);
  const [features, setFeatures] = useState([]);
  const [users, setUsers] = useState([]);
  const [tierLimits, setTierLimits] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedUser, setSelectedUser] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (!localStorage.getItem('admin_token')) {
      navigate('/admin/login');
      return;
    }
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [statsRes, healthRes, featuresRes, usersRes, limitsRes] = await Promise.all([
        adminFetch('/admin/stats'),
        adminFetch('/admin/manage/health').catch(() => ({ status: 'unknown' })),
        adminFetch('/admin/manage/features').catch(() => []),
        adminFetch('/admin/users?per_page=50'),
        adminFetch('/admin/manage/tier-limits').catch(() => null)
      ]);
      setStats(statsRes);
      setHealth(healthRes);
      setFeatures(featuresRes);
      setUsers(usersRes.users || []);
      setTierLimits(limitsRes);
    } catch (err) {
      toast.error('Failed to load data');
    }
    setLoading(false);
  };

  const tabs = [
    { id: 'overview', label: 'Overview', icon: BarChart3 },
    { id: 'users', label: 'Users', icon: Users },
    { id: 'features', label: 'Features', icon: Settings },
    { id: 'tiers', label: 'Tier Limits', icon: DollarSign },
    { id: 'system', label: 'System', icon: Server },
  ];

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-white">Loading admin dashboard...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900">
      <header className="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Shield className="w-8 h-8 text-blue-500" />
            <h1 className="text-xl font-bold text-white">Admin Dashboard</h1>
          </div>
          <div className="flex items-center gap-4">
            <button onClick={loadData} className="p-2 hover:bg-gray-700 rounded-lg">
              <RefreshCw className="w-5 h-5 text-gray-400" />
            </button>
            <button
              onClick={() => { localStorage.removeItem('admin_token'); navigate('/admin/login'); }}
              className="px-4 py-2 text-sm text-gray-400 hover:text-white"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      <div className="flex">
        <aside className="w-64 bg-gray-800 border-r border-gray-700 min-h-[calc(100vh-73px)]">
          <nav className="p-4 space-y-1">
            {tabs.map(tab => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                    activeTab === tab.id
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-400 hover:bg-gray-700 hover:text-white'
                  }`}
                >
                  <Icon className="w-5 h-5" />
                  {tab.label}
                </button>
              );
            })}
          </nav>
        </aside>

        <main className="flex-1 p-6">
          {activeTab === 'overview' && <OverviewTab stats={stats} health={health} />}
          {activeTab === 'users' && (
            <UsersTab 
              users={users} 
              searchQuery={searchQuery}
              setSearchQuery={setSearchQuery}
              onRefresh={loadData}
              selectedUser={selectedUser}
              setSelectedUser={setSelectedUser}
            />
          )}
          {activeTab === 'features' && <FeaturesTab features={features} onRefresh={loadData} />}
          {activeTab === 'tiers' && <TierLimitsTab limits={tierLimits} onRefresh={loadData} />}
          {activeTab === 'system' && <SystemTab health={health} />}
        </main>
      </div>
    </div>
  );
}

function OverviewTab({ stats, health }) {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-white">Platform Overview</h2>
      <div className="grid grid-cols-4 gap-4">
        <StatCard title="Total Users" value={stats?.total_users || 0} icon={Users} />
        <StatCard title="Active (24h)" value={stats?.active_users_24h || 0} icon={Activity} color="text-green-500" />
        <StatCard title="Total Content" value={stats?.total_content || 0} icon={Zap} color="text-blue-500" />
        <StatCard title="Revenue" value={`$${(stats?.total_revenue || 0).toLocaleString()}`} icon={DollarSign} color="text-yellow-500" />
      </div>
      <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
        <h3 className="text-lg font-semibold text-white mb-4">System Status</h3>
        <div className="flex items-center gap-3">
          <div className={`w-3 h-3 rounded-full ${health?.status === 'healthy' ? 'bg-green-500' : 'bg-yellow-500'}`} />
          <span className="text-white capitalize">{health?.status || 'Unknown'}</span>
        </div>
      </div>
      <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
        <h3 className="text-lg font-semibold text-white mb-4">Users by Tier</h3>
        <div className="grid grid-cols-4 gap-4">
          {['free', 'creator', 'pro', 'agency'].map(tier => (
            <div key={tier} className="bg-gray-700 rounded-lg p-4 text-center">
              <p className="text-2xl font-bold text-white">{stats?.users_by_tier?.[tier] || 0}</p>
              <p className="text-sm text-gray-400 capitalize">{tier}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function UsersTab({ users, searchQuery, setSearchQuery, onRefresh, selectedUser, setSelectedUser }) {
  const handleAction = async (userId, action, data = {}) => {
    try {
      await adminFetch(`/admin/manage/users/${userId}/${action}`, { method: 'POST', body: JSON.stringify(data) });
      toast.success(`Action completed`);
      onRefresh();
    } catch (err) {
      toast.error(err.message);
    }
  };

  const handleChangeTier = async (userId) => {
    const tier = prompt('New tier (free, creator, pro, agency):');
    if (!tier || !['free', 'creator', 'pro', 'agency'].includes(tier)) return;
    try {
      await adminFetch(`/admin/manage/users/${userId}/subscription/change-tier`, {
        method: 'POST',
        body: JSON.stringify({ new_tier: tier, duration_days: 365 })
      });
      toast.success(`Tier changed to ${tier}`);
      onRefresh();
    } catch (err) {
      toast.error(err.message);
    }
  };

  const handleAddUsage = async (userId) => {
    const type = prompt('Usage type (generations, images, videos):') || 'generations';
    const amount = prompt('Amount to add:', '10');
    if (!amount) return;
    try {
      await adminFetch(`/admin/manage/users/${userId}/usage/add`, {
        method: 'POST',
        body: JSON.stringify({ usage_type: type, amount: parseInt(amount), reason: 'Admin granted' })
      });
      toast.success(`Added ${amount} ${type}`);
    } catch (err) {
      toast.error(err.message);
    }
  };

  const filtered = users.filter(u => 
    u.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
    u.full_name?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-white">User Management</h2>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            type="text"
            placeholder="Search users..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10 pr-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white"
          />
        </div>
      </div>
      <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-700">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">User</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Status</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Tier</th>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Content</th>
              <th className="px-4 py-3 text-right text-sm font-medium text-gray-400">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700">
            {filtered.map(user => (
              <tr key={user.id} className="hover:bg-gray-700/50">
                <td className="px-4 py-3">
                  <p className="text-white font-medium">{user.full_name || 'No name'}</p>
                  <p className="text-sm text-gray-400">{user.email}</p>
                </td>
                <td className="px-4 py-3">
                  {user.is_active ? (
                    <span className="px-2 py-1 text-xs bg-green-500/20 text-green-400 rounded">Active</span>
                  ) : (
                    <span className="px-2 py-1 text-xs bg-red-500/20 text-red-400 rounded">Suspended</span>
                  )}
                </td>
                <td className="px-4 py-3">
                  <span className="text-gray-300 capitalize">{user.subscription_tier || 'free'}</span>
                </td>
                <td className="px-4 py-3 text-gray-400">{user.content_count}</td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-end gap-2">
                    <button onClick={() => setSelectedUser(user)} className="p-1 hover:bg-gray-600 rounded" title="View">
                      <Eye className="w-4 h-4 text-gray-400" />
                    </button>
                    <button onClick={() => handleChangeTier(user.id)} className="p-1 hover:bg-gray-600 rounded" title="Change tier">
                      <DollarSign className="w-4 h-4 text-gray-400" />
                    </button>
                    <button onClick={() => handleAddUsage(user.id)} className="p-1 hover:bg-gray-600 rounded" title="Add usage">
                      <Plus className="w-4 h-4 text-gray-400" />
                    </button>
                    {user.is_active ? (
                      <button onClick={() => handleAction(user.id, 'suspend', { reason: 'Admin' })} className="p-1 hover:bg-red-500/20 rounded" title="Suspend">
                        <XCircle className="w-4 h-4 text-red-400" />
                      </button>
                    ) : (
                      <button onClick={() => handleAction(user.id, 'unsuspend')} className="p-1 hover:bg-green-500/20 rounded" title="Reactivate">
                        <CheckCircle className="w-4 h-4 text-green-400" />
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {selectedUser && <UserModal user={selectedUser} onClose={() => setSelectedUser(null)} />}
    </div>
  );
}

function FeaturesTab({ features, onRefresh }) {
  const handleToggle = async (feature) => {
    try {
      await adminFetch(`/admin/manage/features/${feature.key}`, {
        method: 'PUT',
        body: JSON.stringify({ enabled: !feature.enabled })
      });
      toast.success(`${feature.key} ${!feature.enabled ? 'enabled' : 'disabled'}`);
      onRefresh();
    } catch (err) {
      toast.error(err.message);
    }
  };

  const categories = [...new Set(features.map(f => f.category))];

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-white">Feature Flags</h2>
      <p className="text-gray-400">Enable or disable platform features globally.</p>
      {categories.map(cat => (
        <div key={cat} className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
          <div className="px-4 py-3 bg-gray-700 border-b border-gray-600">
            <h3 className="text-lg font-medium text-white capitalize">{cat}</h3>
          </div>
          <div className="divide-y divide-gray-700">
            {features.filter(f => f.category === cat).map(feature => (
              <div key={feature.key} className="px-4 py-4 flex items-center justify-between">
                <div>
                  <p className="text-white font-medium">{feature.key.replace('feature_', '').replace(/_/g, ' ')}</p>
                  <p className="text-sm text-gray-400">{feature.description}</p>
                </div>
                <button
                  onClick={() => handleToggle(feature)}
                  className={`relative w-14 h-7 rounded-full transition-colors ${feature.enabled ? 'bg-blue-600' : 'bg-gray-600'}`}
                >
                  <div className={`absolute top-1 w-5 h-5 rounded-full bg-white transition-transform ${feature.enabled ? 'left-8' : 'left-1'}`} />
                </button>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function TierLimitsTab({ limits, onRefresh }) {
  const [editing, setEditing] = useState(null);
  const [values, setValues] = useState({});

  const handleSave = async (tier) => {
    try {
      await adminFetch(`/admin/manage/tier-limits/${tier}`, {
        method: 'PUT',
        body: JSON.stringify({ limits: values })
      });
      toast.success('Limits updated');
      setEditing(null);
      onRefresh();
    } catch (err) {
      toast.error(err.message);
    }
  };

  if (!limits) return <p className="text-gray-400">Loading...</p>;

  const tiers = ['free', 'creator', 'pro', 'agency'];
  const keys = Object.keys(limits.free || {});

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-white">Tier Limits</h2>
      <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-700">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Limit</th>
              {tiers.map(t => (
                <th key={t} className="px-4 py-3 text-center text-sm font-medium text-gray-400 capitalize">
                  {t}
                  <button onClick={() => { setEditing(t); setValues(limits[t]); }} className="ml-2 text-blue-400">
                    <Edit className="w-3 h-3 inline" />
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700">
            {keys.map(key => (
              <tr key={key}>
                <td className="px-4 py-3 text-white capitalize">{key.replace(/_/g, ' ')}</td>
                {tiers.map(t => (
                  <td key={t} className="px-4 py-3 text-center">
                    {editing === t ? (
                      <input
                        type="number"
                        value={values[key] || 0}
                        onChange={(e) => setValues({ ...values, [key]: parseInt(e.target.value) || 0 })}
                        className="w-20 px-2 py-1 bg-gray-700 border border-gray-600 rounded text-white text-center"
                      />
                    ) : (
                      <span className="text-gray-400">{limits[t]?.[key] || 0}</span>
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        {editing && (
          <div className="px-4 py-3 bg-gray-700 flex justify-end gap-2">
            <button onClick={() => setEditing(null)} className="px-4 py-2 text-gray-400">Cancel</button>
            <button onClick={() => handleSave(editing)} className="px-4 py-2 bg-blue-600 text-white rounded-lg">Save</button>
          </div>
        )}
      </div>
    </div>
  );
}

function SystemTab({ health }) {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-white">System Status</h2>
      <div className="grid grid-cols-2 gap-6">
        <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
          <h3 className="text-lg font-medium text-white mb-4">Health</h3>
          <div className="flex items-center gap-3 mb-4">
            <div className={`w-4 h-4 rounded-full ${health?.status === 'healthy' ? 'bg-green-500' : 'bg-yellow-500'}`} />
            <span className="text-xl text-white capitalize">{health?.status || 'Unknown'}</span>
          </div>
          <div className="space-y-2 text-gray-400">
            <p>Error Rate: {health?.metrics?.error_rate || 0}%</p>
            <p>Errors (1h): {health?.metrics?.errors_last_hour || 0}</p>
          </div>
        </div>
        <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
          <h3 className="text-lg font-medium text-white mb-4">Database</h3>
          <div className="space-y-2">
            {health?.database && Object.entries(health.database).map(([t, c]) => (
              <div key={t} className="flex justify-between">
                <span className="text-gray-400 capitalize">{t}</span>
                <span className="text-white">{c.toLocaleString()}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({ title, value, icon: Icon, color = 'text-blue-500' }) {
  return (
    <div className="bg-gray-800 rounded-xl border border-gray-700 p-4">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-gray-400">{title}</p>
          <p className="text-2xl font-bold text-white mt-1">{value}</p>
        </div>
        <Icon className={`w-8 h-8 ${color}`} />
      </div>
    </div>
  );
}

function UserModal({ user, onClose }) {
  const [usage, setUsage] = useState(null);

  useEffect(() => {
    adminFetch(`/admin/manage/users/${user.id}/usage`)
      .then(setUsage)
      .catch(() => {});
  }, [user.id]);

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-xl border border-gray-700 w-full max-w-lg">
        <div className="px-6 py-4 border-b border-gray-700 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-white">User Details</h3>
          <button onClick={onClose} className="p-1 hover:bg-gray-700 rounded"><X className="w-5 h-5 text-gray-400" /></button>
        </div>
        <div className="p-6 space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div><p className="text-sm text-gray-400">Email</p><p className="text-white">{user.email}</p></div>
            <div><p className="text-sm text-gray-400">Name</p><p className="text-white">{user.full_name || 'N/A'}</p></div>
            <div><p className="text-sm text-gray-400">Tier</p><p className="text-white capitalize">{user.subscription_tier || 'free'}</p></div>
            <div><p className="text-sm text-gray-400">Joined</p><p className="text-white">{new Date(user.created_at).toLocaleDateString()}</p></div>
          </div>
          {usage && (
            <div>
              <h4 className="text-white font-medium mb-2">Usage</h4>
              <div className="grid grid-cols-2 gap-2">
                {Object.entries(usage.usage || {}).map(([k, v]) => (
                  <div key={k} className="bg-gray-700 rounded p-2">
                    <p className="text-xs text-gray-400 capitalize">{k.replace(/_/g, ' ')}</p>
                    <p className="text-white">{v.used} / {v.limit === -1 ? '∞' : v.limit}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
