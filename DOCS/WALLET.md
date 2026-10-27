# WALLET.md — Money rules (read before touching any money code)

This is the highest-risk part of OSP Music AI. A bug here either loses Omar money or steals from users. Business rules come from [PRD.md](PRD.md) §4.3 and §4.5. Tables are in [DATABASE.md](DATABASE.md) §2.

## 1. Principles

1. Money = **integer TZS**. Never floats, never Decimal division without explicit rounding.
2. `Wallet.balance_tzs` can never go below 0 (DB CHECK constraint + service check).
3. Every change to a balance creates exactly **one `LedgerEntry`** in the **same DB transaction**.
4. `LedgerEntry` is append-only. Mistakes are fixed with a new `adjustment` entry, never by editing.
5. Every entry has a **unique `idempotency_key`**. Running the same operation twice must do nothing the second time.
6. Only `apps/wallet/services.py` may change balances. Views, tasks, signals, and admin call these functions.
7. Invariant (tested): `wallet.balance_tzs == SUM(ledger.amount_tzs)` for every wallet.

## 2. The service functions

All functions run inside `transaction.atomic()` and lock the wallet row with `select_for_update()`.

```python
def credit_topup(payment: Payment) -> LedgerEntry
def charge_song(user, job: SongJob, price_tzs: int) -> LedgerEntry     # raises InsufficientBalance
def refund_song(job: SongJob, amount_tzs: int) -> LedgerEntry | None
def adjust(wallet, amount_tzs: int, note: str, staff_user) -> LedgerEntry
```

Common pattern:

```python
with transaction.atomic():
    wallet = Wallet.objects.select_for_update().get(user=user)
    if LedgerEntry.objects.filter(idempotency_key=key).exists():
        return existing_entry          # already done → do nothing
    new_balance = wallet.balance_tzs + amount
    if new_balance < 0:
        raise InsufficientBalance
    wallet.balance_tzs = new_balance
    wallet.save(update_fields=["balance_tzs", "updated_at"])
    return LedgerEntry.objects.create(..., balance_after_tzs=new_balance, idempotency_key=key)
```

The UNIQUE constraint on `idempotency_key` is the final safety net: if two workers race, one insert fails with `IntegrityError` and its whole transaction rolls back.

## 3. Idempotency keys

| Operation | Key |
|---|---|
| Top-up credit | `topup:{payment.id}` |
| Song charge | `charge:{job.id}` |
| Song refund | `refund:{job.id}` (only one refund per job, ever) |
| Admin adjustment | `adjust:{uuid4}` (new each time — admin intends each one) |

## 4. Song charging and refunds

**Charge at creation** (in `POST /api/songs`, same transaction that creates the job):
- Read `price_tzs` from `AppSettings`, store it on the job as a snapshot.
- `charge_song()` → entry `-price_tzs`. If balance is too low → return HTTP 402 and create **no** job.

**Refund at settlement** (when the job reaches a final state, see MUREKA.md §6):

```
successful = number of versions with status "ready"
requested  = job.versions_requested            # 2
kept       = (job.price_tzs * successful) // requested
refund     = job.price_tzs - kept
```

| successful | refund (price 1,000) |
|---|---|
| 2 | 0 → no entry created |
| 1 | 500 |
| 0 | 1,000 |

- Settlement runs in one transaction: lock job, `if job.settled_at: return`, call `refund_song()` if refund > 0, set `settled_at = now()`.
- The user always sees the refund as its own line in Wallet history.

## 5. Top-up credit

Only `payments` code calls `credit_topup()`, and only after the payment is **confirmed by Snippe's GET status API** with `status == "completed"` and confirmed amount == `payment.amount_tzs` (see SNIPPE.md §4). Amount credited = `payment.amount_tzs`. OSP absorbs Snippe's ~2.5% fee, so the user gets the full amount they paid.

If the confirmed amount differs from the requested amount → do **not** credit; mark the payment for admin review (log + admin filter).

## 6. Admin adjustments

- Only staff users, from Django admin action "Adjust balance".
- Requires amount (≠ 0) and a note of at least 10 characters.
- Records `created_by`.
- Cannot make balance negative.

## 7. Required tests (must pass before any real money)

1. Charge with enough balance → balance down, one entry.
2. Charge with too little balance → 402, no job, no entry.
3. Two concurrent charges that together exceed the balance → only one succeeds (use threads + real Postgres).
4. `credit_topup` called twice for the same payment → credited once.
5. Settlement run twice → refunded once.
6. 1 of 2 versions ready → refund exactly half; 0 of 2 → full refund; 2 of 2 → no refund.
7. Odd price (e.g. 999) with 1 ready → refund 500 (999 − 499); no money created or lost.
8. Adjustment that would go negative → rejected.
9. Invariant check: balance equals ledger sum after a random sequence of 200 operations.
10. LedgerEntry update/delete attempts raise an error (override `save`/`delete` for existing rows).

## 8. Daily integrity check

Celery Beat task `check_wallet_integrity` (daily, 03:00 EAT): for every wallet compare balance vs ledger sum. Any mismatch → error log + red warning in the admin daily summary.
