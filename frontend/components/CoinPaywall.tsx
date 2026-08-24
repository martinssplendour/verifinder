"use client";

import { Coins, LoaderCircle, Sparkles } from "lucide-react";

export type CoinPack = "coins_25" | "coins_75";

/**
 * Pack copy lives here rather than in each surface so a price change is one edit.
 * The amounts mirror the Stripe prices behind `stripe_coin_pack_*_price_id`;
 * Stripe remains the authority at checkout.
 */
const PACKS: { pack: CoinPack; label: string; unit: string; price: string; best: boolean }[] = [
  { pack: "coins_25", label: "25 coins", unit: "16p per Ask message", price: "£3.99", best: false },
  { pack: "coins_75", label: "75 coins", unit: "12p per Ask message", price: "£8.99", best: true },
];

export function CoinPaywall({
  title = "Keep this conversation going.",
  message,
  isSignedIn,
  coinBillingConfigured,
  purchasing,
  onBuy,
  onSignIn,
  onViewPlans,
}: {
  title?: string;
  message?: string | null;
  isSignedIn: boolean;
  coinBillingConfigured: boolean;
  purchasing: CoinPack | null;
  onBuy: (pack: CoinPack) => void;
  onSignIn: () => void;
  onViewPlans: () => void;
}) {
  return (
    <section className="coin-paywall" aria-label="Buy Ask coins">
      <div className="coin-paywall-copy">
        <span><Coins size={22} /></span>
        <div><p className="kicker">Pay as you go</p><h2>{title}</h2>{message && <p>{message}</p>}</div>
      </div>
      {!isSignedIn ? (
        <button className="button" type="button" onClick={onSignIn}>Sign in to buy coins</button>
      ) : (
        <div className="coin-pack-grid">
          {PACKS.map(({ pack, label, unit, price, best }) => (
            <button
              key={pack}
              className={best ? "is-best" : undefined}
              type="button"
              disabled={Boolean(purchasing) || !coinBillingConfigured}
              onClick={() => onBuy(pack)}
            >
              <span><strong>{label}</strong><small>{unit}</small></span>
              <em>{price}</em>
              {purchasing === pack && <LoaderCircle className="spin" size={16} />}
            </button>
          ))}
        </div>
      )}
      <div className="coin-paywall-footer">
        <small>One-time payment. 1 coin = 1 Ask message. Coins do not expire.</small>
        <button type="button" onClick={onViewPlans}><Sparkles size={13} />Or get unlimited Ask with Plus</button>
      </div>
    </section>
  );
}
