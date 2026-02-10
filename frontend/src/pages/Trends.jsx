import { useState, useEffect } from 'react';
import {
  TrendingUp,
  RefreshCw,
  Search,
  ExternalLink,
  Clock,
  Filter,
  Plus,
  Sparkles,
  Tag,
  X,
  AlertCircle,
  Layers
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { trendsApi, categoriesApi } from '../services/api';
import {
  Card,
  LoadingState,
  ErrorState,
  EmptyState,
  Badge,
  Spinner,
  Modal
} from '../components/ui';
import toast from 'react-hot-toast';

export default function Trends() {
  const navigate = useNavigate();
  const [trends, setTrends] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [scraping, setScraping] = useState(false);
  const [error, setError] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [showCategoryModal, setShowCategoryModal] = useState(false);
  const [newCategory, setNewCategory] = useState({ name: '', description: '', keywords: '' });
  const [creatingCategory, setCreatingCategory] = useState(false);
  const [seeding, setSeeding] = useState(false);

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

  const handleSeedCategories = async () => {
    setSeeding(true);
    try {
      const res = await fetch('/api/v1/setup/seed-categories', { 
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      const data = await res.json();
      toast.success(`Created ${data.created?.length || 0} categories!`);
      fetchData();
    } catch (err) {
      toast.error('Failed to seed categories');
    } finally {
      setSeeding(false);
    }
  };

  const handleScrape = async () => {
    if (categories.length === 0) {
      toast.error('Please seed categories first');
      return;
    }
    
    setScraping(true);
    try {
      const res = await trendsApi.scrape({
        category_id: selectedCategory,
      });
      toast.success(`Found ${res.data.trends_found} trends!`);
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to scrape trends');
    } finally {
      setScraping(false);
    }
  };

  const handleCreateCategory = async () => {
    if (!newCategory.name.trim()) {
      toast.error('Category name is required');
      return;
    }
    
    setCreatingCategory(true);
    try {
      await categoriesApi.create({
        name: newCategory.name,
        description: newCategory.description,
        keywords: newCategory.keywords.split(',').map(k => k.trim()).filter(k => k),
      });
      toast.success('Category created!');
      setShowCategoryModal(false);
      setNewCategory({ name: '', description: '', keywords: '' });
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to create category');
    } finally {
      setCreatingCategory(false);
    }
  };

  const handleCreateContent = (trend) => {
    // Navigate to Content Studio with trend pre-filled
    navigate(`/studio/create?trend=${encodeURIComponent(trend.title)}&trend_id=${trend.id}`);
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
      case 'google_news': return 'success';
      case 'rss': return 'warning';
      case 'news_api': return 'default';
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

  // Show setup prompt if no categories
  if (categories.length === 0) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="page-title">Trends</h1>
          <p className="text-silver mt-1">Discover trending topics for content inspiration</p>
        </div>
        
        <Card className="p-8 text-center">
          <AlertCircle className="w-16 h-16 mx-auto text-amber-400 mb-4" />
          <h2 className="text-xl font-bold text-pearl mb-2">Setup Required</h2>
          <p className="text-silver mb-6 max-w-md mx-auto">
            Before you can discover trends, we need to set up content categories. 
            This only takes a moment.
          </p>
          <button
            onClick={handleSeedCategories}
            disabled={seeding}
            className="btn-primary flex items-center gap-2 mx-auto"
          >
            {seeding ? <Spinner size="sm" /> : <Sparkles className="w-4 h-4" />}
            {seeding ? 'Setting up...' : 'Setup Categories'}
          </button>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="page-title">Trends</h1>
          <p className="text-silver mt-1">Discover trending topics for content inspiration</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => setShowCategoryModal(true)}
            className="btn-secondary flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            Add Category
          </button>
          <button
            onClick={handleScrape}
            disabled={scraping}
            className="btn-primary flex items-center gap-2"
          >
            {scraping ? <Spinner size="sm" /> : <RefreshCw className="w-4 h-4" />}
            {scraping ? 'Scraping...' : 'Scrape Trends'}
          </button>
        </div>
      </div>

      {/* Categories */}
      <Card className="p-4">
        <div className="flex items-center gap-2 mb-3">
          <Tag className="w-4 h-4 text-silver" />
          <span className="text-sm text-silver font-medium">Categories</span>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setSelectedCategory(null)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors
                      ${!selectedCategory 
                        ? 'bg-accent text-white' 
                        : 'bg-slate text-silver hover:text-pearl'}`}
          >
            All ({trends.length})
          </button>
          {categories.map((cat) => {
            const count = trends.filter(t => t.category_id === cat.id).length;
            return (
              <button
                key={cat.id}
                onClick={() => setSelectedCategory(cat.id)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors
                          ${selectedCategory === cat.id 
                            ? 'bg-accent text-white' 
                            : 'bg-slate text-silver hover:text-pearl'}`}
              >
                {cat.name} ({count})
              </button>
            );
          })}
        </div>
      </Card>

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
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="p-4 text-center">
          <p className="text-2xl font-display font-bold text-pearl">{trends.length}</p>
          <p className="text-silver text-sm">Total Trends</p>
        </Card>
        <Card className="p-4 text-center">
          <p className="text-2xl font-display font-bold text-pearl">
            {trends.filter(t => t.source === 'google_news').length}
          </p>
          <p className="text-silver text-sm">Google News</p>
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

                    {/* Score & Actions */}
                    <div className="flex items-center gap-4 shrink-0">
                      <div className="text-right">
                        <p className="text-2xl font-display font-bold text-pearl">
                          {trend.popularity_score}
                        </p>
                        <p className="text-silver text-xs">Score</p>
                      </div>
                      <button
                        onClick={() => handleCreateContent(trend)}
                        className="btn-primary text-sm px-3 py-1.5 flex items-center gap-1"
                      >
                        <Layers className="w-3 h-3" />
                        Create
                      </button>
                    </div>
                  </div>

                  {/* Meta */}
                  <div className="flex flex-wrap items-center gap-3">
                    <Badge variant={getSourceBadgeVariant(trend.source)}>
                      {trend.source?.replace('_', ' ')}
                    </Badge>

                    {categories.find(c => c.id === trend.category_id) && (
                      <Badge variant="secondary">
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
            : "Click 'Scrape Trends' to discover trending topics in your categories"
          }
          action={
            !searchQuery && !selectedCategory && (
              <button onClick={handleScrape} disabled={scraping} className="btn-primary">
                {scraping ? 'Scraping...' : 'Scrape Trends Now'}
              </button>
            )
          }
        />
      )}

      {/* Create Category Modal */}
      {showCategoryModal && (
        <Modal onClose={() => setShowCategoryModal(false)} title="Add Custom Category">
          <div className="space-y-4">
            <div>
              <label className="block text-sm text-silver mb-1">Category Name *</label>
              <input
                type="text"
                value={newCategory.name}
                onChange={(e) => setNewCategory({ ...newCategory, name: e.target.value })}
                placeholder="e.g., Cryptocurrency"
                className="input-field w-full"
              />
            </div>
            
            <div>
              <label className="block text-sm text-silver mb-1">Description</label>
              <textarea
                value={newCategory.description}
                onChange={(e) => setNewCategory({ ...newCategory, description: e.target.value })}
                placeholder="What kind of content does this category cover?"
                rows={2}
                className="input-field w-full"
              />
            </div>
            
            <div>
              <label className="block text-sm text-silver mb-1">Keywords (comma-separated)</label>
              <input
                type="text"
                value={newCategory.keywords}
                onChange={(e) => setNewCategory({ ...newCategory, keywords: e.target.value })}
                placeholder="bitcoin, ethereum, defi, nft, web3"
                className="input-field w-full"
              />
              <p className="text-xs text-silver mt-1">Used to find relevant trends</p>
            </div>
            
            <div className="flex gap-3 pt-4">
              <button
                onClick={() => setShowCategoryModal(false)}
                className="btn-secondary flex-1"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateCategory}
                disabled={creatingCategory}
                className="btn-primary flex-1"
              >
                {creatingCategory ? <Spinner size="sm" /> : 'Create Category'}
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
