import { useState, useEffect } from 'react';
import { BarChart3, TrendingUp, TrendingDown, DollarSign, Image, Video, Share2, Clock, Zap, Calendar } from 'lucide-react';
import { analyticsApi } from '../../services/api';
import { Card, LoadingState, Badge } from '../../components/ui';
import toast from 'react-hot-toast';

export default function AnalyticsDashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState(30);

  useEffect(() => { fetchAnalytics(); }, [period]);

  const fetchAnalytics = async () => {
    setLoading(true);
    try {
      const res = await analyticsApi.getDashboard(period);
      setData(res.data);
    } catch (err) { toast.error('Failed to load analytics'); }
    setLoading(false);
  };

  if (loading) return <LoadingState message="Loading analytics..." />;
  if (!data) return null;

  const { overview, content, social, videos, costs, best_times } = data;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title flex items-center gap-3">
            <BarChart3 className="w-8 h-8 text-accent" />
            Analytics
          </h1>
          <p className="text-silver mt-1">Track your content performance</p>
        </div>
        <select
          value={period}
          onChange={(e) => setPeriod(parseInt(e.target.value))}
          className="input-field w-auto"
        >
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
        </select>
      </div>

      {/* Overview Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <Card className="p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-silver text-sm">Content Generated</p>
              <p className="text-3xl font-bold text-pearl mt-1">{overview.content_generated}</p>
            </div>
            <Image className="w-10 h-10 text-blue-400" />
          </div>
          {overview.content_change_percent !== 0 && (
            <div className={`flex items-center gap-1 mt-2 text-sm ${overview.content_change_percent > 0 ? 'text-success' : 'text-error'}`}>
              {overview.content_change_percent > 0 ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
              {Math.abs(overview.content_change_percent)}% vs previous period
            </div>
          )}
        </Card>

        <Card className="p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-silver text-sm">Videos Created</p>
              <p className="text-3xl font-bold text-pearl mt-1">{overview.videos_generated}</p>
            </div>
            <Video className="w-10 h-10 text-purple-400" />
          </div>
        </Card>

        <Card className="p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-silver text-sm">Posts Published</p>
              <p className="text-3xl font-bold text-pearl mt-1">{overview.posts_published}</p>
            </div>
            <Share2 className="w-10 h-10 text-green-400" />
          </div>
        </Card>

        <Card className="p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-silver text-sm">Total Engagement</p>
              <p className="text-3xl font-bold text-pearl mt-1">
                {(overview.total_engagement?.likes || 0) + (overview.total_engagement?.comments || 0)}
              </p>
            </div>
            <Zap className="w-10 h-10 text-yellow-400" />
          </div>
        </Card>

        <Card className="p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-silver text-sm">Total Cost</p>
              <p className="text-3xl font-bold text-accent mt-1">${overview.total_cost_usd}</p>
            </div>
            <DollarSign className="w-10 h-10 text-accent" />
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Content by Type */}
        <Card className="p-6">
          <h2 className="section-title mb-4">Content by Type</h2>
          {Object.keys(content.by_type || {}).length === 0 ? (
            <p className="text-silver text-center py-8">No content generated yet</p>
          ) : (
            <div className="space-y-3">
              {Object.entries(content.by_type).map(([type, count]) => {
                const maxCount = Math.max(...Object.values(content.by_type));
                const percentage = (count / maxCount) * 100;
                return (
                  <div key={type}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-pearl capitalize">{type}</span>
                      <span className="text-silver">{count}</span>
                    </div>
                    <div className="h-2 bg-slate rounded-full overflow-hidden">
                      <div className="h-full bg-accent" style={{ width: `${percentage}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </Card>

        {/* Social by Platform */}
        <Card className="p-6">
          <h2 className="section-title mb-4">Posts by Platform</h2>
          {Object.keys(social.by_platform || {}).length === 0 ? (
            <p className="text-silver text-center py-8">No posts published yet</p>
          ) : (
            <div className="space-y-3">
              {Object.entries(social.by_platform).map(([platform, count]) => {
                const maxCount = Math.max(...Object.values(social.by_platform));
                const percentage = (count / maxCount) * 100;
                const colors = { twitter: 'bg-blue-400', instagram: 'bg-pink-400', linkedin: 'bg-blue-600', facebook: 'bg-blue-500' };
                return (
                  <div key={platform}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-pearl capitalize">{platform}</span>
                      <span className="text-silver">{count}</span>
                    </div>
                    <div className="h-2 bg-slate rounded-full overflow-hidden">
                      <div className={`h-full ${colors[platform] || 'bg-accent'}`} style={{ width: `${percentage}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </Card>

        {/* Top Posts */}
        <Card className="p-6">
          <h2 className="section-title mb-4">Top Performing Posts</h2>
          {social.top_posts?.length === 0 ? (
            <p className="text-silver text-center py-8">No engagement data yet</p>
          ) : (
            <div className="space-y-3">
              {social.top_posts?.slice(0, 5).map((post, i) => (
                <div key={post.id} className="p-3 bg-slate rounded-lg">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <Badge variant="secondary" className="text-xs capitalize mb-1">{post.platform}</Badge>
                      <p className="text-sm text-pearl line-clamp-2">{post.caption}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-accent font-bold">{post.score}</p>
                      <p className="text-xs text-silver">score</p>
                    </div>
                  </div>
                  {post.engagement && (
                    <div className="flex gap-4 mt-2 text-xs text-silver">
                      <span>❤️ {post.engagement.likes || 0}</span>
                      <span>💬 {post.engagement.comments || 0}</span>
                      <span>🔄 {post.engagement.shares || 0}</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </Card>

        {/* Cost Breakdown */}
        <Card className="p-6">
          <h2 className="section-title mb-4">Cost by Feature</h2>
          {Object.keys(costs.by_feature || {}).length === 0 ? (
            <p className="text-silver text-center py-8">No costs recorded yet</p>
          ) : (
            <div className="space-y-3">
              {Object.entries(costs.by_feature).map(([feature, cost]) => (
                <div key={feature} className="flex justify-between items-center p-3 bg-slate rounded-lg">
                  <span className="text-pearl capitalize">{feature.replace('_', ' ')}</span>
                  <span className="text-accent font-bold">${cost.toFixed(2)}</span>
                </div>
              ))}
              <div className="flex justify-between items-center p-3 bg-accent/10 rounded-lg border border-accent">
                <span className="text-pearl font-medium">Total</span>
                <span className="text-accent font-bold">${costs.total_cost_usd.toFixed(2)}</span>
              </div>
            </div>
          )}
        </Card>

        {/* Best Times */}
        <Card className="p-6 lg:col-span-2">
          <h2 className="section-title mb-4 flex items-center gap-2">
            <Clock className="w-5 h-5" />
            Best Posting Times
          </h2>
          {!best_times?.best_days ? (
            <p className="text-silver text-center py-8">Need more published posts for analysis</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h3 className="text-sm font-medium text-pearl mb-3">Best Days</h3>
                <div className="space-y-2">
                  {best_times.best_days.map((day, i) => (
                    <div key={day.day} className="flex items-center justify-between p-3 bg-slate rounded-lg">
                      <div className="flex items-center gap-3">
                        <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${i === 0 ? 'bg-accent text-white' : 'bg-graphite text-silver'}`}>
                          {i + 1}
                        </span>
                        <span className="text-pearl">{day.day}</span>
                      </div>
                      <div className="text-right">
                        <p className="text-accent font-bold">{day.avg_engagement.toFixed(1)}</p>
                        <p className="text-xs text-silver">{day.posts} posts</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <h3 className="text-sm font-medium text-pearl mb-3">Best Hours</h3>
                <div className="space-y-2">
                  {best_times.best_hours.map((hour, i) => (
                    <div key={hour.hour} className="flex items-center justify-between p-3 bg-slate rounded-lg">
                      <div className="flex items-center gap-3">
                        <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${i === 0 ? 'bg-accent text-white' : 'bg-graphite text-silver'}`}>
                          {i + 1}
                        </span>
                        <span className="text-pearl">
                          {hour.hour === 0 ? '12 AM' : hour.hour < 12 ? `${hour.hour} AM` : hour.hour === 12 ? '12 PM' : `${hour.hour - 12} PM`}
                        </span>
                      </div>
                      <div className="text-right">
                        <p className="text-accent font-bold">{hour.avg_engagement.toFixed(1)}</p>
                        <p className="text-xs text-silver">{hour.posts} posts</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
          {best_times?.total_posts_analyzed && (
            <p className="text-xs text-silver text-center mt-4">
              Analysis based on {best_times.total_posts_analyzed} published posts
            </p>
          )}
        </Card>

        {/* Video Stats */}
        <Card className="p-6 lg:col-span-2">
          <h2 className="section-title mb-4 flex items-center gap-2">
            <Video className="w-5 h-5" />
            Video Analytics
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-4 bg-slate rounded-lg text-center">
              <p className="text-2xl font-bold text-pearl">{videos.total_videos}</p>
              <p className="text-xs text-silver">Total Videos</p>
            </div>
            <div className="p-4 bg-slate rounded-lg text-center">
              <p className="text-2xl font-bold text-success">{videos.by_status?.completed || 0}</p>
              <p className="text-xs text-silver">Completed</p>
            </div>
            <div className="p-4 bg-slate rounded-lg text-center">
              <p className="text-2xl font-bold text-pearl">{videos.avg_duration_seconds}s</p>
              <p className="text-xs text-silver">Avg Duration</p>
            </div>
            <div className="p-4 bg-slate rounded-lg text-center">
              <p className="text-2xl font-bold text-accent">${videos.total_cost_usd}</p>
              <p className="text-xs text-silver">Total Cost</p>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
