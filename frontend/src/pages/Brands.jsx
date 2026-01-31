import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Building2,
  Plus,
  Search,
  MoreVertical,
  Edit,
  Trash2,
  Image as ImageIcon,
  Sparkles
} from 'lucide-react';
import { brandsApi } from '../services/api';
import {
  Card,
  LoadingState,
  ErrorState,
  EmptyState,
  Modal,
  ConfirmDialog,
  Badge
} from '../components/ui';
import toast from 'react-hot-toast';

export default function Brands() {
  const [brands, setBrands] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [deleteTarget, setDeleteTarget] = useState(null);
  const navigate = useNavigate();

  const fetchBrands = async () => {
    setLoading(true);
    try {
      const res = await brandsApi.getAll();
      setBrands(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBrands();
  }, []);

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await brandsApi.delete(deleteTarget.id);
      toast.success('Brand deleted successfully');
      fetchBrands();
    } catch (err) {
      toast.error('Failed to delete brand');
    }
    setDeleteTarget(null);
  };

  const filteredBrands = brands.filter(brand =>
    brand.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    brand.description?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  if (loading) return <LoadingState message="Loading brands..." />;
  if (error) return <ErrorState message={error} onRetry={fetchBrands} />;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="page-title">Brands</h1>
          <p className="text-silver mt-1">Manage your AI personas and brand profiles</p>
        </div>
        <Link to="/brands/new" className="btn-primary flex items-center gap-2 w-fit">
          <Plus className="w-4 h-4" />
          Create Brand
        </Link>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-silver" />
        <input
          type="text"
          placeholder="Search brands..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="input-field pl-12"
        />
      </div>

      {/* Brands Grid */}
      {filteredBrands.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredBrands.map((brand) => (
            <Card key={brand.id} className="overflow-hidden card-hover group">
              {/* Avatar/Image */}
              <div className="h-40 bg-gradient-to-br from-slate to-graphite relative overflow-hidden">
                {brand.reference_image_url ? (
                  <img
                    src={brand.reference_image_url}
                    alt={brand.name}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <Building2 className="w-16 h-16 text-graphite" />
                  </div>
                )}
                <div className="absolute inset-0 bg-gradient-to-t from-charcoal/90 to-transparent" />

                {/* Actions */}
                <div className="absolute top-3 right-3 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      navigate(`/brands/${brand.id}/edit`);
                    }}
                    className="p-2 bg-charcoal/80 backdrop-blur rounded-lg text-silver hover:text-pearl transition-colors"
                  >
                    <Edit className="w-4 h-4" />
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setDeleteTarget(brand);
                    }}
                    className="p-2 bg-charcoal/80 backdrop-blur rounded-lg text-silver hover:text-error transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Content */}
              <div className="p-5">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h3 className="font-display font-semibold text-lg text-pearl">
                      {brand.name}
                    </h3>
                    {brand.persona_name && (
                      <p className="text-silver text-sm">
                        Persona: {brand.persona_name}
                      </p>
                    )}
                  </div>
                </div>

                {brand.description && (
                  <p className="text-silver text-sm line-clamp-2 mb-4">
                    {brand.description}
                  </p>
                )}

                {/* Traits */}
                {brand.persona_traits && brand.persona_traits.length > 0 && (
                  <div className="flex flex-wrap gap-2 mb-4">
                    {brand.persona_traits.slice(0, 3).map((trait, i) => (
                      <Badge key={i} variant="info">{trait}</Badge>
                    ))}
                    {brand.persona_traits.length > 3 && (
                      <Badge variant="info">+{brand.persona_traits.length - 3}</Badge>
                    )}
                  </div>
                )}

                {/* Actions */}
                <div className="flex gap-2 pt-4 border-t border-graphite">
                  <Link
                    to={`/generate?brand=${brand.id}`}
                    className="flex-1 btn-primary text-sm py-2 flex items-center justify-center gap-2"
                  >
                    <Sparkles className="w-4 h-4" />
                    Generate
                  </Link>
                  <Link
                    to={`/brands/${brand.id}`}
                    className="flex-1 btn-secondary text-sm py-2 text-center"
                  >
                    View Details
                  </Link>
                </div>
              </div>
            </Card>
          ))}
        </div>
      ) : (
        <EmptyState
          icon={Building2}
          title="No brands yet"
          description="Create your first brand to start generating AI content"
          action={
            <Link to="/brands/new" className="btn-primary">
              Create Your First Brand
            </Link>
          }
        />
      )}

      {/* Delete Confirmation */}
      <ConfirmDialog
        isOpen={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
        title="Delete Brand"
        message={`Are you sure you want to delete "${deleteTarget?.name}"? This action cannot be undone.`}
        confirmText="Delete"
        danger
      />
    </div>
  );
}
