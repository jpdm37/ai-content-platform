import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { 
  Sparkles, Twitter, Instagram, Linkedin, Facebook, Video, Image, 
  MessageSquare, Hash, Zap, ArrowRight, TrendingUp, Building2,
  ChevronRight, Info, AlertCircle
} from 'lucide-react';
import { studioApi, brandsApi, loraApi, trendsApi } from '../../services/api';
import { Card, LoadingState, Spinner, Badge } from '../../components/ui';
import toast from 'react-hot-toast';

const platforms = [
  { id: 'instagram', name: 'Instagram', icon: Instagram },
  { id: 'twitter', name: 'Twitter/X', icon: Twitter },
  { id: 'linkedin', name: 'LinkedIn', icon: Linkedin },
  { id: 'facebook', name: 'Facebook', icon: Facebook },
];

const contentTypes = [
  { id: 'caption', name: 'Captions', icon: MessageSquare, description: 'Multiple caption variations', default: true },
  { id: 'hashtags', name: 'Hashtags', icon: Hash, description: 'Optimized hashtag sets', default: true },
  { id: 'hook', name: 'Hooks', icon: Zap, description: 'Attention-grabbing openers' },
  { id: 'cta', name: 'CTAs', icon: ArrowRight, description: 'Call to action phrases' },
  { id: 'image', name: 'Images', icon: Image, description: 'AI-generated visuals', default: true },
];

const tones = [
  { id: 'professional', name: 'Professional', emoji: '💼', description: 'Business-appropriate' },
  { id: 'casual', name: 'Casual', emoji: '😊', description: 'Friendly and relaxed' },
  { id: 'humorous', name: 'Humorous', emoji: '😄', description: 'Fun and witty' },
  { id: 'inspirational', name: 'Inspirational', emoji: '✨', description: 'Motivating and uplifting' },
  { id: 'educational', name: 'Educational', emoji: '📚', description: 'Informative and helpful' },
  { id: 'urgent', name: 'Urgent', emoji: '🚨', description: 'Time-sensitive, action-focused' },
];

