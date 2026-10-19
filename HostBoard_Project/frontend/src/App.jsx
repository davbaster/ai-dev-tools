import { useEffect, useMemo, useState } from 'react'
import {
  ArrowUpRight,
  Ban,
  BellRing,
  Check,
  ChevronDown,
  CircleUserRound,
  Clock3,
  DoorOpen,
  Edit3,
  LayoutList,
  LogOut,
  Menu,
  MoreHorizontal,
  Plus,
  Settings2,
  ShieldCheck,
  Sparkles,
  Table2,
  UsersRound,
  X,
} from 'lucide-react'
import { backendApi as api } from './api/backendApi'

const preferenceOptions = ['No preference', 'Dining room', 'Patio', 'Bar']

const formatTime = (value) => new Intl.DateTimeFormat('en-US', { hour: 'numeric', minute: '2-digit' }).format(new Date(value))
const formatDate = (value = new Date()) => new Intl.DateTimeFormat('en-US', { weekday: 'long', month: 'long', day: 'numeric' }).format(new Date(value))
const formatRelative = (value) => {
  const minutes = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 60000))
  if (minutes < 1) return 'Just now'
  if (minutes === 1) return '1 min ago'
  return `${minutes} min ago`
}

function App() {
  const [session, setSession] = useState(() => api.getSession())
  const [data, setData] = useState(null)
  const [view, setView] = useState('waitlist')
  const [loading, setLoading] = useState(Boolean(session))
  const [modal, setModal] = useState(null)
  const [toast, setToast] = useState(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const refresh = async () => {
    const dashboard = await api.getDashboard()
    setData(dashboard)
  }

  useEffect(() => {
    if (!session) return undefined
    let mounted = true
    setLoading(true)
    api.getDashboard().then((dashboard) => {
      if (mounted) {
        setData(dashboard)
        setLoading(false)
      }
    }).catch((error) => {
      if (!mounted) return
      setLoading(false)
      if (error.status === 401) {
        api.clearSession()
        setSession(null)
        setData(null)
      } else {
        notify(error.message, 'error')
      }
    })
    return () => { mounted = false }
  }, [session])

  useEffect(() => {
    if (!toast) return undefined
    const timeout = window.setTimeout(() => setToast(null), 3600)
    return () => window.clearTimeout(timeout)
  }, [toast])

  const notify = (message, tone = 'success') => setToast({ message, tone })

  const handleLogin = async (credentials) => {
    try {
      const nextSession = await api.login(credentials)
      setSession(nextSession)
      notify(`Welcome back, ${nextSession.name.split(' ')[0]}.`)
    } catch (error) {
      throw error
    }
  }

  const handleLogout = () => {
    void api.logout()
    setSession(null)
    setData(null)
    setView('waitlist')
  }

  const runMutation = async (action, successMessage) => {
    try {
      await action()
      await refresh()
      setModal(null)
      notify(successMessage)
    } catch (error) {
      if (error.status === 401) {
        api.clearSession()
        setSession(null)
        setData(null)
      } else {
        notify(error.message, 'error')
      }
    }
  }

  if (!session) return <LoginScreen onLogin={handleLogin} />
  if (loading || !data) return <LoadingScreen />

  const activeCount = data.entries.filter((entry) => entry.status === 'waiting').length
  const occupiedTableIds = new Set(data.tables.filter((table) => table.availability === 'occupied').map((table) => table.id))
  const availableCount = data.tables.filter((table) => table.isActive && table.availability === 'available').length

  return (
    <div className="app-shell">
      <aside className={`sidebar ${sidebarOpen ? 'is-open' : ''}`}>
        <div className="brand-lockup">
          <div className="brand-mark"><span>J</span><span>P</span></div>
          <div>
            <div className="brand-name">HOSTBOARD</div>
            <div className="brand-subtitle">June & Pine</div>
          </div>
          <button className="icon-button sidebar-close" onClick={() => setSidebarOpen(false)} aria-label="Close navigation"><X size={18} /></button>
        </div>
        <div className="service-switcher">
          <div className="service-kicker"><span className="live-dot" /> Live service</div>
          <strong>{data.restaurant.serviceLabel}</strong>
          <span className="service-date">{formatDate()}</span>
          <ChevronDown size={15} />
        </div>
        <nav className="primary-nav" aria-label="Primary navigation">
          <NavItem icon={<LayoutList size={18} />} label="Waitlist" active={view === 'waitlist'} onClick={() => { setView('waitlist'); setSidebarOpen(false) }} count={activeCount} />
          <NavItem icon={<Clock3 size={18} />} label="Today’s history" active={view === 'history'} onClick={() => { setView('history'); setSidebarOpen(false) }} />
          {session.role === 'manager' && <NavItem icon={<Settings2 size={18} />} label="Manager settings" active={view === 'settings'} onClick={() => { setView('settings'); setSidebarOpen(false) }} />}
        </nav>
        <div className="sidebar-footer">
          <div className="sidebar-note"><Sparkles size={15} /><span>Keep the room moving.</span></div>
          <div className="profile-row">
            <div className="avatar">{session.name.split(' ').map((part) => part[0]).join('')}</div>
            <div className="profile-copy"><strong>{session.name}</strong><span>{session.role}</span></div>
            <button className="icon-button" onClick={handleLogout} aria-label="Sign out" title="Sign out"><LogOut size={17} /></button>
          </div>
        </div>
      </aside>
      {sidebarOpen && <button className="sidebar-scrim" onClick={() => setSidebarOpen(false)} aria-label="Close navigation" />}
      <main className="main-shell">
        <header className="topbar">
          <button className="icon-button menu-button" onClick={() => setSidebarOpen(true)} aria-label="Open navigation"><Menu size={20} /></button>
          <div className="crumb"><span>Operations</span><span className="crumb-slash">/</span><strong>{view === 'waitlist' ? 'Waitlist' : view === 'history' ? 'Today’s history' : 'Manager settings'}</strong></div>
          <div className="topbar-actions">
            <div className={`open-pill ${data.restaurant.isOpen ? 'is-open' : 'is-closed'}`}><span className="open-pill-dot" /> {data.restaurant.isOpen ? 'Open now' : 'Closed'}</div>
            <div className="topbar-date">{formatDate()}</div>
            <button className="avatar avatar-small" aria-label="Current profile">{session.name.split(' ').map((part) => part[0]).join('')}</button>
          </div>
        </header>
        <div className="content-wrap">
          {view === 'waitlist' && <WaitlistView data={data} onAdd={() => setModal({ type: 'party' })} onEdit={(entry) => setModal({ type: 'party', entry })} onSeat={(entry) => setModal({ type: 'seat', entry })} onCancel={(entry) => setModal({ type: 'cancel', entry })} onReleaseTable={(table) => setModal({ type: 'release-table', table })} />}
          {view === 'history' && <HistoryView data={data} onReleaseTable={(table) => setModal({ type: 'release-table', table })} />}
          {view === 'settings' && session.role === 'manager' && <SettingsView data={data} onRefresh={refresh} onNotify={notify} onModal={setModal} />}
        </div>
      </main>
      {modal?.type === 'party' && <PartyModal entry={modal.entry} entries={data.entries} onClose={() => setModal(null)} onSave={(payload) => runMutation(() => modal.entry ? api.updateEntry(modal.entry.id, payload, session) : api.createEntry(payload, session), modal.entry ? 'Party details updated.' : 'Party added to the waitlist.')} />}
      {modal?.type === 'seat' && <SeatModal entry={modal.entry} tables={data.tables} entries={data.entries} areas={data.areas} onClose={() => setModal(null)} onSeat={(tableId) => runMutation(() => api.seatEntry(modal.entry.id, tableId, session), `${modal.entry.guestName} is seated.`)} />}
      {modal?.type === 'cancel' && <ConfirmModal title="Cancel this party?" description={`${modal.entry.guestName} will leave the active queue. This action will be kept in today’s history.`} confirmLabel="Cancel party" onClose={() => setModal(null)} onConfirm={() => runMutation(() => api.cancelEntry(modal.entry.id, session), `${modal.entry.guestName} was cancelled.`)} />}
      {modal?.type === 'table' && <TableModal table={modal.table} areas={data.areas} onClose={() => setModal(null)} onSave={(payload) => runMutation(() => modal.table ? api.updateTable(modal.table.id, payload) : api.createTable(payload), modal.table ? 'Table details updated.' : 'Table added to the room.')} />}
      {modal?.type === 'staff' && <StaffModal onClose={() => setModal(null)} onSave={(payload) => runMutation(() => api.createStaff(payload), 'Staff account created.')} />}
      {modal?.type === 'release-table' && <ConfirmModal title={`Mark ${modal.table.name} as free?`} description={modal.table.currentParty ? `${modal.table.currentParty.guestName}’s party (${modal.table.currentParty.partySize} guests) has finished using table ${modal.table.name}. It will become available immediately for new parties.` : `Mark table ${modal.table.name} as free and ready for new guests.`} confirmLabel="Mark table free" onClose={() => setModal(null)} onConfirm={() => runMutation(() => api.releaseTable(modal.table.id), `Table ${modal.table.name} is now free.`)} />}
      {toast && <div className={`toast toast-${toast.tone}`} role="status"><span className="toast-icon">{toast.tone === 'error' ? <Ban size={16} /> : <Check size={16} />}</span>{toast.message}</div>}
    </div>
  )
}

function NavItem({ icon, label, active, onClick, count }) {
  return <button className={`nav-item ${active ? 'is-active' : ''}`} onClick={onClick}>{icon}<span>{label}</span>{count > 0 && <span className="nav-count">{count}</span>}</button>
}

function LoadingScreen() {
  return <div className="loading-screen"><div className="loading-orbit"><span /></div><span>Opening the service board</span></div>
}

function LoginScreen({ onLogin }) {
  const [identifier, setIdentifier] = useState('maya@juneandpine.com')
  const [password, setPassword] = useState('demo1234')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const submit = async (event) => {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      await onLogin({ identifier, password })
    } catch (loginError) {
      setError(loginError.message)
    } finally {
      setBusy(false)
    }
  }

  return <div className="login-screen">
    <div className="login-ambient ambient-one" /><div className="login-ambient ambient-two" />
    <div className="login-left">
      <div className="login-brand"><div className="brand-mark"><span>J</span><span>P</span></div><span>HOSTBOARD</span></div>
      <div className="login-copy"><p className="eyebrow">June & Pine / Service operations</p><h1>Make every<br /><em>seat</em> count.</h1><p>A clear-eyed waitlist for the moments between arrival and first bite.</p></div>
      <div className="login-footer"><span>Staff workspace</span><span className="login-footer-line" /><span>Brooklyn, NY</span></div>
    </div>
    <div className="login-panel-wrap"><div className="login-panel">
      <div className="panel-kicker"><ShieldCheck size={16} /> Staff sign in</div>
      <h2>Good evening.</h2><p className="panel-intro">Sign in to open tonight’s service board.</p>
      <form onSubmit={submit} className="login-form">
        <Field label="Work email" value={identifier} onChange={setIdentifier} type="email" autoComplete="username" />
        <Field label="Password" value={password} onChange={setPassword} type="password" autoComplete="current-password" />
        {error && <div className="form-error"><Ban size={15} />{error}</div>}
        <button className="button button-primary button-wide" disabled={busy}>{busy ? 'Opening board…' : 'Enter service board'} <ArrowUpRight size={17} /></button>
      </form>
      <div className="demo-accounts"><span>Demo access</span><button type="button" onClick={() => { setIdentifier('maya@juneandpine.com'); setPassword('demo1234') }}>Manager</button><button type="button" onClick={() => { setIdentifier('luca@juneandpine.com'); setPassword('demo1234') }}>Host</button></div>
    </div></div>
  </div>
}

