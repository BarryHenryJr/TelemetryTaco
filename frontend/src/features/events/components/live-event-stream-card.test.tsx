import { afterEach, describe, expect, it, vi } from 'vitest'
import { screen } from '@testing-library/react'
import { LiveEventStreamCard } from '@/features/events/components/live-event-stream-card'
import { renderWithProviders } from '@/test/test-utils'

function mockJsonResponse(body: unknown, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  )
}

describe('LiveEventStreamCard', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders the empty state when no events exist', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => mockJsonResponse([]))

    renderWithProviders(<LiveEventStreamCard limit={100} />)

    expect(await screen.findByText('No events yet')).toBeInTheDocument()
  })

  it('renders fetched events', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
      mockJsonResponse([
        {
          id: 1,
          uuid: '5bb31741-4f62-4fab-8fc4-45a8ee3a5487',
          distinct_id: 'user-123',
          event_name: 'page_view',
          properties: { path: '/' },
          timestamp: '2026-03-13T08:00:00Z',
          created_at: '2026-03-13T08:00:00Z',
        },
      ]),
    )

    renderWithProviders(<LiveEventStreamCard limit={100} />)

    expect(await screen.findByText('page_view')).toBeInTheDocument()
    expect(screen.getByText('user-123')).toBeInTheDocument()
  })
})
