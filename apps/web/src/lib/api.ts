export const apiBaseUrl =
  import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

export type CurrentUserResponse = {
  clerk_user_id: string
  session_id: string | null
  organization_id: string | null
  organization_role: string | null
}

export async function fetchCurrentUser(
  token: string,
): Promise<CurrentUserResponse> {
  const response = await fetch(`${apiBaseUrl}/auth/me`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })

  if (!response.ok) {
    throw new Error(`Auth request failed with status ${response.status}`)
  }

  return response.json() as Promise<CurrentUserResponse>
}
