import { useState, useEffect } from 'react';
import {
  FolderOpen,
  Plus,
  Trash2,
  Download,
  RefreshCw
} from 'lucide-react';
import { categoriesApi } from '../services/api';
import {
  Card,
  LoadingState,
  ErrorState,
  EmptyState,
  Modal,
  ConfirmDialog,
  Badge,
  Spinner
} from '../components/ui';
import toast from 'react-hot-toast';

export default function Categories() {
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [seeding, setSeeding] = useState(false);
  const [error, setError] = useState(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [newCategory, setNewCategory] = useState({
    name: '',
    description: '',
    keywords: '',
  });

  const fetchCategories = async () => {
    setLoading(true);
    try {
      const res = await categoriesApi.getAll();
      setCategories(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCategories();
  }, []);

  const handleSeedCategories = async () => {
    setSeeding(true);
    try {
      await categoriesApi.seed();
      toast.success('Default categories created!');
      fetchCategories();
    } catch (err) {
      toast.error('Failed to seed categories');
    } finally {
      setSeeding(false);
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!newCategory.name.trim()) {
      toast.error('Category name is required');
      return;
    }

    try {
      await categoriesApi.create({
        name: newCategory.name,
        description: newCategory.description,
        keywords: newCategory.keywords.split(',').map(k => k.trim()).filter(Boolean),
      });
      toast.success('Category created!');
      setShowCreateModal(false);
      setNewCategory({ name: '', description: '', keywords: '' });
      fetchCategories();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to create category');
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await categoriesApi.delete(deleteTarget.id);
      toast.success('Category deleted');
      fetchCategories();
    } catch (err) {
      toast.error('Failed to delete category');
    }
    setDeleteTarget(null);
  };

  if (loading) return <LoadingState message="Loading categories..." />;
  if (error) return <ErrorState message={error} onRetry={fetchCategories} />;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="page-title">Categories</h1>
          <p className="text-silver mt-1">Organize your content by category</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={handleSeedCategories}
            disabled={seeding}
            className="btn-secondary flex items-center gap-2"
          >
            {seeding ? <Spinner size="sm" /> : <Download className="w-4 h-4" />}
            Seed Defaults
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="btn-primary flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            Add Category
          </button>
        </div>
      </div>

      {/* Categories Grid */}
      {categories.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {categories.map((category) => (
            <Card key={category.id} className="p-6 card-hover group">
              <div className="flex items-start justify-between mb-4">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-accent/20 to-accent/5 
                              flex items-center justify-center">
                  <FolderOpen className="w-6 h-6 text-accent" />
                </div>
                <button
                  onClick={() => setDeleteTarget(category)}
                  className="p-2 text-silver hover:text-error transition-colors opacity-0 
                           group-hover:opacity-100 rounded-lg hover:bg-slate"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>

              <h3 className="font-display font-semibold text-lg text-pearl mb-2">
                {category.name}
              </h3>

              {category.description && (
                <p className="text-silver text-sm mb-4 line-clamp-2">
                  {category.description}
                </p>
              )}

              {category.keywords && category.keywords.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {category.keywords.slice(0, 4).map((keyword, i) => (
                    <Badge key={i} variant="info">{keyword}</Badge>
                  ))}
                  {category.keywords.length > 4 && (
                    <Badge variant="info">+{category.keywords.length - 4}</Badge>
                  )}
                </div>
              )}
            </Card>
          ))}
        </div>
      ) : (
        <EmptyState
          icon={FolderOpen}
          title="No categories yet"
          description="Create categories to organize your content, or seed the default categories"
          action={
            <div className="flex gap-3">
              <button onClick={handleSeedCategories} className="btn-secondary">
                Seed Default Categories
              </button>
              <button onClick={() => setShowCreateModal(true)} className="btn-primary">
                Create Category
              </button>
            </div>
          }
        />
      )}

      {/* Create Modal */}
      <Modal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        title="Create Category"
      >
        <form onSubmit={handleCreate} className="space-y-4">
          <div>
            <label className="label">Name *</label>
            <input
              type="text"
              value={newCategory.name}
              onChange={(e) => setNewCategory({ ...newCategory, name: e.target.value })}
              placeholder="e.g., Lifestyle"
              className="input-field"
              required
            />
          </div>
          <div>
            <label className="label">Description</label>
            <textarea
              value={newCategory.description}
              onChange={(e) => setNewCategory({ ...newCategory, description: e.target.value })}
              placeholder="Describe this category..."
              rows={3}
              className="input-field"
            />
          </div>
          <div>
            <label className="label">Keywords (comma-separated)</label>
            <input
              type="text"
              value={newCategory.keywords}
              onChange={(e) => setNewCategory({ ...newCategory, keywords: e.target.value })}
              placeholder="lifestyle, daily routine, wellness"
              className="input-field"
            />
          </div>
          <div className="flex gap-3 justify-end pt-4">
            <button
              type="button"
              onClick={() => setShowCreateModal(false)}
              className="btn-secondary"
            >
              Cancel
            </button>
            <button type="submit" className="btn-primary">
              Create Category
            </button>
          </div>
        </form>
      </Modal>

      {/* Delete Confirmation */}
      <ConfirmDialog
        isOpen={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
        title="Delete Category"
        message={`Are you sure you want to delete "${deleteTarget?.name}"?`}
        confirmText="Delete"
        danger
      />
    </div>
  );
}
