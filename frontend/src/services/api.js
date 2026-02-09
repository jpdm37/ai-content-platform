import axios from 'axios';

// Use environment variable or default to relative path for production
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for debugging
api.interceptors.request.use((config) => {
  console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
  return config;
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// ============ Brands API ============
export const brandsApi = {
  list: () => api.get('/brands/'),
  getAll: () => api.get('/brands/'),
  get: (id) => api.get(`/brands/${id}`),
  getById: (id) => api.get(`/brands/${id}`),
  create: (data) => api.post('/brands/', data),
  update: (id, data) => api.put(`/brands/${id}`, data),
  delete: (id) => api.delete(`/brands/${id}`),
  getCategories: (id) => api.get(`/brands/${id}/categories`),
  addCategory: (brandId, categoryId) => api.post(`/brands/${brandId}/categories/${categoryId}`),
  removeCategory: (brandId, categoryId) => api.delete(`/brands/${brandId}/categories/${categoryId}`),
};

// ============ Categories API ============
export const categoriesApi = {
  getAll: () => api.get('/categories/'),
  getById: (id) => api.get(`/categories/${id}`),
  create: (data) => api.post('/categories/', data),
  delete: (id) => api.delete(`/categories/${id}`),
  seed: () => api.post('/categories/seed'),
};

// ============ Trends API ============
export const trendsApi = {
  getAll: (params) => api.get('/trends/', { params }),
  getTop: (params) => api.get('/trends/top', { params }),
  getRecent: (params) => api.get('/trends/recent', { params }),
  getById: (id) => api.get(`/trends/${id}`),
  getByCategory: (categoryId, limit = 20) => api.get(`/trends/category/${categoryId}`, { params: { limit } }),
  scrape: (data) => api.post('/trends/scrape', data),
  cleanupExpired: () => api.delete('/trends/expired'),
};

// ============ Generation API ============
export const generateApi = {
  avatar: (data) => api.post('/generate/avatar', data),
  content: (data) => api.post('/generate/content/', data),
  getAll: (params) => api.get('/generate/content/', { params }),
  getById: (id) => api.get(`/generate/content/${id}`),
  delete: (id) => api.delete(`/generate/content/${id}`),
  getByBrand: (brandId, limit = 20) => api.get(`/generate/brand/${brandId}/content`, { params: { limit } }),
};

// ============ Status API ============
export const statusApi = {
  health: () => api.get('/health'),
  status: () => api.get('/status'),
};

// ============ LoRA Training API ============
export const loraApi = {
  // Models
  listModels: (params) => api.get('/lora/models/', { params }),
  getModel: (id) => api.get(`/lora/models/${id}`),
  createModel: (data) => api.post('/lora/models/', data),
  updateModel: (id, data) => api.put(`/lora/models/${id}`, data),
  deleteModel: (id) => api.delete(`/lora/models/${id}`),
  
  // Images
  addImage: (modelId, data) => api.post(`/lora/models/${modelId}/images`, data),
  bulkAddImages: (modelId, urls) => api.post(`/lora/models/${modelId}/images/bulk`, urls),
  listImages: (modelId) => api.get(`/lora/models/${modelId}/images`),
  deleteImage: (modelId, imageId) => api.delete(`/lora/models/${modelId}/images/${imageId}`),
  
  // Training
  validateModel: (modelId) => api.post(`/lora/models/${modelId}/validate`),
  startTraining: (modelId, config) => api.post(`/lora/models/${modelId}/train`, config),
  getProgress: (modelId) => api.get(`/lora/models/${modelId}/progress`),
  cancelTraining: (modelId) => api.post(`/lora/models/${modelId}/cancel`),
  
  // Generation
  generate: (data) => api.post('/lora/generate', data),
  generateBatch: (data) => api.post('/lora/generate/batch', data),
  generateScenario: (data) => api.post('/lora/generate/scenario', data),
  generateTestSamples: (modelId, num = 4) => api.post(`/lora/models/${modelId}/test-samples`, null, { params: { num_samples: num } }),
  
  // Samples
  listSamples: (modelId, params) => api.get(`/lora/models/${modelId}/samples`, { params }),
  rateSample: (sampleId, data) => api.post(`/lora/samples/${sampleId}/rate`, data),
  deleteSample: (sampleId) => api.delete(`/lora/samples/${sampleId}`),
  
  // Stats
  getModelStats: (modelId) => api.get(`/lora/models/${modelId}/stats`),
  getUserStats: () => api.get('/lora/stats')
};

// ============ Billing API ============
export const billingApi = {
  // Plans
  listPlans: () => api.get('/billing/plans/'),
  getPlan: (tier) => api.get(`/billing/plans/${tier}`),
  
  // Subscription
  getSubscription: () => api.get('/billing/subscription'),
  getUsage: () => api.get('/billing/usage'),
  checkLimit: (feature) => api.get(`/billing/check-limit/${feature}`),
  
  // Checkout
  createCheckout: (data) => api.post('/billing/checkout', data),
  createPortal: (data) => api.post('/billing/portal', data),
  
  // Plan changes
  changePlan: (data) => api.post('/billing/change-plan', data),
  cancelSubscription: (atPeriodEnd = true) => api.post('/billing/cancel', null, { params: { at_period_end: atPeriodEnd } }),
  reactivate: () => api.post('/billing/reactivate'),
  
  // Payments
  getPayments: (params) => api.get('/billing/payments', { params }),
  
  // Coupons
  validateCoupon: (code, tier) => api.post('/billing/coupon/validate', { code }, { params: { tier } })
};

// ============ Social Media API ============
export const socialApi = {
  // Accounts
  listAccounts: (params) => api.get('/social/accounts/', { params }),
  getAccount: (id) => api.get(`/social/accounts/${id}`),
  getConnectUrl: (platform, brandId) => api.get(`/social/connect/${platform}/url`, { params: { brand_id: brandId } }),
  connectCallback: (platform, data) => api.post(`/social/connect/${platform}/callback`, data),
  disconnectAccount: (id) => api.delete(`/social/accounts/${id}`),
  updateAccountBrand: (id, brandId) => api.put(`/social/accounts/${id}/brand`, null, { params: { brand_id: brandId } }),
  
  // Posts
  createPost: (data) => api.post('/social/posts', data),
  listPosts: (params) => api.get('/social/posts', { params }),
  getPost: (id) => api.get(`/social/posts/${id}`),
  updatePost: (id, data) => api.put(`/social/posts/${id}`, data),
  deletePost: (id) => api.delete(`/social/posts/${id}`),
  cancelPost: (id) => api.post(`/social/posts/${id}/cancel`),
  
  // Quick post
  postNow: (data) => api.post('/social/posts/now', data),
  
  // Bulk
  bulkSchedule: (data) => api.post('/social/posts/bulk', data),
  
  // Calendar
  getCalendar: (year, month, params) => api.get('/social/calendar', { params: { year, month, ...params } }),
  
  // Best times
  getBestTimes: (accountId) => api.get(`/social/accounts/${accountId}/best-times`),
  
  // Templates
  createTemplate: (data) => api.post('/social/templates/', data),
  listTemplates: (params) => api.get('/social/templates/', { params }),
  deleteTemplate: (id) => api.delete(`/social/templates/${id}`)
};

// ============ Video Generation API ============
export const videoApi = {
  // Generation
  generate: (data) => api.post('/video/generate', data),
  generateFromTemplate: (data) => api.post('/video/generate/template', data),
  generateBatch: (data) => api.post('/video/generate/batch', data),
  
  // Videos
  listVideos: (params) => api.get('/video/videos/', { params }),
  getVideo: (id) => api.get(`/video/videos/${id}`),
  getProgress: (id) => api.get(`/video/videos/${id}/progress`),
  cancelVideo: (id) => api.post(`/video/videos/${id}/cancel`),
  deleteVideo: (id) => api.delete(`/video/videos/${id}`),
  
  // Cost
  estimateCost: (data) => api.post('/video/estimate-cost', data),
  
  // Voices
  listVoices: () => api.get('/video/voices'),
  listVoiceClones: () => api.get('/video/voices/clones'),
  createVoiceClone: (data) => api.post('/video/voices/clone', data),
  deleteVoiceClone: (id) => api.delete(`/video/voices/clones/${id}`),
  
  // Templates
  listTemplates: (params) => api.get('/video/templates/', { params }),
  createTemplate: (data) => api.post('/video/templates/', data),
  deleteTemplate: (id) => api.delete(`/video/templates/${id}`),
  
  // Presets
  listExpressions: () => api.get('/video/expressions'),
  listAspectRatios: () => api.get('/video/aspect-ratios')
};

// ============ Content Studio API ============
export const studioApi = {
  // Projects
  createProject: (data) => api.post('/studio/projects/', data),
  listProjects: (params) => api.get('/studio/projects/', { params }),
  getProject: (id) => api.get(`/studio/projects/${id}`),
  getProjectProgress: (id) => api.get(`/studio/projects/${id}/progress`),
  deleteProject: (id) => api.delete(`/studio/projects/${id}`),
  
  // Assets
  getAssets: (projectId, params) => api.get(`/studio/projects/${projectId}/assets`, { params }),
  updateAsset: (id, data) => api.patch(`/studio/assets/${id}`, data),
  selectAsset: (id) => api.post(`/studio/assets/${id}/select`),
  toggleFavorite: (id) => api.post(`/studio/assets/${id}/favorite`),
  
  // Quick generate
  quickGenerate: (data) => api.post('/studio/quick-generate', data),
  
  // Templates
  listTemplates: (params) => api.get('/studio/templates/', { params }),
  createTemplate: (data) => api.post('/studio/templates/', data),
  deleteTemplate: (id) => api.delete(`/studio/templates/${id}`),
  
  // Presets
  getTones: () => api.get('/studio/tones'),
  getPlatforms: () => api.get('/studio/platforms')
};

// ============ Brand Voice API ============
export const brandVoiceApi = {
  // Voice profile
  getVoice: (brandId) => api.get(`/voice/brands/${brandId}`),
  getVoiceStats: (brandId) => api.get(`/voice/brands/${brandId}/stats`),
  
  // Examples
  getExamples: (brandId) => api.get(`/voice/brands/${brandId}/examples`),
  addExample: (brandId, data) => api.post(`/voice/brands/${brandId}/examples`, data),
  addExamplesBulk: (brandId, data) => api.post(`/voice/brands/${brandId}/examples/bulk`, data),
  deleteExample: (brandId, exampleId) => api.delete(`/voice/brands/${brandId}/examples/${exampleId}`),
  
  // Training
  train: (brandId) => api.post(`/voice/brands/${brandId}/train`),
  
  // Generation
  generate: (brandId, data) => api.post(`/voice/brands/${brandId}/generate`, data),
  generateVariations: (brandId, data) => api.post(`/voice/brands/${brandId}/generate/variations`, data),
  
  // Feedback
  recordFeedback: (data) => api.post('/voice/feedback', data),
  
  // Analysis
  analyzeText: (data) => api.post('/voice/analyze', data)
};

// ============ Analytics API ============
export const analyticsApi = {
  getOverview: (days) => api.get('/analytics/overview', { params: { days } }),
  getContent: (days) => api.get('/analytics/content', { params: { days } }),
  getSocial: (days) => api.get('/analytics/social', { params: { days } }),
  getVideos: (days) => api.get('/analytics/videos', { params: { days } }),
  getStudio: (days) => api.get('/analytics/studio', { params: { days } }),
  getCosts: (days) => api.get('/analytics/costs', { params: { days } }),
  getBestTimes: () => api.get('/analytics/best-times/'),
  getDashboard: (days) => api.get('/analytics/dashboard', { params: { days } })
};

// ============ AI Assistant API ============
export const assistantApi = {
  chat: (data) => api.post('/assistant/chat', data),
  improve: (data) => api.post('/assistant/improve', data),
  hashtags: (data) => api.post('/assistant/hashtags', data),
  translate: (data) => api.post('/assistant/translate', data),
  variations: (data) => api.post('/assistant/variations', data),
  optimize: (data) => api.post('/assistant/optimize', data),
  suggestCta: (data) => api.post('/assistant/suggest-cta', data),
  getCapabilities: () => api.get('/assistant/capabilities/')
};

// ============ Admin API ============
const adminInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' }
});

