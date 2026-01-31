import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Sparkles, Plus, Trash2, Play, Eye, CheckCircle, Clock, AlertCircle, XCircle, Image as ImageIcon, Zap } from 'lucide-react';
import { loraApi } from '../../services/api';
import { Card, Badge, LoadingState, EmptyState, ConfirmDialog, Spinner } from '../../components/ui';
import toast from 'react-hot-toast';

const statusConfig = {
  pending: { color: 'warning', icon: Clock, label: 'Pending' },
  validating: { color: 'info', icon: Clock, label: 'Validating' },
  uploading: { color: 'info', icon: Clock, label: 'Uploading' },
  training: { color: 'warning', icon: Sparkles, label: 'Training' },
  completed: { color: 'success', icon: CheckCircle, label: 'Ready' },
  failed: { color: 'error', icon: XCircle, label: 'Failed' },
  cancelled: { color: 'default', icon: AlertCircle, label: 'Cancelled' }
};

export default function LoraModels() {
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deleteModel, setDeleteModel] = useState(null);

  useEffect(() => { fetchModels(); }, []);

  const fetchModels = async () => {
    try {
      const res = await loraApi.listModels();
      setModels(res.data);
    } catch (err) { toast.error('Failed to load models'); }
    setLoading(false);
  };

  const handleDelete = async () => {
    if (!deleteModel) return;
    try {
      await loraApi.deleteModel(deleteModel.id);
      toast.success('Model deleted');
      fetchModels();
    } catch (err) { toast.error('Failed to delete'); }
    setDeleteModel(null);
  };

  if (loading) return <LoadingState message="Loading LoRA models..." />;

  const completed = models.filter(m => m.status === 'completed').length;
  const training = models.filter(m => m.status === 'training').length;
  const avgConsistency = models.filter(m => m.consistency_score).length > 0
    ? Math.round(models.reduce((acc, m) => acc + (m.consistency_score || 0), 0) / models.filter(m => m.consistency_score).length) : 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title flex items-center gap-3"><Sparkles className="w-8 h-8 text-accent" />Avatar Training</h1>
          <p className="text-silver mt-1">Train custom AI avatars for 95%+ consistency</p>
        </div>
        <Link to="/lora/new" className="btn-primary flex items-center gap-2"><Plus className="w-4 h-4" />New Model</Link>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="p-4"><p className="text-silver text-sm">Total Models</p><p className="text-2xl font-bold text-pearl">{models.length}</p></Card>
        <Card className="p-4"><p className="text-silver text-sm">Ready to Use</p><p className="text-2xl font-bold text-success">{completed}</p></Card>
        <Card className="p-4"><p className="text-silver text-sm">Training</p><p className="text-2xl font-bold text-warning">{training}</p></Card>
        <Card className="p-4"><p className="text-silver text-sm">Avg Consistency</p><p className="text-2xl font-bold text-accent">{avgConsistency || '-'}%</p></Card>
      </div>

      {models.length === 0 ? (
        <EmptyState icon={Sparkles} title="No trained models yet" description="Create your first LoRA model for consistent avatar generation" action={<Link to="/lora/new" className="btn-primary">Start Training</Link>} />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {models.map(model => {
            const status = statusConfig[model.status] || statusConfig.pending;
            const StatusIcon = status.icon;
            return (
              <Card key={model.id} className="p-5 hover:border-accent/50 transition-all group">
                <div className="flex items-start justify-between mb-3">
                  <div><h3 className="font-semibold text-pearl text-lg">{model.name}</h3><p className="text-silver text-sm">Trigger: <code className="bg-slate px-1 rounded">{model.trigger_word}</code></p></div>
                  <Badge variant={status.color}><StatusIcon className="w-3 h-3 mr-1" />{status.label}</Badge>
                </div>
                <div className="grid grid-cols-2 gap-2 text-sm text-silver mb-4">
                  <div><span className="text-silver/70">Images:</span> {model.reference_image_count}</div>
                  <div><span className="text-silver/70">Steps:</span> {model.training_steps}</div>
                  <div><span className="text-silver/70">Consistency:</span> {model.consistency_score ? `${Math.round(model.consistency_score)}%` : '-'}</div>
                  <div><span className="text-silver/70">Cost:</span> ${model.training_cost_usd?.toFixed(2) || '-'}</div>
                </div>
                {model.status === 'training' && (
                  <div className="mb-4"><div className="h-2 bg-slate rounded-full overflow-hidden"><div className="h-full bg-accent transition-all" style={{ width: `${model.progress_percent}%` }} /></div><p className="text-xs text-silver mt-1">{model.progress_percent}% complete</p></div>
                )}
                <div className="flex gap-2">
                  <Link to={`/lora/${model.id}`} className="btn-secondary flex-1 text-center text-sm py-2"><Eye className="w-4 h-4 inline mr-1" />View</Link>
                  {model.status === 'completed' && <Link to={`/lora/${model.id}/generate`} className="btn-primary flex-1 text-center text-sm py-2"><Zap className="w-4 h-4 inline mr-1" />Generate</Link>}
                  <button onClick={() => setDeleteModel(model)} className="p-2 text-silver hover:text-error transition-colors"><Trash2 className="w-4 h-4" /></button>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      <ConfirmDialog isOpen={!!deleteModel} onClose={() => setDeleteModel(null)} onConfirm={handleDelete} title="Delete Model?" message={`Delete "${deleteModel?.name}"? This cannot be undone.`} confirmText="Delete" danger />
    </div>
  );
}
