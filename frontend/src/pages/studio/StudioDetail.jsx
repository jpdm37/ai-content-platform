import { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Sparkles, Heart, Check, Copy, Download, RefreshCw, Image, Video, MessageSquare, Hash, Zap, ArrowRight, Star } from 'lucide-react';
import { studioApi } from '../../services/api';
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
  const [project, setProject] = useState(null);
  const [assets, setAssets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState({ type: 'all', platform: 'all' });
  const [selectedAsset, setSelectedAsset] = useState(null);

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
      setAssets(prev => prev.map(a => a.id === assetId ? { ...a, is_selected: true } : a));
      toast.success('Asset selected');
    } catch (err) { toast.error('Failed to select'); }
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard');
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
          <p className="text-2xl font-bold text-accent">${project.total_cost_usd?.toFixed(2)}</p>
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
                  <div key={asset.id} className="relative group">
                    {type === 'image' ? (
                      <img src={asset.media_url} alt="" className="w-full aspect-square object-cover rounded-lg" />
                    ) : (
                      <video src={asset.media_url} className="w-full aspect-video object-cover rounded-lg" />
                    )}
                    <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity rounded-lg flex items-center justify-center gap-2">
                      <button onClick={() => toggleFavorite(asset.id)} className={`p-2 rounded-full ${asset.is_favorite ? 'bg-pink-500' : 'bg-white/20'}`}>
                        <Heart className={`w-5 h-5 ${asset.is_favorite ? 'text-white fill-current' : 'text-white'}`} />
                      </button>
                      <button onClick={() => selectAsset(asset.id)} className={`p-2 rounded-full ${asset.is_selected ? 'bg-green-500' : 'bg-white/20'}`}>
                        <Check className="w-5 h-5 text-white" />
                      </button>
                      {asset.media_url && (
                        <a href={asset.media_url} download className="p-2 rounded-full bg-white/20">
                          <Download className="w-5 h-5 text-white" />
                        </a>
                      )}
                    </div>
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
                  <div key={asset.id} className={`p-4 rounded-lg border ${asset.is_selected ? 'border-accent bg-accent/5' : 'border-graphite'}`}>
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
                        <button onClick={() => selectAsset(asset.id)} className={`p-2 rounded-lg ${asset.is_selected ? 'bg-green-500 text-white' : 'hover:bg-slate text-silver'}`}>
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
    </div>
  );
}
