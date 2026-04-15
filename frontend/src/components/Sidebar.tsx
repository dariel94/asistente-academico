import type { Perfil } from '../types/chat';

interface Props {
  perfil: Perfil;
  onLogout: () => void;
}

const ESTADO_LABELS: Record<string, string> = {
  regular: 'Regular',
  condicional: 'Condicional',
  libre: 'Libre',
  egresado: 'Egresado',
};

export default function Sidebar({ perfil, onLogout }: Props) {
  return (
    <aside className="w-72 bg-gray-50 border-r border-gray-200 flex flex-col">
      <div className="p-6 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-800">Perfil</h2>
      </div>

      <div className="p-6 space-y-4 flex-1">
        <div>
          <span className="text-xs text-gray-500 uppercase tracking-wide">Nombre</span>
          <p className="text-sm font-medium text-gray-800">
            {perfil.nombre} {perfil.apellido}
          </p>
        </div>

        <div>
          <span className="text-xs text-gray-500 uppercase tracking-wide">Legajo</span>
          <p className="text-sm font-medium text-gray-800">{perfil.legajo}</p>
        </div>

        <div>
          <span className="text-xs text-gray-500 uppercase tracking-wide">Carrera</span>
          <p className="text-sm font-medium text-gray-800">{perfil.carrera}</p>
        </div>

        <div>
          <span className="text-xs text-gray-500 uppercase tracking-wide">Estado</span>
          <p className="text-sm font-medium text-gray-800">
            {ESTADO_LABELS[perfil.estado] ?? perfil.estado}
          </p>
        </div>
      </div>

      <div className="p-6 border-t border-gray-200">
        <button
          onClick={onLogout}
          className="w-full py-2 px-4 text-sm text-gray-600 border border-gray-300 rounded-lg hover:bg-gray-100 transition-colors"
        >
          Cerrar sesión
        </button>
      </div>
    </aside>
  );
}
