import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:3012';

class ApiClient {
  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Add request interceptor to include auth token
    this.client.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('access_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Add response interceptor to handle errors
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          // Token expired or invalid
          localStorage.removeItem('access_token');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  async get(url, config = {}) {
    const response = await this.client.get(url, config);
    return response.data;
  }

  async post(url, data = {}, config = {}) {
    const response = await this.client.post(url, data, config);
    return response.data;
  }

  async put(url, data = {}, config = {}) {
    const response = await this.client.put(url, data, config);
    return response.data;
  }

  async delete(url, config = {}) {
    const response = await this.client.delete(url, config);
    return response.data;
  }

  // Auth methods
  async login(username, password) {
    const response = await this.client.post(
      `/api/v1/auth/login?username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`
    );
    return response.data;
  }

  async register(userData) {
    const response = await this.client.post('/api/v1/auth/register', userData);
    return response.data;
  }

  async logout() {
    localStorage.removeItem('access_token');
  }

  // Account methods
  async getAccounts() {
    return this.get('/api/v1/accounts');
  }

  async createAccount(accountData) {
    return this.post('/api/v1/accounts', accountData);
  }

  async updateAccount(id, accountData) {
    return this.put(`/api/v1/accounts/${id}`, accountData);
  }

  async deleteAccount(id) {
    return this.delete(`/api/v1/accounts/${id}`);
  }

  // Position methods
  async getPositions() {
    return this.get('/api/v1/positions');
  }

  async closePosition(id) {
    return this.post(`/api/v1/positions/${id}/close`);
  }

  // Trade methods
  async getTrades() {
    return this.get('/api/v1/trades');
  }

  // Signal methods
  async getSignals() {
    return this.get('/api/v1/signals');
  }

  async createSignal(signalData) {
    return this.post('/api/v1/signals', signalData);
  }

  // API Key methods
  async getApiKeys() {
    return this.get('/api/v1/api-keys');
  }

  async createApiKey(name, expiresDays = 30) {
    return this.post(`/api/v1/api-keys?name=${encodeURIComponent(name)}&expires_days=${expiresDays}`);
  }

  async deleteApiKey(id) {
    return this.delete(`/api/v1/api-keys/${id}`);
  }

  // Strategy methods
  async getStrategies() {
    return this.get('/api/strategies');
  }

  async getTopStrategies() {
    return this.get('/api/strategies/top');
  }

  async enableStrategy(id, accountId) {
    return this.post(`/api/strategies/${id}/enable`, { account_id: accountId });
  }

  async disableStrategy(id, accountId) {
    return this.post(`/api/strategies/${id}/disable`, { account_id: accountId });
  }

  // Health check
  async healthCheck() {
    return this.get('/health');
  }

  // Metrics
  async getMetrics() {
    return this.get('/metrics');
  }
}

export const api = new ApiClient();
export default api;