import { useState, useEffect, useCallback } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { Sparkles, Heart, Check, Copy, Download, RefreshCw, Image, Video, MessageSquare, Hash, Zap, ArrowRight, Star, Calendar, Send } from 'lucide-react';
import { studioApi, socialApi } from '../../services/api';
import { Card, Badge, LoadingState, Spinner, Modal } from '../../components/ui';
import toast from 'react-hot-toast';

const contentTypeConfig = {
  caption: { icon: MessageSquare, label: 'Captions', color: 'bg-blue-500' },
  image: { icon: Image, label: 'Images', color: 'bg-purple-500' },
  video: { icon: Video, label: 'Video', color: 'bg-red-500' },
  hashtags: { icon: Hash, label: 'Hashtags', color: 'bg-green-500' },
  hook: { icon: Zap, label: 'Hooks', color: 'bg-yellow-500' },
  cta: { icon: ArrowRight, label: 'CTAs', color: 'bg-orange-500' },
};

export default function StudioDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [project, setProject] = useState(null);
  const [assets, setAssets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState({ type: 'all', platform: 'all' });
  const [selectedAsset, setSelectedAsset] = useState(null);
  const [showScheduleModal, setShowScheduleModal] = useState(false);
  const [scheduleDate, setScheduleDate] = useState('');
  const [scheduleTime, setScheduleTime] = useState('12:00');
  const [schedulePlatform, setSchedulePlatform] = useState('instagram');
  const [scheduling, setScheduling] = useState(false);

  const fetchProject = useCallback(async () => {
    try {
      const res = await studioApi.getProject(id);
      setProject(res.data);
      setAssets(res.data.assets || []);
    } catch (err) { toast.error('Failed to load project'); }
    setLoading(false);
  }, [id]);

  useEffect(() => { fetchProject(); }, [fetchProject]);

  // Poll for updates if generating
  useEffect(() => {
    if (project?.status === 'generating') {
      const interval = setInterval(fetchProject, 3000);
      return () => clearInterval(interval);
    }
  }, [project?.status, fetchProject]);

  const toggleFavorite = async (assetId) => {
    try {
      await studioApi.toggleFavorite(assetId);
      setAssets(prev => prev.map(a => a.id === assetId ? { ...a, is_favorite: !a.is_favorite } : a));
    } catch (err) { toast.error('Failed to update'); }
  };

  const selectAsset = async (assetId) => {
    try {
      await studioApi.selectAsset(assetId);
      setAssets(prev => prev.map(a => a.id === assetId ? { ...a, is_selected: !a.is_selected } : a));
      toast.success('Selection updated');
    } catch (err) { toast.error('Failed to select'); }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard');
  };

  // Get selected content for scheduling
  const selectedAssets = assets.filter(a => a.is_selected);
  const selectedCaption = selectedAssets.find(a => a.content_type === 'caption');
  const selectedImage = selectedAssets.find(a => a.content_type === 'image');
  const selectedHashtags = selectedAssets.find(a => a.content_type === 'hashtags');
  const selectedHook = selectedAssets.find(a => a.content_type === 'hook');
  const selectedCta = selectedAssets.find(a => a.content_type === 'cta');

  // Build combined caption
  const buildFullCaption = () => {
    let parts = [];
    if (selectedHook) parts.push(selectedHook.text_content);
    if (selectedCaption) parts.push(selectedCaption.text_content);
    if (selectedCta) parts.push(selectedCta.text_content);
    if (selectedHashtags) parts.push('\n\n' + selectedHashtags.text_content);
    return parts.join('\n\n');
  };

  const handleSchedule = async () => {
    if (!selectedCaption && !selectedImage) {
      toast.error('Please select at least a caption or image');
      return;
    }

    if (!scheduleDate) {
      toast.error('Please select a date');
      return;
    }

    setScheduling(true);
    try {
      const scheduledFor = new Date(`${scheduleDate}T${scheduleTime}`).toISOString();
      
      await socialApi.createPost({
        caption: buildFullCaption(),
        media_url: selectedImage?.media_url || null,
        platform: schedulePlatform,
        scheduled_for: scheduledFor,
        brand_id: project.brand_id,
        studio_project_id: project.id,
      });

      toast.success('Content scheduled successfully!');
      setShowScheduleModal(false);
      navigate('/schedule');
    } catch (err) {
      toast.error('Failed to schedule content');
      console.error(err);
    }
    setScheduling(false);
  };

  const copyAllSelected = () => {
    const fullCaption = buildFullCaption();
    navigator.clipboard.writeText(fullCaption);
    toast.success('All selected content copied to clipboard');
  };

  if (loading) return <LoadingState message="Loading project..." />;
  if (!project) return <div className="text-center py-12 text-silver">Project not found</div>;

  const isGenerating = project.status === 'generating';
  const filteredAssets = assets.filter(a => {
    if (filter.type !== 'all' && a.content_type !== filter.type) return false;
    if (filter.platform !== 'all' && a.platform !== filter.platform) return false;
    return true;
  });

  const groupedAssets = filteredAssets.reduce((acc, asset) => {
    const key = asset.content_type;
    if (!acc[key]) acc[key] = [];
    acc[key].push(asset);
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="page-title">{project.name}</h1>
            <Badge className={`${project.status === 'completed' ? 'bg-success' : project.status === 'generating' ? 'bg-info' : 'bg-error'} text-white`}>
              {isGenerating && <Spinner size="xs" className="mr-1" />}
              {project.status}
            </Badge>
          </div>
          <p className="text-silver mt-1 max-w-2xl">{project.brief}</p>
        </div>
        <Link to="/studio" className="btn-secondary">← Back</Link>
      </div>

      {/* Progress */}
      {isGenerating && (
        <Card className="p-6">
          <div className="flex items-center justify-between mb-3">
            <span className="text-pearl font-medium flex items-center gap-2">
              <RefreshCw className="w-5 h-5 animate-spin text-accent" />
              {project.current_step || 'Generating...'}
            </span>
            <span className="text-pearl font-mono">{project.progress_percent}%</span>
          </div>
          <div className="h-3 bg-slate rounded-full overflow-hidden">
            <div className="h-full bg-accent transition-all" style={{ width: `${project.progress_percent}%` }} />
          </div>
        </Card>
      )}

      {/* Action Bar - Show when content is generated */}
      {!isGenerating && selectedAssets.length > 0 && (
        <Card className="p-4 bg-gradient-to-r from-accent/20 to-purple-500/20 border-accent/50">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Check className="w-6 h-6 text-accent" />
              <div>
                <p className="text-pearl font-medium">{selectedAssets.length} items selected</p>
                <p className="text-silver text-sm">
                  {selectedCaption && '1 caption'}{selectedCaption && selectedImage && ', '}{selectedImage && '1 image'}
                  {selectedHashtags && ', hashtags'}{selectedHook && ', hook'}{selectedCta && ', CTA'}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <button onClick={copyAllSelected} className="btn-secondary flex items-center gap-2">
                <Copy className="w-4 h-4" />
                Copy All
              </button>
              <button onClick={() => setShowScheduleModal(true)} className="btn-primary flex items-center gap-2">
                <Calendar className="w-4 h-4" />
                Schedule Post
              </button>
            </div>
          </div>
        </Card>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <Card className="p-4 text-center">
          <MessageSquare className="w-6 h-6 mx-auto text-blue-400 mb-2" />
          <p className="text-2xl font-bold text-pearl">{project.captions_generated}</p>
          <p className="text-xs text-silver">Captions</p>
        </Card>
        <Card className="p-4 text-center">
          <Image className="w-6 h-6 mx-auto text-purple-400 mb-2" />
          <p className="text-2xl font-bold text-pearl">{project.images_generated}</p>
          <p className="text-xs text-silver">Images</p>
        </Card>
        <Card className="p-4 text-center">
          <Video className="w-6 h-6 mx-auto text-red-400 mb-2" />
          <p className="text-2xl font-bold text-pearl">{project.videos_generated}</p>
          <p className="text-xs text-silver">Videos</p>
        </Card>
        <Card className="p-4 text-center">
          <Heart className="w-6 h-6 mx-auto text-pink-400 mb-2" />
          <p className="text-2xl font-bold text-pearl">{assets.filter(a => a.is_favorite).length}</p>
          <p className="text-xs text-silver">Favorites</p>
        </Card>
        <Card className="p-4 text-center">
          <p className="text-2xl font-bold text-accent">${project.total_cost_usd?.toFixed(2) || '0.00'}</p>
          <p className="text-xs text-silver">Total Cost</p>
        </Card>
      </div>

      {/* Filters */}
      <div className="flex gap-4">
        <select
          value={filter.type}
          onChange={(e) => setFilter({ ...filter, type: e.target.value })}
          className="input-field w-auto"
        >
          <option value="all">All Types</option>
          {Object.entries(contentTypeConfig).map(([key, val]) => (
            <option key={key} value={key}>{val.label}</option>
          ))}
        </select>
        <select
          value={filter.platform}
          onChange={(e) => setFilter({ ...filter, platform: e.target.value })}
          className="input-field w-auto"
        >
          <option value="all">All Platforms</option>
          {project.target_platforms?.map(p => (
            <option key={p} value={p} className="capitalize">{p}</option>
          ))}
        </select>
      </div>

      {/* Workflow Guide */}
      {!isGenerating && selectedAssets.length === 0 && (
        <Card className="p-4 bg-slate/50 border-dashed border-silver/30">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-accent/20 flex items-center justify-center">
              <Check className="w-5 h-5 text-accent" />
            </div>
            <div>
              <p className="text-pearl font-medium">Select your favorite content</p>
              <p className="text-silver text-sm">Click the ✓ checkmark on items you want to use, then schedule or copy them</p>
            </div>
          </div>
        </Card>
      )}

      {/* Assets by Type */}
      {Object.entries(groupedAssets).map(([type, typeAssets]) => {
        const config = contentTypeConfig[type] || { icon: Sparkles, label: type, color: 'bg-gray-500' };
        const TypeIcon = config.icon;

        return (
          <Card key={type} className="p-6">
            <h2 className="section-title flex items-center gap-2 mb-4">
              <TypeIcon className="w-5 h-5" />
              {config.label}
              <Badge className="ml-2">{typeAssets.length}</Badge>
            </h2>

            {type === 'image' || type === 'video' ? (
              // Media grid
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {typeAssets.map(asset => (
                  <div key={asset.id} className={`relative group rounded-lg overflow-hidden ${asset.is_selected ? 'ring-2 ring-accent' : ''}`}>
                    {type === 'image' ? (
                      <img src={asset.media_url} alt="" className="w-full aspect-square object-cover" />
                    ) : (
                      <video src={asset.media_url} className="w-full aspect-video object-cover" />
                    )}
                    <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                      <button onClick={() => toggleFavorite(asset.id)} className={`p-2 rounded-full ${asset.is_favorite ? 'bg-pink-500' : 'bg-white/20'}`}>
                        <Heart className={`w-5 h-5 ${asset.is_favorite ? 'text-white fill-current' : 'text-white'}`} />
                      </button>
                      <button onClick={() => selectAsset(asset.id)} className={`p-2 rounded-full ${asset.is_selected ? 'bg-accent' : 'bg-white/20'}`}>
                        <Check className="w-5 h-5 text-white" />
                      </button>
                      {asset.media_url && (
                        <a href={asset.media_url} download className="p-2 rounded-full bg-white/20">
                          <Download className="w-5 h-5 text-white" />
                        </a>
                      )}
                    </div>
                    {asset.is_selected && (
                      <div className="absolute top-2 right-2 w-6 h-6 bg-accent rounded-full flex items-center justify-center">
                        <Check className="w-4 h-4 text-white" />
                      </div>
                    )}
                    {asset.platform && (
                      <Badge className="absolute top-2 left-2 text-xs capitalize">{asset.platform}</Badge>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              // Text content list
              <div className="space-y-3">
                {typeAssets.map(asset => (
                  <div key={asset.id} className={`p-4 rounded-lg border transition-all ${asset.is_selected ? 'border-accent bg-accent/10 ring-1 ring-accent' : 'border-graphite hover:border-silver'}`}>
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        {asset.platform && (
                          <Badge variant="secondary" className="text-xs capitalize mb-2">{asset.platform}</Badge>
                        )}
                        <p className="text-pearl whitespace-pre-wrap">{asset.text_content}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <button onClick={() => toggleFavorite(asset.id)} className={`p-2 rounded-lg hover:bg-slate ${asset.is_favorite ? 'text-pink-500' : 'text-silver'}`}>
                          <Heart className={`w-5 h-5 ${asset.is_favorite ? 'fill-current' : ''}`} />
                        </button>
                        <button onClick={() => copyToClipboard(asset.text_content)} className="p-2 rounded-lg hover:bg-slate text-silver">
                          <Copy className="w-5 h-5" />
                        </button>
                        <button onClick={() => selectAsset(asset.id)} className={`p-2 rounded-lg ${asset.is_selected ? 'bg-accent text-white' : 'hover:bg-slate text-silver'}`}>
                          <Check className="w-5 h-5" />
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        );
      })}

      {filteredAssets.length === 0 && !isGenerating && (
        <Card className="p-12 text-center">
          <Sparkles className="w-12 h-12 mx-auto text-silver mb-4" />
          <p className="text-silver">No assets match your filters</p>
        </Card>
      )}

      {/* Schedule Modal */}
      {showScheduleModal && (
        <Modal onClose={() => setShowScheduleModal(false)} title="Schedule Post">
          <div className="space-y-4">
            {/* Preview */}
            <div className="bg-slate rounded-lg p-4 max-h-48 overflow-y-auto">
              <p className="text-sm text-silver mb-2">Preview:</p>
              {selectedImage && (
                <img src={selectedImage.media_url} alt="" className="w-20 h-20 object-cover rounded mb-2" />
              )}
              <p className="text-pearl text-sm whitespace-pre-wrap line-clamp-4">{buildFullCaption()}</p>
            </div>

            {/* Platform */}
            <div>
              <label className="block text-sm text-silver mb-1">Platform</label>
              <select
                value={schedulePlatform}
                onChange={(e) => setSchedulePlatform(e.target.value)}
                className="input-field w-full"
              >
                <option value="instagram">Instagram</option>
                <option value="twitter">Twitter/X</option>
                <option value="tiktok">TikTok</option>
                <option value="linkedin">LinkedIn</option>
                <option value="facebook">Facebook</option>
              </select>
            </div>

            {/* Date */}
            <div>
              <label className="block text-sm text-silver mb-1">Date</label>
              <input
                type="date"
                value={scheduleDate}
                onChange={(e) => setScheduleDate(e.target.value)}
                min={new Date().toISOString().split('T')[0]}
                className="input-field w-full"
              />
            </div>

            {/* Time */}
            <div>
              <label className="block text-sm text-silver mb-1">Time</label>
              <input
                type="time"
                value={scheduleTime}
                onChange={(e) => setScheduleTime(e.target.value)}
                className="input-field w-full"
              />
            </div>

            {/* Actions */}
            <div className="flex gap-3 pt-4">
              <button
                onClick={() => setShowScheduleModal(false)}
                className="btn-secondary flex-1"
              >
                Cancel
              </button>
              <button
                onClick={handleSchedule}
                disabled={scheduling}
                className="btn-primary flex-1 flex items-center justify-center gap-2"
              >
                {scheduling ? <Spinner size="sm" /> : <Send className="w-4 h-4" />}
                Schedule
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
