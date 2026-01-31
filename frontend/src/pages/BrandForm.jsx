import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Save, Plus, X, Sparkles } from 'lucide-react';
import { brandsApi, categoriesApi } from '../services/api';
import { Card, LoadingState, Spinner } from '../components/ui';
import toast from 'react-hot-toast';

export default function BrandForm() {
  const { id } = useParams();
  const isEditing = !!id;
  const navigate = useNavigate();

  const [loading, setLoading] = useState(isEditing);
  const [saving, setSaving] = useState(false);
  const [categories, setCategories] = useState([]);
  const [newTrait, setNewTrait] = useState('');
  const [newKeyword, setNewKeyword] = useState('');

  const [formData, setFormData] = useState({
    name: '',
    description: '',
    persona_name: '',
    persona_age: '',
    persona_gender: '',
    persona_style: '',
    persona_voice: '',
    persona_traits: [],
    brand_keywords: [],
    brand_colors: [],
    category_ids: [],
  });

  useEffect(() => {
    const fetchData = async () => {
      try {
        const catRes = await categoriesApi.getAll();
        setCategories(catRes.data);

        if (isEditing) {
          const brandRes = await brandsApi.getById(id);
          const brand = brandRes.data;
          setFormData({
            name: brand.name || '',
            description: brand.description || '',
            persona_name: brand.persona_name || '',
            persona_age: brand.persona_age || '',
            persona_gender: brand.persona_gender || '',
            persona_style: brand.persona_style || '',
            persona_voice: brand.persona_voice || '',
            persona_traits: brand.persona_traits || [],
            brand_keywords: brand.brand_keywords || [],
            brand_colors: brand.brand_colors || [],
            category_ids: [],
          });
        }
      } catch (err) {
        toast.error('Failed to load data');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [id, isEditing]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleAddTrait = () => {
    if (newTrait.trim() && !formData.persona_traits.includes(newTrait.trim())) {
      setFormData((prev) => ({
        ...prev,
        persona_traits: [...prev.persona_traits, newTrait.trim()],
      }));
      setNewTrait('');
    }
  };

  const handleRemoveTrait = (trait) => {
    setFormData((prev) => ({
      ...prev,
      persona_traits: prev.persona_traits.filter((t) => t !== trait),
    }));
  };

  const handleAddKeyword = () => {
    if (newKeyword.trim() && !formData.brand_keywords.includes(newKeyword.trim())) {
      setFormData((prev) => ({
        ...prev,
        brand_keywords: [...prev.brand_keywords, newKeyword.trim()],
      }));
      setNewKeyword('');
    }
  };

  const handleRemoveKeyword = (keyword) => {
    setFormData((prev) => ({
      ...prev,
      brand_keywords: prev.brand_keywords.filter((k) => k !== keyword),
    }));
  };

  const handleCategoryToggle = (categoryId) => {
    setFormData((prev) => ({
      ...prev,
      category_ids: prev.category_ids.includes(categoryId)
        ? prev.category_ids.filter((id) => id !== categoryId)
        : [...prev.category_ids, categoryId],
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.name.trim()) {
      toast.error('Brand name is required');
      return;
    }

    setSaving(true);
    try {
      if (isEditing) {
        await brandsApi.update(id, formData);
        toast.success('Brand updated successfully');
      } else {
        await brandsApi.create(formData);
        toast.success('Brand created successfully');
      }
      navigate('/brands');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to save brand');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <LoadingState message="Loading brand..." />;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <button
          onClick={() => navigate('/brands')}
          className="p-2 text-silver hover:text-pearl transition-colors rounded-lg hover:bg-slate"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div>
          <h1 className="page-title">{isEditing ? 'Edit Brand' : 'Create Brand'}</h1>
          <p className="text-silver mt-1">
            {isEditing ? 'Update your brand profile and AI persona' : 'Set up a new AI persona for content generation'}
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Basic Info */}
        <Card className="p-6">
          <h2 className="section-title mb-6">Basic Information</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="md:col-span-2">
              <label className="label">Brand Name *</label>
              <input
                type="text"
                name="name"
                value={formData.name}
                onChange={handleChange}
                placeholder="e.g., TechStyle Co"
                className="input-field"
                required
              />
            </div>
            <div className="md:col-span-2">
              <label className="label">Description</label>
              <textarea
                name="description"
                value={formData.description}
                onChange={handleChange}
                placeholder="Describe your brand and what it represents..."
                rows={3}
                className="input-field"
              />
            </div>
          </div>
        </Card>

        {/* AI Persona */}
        <Card className="p-6">
          <div className="flex items-center gap-2 mb-6">
            <Sparkles className="w-5 h-5 text-accent" />
            <h2 className="section-title">AI Persona</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="label">Persona Name</label>
              <input
                type="text"
                name="persona_name"
                value={formData.persona_name}
                onChange={handleChange}
                placeholder="e.g., Alex"
                className="input-field"
              />
            </div>
            <div>
              <label className="label">Age Range</label>
              <input
                type="text"
                name="persona_age"
                value={formData.persona_age}
                onChange={handleChange}
                placeholder="e.g., late 20s, mid 30s"
                className="input-field"
              />
            </div>
            <div>
              <label className="label">Gender</label>
              <select
                name="persona_gender"
                value={formData.persona_gender}
                onChange={handleChange}
                className="input-field"
              >
                <option value="">Select gender</option>
                <option value="female">Female</option>
                <option value="male">Male</option>
                <option value="non-binary">Non-binary</option>
                <option value="other">Other</option>
              </select>
            </div>
            <div>
              <label className="label">Visual Style</label>
              <input
                type="text"
                name="persona_style"
                value={formData.persona_style}
                onChange={handleChange}
                placeholder="e.g., minimalist, modern fashion, athletic"
                className="input-field"
              />
            </div>
            <div className="md:col-span-2">
              <label className="label">Voice & Tone</label>
              <textarea
                name="persona_voice"
                value={formData.persona_voice}
                onChange={handleChange}
                placeholder="Describe how your AI persona should write and communicate..."
                rows={2}
                className="input-field"
              />
            </div>

            {/* Personality Traits */}
            <div className="md:col-span-2">
              <label className="label">Personality Traits</label>
              <div className="flex gap-2 mb-3">
                <input
                  type="text"
                  value={newTrait}
                  onChange={(e) => setNewTrait(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddTrait())}
                  placeholder="Add a trait..."
                  className="input-field"
                />
                <button
                  type="button"
                  onClick={handleAddTrait}
                  className="btn-secondary px-4"
                >
                  <Plus className="w-4 h-4" />
                </button>
              </div>
              <div className="flex flex-wrap gap-2">
                {formData.persona_traits.map((trait) => (
                  <span
                    key={trait}
                    className="inline-flex items-center gap-1 px-3 py-1 bg-accent/10 text-accent rounded-full text-sm"
                  >
                    {trait}
                    <button
                      type="button"
                      onClick={() => handleRemoveTrait(trait)}
                      className="hover:text-error transition-colors"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                ))}
              </div>
            </div>
          </div>
        </Card>

        {/* Brand Keywords */}
        <Card className="p-6">
          <h2 className="section-title mb-6">Brand Keywords</h2>
          <p className="text-silver text-sm mb-4">
            Add keywords that represent your brand. These will be used in content generation.
          </p>
          <div className="flex gap-2 mb-3">
            <input
              type="text"
              value={newKeyword}
              onChange={(e) => setNewKeyword(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddKeyword())}
              placeholder="Add a keyword..."
              className="input-field"
            />
            <button
              type="button"
              onClick={handleAddKeyword}
              className="btn-secondary px-4"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            {formData.brand_keywords.map((keyword) => (
              <span
                key={keyword}
                className="inline-flex items-center gap-1 px-3 py-1 bg-slate text-pearl rounded-full text-sm"
              >
                {keyword}
                <button
                  type="button"
                  onClick={() => handleRemoveKeyword(keyword)}
                  className="hover:text-error transition-colors"
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            ))}
          </div>
        </Card>

        {/* Categories */}
        <Card className="p-6">
          <h2 className="section-title mb-6">Content Categories</h2>
          <p className="text-silver text-sm mb-4">
            Select the categories this brand will create content for.
          </p>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {categories.map((category) => (
              <button
                key={category.id}
                type="button"
                onClick={() => handleCategoryToggle(category.id)}
                className={`p-4 rounded-xl border transition-all text-left
                          ${formData.category_ids.includes(category.id)
                    ? 'bg-accent/10 border-accent text-pearl'
                    : 'bg-slate border-graphite text-silver hover:border-silver/50'
                  }`}
              >
                <p className="font-medium">{category.name}</p>
                {category.description && (
                  <p className="text-xs mt-1 opacity-70 line-clamp-2">{category.description}</p>
                )}
              </button>
            ))}
          </div>
          {categories.length === 0 && (
            <p className="text-silver text-center py-4">
              No categories available. Create some categories first.
            </p>
          )}
        </Card>

        {/* Submit */}
        <div className="flex gap-4 justify-end">
          <button
            type="button"
            onClick={() => navigate('/brands')}
            className="btn-secondary"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={saving}
            className="btn-primary flex items-center gap-2"
          >
            {saving ? (
              <>
                <Spinner size="sm" />
                Saving...
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                {isEditing ? 'Update Brand' : 'Create Brand'}
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
