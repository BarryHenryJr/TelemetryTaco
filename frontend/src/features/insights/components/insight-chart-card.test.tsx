import { afterEach, describe, expect, it, vi } from 'vitest'
import { screen } from '@testing-library/react'
import { InsightChartCard } from '@/features/insights/components/insight-chart-card'
import { renderWithProviders } from '@/test/test-utils'

function mockJsonResponse(body: unknown, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  )
}

describe('InsightChartCard', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders an empty-state message', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => mockJsonResponse([]))

    renderWithProviders(<InsightChartCard lookbackMinutes={60} />)

    expect(await screen.findByText('No data available')).toBeInTheDocument()
  })

  it('renders an error message on request failure', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() =>
      Promise.resolve(new Response('oops', { status: 500 })),
    )

    renderWithProviders(<InsightChartCard lookbackMinutes={60} />)

    expect(await screen.findByText('Insight query failed')).toBeInTheDocument()
  })
})
