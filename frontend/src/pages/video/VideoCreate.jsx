import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Video, Mic, User, Sparkles, Wand2 } from 'lucide-react';
import { videoApi, loraApi, brandsApi } from '../../services/api';
import { Card, LoadingState, Spinner } from '../../components/ui';
import toast from 'react-hot-toast';

const aspectRatios = [
  { id: '9:16', name: 'Portrait', desc: 'TikTok, Reels' },
  { id: '16:9', name: 'Landscape', desc: 'YouTube' },
  { id: '1:1', name: 'Square', desc: 'Instagram' },
];

const expressions = [
  { id: 'neutral', name: 'Neutral' },
  { id: 'happy', name: 'Happy' },
  { id: 'serious', name: 'Serious' },
  { id: 'excited', name: 'Excited' },
];

export default function VideoCreate() {
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [loraModels, setLoraModels] = useState([]);
  const [brands, setBrands] = useState([]);
  const [voices, setVoices] = useState([]);
  const [costEstimate, setCostEstimate] = useState(null);

  const [formData, setFormData] = useState({
    script: '',
    title: '',
    lora_model_id: '',
    avatar_image_url: '',
    avatar_prompt: '',
    voice_provider: 'elevenlabs',
    voice_id: '',
    aspect_ratio: '9:16',
    expression: 'neutral',
    head_movement: 'natural',
    eye_contact: true,
    background_color: '#000000',
    brand_id: ''
  });

  const [avatarSource, setAvatarSource] = useState('lora');

  useEffect(() => { fetchData(); }, []);

  useEffect(() => {
    if (formData.script.length > 10) estimateCost();
    else setCostEstimate(null);
  }, [formData.script, avatarSource]);

  const fetchData = async () => {
    try {
      const [loraRes, brandsRes, voicesRes] = await Promise.all([
        loraApi.listModels(),
        brandsApi.list(),
        videoApi.listVoices()
      ]);
      setLoraModels(loraRes.data.filter(m => m.status === 'completed'));
      setBrands(brandsRes.data);
      setVoices(voicesRes.data);
      if (voicesRes.data?.[0]?.voices?.[0]) {
        setFormData(prev => ({ ...prev, voice_id: voicesRes.data[0].voices[0].id }));
      }
    } catch (err) { toast.error('Failed to load data'); }
    setLoading(false);
  };

  const estimateCost = async () => {
    try {
      const res = await videoApi.estimateCost({ script: formData.script, generate_avatar: avatarSource !== 'url' });
      setCostEstimate(res.data);
    } catch (err) {}
  };

  const handleGenerate = async () => {
    if (!formData.script.trim()) return toast.error('Please enter a script');
    if (avatarSource === 'lora' && !formData.lora_model_id) return toast.error('Please select a LoRA model');
    if (avatarSource === 'url' && !formData.avatar_image_url) return toast.error('Please enter an image URL');
    if (avatarSource === 'prompt' && !formData.avatar_prompt) return toast.error('Please enter a prompt');

    setGenerating(true);
    try {
      const payload = {
        script: formData.script,
        title: formData.title || undefined,
        voice_provider: formData.voice_provider,
        voice_id: formData.voice_id || undefined,
        aspect_ratio: formData.aspect_ratio,
        expression: formData.expression,
        head_movement: formData.head_movement,
        eye_contact: formData.eye_contact,
        background_color: formData.background_color,
        brand_id: formData.brand_id ? parseInt(formData.brand_id) : undefined,
        ...(avatarSource === 'lora' && { lora_model_id: parseInt(formData.lora_model_id) }),
        ...(avatarSource === 'url' && { avatar_image_url: formData.avatar_image_url }),
        ...(avatarSource === 'prompt' && { avatar_prompt: formData.avatar_prompt }),
      };

      const res = await videoApi.generate(payload);
      toast.success('Video generation started!');
      window.location.href = `/video/${res.data.id}`;
    } catch (err) { toast.error(err.response?.data?.detail || 'Generation failed'); }
    setGenerating(false);
  };

  if (loading) return <LoadingState message="Loading..." />;

  const selectedVoices = voices.find(v => v.provider === formData.voice_provider)?.voices || [];

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="page-title flex items-center gap-3"><Video className="w-8 h-8 text-accent" />Create Video</h1>
        <p className="text-silver mt-1">Generate AI avatar videos with lip-sync</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          {/* Script */}
          <Card className="p-6">
            <h2 className="section-title mb-4">Script</h2>
            <input type="text" value={formData.title} onChange={(e) => setFormData({ ...formData, title: e.target.value })} placeholder="Video title (optional)" className="input-field mb-3" />
            <textarea value={formData.script} onChange={(e) => setFormData({ ...formData, script: e.target.value })} placeholder="Enter what your avatar will say..." className="input-field min-h-[180px]" maxLength={5000} />
            <div className="flex justify-between text-xs text-silver mt-1">
              <span>{formData.script.length}/5000</span>
              <span>~{Math.ceil(formData.script.split(' ').length / 150)} min</span>
            </div>
          </Card>

          {/* Avatar */}
          <Card className="p-6">
            <h2 className="section-title mb-4">Avatar</h2>
            <div className="flex gap-2 mb-4">
              {[{ id: 'lora', label: 'LoRA Model', icon: Sparkles }, { id: 'url', label: 'Image URL', icon: User }, { id: 'prompt', label: 'Generate', icon: Wand2 }].map(opt => (
                <button key={opt.id} onClick={() => setAvatarSource(opt.id)} className={`flex-1 p-3 rounded-xl border-2 transition-all ${avatarSource === opt.id ? 'border-accent bg-accent/10' : 'border-graphite'}`}>
                  <opt.icon className={`w-5 h-5 mx-auto mb-1 ${avatarSource === opt.id ? 'text-accent' : 'text-silver'}`} />
                  <span className="text-sm">{opt.label}</span>
                </button>
              ))}
            </div>

            {avatarSource === 'lora' && (
              loraModels.length === 0 ? (
                <div className="bg-slate rounded-lg p-4 text-center">
                  <p className="text-silver mb-2">No trained models</p>
                  <Link to="/lora/new" className="text-accent">Train avatar →</Link>
                </div>
              ) : (
                <select value={formData.lora_model_id} onChange={(e) => setFormData({ ...formData, lora_model_id: e.target.value })} className="input-field">
                  <option value="">Select model...</option>
                  {loraModels.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
                </select>
              )
            )}
            {avatarSource === 'url' && <input type="url" value={formData.avatar_image_url} onChange={(e) => setFormData({ ...formData, avatar_image_url: e.target.value })} placeholder="https://..." className="input-field" />}
            {avatarSource === 'prompt' && <textarea value={formData.avatar_prompt} onChange={(e) => setFormData({ ...formData, avatar_prompt: e.target.value })} placeholder="Describe the avatar..." className="input-field min-h-[80px]" />}
          </Card>

          {/* Voice */}
          <Card className="p-6">
            <h2 className="section-title mb-4 flex items-center gap-2"><Mic className="w-5 h-5" />Voice</h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label">Provider</label>
                <select value={formData.voice_provider} onChange={(e) => setFormData({ ...formData, voice_provider: e.target.value, voice_id: '' })} className="input-field">
                  <option value="elevenlabs">ElevenLabs</option>
                  <option value="openai">OpenAI</option>
                </select>
              </div>
              <div>
                <label className="label">Voice</label>
                <select value={formData.voice_id} onChange={(e) => setFormData({ ...formData, voice_id: e.target.value })} className="input-field">
                  {selectedVoices.map(v => <option key={v.id} value={v.id}>{v.name} ({v.gender})</option>)}
                </select>
              </div>
            </div>
          </Card>

          {/* Settings */}
          <Card className="p-6">
            <h2 className="section-title mb-4">Settings</h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label">Aspect Ratio</label>
                <select value={formData.aspect_ratio} onChange={(e) => setFormData({ ...formData, aspect_ratio: e.target.value })} className="input-field">
                  {aspectRatios.map(ar => <option key={ar.id} value={ar.id}>{ar.name} ({ar.desc})</option>)}
                </select>
              </div>
              <div>
                <label className="label">Expression</label>
                <select value={formData.expression} onChange={(e) => setFormData({ ...formData, expression: e.target.value })} className="input-field">
                  {expressions.map(e => <option key={e.id} value={e.id}>{e.name}</option>)}
                </select>
              </div>
              <div>
                <label className="label">Background Color</label>
                <input type="color" value={formData.background_color} onChange={(e) => setFormData({ ...formData, background_color: e.target.value })} className="input-field h-10" />
              </div>
              <div>
                <label className="label">Brand (optional)</label>
                <select value={formData.brand_id} onChange={(e) => setFormData({ ...formData, brand_id: e.target.value })} className="input-field">
                  <option value="">None</option>
                  {brands.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}
                </select>
              </div>
            </div>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {costEstimate && (
            <Card className="p-6">
              <h3 className="section-title mb-4">Cost Estimate</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between"><span className="text-silver">Audio</span><span className="text-pearl">${costEstimate.audio_cost.toFixed(3)}</span></div>
                <div className="flex justify-between"><span className="text-silver">Avatar</span><span className="text-pearl">${costEstimate.avatar_cost.toFixed(3)}</span></div>
                <div className="flex justify-between"><span className="text-silver">Video</span><span className="text-pearl">${costEstimate.video_cost.toFixed(3)}</span></div>
                <div className="flex justify-between"><span className="text-silver">Processing</span><span className="text-pearl">${costEstimate.processing_cost.toFixed(3)}</span></div>
                <hr className="border-graphite" />
                <div className="flex justify-between font-bold"><span className="text-pearl">Total</span><span className="text-accent">${costEstimate.total_cost.toFixed(2)}</span></div>
              </div>
              <p className="text-xs text-silver mt-3">~{Math.ceil(costEstimate.estimated_duration_seconds)}s video</p>
            </Card>
          )}

          <Card className="p-6">
            <button onClick={handleGenerate} disabled={generating || !formData.script} className="btn-primary w-full py-4 text-lg">
              {generating ? <><Spinner size="sm" className="mr-2" />Generating...</> : 'Generate Video'}
            </button>
            <p className="text-xs text-silver text-center mt-3">Usually takes 2-5 minutes</p>
          </Card>

          <Card className="p-4 bg-accent/10 border-accent/30">
            <h4 className="font-medium text-pearl mb-2">💡 Tips</h4>
            <ul className="text-xs text-silver space-y-1">
              <li>• Keep scripts under 2 min for best results</li>
              <li>• Use clear, conversational language</li>
              <li>• LoRA avatars give 95%+ consistency</li>
              <li>• Portrait (9:16) works best for social</li>
            </ul>
          </Card>
        </div>
      </div>
    </div>
  );
}