function WaitlistView({ data, onAdd, onEdit, onSeat, onCancel, onReleaseTable }) {
  const [filter, setFilter] = useState('All')
  const waiting = data.entries.filter((entry) => entry.status === 'waiting')
  const seated = data.entries.filter((entry) => entry.status === 'seated').length
  const available = data.tables.filter((table) => table.isActive && table.availability === 'available').length
  const visible = filter === 'All' ? waiting : waiting.filter((entry) => entry.seatingPreference === filter)
  const oldest = waiting[0]

  return <>
    <section className="page-intro page-intro-board">
      <div><p className="eyebrow"><span className="eyebrow-pulse" /> Live service / {data.restaurant.serviceLabel}</p><h1>Keep the room moving<span className="period">.</span></h1><p className="page-description">The active board for tonight’s walk-ins. First in, first served.</p></div>
      <button className="button button-primary button-add" onClick={onAdd}><Plus size={18} /> Add party</button>
    </section>
    <section className="metric-strip" aria-label="Service summary">
      <Metric label="Waiting now" value={waiting.length} detail={waiting.length ? `Next up: ${waiting[0].guestName}` : 'The queue is clear'} accent="red" />
      <Metric label="Seated tonight" value={seated} detail="Completed service entries" accent="green" />
      <Metric label="Open tables" value={available} detail="Ready for a party" accent="ink" />
      <Metric label="Longest wait" value={oldest ? formatRelative(oldest.createdAt) : '—'} detail={oldest ? oldest.guestName : 'No active parties'} accent="amber" />
    </section>
    <div className="board-grid">
      <section className="queue-panel">
        <div className="section-heading queue-heading"><div><p className="eyebrow">The line</p><h2>Active waitlist <span className="heading-count">{waiting.length}</span></h2></div><div className="filter-tabs">{['All', 'Dining room', 'Patio', 'Bar'].map((item) => <button key={item} className={filter === item ? 'is-active' : ''} onClick={() => setFilter(item)}>{item}</button>)}</div></div>
        {visible.length === 0 ? <EmptyQueue onAdd={onAdd} filtered={filter !== 'All'} /> : <div className="queue-list">{visible.map((entry, index) => <QueueRow key={entry.id} entry={entry} position={waiting.indexOf(entry) + 1} isNext={waiting.indexOf(entry) === 0} onEdit={onEdit} onSeat={onSeat} onCancel={onCancel} />)}</div>}
      </section>
      <aside className="room-rail">
        <div className="rail-heading"><div><p className="eyebrow">The room</p><h2>Table pulse</h2></div><Table2 size={20} /></div>
        <div className="table-summary"><strong>{available}</strong><span>of {data.tables.filter((table) => table.isActive).length} active tables open</span><div className="table-meter"><span style={{ width: `${Math.max(6, (available / Math.max(1, data.tables.filter((table) => table.isActive).length)) * 100)}%` }} /></div></div>
        <div className="mini-table-grid">{data.tables.filter((table) => table.isActive).map((table) => { const occupied = table.availability === 'occupied'; return <button type="button" className={`mini-table ${occupied ? 'is-occupied' : ''}`} key={table.id} onClick={() => occupied && onReleaseTable && onReleaseTable(table)} style={{ cursor: occupied ? 'pointer' : 'default', textAlign: 'left', border: 'none', font: 'inherit' }} title={occupied ? `Occupied by ${table.currentParty?.guestName || 'party'}. Click to mark table free.` : `${table.capacity} seats available`}><span>{table.name}</span><small>{occupied ? (table.currentParty ? `${table.currentParty.guestName} · Free` : 'Occupied · Free') : `${table.capacity} seats`}</small></button> })}</div>
        <div className="rail-divider" />
        <div className="rail-activity"><div className="rail-heading small"><h3>Service note</h3><BellRing size={16} /></div><p>Click occupied tables to mark them free once guests depart, or select an available table when seating.</p><div className="activity-user"><div className="avatar avatar-tiny">JP</div><span>June & Pine staff workspace</span></div></div>
      </aside>
    </div>
  </>
}

