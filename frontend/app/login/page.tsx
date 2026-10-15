"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const router = useRouter();
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function sendOtp(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const response = await fetch("/api/auth/otp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone: phone.trim() }),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || "OTP could not be sent.");
      setSent(true);
      setNotice("If phone sign-in is enabled for this project, a verification code has been sent.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "OTP delivery is unavailable.");
    } finally {
      setBusy(false);
    }
  }

  async function verifyOtp(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const response = await fetch("/api/auth/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone: phone.trim(), token: code.trim() }),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || "Verification failed.");
      router.replace("/dashboard");
      router.refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Phone verification failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="command-shell">
      <div className="command-wrap">
        <header className="command-header">
          <div>
            <div className="eyebrow"><span className="eyebrow-line" /> SAATHI</div>
            <h1>Sign in with <em>your phone.</em></h1>
            <p>Use a verified phone number to connect this session to your household. Saathi never treats a typed household ID as proof of ownership.</p>
          </div>
          <Link href="/dashboard" className="site-nav-cta">Back to dashboard</Link>
        </header>

        <section className="consent-card" aria-labelledby="phone-login-title">
          <div className="context-title">
            <div><span className="panel-kicker">VERIFIED IDENTITY</span><h2 id="phone-login-title">Phone verification</h2></div>
          </div>
          <p className="consent-intro">Enter your phone in international format, for example +919876543210. SMS sign-in must be enabled in the Supabase Auth settings before this can work.</p>

          {!sent ? (
            <form onSubmit={sendOtp} className="auth-form">
              <label htmlFor="phone-number">Phone number</label>
              <input
                id="phone-number"
                type="tel"
                inputMode="tel"
                autoComplete="tel"
                placeholder="+919876543210"
                pattern="\+[1-9][0-9]{7,14}"
                value={phone}
                onChange={(event) => setPhone(event.target.value)}
                required
                maxLength={16}
              />
              <button type="submit" className="run-button" disabled={busy || !phone.trim()}>{busy ? "Sending code…" : "Send verification code"}</button>
            </form>
          ) : (
            <form onSubmit={verifyOtp} className="auth-form">
              <label htmlFor="phone-code">Six-digit verification code</label>
              <input
                id="phone-code"
                type="text"
                inputMode="numeric"
                autoComplete="one-time-code"
                pattern="[0-9]{6}"
                maxLength={6}
                value={code}
                onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 6))}
                required
              />
              <button type="submit" className="run-button" disabled={busy || code.length !== 6}>{busy ? "Verifying…" : "Verify and continue"}</button>
              <button type="button" className="voice-button" onClick={() => { setSent(false); setCode(""); setNotice(null); setError(null); }} disabled={busy}>Change phone number</button>
            </form>
          )}

          {notice && <p role="status" aria-live="polite">{notice}</p>}
          {error && <p className="voice-error" role="alert" aria-live="assertive">{error}</p>}
          <p className="consent-intro">If OTP delivery is unavailable, the project's phone provider or Supabase Auth configuration must be completed by an administrator. No household data is exposed until the server verifies the session.</p>
        </section>
      </div>
    </main>
  );
}
