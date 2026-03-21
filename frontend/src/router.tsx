import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import { DashboardLayout } from './layouts/DashboardLayout';
import { LoginPage } from './pages/Auth/LoginPage';
import { SignupPage } from './pages/Auth/SignupPage';
import { DashboardPage } from './pages/Dashboard/DashboardPage';
import { ScansPage } from './pages/Scans/ScansPage';
import { ScanDetailsPage } from './pages/Scans/ScanDetailsPage';
import { SandboxPage } from './pages/Sandbox/SandboxPage';
import { ThreatIntelPage } from './pages/ThreatIntel/ThreatIntelPage';
import { TenantAdminPage } from './pages/Admin/TenantAdminPage';
import { SecurityScannerPage } from './pages/SecurityScanner/SecurityScannerPage';

export const MainRouter = () => {
  const { isAuthenticated } = useAuth();

  return (
    <Routes>
      <Route path="/login" element={!isAuthenticated ? <LoginPage /> : <Navigate to="/" />} />
      <Route path="/signup" element={!isAuthenticated ? <SignupPage /> : <Navigate to="/" />} />
      
      <Route element={isAuthenticated ? <DashboardLayout /> : <Navigate to="/login" />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/scans" element={<ScansPage />} />
        <Route path="/scans/:id" element={<ScanDetailsPage />} />
        <Route path="/sandbox" element={<SandboxPage />} />
        <Route path="/sandbox/:id" element={<SandboxPage />} />
        <Route path="/security-scanner" element={<SecurityScannerPage />} />
        <Route path="/intel" element={<ThreatIntelPage />} />
        <Route path="/admin" element={<TenantAdminPage />} />
      </Route>
    </Routes>
  );
};
