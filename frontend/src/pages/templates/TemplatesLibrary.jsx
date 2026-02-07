import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Rocket, MessageCircle, BookOpen, Tag, Heart, Calendar,
  Camera, Users, Search, Filter, ChevronRight, Copy, Zap,
  Instagram, Twitter, Linkedin, Facebook, Star
} from 'lucide-react';
import api from '../../services/api';
import { Card, LoadingState, Badge, Modal } from '../../components/ui';
import toast from 'react-hot-toast';

// Icon mapping for categories
const categoryIcons = {
  rocket: Rocket,
  'message-circle': MessageCircle,
  'book-open': BookOpen,
  tag: Tag,
  heart: Heart,
  calendar: Calendar,
  camera: Camera,
  users: Users
};

// Platform icons
const platformIcons = {
  instagram: Instagram,
  twitter: Twitter,
  linkedin: Linkedin,
  facebook: Facebook
};

export default function TemplatesLibrary() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [categories, setCategories] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [recommended, setRecommended] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    fetchTemplates();
  }, [selectedCategory, searchQuery]);

  const fetchData = async () => {
    try {
      const [categoriesRes, recommendedRes] = await Promise.all([
        api.get('/templates/categories'),
        api.get('/templates/recommended')
      ]);
      setCategories(categoriesRes.data.categories);
      setRecommended(recommendedRes.data.templates);
    } catch (err) {
      toast.error('Failed to load templates');
    }
    setLoading(false);
  };

  const fetchTemplates = async () => {
    try {
      const params = new URLSearchParams();
      if (selectedCategory) params.append('category_id', selectedCategory);
      if (searchQuery) params.append('search', searchQuery);
      
      const res = await api.get(`/templates/?${params.toString()}`);
      setTemplates(res.data.templates);
    } catch (err) {
      console.error('Failed to fetch templates:', err);
    }
  };

  const handleUseTemplate = (template) => {
    setSelectedTemplate(template);
    setShowModal(true);
  };

  const handleCopyPrompt = (template) => {
    navigator.clipboard.writeText(template.prompt_template);
    toast.success('Prompt copied to clipboard!');
  };

  const handleGenerateWithTemplate = () => {
    // Navigate to studio with template pre-selected
    navigate(`/studio/new?template=${selectedTemplate.id}`);
  };

  if (loading) return <LoadingState message="Loading templates..." />;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-pearl">Content Templates</h1>
        <p className="text-silver">Pre-built templates to jumpstart your content creation</p>
      </div>

      {/* Search & Filter */}
      <div className="flex flex-col md:flex-row gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-silver" />
          <input
            type="text"
            placeholder="Search templates..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-3 rounded-lg bg-slate border border-graphite text-pearl placeholder-silver focus:border-accent focus:outline-none"
          />
        </div>
        <select
          value={selectedCategory || ''}
          onChange={(e) => setSelectedCategory(e.target.value || null)}
          className="px-4 py-3 rounded-lg bg-slate border border-graphite text-pearl focus:border-accent focus:outline-none"
        >
          <option value="">All Categories</option>
          {categories.map(cat => (
            <option key={cat.id} value={cat.id}>{cat.name}</option>
          ))}
        </select>
      </div>

      {/* Recommended Templates */}
      {!selectedCategory && !searchQuery && recommended.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-4">
            <Star className="w-5 h-5 text-yellow-500" />
            <h2 className="text-lg font-semibold text-pearl">Recommended for You</h2>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {recommended.slice(0, 6).map(template => (
              <TemplateCard
                key={template.id}
                template={template}
                onUse={() => handleUseTemplate(template)}
                onCopy={() => handleCopyPrompt(template)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Categories */}
      {!selectedCategory && !searchQuery && (
        <div>
          <h2 className="text-lg font-semibold text-pearl mb-4">Browse by Category</h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
            {categories.map(category => {
              const IconComponent = categoryIcons[category.icon] || MessageCircle;
              const templateCount = templates.filter(t => t.category_id === category.id).length;
              
              return (
                <button
                  key={category.id}
                  onClick={() => setSelectedCategory(category.id)}
                  className="p-5 rounded-xl bg-charcoal border border-graphite hover:border-accent transition-all text-left group"
                >
                  <div className="w-12 h-12 rounded-lg bg-accent/20 flex items-center justify-center mb-3 group-hover:bg-accent/30 transition-colors">
                    <IconComponent className="w-6 h-6 text-accent" />
                  </div>
                  <h3 className="font-semibold text-pearl mb-1">{category.name}</h3>
                  <p className="text-sm text-silver line-clamp-2">{category.description}</p>
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Template List */}
      {(selectedCategory || searchQuery) && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              {selectedCategory && (
                <button
                  onClick={() => setSelectedCategory(null)}
                  className="text-accent hover:underline"
                >
                  ← Back to categories
                </button>
              )}
              <span className="text-silver">
                {templates.length} template{templates.length !== 1 ? 's' : ''} found
              </span>
            </div>
          </div>
          
          {templates.length === 0 ? (
            <Card className="p-8 text-center">
              <p className="text-silver">No templates found matching your criteria.</p>
            </Card>
          ) : (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              {templates.map(template => (
                <TemplateCard
                  key={template.id}
                  template={template}
                  onUse={() => handleUseTemplate(template)}
                  onCopy={() => handleCopyPrompt(template)}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Template Detail Modal */}
      <Modal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        title={selectedTemplate?.name || 'Template Details'}
        size="lg"
      >
        {selectedTemplate && (
          <div className="space-y-6">
            <p className="text-silver">{selectedTemplate.description}</p>
            
            {/* Platforms */}
            <div>
              <h4 className="text-sm font-medium text-pearl mb-2">Best for platforms:</h4>
              <div className="flex gap-2">
                {selectedTemplate.platforms.map(platform => {
                  const PlatformIcon = platformIcons[platform] || MessageCircle;
                  return (
                    <div key={platform} className="flex items-center gap-1 px-3 py-1 bg-slate rounded-full">
                      <PlatformIcon className="w-4 h-4 text-silver" />
                      <span className="text-sm text-silver capitalize">{platform}</span>
                    </div>
                  );
                })}
              </div>
            </div>
            
            {/* Prompt Template */}
            <div>
              <h4 className="text-sm font-medium text-pearl mb-2">Prompt Template:</h4>
              <div className="p-4 bg-slate rounded-lg">
                <p className="text-silver text-sm font-mono">{selectedTemplate.prompt_template}</p>
              </div>
            </div>
            
            {/* Variables */}
            <div>
              <h4 className="text-sm font-medium text-pearl mb-2">Variables to fill:</h4>
              <div className="flex flex-wrap gap-2">
                {selectedTemplate.variables.map(variable => (
                  <span key={variable} className="px-3 py-1 bg-accent/20 text-accent rounded-full text-sm">
                    {`{${variable}}`}
                  </span>
                ))}
              </div>
            </div>
            
            {/* Example Output */}
            <div>
              <h4 className="text-sm font-medium text-pearl mb-2">Example Output:</h4>
              <div className="p-4 bg-slate rounded-lg border-l-4 border-accent">
                <p className="text-pearl whitespace-pre-wrap text-sm">{selectedTemplate.example_output}</p>
              </div>
            </div>
            
            {/* Tips */}
            <div>
              <h4 className="text-sm font-medium text-pearl mb-2">Pro Tips:</h4>
              <ul className="space-y-1">
                {selectedTemplate.tips.map((tip, i) => (
                  <li key={i} className="text-sm text-silver flex items-start gap-2">
                    <span className="text-accent">•</span>
                    {tip}
                  </li>
                ))}
              </ul>
            </div>
            
            {/* Actions */}
            <div className="flex gap-3 pt-4 border-t border-graphite">
              <button
                onClick={() => handleCopyPrompt(selectedTemplate)}
                className="flex-1 py-3 rounded-lg border border-graphite text-silver hover:text-pearl hover:border-silver transition-all flex items-center justify-center gap-2"
              >
                <Copy className="w-4 h-4" />
                Copy Prompt
              </button>
              <button
                onClick={handleGenerateWithTemplate}
                className="flex-1 btn-primary py-3 flex items-center justify-center gap-2"
              >
                <Zap className="w-4 h-4" />
                Use Template
              </button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}

// Template Card Component
function TemplateCard({ template, onUse, onCopy }) {
  return (
    <Card className="p-5 hover:border-accent/50 transition-all">
      <div className="flex justify-between items-start mb-3">
        <h3 className="font-semibold text-pearl">{template.name}</h3>
        <Badge variant="default" className="text-xs">{template.category_id.replace('_', ' ')}</Badge>
      </div>
      
      <p className="text-sm text-silver mb-4 line-clamp-2">{template.description}</p>
      
      {/* Platforms */}
      <div className="flex gap-1 mb-4">
        {template.platforms.slice(0, 4).map(platform => {
          const PlatformIcon = platformIcons[platform] || MessageCircle;
          return (
            <div key={platform} className="w-6 h-6 rounded bg-slate flex items-center justify-center" title={platform}>
              <PlatformIcon className="w-3.5 h-3.5 text-silver" />
            </div>
          );
        })}
      </div>
      
      {/* Best For */}
      <div className="flex flex-wrap gap-1 mb-4">
        {template.best_for.slice(0, 2).map((use, i) => (
          <span key={i} className="text-xs px-2 py-0.5 bg-slate rounded text-silver">
            {use}
          </span>
        ))}
      </div>
      
      {/* Actions */}
      <div className="flex gap-2">
        <button
          onClick={onCopy}
          className="flex-1 py-2 text-sm rounded border border-graphite text-silver hover:text-pearl hover:border-silver transition-all"
        >
          Copy
        </button>
        <button
          onClick={onUse}
          className="flex-1 py-2 text-sm rounded bg-accent text-midnight hover:bg-accent/90 transition-all font-medium"
        >
          Use
        </button>
      </div>
    </Card>
  );
}
