import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Sparkles, Upload, X, Check, AlertTriangle, Image as ImageIcon, ChevronRight, Info } from 'lucide-react';
import { loraApi, brandsApi } from '../../services/api';
import { Card, Badge, Spinner, LoadingState } from '../../components/ui';
import toast from 'react-hot-toast';

export default function LoraCreate() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [brands, setBrands] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);

  // Form state
  const [formData, setFormData] = useState({
    brand_id: '',
    name: '',
    trigger_word: 'AVATAR',
    training_steps: 1000,
    lora_rank: 16,
    resolution: 1024
  });

  // Images state
  const [imageUrls, setImageUrls] = useState([]);
  const [imageInput, setImageInput] = useState('');
  const [uploadedImages, setUploadedImages] = useState([]);
  const [validating, setValidating] = useState(false);

  // Created model
  const [modelId, setModelId] = useState(null);
  const [validation, setValidation] = useState(null);

  useEffect(() => {
    brandsApi.list().then(res => { setBrands(res.data); setLoading(false); }).catch(() => setLoading(false));
  }, []);

  const handleAddImage = () => {
    if (!imageInput.trim()) return;
    if (imageUrls.includes(imageInput)) { toast.error('Image already added'); return; }
    setImageUrls([...imageUrls, imageInput]);
    setImageInput('');
  };

  const handleRemoveImage = (url) => setImageUrls(imageUrls.filter(u => u !== url));

  const handleCreateModel = async () => {
    if (!formData.brand_id || !formData.name) { toast.error('Please fill required fields'); return; }
    setCreating(true);
    try {
      const res = await loraApi.createModel({
        brand_id: parseInt(formData.brand_id),
        name: formData.name,
        trigger_word: formData.trigger_word.toUpperCase().replace(/\s+/g, '_'),
        config: { training_steps: formData.training_steps, lora_rank: formData.lora_rank, resolution: formData.resolution }
      });
      setModelId(res.data.id);
      toast.success('Model created!');
      setStep(2);
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed to create model'); }
    setCreating(false);
  };

  const handleUploadImages = async () => {
    if (imageUrls.length < 5) { toast.error('Add at least 5 images'); return; }
    setValidating(true);
    try {
      const res = await loraApi.bulkAddImages(modelId, imageUrls);
      setUploadedImages(res.data.images);
      toast.success(`${res.data.valid} images validated`);
      setStep(3);
    } catch (err) { toast.error('Failed to upload images'); }
    setValidating(false);
  };

  const handleValidate = async () => {
    setValidating(true);
    try {
      const res = await loraApi.validateModel(modelId);
      setValidation(res.data);
      if (res.data.is_ready) { setStep(4); toast.success('Ready for training!'); }
      else toast.error('Not ready: ' + res.data.issues.join(', '));
    } catch (err) { toast.error('Validation failed'); }
    setValidating(false);
  };

  const handleStartTraining = async () => {
    setCreating(true);
    try {
      await loraApi.startTraining(modelId);
      toast.success('Training started!');
      navigate(`/lora/${modelId}`);
    } catch (err) { toast.error(err.response?.data?.detail?.message || 'Failed to start training'); }
    setCreating(false);
  };

  if (loading) return <LoadingState message="Loading..." />;

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="page-title flex items-center gap-3"><Sparkles className="w-8 h-8 text-accent" />Create LoRA Model</h1>
        <p className="text-silver mt-1">Train a custom AI avatar for consistent generation</p>
      </div>

      {/* Progress Steps */}
      <div className="flex items-center gap-2">
        {['Configure', 'Upload Images', 'Validate', 'Train'].map((label, i) => (
          <div key={i} className="flex items-center">
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${step > i + 1 ? 'bg-success text-white' : step === i + 1 ? 'bg-accent text-white' : 'bg-slate text-silver'}`}>
              {step > i + 1 ? <Check className="w-4 h-4" /> : i + 1}
            </div>
            <span className={`ml-2 text-sm ${step === i + 1 ? 'text-pearl' : 'text-silver'}`}>{label}</span>
            {i < 3 && <ChevronRight className="w-4 h-4 text-graphite mx-3" />}
          </div>
        ))}
      </div>

      {/* Step 1: Configure */}
      {step === 1 && (
        <Card className="p-6 space-y-4">
          <h2 className="section-title">Model Configuration</h2>
          <div>
            <label className="label">Brand *</label>
            <select value={formData.brand_id} onChange={e => setFormData({ ...formData, brand_id: e.target.value })} className="input-field">
              <option value="">Select brand...</option>
              {brands.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Model Name *</label>
            <input type="text" value={formData.name} onChange={e => setFormData({ ...formData, name: e.target.value })} placeholder="e.g., Jane Avatar v1" className="input-field" />
          </div>
          <div>
            <label className="label">Trigger Word</label>
            <input type="text" value={formData.trigger_word} onChange={e => setFormData({ ...formData, trigger_word: e.target.value })} placeholder="AVATAR" className="input-field" />
            <p className="text-xs text-silver mt-1">Use this word in prompts to activate the LoRA</p>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div><label className="label">Training Steps</label><input type="number" value={formData.training_steps} onChange={e => setFormData({ ...formData, training_steps: parseInt(e.target.value) })} min={500} max={4000} className="input-field" /></div>
            <div><label className="label">LoRA Rank</label><select value={formData.lora_rank} onChange={e => setFormData({ ...formData, lora_rank: parseInt(e.target.value) })} className="input-field"><option value={8}>8 (Faster)</option><option value={16}>16 (Balanced)</option><option value={32}>32 (Quality)</option></select></div>
            <div><label className="label">Resolution</label><select value={formData.resolution} onChange={e => setFormData({ ...formData, resolution: parseInt(e.target.value) })} className="input-field"><option value={512}>512px</option><option value={768}>768px</option><option value={1024}>1024px</option></select></div>
          </div>
          <div className="bg-slate/50 rounded-lg p-4 text-sm">
            <p className="text-pearl font-medium mb-1"><Info className="w-4 h-4 inline mr-1" />Estimated Cost</p>
            <p className="text-silver">~${(1.5 + formData.training_steps * 0.001).toFixed(2)} USD • {Math.round(formData.training_steps / 50)} min training time</p>
          </div>
          <button onClick={handleCreateModel} disabled={creating || !formData.brand_id || !formData.name} className="btn-primary w-full">
            {creating ? <Spinner size="sm" /> : 'Continue to Images'}
          </button>
        </Card>
      )}

      {/* Step 2: Upload Images */}
      {step === 2 && (
        <Card className="p-6 space-y-4">
          <h2 className="section-title">Reference Images</h2>
          <p className="text-silver text-sm">Add 10-30 high-quality images of your avatar subject. Include variety in poses, lighting, and expressions for best results.</p>
          
          <div className="bg-slate/50 rounded-lg p-4">
            <h3 className="text-pearl font-medium mb-2">Image Guidelines:</h3>
            <ul className="text-sm text-silver space-y-1">
              <li>✓ Clear face visible in most images</li>
              <li>✓ Good lighting, not too dark or bright</li>
              <li>✓ Mix of close-ups and wider shots</li>
              <li>✓ Different angles and expressions</li>
              <li>✓ At least 512x512 resolution</li>
            </ul>
          </div>

          <div className="flex gap-2">
            <input type="url" value={imageInput} onChange={e => setImageInput(e.target.value)} placeholder="Paste image URL..." className="input-field flex-1" onKeyDown={e => e.key === 'Enter' && handleAddImage()} />
            <button onClick={handleAddImage} className="btn-secondary px-4">Add</button>
          </div>

          <div className="grid grid-cols-4 gap-3">
            {imageUrls.map((url, i) => (
              <div key={i} className="relative group aspect-square bg-slate rounded-lg overflow-hidden">
                <img src={url} alt="" className="w-full h-full object-cover" onError={e => e.target.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg"/>'} />
                <button onClick={() => handleRemoveImage(url)} className="absolute top-1 right-1 p-1 bg-black/50 rounded-full opacity-0 group-hover:opacity-100 transition-opacity"><X className="w-4 h-4 text-white" /></button>
              </div>
            ))}
            {imageUrls.length < 30 && (
              <div className="aspect-square border-2 border-dashed border-graphite rounded-lg flex items-center justify-center text-silver">
                <div className="text-center"><ImageIcon className="w-8 h-8 mx-auto mb-1 opacity-50" /><span className="text-xs">{imageUrls.length}/30</span></div>
              </div>
            )}
          </div>

          <div className="flex gap-3">
            <button onClick={() => setStep(1)} className="btn-secondary flex-1">Back</button>
            <button onClick={handleUploadImages} disabled={validating || imageUrls.length < 5} className="btn-primary flex-1">
              {validating ? <><Spinner size="sm" className="mr-2" />Validating...</> : `Upload ${imageUrls.length} Images`}
            </button>
          </div>
        </Card>
      )}

      {/* Step 3: Validation Results */}
      {step === 3 && (
        <Card className="p-6 space-y-4">
          <h2 className="section-title">Image Validation Results</h2>
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-slate/50 rounded-lg p-4 text-center">
              <p className="text-3xl font-bold text-success">{uploadedImages.filter(i => i.status === 'valid').length}</p>
              <p className="text-silver text-sm">Valid Images</p>
            </div>
            <div className="bg-slate/50 rounded-lg p-4 text-center">
              <p className="text-3xl font-bold text-error">{uploadedImages.filter(i => i.status === 'invalid').length}</p>
              <p className="text-silver text-sm">Invalid</p>
            </div>
          </div>

          <div className="grid grid-cols-5 gap-2 max-h-64 overflow-y-auto">
            {uploadedImages.map((img, i) => (
              <div key={i} className={`relative aspect-square rounded-lg overflow-hidden border-2 ${img.status === 'valid' ? 'border-success' : 'border-error'}`}>
                <img src={img.url} alt="" className="w-full h-full object-cover" />
                <div className={`absolute bottom-0 inset-x-0 p-1 text-xs text-center ${img.status === 'valid' ? 'bg-success/80' : 'bg-error/80'} text-white`}>
                  {img.face_detected ? `${Math.round(img.quality_score)}%` : 'No face'}
                </div>
              </div>
            ))}
          </div>

          <div className="flex gap-3">
            <button onClick={() => setStep(2)} className="btn-secondary flex-1">Add More Images</button>
            <button onClick={handleValidate} disabled={validating} className="btn-primary flex-1">
              {validating ? <><Spinner size="sm" className="mr-2" />Checking...</> : 'Validate for Training'}
            </button>
          </div>
        </Card>
      )}

      {/* Step 4: Ready to Train */}
      {step === 4 && validation && (
        <Card className="p-6 space-y-4">
          <div className="text-center py-4">
            <div className="w-16 h-16 rounded-full bg-success/20 flex items-center justify-center mx-auto mb-4"><Check className="w-8 h-8 text-success" /></div>
            <h2 className="text-2xl font-display font-bold text-pearl">Ready to Train!</h2>
            <p className="text-silver mt-2">Your model is configured and images are validated.</p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="bg-slate/50 rounded-lg p-4"><p className="text-silver text-sm">Valid Images</p><p className="text-xl font-bold text-pearl">{validation.valid_image_count}</p></div>
            <div className="bg-slate/50 rounded-lg p-4"><p className="text-silver text-sm">Faces Detected</p><p className="text-xl font-bold text-pearl">{validation.faces_detected}</p></div>
            <div className="bg-slate/50 rounded-lg p-4"><p className="text-silver text-sm">Avg Quality</p><p className="text-xl font-bold text-pearl">{Math.round(validation.average_quality)}%</p></div>
            <div className="bg-slate/50 rounded-lg p-4"><p className="text-silver text-sm">Est. Cost</p><p className="text-xl font-bold text-accent">${validation.estimated_cost_usd}</p></div>
          </div>

          {validation.warnings?.length > 0 && (
            <div className="bg-warning/10 border border-warning/30 rounded-lg p-4">
              <p className="font-medium text-warning mb-2"><AlertTriangle className="w-4 h-4 inline mr-1" />Suggestions</p>
              <ul className="text-sm text-silver space-y-1">{validation.warnings.map((w, i) => <li key={i}>• {w}</li>)}</ul>
            </div>
          )}

          <button onClick={handleStartTraining} disabled={creating} className="btn-primary w-full py-3 text-lg">
            {creating ? <><Spinner size="sm" className="mr-2" />Starting...</> : `Start Training (~${validation.estimated_time_minutes} min)`}
          </button>
        </Card>
      )}
    </div>
  );
}
