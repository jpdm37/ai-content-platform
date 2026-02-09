import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Sparkles, Plus, Clock, CheckCircle, XCircle, ChevronRight, Image, Video, Hash, MessageSquare, Zap, Trash2 } from 'lucide-react';
import { studioApi } from '../../services/api';
import { Card, Badge, LoadingState, EmptyState, Spinner } from '../../components/ui';
import toast from 'react-hot-toast';

const statusConfig = {
  draft: { color: 'bg-gray-500', label: 'Draft' },
  generating: { color: 'bg-blue-500', label: 'Generating' },
  completed: { color: 'bg-green-500', label: 'Complete' },
  partial: { color: 'bg-yellow-500', label: 'Partial' },
  failed: { color: 'bg-red-500', label: 'Failed' }
};

export default function StudioProjects() {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { fetchProjects(); }, []);

  const fetchProjects = async () => {
    try {
      const res = await studioApi.listProjects();
      setProjects(res.data.projects);
    } catch (err) { toast.error('Failed to load projects'); }
    setLoading(false);
  };

  const handleDelete = async (e, projectId) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (!confirm('Are you sure you want to delete this project?')) return;
    
    try {
      await studioApi.deleteProject(projectId);
      toast.success('Project deleted');
      setProjects(projects.filter(p => p.id !== projectId));
    } catch (err) {
      toast.error('Failed to delete project');
    }
  };

  if (loading) return <LoadingState message="Loading projects..." />;

  const stats = {
    total: projects.length,
    completed: projects.filter(p => p.status === 'completed').length,
    generating: projects.filter(p => p.status === 'generating').length
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title flex items-center gap-3">
            <Sparkles className="w-8 h-8 text-accent" />
            Content Studio
          </h1>
          <p className="text-silver mt-1">Generate complete content packages from a single brief</p>
        </div>
        <Link to="/studio/create" className="btn-primary flex items-center gap-2">
          <Plus className="w-4 h-4" />New Project
        </Link>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <Card className="p-4 text-center">
          <p className="text-silver text-sm">Total Projects</p>
          <p className="text-3xl font-bold text-pearl">{stats.total}</p>
        </Card>
        <Card className="p-4 text-center">
          <p className="text-silver text-sm">Completed</p>
          <p className="text-3xl font-bold text-success">{stats.completed}</p>
        </Card>
        <Card className="p-4 text-center">
          <p className="text-silver text-sm">In Progress</p>
          <p className="text-3xl font-bold text-warning">{stats.generating}</p>
        </Card>
      </div>

      {/* Projects List */}
      {projects.length === 0 ? (
        <EmptyState
          icon={Sparkles}
          title="No projects yet"
          description="Create your first content project to generate captions, images, videos, and more from a single brief"
          action={<Link to="/studio/create" className="btn-primary">Create Project</Link>}
        />
      ) : (
        <div className="space-y-4">
          {projects.map(project => {
            const status = statusConfig[project.status] || statusConfig.draft;
            const isGenerating = project.status === 'generating';

            return (
              <Link key={project.id} to={`/studio/${project.id}`}>
                <Card className="p-5 hover:border-accent/50 transition-colors">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3">
                        <h3 className="text-lg font-semibold text-pearl">{project.name}</h3>
                        <Badge className={`${status.color} text-white text-xs`}>
                          {isGenerating && <Spinner size="xs" className="mr-1" />}
                          {status.label}
                        </Badge>
                      </div>
                      <p className="text-silver mt-1 line-clamp-2">{project.brief}</p>
                      
                      <div className="flex items-center gap-4 mt-3">
                        <span className="flex items-center gap-1 text-sm text-silver">
                          <MessageSquare className="w-4 h-4" />
                          {project.captions_generated} captions
                        </span>
                        <span className="flex items-center gap-1 text-sm text-silver">
                          <Image className="w-4 h-4" />
                          {project.images_generated} images
                        </span>
                        {project.include_video && (
                          <span className="flex items-center gap-1 text-sm text-silver">
                            <Video className="w-4 h-4" />
                            {project.videos_generated} video
                          </span>
                        )}
                      </div>

                      <div className="flex items-center gap-2 mt-3">
                        {project.target_platforms?.map(p => (
                          <Badge key={p} variant="secondary" className="text-xs capitalize">{p}</Badge>
                        ))}
                      </div>
                    </div>

                    <div className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        <p className="text-xs text-silver">{new Date(project.created_at).toLocaleDateString()}</p>
                        <button
                          onClick={(e) => handleDelete(e, project.id)}
                          className="p-1.5 text-silver hover:text-red-500 hover:bg-red-500/10 rounded transition-colors"
                          title="Delete project"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                      {isGenerating && (
                        <div className="mt-2">
                          <div className="w-24 h-2 bg-slate rounded-full overflow-hidden">
                            <div className="h-full bg-accent transition-all" style={{ width: `${project.progress_percent}%` }} />
                          </div>
                          <p className="text-xs text-silver mt-1">{project.progress_percent}%</p>
                        </div>
                      )}
                      <ChevronRight className="w-5 h-5 text-silver mt-2 ml-auto" />
                    </div>
                  </div>
                </Card>
              </Link>
            );
          })}
        </div>
      )}

      {/* Quick Tips */}
      <Card className="p-5 bg-accent/10 border-accent/30">
        <h3 className="font-semibold text-pearl mb-3 flex items-center gap-2">
          <Zap className="w-5 h-5 text-accent" />
          What Content Studio Creates
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-accent" />
            <span className="text-sm text-silver">Caption variations</span>
          </div>
          <div className="flex items-center gap-2">
            <Hash className="w-5 h-5 text-accent" />
            <span className="text-sm text-silver">Hashtag sets</span>
          </div>
          <div className="flex items-center gap-2">
            <Image className="w-5 h-5 text-accent" />
            <span className="text-sm text-silver">Image options</span>
          </div>
          <div className="flex items-center gap-2">
            <Video className="w-5 h-5 text-accent" />
            <span className="text-sm text-silver">Talking head video</span>
          </div>
        </div>
      </Card>
    </div>
  );
}
