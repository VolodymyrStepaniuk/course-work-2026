import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import DashboardPage from './pages/DashboardPage';
import PackagesPage from './pages/PackagesPage';
import RegisterPage from './pages/RegisterPage';
import VerifyPage from './pages/VerifyPage';

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-shell">
        <Sidebar />
        <main className="main-content">
          <Routes>
            <Route path="/"         element={<DashboardPage />} />
            <Route path="/packages" element={<PackagesPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/verify"   element={<VerifyPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