export default function StudioCreate() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [brands, setBrands] = useState([]);
  const [loraModels, setLoraModels] = useState([]);
  const [suggestedTrends, setSuggestedTrends] = useState([]);
  const [showTrendSuggestions, setShowTrendSuggestions] = useState(false);

  // Get trend from URL params
  const trendFromUrl = searchParams.get('trend');
  const trendId = searchParams.get('trend_id');

  const [formData, setFormData] = useState({
    brief: trendFromUrl || '',
    name: '',
    target_platforms: ['instagram'],
    content_types: ['caption', 'hashtags', 'image'],
    tone: 'professional',
    num_variations: 3,
    brand_id: '',
    include_video: false,
    lora_model_id: '',
    video_duration: '30s'
  });

  useEffect(() => { 
    fetchData(); 
  }, []);

  // Auto-generate name from brief
  useEffect(() => {
    if (formData.brief && !formData.name) {
      const autoName = formData.brief.slice(0, 50).split(' ').slice(0, 5).join(' ');
      setFormData(prev => ({ ...prev, name: autoName }));
    }
  }, [formData.brief]);

  const fetchData = async () => {
    try {
      const [brandsRes, loraRes, trendsRes] = await Promise.all([
        brandsApi.list(),
        loraApi.listModels(),
        trendsApi.getTop({ limit: 5 }).catch(() => ({ data: [] })),
      ]);
      
      const brandsList = brandsRes.data || [];
      const completedModels = (loraRes.data || []).filter(m => m.status === 'completed');
      
      setBrands(brandsList);
      setLoraModels(completedModels);
      setSuggestedTrends(trendsRes.data || []);
      
      // Auto-select first brand if available
      if (brandsList.length > 0 && !formData.brand_id) {
        const firstBrandId = brandsList[0].id;
        setFormData(prev => ({ ...prev, brand_id: firstBrandId.toString() }));
        
        // Auto-select matching LoRA model for this brand
        const matchingModel = completedModels.find(m => m.brand_id === firstBrandId);
        if (matchingModel) {
          setFormData(prev => ({ ...prev, lora_model_id: matchingModel.id.toString() }));
        }
      }
    } catch (err) { 
      console.error(err); 
    }
    setLoading(false);
  };

  // When brand changes, auto-select matching LoRA model
  const handleBrandChange = (brandId) => {
    setFormData(prev => ({ ...prev, brand_id: brandId }));
    
    const matchingModel = loraModels.find(m => m.brand_id === parseInt(brandId));
    if (matchingModel) {
      setFormData(prev => ({ ...prev, lora_model_id: matchingModel.id.toString() }));
    } else {
      setFormData(prev => ({ ...prev, lora_model_id: '' }));
    }
  };

  const togglePlatform = (id) => {
    setFormData(prev => ({
      ...prev,
      target_platforms: prev.target_platforms.includes(id)
        ? prev.target_platforms.filter(p => p !== id)
        : [...prev.target_platforms, id]
    }));
  };

  const toggleContentType = (id) => {
    setFormData(prev => ({
      ...prev,
      content_types: prev.content_types.includes(id)
        ? prev.content_types.filter(c => c !== id)
        : [...prev.content_types, id]
    }));
  };

  const useTrendAsBrief = (trend) => {
    setFormData(prev => ({ 
      ...prev, 
      brief: trend.title,
      name: trend.title.slice(0, 50)
    }));
    setShowTrendSuggestions(false);
  };

  const handleSubmit = async () => {
    if (!formData.brief.trim()) {
      toast.error('Please describe what content you want to create');
      return;
    }
    if (formData.target_platforms.length === 0) {
      toast.error('Please select at least one platform');
      return;
    }
    if (formData.content_types.length === 0) {
      toast.error('Please select at least one content type');
      return;
    }

    setCreating(true);
    try {
      const payload = {
        brief: formData.brief,
        name: formData.name || formData.brief.slice(0, 50),
        target_platforms: formData.target_platforms,
        content_types: formData.content_types,
        tone: formData.tone,
        num_variations: formData.num_variations,
        include_video: formData.include_video,
        video_duration: formData.video_duration,
      };

      if (formData.brand_id) payload.brand_id = parseInt(formData.brand_id);
      if (formData.lora_model_id) payload.lora_model_id = parseInt(formData.lora_model_id);

      const res = await studioApi.createProject(payload);
      toast.success('Project created! Generating content...');
      navigate(`/studio/${res.data.id}`);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to create project');
    }
    setCreating(false);
  };

  if (loading) return <LoadingState message="Loading..." />;

  const selectedBrand = brands.find(b => b.id === parseInt(formData.brand_id));
  const selectedModel = loraModels.find(m => m.id === parseInt(formData.lora_model_id));

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="page-title">Create Content</h1>
        <p className="text-silver mt-1">
          Generate captions, images, hashtags, and more from a single brief
        </p>
      </div>

      {/* Trend Banner (if coming from trends) */}
      {trendFromUrl && (
        <Card className="p-4 bg-gradient-to-r from-success/10 to-transparent border-success/30">
          <div className="flex items-center gap-3">
            <TrendingUp className="w-5 h-5 text-success" />
            <div className="flex-1">
              <p className="text-sm text-silver">Creating content about trending topic:</p>
              <p className="text-pearl font-medium">{trendFromUrl}</p>
            </div>
            <Badge variant="success">Trending</Badge>
          </div>
        </Card>
      )}

      {/* Setup Warning */}
      {brands.length === 0 && (
        <Card className="p-4 bg-warning/10 border-warning/30">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-warning mt-0.5" />
            <div>
              <p className="text-pearl font-medium">Create a brand first</p>
              <p className="text-silver text-sm mb-2">
                Brands help maintain consistent voice and style across your content.
              </p>
              <button
                onClick={() => navigate('/brands/new')}
                className="text-sm text-accent hover:underline"
              >
                Create your first brand →
              </button>
            </div>
          </div>
        </Card>
      )}

      {/* Main Form */}
      <Card className="p-6 space-y-6">
        {/* Brief Input */}
        <div>
          <label className="block text-pearl font-medium mb-2">
            What do you want to create content about? *
          </label>
          <div className="relative">
            <textarea
              value={formData.brief}
              onChange={(e) => setFormData({ ...formData, brief: e.target.value })}
              placeholder="e.g., Our new summer collection featuring sustainable fabrics..."
              rows={3}
              className="input-field w-full resize-none"
            />
            {!formData.brief && suggestedTrends.length > 0 && (
              <button
                onClick={() => setShowTrendSuggestions(!showTrendSuggestions)}
                className="absolute bottom-3 right-3 text-xs text-accent hover:underline flex items-center gap-1"
              >
                <TrendingUp className="w-3 h-3" />
                Use a trending topic
              </button>
            )}
          </div>
          
          {/* Trend Suggestions Dropdown */}
          {showTrendSuggestions && (
            <div className="mt-2 p-3 bg-slate rounded-lg border border-graphite">
              <p className="text-xs text-silver mb-2 font-medium">Trending topics:</p>
              <div className="space-y-2">
                {suggestedTrends.map(trend => (
                  <button
                    key={trend.id}
                    onClick={() => useTrendAsBrief(trend)}
                    className="w-full text-left p-2 rounded-lg hover:bg-graphite transition-colors flex items-center gap-2"
                  >
                    <span className="text-pearl text-sm flex-1 truncate">{trend.title}</span>
                    <ChevronRight className="w-4 h-4 text-silver" />
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Brand & Avatar Selection */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-pearl font-medium mb-2">Brand</label>
            <select
              value={formData.brand_id}
              onChange={(e) => handleBrandChange(e.target.value)}
              className="input-field w-full"
            >
              <option value="">No brand (generic content)</option>
              {brands.map(brand => (
                <option key={brand.id} value={brand.id}>{brand.name}</option>
              ))}
            </select>
            {selectedBrand && (
              <p className="text-xs text-silver mt-1">
                Voice: {selectedBrand.description?.slice(0, 50) || 'No description'}...
              </p>
            )}
          </div>

          <div>
            <label className="block text-pearl font-medium mb-2">
              AI Avatar
              <span className="text-silver font-normal text-sm ml-2">(for images)</span>
            </label>
            <select
              value={formData.lora_model_id}
              onChange={(e) => setFormData({ ...formData, lora_model_id: e.target.value })}
              className="input-field w-full"
              disabled={loraModels.length === 0}
            >
              <option value="">No avatar (stock images)</option>
              {loraModels.map(model => (
                <option key={model.id} value={model.id}>
                  {model.name} {model.brand_id === parseInt(formData.brand_id) ? '✓' : ''}
                </option>
              ))}
            </select>
            {loraModels.length === 0 && (
              <button
                onClick={() => navigate('/lora/new')}
                className="text-xs text-accent hover:underline mt-1"
              >
                Train your first AI avatar →
              </button>
            )}
            {selectedModel && (
              <p className="text-xs text-success mt-1 flex items-center gap-1">
                <Sparkles className="w-3 h-3" />
                Images will feature your AI avatar
              </p>
            )}
          </div>
        </div>

        {/* Platforms */}
        <div>
          <label className="block text-pearl font-medium mb-2">Target Platforms *</label>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {platforms.map(platform => {
              const Icon = platform.icon;
              const selected = formData.target_platforms.includes(platform.id);
              return (
                <button
                  key={platform.id}
                  type="button"
                  onClick={() => togglePlatform(platform.id)}
                  className={`flex items-center gap-2 p-3 rounded-xl border transition-all
                            ${selected 
                              ? 'border-accent bg-accent/10 text-accent' 
                              : 'border-graphite hover:border-silver text-silver hover:text-pearl'
                            }`}
                >
                  <Icon className="w-5 h-5" />
                  <span className="font-medium">{platform.name}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Content Types */}
        <div>
          <label className="block text-pearl font-medium mb-2">Content to Generate *</label>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {contentTypes.map(type => {
              const Icon = type.icon;
              const selected = formData.content_types.includes(type.id);
              return (
                <button
                  key={type.id}
                  type="button"
                  onClick={() => toggleContentType(type.id)}
                  className={`flex flex-col items-start p-3 rounded-xl border transition-all
                            ${selected 
                              ? 'border-accent bg-accent/10' 
                              : 'border-graphite hover:border-silver'
                            }`}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <Icon className={`w-4 h-4 ${selected ? 'text-accent' : 'text-silver'}`} />
                    <span className={`font-medium ${selected ? 'text-accent' : 'text-pearl'}`}>
                      {type.name}
                    </span>
                  </div>
                  <span className="text-xs text-silver">{type.description}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Tone */}
        <div>
          <label className="block text-pearl font-medium mb-2">Tone</label>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {tones.map(tone => {
              const selected = formData.tone === tone.id;
              return (
                <button
                  key={tone.id}
                  type="button"
                  onClick={() => setFormData({ ...formData, tone: tone.id })}
                  className={`flex items-center gap-2 p-3 rounded-xl border transition-all
                            ${selected 
                              ? 'border-accent bg-accent/10' 
                              : 'border-graphite hover:border-silver'
                            }`}
                >
                  <span className="text-xl">{tone.emoji}</span>
                  <div className="text-left">
                    <span className={`font-medium block ${selected ? 'text-accent' : 'text-pearl'}`}>
                      {tone.name}
                    </span>
                    <span className="text-xs text-silver">{tone.description}</span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Variations */}
        <div>
          <label className="block text-pearl font-medium mb-2">
            Number of Variations
            <span className="text-silver font-normal text-sm ml-2">(for captions & images)</span>
          </label>
          <div className="flex gap-3">
            {[2, 3, 5].map(num => (
              <button
                key={num}
                type="button"
                onClick={() => setFormData({ ...formData, num_variations: num })}
                className={`px-4 py-2 rounded-lg border transition-all
                          ${formData.num_variations === num
                            ? 'border-accent bg-accent/10 text-accent'
                            : 'border-graphite text-silver hover:border-silver hover:text-pearl'
                          }`}
              >
                {num}
              </button>
            ))}
          </div>
        </div>
      </Card>

      {/* Summary & Submit */}
      <Card className="p-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h3 className="text-pearl font-medium">Ready to generate?</h3>
            <p className="text-silver text-sm">
              {formData.content_types.length} content types × {formData.num_variations} variations
              {selectedModel && ' with AI avatar'}
            </p>
          </div>
          <button
            onClick={handleSubmit}
            disabled={creating || !formData.brief.trim()}
            className="btn-primary flex items-center gap-2 px-8"
          >
            {creating ? (
              <>
                <Spinner size="sm" />
                Creating...
              </>
            ) : (
              <>
                <Sparkles className="w-5 h-5" />
                Generate Content
              </>
            )}
          </button>
        </div>
      </Card>
    </div>
  );
}
