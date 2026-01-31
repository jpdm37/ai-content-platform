import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Sparkles, Twitter, Instagram, Linkedin, Facebook, Video, Image, MessageSquare, Hash, Zap, ArrowRight } from 'lucide-react';
import { studioApi, brandsApi, loraApi } from '../../services/api';
import { Card, LoadingState, Spinner } from '../../components/ui';
import toast from 'react-hot-toast';

const platforms = [
  { id: 'twitter', name: 'Twitter/X', icon: Twitter },
  { id: 'instagram', name: 'Instagram', icon: Instagram },
  { id: 'linkedin', name: 'LinkedIn', icon: Linkedin },
  { id: 'facebook', name: 'Facebook', icon: Facebook },
];

const contentTypes = [
  { id: 'caption', name: 'Captions', icon: MessageSquare, description: 'Multiple variations' },
  { id: 'hashtags', name: 'Hashtags', icon: Hash, description: 'Platform optimized' },
  { id: 'hook', name: 'Hooks', icon: Zap, description: 'Attention grabbers' },
  { id: 'cta', name: 'CTAs', icon: ArrowRight, description: 'Call to actions' },
  { id: 'image', name: 'Images', icon: Image, description: 'AI generated' },
];

const tones = [
  { id: 'professional', name: 'Professional', emoji: '💼' },
  { id: 'casual', name: 'Casual', emoji: '😊' },
  { id: 'humorous', name: 'Humorous', emoji: '😄' },
  { id: 'inspirational', name: 'Inspirational', emoji: '✨' },
  { id: 'educational', name: 'Educational', emoji: '📚' },
  { id: 'urgent', name: 'Urgent', emoji: '🚨' },
];

