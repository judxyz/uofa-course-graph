const DEFAULT_API_BASE_URL = 'http://localhost:8000'

export function getApiBaseUrl() {
  return import.meta.env.VITE_API_BASE_URL?.trim() || DEFAULT_API_BASE_URL
}

export async function fetchJson<T>(input: URL | string, init?: RequestInit): Promise<T> {
  let response: Response

  try {
    response = await fetch(input, init)
  } catch {
    throw new Error(`Unable to connect to services.`)
  }

  if (!response.ok) {
    const fallbackMessage = `Request failed with status ${response.status}`
    const responseText = await response.text()

    try {
      const errorBody = JSON.parse(responseText) as { detail?: string; message?: string }
      throw new Error(errorBody.detail || errorBody.message || fallbackMessage)
    } catch {
      throw new Error(responseText || fallbackMessage)
    }
  }

  return (await response.json()) as T
}
