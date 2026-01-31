import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  Sparkles,
  Image as ImageIcon,
  Type,
  Wand2,
  ArrowRight,
  Loader2,
  Download,
  Copy,
  Check,
  RefreshCw
} from 'lucide-react';
import { brandsApi, categoriesApi, trendsApi, generateApi } from '../services/api';
import { Card, LoadingState, ErrorState, Badge, Spinner } from '../components/ui';
import toast from 'react-hot-toast';

export default function Generate() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const preselectedBrand = searchParams.get('brand');

  const [brands, setBrands] = useState([]);
  const [categories, setCategories] = useState([]);
  const [trends, setTrends] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [generatedContent, setGeneratedContent] = useState(null);
  const [copied, setCopied] = useState(false);

  const [formData, setFormData] = useState({
    brand_id: preselectedBrand || '',
    category_id: '',
    trend_id: '',
    content_type: 'image',
    custom_prompt: '',
    include_caption: true,
  });

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [brandsRes, categoriesRes] = await Promise.all([
          brandsApi.getAll(),
          categoriesApi.getAll(),
        ]);
        setBrands(brandsRes.data);
        setCategories(categoriesRes.data);
      } catch (err) {
        toast.error('Failed to load data');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  useEffect(() => {
    const fetchTrends = async () => {
      if (formData.category_id) {
        try {
          const res = await trendsApi.getByCategory(formData.category_id, 10);
          setTrends(res.data);
        } catch (err) {
          setTrends([]);
        }
      } else {
        setTrends([]);
      }
    };

    fetchTrends();
  }, [formData.category_id]);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  };

  const handleGenerate = async () => {
    if (!formData.brand_id) {
      toast.error('Please select a brand');
      return;
    }

    setGenerating(true);
    setGeneratedContent(null);

    try {
      const res = await generateApi.content({
        brand_id: parseInt(formData.brand_id),
        category_id: formData.category_id ? parseInt(formData.category_id) : null,
        trend_id: formData.trend_id ? parseInt(formData.trend_id) : null,
        content_type: formData.content_type,
        custom_prompt: formData.custom_prompt || null,
        include_caption: formData.include_caption,
      });

      setGeneratedContent(res.data);
      toast.success('Content generated successfully!');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Generation failed');
    } finally {
      setGenerating(false);
    }
  };

  const handleGenerateAvatar = async () => {
    if (!formData.brand_id) {
      toast.error('Please select a brand');
      return;
    }

    setGenerating(true);
    setGeneratedContent(null);

    try {
      const res = await generateApi.avatar({
        brand_id: parseInt(formData.brand_id),
        custom_prompt: formData.custom_prompt || null,
      });

      setGeneratedContent(res.data);
      toast.success('Avatar generated successfully!');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Avatar generation failed');
    } finally {
      setGenerating(false);
    }
  };

  const handleCopyCaption = () => {
    if (generatedContent?.caption) {
      navigator.clipboard.writeText(generatedContent.caption);
      setCopied(true);
      toast.success('Caption copied!');
      setTimeout(() => setCopied(false), 2000);
    }
  };

  if (loading) return <LoadingState message="Loading..." />;

  const selectedBrand = brands.find(b => b.id === parseInt(formData.brand_id));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="page-title flex items-center gap-3">
          <Sparkles className="w-8 h-8 text-accent" />
          Generate Content
        </h1>
        <p className="text-silver mt-1">Create AI-powered images and captions for your brands</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Form */}
        <Card className="p-6 space-y-6">
          <h2 className="section-title">Configuration</h2>

          {/* Brand Selection */}
          <div>
            <label className="label">Select Brand *</label>
            <select
              name="brand_id"
              value={formData.brand_id}
              onChange={handleChange}
              className="input-field"
              required
            >
              <option value="">Choose a brand...</option>
              {brands.map((brand) => (
                <option key={brand.id} value={brand.id}>
                  {brand.name} {brand.persona_name ? `(${brand.persona_name})` : ''}
                </option>
              ))}
            </select>
            {brands.length === 0 && (
              <p className="text-silver text-sm mt-2">
                No brands available.{' '}
                <button
                  onClick={() => navigate('/brands/new')}
                  className="text-accent hover:underline"
                >
                  Create one
                </button>
              </p>
            )}
          </div>

          {/* Content Type */}
          <div>
            <label className="label">Content Type</label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setFormData(prev => ({ ...prev, content_type: 'image' }))}
                className={`p-4 rounded-xl border flex flex-col items-center gap-2 transition-all
                          ${formData.content_type === 'image'
                    ? 'bg-accent/10 border-accent text-pearl'
                    : 'bg-slate border-graphite text-silver hover:border-silver/50'
                  }`}
              >
                <ImageIcon className="w-6 h-6" />
                <span className="font-medium">Image</span>
              </button>
              <button
                type="button"
                onClick={() => setFormData(prev => ({ ...prev, content_type: 'text' }))}
                className={`p-4 rounded-xl border flex flex-col items-center gap-2 transition-all
                          ${formData.content_type === 'text'
                    ? 'bg-accent/10 border-accent text-pearl'
                    : 'bg-slate border-graphite text-silver hover:border-silver/50'
                  }`}
              >
                <Type className="w-6 h-6" />
                <span className="font-medium">Text Only</span>
              </button>
            </div>
          </div>

          {/* Category Selection */}
          <div>
            <label className="label">Category (Optional)</label>
            <select
              name="category_id"
              value={formData.category_id}
              onChange={handleChange}
              className="input-field"
            >
              <option value="">No specific category</option>
              {categories.map((cat) => (
                <option key={cat.id} value={cat.id}>{cat.name}</option>
              ))}
            </select>
          </div>

          {/* Trend Selection */}
          {trends.length > 0 && (
            <div>
              <label className="label">Use Trending Topic (Optional)</label>
              <select
                name="trend_id"
                value={formData.trend_id}
                onChange={handleChange}
                className="input-field"
              >
                <option value="">No specific trend</option>
                {trends.map((trend) => (
                  <option key={trend.id} value={trend.id}>
                    {trend.title} (Score: {trend.popularity_score})
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Custom Prompt */}
          <div>
            <label className="label">Custom Prompt (Optional)</label>
            <textarea
              name="custom_prompt"
              value={formData.custom_prompt}
              onChange={handleChange}
              placeholder="Add custom instructions for the AI..."
              rows={3}
              className="input-field"
            />
          </div>

          {/* Include Caption */}
          {formData.content_type === 'image' && (
            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                name="include_caption"
                checked={formData.include_caption}
                onChange={handleChange}
                id="include_caption"
                className="w-5 h-5 rounded border-graphite bg-slate text-accent 
                         focus:ring-accent focus:ring-offset-0"
              />
              <label htmlFor="include_caption" className="text-pearl cursor-pointer">
                Generate caption with hashtags
              </label>
            </div>
          )}

          {/* Generate Buttons */}
          <div className="flex gap-3 pt-4">
            <button
              onClick={handleGenerate}
              disabled={generating || !formData.brand_id}
              className="flex-1 btn-primary flex items-center justify-center gap-2 py-3"
            >
              {generating ? (
                <>
                  <Spinner size="sm" />
                  Generating...
                </>
              ) : (
                <>
                  <Wand2 className="w-5 h-5" />
                  Generate Content
                </>
              )}
            </button>
          </div>

          {/* Generate Avatar Button */}
          {formData.brand_id && (
            <button
              onClick={handleGenerateAvatar}
              disabled={generating}
              className="w-full btn-secondary flex items-center justify-center gap-2"
            >
              <Sparkles className="w-4 h-4" />
              Generate Brand Avatar
            </button>
          )}
        </Card>

        {/* Preview / Result */}
        <Card className="p-6">
          <h2 className="section-title mb-6">Result</h2>

          {generating && (
            <div className="flex flex-col items-center justify-center py-20">
              <div className="w-20 h-20 rounded-full bg-accent/10 flex items-center justify-center mb-6">
                <Loader2 className="w-10 h-10 text-accent animate-spin" />
              </div>
              <p className="text-pearl font-medium mb-2">Generating your content...</p>
              <p className="text-silver text-sm">This may take a few seconds</p>
            </div>
          )}

          {!generating && !generatedContent && (
            <div className="flex flex-col items-center justify-center py-20 text-center">
              <div className="w-20 h-20 rounded-full bg-slate flex items-center justify-center mb-6">
                <Sparkles className="w-10 h-10 text-silver" />
              </div>
              <p className="text-pearl font-medium mb-2">Ready to generate</p>
              <p className="text-silver text-sm">
                Configure your settings and click generate
              </p>
            </div>
          )}

          {!generating && generatedContent && (
            <div className="space-y-6">
              {/* Status */}
              <div className="flex items-center justify-between">
                <Badge
                  variant={
                    generatedContent.status === 'completed' ? 'success' :
                      generatedContent.status === 'failed' ? 'error' : 'warning'
                  }
                >
                  {generatedContent.status}
                </Badge>
                <button
                  onClick={handleGenerate}
                  className="text-accent hover:text-accent-light flex items-center gap-1 text-sm"
                >
                  <RefreshCw className="w-4 h-4" />
                  Regenerate
                </button>
              </div>

              {/* Image */}
              {generatedContent.result_url && (
                <div className="relative group">
                  <img
                    src={generatedContent.result_url}
                    alt="Generated content"
                    className="w-full rounded-xl"
                  />
                  <div className="absolute inset-0 bg-midnight/60 opacity-0 group-hover:opacity-100 
                                transition-opacity flex items-center justify-center gap-4 rounded-xl">
                    <a
                      href={generatedContent.result_url}
                      download
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-3 bg-accent rounded-full text-white hover:bg-accent-light transition-colors"
                    >
                      <Download className="w-5 h-5" />
                    </a>
                  </div>
                </div>
              )}

              {/* Caption */}
              {generatedContent.caption && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <label className="label mb-0">Caption</label>
                    <button
                      onClick={handleCopyCaption}
                      className="text-accent hover:text-accent-light flex items-center gap-1 text-sm"
                    >
                      {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                      {copied ? 'Copied!' : 'Copy'}
                    </button>
                  </div>
                  <div className="p-4 bg-slate rounded-xl">
                    <p className="text-pearl whitespace-pre-wrap">{generatedContent.caption}</p>
                  </div>
                </div>
              )}

              {/* Hashtags */}
              {generatedContent.hashtags && generatedContent.hashtags.length > 0 && (
                <div className="space-y-3">
                  <label className="label mb-0">Hashtags</label>
                  <div className="flex flex-wrap gap-2">
                    {generatedContent.hashtags.map((tag, i) => (
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

              {/* Prompt Used */}
              {generatedContent.prompt_used && (
                <div className="space-y-3">
                  <label className="label mb-0">Prompt Used</label>
                  <div className="p-4 bg-slate rounded-xl">
                    <p className="text-silver text-sm">{generatedContent.prompt_used}</p>
                  </div>
                </div>
              )}

              {/* Error Message */}
              {generatedContent.error_message && (
                <div className="p-4 bg-error/10 border border-error/30 rounded-xl">
                  <p className="text-error text-sm">{generatedContent.error_message}</p>
                </div>
              )}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
