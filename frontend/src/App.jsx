import { useState, useRef, useEffect } from 'react'
import './App.css'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const DEFAULT_DBS = [
  { id: 'chinook', name: 'Chinook', path: 'data/datasets/chinook.sqlite', icon: '🎵' },
  { id: 'app',    name: 'App DB',  path: 'data/app.db',                   icon: '🗃️' },
]

const PILL_COLORS = [
  { bg: 'rgba(10,132,255,0.18)',  border: 'rgba(10,132,255,0.35)',  text: '#0a84ff',  dot: '#0a84ff'  },
  { bg: 'rgba(48,209,88,0.18)',   border: 'rgba(48,209,88,0.35)',   text: '#30d158',  dot: '#30d158'  },
  { bg: 'rgba(191,90,242,0.18)', border: 'rgba(191,90,242,0.35)', text: '#bf5af2',  dot: '#bf5af2'  },
  { bg: 'rgba(255,159,10,0.18)', border: 'rgba(255,159,10,0.35)', text: '#ff9f0a',  dot: '#ff9f0a'  },
  { bg: 'rgba(100,210,255,0.18)',border: 'rgba(100,210,255,0.35)',text: '#64d2ff',  dot: '#64d2ff'  },
  { bg: 'rgba(255,69,58,0.18)',  border: 'rgba(255,69,58,0.35)',  text: '#ff453a',  dot: '#ff453a'  },
]

