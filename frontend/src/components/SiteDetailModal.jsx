import { useEffect, useRef } from 'react'
import PropTypes from 'prop-types'

function ScoreRow({ label, score, detail }) {
  const pct = Math.min(Math.max(score ?? 0, 0), 100)
  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-gray-400">{label}</span>
        <span className="text-white font-medium">{pct.toFixed(1)}</span>
      </div>
      <div className="w-full bg-slate-700 rounded-full h-2">
        <div className="bg-orange-500 h-2 rounded-full transition-all" style={{ width: `${pct}%` }} />
      </div>
      {detail && <p className="text-gray-500 text-xs mt-0.5">{detail}</p>}
    </div>
  )
}

ScoreRow.propTypes = {
  label:  PropTypes.string.isRequired,
  score:  PropTypes.number,
  detail: PropTypes.string,
}

export default function SiteDetailModal({ data, onClose }) {
  const dialogRef = useRef(null)
  const site   = data?.site   ?? data
  const nearby = data?.nearby ?? []

  // Open the native <dialog> and handle Escape
  useEffect(() => {
    const el = dialogRef.current
    if (!el) return
    el.showModal()
    const handleCancel = e => { e.preventDefault(); onClose() }
    el.addEventListener('cancel', handleCancel)
    return () => el.removeEventListener('cancel', handleCancel)
  }, [onClose])

  if (!site) return null

  return (
    // Native <dialog> satisfies accessibility requirements without extra role/keyboard hacks
    <dialog
      ref={dialogRef}
      className="fixed m-auto bg-transparent p-0 max-w-lg w-full max-h-[90vh] backdrop:bg-black/60 backdrop:backdrop-blur-sm rounded-2xl"
    >
      <div className="bg-slate-900 border border-white/10 rounded-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-white/10">
          <div>
            <h2 className="text-lg font-bold text-white">
              {site.state} · {site.county || 'Unknown county'}
            </h2>
            <p className="text-gray-500 text-sm">
              {site.latitude?.toFixed(4)}, {site.longitude?.toFixed(4)}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-3xl font-bold text-orange-400">
              {site.total_score?.toFixed(1)}
            </span>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-white text-xl leading-none"
              aria-label="Close"
            >
              ✕
            </button>
          </div>
        </div>

        <div className="p-5 space-y-5">

          {/* Score breakdown */}
          <section>
            <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-3">
              Score Breakdown
            </h3>
            <div className="space-y-3">
              <ScoreRow
                label="Solar Irradiance (GHI)"
                score={site.ghi_score}
                detail={site.ghi_value ? `${site.ghi_value.toFixed(2)} kWh/m²/day` : undefined}
              />
              <ScoreRow
                label="Land Cover Suitability"
                score={site.land_cover_score}
                detail={site.land_cover_name}
              />
              <ScoreRow
                label="Terrain Slope"
                score={site.slope_score}
                detail={site.slope_degrees != null ? `${site.slope_degrees.toFixed(1)}°` : undefined}
              />
              <ScoreRow
                label="Proximity to Existing Sites"
                score={site.proximity_score}
              />
            </div>
          </section>

          <p className="text-gray-600 text-xs">
            Total = GHI×35% + Land×35% + Slope×20% + Proximity×10%
          </p>

          {/* ML Prediction */}
          {site.predicted_capacity_mw != null && (
            <section className="bg-slate-800/60 border border-orange-500/20 rounded-xl p-4">
              <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-2">
                ML Capacity Prediction
              </h3>
              <div className="flex items-end gap-2">
                <span className="text-3xl font-bold text-orange-400">
                  {site.predicted_capacity_mw.toFixed(1)}
                </span>
                <span className="text-gray-400 mb-0.5">MW predicted AC capacity</span>
              </div>
              <p className="text-gray-500 text-xs mt-1">
                Estimated by a Random Forest model trained on 6,500+ real US solar installations (R² = 0.91)
              </p>
            </section>
          )}

          {/* Raw values */}
          <section>
            <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-3">
              Raw Values
            </h3>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <DataRow label="Rank"      value={site.rank ? `#${site.rank}` : '—'} />
              <DataRow label="State"     value={site.state ?? '—'} />
              <DataRow label="County"    value={site.county ?? 'Unknown'} />
              <DataRow label="GHI"       value={site.ghi_value ? `${site.ghi_value.toFixed(2)} kWh/m²/d` : 'N/A'} />
              <DataRow label="Land Type" value={site.land_cover_name ?? 'N/A'} />
              <DataRow label="Slope"     value={site.slope_degrees != null ? `${site.slope_degrees.toFixed(1)}°` : 'N/A'} />
              {site.predicted_capacity_mw != null && (
                <DataRow label="ML Predicted MW" value={`${site.predicted_capacity_mw.toFixed(1)} MW`} />
              )}
            </div>
          </section>

          {/* Nearby installations */}
          {nearby.length > 0 && (
            <section>
              <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-3">
                Nearby Installations
              </h3>
              <div className="space-y-2">
                {nearby.map(n => (
                  <div
                    key={`${n.latitude},${n.longitude}`}
                    className="bg-slate-800 rounded-lg px-3 py-2 text-xs text-gray-300"
                  >
                    <span className="font-medium text-white">{n.name || 'Unnamed'}</span>
                    <span className="text-gray-500 ml-2">{n.capacity_mw} MW · {n.install_year}</span>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>
      </div>
    </dialog>
  )
}

SiteDetailModal.propTypes = {
  data:    PropTypes.object.isRequired,
  onClose: PropTypes.func.isRequired,
}

function DataRow({ label, value }) {
  return (
    <div className="bg-slate-800 rounded-lg px-3 py-2">
      <p className="text-gray-500 text-xs">{label}</p>
      <p className="text-white font-medium text-sm truncate">{value}</p>
    </div>
  )
}

DataRow.propTypes = {
  label: PropTypes.string.isRequired,
  value: PropTypes.string.isRequired,
}
