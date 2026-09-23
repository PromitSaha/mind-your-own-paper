export const apiBaseUrl =
  import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

export type CurrentUserResponse = {
  id: string
  clerk_user_id: string
  email: string
  first_name: string | null
  last_name: string | null
  image_url: string | null
  is_deleted: boolean
  created_at: string
  updated_at: string
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
