import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { 
  FlaskConical, Plus, Play, Pause, Square, Trophy,
  TrendingUp, Users, MousePointer, Target, AlertCircle,
  ChevronRight, BarChart2, Percent, Clock, CheckCircle
} from 'lucide-react';
import api from '../../services/api';
import { Card, LoadingState, Badge, Modal, Spinner } from '../../components/ui';
import toast from 'react-hot-toast';

// Status colors
const statusColors = {
  draft: 'bg-gray-500',
  running: 'bg-green-500',
  paused: 'bg-yellow-500',
  completed: 'bg-blue-500',
  cancelled: 'bg-red-500'
};

// Status icons
const statusIcons = {
  draft: Clock,
  running: Play,
  paused: Pause,
  completed: CheckCircle,
  cancelled: Square
};

export default function ABTestingDashboard() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [tests, setTests] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [showCreateModal, setShowCreateModal] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [testsRes, templatesRes] = await Promise.all([
        api.get('/ab-tests/'),
        api.get('/ab-tests/templates')
      ]);
      setTests(testsRes.data.tests);
      setTemplates(templatesRes.data.templates);
    } catch (err) {
      toast.error('Failed to load A/B tests');
    }
    setLoading(false);
  };

  const handleStartTest = async (testId) => {
    try {
      await api.post(`/ab-tests/${testId}/start`);
      toast.success('Test started');
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to start test');
    }
  };

  const handlePauseTest = async (testId) => {
    try {
      await api.post(`/ab-tests/${testId}/pause`);
      toast.success('Test paused');
      fetchData();
    } catch (err) {
      toast.error('Failed to pause test');
    }
  };

  const handleEndTest = async (testId) => {
    if (!confirm('Are you sure you want to end this test?')) return;
    try {
      await api.post(`/ab-tests/${testId}/end`);
      toast.success('Test completed');
      fetchData();
    } catch (err) {
      toast.error('Failed to end test');
    }
  };

  const runningTests = tests.filter(t => t.status === 'running');
  const completedTests = tests.filter(t => t.status === 'completed');

  if (loading) return <LoadingState message="Loading A/B tests..." />;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-pearl flex items-center gap-2">
            <FlaskConical className="w-7 h-7 text-accent" />
            A/B Testing
          </h1>
          <p className="text-silver">Test different content variations to optimize performance</p>
        </div>
        
        <button
          onClick={() => setShowCreateModal(true)}
          className="btn-primary px-4 py-2 flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          New Test
        </button>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-green-500/20 flex items-center justify-center">
              <Play className="w-5 h-5 text-green-500" />
            </div>
            <div>
              <p className="text-2xl font-bold text-pearl">{runningTests.length}</p>
              <p className="text-xs text-silver">Running</p>
            </div>
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
              <CheckCircle className="w-5 h-5 text-blue-500" />
            </div>
            <div>
              <p className="text-2xl font-bold text-pearl">{completedTests.length}</p>
              <p className="text-xs text-silver">Completed</p>
            </div>
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-yellow-500/20 flex items-center justify-center">
              <Trophy className="w-5 h-5 text-yellow-500" />
            </div>
            <div>
              <p className="text-2xl font-bold text-pearl">
                {completedTests.filter(t => t.is_significant).length}
              </p>
              <p className="text-xs text-silver">Significant Results</p>
            </div>
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-accent/20 flex items-center justify-center">
              <BarChart2 className="w-5 h-5 text-accent" />
            </div>
            <div>
              <p className="text-2xl font-bold text-pearl">{tests.length}</p>
              <p className="text-xs text-silver">Total Tests</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Running Tests */}
      {runningTests.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold text-pearl mb-4 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
            Running Tests
          </h2>
          <div className="grid md:grid-cols-2 gap-4">
            {runningTests.map(test => (
              <TestCard
                key={test.id}
                test={test}
                onStart={handleStartTest}
                onPause={handlePauseTest}
                onEnd={handleEndTest}
                onClick={() => navigate(`/ab-testing/${test.id}`)}
              />
            ))}
          </div>
        </div>
      )}

      {/* All Tests */}
      <div>
        <h2 className="text-lg font-semibold text-pearl mb-4">All Tests</h2>
        {tests.length === 0 ? (
          <Card className="p-8 text-center">
            <FlaskConical className="w-12 h-12 text-silver mx-auto mb-4" />
            <p className="text-pearl font-medium mb-2">No A/B tests yet</p>
            <p className="text-silver text-sm mb-4">
              Create your first test to start optimizing your content
            </p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="btn-primary px-4 py-2"
            >
              Create Test
            </button>
          </Card>
        ) : (
          <div className="space-y-3">
            {tests.map(test => (
              <TestCard
                key={test.id}
                test={test}
                onStart={handleStartTest}
                onPause={handlePauseTest}
                onEnd={handleEndTest}
                onClick={() => navigate(`/ab-testing/${test.id}`)}
                compact
              />
            ))}
          </div>
        )}
      </div>

      {/* Create Test Modal */}
      <CreateTestModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        templates={templates}
        onCreated={() => {
          setShowCreateModal(false);
          fetchData();
        }}
      />
    </div>
  );
}