adminInstance.interceptors.request.use((config) => {
  const token = localStorage.getItem('adminToken');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const adminApi = {
  // Auth
  login: (data) => adminInstance.post('/admin/login', data),
  setup: (data) => adminInstance.post('/admin/setup', data),
  getMe: () => adminInstance.get('/admin/me'),
  
  // Stats
  getStats: () => adminInstance.get('/admin/stats'),
  
  // Users
  listUsers: (params) => adminInstance.get('/admin/users', { params }),
  getUser: (id) => adminInstance.get(`/admin/users/${id}`),
  updateUser: (id, data) => adminInstance.patch(`/admin/users/${id}`, data),
  grantSubscription: (id, data) => adminInstance.post(`/admin/users/${id}/subscription`, data),
  impersonateUser: (id, data) => adminInstance.post(`/admin/users/${id}/impersonate`, data),
  createTestBrand: (id, data) => adminInstance.post(`/admin/users/${id}/test-brand`, data),
  
  // Settings
  getSettings: () => adminInstance.get('/admin/settings'),
  updateSetting: (key, data) => adminInstance.put(`/admin/settings/${key}`, data),
  
  // Audit
  getAuditLogs: (params) => adminInstance.get('/admin/audit-logs', { params }),
  
  // Costs (uses main api with admin token)
  getCostOverview: (params) => adminInstance.get('/costs/admin/overview', { params }),
  getTopUsers: (params) => adminInstance.get('/costs/admin/top-users', { params }),
  getModelUsage: (params) => adminInstance.get('/costs/admin/model-usage', { params })
};

export default api;
