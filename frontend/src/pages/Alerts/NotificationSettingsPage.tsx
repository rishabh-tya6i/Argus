import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { alertsApi, NotificationChannel } from '../../api/alerts';
import { Settings, Slack, Mail, Globe, Trash2, Plus, Info } from 'lucide-react';

export const NotificationSettingsPage = () => {
    const queryClient = useQueryClient();
    const [newChannelType, setNewChannelType] = useState<string>('slack');
    const [config, setConfig] = useState<string>('');

    const { data: channels = [], isLoading } = useQuery({
        queryKey: ['notification-channels'],
        queryFn: alertsApi.getNotificationChannels
    });

    const createMutation = useMutation({
        mutationFn: (payload: { type: string, config: any }) => alertsApi.createNotificationChannel(payload),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['notification-channels'] });
            setConfig('');
        }
    });

    const deleteMutation = useMutation({
        mutationFn: (id: number) => alertsApi.deleteNotificationChannel(id),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['notification-channels'] });
        }
    });

    const handleCreate = (e: React.FormEvent) => {
        e.preventDefault();
        try {
            const parsedConfig = JSON.parse(config);
            createMutation.mutate({ type: newChannelType, config: parsedConfig });
        } catch (err) {
            alert('Invalid JSON config');
        }
    };

    if (isLoading) return <div className="flex justify-center p-12"><span className="loading loading-spinner loading-lg"></span></div>;

    const getIcon = (type: string) => {
        switch (type) {
            case 'slack': return <Slack className="w-5 h-5 text-primary" />;
            case 'email': return <Mail className="w-5 h-5 text-secondary" />;
            case 'webhook': return <Globe className="w-5 h-5 text-info" />;
            default: return <Settings className="w-5 h-5" />;
        }
    };

    const getFriendlyConfig = (channel: NotificationChannel) => {
        if (channel.type === 'slack') return `Webhook: ${channel.config.webhook_url.substring(0, 30)}...`;
        if (channel.type === 'email') return `To: ${channel.config.recipients?.join(', ') || 'user@example.com'}`;
        if (channel.type === 'webhook') return `URL: ${channel.config.url.substring(0, 30)}...`;
        return JSON.stringify(channel.config);
    };

    return (
        <div className="space-y-6">
            <div className="bg-base-100 p-8 rounded-2xl border border-base-300 shadow-sm flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-black mb-1 flex items-center gap-3">
                        <Settings className="w-8 h-8 text-primary" />
                        Notification Channels
                    </h1>
                    <p className="text-base-content/60">Configure where you want to receive security alerts.</p>
                </div>
                <button 
                  className="btn btn-primary btn-sm rounded-lg"
                  onClick={() => (window as any).channel_modal.showModal()}
                >
                  <Plus className="w-4 h-4 mr-1" /> Add Channel
                </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {channels.map((channel: NotificationChannel) => (
                    <div key={channel.id} className="card bg-base-100 border border-base-300 shadow-sm hover:shadow-md transition-all">
                        <div className="card-body p-6">
                            <div className="flex justify-between items-center mb-4">
                                <div className="bg-base-200 p-2 rounded-lg">
                                    {getIcon(channel.type)}
                                </div>
                                <span className="text-xs font-black uppercase tracking-widest text-base-content/40 tracking">
                                    {channel.type}
                                </span>
                            </div>
                            <h3 className="font-bold text-lg mb-1">{channel.type.toUpperCase()} Channel</h3>
                            <p className="text-xs text-base-content/60 break-all h-12 overflow-hidden">
                                {getFriendlyConfig(channel)}
                            </p>
                            <div className="card-actions justify-between items-center mt-6">
                                <div className={`badge badge-sm uppercase font-bold ${channel.is_active ? 'badge-success' : 'badge-ghost opacity-50'}`}>
                                    {channel.is_active ? 'Active' : 'Inactive'}
                                </div>
                                <button 
                                    className="btn btn-ghost btn-sm text-error h-10 w-10 p-0"
                                    onClick={() => deleteMutation.mutate(channel.id)}
                                >
                                    <Trash2 className="w-4 h-4" />
                                </button>
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {channels.length === 0 && (
                <div className="p-20 text-center bg-base-100 rounded-2xl border border-dashed border-base-300">
                    <Info className="w-12 h-12 mx-auto mb-4 opacity-10" />
                    <p className="text-base-content/40 font-medium">No notification channels configured yet.</p>
                </div>
            )}

            {/* Creation Modal */}
            <dialog id="channel_modal" className="modal">
                <div className="modal-box max-w-lg p-8">
                    <h3 className="font-black text-2xl mb-2">New Channel</h3>
                    <p className="text-sm text-base-content/60 mb-6">Select a type and provide JSON configuration.</p>
                    <form onSubmit={handleCreate} className="space-y-6">
                        <div className="form-control">
                            <label className="label text-xs font-black uppercase opacity-60">Type</label>
                            <select 
                                className="select select-bordered select-md w-full rounded-xl"
                                value={newChannelType}
                                onChange={(e) => setNewChannelType(e.target.value)}
                            >
                                <option value="slack">Slack</option>
                                <option value="webhook">Webhook</option>
                                <option value="email">Email</option>
                            </select>
                        </div>
                        <div className="form-control">
                            <label className="label text-xs font-black uppercase opacity-60">Configuration (JSON)</label>
                            <textarea 
                                className="textarea textarea-bordered h-48 font-mono text-xs p-4 rounded-xl leading-relaxed"
                                placeholder={newChannelType === 'slack' ? '{"webhook_url": "..."}' : '{"url": "...", "secret": "..."}'}
                                value={config}
                                onChange={(e) => setConfig(e.target.value)}
                                required
                            />
                            <label className="label">
                                <span className="label-text-alt text-base-content/40 italic">
                                    {newChannelType === 'slack' ? 'Example: {"webhook_url": "https://hooks.slack.com/services/..."}' : 
                                     newChannelType === 'webhook' ? 'Example: {"url": "https://yoursite.com/hook", "secret": "xyz"}' :
                                     'Example: {"recipients": ["alerts@company.com"]}'}
                                </span>
                            </label>
                        </div>
                        <div className="modal-action">
                            <button type="button" className="btn btn-ghost px-6" onClick={() => (window as any).channel_modal.close()}>Cancel</button>
                            <button type="submit" className="btn btn-primary px-8 rounded-lg shadow-lg shadow-primary/20">Create Channel</button>
                        </div>
                    </form>
                </div>
            </dialog>
        </div>
    );
};
