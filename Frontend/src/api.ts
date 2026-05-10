import axios from 'axios';

const BASE = import.meta.env.VITE_API_BASE ?? '/api/v1';

export const api = axios.create({ baseURL: BASE });

/* ── Packages ── */
export interface PackageCreate {
  sender: string;
  recipient: string;
  contents: string;
  weight_kg: number;
  destination: string;
  routing_zone: string;
}

export interface PackageResponse {
  sku: string;
  sender: string;
  recipient: string;
  contents: string;
  weight_kg: number;
  destination: string;
  routing_zone: string;
  status: 'REGISTERED' | 'IN_TRANSIT' | 'DELIVERED' | 'CANCELLED';
  created_at: string;
}

export interface PackageUpdate {
  sender?: string;
  recipient?: string;
  contents?: string;
  weight_kg?: number;
  destination?: string;
  routing_zone?: string;
  status?: PackageResponse['status'];
}

export interface VerifyResponse {
  filename: string;
  verified: boolean;
  registered: boolean;
  matched_data: string | null;
  package: PackageResponse | null;
  details: {
    barcodes_found: { data: string; type: string; bounding_box: { x: number; y: number; w: number; h: number } }[];
    texts_found: { text: string; confidence: number }[];
  };
  timing: {
    total_ms: number;
    scan_ms: number;
    ocr_ms: number;
    db_ms: number;
  };
}

/* ── API calls ── */
export const getPackages = (skip = 0, limit = 50) =>
  api.get<PackageResponse[]>('/packages', { params: { skip, limit } }).then(r => r.data);

export const getPackage = (sku: string) =>
  api.get<PackageResponse>(`/packages/${sku}`).then(r => r.data);

export const createPackage = (data: PackageCreate) =>
  api.post<PackageResponse>('/packages', data).then(r => r.data);

export const updatePackage = (sku: string, data: PackageUpdate) =>
  api.patch<PackageResponse>(`/packages/${sku}`, data).then(r => r.data);

export const deletePackage = (sku: string) =>
  api.delete(`/packages/${sku}`);

export const getLabelUrl = (sku: string) => `${BASE}/packages/${sku}/label`;

export const verifyPackage = (file: File, languages?: string[]) => {
  const form = new FormData();
  form.append('file', file);
  const params = languages ? new URLSearchParams(languages.map(l => ['languages', l])) : undefined;
  return api.post<VerifyResponse>('/verify/package', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    params,
  }).then(r => r.data);
};

export const checkHealth = () =>
  api.get<{ status: string }>('/health').then(r => r.data);
