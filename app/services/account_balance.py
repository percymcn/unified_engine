"""Balance extraction for nested broker accounts and account cards."""

from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

BALANCE_KEYS: Sequence[str] = (
    "balance",
    "accountBalance",
    "account_balance",
    "Balance",
    "projectedBalance",
)
EQUITY_KEYS: Sequence[str] = (
    "equity",
    "Equity",
    "accountEquity",
    "account_equity",
)


def _as_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def money_from_row(row: Optional[Mapping[str, Any]], keys: Iterable[str]) -> Optional[float]:
    """Read the first numeric money field from a broker account row."""
    if not isinstance(row, Mapping):
        return None
    for key in keys:
        if key in row:
            amount = _as_float(row.get(key))
            if amount is not None:
                return amount
    return None


def coerce_account_rows(raw: Any) -> List[Dict[str, Any]]:
    """Normalize an SDK account list or dataframe-like object into dict rows."""
    if raw is None:
        return []
    if isinstance(raw, list):
        rows: List[Dict[str, Any]] = []
        for item in raw:
            if isinstance(item, Mapping):
                rows.append(dict(item))
            else:
                rows.append({"id": item})
        return rows
    if hasattr(raw, "to_dict"):
        try:
            records = raw.to_dict(orient="records")
        except TypeError:
            records = raw.to_dict()
        if isinstance(records, list):
            return [dict(item) for item in records if isinstance(item, Mapping)]
    return []


def balance_for_nested_account(
    row: Optional[Mapping[str, Any]],
    account_state: Optional[Mapping[str, Any]],
    account_id: Any,
    selected_account_id: Any,
) -> Tuple[Optional[float], Optional[float], str]:
    """
    Prefer columns on the nested account row.

    The single selected account may use the SDK account-state snapshot.
    That snapshot is not copied onto every nested account.
    """
    balance = money_from_row(row, BALANCE_KEYS)
    equity = money_from_row(row, EQUITY_KEYS)
    currency = None
    if isinstance(row, Mapping):
        currency = row.get("currency") or row.get("Currency")

    is_selected = (
        selected_account_id is not None and str(account_id) == str(selected_account_id)
    )
    if balance is None and is_selected:
        balance = money_from_row(account_state, BALANCE_KEYS)
        if equity is None:
            equity = money_from_row(account_state, EQUITY_KEYS)
        if not currency and isinstance(account_state, Mapping):
            currency = account_state.get("currency") or account_state.get("Currency")

    return balance, equity, str(currency or "USD")


def _matching_row(rows: Sequence[Mapping[str, Any]], account_id: Any) -> Optional[Mapping[str, Any]]:
    if account_id is None:
        return None
    wanted = str(account_id)
    for row in rows:
        row_id = row.get("id") or row.get("account_id") or row.get("accountId")
        if row_id is not None and str(row_id) == wanted:
            return row
    return None


def resolve_card_balances(
    stored_balance: Any,
    stored_equity: Any,
    metadata: Optional[Mapping[str, Any]],
) -> Tuple[float, float]:
    """
    Choose the balance shown on an account card.

    A stored non-zero balance is kept. A stored zero is replaced by the selected
    subaccount, the default nested account, or the only discovered non-zero row.
    """
    balance = _as_float(stored_balance) or 0.0
    equity = _as_float(stored_equity) or 0.0
    if balance != 0.0:
        return balance, equity

    meta = metadata if isinstance(metadata, Mapping) else {}
    selected = meta.get("selected_subaccount") or meta.get("selected_account")
    if isinstance(selected, Mapping):
        selected_balance = money_from_row(selected, BALANCE_KEYS)
        selected_equity = money_from_row(selected, EQUITY_KEYS)
        if selected_balance:
            return selected_balance, selected_equity if selected_equity is not None else selected_balance

    discovered = meta.get("discovered_accounts") or meta.get("selected_accounts") or []
    if not isinstance(discovered, list):
        discovered = []
    rows = [row for row in discovered if isinstance(row, Mapping)]

    chosen = _matching_row(rows, meta.get("default_account_id"))
    if chosen is None:
        nonzero = [row for row in rows if money_from_row(row, BALANCE_KEYS)]
        if len(nonzero) == 1:
            chosen = nonzero[0]
        elif len(rows) == 1:
            chosen = rows[0]

    if chosen is not None:
        chosen_balance = money_from_row(chosen, BALANCE_KEYS)
        chosen_equity = money_from_row(chosen, EQUITY_KEYS)
        if chosen_balance:
            return chosen_balance, chosen_equity if chosen_equity is not None else chosen_balance

    return balance, equity