export default function App() {
  const [databases, setDatabases]     = useState(() => {
    try {
      const saved = localStorage.getItem('askdb_databases')
      return saved ? JSON.parse(saved) : DEFAULT_DBS
    } catch { return DEFAULT_DBS }
  })
  const [activeDb,  setActiveDb]      = useState(() => {
    try {
      const saved = localStorage.getItem('askdb_active_db')
      return saved ? JSON.parse(saved) : DEFAULT_DBS[0]
    } catch { return DEFAULT_DBS[0] }
  })
  const [messages,  setMessages]      = useState([])
  const [input,     setInput]         = useState('')
  const [loading,   setLoading]       = useState(false)
  const [tab,       setTab]           = useState('chat')
  const [showConnect, setShowConnect] = useState(false)
  const [schema,    setSchema]        = useState(null)
  const [pillColor, setPillColor]     = useState(0)
  const [cornerFlash, setCornerFlash] = useState(false)
  const [pillVisible, setPillVisible] = useState(true)
  const msgRefs   = useRef({})
  const bottomRef = useRef(null)
  const pillRef   = useRef(null)
  const pillPos   = useRef({ x: 320, y: 40, vx: 1.6, vy: 1.1 })
  const colorIdx  = useRef(0)

  // DVD bounce animation
  useEffect(() => {
    let raf
    function bounce() {
      const pill = pillRef.current
      if (!pill) { raf = requestAnimationFrame(bounce); return }
      const pw   = pill.offsetWidth  || 110
      const ph   = pill.offsetHeight || 34
      const maxX = window.innerWidth  - pw
      const maxY = window.innerHeight - ph
      const p    = pillPos.current
      p.x += p.vx
      p.y += p.vy
      let hitX = false, hitY = false
      if (p.x <= 0)    { p.x = 0;    p.vx =  Math.abs(p.vx); hitX = true }
      if (p.x >= maxX) { p.x = maxX; p.vx = -Math.abs(p.vx); hitX = true }
      if (p.y <= 0)    { p.y = 0;    p.vy =  Math.abs(p.vy); hitY = true }
      if (p.y >= maxY) { p.y = maxY; p.vy = -Math.abs(p.vy); hitY = true }
      if (hitX || hitY) {
        colorIdx.current = (colorIdx.current + 1) % PILL_COLORS.length
        setPillColor(colorIdx.current)
        if (hitX && hitY) {          // Perfect corner hit!
          setCornerFlash(true)
          setTimeout(() => setCornerFlash(false), 600)
        }
      }
      pill.style.left = p.x + 'px'
      pill.style.top  = p.y + 'px'
      raf = requestAnimationFrame(bounce)
    }
    raf = requestAnimationFrame(bounce)
    return () => cancelAnimationFrame(raf)
  }, [])

  // Persist databases list and active db to localStorage
  useEffect(() => {
    localStorage.setItem('askdb_databases', JSON.stringify(databases))
  }, [databases])

  useEffect(() => {
    localStorage.setItem('askdb_active_db', JSON.stringify(activeDb))
  }, [activeDb])

  const [suggestions, setSuggestions] = useState([])

  // Load schema + suggestions whenever active DB changes
  useEffect(() => {
    setSchema(null)
    setSuggestions([])
    fetch(`${API}/schema?db_path=${encodeURIComponent(activeDb.path)}`)
      .then(r => {
        if (!r.ok) throw new Error('not found')
        return r.json()
      })
      .then(d => {
        if (!d.tables) throw new Error('no tables')
        setSchema(d.tables)
      })
      .catch(() => {
        // DB not accessible (e.g. local file on hosted version) — remove it and fall back
        const isDefault = DEFAULT_DBS.find(d => d.id === activeDb.id)
        if (!isDefault) {
          setDatabases(prev => prev.filter(d => d.id !== activeDb.id))
          setActiveDb(DEFAULT_DBS[0])
        }
      })
    // Load schema-aware suggestions
    fetch(`${API}/suggest?db_path=${encodeURIComponent(activeDb.path)}`)
      .then(r => r.json())
      .then(d => { if (d.questions) setSuggestions(d.questions.slice(0, 4)) })
      .catch(() => {})
  }, [activeDb])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  async function sendMessage(e) {
    e.preventDefault()
    const q = input.trim()
    if (!q || loading) return
    setInput('')
    const userMsg = { role: 'user', text: q, id: Date.now() }
    setMessages(prev => [...prev, userMsg])
    setLoading(true)
    try {
      const res = await fetch(`${API}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q, db_path: activeDb.path }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Server error')
      setMessages(prev => [...prev, { role: 'assistant', data, id: Date.now() }])
    } catch (err) {
      setMessages(prev => [...prev, { role: 'error', text: err.message, id: Date.now() }])
    } finally {
      setLoading(false)
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(e) }
  }

  function scrollToMessage(id) {
    msgRefs.current[id]?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  function switchDb(db) { setActiveDb(db); setMessages([]) }

  function removeDb(e, db) {
    e.stopPropagation()
    if (DEFAULT_DBS.find(d => d.id === db.id)) return // protect built-in DBs
    const remaining = databases.filter(d => d.id !== db.id)
    setDatabases(remaining)
    if (activeDb.id === db.id) { setActiveDb(DEFAULT_DBS[0]); setMessages([]) }
  }

  const userMessages = messages.filter(m => m.role === 'user')

  return (
    <div className="app">
      {/* Left sidebar */}
      <aside className="sidebar">
        <div className="logo">
          <span className="logo-icon">🗄️</span>
          <span className="logo-text"><span className="logo-ask">Ask</span><span className="logo-db">DB</span><span className="logo-ai">.Ai</span></span>
        </div>

        <div className="sidebar-section-label">Databases</div>
        <div className="db-list">
          {databases.map(db => (
            <div key={db.id} className="db-item-wrap">
              <button className={`db-item ${activeDb.id === db.id ? 'active' : ''}`} onClick={() => switchDb(db)}>
                <span className="db-icon">{db.icon}</span>
                <span className="db-name">{db.name}</span>
                {activeDb.id === db.id && <span className="db-dot" />}
              </button>
              {!DEFAULT_DBS.find(d => d.id === db.id) && (
                <button className="db-delete-btn" onClick={e => removeDb(e, db)} title="Remove database">✕</button>
              )}
            </div>
          ))}
        </div>

        <button className="connect-btn" onClick={() => setShowConnect(true)}>
          <span>+</span> Connect Database
        </button>

        <div className="sidebar-divider" />

        <nav>
          <button className={`nav-btn ${tab === 'chat' ? 'active' : ''}`} onClick={() => setTab('chat')}>
            <span>💬</span> Chat
          </button>
          <button className={`nav-btn ${tab === 'dq' ? 'active' : ''}`} onClick={() => setTab('dq')}>
            <span>🔍</span> Data Quality
          </button>
        </nav>

      </aside>

      {/* DVD-bounce pill */}
      <div
        ref={pillRef}
        className={`db-pill${cornerFlash ? ' pill-corner' : ''}${!pillVisible ? ' pill-hidden' : ''}`}
        style={{
          background:   PILL_COLORS[pillColor].bg,
          borderColor:  PILL_COLORS[pillColor].border,
          color:        PILL_COLORS[pillColor].text,
          pointerEvents: 'auto',
          cursor: 'pointer',
        }}
        onClick={() => setPillVisible(false)}
        title="Click to hide"
      >
        <span className="pill-dot" style={{ background: PILL_COLORS[pillColor].dot, boxShadow: `0 0 7px ${PILL_COLORS[pillColor].dot}` }} />
        AskDB.Ai
      </div>

      {/* Restore dot — appears when pill is hidden */}
      {!pillVisible && (
        <button className="pill-restore" onClick={() => setPillVisible(true)} title="Show AskDB.Ai">
          <span className="pill-restore-dot" />
        </button>
      )}

      {/* Main */}
      <main className="main">
        {tab === 'chat' && (
          <ChatView
            messages={messages}
            loading={loading}
            input={input}
            setInput={setInput}
            onSubmit={sendMessage}
            onKeyDown={handleKeyDown}
            activeDb={activeDb}
            bottomRef={bottomRef}
            msgRefs={msgRefs}
            onSuggestion={q => { setInput(q) }}
            suggestions={suggestions}
          />
        )}
        {tab === 'dq' && <DataQualityView activeDb={activeDb} />}
      </main>

      {/* Floating: Query History */}
      <QueryHistoryPanel userMessages={userMessages} onJump={scrollToMessage} />

      {/* Floating: Schema Browser */}
      <SchemaPanel schema={schema} activeDb={activeDb} databases={databases} onSwitch={db => { setActiveDb(db); setMessages([]) }} />

      {showConnect && (
        <ConnectModal
          onClose={() => setShowConnect(false)}
          onConnect={db => { setDatabases(p => [...p, db]); setActiveDb(db); setShowConnect(false); setMessages([]) }}
        />
      )}
    </div>
  )
}

// ── Query History Panel (floating, top-right) ──────────────────────────────

function QueryHistoryPanel({ userMessages, onJump }) {
  return (
    <aside className="float-panel qh-panel">
      <div className="fp-title">
        <span className="fp-icon">🕐</span>
        Query History
        {userMessages.length > 0 && (
          <span className="fp-badge">{userMessages.length}</span>
        )}
      </div>
      {userMessages.length === 0 ? (
        <p className="fp-empty">No queries yet</p>
      ) : (
        <div className="history-list">
          {[...userMessages].reverse().map((m, i) => (
            <button
              key={m.id}
              className="history-item"
              onClick={() => onJump(m.id)}
            >
              <span className="history-num">{userMessages.length - i}</span>
              <span className="history-text">{m.text}</span>
              <span className="history-arrow">↗</span>
            </button>
          ))}
        </div>
      )}
    </aside>
  )
}

// ── Schema Panel (floating, bottom-right) ──────────────────────────────────

function SchemaPanel({ schema, activeDb, databases, onSwitch }) {
  const [schemaOpen, setSchemaOpen] = useState({})
  const [dropdownOpen, setDropdownOpen] = useState(false)
  function toggleTable(t) { setSchemaOpen(p => ({ ...p, [t]: !p[t] })) }

  return (
    <aside className="float-panel schema-panel">
      <div className="fp-title">
        <span className="fp-icon">🗂</span>
        Schema
        <button
          className="schema-db-dropdown-btn"
          onClick={() => setDropdownOpen(o => !o)}
          title="Switch database"
        >
          <span className="schema-db-active-name">{activeDb.icon} {activeDb.name}</span>
          <span className={`schema-dropdown-arrow${dropdownOpen ? ' open' : ''}`}>▾</span>
        </button>
      </div>
      {dropdownOpen && (
        <div className="schema-db-switcher">
          {databases.map(db => (
            <button
              key={db.id}
              className={`schema-db-btn${activeDb.id === db.id ? ' active' : ''}`}
              onClick={() => { onSwitch(db); setDropdownOpen(false) }}
            >
              {db.icon} {db.name}
            </button>
          ))}
        </div>
      )}
      {!schema ? (
        <p className="fp-empty">Loading…</p>
      ) : Object.keys(schema).length === 0 ? (
        <p className="fp-empty">No tables found</p>
      ) : (
        <div className="schema-list">
          {Object.entries(schema).map(([table, cols]) => (
            <div key={table} className="schema-table">
              <button className="schema-table-header" onClick={() => toggleTable(table)}>
                <span className="schema-table-icon">{schemaOpen[table] ? '▾' : '▸'}</span>
                <span className="schema-table-name">{table}</span>
                <span className="schema-col-count">{cols.length}</span>
              </button>
              {schemaOpen[table] && (
                <div className="schema-cols">
                  {cols.map(c => (
                    <div key={c} className="schema-col">
                      <span className="schema-col-dot" />
                      {c}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </aside>
  )
}

// ── Chat View ──────────────────────────────────────────────────────────────

function ChatView({ messages, loading, input, setInput, onSubmit, onKeyDown, activeDb, bottomRef, msgRefs, onSuggestion, suggestions }) {
  const fallbackSuggestions = ['How many records are in each table?', 'Show top 10 rows', 'What are the most common values?', 'Show a summary of the data']
  const chips = suggestions && suggestions.length > 0 ? suggestions : fallbackSuggestions
  return (
    <div className="chat-view">
      <div className="messages-area">
        {messages.length === 0 && !loading && (
          <div className="empty-state">
            <h2>What would you like<br />to know?</h2>
            <p>Ask anything about your database in plain English</p>
            <div className="suggestions">
              {chips.map(s => (
                <button key={s} className="suggestion-chip" onClick={() => onSuggestion(s)}>{s}</button>
              ))}
            </div>
          </div>
        )}

        {messages.map(msg => (
          <div key={msg.id} ref={el => { if (el) msgRefs.current[msg.id] = el }}>
            <Message msg={msg} />
          </div>
        ))}

        {loading && (
          <div className="msg assistant">
            <div className="msg-bubble loading-bubble">
              <span className="dot" /><span className="dot" /><span className="dot" />
            </div>
            <div className="msg-byline">
              <div className="msg-avatar thinking">
                <span className="avatar-text">DB</span>
                <span className="avatar-ring" />
              </div>
              <span className="msg-byline-label">Thinking…</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <form className="input-bar" onSubmit={onSubmit}>
        <div className="input-wrap">
          <textarea
            className="chat-input"
            placeholder="Ask about the data..."
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            rows={2}
            disabled={loading}
          />
          <div className="input-actions">
            <span className="input-brand">AskDB.Ai</span>
            <button className="send-btn" type="submit" disabled={loading || !input.trim()}>
              {loading ? <span className="spinner" /> : <svg width="15" height="15" viewBox="0 0 15 15" fill="none"><path d="M7.5 2L7.5 13M7.5 2L3 6.5M7.5 2L12 6.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/></svg>}
            </button>
          </div>
        </div>
        <p className="input-hint">Enter to send · Shift+Enter for new line</p>
      </form>
    </div>
  )
}

// ── SVG Chart helpers ───────────────────────────────────────────────────────

const CHART_COLORS = ['#0a84ff','#64d2ff','#30d158','#ff9f0a','#bf5af2','#ff453a','#5e5ce6','#ffd60a']

function polarToCartesian(cx, cy, r, deg) {
  const rad = (deg - 90) * Math.PI / 180
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) }
}

// Resolve chart type: prefer backend viz.kind, fall back to heuristics
function resolveChartType(viz, columns, rows) {
  if (!columns || !rows || rows.length < 2) return null
  // Use backend decision if available and not "table"
  if (viz && viz.kind && viz.kind !== 'table') return viz.kind
  // Heuristic fallback: 2 cols, second numeric
  if (columns.length === 2) {
    const vals = rows.map(r => parseFloat(r[1]))
    if (vals.some(isNaN)) return null
    const sum = vals.reduce((a, b) => a + b, 0)
    if (sum > 85 && sum < 115) return 'pie'
    return 'bar'
  }
  return null
}

function ChartRenderer({ columns, rows, viz }) {
  const type = resolveChartType(viz, columns, rows)
  const [tooltip, setTooltip] = useState(null)
  const [chartType, setChartType] = useState(null)

  useEffect(() => { setChartType(type) }, [type])

  if (!chartType) return null

  // Identify x/y columns from backend hint or default to col 0/1
  const xColIdx = viz?.x ? columns.indexOf(viz.x) : 0
  const yColIdx = viz?.y ? columns.indexOf(viz.y) : 1
  const safeX = xColIdx >= 0 ? xColIdx : 0
  const safeY = yColIdx >= 0 ? yColIdx : 1

  const labels = rows.map(r => String(r[safeX] ?? ''))
  const values = rows.map(r => parseFloat(r[safeY]))
  const total  = values.reduce((a, b) => a + b, 0)

  const showTip = (e, label, value) => {
    const svg = e.currentTarget.closest('svg')
    if (!svg) return
    const rect = svg.getBoundingClientRect()
    setTooltip({ x: e.clientX - rect.left, y: e.clientY - rect.top - 36, label, value })
  }
  const hideTip = () => setTooltip(null)

  const Tooltip = ({ x, y, label, value, isPct }) => (
    <g transform={`translate(${x},${y})`}>
      <rect x="-60" y="-24" width="120" height="24" rx="6" fill="rgba(28,28,30,0.97)" stroke="rgba(255,255,255,0.1)" strokeWidth="1"/>
      <text textAnchor="middle" y="-8" fontSize="10" fill="rgba(235,235,245,0.9)" fontFamily="system-ui">
        {String(label).slice(0, 18)}: {isPct ? value.toFixed(1) + '%' : Number(value).toLocaleString()}
      </text>
    </g>
  )

  const typeOptions = ['bar', 'line', 'pie'].filter(t => {
    if (t === 'pie') return rows.length <= 12
    return true
  })

  const TypeToggle = () => (
    <div className="chart-type-toggle">
      {typeOptions.map(t => (
        <button key={t} className={`chart-type-btn${chartType === t ? ' active' : ''}`} onClick={() => setChartType(t)}>
          {t === 'bar' ? '📊' : t === 'line' ? '📈' : '🥧'}
        </button>
      ))}
    </div>
  )

  // ── Pie ──────────────────────────────────────────────────────────────────
  if (chartType === 'pie') {
    const cx = 100, cy = 100, r = 82
    let angle = 0
    const slices = values.map((v, i) => {
      const sweep = (v / total) * 360
      const s = polarToCartesian(cx, cy, r, angle)
      const e2 = polarToCartesian(cx, cy, r, angle + sweep)
      const large = sweep > 180 ? 1 : 0
      const d = `M ${cx} ${cy} L ${s.x} ${s.y} A ${r} ${r} 0 ${large} 1 ${e2.x} ${e2.y} Z`
      const color = CHART_COLORS[i % CHART_COLORS.length]
      angle += sweep
      return (
        <path key={i} d={d} fill={color} stroke="rgba(0,0,0,0.25)" strokeWidth="1"
          style={{ cursor: 'pointer' }}
          onMouseEnter={ev => showTip(ev, labels[i], (v / total) * 100)}
          onMouseLeave={hideTip}
          onMouseMove={ev => showTip(ev, labels[i], (v / total) * 100)}
        />
      )
    })
    return (
      <div className="chart-wrap">
        <TypeToggle />
        <div className="pie-row">
          <svg width="200" height="200" viewBox="0 0 200 200" style={{ overflow: 'visible', flexShrink: 0 }}>
            <circle cx={cx} cy={cy} r={r} fill="rgba(0,0,0,0.3)" />
            {slices}
            <circle cx={cx} cy={cy} r={36} fill="rgba(10,10,14,0.95)" />
            <text x={cx} y={cy+4} textAnchor="middle" fontSize="11" fill="rgba(235,235,245,0.6)" fontFamily="system-ui">
              {rows.length} items
            </text>
            {tooltip && <Tooltip {...tooltip} isPct={true} />}
          </svg>
          <div className="chart-legend">
            {labels.map((l, i) => (
              <div key={i} className="legend-item">
                <span className="legend-dot" style={{ background: CHART_COLORS[i % CHART_COLORS.length] }} />
                <span className="legend-label" title={l}>{l.slice(0, 20)}</span>
                <span className="legend-val">{((values[i] / total) * 100).toFixed(1)}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  // ── Line ─────────────────────────────────────────────────────────────────
  if (chartType === 'line') {
    const W = 480, H = 160, pad = { l: 48, r: 16, t: 16, b: 36 }
    const innerW = W - pad.l - pad.r
    const innerH = H - pad.t - pad.b
    const numVals = values.filter(v => !isNaN(v))
    const minV = Math.min(...numVals), maxV = Math.max(...numVals)
    const rangeV = maxV - minV || 1
    const pts = values.map((v, i) => ({
      x: pad.l + (i / Math.max(values.length - 1, 1)) * innerW,
      y: pad.t + innerH - ((v - minV) / rangeV) * innerH,
      label: labels[i], value: v
    }))
    const pathD = pts.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ')
    const areaD = `${pathD} L ${pts[pts.length-1].x} ${pad.t + innerH} L ${pad.l} ${pad.t + innerH} Z`
    // Y-axis labels
    const ySteps = 4
    const yLabels = Array.from({length: ySteps + 1}, (_, i) => ({
      y: pad.t + innerH - (i / ySteps) * innerH,
      val: minV + (i / ySteps) * rangeV
    }))
    // X-axis: show up to 8 labels
    const xStep = Math.ceil(labels.length / 8)
    return (
      <div className="chart-wrap line-chart-wrap">
        <TypeToggle />
        <svg width="100%" height={H} viewBox={`0 0 ${W} ${H}`} style={{ overflow: 'visible' }}>
          <defs>
            <linearGradient id="lineGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#0a84ff" stopOpacity="0.3"/>
              <stop offset="100%" stopColor="#0a84ff" stopOpacity="0"/>
            </linearGradient>
          </defs>
          {/* Grid lines */}
          {yLabels.map((yl, i) => (
            <g key={i}>
              <line x1={pad.l} y1={yl.y} x2={W - pad.r} y2={yl.y} stroke="rgba(255,255,255,0.06)" strokeWidth="1"/>
              <text x={pad.l - 6} y={yl.y + 4} textAnchor="end" fontSize="9" fill="rgba(235,235,245,0.4)">
                {Number(yl.val).toLocaleString(undefined, {maximumFractionDigits: 0})}
              </text>
            </g>
          ))}
          {/* X-axis labels */}
          {pts.filter((_, i) => i % xStep === 0).map((p, i) => (
            <text key={i} x={p.x} y={H - 4} textAnchor="middle" fontSize="9" fill="rgba(235,235,245,0.4)">
              {String(p.label).slice(0, 8)}
            </text>
          ))}
          {/* Area fill */}
          <path d={areaD} fill="url(#lineGrad)" />
          {/* Line */}
          <path d={pathD} fill="none" stroke="#0a84ff" strokeWidth="2" strokeLinejoin="round"/>
          {/* Dots */}
          {pts.map((p, i) => (
            <circle key={i} cx={p.x} cy={p.y} r="3" fill="#0a84ff"
              style={{ cursor: 'pointer' }}
              onMouseEnter={ev => showTip(ev, p.label, p.value)}
              onMouseLeave={hideTip}
              onMouseMove={ev => showTip(ev, p.label, p.value)}
            />
          ))}
          {tooltip && <Tooltip {...tooltip} isPct={false} />}
        </svg>
      </div>
    )
  }

  // ── Bar ──────────────────────────────────────────────────────────────────
  const max = Math.max(...values.filter(v => !isNaN(v)))
  const barW = Math.max(20, Math.min(40, Math.floor(420 / rows.length) - 8))
  const gap = Math.max(6, Math.min(14, Math.floor(barW / 3)))
  const svgW = Math.max(rows.length * (barW + gap) + gap + 40, 280)
  return (
    <div className="chart-wrap bar-chart-wrap">
      <TypeToggle />
      <svg width="100%" height="180" viewBox={`0 0 ${svgW} 180`} style={{ overflow: 'visible' }}>
        {/* Y-axis grid */}
        {[0, 0.25, 0.5, 0.75, 1].map((pct, i) => (
          <g key={i}>
            <line x1="0" y1={10 + (1 - pct) * 130} x2={svgW} y2={10 + (1 - pct) * 130}
              stroke="rgba(255,255,255,0.05)" strokeWidth="1"/>
          </g>
        ))}
        {values.map((v, i) => {
          if (isNaN(v)) return null
          const bh = Math.max((v / max) * 130, 2)
          const x = i * (barW + gap) + gap
          const color = CHART_COLORS[i % CHART_COLORS.length]
          return (
            <g key={i} style={{ cursor: 'pointer' }}
              onMouseEnter={ev => showTip(ev, labels[i], v)}
              onMouseLeave={hideTip}
              onMouseMove={ev => showTip(ev, labels[i], v)}>
              <rect x={x} y={140 - bh} width={barW} height={bh} fill={color} rx="3" opacity="0.85"/>
              <text x={x + barW/2} y={156} textAnchor="middle" fontSize="8" fill="rgba(235,235,245,0.4)">
                {String(labels[i]).slice(0, Math.max(6, barW / 7))}
              </text>
            </g>
          )
        })}
        {tooltip && <Tooltip {...tooltip} isPct={false} />}
      </svg>
    </div>
  )
}

function detectChart(columns, rows, viz) {
  return resolveChartType(viz, columns, rows)
}

function exportCSV(columns, rows) {
  const header = columns.join(',')
  const body = rows.map(r => r.map(cell => {
    const v = cell === null ? '' : String(cell)
    return v.includes(',') || v.includes('"') || v.includes('\n') ? `"${v.replace(/"/g, '""')}"` : v
  }).join(',')).join('\n')
  const blob = new Blob([header + '\n' + body], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = 'askdb_results.csv'; a.click()
  URL.revokeObjectURL(url)
}

