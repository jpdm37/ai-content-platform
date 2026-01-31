import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Mic2, Plus, Trash2, Play, RefreshCw, CheckCircle, AlertCircle, Sparkles, Copy } from 'lucide-react';
import { brandVoiceApi, brandsApi } from '../../services/api';
import { Card, Badge, LoadingState, Modal, Spinner, ConfirmDialog } from '../../components/ui';
import toast from 'react-hot-toast';

export default function BrandVoice() {
  const { brandId } = useParams();
  const [brand, setBrand] = useState(null);
  const [voice, setVoice] = useState(null);
  const [examples, setExamples] = useState([]);
  const [loading, setLoading] = useState(true);
  const [training, setTraining] = useState(false);

  // Modals
  const [showAddExample, setShowAddExample] = useState(false);
  const [showGenerate, setShowGenerate] = useState(false);
  const [deleteExample, setDeleteExample] = useState(null);

  // Form states
  const [newExample, setNewExample] = useState({ content: '', content_type: 'social_post', platform: '' });
  const [generateForm, setGenerateForm] = useState({ prompt: '', voice_strength: 0.8, platform: 'instagram' });
  const [generatedContent, setGeneratedContent] = useState(null);
  const [generating, setGenerating] = useState(false);

  useEffect(() => { fetchData(); }, [brandId]);

  const fetchData = async () => {
    try {
      const [brandRes, voiceRes, examplesRes] = await Promise.all([
        brandsApi.get(brandId),
        brandVoiceApi.getVoice(brandId),
        brandVoiceApi.getExamples(brandId)
      ]);
      setBrand(brandRes.data);
      setVoice(voiceRes.data);
      setExamples(examplesRes.data);
    } catch (err) { 
      console.error(err);
      toast.error('Failed to load brand voice');
    }
    setLoading(false);
  };

  const handleAddExample = async () => {
    if (newExample.content.length < 20) {
      toast.error('Example must be at least 20 characters');
      return;
    }

    try {
      const res = await brandVoiceApi.addExample(brandId, newExample);
      setExamples([res.data, ...examples]);
      setNewExample({ content: '', content_type: 'social_post', platform: '' });
      setShowAddExample(false);
      toast.success('Example added');
      fetchData(); // Refresh voice status
    } catch (err) {
      toast.error('Failed to add example');
    }
  };

  const handleDeleteExample = async () => {
    if (!deleteExample) return;
    try {
      await brandVoiceApi.deleteExample(brandId, deleteExample.id);
      setExamples(examples.filter(e => e.id !== deleteExample.id));
      toast.success('Example removed');
      fetchData();
    } catch (err) { toast.error('Failed to delete'); }
    setDeleteExample(null);
  };

  const handleTrain = async () => {
    if (examples.length < 5) {
      toast.error('Need at least 5 examples to train');
      return;
    }

    setTraining(true);
    try {
      await brandVoiceApi.train(brandId);
      toast.success('Voice trained successfully!');
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Training failed');
    }
    setTraining(false);
  };

  const handleGenerate = async () => {
    if (!generateForm.prompt) {
      toast.error('Please enter a prompt');
      return;
    }

    setGenerating(true);
    try {
      const res = await brandVoiceApi.generate(brandId, generateForm);
      setGeneratedContent(res.data);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Generation failed');
    }
    setGenerating(false);
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied!');
  };

  if (loading) return <LoadingState message="Loading brand voice..." />;
  if (!brand) return <div className="text-center py-12 text-silver">Brand not found</div>;

  const canTrain = examples.length >= 5;
  const needsRetraining = voice?.training_status === 'pending' && voice?.is_trained;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="page-title flex items-center gap-3">
            <Mic2 className="w-8 h-8 text-accent" />
            {brand.name} Voice
          </h1>
          <p className="text-silver mt-1">Train AI to match your brand's writing style</p>
        </div>
        <Link to="/brands" className="btn-secondary">← Back to Brands</Link>
      </div>

      {/* Voice Status */}
      <Card className="p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className={`w-16 h-16 rounded-full flex items-center justify-center ${voice?.is_trained ? 'bg-success/20' : 'bg-warning/20'}`}>
              {voice?.is_trained ? (
                <CheckCircle className="w-8 h-8 text-success" />
              ) : (
                <AlertCircle className="w-8 h-8 text-warning" />
              )}
            </div>
            <div>
              <h2 className="text-xl font-semibold text-pearl">
                {voice?.is_trained ? 'Voice Trained' : 'Voice Not Trained'}
              </h2>
              <p className="text-silver">
                {voice?.is_trained 
                  ? `Used ${voice.times_used} times • ${voice.example_count} examples`
                  : `Add ${Math.max(5 - examples.length, 0)} more examples to train`
                }
              </p>
              {needsRetraining && (
                <Badge className="bg-warning text-white mt-2">New examples added - retrain recommended</Badge>
              )}
            </div>
          </div>

          <div className="flex gap-3">
            {voice?.is_trained && (
              <button onClick={() => setShowGenerate(true)} className="btn-primary flex items-center gap-2">
                <Sparkles className="w-4 h-4" />Generate with Voice
              </button>
            )}
            <button
              onClick={handleTrain}
              disabled={!canTrain || training}
              className={`btn-secondary flex items-center gap-2 ${!canTrain ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              {training ? <Spinner size="sm" /> : <RefreshCw className="w-4 h-4" />}
              {voice?.is_trained ? 'Retrain' : 'Train Voice'}
            </button>
          </div>
        </div>

        {/* Characteristics */}
        {voice?.characteristics && (
          <div className="mt-6 pt-6 border-t border-graphite">
            <h3 className="text-sm font-medium text-pearl mb-3">Detected Characteristics</h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {voice.characteristics.overall_tone && (
                <div>
                  <p className="text-xs text-silver">Tone</p>
                  <p className="text-pearl capitalize">{voice.characteristics.overall_tone}</p>
                </div>
              )}
              {voice.characteristics.formality_level && (
                <div>
                  <p className="text-xs text-silver">Formality</p>
                  <p className="text-pearl capitalize">{voice.characteristics.formality_level}</p>
                </div>
              )}
              {voice.characteristics.emoji_usage && (
                <div>
                  <p className="text-xs text-silver">Emoji Usage</p>
                  <p className="text-pearl capitalize">{voice.characteristics.emoji_usage}</p>
                </div>
              )}
              {voice.characteristics.vocabulary_complexity && (
                <div>
                  <p className="text-xs text-silver">Vocabulary</p>
                  <p className="text-pearl capitalize">{voice.characteristics.vocabulary_complexity}</p>
                </div>
              )}
            </div>
            {voice.characteristics.common_phrases?.length > 0 && (
              <div className="mt-4">
                <p className="text-xs text-silver mb-2">Common Phrases</p>
                <div className="flex flex-wrap gap-2">
                  {voice.characteristics.common_phrases.slice(0, 5).map((phrase, i) => (
                    <Badge key={i} variant="secondary">"{phrase}"</Badge>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </Card>

      {/* Examples */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="section-title">Training Examples ({examples.length})</h2>
          <button onClick={() => setShowAddExample(true)} className="btn-primary flex items-center gap-2">
            <Plus className="w-4 h-4" />Add Example
          </button>
        </div>

        <p className="text-silver text-sm mb-4">
          Add 5-20 examples of your brand's content. The more examples, the better the voice matching.
        </p>

        {/* Progress */}
        <div className="mb-6">
          <div className="flex justify-between text-sm mb-1">
            <span className="text-silver">Training progress</span>
            <span className="text-pearl">{examples.length}/5 minimum</span>
          </div>
          <div className="h-2 bg-slate rounded-full overflow-hidden">
            <div 
              className={`h-full transition-all ${examples.length >= 5 ? 'bg-success' : 'bg-warning'}`} 
              style={{ width: `${Math.min(examples.length / 5 * 100, 100)}%` }} 
            />
          </div>
        </div>

        {/* Example List */}
        {examples.length === 0 ? (
          <div className="text-center py-8 border-2 border-dashed border-graphite rounded-lg">
            <Mic2 className="w-12 h-12 mx-auto text-silver mb-3" />
            <p className="text-silver">No examples yet</p>
            <button onClick={() => setShowAddExample(true)} className="text-accent mt-2">Add your first example</button>
          </div>
        ) : (
          <div className="space-y-3 max-h-[400px] overflow-y-auto">
            {examples.map(example => (
              <div key={example.id} className="p-4 bg-slate rounded-lg">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex gap-2 mb-2">
                      {example.content_type && <Badge variant="secondary" className="text-xs">{example.content_type}</Badge>}
                      {example.platform && <Badge variant="secondary" className="text-xs capitalize">{example.platform}</Badge>}
                    </div>
                    <p className="text-pearl text-sm">{example.content}</p>
                    {example.analysis && (
                      <div className="flex gap-4 mt-2 text-xs text-silver">
                        <span>{example.analysis.word_count} words</span>
                        <span>{example.analysis.emoji_count} emojis</span>
                        <span>{example.analysis.hashtag_count} hashtags</span>
                      </div>
                    )}
                  </div>
                  <button onClick={() => setDeleteExample(example)} className="text-silver hover:text-error">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Add Example Modal */}
      <Modal isOpen={showAddExample} onClose={() => setShowAddExample(false)} title="Add Training Example">
        <div className="space-y-4">
          <div>
            <label className="label">Example Content *</label>
            <textarea
              value={newExample.content}
              onChange={(e) => setNewExample({ ...newExample, content: e.target.value })}
              placeholder="Paste an example of your brand's content (social post, caption, etc.)..."
              className="input-field min-h-[150px]"
            />
            <p className="text-xs text-silver mt-1">{newExample.content.length} characters (min 20)</p>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">Content Type</label>
              <select
                value={newExample.content_type}
                onChange={(e) => setNewExample({ ...newExample, content_type: e.target.value })}
                className="input-field"
              >
                <option value="social_post">Social Post</option>
                <option value="caption">Caption</option>
                <option value="blog">Blog</option>
                <option value="email">Email</option>
                <option value="ad_copy">Ad Copy</option>
              </select>
            </div>
            <div>
              <label className="label">Platform (optional)</label>
              <select
                value={newExample.platform}
                onChange={(e) => setNewExample({ ...newExample, platform: e.target.value })}
                className="input-field"
              >
                <option value="">Any</option>
                <option value="twitter">Twitter</option>
                <option value="instagram">Instagram</option>
                <option value="linkedin">LinkedIn</option>
                <option value="facebook">Facebook</option>
              </select>
            </div>
          </div>
          <div className="flex justify-end gap-3">
            <button onClick={() => setShowAddExample(false)} className="btn-secondary">Cancel</button>
            <button onClick={handleAddExample} className="btn-primary">Add Example</button>
          </div>
        </div>
      </Modal>

      {/* Generate Modal */}
      <Modal isOpen={showGenerate} onClose={() => { setShowGenerate(false); setGeneratedContent(null); }} title="Generate with Brand Voice" size="lg">
        <div className="space-y-4">
          <div>
            <label className="label">What do you want to create?</label>
            <textarea
              value={generateForm.prompt}
              onChange={(e) => setGenerateForm({ ...generateForm, prompt: e.target.value })}
              placeholder="e.g., A post announcing our new product launch..."
              className="input-field min-h-[100px]"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">Platform</label>
              <select
                value={generateForm.platform}
                onChange={(e) => setGenerateForm({ ...generateForm, platform: e.target.value })}
                className="input-field"
              >
                <option value="twitter">Twitter</option>
                <option value="instagram">Instagram</option>
                <option value="linkedin">LinkedIn</option>
                <option value="facebook">Facebook</option>
              </select>
            </div>
            <div>
              <label className="label">Voice Strength: {Math.round(generateForm.voice_strength * 100)}%</label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={generateForm.voice_strength}
                onChange={(e) => setGenerateForm({ ...generateForm, voice_strength: parseFloat(e.target.value) })}
                className="w-full"
              />
            </div>
          </div>
          
          <button onClick={handleGenerate} disabled={generating} className="btn-primary w-full">
            {generating ? <><Spinner size="sm" className="mr-2" />Generating...</> : 'Generate Content'}
          </button>

          {generatedContent && (
            <div className="mt-4 p-4 bg-slate rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-silver">Generated Content</span>
                <button onClick={() => copyToClipboard(generatedContent.content)} className="text-accent text-sm flex items-center gap-1">
                  <Copy className="w-4 h-4" />Copy
                </button>
              </div>
              <p className="text-pearl whitespace-pre-wrap">{generatedContent.content}</p>
            </div>
          )}
        </div>
      </Modal>

      {/* Delete Confirmation */}
      <ConfirmDialog
        isOpen={!!deleteExample}
        onClose={() => setDeleteExample(null)}
        onConfirm={handleDeleteExample}
        title="Remove Example?"
        message="This will remove the example from training data."
        confirmText="Remove"
        danger
      />
    </div>
  );
}
