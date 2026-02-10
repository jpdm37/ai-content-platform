import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Sparkles, Upload, X, Check, AlertTriangle, Image as ImageIcon, 
  ChevronRight, Info, Plus, Wand2, User, Camera, Loader2
} from 'lucide-react';
import { loraApi, brandsApi } from '../../services/api';
import { Card, Badge, Spinner, LoadingState } from '../../components/ui';
import toast from 'react-hot-toast';

export default function LoraCreate() {
  const navigate = useNavigate();
  const fileInputRef = useRef(null);
  const [step, setStep] = useState(1);
  const [brands, setBrands] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [avatarMode, setAvatarMode] = useState(null); // 'upload' | 'generate'

  // Form state
  const [formData, setFormData] = useState({
    brand_id: '',
    name: '',
    trigger_word: 'AVATAR',
    training_steps: 1000,
    lora_rank: 16,
    resolution: 1024
  });

  // Avatar generation state (for brands without photos)
  const [generationPrompt, setGenerationPrompt] = useState({
    gender: '',
    age_range: '',
    ethnicity: '',
    style: '',
    description: ''
  });
  const [generatingAvatar, setGeneratingAvatar] = useState(false);
  const [generatedAvatars, setGeneratedAvatars] = useState([]);

  // Images state
  const [imageUrls, setImageUrls] = useState([]);
  const [imageInput, setImageInput] = useState('');
  const [uploadedImages, setUploadedImages] = useState([]);
  const [validating, setValidating] = useState(false);
  const [uploading, setUploading] = useState(false);

  // Created model
  const [modelId, setModelId] = useState(null);
  const [validation, setValidation] = useState(null);

  useEffect(() => {
    brandsApi.list().then(res => { 
      setBrands(res.data); 
      setLoading(false); 
    }).catch(() => setLoading(false));
  }, []);

  // Handle URL input
  const handleAddImageUrl = () => {
    if (!imageInput.trim()) return;
    if (imageUrls.includes(imageInput)) { 
      toast.error('Image already added'); 
      return; 
    }
    // Basic URL validation
    try {
      new URL(imageInput);
      setImageUrls([...imageUrls, imageInput]);
      setImageInput('');
    } catch {
      toast.error('Please enter a valid URL');
    }
  };

  // Handle file upload
  const handleFileUpload = async (e) => {
    const files = Array.from(e.target.files);
    if (files.length === 0) return;

    setUploading(true);
    const newUrls = [];

    for (const file of files) {
      // Validate file type
      if (!file.type.startsWith('image/')) {
        toast.error(`${file.name} is not an image`);
        continue;
      }
      
      // Validate file size (max 10MB)
      if (file.size > 10 * 1024 * 1024) {
        toast.error(`${file.name} is too large (max 10MB)`);
        continue;
      }

      try {
        // Convert to base64 data URL for preview
        const dataUrl = await fileToDataUrl(file);
        newUrls.push(dataUrl);
        
        // In production, you'd upload to a server/S3 here
        // For now, we'll use the data URL directly
      } catch (err) {
        toast.error(`Failed to process ${file.name}`);
      }
    }

    setImageUrls([...imageUrls, ...newUrls]);
    setUploading(false);
    
    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const fileToDataUrl = (file) => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  };

  const handleRemoveImage = (url) => {
    setImageUrls(imageUrls.filter(u => u !== url));
  };

  // Generate AI avatar
  const handleGenerateAvatar = async () => {
    if (!generationPrompt.gender || !generationPrompt.style) {
      toast.error('Please select gender and style');
      return;
    }

    setGeneratingAvatar(true);
    try {
      // Build prompt for avatar generation
      const prompt = buildAvatarPrompt(generationPrompt);
      
      // Call generation API (we'll generate 4 variations)
      const res = await fetch('/api/v1/generate/avatar-concept', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt,
          num_images: 4,
          style: generationPrompt.style
        })
      });
      
      if (res.ok) {
        const data = await res.json();
        setGeneratedAvatars(data.images || []);
        toast.success('Avatar concepts generated!');
      } else {
        // Fallback: show placeholder message
        toast.error('Avatar generation coming soon. Please upload photos for now.');
      }
    } catch (err) {
      toast.error('Failed to generate avatar. Please try uploading photos instead.');
    }
    setGeneratingAvatar(false);
  };

  const buildAvatarPrompt = (params) => {
    const parts = ['portrait of a person'];
    if (params.gender) parts.push(params.gender);
    if (params.age_range) parts.push(`${params.age_range} years old`);
    if (params.ethnicity) parts.push(params.ethnicity);
    if (params.description) parts.push(params.description);
    parts.push('professional photo, high quality, detailed face');
    return parts.join(', ');
  };

  const selectGeneratedAvatar = (avatarUrl) => {
    // Add all generated variations as training images
    setImageUrls([...imageUrls, ...generatedAvatars]);
    toast.success('Avatar images added! Generate more for better training.');
  };

  const handleCreateModel = async () => {
    if (!formData.brand_id || !formData.name) { 
      toast.error('Please fill required fields'); 
      return; 
    }
    setCreating(true);
    try {
      const res = await loraApi.createModel({
        brand_id: parseInt(formData.brand_id),
        name: formData.name,
        trigger_word: formData.trigger_word.toUpperCase().replace(/\s+/g, '_'),
        config: { 
          training_steps: formData.training_steps, 
          lora_rank: formData.lora_rank, 
          resolution: formData.resolution 
        }
      });
      setModelId(res.data.id);
      toast.success('Model created!');
      setStep(2);
    } catch (err) { 
      toast.error(err.response?.data?.detail || 'Failed to create model'); 
    }
    setCreating(false);
  };

  const handleUploadImages = async () => {
    // Lower minimum to 3 images for easier onboarding
    if (imageUrls.length < 3) { 
      toast.error('Add at least 3 images (5+ recommended for best results)'); 
      return; 
    }
    setValidating(true);
    try {
      const res = await loraApi.bulkAddImages(modelId, imageUrls);
      setUploadedImages(res.data.images);
      toast.success(`${res.data.valid} images validated`);
      setStep(3);
    } catch (err) { 
      toast.error('Failed to upload images'); 
    }
    setValidating(false);
  };

  const handleValidate = async () => {
    setValidating(true);
    try {
      const res = await loraApi.validateModel(modelId);
      setValidation(res.data);
      if (res.data.is_ready) {
        toast.success('Ready for training!');
        setStep(4);
      } else {
        toast.error(res.data.issues?.join(', ') || 'Validation failed');
      }
    } catch (err) { 
      toast.error('Validation failed'); 
    }
    setValidating(false);
  };

  const handleStartTraining = async () => {
    setCreating(true);
    try {
      await loraApi.startTraining(modelId);
      toast.success('Training started! This may take 15-30 minutes.');
      navigate(`/lora/${modelId}`);
    } catch (err) { 
      toast.error(err.response?.data?.detail || 'Failed to start training'); 
    }
    setCreating(false);
  };

  if (loading) return <LoadingState message="Loading..." />;

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="page-title">Create AI Avatar</h1>
        <p className="text-silver mt-1">
          Train a custom AI model to generate consistent images of your brand's avatar
        </p>
      </div>

      {/* Progress Steps */}
      <div className="flex items-center gap-2">
        {[1, 2, 3, 4].map((s) => (
          <div key={s} className="flex items-center">
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold
                          ${step >= s ? 'bg-accent text-white' : 'bg-slate text-silver'}`}>
              {step > s ? <Check className="w-4 h-4" /> : s}
            </div>
            {s < 4 && (
              <div className={`w-12 h-1 mx-2 rounded ${step > s ? 'bg-accent' : 'bg-slate'}`} />
            )}
          </div>
        ))}
      </div>

      {/* Step 1: Configure */}
      {step === 1 && (
        <Card className="p-6 space-y-6">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-accent" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-pearl">Configure Your Avatar</h2>
              <p className="text-silver text-sm">Set up the basic details</p>
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-pearl mb-1">Brand *</label>
              <select
                value={formData.brand_id}
                onChange={(e) => setFormData({ ...formData, brand_id: e.target.value })}
                className="input-field w-full"
              >
                <option value="">Select a brand</option>
                {brands.map(brand => (
                  <option key={brand.id} value={brand.id}>{brand.name}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-pearl mb-1">Avatar Name *</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="e.g., Brand Ambassador v1"
                className="input-field w-full"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-pearl mb-1">
                Trigger Word
                <span className="text-silver font-normal ml-2">(used in prompts)</span>
              </label>
              <input
                type="text"
                value={formData.trigger_word}
                onChange={(e) => setFormData({ ...formData, trigger_word: e.target.value })}
                placeholder="AVATAR"
                className="input-field w-full"
              />
              <p className="text-xs text-silver mt-1">
                This word activates your avatar in image generation prompts
              </p>
            </div>

            <details className="group">
              <summary className="text-sm text-accent cursor-pointer hover:underline">
                Advanced Settings
              </summary>
              <div className="mt-4 space-y-4 pl-4 border-l border-graphite">
                <div>
                  <label className="block text-sm text-silver mb-1">Training Steps</label>
                  <select
                    value={formData.training_steps}
                    onChange={(e) => setFormData({ ...formData, training_steps: parseInt(e.target.value) })}
                    className="input-field w-full"
                  >
                    <option value={500}>500 (Faster, ~$1)</option>
                    <option value={1000}>1000 (Recommended, ~$2)</option>
                    <option value={2000}>2000 (Higher quality, ~$3)</option>
                  </select>
                </div>
              </div>
            </details>
          </div>

          <button
            onClick={handleCreateModel}
            disabled={creating || !formData.brand_id || !formData.name}
            className="btn-primary w-full flex items-center justify-center gap-2"
          >
            {creating ? <Spinner size="sm" /> : <ChevronRight className="w-5 h-5" />}
            Continue to Images
          </button>
        </Card>
      )}

      {/* Step 2: Upload Images */}
      {step === 2 && (
        <Card className="p-6 space-y-6">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center">
              <Camera className="w-5 h-5 text-accent" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-pearl">Add Training Images</h2>
              <p className="text-silver text-sm">
                Minimum 3 images • Recommended 5-15 for best results
              </p>
            </div>
          </div>

          {/* Mode Selection (if no images yet) */}
          {imageUrls.length === 0 && !avatarMode && (
            <div className="grid grid-cols-2 gap-4">
              <button
                onClick={() => setAvatarMode('upload')}
                className="p-6 rounded-xl border-2 border-dashed border-graphite hover:border-accent 
                         transition-colors text-center group"
              >
                <Upload className="w-10 h-10 mx-auto mb-3 text-silver group-hover:text-accent" />
                <p className="font-medium text-pearl">Upload Photos</p>
                <p className="text-sm text-silver mt-1">
                  I have photos of my avatar/influencer
                </p>
              </button>
              
              <button
                onClick={() => setAvatarMode('generate')}
                className="p-6 rounded-xl border-2 border-dashed border-graphite hover:border-accent 
                         transition-colors text-center group"
              >
                <Wand2 className="w-10 h-10 mx-auto mb-3 text-silver group-hover:text-accent" />
                <p className="font-medium text-pearl">Generate Avatar</p>
                <p className="text-sm text-silver mt-1">
                  Create a new AI avatar from scratch
                </p>
                <Badge variant="warning" className="mt-2">Coming Soon</Badge>
              </button>
            </div>
          )}

          {/* Upload Mode */}
          {(avatarMode === 'upload' || imageUrls.length > 0) && (
            <div className="space-y-4">
              {/* File Upload */}
              <div className="border-2 border-dashed border-graphite rounded-xl p-6 text-center hover:border-accent transition-colors">
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept="image/*"
                  onChange={handleFileUpload}
                  className="hidden"
                  id="file-upload"
                />
                <label 
                  htmlFor="file-upload" 
                  className="cursor-pointer block"
                >
                  {uploading ? (
                    <Loader2 className="w-10 h-10 mx-auto mb-3 text-accent animate-spin" />
                  ) : (
                    <Upload className="w-10 h-10 mx-auto mb-3 text-silver" />
                  )}
                  <p className="text-pearl font-medium">
                    {uploading ? 'Processing...' : 'Click to upload images'}
                  </p>
                  <p className="text-sm text-silver mt-1">
                    or drag and drop • PNG, JPG up to 10MB each
                  </p>
                </label>
              </div>

              {/* URL Input */}
              <div className="flex gap-2">
                <input
                  type="url"
                  value={imageInput}
                  onChange={(e) => setImageInput(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleAddImageUrl()}
                  placeholder="Or paste image URL..."
                  className="input-field flex-1"
                />
                <button
                  onClick={handleAddImageUrl}
                  disabled={!imageInput.trim()}
                  className="btn-secondary px-4"
                >
                  <Plus className="w-5 h-5" />
                </button>
              </div>

              {/* Image Grid */}
              {imageUrls.length > 0 && (
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-silver">
                      {imageUrls.length} image{imageUrls.length !== 1 ? 's' : ''} added
                    </span>
                    <span className={`text-sm ${imageUrls.length >= 3 ? 'text-success' : 'text-warning'}`}>
                      {imageUrls.length >= 3 ? '✓ Minimum met' : `Need ${3 - imageUrls.length} more`}
                    </span>
                  </div>
                  <div className="grid grid-cols-4 sm:grid-cols-5 gap-2">
                    {imageUrls.map((url, i) => (
                      <div key={i} className="relative aspect-square group">
                        <img
                          src={url}
                          alt={`Reference ${i + 1}`}
                          className="w-full h-full object-cover rounded-lg"
                          onError={(e) => {
                            e.target.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect fill="%231e1e26" width="100" height="100"/><text fill="%23666" x="50%" y="50%" text-anchor="middle" dy=".3em" font-size="12">Error</text></svg>';
                          }}
                        />
                        <button
                          onClick={() => handleRemoveImage(url)}
                          className="absolute -top-2 -right-2 w-6 h-6 bg-error rounded-full 
                                   flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                        >
                          <X className="w-4 h-4 text-white" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Tips */}
              <div className="p-4 bg-slate/50 rounded-xl">
                <h4 className="text-sm font-medium text-pearl mb-2 flex items-center gap-2">
                  <Info className="w-4 h-4 text-accent" />
                  Tips for best results
                </h4>
                <ul className="text-sm text-silver space-y-1">
                  <li>• Use clear, well-lit photos with visible face</li>
                  <li>• Include variety: different angles, expressions, outfits</li>
                  <li>• Avoid group photos or heavy filters</li>
                  <li>• 5-15 high-quality images work best</li>
                </ul>
              </div>
            </div>
          )}

          {/* Generate Mode (Coming Soon) */}
          {avatarMode === 'generate' && (
            <div className="space-y-4">
              <div className="p-6 bg-slate/50 rounded-xl text-center">
                <Wand2 className="w-12 h-12 mx-auto mb-3 text-silver" />
                <h3 className="text-pearl font-medium mb-2">AI Avatar Generation</h3>
                <p className="text-silver text-sm mb-4">
                  This feature is coming soon! For now, please upload existing photos 
                  or use stock images of your desired avatar look.
                </p>
                <button
                  onClick={() => setAvatarMode('upload')}
                  className="btn-secondary"
                >
                  Switch to Upload
                </button>
              </div>
            </div>
          )}

          <div className="flex gap-3">
            <button
              onClick={() => { setStep(1); setAvatarMode(null); }}
              className="btn-secondary flex-1"
            >
              Back
            </button>
            <button
              onClick={handleUploadImages}
              disabled={validating || imageUrls.length < 3}
              className="btn-primary flex-1 flex items-center justify-center gap-2"
            >
              {validating ? <Spinner size="sm" /> : <ChevronRight className="w-5 h-5" />}
              Validate Images
            </button>
          </div>
        </Card>
      )}

      {/* Step 3: Review */}
      {step === 3 && (
        <Card className="p-6 space-y-6">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center">
              <Check className="w-5 h-5 text-accent" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-pearl">Review & Validate</h2>
              <p className="text-silver text-sm">Check your images before training</p>
            </div>
          </div>

          {/* Image Validation Results */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {uploadedImages.map((img, i) => (
              <div key={i} className="relative">
                <img
                  src={img.original_url}
                  alt={`Image ${i + 1}`}
                  className="w-full aspect-square object-cover rounded-lg"
                />
                <div className={`absolute bottom-2 right-2 px-2 py-1 rounded text-xs font-medium
                              ${img.validation_status === 'valid' ? 'bg-success/80 text-white' : 'bg-warning/80 text-white'}`}>
                  {img.face_detected ? '✓ Face' : '⚠ No face'}
                </div>
              </div>
            ))}
          </div>

          <button
            onClick={handleValidate}
            disabled={validating}
            className="btn-primary w-full flex items-center justify-center gap-2"
          >
            {validating ? <Spinner size="sm" /> : <Check className="w-5 h-5" />}
            Validate for Training
          </button>
        </Card>
      )}

      {/* Step 4: Start Training */}
      {step === 4 && validation && (
        <Card className="p-6 space-y-6">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-xl bg-success/10 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-success" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-pearl">Ready to Train!</h2>
              <p className="text-silver text-sm">Your avatar is ready for training</p>
            </div>
          </div>

          {/* Summary */}
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 bg-slate rounded-xl">
              <p className="text-silver text-sm">Valid Images</p>
              <p className="text-2xl font-bold text-pearl">{validation.valid_image_count}</p>
            </div>
            <div className="p-4 bg-slate rounded-xl">
              <p className="text-silver text-sm">Estimated Cost</p>
              <p className="text-2xl font-bold text-pearl">${validation.estimated_cost_usd}</p>
            </div>
            <div className="p-4 bg-slate rounded-xl">
              <p className="text-silver text-sm">Training Time</p>
              <p className="text-2xl font-bold text-pearl">~{validation.estimated_time_minutes} min</p>
            </div>
            <div className="p-4 bg-slate rounded-xl">
              <p className="text-silver text-sm">Quality Score</p>
              <p className="text-2xl font-bold text-pearl">{Math.round(validation.average_quality)}/100</p>
            </div>
          </div>

          {/* Warnings */}
          {validation.warnings?.length > 0 && (
            <div className="p-4 bg-warning/10 border border-warning/30 rounded-xl">
              <h4 className="font-medium text-warning mb-2 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4" />
                Recommendations
              </h4>
              <ul className="text-sm text-silver space-y-1">
                {validation.warnings.map((w, i) => (
                  <li key={i}>• {w}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="flex gap-3">
            <button
              onClick={() => setStep(2)}
              className="btn-secondary flex-1"
            >
              Add More Images
            </button>
            <button
              onClick={handleStartTraining}
              disabled={creating}
              className="btn-primary flex-1 flex items-center justify-center gap-2"
            >
              {creating ? <Spinner size="sm" /> : <Sparkles className="w-5 h-5" />}
              Start Training
            </button>
          </div>
        </Card>
      )}
    </div>
  );
}
