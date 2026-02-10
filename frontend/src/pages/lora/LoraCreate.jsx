import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Sparkles, Upload, X, Check, Image as ImageIcon, 
  ChevronRight, ChevronLeft, Plus, Wand2, User, 
  Loader2, RefreshCw, CheckCircle2
} from 'lucide-react';
import { loraApi, brandsApi } from '../../services/api';
import { Card, Badge, Spinner, LoadingState } from '../../components/ui';
import toast from 'react-hot-toast';

const avatarApi = {
  generateConcepts: (data) => fetch('/api/v1/avatar/generate-concepts', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  }).then(r => r.json()),
  generateTrainingImages: (data) => fetch('/api/v1/avatar/generate-training-images', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  }).then(r => r.json()),
  createFromGenerated: (data) => fetch('/api/v1/avatar/create-from-generated', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  }).then(r => r.json()),
};

export default function LoraCreate() {
  const navigate = useNavigate();
  const fileInputRef = useRef(null);
  const [step, setStep] = useState(1);
  const [mode, setMode] = useState(null);
  const [brands, setBrands] = useState([]);
  const [loading, setLoading] = useState(true);
  
  const [formData, setFormData] = useState({
    brand_id: '', name: '', trigger_word: 'AVATAR', training_steps: 1000,
  });

  const [avatarConfig, setAvatarConfig] = useState({
    gender: '', age_range: '', style: 'professional', ethnicity: '',
    hair_color: '', custom_description: ''
  });

  const [generating, setGenerating] = useState(false);
  const [concepts, setConcepts] = useState([]);
  const [selectedConcept, setSelectedConcept] = useState(null);
  const [trainingImages, setTrainingImages] = useState([]);
  const [promptUsed, setPromptUsed] = useState('');
  const [imageUrls, setImageUrls] = useState([]);
  const [imageInput, setImageInput] = useState('');
  const [uploading, setUploading] = useState(false);
  const [creating, setCreating] = useState(false);

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
      const res = await brandsApi.list();
      setBrands(res.data || []);
    } catch (err) { console.error(err); }
    setLoading(false);
  };

  const handleFileUpload = async (e) => {
    const files = Array.from(e.target.files);
    if (!files.length) return;
    setUploading(true);
    const newUrls = [];
    for (const file of files) {
      if (!file.type.startsWith('image/') || file.size > 10*1024*1024) continue;
      try {
        const dataUrl = await new Promise((res, rej) => {
          const r = new FileReader();
          r.onload = () => res(r.result);
          r.onerror = rej;
          r.readAsDataURL(file);
        });
        newUrls.push(dataUrl);
      } catch {}
    }
    setImageUrls([...imageUrls, ...newUrls]);
    setUploading(false);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleGenerateConcepts = async () => {
    if (!avatarConfig.gender || !avatarConfig.age_range) {
      toast.error('Please select gender and age range'); return;
    }
    setGenerating(true); setConcepts([]);
    try {
      const result = await avatarApi.generateConcepts({
        brand_id: parseInt(formData.brand_id), avatar_name: formData.name,
        ...avatarConfig, num_concepts: 4
      });
      if (result.success && result.concepts?.length) {
        setConcepts(result.concepts);
        setPromptUsed(result.prompt_used);
        toast.success('Concepts generated!');
        setStep(3);
      } else toast.error(result.error || 'Failed');
    } catch { toast.error('Generation failed'); }
    setGenerating(false);
  };

  const handleConfirmConcept = async () => {
    if (!selectedConcept) { toast.error('Select an avatar'); return; }
    setGenerating(true);
    try {
      const result = await avatarApi.generateTrainingImages({
        brand_id: parseInt(formData.brand_id), avatar_name: formData.name,
        selected_concept_url: selectedConcept.image_url,
        selected_seed: selectedConcept.seed, original_prompt: promptUsed,
        requirements: avatarConfig, num_training_images: 12
      });
      if (result.success) {
        const all = [selectedConcept.image_url, ...result.training_images.map(i => i.image_url)];
        setTrainingImages(all); setImageUrls(all);
        toast.success('Training images ready!'); setStep(4);
      } else toast.error(result.error || 'Failed');
    } catch { toast.error('Failed'); }
    setGenerating(false);
  };

  const handleCreateModel = async () => {
    setCreating(true);
    try {
      if (mode === 'generate' && trainingImages.length) {
        const result = await avatarApi.createFromGenerated({
          brand_id: parseInt(formData.brand_id), avatar_name: formData.name,
          training_image_urls: trainingImages, trigger_word: formData.trigger_word,
          training_steps: formData.training_steps
        });
        if (result.success) { toast.success('Training started!'); navigate(`/lora/${result.model_id}`); }
        else toast.error(result.message);
      } else {
        const res = await loraApi.createModel({
          brand_id: parseInt(formData.brand_id), name: formData.name,
          trigger_word: formData.trigger_word.toUpperCase().replace(/\s+/g, '_'),
          config: { training_steps: formData.training_steps }
        });
        await loraApi.bulkAddImages(res.data.id, imageUrls);
        const v = await loraApi.validateModel(res.data.id);
        if (v.data.is_ready) {
          await loraApi.startTraining(res.data.id);
          toast.success('Training started!'); navigate(`/lora/${res.data.id}`);
        } else toast.error(v.data.issues?.join(', '));
      }
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed'); }
    setCreating(false);
  };

  if (loading) return <LoadingState message="Loading..." />;

  const styles = ['professional','influencer','corporate','creative','lifestyle','tech','fitness','fashion'];

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="text-center">
        <h1 className="page-title">Create AI Avatar</h1>
        <p className="text-silver mt-1">Train a custom AI model for consistent brand imagery</p>
      </div>

      {/* Step 1: Setup */}
      {step === 1 && (
        <Card className="p-6 space-y-6">
          <h2 className="text-lg font-bold text-pearl flex items-center gap-2">
            <User className="w-5 h-5 text-accent" /> Basic Information
          </h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-pearl mb-1">Brand *</label>
              <select value={formData.brand_id} onChange={e => setFormData({...formData, brand_id: e.target.value})} className="input-field w-full">
                <option value="">Select brand</option>
                {brands.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-pearl mb-1">Avatar Name *</label>
              <input value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})} placeholder="e.g., Luna, Alex" className="input-field w-full" />
            </div>
          </div>
          <button onClick={() => setStep(2)} disabled={!formData.brand_id || !formData.name} className="btn-primary w-full">Continue <ChevronRight className="w-5 h-5 ml-2" /></button>
        </Card>
      )}

      {/* Step 2: Mode Selection */}
      {step === 2 && !mode && (
        <Card className="p-6 space-y-6">
          <h2 className="text-lg font-bold text-pearl">How would you like to create your avatar?</h2>
          <div className="grid grid-cols-2 gap-4">
            <button onClick={() => { setMode('generate'); }} className="p-6 rounded-xl border-2 border-graphite hover:border-accent bg-gradient-to-br from-accent/5 to-transparent text-left">
              <Wand2 className="w-10 h-10 mb-3 text-accent" />
              <h3 className="font-bold text-pearl">Generate New Avatar</h3>
              <p className="text-silver text-sm mt-1">Create from scratch - no photos needed</p>
              <Badge variant="success" className="mt-3">Recommended</Badge>
            </button>
            <button onClick={() => { setMode('upload'); setStep(3); }} className="p-6 rounded-xl border-2 border-graphite hover:border-accent text-left">
              <Upload className="w-10 h-10 mb-3 text-silver" />
              <h3 className="font-bold text-pearl">Upload Photos</h3>
              <p className="text-silver text-sm mt-1">Use existing photos (5-15 images)</p>
            </button>
          </div>
          <button onClick={() => setStep(1)} className="btn-secondary w-full"><ChevronLeft className="w-5 h-5 mr-2" /> Back</button>
        </Card>
      )}

      {/* Step 2: Generate - Design */}
      {step === 2 && mode === 'generate' && (
        <Card className="p-6 space-y-6">
          <h2 className="text-lg font-bold text-pearl flex items-center gap-2"><Wand2 className="w-5 h-5 text-accent" /> Design Your Avatar</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-pearl mb-2">Gender *</label>
              <div className="flex gap-2">
                {['male','female','non-binary'].map(g => (
                  <button key={g} onClick={() => setAvatarConfig({...avatarConfig, gender: g})}
                    className={`flex-1 py-2 rounded-lg border text-sm capitalize ${avatarConfig.gender === g ? 'border-accent bg-accent/10 text-accent' : 'border-graphite text-silver'}`}>{g}</button>
                ))}
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-pearl mb-2">Age *</label>
              <select value={avatarConfig.age_range} onChange={e => setAvatarConfig({...avatarConfig, age_range: e.target.value})} className="input-field w-full">
                <option value="">Select</option>
                {['18-24','25-30','31-40','41-50','51-60'].map(a => <option key={a} value={a}>{a}</option>)}
              </select>
            </div>
            <div className="col-span-2">
              <label className="block text-sm font-medium text-pearl mb-2">Style</label>
              <div className="grid grid-cols-4 gap-2">
                {styles.map(s => (
                  <button key={s} onClick={() => setAvatarConfig({...avatarConfig, style: s})}
                    className={`py-2 rounded-lg border text-sm capitalize ${avatarConfig.style === s ? 'border-accent bg-accent/10 text-accent' : 'border-graphite text-silver'}`}>{s}</button>
                ))}
              </div>
            </div>
            <div>
              <label className="block text-sm text-pearl mb-1">Ethnicity</label>
              <select value={avatarConfig.ethnicity} onChange={e => setAvatarConfig({...avatarConfig, ethnicity: e.target.value})} className="input-field w-full">
                <option value="">Any</option>
                {['caucasian','african','asian','hispanic','middle eastern','south asian','mixed'].map(e => <option key={e} value={e} className="capitalize">{e}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm text-pearl mb-1">Hair Color</label>
              <select value={avatarConfig.hair_color} onChange={e => setAvatarConfig({...avatarConfig, hair_color: e.target.value})} className="input-field w-full">
                <option value="">Any</option>
                {['black','brown','blonde','red','gray'].map(c => <option key={c} value={c} className="capitalize">{c}</option>)}
              </select>
            </div>
            <div className="col-span-2">
              <label className="block text-sm text-pearl mb-1">Additional Details</label>
              <textarea value={avatarConfig.custom_description} onChange={e => setAvatarConfig({...avatarConfig, custom_description: e.target.value})} placeholder="e.g., glasses, beard, athletic..." rows={2} className="input-field w-full resize-none" />
            </div>
          </div>
          <div className="flex gap-3">
            <button onClick={() => setMode(null)} className="btn-secondary flex-1"><ChevronLeft className="w-5 h-5 mr-2" /> Back</button>
            <button onClick={handleGenerateConcepts} disabled={generating || !avatarConfig.gender || !avatarConfig.age_range} className="btn-primary flex-1">
              {generating ? <><Loader2 className="w-5 h-5 animate-spin mr-2" /> Generating...</> : <><Wand2 className="w-5 h-5 mr-2" /> Generate Avatars</>}
            </button>
          </div>
        </Card>
      )}

      {/* Step 3: Generate - Select Concept */}
      {step === 3 && mode === 'generate' && (
        <Card className="p-6 space-y-6">
          <div className="flex justify-between items-center">
            <h2 className="text-lg font-bold text-pearl">Choose Your Avatar</h2>
            <button onClick={() => { setSelectedConcept(null); handleGenerateConcepts(); }} disabled={generating} className="btn-secondary text-sm">
              <RefreshCw className={`w-4 h-4 mr-1 ${generating ? 'animate-spin' : ''}`} /> Regenerate
            </button>
          </div>
          {generating && !concepts.length ? (
            <div className="py-12 text-center"><Loader2 className="w-12 h-12 mx-auto text-accent animate-spin mb-4" /><p className="text-pearl">Generating concepts...</p></div>
          ) : (
            <div className="grid grid-cols-2 gap-4">
              {concepts.map((c, i) => (
                <button key={i} onClick={() => setSelectedConcept(c)} className={`relative aspect-square rounded-xl overflow-hidden border-4 ${selectedConcept?.index === c.index ? 'border-accent ring-4 ring-accent/30' : 'border-transparent hover:border-accent/50'}`}>
                  <img src={c.image_url} alt="" className="w-full h-full object-cover" />
                  {selectedConcept?.index === c.index && <div className="absolute top-3 right-3 w-8 h-8 bg-accent rounded-full flex items-center justify-center"><Check className="w-5 h-5 text-white" /></div>}
                </button>
              ))}
            </div>
          )}
          <div className="flex gap-3">
            <button onClick={() => setStep(2)} className="btn-secondary flex-1"><ChevronLeft className="w-5 h-5 mr-2" /> Adjust</button>
            <button onClick={handleConfirmConcept} disabled={!selectedConcept || generating} className="btn-primary flex-1">
              {generating ? <><Loader2 className="w-5 h-5 animate-spin mr-2" /> Creating...</> : <>Use This <ChevronRight className="w-5 h-5 ml-2" /></>}
            </button>
          </div>
        </Card>
      )}

      {/* Step 3: Upload Mode */}
      {step === 3 && mode === 'upload' && (
        <Card className="p-6 space-y-6">
          <h2 className="text-lg font-bold text-pearl">Upload Training Images</h2>
          <div className="border-2 border-dashed border-graphite rounded-xl p-6 text-center hover:border-accent">
            <input ref={fileInputRef} type="file" multiple accept="image/*" onChange={handleFileUpload} className="hidden" id="upload" />
            <label htmlFor="upload" className="cursor-pointer">
              {uploading ? <Loader2 className="w-10 h-10 mx-auto mb-3 text-accent animate-spin" /> : <Upload className="w-10 h-10 mx-auto mb-3 text-silver" />}
              <p className="text-pearl">Click to upload</p>
            </label>
          </div>
          <div className="flex gap-2">
            <input value={imageInput} onChange={e => setImageInput(e.target.value)} placeholder="Or paste URL..." className="input-field flex-1" />
            <button onClick={() => { if (imageInput) { setImageUrls([...imageUrls, imageInput]); setImageInput(''); }}} className="btn-secondary px-4"><Plus className="w-5 h-5" /></button>
          </div>
          {imageUrls.length > 0 && (
            <div className="grid grid-cols-5 gap-2">
              {imageUrls.map((u, i) => (
                <div key={i} className="relative aspect-square group">
                  <img src={u} className="w-full h-full object-cover rounded-lg" />
                  <button onClick={() => setImageUrls(imageUrls.filter((_, j) => j !== i))} className="absolute -top-2 -right-2 w-6 h-6 bg-error rounded-full opacity-0 group-hover:opacity-100"><X className="w-4 h-4 text-white mx-auto" /></button>
                </div>
              ))}
            </div>
          )}
          <div className="flex gap-3">
            <button onClick={() => { setMode(null); setStep(2); }} className="btn-secondary flex-1"><ChevronLeft className="w-5 h-5 mr-2" /> Back</button>
            <button onClick={() => setStep(4)} disabled={imageUrls.length < 3} className="btn-primary flex-1">Continue <ChevronRight className="w-5 h-5 ml-2" /></button>
          </div>
        </Card>
      )}

      {/* Step 4: Review & Train */}
      {step === 4 && (
        <Card className="p-6 space-y-6">
          <h2 className="text-lg font-bold text-pearl flex items-center gap-2"><CheckCircle2 className="w-5 h-5 text-success" /> Ready to Train</h2>
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 bg-slate rounded-xl"><p className="text-silver text-sm">Name</p><p className="text-lg font-bold text-pearl">{formData.name}</p></div>
            <div className="p-4 bg-slate rounded-xl"><p className="text-silver text-sm">Images</p><p className="text-lg font-bold text-pearl">{trainingImages.length || imageUrls.length}</p></div>
            <div className="p-4 bg-slate rounded-xl"><p className="text-silver text-sm">Time</p><p className="text-lg font-bold text-pearl">~20 min</p></div>
            <div className="p-4 bg-slate rounded-xl"><p className="text-silver text-sm">Cost</p><p className="text-lg font-bold text-pearl">~$2-3</p></div>
          </div>
          <div className="grid grid-cols-6 gap-2">
            {(trainingImages.length ? trainingImages : imageUrls).slice(0, 6).map((u, i) => <img key={i} src={u} className="aspect-square object-cover rounded-lg" />)}
          </div>
          <div className="flex gap-3">
            <button onClick={() => setStep(mode === 'generate' ? 3 : 3)} className="btn-secondary flex-1"><ChevronLeft className="w-5 h-5 mr-2" /> Back</button>
            <button onClick={handleCreateModel} disabled={creating} className="btn-primary flex-1">
              {creating ? <><Loader2 className="w-5 h-5 animate-spin mr-2" /> Starting...</> : <><Sparkles className="w-5 h-5 mr-2" /> Start Training</>}
            </button>
          </div>
        </Card>
      )}
    </div>
  );
}
