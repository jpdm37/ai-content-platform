import { Loader2, AlertCircle, CheckCircle, Info, X } from 'lucide-react';

// Loading Spinner
export function Spinner({ size = 'md', className = '' }) {
  const sizes = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-8 h-8',
  };

  return (
    <Loader2 className={`${sizes[size]} animate-spin text-accent ${className}`} />
  );
}

// Loading State
export function LoadingState({ message = 'Loading...' }) {
  return (
    <div className="flex flex-col items-center justify-center py-12">
      <Spinner size="lg" />
      <p className="mt-4 text-silver">{message}</p>
    </div>
  );
}

// Error State
export function ErrorState({ message, onRetry }) {
  return (
    <div className="flex flex-col items-center justify-center py-12">
      <div className="w-16 h-16 rounded-full bg-error/10 flex items-center justify-center mb-4">
        <AlertCircle className="w-8 h-8 text-error" />
      </div>
      <p className="text-pearl font-medium mb-2">Something went wrong</p>
      <p className="text-silver text-sm mb-4">{message}</p>
      {onRetry && (
        <button onClick={onRetry} className="btn-secondary">
          Try Again
        </button>
      )}
    </div>
  );
}

// Empty State
export function EmptyState({ icon: Icon, title, description, action }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      {Icon && (
        <div className="w-16 h-16 rounded-full bg-slate flex items-center justify-center mb-4">
          <Icon className="w-8 h-8 text-silver" />
        </div>
      )}
      <p className="text-pearl font-medium mb-2">{title}</p>
      <p className="text-silver text-sm mb-4 max-w-md">{description}</p>
      {action}
    </div>
  );
}

// Modal
export function Modal({ isOpen, onClose, title, children, size = 'md' }) {
  if (!isOpen) return null;

  const sizes = {
    sm: 'max-w-md',
    md: 'max-w-lg',
    lg: 'max-w-2xl',
    xl: 'max-w-4xl',
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-midnight/90 backdrop-blur-sm"
        onClick={onClose}
      />
      <div
        className={`relative w-full ${sizes[size]} bg-charcoal rounded-2xl border border-graphite 
                    shadow-card animate-slide-up`}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-graphite">
          <h3 className="font-display font-semibold text-lg text-pearl">{title}</h3>
          <button
            onClick={onClose}
            className="p-2 text-silver hover:text-pearl transition-colors rounded-lg hover:bg-slate"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-6">{children}</div>
      </div>
    </div>
  );
}

// Confirmation Dialog
export function ConfirmDialog({ isOpen, onClose, onConfirm, title, message, confirmText = 'Confirm', danger = false }) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title={title} size="sm">
      <p className="text-silver mb-6">{message}</p>
      <div className="flex gap-3 justify-end">
        <button onClick={onClose} className="btn-secondary">
          Cancel
        </button>
        <button
          onClick={() => {
            onConfirm();
            onClose();
          }}
          className={danger ? 'btn-danger' : 'btn-primary'}
        >
          {confirmText}
        </button>
      </div>
    </Modal>
  );
}

// Badge
export function Badge({ variant = 'info', children, className = '' }) {
  const variants = {
    default: 'bg-graphite text-silver',
    success: 'badge-success',
    warning: 'badge-warning',
    error: 'badge-error',
    info: 'badge-info',
    secondary: 'bg-slate text-silver border border-graphite',
  };

  return <span className={`badge ${variants[variant] || ''} ${className}`}>{children}</span>;
}

// Status Badge
export function StatusBadge({ status }) {
  const statusConfig = {
    pending: { variant: 'warning', label: 'Pending' },
    generating: { variant: 'info', label: 'Generating' },
    completed: { variant: 'success', label: 'Completed' },
    failed: { variant: 'error', label: 'Failed' },
  };

  const config = statusConfig[status?.toLowerCase()] || { variant: 'info', label: status };

  return <Badge variant={config.variant}>{config.label}</Badge>;
}

// Card
export function Card({ children, className = '', hover = false, onClick }) {
  return (
    <div
      className={`card ${hover ? 'card-hover cursor-pointer' : ''} ${className}`}
      onClick={onClick}
    >
      {children}
    </div>
  );
}

// Stats Card
export function StatsCard({ label, value, icon: Icon, trend, color = 'accent' }) {
  const colors = {
    accent: 'from-accent/20 to-accent/5 text-accent',
    success: 'from-success/20 to-success/5 text-success',
    warning: 'from-warning/20 to-warning/5 text-warning',
    error: 'from-error/20 to-error/5 text-error',
  };

  return (
    <Card className="p-6">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-silver text-sm mb-1">{label}</p>
          <p className="text-3xl font-display font-bold text-pearl">{value}</p>
          {trend && (
            <p className={`text-sm mt-2 ${trend > 0 ? 'text-success' : 'text-error'}`}>
              {trend > 0 ? '+' : ''}{trend}% from last week
            </p>
          )}
        </div>
        {Icon && (
          <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${colors[color]} 
                          flex items-center justify-center`}>
            <Icon className="w-6 h-6" />
          </div>
        )}
      </div>
    </Card>
  );
}

// Skeleton Loaders
export function SkeletonCard() {
  return (
    <div className="card p-6 space-y-4">
      <div className="skeleton h-4 w-1/3" />
      <div className="skeleton h-8 w-1/2" />
      <div className="skeleton h-4 w-2/3" />
    </div>
  );
}

export function SkeletonList({ count = 3 }) {
  return (
    <div className="space-y-4">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="card p-4 flex items-center gap-4">
          <div className="skeleton w-12 h-12 rounded-xl" />
          <div className="flex-1 space-y-2">
            <div className="skeleton h-4 w-1/3" />
            <div className="skeleton h-3 w-1/2" />
          </div>
        </div>
      ))}
    </div>
  );
}

// Tabs
export function Tabs({ tabs, activeTab, onChange }) {
  return (
    <div className="flex gap-1 p-1 bg-slate rounded-xl">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onChange(tab.id)}
          className={`flex-1 px-4 py-2 rounded-lg font-medium text-sm transition-all
                    ${activeTab === tab.id
              ? 'bg-accent text-white shadow-lg'
              : 'text-silver hover:text-pearl'
            }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}

// Progress Bar
export function ProgressBar({ value = 0, color = 'primary', showLabel = false, className = '' }) {
  const colors = {
    primary: 'bg-accent',
    success: 'bg-success',
    warning: 'bg-warning',
    error: 'bg-error',
    info: 'bg-blue-500',
    secondary: 'bg-purple-500'
  };

  return (
    <div className={`w-full ${className}`}>
      <div className="h-2 bg-slate rounded-full overflow-hidden">
        <div
          className={`h-full ${colors[color] || colors.primary} transition-all duration-300`}
          style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
        />
      </div>
      {showLabel && (
        <p className="text-xs text-silver mt-1 text-right">{Math.round(value)}%</p>
      )}
    </div>
  );
}
