import { Routes, Route } from "react-router-dom";
import { WizardProvider } from "./context/WizardContext";
import AppShell from "./components/layout/AppShell";
import DashboardPage from "./pages/DashboardPage";
import IntakePage from "./pages/IntakePage";
import UploadPage from "./pages/UploadPage";
import ConfirmPage from "./pages/ConfirmPage";
import ProcessingPage from "./pages/ProcessingPage";
import CheckpointPage from "./pages/CheckpointPage";
import ResultsPage from "./pages/ResultsPage";
import ValidatePage from "./pages/ValidatePage";
import NotFoundPage from "./pages/NotFoundPage";

export default function App() {
  return (
    <WizardProvider>
      <AppShell>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/intake" element={<IntakePage />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/validate" element={<ValidatePage />} />
          <Route path="/confirm" element={<ConfirmPage />} />
          <Route path="/jobs/:jobId/processing" element={<ProcessingPage />} />
          <Route path="/jobs/:jobId/checkpoint" element={<CheckpointPage />} />
          <Route path="/jobs/:jobId/results" element={<ResultsPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </AppShell>
    </WizardProvider>
  );
}