// Test Card Component
function TestCard({ test, onStart, onPause, onEnd, onClick, compact = false }) {
  const StatusIcon = statusIcons[test.status] || Clock;
  
  if (compact) {
    return (
      <Card 
        className="p-4 cursor-pointer hover:border-accent/50 transition-all"
        onClick={onClick}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`w-2 h-2 rounded-full ${statusColors[test.status]}`}></div>
            <div>
              <p className="text-pearl font-medium">{test.name}</p>
              <p className="text-xs text-silver">
                {test.test_type} • {test.variations_count} variations
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant={test.status === 'running' ? 'success' : 'default'}>
              {test.status}
            </Badge>
            {test.is_significant && (
              <Badge variant="success" className="bg-yellow-500/20 text-yellow-400">
                Significant
              </Badge>
            )}
            <ChevronRight className="w-4 h-4 text-silver" />
          </div>
        </div>
      </Card>
    );
  }
  
  return (
    <Card className="p-5">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-pearl font-semibold">{test.name}</h3>
          <p className="text-sm text-silver">{test.test_type} test</p>
        </div>
        <Badge variant={test.status === 'running' ? 'success' : 'default'}>
          <StatusIcon className="w-3 h-3 mr-1" />
          {test.status}
        </Badge>
      </div>
      
      <div className="flex items-center gap-4 text-sm text-silver mb-4">
        <span>{test.variations_count} variations</span>
        <span>•</span>
        <span>Created {new Date(test.created_at).toLocaleDateString()}</span>
      </div>
      
      {test.is_significant && (
        <div className="p-3 bg-green-500/10 border border-green-500/30 rounded-lg mb-4">
          <p className="text-green-400 text-sm flex items-center gap-2">
            <Trophy className="w-4 h-4" />
            Statistically significant result!
          </p>
        </div>
      )}
      
      <div className="flex gap-2">
        {test.status === 'draft' && (
          <button
            onClick={(e) => { e.stopPropagation(); onStart(test.id); }}
            className="flex-1 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors flex items-center justify-center gap-2"
          >
            <Play className="w-4 h-4" />
            Start Test
          </button>
        )}
        {test.status === 'running' && (
          <>
            <button
              onClick={(e) => { e.stopPropagation(); onPause(test.id); }}
              className="flex-1 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 transition-colors flex items-center justify-center gap-2"
            >
              <Pause className="w-4 h-4" />
              Pause
            </button>
            <button
              onClick={(e) => { e.stopPropagation(); onEnd(test.id); }}
              className="flex-1 py-2 border border-graphite text-silver rounded-lg hover:text-pearl hover:border-silver transition-colors flex items-center justify-center gap-2"
            >
              <Square className="w-4 h-4" />
              End Test
            </button>
          </>
        )}
        {test.status === 'paused' && (
          <button
            onClick={(e) => { e.stopPropagation(); onStart(test.id); }}
            className="flex-1 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors flex items-center justify-center gap-2"
          >
            <Play className="w-4 h-4" />
            Resume
          </button>
        )}
        <button
          onClick={onClick}
          className="py-2 px-4 border border-graphite text-silver rounded-lg hover:text-pearl hover:border-silver transition-colors"
        >
          View Details
        </button>
      </div>
    </Card>
  );
}

