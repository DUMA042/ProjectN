import { Routes, Route, Navigate } from "react-router-dom";
import Sidebar from "./components/layout/Sidebar";
import Header from "./components/layout/Header";
import StatusBar from "./components/layout/StatusBar";
import DashboardPage from "./pages/DashboardPage";
import ManagementPage from "./pages/ManagementPage";
import UploadPage from "./pages/UploadPage";
import AdminPage from "./pages/AdminPage";
import ReportsPage from "./pages/ReportsPage";
import SettingsPage from "./pages/SettingsPage";
import RulesSettingsPage from "./pages/RulesSettingsPage";

export default function App() {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/management" element={<ManagementPage />} />
            {/* Legacy Management routes now live inside the unified workspace */}
            <Route path="/employees" element={<Navigate to="/management" replace />} />
            <Route path="/attendance" element={<Navigate to="/management" replace />} />
            <Route path="/leave" element={<Navigate to="/management" replace />} />
            <Route path="/training" element={<Navigate to="/management" replace />} />
            <Route path="/upload" element={<UploadPage />} />
            <Route path="/admin" element={<AdminPage />} />
            <Route path="/reports" element={<ReportsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/rules-settings" element={<RulesSettingsPage />} />
          </Routes>
        </main>
        <StatusBar />
      </div>
    </div>
  );
}
