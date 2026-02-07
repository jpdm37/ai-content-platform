import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { AuthProvider } from './contexts/AuthContext';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';

// Pages
import Dashboard from './pages/Dashboard';
import Brands from './pages/Brands';
import BrandForm from './pages/BrandForm';
import Categories from './pages/Categories';
import Trends from './pages/Trends';
import Generate from './pages/Generate';
import Content from './pages/Content';
import Settings from './pages/Settings';

// Auth Pages
import Login from './pages/auth/Login';
import Register from './pages/auth/Register';
import ForgotPassword from './pages/auth/ForgotPassword';
import ResetPassword from './pages/auth/ResetPassword';
import VerifyEmail from './pages/auth/VerifyEmail';
import OAuthCallback from './pages/auth/OAuthCallback';

// LoRA Pages
import LoraModels from './pages/lora/LoraModels';
import LoraCreate from './pages/lora/LoraCreate';
import LoraDetail from './pages/lora/LoraDetail';

// Billing Pages
import Pricing from './pages/billing/Pricing';
import Billing from './pages/billing/Billing';

// Social Pages
import SocialAccounts from './pages/social/SocialAccounts';
import SocialSchedule from './pages/social/SocialSchedule';
import SocialCallback from './pages/social/SocialCallback';

// Video Pages
import VideoCreate from './pages/video/VideoCreate';
import { VideoList, VideoDetail } from './pages/video/VideoList';

// Studio Pages
import StudioProjects from './pages/studio/StudioProjects';
import StudioCreate from './pages/studio/StudioCreate';
import StudioDetail from './pages/studio/StudioDetail';

// Brand Voice Pages
import BrandVoice from './pages/brandvoice/BrandVoice';

// Analytics Pages
import AnalyticsDashboard from './pages/analytics/AnalyticsDashboard';

// Cost Dashboard
import CostDashboard from './pages/costs/CostDashboard';

// Assistant Pages
import AssistantChat from './pages/assistant/AssistantChat';

// Admin Pages
import AdminLogin from './pages/admin/AdminLogin';
import AdminDashboard from './pages/admin/AdminDashboard';

// Onboarding
import OnboardingWizard from './pages/onboarding/OnboardingWizard';

// Templates
import TemplatesLibrary from './pages/templates/TemplatesLibrary';

// Calendar
import ContentCalendar from './pages/calendar/ContentCalendar';

// A/B Testing
import ABTestingDashboard, { ABTestDetail } from './pages/abtesting/ABTesting';

// Performance Tracking
import PerformanceDashboard from './pages/performance/PerformanceDashboard';

