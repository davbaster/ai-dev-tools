const resolveBaseUrl = () => {
  if (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_BASE_URL !== undefined) {
    return import.meta.env.VITE_API_BASE_URL
  }
  if (typeof process !== 'undefined' && process.env?.VITE_API_BASE_URL !== undefined) {
    return process.env.VITE_API_BASE_URL
  }
  return 'http://localhost:8000'
}

const API_BASE_URL = resolveBaseUrl()
const SESSION_KEY = 'hostboard-session'

const memoryStorage = {
  _data: {},
  getItem(key) { return this._data[key] || null },
  setItem(key, value) { this._data[key] = String(value) },
  removeItem(key) { delete this._data[key] },
  clear() { this._data = {} },
}

const getStorage = () => {
  if (typeof window !== 'undefined' && window.sessionStorage) {
    return window.sessionStorage
  }
  return memoryStorage
}

let nodeCookie = ''

const request = async (path, options = {}) => {
  const headers = {
    ...(options.body ? { 'Content-Type': 'application/json' } : {}),
    ...(typeof window === 'undefined' && nodeCookie ? { Cookie: nodeCookie } : {}),
    ...options.headers,
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    credentials: 'include',
    ...options,
    headers,
  })

  if (typeof window === 'undefined') {
    const rawSetCookie = response.headers.get('set-cookie')
    if (rawSetCookie) {
      nodeCookie = rawSetCookie.split(';')[0]
    }
  }

  if (response.status === 204) return null

  const body = await response.json().catch(() => null)
  if (!response.ok) {
    const error = new Error(body?.error?.message || 'The server could not complete that request.')
    error.status = response.status
    error.code = body?.error?.code
    error.fields = body?.error?.fields
    throw error
  }
  return body
}

const mapRestaurant = (restaurant) => ({
  ...restaurant,
  isOpen: restaurant.is_open,
  serviceLabel: restaurant.service_label,
})

const mapArea = (area) => ({
  ...area,
  isActive: area.is_active,
})

const mapTable = (table) => ({
  ...table,
  areaId: table.area_id,
  isActive: table.is_active,
  currentParty: table.current_party ? {
    id: table.current_party.id,
    guestName: table.current_party.guest_name,
    partySize: table.current_party.party_size,
  } : null,
})

const mapUser = (user) => ({
  ...user,
  isActive: user.is_active,
})

const mapEntry = (entry) => ({
  ...entry,
  guestName: entry.guest_name,
  partySize: entry.party_size,
  seatingPreference: entry.seating_preference || 'No preference',
  createdAt: entry.created_at,
  updatedAt: entry.updated_at,
  seatedAt: entry.seated_at,
  cancelledAt: entry.cancelled_at,
  assignedTableId: entry.assigned_table_id,
  isTableOccupied: Boolean(entry.is_table_occupied),
  createdBy: entry.created_by,
  completedBy: entry.completed_by,
  notes: entry.notes || '',
})

const mapDashboard = (dashboard) => ({
  restaurant: mapRestaurant(dashboard.restaurant),
  areas: dashboard.areas.map(mapArea),
  tables: dashboard.tables.map(mapTable),
  users: dashboard.users.map(mapUser),
  entries: dashboard.entries.map(mapEntry),
})

const partyPayload = (payload) => ({
  guest_name: payload.guestName,
  phone: payload.phone,
  party_size: Number(payload.partySize),
  seating_preference: payload.seatingPreference === 'No preference' ? null : payload.seatingPreference,
  notes: payload.notes || null,
})

const storeSession = (user) => {
  const session = mapUser(user)
  getStorage().setItem(SESSION_KEY, JSON.stringify(session))
  return session
}

export const backendApi = {
  getSession() {
    try {
      const session = getStorage().getItem(SESSION_KEY)
      return session ? JSON.parse(session) : null
    } catch {
      return null
    }
  },

  clearSession() {
    getStorage().removeItem(SESSION_KEY)
  },

  async login({ identifier, password }) {
    const body = await request('/api/auth/login/', {
      method: 'POST',
      body: JSON.stringify({ identifier, password }),
    })
    return storeSession(body.user)
  },

  async logout() {
    try {
      await request('/api/auth/logout/', { method: 'POST' })
    } finally {
      this.clearSession()
    }
  },

  async getDashboard() {
    return mapDashboard(await request('/api/dashboard/'))
  },

  async createEntry(payload) {
    const body = await request('/api/waitlist/', {
      method: 'POST',
      body: JSON.stringify(partyPayload(payload)),
    })
    return { entry: mapEntry(body.entry), warnings: body.warnings || [] }
  },

  async updateEntry(id, payload) {
    const body = await request(`/api/waitlist/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify(partyPayload(payload)),
    })
    return { entry: mapEntry(body.entry), warnings: body.warnings || [] }
  },

  async cancelEntry(id) {
    const body = await request(`/api/waitlist/${id}/cancel/`, { method: 'POST' })
    return mapEntry(body.entry)
  },

  async seatEntry(id, tableId) {
    const body = await request(`/api/waitlist/${id}/seat/`, {
      method: 'POST',
      body: JSON.stringify({ table_id: tableId }),
    })
    return mapEntry(body.entry)
  },

  async updateRestaurant(payload) {
    const body = await request('/api/settings/restaurant/', {
      method: 'PATCH',
      body: JSON.stringify({
        name: payload.name,
        is_open: payload.isOpen,
      }),
    })
    return mapRestaurant(body.restaurant)
  },

  async createTable(payload) {
    const body = await request('/api/tables/', {
      method: 'POST',
      body: JSON.stringify({
        name: payload.name,
        capacity: Number(payload.capacity),
        area_id: payload.areaId,
      }),
    })
    return mapTable(body.table)
  },

  async updateTable(id, payload) {
    const body = await request(`/api/tables/${id}/`, {
      method: 'PATCH',
      body: JSON.stringify({
        name: payload.name,
        capacity: Number(payload.capacity),
        area_id: payload.areaId,
        is_active: payload.isActive,
      }),
    })
    return mapTable(body.table)
  },

  async createStaff(payload) {
    const body = await request('/api/staff/', {
      method: 'POST',
      body: JSON.stringify({
        name: payload.name,
        identifier: payload.identifier,
        role: payload.role,
      }),
    })
    return mapUser(body.user)
  },

  async toggleStaff(id, isActive) {
    const body = await request(`/api/staff/${id}/status/`, {
      method: 'POST',
      body: JSON.stringify({ is_active: isActive }),
    })
    return mapUser(body.user)
  },

  async releaseTable(id) {
    const body = await request(`/api/tables/${id}/release/`, {
      method: 'POST',
    })
    return mapTable(body.table)
  },
}

export const api = backendApi
export {
  mapRestaurant,
  mapArea,
  mapTable,
  mapUser,
  mapEntry,
  mapDashboard,
  partyPayload,
}
export default backendApi
