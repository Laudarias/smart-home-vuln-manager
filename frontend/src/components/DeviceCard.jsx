/**
 * Tarjeta de dispositivo con toda la información disponible:
 * nombre, fabricante, IP, MAC, OS, tipo, puertos, vulnerabilidades.
 */

const DEVICE_ICONS = {
  router:           "📡",
  mobile:           "📱",
  computer:         "💻",
  "computer-windows": "💻",
  "computer-mac":   "🍏",
  "computer-linux": "🐧",
  "smart-home":     "🏠",
  "smart-tv":       "📺",
  printer:          "🖨️",
  nas:              "💾",
  server:           "🖥️",
  "media-server":   "🎵",
  unknown:          "❓",
};

const DEVICE_TYPE_LABELS = {
  router:           "Router / Gateway",
  mobile:           "Móvil / Tablet",
  computer:         "Ordenador",
  "computer-windows": "PC Windows",
  "computer-mac":   "Mac",
  "computer-linux": "PC Linux",
  "smart-home":     "Dispositivo inteligente",
  "smart-tv":       "Smart TV",
  printer:          "Impresora",
  nas:              "Almacenamiento (NAS)",
  server:           "Servidor",
  "media-server":   "Servidor multimedia",
  unknown:          "Desconocido",
};

/**
 * Severidad → color de badge.
 * Criterios CVSS v3:
 *   Crítica  9.0–10.0  rojo intenso
 *   Alta     7.0–8.9   naranja
 *   Media    4.0–6.9   amarillo
 *   Baja     0.1–3.9   verde
 */
const SEVERITY_STYLES = {
  critical: "bg-red-600 text-white",
  high:     "bg-orange-500 text-white",
  medium:   "bg-yellow-500 text-gray-900",
  low:      "bg-green-600 text-white",
  info:     "bg-gray-600 text-white",
};

const SEVERITY_LABELS = {
  critical: "Crítica",
  high:     "Alta",
  medium:   "Media",
  low:      "Baja",
  info:     "Info",
};

function SeverityBadge({ level, count }) {
  if (!count) return null;
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold
                  ${SEVERITY_STYLES[level] ?? "bg-gray-600 text-white"}`}
    >
      {SEVERITY_LABELS[level] ?? level}: {count}
    </span>
  );
}

function getBestName(device) {
  return (
    device.mdns_name ||
    device.hostname ||
    device.netbios_name ||
    device.manufacturer ||
    device.ip
  );
}

export default function DeviceCard({ device, onClick }) {
  const icon  = DEVICE_ICONS[device.device_type] ?? "❓";
  const label = DEVICE_TYPE_LABELS[device.device_type] ?? "Desconocido";
  const name  = getBestName(device);
  const hasVulns = device.vuln_total > 0;

  return (
    <button
      onClick={() => onClick?.(device)}
      className={`w-full text-left bg-gray-900 rounded-2xl p-5 shadow transition
                  hover:bg-gray-800 border
                  ${device.status === "offline"
                    ? "border-gray-700 opacity-60"
                    : hasVulns
                      ? "border-orange-700"
                      : "border-gray-700"}`}
    >
      {/* Encabezado */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="text-3xl leading-none">{icon}</span>
          <div>
            <p className="text-white font-semibold leading-tight truncate max-w-[180px]">
              {name}
            </p>
            <p className="text-gray-400 text-xs mt-0.5">{label}</p>
          </div>
        </div>
        {/* Badge online/offline */}
        <span
          className={`shrink-0 text-xs font-medium px-2 py-0.5 rounded-full
                      ${device.status === "online"
                        ? "bg-green-900 text-green-400"
                        : "bg-gray-800 text-gray-500"}`}
        >
          {device.status === "online" ? "En línea" : "Sin conexión"}
        </span>
      </div>

      {/* Detalles */}
      <div className="mt-4 space-y-1 text-sm text-gray-400">
        <div className="flex justify-between">
          <span>IP</span>
          <span className="text-gray-200 font-mono">{device.ip}</span>
        </div>
        {device.mac && (
          <div className="flex justify-between">
            <span>MAC</span>
            <span className="text-gray-200 font-mono text-xs">{device.mac}</span>
          </div>
        )}
        {device.manufacturer && name !== device.manufacturer && (
          <div className="flex justify-between">
            <span>Fabricante</span>
            <span className="text-gray-200 truncate max-w-[180px]">{device.manufacturer}</span>
          </div>
        )}
        {device.os_name && (
          <div className="flex justify-between">
            <span>Sistema operativo</span>
            <span className="text-gray-200 truncate max-w-[180px]">
              {device.os_name}
              {device.os_accuracy && (
                <span className="text-gray-500 text-xs ml-1">({device.os_accuracy}%)</span>
              )}
            </span>
          </div>
        )}
        {device.ports?.length > 0 && (
          <div className="flex justify-between">
            <span>Puertos abiertos</span>
            <span className="text-gray-200">
              {device.ports.slice(0, 5).map((p) => p.port).join(", ")}
              {device.ports.length > 5 && (
                <span className="text-gray-500"> +{device.ports.length - 5}</span>
              )}
            </span>
          </div>
        )}
      </div>

      {/* Badges de vulnerabilidades */}
      {hasVulns && (
        <div className="mt-4 flex flex-wrap gap-1.5">
          <SeverityBadge level="critical" count={device.vuln_critical} />
          <SeverityBadge level="high"     count={device.vuln_high} />
          <SeverityBadge level="medium"   count={device.vuln_medium} />
          <SeverityBadge level="low"      count={device.vuln_low} />
        </div>
      )}
      {!hasVulns && device.status === "online" && (
        <p className="mt-4 text-xs text-green-500">✓ Sin vulnerabilidades conocidas</p>
      )}
    </button>
  );
}