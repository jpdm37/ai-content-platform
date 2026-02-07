import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  User, Briefcase, Zap, Users, DollarSign, 
  ChevronRight, ChevronLeft, Check, Sparkles,
  Instagram, Twitter, Linkedin, ArrowRight
} from 'lucide-react';
import api from '../../services/api';
import { Card, Spinner } from '../../components/ui';
import toast from 'react-hot-toast';

// Goal icons mapping
const goalIcons = {
  user: User,
  briefcase: Briefcase,
  zap: Zap,
  users: Users,
  'dollar-sign': DollarSign
};

export default function OnboardingWizard() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [status, setStatus] = useState(null);
  const [goals, setGoals] = useState([]);
  const [templates, setTemplates] = useState([]);
  
  // Form state
  const [selectedGoal, setSelectedGoal] = useState(null);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [brandName, setBrandName] = useState('');
  const [createdBrand, setCreatedBrand] = useState(null);
  const [generatedContent, setGeneratedContent] = useState(null);

  useEffect(() => {
    fetchOnboardingData();
  }, []);

  const fetchOnboardingData = async () => {
    try {
      const [statusRes, goalsRes] = await Promise.all([
        api.get('/onboarding/status'),
        api.get('/onboarding/goals')
      ]);
      
      setStatus(statusRes.data);
      setGoals(goalsRes.data.goals);
      
      // If already has a goal, fetch templates
      if (statusRes.data.selected_goal) {
        setSelectedGoal(statusRes.data.selected_goal);
        const templatesRes = await api.get(`/onboarding/brand-templates?goal_id=${statusRes.data.selected_goal}`);
        setTemplates(templatesRes.data.templates);
      }
      
      // If onboarding is complete, redirect to dashboard
      if (statusRes.data.is_complete) {
        navigate('/');
      }
    } catch (err) {
      console.error('Failed to fetch onboarding data:', err);
      toast.error('Failed to load onboarding');
    }
    setLoading(false);
  };

  const handleSelectGoal = async (goalId) => {
    setSelectedGoal(goalId);
    setSubmitting(true);
    
    try {
      await api.post('/onboarding/goals', { goal_id: goalId });
      
      // Fetch templates for this goal
      const templatesRes = await api.get(`/onboarding/brand-templates?goal_id=${goalId}`);
      setTemplates(templatesRes.data.templates);
      
      // Update status
      const statusRes = await api.get('/onboarding/status');
      setStatus(statusRes.data);
    } catch (err) {
      toast.error('Failed to save goal');
    }
    setSubmitting(false);
  };

  const handleCreateBrand = async () => {
    if (!brandName.trim() || !selectedTemplate) {
      toast.error('Please enter a brand name and select a template');
      return;
    }
    
    setSubmitting(true);
    try {
      const res = await api.post('/onboarding/brand', {
        template_id: selectedTemplate,
        brand_name: brandName
      });
      
      setCreatedBrand(res.data);
      
      // Update status
      const statusRes = await api.get('/onboarding/status');
      setStatus(statusRes.data);
      
      toast.success('Brand created! Now let\'s generate some content.');
    } catch (err) {
      toast.error('Failed to create brand');
    }
    setSubmitting(false);
  };

  const handleGenerateContent = async () => {
    if (!createdBrand) return;
    
    setSubmitting(true);
    try {
      const res = await api.post('/onboarding/generate-content', {
        brand_id: createdBrand.id,
        content_type: 'caption'
      });
      
      setGeneratedContent(res.data);
      
      // Update status
      const statusRes = await api.get('/onboarding/status');
      setStatus(statusRes.data);
      
      toast.success('Content generated!');
    } catch (err) {
      toast.error('Failed to generate content');
    }
    setSubmitting(false);
  };

  const handleSkip = async () => {
    try {
      await api.post('/onboarding/skip');
      navigate('/');
    } catch (err) {
      toast.error('Failed to skip onboarding');
    }
  };

  const handleComplete = async () => {
    try {
      await api.post('/onboarding/step', { step_id: 'complete', completed: true });
      toast.success('Welcome to the platform! 🎉');
      navigate('/');
    } catch (err) {
      navigate('/');
    }
  };

  const getCurrentStepIndex = () => {
    if (!status) return 0;
    const stepOrder = ['welcome', 'select_goal', 'create_brand', 'first_content', 'connect_social', 'complete'];
    return stepOrder.indexOf(status.current_step);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center gradient-bg">
        <Spinner size="lg" />
      </div>
    );
  }

  const currentStep = getCurrentStepIndex();

  return (
    <div className="min-h-screen gradient-bg py-12 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Progress bar */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-silver">Getting Started</span>
            <span className="text-sm text-silver">{status?.progress_percent || 0}% Complete</span>
          </div>
          <div className="h-2 bg-slate rounded-full overflow-hidden">
            <div 
              className="h-full bg-accent transition-all duration-500"
              style={{ width: `${status?.progress_percent || 0}%` }}
            />
          </div>
        </div>

        {/* Step 1: Welcome */}
        {currentStep === 0 && (
          <Card className="p-8 text-center">
            <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-accent/20 flex items-center justify-center">
              <Sparkles className="w-10 h-10 text-accent" />
            </div>
            <h1 className="text-3xl font-bold text-pearl mb-4">Welcome to AI Content Platform! 🎉</h1>
            <p className="text-silver text-lg mb-8 max-w-xl mx-auto">
              Let's get you set up in just a few minutes. We'll help you create your first brand 
              and generate some amazing content.
            </p>
            <div className="flex justify-center gap-4">
              <button 
                onClick={() => api.post('/onboarding/step', { step_id: 'welcome', completed: true }).then(fetchOnboardingData)}
                className="btn-primary px-8 py-3 text-lg"
              >
                Let's Get Started <ChevronRight className="inline w-5 h-5 ml-2" />
              </button>
            </div>
            <button onClick={handleSkip} className="mt-4 text-silver hover:text-pearl text-sm">
              Skip onboarding
            </button>
          </Card>
        )}

        {/* Step 2: Select Goal */}
        {currentStep === 1 && (
          <Card className="p-8">
            <h2 className="text-2xl font-bold text-pearl mb-2">What brings you here?</h2>
            <p className="text-silver mb-8">This helps us personalize your experience</p>
            
            <div className="grid md:grid-cols-2 gap-4 mb-8">
              {goals.map((goal) => {
                const IconComponent = goalIcons[goal.icon] || User;
                return (
                  <button
                    key={goal.id}
                    onClick={() => handleSelectGoal(goal.id)}
                    disabled={submitting}
                    className={`p-6 rounded-xl border-2 text-left transition-all ${
                      selectedGoal === goal.id 
                        ? 'border-accent bg-accent/10' 
                        : 'border-graphite hover:border-silver'
                    }`}
                  >
                    <div className="flex items-start gap-4">
                      <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${
                        selectedGoal === goal.id ? 'bg-accent/20' : 'bg-slate'
                      }`}>
                        <IconComponent className={`w-6 h-6 ${
                          selectedGoal === goal.id ? 'text-accent' : 'text-silver'
                        }`} />
                      </div>
                      <div>
                        <h3 className="font-semibold text-pearl mb-1">{goal.name}</h3>
                        <p className="text-sm text-silver">{goal.description}</p>
                      </div>
                      {selectedGoal === goal.id && (
                        <Check className="w-5 h-5 text-accent ml-auto" />
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          </Card>
        )}

        {/* Step 3: Create Brand */}
        {currentStep === 2 && (
          <Card className="p-8">
            <h2 className="text-2xl font-bold text-pearl mb-2">Create Your First Brand</h2>
            <p className="text-silver mb-8">Choose a template to get started quickly</p>
            
            {/* Brand name input */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-pearl mb-2">Brand Name</label>
              <input
                type="text"
                value={brandName}
                onChange={(e) => setBrandName(e.target.value)}
                placeholder="e.g., My Awesome Brand"
                className="w-full px-4 py-3 rounded-lg bg-slate border border-graphite text-pearl placeholder-silver focus:border-accent focus:outline-none"
              />
            </div>
            
            {/* Template selection */}
            <div className="mb-8">
              <label className="block text-sm font-medium text-pearl mb-4">Choose a Template</label>
              <div className="grid md:grid-cols-2 gap-4">
                {templates.map((template) => (
                  <button
                    key={template.id}
                    onClick={() => setSelectedTemplate(template.id)}
                    className={`p-5 rounded-xl border-2 text-left transition-all ${
                      selectedTemplate === template.id 
                        ? 'border-accent bg-accent/10' 
                        : 'border-graphite hover:border-silver'
                    }`}
                  >
                    <h3 className="font-semibold text-pearl mb-1">{template.name}</h3>
                    <p className="text-sm text-silver mb-2">{template.description}</p>
                    <p className="text-xs text-silver italic">Voice: {template.persona_voice}</p>
                    {selectedTemplate === template.id && (
                      <Check className="w-5 h-5 text-accent mt-2" />
                    )}
                  </button>
                ))}
              </div>
            </div>
            
            <button
              onClick={handleCreateBrand}
              disabled={!brandName.trim() || !selectedTemplate || submitting}
              className="btn-primary w-full py-3 disabled:opacity-50"
            >
              {submitting ? <Spinner size="sm" /> : 'Create Brand'}
            </button>
          </Card>
        )}

        {/* Step 4: Generate First Content */}
        {currentStep === 3 && (
          <Card className="p-8">
            <h2 className="text-2xl font-bold text-pearl mb-2">Generate Your First Content</h2>
            <p className="text-silver mb-8">Let's see AI content generation in action!</p>
            
            {!generatedContent ? (
              <div className="text-center py-8">
                <div className="w-24 h-24 mx-auto mb-6 rounded-full bg-accent/20 flex items-center justify-center">
                  <Zap className="w-12 h-12 text-accent" />
                </div>
                <p className="text-silver mb-6">
                  Click the button below to generate an engaging social media post for <strong className="text-pearl">{createdBrand?.name || 'your brand'}</strong>
                </p>
                <button
                  onClick={handleGenerateContent}
                  disabled={submitting}
                  className="btn-primary px-8 py-3"
                >
                  {submitting ? (
                    <>
                      <Spinner size="sm" className="mr-2" />
                      Generating...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-5 h-5 mr-2 inline" />
                      Generate Content
                    </>
                  )}
                </button>
              </div>
            ) : (
              <div className="space-y-6">
                <div className="p-6 bg-slate rounded-xl">
                  <h3 className="text-sm font-medium text-silver mb-2">Generated Caption</h3>
                  <p className="text-pearl text-lg">{generatedContent.caption}</p>
                  
                  {generatedContent.hashtags && generatedContent.hashtags.length > 0 && (
                    <div className="mt-4">
                      <h3 className="text-sm font-medium text-silver mb-2">Hashtags</h3>
                      <div className="flex flex-wrap gap-2">
                        {generatedContent.hashtags.map((tag, i) => (
                          <span key={i} className="px-3 py-1 bg-accent/20 text-accent rounded-full text-sm">
                            #{tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
                
                <div className="bg-green-500/10 border border-green-500/30 rounded-xl p-4">
                  <p className="text-green-400 flex items-center">
                    <Check className="w-5 h-5 mr-2" />
                    Amazing! You just created your first AI-generated content.
                  </p>
                </div>
                
                <button
                  onClick={() => api.post('/onboarding/step', { step_id: 'first_content', completed: true }).then(fetchOnboardingData)}
                  className="btn-primary w-full py-3"
                >
                  Continue <ChevronRight className="inline w-5 h-5 ml-2" />
                </button>
              </div>
            )}
          </Card>
        )}

        {/* Step 5: Connect Social (Optional) */}
        {currentStep === 4 && (
          <Card className="p-8">
            <h2 className="text-2xl font-bold text-pearl mb-2">Connect Your Social Accounts</h2>
            <p className="text-silver mb-8">Post directly to your favorite platforms (optional)</p>
            
            <div className="grid md:grid-cols-3 gap-4 mb-8">
              <button className="p-6 rounded-xl border-2 border-graphite hover:border-pink-500 transition-all">
                <Instagram className="w-8 h-8 text-pink-500 mx-auto mb-3" />
                <span className="text-pearl">Instagram</span>
              </button>
              <button className="p-6 rounded-xl border-2 border-graphite hover:border-blue-400 transition-all">
                <Twitter className="w-8 h-8 text-blue-400 mx-auto mb-3" />
                <span className="text-pearl">Twitter/X</span>
              </button>
              <button className="p-6 rounded-xl border-2 border-graphite hover:border-blue-600 transition-all">
                <Linkedin className="w-8 h-8 text-blue-600 mx-auto mb-3" />
                <span className="text-pearl">LinkedIn</span>
              </button>
            </div>
            
            <div className="flex gap-4">
              <button
                onClick={handleComplete}
                className="flex-1 py-3 rounded-lg border border-graphite text-silver hover:text-pearl hover:border-silver transition-all"
              >
                Skip for now
              </button>
              <button
                onClick={() => navigate('/social/accounts')}
                className="flex-1 btn-primary py-3"
              >
                Connect Accounts
              </button>
            </div>
          </Card>
        )}

        {/* Step 6: Complete */}
        {currentStep >= 5 && (
          <Card className="p-8 text-center">
            <div className="w-24 h-24 mx-auto mb-6 rounded-full bg-green-500/20 flex items-center justify-center">
              <Check className="w-12 h-12 text-green-500" />
            </div>
            <h1 className="text-3xl font-bold text-pearl mb-4">You're All Set! 🎉</h1>
            <p className="text-silver text-lg mb-8 max-w-xl mx-auto">
              Your account is ready. Start creating amazing content and grow your brand with AI.
            </p>
            
            <div className="grid md:grid-cols-3 gap-4 mb-8 text-left">
              <div className="p-4 bg-slate rounded-xl">
                <h3 className="font-semibold text-pearl mb-2">Content Studio</h3>
                <p className="text-sm text-silver">Create multi-platform content from a single brief</p>
              </div>
              <div className="p-4 bg-slate rounded-xl">
                <h3 className="font-semibold text-pearl mb-2">AI Assistant</h3>
                <p className="text-sm text-silver">Get help improving and optimizing your content</p>
              </div>
              <div className="p-4 bg-slate rounded-xl">
                <h3 className="font-semibold text-pearl mb-2">Schedule Posts</h3>
                <p className="text-sm text-silver">Plan and automate your social media calendar</p>
              </div>
            </div>
            
            <button onClick={handleComplete} className="btn-primary px-8 py-3 text-lg">
              Go to Dashboard <ArrowRight className="inline w-5 h-5 ml-2" />
            </button>
          </Card>
        )}
      </div>
    </div>
  );
}
