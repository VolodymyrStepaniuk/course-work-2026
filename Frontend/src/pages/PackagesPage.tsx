import { useEffect, useState } from 'react';
import {
  Package, RefreshCw, Download, Trash2, Search, Pencil, X, Check,
  ChevronLeft, ChevronRight, ChevronsUpDown, ChevronUp, ChevronDown
} from 'lucide-react';
import {
  getPackages, deletePackage, getLabelUrl,
  updatePackage
} from '../api';
import type { PackageResponse, PackageUpdate } from '../api';
import { StatusBadge } from '../components/StatusBadge';


function EditModal({
  pkg, onClose, onSaved,
}: { pkg: PackageResponse; onClose: () => void; onSaved: (p: PackageResponse) => void }) {
  const [form, setForm] = useState<PackageUpdate>({
    sender: pkg.sender, recipient: pkg.recipient, contents: pkg.contents,
    weight_kg: pkg.weight_kg, destination: pkg.destination,
    routing_zone: pkg.routing_zone, status: pkg.status,
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const save = async () => {
    setSaving(true); setError('');
    try {
      const updated = await updatePackage(pkg.sku, form);
      onSaved(updated);
    } catch (e) {
      const err = e as { response?: { data?: { detail?: string } } };
      setError(err?.response?.data?.detail ?? 'Failed to update');
    } finally { setSaving(false); }
  };

  const field = (key: keyof PackageUpdate, label: string, type = 'text') => (
    <div className="form-group">
      <label htmlFor={`edit-${key}`}>{label}</label>
      <input
        id={`edit-${key}`}
        type={type}
        value={(form[key] as string | number) ?? ''}
        onChange={e => setForm(f => ({
          ...f,
          [key]: type === 'number' ? parseFloat(e.target.value) : e.target.value,
        }))}
      />
    </div>
  );

  return (
    <div className="modal-backdrop" onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="modal">
        <div className="modal-header">
          <h3>Edit Package — <span className="mono text-accent">{pkg.sku}</span></h3>
          <button className="btn btn-secondary btn-icon btn-sm" onClick={onClose}><X size={16} /></button>
        </div>
        <div className="modal-body">
          <div className="form-grid">
            {field('sender', 'Sender')}
            {field('recipient', 'Recipient')}
            {field('destination', 'Destination')}
            {field('routing_zone', 'Routing Zone')}
            {field('weight_kg', 'Weight (kg)', 'number')}
          </div>
          {field('contents', 'Contents')}
          <div className="form-group">
            <label htmlFor="edit-status">Status</label>
            <select
              id="edit-status"
              value={form.status}
              onChange={e => setForm(f => ({ ...f, status: e.target.value as PackageResponse['status'] }))}
            >
              <option value="REGISTERED">Registered</option>
              <option value="IN_TRANSIT">In Transit</option>
              <option value="DELIVERED">Delivered</option>
              <option value="CANCELLED">Cancelled</option>
            </select>
          </div>
          {error && <div className="alert alert-danger mt-3">{error}</div>}
        </div>
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={save} disabled={saving}>
            {saving ? <div className="spinner" /> : <Check size={16} />}
            Save Changes
          </button>
        </div>
      </div>
    </div>
  );
}
export default function PackagesPage() {
  const [packages, setPackages] = useState<PackageResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');
  const [editPkg, setEditPkg] = useState<PackageResponse | null>(null);
  const [toDelete, setToDelete] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  // Pagination & Sorting state
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(10);
  const [sortConfig, setSortConfig] = useState<{ key: keyof PackageResponse; direction: 'asc' | 'desc' }>({
    key: 'created_at',
    direction: 'desc',
  });

  const load = () => {
    setLoading(true);
    // Fetching 100 to allow in-memory filtering/sorting/pagination as requested
    getPackages(0, 100).then(p => { setPackages(p); setLoading(false) })
      .catch(() => setLoading(false));
  };

  useEffect(() => {
    setCurrentPage(1);
  }, [query]);

  useEffect(() => {
    load();
  }, []);

  const requestSort = (key: keyof PackageResponse) => {
    let direction: 'asc' | 'desc' = 'asc';
    if (sortConfig.key === key && sortConfig.direction === 'asc') {
      direction = 'desc';
    }
    setSortConfig({ key, direction });
  };

  const filtered = packages.filter(p => {
    const q = query.toLowerCase();
    return !q || [p.sku, p.sender, p.recipient, p.destination, p.contents, p.routing_zone]
      .some(v => v.toLowerCase().includes(q));
  });

  const sorted = [...filtered].sort((a, b) => {
    let aVal = a[sortConfig.key];
    let bVal = b[sortConfig.key];

    if (typeof aVal === 'string') aVal = aVal.toLowerCase();
    if (typeof bVal === 'string') bVal = bVal.toLowerCase();

    if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1;
    if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1;
    return 0;
  });

  const totalPages = Math.ceil(sorted.length / pageSize);
  const paginated = sorted.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  const SortIndicator = ({ column }: { column: keyof PackageResponse }) => {
    if (sortConfig.key !== column) return <ChevronsUpDown size={12} className="sort-icon" />;
    return sortConfig.direction === 'asc'
      ? <ChevronUp size={12} className="sort-icon active" />
      : <ChevronDown size={12} className="sort-icon active" />;
  };

  const confirmDelete = async () => {
    if (!toDelete) return;
    setDeleting(true);
    try {
      await deletePackage(toDelete);
      setPackages(ps => ps.filter(p => p.sku !== toDelete));
    } finally { setDeleting(false); setToDelete(null); }
  };

  return (
    <div>
      <div className="page-header">
        <h1><span className="gradient-text">Package</span> Registry</h1>
        <p>Browse, edit, and manage all registered warehouse packages.</p>
      </div>

      <div className="card">
        <div className="card-header">
          <div className="card-title">
            <div className="title-icon"><Package size={16} /></div>
            All Packages <span className="badge badge-muted" style={{ marginLeft: 4 }}>{filtered.length}</span>
          </div>
          <div className="flex gap-2">
            <div style={{ position: 'relative' }}>
              <Search size={14} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
              <input
                id="pkg-search"
                style={{ paddingLeft: 32, width: 220 }}
                placeholder="Search packages…"
                value={query}
                onChange={e => setQuery(e.target.value)}
              />
            </div>
            <button className="btn btn-secondary btn-icon" onClick={load} title="Refresh">
              <RefreshCw size={16} className={loading ? 'spin' : ''} />
            </button>
          </div>
        </div>

        {loading ? (
          <div className="flex items-center gap-3" style={{ padding: '32px 0' }}>
            <div className="spinner" /><span className="text-secondary">Loading packages…</span>
          </div>
        ) : filtered.length === 0 ? (
          <p className="text-secondary text-sm" style={{ padding: '20px 0' }}>
            {query ? 'No packages match your search.' : 'No packages found. Register one first.'}
          </p>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th className="sortable-th" onClick={() => requestSort('sku')}>SKU <SortIndicator column="sku" /></th>
                  <th className="sortable-th" onClick={() => requestSort('sender')}>Sender <SortIndicator column="sender" /></th>
                  <th className="sortable-th" onClick={() => requestSort('recipient')}>Recipient <SortIndicator column="recipient" /></th>
                  <th className="sortable-th" onClick={() => requestSort('destination')}>Destination <SortIndicator column="destination" /></th>
                  <th className="sortable-th" onClick={() => requestSort('routing_zone')}>Zone <SortIndicator column="routing_zone" /></th>
                  <th className="sortable-th" onClick={() => requestSort('weight_kg')}>Weight <SortIndicator column="weight_kg" /></th>
                  <th className="sortable-th" onClick={() => requestSort('status')}>Status <SortIndicator column="status" /></th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {paginated.map(p => (
                  <tr key={p.sku}>
                    <td><span className="mono text-accent">{p.sku}</span></td>
                    <td className="text-sm">{p.sender}</td>
                    <td className="text-sm">{p.recipient}</td>
                    <td className="text-secondary text-sm">{p.destination}</td>
                    <td><span className="badge badge-muted">{p.routing_zone}</span></td>
                    <td className="text-secondary text-sm">{p.weight_kg} kg</td>
                    <td><StatusBadge status={p.status} /></td>
                    <td>
                      <div className="flex gap-2">
                        <a
                          href={getLabelUrl(p.sku)}
                          target="_blank"
                          rel="noreferrer"
                          className="btn btn-secondary btn-icon btn-sm"
                          title="Download label"
                        >
                          <Download size={14} />
                        </a>
                        <button
                          className="btn btn-secondary btn-icon btn-sm"
                          title="Edit"
                          onClick={() => setEditPkg(p)}
                        >
                          <Pencil size={14} />
                        </button>
                        <button
                          className="btn btn-danger btn-icon btn-sm"
                          title="Delete"
                          onClick={() => setToDelete(p.sku)}
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {!loading && totalPages > 1 && (
          <div className="pagination">
            <button
              className="pagination-btn"
              disabled={currentPage === 1}
              onClick={() => setCurrentPage(p => p - 1)}
            >
              <ChevronLeft size={16} />
            </button>

            {[...Array(totalPages)].map((_, i) => {
              const page = i + 1;
              // Simple pagination logic: show first, last, and current ± 1
              if (
                page === 1 ||
                page === totalPages ||
                (page >= currentPage - 1 && page <= currentPage + 1)
              ) {
                return (
                  <button
                    key={page}
                    className={`pagination-btn ${currentPage === page ? 'active' : ''}`}
                    onClick={() => setCurrentPage(page)}
                  >
                    {page}
                  </button>
                );
              }
              if (page === currentPage - 2 || page === currentPage + 2) {
                return <span key={page} className="text-muted">…</span>;
              }
              return null;
            })}

            <button
              className="pagination-btn"
              disabled={currentPage === totalPages}
              onClick={() => setCurrentPage(p => p + 1)}
            >
              <ChevronRight size={16} />
            </button>
          </div>
        )}
      </div>

      {/* Edit modal */}
      {editPkg && (
        <EditModal
          pkg={editPkg}
          onClose={() => setEditPkg(null)}
          onSaved={updated => {
            setPackages(ps => ps.map(p => p.sku === updated.sku ? updated : p));
            setEditPkg(null);
          }}
        />
      )}

      {/* Delete confirm modal */}
      {toDelete && (
        <div className="modal-backdrop" onClick={e => { if (e.target === e.currentTarget) setToDelete(null); }}>
          <div className="modal" style={{ maxWidth: 400 }}>
            <div className="modal-header">
              <h3>Delete Package</h3>
              <button className="btn btn-secondary btn-icon btn-sm" onClick={() => setToDelete(null)}><X size={16} /></button>
            </div>
            <div className="modal-body">
              <p>Are you sure you want to permanently delete <span className="mono text-accent">{toDelete}</span>? This cannot be undone.</p>
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setToDelete(null)}>Cancel</button>
              <button className="btn btn-danger" onClick={confirmDelete} disabled={deleting}>
                {deleting ? <div className="spinner" /> : <Trash2 size={16} />}
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
