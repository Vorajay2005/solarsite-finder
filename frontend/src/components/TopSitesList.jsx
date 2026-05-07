import PropTypes from 'prop-types'

function scoreColor(score) {
  if (score >= 80) return 'text-orange-400'
  if (score >= 60) return 'text-yellow-400'
  if (score >= 40) return 'text-blue-400'
  return 'text-gray-400'
}

function ScoreBar({ value, color }) {
  const barColor = {
    'text-orange-400': 'bg-orange-500',
    'text-yellow-400': 'bg-yellow-500',
    'text-blue-400':   'bg-blue-500',
    'text-gray-400':   'bg-gray-500',
  }[color] ?? 'bg-orange-500'

  return (
    <div className="w-full bg-slate-700 rounded-full h-1.5 mt-1">
      <div className={`${barColor} h-1.5 rounded-full`} style={{ width: `${Math.min(value, 100)}%` }} />
    </div>
  )
}

ScoreBar.propTypes = {
  value: PropTypes.number.isRequired,
  color: PropTypes.string.isRequired,
}

export default function TopSitesList({ sites, onSiteClick, stats }) {
  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white">Top Ranked Solar Sites</h2>
          <p className="text-gray-500 text-sm mt-1">
            Ranked by weighted suitability score (GHI 35%, Land Cover 35%, Slope 20%, Proximity 10%)
          </p>
        </div>
        {stats?.totals && (
          <div className="text-right text-sm text-gray-400">
            <p>{stats.totals.candidates?.toLocaleString()} candidates evaluated</p>
            <p>{stats.totals.existing} existing installations</p>
          </div>
        )}
      </div>

      {/* Score weight legend */}
      <div className="bg-slate-900 border border-white/10 rounded-xl p-4 grid grid-cols-4 gap-3 text-center text-xs">
        <div><p className="text-orange-400 font-bold text-lg">35%</p><p className="text-gray-400">Solar Irradiance (GHI)</p></div>
        <div><p className="text-yellow-400 font-bold text-lg">35%</p><p className="text-gray-400">Land Cover Type</p></div>
        <div><p className="text-blue-400 font-bold text-lg">20%</p><p className="text-gray-400">Terrain Slope</p></div>
        <div><p className="text-green-400 font-bold text-lg">10%</p><p className="text-gray-400">Proximity Score</p></div>
      </div>

      {/* Site rows */}
      {sites.length === 0 && (
        <p className="text-gray-500 text-center py-12">No sites loaded. Run the setup scripts first.</p>
      )}

      <div className="space-y-3">
        {sites.map((site, idx) => {
          const color = scoreColor(site.total_score)
          return (
            <button
              key={site.candidate_id}
              onClick={() => onSiteClick(site)}
              className="w-full text-left bg-slate-900 border border-white/10 hover:border-orange-500/40 rounded-xl p-4 transition-colors group"
            >
              <div className="flex items-start gap-4">
                {/* Rank badge */}
                <div className={`w-10 h-10 rounded-lg flex items-center justify-center font-bold text-lg flex-shrink-0 ${
                  idx === 0 ? 'bg-orange-500 text-white' :
                  idx === 1 ? 'bg-yellow-500/20 text-yellow-400' :
                  idx === 2 ? 'bg-blue-500/20 text-blue-400' :
                  'bg-slate-800 text-gray-400'
                }`}>
                  {idx + 1}
                </div>

                {/* Main info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-white font-medium">
                      {site.state} · {site.county || 'Unknown county'}
                      <span className="text-gray-500 text-xs ml-2 font-normal">
                        {site.latitude?.toFixed(2)}, {site.longitude?.toFixed(2)}
                      </span>
                    </p>
                    <span className={`font-bold text-lg flex-shrink-0 ${color}`}>
                      {site.total_score?.toFixed(1)}
                    </span>
                  </div>

                  {/* Sub-scores */}
                  <div className="grid grid-cols-5 gap-2 mt-3 text-xs text-gray-400">
                    <SubScore label="GHI"       value={site.ghi_score}        raw={site.ghi_value ? `${site.ghi_value.toFixed(2)} kWh/m²/d` : null} />
                    <SubScore label="Land"      value={site.land_cover_score} raw={site.land_cover_name} />
                    <SubScore label="Slope"     value={site.slope_score}      raw={site.slope_degrees ? `${site.slope_degrees.toFixed(1)}°` : null} />
                    <SubScore label="Proximity" value={site.proximity_score}  raw={null} />
                    <SubScore label="ML (MW)"   value={null} raw={site.predicted_capacity_mw != null ? `${site.predicted_capacity_mw.toFixed(1)} MW` : null} isMl />
                  </div>

                  <ScoreBar value={site.total_score} color={color} />
                </div>
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}

TopSitesList.propTypes = {
  sites:       PropTypes.array.isRequired,
  onSiteClick: PropTypes.func.isRequired,
  stats:       PropTypes.object,
}

function SubScore({ label, value, raw, isMl }) {
  return (
    <div>
      <span className={isMl ? 'text-orange-400' : 'text-gray-500'}>{label}: </span>
      {value != null && <span className="text-white">{value.toFixed(0)}</span>}
      {raw && <span className={`block truncate ${isMl ? 'text-orange-300 font-medium' : 'text-gray-600'}`}>{raw}</span>}
      {value == null && !raw && <span className="text-white">—</span>}
    </div>
  )
}

SubScore.propTypes = {
  label: PropTypes.string.isRequired,
  value: PropTypes.number,
  raw:   PropTypes.string,
  isMl:  PropTypes.bool,
}