def selected_snapshot_from_credentials(credentials: Optional[Mapping[str, Any]]) -> Optional[Dict[str, Any]]:
    """Pull the selected nested account snapshot out of create-account credentials."""
    if not isinstance(credentials, Mapping):
        return None
    selected = credentials.get("selected_subaccount") or credentials.get("selected_account")
    if isinstance(selected, Mapping):
        return dict(selected)
    accounts = credentials.get("selected_accounts")
    if isinstance(accounts, list) and accounts:
        default_id = credentials.get("default_account_id")
        match = _matching_row(
            [row for row in accounts if isinstance(row, Mapping)],
            default_id,
        )
        if match is not None:
            return dict(match)
        first = accounts[0]
        if isinstance(first, Mapping):
            return dict(first)
    return None


def metadata_for_selected_snapshot(
    credentials: Optional[Mapping[str, Any]],
    snapshot: Mapping[str, Any],
) -> Dict[str, Any]:
    """Metadata stored on the trading account so a reload can show the nested balance."""
    selected_accounts = []
    if isinstance(credentials, Mapping) and isinstance(credentials.get("selected_accounts"), list):
        selected_accounts = [
            dict(row) for row in credentials["selected_accounts"] if isinstance(row, Mapping)
        ]
    if not selected_accounts:
        selected_accounts = [dict(snapshot)]
    default_id = None
    if isinstance(credentials, Mapping):
        default_id = credentials.get("default_account_id")
    return {
        "selected_subaccount": dict(snapshot),
        "selected_accounts": selected_accounts,
        "discovered_accounts": selected_accounts,
        "default_account_id": default_id or snapshot.get("id") or snapshot.get("account_id"),
    }


def account_identity_matches(account_id: Any, row_id: Any, account_number: Any) -> bool:
    """Match a delete request to a numeric primary key or a broker account number."""
    wanted = str(account_id)
    if row_id is not None and str(row_id) == wanted:
        return True
    if account_number is not None and str(account_number) == wanted:
        return True
    return False


def delete_trading_account(db: Any, user_id: int, account_id: Any) -> bool:
    """Delete a user's trading account and commit so a reload does not restore the card."""
    from app.models.database_models import TradingAccount

    rows = (
        db.query(TradingAccount)
        .filter(TradingAccount.user_id == user_id)
        .all()
    )
    target = None
    for row in rows:
        if account_identity_matches(account_id, getattr(row, "id", None), getattr(row, "account_number", None)):
            target = row
            break
    if target is None:
        return False
    db.delete(target)
    db.commit()
    return True


def apply_discovered_balances(stored_accounts: Sequence[Any], snapshots: Sequence[Mapping[str, Any]]) -> int:
    """
    Remember discovered nested accounts on stored rows whose balance is still zero.

    Returns how many stored rows were updated. Does not replace a non-zero balance.
    """
    if not snapshots:
        return 0
    clean = [dict(row) for row in snapshots if isinstance(row, Mapping)]
    if not clean:
        return 0

    updated = 0
    for stored in stored_accounts:
        meta = dict(stored.extra_metadata or {}) if isinstance(getattr(stored, "extra_metadata", None), Mapping) else {}
        meta["discovered_accounts"] = clean
        stored.extra_metadata = meta
        balance, equity = resolve_card_balances(stored.balance, stored.equity, meta)
        if (stored.balance or 0) == 0 and balance:
            stored.balance = balance
            updated += 1
        if (stored.equity or 0) == 0 and equity:
            stored.equity = equity
    return updated


def serialize_trading_account(account: Any) -> Dict[str, Any]:
    """Card payload expected by the accounts UI."""
    broker = account.broker.value if hasattr(account.broker, "value") else str(account.broker)
    account_type = (
        account.account_type.value if hasattr(account.account_type, "value") else str(account.account_type)
    )
    meta = account.extra_metadata if isinstance(getattr(account, "extra_metadata", None), Mapping) else {}
    balance, equity = resolve_card_balances(account.balance, account.equity, meta)
    created = account.created_at.isoformat() if getattr(account, "created_at", None) else None
    last_sync = account.last_sync.isoformat() if getattr(account, "last_sync", None) else None
    return {
        "id": account.id,
        "account_id": account.account_number,
        "broker": broker,
        "account_type": account_type,
        "currency": account.currency or "USD",
        "leverage": account.leverage or 1,
        "is_active": bool(account.is_active),
        "is_connected": bool(account.is_connected),
        "balance": balance,
        "equity": equity,
        "margin": float(account.margin or 0),
        "free_margin": float(account.free_margin or 0),
        "last_sync": last_sync,
        "created_at": created,
    }
