import React, { useState } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Sidebar from './Sidebar';
import MyReports from './MyReports';
import UploadPrescription from './UploadPrescription';
import './PatientDashboard.css';

function PatientDashboard({ user, onLogout }) {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  return (
    <div className="dashboard-container">
      <Sidebar 
        user={user} 
        onLogout={onLogout}
        isOpen={sidebarOpen}
        toggleSidebar={() => setSidebarOpen(!sidebarOpen)}
      />
      
      <div className={`dashboard-main ${sidebarOpen ? 'sidebar-open' : 'sidebar-closed'}`}>
        <Routes>
          <Route path="/" element={<Navigate to="reports" />} />
          <Route path="reports" element={<MyReports userId={user.id} />} />
          <Route path="upload" element={<UploadPrescription userId={user.id} />} />
        </Routes>
      </div>
    </div>
  );
}

export default PatientDashboard;
