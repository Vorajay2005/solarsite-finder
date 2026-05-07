import { useEffect, useState } from 'react'

// NJ DEP land cover types from the shapefile
const LAND_TYPES = [
  '', 'Cultivated Crops', 'Barren Land', 'Deciduous Forest',
  'Woody Wetlands', 'Developed Low Intensity', 'Developed Open Space',
]

const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:5001'

export default function FilterPanel({ filters, onApply, stats }) {
  const [local, setLocal] = useState(filters)
  const [counties, setCounties] = useState([])

  // Fetch the real list of NJ counties from the backend on mount
  useEffect(() => {
    fetch(`${API}/api/counties?state=NJ`)
      .then(r => r.json())
      .then(data => setCounties(Array.isArray(data) ? data : []))
      .catch(() => setCounties([]))
  }, [])

  function handleChange(key, value) {
    setLocal(prev => ({ ...prev, [key]: value }))
  }

  function handleApply() {
    onApply(local)
  }

  function handleReset() {
    const reset = { state: 'NJ', county: '', min_score: 0, land_cover: '', max_slope: '' }
    setLocal(reset)
    onApply(reset)
  }

  return (
    <aside className="w-64 flex-shrink-0 bg-slate-900 border-r border-white/10 flex flex-col overflow-y-auto">
      <div className="p-4 border-b border-white/10">
        <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider">Filters</h2>
      </div>

      <div className="p-4 flex flex-col gap-5 flex-1">

        {/* NJ County */}
        <div>
          <label className="block text-xs text-gray-400 mb-1.5">NJ County</label>
          <select
            value={local.county || ''}
            onChange={e => handleChange('county', e.target.value)}
            className="w-full bg-slate-800 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-orange-500"
          >
            <option value="">All NJ Counties</option>
            {counties.map(c => (
              <option key={c.county} value={c.county}>
                {c.county} ({c.site_count})
              </option>
            ))}
          </select>
        </div>

        {/* Min score */}
        <div>
          <label className="block text-xs text-gray-400 mb-1.5">
            Min Score: <span className="text-orange-400 font-medium">{local.min_score}</span>
          </label>
          <input
            type="range"
            min={0} max={100} step={5}
            value={local.min_score}
            onChange={e => handleChange('min_score', Number(e.target.value))}
            className="w-full accent-orange-500"
          />
          <div className="flex justify-between text-xs text-gray-600 mt-1">
            <span>0</span><span>50</span><span>100</span>
          </div>
        </div>

        {/* Land cover */}
        <div>
          <label className="block text-xs text-gray-400 mb-1.5">Land Cover Type</label>
          <select
            value={local.land_cover}
            onChange={e => handleChange('land_cover', e.target.value)}
            className="w-full bg-slate-800 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-orange-500"
          >
            {LAND_TYPES.map(t => (
              <option key={t} value={t}>{t || 'All Types'}</option>
            ))}
          </select>
        </div>

        {/* Max slope */}
        <div>
          <label className="block text-xs text-gray-400 mb-1.5">Max Slope (degrees)</label>
          <input
            type="number"
            min={0} max={30} placeholder="Any"
            value={local.max_slope}
            onChange={e => handleChange('max_slope', e.target.value)}
            className="w-full bg-slate-800 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-orange-500"
          />
        </div>

        {/* Buttons */}
        <div className="flex flex-col gap-2 mt-auto pt-4 border-t border-white/10">
          <button
            onClick={handleApply}
            className="w-full bg-orange-500 hover:bg-orange-600 text-white text-sm font-medium py-2 rounded-lg transition-colors"
          >
            Apply Filters
          </button>
          <button
            onClick={handleReset}
            className="w-full bg-slate-800 hover:bg-slate-700 text-gray-300 text-sm py-2 rounded-lg transition-colors"
          >
            Reset
          </button>
        </div>

        {/* Quick stats */}
        {stats && (
          <div className="border-t border-white/10 pt-4 space-y-2">
            <p className="text-xs text-gray-500 uppercase tracking-wider">Dataset</p>
            <div className="space-y-1.5 text-xs text-gray-400">
              <div className="flex justify-between">
                <span>Candidate sites</span>
                <span className="text-white">{stats.totals?.candidates?.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span>Scored sites</span>
                <span className="text-white">{stats.totals?.scored?.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span>Existing installs</span>
                <span className="text-green-400">{stats.totals?.existing}</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </aside>
  )
}
