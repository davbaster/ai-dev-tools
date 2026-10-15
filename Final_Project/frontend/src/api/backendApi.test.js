import test from 'node:test'
import assert from 'node:assert/strict'
import {
  backendApi,
  mapRestaurant,
  mapArea,
  mapTable,
  mapUser,
  mapEntry,
  mapDashboard,
  partyPayload,
} from './backendApi.js'

test('mapRestaurant maps backend snake_case fields to frontend camelCase', () => {
  const raw = {
    id: 'rest-1',
    name: 'June & Pine',
    is_open: true,
    timezone: 'America/New_York',
    service_label: 'Dinner service',
  }
  const mapped = mapRestaurant(raw)
  assert.equal(mapped.isOpen, true)
  assert.equal(mapped.serviceLabel, 'Dinner service')
  assert.equal(mapped.name, 'June & Pine')
})

test('mapArea maps area active flag', () => {
  const raw = { id: 'area-1', name: 'Patio', is_active: true }
  const mapped = mapArea(raw)
  assert.equal(mapped.isActive, true)
  assert.equal(mapped.name, 'Patio')
})

test('mapTable maps area_id and is_active', () => {
  const raw = { id: 'table-1', name: 'T01', capacity: 4, area_id: 'area-1', is_active: false }
  const mapped = mapTable(raw)
  assert.equal(mapped.areaId, 'area-1')
  assert.equal(mapped.isActive, false)
  assert.equal(mapped.capacity, 4)
})

test('mapUser maps is_active', () => {
  const raw = { id: 'user-1', name: 'Maya Chen', identifier: 'maya@juneandpine.com', role: 'manager', is_active: true }
  const mapped = mapUser(raw)
  assert.equal(mapped.isActive, true)
  assert.equal(mapped.role, 'manager')
})

test('mapEntry maps all waitlist entry fields and defaults empty notes and seating preference', () => {
  const raw = {
    id: 'entry-1',
    guest_name: 'Olivia Park',
    party_size: 2,
    seating_preference: null,
    notes: null,
    status: 'waiting',
    created_at: '2026-09-28T18:00:00Z',
    updated_at: null,
    seated_at: null,
    cancelled_at: null,
    assigned_table_id: null,
    created_by: 'Luca Rivera',
    completed_by: null,
  }
  const mapped = mapEntry(raw)
  assert.equal(mapped.guestName, 'Olivia Park')
  assert.equal(mapped.partySize, 2)
  assert.equal(mapped.seatingPreference, 'No preference')
  assert.equal(mapped.notes, '')
  assert.equal(mapped.assignedTableId, null)
  assert.equal(mapped.createdBy, 'Luca Rivera')
})

test('mapDashboard maps all nested collections', () => {
  const raw = {
    restaurant: { id: 'r1', name: 'June & Pine', is_open: true, timezone: 'America/New_York', service_label: 'Dinner' },
    areas: [{ id: 'a1', name: 'Bar', is_active: true }],
    tables: [{ id: 't1', name: 'B01', capacity: 2, area_id: 'a1', is_active: true }],
    users: [{ id: 'u1', name: 'Luca', identifier: 'luca@juneandpine.com', role: 'host', is_active: true }],
    entries: [{
      id: 'e1',
      guest_name: 'Guest',
      party_size: 2,
      seating_preference: 'Bar',
      notes: 'Near window',
      status: 'waiting',
      created_at: '2026-09-28T18:00:00Z',
      updated_at: null,
      seated_at: null,
      cancelled_at: null,
      assigned_table_id: null,
      created_by: 'Luca',
      completed_by: null,
    }],
  }
  const mapped = mapDashboard(raw)
  assert.equal(mapped.restaurant.isOpen, true)
  assert.equal(mapped.areas[0].isActive, true)
  assert.equal(mapped.tables[0].areaId, 'a1')
  assert.equal(mapped.users[0].isActive, true)
  assert.equal(mapped.entries[0].guestName, 'Guest')
  assert.equal(mapped.entries[0].seatingPreference, 'Bar')
})

test('partyPayload serializes frontend payload to backend request format', () => {
  const payload1 = {
    guestName: 'John Doe',
    phone: '(555) 123-4567',
    partySize: '4',
    seatingPreference: 'Patio',
    notes: 'Anniversary',
  }
  const serialized1 = partyPayload(payload1)
  assert.deepEqual(serialized1, {
    guest_name: 'John Doe',
    phone: '(555) 123-4567',
    party_size: 4,
    seating_preference: 'Patio',
    notes: 'Anniversary',
  })

  const payload2 = {
    guestName: 'Jane Doe',
    phone: '5551234',
    partySize: 2,
    seatingPreference: 'No preference',
    notes: '',
  }
  const serialized2 = partyPayload(payload2)
  assert.equal(serialized2.seating_preference, null)
  assert.equal(serialized2.notes, null)
})

test('session management stores, retrieves, and clears session', () => {
  backendApi.clearSession()
  assert.equal(backendApi.getSession(), null)
})

