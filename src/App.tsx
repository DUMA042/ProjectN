import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import { ToastProvider } from "./components/ui/Toast";
import ErrorBoundary from "./components/ui/ErrorBoundary";
import Sidebar from "./components/layout/Sidebar";
import Header from "./components/layout/Header";
import StatusBar from "./components/layout/StatusBar";
import ServiceBanner from "./components/layout/ServiceBanner";
import DashboardPage from "./pages/DashboardPage";
import ManagementPage from "./pages/ManagementPage";
import UploadPage from "./pages/UploadPage";
import ReportsPage from "./pages/ReportsPage";
import IndividualReportPage from "./pages/IndividualReportPage";
import SettingsPage from "./pages/SettingsPage";
import RulesSettingsPage from "./pages/RulesSettingsPage";
import NotFoundPage from "./pages/NotFoundPage";

export default function App() {
  const location = useLocation();

  return (
    <ToastProvider>
      <div className="flex h-screen overflow-hidden">
        <Sidebar />
        <div className="flex flex-1 flex-col overflow-hidden">
          <Header />
          <ServiceBanner />
          <main className="flex-1 overflow-y-auto">
            {/* Keyed by path: navigating away from a crashed page resets the
                boundary, and a crash anywhere still leaves the shell usable. */}
            <ErrorBoundary key={location.pathname} label="this page">
              <Routes>
                <Route path="/" element={<DashboardPage />} />
                <Route path="/management" element={<ManagementPage />} />
                {/* Legacy routes now live inside the unified workspace */}
                <Route path="/employees" element={<Navigate to="/management" replace />} />
                <Route path="/attendance" element={<Navigate to="/management" replace />} />
                <Route path="/leave" element={<Navigate to="/management" replace />} />
                <Route path="/training" element={<Navigate to="/management" replace />} />
                <Route path="/upload" element={<UploadPage />} />
                <Route path="/reports" element={<ReportsPage />} />
                <Route path="/individual-report" element={<IndividualReportPage />} />
                <Route path="/settings" element={<SettingsPage />} />
                <Route path="/rules-settings" element={<RulesSettingsPage />} />
                <Route path="*" element={<NotFoundPage />} />
              </Routes>
            </ErrorBoundary>
          </main>
          <StatusBar />
        </div>
      </div>
    </ToastProvider>
  );
}
