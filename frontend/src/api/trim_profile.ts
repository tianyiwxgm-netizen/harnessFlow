import { apiClient } from '@/api/client';
import { isTrimProfile, type TrimProfile } from '@/domain/trim_profile';

export interface ProfilePatchResponse {
  profile: TrimProfile;
  synced: boolean;
  note?: string;
}

export async function patchConfigProfile(profile: TrimProfile): Promise<ProfilePatchResponse> {
  if (!isTrimProfile(profile)) {
    throw new Error(`patchConfigProfile: "${profile}" is not a valid TrimProfile`);
  }
  const response = await apiClient.patch<ProfilePatchResponse>('/config/profile', { profile });
  return response.data;
}
