/**
 * API Service Layer — connects React frontend to FastAPI backend
 * Base URL: http://localhost:8000
 */
import axios from 'axios';

const BASE_URL = 'http://localhost:8000';

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

// ── Interceptors ──────────────────────────────────────────────────────────────
api.interceptors.response.use(
  (res) => res.data,
  (err) => {
    console.error('[API Error]', err.response?.data || err.message);
    return Promise.reject(err);
  }
);

// ── Health ─────────────────────────────────────────────────────────────────────
export const getHealth = () => api.get('/');

// ── Analytics ──────────────────────────────────────────────────────────────────
export const getDashboard      = () => api.get('/api/analytics/dashboard');
export const getSeverityTrend  = () => api.get('/api/analytics/severity-trend');
export const getUtilization    = () => api.get('/api/analytics/resource-utilization');
export const getTeamsOverview  = () => api.get('/api/analytics/teams-overview');

// ── Zones ──────────────────────────────────────────────────────────────────────
export const getZones        = (params = {}) => api.get('/api/zones/', { params });
export const getZone         = (id)          => api.get(`/api/zones/${id}`);
export const getZonesSummary = ()            => api.get('/api/zones/summary');
export const getZoneDemand   = (id)          => api.get(`/api/zones/${id}/demand`);
export const createZone      = (data)        => api.post('/api/zones/', data);
export const updateZone      = (id, data)    => api.put(`/api/zones/${id}`, data);
export const deactivateZone  = (id)          => api.delete(`/api/zones/${id}`);

// ── Resources ─────────────────────────────────────────────────────────────────
export const getResources        = (params = {}) => api.get('/api/resources/', { params });
export const getResourceSummary  = ()            => api.get('/api/resources/summary');
export const getResourceAlerts   = ()            => api.get('/api/resources/alerts');
export const updateResource      = (id, data)    => api.put(`/api/resources/${id}`, data);

// ── Depots ────────────────────────────────────────────────────────────────────
export const getDepots = () => api.get('/api/depots/');
export const getDepot  = (id) => api.get(`/api/depots/${id}`);

// ── Teams ─────────────────────────────────────────────────────────────────────
export const getTeams       = (params = {}) => api.get('/api/teams/', { params });
export const getTeamSummary = ()            => api.get('/api/teams/summary');
export const updateTeamStatus = (id, status, location) =>
  api.put(`/api/teams/${id}/status`, null, { params: { status, location } });

// ── Feeds ─────────────────────────────────────────────────────────────────────
export const getLiveFeed    = () => api.get('/api/feeds/live');
export const getGdacsFeed   = () => api.get('/api/feeds/gdacs');
export const getUsgsFeed    = () => api.get('/api/feeds/usgs');
export const classifyFeeds  = () => api.post('/api/feeds/classify');

// ── Events ────────────────────────────────────────────────────────────────────
export const getEvents     = (params = {}) => api.get('/api/events/', { params });
export const getEventStats = ()            => api.get('/api/events/stats');

// ── Allocation ────────────────────────────────────────────────────────────────
export const optimizeZone    = (zone_id)          => api.post('/api/allocation/optimize', null, { params: { zone_id } });
export const optimizeAll     = (severity_filter)  => api.post('/api/allocation/optimize-all', null, { params: { severity_filter } });
export const getNearestDepot = (zone_id)          => api.get('/api/allocation/nearest-depot', { params: { zone_id } });
export const getRoute        = (zone_id, depot_id) => api.get('/api/allocation/routes', { params: { zone_id, depot_id } });

export default api;