export default function App() {
  return (
    <Router>
      <AuthProvider>
        <Toaster
          position="top-right"
          toastOptions={{
            duration: 3000,
            style: { background: '#1e1e26', color: '#e8e8ef', border: '1px solid #2a2a35' },
            success: { iconTheme: { primary: '#10b981', secondary: '#1e1e26' } },
            error: { iconTheme: { primary: '#ef4444', secondary: '#1e1e26' } },
          }}
        />
        <Routes>
          {/* Auth Routes (public) */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPassword />} />
          <Route path="/verify-email" element={<VerifyEmail />} />
          <Route path="/auth/callback/:provider" element={<OAuthCallback />} />

          {/* Onboarding (protected but no layout) */}
          <Route path="/onboarding" element={<ProtectedRoute><OnboardingWizard /></ProtectedRoute>} />

          {/* Protected Routes */}
          <Route path="/" element={<ProtectedRoute><Layout><Dashboard /></Layout></ProtectedRoute>} />
          <Route path="/brands" element={<ProtectedRoute><Layout><Brands /></Layout></ProtectedRoute>} />
          <Route path="/brands/new" element={<ProtectedRoute requireVerified><Layout><BrandForm /></Layout></ProtectedRoute>} />
          <Route path="/brands/:id" element={<ProtectedRoute><Layout><BrandForm /></Layout></ProtectedRoute>} />
          <Route path="/brands/:id/edit" element={<ProtectedRoute><Layout><BrandForm /></Layout></ProtectedRoute>} />
          <Route path="/categories" element={<ProtectedRoute><Layout><Categories /></Layout></ProtectedRoute>} />
          <Route path="/trends" element={<ProtectedRoute><Layout><Trends /></Layout></ProtectedRoute>} />
          <Route path="/generate" element={<ProtectedRoute requireVerified><Layout><Generate /></Layout></ProtectedRoute>} />
          <Route path="/content" element={<ProtectedRoute><Layout><Content /></Layout></ProtectedRoute>} />
          <Route path="/settings" element={<ProtectedRoute><Layout><Settings /></Layout></ProtectedRoute>} />
          
          {/* LoRA Training Routes */}
          <Route path="/lora" element={<ProtectedRoute><Layout><LoraModels /></Layout></ProtectedRoute>} />
          <Route path="/lora/new" element={<ProtectedRoute requireVerified><Layout><LoraCreate /></Layout></ProtectedRoute>} />
          <Route path="/lora/:id" element={<ProtectedRoute><Layout><LoraDetail /></Layout></ProtectedRoute>} />
          
          {/* Billing Routes */}
          <Route path="/pricing" element={<Layout><Pricing /></Layout>} />
          <Route path="/billing" element={<ProtectedRoute><Layout><Billing /></Layout></ProtectedRoute>} />
          
          {/* Social Media Routes */}
          <Route path="/social/accounts" element={<ProtectedRoute><Layout><SocialAccounts /></Layout></ProtectedRoute>} />
          <Route path="/social/schedule" element={<ProtectedRoute><Layout><SocialSchedule /></Layout></ProtectedRoute>} />
          <Route path="/social/callback/:platform" element={<SocialCallback />} />
          
          {/* Video Generation Routes */}
          <Route path="/video" element={<ProtectedRoute><Layout><VideoList /></Layout></ProtectedRoute>} />
          <Route path="/video/create" element={<ProtectedRoute requireVerified><Layout><VideoCreate /></Layout></ProtectedRoute>} />
          <Route path="/video/:id" element={<ProtectedRoute><Layout><VideoDetail /></Layout></ProtectedRoute>} />
          
          {/* Content Studio Routes */}
          <Route path="/studio" element={<ProtectedRoute><Layout><StudioProjects /></Layout></ProtectedRoute>} />
          <Route path="/studio/create" element={<ProtectedRoute requireVerified><Layout><StudioCreate /></Layout></ProtectedRoute>} />
          <Route path="/studio/:id" element={<ProtectedRoute><Layout><StudioDetail /></Layout></ProtectedRoute>} />
          
          {/* Templates Library */}
          <Route path="/templates" element={<ProtectedRoute><Layout><TemplatesLibrary /></Layout></ProtectedRoute>} />
          
          {/* Content Calendar */}
          <Route path="/calendar" element={<ProtectedRoute><Layout><ContentCalendar /></Layout></ProtectedRoute>} />
          
          {/* A/B Testing */}
          <Route path="/ab-testing" element={<ProtectedRoute><Layout><ABTestingDashboard /></Layout></ProtectedRoute>} />
          <Route path="/ab-testing/:id" element={<ProtectedRoute><Layout><ABTestDetail /></Layout></ProtectedRoute>} />
          
          {/* Performance Tracking */}
          <Route path="/performance" element={<ProtectedRoute><Layout><PerformanceDashboard /></Layout></ProtectedRoute>} />
          
          {/* Brand Voice Routes */}
          <Route path="/brands/:brandId/voice" element={<ProtectedRoute><Layout><BrandVoice /></Layout></ProtectedRoute>} />
          
          {/* Analytics Routes */}
          <Route path="/analytics" element={<ProtectedRoute><Layout><AnalyticsDashboard /></Layout></ProtectedRoute>} />
          
          {/* Cost Dashboard */}
          <Route path="/costs" element={<ProtectedRoute><Layout><CostDashboard /></Layout></ProtectedRoute>} />
          
          {/* AI Assistant Routes */}
          <Route path="/assistant" element={<ProtectedRoute><Layout><AssistantChat /></Layout></ProtectedRoute>} />
          
          {/* Admin Routes (separate auth system) */}
          <Route path="/admin/login" element={<AdminLogin />} />
          <Route path="/admin/dashboard" element={<AdminDashboard />} />
          <Route path="/admin" element={<AdminDashboard />} />
        </Routes>
      </AuthProvider>
    </Router>
  );
}
