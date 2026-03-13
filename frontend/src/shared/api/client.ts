const API_BASE_URL = import.meta.env.VITE_API_URL || ''

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export function buildApiUrl(path: string, searchParams?: URLSearchParams) {
  const url = new URL(path, API_BASE_URL || window.location.origin)
  if (searchParams) {
    url.search = searchParams.toString()
  }

  if (!API_BASE_URL) {
    return `${url.pathname}${url.search}`
  }

  return url.toString()
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(buildApiUrl(path), {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  })

  if (!response.ok) {
    throw new ApiError(`Request failed with status ${response.status}`, response.status)
  }

  return (await response.json()) as T
}