export default function StudioCreate() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [brands, setBrands] = useState([]);
  const [loraModels, setLoraModels] = useState([]);

  const [formData, setFormData] = useState({
    brief: '',
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

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    try {
      const [brandsRes, loraRes] = await Promise.all([
        brandsApi.list(),
        loraApi.listModels()
      ]);
      setBrands(brandsRes.data);
      setLoraModels(loraRes.data.filter(m => m.status === 'completed'));
    } catch (err) { console.error(err); }
    setLoading(false);
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

  const handleSubmit = async () => {
    if (!formData.brief.trim()) {
      toast.error('Please enter a content brief');
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
        ...formData,
        brand_id: formData.brand_id ? parseInt(formData.brand_id) : undefined,
        lora_model_id: formData.include_video && formData.lora_model_id ? parseInt(formData.lora_model_id) : undefined,
        content_types: formData.include_video ? [...formData.content_types, 'video'] : formData.content_types
      };

      const res = await studioApi.createProject(payload);
      toast.success('Project created! Generating content...');
      navigate(`/studio/${res.data.id}`);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to create project');
    }
    setCreating(false);
  };

  if (loading) return <LoadingState message="Loading..." />;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="page-title flex items-center gap-3">
          <Sparkles className="w-8 h-8 text-accent" />
          Create Content Project
        </h1>
        <p className="text-silver mt-1">Generate a complete content package from one brief</p>
      </div>

      {/* Brief */}
      <Card className="p-6">
        <h2 className="section-title mb-4">Content Brief</h2>
        <div className="space-y-4">
          <div>
            <label className="label">Project Name (optional)</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="e.g., Product Launch Q1"
              className="input-field"
            />
          </div>
          <div>
            <label className="label">What do you want to create content about? *</label>
            <textarea
              value={formData.brief}
              onChange={(e) => setFormData({ ...formData, brief: e.target.value })}
              placeholder="Describe your content idea, product launch, announcement, or topic. The more detail you provide, the better the results..."
              className="input-field min-h-[120px]"
              maxLength={2000}
            />
            <p className="text-xs text-silver mt-1">{formData.brief.length}/2000</p>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">Brand (optional)</label>
              <select
                value={formData.brand_id}
                onChange={(e) => setFormData({ ...formData, brand_id: e.target.value })}
                className="input-field"
              >
                <option value="">No brand</option>
                {brands.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}
              </select>
            </div>
            <div>
              <label className="label">Variations per platform</label>
              <select
                value={formData.num_variations}
                onChange={(e) => setFormData({ ...formData, num_variations: parseInt(e.target.value) })}
                className="input-field"
              >
                {[1, 2, 3, 4, 5].map(n => <option key={n} value={n}>{n} variations</option>)}
              </select>
            </div>
          </div>
        </div>
      </Card>

      {/* Platforms */}
      <Card className="p-6">
        <h2 className="section-title mb-4">Target Platforms *</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {platforms.map(platform => {
            const selected = formData.target_platforms.includes(platform.id);
            return (
              <button
                key={platform.id}
                onClick={() => togglePlatform(platform.id)}
                className={`p-4 rounded-xl border-2 transition-all text-center ${
                  selected ? 'border-accent bg-accent/10' : 'border-graphite hover:border-silver'
                }`}
              >
                <platform.icon className={`w-6 h-6 mx-auto mb-2 ${selected ? 'text-accent' : 'text-silver'}`} />
                <span className={`text-sm ${selected ? 'text-pearl' : 'text-silver'}`}>{platform.name}</span>
              </button>
            );
          })}
        </div>
      </Card>

      {/* Content Types */}
      <Card className="p-6">
        <h2 className="section-title mb-4">Content Types *</h2>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {contentTypes.map(type => {
            const selected = formData.content_types.includes(type.id);
            return (
              <button
                key={type.id}
                onClick={() => toggleContentType(type.id)}
                className={`p-4 rounded-xl border-2 transition-all text-center ${
                  selected ? 'border-accent bg-accent/10' : 'border-graphite hover:border-silver'
                }`}
              >
                <type.icon className={`w-6 h-6 mx-auto mb-2 ${selected ? 'text-accent' : 'text-silver'}`} />
                <span className={`text-sm font-medium ${selected ? 'text-pearl' : 'text-silver'}`}>{type.name}</span>
                <p className="text-xs text-silver mt-1">{type.description}</p>
              </button>
            );
          })}
        </div>
      </Card>

      {/* Tone */}
      <Card className="p-6">
        <h2 className="section-title mb-4">Content Tone</h2>
        <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
          {tones.map(tone => (
            <button
              key={tone.id}
              onClick={() => setFormData({ ...formData, tone: tone.id })}
              className={`p-3 rounded-xl border-2 transition-all text-center ${
                formData.tone === tone.id ? 'border-accent bg-accent/10' : 'border-graphite hover:border-silver'
              }`}
            >
              <span className="text-2xl">{tone.emoji}</span>
              <p className={`text-xs mt-1 ${formData.tone === tone.id ? 'text-pearl' : 'text-silver'}`}>{tone.name}</p>
            </button>
          ))}
        </div>
      </Card>

      {/* Video Option */}
      <Card className="p-6">
        <div className="flex items-start gap-4">
          <div className="flex-1">
            <h2 className="section-title flex items-center gap-2">
              <Video className="w-5 h-5" />
              Include Talking Head Video
            </h2>
            <p className="text-silver text-sm mt-1">Generate a video of your AI avatar presenting the content</p>
          </div>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={formData.include_video}
              onChange={(e) => setFormData({ ...formData, include_video: e.target.checked })}
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-graphite rounded-full peer peer-checked:bg-accent transition-colors after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:after:translate-x-full"></div>
          </label>
        </div>

        {formData.include_video && (
          <div className="mt-4 pt-4 border-t border-graphite grid grid-cols-2 gap-4">
            <div>
              <label className="label">Avatar Model</label>
              {loraModels.length === 0 ? (
                <p className="text-silver text-sm">No trained avatars. <a href="/lora/new" className="text-accent">Train one first</a></p>
              ) : (
                <select
                  value={formData.lora_model_id}
                  onChange={(e) => setFormData({ ...formData, lora_model_id: e.target.value })}
                  className="input-field"
                >
                  <option value="">Select avatar...</option>
                  {loraModels.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
                </select>
              )}
            </div>
            <div>
              <label className="label">Video Duration</label>
              <select
                value={formData.video_duration}
                onChange={(e) => setFormData({ ...formData, video_duration: e.target.value })}
                className="input-field"
              >
                <option value="15s">15 seconds</option>
                <option value="30s">30 seconds</option>
                <option value="60s">60 seconds</option>
              </select>
            </div>
          </div>
        )}
      </Card>

      {/* Submit */}
      <div className="flex items-center justify-between">
        <div className="text-sm text-silver">
          Will generate: {formData.content_types.length} content types × {formData.target_platforms.length} platforms × {formData.num_variations} variations
          {formData.include_video && ' + 1 video'}
        </div>
        <button
          onClick={handleSubmit}
          disabled={creating}
          className="btn-primary px-8 py-3 text-lg"
        >
          {creating ? <><Spinner size="sm" className="mr-2" />Creating...</> : 'Create Project'}
        </button>
      </div>
    </div>
  );
}
