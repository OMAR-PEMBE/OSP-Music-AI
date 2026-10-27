# OSP Music AI — PRD (MVP)

**Version:** 1.0 (MVP) · **Owner:** Omar Pembe, OSP Technologies · **Market:** Tanzania
**One line:** Type an idea, get two AI songs in Swahili or English, pay with mobile money.

> Rule for the coding agent: build ONLY what is in this file. Anything in "Not in MVP" must not be built, stubbed in the UI, or "prepared for" beyond what TECH.md says.

---

## 1. Goal of the MVP

Launch a working, paid web app fast, so real users pay for real songs. Success after the first 60 days:

- 100+ registered users
- 30+ users who topped up at least once
- Generation success rate ≥ 90%
- Zero wallet errors (no double charges, no free money)

## 2. Users

- **Everyday creators:** want a full song from an idea (birthdays, love songs, church, fun).
- **Upcoming artists / content creators:** paste their own lyrics, download the song and use it anywhere (TikTok, YouTube, etc.).

## 3. Platform

- **Web app only**, mobile-first design. Installable to the phone home screen (PWA).
- Interface language: **English only**. Song language remains selectable separately.
- Appearance: **light / dark** toggle. Default: follow the phone/system setting.

## 4. Features

### 4.1 Account
- Sign up with first name, last name, email + password; verify email by link. (First/last name are required by Snippe for payments.)
- Login, logout, forgot password (reset link by email).
- Profile: display name (required, unique), email, optional profile picture.
- **Delete account** from Settings (see 4.7).

**Done when:** a user can register, verify, log in, reset password, and nobody can see another user's data by changing an ID in the URL.

### 4.2 Create (one screen)
Fields:
1. **Song idea** (required): free text, e.g. "Wimbo wa mapenzi kwa mpenzi wangu Asha".
2. **Genre** (required): Bongo Flava, R&B, Afrobeats, Amapiano, Gospel, Hip-Hop, Other (text).
3. **Song language**: Swahili, English, Mixed.
4. **Voice**: Male, Female, Auto.
5. **Lyrics** (optional), with two ways:
   - User pastes their own lyrics, or
   - User taps **"Niandikie mashairi / Write lyrics for me"** → system writes lyrics → user can edit them. This is **free** but limited to **10 per user per day**.
   - If the lyrics box is empty when generating, the system writes lyrics automatically.
6. Shows **price** (e.g. TZS 1,000) and **current balance**, then the **Generate** button.

Rules:
- Every request returns **2 versions** of the same song.
- Song length is automatic.
- If balance < price → button becomes **"Top up"** and opens Wallet.
- Double-tapping Generate must never create two requests or two charges.

**Done when:** a valid request creates one job, deducts the price once, and the user can leave the page and come back later to find it.

### 4.3 Generation status
- Statuses shown to users: **In queue → Creating → Ready / Partly ready / Failed**.
- The user can **start listening while the song is still being created** (streaming), when available.
- When finished: a red dot on **My Music** plus an in-app toast "Wimbo wako uko tayari / Your song is ready". **No emails.**
- Refund rules (automatic):

| Outcome | Charge |
|---|---|
| Both versions succeed | Full price (TZS 1,000) |
| One succeeds, one fails | Half price (refund TZS 500) |
| Both fail | Free (refund TZS 1,000) |

**Done when:** every refund appears in Wallet history once, and is never repeated.

### 4.4 My Music
- List of the user's songs, newest first: title, date, genre, status, 2 versions.
- Each version: play/pause, progress bar, **Download MP3**.
- Rename song, delete song (with confirmation).
- View the lyrics used.
- Songs are **private**: only the owner can play or download them.

**Done when:** songs remain playable and downloadable after the provider's temporary links expire (we keep our own copy).

### 4.5 Wallet (TZS balance)
- Shows **balance in TZS** (no credits).
- **Top up:** quick buttons TZS 1,000 / 3,000 / 5,000 / 10,000 or a custom amount (min TZS 1,000, max TZS 500,000). These are shortcuts, not packages.
- Pay with Snippe mobile money (M-Pesa, Mixx by Yas, Airtel Money, Halotel). User enters phone number → approves the push on their phone.
- Payment statuses: **Pending, Successful, Failed**.
- Balance increases **only after the backend confirms the payment** with Snippe.
- History: every top-up, song charge, and refund with date, amount, and balance after.
- Balance never expires. Top-ups are **non-refundable** (shown before paying).

**Done when:** a repeated or fake payment notification can never add money twice or add money without a real payment.

### 4.6 Support
- Floating **WhatsApp button** (direct link to the OSP support number; no API).
- Contact form (name, email, message) that emails the owner.
- Short FAQ page (how it works, payment, refunds, ownership, deleting account).

### 4.7 Legal and account deletion
- Pages: **Terms**, **Privacy Policy**, **Refund rules**.
- Ownership statement: users may download and use their songs commercially, under the AI provider's licence; OSP does not distribute music or pay royalties.
- **Delete account:** user confirms with password → account, profile, songs, and lyrics are deleted. Payment records are kept **anonymized** for accounting. Remaining balance is lost (warning shown first).

### 4.8 Landing page (public)
- Hero: what it does + **"Anza Sasa / Get Started"**.
- How it works in 3 steps.
- A few sample songs made by OSP (clearly ours, not fake user songs).
- Price per song, payment logos, FAQ, footer links.

### 4.9 Owner admin (Django admin)
The owner can:
- See and search users, songs/jobs, payments, wallet transactions.
- Change the **song price**, the **active engine (Mureka/Suno)**, the **fallback engine** and the **AI model** in Settings.
- Give a manual balance adjustment (requires a reason; recorded).
- Retry checking a stuck job's status (never resubmits a paid generation automatically).
- See a daily summary: new users, top-ups (TZS), songs generated, failures, refunds, estimated Mureka cost, estimated profit.
- Turn generation **on/off** (maintenance switch) and get warned when the Mureka balance is low.

## 5. Business rules (summary)

- Price per request: **TZS 1,000** (2 versions), editable by admin. The price shown is the price charged.
- Refunds: see table in 4.3. No refunds for top-ups.
- No free song generations. Lyrics writing is free (10/day).
- Balance is held in TZS, never expires, and is lost only on account deletion.
- Engines: **Mureka + Suno** (same engines as Zeno). Mureka is the default engine; Suno is the second engine (switchable/fallback by admin) once its official API key and price are set — see SUNO.md. The user does not choose the engine in MVP.

## 6. Not in MVP (do NOT build)

Artist Studio / persistent artists, subscriptions, voice cloning, Android/iOS store apps, public feed / likes / follows / comments, regenerate single version, song extension/stems/editing, user choosing the engine, USD display, staff roles, expense tracking, custom admin dashboard, email notifications, phone OTP, Google login, referral system.

## 7. Phase 2 preview (for context only)

1. Artist Studio + subscriptions
2. Let users choose engine (Sauti A / Sauti B)
3. Android app (Google Play Billing), then iOS
4. Public community
