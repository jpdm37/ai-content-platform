import { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Video, Plus, Play, Download, Trash2, Clock, CheckCircle, XCircle, RefreshCw, Copy } from 'lucide-react';
import { videoApi } from '../../services/api';
import { Card, Badge, LoadingState, EmptyState, ConfirmDialog, Spinner } from '../../components/ui';
import toast from 'react-hot-toast';

const statusConfig = {
  pending: { color: 'warning', icon: Clock, label: 'Queued' },
  generating_audio: { color: 'info', icon: RefreshCw, label: 'Generating Audio' },
  generating_avatar: { color: 'info', icon: RefreshCw, label: 'Creating Avatar' },
  generating_video: { color: 'warning', icon: RefreshCw, label: 'Animating' },
  processing: { color: 'info', icon: RefreshCw, label: 'Processing' },
  completed: { color: 'success', icon: CheckCircle, label: 'Ready' },
  failed: { color: 'error', icon: XCircle, label: 'Failed' },
  cancelled: { color: 'default', icon: XCircle, label: 'Cancelled' }
};

export function VideoList() {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deleteVideo, setDeleteVideo] = useState(null);

  useEffect(() => { fetchVideos(); }, []);

  const fetchVideos = async () => {
    try {
      const res = await videoApi.listVideos();
      setVideos(res.data.videos);
    } catch (err) { toast.error('Failed to load videos'); }
    setLoading(false);
  };

  const handleDelete = async () => {
    if (!deleteVideo) return;
    try {
      await videoApi.deleteVideo(deleteVideo.id);
      toast.success('Video deleted');
      fetchVideos();
    } catch (err) { toast.error('Failed to delete'); }
    setDeleteVideo(null);
  };

  if (loading) return <LoadingState message="Loading videos..." />;

  const completed = videos.filter(v => v.status === 'completed').length;
  const processing = videos.filter(v => ['pending', 'generating_audio', 'generating_avatar', 'generating_video', 'processing'].includes(v.status)).length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title flex items-center gap-3"><Video className="w-8 h-8 text-accent" />Videos</h1>
          <p className="text-silver mt-1">Your generated talking head videos</p>
        </div>
        <Link to="/video/create" className="btn-primary flex items-center gap-2"><Plus className="w-4 h-4" />New Video</Link>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="p-4"><p className="text-silver text-sm">Total</p><p className="text-2xl font-bold text-pearl">{videos.length}</p></Card>
        <Card className="p-4"><p className="text-silver text-sm">Completed</p><p className="text-2xl font-bold text-success">{completed}</p></Card>
        <Card className="p-4"><p className="text-silver text-sm">Processing</p><p className="text-2xl font-bold text-warning">{processing}</p></Card>
        <Card className="p-4"><p className="text-silver text-sm">Total Cost</p><p className="text-2xl font-bold text-accent">${videos.reduce((a, v) => a + (v.total_cost_usd || 0), 0).toFixed(2)}</p></Card>
      </div>

      {videos.length === 0 ? (
        <EmptyState icon={Video} title="No videos yet" description="Create your first talking head video" action={<Link to="/video/create" className="btn-primary">Create Video</Link>} />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {videos.map(video => {
            const status = statusConfig[video.status] || statusConfig.pending;
            const StatusIcon = status.icon;
            const isProcessing = ['pending', 'generating_audio', 'generating_avatar', 'generating_video', 'processing'].includes(video.status);

            return (
              <Card key={video.id} className="overflow-hidden group">
                <div className="aspect-video bg-slate relative">
                  {video.thumbnail_url ? (
                    <img src={video.thumbnail_url} alt="" className="w-full h-full object-cover" />
                  ) : video.video_url ? (
                    <video src={video.video_url} className="w-full h-full object-cover" />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      {isProcessing ? <RefreshCw className="w-8 h-8 text-accent animate-spin" /> : <Video className="w-8 h-8 text-silver" />}
                    </div>
                  )}
                  {video.status === 'completed' && video.video_url && (
                    <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                      <Play className="w-12 h-12 text-white" />
                    </div>
                  )}
                  <Badge className={`absolute top-2 right-2 ${status.color === 'success' ? 'bg-success' : status.color === 'error' ? 'bg-error' : status.color === 'warning' ? 'bg-warning' : 'bg-info'} text-white`}>
                    <StatusIcon className={`w-3 h-3 mr-1 ${isProcessing ? 'animate-spin' : ''}`} />{status.label}
                  </Badge>
                </div>
                <div className="p-4">
                  <h3 className="font-semibold text-pearl truncate">{video.title || 'Untitled'}</h3>
                  <p className="text-silver text-sm line-clamp-2 mt-1">{video.script?.slice(0, 100)}...</p>
                  <div className="flex items-center justify-between mt-3">
                    <span className="text-xs text-silver">{new Date(video.created_at).toLocaleDateString()}</span>
                    <span className="text-xs text-accent">${video.total_cost_usd?.toFixed(2)}</span>
                  </div>
                  <div className="flex gap-2 mt-3">
                    <Link to={`/video/${video.id}`} className="btn-secondary flex-1 text-center text-sm py-2">View</Link>
                    {video.video_url && <a href={video.video_url} download className="p-2 text-silver hover:text-accent"><Download className="w-4 h-4" /></a>}
                    <button onClick={() => setDeleteVideo(video)} className="p-2 text-silver hover:text-error"><Trash2 className="w-4 h-4" /></button>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      <ConfirmDialog isOpen={!!deleteVideo} onClose={() => setDeleteVideo(null)} onConfirm={handleDelete} title="Delete Video?" message="This cannot be undone." confirmText="Delete" danger />
    </div>
  );
}

export function VideoDetail() {
  const { id } = useParams();
  const [video, setVideo] = useState(null);
  const [progress, setProgress] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchVideo = useCallback(async () => {
    try {
      const res = await videoApi.getVideo(id);
      setVideo(res.data);
      if (['pending', 'generating_audio', 'generating_avatar', 'generating_video', 'processing'].includes(res.data.status)) {
        fetchProgress();
      }
    } catch (err) { toast.error('Failed to load video'); }
    setLoading(false);
  }, [id]);

  const fetchProgress = async () => {
    try {
      const res = await videoApi.getProgress(id);
      setProgress(res.data);
    } catch (err) {}
  };

  useEffect(() => { fetchVideo(); }, [fetchVideo]);

  useEffect(() => {
    if (video && ['pending', 'generating_audio', 'generating_avatar', 'generating_video', 'processing'].includes(video.status)) {
      const interval = setInterval(() => { fetchVideo(); fetchProgress(); }, 5000);
      return () => clearInterval(interval);
    }
  }, [video?.status, fetchVideo]);

  const copyScript = () => { navigator.clipboard.writeText(video.script); toast.success('Script copied!'); };

  if (loading) return <LoadingState message="Loading video..." />;
  if (!video) return <div className="text-center py-12 text-silver">Video not found</div>;

  const status = statusConfig[video.status] || statusConfig.pending;
  const StatusIcon = status.icon;
  const isProcessing = ['pending', 'generating_audio', 'generating_avatar', 'generating_video', 'processing'].includes(video.status);

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title">{video.title || 'Untitled Video'}</h1>
          <div className="flex items-center gap-3 mt-2">
            <Badge className={`${status.color === 'success' ? 'bg-success' : status.color === 'error' ? 'bg-error' : 'bg-info'} text-white`}>
              <StatusIcon className={`w-3 h-3 mr-1 ${isProcessing ? 'animate-spin' : ''}`} />{status.label}
            </Badge>
            <span className="text-silver text-sm">{new Date(video.created_at).toLocaleString()}</span>
          </div>
        </div>
        <Link to="/video" className="btn-secondary">← Back</Link>
      </div>

      {/* Progress */}
      {isProcessing && progress && (
        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="section-title flex items-center gap-2"><RefreshCw className="w-5 h-5 animate-spin text-accent" />Processing</h2>
            <span className="text-pearl font-mono">{progress.progress_percent}%</span>
          </div>
          <div className="h-3 bg-slate rounded-full overflow-hidden mb-2">
            <div className="h-full bg-accent transition-all" style={{ width: `${progress.progress_percent}%` }} />
          </div>
          <p className="text-silver text-sm">{progress.current_step} • {progress.estimated_time_remaining ? `~${Math.round(progress.estimated_time_remaining / 60)} min remaining` : 'Estimating...'}</p>
        </Card>
      )}

      {/* Video Player */}
      {video.video_url && (
        <Card className="p-6">
          <h2 className="section-title mb-4">Video</h2>
          <video src={video.video_url} controls className="w-full rounded-xl bg-black" poster={video.thumbnail_url} />
          <div className="flex gap-3 mt-4">
            <a href={video.video_url} download className="btn-primary flex items-center gap-2"><Download className="w-4 h-4" />Download</a>
            {video.audio_url && <a href={video.audio_url} download className="btn-secondary">Download Audio</a>}
          </div>
        </Card>
      )}

      {/* Error */}
      {video.status === 'failed' && (
        <Card className="p-6 border-error">
          <h2 className="section-title text-error mb-2">Generation Failed</h2>
          <p className="text-silver">{video.error_message || 'Unknown error'}</p>
          <Link to="/video/create" className="btn-primary mt-4">Try Again</Link>
        </Card>
      )}

      {/* Script */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="section-title">Script</h2>
          <button onClick={copyScript} className="text-accent text-sm flex items-center gap-1"><Copy className="w-4 h-4" />Copy</button>
        </div>
        <p className="text-pearl whitespace-pre-wrap">{video.script}</p>
        <p className="text-silver text-sm mt-4">{video.script.length} characters • ~{video.audio_duration_seconds?.toFixed(1) || Math.ceil(video.script.split(' ').length / 150 * 60)}s</p>
      </Card>

      {/* Details */}
      <Card className="p-6">
        <h2 className="section-title mb-4">Details</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div><p className="text-silver text-sm">Voice</p><p className="text-pearl">{video.voice_name || video.voice_provider}</p></div>
          <div><p className="text-silver text-sm">Aspect Ratio</p><p className="text-pearl">{video.aspect_ratio}</p></div>
          <div><p className="text-silver text-sm">Expression</p><p className="text-pearl capitalize">{video.expression}</p></div>
          <div><p className="text-silver text-sm">Resolution</p><p className="text-pearl">{video.resolution}</p></div>
        </div>
      </Card>

      {/* Cost */}
      <Card className="p-6">
        <h2 className="section-title mb-4">Cost Breakdown</h2>
        <div className="space-y-2">
          <div className="flex justify-between"><span className="text-silver">Audio</span><span className="text-pearl">${video.audio_cost_usd?.toFixed(3) || '0.000'}</span></div>
          <div className="flex justify-between"><span className="text-silver">Video</span><span className="text-pearl">${video.video_cost_usd?.toFixed(3) || '0.000'}</span></div>
          <hr className="border-graphite" />
          <div className="flex justify-between font-bold"><span className="text-pearl">Total</span><span className="text-accent">${video.total_cost_usd?.toFixed(2) || '0.00'}</span></div>
        </div>
      </Card>
    </div>
  );
}

export default VideoList;
