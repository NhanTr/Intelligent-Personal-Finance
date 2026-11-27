from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
import re
import pandas as pd

REQUIRED = ["transaction_id", "date", "type", "amount", "category"]


def validate(df, user_id, existing=()):
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        return df, [{"line": "file", "message": "Thiếu cột: " + ", ".join(missing)}], []
    df = df.copy().reset_index(drop=True)
    if "note" not in df:
        df["note"] = ""
    warnings = []
    if "user_id" in df and df["user_id"].fillna("").astype(str).ne(user_id).any():
        warnings.append("user_id trong file khác tài khoản hiện tại và sẽ bị bỏ qua; dữ liệu chỉ thuộc phiên hiện tại.")
    df["user_id"] = user_id
    date_strings = df["date"].fillna("").astype(str).str.strip()
    dates = pd.to_datetime(date_strings, format="%Y-%m-%d", errors="coerce")
    # Preserve CSV text before calling this function (read_csv(dtype=str)).
    # Accept digits only: interpreting 150.000 as 150 would silently lose money.
    raw_amounts = df["amount"].fillna("").astype(str).str.strip()
    valid_amounts = raw_amounts.str.fullmatch(r"[0-9]+")
    duplicate = df["transaction_id"].astype(str).duplicated(keep=False) | df["transaction_id"].astype(str).isin(existing)
    errors = []
    for i in range(len(df)):
        issues = []
        for col in REQUIRED:
            if pd.isna(df.at[i, col]) or not str(df.at[i, col]).strip():
                issues.append("thiếu " + col)
        if pd.isna(dates.iloc[i]) or not date_strings.iloc[i].isascii() or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', date_strings.iloc[i]):
            issues.append("ngày phải theo YYYY-MM-DD")
        if not valid_amounts.iloc[i] or len(raw_amounts.iloc[i]) > 16 or int(raw_amounts.iloc[i]) <= 0 or int(raw_amounts.iloc[i]) > 2**53:
            issues.append("Số tiền phải là số nguyên VND dương, không có dấu phân cách; ví dụ 150.000 nhập thành 150000")
        if df.at[i, "type"] not in ("income", "expense", "transfer"):
            issues.append("type phải là income, expense hoặc transfer")
        if duplicate.iloc[i]: issues.append("trùng transaction_id trong file hoặc dữ liệu hiện có")
        if issues: errors.append({"line": i + 2, "message": "; ".join(issues)})
    return df, errors, warnings


def savings(goal, saved, income, essential, optional):
    # Decimal prevents floating-point error from rounding a whole-month result up.
    goal, saved, income, essential, optional = (
        Decimal(str(value)) for value in (goal, saved, income, essential, optional)
    )
    rows = []
    for label, pct in [("Giữ nguyên", Decimal("0")), ("Giảm 10% chi tùy chọn", Decimal("0.1")), ("Giảm 20% chi tùy chọn", Decimal("0.2"))]:
        cost = essential + optional * (1 - pct)
        monthly = income - cost
        remaining = max(Decimal(0), goal - saved)
        months = 0 if remaining == 0 else int((remaining / monthly).to_integral_value(rounding=ROUND_CEILING)) if monthly > 0 else None
        rows.append({"scenario": label, "cost": cost, "monthly": monthly, "months": months})
    return rows


def money(n):
    rounded = Decimal(str(n)).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    return f"{rounded:,.0f}".replace(",", ".") + " VND"
