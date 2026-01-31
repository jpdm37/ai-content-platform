import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Calendar as CalendarIcon, Plus, ChevronLeft, ChevronRight, Clock, Image as ImageIcon, Send, Trash2, Edit2, Twitter, Instagram, Linkedin } from 'lucide-react';
import { socialApi, brandsApi, generateApi } from '../../services/api';
import { Card, Badge, LoadingState, Spinner, Modal, ConfirmDialog } from '../../components/ui';
import toast from 'react-hot-toast';

const platformIcons = { twitter: Twitter, instagram: Instagram, linkedin: Linkedin };
const statusColors = {
  draft: 'bg-gray-500',
  scheduled: 'bg-blue-500',
  publishing: 'bg-yellow-500',
  published: 'bg-green-500',
  failed: 'bg-red-500',
  cancelled: 'bg-gray-400'
};

export default function SocialSchedule() {
  const [searchParams] = useSearchParams();
  const preselectedAccount = searchParams.get('account');

  const [accounts, setAccounts] = useState([]);
  const [brands, setBrands] = useState([]);
  const [posts, setPosts] = useState([]);
  const [calendarData, setCalendarData] = useState([]);
  const [loading, setLoading] = useState(true);

  // Calendar state
  const [currentDate, setCurrentDate] = useState(new Date());
  const [viewMode, setViewMode] = useState('calendar'); // calendar, list

  // Create/Edit modal
  const [showModal, setShowModal] = useState(false);
  const [editingPost, setEditingPost] = useState(null);
  const [formData, setFormData] = useState({
    social_account_id: preselectedAccount || '',
    caption: '',
    hashtags: '',
    media_urls: '',
    scheduled_for: '',
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
  });
  const [saving, setSaving] = useState(false);

  // Delete confirmation
  const [deletePost, setDeletePost] = useState(null);

  // Content picker
  const [contentPickerOpen, setContentPickerOpen] = useState(false);
  const [generatedContent, setGeneratedContent] = useState([]);

  useEffect(() => {
    fetchData();
  }, [currentDate]);

  const fetchData = async () => {
    try {
      const [accountsRes, brandsRes] = await Promise.all([
        socialApi.listAccounts(),
        brandsApi.list()
      ]);
      setAccounts(accountsRes.data);
      setBrands(brandsRes.data);

      // Fetch calendar data
      const year = currentDate.getFullYear();
      const month = currentDate.getMonth() + 1;
      const calendarRes = await socialApi.getCalendar(year, month);
      setCalendarData(calendarRes.data);

      // Fetch posts list
      const postsRes = await socialApi.listPosts({ limit: 50 });
      setPosts(postsRes.data);

      // Fetch generated content for picker
      const contentRes = await generateApi.getAll({ limit: 20 });
      setGeneratedContent(contentRes.data);
    } catch (err) {
      toast.error('Failed to load data');
    }
    setLoading(false);
  };

  const handleCreatePost = () => {
    setEditingPost(null);
    setFormData({
      social_account_id: preselectedAccount || '',
      caption: '',
      hashtags: '',
      media_urls: '',
      scheduled_for: getDefaultScheduleTime(),
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
    });
    setShowModal(true);
  };

  const handleEditPost = (post) => {
    setEditingPost(post);
    setFormData({
      social_account_id: post.social_account_id,
      caption: post.caption || '',
      hashtags: (post.hashtags || []).join(', '),
      media_urls: (post.media_urls || []).join('\n'),
      scheduled_for: formatDateTimeLocal(post.scheduled_for),
      timezone: post.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone
    });
    setShowModal(true);
  };

  const handleSavePost = async () => {
    if (!formData.social_account_id) {
      toast.error('Please select an account');
      return;
    }
    if (!formData.caption && !formData.media_urls) {
      toast.error('Please add caption or media');
      return;
    }
    if (!formData.scheduled_for) {
      toast.error('Please select a schedule time');
      return;
    }

    setSaving(true);
    try {
      const payload = {
        social_account_id: parseInt(formData.social_account_id),
        caption: formData.caption,
        hashtags: formData.hashtags.split(',').map(h => h.trim()).filter(Boolean),
        media_urls: formData.media_urls.split('\n').map(u => u.trim()).filter(Boolean),
        scheduled_for: new Date(formData.scheduled_for).toISOString(),
        timezone: formData.timezone
      };

      if (editingPost) {
        await socialApi.updatePost(editingPost.id, payload);
        toast.success('Post updated');
      } else {
        await socialApi.createPost(payload);
        toast.success('Post scheduled');
      }

      setShowModal(false);
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to save post');
    }
    setSaving(false);
  };

  const handleDeletePost = async () => {
    if (!deletePost) return;
    try {
      await socialApi.deletePost(deletePost.id);
      toast.success('Post deleted');
      fetchData();
    } catch (err) {
      toast.error('Failed to delete post');
    }
    setDeletePost(null);
  };

  const handlePostNow = async (post) => {
    if (!confirm('Post immediately?')) return;
    try {
      await socialApi.postNow({
        social_account_id: post.social_account_id,
        caption: post.caption,
        hashtags: post.hashtags,
        media_urls: post.media_urls
      });
      toast.success('Posted successfully!');
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to post');
    }
  };

  const handleSelectContent = (content) => {
    setFormData({
      ...formData,
      caption: content.caption || '',
      media_urls: content.result_url || ''
    });
    setContentPickerOpen(false);
  };

  // Calendar helpers
  const getDefaultScheduleTime = () => {
    const d = new Date();
    d.setHours(d.getHours() + 1, 0, 0, 0);
    return formatDateTimeLocal(d);
  };

  const formatDateTimeLocal = (date) => {
    const d = new Date(date);
    return d.toISOString().slice(0, 16);
  };

  const getDaysInMonth = () => {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const days = [];

    // Add padding for days before first of month
    for (let i = 0; i < firstDay.getDay(); i++) {
      days.push(null);
    }

    // Add days of month
    for (let i = 1; i <= lastDay.getDate(); i++) {
      days.push(i);
    }

    return days;
  };

  const getPostsForDay = (day) => {
    if (!day) return [];
    const dateStr = `${currentDate.getFullYear()}-${String(currentDate.getMonth() + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    const dayData = calendarData.find(d => d.date === dateStr);
    return dayData?.posts || [];
  };

  const prevMonth = () => setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() - 1));
  const nextMonth = () => setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + 1));

  if (loading) return <LoadingState message="Loading schedule..." />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="page-title flex items-center gap-3">
            <CalendarIcon className="w-8 h-8 text-accent" />
            Post Schedule
          </h1>
          <p className="text-silver mt-1">Schedule and manage your social media posts</p>
        </div>
        <div className="flex gap-3">
          <div className="flex bg-slate rounded-lg p-1">
            <button
              onClick={() => setViewMode('calendar')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${viewMode === 'calendar' ? 'bg-accent text-white' : 'text-silver hover:text-pearl'}`}
            >
              Calendar
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${viewMode === 'list' ? 'bg-accent text-white' : 'text-silver hover:text-pearl'}`}
            >
              List
            </button>
          </div>
          <button onClick={handleCreatePost} className="btn-primary flex items-center gap-2">
            <Plus className="w-4 h-4" /> Schedule Post
          </button>
        </div>
      </div>

      {/* Calendar View */}
      {viewMode === 'calendar' && (
        <Card className="p-6">
          {/* Calendar Header */}
          <div className="flex items-center justify-between mb-6">
            <button onClick={prevMonth} className="p-2 hover:bg-slate rounded-lg transition-colors">
              <ChevronLeft className="w-5 h-5 text-silver" />
            </button>
            <h2 className="text-xl font-display font-bold text-pearl">
              {currentDate.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}
            </h2>
            <button onClick={nextMonth} className="p-2 hover:bg-slate rounded-lg transition-colors">
              <ChevronRight className="w-5 h-5 text-silver" />
            </button>
          </div>

          {/* Calendar Grid */}
          <div className="grid grid-cols-7 gap-1">
            {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day => (
              <div key={day} className="text-center text-silver text-sm font-medium py-2">
                {day}
              </div>
            ))}

            {getDaysInMonth().map((day, i) => {
              const dayPosts = getPostsForDay(day);
              const isToday = day === new Date().getDate() && 
                currentDate.getMonth() === new Date().getMonth() &&
                currentDate.getFullYear() === new Date().getFullYear();

              return (
                <div
                  key={i}
                  className={`min-h-[100px] p-2 border border-graphite rounded-lg ${day ? 'bg-charcoal' : 'bg-slate/30'} ${isToday ? 'ring-2 ring-accent' : ''}`}
                >
                  {day && (
                    <>
                      <span className={`text-sm font-medium ${isToday ? 'text-accent' : 'text-silver'}`}>
                        {day}
                      </span>
                      <div className="mt-1 space-y-1">
                        {dayPosts.slice(0, 3).map((post, j) => {
                          const Icon = platformIcons[post.platform] || CalendarIcon;
                          return (
                            <div
                              key={j}
                              className={`text-xs p-1 rounded ${statusColors[post.status]} text-white truncate cursor-pointer hover:opacity-80`}
                              title={post.caption_preview}
                              onClick={() => {
                                const fullPost = posts.find(p => p.id === post.id);
                                if (fullPost) handleEditPost(fullPost);
                              }}
                            >
                              <Icon className="w-3 h-3 inline mr-1" />
                              {new Date(post.scheduled_for).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </div>
                          );
                        })}
                        {dayPosts.length > 3 && (
                          <span className="text-xs text-silver">+{dayPosts.length - 3} more</span>
                        )}
                      </div>
                    </>
                  )}
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {/* List View */}
      {viewMode === 'list' && (
        <Card className="p-6">
          {posts.length === 0 ? (
            <div className="text-center py-12">
              <CalendarIcon className="w-12 h-12 text-silver mx-auto mb-4" />
              <p className="text-pearl font-medium">No posts scheduled</p>
              <p className="text-silver text-sm">Create your first scheduled post</p>
            </div>
          ) : (
            <div className="space-y-4">
              {posts.map((post) => {
                const account = accounts.find(a => a.id === post.social_account_id);
                const Icon = platformIcons[post.platform] || CalendarIcon;

                return (
                  <div key={post.id} className="flex items-start gap-4 p-4 bg-slate rounded-xl">
                    {/* Media Preview */}
                    <div className="w-20 h-20 bg-graphite rounded-lg flex-shrink-0 overflow-hidden">
                      {post.media_urls?.[0] ? (
                        <img src={post.media_urls[0]} alt="" className="w-full h-full object-cover" />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center">
                          <ImageIcon className="w-8 h-8 text-silver" />
                        </div>
                      )}
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <Icon className="w-4 h-4 text-silver" />
                        <span className="text-silver text-sm">@{post.account_username}</span>
                        <Badge className={`${statusColors[post.status]} text-white text-xs`}>
                          {post.status}
                        </Badge>
                      </div>
                      <p className="text-pearl line-clamp-2">{post.caption}</p>
                      <div className="flex items-center gap-4 mt-2 text-sm text-silver">
                        <span className="flex items-center gap-1">
                          <Clock className="w-4 h-4" />
                          {new Date(post.scheduled_for).toLocaleString()}
                        </span>
                        {post.hashtags?.length > 0 && (
                          <span>{post.hashtags.length} hashtags</span>
                        )}
                        {post.media_urls?.length > 0 && (
                          <span>{post.media_urls.length} media</span>
                        )}
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2">
                      {post.status === 'scheduled' && (
                        <>
                          <button
                            onClick={() => handlePostNow(post)}
                            className="p-2 text-silver hover:text-success transition-colors"
                            title="Post Now"
                          >
                            <Send className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleEditPost(post)}
                            className="p-2 text-silver hover:text-accent transition-colors"
                            title="Edit"
                          >
                            <Edit2 className="w-4 h-4" />
                          </button>
                        </>
                      )}
                      <button
                        onClick={() => setDeletePost(post)}
                        className="p-2 text-silver hover:text-error transition-colors"
                        title="Delete"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </Card>
      )}

      {/* Create/Edit Modal */}
      <Modal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        title={editingPost ? 'Edit Post' : 'Schedule Post'}
        size="lg"
      >
        <div className="space-y-4">
          {/* Account Selection */}
          <div>
            <label className="label">Social Account *</label>
            <select
              value={formData.social_account_id}
              onChange={(e) => setFormData({ ...formData, social_account_id: e.target.value })}
              className="input-field"
            >
              <option value="">Select account...</option>
              {accounts.map((account) => (
                <option key={account.id} value={account.id}>
                  {account.platform} - @{account.platform_username}
                </option>
              ))}
            </select>
          </div>

          {/* Caption */}
          <div>
            <div className="flex justify-between">
              <label className="label">Caption</label>
              <button
                onClick={() => setContentPickerOpen(true)}
                className="text-accent text-sm hover:text-accent-light"
              >
                Use generated content
              </button>
            </div>
            <textarea
              value={formData.caption}
              onChange={(e) => setFormData({ ...formData, caption: e.target.value })}
              placeholder="Write your caption..."
              className="input-field min-h-[120px]"
            />
            <p className="text-silver text-xs mt-1">{formData.caption.length} characters</p>
          </div>

          {/* Hashtags */}
          <div>
            <label className="label">Hashtags (comma separated)</label>
            <input
              type="text"
              value={formData.hashtags}
              onChange={(e) => setFormData({ ...formData, hashtags: e.target.value })}
              placeholder="marketing, socialmedia, AI"
              className="input-field"
            />
          </div>

          {/* Media URLs */}
          <div>
            <label className="label">Media URLs (one per line)</label>
            <textarea
              value={formData.media_urls}
              onChange={(e) => setFormData({ ...formData, media_urls: e.target.value })}
              placeholder="https://example.com/image1.jpg&#10;https://example.com/image2.jpg"
              className="input-field min-h-[80px]"
            />
          </div>

          {/* Schedule Time */}
          <div>
            <label className="label">Schedule For *</label>
            <input
              type="datetime-local"
              value={formData.scheduled_for}
              onChange={(e) => setFormData({ ...formData, scheduled_for: e.target.value })}
              className="input-field"
            />
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-4">
            <button onClick={() => setShowModal(false)} className="btn-secondary flex-1">
              Cancel
            </button>
            <button onClick={handleSavePost} disabled={saving} className="btn-primary flex-1">
              {saving ? <Spinner size="sm" /> : editingPost ? 'Update Post' : 'Schedule Post'}
            </button>
          </div>
        </div>
      </Modal>

      {/* Content Picker Modal */}
      <Modal
        isOpen={contentPickerOpen}
        onClose={() => setContentPickerOpen(false)}
        title="Select Generated Content"
        size="lg"
      >
        <div className="grid grid-cols-2 gap-4 max-h-[400px] overflow-y-auto">
          {generatedContent.map((content) => (
            <div
              key={content.id}
              onClick={() => handleSelectContent(content)}
              className="bg-slate rounded-lg p-3 cursor-pointer hover:bg-graphite transition-colors"
            >
              {content.result_url && (
                <img src={content.result_url} alt="" className="w-full aspect-square object-cover rounded-lg mb-2" />
              )}
              <p className="text-sm text-pearl line-clamp-2">{content.caption}</p>
            </div>
          ))}
        </div>
      </Modal>

      {/* Delete Confirmation */}
      <ConfirmDialog
        isOpen={!!deletePost}
        onClose={() => setDeletePost(null)}
        onConfirm={handleDeletePost}
        title="Delete Post?"
        message="This post will be permanently deleted."
        confirmText="Delete"
        danger
      />
    </div>
  );
}