function Metric({ label, value, detail, accent }) {
  return <div className={`metric metric-${accent}`}><div className="metric-top"><span>{label}</span><span className="metric-mark" /></div><strong>{value}</strong><small>{detail}</small></div>
}

function QueueRow({ entry, position, isNext, onEdit, onSeat, onCancel }) {
  return <article className={`queue-row ${isNext ? 'is-next' : ''}`}>
    <div className="queue-position">{isNext ? <span className="next-tag">Next</span> : <span>{String(position).padStart(2, '0')}</span>}</div>
    <div className="party-main"><div className="party-name-line"><h3>{entry.guestName}</h3>{entry.notes && <span className="note-flag" title={entry.notes}>Note</span>}</div><div className="party-meta"><span><UsersRound size={14} /> {entry.partySize} {entry.partySize === 1 ? 'guest' : 'guests'}</span><span><DoorOpen size={14} /> {entry.seatingPreference}</span><span><Clock3 size={14} /> {formatTime(entry.createdAt)}</span><span className="party-phone-inline">{entry.phone}</span></div></div>
    <div className="party-phone">{entry.phone}</div>
    <div className="wait-age"><strong>{formatRelative(entry.createdAt)}</strong><span>waiting</span></div>
    <div className="row-actions"><button className="button button-seat" onClick={() => onSeat(entry)}><Table2 size={15} /> Seat</button><button className="icon-button" onClick={() => onEdit(entry)} aria-label={`Edit ${entry.guestName}`} title="Edit"><Edit3 size={16} /></button><button className="icon-button icon-danger" onClick={() => onCancel(entry)} aria-label={`Cancel ${entry.guestName}`} title="Cancel"><X size={17} /></button></div>
  </article>
}

