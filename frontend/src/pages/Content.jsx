import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Images,
  Filter,
  Search,
  Trash2,
  Download,
  Eye,
  Copy,
  X,
  ExternalLink
} from 'lucide-react';
import { generateApi, brandsApi, categoriesApi } from '../services/api';
import {
  Card,
  LoadingState,
  ErrorState,
  EmptyState,
  Modal,
  ConfirmDialog,
  Badge,
  StatusBadge
} from '../components/ui';
import toast from 'react-hot-toast';

export default function Content() {
  const [content, setContent] = useState([]);
  const [brands, setBrands] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedContent, setSelectedContent] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);

  const [filters, setFilters] = useState({
    brand_id: '',
    category_id: '',
    content_type: '',
    status: '',
  });

  const fetchData = async () => {
    setLoading(true);
    try {
      const [contentRes, brandsRes, categoriesRes] = await Promise.all([
        generateApi.getAll({ limit: 100 }),
        brandsApi.getAll(),
        categoriesApi.getAll(),
      ]);
      setContent(contentRes.data);
      setBrands(brandsRes.data);
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

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await generateApi.delete(deleteTarget.id);
      toast.success('Content deleted');
      fetchData();
    } catch (err) {
      toast.error('Failed to delete content');
    }
    setDeleteTarget(null);
  };

  const handleCopyCaption = (caption) => {
    navigator.clipboard.writeText(caption);
    toast.success('Caption copied!');
  };

  const filteredContent = content.filter((item) => {
    if (filters.brand_id && item.brand_id !== parseInt(filters.brand_id)) return false;
    if (filters.category_id && item.category_id !== parseInt(filters.category_id)) return false;
    if (filters.content_type && item.content_type !== filters.content_type) return false;
    if (filters.status && item.status !== filters.status) return false;
    return true;
  });

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (loading) return <LoadingState message="Loading content..." />;
  if (error) return <ErrorState message={error} onRetry={fetchData} />;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="page-title">Generated Content</h1>
          <p className="text-silver mt-1">Browse and manage all your AI-generated content</p>
        </div>
        <Link to="/generate" className="btn-primary flex items-center gap-2 w-fit">
          Generate New
        </Link>
      </div>

      {/* Filters */}
      <Card className="p-4">
        <div className="flex items-center gap-2 mb-4">
          <Filter className="w-5 h-5 text-silver" />
          <span className="text-pearl font-medium">Filters</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <select
            value={filters.brand_id}
            onChange={(e) => setFilters({ ...filters, brand_id: e.target.value })}
            className="input-field"
          >
            <option value="">All Brands</option>
            {brands.map((brand) => (
              <option key={brand.id} value={brand.id}>{brand.name}</option>
            ))}
          </select>
          <select
            value={filters.category_id}
            onChange={(e) => setFilters({ ...filters, category_id: e.target.value })}
            className="input-field"
          >
            <option value="">All Categories</option>
            {categories.map((cat) => (
              <option key={cat.id} value={cat.id}>{cat.name}</option>
            ))}
          </select>
          <select
            value={filters.content_type}
            onChange={(e) => setFilters({ ...filters, content_type: e.target.value })}
            className="input-field"
          >
            <option value="">All Types</option>
            <option value="IMAGE">Images</option>
            <option value="TEXT">Text</option>
          </select>
          <select
            value={filters.status}
            onChange={(e) => setFilters({ ...filters, status: e.target.value })}
            className="input-field"
          >
            <option value="">All Status</option>
            <option value="COMPLETED">Completed</option>
            <option value="PENDING">Pending</option>
            <option value="GENERATING">Generating</option>
            <option value="FAILED">Failed</option>
          </select>
        </div>
      </Card>

      {/* Content Grid */}
      {filteredContent.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {filteredContent.map((item) => (
            <Card key={item.id} className="overflow-hidden card-hover group">
              {/* Image */}
              <div
                className="aspect-square bg-slate relative cursor-pointer"
                onClick={() => setSelectedContent(item)}
              >
                {item.result_url ? (
                  <img
                    src={item.result_url}
                    alt=""
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <Images className="w-12 h-12 text-graphite" />
                  </div>
                )}

                {/* Overlay */}
                <div className="absolute inset-0 bg-midnight/60 opacity-0 group-hover:opacity-100 
                              transition-opacity flex items-center justify-center gap-3">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedContent(item);
                    }}
                    className="p-2 bg-accent rounded-lg text-white"
                  >
                    <Eye className="w-5 h-5" />
                  </button>
                  {item.result_url && (
                    <a
                      href={item.result_url}
                      download
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      className="p-2 bg-success rounded-lg text-white"
                    >
                      <Download className="w-5 h-5" />
                    </a>
                  )}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setDeleteTarget(item);
                    }}
                    className="p-2 bg-error rounded-lg text-white"
                  >
                    <Trash2 className="w-5 h-5" />
                  </button>
                </div>

                {/* Status Badge */}
                <div className="absolute top-3 right-3">
                  <StatusBadge status={item.status} />
                </div>
              </div>

              {/* Info */}
              <div className="p-4">
                <div className="flex items-center justify-between mb-2">
                  <Badge variant="info" className="capitalize">
                    {item.content_type?.toLowerCase()}
                  </Badge>
                  <span className="text-silver text-xs">
                    {formatDate(item.created_at)}
                  </span>
                </div>
                {item.caption && (
                  <p className="text-silver text-sm line-clamp-2">{item.caption}</p>
                )}
              </div>
            </Card>
          ))}
        </div>
      ) : (
        <EmptyState
          icon={Images}
          title="No content found"
          description={Object.values(filters).some(Boolean)
            ? "Try adjusting your filters"
            : "Generate your first content to see it here"
          }
          action={
            !Object.values(filters).some(Boolean) && (
              <Link to="/generate" className="btn-primary">
                Generate Content
              </Link>
            )
          }
        />
      )}

      {/* Detail Modal */}
      <Modal
        isOpen={!!selectedContent}
        onClose={() => setSelectedContent(null)}
        title="Content Details"
        size="lg"
      >
        {selectedContent && (
          <div className="space-y-6">
            {/* Image */}
            {selectedContent.result_url && (
              <div className="relative">
                <img
                  src={selectedContent.result_url}
                  alt=""
                  className="w-full rounded-xl"
                />
                <a
                  href={selectedContent.result_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="absolute top-3 right-3 p-2 bg-charcoal/80 backdrop-blur rounded-lg 
                           text-pearl hover:text-accent transition-colors"
                >
                  <ExternalLink className="w-5 h-5" />
                </a>
              </div>
            )}

            {/* Status */}
            <div className="flex items-center gap-3">
              <StatusBadge status={selectedContent.status} />
              <Badge variant="info" className="capitalize">
                {selectedContent.content_type?.toLowerCase()}
              </Badge>
              <span className="text-silver text-sm">
                Created {formatDate(selectedContent.created_at)}
              </span>
            </div>

            {/* Caption */}
            {selectedContent.caption && (
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="label mb-0">Caption</span>
                  <button
                    onClick={() => handleCopyCaption(selectedContent.caption)}
                    className="text-accent hover:text-accent-light flex items-center gap-1 text-sm"
                  >
                    <Copy className="w-4 h-4" />
                    Copy
                  </button>
                </div>
                <div className="p-4 bg-slate rounded-xl">
                  <p className="text-pearl whitespace-pre-wrap">{selectedContent.caption}</p>
                </div>
              </div>
            )}

            {/* Hashtags */}
            {selectedContent.hashtags && selectedContent.hashtags.length > 0 && (
              <div>
                <span className="label">Hashtags</span>
                <div className="flex flex-wrap gap-2">
                  {selectedContent.hashtags.map((tag, i) => (
                    <span
                      key={i}
                      className="px-3 py-1 bg-accent/10 text-accent rounded-full text-sm"
                    >
                      #{tag}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Prompt */}
            {selectedContent.prompt_used && (
              <div>
                <span className="label">Prompt Used</span>
                <div className="p-4 bg-slate rounded-xl">
                  <p className="text-silver text-sm">{selectedContent.prompt_used}</p>
                </div>
              </div>
            )}

            {/* Error */}
            {selectedContent.error_message && (
              <div className="p-4 bg-error/10 border border-error/30 rounded-xl">
                <p className="text-error text-sm">{selectedContent.error_message}</p>
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-3 pt-4 border-t border-graphite">
              {selectedContent.result_url && (
                <a
                  href={selectedContent.result_url}
                  download
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-primary flex items-center gap-2"
                >
                  <Download className="w-4 h-4" />
                  Download
                </a>
              )}
              <button
                onClick={() => {
                  setDeleteTarget(selectedContent);
                  setSelectedContent(null);
                }}
                className="btn-danger flex items-center gap-2"
              >
                <Trash2 className="w-4 h-4" />
                Delete
              </button>
            </div>
          </div>
        )}
      </Modal>

      {/* Delete Confirmation */}
      <ConfirmDialog
        isOpen={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
        title="Delete Content"
        message="Are you sure you want to delete this content? This action cannot be undone."
        confirmText="Delete"
        danger
      />
    </div>
  );
}
