import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Sparkles, Building2, User, Share2, Wand2, Calendar,
  ChevronRight, ChevronLeft, Check, Target, Users, Briefcase,
  Instagram, Twitter, Linkedin, Facebook, Youtube,
  Loader2, Upload, CheckCircle2, ArrowRight, Zap, Clock
} from 'lucide-react';
import { brandsApi, loraApi, studioApi } from '../../services/api';
import { Card, Badge, Spinner } from '../../components/ui';
import toast from 'react-hot-toast';

// API helpers
const onboardingApi = {
  getStatus: () => fetch('/api/v1/onboarding/status').then(r => r.json()),
  saveGoals: (data) => fetch('/api/v1/onboarding/goals', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  }).then(r => r.json()),
  complete: () => fetch('/api/v1/onboarding/complete', { method: 'POST' }).then(r => r.json()),
};

const avatarApi = {
  generateConcepts: (data) => fetch('/api/v1/avatar/generate-concepts', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  }).then(r => r.json()),
  generateTrainingImages: (data) => fetch('/api/v1/avatar/generate-training-images', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  }).then(r => r.json()),
  createFromGenerated: (data) => fetch('/api/v1/avatar/create-from-generated', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  }).then(r => r.json()),
};

// Step definitions
const STEPS = [
  { id: 'welcome', title: 'Welcome', icon: Sparkles },
  { id: 'brand', title: 'Your Brand', icon: Building2 },
  { id: 'avatar', title: 'AI Avatar', icon: User },
  { id: 'social', title: 'Social Media', icon: Share2 },
  { id: 'content', title: 'First Content', icon: Wand2 },
  { id: 'complete', title: 'Ready!', icon: CheckCircle2 },
];

// User goals
const GOALS = [
  { id: 'grow_audience', label: 'Grow my audience', icon: Users, description: 'Build followers and engagement' },
  { id: 'save_time', label: 'Save time on content', icon: Clock, description: 'Automate content creation' },
  { id: 'consistent_brand', label: 'Consistent branding', icon: Target, description: 'Unified voice across platforms' },
  { id: 'more_content', label: 'Post more frequently', icon: Calendar, description: 'Never run out of content' },
];

// User types
const USER_TYPES = [
  { id: 'creator', label: 'Solo Creator', description: 'Individual influencer or content creator' },
  { id: 'business', label: 'Small Business', description: 'Company with 1-10 employees' },
  { id: 'agency', label: 'Agency', description: 'Managing multiple brands/clients' },
];

// Industries
const INDUSTRIES = [
  'Fashion & Beauty', 'Health & Fitness', 'Food & Beverage', 'Technology',
  'Finance', 'Real Estate', 'Education', 'Entertainment', 'Travel',
  'E-commerce', 'Professional Services', 'Other'
];

// Social platforms
const SOCIAL_PLATFORMS = [
  { id: 'instagram', name: 'Instagram', icon: Instagram, color: 'pink' },
  { id: 'twitter', name: 'Twitter/X', icon: Twitter, color: 'blue' },
  { id: 'linkedin', name: 'LinkedIn', icon: Linkedin, color: 'blue' },
  { id: 'facebook', name: 'Facebook', icon: Facebook, color: 'blue' },
  { id: 'youtube', name: 'YouTube', icon: Youtube, color: 'red' },
];