// Create Test Modal
function CreateTestModal({ isOpen, onClose, templates, onCreated }) {
  const [step, setStep] = useState(1);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [testName, setTestName] = useState('');
  const [variations, setVariations] = useState([
    { name: 'Control', content: '' },
    { name: 'Variation A', content: '' }
  ]);
  const [submitting, setSubmitting] = useState(false);

  const handleCreateFromTemplate = async () => {
    if (!testName || !selectedTemplate) return;
    
    setSubmitting(true);
    try {
      await api.post('/ab-tests/from-template', {
        template_id: selectedTemplate.id,
        name: testName
      });
      toast.success('Test created!');
      onCreated();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to create test');
    }
    setSubmitting(false);
  };

  const handleCreateCustom = async () => {
    if (!testName || variations.length < 2) return;
    
    setSubmitting(true);
    try {
      await api.post('/ab-tests/', {
        name: testName,
        test_type: 'caption',
        variations: variations.map(v => ({
          name: v.name,
          content: v.content
        }))
      });
      toast.success('Test created!');
      onCreated();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to create test');
    }
    setSubmitting(false);
  };

  const addVariation = () => {
    const letter = String.fromCharCode(65 + variations.length - 1);
    setVariations([...variations, { name: `Variation ${letter}`, content: '' }]);
  };

  const updateVariation = (index, field, value) => {
    const updated = [...variations];
    updated[index][field] = value;
    setVariations(updated);
  };

  if (!isOpen) return null;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Create A/B Test" size="lg">
      <div className="space-y-6">
        {step === 1 && (
          <>
            <p className="text-silver">Choose how you want to create your test:</p>
            
            <div className="grid md:grid-cols-2 gap-4">
              <button
                onClick={() => setStep(2)}
                className="p-6 rounded-xl border-2 border-graphite hover:border-accent transition-all text-left"
              >
                <FlaskConical className="w-8 h-8 text-accent mb-3" />
                <h3 className="text-pearl font-semibold mb-1">From Template</h3>
                <p className="text-sm text-silver">Use a pre-built test template</p>
              </button>
              
              <button
                onClick={() => setStep(3)}
                className="p-6 rounded-xl border-2 border-graphite hover:border-accent transition-all text-left"
              >
                <Plus className="w-8 h-8 text-accent mb-3" />
                <h3 className="text-pearl font-semibold mb-1">Custom Test</h3>
                <p className="text-sm text-silver">Create your own variations</p>
              </button>
            </div>
          </>
        )}

        {step === 2 && (
          <>
            <button onClick={() => setStep(1)} className="text-accent text-sm">
              ← Back
            </button>
            
            <div>
              <label className="block text-sm font-medium text-pearl mb-2">Test Name</label>
              <input
                type="text"
                value={testName}
                onChange={(e) => setTestName(e.target.value)}
                placeholder="e.g., Emoji vs No Emoji Test"
                className="w-full px-4 py-2 rounded-lg bg-slate border border-graphite text-pearl focus:border-accent focus:outline-none"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-pearl mb-3">Select Template</label>
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {templates.map((template) => (
                  <button
                    key={template.id}
                    onClick={() => setSelectedTemplate(template)}
                    className={`w-full p-4 rounded-lg border-2 text-left transition-all ${
                      selectedTemplate?.id === template.id
                        ? 'border-accent bg-accent/10'
                        : 'border-graphite hover:border-silver'
                    }`}
                  >
                    <h4 className="text-pearl font-medium">{template.name}</h4>
                    <p className="text-sm text-silver">{template.description}</p>
                    <div className="flex gap-2 mt-2">
                      {template.variations.map((v, i) => (
                        <span key={i} className="text-xs px-2 py-0.5 bg-slate rounded">
                          {v.name}
                        </span>
                      ))}
                    </div>
                  </button>
                ))}
              </div>
            </div>
            
            <button
              onClick={handleCreateFromTemplate}
              disabled={!testName || !selectedTemplate || submitting}
              className="w-full btn-primary py-3 disabled:opacity-50"
            >
              {submitting ? <Spinner size="sm" /> : 'Create Test'}
            </button>
          </>
        )}

        {step === 3 && (
          <>
            <button onClick={() => setStep(1)} className="text-accent text-sm">
              ← Back
            </button>
            
            <div>
              <label className="block text-sm font-medium text-pearl mb-2">Test Name</label>
              <input
                type="text"
                value={testName}
                onChange={(e) => setTestName(e.target.value)}
                placeholder="e.g., Caption Length Test"
                className="w-full px-4 py-2 rounded-lg bg-slate border border-graphite text-pearl focus:border-accent focus:outline-none"
              />
            </div>
            
            <div>
              <div className="flex items-center justify-between mb-3">
                <label className="text-sm font-medium text-pearl">Variations</label>
                {variations.length < 5 && (
                  <button onClick={addVariation} className="text-accent text-sm">
                    + Add Variation
                  </button>
                )}
              </div>
              
              <div className="space-y-3">
                {variations.map((variation, index) => (
                  <div key={index} className="p-3 bg-slate rounded-lg">
                    <input
                      type="text"
                      value={variation.name}
                      onChange={(e) => updateVariation(index, 'name', e.target.value)}
                      className="w-full mb-2 px-3 py-1.5 rounded bg-charcoal border border-graphite text-pearl text-sm focus:border-accent focus:outline-none"
                    />
                    <textarea
                      value={variation.content}
                      onChange={(e) => updateVariation(index, 'content', e.target.value)}
                      placeholder="Enter the content for this variation..."
                      rows={2}
                      className="w-full px-3 py-2 rounded bg-charcoal border border-graphite text-pearl text-sm focus:border-accent focus:outline-none resize-none"
                    />
                  </div>
                ))}
              </div>
            </div>
            
            <button
              onClick={handleCreateCustom}
              disabled={!testName || variations.length < 2 || submitting}
              className="w-full btn-primary py-3 disabled:opacity-50"
            >
              {submitting ? <Spinner size="sm" /> : 'Create Test'}
            </button>
          </>
        )}
      </div>
    </Modal>
  );
}

