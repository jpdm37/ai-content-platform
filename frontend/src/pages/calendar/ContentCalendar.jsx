import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  ChevronLeft, ChevronRight, Plus, Calendar as CalendarIcon,
  Clock, AlertCircle, Instagram, Twitter, Linkedin, Facebook,
  MoreHorizontal, Edit, Trash2, ExternalLink, Zap, Lightbulb
} from 'lucide-react';
import api from '../../services/api';
import { Card, LoadingState, Badge, Modal, Spinner } from '../../components/ui';
import toast from 'react-hot-toast';

// Platform icons
const platformIcons = {
  instagram: Instagram,
  twitter: Twitter,
  linkedin: Linkedin,
  facebook: Facebook
};

// Platform colors
const platformColors = {
  instagram: 'bg-gradient-to-r from-purple-500 to-pink-500',
  twitter: 'bg-blue-400',
  linkedin: 'bg-blue-600',
  facebook: 'bg-blue-500',
  tiktok: 'bg-black'
};

export default function ContentCalendar() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState('week'); // 'week' or 'month'
  const [currentDate, setCurrentDate] = useState(new Date());
  const [calendarData, setCalendarData] = useState(null);
  const [gaps, setGaps] = useState(null);
  const [selectedPost, setSelectedPost] = useState(null);
  const [showPostModal, setShowPostModal] = useState(false);
  const [showGapModal, setShowGapModal] = useState(false);
  const [selectedGap, setSelectedGap] = useState(null);
  const [rescheduling, setRescheduling] = useState(false);

  useEffect(() => {
    fetchCalendarData();
  }, [currentDate, view]);

  useEffect(() => {
    fetchGaps();
  }, []);

  const fetchCalendarData = async () => {
    setLoading(true);
    try {
      let res;
      if (view === 'week') {
        res = await api.get('/calendar/week', {
          params: { week_offset: getWeekOffset() }
        });
      } else {
        res = await api.get('/calendar/month', {
          params: { 
            year: currentDate.getFullYear(),
            month: currentDate.getMonth() + 1
          }
        });
      }
      setCalendarData(res.data);
    } catch (err) {
      toast.error('Failed to load calendar');
    }
    setLoading(false);
  };

  const fetchGaps = async () => {
    try {
      const res = await api.get('/calendar/gaps', { params: { days_ahead: 14 } });
      setGaps(res.data);
    } catch (err) {
      console.error('Failed to fetch gaps:', err);
    }
  };

  const getWeekOffset = () => {
    const now = new Date();
    const startOfThisWeek = new Date(now.setDate(now.getDate() - now.getDay() + 1));
    const diffTime = currentDate - startOfThisWeek;
    const diffWeeks = Math.floor(diffTime / (7 * 24 * 60 * 60 * 1000));
    return diffWeeks;
  };

  const navigatePrevious = () => {
    const newDate = new Date(currentDate);
    if (view === 'week') {
      newDate.setDate(newDate.getDate() - 7);
    } else {
      newDate.setMonth(newDate.getMonth() - 1);
    }
    setCurrentDate(newDate);
  };

  const navigateNext = () => {
    const newDate = new Date(currentDate);
    if (view === 'week') {
      newDate.setDate(newDate.getDate() + 7);
    } else {
      newDate.setMonth(newDate.getMonth() + 1);
    }
    setCurrentDate(newDate);
  };

  const navigateToday = () => {
    setCurrentDate(new Date());
  };

  const handlePostClick = (post) => {
    setSelectedPost(post);
    setShowPostModal(true);
  };

  const handleGapClick = (gap) => {
    setSelectedGap(gap);
    setShowGapModal(true);
  };

  const handleReschedule = async (postId, newDateTime) => {
    setRescheduling(true);
    try {
      await api.put(`/calendar/schedule/${postId}/reschedule`, {
        new_time: newDateTime
      });
      toast.success('Post rescheduled');
      fetchCalendarData();
      setShowPostModal(false);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to reschedule');
    }
    setRescheduling(false);
  };

  const handleCancelPost = async (postId) => {
    if (!confirm('Are you sure you want to cancel this scheduled post?')) return;
    
    try {
      await api.delete(`/calendar/schedule/${postId}`);
      toast.success('Post cancelled');
      fetchCalendarData();
      setShowPostModal(false);
    } catch (err) {
      toast.error('Failed to cancel post');
    }
  };

  const getTitle = () => {
    if (!calendarData) return '';
    if (view === 'month') {
      return `${calendarData.month_name} ${calendarData.year}`;
    }
    return `Week of ${calendarData.week_start}`;
  };

  if (loading && !calendarData) return <LoadingState message="Loading calendar..." />;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-pearl">Content Calendar</h1>
          <p className="text-silver">Plan and schedule your content</p>
        </div>
        
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/studio/create')}
            className="btn-primary px-4 py-2 flex items-center gap-2"
          >
            <Plus className="w-4 h-4" />
            Create Content
          </button>
        </div>
      </div>

      {/* Gaps Alert */}
      {gaps && gaps.empty_days_count > 0 && (
        <Card className="p-4 border-l-4 border-yellow-500 bg-yellow-500/10">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-yellow-500 mt-0.5" />
            <div className="flex-1">
              <p className="text-pearl font-medium">
                You have {gaps.empty_days_count} days without scheduled content
              </p>
              <p className="text-silver text-sm mt-1">
                {gaps.recommendation?.message}
              </p>
            </div>
            <button
              onClick={() => navigate('/templates')}
              className="text-sm text-accent hover:underline"
            >
              Fill Gaps →
            </button>
          </div>
        </Card>
      )}

      {/* Calendar Controls */}
      <Card className="p-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          {/* Navigation */}
          <div className="flex items-center gap-2">
            <button
              onClick={navigatePrevious}
              className="p-2 hover:bg-slate rounded-lg transition-colors"
            >
              <ChevronLeft className="w-5 h-5 text-silver" />
            </button>
            <button
              onClick={navigateToday}
              className="px-3 py-1 text-sm text-silver hover:text-pearl hover:bg-slate rounded-lg transition-colors"
            >
              Today
            </button>
            <button
              onClick={navigateNext}
              className="p-2 hover:bg-slate rounded-lg transition-colors"
            >
              <ChevronRight className="w-5 h-5 text-silver" />
            </button>
            <span className="ml-4 text-lg font-semibold text-pearl">{getTitle()}</span>
          </div>
          
          {/* View Toggle */}
          <div className="flex items-center gap-2 bg-slate rounded-lg p-1">
            <button
              onClick={() => setView('week')}
              className={`px-4 py-1.5 rounded-md text-sm transition-colors ${
                view === 'week' ? 'bg-charcoal text-pearl' : 'text-silver hover:text-pearl'
              }`}
            >
              Week
            </button>
            <button
              onClick={() => setView('month')}
              className={`px-4 py-1.5 rounded-md text-sm transition-colors ${
                view === 'month' ? 'bg-charcoal text-pearl' : 'text-silver hover:text-pearl'
              }`}
            >
              Month
            </button>
          </div>
        </div>
      </Card>

      {/* Calendar Grid */}
      {view === 'week' ? (
        <WeekView 
          data={calendarData}
          onPostClick={handlePostClick}
          onGapClick={handleGapClick}
        />
      ) : (
        <MonthView 
          data={calendarData}
          onPostClick={handlePostClick}
          onDayClick={(date) => handleGapClick({ date, weekday: '' })}
        />
      )}

      {/* Stats */}
      {calendarData?.stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card className="p-4 text-center">
            <p className="text-2xl font-bold text-pearl">{calendarData.total_posts || 0}</p>
            <p className="text-sm text-silver">Total Posts</p>
          </Card>
          <Card className="p-4 text-center">
            <p className="text-2xl font-bold text-green-500">{calendarData.stats?.published || 0}</p>
            <p className="text-sm text-silver">Published</p>
          </Card>
          <Card className="p-4 text-center">
            <p className="text-2xl font-bold text-blue-500">{calendarData.stats?.scheduled || 0}</p>
            <p className="text-sm text-silver">Scheduled</p>
          </Card>
          <Card className="p-4 text-center">
            <p className="text-2xl font-bold text-yellow-500">
              {gaps?.coverage_percent || 0}%
            </p>
            <p className="text-sm text-silver">Coverage</p>
          </Card>
        </div>
      )}

      {/* Post Detail Modal */}
      <Modal
        isOpen={showPostModal}
        onClose={() => setShowPostModal(false)}
        title="Scheduled Post"
      >
        {selectedPost && (
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className={`w-10 h-10 rounded-lg ${platformColors[selectedPost.platform] || 'bg-slate'} flex items-center justify-center`}>
                {platformIcons[selectedPost.platform] ? (
                  (() => {
                    const Icon = platformIcons[selectedPost.platform];
                    return <Icon className="w-5 h-5 text-white" />;
                  })()
                ) : (
                  <span className="text-white text-xs">{selectedPost.platform}</span>
                )}
              </div>
              <div>
                <p className="text-pearl font-medium capitalize">{selectedPost.platform}</p>
                <p className="text-silver text-sm">
                  {new Date(selectedPost.scheduled_time).toLocaleString()}
                </p>
              </div>
              <Badge className="ml-auto">{selectedPost.status}</Badge>
            </div>
            
            <div className="p-4 bg-slate rounded-lg">
              <p className="text-pearl">{selectedPost.caption_preview}</p>
            </div>
            
            <div className="flex gap-2">
              <button
                onClick={() => handleCancelPost(selectedPost.id)}
                className="flex-1 py-2 rounded-lg border border-red-500/50 text-red-400 hover:bg-red-500/10 transition-colors flex items-center justify-center gap-2"
              >
                <Trash2 className="w-4 h-4" />
                Cancel Post
              </button>
              <button
                onClick={() => navigate(`/studio/${selectedPost.content_id}`)}
                className="flex-1 py-2 rounded-lg border border-graphite text-silver hover:text-pearl hover:border-silver transition-colors flex items-center justify-center gap-2"
              >
                <Edit className="w-4 h-4" />
                Edit Content
              </button>
            </div>
          </div>
        )}
      </Modal>

      {/* Fill Gap Modal */}
      <Modal
        isOpen={showGapModal}
        onClose={() => setShowGapModal(false)}
        title="Fill Content Gap"
      >
        {selectedGap && (
          <div className="space-y-4">
            <p className="text-silver">
              No content scheduled for <span className="text-pearl">{selectedGap.date}</span>
            </p>
            
            <div className="space-y-2">
              <p className="text-sm font-medium text-pearl">Quick Actions:</p>
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => {
                    setShowGapModal(false);
                    navigate('/studio/create');
                  }}
                  className="p-4 rounded-lg border border-graphite hover:border-accent transition-colors text-left"
                >
                  <Zap className="w-5 h-5 text-accent mb-2" />
                  <p className="text-pearl font-medium">Create New</p>
                  <p className="text-xs text-silver">Generate with AI</p>
                </button>
                <button
                  onClick={() => {
                    setShowGapModal(false);
                    navigate('/templates');
                  }}
                  className="p-4 rounded-lg border border-graphite hover:border-accent transition-colors text-left"
                >
                  <Lightbulb className="w-5 h-5 text-yellow-500 mb-2" />
                  <p className="text-pearl font-medium">Use Template</p>
                  <p className="text-xs text-silver">Start from template</p>
                </button>
              </div>
            </div>
            
            {selectedGap.suggested_times && (
              <div>
                <p className="text-sm font-medium text-pearl mb-2">Suggested Times:</p>
                <div className="flex flex-wrap gap-2">
                  {selectedGap.suggested_times.map((slot, i) => (
                    <span key={i} className="px-3 py-1 bg-slate rounded-full text-sm text-silver">
                      {slot.time || slot} - {slot.label || 'Good'}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}

// Week View Component
function WeekView({ data, onPostClick, onGapClick }) {
  if (!data?.days) return null;
  
  const hours = Array.from({ length: 24 }, (_, i) => i);
  
  return (
    <div className="overflow-x-auto">
      <div className="min-w-[800px]">
        {/* Day Headers */}
        <div className="grid grid-cols-8 gap-1 mb-2">
          <div className="p-2 text-xs text-silver">Time</div>
          {data.days.map((day, i) => (
            <div 
              key={i}
              className={`p-2 text-center rounded-lg ${day.is_today ? 'bg-accent/20' : ''}`}
            >
              <p className={`text-xs ${day.is_today ? 'text-accent' : 'text-silver'}`}>
                {day.weekday_short}
              </p>
              <p className={`text-lg font-bold ${day.is_today ? 'text-accent' : 'text-pearl'}`}>
                {day.day}
              </p>
              {day.post_count > 0 && (
                <Badge variant="default" className="text-xs mt-1">{day.post_count}</Badge>
              )}
            </div>
          ))}
        </div>
        
        {/* Time Grid - Simplified view showing posts */}
        <Card className="p-4">
          <div className="grid grid-cols-7 gap-4">
            {data.days.map((day, dayIndex) => (
              <div key={dayIndex} className={`min-h-[200px] ${day.is_past ? 'opacity-50' : ''}`}>
                {day.posts.length > 0 ? (
                  <div className="space-y-2">
                    {day.posts.map((post, postIndex) => (
                      <button
                        key={postIndex}
                        onClick={() => onPostClick(post)}
                        className={`w-full p-2 rounded-lg text-left text-xs ${
                          platformColors[post.platform] || 'bg-slate'
                        } hover:opacity-80 transition-opacity`}
                      >
                        <p className="text-white font-medium truncate">
                          {post.scheduled_hour}:00 - {post.platform}
                        </p>
                        <p className="text-white/80 truncate">{post.caption_preview}</p>
                      </button>
                    ))}
                  </div>
                ) : !day.is_past ? (
                  <button
                    onClick={() => onGapClick({ date: day.date, weekday: day.weekday })}
                    className="w-full h-full min-h-[100px] border-2 border-dashed border-graphite rounded-lg flex items-center justify-center hover:border-accent/50 transition-colors group"
                  >
                    <Plus className="w-6 h-6 text-graphite group-hover:text-accent/50" />
                  </button>
                ) : (
                  <div className="w-full h-full min-h-[100px] flex items-center justify-center">
                    <p className="text-silver text-xs">No posts</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}

// Month View Component
function MonthView({ data, onPostClick, onDayClick }) {
  if (!data?.days) return null;
  
  // Pad beginning of month
  const firstDay = new Date(data.year, data.month - 1, 1);
  const startPadding = firstDay.getDay() === 0 ? 6 : firstDay.getDay() - 1;
  
  const weeks = [];
  let currentWeek = Array(startPadding).fill(null);
  
  data.days.forEach((day) => {
    currentWeek.push(day);
    if (currentWeek.length === 7) {
      weeks.push(currentWeek);
      currentWeek = [];
    }
  });
  
  if (currentWeek.length > 0) {
    while (currentWeek.length < 7) currentWeek.push(null);
    weeks.push(currentWeek);
  }
  
  const weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  
  return (
    <Card className="p-4">
      {/* Weekday Headers */}
      <div className="grid grid-cols-7 gap-1 mb-2">
        {weekdays.map((day) => (
          <div key={day} className="p-2 text-center text-xs text-silver font-medium">
            {day}
          </div>
        ))}
      </div>
      
      {/* Calendar Grid */}
      <div className="space-y-1">
        {weeks.map((week, weekIndex) => (
          <div key={weekIndex} className="grid grid-cols-7 gap-1">
            {week.map((day, dayIndex) => (
              <div
                key={dayIndex}
                className={`min-h-[100px] p-2 rounded-lg border ${
                  day?.is_today 
                    ? 'border-accent bg-accent/10' 
                    : day 
                      ? 'border-graphite hover:border-silver cursor-pointer' 
                      : 'border-transparent'
                } ${day?.is_past ? 'opacity-50' : ''}`}
                onClick={() => day && !day.is_past && day.post_count === 0 && onDayClick(day.date)}
              >
                {day && (
                  <>
                    <p className={`text-sm font-medium ${day.is_today ? 'text-accent' : 'text-pearl'}`}>
                      {day.day}
                    </p>
                    <div className="mt-1 space-y-1">
                      {day.posts.slice(0, 3).map((post, i) => (
                        <button
                          key={i}
                          onClick={(e) => {
                            e.stopPropagation();
                            onPostClick(post);
                          }}
                          className={`w-full px-1 py-0.5 rounded text-xs text-white truncate ${
                            platformColors[post.platform] || 'bg-slate'
                          }`}
                        >
                          {post.platform}
                        </button>
                      ))}
                      {day.posts.length > 3 && (
                        <p className="text-xs text-silver">+{day.posts.length - 3} more</p>
                      )}
                    </div>
                  </>
                )}
              </div>
            ))}
          </div>
        ))}
      </div>
    </Card>
  );
}