export default function OnboardingWizard() {
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Form data across all steps
  const [formData, setFormData] = useState({
    // Step 1: Welcome
    userType: '',
    goals: [],
    
    // Step 2: Brand
    brandName: '',
    industry: '',
    targetAudience: '',
    brandVoice: 'professional', // professional, casual, friendly, authoritative
    brandDescription: '',
    
    // Step 3: Avatar
    avatarMode: null, // 'generate' | 'upload' | 'skip'
    avatarConfig: {
      gender: '',
      age_range: '',
      style: 'professional',
      ethnicity: '',
      custom_description: ''
    },
    avatarConcepts: [],
    selectedConcept: null,
    avatarTrainingStarted: false,
    avatarModelId: null,
    
    // Step 4: Social
    connectedPlatforms: [],
    skippedSocial: false,
    
    // Step 5: Content
    firstContentBrief: '',
    generatedContent: null,
  });

  // Generation states
  const [generatingConcepts, setGeneratingConcepts] = useState(false);
  const [generatingTraining, setGeneratingTraining] = useState(false);
  const [generatingContent, setGeneratingContent] = useState(false);

  useEffect(() => {
    checkOnboardingStatus();
  }, []);

  const checkOnboardingStatus = async () => {
    try {
      const status = await onboardingApi.getStatus();
      if (status.is_complete) {
        navigate('/');
        return;
      }
      // Could resume from saved step here
    } catch (err) {
      console.log('No existing onboarding status');
    }
    setLoading(false);
  };

  const updateFormData = (updates) => {
    setFormData(prev => ({ ...prev, ...updates }));
  };

  const nextStep = () => {
    if (currentStep < STEPS.length - 1) {
      setCurrentStep(currentStep + 1);
      window.scrollTo(0, 0);
    }
  };

  const prevStep = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
      window.scrollTo(0, 0);
    }
  };

  // Step 2: Create Brand
  const handleCreateBrand = async () => {
    if (!formData.brandName.trim()) {
      toast.error('Please enter a brand name');
      return;
    }
    
    setSaving(true);
    try {
      const res = await brandsApi.create({
        name: formData.brandName,
        description: formData.brandDescription || `${formData.industry} brand targeting ${formData.targetAudience}`,
        industry: formData.industry,
        target_audience: formData.targetAudience,
        voice_tone: formData.brandVoice,
      });
      
      updateFormData({ brandId: res.data.id });
      toast.success('Brand created!');
      nextStep();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to create brand');
    }
    setSaving(false);
  };

  // Step 3: Generate Avatar Concepts
  const handleGenerateAvatarConcepts = async () => {
    const { avatarConfig } = formData;
    if (!avatarConfig.gender || !avatarConfig.age_range) {
      toast.error('Please select gender and age range');
      return;
    }

    setGeneratingConcepts(true);
    try {
      const result = await avatarApi.generateConcepts({
        brand_id: formData.brandId,
        avatar_name: `${formData.brandName} Avatar`,
        ...avatarConfig,
        num_concepts: 4
      });

      if (result.success && result.concepts?.length) {
        updateFormData({ 
          avatarConcepts: result.concepts,
          promptUsed: result.prompt_used 
        });
        toast.success('Avatar concepts ready!');
      } else {
        toast.error(result.error || 'Generation failed');
      }
    } catch (err) {
      toast.error('Failed to generate avatars');
    }
    setGeneratingConcepts(false);
  };

  // Step 3: Confirm avatar and start training
  const handleConfirmAvatar = async () => {
    if (!formData.selectedConcept) {
      toast.error('Please select an avatar');
      return;
    }

    setGeneratingTraining(true);
    try {
      // Generate training images
      const trainingResult = await avatarApi.generateTrainingImages({
        brand_id: formData.brandId,
        avatar_name: `${formData.brandName} Avatar`,
        selected_concept_url: formData.selectedConcept.image_url,
        selected_seed: formData.selectedConcept.seed,
        original_prompt: formData.promptUsed,
        requirements: formData.avatarConfig,
        num_training_images: 12
      });

      if (trainingResult.success) {
        // Start LoRA training
        const createResult = await avatarApi.createFromGenerated({
          brand_id: formData.brandId,
          avatar_name: `${formData.brandName} Avatar`,
          training_image_urls: [
            formData.selectedConcept.image_url,
            ...trainingResult.training_images.map(i => i.image_url)
          ],
          trigger_word: formData.brandName.toUpperCase().replace(/\s+/g, '_'),
          training_steps: 1000
        });

        if (createResult.success) {
          updateFormData({ 
            avatarTrainingStarted: true,
            avatarModelId: createResult.model_id 
          });
          toast.success('Avatar training started! It will be ready in ~20 minutes.');
          nextStep();
        } else {
          toast.error(createResult.message || 'Failed to start training');
        }
      } else {
        toast.error(trainingResult.error || 'Failed to create training images');
      }
    } catch (err) {
      toast.error('Avatar creation failed');
    }
    setGeneratingTraining(false);
  };

  // Step 4: Connect social (placeholder - would use OAuth)
  const handleConnectSocial = (platformId) => {
    // In production, this would trigger OAuth flow
    toast.success(`${platformId} connection coming soon!`);
    updateFormData({
      connectedPlatforms: [...formData.connectedPlatforms, platformId]
    });
  };

  // Step 5: Generate first content
  const handleGenerateFirstContent = async () => {
    setGeneratingContent(true);
    try {
      const brief = formData.firstContentBrief || 
        `Introduce ${formData.brandName} to our audience. Highlight our focus on ${formData.industry} and our commitment to serving ${formData.targetAudience}.`;

      const res = await studioApi.createProject({
        brief,
        name: 'Welcome Post',
        brand_id: formData.brandId,
        target_platforms: formData.connectedPlatforms.length > 0 
          ? formData.connectedPlatforms 
          : ['instagram'],
        content_types: ['caption', 'hashtags', 'image'],
        tone: formData.brandVoice,
        num_variations: 2,
      });

      updateFormData({ 
        generatedContent: res.data,
        contentProjectId: res.data.id 
      });
      toast.success('Your first content is ready!');
    } catch (err) {
      toast.error('Content generation failed');
    }
    setGeneratingContent(false);
  };

  // Complete onboarding
  const handleComplete = async () => {
    setSaving(true);
    try {
      await onboardingApi.complete();
      toast.success('Welcome aboard! 🎉');
      navigate('/');
    } catch (err) {
      // Still navigate even if API fails
      navigate('/');
    }
    setSaving(false);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-midnight">
        <Loader2 className="w-8 h-8 animate-spin text-accent" />
      </div>
    );
  }

  const currentStepData = STEPS[currentStep];

  return (
    <div className="min-h-screen bg-gradient-to-br from-midnight via-charcoal to-midnight">
      {/* Progress Header */}
      <div className="sticky top-0 z-50 bg-charcoal/90 backdrop-blur border-b border-graphite">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent to-accent-dark flex items-center justify-center">
                <Zap className="w-5 h-5 text-white" />
              </div>
              <span className="font-display font-bold text-xl text-pearl">AI Content Platform</span>
            </div>
            <span className="text-silver text-sm">
              Step {currentStep + 1} of {STEPS.length}
            </span>
          </div>
          
          {/* Progress Bar */}
          <div className="flex gap-2">
            {STEPS.map((step, i) => (
              <div 
                key={step.id}
                className={`h-1.5 flex-1 rounded-full transition-all ${
                  i < currentStep ? 'bg-success' :
                  i === currentStep ? 'bg-accent' :
                  'bg-slate'
                }`}
              />
            ))}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-2xl mx-auto px-4 py-8">
        
        {/* Step 0: Welcome */}
        {currentStep === 0 && (
          <div className="space-y-8 animate-fade-in">
            <div className="text-center">
              <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-accent to-accent-dark flex items-center justify-center">
                <Sparkles className="w-10 h-10 text-white" />
              </div>
              <h1 className="text-3xl font-display font-bold text-pearl mb-3">
                Welcome to AI Content Platform!
              </h1>
              <p className="text-silver text-lg">
                Let's set up your account in just a few minutes
              </p>
            </div>

            {/* User Type */}
            <Card className="p-6">
              <h2 className="text-lg font-bold text-pearl mb-4">What describes you best?</h2>
              <div className="space-y-3">
                {USER_TYPES.map(type => (
                  <button
                    key={type.id}
                    onClick={() => updateFormData({ userType: type.id })}
                    className={`w-full p-4 rounded-xl border-2 text-left transition-all ${
                      formData.userType === type.id
                        ? 'border-accent bg-accent/10'
                        : 'border-graphite hover:border-silver'
                    }`}
                  >
                    <p className={`font-medium ${formData.userType === type.id ? 'text-accent' : 'text-pearl'}`}>
                      {type.label}
                    </p>
                    <p className="text-silver text-sm">{type.description}</p>
                  </button>
                ))}
              </div>
            </Card>

            {/* Goals */}
            <Card className="p-6">
              <h2 className="text-lg font-bold text-pearl mb-4">What are your main goals?</h2>
              <p className="text-silver text-sm mb-4">Select all that apply</p>
              <div className="grid grid-cols-2 gap-3">
                {GOALS.map(goal => {
                  const Icon = goal.icon;
                  const selected = formData.goals.includes(goal.id);
                  return (
                    <button
                      key={goal.id}
                      onClick={() => {
                        const newGoals = selected
                          ? formData.goals.filter(g => g !== goal.id)
                          : [...formData.goals, goal.id];
                        updateFormData({ goals: newGoals });
                      }}
                      className={`p-4 rounded-xl border-2 text-left transition-all ${
                        selected
                          ? 'border-accent bg-accent/10'
                          : 'border-graphite hover:border-silver'
                      }`}
                    >
                      <Icon className={`w-6 h-6 mb-2 ${selected ? 'text-accent' : 'text-silver'}`} />
                      <p className={`font-medium text-sm ${selected ? 'text-accent' : 'text-pearl'}`}>
                        {goal.label}
                      </p>
                    </button>
                  );
                })}
              </div>
            </Card>

            <button
              onClick={nextStep}
              disabled={!formData.userType}
              className="btn-primary w-full py-4 text-lg flex items-center justify-center gap-2"
            >
              Get Started
              <ChevronRight className="w-5 h-5" />
            </button>
          </div>
        )}

        {/* Step 1: Brand */}
        {currentStep === 1 && (
          <div className="space-y-6 animate-fade-in">
            <div className="text-center mb-8">
              <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-accent/10 flex items-center justify-center">
                <Building2 className="w-8 h-8 text-accent" />
              </div>
              <h1 className="text-2xl font-display font-bold text-pearl mb-2">
                Tell us about your brand
              </h1>
              <p className="text-silver">
                This helps us create content that matches your voice
              </p>
            </div>

            <Card className="p-6 space-y-5">
              <div>
                <label className="block text-sm font-medium text-pearl mb-2">Brand Name *</label>
                <input
                  type="text"
                  value={formData.brandName}
                  onChange={(e) => updateFormData({ brandName: e.target.value })}
                  placeholder="e.g., Acme Inc, Sarah's Bakery"
                  className="input-field w-full text-lg"
                  autoFocus
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-pearl mb-2">Industry</label>
                <select
                  value={formData.industry}
                  onChange={(e) => updateFormData({ industry: e.target.value })}
                  className="input-field w-full"
                >
                  <option value="">Select your industry</option>
                  {INDUSTRIES.map(ind => (
                    <option key={ind} value={ind}>{ind}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-pearl mb-2">Target Audience</label>
                <input
                  type="text"
                  value={formData.targetAudience}
                  onChange={(e) => updateFormData({ targetAudience: e.target.value })}
                  placeholder="e.g., Young professionals, Health-conscious millennials"
                  className="input-field w-full"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-pearl mb-2">Brand Voice</label>
                <div className="grid grid-cols-2 gap-3">
                  {[
                    { id: 'professional', label: 'Professional', emoji: '💼' },
                    { id: 'casual', label: 'Casual & Friendly', emoji: '😊' },
                    { id: 'authoritative', label: 'Authoritative', emoji: '📚' },
                    { id: 'playful', label: 'Playful & Fun', emoji: '🎉' },
                  ].map(voice => (
                    <button
                      key={voice.id}
                      onClick={() => updateFormData({ brandVoice: voice.id })}
                      className={`p-3 rounded-xl border-2 text-left transition-all ${
                        formData.brandVoice === voice.id
                          ? 'border-accent bg-accent/10'
                          : 'border-graphite hover:border-silver'
                      }`}
                    >
                      <span className="text-xl mr-2">{voice.emoji}</span>
                      <span className={formData.brandVoice === voice.id ? 'text-accent' : 'text-pearl'}>
                        {voice.label}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            </Card>

            <div className="flex gap-3">
              <button onClick={prevStep} className="btn-secondary flex-1 py-3">
                <ChevronLeft className="w-5 h-5 mr-2" /> Back
              </button>
              <button
                onClick={handleCreateBrand}
                disabled={!formData.brandName.trim() || saving}
                className="btn-primary flex-1 py-3"
              >
                {saving ? <Loader2 className="w-5 h-5 animate-spin mr-2" /> : null}
                Continue <ChevronRight className="w-5 h-5 ml-2" />
              </button>
            </div>
          </div>
        )}

        {/* Step 2: Avatar */}
        {currentStep === 2 && (
          <div className="space-y-6 animate-fade-in">
            <div className="text-center mb-8">
              <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-accent/10 flex items-center justify-center">
                <User className="w-8 h-8 text-accent" />
              </div>
              <h1 className="text-2xl font-display font-bold text-pearl mb-2">
                Create Your AI Avatar
              </h1>
              <p className="text-silver">
                A consistent face for your brand across all content
              </p>
            </div>

            {/* Mode Selection */}
            {!formData.avatarMode && (
              <div className="grid grid-cols-1 gap-4">
                <button
                  onClick={() => updateFormData({ avatarMode: 'generate' })}
                  className="p-6 rounded-xl border-2 border-graphite hover:border-accent bg-gradient-to-br from-accent/5 to-transparent text-left transition-all"
                >
                  <Wand2 className="w-10 h-10 mb-3 text-accent" />
                  <h3 className="font-bold text-pearl text-lg">Generate New Avatar</h3>
                  <p className="text-silver mt-1">Create a unique AI avatar from scratch</p>
                  <Badge variant="success" className="mt-3">Recommended</Badge>
                </button>
                
                <button
                  onClick={() => updateFormData({ avatarMode: 'upload' })}
                  className="p-6 rounded-xl border-2 border-graphite hover:border-accent text-left transition-all"
                >
                  <Upload className="w-10 h-10 mb-3 text-silver" />
                  <h3 className="font-bold text-pearl text-lg">Upload Photos</h3>
                  <p className="text-silver mt-1">Use existing photos of your avatar</p>
                </button>

                <button
                  onClick={() => { updateFormData({ avatarMode: 'skip' }); nextStep(); }}
                  className="p-4 text-center text-silver hover:text-pearl transition-colors"
                >
                  Skip for now →
                </button>
              </div>
            )}

            {/* Generate Avatar Form */}
            {formData.avatarMode === 'generate' && formData.avatarConcepts.length === 0 && (
              <Card className="p-6 space-y-5">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-pearl mb-2">Gender *</label>
                    <div className="flex gap-2">
                      {['male', 'female'].map(g => (
                        <button
                          key={g}
                          onClick={() => updateFormData({ 
                            avatarConfig: { ...formData.avatarConfig, gender: g }
                          })}
                          className={`flex-1 py-2 rounded-lg border text-sm capitalize ${
                            formData.avatarConfig.gender === g
                              ? 'border-accent bg-accent/10 text-accent'
                              : 'border-graphite text-silver'
                          }`}
                        >
                          {g}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-pearl mb-2">Age Range *</label>
                    <select
                      value={formData.avatarConfig.age_range}
                      onChange={(e) => updateFormData({
                        avatarConfig: { ...formData.avatarConfig, age_range: e.target.value }
                      })}
                      className="input-field w-full"
                    >
                      <option value="">Select</option>
                      {['25-30', '31-40', '41-50', '51-60'].map(a => (
                        <option key={a} value={a}>{a}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-pearl mb-2">Style</label>
                  <div className="grid grid-cols-4 gap-2">
                    {['professional', 'influencer', 'corporate', 'creative'].map(s => (
                      <button
                        key={s}
                        onClick={() => updateFormData({
                          avatarConfig: { ...formData.avatarConfig, style: s }
                        })}
                        className={`py-2 rounded-lg border text-xs capitalize ${
                          formData.avatarConfig.style === s
                            ? 'border-accent bg-accent/10 text-accent'
                            : 'border-graphite text-silver'
                        }`}
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-pearl mb-2">Additional Details</label>
                  <input
                    value={formData.avatarConfig.custom_description}
                    onChange={(e) => updateFormData({
                      avatarConfig: { ...formData.avatarConfig, custom_description: e.target.value }
                    })}
                    placeholder="e.g., glasses, beard, athletic build..."
                    className="input-field w-full"
                  />
                </div>

                <button
                  onClick={handleGenerateAvatarConcepts}
                  disabled={generatingConcepts || !formData.avatarConfig.gender || !formData.avatarConfig.age_range}
                  className="btn-primary w-full py-3"
                >
                  {generatingConcepts ? (
                    <><Loader2 className="w-5 h-5 animate-spin mr-2" /> Generating...</>
                  ) : (
                    <><Wand2 className="w-5 h-5 mr-2" /> Generate Avatars</>
                  )}
                </button>
              </Card>
            )}

            {/* Avatar Selection */}
            {formData.avatarConcepts.length > 0 && !formData.avatarTrainingStarted && (
              <Card className="p-6 space-y-5">
                <h3 className="font-bold text-pearl">Choose your avatar:</h3>
                <div className="grid grid-cols-2 gap-4">
                  {formData.avatarConcepts.map((concept, i) => (
                    <button
                      key={i}
                      onClick={() => updateFormData({ selectedConcept: concept })}
                      className={`relative aspect-square rounded-xl overflow-hidden border-4 transition-all ${
                        formData.selectedConcept?.index === concept.index
                          ? 'border-accent ring-4 ring-accent/30'
                          : 'border-transparent hover:border-accent/50'
                      }`}
                    >
                      <img src={concept.image_url} alt="" className="w-full h-full object-cover" />
                      {formData.selectedConcept?.index === concept.index && (
                        <div className="absolute top-2 right-2 w-8 h-8 bg-accent rounded-full flex items-center justify-center">
                          <Check className="w-5 h-5 text-white" />
                        </div>
                      )}
                    </button>
                  ))}
                </div>

                <button
                  onClick={handleConfirmAvatar}
                  disabled={!formData.selectedConcept || generatingTraining}
                  className="btn-primary w-full py-3"
                >
                  {generatingTraining ? (
                    <><Loader2 className="w-5 h-5 animate-spin mr-2" /> Creating Avatar...</>
                  ) : (
                    <>Use This Avatar <ChevronRight className="w-5 h-5 ml-2" /></>
                  )}
                </button>
              </Card>
            )}

            {/* Navigation */}
            {!formData.avatarMode && (
              <button onClick={prevStep} className="btn-secondary w-full py-3">
                <ChevronLeft className="w-5 h-5 mr-2" /> Back
              </button>
            )}
            
            {formData.avatarMode && formData.avatarConcepts.length === 0 && !generatingConcepts && (
              <button 
                onClick={() => updateFormData({ avatarMode: null })} 
                className="btn-secondary w-full py-3"
              >
                <ChevronLeft className="w-5 h-5 mr-2" /> Back
              </button>
            )}
          </div>
        )}

        {/* Step 3: Social Accounts */}
        {currentStep === 3 && (
          <div className="space-y-6 animate-fade-in">
            <div className="text-center mb-8">
              <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-accent/10 flex items-center justify-center">
                <Share2 className="w-8 h-8 text-accent" />
              </div>
              <h1 className="text-2xl font-display font-bold text-pearl mb-2">
                Connect Your Social Accounts
              </h1>
              <p className="text-silver">
                Publish directly to your favorite platforms
              </p>
            </div>

            {/* Avatar Training Status */}
            {formData.avatarTrainingStarted && (
              <Card className="p-4 bg-accent/10 border-accent/30">
                <div className="flex items-center gap-3">
                  <Loader2 className="w-5 h-5 text-accent animate-spin" />
                  <div>
                    <p className="text-pearl font-medium">Your avatar is training...</p>
                    <p className="text-silver text-sm">This will be ready in ~20 minutes</p>
                  </div>
                </div>
              </Card>
            )}

            <Card className="p-6">
              <div className="space-y-3">
                {SOCIAL_PLATFORMS.map(platform => {
                  const Icon = platform.icon;
                  const connected = formData.connectedPlatforms.includes(platform.id);
                  return (
                    <button
                      key={platform.id}
                      onClick={() => handleConnectSocial(platform.id)}
                      className={`w-full p-4 rounded-xl border-2 flex items-center justify-between transition-all ${
                        connected
                          ? 'border-success bg-success/10'
                          : 'border-graphite hover:border-accent'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <Icon className={`w-6 h-6 ${connected ? 'text-success' : 'text-silver'}`} />
                        <span className={connected ? 'text-success' : 'text-pearl'}>
                          {platform.name}
                        </span>
                      </div>
                      {connected ? (
                        <CheckCircle2 className="w-5 h-5 text-success" />
                      ) : (
                        <span className="text-sm text-silver">Connect</span>
                      )}
                    </button>
                  );
                })}
              </div>
            </Card>

            <div className="flex gap-3">
              <button onClick={prevStep} className="btn-secondary flex-1 py-3">
                <ChevronLeft className="w-5 h-5 mr-2" /> Back
              </button>
              <button onClick={nextStep} className="btn-primary flex-1 py-3">
                {formData.connectedPlatforms.length > 0 ? 'Continue' : 'Skip for now'}
                <ChevronRight className="w-5 h-5 ml-2" />
              </button>
            </div>
          </div>
        )}

        {/* Step 4: First Content */}
        {currentStep === 4 && (
          <div className="space-y-6 animate-fade-in">
            <div className="text-center mb-8">
              <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-accent/10 flex items-center justify-center">
                <Wand2 className="w-8 h-8 text-accent" />
              </div>
              <h1 className="text-2xl font-display font-bold text-pearl mb-2">
                Create Your First Content
              </h1>
              <p className="text-silver">
                See your brand voice in action
              </p>
            </div>

            {!formData.generatedContent ? (
              <Card className="p-6 space-y-5">
                <div>
                  <label className="block text-sm font-medium text-pearl mb-2">
                    What would you like to post about?
                  </label>
                  <textarea
                    value={formData.firstContentBrief}
                    onChange={(e) => updateFormData({ firstContentBrief: e.target.value })}
                    placeholder={`e.g., Introduce ${formData.brandName} to our audience and share what makes us unique...`}
                    rows={4}
                    className="input-field w-full resize-none"
                  />
                </div>

                <button
                  onClick={handleGenerateFirstContent}
                  disabled={generatingContent}
                  className="btn-primary w-full py-3"
                >
                  {generatingContent ? (
                    <><Loader2 className="w-5 h-5 animate-spin mr-2" /> Creating...</>
                  ) : (
                    <><Sparkles className="w-5 h-5 mr-2" /> Generate Content</>
                  )}
                </button>
              </Card>
            ) : (
              <Card className="p-6 space-y-5">
                <div className="flex items-center gap-2 text-success mb-4">
                  <CheckCircle2 className="w-5 h-5" />
                  <span className="font-medium">Content Generated!</span>
                </div>
                
                <div className="p-4 bg-slate rounded-xl">
                  <p className="text-pearl">
                    Your content project has been created. View it in your dashboard to see captions, hashtags, and images.
                  </p>
                </div>

                <button onClick={nextStep} className="btn-primary w-full py-3">
                  Complete Setup <ChevronRight className="w-5 h-5 ml-2" />
                </button>
              </Card>
            )}

            <button onClick={prevStep} className="btn-secondary w-full py-3">
              <ChevronLeft className="w-5 h-5 mr-2" /> Back
            </button>
          </div>
        )}

        {/* Step 5: Complete */}
        {currentStep === 5 && (
          <div className="space-y-8 animate-fade-in text-center">
            <div className="w-24 h-24 mx-auto rounded-full bg-gradient-to-br from-success to-success/50 flex items-center justify-center">
              <CheckCircle2 className="w-12 h-12 text-white" />
            </div>

            <div>
              <h1 className="text-3xl font-display font-bold text-pearl mb-3">
                You're All Set! 🎉
              </h1>
              <p className="text-silver text-lg">
                {formData.brandName} is ready to create amazing content
              </p>
            </div>

            <Card className="p-6 text-left">
              <h3 className="font-bold text-pearl mb-4">What's next:</h3>
              <div className="space-y-3">
                <div className="flex items-start gap-3">
                  <CheckCircle2 className="w-5 h-5 text-success mt-0.5" />
                  <div>
                    <p className="text-pearl">Brand "{formData.brandName}" created</p>
                  </div>
                </div>
                
                {formData.avatarTrainingStarted && (
                  <div className="flex items-start gap-3">
                    <Loader2 className="w-5 h-5 text-accent animate-spin mt-0.5" />
                    <div>
                      <p className="text-pearl">Avatar training in progress</p>
                      <p className="text-silver text-sm">Ready in ~20 minutes</p>
                    </div>
                  </div>
                )}
                
                {formData.connectedPlatforms.length > 0 && (
                  <div className="flex items-start gap-3">
                    <CheckCircle2 className="w-5 h-5 text-success mt-0.5" />
                    <p className="text-pearl">
                      Connected: {formData.connectedPlatforms.join(', ')}
                    </p>
                  </div>
                )}
                
                {formData.generatedContent && (
                  <div className="flex items-start gap-3">
                    <CheckCircle2 className="w-5 h-5 text-success mt-0.5" />
                    <p className="text-pearl">First content project created</p>
                  </div>
                )}
              </div>
            </Card>

            <button
              onClick={handleComplete}
              disabled={saving}
              className="btn-primary w-full py-4 text-lg"
            >
              {saving ? <Loader2 className="w-5 h-5 animate-spin mr-2" /> : null}
              Go to Dashboard
              <ArrowRight className="w-5 h-5 ml-2" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
