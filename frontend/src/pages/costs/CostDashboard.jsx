import { useState, useEffect } from 'react';
import { DollarSign, TrendingUp, Zap, AlertTriangle, BarChart3, ArrowUp, Clock } from 'lucide-react';
import api from '../../services/api';
import { Card, LoadingState, Badge, Spinner } from '../../components/ui';
import toast from 'react-hot-toast';

export default function CostDashboard() {
  const [loading, setLoading] = useState(true);
  const [usage, setUsage] = useState(null);
  const [history, setHistory] = useState(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [usageRes, historyRes] = await Promise.all([
        api.get('/costs/my-usage'),
        api.get('/costs/my-history?days=14')
      ]);
      setUsage(usageRes.data);
      setHistory(historyRes.data);
    } catch (err) {
      toast.error('Failed to load usage data');
    }
    setLoading(false);
  };

  if (loading) return <LoadingState message="Loading usage data..." />;

  const usagePercent = usage ? (usage.daily_cost_used / usage.daily_cost_limit) * 100 : 0;
  const monthlyPercent = usage ? (usage.monthly_cost_used / usage.monthly_cost_limit) * 100 : 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-pearl">Usage & Costs</h1>
          <p className="text-silver">Monitor your AI generation usage and costs</p>
        </div>
        <Badge variant={usage?.can_generate ? 'success' : 'error'} className="text-sm px-3 py-1">
          {usage?.can_generate ? '✓ Can Generate' : '⚠ Limit Reached'}
        </Badge>
      </div>

      {/* Quota Warning */}
      {!usage?.can_generate && (
        <Card className="p-4 border-l-4 border-yellow-500 bg-yellow-500/10">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-yellow-500 mt-0.5" />
            <div>
              <p className="font-medium text-pearl">Usage limit reached</p>
              <p className="text-sm text-silver">
                You've reached your daily generation limit. Upgrade your plan for more capacity.
              </p>
            </div>
          </div>
        </Card>
      )}

      {/* Current Plan */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-lg bg-accent/20 flex items-center justify-center">
              <Zap className="w-6 h-6 text-accent" />
            </div>
            <div>
              <p className="text-sm text-silver">Current Plan</p>
              <p className="text-xl font-bold text-pearl capitalize">{usage?.tier || 'Free'}</p>
            </div>
          </div>
          {usage?.upgrade_benefits && (
            <a href="/pricing" className="btn-primary text-sm">
              Upgrade to {usage.upgrade_benefits.next_tier}
            </a>
          )}
        </div>
        
        {usage?.upgrade_benefits && (
          <div className="mt-4 p-4 bg-slate/50 rounded-lg">
            <p className="text-sm font-medium text-pearl mb-2">
              Upgrade to {usage.upgrade_benefits.next_tier} ({usage.upgrade_benefits.price}):
            </p>
            <ul className="text-sm text-silver space-y-1">
              {usage.upgrade_benefits.benefits.map((benefit, i) => (
                <li key={i} className="flex items-center gap-2">
                  <span className="text-green-400">✓</span> {benefit}
                </li>
              ))}
            </ul>
          </div>
        )}
      </Card>

      {/* Usage Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="p-5">
          <p className="text-sm text-silver mb-1">Generations Today</p>
          <p className="text-2xl font-bold text-pearl">
            {usage?.daily_generations_used || 0}
            <span className="text-sm text-silver font-normal"> / {usage?.daily_generations_limit}</span>
          </p>
          <div className="mt-2 h-2 bg-slate rounded-full overflow-hidden">
            <div 
              className="h-full bg-accent rounded-full transition-all"
              style={{ width: `${Math.min((usage?.daily_generations_used / usage?.daily_generations_limit) * 100, 100)}%` }}
            />
          </div>
        </Card>
        
        <Card className="p-5">
          <p className="text-sm text-silver mb-1">Images Today</p>
          <p className="text-2xl font-bold text-pearl">
            {usage?.daily_images_used || 0}
            <span className="text-sm text-silver font-normal"> / {usage?.daily_images_limit}</span>
          </p>
          <div className="mt-2 h-2 bg-slate rounded-full overflow-hidden">
            <div 
              className="h-full bg-blue-500 rounded-full transition-all"
              style={{ width: `${Math.min((usage?.daily_images_used / usage?.daily_images_limit) * 100, 100)}%` }}
            />
          </div>
        </Card>
        
        <Card className="p-5">
          <p className="text-sm text-silver mb-1">Videos Today</p>
          <p className="text-2xl font-bold text-pearl">
            {usage?.daily_videos_used || 0}
            <span className="text-sm text-silver font-normal"> / {usage?.daily_videos_limit}</span>
          </p>
          <div className="mt-2 h-2 bg-slate rounded-full overflow-hidden">
            <div 
              className="h-full bg-purple-500 rounded-full transition-all"
              style={{ width: `${Math.min((usage?.daily_videos_used / usage?.daily_videos_limit) * 100, 100)}%` }}
            />
          </div>
        </Card>
        
        <Card className="p-5">
          <p className="text-sm text-silver mb-1">Daily Cost</p>
          <p className="text-2xl font-bold text-accent">
            ${usage?.daily_cost_used?.toFixed(2) || '0.00'}
            <span className="text-sm text-silver font-normal"> / ${usage?.daily_cost_limit}</span>
          </p>
          <div className="mt-2 h-2 bg-slate rounded-full overflow-hidden">
            <div 
              className={`h-full rounded-full transition-all ${usagePercent > 80 ? 'bg-red-500' : 'bg-green-500'}`}
              style={{ width: `${Math.min(usagePercent, 100)}%` }}
            />
          </div>
        </Card>
      </div>

      {/* Monthly Overview */}
      <Card className="p-6">
        <h2 className="text-lg font-semibold text-pearl mb-4 flex items-center gap-2">
          <BarChart3 className="w-5 h-5" />
          Monthly Overview
        </h2>
        
        <div className="grid md:grid-cols-2 gap-6">
          <div>
            <p className="text-sm text-silver mb-2">Monthly Cost Usage</p>
            <div className="flex items-end gap-2 mb-2">
              <span className="text-3xl font-bold text-pearl">${usage?.monthly_cost_used?.toFixed(2)}</span>
              <span className="text-silver">/ ${usage?.monthly_cost_limit}</span>
            </div>
            <div className="h-3 bg-slate rounded-full overflow-hidden">
              <div 
                className={`h-full rounded-full transition-all ${monthlyPercent > 80 ? 'bg-yellow-500' : 'bg-accent'}`}
                style={{ width: `${Math.min(monthlyPercent, 100)}%` }}
              />
            </div>
            <p className="text-xs text-silver mt-1">{monthlyPercent.toFixed(1)}% of monthly limit used</p>
          </div>
          
          <div className="space-y-3">
            <div className="flex justify-between items-center p-3 bg-slate/50 rounded-lg">
              <span className="text-silver">Total Generations (30d)</span>
              <span className="font-semibold text-pearl">{history?.total_generations || 0}</span>
            </div>
            <div className="flex justify-between items-center p-3 bg-slate/50 rounded-lg">
              <span className="text-silver">Total Images (30d)</span>
              <span className="font-semibold text-pearl">{history?.total_images || 0}</span>
            </div>
            <div className="flex justify-between items-center p-3 bg-slate/50 rounded-lg">
              <span className="text-silver">Total Videos (30d)</span>
              <span className="font-semibold text-pearl">{history?.total_videos || 0}</span>
            </div>
          </div>
        </div>
      </Card>

      {/* Usage History Chart */}
      <Card className="p-6">
        <h2 className="text-lg font-semibold text-pearl mb-4 flex items-center gap-2">
          <TrendingUp className="w-5 h-5" />
          Last 14 Days
        </h2>
        
        <div className="h-48 flex items-end gap-1">
          {history?.daily_usage?.slice(0, 14).reverse().map((day, i) => {
            const maxGen = Math.max(...history.daily_usage.map(d => d.generations), 1);
            const height = (day.generations / maxGen) * 100;
            
            return (
              <div key={i} className="flex-1 flex flex-col items-center gap-1">
                <div 
                  className="w-full bg-accent/80 rounded-t hover:bg-accent transition-colors cursor-pointer group relative"
                  style={{ height: `${Math.max(height, 4)}%` }}
                >
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-charcoal rounded text-xs text-pearl opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-10">
                    {day.generations} generations<br />
                    ${day.cost.toFixed(3)}
                  </div>
                </div>
                <span className="text-xs text-silver -rotate-45 origin-center">
                  {new Date(day.date).toLocaleDateString('en', { month: 'short', day: 'numeric' })}
                </span>
              </div>
            );
          })}
        </div>
      </Card>

      {/* Cost Savings Tips */}
      <Card className="p-6">
        <h2 className="text-lg font-semibold text-pearl mb-4">💡 Cost Optimization Tips</h2>
        <div className="grid md:grid-cols-2 gap-4">
          <div className="p-4 bg-slate/50 rounded-lg">
            <h3 className="font-medium text-pearl mb-2">Use Batch Generation</h3>
            <p className="text-sm text-silver">
              Generate multiple variations at once instead of one at a time. 
              Our batch processing saves up to 50% on API costs.
            </p>
          </div>
          <div className="p-4 bg-slate/50 rounded-lg">
            <h3 className="font-medium text-pearl mb-2">Reuse Brand Voice</h3>
            <p className="text-sm text-silver">
              Train your brand voice once, then use it for all content. 
              This reduces the tokens needed for each generation.
            </p>
          </div>
          <div className="p-4 bg-slate/50 rounded-lg">
            <h3 className="font-medium text-pearl mb-2">Schedule Off-Peak</h3>
            <p className="text-sm text-silver">
              Non-urgent content can be queued for batch processing 
              during off-peak hours for additional savings.
            </p>
          </div>
          <div className="p-4 bg-slate/50 rounded-lg">
            <h3 className="font-medium text-pearl mb-2">Use Templates</h3>
            <p className="text-sm text-silver">
              Save successful content as templates. 
              Generating variations from templates uses fewer tokens.
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
}
