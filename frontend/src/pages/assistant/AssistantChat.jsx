import { useState, useEffect, useRef } from 'react';
import { MessageCircle, Send, Sparkles, Copy, Hash, Globe, Wand2, Zap, RotateCcw } from 'lucide-react';
import { assistantApi, brandsApi } from '../../services/api';
import { Card, LoadingState, Badge, Spinner } from '../../components/ui';
import toast from 'react-hot-toast';

const quickActions = [
  { id: 'improve', icon: Wand2, label: 'Improve', color: 'bg-blue-500' },
  { id: 'hashtags', icon: Hash, label: 'Hashtags', color: 'bg-green-500' },
  { id: 'variations', icon: RotateCcw, label: 'Variations', color: 'bg-purple-500' },
  { id: 'translate', icon: Globe, label: 'Translate', color: 'bg-orange-500' },
];

const suggestedPrompts = [
  "Help me write a caption for a product launch",
  "Make this more engaging: [paste your content]",
  "What hashtags should I use for fitness content?",
  "Rewrite this to be more professional",
  "Translate this to Spanish",
  "Give me 3 variations of this caption",
];

export default function AssistantChat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [brands, setBrands] = useState([]);
  const [selectedBrand, setSelectedBrand] = useState('');
  const [selectedContent, setSelectedContent] = useState('');
  const [showQuickAction, setShowQuickAction] = useState(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    fetchBrands();
    // Add welcome message
    setMessages([{
      role: 'assistant',
      content: "Hi! I'm your AI content assistant. I can help you:\n\n• Write and improve captions\n• Generate hashtags\n• Translate content\n• Create variations\n• Optimize for platforms\n\nHow can I help you today?"
    }]);
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const fetchBrands = async () => {
    try {
      const res = await brandsApi.list();
      setBrands(res.data);
    } catch (err) {}
  };

  const sendMessage = async () => {
    if (!input.trim() || sending) return;

    const userMessage = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setSending(true);

    try {
      const context = {};
      if (selectedBrand) context.brand_id = parseInt(selectedBrand);
      if (selectedContent) context.current_content = selectedContent;

      const res = await assistantApi.chat({
        message: input,
        conversation_history: messages.slice(-10),
        context
      });

      setMessages(prev => [...prev, { role: 'assistant', content: res.data.response, actions: res.data.actions }]);
    } catch (err) {
      toast.error('Failed to get response');
      setMessages(prev => [...prev, { role: 'assistant', content: "Sorry, I encountered an error. Please try again." }]);
    }
    setSending(false);
  };

  const handleQuickAction = async (action, params = {}) => {
    if (!selectedContent && action !== 'chat') {
      toast.error('Please enter some content first');
      return;
    }

    setSending(true);
    try {
      let res;
      switch (action) {
        case 'improve':
          res = await assistantApi.improve({ content: selectedContent, improvement_type: params.type || 'general' });
          setMessages(prev => [...prev, 
            { role: 'user', content: `Improve this content (${params.type || 'general'}):\n${selectedContent}` },
            { role: 'assistant', content: res.data.improved }
          ]);
          break;
        case 'hashtags':
          res = await assistantApi.hashtags({ content: selectedContent, platform: params.platform || 'instagram', count: 10 });
          setMessages(prev => [...prev,
            { role: 'user', content: `Generate hashtags for:\n${selectedContent}` },
            { role: 'assistant', content: res.data.hashtags.join('\n') }
          ]);
          break;
        case 'variations':
          res = await assistantApi.variations({ content: selectedContent, count: 3 });
          setMessages(prev => [...prev,
            { role: 'user', content: `Create variations of:\n${selectedContent}` },
            { role: 'assistant', content: res.data.variations.map((v, i) => `**Variation ${i + 1}:**\n${v}`).join('\n\n') }
          ]);
          break;
        case 'translate':
          res = await assistantApi.translate({ content: selectedContent, target_language: params.language || 'Spanish' });
          setMessages(prev => [...prev,
            { role: 'user', content: `Translate to ${params.language || 'Spanish'}:\n${selectedContent}` },
            { role: 'assistant', content: res.data.translated }
          ]);
          break;
      }
    } catch (err) {
      toast.error('Action failed');
    }
    setSending(false);
    setShowQuickAction(null);
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied!');
  };

  const useSuggested = (prompt) => {
    setInput(prompt);
  };

  return (
    <div className="h-[calc(100vh-8rem)] flex gap-6">
      {/* Main Chat */}
      <div className="flex-1 flex flex-col">
        <div className="flex items-center justify-between mb-4">
          <h1 className="page-title flex items-center gap-3">
            <MessageCircle className="w-8 h-8 text-accent" />
            AI Assistant
          </h1>
          <select
            value={selectedBrand}
            onChange={(e) => setSelectedBrand(e.target.value)}
            className="input-field w-auto"
          >
            <option value="">No brand context</option>
            {brands.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}
          </select>
        </div>

        {/* Messages */}
        <Card className="flex-1 p-4 overflow-hidden flex flex-col">
          <div className="flex-1 overflow-y-auto space-y-4 mb-4">
            {messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[80%] p-4 rounded-2xl ${
                  msg.role === 'user' 
                    ? 'bg-accent text-white rounded-br-md' 
                    : 'bg-slate text-pearl rounded-bl-md'
                }`}>
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                  {msg.role === 'assistant' && (
                    <button 
                      onClick={() => copyToClipboard(msg.content)} 
                      className="mt-2 text-xs opacity-60 hover:opacity-100 flex items-center gap-1"
                    >
                      <Copy className="w-3 h-3" /> Copy
                    </button>
                  )}
                </div>
              </div>
            ))}
            {sending && (
              <div className="flex justify-start">
                <div className="bg-slate p-4 rounded-2xl rounded-bl-md">
                  <Spinner size="sm" />
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
              placeholder="Ask me anything about content creation..."
              className="input-field flex-1"
              disabled={sending}
            />
            <button onClick={sendMessage} disabled={sending || !input.trim()} className="btn-primary px-4">
              <Send className="w-5 h-5" />
            </button>
          </div>
        </Card>
      </div>

      {/* Sidebar */}
      <div className="w-80 space-y-4">
        {/* Content Input */}
        <Card className="p-4">
          <h3 className="text-sm font-medium text-pearl mb-2">Working Content</h3>
          <textarea
            value={selectedContent}
            onChange={(e) => setSelectedContent(e.target.value)}
            placeholder="Paste content here to improve, translate, or generate hashtags..."
            className="input-field min-h-[100px] text-sm"
          />
        </Card>

        {/* Quick Actions */}
        <Card className="p-4">
          <h3 className="text-sm font-medium text-pearl mb-3">Quick Actions</h3>
          <div className="grid grid-cols-2 gap-2">
            {quickActions.map(action => (
              <button
                key={action.id}
                onClick={() => setShowQuickAction(action.id)}
                disabled={!selectedContent || sending}
                className={`p-3 rounded-lg text-center transition-all ${
                  selectedContent ? 'hover:bg-slate' : 'opacity-50 cursor-not-allowed'
                }`}
              >
                <div className={`w-10 h-10 ${action.color} rounded-full flex items-center justify-center mx-auto mb-2`}>
                  <action.icon className="w-5 h-5 text-white" />
                </div>
                <span className="text-xs text-pearl">{action.label}</span>
              </button>
            ))}
          </div>

          {/* Quick Action Options */}
          {showQuickAction === 'improve' && (
            <div className="mt-3 pt-3 border-t border-graphite">
              <p className="text-xs text-silver mb-2">Improvement type:</p>
              <div className="flex flex-wrap gap-2">
                {['general', 'shorter', 'longer', 'engaging', 'professional', 'casual'].map(type => (
                  <button
                    key={type}
                    onClick={() => handleQuickAction('improve', { type })}
                    className="px-3 py-1 bg-slate rounded-full text-xs text-pearl hover:bg-accent hover:text-white"
                  >
                    {type}
                  </button>
                ))}
              </div>
            </div>
          )}

          {showQuickAction === 'translate' && (
            <div className="mt-3 pt-3 border-t border-graphite">
              <p className="text-xs text-silver mb-2">Target language:</p>
              <div className="flex flex-wrap gap-2">
                {['Spanish', 'French', 'German', 'Italian', 'Portuguese', 'Japanese', 'Chinese'].map(lang => (
                  <button
                    key={lang}
                    onClick={() => handleQuickAction('translate', { language: lang })}
                    className="px-3 py-1 bg-slate rounded-full text-xs text-pearl hover:bg-accent hover:text-white"
                  >
                    {lang}
                  </button>
                ))}
              </div>
            </div>
          )}

          {showQuickAction === 'hashtags' && (
            <div className="mt-3 pt-3 border-t border-graphite">
              <p className="text-xs text-silver mb-2">Platform:</p>
              <div className="flex flex-wrap gap-2">
                {['instagram', 'twitter', 'linkedin', 'tiktok'].map(platform => (
                  <button
                    key={platform}
                    onClick={() => handleQuickAction('hashtags', { platform })}
                    className="px-3 py-1 bg-slate rounded-full text-xs text-pearl hover:bg-accent hover:text-white capitalize"
                  >
                    {platform}
                  </button>
                ))}
              </div>
            </div>
          )}

          {showQuickAction === 'variations' && (
            <div className="mt-3 pt-3 border-t border-graphite">
              <button
                onClick={() => handleQuickAction('variations')}
                className="btn-primary w-full text-sm"
              >
                Generate 3 Variations
              </button>
            </div>
          )}
        </Card>

        {/* Suggested Prompts */}
        <Card className="p-4">
          <h3 className="text-sm font-medium text-pearl mb-3 flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-accent" />
            Try asking...
          </h3>
          <div className="space-y-2">
            {suggestedPrompts.map((prompt, i) => (
              <button
                key={i}
                onClick={() => useSuggested(prompt)}
                className="w-full text-left p-2 text-xs text-silver hover:text-pearl hover:bg-slate rounded-lg transition-colors"
              >
                "{prompt}"
              </button>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
