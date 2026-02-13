/**
 * API Service - Complete with Avatar endpoints for onboarding
 * 
 * This file should replace: frontend/src/services/api.js
 */
import axios from 'axios';

// Use environment variable or default to the deployed backend
const API_BASE_URL = import.meta.env.VITE_API_URL || 'https://ai-content-platform-kpc2.onrender.com/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for authentication
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    // Handle 401 Unauthorized - try to refresh token
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      const refreshToken = localStorage.getItem('refreshToken');
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken
          });
          
          const { access_token, refresh_token: newRefresh } = response.data;
          localStorage.setItem('token', access_token);
          localStorage.setItem('refreshToken', newRefresh);
          
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return api(originalRequest);
        } catch (refreshError) {
          // Refresh failed, redirect to login
          localStorage.removeItem('token');
          localStorage.removeItem('refreshToken');
          window.location.href = '/login';
          return Promise.reject(refreshError);
        }
      }
    }
    
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// ============ Authentication API ============
export const authApi = {
  register: (data) => api.post('/auth/register', data),
  login: (data) => api.post('/auth/login', data),
  logout: (data) => api.post('/auth/logout', data),
  refresh: (data) => api.post('/auth/refresh', data),
  
  // Profile
  getProfile: () => api.get('/auth/me'),
  updateProfile: (data) => api.put('/auth/me', data),
  updatePassword: (data) => api.put('/auth/me/password', data),
  updateApiKeys: (data) => api.put('/auth/me/api-keys', data),
  
  // Email verification
  sendVerification: (data) => api.post('/auth/verify-email/send', data),
  confirmVerification: (data) => api.post('/auth/verify-email/confirm', data),
  
  // Password reset
  requestReset: (data) => api.post('/auth/password-reset/request', data),
  confirmReset: (data) => api.post('/auth/password-reset/confirm', data),
  
  // OAuth
  getOAuthProviders: () => api.get('/auth/oauth/providers'),
  initiateOAuth: (provider) => api.get(`/auth/oauth/${provider}`),
  handleOAuthCallback: (provider, code) => api.post(`/auth/oauth/${provider}/callback`, null, { params: { code } }),
  
  // Status
  getStatus: () => api.get('/auth/status'),
};

