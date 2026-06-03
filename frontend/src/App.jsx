import { useState, useEffect, useRef, useCallback } from "react";
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

  // Ref para leer el valor actual de scanning dentro de callbacks/intervals
  // sin depender del closure stale
  const scanningRef = useRef(false);

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
      scanningRef.current = s.scanning;
      setNextScan(s.next_run);
      if (s.interval_minutes) setScanInterval(s.interval_minutes);
      return s.scanning; // devuelve el valor actual para usarlo en cadena
    } catch {
      return false;
    }
  }, []);

  useEffect(() => {
    loadDevices();
    loadScans();
    loadScanStatus();
  }, [loadDevices, loadScans, loadScanStatus]);

  // Polling: se activa solo cuando hay un escaneo en curso (iniciado por el scheduler).
  // Para el escaneo manual, handleStartScan ya es sincrónico y recarga al terminar.
  useEffect(() => {
    if (!scanning) return;

    const interval = setInterval(async () => {
      const stillScanning = await loadScanStatus();
      // Ahora usamos el valor de retorno real, no el closure stale
      if (!stillScanning) {
        await loadDevices();
        await loadScans();
        clearInterval(interval);
      }
    }, 4000);

    return () => clearInterval(interval);
  }, [scanning, loadDevices, loadScans, loadScanStatus]);

  // FIX PRINCIPAL: startScan ya es sincrónico en el backend
  // (el endpoint /discover bloquea hasta terminar el pipeline completo).
  // Solo hay que recargar los datos DESPUÉS de que la promesa resuelva.
  const handleStartScan = async () => {
    setScanError("");
    setScanning(true);
    scanningRef.current = true;
    try {
      await api.startScan(); // espera a que el backend termine todo el pipeline
      // El escaneo terminó → recargar dispositivos y scans
      await loadDevices();
      await loadScans();
    } catch (err) {
      setScanError(err.message);
    } finally {
      setScanning(false);
      scanningRef.current = false;
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
    // FIX TEMA: bg-gray-950 igual que LoginPage y demás pantallas
    <div className="min-h-screen bg-gray-950">
      {isDefaultPassword && (
        <div className="bg-yellow-500 text-yellow-900 text-sm font-medium px-4 py-2 text-center">
          ⚠️ Estás usando la contraseña por defecto.{" "}
          <button onClick={() => setShowChangePassword(true)} className="underline font-bold">
            Cámbiala ahora
          </button>
        </div>
      )}

      {/* Header oscuro */}
      <header className="bg-gray-900 border-b border-gray-800 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-2xl">🏠</span>
          <h1 className="font-bold text-lg text-white">Smart Home Vulnerability Manager</h1>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setView(view === "devices" ? "settings" : "devices")}
            className="text-gray-400 hover:text-white px-3 py-1.5 rounded text-sm transition"
          >
            {view === "devices" ? "⚙️ Ajustes" : "← Volver"}
          </button>
          <button
            onClick={logout}
            className="text-gray-400 hover:text-white px-3 py-1.5 rounded text-sm transition"
          >
            Salir
          </button>
        </div>
      </header>

      {view === "devices" ? (
        <main className="max-w-6xl mx-auto px-4 py-8">
          {/* Tarjetas de stats — tema oscuro */}
          <div className="grid grid-cols-3 gap-4 mb-8">
            <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
              <p className="text-3xl font-bold text-blue-400">{onlineCount}</p>
              <p className="text-gray-400 text-sm">Dispositivos</p>
            </div>
            <div
              className={`bg-gray-900 rounded-xl p-4 border ${
                criticalCount > 0 ? "border-red-700" : "border-gray-800"
              }`}
            >
              <p className="text-3xl font-bold text-red-400">{criticalCount}</p>
              <p className="text-gray-400 text-sm">Críticas</p>
            </div>
            <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
              <p className="text-3xl font-bold text-gray-300">{totalVulns}</p>
              <p className="text-gray-400 text-sm">Total Vulnerabilidades</p>
            </div>
          </div>

          {/* Barra de acción */}
          <div className="flex items-center gap-4 mb-8">
            <button
              onClick={handleStartScan}
              disabled={scanning}
              className="px-6 py-3 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-semibold transition"
            >
              {scanning ? "Escaneando red… (puede tomar 1-2 min)" : "🔍 Escanear red ahora"}
            </button>
            <div className="text-sm text-gray-400">
              {lastScan && (
                <span>
                  Último: {new Date(lastScan.started_at).toLocaleString("es")} ·{" "}
                  {lastScan.devices_found} disp.
                </span>
              )}
              {nextScan && (
                <span className="ml-3">
                  Próximo: {new Date(nextScan).toLocaleString("es", { timeStyle: "short" })}
                </span>
              )}
            </div>
          </div>

          {scanError && (
            <div className="mb-6 bg-red-900/40 border border-red-700 rounded px-4 py-3 text-red-300 text-sm">
              {scanError}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {devices.map((d) => (
              <DeviceCard
                key={d.id}
                device={d}
                onClick={(device) => {
                  setSelectedDevice(device.id);
                }}
                onVulnResolved={handleVulnResolved}
              />
            ))}
          </div>
        </main>
      ) : (
        <main className="max-w-2xl mx-auto px-4 py-8">
          {/* Panel de ajustes — tema oscuro */}
          <div className="bg-gray-900 rounded-2xl p-8 border border-gray-800">
            <h2 className="text-xl font-bold text-white mb-6">Ajustes</h2>

            <label className="block text-sm font-medium text-gray-300 mb-2">
              Escaneo automático cada (minutos)
            </label>
            <input
              type="number"
              min="0"
              value={scanInterval}
              onChange={(e) => setScanInterval(Number(e.target.value))}
              className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg
                         text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <p className="text-xs text-gray-500 mt-1">
              La red se escanea automáticamente cada N minutos. 0 = desactivar.
            </p>

            <button
              onClick={handleSaveInterval}
              className="mt-4 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-500 transition"
            >
              Guardar
            </button>

            <hr className="my-8 border-gray-800" />

            <button
              onClick={() => setShowChangePassword(true)}
              className="w-full py-3 border border-gray-700 rounded-lg text-gray-300
                         hover:bg-gray-800 transition"
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
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="text-gray-400">Cargando…</div>
      </div>
    );
  }

  return token ? <Dashboard /> : <LoginPage />;
}

export default AppContent;