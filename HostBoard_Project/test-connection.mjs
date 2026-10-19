import { spawn } from 'node:child_process'
import assert from 'node:assert/strict'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const backendDir = path.resolve(__dirname, 'backend')
const TEST_PORT = 8889

process.env.VITE_API_BASE_URL = `http://127.0.0.1:${TEST_PORT}`

console.log('--- HostBoard Frontend-Backend Live Connection Test ---')
console.log(`Starting backend server on port ${TEST_PORT}...`)

const server = spawn('uv', ['run', 'uvicorn', 'app.main:app', '--port', String(TEST_PORT)], {
  cwd: backendDir,
  shell: true,
  stdio: 'pipe',
})

server.stderr.on('data', (d) => {
  // Uncomment to debug server:
  // process.stderr.write(d)
})

const waitForServer = async (retries = 30) => {
  for (let i = 0; i < retries; i++) {
    try {
      const res = await fetch(`http://127.0.0.1:${TEST_PORT}/docs`)
      if (res.ok) return true
    } catch {
      // wait and retry
    }
    await new Promise((r) => setTimeout(r, 500))
  }
  throw new Error('Backend failed to start within timeout')
}

try {
  await waitForServer()
  console.log('✓ Backend server is up and listening.')

  const { backendApi } = await import('./frontend/src/api/backendApi.js')

  console.log('\n[1] Testing Host Authentication...')
  const hostUser = await backendApi.login({
    identifier: 'luca@juneandpine.com',
    password: 'demo1234',
  })
  assert.equal(hostUser.identifier, 'luca@juneandpine.com')
  assert.equal(hostUser.role, 'host')
  assert.equal(backendApi.getSession()?.identifier, 'luca@juneandpine.com')
  console.log('✓ Host authenticated successfully, session stored.')

  console.log('\n[2] Testing Dashboard Fetch...')
  const dashboard = await backendApi.getDashboard()
  assert.equal(dashboard.restaurant.name, 'June & Pine')
  assert.equal(dashboard.restaurant.isOpen, true)
  assert.ok(dashboard.tables.length > 0)
  assert.ok(dashboard.areas.length > 0)
  assert.ok(dashboard.entries.length > 0)
  console.log(`✓ Dashboard loaded: ${dashboard.tables.length} tables, ${dashboard.entries.length} waitlist entries.`)

  console.log('\n[3] Testing Adding Party to Waitlist (createEntry)...')
  const { entry: newEntry, warnings } = await backendApi.createEntry({
    guestName: 'Live Test Party',
    phone: '(555) 777-8888',
    partySize: 2,
    seatingPreference: 'Patio',
    notes: 'Window booth',
  })
  assert.equal(newEntry.guestName, 'Live Test Party')
  assert.equal(newEntry.partySize, 2)
  assert.equal(newEntry.status, 'waiting')
  console.log(`✓ Party added: "${newEntry.guestName}" with ID ${newEntry.id}.`)

  console.log('\n[4] Testing Editing Party Details (updateEntry)...')
  const { entry: updatedEntry } = await backendApi.updateEntry(newEntry.id, {
    guestName: 'Live Test Party Updated',
    phone: '(555) 777-8888',
    partySize: 3,
    seatingPreference: 'Patio',
    notes: 'Needs booth',
  })
  assert.equal(updatedEntry.guestName, 'Live Test Party Updated')
  assert.equal(updatedEntry.partySize, 3)
  console.log('✓ Party updated successfully.')

  console.log('\n[5] Testing Seating Party at Table (seatEntry)...')
  const seatedEntry = await backendApi.seatEntry(newEntry.id, 'table-4')
  assert.equal(seatedEntry.status, 'seated')
  assert.equal(seatedEntry.assignedTableId, 'table-4')
  console.log(`✓ Party seated at table-4.`)

  const refreshedDash = await backendApi.getDashboard()
  const table4 = refreshedDash.tables.find((t) => t.id === 'table-4')
  assert.equal(table4.availability, 'occupied')
  console.log('✓ Dashboard verified table-4 availability is now "occupied".')

  console.log('\n[6] Testing Table Release (releaseTable)...')
  const freedTable = await backendApi.releaseTable('table-4')
  assert.equal(freedTable.availability, 'available')
  assert.equal(freedTable.currentParty, null)
  console.log('✓ Table-4 marked as free and available.')

  const dashAfterRelease = await backendApi.getDashboard()
  const table4Freed = dashAfterRelease.tables.find((t) => t.id === 'table-4')
  assert.equal(table4Freed.availability, 'available')
  const originalSeated = dashAfterRelease.entries.find((e) => e.id === newEntry.id)
  assert.equal(originalSeated.status, 'seated')
  console.log('✓ Dashboard verified table-4 is available and party remains seated in history.')

  console.log('\n[7] Testing Host Logout...')
  await backendApi.logout()
  assert.equal(backendApi.getSession(), null)
  console.log('✓ Host logged out, session cleared.')

  console.log('\n[8] Testing Manager Flow...')
  const managerUser = await backendApi.login({
    identifier: 'maya@juneandpine.com',
    password: 'demo1234',
  })
  assert.equal(managerUser.role, 'manager')
  console.log('✓ Manager logged in.')

  console.log('\n[9] Testing Restaurant Settings Update...')
  const updatedRest = await backendApi.updateRestaurant({
    name: 'June & Pine Bistro',
    isOpen: true,
  })
  assert.equal(updatedRest.name, 'June & Pine Bistro')
  console.log('✓ Restaurant settings updated.')

  console.log('\n[10] Testing Table Creation & Update...')
  const newTable = await backendApi.createTable({
    name: 'P99',
    capacity: 4,
    areaId: 'area-2',
  })
  assert.equal(newTable.name, 'P99')
  assert.equal(newTable.capacity, 4)

  const updatedTable = await backendApi.updateTable(newTable.id, {
    name: 'P99',
    capacity: 6,
    areaId: 'area-2',
    isActive: true,
  })
  assert.equal(updatedTable.capacity, 6)
  console.log('✓ Table created and updated.')

  console.log('\n[11] Testing Staff Account Creation & Toggle...')
  const newStaff = await backendApi.createStaff({
    name: 'Morgan Test',
    identifier: 'morgan.test@juneandpine.com',
    role: 'host',
  })
  assert.equal(newStaff.identifier, 'morgan.test@juneandpine.com')

  const disabledStaff = await backendApi.toggleStaff(newStaff.id, false)
  assert.equal(disabledStaff.isActive, false)
  console.log('✓ Staff created and status toggled.')

  await backendApi.logout()
  console.log('\n========================================')
  console.log('🎉 ALL 11 LIVE INTEGRATION TESTS PASSED!')
  console.log('Frontend backendApi and FastAPI backend are fully connected.')
  console.log('========================================')
} finally {
  console.log('Stopping test backend server...')
  try {
    spawn('taskkill', ['/pid', String(server.pid), '/f', '/t'], { stdio: 'ignore' })
  } catch {}
  server.kill()
  setTimeout(() => process.exit(0), 500)
}
