import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Users, Settings, BarChart3, Shield, Bell, Activity,
  Plus, Search, RefreshCw, CheckCircle, XCircle, Eye,
  DollarSign, Server, Zap, X, Edit, Trash2, Mail,
  AlertTriangle, Info, LogOut, Home
} from 'lucide-react';
import toast from 'react-hot-toast';

// Use base URL without /api/v1 suffix
const API_BASE = (import.meta.env.VITE_API_URL || 'https://ai-content-platform-kpc2.onrender.com').replace(/\/api\/v1\/?$/, '');

const adminFetch = async (endpoint, options = {}) => {
  const token = localStorage.getItem('admin_token');
  if (!token) throw new Error('Not authenticated');
  
  const res = await fetch(`${API_BASE}/api/v1${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
      ...options.headers
    }
  });
  
  if (res.status === 401) {
    localStorage.removeItem('admin_token');
    localStorage.removeItem('admin_user');
    window.location.href = '/admin/login';
    throw new Error('Session expired');
  }
  
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request failed' }));
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
  const [announcements, setAnnouncements] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedUser, setSelectedUser] = useState(null);
  const [adminUser, setAdminUser] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const token = localStorage.getItem('admin_token');
    const user = localStorage.getItem('admin_user');
    if (!token) { navigate('/admin/login'); return; }
    if (user) { try { setAdminUser(JSON.parse(user)); } catch (e) {} }
    loadData();
  }, [navigate]);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const results = await Promise.allSettled([
        adminFetch('/admin/stats'),
        adminFetch('/admin/manage/health'),
        adminFetch('/admin/manage/features'),
        adminFetch('/admin/users?per_page=100'),
        adminFetch('/admin/manage/tier-limits'),
        adminFetch('/admin/manage/announcements')
      ]);
      
      // Log results for debugging
      console.log('Admin API Results:', results.map((r, i) => ({
        endpoint: ['/admin/stats', '/admin/manage/health', '/admin/manage/features', '/admin/users', '/admin/manage/tier-limits', '/admin/manage/announcements'][i],
        status: r.status,
        value: r.status === 'fulfilled' ? r.value : null,
        error: r.status === 'rejected' ? r.reason?.message : null
      })));
      
      // Show errors for failed requests
      results.forEach((r, i) => {
        if (r.status === 'rejected') {
          const endpoints = ['stats', 'health', 'features', 'users', 'tier-limits', 'announcements'];
          console.error(`Failed to load ${endpoints[i]}:`, r.reason);
        }
      });
      
      setStats(results[0].status === 'fulfilled' ? results[0].value : null);
      setHealth(results[1].status === 'fulfilled' ? results[1].value : { status: 'unknown' });
      setFeatures(results[2].status === 'fulfilled' ? results[2].value : []);
      setUsers(results[3].status === 'fulfilled' ? (results[3].value.users || []) : []);
      setTierLimits(results[4].status === 'fulfilled' ? results[4].value : null);
      setAnnouncements(results[5].status === 'fulfilled' ? results[5].value : []);
    } catch (err) {
      console.error('Load data error:', err);
      toast.error('Failed to load some data');
    }
    setLoading(false);
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('admin_token');
    localStorage.removeItem('admin_user');
    navigate('/admin/login');
  };

  const tabs = [
    { id: 'overview', label: 'Overview', icon: BarChart3 },
    { id: 'users', label: 'Users', icon: Users },
    { id: 'features', label: 'Features', icon: Settings },
    { id: 'tiers', label: 'Tier Limits', icon: DollarSign },
    { id: 'announcements', label: 'Announcements', icon: Bell },
    { id: 'system', label: 'System', icon: Server },
  ];

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <RefreshCw className="w-8 h-8 text-blue-500 animate-spin" />
          <p className="text-white">Loading admin dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900">
      <header className="bg-gray-800 border-b border-gray-700 px-6 py-4 sticky top-0 z-40">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Shield className="w-8 h-8 text-blue-500" />
            <div>
              <h1 className="text-xl font-bold text-white">Admin Dashboard</h1>
              <p className="text-xs text-gray-400">AI Content Platform</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            {health && (
              <div className="flex items-center gap-2 px-3 py-1 bg-gray-700 rounded-full">
                <div className={`w-2 h-2 rounded-full ${health.status === 'healthy' ? 'bg-green-500' : health.status === 'degraded' ? 'bg-yellow-500' : 'bg-red-500'}`} />
                <span className="text-xs text-gray-300 capitalize">{health.status}</span>
              </div>
            )}
            <button onClick={loadData} className="p-2 hover:bg-gray-700 rounded-lg" title="Refresh">
              <RefreshCw className="w-5 h-5 text-gray-400" />
            </button>
            <a href="/" className="p-2 hover:bg-gray-700 rounded-lg" title="Main app">
              <Home className="w-5 h-5 text-gray-400" />
            </a>
            <div className="flex items-center gap-3 pl-4 border-l border-gray-700">
              <div className="text-right">
                <p className="text-sm text-white">{adminUser?.name || 'Admin'}</p>
                <p className="text-xs text-gray-400">{adminUser?.role || 'admin'}</p>
              </div>
              <button onClick={handleLogout} className="p-2 hover:bg-red-500/20 rounded-lg" title="Logout">
                <LogOut className="w-5 h-5 text-gray-400 hover:text-red-400" />
              </button>
            </div>
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
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${activeTab === tab.id ? 'bg-blue-600 text-white' : 'text-gray-400 hover:bg-gray-700 hover:text-white'}`}
                >
                  <Icon className="w-5 h-5" />
                  {tab.label}
                </button>
              );
            })}
          </nav>
          <div className="p-4 border-t border-gray-700 mt-4">
            <h4 className="text-xs font-medium text-gray-500 uppercase mb-3">Quick Stats</h4>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between"><span className="text-gray-400">Users</span><span className="text-white font-medium">{stats?.total_users || 0}</span></div>
              <div className="flex justify-between"><span className="text-gray-400">Active (24h)</span><span className="text-green-400 font-medium">{stats?.active_users_24h || 0}</span></div>
              <div className="flex justify-between"><span className="text-gray-400">Content</span><span className="text-white font-medium">{stats?.total_content || 0}</span></div>
            </div>
          </div>
        </aside>

        <main className="flex-1 p-6">
          {activeTab === 'overview' && <OverviewTab stats={stats} health={health} users={users} />}
          {activeTab === 'users' && <UsersTab users={users} searchQuery={searchQuery} setSearchQuery={setSearchQuery} onRefresh={loadData} selectedUser={selectedUser} setSelectedUser={setSelectedUser} />}
          {activeTab === 'features' && <FeaturesTab features={features} onRefresh={loadData} />}
          {activeTab === 'tiers' && <TierLimitsTab limits={tierLimits} onRefresh={loadData} />}
          {activeTab === 'announcements' && <AnnouncementsTab announcements={announcements} onRefresh={loadData} />}
          {activeTab === 'system' && <SystemTab health={health} />}
        </main>
      </div>
    </div>
  );
}

