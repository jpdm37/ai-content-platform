import { useState, useEffect } from 'react';
import {
  TrendingUp,
  RefreshCw,
  Search,
  ExternalLink,
  Clock,
  Filter
} from 'lucide-react';
import { trendsApi, categoriesApi } from '../services/api';
import {
  Card,
  LoadingState,
  ErrorState,
  EmptyState,
  Badge,
  Spinner,
  Tabs
} from '../components/ui';
import toast from 'react-hot-toast';

export default function Trends() {
  const [trends, setTrends] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [scraping, setScraping] = useState(false);
  const [error, setError] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');

  const fetchData = async () => {
    setLoading(true);
    try {
      const [trendsRes, categoriesRes] = await Promise.all([
        trendsApi.getAll({ limit: 100 }),
        categoriesApi.getAll(),
      ]);
      setTrends(trendsRes.data);
      setCategories(categoriesRes.data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleScrape = async () => {
    setScraping(true);
    try {
      const res = await trendsApi.scrape({
        category_id: selectedCategory,
        sources: ['google_trends', 'rss'],
      });
      toast.success(`Found ${res.data.trends_found} trends!`);
      fetchData();
    } catch (err) {
      toast.error('Failed to scrape trends');
    } finally {
      setScraping(false);
    }
  };

  const filteredTrends = trends.filter((trend) => {
    const matchesCategory = !selectedCategory || trend.category_id === selectedCategory;
    const matchesSearch = !searchQuery ||
      trend.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      trend.description?.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  const getSourceBadgeVariant = (source) => {
    switch (source) {
      case 'google_trends': return 'info';
      case 'rss': return 'warning';
      case 'news_api': return 'success';
      default: return 'info';
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const days = Math.floor(hours / 24);

    if (hours < 1) return 'Just now';
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;
    return date.toLocaleDateString();
  };

  if (loading) return <LoadingState message="Loading trends..." />;
  if (error) return <ErrorState message={error} onRetry={fetchData} />;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="page-title">Trends</h1>
          <p className="text-silver mt-1">Discover trending topics for content inspiration</p>
        </div>
        <button
          onClick={handleScrape}
          disabled={scraping}
          className="btn-primary flex items-center gap-2 w-fit"
        >
          {scraping ? <Spinner size="sm" /> : <RefreshCw className="w-4 h-4" />}
          {scraping ? 'Scraping...' : 'Scrape New Trends'}
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-silver" />
          <input
            type="text"
            placeholder="Search trends..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="input-field pl-12"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="w-5 h-5 text-silver" />
          <select
            value={selectedCategory || ''}
            onChange={(e) => setSelectedCategory(e.target.value ? parseInt(e.target.value) : null)}
            className="input-field w-48"
          >
            <option value="">All Categories</option>
            {categories.map((cat) => (
              <option key={cat.id} value={cat.id}>{cat.name}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="p-4 text-center">
          <p className="text-2xl font-display font-bold text-pearl">{trends.length}</p>
          <p className="text-silver text-sm">Total Trends</p>
        </Card>
        <Card className="p-4 text-center">
          <p className="text-2xl font-display font-bold text-pearl">
            {trends.filter(t => t.source === 'google_trends').length}
          </p>
          <p className="text-silver text-sm">Google Trends</p>
        </Card>
        <Card className="p-4 text-center">
          <p className="text-2xl font-display font-bold text-pearl">
            {trends.filter(t => t.source === 'rss').length}
          </p>
          <p className="text-silver text-sm">RSS Feeds</p>
        </Card>
        <Card className="p-4 text-center">
          <p className="text-2xl font-display font-bold text-pearl">
            {trends.filter(t => t.source === 'news_api').length}
          </p>
          <p className="text-silver text-sm">News API</p>
        </Card>
      </div>

      {/* Trends List */}
      {filteredTrends.length > 0 ? (
        <div className="space-y-4">
          {filteredTrends.map((trend, index) => (
            <Card
              key={trend.id}
              className="p-5 card-hover animate-fade-in"
              style={{ animationDelay: `${index * 50}ms` }}
            >
              <div className="flex items-start gap-4">
                {/* Rank */}
                <div className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center 
                              text-accent font-bold shrink-0">
                  {index + 1}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <h3 className="font-medium text-pearl mb-1 line-clamp-1">
                        {trend.title}
                      </h3>
                      {trend.description && (
                        <p className="text-silver text-sm line-clamp-2 mb-3">
                          {trend.description}
                        </p>
                      )}
                    </div>

                    {/* Score */}
                    <div className="text-right shrink-0">
                      <p className="text-2xl font-display font-bold text-pearl">
                        {trend.popularity_score}
                      </p>
                      <p className="text-silver text-xs">Score</p>
                    </div>
                  </div>

                  {/* Meta */}
                  <div className="flex flex-wrap items-center gap-3">
                    <Badge variant={getSourceBadgeVariant(trend.source)}>
                      {trend.source.replace('_', ' ')}
                    </Badge>

                    {categories.find(c => c.id === trend.category_id) && (
                      <Badge variant="info">
                        {categories.find(c => c.id === trend.category_id)?.name}
                      </Badge>
                    )}

                    <span className="flex items-center gap-1 text-silver text-xs">
                      <Clock className="w-3 h-3" />
                      {formatDate(trend.scraped_at)}
                    </span>

                    {trend.source_url && (
                      <a
                        href={trend.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 text-accent hover:text-accent-light text-xs"
                      >
                        <ExternalLink className="w-3 h-3" />
                        Source
                      </a>
                    )}
                  </div>

                  {/* Related Keywords */}
                  {trend.related_keywords && trend.related_keywords.length > 0 && (
                    <div className="flex flex-wrap gap-2 mt-3">
                      {trend.related_keywords.map((keyword, i) => (
                        <span
                          key={i}
                          className="text-xs px-2 py-1 bg-slate rounded-md text-silver"
                        >
                          {keyword}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </Card>
          ))}
        </div>
      ) : (
        <EmptyState
          icon={TrendingUp}
          title="No trends found"
          description={searchQuery || selectedCategory
            ? "Try adjusting your filters"
            : "Click 'Scrape New Trends' to discover trending topics"
          }
          action={
            !searchQuery && !selectedCategory && (
              <button onClick={handleScrape} className="btn-primary">
                Scrape Trends Now
              </button>
            )
          }
        />
      )}
    </div>
  );
}
