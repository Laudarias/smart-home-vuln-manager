import { useState, useEffect, useCallback } from "react";
import { AuthProvider, useAuth } from "./context/AuthContext";
import LoginPage from "./components/LoginPage";
import DeviceCard from "./components/DeviceCard";
import VulnerabilityModal from "./components/VulnerabilityModal";
import ChangePassword from "./components/ChangePassword";
import { devicesApi, scansApi } from "./api/client";

// ── Dashboard principal ───────────────────────────────────────────────────────

function Dashboard() {
  const { logout, isDefaultPassword } = useAuth();

  const [devices, setDevices]   = useState([]);
  const [scans, setScans]       = useState([]);
  const [scanning, setScanning] = useState(false);
  const [scanError, setScanError] = useState("");
  const [nextScan, setNextScan] = useState(null);
  const [scanInterval, setScanInterval] = useState(60);

  // Modales
  const [selectedDevice, setSelectedDevice] = useState(null);
  const [deviceVulns, setDeviceVulns]       = useState([]);
  const [showChangePassword, setShowChangePassword] = useState(false);
  const [showSettings, setShowSettings]     = useState(false);

  // ── Cargar datos ───────────────────────────────────────────────────────────

  const loadDevices = useCallback(async () => {
    try {
      const data = await devicesApi.getAll();
      setDevices(data);
    } catch {}
  }, []);

  const loadScans = useCallback(async () => {
    try {
      const data = await scansApi.getAll();
      setScans(data);
    } catch {}
  }, []);

  const loadScanStatus = useCallback(async () => {
    try {
      const s = await scansApi.getStatus();
      setScanning(s.scanning);
      setNextScan(s.next_scheduled_scan);
    } catch {}
  }, []);

  useEffect(() => {
    loadDevices();
    loadScans();
    loadScanStatus();
  }, [loadDevices, loadScans, loadScanStatus]);

  // Polling mientras hay un escaneo en curso
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

  // ── Acciones ───────────────────────────────────────────────────────────────

  const handleStartScan = async () => {
    setScanError("");
    setScanning(true);
    try {
      await scansApi.startScan();
      await loadDevices();
      await loadScans();
    } catch (err) {
      setScanError(err.message);
    } finally {
      setScanning(false);
    }
  };

  const handleSelectDevice = async (device) => {
    setSelectedDevice(device);
    try {
      const vulns = await devicesApi.getVulnerabilities(device.id);
      setDeviceVulns(vulns);
    } catch {
      setDeviceVulns([]);
    }
  };

  const handleSaveSettings = async () => {
    try {
      await scansApi.updateSettings(scanInterval);
      await loadScanStatus();
      setShowSettings(false);
    } catch {}
  };

  // ── Estadísticas rápidas ──────────────────────────────────────────────────
  const onlineCount   = devices.filter((d) => d.status === "online").length;
  const criticalCount = devices.reduce((s, d) => s + (d.vuln_critical || 0), 0);
  const highCount     = devices.reduce((s, d) => s + (d.vuln_high || 0), 0);
  const lastScan      = scans[0];

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Banner contraseña por defecto */}
      {isDefaultPassword && (
        <div className="bg-yellow-600 text-yellow-950 text-sm font-medium px-4 py-2 text-center">
          ⚠️ Estás usando la contraseña por defecto.{" "}
          <button
            onClick={() => setShowChangePassword(true)}
            className="underline font-bold"
          >
            Cámbiala ahora
          </button>
        </div>
      )}

      {/* Navbar */}
      <header className="border-b border-gray-800 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-2xl">🏠</span>
          <h1 className="font-bold text-lg">Smart Home Scanner</h1>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowSettings(true)}
            className="text-gray-400 hover:text-white px-3 py-1.5 rounded-lg
                       hover:bg-gray-800 transition text-sm"
          >
            ⚙️ Ajustes
          </button>
          <button
            onClick={logout}
            className="text-gray-400 hover:text-white px-3 py-1.5 rounded-lg
                       hover:bg-gray-800 transition text-sm"
          >
            Cerrar sesión
          </button>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-8">
        {/* Resumen */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
          {[
            { label: "Dispositivos activos", value: onlineCount, color: "text-blue-400" },
            { label: "Total detectados",      value: devices.length, color: "text-gray-300" },
            { label: "Vulnerabilidades críticas", value: criticalCount, color: "text-red-400" },
            { label: "Vulnerabilidades altas",    value: highCount,    color: "text-orange-400" },
          ].map(({ label, value, color }) => (
            <div key={label} className="bg-gray-900 rounded-2xl p-4">
              <p className={`text-3xl font-bold ${color}`}>{value}</p>
              <p className="text-gray-400 text-xs mt-1">{label}</p>
            </div>
          ))}
        </div>

        {/* Botón de escaneo */}
        <div className="flex items-center gap-4 mb-8">
          <button
            onClick={handleStartScan}
            disabled={scanning}
            className="px-6 py-3 rounded-xl bg-blue-600 hover:bg-blue-500
                       disabled:opacity-50 disabled:cursor-not-allowed
                       font-semibold transition flex items-center gap-2"
          >
            {scanning ? (
              <>
                <span className="animate-spin">⏳</span> Escaneando…
              </>
            ) : (
              "🔍 Escanear red ahora"
            )}
          </button>

          <div className="text-sm text-gray-400">
            {lastScan && (
              <span>
                Último escaneo:{" "}
                {new Date(lastScan.started_at).toLocaleString("es", { timeStyle: "short", dateStyle: "short" })}
                {" · "}{lastScan.device_count} disp. · {lastScan.vuln_count} vuln.
              </span>
            )}
            {nextScan && (
              <span className="ml-3 text-gray-500">
                Próximo automático:{" "}
                {new Date(nextScan).toLocaleString("es", { timeStyle: "short", dateStyle: "short" })}
              </span>
            )}
          </div>
        </div>

        {scanError && (
          <div className="mb-6 bg-red-900/30 border border-red-800 rounded-xl px-4 py-3 text-red-400 text-sm">
            {scanError}
          </div>
        )}

        {/* Dispositivos */}
        {devices.length === 0 ? (
          <div className="text-center py-20 text-gray-500">
            <p className="text-5xl mb-4">📡</p>
            <p className="text-lg font-medium">No hay dispositivos detectados</p>
            <p className="text-sm mt-1">Pulsa "Escanear red ahora" para descubrir los dispositivos de tu hogar.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {devices.map((d) => (
              <DeviceCard key={d.id} device={d} onClick={handleSelectDevice} />
            ))}
          </div>
        )}
      </main>

      {/* Modales */}
      {selectedDevice && (
        <VulnerabilityModal
          device={selectedDevice}
          vulnerabilities={deviceVulns}
          onClose={() => setSelectedDevice(null)}
        />
      )}

      {showChangePassword && (
        <ChangePassword onClose={() => setShowChangePassword(false)} />
      )}

      {showSettings && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 px-4">
          <div className="bg-gray-900 rounded-2xl p-8 w-full max-w-md shadow-2xl">
            <h2 className="text-xl font-bold text-white mb-1">Ajustes</h2>
            <p className="text-gray-400 text-sm mb-6">Configura el escaneo automático y la seguridad.</p>

            <label className="block text-sm font-medium text-gray-300 mb-2">
              Escaneo automático cada (minutos)
            </label>
            <input
              type="number"
              min="0"
              max="1440"
              value={scanInterval}
              onChange={(e) => setScanInterval(Number(e.target.value))}
              className="w-full px-4 py-3 rounded-xl bg-gray-800 border border-gray-700
                         text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <p className="text-xs text-gray-500 mt-1">Pon 0 para desactivar el escaneo automático.</p>

            <button
              onClick={() => { setShowChangePassword(true); setShowSettings(false); }}
              className="mt-5 w-full py-3 rounded-xl border border-gray-700 text-gray-300
                         hover:bg-gray-800 transition text-sm"
            >
              🔑 Cambiar contraseña
            </button>

            <div className="flex gap-3 mt-3">
              <button
                onClick={() => setShowSettings(false)}
                className="flex-1 py-3 rounded-xl border border-gray-700 text-gray-300
                           hover:bg-gray-800 transition"
              >
                Cancelar
              </button>
              <button
                onClick={handleSaveSettings}
                className="flex-1 py-3 rounded-xl bg-blue-600 hover:bg-blue-500
                           text-white font-semibold transition"
              >
                Guardar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Root con AuthProvider ─────────────────────────────────────────────────────

function AppContent() {
  const { token, checking } = useAuth();

  if (checking) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="text-gray-500 animate-pulse">Cargando…</div>
      </div>
    );
  }

  return token ? <Dashboard /> : <LoginPage />;
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}