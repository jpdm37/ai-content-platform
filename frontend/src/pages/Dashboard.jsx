import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Building2,
  FolderOpen,
  TrendingUp,
  Images,
  Sparkles,
  ArrowRight,
  RefreshCw,
  Zap
} from 'lucide-react';
import { brandsApi, categoriesApi, trendsApi, generateApi, statusApi } from '../services/api';
import { StatsCard, Card, LoadingState, ErrorState, Badge } from '../components/ui';

export default function Dashboard() {
  const [stats, setStats] = useState({
    brands: 0,
    categories: 0,
    trends: 0,
    content: 0,
  });
  const [recentContent, setRecentContent] = useState([]);
  const [topTrends, setTopTrends] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [apiStatus, setApiStatus] = useState(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [brandsRes, categoriesRes, trendsRes, contentRes, statusRes] = await Promise.all([
        brandsApi.getAll(),
        categoriesApi.getAll(),
        trendsApi.getTop({ limit: 5 }),
        generateApi.getAll({ limit: 5 }),
        statusApi.status().catch(() => ({ data: null })),
      ]);

      setStats({
        brands: brandsRes.data.length,
        categories: categoriesRes.data.length,
        trends: trendsRes.data.length,
        content: contentRes.data.length,
      });
      setTopTrends(trendsRes.data);
      setRecentContent(contentRes.data);
      setApiStatus(statusRes.data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  if (loading) return <LoadingState message="Loading dashboard..." />;
  if (error) return <ErrorState message={error} onRetry={fetchData} />;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="text-silver mt-1">Welcome to your AI Content Platform</p>
        </div>
        <div className="flex gap-3">
          <button onClick={fetchData} className="btn-secondary flex items-center gap-2">
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
          <Link to="/generate" className="btn-primary flex items-center gap-2">
            <Sparkles className="w-4 h-4" />
            Generate Content
          </Link>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard
          label="Total Brands"
          value={stats.brands}
          icon={Building2}
          color="accent"
        />
        <StatsCard
          label="Categories"
          value={stats.categories}
          icon={FolderOpen}
          color="success"
        />
        <StatsCard
          label="Active Trends"
          value={stats.trends}
          icon={TrendingUp}
          color="warning"
        />
        <StatsCard
          label="Generated Content"
          value={stats.content}
          icon={Images}
          color="accent"
        />
      </div>

      {/* API Status */}
      {apiStatus && (
        <Card className="p-6">
          <h2 className="section-title mb-4 flex items-center gap-2">
            <Zap className="w-5 h-5 text-accent" />
            API Configuration
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="flex items-center gap-3">
              <div className={`w-3 h-3 rounded-full ${apiStatus.openai_configured ? 'bg-success' : 'bg-error'}`} />
              <span className="text-silver">OpenAI API</span>
              <Badge variant={apiStatus.openai_configured ? 'success' : 'error'}>
                {apiStatus.openai_configured ? 'Connected' : 'Not Configured'}
              </Badge>
            </div>
            <div className="flex items-center gap-3">
              <div className={`w-3 h-3 rounded-full ${apiStatus.replicate_configured ? 'bg-success' : 'bg-error'}`} />
              <span className="text-silver">Replicate API</span>
              <Badge variant={apiStatus.replicate_configured ? 'success' : 'error'}>
                {apiStatus.replicate_configured ? 'Connected' : 'Not Configured'}
              </Badge>
            </div>
            <div className="flex items-center gap-3">
              <div className={`w-3 h-3 rounded-full ${apiStatus.news_api_configured ? 'bg-success' : 'bg-warning'}`} />
              <span className="text-silver">News API</span>
              <Badge variant={apiStatus.news_api_configured ? 'success' : 'warning'}>
                {apiStatus.news_api_configured ? 'Connected' : 'Optional'}
              </Badge>
            </div>
          </div>
        </Card>
      )}

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Trends */}
        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="section-title">Top Trends</h2>
            <Link to="/trends" className="text-accent hover:text-accent-light flex items-center gap-1 text-sm">
              View all <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
          {topTrends.length > 0 ? (
            <div className="space-y-3">
              {topTrends.map((trend, index) => (
                <div
                  key={trend.id}
                  className="flex items-center gap-4 p-3 rounded-xl bg-slate/50 hover:bg-slate transition-colors"
                >
                  <div className="w-8 h-8 rounded-lg bg-accent/10 flex items-center justify-center text-accent font-bold">
                    {index + 1}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-pearl font-medium truncate">{trend.title}</p>
                    <p className="text-silver text-sm capitalize">{trend.source}</p>
                  </div>
                  <Badge variant="info">{trend.popularity_score}</Badge>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <p className="text-silver">No trends yet</p>
              <Link to="/trends" className="text-accent hover:underline text-sm">
                Scrape some trends
              </Link>
            </div>
          )}
        </Card>

        {/* Recent Content */}
        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="section-title">Recent Content</h2>
            <Link to="/content" className="text-accent hover:text-accent-light flex items-center gap-1 text-sm">
              View all <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
          {recentContent.length > 0 ? (
            <div className="space-y-3">
              {recentContent.map((content) => (
                <div
                  key={content.id}
                  className="flex items-center gap-4 p-3 rounded-xl bg-slate/50 hover:bg-slate transition-colors"
                >
                  {content.result_url ? (
                    <img
                      src={content.result_url}
                      alt=""
                      className="w-12 h-12 rounded-lg object-cover"
                    />
                  ) : (
                    <div className="w-12 h-12 rounded-lg bg-graphite flex items-center justify-center">
                      <Images className="w-6 h-6 text-silver" />
                    </div>
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="text-pearl font-medium capitalize">{content.content_type}</p>
                    <p className="text-silver text-sm truncate">
                      {content.caption?.slice(0, 50) || 'No caption'}
                    </p>
                  </div>
                  <Badge
                    variant={
                      content.status === 'completed' ? 'success' :
                        content.status === 'failed' ? 'error' : 'warning'
                    }
                  >
                    {content.status}
                  </Badge>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <p className="text-silver">No content generated yet</p>
              <Link to="/generate" className="text-accent hover:underline text-sm">
                Generate your first content
              </Link>
            </div>
          )}
        </Card>
      </div>

      {/* Quick Actions */}
      <Card className="p-6">
        <h2 className="section-title mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Link
            to="/brands/new"
            className="p-4 rounded-xl bg-slate hover:bg-graphite border border-graphite hover:border-accent/30 
                     transition-all group"
          >
            <Building2 className="w-8 h-8 text-accent mb-3 group-hover:scale-110 transition-transform" />
            <p className="font-medium text-pearl">Create Brand</p>
            <p className="text-silver text-sm">Set up a new AI persona</p>
          </Link>
          <Link
            to="/trends"
            className="p-4 rounded-xl bg-slate hover:bg-graphite border border-graphite hover:border-accent/30 
                     transition-all group"
          >
            <TrendingUp className="w-8 h-8 text-success mb-3 group-hover:scale-110 transition-transform" />
            <p className="font-medium text-pearl">Scrape Trends</p>
            <p className="text-silver text-sm">Find trending topics</p>
          </Link>
          <Link
            to="/generate"
            className="p-4 rounded-xl bg-slate hover:bg-graphite border border-graphite hover:border-accent/30 
                     transition-all group"
          >
            <Sparkles className="w-8 h-8 text-warning mb-3 group-hover:scale-110 transition-transform" />
            <p className="font-medium text-pearl">Generate Image</p>
            <p className="text-silver text-sm">Create AI content</p>
          </Link>
          <Link
            to="/categories"
            className="p-4 rounded-xl bg-slate hover:bg-graphite border border-graphite hover:border-accent/30 
                     transition-all group"
          >
            <FolderOpen className="w-8 h-8 text-accent-light mb-3 group-hover:scale-110 transition-transform" />
            <p className="font-medium text-pearl">Manage Categories</p>
            <p className="text-silver text-sm">Organize content types</p>
          </Link>
        </div>
      </Card>
    </div>
  );
}
