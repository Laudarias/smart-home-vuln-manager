import { useState } from "react";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";

export default function ChangePassword({ onClose }) {
  const { setIsDefaultPassword } = useAuth();
  const [form, setForm] = useState({ current: "", next: "", confirm: "" });
  const [error, setError]   = useState("");
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    if (form.next.length < 8) {
      setError("La nueva contraseña debe tener al menos 8 caracteres.");
      return;
    }
    if (form.next !== form.confirm) {
      setError("Las contraseñas nuevas no coinciden.");
      return;
    }
    setLoading(true);
    try {
      await api.changePassword(form.current, form.next);
      setIsDefaultPassword(false);
      setSuccess(true);
    } catch (err) {
      setError(err.message || "No se pudo cambiar la contraseña.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 px-4">
      <div className="bg-gray-900 rounded-2xl p-8 w-full max-w-md shadow-2xl">
        <h2 className="text-xl font-bold text-white mb-1">Cambiar contraseña</h2>
        <p className="text-gray-400 text-sm mb-6">
          Elige una contraseña segura de al menos 8 caracteres.
        </p>

        {success ? (
          <div className="text-center py-4">
            <div className="text-green-400 text-5xl mb-3">✓</div>
            <p className="text-white font-medium">¡Contraseña actualizada!</p>
            <button
              onClick={onClose}
              className="mt-5 px-6 py-2 rounded-xl bg-blue-600 hover:bg-blue-500
                         text-white font-semibold transition"
            >
              Cerrar
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            {[
              { label: "Contraseña actual", key: "current", placeholder: "Tu contraseña actual" },
              { label: "Nueva contraseña", key: "next", placeholder: "Mínimo 8 caracteres" },
              { label: "Confirmar nueva contraseña", key: "confirm", placeholder: "Repite la nueva contraseña" },
            ].map(({ label, key, placeholder }) => (
              <div key={key}>
                <label className="block text-sm font-medium text-gray-300 mb-1">{label}</label>
                <input
                  type="password"
                  value={form[key]}
                  onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                  placeholder={placeholder}
                  className="w-full px-4 py-3 rounded-xl bg-gray-800 border border-gray-700
                             text-white placeholder-gray-500 focus:outline-none focus:ring-2
                             focus:ring-blue-500 transition"
                  required
                />
              </div>
            ))}

            {error && (
              <p className="text-sm text-red-400 bg-red-900/30 rounded-lg px-3 py-2">{error}</p>
            )}

            <div className="flex gap-3 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 py-3 rounded-xl border border-gray-700 text-gray-300
                           hover:bg-gray-800 transition"
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={loading}
                className="flex-1 py-3 rounded-xl bg-blue-600 hover:bg-blue-500
                           disabled:opacity-50 text-white font-semibold transition"
              >
                {loading ? "Guardando…" : "Guardar"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}