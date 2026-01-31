import { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Sparkles, Image as ImageIcon, Zap, Clock, CheckCircle, XCircle, RefreshCw, Star, Download, Trash2 } from 'lucide-react';
import { loraApi } from '../../services/api';
import { Card, Badge, LoadingState, Spinner, Modal, ConfirmDialog } from '../../components/ui';
import toast from 'react-hot-toast';

const statusConfig = {
  pending: { color: 'warning', label: 'Pending Setup' },
  validating: { color: 'info', label: 'Validating' },
  uploading: { color: 'info', label: 'Uploading' },
  training: { color: 'warning', label: 'Training' },
  completed: { color: 'success', label: 'Ready' },
  failed: { color: 'error', label: 'Failed' },
  cancelled: { color: 'default', label: 'Cancelled' }
};

export default function LoraDetail() {
  const { id } = useParams();
  const [model, setModel] = useState(null);
  const [loading, setLoading] = useState(true);
  const [progress, setProgress] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [prompt, setPrompt] = useState('professional headshot, studio lighting');
  const [generatedImages, setGeneratedImages] = useState([]);
  const [selectedImage, setSelectedImage] = useState(null);
  const [deleteSample, setDeleteSample] = useState(null);

  const fetchModel = useCallback(async () => {
    try {
      const res = await loraApi.getModel(id);
      setModel(res.data);
      if (res.data.status === 'training') fetchProgress();
    } catch (err) { toast.error('Failed to load model'); }
    setLoading(false);
  }, [id]);

  const fetchProgress = async () => {
    try {
      const res = await loraApi.getProgress(id);
      setProgress(res.data);
    } catch (err) {}
  };

  useEffect(() => { fetchModel(); }, [fetchModel]);

  useEffect(() => {
    if (model?.status === 'training') {
      const interval = setInterval(fetchProgress, 5000);
      return () => clearInterval(interval);
    }
  }, [model?.status]);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const res = await loraApi.generate({ lora_model_id: parseInt(id), prompt, num_outputs: 1 });
      setGeneratedImages([...res.data.samples, ...generatedImages]);
      toast.success('Image generated!');
    } catch (err) { toast.error(err.response?.data?.detail || 'Generation failed'); }
    setGenerating(false);
  };

  const handleGenerateTests = async () => {
    setGenerating(true);
    try {
      const res = await loraApi.generateTestSamples(id, 4);
      setModel({ ...model, consistency_score: res.data.consistency_score });
      setGeneratedImages([...res.data.samples, ...generatedImages]);
      toast.success(`Generated ${res.data.samples.length} test images`);
    } catch (err) { toast.error('Failed to generate tests'); }
    setGenerating(false);
  };

  const handleRate = async (sampleId, rating) => {
    try {
      await loraApi.rateSample(sampleId, { rating });
      setGeneratedImages(generatedImages.map(img => img.id === sampleId ? { ...img, user_rating: rating } : img));
      toast.success('Rating saved');
    } catch (err) { toast.error('Failed to save rating'); }
  };

  const handleDeleteSample = async () => {
    if (!deleteSample) return;
    try {
      await loraApi.deleteSample(deleteSample.id);
      setGeneratedImages(generatedImages.filter(img => img.id !== deleteSample.id));
      toast.success('Deleted');
    } catch (err) { toast.error('Failed to delete'); }
    setDeleteSample(null);
  };

  if (loading) return <LoadingState message="Loading model..." />;
  if (!model) return <div className="text-center py-12 text-silver">Model not found</div>;

  const status = statusConfig[model.status] || statusConfig.pending;
  const isReady = model.status === 'completed';
  const isTraining = model.status === 'training';

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <h1 className="page-title">{model.name}</h1>
            <Badge variant={status.color}>{status.label}</Badge>
          </div>
          <p className="text-silver">Trigger: <code className="bg-slate px-2 py-1 rounded">{model.trigger_word}</code> • v{model.version}</p>
        </div>
        <Link to="/lora" className="btn-secondary">← Back</Link>
      </div>

      {/* Training Progress */}
      {isTraining && progress && (
        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="section-title flex items-center gap-2"><RefreshCw className="w-5 h-5 animate-spin text-accent" />Training in Progress</h2>
            <span className="text-pearl font-mono">{progress.progress_percent}%</span>
          </div>
          <div className="h-3 bg-slate rounded-full overflow-hidden mb-2">
            <div className="h-full bg-gradient-to-r from-accent to-accent-dark transition-all duration-500" style={{ width: `${progress.progress_percent}%` }} />
          </div>
          <div className="flex justify-between text-sm text-silver">
            <span>Step {progress.current_step || 0} / {progress.total_steps || model.training_steps}</span>
            <span>{progress.eta_seconds ? `~${Math.round(progress.eta_seconds / 60)} min remaining` : 'Estimating...'}</span>
          </div>
          {progress.logs?.length > 0 && (
            <div className="mt-4 bg-midnight rounded-lg p-3 font-mono text-xs text-silver max-h-32 overflow-y-auto">
              {progress.logs.slice(-5).map((log, i) => <div key={i}>{log}</div>)}
            </div>
          )}
        </Card>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <Card className="p-4"><p className="text-silver text-sm">Images</p><p className="text-2xl font-bold text-pearl">{model.reference_image_count}</p></Card>
        <Card className="p-4"><p className="text-silver text-sm">Steps</p><p className="text-2xl font-bold text-pearl">{model.training_steps}</p></Card>
        <Card className="p-4"><p className="text-silver text-sm">Consistency</p><p className="text-2xl font-bold text-accent">{model.consistency_score ? `${Math.round(model.consistency_score)}%` : '-'}</p></Card>
        <Card className="p-4"><p className="text-silver text-sm">Cost</p><p className="text-2xl font-bold text-pearl">${model.training_cost_usd?.toFixed(2) || '-'}</p></Card>
        <Card className="p-4"><p className="text-silver text-sm">Duration</p><p className="text-2xl font-bold text-pearl">{model.training_duration_seconds ? `${Math.round(model.training_duration_seconds / 60)}m` : '-'}</p></Card>
      </div>

      {/* Reference Images */}
      <Card className="p-6">
        <h2 className="section-title mb-4">Reference Images ({model.reference_images?.length || 0})</h2>
        <div className="grid grid-cols-6 md:grid-cols-10 gap-2">
          {model.reference_images?.slice(0, 20).map((img, i) => (
            <div key={i} className={`aspect-square rounded-lg overflow-hidden border-2 ${img.validation_status === 'valid' ? 'border-success/50' : 'border-error/50'}`}>
              <img src={img.original_url} alt="" className="w-full h-full object-cover" />
            </div>
          ))}
          {model.reference_images?.length > 20 && (
            <div className="aspect-square rounded-lg bg-slate flex items-center justify-center text-silver text-sm">+{model.reference_images.length - 20}</div>
          )}
        </div>
      </Card>

      {/* Generation */}
      {isReady && (
        <Card className="p-6">
          <h2 className="section-title mb-4">Generate Images</h2>
          <div className="flex gap-3 mb-4">
            <input type="text" value={prompt} onChange={e => setPrompt(e.target.value)} placeholder="Describe the image..." className="input-field flex-1" />
            <button onClick={handleGenerate} disabled={generating} className="btn-primary px-6">
              {generating ? <Spinner size="sm" /> : <><Zap className="w-4 h-4 mr-1" />Generate</>}
            </button>
          </div>
          <div className="flex gap-2 flex-wrap">
            {['professional headshot, studio lighting', 'casual portrait, outdoor', 'close-up smile, warm lighting', 'business attire, office background'].map(p => (
              <button key={p} onClick={() => setPrompt(p)} className="text-xs bg-slate hover:bg-graphite px-3 py-1 rounded-full text-silver transition-colors">{p}</button>
            ))}
          </div>
          {!model.consistency_score && (
            <button onClick={handleGenerateTests} disabled={generating} className="mt-4 btn-secondary w-full">
              {generating ? <Spinner size="sm" /> : 'Generate Test Samples & Calculate Consistency'}
            </button>
          )}
        </Card>
      )}

      {/* Generated Samples */}
      {(generatedImages.length > 0 || model.recent_samples?.length > 0) && (
        <Card className="p-6">
          <h2 className="section-title mb-4">Generated Samples</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[...generatedImages, ...(model.recent_samples || [])].map((sample, i) => (
              <div key={sample.id || i} className="group relative aspect-square rounded-xl overflow-hidden bg-slate">
                <img src={sample.image_url} alt="" className="w-full h-full object-cover cursor-pointer" onClick={() => setSelectedImage(sample)} />
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent opacity-0 group-hover:opacity-100 transition-opacity">
                  <div className="absolute bottom-0 inset-x-0 p-3">
                    <div className="flex items-center justify-between">
                      <div className="flex gap-1">
                        {[1,2,3,4,5].map(n => (
                          <button key={n} onClick={() => handleRate(sample.id, n)} className={`p-1 ${sample.user_rating >= n ? 'text-yellow-400' : 'text-white/50'}`}>
                            <Star className="w-4 h-4" fill={sample.user_rating >= n ? 'currentColor' : 'none'} />
                          </button>
                        ))}
                      </div>
                      <div className="flex gap-1">
                        <a href={sample.image_url} download className="p-1 text-white/70 hover:text-white"><Download className="w-4 h-4" /></a>
                        <button onClick={() => setDeleteSample(sample)} className="p-1 text-white/70 hover:text-error"><Trash2 className="w-4 h-4" /></button>
                      </div>
                    </div>
                  </div>
                </div>
                {sample.is_test_sample && <Badge variant="info" className="absolute top-2 left-2 text-xs">Test</Badge>}
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Image Preview Modal */}
      <Modal isOpen={!!selectedImage} onClose={() => setSelectedImage(null)} title="Generated Image">
        {selectedImage && (
          <div>
            <img src={selectedImage.image_url} alt="" className="w-full rounded-lg mb-4" />
            <p className="text-sm text-silver mb-2"><strong>Prompt:</strong> {selectedImage.prompt}</p>
            <div className="flex gap-4 text-sm text-silver">
              <span>Scale: {selectedImage.lora_scale}</span>
              <span>Guidance: {selectedImage.guidance_scale}</span>
              {selectedImage.seed && <span>Seed: {selectedImage.seed}</span>}
            </div>
          </div>
        )}
      </Modal>

      <ConfirmDialog isOpen={!!deleteSample} onClose={() => setDeleteSample(null)} onConfirm={handleDeleteSample} title="Delete Sample?" message="This cannot be undone." confirmText="Delete" danger />
    </div>
  );
}
