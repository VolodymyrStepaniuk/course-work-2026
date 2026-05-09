import { useState, useEffect } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard, Package, ScanLine, PlusCircle,
  Menu, X
} from 'lucide-react';
import { checkHealth } from '../api';

const links = [
  { to: '/',          label: 'Dashboard',     icon: LayoutDashboard },
  { to: '/packages',  label: 'Packages',      icon: Package },
  { to: '/register',  label: 'Register New',  icon: PlusCircle },
  { to: '/verify',    label: 'Verify Label',  icon: ScanLine },
];

export default function Sidebar() {
  const [online, setOnline] = useState<boolean | null>(null);
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    const check = async () => {
      try { await checkHealth(); setOnline(true); }
      catch { setOnline(false); }
    };
    check();
    const t = setInterval(check, 10_000);
    return () => clearInterval(t);
  }, []);

  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { setMobileOpen(false); }, [location]);

  const nav = (
    <>
      <div className="sidebar-logo">
        <div className="logo-icon">📦</div>
        <h2>WarehouseOS</h2>
        <p>Barcode System</p>
      </div>

      <span className="nav-section-label">Navigation</span>
      {links.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          end={to === '/'}
          className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
        >
          <Icon className="nav-icon" size={16} />
          {label}
        </NavLink>
      ))}

      <div style={{ marginTop: 'auto', padding: '16px 20px', borderTop: '1px solid var(--border)' }}>
        <div className="flex items-center gap-2" style={{ fontSize: '0.78rem' }}>
          <div style={{
            width: 8, height: 8, borderRadius: '50%',
            background: online === null ? 'var(--warn)' : online ? 'var(--success)' : 'var(--danger)',
            boxShadow: `0 0 6px ${online ? 'var(--success)' : 'var(--danger)'}`,
            animation: online === true ? 'pulse-dot 2s infinite' : 'none',
          }} />
          <span className="text-secondary">
            {online === null ? 'Connecting…' : online ? 'API Online' : 'API Offline'}
          </span>
        </div>
      </div>
    </>
  );

  return (
    <>
      {/* Mobile toggle */}
      <button
        className="btn btn-secondary btn-icon"
        onClick={() => setMobileOpen(o => !o)}
        style={{ position: 'fixed', top: 16, left: 16, zIndex: 200, display: 'none' }}
        id="sidebar-toggle"
      >
        {mobileOpen ? <X size={18} /> : <Menu size={18} />}
      </button>

      <aside className="sidebar">{nav}</aside>
    </>
  );
}
