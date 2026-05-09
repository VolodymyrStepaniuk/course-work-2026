import { useEffect, useState } from 'react';
import {
  Package, CheckCircle, Truck, Archive,
  TrendingUp, Clock, AlertTriangle
} from 'lucide-react';
import { getPackages } from '../api';
import type { PackageResponse } from '../api';
import { StatusBadge } from '../components/StatusBadge';

function StatCard({
  label, value, icon: Icon, color, sub
}: {
  label: string; value: number | string; icon: React.ElementType;
  color: string; sub?: string;
}) {
  return (
    <div className="stat-card">
      <div className="stat-icon" style={{ background: `${color}22`, color }}>
        <Icon size={18} />
      </div>
      <div className="stat-value" style={{ color }}>{value}</div>
      <div className="stat-label">{label}</div>
      {sub && <div className="text-xs text-muted">{sub}</div>}
    </div>
  );
}

export default function DashboardPage() {
  const [packages, setPackages] = useState<PackageResponse[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getPackages(0, 100).then(p => { setPackages(p); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const total = packages.length;
  const registered = packages.filter(p => p.status === 'REGISTERED').length;
  const inTransit = packages.filter(p => p.status === 'IN_TRANSIT').length;
  const delivered = packages.filter(p => p.status === 'DELIVERED').length;
  const cancelled = packages.filter(p => p.status === 'CANCELLED').length;

  const recent = [...packages]
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 5);

  return (
    <div>
      <div className="page-header">
        <h1>
          <span className="gradient-text">Warehouse</span> Dashboard
        </h1>
        <p>Overview of all registered packages and system health.</p>
      </div>

      {loading ? (
        <div className="flex items-center gap-3" style={{ padding: '40px 0' }}>
          <div className="spinner" /><span className="text-secondary">Loading…</span>
        </div>
      ) : (
        <>
          <div className="stats-grid">
            <StatCard label="Total Packages" value={total} icon={Package} color="var(--accent)" />
            <StatCard label="Registered" value={registered} icon={Archive} color="var(--info)" />
            <StatCard label="In Transit" value={inTransit} icon={Truck} color="var(--warn)" />
            <StatCard label="Delivered" value={delivered} icon={CheckCircle} color="var(--success)" />
            <StatCard label="Cancelled" value={cancelled} icon={AlertTriangle} color="var(--danger)" />
            <StatCard
              label="Delivery Rate"
              value={total ? `${Math.round((delivered / total) * 100)}%` : '—'}
              icon={TrendingUp}
              color="var(--accent)"
            />
          </div>

          <div className="card">
            <div className="card-header">
              <div className="card-title">
                <div className="title-icon"><Clock size={16} /></div>
                Recent Packages
              </div>
            </div>
            {recent.length === 0 ? (
              <p className="text-secondary text-sm" style={{ padding: '20px 0' }}>
                No packages registered yet. Go to <strong>Register New</strong> to add one.
              </p>
            ) : (
              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>SKU</th>
                      <th>Recipient</th>
                      <th>Destination</th>
                      <th>Weight</th>
                      <th>Status</th>
                      <th>Registered</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recent.map(p => (
                      <tr key={p.sku}>
                        <td><span className="mono text-accent">{p.sku}</span></td>
                        <td>{p.recipient}</td>
                        <td className="text-secondary">{p.destination}</td>
                        <td className="text-secondary">{p.weight_kg} kg</td>
                        <td><StatusBadge status={p.status} /></td>
                        <td className="text-muted text-xs">
                          {new Date(p.created_at).toLocaleDateString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
