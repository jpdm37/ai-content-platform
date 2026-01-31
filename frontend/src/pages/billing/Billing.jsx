import { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { CreditCard, Download, ExternalLink, AlertTriangle, Check, Zap, TrendingUp, Calendar, Image as ImageIcon } from 'lucide-react';
import { billingApi } from '../../services/api';
import { Card, Badge, LoadingState, Spinner, ProgressBar } from '../../components/ui';
import toast from 'react-hot-toast';

export default function Billing() {
  const [searchParams] = useSearchParams();
  const [subscription, setSubscription] = useState(null);
  const [usage, setUsage] = useState(null);
  const [payments, setPayments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [portalLoading, setPortalLoading] = useState(false);

  useEffect(() => {
    // Check for success redirect
    if (searchParams.get('success') === 'true') {
      toast.success('Subscription activated! Welcome to your new plan.');
    }
    fetchData();
  }, [searchParams]);

  const fetchData = async () => {
    try {
      const [subRes, usageRes, paymentsRes] = await Promise.all([
        billingApi.getSubscription(),
        billingApi.getUsage(),
        billingApi.getPayments({ limit: 5 })
      ]);
      setSubscription(subRes.data);
      setUsage(usageRes.data);
      setPayments(paymentsRes.data.payments);
    } catch (err) {
      toast.error('Failed to load billing info');
    }
    setLoading(false);
  };

  const openBillingPortal = async () => {
    setPortalLoading(true);
    try {
      const res = await billingApi.createPortal({
        return_url: window.location.href
      });
      window.location.href = res.data.portal_url;
    } catch (err) {
      toast.error('Failed to open billing portal');
      setPortalLoading(false);
    }
  };

  const handleCancel = async () => {
    if (!confirm('Are you sure you want to cancel? You\'ll keep access until the end of your billing period.')) return;
    
    try {
      await billingApi.cancelSubscription(true);
      toast.success('Subscription will cancel at end of billing period');
      fetchData();
    } catch (err) {
      toast.error('Failed to cancel subscription');
    }
  };

  const handleReactivate = async () => {
    try {
      await billingApi.reactivate();
      toast.success('Subscription reactivated!');
      fetchData();
    } catch (err) {
      toast.error('Failed to reactivate subscription');
    }
  };

  if (loading) return <LoadingState message="Loading billing..." />;

  const tierColors = {
    free: 'text-gray-400',
    creator: 'text-blue-400',
    pro: 'text-accent',
    agency: 'text-purple-400'
  };

  const usagePercent = (used, limit) => limit > 0 ? Math.min(100, (used / limit) * 100) : 0;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="page-title flex items-center gap-3">
          <CreditCard className="w-8 h-8 text-accent" />
          Billing & Subscription
        </h1>
        <p className="text-silver mt-1">Manage your subscription and view usage</p>
      </div>

      {/* Current Plan Card */}
      <Card className="p-6">
        <div className="flex items-start justify-between mb-6">
          <div>
            <p className="text-silver text-sm mb-1">Current Plan</p>
            <h2 className={`text-3xl font-display font-bold ${tierColors[subscription?.tier] || 'text-pearl'}`}>
              {subscription?.plan?.features ? subscription.tier.charAt(0).toUpperCase() + subscription.tier.slice(1) : 'Free'}
            </h2>
            {subscription?.cancel_at_period_end && (
              <Badge variant="warning" className="mt-2">Cancels at period end</Badge>
            )}
          </div>
          <div className="text-right">
            {subscription?.tier !== 'free' && (
              <>
                <p className="text-silver text-sm">Next billing date</p>
                <p className="text-pearl font-medium">
                  {subscription?.current_period_end 
                    ? new Date(subscription.current_period_end).toLocaleDateString()
                    : '-'}
                </p>
              </>
            )}
          </div>
        </div>

        <div className="flex flex-wrap gap-3">
          <Link to="/pricing" className="btn-primary">
            {subscription?.tier === 'free' ? 'Upgrade Plan' : 'Change Plan'}
          </Link>
          {subscription?.tier !== 'free' && (
            <>
              <button onClick={openBillingPortal} disabled={portalLoading} className="btn-secondary flex items-center gap-2">
                {portalLoading ? <Spinner size="sm" /> : <ExternalLink className="w-4 h-4" />}
                Manage Payment
              </button>
              {subscription?.cancel_at_period_end ? (
                <button onClick={handleReactivate} className="btn-secondary text-success">
                  Reactivate
                </button>
              ) : (
                <button onClick={handleCancel} className="btn-secondary text-error">
                  Cancel Plan
                </button>
              )}
            </>
          )}
        </div>
      </Card>

      {/* Usage Overview */}
      <Card className="p-6">
        <h3 className="section-title mb-6">Usage This Period</h3>
        
        <div className="space-y-6">
          {/* Generations */}
          <div>
            <div className="flex justify-between mb-2">
              <div className="flex items-center gap-2">
                <ImageIcon className="w-5 h-5 text-accent" />
                <span className="text-pearl font-medium">Generations</span>
              </div>
              <span className="text-silver">
                {usage?.generations_used || 0} / {usage?.generations_limit || 0}
              </span>
            </div>
            <ProgressBar 
              value={usagePercent(usage?.generations_used, usage?.generations_limit)} 
              color={usagePercent(usage?.generations_used, usage?.generations_limit) > 90 ? 'error' : 'primary'}
            />
            {usage?.generations_remaining <= 10 && usage?.generations_limit > 0 && (
              <p className="text-warning text-sm mt-1 flex items-center gap-1">
                <AlertTriangle className="w-4 h-4" />
                Only {usage?.generations_remaining} generations remaining
              </p>
            )}
          </div>

          {/* Brands */}
          <div>
            <div className="flex justify-between mb-2">
              <div className="flex items-center gap-2">
                <Zap className="w-5 h-5 text-blue-400" />
                <span className="text-pearl font-medium">Brands</span>
              </div>
              <span className="text-silver">
                {usage?.brands_used || 0} / {usage?.brands_limit || 0}
              </span>
            </div>
            <ProgressBar 
              value={usagePercent(usage?.brands_used, usage?.brands_limit)} 
              color="info"
            />
          </div>

          {/* LoRA Models */}
          <div>
            <div className="flex justify-between mb-2">
              <div className="flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-purple-400" />
                <span className="text-pearl font-medium">LoRA Avatars</span>
              </div>
              <span className="text-silver">
                {usage?.lora_models_used || 0} / {usage?.lora_models_limit || 0}
              </span>
            </div>
            <ProgressBar 
              value={usagePercent(usage?.lora_models_used, usage?.lora_models_limit)} 
              color="secondary"
            />
          </div>

          {/* Social Accounts */}
          <div>
            <div className="flex justify-between mb-2">
              <div className="flex items-center gap-2">
                <Calendar className="w-5 h-5 text-green-400" />
                <span className="text-pearl font-medium">Social Accounts</span>
              </div>
              <span className="text-silver">
                {usage?.social_accounts_used || 0} / {usage?.social_accounts_limit || 0}
              </span>
            </div>
            <ProgressBar 
              value={usagePercent(usage?.social_accounts_used, usage?.social_accounts_limit)} 
              color="success"
            />
          </div>
        </div>

        {usage?.reset_date && (
          <p className="text-silver text-sm mt-6">
            Usage resets on {new Date(usage.reset_date).toLocaleDateString()}
          </p>
        )}
      </Card>

      {/* Payment History */}
      {payments.length > 0 && (
        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="section-title">Recent Payments</h3>
            <button onClick={openBillingPortal} className="text-accent text-sm hover:text-accent-light">
              View all invoices
            </button>
          </div>

          <div className="space-y-3">
            {payments.map((payment) => (
              <div key={payment.id} className="flex items-center justify-between py-3 border-b border-graphite last:border-0">
                <div className="flex items-center gap-3">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                    payment.status === 'succeeded' ? 'bg-success/20' : 'bg-error/20'
                  }`}>
                    {payment.status === 'succeeded' ? (
                      <Check className="w-4 h-4 text-success" />
                    ) : (
                      <AlertTriangle className="w-4 h-4 text-error" />
                    )}
                  </div>
                  <div>
                    <p className="text-pearl font-medium">
                      ${(payment.amount / 100).toFixed(2)} {payment.currency.toUpperCase()}
                    </p>
                    <p className="text-silver text-sm">
                      {new Date(payment.created_at).toLocaleDateString()}
                    </p>
                  </div>
                </div>
                <Badge variant={payment.status === 'succeeded' ? 'success' : 'error'}>
                  {payment.status}
                </Badge>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Plan Features */}
      {subscription?.plan && (
        <Card className="p-6">
          <h3 className="section-title mb-4">Your Plan Includes</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {subscription.plan.features.map((feature, i) => (
              <div key={i} className="flex items-center gap-2">
                <Check className="w-5 h-5 text-success flex-shrink-0" />
                <span className="text-silver text-sm">{feature}</span>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
