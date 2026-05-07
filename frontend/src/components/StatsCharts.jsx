import PropTypes from 'prop-types'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from 'recharts'

const CHART_COLORS = ['#f97316', '#eab308', '#22c55e', '#3b82f6', '#a855f7', '#ec4899', '#14b8a6']

const RADIAN = Math.PI / 180
function PieLabel({ cx, cy, midAngle, innerRadius, outerRadius, percent }) {
  if (percent <= 0.03) return null
  const radius = innerRadius + (outerRadius - innerRadius) * 0.5
  const x = cx + radius * Math.cos(-midAngle * RADIAN)
  const y = cy + radius * Math.sin(-midAngle * RADIAN)
  return (
    <text x={x} y={y} fill="white" textAnchor="middle" dominantBaseline="central" fontSize={12} fontWeight="bold">
      {`${(percent * 100).toFixed(1)}%`}
    </text>
  )
}

PieLabel.propTypes = {
  cx:          PropTypes.number,
  cy:          PropTypes.number,
  midAngle:    PropTypes.number,
  innerRadius: PropTypes.number,
  outerRadius: PropTypes.number,
  percent:     PropTypes.number,
}

export default function StatsCharts({ stats, sites }) {
  if (!stats) {
    return <p className="text-gray-400 text-center mt-20">Loading statistics…</p>
  }

  // Score distribution for bar chart
  const scoreDist = (stats.score_distribution || []).map(d => ({
    name:  d.bucket,
    count: d.count,
  }))

  // Avg score by NJ county
  const ghiByState = (stats.ghi_by_state || []).slice(0, 10).map(d => ({
    state:      d.state,
    avg_ghi:    Number(d.avg_ghi) || 0,
    best_score: Number(d.best_score) || 0,
  }))

  // Land cover pie
  const landCover = (stats.land_cover_counts || []).filter(d => d.land_cover_name)

  // Existing installations bar
  const existingByState = (stats.existing_by_state || []).slice(0, 10).map(d => ({
    state:    d.state,
    total_mw: Number(d.total_mw) || 0,
    count:    d.count,
  }))

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      <h2 className="text-xl font-bold text-white">Data Analysis &amp; Visualizations</h2>

      {/* Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Score distribution */}
        <ChartCard title="NJ Candidate Site Score Distribution" subtitle="671 NJ candidate sites by suitability score">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={scoreDist} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 12 }} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} />
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }} formatter={(v) => [v, 'Sites']} />
              <Bar dataKey="count" fill="#f97316" radius={[4, 4, 0, 0]} name="Sites" />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* Avg score by NJ county */}
        <ChartCard title="Average Suitability Score by NJ County" subtitle="Top 10 counties ranked by avg score — higher is better">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={ghiByState} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="state" tick={{ fill: '#94a3b8', fontSize: 10 }} angle={-30} textAnchor="end" height={45} />
              <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} domain={[0, 80]} />
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }} formatter={(v) => [v.toFixed(1), 'Avg Score']} />
              <Bar dataKey="best_score" fill="#eab308" radius={[4, 4, 0, 0]} name="Avg Score" />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      {/* Row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Land cover pie */}
        <ChartCard title="Land Cover Breakdown" subtitle="All 671 NJ candidate sites by land type">
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie
                data={landCover}
                dataKey="count"
                nameKey="land_cover_name"
                cx="50%" cy="50%"
                outerRadius={90}
                label={PieLabel}
                labelLine={false}
              >
                {landCover.map((_, i) => (
                  <Cell key={`cell-${i}`} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                ))}
              </Pie>
              <Legend
                formatter={value => <span style={{ color: '#94a3b8', fontSize: 11 }}>{value}</span>}
              />
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }} formatter={(v, n) => [v, n]} />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* NJ existing capacity by county */}
        <ChartCard title="Existing NJ Solar Capacity by County" subtitle="Total installed MW across 330 NJ installations (USPVDB)">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={existingByState} layout="vertical" margin={{ top: 5, right: 30, bottom: 5, left: 70 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis type="number" tick={{ fill: '#94a3b8', fontSize: 11 }} />
              <YAxis type="category" dataKey="state" tick={{ fill: '#94a3b8', fontSize: 11 }} width={65} />
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }} formatter={(v) => [`${v} MW`, 'Capacity']} />
              <Bar dataKey="total_mw" fill="#22c55e" radius={[0, 4, 4, 0]} name="Total MW" />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      {/* Summary table */}
      {stats.totals && (
        <ChartCard title="NJ Dataset Summary" subtitle="Key counts — all data scoped to New Jersey">
          <div className="grid grid-cols-3 gap-4 py-4">
            <StatBox label="NJ Candidate Sites"      value={stats.totals.candidates?.toLocaleString()} color="text-orange-400" />
            <StatBox label="Scored Sites"            value={stats.totals.scored?.toLocaleString()}     color="text-yellow-400" />
            <StatBox label="Existing NJ Installs"   value={stats.totals.existing?.toLocaleString()}   color="text-green-400" />
          </div>
        </ChartCard>
      )}
    </div>
  )
}

StatsCharts.propTypes = {
  stats: PropTypes.object,
  sites: PropTypes.array,
}

function ChartCard({ title, subtitle, children }) {
  return (
    <div className="bg-slate-900 border border-white/10 rounded-xl p-4">
      <h3 className="text-white font-semibold mb-1">{title}</h3>
      <p className="text-gray-500 text-xs mb-4">{subtitle}</p>
      {children}
    </div>
  )
}

ChartCard.propTypes = {
  title:    PropTypes.string.isRequired,
  subtitle: PropTypes.string.isRequired,
  children: PropTypes.node.isRequired,
}

function StatBox({ label, value, color }) {
  return (
    <div className="bg-slate-800 rounded-lg p-4 text-center">
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
      <p className="text-gray-400 text-xs mt-1">{label}</p>
    </div>
  )
}

StatBox.propTypes = {
  label: PropTypes.string.isRequired,
  value: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  color: PropTypes.string.isRequired,
}