function EmptyQueue({ onAdd, filtered }) {
  return <div className="empty-state"><div className="empty-icon"><Sparkles size={22} /></div><h3>{filtered ? 'No parties in this area' : 'A clear room, for now'}</h3><p>{filtered ? 'Try another seating preference.' : 'When the first walk-in arrives, add them to the board.'}</p>{!filtered && <button className="button button-secondary" onClick={onAdd}><Plus size={16} /> Add first party</button>}</div>
}

function HistoryView({ data, onReleaseTable }) {
  const history = data.entries.filter((entry) => entry.status !== 'waiting').sort((a, b) => new Date(b.seatedAt || b.cancelledAt || b.createdAt) - new Date(a.seatedAt || a.cancelledAt || a.createdAt))
  const seated = history.filter((entry) => entry.status === 'seated').length
  return <><section className="page-intro"><div><p className="eyebrow">Service archive / Today</p><h1>Today’s history<span className="period">.</span></h1><p className="page-description">A quiet record of every handoff after the waitlist.</p></div><div className="history-total"><strong>{history.length}</strong><span>completed entries</span></div></section><section className="history-summary"><div><span className="summary-label">Seated</span><strong>{seated}</strong><span>parties at a table</span></div><div><span className="summary-label">Cancelled</span><strong>{history.length - seated}</strong><span>parties left the line</span></div><div><span className="summary-label">Service date</span><strong>{new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric' }).format(new Date())}</strong><span>{data.restaurant.name}</span></div></section><section className="history-panel"><div className="section-heading"><div><p className="eyebrow">The log</p><h2>Completed entries</h2></div><span className="muted-label">Current service day</span></div>{history.length === 0 ? <EmptyHistory /> : <div className="history-list">{history.map((entry) => <HistoryRow key={entry.id} entry={entry} table={data.tables.find((table) => table.id === entry.assignedTableId)} onReleaseTable={onReleaseTable} />)}</div>}</section></>
}

function HistoryRow({ entry, table, onReleaseTable }) {
  const isSeated = entry.status === 'seated'
  const isOccupied = isSeated && entry.isTableOccupied && table && table.availability === 'occupied'
  return <div className="history-row"><div className={`history-status ${isSeated ? 'status-seated' : 'status-cancelled'}`}>{isSeated ? <Check size={15} /> : <X size={15} />}</div><div className="history-party"><strong>{entry.guestName}</strong><span>{entry.partySize} guests · {entry.seatingPreference}</span></div><div className="history-detail"><span>{isSeated ? `Seated at ${table?.name || 'table'}` : 'Cancelled from queue'}</span><small>{formatTime(entry.seatedAt || entry.cancelledAt || entry.createdAt)}</small></div><div className="history-staff"><div className="avatar avatar-tiny">{(entry.completedBy || 'Staff').split(' ').map((part) => part[0]).join('')}</div><span>{entry.completedBy || 'Staff'}</span></div>{isOccupied && <button className="button button-ghost" style={{ padding: '0.35rem 0.75rem', fontSize: '0.85rem' }} onClick={() => onReleaseTable(table)}>Free table</button>}</div>
}

function EmptyHistory() { return <div className="empty-state compact"><div className="empty-icon"><Clock3 size={21} /></div><h3>Nothing filed yet</h3><p>Seated and cancelled parties will appear here.</p></div> }

function SettingsView({ data, onRefresh, onNotify, onModal }) {
  const [tab, setTab] = useState('room')
  const [restaurantName, setRestaurantName] = useState(data.restaurant.name)
  const [isOpen, setIsOpen] = useState(data.restaurant.isOpen)
  const [saving, setSaving] = useState(false)
  const saveRestaurant = async (event) => {
    event.preventDefault()
    setSaving(true)
    try { await api.updateRestaurant({ name: restaurantName, isOpen }); await onRefresh(); onNotify('Restaurant settings saved.') } catch (error) { onNotify(error.message, 'error') } finally { setSaving(false) }
  }
  return <><section className="page-intro settings-intro"><div><p className="eyebrow">Control room / Manager access</p><h1>Make it yours<span className="period">.</span></h1><p className="page-description">The small controls that keep tonight’s operation feeling like yours.</p></div><div className="manager-seal"><ShieldCheck size={19} /><span>Manager access</span></div></section><div className="settings-layout"><div className="settings-tabs" role="tablist"><button className={tab === 'room' ? 'is-active' : ''} onClick={() => setTab('room')}><Settings2 size={17} /> Restaurant</button><button className={tab === 'tables' ? 'is-active' : ''} onClick={() => setTab('tables')}><Table2 size={17} /> Tables <span>{data.tables.length}</span></button><button className={tab === 'staff' ? 'is-active' : ''} onClick={() => setTab('staff')}><UsersRound size={17} /> Staff <span>{data.users.length}</span></button></div><div className="settings-content">{tab === 'room' && <form className="settings-section" onSubmit={saveRestaurant}><div className="settings-section-head"><div><p className="eyebrow">Restaurant identity</p><h2>Tonight’s room</h2></div><button className="button button-primary" disabled={saving}>{saving ? 'Saving…' : 'Save changes'}</button></div><div className="form-grid"><Field label="Restaurant name" value={restaurantName} onChange={setRestaurantName} /><div className="setting-toggle"><div><strong>Accept new parties</strong><span>When closed, the queue stays visible but new entries are paused.</span></div><button type="button" className={`toggle ${isOpen ? 'is-on' : ''}`} onClick={() => setIsOpen((value) => !value)} aria-label="Toggle restaurant open status"><span /></button></div></div><div className="preference-section"><div><p className="eyebrow">Seating preferences</p><h3>Areas in the room</h3></div><div className="preference-chips">{data.areas.filter((area) => area.isActive).map((area) => <span key={area.id} className="preference-chip"><span className="chip-dot" />{area.name}</span>)}</div></div></form>}{tab === 'tables' && <TablesSettings data={data} onModal={onModal} />}{tab === 'staff' && <StaffSettings data={data} onModal={onModal} onRefresh={onRefresh} onNotify={onNotify} />}</div></div></>
}

function TablesSettings({ data, onModal }) {
  return <section className="settings-section"><div className="settings-section-head"><div><p className="eyebrow">Room inventory</p><h2>Tables</h2><p className="section-subtitle">Active tables are available to hosts when seating a party.</p></div><button className="button button-primary" onClick={() => onModal({ type: 'table' })}><Plus size={16} /> Add table</button></div><div className="inventory-list">{data.tables.map((table) => <div className={`inventory-row ${!table.isActive ? 'is-inactive' : ''}`} key={table.id}><div className="inventory-symbol"><Table2 size={18} /></div><div className="inventory-main"><strong>{table.name}</strong><span>{table.capacity} seats · {data.areas.find((area) => area.id === table.areaId)?.name || 'No area'}</span></div><span className={`inventory-status ${table.availability}`}>{table.availability === 'occupied' ? 'Occupied' : table.isActive ? 'Available' : 'Inactive'}</span>{table.availability === 'occupied' && <button className="text-button" style={{ marginLeft: '0.5rem', fontWeight: 600 }} onClick={() => onModal({ type: 'release-table', table })}>Free table</button>}<button className="icon-button" onClick={() => onModal({ type: 'table', table })} aria-label={`Edit ${table.name}`} title="Edit table"><MoreHorizontal size={18} /></button></div>)}</div></section>
}

function StaffSettings({ data, onModal, onRefresh, onNotify }) {
  const toggle = async (user) => { try { await api.toggleStaff(user.id, !user.isActive); await onRefresh(); onNotify(`${user.name} is now ${user.isActive ? 'inactive' : 'active'}.`) } catch (error) { onNotify(error.message, 'error') } }
  return <section className="settings-section"><div className="settings-section-head"><div><p className="eyebrow">People & access</p><h2>Staff accounts</h2><p className="section-subtitle">Hosts operate the board. Managers own the room.</p></div><button className="button button-primary" onClick={() => onModal({ type: 'staff' })}><Plus size={16} /> Add staff</button></div><div className="inventory-list">{data.users.map((user) => <div className={`inventory-row ${!user.isActive ? 'is-inactive' : ''}`} key={user.id}><div className="avatar avatar-small">{user.name.split(' ').map((part) => part[0]).join('')}</div><div className="inventory-main"><strong>{user.name}</strong><span>{user.identifier}</span></div><span className={`role-pill role-${user.role}`}>{user.role}</span><button className={`text-button ${user.isActive ? 'danger-text' : ''}`} onClick={() => toggle(user)}>{user.isActive ? 'Disable' : 'Enable'}</button></div>)}</div></section>
}

function ModalShell({ title, eyebrow, children, onClose, wide = false }) {
  return <div className="modal-backdrop" role="presentation"><div className={`modal ${wide ? 'modal-wide' : ''}`} role="dialog" aria-modal="true" aria-label={title}><button className="modal-close icon-button" onClick={onClose} aria-label="Close dialog"><X size={18} /></button><p className="eyebrow">{eyebrow}</p><h2>{title}</h2>{children}</div></div>
}

function PartyModal({ entry, entries, onClose, onSave }) {
  const [form, setForm] = useState({ guestName: entry?.guestName || '', phone: entry?.phone || '', partySize: entry?.partySize || 2, seatingPreference: entry?.seatingPreference || 'No preference', notes: entry?.notes || '' })
  const [busy, setBusy] = useState(false)
  const [errors, setErrors] = useState({})
  const duplicate = entries.some((candidate) => candidate.status === 'waiting' && candidate.id !== entry?.id && candidate.phone.replace(/\D/g, '') === form.phone.replace(/\D/g, '') && form.phone.replace(/\D/g, '').length > 5)
  const update = (key, value) => setForm((current) => ({ ...current, [key]: value }))
  const submit = async (event) => {
    event.preventDefault()
    const nextErrors = {}
    if (!form.guestName.trim()) nextErrors.guestName = 'Add the guest name.'
    if (form.phone.replace(/\D/g, '').length < 7) nextErrors.phone = 'Add a valid phone number.'
    if (!Number.isInteger(Number(form.partySize)) || Number(form.partySize) < 1) nextErrors.partySize = 'Use a whole number.'
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length) return
    setBusy(true)
    await onSave(form)
    setBusy(false)
  }
  return <ModalShell title={entry ? 'Edit party' : 'Add a party'} eyebrow={entry ? 'Update the line' : 'New arrival'} onClose={onClose}><form className="modal-form" onSubmit={submit}><div className="form-grid"><Field label="Guest name" value={form.guestName} onChange={(value) => update('guestName', value)} error={errors.guestName} autoFocus /><Field label="Phone number" value={form.phone} onChange={(value) => update('phone', value)} error={errors.phone} type="tel" /><Field label="Party size" value={form.partySize} onChange={(value) => update('partySize', value)} error={errors.partySize} type="number" min="1" /><SelectField label="Seating preference" value={form.seatingPreference} onChange={(value) => update('seatingPreference', value)} options={preferenceOptions} /></div><Field label="Notes for the floor" value={form.notes} onChange={(value) => update('notes', value)} placeholder="High chair, celebration, accessibility…" /><div className="modal-rule" />{duplicate && <div className="duplicate-warning"><BellRing size={17} /><div><strong>Another active party has this number.</strong><span>You can still save this entry, but check the name before calling.</span></div></div>}<div className="modal-actions"><button type="button" className="button button-ghost" onClick={onClose}>Back</button><button className="button button-primary" disabled={busy}>{busy ? 'Saving…' : entry ? 'Save changes' : 'Add to waitlist'} <ArrowUpRight size={16} /></button></div></form></ModalShell>
}

