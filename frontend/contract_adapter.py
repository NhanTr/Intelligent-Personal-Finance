"""Adapter nháp giữa giao dịch mock UI và TransactionRecord ML.

Không tạo API, không xác thực, không thay thế contract BE. Việc gán 00:00 hoặc
chiều chuyển khoản là giả định có opt-in rõ ràng, không dùng âm thầm cho ML.
"""
from datetime import date, datetime, time, timezone, timedelta
from decimal import Decimal, InvalidOperation
import re

VN_TZ = timezone(timedelta(hours=7))
CATEGORY_LABELS = {
    'food':'Ăn uống', 'transport':'Di chuyển', 'housing':'Nhà ở',
    'utilities':'Điện nước', 'shopping':'Mua sắm', 'entertainment':'Giải trí',
    'health':'Sức khỏe', 'education':'Giáo dục', 'salary':'Lương',
    'bonus':'Thưởng', 'transfer':'Chuyển nội bộ', 'other':'Khác',
}
CATEGORY_CODES = {label.casefold(): code for code, label in CATEGORY_LABELS.items()}
CATEGORY_CODES.update({code: code for code in CATEGORY_LABELS})
CATEGORY_CODES['chuyển khoản nội bộ'] = 'transfer'

class AdapterError(ValueError):
    pass

def _category(value):
    if not isinstance(value, str) or not value.strip():
        raise AdapterError('Thiếu danh mục')
    result = CATEGORY_CODES.get(value.strip().casefold())
    if not result:
        raise AdapterError('Danh mục chưa có mapping; cần nhóm xác nhận')
    return result

def _amount(value):
    if isinstance(value, bool): raise AdapterError('Số tiền không hợp lệ')
    if isinstance(value, str) and not re.fullmatch(r'[0-9]+', value.strip()):
        raise AdapterError('Số tiền dạng chữ phải chỉ gồm chữ số, không có dấu phân cách')
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError) as e:
        raise AdapterError('Số tiền không hợp lệ') from e
    if not amount.is_finite() or amount <= 0 or amount != amount.to_integral_value() or amount > 2**53:
        raise AdapterError('Số tiền phải là số nguyên VND dương và biểu diễn chính xác')
    return int(amount)

def _timestamp(value):
    if not isinstance(value, str) or 'T' not in value:
        raise AdapterError('Cần timestamp ISO-8601 có múi giờ')
    try:
        result = datetime.fromisoformat(value.replace('Z','+00:00'))
        if result.utcoffset() is None: raise ValueError('missing timezone')
        return result.astimezone(VN_TZ)
    except ValueError as e:
        raise AdapterError('Timestamp không hợp lệ hoặc thiếu múi giờ') from e

def to_ml_transaction(row, *, assume_midnight=False, transfer_direction=None):
    if not isinstance(row, dict): raise AdapterError('Giao dịch phải là object')
    txid, user = row.get('transaction_id'), row.get('user_id')
    if not isinstance(txid, str) or not txid.strip() or not isinstance(user, str) or not user.strip():
        raise AdapterError('Thiếu transaction_id hoặc user_id')
    kind = row.get('type')
    if kind not in ('income','expense','transfer'): raise AdapterError('Loại không hợp lệ')
    category = _category(row.get('category'))
    if kind == 'transfer':
        if transfer_direction not in ('income','expense'):
            raise AdapterError('Chuyển nội bộ cần xác nhận chiều income/expense')
        if category != 'transfer':
            raise AdapterError('Danh mục chuyển nội bộ không khớp loại; cần nhóm xác nhận')
        kind_ml = transfer_direction
    else:
        kind_ml = kind
        if category == 'transfer': raise AdapterError('Danh mục transfer cần loại chuyển nội bộ rõ ràng')
    stamp = row.get('timestamp') or row.get('occurred_at')
    if stamp:
        dt = _timestamp(stamp)
        if row.get('date') and dt.date().isoformat() != str(row['date']):
            raise AdapterError('Ngày không khớp timestamp tại múi giờ Việt Nam')
    elif assume_midnight:
        try:
            raw_date = row['date']
            if not isinstance(raw_date, str) or date.fromisoformat(raw_date).isoformat() != raw_date: raise ValueError('date')
            dt = datetime.combine(date.fromisoformat(raw_date), time.min, tzinfo=VN_TZ)
        except (KeyError, TypeError, ValueError) as e:
            raise AdapterError('Ngày không hợp lệ') from e
    else:
        raise AdapterError('Thiếu giờ giao dịch; chỉ dùng assume_midnight=True cho giả lập được ghi nhận')
    return {'transaction_id':txid.strip(), 'user_id':user.strip(), 'timestamp':dt.isoformat(),
            'type':kind_ml, 'amount_vnd':_amount(row.get('amount')), 'category':category,
            'is_internal_transfer':kind == 'transfer', 'note':row.get('note') or None}

def from_ml_transaction(row):
    if not isinstance(row, dict): raise AdapterError('Giao dịch phải là object')
    txid,user = row.get('transaction_id'),row.get('user_id')
    if not isinstance(txid,str) or not txid.strip() or not isinstance(user,str) or not user.strip(): raise AdapterError('Thiếu mã hoặc người dùng')
    internal = row.get('is_internal_transfer', False)
    if not isinstance(internal,bool) or row.get('type') not in ('income','expense'): raise AdapterError('Loại hoặc cờ chuyển khoản không hợp lệ')
    category = _category(row.get('category'))
    if (category == 'transfer') != internal: raise AdapterError('Cần xác nhận cờ và danh mục chuyển khoản')
    dt = _timestamp(row.get('timestamp'))
    return {'transaction_id':txid.strip(),'user_id':user.strip(),'date':dt.date().isoformat(),
            'timestamp':dt.isoformat(),'type':'transfer' if internal else row['type'],
            'transfer_direction':row['type'] if internal else None,'amount':_amount(row.get('amount_vnd')),
            'category':CATEGORY_LABELS[category],'note':row.get('note') or ''}
