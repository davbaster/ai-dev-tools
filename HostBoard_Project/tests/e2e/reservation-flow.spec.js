import { test, expect } from '@playwright/test';

test.describe('HostBoard End-to-End Flow', () => {
  test('Admin logs in, adds reservation, assigns table, and frees table', async ({ page }) => {
    // 1. Log in as one of the admins (Maya Chen - manager)
    await page.goto('/');

    // Check we are on the login screen
    await expect(page.getByText('Staff sign in')).toBeVisible();

    // Fill in admin credentials
    await page.getByLabel('Work email').fill('maya@juneandpine.com');
    await page.getByLabel('Password').fill('demo1234');
    await page.getByRole('button', { name: 'Enter service board' }).click();

    // Verify successful login
    await expect(page.getByText('Maya Chen')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Keep the room moving' })).toBeVisible();

    // 2. Make a reservation / add party to waitlist
    await page.getByRole('button', { name: 'Add party' }).first().click();

    // Verify modal is open
    await expect(page.getByRole('dialog', { name: 'Add a party' })).toBeVisible();

    const uniqueGuestName = `E2E Guest ${Date.now()}`;
    await page.getByLabel('Guest name').fill(uniqueGuestName);
    await page.getByLabel('Phone number').fill('(555) 444-1234');
    await page.getByLabel('Party size').fill('2');
    await page.getByLabel('Seating preference').selectOption('Dining room');
    await page.getByLabel('Notes for the floor').fill('Anniversary celebration');

    await page.getByRole('button', { name: 'Add to waitlist' }).click();

    // Wait for the modal to close and party to appear in active waitlist
    await expect(page.getByRole('dialog')).toBeHidden();
    const partyRow = page.locator('.queue-row', { hasText: uniqueGuestName });
    await expect(partyRow).toBeVisible();

    // 3. Assign a table to the reservation
    await partyRow.getByRole('button', { name: 'Seat' }).click();

    // Verify seat modal opened
    const seatModal = page.getByRole('dialog', { name: `Seat ${uniqueGuestName}` });
    await expect(seatModal).toBeVisible();

    // Pick an available table (e.g. T02, T03, or the first available choice)
    const availableTableButton = seatModal.locator('.table-choice:not([disabled])').first();
    await expect(availableTableButton).toBeVisible();
    const tableNameText = await availableTableButton.locator('strong').innerText();

    await availableTableButton.click();
    await seatModal.getByRole('button', { name: 'Confirm table' }).click();

    // Verify party is seated and modal closed
    await expect(seatModal).toBeHidden();
    await expect(page.getByText(`${uniqueGuestName} is seated.`)).toBeVisible();

    // 4. Free the table
    // The occupied table appears in Table Pulse on the right rail
    const tablePulseItem = page.locator(`.mini-table.is-occupied`, { hasText: tableNameText });
    await expect(tablePulseItem).toBeVisible();
    await tablePulseItem.click();

    // Confirm modal for freeing the table
    const freeModal = page.getByRole('dialog', { name: `Mark ${tableNameText} as free?` });
    await expect(freeModal).toBeVisible();
    await freeModal.getByRole('button', { name: 'Mark table free' }).click();

    // Verify table is released
    await expect(freeModal).toBeHidden();
    await expect(page.getByText(`Table ${tableNameText} is now free.`)).toBeVisible();
  });
});

