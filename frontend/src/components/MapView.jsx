import { useEffect, useRef, useState } from 'react'
import PropTypes from 'prop-types'
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'

/**
 * FitBounds re-centers the map whenever the set of visible sites changes.
 * It fits only the markers that are currently displayed — so filtering to
 * NJ zooms to NJ, not the whole US.
 * A stable key string is used as the dependency so React doesn't
 * re-trigger on every parent render.
 */
function FitBounds({ boundsKey, points }) {
  const map = useMap()
  const prev = useRef(null)

  useEffect(() => {
    if (boundsKey === prev.current) return   // same set of sites, don't move
    prev.current = boundsKey

    const valid = points.filter(([lat, lon]) => lat != null && lon != null)
    if (valid.length === 0) return

    map.fitBounds(valid, { padding: [40, 40], maxZoom: 11 })
  }, [boundsKey])   // eslint-disable-line react-hooks/exhaustive-deps

  return null
}

FitBounds.propTypes = {
  boundsKey: PropTypes.string.isRequired,
  points:    PropTypes.array.isRequired,
}

function scoreColor(score) {
  if (score >= 75) return '#f97316'   // orange  — top tier
  if (score >= 55) return '#eab308'   // yellow  — good
  if (score >= 40) return '#3b82f6'   // blue    — moderate
  return '#6b7280'                    // gray    — low
}

