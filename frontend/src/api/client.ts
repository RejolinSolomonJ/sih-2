/**
 * GreenFleet Q - Typed API Client
 */

export const API_BASE = '/api/v1';

export async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorBody.detail || `Request failed with status ${res.status}`);
  }

  return res.json();
}

export const api = {
  // Data
  getDataSummary: () => fetchJson<any>('/data/summary'),
  getDataPreview: (limit: number = 25) => fetchJson<any>(`/data/preview?limit=${limit}`),
  generateData: (samples: number = 50000, seed: number = 42) =>
    fetchJson<any>(`/data/generate?samples=${samples}&seed=${seed}`, { method: 'POST' }),

  // Models
  listModels: () => fetchJson<any[]>('/models'),
  compareModels: () => fetchJson<any>('/models/compare'),
  trainModel: (payload: any) =>
    fetchJson<any>('/models/train', { method: 'POST', body: JSON.stringify(payload) }),
  predictSingle: (payload: any, modelId?: string) =>
    fetchJson<any>(`/models/predict${modelId ? `?model_id=${modelId}` : ''}`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  activateModel: (modelId: string) =>
    fetchJson<any>(`/models/${modelId}/activate`, { method: 'POST' }),

  // Optimization
  startOptimization: (payload: any) =>
    fetchJson<any>('/optimize/run', { method: 'POST', body: JSON.stringify(payload) }),
  getOptimizationStatus: (jobId: string) =>
    fetchJson<any>(`/optimize/${jobId}/status`),
  getOptimizationResult: (jobId: string) =>
    fetchJson<any>(`/optimize/${jobId}/result`),
  listOptimizationJobs: () => fetchJson<any>('/optimize/jobs'),

  // Scenarios
  getFuelPathways: (routes?: string) =>
    fetchJson<any>(`/scenarios/fuel-pathways${routes ? `?routes=${routes}` : ''}`),
  getCarbonSensitivity: () => fetchJson<any>('/scenarios/carbon-price-sensitivity'),
  getSlowSteaming: (vesselId: string = 'panamax_container') =>
    fetchJson<any[]>(`/scenarios/slow-steaming?vessel_id=${vesselId}`),

  // Benchmarks
  runBenchmark: (instanceSize: string = 'small', numRuns: number = 3, seed: number = 42) =>
    fetchJson<any>(`/benchmarks/run?instance_size=${instanceSize}&num_runs=${numRuns}&seed=${seed}`),

  // Config
  getFuels: () => fetchJson<any>('/config/fuels'),
  getVessels: () => fetchJson<any>('/config/vessels'),
  getRoutes: () => fetchJson<any>('/config/routes'),
  getDefaults: () => fetchJson<any>('/config/defaults'),

  // Tools
  optimizeSpeed: (payload: any) =>
    fetchJson<any>('/tools/speed-optimizer', { method: 'POST', body: JSON.stringify(payload) }),
  getCompliance: (params: Record<string, any>) => {
    const qs = new URLSearchParams(params).toString();
    return fetchJson<any>(`/tools/compliance?${qs}`);
  },
};
