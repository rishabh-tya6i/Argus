import React from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { Shield, Search, LayoutDashboard, Box, ShieldAlert, Settings, LogOut } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const DashboardLayout = () => {
  const location = useLocation();
  const { logout } = useAuth();

  const navItems = [
    { label: 'Dashboard', path: '/', icon: LayoutDashboard },
    { label: 'Scans', path: '/scans', icon: Search },
    { label: 'Sandbox', path: '/sandbox', icon: Box },
    { label: 'Threat Intel', path: '/intel', icon: ShieldAlert },
    { label: 'Admin', path: '/admin', icon: Settings },
  ];

  return (
    <div className="flex h-screen bg-base-200">
      {/* Sidebar */}
      <aside className="w-64 bg-base-100 flex flex-col border-r border-base-300">
        <div className="p-4 flex items-center gap-3 border-b border-base-300">
          <Shield className="w-8 h-8 text-primary" />
          <h1 className="text-xl font-bold">Argus Sec</h1>
        </div>
        <nav className="flex-1 p-4 space-y-2">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center gap-3 p-3 rounded-lg transition-colors ${
                location.pathname === item.path || (item.path !== '/' && location.pathname.startsWith(item.path))
                  ? 'bg-primary text-primary-content'
                  : 'hover:bg-base-200'
              }`}
            >
              <item.icon className="w-5 h-5" />
              <span className="font-medium">{item.label}</span>
            </Link>
          ))}
        </nav>
        <div className="p-4 border-t border-base-300">
          <button 
            onClick={logout}
            className="flex items-center gap-3 p-3 w-full text-left rounded-lg hover:bg-base-200 text-error"
          >
            <LogOut className="w-5 h-5" />
            <span className="font-medium">Logout</span>
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Topbar */}
        <header className="h-16 bg-base-100 border-b border-base-300 flex items-center justify-between px-6">
          <h2 className="text-lg font-semibold capitalize">
            {location.pathname === '/' ? 'Dashboard' : location.pathname.split('/')[1].replace('-', ' ')}
          </h2>
          <div className="flex items-center gap-4">
            <div className="avatar placeholder">
              <div className="bg-neutral text-neutral-content rounded-full w-8">
                <span className="text-xs">U</span>
              </div>
            </div>
          </div>
        </header>
        
        {/* Page Content */}
        <main className="flex-1 overflow-y-auto bg-base-200 p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
};
