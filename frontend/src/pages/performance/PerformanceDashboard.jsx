import { useState, useEffect } from 'react';
import { 
  TrendingUp, TrendingDown, Heart, MessageCircle, Share2, Eye,
  Users, BarChart2, RefreshCw, Clock, Zap, Target, ArrowUp,
  ArrowDown, Minus, Instagram, Twitter, Linkedin, Facebook,
  Lightbulb, ExternalLink, Calendar
} from 'lucide-react';
import api from '../../services/api';
import { Card, LoadingState, Badge, Spinner } from '../../components/ui';
import toast from 'react-hot-toast';

// Platform icons
const platformIcons = {
  instagram: Instagram,
  twitter: Twitter,
  linkedin: Linkedin,
  facebook: Facebook
};

// Platform colors
const platformColors = {
  instagram: 'from-purple-500 to-pink-500',
  twitter: 'from-blue-400 to-blue-500',
  linkedin: 'from-blue-600 to-blue-700',
  facebook: 'from-blue-500 to-blue-600',
  tiktok: 'from-gray-800 to-black'
};

export default function PerformanceDashboard() {
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [period, setPeriod] = useState(30);
  const [overview, setOverview] = useState(null);
  const [platforms, setPlatforms] = useState(null);
  const [topPosts, setTopPosts] = useState([]);
  const [trends, setTrends] = useState([]);
  const [insights, setInsights] = useState([]);
  const [bestTimes, setBestTimes] = useState(null);

  useEffect(() => {
    fetchAllData();
  }, [period]);

  const fetchAllData = async () => {
    setLoading(true);
    try {
      const [overviewRes, platformsRes, topPostsRes, trendsRes, insightsRes, bestTimesRes] = await Promise.all([
        api.get(`/performance/overview?days=${period}`),
        api.get(`/performance/platforms?days=${period}`),
        api.get(`/performance/top-posts?days=${period}&limit=5`),
        api.get(`/performance/trends?days=${period}&granularity=day`),
        api.get('/performance/insights'),
        api.get('/performance/best-times')
      ]);
      
      setOverview(overviewRes.data);
      setPlatforms(platformsRes.data.platforms);
      setTopPosts(topPostsRes.data.posts);
      setTrends(trendsRes.data.trends);
      setInsights(insightsRes.data.insights);
      setBestTimes(bestTimesRes.data);
    } catch (err) {
      toast.error('Failed to load performance data');
    }
    setLoading(false);
  };

  const handleSync = async () => {
    setSyncing(true);
    try {
      const res = await api.post('/performance/sync');
      toast.success(`Synced ${res.data.result.synced} posts`);
      fetchAllData();
    } catch (err) {
      toast.error('Failed to sync metrics');
    }
    setSyncing(false);
  };

  const formatNumber = (num) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  const getTrendIcon = (change) => {
    if (change > 5) return <ArrowUp className="w-4 h-4 text-green-500" />;
    if (change < -5) return <ArrowDown className="w-4 h-4 text-red-500" />;
    return <Minus className="w-4 h-4 text-gray-500" />;
  };

  if (loading) return <LoadingState message="Loading performance data..." />;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-pearl flex items-center gap-2">
            <BarChart2 className="w-7 h-7 text-accent" />
            Performance Dashboard
          </h1>
          <p className="text-silver">Track your content performance across platforms</p>
        </div>
        
        <div className="flex items-center gap-3">
          {/* Period Selector */}
          <select
            value={period}
            onChange={(e) => setPeriod(Number(e.target.value))}
            className="px-4 py-2 rounded-lg bg-slate border border-graphite text-pearl focus:border-accent focus:outline-none"
          >
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
          </select>
          
          <button
            onClick={handleSync}
            disabled={syncing}
            className="btn-primary px-4 py-2 flex items-center gap-2"
          >
            {syncing ? <Spinner size="sm" /> : <RefreshCw className="w-4 h-4" />}
            Sync
          </button>
        </div>
      </div>

      {/* Key Metrics */}
      {overview && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <MetricCard
            title="Total Engagements"
            value={formatNumber(overview.metrics.total_engagements)}
            change={overview.trends.engagement_change_percent}
            icon={Heart}
            color="text-pink-500"
          />
          <MetricCard
            title="Avg Engagement Rate"
            value={`${overview.averages.engagement_rate}%`}
            icon={Target}
            color="text-accent"
          />
          <MetricCard
            title="Total Reach"
            value={formatNumber(overview.metrics.reach)}
            icon={Users}
            color="text-blue-500"
          />
          <MetricCard
            title="Posts Published"
            value={overview.total_posts}
            change={overview.trends.post_count_change}
            icon={Zap}
            color="text-yellow-500"
          />
        </div>
      )}

      {/* Insights */}
      {insights.length > 0 && (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {insights.map((insight, i) => (
            <InsightCard key={i} insight={insight} />
          ))}
        </div>
      )}

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Engagement Breakdown */}
        <Card className="lg:col-span-2 p-6">
          <h2 className="text-lg font-semibold text-pearl mb-4">Engagement Breakdown</h2>
          {overview && (
            <div className="grid grid-cols-3 gap-4">
              <div className="text-center p-4 bg-slate rounded-lg">
                <Heart className="w-8 h-8 text-pink-500 mx-auto mb-2" />
                <p className="text-2xl font-bold text-pearl">{formatNumber(overview.metrics.likes)}</p>
                <p className="text-sm text-silver">Likes</p>
                <p className="text-xs text-silver mt-1">
                  ~{overview.averages.likes_per_post} per post
                </p>
              </div>
              <div className="text-center p-4 bg-slate rounded-lg">
                <MessageCircle className="w-8 h-8 text-blue-500 mx-auto mb-2" />
                <p className="text-2xl font-bold text-pearl">{formatNumber(overview.metrics.comments)}</p>
                <p className="text-sm text-silver">Comments</p>
                <p className="text-xs text-silver mt-1">
                  ~{overview.averages.comments_per_post} per post
                </p>
              </div>
              <div className="text-center p-4 bg-slate rounded-lg">
                <Share2 className="w-8 h-8 text-green-500 mx-auto mb-2" />
                <p className="text-2xl font-bold text-pearl">{formatNumber(overview.metrics.shares)}</p>
                <p className="text-sm text-silver">Shares</p>
              </div>
            </div>
          )}
        </Card>

        {/* Best Times */}
        <Card className="p-6">
          <h2 className="text-lg font-semibold text-pearl mb-4 flex items-center gap-2">
            <Clock className="w-5 h-5 text-accent" />
            Best Posting Times
          </h2>
          {bestTimes && (
            <div className="space-y-4">
              <div>
                <p className="text-sm text-silver mb-2">Best Days</p>
                <div className="space-y-2">
                  {bestTimes.best_days?.slice(0, 3).map((day, i) => (
                    <div key={i} className="flex justify-between items-center">
                      <span className="text-pearl">{day.day}</span>
                      <Badge variant={i === 0 ? 'success' : 'default'}>
                        {Math.round(day.avg_engagement)} avg
                      </Badge>
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <p className="text-sm text-silver mb-2">Best Hours</p>
                <div className="flex flex-wrap gap-2">
                  {bestTimes.best_hours?.slice(0, 5).map((hour, i) => (
                    <span 
                      key={i}
                      className={`px-3 py-1 rounded-full text-sm ${
                        i === 0 ? 'bg-accent text-midnight' : 'bg-slate text-silver'
                      }`}
                    >
                      {hour.hour}:00
                    </span>
                  ))}
                </div>
              </div>
              {bestTimes.recommendation && (
                <p className="text-sm text-silver italic mt-4">
                  💡 {bestTimes.recommendation}
                </p>
              )}
            </div>
          )}
        </Card>
      </div>

      {/* Platform Performance */}
      {platforms && Object.keys(platforms).length > 0 && (
        <Card className="p-6">
          <h2 className="text-lg font-semibold text-pearl mb-4">Performance by Platform</h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
            {Object.entries(platforms).map(([platform, data]) => {
              const Icon = platformIcons[platform] || BarChart2;
              const gradient = platformColors[platform] || 'from-gray-500 to-gray-600';
              
              return (
                <div key={platform} className="p-4 bg-slate rounded-xl">
                  <div className="flex items-center gap-3 mb-3">
                    <div className={`w-10 h-10 rounded-lg bg-gradient-to-r ${gradient} flex items-center justify-center`}>
                      <Icon className="w-5 h-5 text-white" />
                    </div>
                    <div>
                      <p className="text-pearl font-medium capitalize">{platform}</p>
                      <p className="text-xs text-silver">{data.posts} posts</p>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-sm text-silver">Engagements</span>
                      <span className="text-pearl font-medium">{formatNumber(data.total_engagements)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-silver">Eng. Rate</span>
                      <span className="text-accent font-medium">{data.engagement_rate}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-silver">Reach</span>
                      <span className="text-pearl">{formatNumber(data.reach)}</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {/* Engagement Trend Chart */}
      {trends.length > 0 && (
        <Card className="p-6">
          <h2 className="text-lg font-semibold text-pearl mb-4">Engagement Trend</h2>
          <div className="h-64">
            <TrendChart data={trends} />
          </div>
        </Card>
      )}

      {/* Top Performing Posts */}
      {topPosts.length > 0 && (
        <Card className="p-6">
          <h2 className="text-lg font-semibold text-pearl mb-4">Top Performing Posts</h2>
          <div className="space-y-4">
            {topPosts.map((post, i) => {
              const Icon = platformIcons[post.platform] || BarChart2;
              
              return (
                <div 
                  key={post.id}
                  className="flex items-start gap-4 p-4 bg-slate rounded-lg hover:bg-slate/80 transition-colors"
                >
                  <div className="flex items-center justify-center w-8 h-8 rounded-full bg-charcoal text-pearl font-bold">
                    {i + 1}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <Icon className="w-4 h-4 text-silver" />
                      <span className="text-xs text-silver capitalize">{post.platform}</span>
                      <span className="text-xs text-silver">•</span>
                      <span className="text-xs text-silver">
                        {new Date(post.published_at).toLocaleDateString()}
                      </span>
                    </div>
                    <p className="text-pearl truncate">{post.caption_preview}</p>
                    <div className="flex gap-4 mt-2">
                      <span className="text-sm text-silver flex items-center gap-1">
                        <Heart className="w-3 h-3" /> {post.metrics.likes}
                      </span>
                      <span className="text-sm text-silver flex items-center gap-1">
                        <MessageCircle className="w-3 h-3" /> {post.metrics.comments}
                      </span>
                      <span className="text-sm text-silver flex items-center gap-1">
                        <Share2 className="w-3 h-3" /> {post.metrics.shares}
                      </span>
                    </div>
                  </div>
                  {post.post_url && (
                    <a 
                      href={post.post_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-2 hover:bg-charcoal rounded-lg transition-colors"
                    >
                      <ExternalLink className="w-4 h-4 text-silver" />
                    </a>
                  )}
                </div>
              );
            })}
          </div>
        </Card>
      )}
    </div>
  );
}

// Metric Card Component
function MetricCard({ title, value, change, icon: Icon, color }) {
  return (
    <Card className="p-4">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-silver">{title}</p>
          <p className="text-2xl font-bold text-pearl mt-1">{value}</p>
          {change !== undefined && (
            <div className="flex items-center gap-1 mt-1">
              {change > 0 ? (
                <ArrowUp className="w-3 h-3 text-green-500" />
              ) : change < 0 ? (
                <ArrowDown className="w-3 h-3 text-red-500" />
              ) : (
                <Minus className="w-3 h-3 text-gray-500" />
              )}
              <span className={`text-xs ${
                change > 0 ? 'text-green-500' : change < 0 ? 'text-red-500' : 'text-gray-500'
              }`}>
                {Math.abs(change)}%
              </span>
            </div>
          )}
        </div>
        <div className={`w-10 h-10 rounded-lg bg-slate flex items-center justify-center`}>
          <Icon className={`w-5 h-5 ${color}`} />
        </div>
      </div>
    </Card>
  );
}

// Insight Card Component
function InsightCard({ insight }) {
  const typeStyles = {
    positive: 'border-l-green-500 bg-green-500/10',
    warning: 'border-l-yellow-500 bg-yellow-500/10',
    info: 'border-l-blue-500 bg-blue-500/10',
    tip: 'border-l-accent bg-accent/10',
    suggestion: 'border-l-purple-500 bg-purple-500/10'
  };
  
  return (
    <Card className={`p-4 border-l-4 ${typeStyles[insight.type] || typeStyles.info}`}>
      <div className="flex items-start gap-3">
        <Lightbulb className="w-5 h-5 text-yellow-500 mt-0.5" />
        <div className="flex-1">
          <p className="text-pearl font-medium">{insight.title}</p>
          <p className="text-sm text-silver mt-1">{insight.message}</p>
          {insight.action && (
            <a 
              href={insight.action_link}
              className="text-sm text-accent hover:underline mt-2 inline-block"
            >
              {insight.action} →
            </a>
          )}
        </div>
      </div>
    </Card>
  );
}

// Simple Trend Chart Component
function TrendChart({ data }) {
  if (!data || data.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-silver">
        No trend data available
      </div>
    );
  }
  
  const maxEngagements = Math.max(...data.map(d => d.engagements), 1);
  
  return (
    <div className="h-full flex items-end gap-1">
      {data.map((point, i) => {
        const height = (point.engagements / maxEngagements) * 100;
        
        return (
          <div 
            key={i}
            className="flex-1 flex flex-col items-center"
            title={`${point.period}: ${point.engagements} engagements`}
          >
            <div 
              className="w-full bg-accent/80 rounded-t hover:bg-accent transition-colors cursor-pointer"
              style={{ height: `${Math.max(height, 2)}%` }}
            />
            {i % Math.ceil(data.length / 7) === 0 && (
              <span className="text-xs text-silver mt-2 truncate w-full text-center">
                {point.period.slice(5)}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}
