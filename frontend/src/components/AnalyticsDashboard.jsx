import React, { useEffect, useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

export default function AnalyticsDashboard() {
    const [stats, setStats] = useState(null);

    useEffect(() => {
        fetch('http://localhost:8000/api/stats')
            .then(res => res.json())
            .then(data => setStats(data))
            .catch(err => console.error(err));
    }, []);

    if (!stats) return <div className="p-10 text-center">Loading Analytics...</div>;

    const pieData = [
        { name: 'Safe', value: stats.safe_sites },
        { name: 'Phishing', value: stats.phishing_detected },
    ];
    const COLORS = ['#00C49F', '#FF8042'];

    return (
        <div className="space-y-6">
            {/* Top Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <StatCard title="Total Scans" value={stats.total_scans} icon="🔍" />
                <StatCard title="Phishing Detected" value={stats.phishing_detected} color="text-error" icon="⚠️" />
                <StatCard title="Safe Sites" value={stats.safe_sites} color="text-success" icon="✅" />
                <StatCard title="Model Accuracy" value={(stats.model_performance.accuracy * 100).toFixed(1) + "%"} icon="🎯" />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Trend Chart */}
                <div className="card bg-base-100 shadow-xl">
                    <div className="card-body">
                        <h2 className="card-title">Weekly Detection Trends</h2>
                        <div className="h-64 w-full">
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={stats.trends}>
                                    <CartesianGrid strokeDasharray="3 3" />
                                    <XAxis dataKey="name" />
                                    <YAxis />
                                    <Tooltip />
                                    <Legend />
                                    <Bar dataKey="safe" fill="#00C49F" name="Safe" />
                                    <Bar dataKey="phishing" fill="#FF8042" name="Phishing" />
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    </div>
                </div>

                {/* Distribution Chart */}
                <div className="card bg-base-100 shadow-xl">
                    <div className="card-body">
                        <h2 className="card-title">Threat Distribution</h2>
                        <div className="h-64 w-full flex justify-center">
                            <ResponsiveContainer width="100%" height="100%">
                                <PieChart>
                                    <Pie
                                        data={pieData}
                                        cx="50%"
                                        cy="50%"
                                        innerRadius={60}
                                        outerRadius={80}
                                        fill="#8884d8"
                                        paddingAngle={5}
                                        dataKey="value"
                                    >
                                        {pieData.map((entry, index) => (
                                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                        ))}
                                    </Pie>
                                    <Tooltip />
                                    <Legend />
                                </PieChart>
                            </ResponsiveContainer>
                        </div>
                    </div>
                </div>
            </div>

            {/* Model Performance Table */}
            <div className="card bg-base-100 shadow-xl">
                <div className="card-body">
                    <h2 className="card-title">Model Performance Metrics</h2>
                    <div className="overflow-x-auto">
                        <table className="table w-full">
                            <thead>
                                <tr>
                                    <th>Metric</th>
                                    <th>Score</th>
                                    <th>Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td>Accuracy</td>
                                    <td>{(stats.model_performance.accuracy * 100).toFixed(1)}%</td>
                                    <td><progress className="progress progress-success w-56" value={stats.model_performance.accuracy * 100} max="100"></progress></td>
                                </tr>
                                <tr>
                                    <td>Precision</td>
                                    <td>{(stats.model_performance.precision * 100).toFixed(1)}%</td>
                                    <td><progress className="progress progress-info w-56" value={stats.model_performance.precision * 100} max="100"></progress></td>
                                </tr>
                                <tr>
                                    <td>Recall</td>
                                    <td>{(stats.model_performance.recall * 100).toFixed(1)}%</td>
                                    <td><progress className="progress progress-warning w-56" value={stats.model_performance.recall * 100} max="100"></progress></td>
                                </tr>
                                <tr>
                                    <td>F1 Score</td>
                                    <td>{(stats.model_performance.f1 * 100).toFixed(1)}%</td>
                                    <td><progress className="progress progress-primary w-56" value={stats.model_performance.f1 * 100} max="100"></progress></td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    );
}

function StatCard({ title, value, color = "", icon }) {
    return (
        <div className="stats shadow">
            <div className="stat">
                <div className="stat-figure text-secondary text-3xl">{icon}</div>
                <div className="stat-title">{title}</div>
                <div className={`stat-value ${color}`}>{value}</div>
            </div>
        </div>
    );
}
