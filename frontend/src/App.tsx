import React from 'react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { AppLayout } from './layout/AppLayout';
import { Plus } from 'lucide-react';

// Dashboard Page (with header shell)
const DashboardPage: React.FC = () => {
  return (
    <div className="p-8">
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
        <div className="flex items-center justify-between">
          <h1 className="text-4xl font-bold text-gray-900 tracking-tight">Dashboard</h1>
          <button className="flex items-center gap-2 px-5 py-2.5 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors shadow-sm">
            <Plus size={20} />
            <span className="font-medium">New Scan</span>
          </button>
        </div>
      </div>
      {/* Empty space below for future widgets */}
    </div>
  );
};

// Placeholder Pages
const PlaceholderPage: React.FC<{ title: string }> = ({ title }) => {
  return (
    <div className="p-8">
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
        <h1 className="text-4xl font-bold text-gray-900 tracking-tight">{title}</h1>
      </div>
    </div>
  );
};

const App: React.FC = () => {
  return (
    <MemoryRouter>
      <Routes>
        <Route path="/" element={<AppLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="portfolio" element={<PlaceholderPage title="Portfolio" />} />
          <Route path="projects" element={<PlaceholderPage title="Projects" />} />
          <Route path="resumes" element={<PlaceholderPage title="Resumes" />} />
          <Route path="scanned-results" element={<PlaceholderPage title="Scanned Results" />} />
          <Route path="resume-generation" element={<PlaceholderPage title="Resume Generation" />} />
          <Route path="ai-analysis" element={<PlaceholderPage title="AI-Powered Analysis" />} />
          <Route path="skill-progression" element={<PlaceholderPage title="Skill Progression" />} />
          <Route path="more" element={<PlaceholderPage title="More" />} />
          <Route path="settings" element={<PlaceholderPage title="Settings" />} />
          <Route path="help" element={<PlaceholderPage title="Get Help" />} />
          <Route path="search" element={<PlaceholderPage title="Search" />} />
        </Route>
      </Routes>
    </MemoryRouter>
  );
};

export default App;