function SeatModal({ entry, tables, entries, areas, onClose, onSeat }) {
  const [selected, setSelected] = useState('')
  const [busy, setBusy] = useState(false)
  const options = tables.filter((table) => table.isActive && table.availability === 'available')
  const submit = async () => { if (!selected) return; setBusy(true); await onSeat(selected); setBusy(false) }
  return <ModalShell title={`Seat ${entry.guestName}`} eyebrow="Choose a table" onClose={onClose} wide><div className="seat-party-summary"><div className="seat-number">{entry.partySize}</div><div><strong>{entry.guestName}</strong><span>{entry.partySize} guests · {entry.seatingPreference} · waiting {formatRelative(entry.createdAt).replace(' ago', '')}</span></div></div><div className="table-choice-grid">{options.map((table) => { const area = areas.find((candidate) => candidate.id === table.areaId)?.name; const fits = table.capacity >= entry.partySize; return <button type="button" key={table.id} disabled={!fits} className={`table-choice ${selected === table.id ? 'is-selected' : ''} ${!fits ? 'is-too-small' : ''}`} onClick={() => setSelected(table.id)}><span className="choice-check">{selected === table.id && <Check size={14} />}</span><Table2 size={22} /><strong>{table.name}</strong><span>{table.capacity} seats</span><small>{area}</small>{!fits && <em>Too small</em>}</button> })}</div>{options.length === 0 && <div className="inline-empty">There are no active tables available right now.</div>}<div className="modal-actions"><button type="button" className="button button-ghost" onClick={onClose}>Back</button><button className="button button-primary" disabled={!selected || busy} onClick={submit}>{busy ? 'Seating…' : 'Confirm table'} <Check size={16} /></button></div></ModalShell>
}

