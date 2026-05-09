import type { PackageResponse } from '../api';

const STATUS_MAP: Record<PackageResponse['status'], { label: string; cls: string }> = {
  REGISTERED: { label: 'Registered', cls: 'badge-info' },
  IN_TRANSIT: { label: 'In Transit', cls: 'badge-warn' },
  DELIVERED: { label: 'Delivered', cls: 'badge-success' },
  CANCELLED: { label: 'Cancelled', cls: 'badge-danger' },
};

export function StatusBadge({ status }: { status: PackageResponse['status'] }) {
  const s = STATUS_MAP[status] ?? { label: status, cls: 'badge-muted' };
  return <span className={`badge ${s.cls}`}>{s.label}</span>;
}