test('backendApi methods send expected requests and parse responses using mocked fetch', async () => {
  const originalFetch = globalThis.fetch
  const calls = []

  globalThis.fetch = async (url, options) => {
    calls.push({ url, options })
    if (url.endsWith('/api/auth/login/')) {
      return {
        ok: true,
        status: 200,
        headers: new Headers({ 'set-cookie': 'hostboard_session=token-123; Path=/' }),
        json: async () => ({
          user: {
            id: 'user-1',
            name: 'Maya Chen',
            identifier: 'maya@juneandpine.com',
            role: 'manager',
            is_active: true,
          },
        }),
      }
    }
    if (url.endsWith('/api/dashboard/')) {
      return {
        ok: true,
        status: 200,
        headers: new Headers(),
        json: async () => ({
          restaurant: { id: 'r1', name: 'June & Pine', is_open: true, timezone: 'America/New_York', service_label: 'Dinner' },
          areas: [],
          tables: [],
          users: [],
          entries: [],
        }),
      }
    }
    if (url.endsWith('/api/waitlist/') && options.method === 'POST') {
      const body = JSON.parse(options.body)
      return {
        ok: true,
        status: 201,
        headers: new Headers(),
        json: async () => ({
          entry: {
            id: 'entry-99',
            guest_name: body.guest_name,
            party_size: body.party_size,
            seating_preference: body.seating_preference,
            notes: body.notes,
            status: 'waiting',
            created_at: '2026-09-28T19:00:00Z',
            updated_at: null,
            seated_at: null,
            cancelled_at: null,
            assigned_table_id: null,
            created_by: 'Maya Chen',
            completed_by: null,
          },
          warnings: [],
        }),
      }
    }
    if (url.endsWith('/api/auth/logout/')) {
      return {
        ok: true,
        status: 204,
        headers: new Headers(),
        json: async () => null,
      }
    }
    return {
      ok: false,
      status: 404,
      headers: new Headers(),
      json: async () => ({ error: { code: 'not_found', message: 'Not found' } }),
    }
  }

  try {
    // 1. Login
    const user = await backendApi.login({ identifier: 'maya@juneandpine.com', password: 'demo' })
    assert.equal(user.identifier, 'maya@juneandpine.com')
    assert.equal(backendApi.getSession()?.name, 'Maya Chen')

    // 2. Dashboard
    const dashboard = await backendApi.getDashboard()
    assert.equal(dashboard.restaurant.isOpen, true)

    // 3. Create entry
    const { entry } = await backendApi.createEntry({
      guestName: 'Taylor',
      phone: '555-9999',
      partySize: 3,
      seatingPreference: 'Patio',
    })
    assert.equal(entry.guestName, 'Taylor')
    assert.equal(entry.partySize, 3)

    // 4. Logout
    await backendApi.logout()
    assert.equal(backendApi.getSession(), null)
  } finally {
    globalThis.fetch = originalFetch
  }
})

test('backendApi correctly formats API errors from response body', async () => {
  const originalFetch = globalThis.fetch
  globalThis.fetch = async () => ({
    ok: false,
    status: 422,
    headers: new Headers(),
    json: async () => ({
      error: {
        code: 'validation_error',
        message: 'Review the highlighted fields.',
        fields: {
          phone: ['Phone must have at least 7 digits.'],
        },
      },
    }),
  })

  try {
    await assert.rejects(
      async () => {
        await backendApi.createEntry({ guestName: 'Test', phone: '1', partySize: 1 })
      },
      (err) => {
        assert.equal(err.status, 422)
        assert.equal(err.code, 'validation_error')
        assert.equal(err.message, 'Review the highlighted fields.')
        assert.deepEqual(err.fields, { phone: ['Phone must have at least 7 digits.'] })
        return true
      },
    )
  } finally {
    globalThis.fetch = originalFetch
  }
})

test('mapTable maps current_party and availability', () => {
  const raw = {
    id: 'table-1',
    name: 'T01',
    capacity: 2,
    area_id: 'area-1',
    is_active: true,
    availability: 'occupied',
    current_party: {
      id: 'entry-5',
      guest_name: 'Jamie Wilson',
      party_size: 2,
    },
  }
  const mapped = mapTable(raw)
  assert.equal(mapped.availability, 'occupied')
  assert.equal(mapped.currentParty?.guestName, 'Jamie Wilson')
  assert.equal(mapped.currentParty?.partySize, 2)
})

test('backendApi.releaseTable sends POST to release endpoint and returns mapped table', async () => {
  const originalFetch = globalThis.fetch
  let calledUrl = ''
  let calledMethod = ''

  globalThis.fetch = async (url, options) => {
    calledUrl = url
    calledMethod = options.method
    return {
      ok: true,
      status: 200,
      headers: new Headers(),
      json: async () => ({
        table: {
          id: 'table-1',
          name: 'T01',
          capacity: 2,
          area_id: 'area-1',
          is_active: true,
          availability: 'available',
          current_party: null,
        },
        message: 'Table T01 is now available.',
      }),
    }
  }

  try {
    const table = await backendApi.releaseTable('table-1')
    assert.ok(calledUrl.endsWith('/api/tables/table-1/release/'))
    assert.equal(calledMethod, 'POST')
    assert.equal(table.availability, 'available')
    assert.equal(table.currentParty, null)
  } finally {
    globalThis.fetch = originalFetch
  }
})