function OverviewTab({ stats, health, users }) {
  const recentUsers = users?.slice(0, 5) || [];
  
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-white">Platform Overview</h2>
      
      <div className="grid grid-cols-4 gap-4">
        <StatCard title="Total Users" value={stats?.total_users || 0} icon={Users} subtitle={`+${stats?.signups_today || 0} today`} />
        <StatCard title="Active (24h)" value={stats?.active_users_24h || 0} icon={Activity} color="text-green-500" subtitle={`${stats?.active_users_7d || 0} this week`} />
        <StatCard title="Total Content" value={stats?.total_content || 0} icon={Zap} color="text-blue-500" subtitle={`${stats?.total_videos || 0} videos`} />
        <StatCard title="Revenue" value={`$${(stats?.total_revenue || 0).toLocaleString()}`} icon={DollarSign} color="text-yellow-500" subtitle="All time" />
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
          <h3 className="text-lg font-semibold text-white mb-4">System Status</h3>
          <div className="flex items-center gap-3 mb-4">
            <div className={`w-4 h-4 rounded-full ${health?.status === 'healthy' ? 'bg-green-500 animate-pulse' : health?.status === 'degraded' ? 'bg-yellow-500' : 'bg-red-500'}`} />
            <span className="text-xl text-white capitalize">{health?.status || 'Unknown'}</span>
          </div>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div className="bg-gray-700/50 rounded-lg p-3"><p className="text-gray-400">Error Rate</p><p className="text-white text-lg font-medium">{health?.metrics?.error_rate || 0}%</p></div>
            <div className="bg-gray-700/50 rounded-lg p-3"><p className="text-gray-400">Errors (1h)</p><p className="text-white text-lg font-medium">{health?.metrics?.errors_last_hour || 0}</p></div>
          </div>
        </div>

        <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
          <h3 className="text-lg font-semibold text-white mb-4">Users by Tier</h3>
          <div className="space-y-3">
            {['free', 'creator', 'pro', 'agency'].map(tier => {
              const count = stats?.users_by_tier?.[tier] || 0;
              const total = stats?.total_users || 1;
              const pct = Math.round((count / total) * 100);
              return (
                <div key={tier}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-gray-400 capitalize">{tier}</span>
                    <span className="text-white">{count} ({pct}%)</span>
                  </div>
                  <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                    <div className={`h-full rounded-full ${tier === 'agency' ? 'bg-purple-500' : tier === 'pro' ? 'bg-blue-500' : tier === 'creator' ? 'bg-green-500' : 'bg-gray-500'}`} style={{ width: `${pct}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
          <h3 className="text-lg font-semibold text-white mb-4">Recent Signups</h3>
          <div className="space-y-3">
            {recentUsers.length > 0 ? recentUsers.map(user => (
              <div key={user.id} className="flex items-center justify-between py-2 border-b border-gray-700 last:border-0">
                <div><p className="text-white">{user.full_name || user.email}</p><p className="text-xs text-gray-400">{user.email}</p></div>
                <span className={`px-2 py-1 text-xs rounded capitalize ${user.subscription_tier === 'pro' ? 'bg-blue-500/20 text-blue-400' : user.subscription_tier === 'creator' ? 'bg-green-500/20 text-green-400' : user.subscription_tier === 'agency' ? 'bg-purple-500/20 text-purple-400' : 'bg-gray-500/20 text-gray-400'}`}>{user.subscription_tier || 'free'}</span>
              </div>
            )) : <p className="text-gray-400">No users yet</p>}
          </div>
        </div>

        <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
          <h3 className="text-lg font-semibold text-white mb-4">Signup Trends</h3>
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center p-4 bg-gray-700/50 rounded-lg"><p className="text-3xl font-bold text-white">{stats?.signups_today || 0}</p><p className="text-sm text-gray-400">Today</p></div>
            <div className="text-center p-4 bg-gray-700/50 rounded-lg"><p className="text-3xl font-bold text-white">{stats?.signups_this_week || 0}</p><p className="text-sm text-gray-400">This Week</p></div>
            <div className="text-center p-4 bg-gray-700/50 rounded-lg"><p className="text-3xl font-bold text-white">{stats?.signups_this_month || 0}</p><p className="text-sm text-gray-400">This Month</p></div>
          </div>
        </div>
      </div>
    </div>
  );
}

function UsersTab({ users, searchQuery, setSearchQuery, onRefresh, selectedUser, setSelectedUser }) {
  const [actionLoading, setActionLoading] = useState(null);
  const [tierFilter, setTierFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');

  const handleAction = async (userId, action, data = {}) => {
    setActionLoading(userId);
    try {
      await adminFetch(`/admin/manage/users/${userId}/${action}`, { method: 'POST', body: JSON.stringify(data) });
      toast.success('Action completed');
      onRefresh();
    } catch (err) { toast.error(err.message); }
    setActionLoading(null);
  };

  const handleChangeTier = async (userId, currentTier) => {
    const tiers = ['free', 'creator', 'pro', 'agency'];
    const tier = prompt(`Change tier to (${tiers.join(', ')}):\nCurrent: ${currentTier || 'free'}`);
    if (!tier || !tiers.includes(tier.toLowerCase())) { if (tier) toast.error('Invalid tier'); return; }
    setActionLoading(userId);
    try {
      await adminFetch(`/admin/manage/users/${userId}/subscription/change-tier`, { method: 'POST', body: JSON.stringify({ new_tier: tier.toLowerCase(), duration_days: 365 }) });
      toast.success(`Tier changed to ${tier}`);
      onRefresh();
    } catch (err) { toast.error(err.message); }
    setActionLoading(null);
  };

  const handleAddUsage = async (userId) => {
    const type = prompt('Usage type (generations, images, videos):', 'generations');
    if (!type) return;
    const amount = prompt(`Amount of ${type} to add:`, '10');
    if (!amount || isNaN(parseInt(amount))) return;
    setActionLoading(userId);
    try {
      await adminFetch(`/admin/manage/users/${userId}/usage/add`, { method: 'POST', body: JSON.stringify({ usage_type: type, amount: parseInt(amount), reason: 'Admin granted' }) });
      toast.success(`Added ${amount} ${type}`);
      onRefresh();
    } catch (err) { toast.error(err.message); }
    setActionLoading(null);
  };

  const handleVerifyEmail = async (userId) => {
    setActionLoading(userId);
    try { await adminFetch(`/admin/manage/users/${userId}/verify-email`, { method: 'POST' }); toast.success('Email verified'); onRefresh(); } catch (err) { toast.error(err.message); }
    setActionLoading(null);
  };

  const handleResetPassword = async (userId, email) => {
    const pw = prompt(`New password for ${email} (min 8 chars):`);
    if (!pw || pw.length < 8) { if (pw) toast.error('Min 8 characters'); return; }
    setActionLoading(userId);
    try { await adminFetch(`/admin/manage/users/${userId}/reset-password`, { method: 'POST', body: JSON.stringify({ new_password: pw }) }); toast.success('Password reset'); } catch (err) { toast.error(err.message); }
    setActionLoading(null);
  };

  const filtered = users.filter(u => {
    const matchesSearch = u.email.toLowerCase().includes(searchQuery.toLowerCase()) || u.full_name?.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesTier = tierFilter === 'all' || (u.subscription_tier || 'free') === tierFilter;
    const matchesStatus = statusFilter === 'all' || (statusFilter === 'active' && u.is_active) || (statusFilter === 'suspended' && !u.is_active) || (statusFilter === 'unverified' && !u.is_verified);
    return matchesSearch && matchesTier && matchesStatus;
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div><h2 className="text-2xl font-bold text-white">User Management</h2><p className="text-sm text-gray-400">{users.length} total users</p></div>
        <div className="flex items-center gap-3">
          <select value={tierFilter} onChange={(e) => setTierFilter(e.target.value)} className="px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm">
            <option value="all">All Tiers</option><option value="free">Free</option><option value="creator">Creator</option><option value="pro">Pro</option><option value="agency">Agency</option>
          </select>
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white text-sm">
            <option value="all">All Status</option><option value="active">Active</option><option value="suspended">Suspended</option><option value="unverified">Unverified</option>
          </select>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
            <input type="text" placeholder="Search users..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="pl-10 pr-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white w-64" />
          </div>
        </div>
      </div>
      
      <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-700">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">User</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Status</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Tier</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Stats</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Joined</th>
                <th className="px-4 py-3 text-right text-sm font-medium text-gray-400">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {filtered.length === 0 ? (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-gray-400">No users found</td></tr>
              ) : filtered.map(user => (
                <tr key={user.id} className="hover:bg-gray-700/50">
                  <td className="px-4 py-3"><p className="text-white font-medium">{user.full_name || 'No name'}</p><p className="text-sm text-gray-400">{user.email}</p></td>
                  <td className="px-4 py-3">
                    <div className="flex flex-col gap-1">
                      {user.is_active ? <span className="inline-flex px-2 py-1 text-xs bg-green-500/20 text-green-400 rounded w-fit">Active</span> : <span className="inline-flex px-2 py-1 text-xs bg-red-500/20 text-red-400 rounded w-fit">Suspended</span>}
                      {!user.is_verified && <span className="inline-flex px-2 py-1 text-xs bg-yellow-500/20 text-yellow-400 rounded w-fit">Unverified</span>}
                    </div>
                  </td>
                  <td className="px-4 py-3"><span className={`px-2 py-1 text-xs rounded capitalize ${user.subscription_tier === 'agency' ? 'bg-purple-500/20 text-purple-400' : user.subscription_tier === 'pro' ? 'bg-blue-500/20 text-blue-400' : user.subscription_tier === 'creator' ? 'bg-green-500/20 text-green-400' : 'bg-gray-500/20 text-gray-400'}`}>{user.subscription_tier || 'free'}</span></td>
                  <td className="px-4 py-3 text-sm text-gray-400"><div>{user.brands_count || 0} brands</div><div>{user.content_count || 0} content</div></td>
                  <td className="px-4 py-3 text-sm text-gray-400">{user.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A'}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1">
                      {actionLoading === user.id ? <RefreshCw className="w-4 h-4 text-blue-400 animate-spin" /> : (
                        <>
                          <button onClick={() => setSelectedUser(user)} className="p-1.5 hover:bg-gray-600 rounded" title="View"><Eye className="w-4 h-4 text-gray-400" /></button>
                          <button onClick={() => handleChangeTier(user.id, user.subscription_tier)} className="p-1.5 hover:bg-gray-600 rounded" title="Change tier"><DollarSign className="w-4 h-4 text-gray-400" /></button>
                          <button onClick={() => handleAddUsage(user.id)} className="p-1.5 hover:bg-gray-600 rounded" title="Add usage"><Plus className="w-4 h-4 text-gray-400" /></button>
                          {!user.is_verified && <button onClick={() => handleVerifyEmail(user.id)} className="p-1.5 hover:bg-green-500/20 rounded" title="Verify email"><Mail className="w-4 h-4 text-green-400" /></button>}
                          <button onClick={() => handleResetPassword(user.id, user.email)} className="p-1.5 hover:bg-yellow-500/20 rounded" title="Reset password"><Edit className="w-4 h-4 text-yellow-400" /></button>
                          {user.is_active ? <button onClick={() => handleAction(user.id, 'suspend', { reason: 'Admin' })} className="p-1.5 hover:bg-red-500/20 rounded" title="Suspend"><XCircle className="w-4 h-4 text-red-400" /></button> : <button onClick={() => handleAction(user.id, 'unsuspend')} className="p-1.5 hover:bg-green-500/20 rounded" title="Reactivate"><CheckCircle className="w-4 h-4 text-green-400" /></button>}
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      {selectedUser && <UserModal user={selectedUser} onClose={() => setSelectedUser(null)} />}
    </div>
  );
}

function FeaturesTab({ features, onRefresh }) {
  const [updating, setUpdating] = useState(null);

  const handleToggle = async (feature) => {
    setUpdating(feature.key);
    try {
      await adminFetch(`/admin/manage/features/${feature.key}`, { method: 'PUT', body: JSON.stringify({ enabled: !feature.enabled }) });
      toast.success(`${feature.key.replace('feature_', '').replace(/_/g, ' ')} ${!feature.enabled ? 'enabled' : 'disabled'}`);
      onRefresh();
    } catch (err) { toast.error(err.message); }
    setUpdating(null);
  };

  const categories = [...new Set(features.map(f => f.category))];

  return (
    <div className="space-y-6">
      <div><h2 className="text-2xl font-bold text-white">Feature Flags</h2><p className="text-gray-400">Enable or disable platform features globally.</p></div>
      {categories.length === 0 ? (
        <div className="bg-gray-800 rounded-xl border border-gray-700 p-8 text-center"><Settings className="w-12 h-12 text-gray-600 mx-auto mb-4" /><p className="text-gray-400">No feature flags configured</p></div>
      ) : categories.map(cat => (
        <div key={cat} className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
          <div className="px-4 py-3 bg-gray-700 border-b border-gray-600"><h3 className="text-lg font-medium text-white capitalize">{cat}</h3></div>
          <div className="divide-y divide-gray-700">
            {features.filter(f => f.category === cat).map(feature => (
              <div key={feature.key} className="px-4 py-4 flex items-center justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <p className="text-white font-medium capitalize">{feature.key.replace('feature_', '').replace(/_/g, ' ')}</p>
                    {feature.overridden && <span className="px-1.5 py-0.5 text-xs bg-blue-500/20 text-blue-400 rounded">Modified</span>}
                  </div>
                  <p className="text-sm text-gray-400">{feature.description}</p>
                </div>
                <button onClick={() => handleToggle(feature)} disabled={updating === feature.key} className={`relative w-14 h-7 rounded-full transition-colors ${feature.enabled ? 'bg-blue-600' : 'bg-gray-600'} ${updating === feature.key ? 'opacity-50' : ''}`}>
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
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      await adminFetch(`/admin/manage/tier-limits/${editing}`, { method: 'PUT', body: JSON.stringify({ limits: values }) });
      toast.success(`${editing} limits updated`);
      setEditing(null);
      onRefresh();
    } catch (err) { toast.error(err.message); }
    setSaving(false);
  };

  if (!limits) return <div className="text-center py-12"><RefreshCw className="w-8 h-8 text-gray-400 mx-auto mb-4 animate-spin" /><p className="text-gray-400">Loading...</p></div>;

  const tiers = ['free', 'creator', 'pro', 'agency'];
  const keys = Object.keys(limits.free || {});

  return (
    <div className="space-y-6">
      <div><h2 className="text-2xl font-bold text-white">Tier Limits</h2><p className="text-gray-400">Configure usage limits for each subscription tier.</p></div>
      <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-700">
            <tr>
              <th className="px-4 py-3 text-left text-sm font-medium text-gray-400">Limit</th>
              {tiers.map(t => (
                <th key={t} className="px-4 py-3 text-center text-sm font-medium text-gray-400">
                  <div className="flex items-center justify-center gap-2"><span className="capitalize">{t}</span><button onClick={() => { setEditing(t); setValues(limits[t] || {}); }} className="p-1 hover:bg-gray-600 rounded"><Edit className="w-3 h-3" /></button></div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700">
            {keys.map(key => (
              <tr key={key}>
                <td className="px-4 py-3 text-white capitalize font-medium">{key.replace(/_/g, ' ')}</td>
                {tiers.map(t => (
                  <td key={t} className="px-4 py-3 text-center">
                    {editing === t ? <input type="number" value={values[key] ?? 0} onChange={(e) => setValues({ ...values, [key]: parseInt(e.target.value) || 0 })} className="w-24 px-2 py-1 bg-gray-700 border border-gray-600 rounded text-white text-center" /> : <span className={`text-gray-300 ${limits[t]?.[key] === -1 ? 'text-green-400' : ''}`}>{limits[t]?.[key] === -1 ? '∞' : (limits[t]?.[key] ?? 0)}</span>}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        {editing && (
          <div className="px-4 py-3 bg-gray-700 flex items-center justify-between border-t border-gray-600">
            <p className="text-sm text-gray-400">Editing <span className="text-white capitalize">{editing}</span> tier</p>
            <div className="flex gap-2">
              <button onClick={() => setEditing(null)} className="px-4 py-2 text-gray-400 hover:text-white" disabled={saving}>Cancel</button>
              <button onClick={handleSave} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2" disabled={saving}>{saving && <RefreshCw className="w-4 h-4 animate-spin" />}Save</button>
            </div>
          </div>
        )}
      </div>
      <p className="text-sm text-gray-500">Note: Use -1 for unlimited.</p>
    </div>
  );
}

function AnnouncementsTab({ announcements, onRefresh }) {
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ title: '', message: '', announcement_type: 'info' });
  const [saving, setSaving] = useState(false);

  const handleCreate = async () => {
    if (!form.title || !form.message) { toast.error('Title and message required'); return; }
    setSaving(true);
    try {
      await adminFetch('/admin/manage/announcements', { method: 'POST', body: JSON.stringify(form) });
      toast.success('Announcement created');
      setCreating(false);
      setForm({ title: '', message: '', announcement_type: 'info' });
      onRefresh();
    } catch (err) { toast.error(err.message); }
    setSaving(false);
  };

  const handleDelete = async (id) => {
    if (!confirm('Delete this announcement?')) return;
    try { await adminFetch(`/admin/manage/announcements/${id}`, { method: 'DELETE' }); toast.success('Deleted'); onRefresh(); } catch (err) { toast.error(err.message); }
  };

  const typeColors = { info: 'bg-blue-500/20 text-blue-400 border-blue-500/30', warning: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30', maintenance: 'bg-red-500/20 text-red-400 border-red-500/30' };
  const typeIcons = { info: Info, warning: AlertTriangle, maintenance: Server };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div><h2 className="text-2xl font-bold text-white">Announcements</h2><p className="text-gray-400">System-wide announcements.</p></div>
        <button onClick={() => setCreating(true)} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2"><Plus className="w-4 h-4" />New</button>
      </div>

      {creating && (
        <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
          <h3 className="text-lg font-medium text-white mb-4">Create Announcement</h3>
          <div className="space-y-4">
            <div><label className="block text-sm text-gray-400 mb-1">Type</label><select value={form.announcement_type} onChange={(e) => setForm({ ...form, announcement_type: e.target.value })} className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white"><option value="info">Info</option><option value="warning">Warning</option><option value="maintenance">Maintenance</option></select></div>
            <div><label className="block text-sm text-gray-400 mb-1">Title</label><input type="text" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white" placeholder="Title" /></div>
            <div><label className="block text-sm text-gray-400 mb-1">Message</label><textarea value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white h-24" placeholder="Message" /></div>
            <div className="flex justify-end gap-2">
              <button onClick={() => setCreating(false)} className="px-4 py-2 text-gray-400">Cancel</button>
              <button onClick={handleCreate} disabled={saving} className="px-4 py-2 bg-blue-600 text-white rounded-lg disabled:opacity-50 flex items-center gap-2">{saving && <RefreshCw className="w-4 h-4 animate-spin" />}Create</button>
            </div>
          </div>
        </div>
      )}

      <div className="space-y-4">
        {announcements.length === 0 ? (
          <div className="bg-gray-800 rounded-xl border border-gray-700 p-8 text-center"><Bell className="w-12 h-12 text-gray-600 mx-auto mb-4" /><p className="text-gray-400">No announcements</p></div>
        ) : announcements.map(ann => {
          const Icon = typeIcons[ann.type] || Info;
          return (
            <div key={ann.id} className={`rounded-xl border p-4 ${typeColors[ann.type] || typeColors.info}`}>
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-3"><Icon className="w-5 h-5 mt-0.5" /><div><h4 className="font-medium">{ann.title}</h4><p className="text-sm opacity-80 mt-1">{ann.message}</p><p className="text-xs opacity-60 mt-2">{ann.created_at ? new Date(ann.created_at).toLocaleString() : ''}</p></div></div>
                <button onClick={() => handleDelete(ann.id)} className="p-1 hover:bg-white/10 rounded"><Trash2 className="w-4 h-4" /></button>
              </div>
            </div>
          );
        })}
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
          <h3 className="text-lg font-medium text-white mb-4">Health Status</h3>
          <div className="flex items-center gap-3 mb-6">
            <div className={`w-5 h-5 rounded-full ${health?.status === 'healthy' ? 'bg-green-500 animate-pulse' : health?.status === 'degraded' ? 'bg-yellow-500' : 'bg-red-500'}`} />
            <span className="text-2xl text-white capitalize">{health?.status || 'Unknown'}</span>
          </div>
          <div className="space-y-3">
            <div className="flex justify-between py-2 border-b border-gray-700"><span className="text-gray-400">Error Rate</span><span className={`font-medium ${(health?.metrics?.error_rate || 0) > 5 ? 'text-red-400' : 'text-green-400'}`}>{health?.metrics?.error_rate || 0}%</span></div>
            <div className="flex justify-between py-2 border-b border-gray-700"><span className="text-gray-400">Errors (1h)</span><span className="text-white">{health?.metrics?.errors_last_hour || 0}</span></div>
            <div className="flex justify-between py-2 border-b border-gray-700"><span className="text-gray-400">Success (1h)</span><span className="text-green-400">{health?.metrics?.success_last_hour || 0}</span></div>
            <div className="flex justify-between py-2"><span className="text-gray-400">Pending Posts</span><span className="text-white">{health?.metrics?.pending_posts || 0}</span></div>
          </div>
        </div>

        <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
          <h3 className="text-lg font-medium text-white mb-4">Database</h3>
          <div className="space-y-3">
            {health?.database ? Object.entries(health.database).map(([t, c]) => (
              <div key={t} className="flex justify-between py-2 border-b border-gray-700 last:border-0"><span className="text-gray-400 capitalize">{t.replace(/_/g, ' ')}</span><span className="text-white font-medium">{c.toLocaleString()}</span></div>
            )) : <p className="text-gray-400">No data</p>}
          </div>
        </div>
      </div>

      <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
        <h3 className="text-lg font-medium text-white mb-4">System Flags</h3>
        <div className="grid grid-cols-2 gap-4">
          <div className="flex items-center justify-between p-3 bg-gray-700/50 rounded-lg"><span className="text-gray-300">Maintenance Mode</span><span className={`px-2 py-1 text-xs rounded ${health?.flags?.maintenance_mode ? 'bg-red-500/20 text-red-400' : 'bg-green-500/20 text-green-400'}`}>{health?.flags?.maintenance_mode ? 'ON' : 'OFF'}</span></div>
          <div className="flex items-center justify-between p-3 bg-gray-700/50 rounded-lg"><span className="text-gray-300">Registration</span><span className={`px-2 py-1 text-xs rounded ${health?.flags?.registration_enabled ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>{health?.flags?.registration_enabled ? 'ENABLED' : 'DISABLED'}</span></div>
        </div>
      </div>
    </div>
  );
}

function StatCard({ title, value, icon: Icon, color = 'text-blue-500', subtitle }) {
  return (
    <div className="bg-gray-800 rounded-xl border border-gray-700 p-4">
      <div className="flex items-start justify-between">
        <div><p className="text-sm text-gray-400">{title}</p><p className="text-2xl font-bold text-white mt-1">{value}</p>{subtitle && <p className="text-xs text-gray-500 mt-1">{subtitle}</p>}</div>
        <Icon className={`w-8 h-8 ${color}`} />
      </div>
    </div>
  );
}

function UserModal({ user, onClose }) {
  const [usage, setUsage] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    adminFetch(`/admin/manage/users/${user.id}/usage`).then(setUsage).catch(() => setUsage(null)).finally(() => setLoading(false));
  }, [user.id]);

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-800 rounded-xl border border-gray-700 w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="px-6 py-4 border-b border-gray-700 flex items-center justify-between sticky top-0 bg-gray-800"><h3 className="text-lg font-semibold text-white">User Details</h3><button onClick={onClose} className="p-1 hover:bg-gray-700 rounded"><X className="w-5 h-5 text-gray-400" /></button></div>
        <div className="p-6 space-y-6">
          <div className="grid grid-cols-2 gap-4">
            <div><p className="text-sm text-gray-400">Email</p><p className="text-white">{user.email}</p></div>
            <div><p className="text-sm text-gray-400">Name</p><p className="text-white">{user.full_name || 'Not set'}</p></div>
            <div><p className="text-sm text-gray-400">Tier</p><p className="text-white capitalize">{user.subscription_tier || 'free'}</p></div>
            <div><p className="text-sm text-gray-400">Status</p><p className={user.is_active ? 'text-green-400' : 'text-red-400'}>{user.is_active ? 'Active' : 'Suspended'}</p></div>
            <div><p className="text-sm text-gray-400">Verified</p><p className={user.is_verified ? 'text-green-400' : 'text-yellow-400'}>{user.is_verified ? 'Yes' : 'No'}</p></div>
            <div><p className="text-sm text-gray-400">Joined</p><p className="text-white">{user.created_at ? new Date(user.created_at).toLocaleDateString() : 'Unknown'}</p></div>
          </div>
          <div>
            <h4 className="text-white font-medium mb-3">Usage</h4>
            {loading ? <div className="flex justify-center py-4"><RefreshCw className="w-5 h-5 text-gray-400 animate-spin" /></div> : usage ? (
              <div className="grid grid-cols-2 gap-2">
                {Object.entries(usage.usage || {}).map(([key, val]) => (
                  <div key={key} className="bg-gray-700/50 rounded-lg p-3">
                    <p className="text-xs text-gray-400 capitalize">{key.replace(/_/g, ' ')}</p>
                    <p className="text-white">{val.used} / {val.limit === -1 ? '∞' : val.limit}</p>
                  </div>
                ))}
              </div>
            ) : <p className="text-gray-400 text-center py-4">Unable to load</p>}
          </div>
        </div>
      </div>
    </div>
  );
}
