import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Users, Key, Settings as SettingsIcon, Building } from 'lucide-react';
import { tenantApi } from '../../api/tenant';

export const TenantAdminPage = () => {
  const { data: tenant } = useQuery({ queryKey: ['tenantDetails'], queryFn: tenantApi.getTenant });
  const { data: users = [] } = useQuery({ queryKey: ['tenantUsers'], queryFn: tenantApi.getUsers });
  const { data: apiKeys = [] } = useQuery({ queryKey: ['tenantApiKeys'], queryFn: tenantApi.getApiKeys });

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Building className="w-6 h-6 text-primary" /> Tenant Administration
        </h1>
        <p className="text-base-content/70">Manage your organization's setup, users, and API keys.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="card bg-base-100 border border-base-300 shadow-sm col-span-1 lg:col-span-3">
          <div className="card-body">
            <h2 className="card-title text-lg flex items-center gap-2 border-b border-base-300 pb-2">
              <SettingsIcon className="w-5 h-5" /> Subscribed Plan Details
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-4">
              <div>
                <p className="text-xs font-semibold text-base-content/60 uppercase tracking-wider">Tenant Name</p>
                <p className="text-lg font-bold">{tenant?.name || 'Loading...'}</p>
              </div>
              <div>
                <p className="text-xs font-semibold text-base-content/60 uppercase tracking-wider">Plan Tier</p>
                <p className="text-lg font-bold text-primary uppercase">{tenant?.plan_tier || 'Enterprise'}</p>
              </div>
              <div>
                <p className="text-xs font-semibold text-base-content/60 uppercase tracking-wider">Tenant Slug</p>
                <p className="font-mono text-sm">{tenant?.slug || '...'}</p>
              </div>
            </div>
          </div>
        </div>

        <div className="card bg-base-100 border border-base-300 shadow-sm col-span-1 lg:col-span-2">
          <div className="card-body p-0">
            <div className="flex justify-between items-center p-6 pb-2">
              <h2 className="card-title text-lg flex items-center gap-2">
                <Users className="w-5 h-5" /> Users
              </h2>
              <button className="btn btn-sm btn-outline">Invite User</button>
            </div>
            <div className="overflow-x-auto w-full">
              <table className="table w-full">
                <thead className="bg-base-200/50">
                  <tr>
                    <th className="pl-6">Email</th>
                    <th>Role</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map(u => (
                    <tr key={u.id}>
                      <td className="pl-6 font-medium">{u.email}</td>
                      <td><span className="badge badge-ghost uppercase text-xs font-bold tracking-widest">{u.role}</span></td>
                      <td><div className="badge badge-success badge-sm">Active</div></td>
                    </tr>
                  ))}
                  {users.length === 0 && (
                    <tr>
                      <td colSpan={3} className="text-center py-6 italic text-base-content/50">No users found.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div className="card bg-base-100 border border-base-300 shadow-sm col-span-1">
          <div className="card-body p-0">
            <div className="flex justify-between items-center p-6 pb-2">
              <h2 className="card-title text-lg flex items-center gap-2">
                <Key className="w-5 h-5" /> API Keys
              </h2>
              <button className="btn btn-sm btn-primary">Create Key</button>
            </div>
            <div className="p-6 pt-2 space-y-4">
               {apiKeys.length === 0 ? (
                 <p className="text-sm text-base-content/60 italic text-center py-4">No API keys generated.</p>
               ) : (
                 apiKeys.map((k: any) => (
                   <div key={k.id} className="border border-base-300 rounded-lg p-3 bg-base-200">
                     <div className="flex justify-between items-center mb-1">
                       <span className="font-semibold text-sm">{k.name}</span>
                       <span className="badge badge-ghost badge-xs">{k.scopes || 'Full'}</span>
                     </div>
                     <span className="font-mono text-xs opacity-70 border border-dashed border-base-300 px-2 py-0.5 rounded">{k.key_prefix}••••••••••</span>
                   </div>
                 ))
               )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
