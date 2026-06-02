// frontend/src/components/LoginPage.jsx
import { useState } from "react";
import { useAuth } from "../context/AuthContext";

export default function LoginPage() {
  const { login } = useAuth();
  const [password, setPassword] = useState("");
  const [error, setError]       = useState("");
  const [loading, setLoading]   = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(password);
      // AuthContext + App.jsx se encargan de redirigir
    } catch (err) {
      setError(err.message || "Contraseña incorrecta. Inténtalo de nuevo.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        {/* Logo / título */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-blue-600 mb-4">
            <svg className="w-9 h-9 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M3 12l9-9 9 9M5 10v9a1 1 0 001 1h4v-5h4v5h4a1 1 0 001-1v-9"
              />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-white">Smart Home Vulnerability Manager</h1>
          <p className="text-gray-400 text-sm mt-1">Ingresa tu contraseña para continuar</p>
        </div>

        {/* Formulario */}
        <form onSubmit={handleSubmit} className="bg-gray-900 rounded-2xl p-8 shadow-xl">
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Contraseña
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            className="w-full px-4 py-3 rounded-xl bg-gray-800 border border-gray-700
                       text-white placeholder-gray-500 focus:outline-none focus:ring-2
                       focus:ring-blue-500 focus:border-transparent transition"
            autoFocus
            required
          />

          {error && (
            <p className="mt-3 text-sm text-red-400 bg-red-900/30 rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading || !password}
            className="mt-5 w-full py-3 rounded-xl bg-blue-600 hover:bg-blue-500
                       disabled:opacity-50 disabled:cursor-not-allowed text-white
                       font-semibold transition"
          >
            {loading ? "Verificando…" : "Entrar"}
          </button>
        </form>

        <p className="text-center text-xs text-gray-600 mt-6">
          Consulta el README para la contraseña inicial.
        </p>
      </div>
    </div>
  );
}