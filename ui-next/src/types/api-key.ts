export interface ApiKey {
  id: number;
  name: string;
  is_active: boolean;
  expires_at?: string;
  last_used_at?: string;
  created_at: string;
  permissions: string[];
}

export interface ApiKeyCreate {
  name: string;
  expires_days?: number;
  permissions?: string[];
}

export interface ApiKeyCreateResponse extends ApiKey {
  api_key: string; // Only returned on creation
}