export default function MapView({ sites, existing, topSites, onSiteClick }) {
  const [showExisting, setShowExisting]     = useState(true)
  const [showCandidates, setShowCandidates] = useState(true)
  const [showTopOnly, setShowTopOnly]       = useState(false)

  const displaySites = showTopOnly ? topSites : sites

  // Build a compact key so FitBounds only refits when the actual site set changes
  // (e.g. after a state filter changes), not on every render.
  const boundsKey = displaySites.slice(0, 5).map(s => s.candidate_id).join(',')
    + '|' + (showExisting ? existing.slice(0, 3).map(s => s.site_id ?? s.latitude).join(',') : '')

  const allPoints = [
    ...displaySites.map(s => [s.latitude, s.longitude]),
    ...(showExisting ? existing.map(s => [s.latitude, s.longitude]) : []),
  ]

  return (
    <div className="relative h-full w-full">
      <MapContainer
        center={[40.1, -74.5]}
        zoom={8}
        style={{ height: '100%', width: '100%' }}
        className="z-0"
      >
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; <a href="https://carto.com/">CARTO</a>'
        />

        <FitBounds boundsKey={boundsKey} points={allPoints} />

        {/* Existing NJ solar installations — green */}
        {showExisting && existing.map(site => (
          <CircleMarker
            key={`existing-${site.site_id ?? String(site.latitude) + ',' + String(site.longitude)}`}
            center={[site.latitude, site.longitude]}
            radius={5}
            pathOptions={{ color: '#22c55e', fillColor: '#22c55e', fillOpacity: 0.8, weight: 1.5 }}
          >
            <Popup>
              <div className="text-sm">
                <p className="font-semibold">{site.name || 'Solar Installation'}</p>
                <p className="text-gray-600">{site.state}{site.county ? ` · ${site.county}` : ''}</p>
                {site.capacity_mw != null && <p>{site.capacity_mw} MW · {site.install_year}</p>}
                {site.land_cover_type && <p className="text-gray-500 text-xs">{site.land_cover_type}</p>}
              </div>
            </Popup>
          </CircleMarker>
        ))}

        {/* Candidate sites — colored by score */}
        {showCandidates && displaySites.map(site => {
          const color  = scoreColor(site.total_score)
          const isTop  = site.rank != null && site.rank <= 10
          return (
            <CircleMarker
              key={`cand-${site.candidate_id}`}
              center={[site.latitude, site.longitude]}
              radius={isTop ? 8 : 5}
              pathOptions={{
                color,
                fillColor:   color,
                fillOpacity: 0.8,
                weight:      isTop ? 2 : 1,
              }}
              eventHandlers={{ click: () => onSiteClick(site) }}
            >
              <Popup>
                <div className="text-sm min-w-[190px]">
                  <div className="flex justify-between items-start mb-1">
                    <p className="font-semibold text-base">Score: {site.total_score?.toFixed(1)}</p>
                    {isTop && <span className="text-xs bg-orange-100 text-orange-700 px-1.5 py-0.5 rounded">Top {site.rank}</span>}
                  </div>
                  <p className="text-gray-500 text-xs mb-1">{site.state}{site.county ? ` · ${site.county}` : ''}</p>
                  <table className="w-full text-xs text-gray-600">
                    <tbody>
                      <tr><td className="pr-2">GHI</td><td className="text-right font-medium text-gray-800">{site.ghi_value != null ? `${site.ghi_value.toFixed(2)} kWh/m²/d` : 'N/A'}</td></tr>
                      <tr><td className="pr-2">Land</td><td className="text-right font-medium text-gray-800">{site.land_cover_name ?? 'N/A'}</td></tr>
                      <tr><td className="pr-2">Slope</td><td className="text-right font-medium text-gray-800">{site.slope_degrees != null ? `${Number(site.slope_degrees).toFixed(1)}°` : 'N/A'}</td></tr>
                      {site.predicted_capacity_mw != null && (
                        <tr>
                          <td className="pr-2 text-orange-600 font-medium">ML Capacity</td>
                          <td className="text-right font-bold text-orange-700">{site.predicted_capacity_mw.toFixed(1)} MW</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                  <button
                    onClick={() => onSiteClick(site)}
                    className="mt-2 w-full bg-orange-500 text-white text-xs py-1 rounded hover:bg-orange-600"
                  >
                    Full Details
                  </button>
                </div>
              </Popup>
            </CircleMarker>
          )
        })}
      </MapContainer>

      {/* Legend */}
      <div className="absolute bottom-6 left-4 bg-slate-900/90 backdrop-blur rounded-xl p-3 text-xs z-[1000] space-y-2">
        <p className="text-gray-400 font-medium uppercase tracking-wider text-[10px]">Score Legend</p>
        <div className="space-y-1.5">
          <LegendItem color="#f97316" label="≥ 75 — Top tier" />
          <LegendItem color="#eab308" label="55–74 — Good" />
          <LegendItem color="#3b82f6" label="40–54 — Moderate" />
          <LegendItem color="#6b7280" label="&lt; 40 — Low" />
          <LegendItem color="#22c55e" label="Existing install" />
        </div>
      </div>

      {/* Layer toggles */}
      <div className="absolute top-4 right-4 bg-slate-900/90 backdrop-blur rounded-xl p-3 text-xs z-[1000] space-y-2 min-w-[160px]">
        <p className="text-gray-400 font-medium uppercase tracking-wider text-[10px]">Layers</p>
        <Toggle label="Existing installs" value={showExisting}   onChange={setShowExisting} />
        <Toggle label="Candidate sites"   value={showCandidates} onChange={setShowCandidates} />
        <Toggle label="Top 20 only"       value={showTopOnly}    onChange={setShowTopOnly} />
        <p className="text-gray-500 pt-1 border-t border-white/10">{displaySites.length} sites shown</p>
      </div>
    </div>
  )
}

MapView.propTypes = {
  sites:       PropTypes.array.isRequired,
  existing:    PropTypes.array.isRequired,
  topSites:    PropTypes.array.isRequired,
  onSiteClick: PropTypes.func.isRequired,
}

function LegendItem({ color, label }) {
  return (
    <div className="flex items-center gap-2">
      <span className="w-3 h-3 rounded-full flex-shrink-0" style={{ background: color }} />
      <span className="text-gray-300">{label}</span>
    </div>
  )
}

LegendItem.propTypes = {
  color: PropTypes.string.isRequired,
  label: PropTypes.string.isRequired,
}

function Toggle({ label, value, onChange }) {
  return (
    <label className="flex items-center gap-2 cursor-pointer select-none">
      <input type="checkbox" checked={value} onChange={e => onChange(e.target.checked)} className="accent-orange-500" />
      <span className="text-gray-300">{label}</span>
    </label>
  )
}

Toggle.propTypes = {
  label:    PropTypes.string.isRequired,
  value:    PropTypes.bool.isRequired,
  onChange: PropTypes.func.isRequired,
}
