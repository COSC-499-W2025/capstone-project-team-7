import React from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from '@/components/sidebar';

export const AppLayout: React.FC = () => {
  return (
    <div className="min-h-screen">
      <Sidebar />
      <main className="dashboard-stage overflow-y-auto">
        <Outlet />
      </main>
    </div>
  );
};
