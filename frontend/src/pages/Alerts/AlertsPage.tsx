import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { alertsApi, SecurityAlert } from '../../api/alerts';
import { Bell, ShieldAlert, CheckCircle, Clock } from 'lucide-react';

export const AlertsPage = () => {
    const queryClient = useQueryClient();
    const { data: alerts = [], isLoading } = useQuery({
        queryKey: ['alerts'],
        queryFn: () => alertsApi.getAlerts()
    });

    const statusMutation = useMutation({
        mutationFn: ({ id, status }: { id: number, status: 'acknowledged' | 'resolved' }) => 
            alertsApi.updateAlertStatus(id, status),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['alerts'] });
        }
    });

    if (isLoading) return <div className="flex justify-center p-12"><span className="loading loading-spinner loading-lg"></span></div>;

    const severityColor = (sev: string) => {
        switch (sev) {
            case 'critical': return 'text-error';
            case 'high': return 'text-warning';
            case 'medium': return 'text-info';
            default: return 'text-success';
        }
    };

    const typeLabel = (type: string) => {
        return type.replace(/_/g, ' ');
    };

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center bg-base-100 p-6 rounded-xl border border-base-300 shadow-sm">
                <div>
                    <h1 className="text-2xl font-bold flex items-center gap-2">
                        <Bell className="w-6 h-6 text-primary" />
                        Security Alerts
                    </h1>
                    <p className="text-base-content/60">Manage and respond to real-time security threats.</p>
                </div>
                <div className="flex gap-2">
                    <div className="badge badge-error gap-1 p-3">
                        {alerts.filter(a => a.severity === 'critical' && a.status !== 'resolved').length} Critical
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 gap-4">
                {alerts.map((alert: SecurityAlert) => (
                    <div key={alert.id} className={`card bg-base-100 border border-base-300 shadow-sm hover:shadow-md transition-shadow ${alert.status === 'resolved' ? 'opacity-60' : ''}`}>
                        <div className="card-body p-6">
                            <div className="flex justify-between items-start">
                                <div className="flex gap-4">
                                    <div className={`p-3 rounded-full bg-base-200 ${severityColor(alert.severity)}`}>
                                        <ShieldAlert className="w-6 h-6" />
                                    </div>
                                    <div>
                                        <div className="flex items-center gap-2 mb-1">
                                            <span className={`text-xs font-black uppercase tracking-wider ${severityColor(alert.severity)}`}>
                                                {alert.severity}
                                            </span>
                                            <span className="text-base-content/30">•</span>
                                            <span className="text-xs font-medium text-base-content/50">
                                                {new Date(alert.created_at).toLocaleString()}
                                            </span>
                                        </div>
                                        <h3 className="text-lg font-bold">{typeLabel(alert.alert_type)}</h3>
                                        <div className="mt-2 flex flex-col gap-1">
                                            {alert.url && <div className="text-sm font-mono truncate max-w-md"><span className="text-base-content/50">URL:</span> {alert.url}</div>}
                                            {alert.domain && <div className="text-sm font-mono"><span className="text-base-content/50">Domain:</span> {alert.domain}</div>}
                                        </div>
                                    </div>
                                </div>
                                <div className="flex flex-col gap-2">
                                    <div className="flex items-center gap-2">
                                        <span className={`badge badge-sm ${
                                            alert.status === 'open' ? 'badge-error' : 
                                            alert.status === 'acknowledged' ? 'badge-warning' : 'badge-success'
                                        }`}>
                                            {alert.status}
                                        </span>
                                    </div>
                                    <div className="flex gap-2 mt-2">
                                        {alert.status === 'open' && (
                                            <button 
                                                onClick={() => statusMutation.mutate({ id: alert.id, status: 'acknowledged' })}
                                                className="btn btn-ghost btn-xs border border-base-300"
                                            >
                                                <Clock className="w-3 h-3 mr-1" /> Acknowledge
                                            </button>
                                        )}
                                        {alert.status !== 'resolved' && (
                                            <button 
                                                onClick={() => statusMutation.mutate({ id: alert.id, status: 'resolved' })}
                                                className="btn btn-ghost btn-xs border border-base-300 hover:bg-success hover:text-success-content"
                                            >
                                                <CheckCircle className="w-3 h-3 mr-1" /> Resolve
                                            </button>
                                        )}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                ))}

                {alerts.length === 0 && (
                    <div className="bg-base-100 p-20 text-center rounded-xl border border-dashed border-base-300">
                        <CheckCircle className="w-12 h-12 mx-auto mb-4 text-success opacity-30" />
                        <h3 className="text-xl font-bold opacity-50">All Clear!</h3>
                        <p className="opacity-40">No security alerts found for your tenant.</p>
                    </div>
                )}
            </div>
        </div>
    );
};