// Test Detail Page (exported separately)
export function ABTestDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [test, setTest] = useState(null);

  useEffect(() => {
    fetchTest();
  }, [id]);

  const fetchTest = async () => {
    try {
      const res = await api.get(`/ab-tests/${id}`);
      setTest(res.data);
    } catch (err) {
      toast.error('Failed to load test');
      navigate('/ab-testing');
    }
    setLoading(false);
  };

  if (loading) return <LoadingState message="Loading test..." />;
  if (!test) return null;

  const winnerVariation = test.variations.find(v => v.is_winner);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <button onClick={() => navigate('/ab-testing')} className="text-silver hover:text-pearl">
          ← Back
        </button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-pearl">{test.name}</h1>
          <p className="text-silver">{test.description}</p>
        </div>
        <Badge variant={test.status === 'running' ? 'success' : 'default'} className="text-sm">
          {test.status}
        </Badge>
      </div>

      {/* Winner Banner */}
      {test.status === 'completed' && winnerVariation && (
        <Card className="p-6 border-2 border-yellow-500/50 bg-yellow-500/10">
          <div className="flex items-center gap-4">
            <Trophy className="w-10 h-10 text-yellow-500" />
            <div>
              <h3 className="text-pearl font-semibold text-lg">Winner: {winnerVariation.name}</h3>
              <p className="text-silver">
                {test.is_significant 
                  ? `Statistically significant (p-value: ${test.p_value})`
                  : 'Not statistically significant - more data may be needed'}
              </p>
            </div>
          </div>
        </Card>
      )}

      {/* Test Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="p-4 text-center">
          <p className="text-2xl font-bold text-pearl">{test.total_impressions}</p>
          <p className="text-sm text-silver">Total Impressions</p>
        </Card>
        <Card className="p-4 text-center">
          <p className="text-2xl font-bold text-pearl">{test.variations.length}</p>
          <p className="text-sm text-silver">Variations</p>
        </Card>
        <Card className="p-4 text-center">
          <p className="text-2xl font-bold text-pearl">{Math.round(test.confidence_level * 100)}%</p>
          <p className="text-sm text-silver">Confidence Level</p>
        </Card>
        <Card className="p-4 text-center">
          <p className={`text-2xl font-bold ${test.sample_size_reached ? 'text-green-500' : 'text-yellow-500'}`}>
            {test.sample_size_reached ? '✓' : '...'}
          </p>
          <p className="text-sm text-silver">Sample Size</p>
        </Card>
      </div>

      {/* Variations Comparison */}
      <Card className="p-6">
        <h2 className="text-lg font-semibold text-pearl mb-4">Variations Performance</h2>
        <div className="space-y-4">
          {test.variations.map((variation) => (
            <div 
              key={variation.id}
              className={`p-4 rounded-lg border-2 ${
                variation.is_winner 
                  ? 'border-yellow-500 bg-yellow-500/10' 
                  : 'border-graphite'
              }`}
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <h3 className="text-pearl font-medium">{variation.name}</h3>
                  {variation.is_control && <Badge>Control</Badge>}
                  {variation.is_winner && <Badge variant="success">Winner</Badge>}
                </div>
                <span className="text-silver text-sm">{variation.traffic_percent}% traffic</span>
              </div>
              
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <p className="text-2xl font-bold text-pearl">{variation.metrics.impressions}</p>
                  <p className="text-xs text-silver">Impressions</p>
                </div>
                <div>
                  <p className="text-2xl font-bold text-accent">{variation.metrics.engagement_rate}%</p>
                  <p className="text-xs text-silver">Engagement Rate</p>
                </div>
                <div>
                  <p className="text-2xl font-bold text-pearl">{variation.metrics.clicks}</p>
                  <p className="text-xs text-silver">Clicks</p>
                </div>
                <div>
                  <p className="text-2xl font-bold text-pearl">{variation.metrics.click_rate}%</p>
                  <p className="text-xs text-silver">Click Rate</p>
                </div>
              </div>
              
              {variation.content && (
                <div className="mt-3 p-3 bg-slate rounded-lg">
                  <p className="text-sm text-silver">{variation.content}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      </Card>

      {/* Visual Comparison */}
      {test.variations.length >= 2 && (
        <Card className="p-6">
          <h2 className="text-lg font-semibold text-pearl mb-4">Engagement Rate Comparison</h2>
          <div className="space-y-3">
            {test.variations.map((variation) => {
              const maxRate = Math.max(...test.variations.map(v => v.metrics.engagement_rate));
              const widthPercent = maxRate > 0 ? (variation.metrics.engagement_rate / maxRate) * 100 : 0;
              
              return (
                <div key={variation.id} className="flex items-center gap-4">
                  <span className="w-24 text-sm text-silver truncate">{variation.name}</span>
                  <div className="flex-1 h-8 bg-slate rounded-lg overflow-hidden">
                    <div 
                      className={`h-full ${variation.is_winner ? 'bg-yellow-500' : 'bg-accent'} transition-all duration-500`}
                      style={{ width: `${widthPercent}%` }}
                    />
                  </div>
                  <span className="w-16 text-right text-pearl font-medium">
                    {variation.metrics.engagement_rate}%
                  </span>
                </div>
              );
            })}
          </div>
        </Card>
      )}
    </div>
  );
}
