import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Building2,
  TrendingUp,
  Images,
  Sparkles,
  ArrowRight,
  RefreshCw,
  Zap,
  CheckCircle2,
  Circle,
  Layers,
  Calendar,
  Play,
  ChevronRight
} from 'lucide-react';
import { brandsApi, categoriesApi, trendsApi, generateApi, studioApi, loraApi } from '../services/api';
import { StatsCard, Card, LoadingState, ErrorState, Badge } from '../components/ui';

export default function Dashboard() {
  const navigate = useNavigate();
  const [stats, setStats] = useState({
    brands: 0,
    avatars: 0,
    trends: 0,
    projects: 0,
  });
  const [recentProjects, setRecentProjects] = useState([]);
  const [topTrends, setTopTrends] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isNewUser, setIsNewUser] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [brandsRes, trendsRes, projectsRes, loraRes] = await Promise.all([
        brandsApi.getAll(),
        trendsApi.getTop({ limit: 5 }).catch(() => ({ data: [] })),
        studioApi.listProjects({ limit: 5 }).catch(() => ({ data: { projects: [] } })),
        loraApi.listModels().catch(() => ({ data: [] })),
      ]);

      const brands = brandsRes.data || [];
      const avatars = (loraRes.data || []).filter(m => m.status === 'completed');
      const projects = projectsRes.data?.projects || projectsRes.data || [];
      const trends = trendsRes.data || [];

      setStats({
        brands: brands.length,
        avatars: avatars.length,
        trends: trends.length,
        projects: projects.length,
      });
      
      setTopTrends(trends);
      setRecentProjects(Array.isArray(projects) ? projects.slice(0, 5) : []);
      
      // Determine if new user (no brands or no projects)
      setIsNewUser(brands.length === 0 || projects.length === 0);
      
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleCreateFromTrend = (trend) => {
    navigate(`/studio/create?trend=${encodeURIComponent(trend.title)}&trend_id=${trend.id}`);
  };

  if (loading) return <LoadingState message="Loading dashboard..." />;
  if (error) return <ErrorState message={error} onRetry={fetchData} />;

  // Getting Started Steps
  const gettingStartedSteps = [
    {
      id: 'brand',
      title: 'Create Your Brand',
      description: 'Define your brand voice and style',
      href: '/brands/new',
      completed: stats.brands > 0,
      icon: Building2,
    },
    {
      id: 'avatar',
      title: 'Train Your AI Avatar',
      description: 'Upload photos to create your AI influencer',
      href: '/lora/new',
      completed: stats.avatars > 0,
      icon: Sparkles,
      optional: true,
    },
    {
      id: 'content',
      title: 'Generate Your First Content',
      description: 'Create captions, images, and hashtags',
      href: '/studio/create',
      completed: stats.projects > 0,
      icon: Layers,
    },
  ];

  const completedSteps = gettingStartedSteps.filter(s => s.completed).length;
  const totalSteps = gettingStartedSteps.length;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="page-title">
            {isNewUser ? 'Welcome to AI Content Platform' : 'Dashboard'}
          </h1>
          <p className="text-silver mt-1">
            {isNewUser 
              ? 'Create AI-powered social media content in minutes'
              : 'Your content creation hub'
            }
          </p>
        </div>
        <div className="flex gap-3">
          <button onClick={fetchData} className="btn-secondary flex items-center gap-2">
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
          <Link to="/studio/create" className="btn-primary flex items-center gap-2">
            <Sparkles className="w-4 h-4" />
            Create Content
          </Link>
        </div>
      </div>

      {/* Getting Started (for new users or incomplete setup) */}
      {(isNewUser || completedSteps < totalSteps) && (
        <Card className="p-6 border-accent/30 bg-gradient-to-br from-accent/5 to-transparent">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="section-title flex items-center gap-2">
                <Zap className="w-5 h-5 text-accent" />
                Getting Started
              </h2>
              <p className="text-silver text-sm mt-1">
                Complete these steps to unlock the full power of AI content creation
              </p>
            </div>
            <div className="text-right">
              <span className="text-2xl font-bold text-accent">{completedSteps}</span>
              <span className="text-silver">/{totalSteps}</span>
            </div>
          </div>
          
          {/* Progress Bar */}
          <div className="h-2 bg-slate rounded-full overflow-hidden mb-6">
            <div 
              className="h-full bg-gradient-to-r from-accent to-accent-light transition-all duration-500"
              style={{ width: `${(completedSteps / totalSteps) * 100}%` }}
            />
          </div>
          
          {/* Steps */}
          <div className="space-y-3">
            {gettingStartedSteps.map((step, index) => {
              const Icon = step.icon;
              return (
                <Link
                  key={step.id}
                  to={step.href}
                  className={`flex items-center gap-4 p-4 rounded-xl transition-all
                            ${step.completed 
                              ? 'bg-success/10 border border-success/20' 
                              : 'bg-slate/50 hover:bg-slate border border-transparent hover:border-accent/30'
                            }`}
                >
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center
                                ${step.completed ? 'bg-success/20' : 'bg-accent/10'}`}>
                    {step.completed ? (
                      <CheckCircle2 className="w-5 h-5 text-success" />
                    ) : (
                      <Icon className="w-5 h-5 text-accent" />
                    )}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className={`font-medium ${step.completed ? 'text-success' : 'text-pearl'}`}>
                        {step.title}
                      </span>
                      {step.optional && (
                        <Badge variant="secondary" className="text-xs">Optional</Badge>
                      )}
                    </div>
                    <p className="text-silver text-sm">{step.description}</p>
                  </div>
                  {!step.completed && (
                    <ChevronRight className="w-5 h-5 text-silver" />
                  )}
                </Link>
              );
            })}
          </div>
        </Card>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard
          label="Brands"
          value={stats.brands}
          icon={Building2}
          color="accent"
          href="/brands"
        />
        <StatsCard
          label="AI Avatars"
          value={stats.avatars}
          icon={Sparkles}
          color="warning"
          href="/lora"
        />
        <StatsCard
          label="Projects"
          value={stats.projects}
          icon={Layers}
          color="success"
          href="/studio"
        />
        <StatsCard
          label="Trending Topics"
          value={stats.trends}
          icon={TrendingUp}
          color="info"
          href="/trends"
        />
      </div>

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Quick Create from Trends */}
        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="section-title">Trending Now</h2>
            <Link to="/trends" className="text-accent hover:text-accent-light flex items-center gap-1 text-sm">
              View all <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
          {topTrends.length > 0 ? (
            <div className="space-y-3">
              {topTrends.map((trend, index) => (
                <div
                  key={trend.id}
                  className="flex items-center gap-4 p-3 rounded-xl bg-slate/50 hover:bg-slate transition-colors group"
                >
                  <div className="w-8 h-8 rounded-lg bg-accent/10 flex items-center justify-center text-accent font-bold">
                    {index + 1}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-pearl font-medium truncate">{trend.title}</p>
                    <p className="text-silver text-sm capitalize">{trend.source?.replace('_', ' ')}</p>
                  </div>
                  <button
                    onClick={() => handleCreateFromTrend(trend)}
                    className="opacity-0 group-hover:opacity-100 transition-opacity px-3 py-1.5 
                             rounded-lg bg-accent/10 text-accent text-sm font-medium hover:bg-accent/20"
                  >
                    Create
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <TrendingUp className="w-12 h-12 mx-auto text-silver/30 mb-3" />
              <p className="text-silver mb-2">No trends yet</p>
              <Link to="/trends" className="text-accent hover:underline text-sm">
                Discover trending topics
              </Link>
            </div>
          )}
        </Card>

        {/* Recent Projects */}
        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="section-title">Recent Projects</h2>
            <Link to="/studio" className="text-accent hover:text-accent-light flex items-center gap-1 text-sm">
              View all <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
          {recentProjects.length > 0 ? (
            <div className="space-y-3">
              {recentProjects.map((project) => (
                <Link
                  key={project.id}
                  to={`/studio/${project.id}`}
                  className="flex items-center gap-4 p-3 rounded-xl bg-slate/50 hover:bg-slate transition-colors"
                >
                  <div className="w-12 h-12 rounded-lg bg-graphite flex items-center justify-center">
                    <Layers className="w-6 h-6 text-accent" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-pearl font-medium truncate">{project.name}</p>
                    <p className="text-silver text-sm truncate">
                      {project.brief?.slice(0, 50) || 'No description'}
                    </p>
                  </div>
                  <Badge
                    variant={
                      project.status === 'completed' ? 'success' :
                      project.status === 'generating' ? 'warning' : 'error'
                    }
                  >
                    {project.status}
                  </Badge>
                </Link>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <Layers className="w-12 h-12 mx-auto text-silver/30 mb-3" />
              <p className="text-silver mb-2">No projects yet</p>
              <Link to="/studio/create" className="text-accent hover:underline text-sm">
                Create your first project
              </Link>
            </div>
          )}
        </Card>
      </div>

      {/* Quick Actions */}
      <Card className="p-6">
        <h2 className="section-title mb-4">Quick Actions</h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <Link
            to="/studio/create"
            className="p-4 rounded-xl bg-gradient-to-br from-accent/10 to-accent/5 border border-accent/20 
                     hover:border-accent/40 transition-all group"
          >
            <Layers className="w-8 h-8 text-accent mb-3 group-hover:scale-110 transition-transform" />
            <p className="font-medium text-pearl">Create Content</p>
            <p className="text-silver text-sm">Generate a full content package</p>
          </Link>
          <Link
            to="/lora/new"
            className="p-4 rounded-xl bg-slate hover:bg-graphite border border-graphite hover:border-accent/30 
                     transition-all group"
          >
            <Sparkles className="w-8 h-8 text-warning mb-3 group-hover:scale-110 transition-transform" />
            <p className="font-medium text-pearl">Train Avatar</p>
            <p className="text-silver text-sm">Create your AI influencer</p>
          </Link>
          <Link
            to="/trends"
            className="p-4 rounded-xl bg-slate hover:bg-graphite border border-graphite hover:border-accent/30 
                     transition-all group"
          >
            <TrendingUp className="w-8 h-8 text-success mb-3 group-hover:scale-110 transition-transform" />
            <p className="font-medium text-pearl">Browse Trends</p>
            <p className="text-silver text-sm">Find viral content ideas</p>
          </Link>
          <Link
            to="/calendar"
            className="p-4 rounded-xl bg-slate hover:bg-graphite border border-graphite hover:border-accent/30 
                     transition-all group"
          >
            <Calendar className="w-8 h-8 text-info mb-3 group-hover:scale-110 transition-transform" />
            <p className="font-medium text-pearl">Content Calendar</p>
            <p className="text-silver text-sm">Schedule your posts</p>
          </Link>
        </div>
      </Card>
    </div>
  );
}