function Message({ msg }) {
  const [sqlOpen, setSqlOpen] = useState(false)

  if (msg.role === 'user') {
    return (
      <div className="msg user">
        <div className="msg-bubble user-bubble">{msg.text}</div>
      </div>
    )
  }
  if (msg.role === 'error') {
    return (
      <div className="msg assistant">
        <div className="msg-bubble error-bubble">⚠️ {msg.text}</div>
        <div className="msg-byline"><div className="msg-avatar"><span className="avatar-text">DB</span></div></div>
      </div>
    )
  }

  const { data } = msg
  if (data.status === 'rejected') {
    return (
      <div className="msg assistant">
        <div className="msg-bubble assistant-bubble">
          <span className="rejected-label">Couldn't answer</span>
          <p>{data.reason}</p>
        </div>
        <div className="msg-byline"><div className="msg-avatar"><span className="avatar-text">DB</span></div><span className="msg-byline-label">AskDB.Ai</span></div>
      </div>
    )
  }

  const chartType = resolveChartType(data.viz, data.columns, data.rows)

  return (
    <div className="msg assistant">
      <div className="msg-bubble assistant-bubble">
        {data.insight?.headline && <p className="insight-headline">{data.insight.headline}</p>}
        {data.insight?.key_findings?.length > 0 && (
          <ul className="findings-list">
            {data.insight.key_findings.map((f, i) => <li key={i}>{f}</li>)}
          </ul>
        )}
        {chartType && <ChartRenderer columns={data.columns} rows={data.rows} viz={data.viz} />}
        {data.columns?.length > 0 && (
          <div className="table-section">
            <div className="table-label-row">
              <span className="table-label">{data.rows?.length} result{data.rows?.length !== 1 ? 's' : ''}</span>
              <button className="csv-export-btn" onClick={() => exportCSV(data.columns, data.rows)} title="Download CSV">
                ↓ CSV
              </button>
            </div>
            <ResultsTable columns={data.columns} rows={data.rows} />
          </div>
        )}
        {data.insight?.caveats?.length > 0 && (
          <div className="caveats">{data.insight.caveats.map((c, i) => <p key={i}>⚡ {c}</p>)}</div>
        )}
        {data.sql && (
          <button className="sql-toggle" onClick={() => setSqlOpen(o => !o)}>
            {sqlOpen ? '▾' : '▸'} View SQL
          </button>
        )}
        {sqlOpen && data.sql && <pre className="sql-block">{data.sql}</pre>}
        {data.insight?.confidence && (
          <span className={`confidence-tag ${data.insight.confidence.toLowerCase()}`}>
            {data.insight.confidence} confidence
          </span>
        )}
      </div>
      <div className="msg-byline">
        <div className="msg-avatar"><span className="avatar-text">DB</span></div>
        <span className="msg-byline-label">AskDB.Ai</span>
      </div>
    </div>
  )
}