function TableModal({ table, areas, onClose, onSave }) {
  const [form, setForm] = useState({ name: table?.name || '', capacity: table?.capacity || 2, areaId: table?.areaId || areas[0]?.id || '', isActive: table?.isActive ?? true })
  const submit = async (event) => { event.preventDefault(); await onSave(form) }
  return <ModalShell title={table ? `Edit ${table.name}` : 'Add a table'} eyebrow="Room inventory" onClose={onClose}><form className="modal-form" onSubmit={submit}><div className="form-grid"><Field label="Table name" value={form.name} onChange={(value) => setForm({ ...form, name: value })} autoFocus /><Field label="Capacity" type="number" min="1" value={form.capacity} onChange={(value) => setForm({ ...form, capacity: value })} /><SelectField label="Area" value={form.areaId} onChange={(value) => setForm({ ...form, areaId: value })} options={areas.map((area) => ({ label: area.name, value: area.id }))} /></div>{table && <div className="setting-toggle modal-toggle"><div><strong>Available for seating</strong><span>Inactive tables stay in the inventory for reference.</span></div><button type="button" className={`toggle ${form.isActive ? 'is-on' : ''}`} onClick={() => setForm({ ...form, isActive: !form.isActive })} aria-label="Toggle table availability"><span /></button></div>}<div className="modal-actions"><button type="button" className="button button-ghost" onClick={onClose}>Back</button><button className="button button-primary">{table ? 'Save table' : 'Add table'} <ArrowUpRight size={16} /></button></div></form></ModalShell>
}

