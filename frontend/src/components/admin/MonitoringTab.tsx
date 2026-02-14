import React, { useEffect, useMemo, useState } from 'react';
import { api } from '../../services/api';
import type { FlowDropItem, HealthCheckItem, MonitoringUxLogItem, TechnicalErrorItem } from '../../types';

type Tab = 'ERRORS' | 'UX' | 'HEALTH';

type ExportKind = 'technical_errors' | 'ux_logs' | 'flow_drop_stats';

function downloadBlob(blob: Blob, filename: string) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
}

const MonitoringTab: React.FC = () => {
    const [tab, setTab] = useState<Tab>('ERRORS');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const [representativeId, setRepresentativeId] = useState<string>('');
    const [startDate, setStartDate] = useState<string>('');
    const [endDate, setEndDate] = useState<string>('');

    const repIdNum = useMemo(() => {
        const v = representativeId.trim();
        if (!v) return null;
        const n = Number(v);
        return Number.isFinite(n) ? n : null;
    }, [representativeId]);

    const [errors, setErrors] = useState<TechnicalErrorItem[]>([]);
    const [uxLogs, setUxLogs] = useState<MonitoringUxLogItem[]>([]);
    const [healthChecks, setHealthChecks] = useState<HealthCheckItem[]>([]);
    const [flowDrops, setFlowDrops] = useState<FlowDropItem[]>([]);

    const token = useMemo(() => localStorage.getItem('access_token') || '', []);

    const load = async () => {
        if (!token) {
            setError('برای مشاهده Monitoring باید وارد شوید.');
            return;
        }
        setLoading(true);
        setError(null);
        try {
            if (tab === 'ERRORS') {
                const data = await api.getMonitoringErrors(token, {
                    representativeId: repIdNum,
                    startDate: startDate || null,
                    endDate: endDate || null,
                    limit: 500,
                });
                setErrors(data || []);
            } else if (tab === 'UX') {
                const [logs, drops] = await Promise.all([
                    api.getMonitoringUxLogs(token, {
                        representativeId: repIdNum,
                        startDate: startDate || null,
                        endDate: endDate || null,
                        limit: 1000,
                    }),
                    api.getMonitoringFlowDrops(token, repIdNum),
                ]);
                setUxLogs(logs || []);
                setFlowDrops(drops || []);
            } else {
                const data = await api.getMonitoringHealthChecks(token, {
                    representativeId: repIdNum,
                    limit: 500,
                });
                setHealthChecks(data || []);
            }
        } catch (e: any) {
            setError(e?.message || 'خطا در دریافت داده‌ها');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        load();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [tab]);

    const onExport = async (kind: ExportKind) => {
        if (!token) return;
        setLoading(true);
        setError(null);
        try {
            if (kind === 'technical_errors') {
                const blob = await api.exportMonitoringErrorsXlsx(token, {
                    representativeId: repIdNum,
                    startDate: startDate || null,
                    endDate: endDate || null,
                });
                downloadBlob(blob, 'monitoring_errors.xlsx');
            } else if (kind === 'ux_logs') {
                const blob = await api.exportMonitoringUxLogsXlsx(token, {
                    representativeId: repIdNum,
                    startDate: startDate || null,
                    endDate: endDate || null,
                });
                downloadBlob(blob, 'monitoring_ux_logs.xlsx');
            } else {
                const blob = await api.exportMonitoringFlowDropsXlsx(token, repIdNum);
                downloadBlob(blob, 'monitoring_flow_drops.xlsx');
            }
        } catch (e: any) {
            setError(e?.message || 'خطا در خروجی گرفتن');
        } finally {
            setLoading(false);
        }
    };

    const tabButton = (id: Tab, label: string) => (
        <button
            onClick={() => setTab(id)}
            className={`px-4 py-2 rounded-xl text-sm font-bold transition-all ${tab === id ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 border hover:bg-gray-50'}`}
        >
            {label}
        </button>
    );

    return (
        <div className="space-y-4">
            <div className="bg-white rounded-2xl border p-4">
                <div className="flex items-center justify-between gap-3 flex-wrap">
                    <div className="flex items-center gap-2 flex-wrap">
                        {tabButton('ERRORS', 'Errors')}
                        {tabButton('UX', 'UX Logs')}
                        {tabButton('HEALTH', 'Health Checks')}
                    </div>

                    <div className="flex items-center gap-2 flex-wrap">
                        <input
                            value={representativeId}
                            onChange={(e) => setRepresentativeId(e.target.value)}
                            placeholder="Representative ID"
                            className="border rounded-xl px-3 py-2 text-sm w-40"
                        />
                        <input
                            value={startDate}
                            onChange={(e) => setStartDate(e.target.value)}
                            placeholder="Start date (YYYY-MM-DD)"
                            className="border rounded-xl px-3 py-2 text-sm w-48"
                        />
                        <input
                            value={endDate}
                            onChange={(e) => setEndDate(e.target.value)}
                            placeholder="End date (YYYY-MM-DD)"
                            className="border rounded-xl px-3 py-2 text-sm w-48"
                        />
                        <button
                            onClick={load}
                            className="bg-gray-900 text-white px-4 py-2 rounded-xl text-sm font-bold"
                            disabled={loading}
                        >
                            Refresh
                        </button>
                    </div>
                </div>

                {error && <div className="mt-3 text-sm text-red-600">{error}</div>}
                {loading && <div className="mt-3 text-sm text-gray-500">Loading...</div>}
            </div>

            {tab === 'ERRORS' && (
                <div className="bg-white rounded-2xl border p-4">
                    <div className="flex items-center justify-between">
                        <h2 className="font-bold">Technical Errors</h2>
                        <button
                            onClick={() => onExport('technical_errors')}
                            className="border px-3 py-2 rounded-xl text-sm font-bold hover:bg-gray-50"
                            disabled={loading}
                        >
                            Export Excel
                        </button>
                    </div>
                    <div className="mt-3 overflow-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="text-gray-500">
                                    <th className="text-right p-2">ID</th>
                                    <th className="text-right p-2">Time</th>
                                    <th className="text-right p-2">Service</th>
                                    <th className="text-right p-2">Type</th>
                                    <th className="text-right p-2">Message</th>
                                    <th className="text-right p-2">User</th>
                                    <th className="text-right p-2">Rep</th>
                                    <th className="text-right p-2">State</th>
                                </tr>
                            </thead>
                            <tbody>
                                {errors.map((r) => (
                                    <tr key={r.error_id} className="border-t">
                                        <td className="p-2">{r.error_id}</td>
                                        <td className="p-2">{r.timestamp}</td>
                                        <td className="p-2">{r.service_name}</td>
                                        <td className="p-2">{r.error_type}</td>
                                        <td className="p-2 max-w-[520px] whitespace-pre-wrap">{r.error_message}</td>
                                        <td className="p-2">{r.user_id || '-'}</td>
                                        <td className="p-2">{r.representative_id ?? '-'}</td>
                                        <td className="p-2">{r.state || '-'}</td>
                                    </tr>
                                ))}
                                {!errors.length && !loading && <tr><td className="p-2 text-gray-500" colSpan={8}>No data</td></tr>}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {tab === 'UX' && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    <div className="bg-white rounded-2xl border p-4">
                        <div className="flex items-center justify-between">
                            <h2 className="font-bold">UX Logs</h2>
                            <button
                                onClick={() => onExport('ux_logs')}
                                className="border px-3 py-2 rounded-xl text-sm font-bold hover:bg-gray-50"
                                disabled={loading}
                            >
                                Export Excel
                            </button>
                        </div>
                        <div className="mt-3 overflow-auto">
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="text-gray-500">
                                        <th className="text-right p-2">ID</th>
                                        <th className="text-right p-2">Time</th>
                                        <th className="text-right p-2">Action</th>
                                        <th className="text-right p-2">Expected</th>
                                        <th className="text-right p-2">State</th>
                                        <th className="text-right p-2">User</th>
                                        <th className="text-right p-2">Rep</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {uxLogs.map((r) => (
                                        <tr key={r.log_id} className="border-t">
                                            <td className="p-2">{r.log_id}</td>
                                            <td className="p-2">{r.timestamp}</td>
                                            <td className="p-2">{r.action}</td>
                                            <td className="p-2">{r.expected_action || '-'}</td>
                                            <td className="p-2">{r.current_state || '-'}</td>
                                            <td className="p-2">{r.user_id}</td>
                                            <td className="p-2">{r.representative_id}</td>
                                        </tr>
                                    ))}
                                    {!uxLogs.length && !loading && <tr><td className="p-2 text-gray-500" colSpan={7}>No data</td></tr>}
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <div className="bg-white rounded-2xl border p-4">
                        <div className="flex items-center justify-between">
                            <h2 className="font-bold">Flow Drops</h2>
                            <button
                                onClick={() => onExport('flow_drop_stats')}
                                className="border px-3 py-2 rounded-xl text-sm font-bold hover:bg-gray-50"
                                disabled={loading}
                            >
                                Export Excel
                            </button>
                        </div>
                        <div className="mt-3 overflow-auto">
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="text-gray-500">
                                        <th className="text-right p-2">Flow</th>
                                        <th className="text-right p-2">Started</th>
                                        <th className="text-right p-2">Completed</th>
                                        <th className="text-right p-2">Abandoned</th>
                                        <th className="text-right p-2">Updated</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {flowDrops.map((r) => (
                                        <tr key={r.id} className="border-t">
                                            <td className="p-2">{r.flow_type}</td>
                                            <td className="p-2">{r.started_count}</td>
                                            <td className="p-2">{r.completed_count}</td>
                                            <td className="p-2">{r.abandoned_count}</td>
                                            <td className="p-2">{r.updated_at}</td>
                                        </tr>
                                    ))}
                                    {!flowDrops.length && !loading && <tr><td className="p-2 text-gray-500" colSpan={5}>No data</td></tr>}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            )}

            {tab === 'HEALTH' && (
                <div className="bg-white rounded-2xl border p-4">
                    <div className="flex items-center justify-between">
                        <h2 className="font-bold">Health Checks</h2>
                    </div>
                    <div className="mt-3 overflow-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="text-gray-500">
                                    <th className="text-right p-2">Time</th>
                                    <th className="text-right p-2">Rep</th>
                                    <th className="text-right p-2">Check</th>
                                    <th className="text-right p-2">Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                {healthChecks.map((r) => (
                                    <tr key={r.id} className="border-t">
                                        <td className="p-2">{r.timestamp}</td>
                                        <td className="p-2">{r.representative_id ?? '-'}</td>
                                        <td className="p-2">{r.check_type}</td>
                                        <td className={`p-2 font-bold ${r.status === 'ok' ? 'text-green-600' : 'text-red-600'}`}>{r.status}</td>
                                    </tr>
                                ))}
                                {!healthChecks.length && !loading && <tr><td className="p-2 text-gray-500" colSpan={4}>No data</td></tr>}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
        </div>
    );
};

export default MonitoringTab;
