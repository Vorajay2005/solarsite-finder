import { useState, useEffect } from 'react'
import MapView from './components/MapView'
import FilterPanel from './components/FilterPanel'
import SiteDetailModal from './components/SiteDetailModal'
import StatsCharts from './components/StatsCharts'
import TopSitesList from './components/TopSitesList'

const API = import.meta.env.VITE_API_URL || 'http://localhost:5001'

const TABS = { MAP: 'map', CHARTS: 'charts', REPORT: 'report' }

function App() {
  const [activeTab, setActiveTab]       = useState(TABS.MAP)
  const [sites, setSites]               = useState([])
  const [existing, setExisting]         = useState([])
  const [stats, setStats]               = useState(null)
  const [selectedSite, setSelectedSite] = useState(null)
  const [loading, setLoading]           = useState(true)
  const [dbReady, setDbReady]           = useState(false)
  const [filters, setFilters]           = useState({
    state:      'NJ',  
    county:     '',     
    min_score:  0,
    land_cover: '',
    max_slope:  '',
  })


  useEffect(() => {
    fetch(`${API}/api/health`)
      .then(r => r.json())
      .then(d => {
        setDbReady(d.db_ready)
        if (d.db_ready) {
          loadAll()
        } else {
          setLoading(false)
        }
      })
      .catch(() => setLoading(false))
  }, [])

  function loadAll() {
    setLoading(true)
    const params = new URLSearchParams()
    if (filters.state)      params.set('state',      filters.state)
    if (filters.county)     params.set('county',     filters.county)
    if (filters.min_score)  params.set('min_score',  filters.min_score)
    if (filters.land_cover) params.set('land_cover', filters.land_cover)
    if (filters.max_slope)  params.set('max_slope',  filters.max_slope)

    const existingParams = new URLSearchParams({ state: filters.state || 'NJ' })
    if (filters.county) existingParams.set('county', filters.county)

    Promise.all([
      fetch(`${API}/api/sites?${params}`).then(r => r.json()),
      fetch(`${API}/api/existing?${existingParams}`).then(r => r.json()),
      fetch(`${API}/api/stats`).then(r => r.json()),
    ])
      .then(([sitesData, existingData, statsData]) => {
        setSites(Array.isArray(sitesData) ? sitesData : [])
        setExisting(Array.isArray(existingData) ? existingData : [])
        setStats(statsData)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }

  function applyFilters(newFilters) {
    setFilters(newFilters)
  }

  useEffect(() => {
    if (!dbReady) return
    const params = new URLSearchParams()
    if (filters.state)      params.set('state',      filters.state)
    if (filters.county)     params.set('county',     filters.county)
    if (filters.min_score)  params.set('min_score',  filters.min_score)
    if (filters.land_cover) params.set('land_cover', filters.land_cover)
    if (filters.max_slope)  params.set('max_slope',  filters.max_slope)

    const existingParams = new URLSearchParams({ state: filters.state || 'NJ' })
    if (filters.county) existingParams.set('county', filters.county)

    Promise.all([
      fetch(`${API}/api/sites?${params}`).then(r => r.json()),
      fetch(`${API}/api/existing?${existingParams}`).then(r => r.json()),
    ])
      .then(([sitesData, existingData]) => {
        setSites(Array.isArray(sitesData) ? sitesData : [])
        setExisting(Array.isArray(existingData) ? existingData : [])
      })
      .catch(console.error)
  }, [filters, dbReady])

  function openSite(site) {
    fetch(`${API}/api/site/${site.candidate_id}`)
      .then(r => r.json())
      .then(d => setSelectedSite(d))
      .catch(() => setSelectedSite({ site, nearby: [] }))
  }

  const topSites = [...sites].sort((a, b) => b.total_score - a.total_score).slice(0, 20)

  return (
    <div className="h-screen flex flex-col bg-slate-950 text-white">

      {/* ── Header ── */}
      <header className="bg-slate-900 border-b border-white/10 px-6 py-3 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-gradient-to-br from-orange-500 to-yellow-400 rounded-lg flex items-center justify-center font-bold text-white text-lg">S</div>
          <div>
            <h1 className="text-xl font-bold bg-gradient-to-r from-orange-400 to-yellow-400 bg-clip-text text-transparent leading-tight">
              Solar Site Finder
            </h1>
            <p className="text-xs text-gray-500">CS 210 Data Management — Solar Suitability Dashboard</p>
          </div>
        </div>

        {/* Tab Navigation */}
        <nav className="flex gap-1 bg-slate-800 rounded-lg p-1">
          {[
            { id: TABS.MAP,     label: 'Map View' },
            { id: TABS.CHARTS,  label: 'Charts' },
            { id: TABS.REPORT,  label: 'Full Report' },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? 'bg-orange-500 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>

        {/* Stats badges */}
        {stats && (
          <div className="hidden lg:flex gap-3 text-sm">
            <span className="bg-slate-800 px-3 py-1 rounded-full text-orange-400 font-medium">
              {stats.totals?.candidates?.toLocaleString()} candidates
            </span>
            <span className="bg-slate-800 px-3 py-1 rounded-full text-green-400 font-medium">
              {stats.totals?.existing} installations
            </span>
          </div>
        )}
      </header>

      {/* ── Not-ready banner ── */}
      {!loading && !dbReady && (
        <div className="bg-yellow-900/50 border-b border-yellow-700 px-6 py-3 text-yellow-300 text-sm">
          Database not ready. Run setup scripts first:
          <code className="ml-2 bg-black/30 px-2 py-0.5 rounded font-mono text-xs">
            python scripts/create_database.py &amp;&amp; python scripts/load_datasets.py &amp;&amp; python scripts/generate_candidate_sites.py &amp;&amp; python scripts/score_sites.py
          </code>
        </div>
      )}

      {/* ── Main layout ── */}
      <div className="flex-1 flex overflow-hidden">

        {/* Left: filter panel */}
        <FilterPanel filters={filters} onApply={applyFilters} stats={stats} />

        {/* Right: tab content */}
        <main className="flex-1 overflow-hidden relative">
          {loading && (
            <div className="absolute inset-0 flex items-center justify-center z-10 bg-slate-950/80">
              <div className="text-center">
                <div className="w-10 h-10 border-2 border-orange-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
                <p className="text-gray-400 text-sm">Loading data…</p>
              </div>
            </div>
          )}

          {activeTab === TABS.MAP && (
            <MapView
              sites={sites}
              existing={existing}
              topSites={topSites}
              onSiteClick={openSite}
            />
          )}

          {activeTab === TABS.CHARTS && (
            <div className="h-full overflow-y-auto p-6">
              <StatsCharts stats={stats} sites={sites} />
            </div>
          )}

          {activeTab === TABS.REPORT && (
            <div className="h-full overflow-y-auto p-6">
              <TopSitesList sites={topSites} onSiteClick={openSite} stats={stats} />
            </div>
          )}
        </main>
      </div>

      {/* Site detail modal */}
      {selectedSite && (
        <SiteDetailModal data={selectedSite} onClose={() => setSelectedSite(null)} />
      )}
    </div>
  )
}

export default App