function ResultsTable({ columns, rows }) {
  return (
    <div className="table-wrapper">
      <table className="results-table">
        <thead><tr>{columns.map(c => <th key={c}>{c}</th>)}</tr></thead>
        <tbody>
          {rows?.slice(0, 50).map((row, i) => (
            <tr key={i}>{row.map((cell, j) => <td key={j}>{cell ?? '—'}</td>)}</tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ── Data Quality ───────────────────────────────────────────────────────────

function DataQualityView({ activeDb }) {
  const [tables, setTables]   = useState(null)
  const [selected, setSelected] = useState('')
  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState(null)

  async function loadTables() {
    try {
      const res = await fetch(`${API}/schema?db_path=${encodeURIComponent(activeDb.path)}`)
      const data = await res.json()
      const list = Object.keys(data.tables)
      setTables(list); if (list.length) setSelected(list[0])
    } catch { setError('Could not load schema.') }
  }
  async function runProfile() {
    setLoading(true); setProfile(null); setError(null)
    try {
      const res = await fetch(`${API}/data-quality/${selected}?db_path=${encodeURIComponent(activeDb.path)}`)
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Error')
      setProfile(data)
    } catch (err) { setError(err.message) }
    finally { setLoading(false) }
  }

  return (
    <div className="dq-view">
      <div className="dq-header">
        <h2>Data Quality</h2>
        <p>Profile tables in <strong>{activeDb.name}</strong> to detect issues.</p>
      </div>
      {!tables ? (
        <button className="connect-btn wide" onClick={loadTables}>Load Tables</button>
      ) : (
        <div className="dq-controls">
          <select className="table-select" value={selected} onChange={e => setSelected(e.target.value)}>
            {tables.map(t => <option key={t}>{t}</option>)}
          </select>
          <button className="send-btn dq-run" onClick={runProfile} disabled={loading}>
            {loading ? <span className="spinner" /> : 'Run'}
          </button>
        </div>
      )}
      {error && <div className="error-card">⚠️ {error}</div>}
      {profile && (
        <div className="dq-result">
          <div className="dq-result-header">
            <span>{selected}</span>
            <span className={`confidence-tag ${profile.confidence?.toLowerCase()}`}>{profile.confidence} Confidence</span>
          </div>
          <pre className="json-block">{JSON.stringify(profile.profile, null, 2)}</pre>
        </div>
      )}
    </div>
  )
}

// ── Connect Modal ──────────────────────────────────────────────────────────

function ConnectModal({ onClose, onConnect }) {
  const [name, setName] = useState('')
  const [path, setPath] = useState('')
  const [icon, setIcon] = useState('🗃️')
  const icons = ['🗃️','🏦','📊','🛒','👤','🏥','🎓','🏭']

  return (
    <div className="modal-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <div className="modal-header">
          <h3>Connect a Database</h3>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>
        <label className="modal-label">Display Name</label>
        <input className="modal-input" placeholder="e.g. Sales DB" value={name} onChange={e => setName(e.target.value)} />
        <label className="modal-label">SQLite File Path</label>
        <input className="modal-input" placeholder="e.g. data/mydb.sqlite" value={path} onChange={e => setPath(e.target.value)} />
        <label className="modal-label">Icon</label>
        <div className="icon-picker">
          {icons.map(ic => <button type="button" key={ic} className={`icon-opt ${ic === icon ? 'selected' : ''}`} onClick={() => setIcon(ic)}>{ic}</button>)}
        </div>
        <div className="modal-actions">
          <button className="modal-cancel" onClick={onClose}>Cancel</button>
          <button className="modal-submit" disabled={!name.trim() || !path.trim()}
            onClick={() => onConnect({ id: Date.now().toString(), name: name.trim(), path: path.trim(), icon })}>
            Connect
          </button>
        </div>
      </div>
    </div>
  )
}
