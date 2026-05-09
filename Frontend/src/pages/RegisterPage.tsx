import { useState } from 'react';
import { PlusCircle, CheckCircle, Download, ArrowRight } from 'lucide-react';
import { createPackage, getLabelUrl } from '../api';
import type { PackageResponse } from '../api';

const INITIAL = {
  sender: '', recipient: '', contents: '',
  weight_kg: '', destination: '', routing_zone: '',
};

export default function RegisterPage() {
  const [form, setForm] = useState(INITIAL);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<PackageResponse | null>(null);

  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm(f => ({ ...f, [k]: e.target.value }));

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true); setError('');
    try {
      const pkg = await createPackage({
        ...form,
        weight_kg: parseFloat(form.weight_kg),
      });
      setResult(pkg);
      setForm(INITIAL);
    } catch (e) {
      const err = e as { response?: { data?: { detail?: Array<{ msg: string }> | string } } };
      const detail = err?.response?.data?.detail;
      setError(Array.isArray(detail)
        ? detail.map((d) => d.msg).join(', ')
        : detail ?? 'Registration failed. Is the API running?');
    } finally { setLoading(false); }
  };

  if (result) {
    return (
      <div>
        <div className="page-header">
          <h1><span className="gradient-text">Registration</span> Successful</h1>
          <p>Your package has been registered. Download the label and attach it to the parcel.</p>
        </div>
        <div className="card" style={{ maxWidth: 520 }}>
          <div className="flex items-center gap-3 mb-4">
            <div style={{ color: 'var(--success)', background: 'rgba(34,197,94,0.12)', borderRadius: '50%', padding: 8 }}>
              <CheckCircle size={28} />
            </div>
            <div>
              <h2 style={{ color: 'var(--success)' }}>Package Registered</h2>
              <p className="text-sm">SKU assigned and saved to the registry.</p>
            </div>
          </div>

          <div style={{
            background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)',
            padding: '14px 16px', border: '1px solid var(--border)', marginBottom: 20,
          }}>
            <div className="text-xs text-muted mb-2">Generated SKU</div>
            <div className="mono" style={{ fontSize: '1.4rem', color: 'var(--accent)', fontWeight: 700 }}>
              {result.sku}
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px 16px', marginBottom: 20 }}>
            {[
              ['Sender', result.sender], ['Recipient', result.recipient],
              ['Destination', result.destination], ['Zone', result.routing_zone],
              ['Weight', `${result.weight_kg} kg`], ['Status', result.status],
            ].map(([l, v]) => (
              <div key={l}>
                <div className="text-xs text-muted">{l}</div>
                <div className="text-sm" style={{ color: 'var(--text-primary)' }}>{v}</div>
              </div>
            ))}
          </div>

          <div className="flex gap-3">
            <a
              id="download-label-btn"
              href={getLabelUrl(result.sku)}
              target="_blank"
              rel="noreferrer"
              className="btn btn-primary"
            >
              <Download size={16} /> Download Label
            </a>
            <button
              id="register-another-btn"
              className="btn btn-secondary"
              onClick={() => setResult(null)}
            >
              <ArrowRight size={16} /> Register Another
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="page-header">
        <h1><span className="gradient-text">Register</span> New Package</h1>
        <p>Fill in the package details to generate an SKU and print a warehouse label.</p>
      </div>

      <div className="card" style={{ maxWidth: 620 }}>
        <div className="card-header">
          <div className="card-title">
            <div className="title-icon"><PlusCircle size={16} /></div>
            Package Details
          </div>
        </div>

        <form onSubmit={submit}>
          <div className="form-grid">
            <div className="form-group">
              <label htmlFor="reg-sender">Sender</label>
              <input id="reg-sender" required placeholder="Company or person name"
                value={form.sender} onChange={set('sender')} />
            </div>
            <div className="form-group">
              <label htmlFor="reg-recipient">Recipient</label>
              <input id="reg-recipient" required placeholder="Full name"
                value={form.recipient} onChange={set('recipient')} />
            </div>
            <div className="form-group">
              <label htmlFor="reg-destination">Destination</label>
              <input id="reg-destination" required placeholder="Warehouse / address"
                value={form.destination} onChange={set('destination')} />
            </div>
            <div className="form-group">
              <label htmlFor="reg-zone">Routing Zone</label>
              <input id="reg-zone" required placeholder="e.g. A-12"
                value={form.routing_zone} onChange={set('routing_zone')} />
            </div>
            <div className="form-group">
              <label htmlFor="reg-weight">Weight (kg)</label>
              <input id="reg-weight" required type="number" step="0.01" min="0.01"
                placeholder="0.00" value={form.weight_kg} onChange={set('weight_kg')} />
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="reg-contents">Contents Description</label>
            <textarea id="reg-contents" required rows={3}
              placeholder="Briefly describe the package contents…"
              value={form.contents} onChange={set('contents') as any}
              style={{ resize: 'vertical' }}
            />
          </div>

          {error && <div className="alert alert-danger mb-4">{error}</div>}

          <button id="reg-submit-btn" type="submit" className="btn btn-primary btn-lg w-full" disabled={loading}>
            {loading ? <><div className="spinner" /> Registering…</> : <><PlusCircle size={18} /> Register Package</>}
          </button>
        </form>
      </div>
    </div>
  );
}