// ============ Avatar API (for onboarding) ============
export const avatarApi = {
  // Generate concepts from description
  generateConcepts: (config) => api.post('/avatar/generate-concepts', config),
  
  // Generate training images from selected concept
  generateTrainingImages: (data) => api.post('/avatar/generate-training-images', data),
  
  // Create LoRA model from generated images
  createFromGenerated: (data) => api.post('/avatar/create-from-generated', data),
  
  // Upload existing images for training
  uploadImages: (brandId, files) => {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));
    return api.post(`/avatar/upload-images?brand_id=${brandId}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  },
  
  // Get avatar training status
  getStatus: (avatarId) => api.get(`/avatar/status/${avatarId}`),
  
  // List all user avatars
  list: () => api.get('/avatar/list'),
  
  // Delete avatar
  delete: (avatarId) => api.delete(`/avatar/${avatarId}`),
};

// ============ Brands API ============
export const brandsApi = {
  getAll: () => api.get('/brands'),
  getById: (id) => api.get(`/brands/${id}`),
  create: (data) => api.post('/brands', data),
  update: (id, data) => api.put(`/brands/${id}`, data),
  delete: (id) => api.delete(`/brands/${id}`),
  getCategories: (id) => api.get(`/brands/${id}/categories`),
  addCategory: (brandId, categoryId) => api.post(`/brands/${brandId}/categories/${categoryId}`),
  removeCategory: (brandId, categoryId) => api.delete(`/brands/${brandId}/categories/${categoryId}`),
};

// ============ Categories API ============
export const categoriesApi = {
  getAll: () => api.get('/categories'),
  getById: (id) => api.get(`/categories/${id}`),
  create: (data) => api.post('/categories', data),
  delete: (id) => api.delete(`/categories/${id}`),
  seed: () => api.post('/categories/seed'),
  getByName: (name) => api.get(`/categories/by-name/${name}`),
};

// ============ Trends API ============
export const trendsApi = {
  getAll: (params) => api.get('/trends', { params }),
  getTop: (params) => api.get('/trends/top', { params }),
  getRecent: (params) => api.get('/trends/recent', { params }),
  getById: (id) => api.get(`/trends/${id}`),
  getByCategory: (categoryId, limit = 20) => api.get(`/trends/category/${categoryId}`, { params: { limit } }),
  scrape: (data) => api.post('/trends/scrape', data),
  seed: () => api.post('/trends/seed'),
  cleanupExpired: () => api.delete('/trends/expired'),
};

// ============ Content Generation API ============
export const generateApi = {
  avatar: (data) => api.post('/generate/avatar', data),
  content: (data) => api.post('/generate/content', data),
  getAll: (params) => api.get('/generate/content', { params }),
  getById: (id) => api.get(`/generate/content/${id}`),
  delete: (id) => api.delete(`/generate/content/${id}`),
  getByBrand: (brandId, limit = 20) => api.get(`/generate/brand/${brandId}/content`, { params: { limit } }),
};

// ============ Social Accounts API ============
export const socialApi = {
  getAll: () => api.get('/social/accounts'),
  getById: (id) => api.get(`/social/accounts/${id}`),
  connect: (platform, data) => api.post(`/social/connect/${platform}`, data),
  disconnect: (id) => api.delete(`/social/accounts/${id}`),
  getCallback: (platform, code) => api.get(`/social/callback/${platform}`, { params: { code } }),
  
  // Posting
  post: (accountId, data) => api.post(`/social/accounts/${accountId}/post`, data),
  schedule: (data) => api.post('/social/schedule', data),
  
  // Scheduled posts
  getScheduled: (params) => api.get('/social/scheduled', { params }),
  cancelScheduled: (id) => api.delete(`/social/scheduled/${id}`),
};

// ============ LoRA / Avatar Training API ============
export const loraApi = {
  // List user's LoRA models
  list: () => api.get('/lora/models'),
  getById: (id) => api.get(`/lora/models/${id}`),
  
  // Create and train
  create: (data) => api.post('/lora/models', data),
  addImages: (modelId, images) => api.post(`/lora/models/${modelId}/images`, images),
  startTraining: (modelId, config) => api.post(`/lora/models/${modelId}/train`, config),
  
  // Training status
  getProgress: (modelId) => api.get(`/lora/models/${modelId}/progress`),
  cancelTraining: (modelId) => api.post(`/lora/models/${modelId}/cancel`),
  
  // Generation with trained model
  generate: (modelId, data) => api.post(`/lora/models/${modelId}/generate`, data),
  getSamples: (modelId) => api.get(`/lora/models/${modelId}/samples`),
  
  // Delete
  delete: (modelId) => api.delete(`/lora/models/${modelId}`),
};

// ============ Studio / Projects API ============
export const studioApi = {
  // Projects
  getProjects: () => api.get('/studio/projects'),
  getProject: (id) => api.get(`/studio/projects/${id}`),
  createProject: (data) => api.post('/studio/projects', data),
  updateProject: (id, data) => api.put(`/studio/projects/${id}`, data),
  deleteProject: (id) => api.delete(`/studio/projects/${id}`),
  
  // Assets
  getAssets: (projectId) => api.get(`/studio/projects/${projectId}/assets`),
  uploadAsset: (projectId, file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post(`/studio/projects/${projectId}/assets`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  },
  deleteAsset: (projectId, assetId) => api.delete(`/studio/projects/${projectId}/assets/${assetId}`),
};

// ============ Billing API ============
export const billingApi = {
  // Subscription
  getSubscription: () => api.get('/billing/subscription'),
  getPlans: () => api.get('/billing/plans'),
  createCheckout: (priceId) => api.post('/billing/checkout', { price_id: priceId }),
  manageSubscription: () => api.post('/billing/portal'),
  
  // Usage
  getUsage: () => api.get('/billing/usage'),
  getDashboard: () => api.get('/billing/dashboard'),
  
  // Limits
  checkLimit: (type) => api.get(`/billing/check-limit/${type}`),
};

// ============ Onboarding API ============
export const onboardingApi = {
  getStatus: () => api.get('/onboarding/status'),
  getProgress: () => api.get('/onboarding/progress'),
  
  // Steps
  completeStep: (step, data) => api.post(`/onboarding/step/${step}`, data),
  skipStep: (step) => api.post(`/onboarding/skip/${step}`),
  
  // Complete onboarding
  complete: () => api.post('/onboarding/complete'),
};

// ============ Status API ============
export const statusApi = {
  health: () => api.get('/health'),
  status: () => api.get('/status'),
};

// ============ Calendar API ============
export const calendarApi = {
  getEvents: (params) => api.get('/calendar/events', { params }),
  createEvent: (data) => api.post('/calendar/events', data),
  updateEvent: (id, data) => api.put(`/calendar/events/${id}`, data),
  deleteEvent: (id) => api.delete(`/calendar/events/${id}`),
};

// ============ Analytics API ============
export const analyticsApi = {
  getOverview: (params) => api.get('/analytics/overview', { params }),
  getContentPerformance: (params) => api.get('/analytics/content', { params }),
  getSocialMetrics: (params) => api.get('/analytics/social', { params }),
  getEngagement: (params) => api.get('/analytics/engagement', { params }),
};

export default api;
