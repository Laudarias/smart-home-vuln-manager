import { useState, useEffect, useCallback } from "react";
import { useAuth } from "./context/AuthContext";
import LoginPage from "./components/LoginPage";
import DeviceCard from "./components/DeviceCard";
import VulnerabilityModal from "./components/VulnerabilityModal";
import ChangePassword from "./components/ChangePassword";
import { api } from "./api/client";

function Dashboard() {
  const { logout, isDefaultPassword, setIsDefaultPassword } = useAuth();
  const [view, setView] = useState("devices");
  const [devices, setDevices] = useState([]);
  const [scans, setScans] = useState([]);
  const [scanning, setScanning] = useState(false);
  const [scanError, setScanError] = useState("");
  const [nextScan, setNextScan] = useState(null);
  const [scanInterval, setScanInterval] = useState(60);
  const [selectedVuln, setSelectedVuln] = useState(null);
  const [selectedDevice, setSelectedDevice] = useState(null);
  const [showChangePassword, setShowChangePassword] = useState(false);

  const loadDevices = useCallback(async () => {
    try {
      const data = await api.listDevices();
      setDevices(data);
    } catch {}
  }, []);

  const loadScans = useCallback(async () => {
    try {
      const data = await api.listScans();
      setScans(data);
    } catch {}
  }, []);

  const loadScanStatus = useCallback(async () => {
    try {
      const s = await api.scanStatus();
      setScanning(s.scanning);
      setNextScan(s.next_run);
      if (s.interval_minutes) setScanInterval(s.interval_minutes);
    } catch {}
  }, []);

  useEffect(() => {
    loadDevices();
    loadScans();
    loadScanStatus();
  }, [loadDevices, loadScans, loadScanStatus]);

  useEffect(() => {
    if (!scanning) return;
    const interval = setInterval(() => {
      loadScanStatus().then(() => {
        if (!scanning) {
          loadDevices();
          loadScans();
        }
      });
    }, 4000);
    return () => clearInterval(interval);
  }, [scanning, loadDevices, loadScans, loadScanStatus]);

  const handleStartScan = async () => {
    setScanError("");
    setScanning(true);
    try {
      await api.startScan();
      await loadDevices();
      await loadScans();
    } catch (err) {
      setScanError(err.message);
    } finally {
      setScanning(false);
    }
  };

  const handleVulnResolved = (deviceId, vulnId) => {
    setDevices((prev) =>
      prev.map((d) =>
        d.id === deviceId
          ? {
              ...d,
              vulnerabilities: d.vulnerabilities.map((v) =>
                v.id === vulnId ? { ...v, status: "resolved" } : v
              ),
              vuln_summary: {
                ...d.vuln_summary,
                [selectedVuln?.severity]: Math.max(
                  0,
                  (d.vuln_summary[selectedVuln?.severity] || 0) - 1
                ),
              },
            }
          : d
      )
    );
    setSelectedVuln(null);
  };

  const handleSaveInterval = async () => {
    try {
      await api.setInterval(scanInterval);
      await loadScanStatus();
      setView("devices");
    } catch {}
  };

  const onlineCount = devices.filter((d) => d.status === "active").length;
  const criticalCount = devices.reduce((s, d) => s + (d.vuln_summary?.critical || 0), 0);
  const totalVulns = devices.reduce(
    (s, d) => s + Object.values(d.vuln_summary || {}).reduce((a, b) => a + b, 0),
    0
  );
  const lastScan = scans[0];

  return (
    <div className="min-h-screen bg-gray-50">
      {isDefaultPassword && (
        <div className="bg-yellow-500 text-yellow-900 text-sm font-medium px-4 py-2 text-center">
          ⚠️ Estás usando la contraseña por defecto.{" "}
          <button onClick={() => setShowChangePassword(true)} className="underline font-bold">
            Cámbiala ahora
          </button>
        </div>
      )}

      <header className="bg-white border-b px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-2xl">🏠</span>
          <h1 className="font-bold text-lg">Smart Home Vulnerability Manager</h1>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setView(view === "devices" ? "settings" : "devices")}
            className="text-gray-600 hover:text-gray-900 px-3 py-1.5 rounded text-sm"
          >
            {view === "devices" ? "⚙️ Ajustes" : "← Volver"}
          </button>
          <button onClick={logout} className="text-gray-600 hover:text-gray-900 px-3 py-1.5 rounded text-sm">
            Salir
          </button>
        </div>
      </header>

      {view === "devices" ? (
        <main className="max-w-6xl mx-auto px-4 py-8">
          <div className="grid grid-cols-3 gap-4 mb-8">
            <div className="bg-white rounded-lg p-4 shadow-sm">
              <p className="text-3xl font-bold text-blue-600">{onlineCount}</p>
              <p className="text-gray-600 text-sm">Dispositivos</p>
            </div>
            <div className={`bg-white rounded-lg p-4 shadow-sm ${criticalCount > 0 ? "border-2 border-red-500" : ""}`}>
              <p className="text-3xl font-bold text-red-600">{criticalCount}</p>
              <p className="text-gray-600 text-sm">Críticas</p>
            </div>
            <div className="bg-white rounded-lg p-4 shadow-sm">
              <p className="text-3xl font-bold text-gray-700">{totalVulns}</p>
              <p className="text-gray-600 text-sm">Total Vulnerabilidades</p>
            </div>
          </div>

          <div className="flex items-center gap-4 mb-8">
            <button
              onClick={handleStartScan}
              disabled={scanning}
              className="px-6 py-3 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-semibold"
            >
              {scanning ? "Escaneando red… (puede tomar 1-2 min)" : "🔍 Escanear red ahora"}
            </button>
            <div className="text-sm text-gray-600">
              {lastScan && (
                <span>
                  Último: {new Date(lastScan.started_at).toLocaleString("es")} · {lastScan.devices_found} disp.
                </span>
              )}
              {nextScan && (
                <span className="ml-3">
                  Próximo: {new Date(nextScan).toLocaleString("es", { timeStyle: "short" })}
                </span>
              )}
            </div>
          </div>

          {scanError && <div className="mb-6 bg-red-100 border border-red-400 rounded px-4 py-3 text-red-700 text-sm">{scanError}</div>}

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {devices.map((d) => (
              <DeviceCard key={d.id} device={d} onVulnResolved={handleVulnResolved} />
            ))}
          </div>
        </main>
      ) : (
        <main className="max-w-2xl mx-auto px-4 py-8">
          <div className="bg-white rounded-lg p-8 shadow-sm">
            <h2 className="text-xl font-bold mb-6">Ajustes</h2>

            <label className="block text-sm font-medium text-gray-700 mb-2">
              Escaneo automático cada (minutos)
            </label>
            <input
              type="number"
              min="0"
              value={scanInterval}
              onChange={(e) => setScanInterval(Number(e.target.value))}
              className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <p className="text-xs text-gray-500 mt-1">La red se escanea automáticamente cada N minutos. 0 = desactivar.</p>

            <button onClick={handleSaveInterval} className="mt-4 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
              Guardar
            </button>

            <hr className="my-8" />

            <button
              onClick={() => setShowChangePassword(true)}
              className="w-full py-3 border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              🔑 Cambiar contraseña
            </button>
          </div>
        </main>
      )}

      {selectedVuln && (
        <VulnerabilityModal
          vuln={selectedVuln}
          deviceId={selectedDevice}
          onClose={() => setSelectedVuln(null)}
          onResolved={handleVulnResolved}
        />
      )}

      {showChangePassword && (
        <ChangePassword
          onClose={() => {
            setShowChangePassword(false);
            setIsDefaultPassword(false);
          }}
        />
      )}
    </div>
  );
}

function AppContent() {
  const { token, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500">Cargando…</div>
      </div>
    );
  }

  return token ? <Dashboard /> : <LoginPage />;
}

export default AppContent;
