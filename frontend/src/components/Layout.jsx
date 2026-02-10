import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Building2,
  FolderOpen,
  TrendingUp,
  Sparkles,
  Images,
  Settings,
  Menu,
  X,
  Zap,
  Share2,
  Calendar,
  CreditCard,
  Video,
  BarChart3,
  MessageCircle,
  Layers,
  DollarSign,
  FileText,
  CalendarDays,
  FlaskConical,
  Activity
} from 'lucide-react';

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Content Studio', href: '/studio', icon: Layers },
  { name: 'Calendar', href: '/calendar', icon: CalendarDays },
  { name: 'Performance', href: '/performance', icon: Activity },
  { name: 'Templates', href: '/templates', icon: FileText },
  { name: 'AI Assistant', href: '/assistant', icon: MessageCircle },
  { name: 'A/B Testing', href: '/ab-testing', icon: FlaskConical },
  { name: 'Brands', href: '/brands', icon: Building2 },
  { name: 'Avatar Training', href: '/lora', icon: Sparkles },
  { name: 'Generate', href: '/generate', icon: Zap },
  { name: 'Videos', href: '/video', icon: Video },
  { name: 'Social Accounts', href: '/social/accounts', icon: Share2 },
  { name: 'Schedule', href: '/schedule', icon: Calendar },
  { name: 'Analytics', href: '/analytics', icon: BarChart3 },
  { name: 'Usage & Costs', href: '/costs', icon: DollarSign },
  { name: 'Trends', href: '/trends', icon: TrendingUp },
];

export default function Layout({ children }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();

  const isActive = (path) => {
    if (path === '/') return location.pathname === '/';
    return location.pathname.startsWith(path);
  };

  return (
    <div className="min-h-screen gradient-bg">
      {/* Mobile sidebar backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-midnight/80 backdrop-blur-sm z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed top-0 left-0 z-50 h-full w-72 bg-charcoal border-r border-graphite/50 
                    transform transition-transform duration-300 ease-in-out flex flex-col
                    lg:translate-x-0 ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}`}
      >
        {/* Logo */}
        <div className="h-16 flex items-center justify-between px-6 border-b border-graphite/50 flex-shrink-0">
          <Link to="/" className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent to-accent-dark 
                          flex items-center justify-center shadow-glow">
              <Zap className="w-5 h-5 text-white" />
            </div>
            <span className="font-display font-bold text-xl text-pearl">AI Content</span>
          </Link>
          <button
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden p-2 text-silver hover:text-pearl transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation - Scrollable */}
        <nav className="flex-1 overflow-y-auto p-4 space-y-1">
          {navigation.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.href);
            return (
              <Link
                key={item.name}
                to={item.href}
                onClick={() => setSidebarOpen(false)}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200
                          ${active
                    ? 'bg-accent/10 text-accent-light border border-accent/20'
                    : 'text-silver hover:text-pearl hover:bg-slate'
                  }`}
              >
                <Icon className={`w-5 h-5 ${active ? 'text-accent' : ''}`} />
                <span className="font-medium">{item.name}</span>
              </Link>
            );
          })}
        </nav>

        {/* Footer - Fixed at bottom */}
        <div className="flex-shrink-0 p-4 border-t border-graphite/50 space-y-3">
          <Link
            to="/billing"
            className={`flex items-center gap-3 px-4 py-2 rounded-xl transition-colors
                      ${isActive('/billing') 
                        ? 'bg-accent/10 text-accent-light border border-accent/20' 
                        : 'text-silver hover:text-pearl hover:bg-slate'}`}
          >
            <CreditCard className="w-5 h-5" />
            <span className="font-medium">Billing</span>
          </Link>
          <Link
            to="/pricing"
            className="flex items-center justify-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-accent to-accent-dark text-white font-medium text-sm hover:opacity-90 transition-opacity"
          >
            <Zap className="w-4 h-4" />
            Upgrade Plan
          </Link>
        </div>
      </aside>

      {/* Main content */}
      <div className="lg:pl-72">
        {/* Top header */}
        <header className="sticky top-0 z-30 h-16 glass border-b border-graphite/50">
          <div className="h-full px-4 sm:px-6 lg:px-8 flex items-center justify-between">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden p-2 text-silver hover:text-pearl transition-colors"
            >
              <Menu className="w-6 h-6" />
            </button>

            <div className="flex-1 lg:flex-none" />

            <div className="flex items-center gap-4">
              <Link
                to="/settings"
                className="p-2 text-silver hover:text-pearl transition-colors rounded-lg hover:bg-slate"
              >
                <Settings className="w-5 h-5" />
              </Link>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="p-4 sm:p-6 lg:p-8">
          <div className="animate-fade-in">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