function StaffModal({ onClose, onSave }) {
  const [form, setForm] = useState({ name: '', identifier: '', role: 'host' })
  return <ModalShell title="Add a staff account" eyebrow="People & access" onClose={onClose}><form className="modal-form" onSubmit={(event) => { event.preventDefault(); onSave(form) }}><Field label="Full name" value={form.name} onChange={(value) => setForm({ ...form, name: value })} autoFocus /><Field label="Work email" type="email" value={form.identifier} onChange={(value) => setForm({ ...form, identifier: value })} /><SelectField label="Role" value={form.role} onChange={(value) => setForm({ ...form, role: value })} options={[{ label: 'Host', value: 'host' }, { label: 'Manager', value: 'manager' }]} /><p className="modal-hint">A temporary password flow will be connected when the backend is added.</p><div className="modal-actions"><button type="button" className="button button-ghost" onClick={onClose}>Back</button><button className="button button-primary">Create account <ArrowUpRight size={16} /></button></div></form></ModalShell>
}

function ConfirmModal({ title, description, confirmLabel, onClose, onConfirm }) {
  const [busy, setBusy] = useState(false)
  const confirm = async () => { setBusy(true); await onConfirm(); setBusy(false) }
  return <ModalShell title={title} eyebrow="Please confirm" onClose={onClose}><p className="confirm-copy">{description}</p><div className="modal-actions"><button className="button button-ghost" onClick={onClose}>Keep party</button><button className="button button-danger" onClick={confirm} disabled={busy}>{busy ? 'Updating…' : confirmLabel} <X size={16} /></button></div></ModalShell>
}

function Field({ label, value, onChange, type = 'text', error, placeholder, ...props }) { return <label className="field"><span>{label}</span><input {...props} type={type} value={value} placeholder={placeholder} onChange={(event) => onChange(event.target.value)} /><>{error && <small className="field-error">{error}</small>}</></label> }
function SelectField({ label, value, onChange, options }) { return <label className="field"><span>{label}</span><div className="select-wrap"><select value={typeof options[0] === 'string' ? value : value} onChange={(event) => onChange(event.target.value)}>{options.map((option) => { const normalized = typeof option === 'string' ? { label: option, value: option } : option; return <option value={normalized.value} key={normalized.value}>{normalized.label}</option> })}</select><ChevronDown size={16} /></div></label> }

export default App
