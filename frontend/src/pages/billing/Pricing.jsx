import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Check, X, Zap, Star, Crown, Building2, Sparkles } from 'lucide-react';
import { billingApi } from '../../services/api';
import { useAuth } from '../../contexts/AuthContext';
import { Card, Badge, LoadingState, Spinner } from '../../components/ui';
import toast from 'react-hot-toast';

const tierIcons = {
  free: Zap,
  creator: Star,
  pro: Crown,
  agency: Building2
};

const tierColors = {
  free: 'from-gray-500 to-gray-600',
  creator: 'from-blue-500 to-blue-600',
  pro: 'from-accent to-accent-dark',
  agency: 'from-purple-500 to-purple-600'
};

export default function Pricing() {
  const navigate = useNavigate();
  const { user, isAuthenticated } = useAuth();
  const [plans, setPlans] = useState([]);
  const [currentTier, setCurrentTier] = useState('free');
  const [loading, setLoading] = useState(true);
  const [checkoutLoading, setCheckoutLoading] = useState(null);
  const [billingInterval, setBillingInterval] = useState('monthly');

  useEffect(() => {
    fetchPlans();
    if (isAuthenticated) fetchSubscription();
  }, [isAuthenticated]);

  const fetchPlans = async () => {
    try {
      const res = await billingApi.listPlans();
      setPlans(res.data.plans);
    } catch (err) {
      toast.error('Failed to load plans');
    }
    setLoading(false);
  };

  const fetchSubscription = async () => {
    try {
      const res = await billingApi.getSubscription();
      setCurrentTier(res.data.tier);
    } catch (err) {}
  };

  const handleSelectPlan = async (tier) => {
    if (!isAuthenticated) {
      navigate('/register', { state: { from: '/pricing', selectedPlan: tier } });
      return;
    }

    if (tier === 'free') {
      toast.error('You are already on the free plan');
      return;
    }

    if (tier === currentTier) {
      toast.error('You are already on this plan');
      return;
    }

    setCheckoutLoading(tier);
    try {
      const res = await billingApi.createCheckout({
        tier,
        success_url: `${window.location.origin}/billing?success=true`,
        cancel_url: `${window.location.origin}/pricing`
      });
      window.location.href = res.data.checkout_url;
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to start checkout');
      setCheckoutLoading(null);
    }
  };

  if (loading) return <LoadingState message="Loading plans..." />;

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-4xl font-display font-bold text-pearl mb-4">
          Simple, Transparent Pricing
        </h1>
        <p className="text-xl text-silver max-w-2xl mx-auto">
          Choose the plan that fits your needs. Upgrade or downgrade anytime.
        </p>
      </div>

      {/* Billing Toggle */}
      <div className="flex justify-center">
        <div className="bg-slate rounded-xl p-1 flex gap-1">
          <button
            onClick={() => setBillingInterval('monthly')}
            className={`px-6 py-2 rounded-lg font-medium transition-all ${
              billingInterval === 'monthly' ? 'bg-accent text-white' : 'text-silver hover:text-pearl'
            }`}
          >
            Monthly
          </button>
          <button
            onClick={() => setBillingInterval('yearly')}
            className={`px-6 py-2 rounded-lg font-medium transition-all flex items-center gap-2 ${
              billingInterval === 'yearly' ? 'bg-accent text-white' : 'text-silver hover:text-pearl'
            }`}
          >
            Yearly <Badge variant="success" className="text-xs">Save 20%</Badge>
          </button>
        </div>
      </div>

      {/* Plans Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {plans.map((plan) => {
          const Icon = tierIcons[plan.tier] || Zap;
          const isCurrentPlan = plan.tier === currentTier;
          const isPopular = plan.tier === 'pro';
          const price = billingInterval === 'yearly' 
            ? Math.round(plan.price_monthly * 12 * 0.8) 
            : plan.price_monthly;
          const monthlyPrice = billingInterval === 'yearly'
            ? Math.round(plan.price_monthly * 0.8)
            : plan.price_monthly;

          return (
            <Card
              key={plan.tier}
              className={`p-6 relative ${isPopular ? 'border-accent ring-2 ring-accent/20' : ''} ${
                isCurrentPlan ? 'border-success' : ''
              }`}
            >
              {isPopular && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <Badge variant="primary" className="bg-accent">Most Popular</Badge>
                </div>
              )}
              {isCurrentPlan && (
                <div className="absolute -top-3 right-4">
                  <Badge variant="success">Current Plan</Badge>
                </div>
              )}

              {/* Plan Header */}
              <div className="text-center mb-6">
                <div className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${tierColors[plan.tier]} flex items-center justify-center mx-auto mb-4`}>
                  <Icon className="w-7 h-7 text-white" />
                </div>
                <h3 className="text-xl font-display font-bold text-pearl">{plan.name}</h3>
                <div className="mt-4">
                  <span className="text-4xl font-bold text-pearl">${monthlyPrice}</span>
                  <span className="text-silver">/mo</span>
                </div>
                {billingInterval === 'yearly' && plan.price_monthly > 0 && (
                  <p className="text-sm text-silver mt-1">
                    ${price}/year (billed annually)
                  </p>
                )}
              </div>

              {/* Features */}
              <ul className="space-y-3 mb-6">
                <li className="flex items-center gap-3 text-sm">
                  <Check className="w-5 h-5 text-success flex-shrink-0" />
                  <span className="text-pearl">
                    <strong>{plan.features.generations_per_month.toLocaleString()}</strong> generations/mo
                  </span>
                </li>
                <li className="flex items-center gap-3 text-sm">
                  <Check className="w-5 h-5 text-success flex-shrink-0" />
                  <span className="text-pearl">
                    <strong>{plan.features.brands}</strong> brand{plan.features.brands !== 1 ? 's' : ''}
                  </span>
                </li>
                <li className="flex items-center gap-3 text-sm">
                  {plan.features.lora_models > 0 ? (
                    <>
                      <Check className="w-5 h-5 text-success flex-shrink-0" />
                      <span className="text-pearl">
                        <strong>{plan.features.lora_models}</strong> LoRA avatar{plan.features.lora_models !== 1 ? 's' : ''}
                      </span>
                    </>
                  ) : (
                    <>
                      <X className="w-5 h-5 text-silver/50 flex-shrink-0" />
                      <span className="text-silver">LoRA avatars</span>
                    </>
                  )}
                </li>
                <li className="flex items-center gap-3 text-sm">
                  {plan.features.social_accounts > 0 ? (
                    <>
                      <Check className="w-5 h-5 text-success flex-shrink-0" />
                      <span className="text-pearl">
                        <strong>{plan.features.social_accounts}</strong> social account{plan.features.social_accounts !== 1 ? 's' : ''}
                      </span>
                    </>
                  ) : (
                    <>
                      <X className="w-5 h-5 text-silver/50 flex-shrink-0" />
                      <span className="text-silver">Social accounts</span>
                    </>
                  )}
                </li>
                <li className="flex items-center gap-3 text-sm">
                  {plan.features.scheduled_posts > 0 || plan.features.scheduled_posts === -1 ? (
                    <>
                      <Check className="w-5 h-5 text-success flex-shrink-0" />
                      <span className="text-pearl">
                        {plan.features.scheduled_posts === -1 ? 'Unlimited' : plan.features.scheduled_posts} scheduled posts
                      </span>
                    </>
                  ) : (
                    <>
                      <X className="w-5 h-5 text-silver/50 flex-shrink-0" />
                      <span className="text-silver">Scheduled posts</span>
                    </>
                  )}
                </li>
                <li className="flex items-center gap-3 text-sm">
                  {plan.features.api_access ? (
                    <>
                      <Check className="w-5 h-5 text-success flex-shrink-0" />
                      <span className="text-pearl">API access</span>
                    </>
                  ) : (
                    <>
                      <X className="w-5 h-5 text-silver/50 flex-shrink-0" />
                      <span className="text-silver">API access</span>
                    </>
                  )}
                </li>
                <li className="flex items-center gap-3 text-sm">
                  {plan.features.priority_support ? (
                    <>
                      <Check className="w-5 h-5 text-success flex-shrink-0" />
                      <span className="text-pearl">Priority support</span>
                    </>
                  ) : (
                    <>
                      <X className="w-5 h-5 text-silver/50 flex-shrink-0" />
                      <span className="text-silver">Priority support</span>
                    </>
                  )}
                </li>
              </ul>

              {/* CTA Button */}
              <button
                onClick={() => handleSelectPlan(plan.tier)}
                disabled={isCurrentPlan || checkoutLoading === plan.tier}
                className={`w-full py-3 rounded-xl font-medium transition-all ${
                  isCurrentPlan
                    ? 'bg-slate text-silver cursor-not-allowed'
                    : isPopular
                    ? 'bg-accent hover:bg-accent-dark text-white shadow-glow'
                    : 'bg-slate hover:bg-graphite text-pearl'
                }`}
              >
                {checkoutLoading === plan.tier ? (
                  <Spinner size="sm" />
                ) : isCurrentPlan ? (
                  'Current Plan'
                ) : plan.tier === 'free' ? (
                  'Get Started'
                ) : (
                  `Upgrade to ${plan.name}`
                )}
              </button>
            </Card>
          );
        })}
      </div>

      {/* FAQ Section */}
      <div className="mt-16">
        <h2 className="text-2xl font-display font-bold text-pearl text-center mb-8">
          Frequently Asked Questions
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-4xl mx-auto">
          {[
            {
              q: 'Can I cancel anytime?',
              a: 'Yes! You can cancel your subscription at any time. You\'ll continue to have access until the end of your billing period.'
            },
            {
              q: 'What happens if I exceed my limits?',
              a: 'You\'ll receive a notification when you\'re close to your limits. You can upgrade your plan at any time to get more.'
            },
            {
              q: 'Do you offer refunds?',
              a: 'We offer a 14-day money-back guarantee on all paid plans. No questions asked.'
            },
            {
              q: 'Can I change plans later?',
              a: 'Absolutely! You can upgrade or downgrade your plan at any time. Changes take effect immediately with prorated billing.'
            }
          ].map((faq, i) => (
            <Card key={i} className="p-5">
              <h3 className="font-semibold text-pearl mb-2">{faq.q}</h3>
              <p className="text-silver text-sm">{faq.a}</p>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
