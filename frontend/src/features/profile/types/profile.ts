/**
 * Request body for PUT /profile (ProfileUpdateRequest, app/modules/profile/
 * schemas.py) - snake_case to match the wire format. Partial update: only
 * supplied fields change. Deliberately no `email`/`role_id`/`status`/
 * `is_superuser`/`id`/`tenant_id` field - the backend schema doesn't accept
 * them either, so there is nothing here to accidentally send.
 *
 * The response to PUT /profile and POST/DELETE /profile/avatar is the same
 * shape GET /auth/me already returns (UserProfileResponse) - reused as-is
 * via `@/features/auth/types/auth`'s `User`/session refresh rather than a
 * second parallel type, matching Sprint 16 Session 1's decision not to
 * duplicate the profile read shape.
 */
export interface ProfileUpdateRequest {
  full_name?: string;
  username?: string;
  phone?: string;
}

/**
 * Request body for POST /profile/change-password, forwarded as-is to the
 * existing POST /auth/change-password (app/modules/auth/schemas.py's
 * ChangePasswordRequest) - password logic stays owned by Auth, Profile is
 * only this BFF route's frontend-facing name for it (Sprint 16 Session 3).
 */
export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}
