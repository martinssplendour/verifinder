export type SubscriptionTier = "free" | "plus" | "professional";

export interface FeatureAllowance {
  allowed: boolean;
  reset_at: string | null;
  word_limit: number | null;
}

export interface AccountStatus {
  authenticated: boolean;
  email: string | null;
  entitlements: {
    tier: SubscriptionTier;
    ask: FeatureAllowance;
    planner: FeatureAllowance;
    report_download: FeatureAllowance;
    watchlists: FeatureAllowance;
  };
  billing_configured: boolean;
  coin_billing_configured: boolean;
  coin_balance: number;
  has_billing_account: boolean;
}
