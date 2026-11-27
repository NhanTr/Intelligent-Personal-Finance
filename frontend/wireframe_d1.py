"""D1 wireframe with session-local sample data and draft API interfaces."""

import uuid
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import altair as alt
import streamlit as st
from api_client import MockApiClient, ApiError
from core import validate, savings, money
from dashboard import compare_periods
from ml_contract import MLContractError
from mock_ml_client import MockMLContractClient
from contract_adapter import CATEGORY_LABELS
from ui_components import Share, amount_change, data_table, primary_caption, section_rule

st.set_page_config(page_title="Sổ Mây · Wireframe D1", page_icon=":material/account_balance_wallet:", layout="wide")
st.markdown("<style>" + (Path(__file__).parent / "ui.css").read_text(encoding="utf-8") + "</style>", unsafe_allow_html=True)

TYPES = {"Thu": "income", "Chi": "expense", "Chuyển nội bộ": "transfer"}
TYPE_LABELS = {value: label for label, value in TYPES.items()}
CATEGORIES = {"Chi": ["Ăn uống", "Di chuyển", "Mua sắm"], "Thu": ["Lương"], "Chuyển nội bộ": ["Chuyển nội bộ"]}
TX_COLUMNS = ["Ngày", "Loại", "Danh mục", "Số tiền (VND)", "Ghi chú"]


def switch_account():
    for key in list(st.session_state):
        if key in {"user", "nav", "notice"} or key.startswith(("dash", "tx", "edit_", "confirm_")):
            del st.session_state[key]


def open_transaction_form():
    st.session_state.nav = "Thu chi"
    st.session_state.tx_actions = True
    st.session_state.tx_tabs = "Thêm giao dịch"


try:
    if "client" not in st.session_state: st.session_state.client = MockApiClient()
    client = st.session_state.client
except ApiError as exc:
    st.error(str(exc)); st.stop()

if "user" not in st.session_state:
    left, right = st.columns([1.2, 1], gap="large")
    with left:
        st.markdown('''<div class="hero"><div class="hero-brand">SỔ MÂY</div><div class="hero-content"><div class="hero-kicker">TÀI CHÍNH CÁ NHÂN</div><h1>Hiểu dòng tiền.<br>Chủ động kế hoạch.</h1><p>Theo dõi thu chi, xem xu hướng và tính thời gian dành dụm cho mục tiêu của bạn.</p><div class="hero-divider"></div><div class="hero-points"><span>Theo dõi thu chi</span><span>Phân tích chi tiêu</span><span>Mô phỏng tiết kiệm</span></div></div></div>''', unsafe_allow_html=True)
    with right:
        st.write(""); st.write("")
        st.markdown('<div class="eyebrow">KHÔNG GIAN CỦA BẠN</div>', unsafe_allow_html=True)
        st.header("Chào mừng trở lại")
        st.caption("Mở khung giao diện D1 để kiểm thử các luồng bằng dữ liệu giả lập.")
        with st.form("login"):
            user_choice = st.selectbox(
                "Tài khoản demo", ["U001", "U002", "U003"],
                format_func=lambda user_id: "U003 · tài khoản trống ban đầu" if user_id == "U003" else user_id,
            )
            password = st.text_input("Mật khẩu demo", value="demo", type="password")
            login = st.form_submit_button("Vào không gian tài chính", type="primary", use_container_width=True)
        if login:
            if password == "demo": st.session_state.user = user_choice; st.rerun()
            else: st.error("Mật khẩu chưa đúng. Mật khẩu demo là demo.")
        st.caption("Bản giả lập · Mật khẩu: demo · Không nhập dữ liệu cá nhân thật")
    st.stop()

user = st.session_state.user
with st.sidebar:
    st.markdown('<div class="sidebar-brand"><strong>Sổ Mây</strong><small>TÀI CHÍNH CÁ NHÂN</small></div>', unsafe_allow_html=True)
    st.caption("Wireframe D1 · Dữ liệu giả lập")
    st.divider()
    page = st.radio("Điều hướng", ["Dashboard", "Thu chi", "Dự báo", "Cảnh báo", "Tiết kiệm"], key="nav", label_visibility="collapsed")
    st.divider()
    st.markdown(f"**{user}**")
    st.caption("Tài khoản demo")
    st.button("Đổi tài khoản", width="stretch", on_click=switch_account)
    with st.expander("Kiểm thử wireframe D1"):
        client.simulate_error = st.checkbox("Giả lập lỗi kết nối")
        forecast_scenario = st.selectbox("Kịch bản dự báo mẫu", ["Theo tài khoản", "Mô hình thành công", "Dự báo cơ sở", "Chưa đủ dữ liệu"])
        anomaly_scenario = st.selectbox("Kịch bản cảnh báo mẫu", ["Theo tài khoản", "Có cảnh báo", "Không có cảnh báo", "Mô hình chưa sẵn sàng"])

# Thiếu dữ liệu mẫu ML chỉ chặn trang thông minh, không chặn đăng nhập/thu chi.
if page in ("Dự báo", "Cảnh báo"):
    try:
        if "ml_client" not in st.session_state:
            st.session_state.ml_client = MockMLContractClient()
        ml_client = st.session_state.ml_client
        ml_client.simulate_error = client.simulate_error
    except MLContractError:
        st.error("Không tải được dữ liệu mẫu ML. Các chức năng thu chi và tiết kiệm vẫn có thể sử dụng.")
        st.stop()

def header(kicker, title, subtitle):
    st.markdown(f'<div class="eyebrow">D1 · {kicker}</div>', unsafe_allow_html=True)
    st.title(title)
    st.markdown(f'<p class="subtle">{subtitle}</p>', unsafe_allow_html=True)

def default_range(rows):
    latest = max((date.fromisoformat(row["date"]) for row in rows), default=date.today())
    return latest - timedelta(days=30), latest


def period_inputs(prefix, dates, columns):
    for name, value in zip(("start", "end"), dates):
        st.session_state.setdefault(prefix + name, value)
    start = columns[0].date_input("Từ ngày", key=prefix + "start", format="DD/MM/YYYY")
    end = columns[1].date_input("Đến ngày", key=prefix + "end", format="DD/MM/YYYY")
    return start, end


def reset_range(prefix, dates):
    st.session_state[prefix + "start"], st.session_state[prefix + "end"] = dates


def empty_state(title, detail):
    st.markdown(f'<div class="empty-ledger"><h3>{title}</h3><p>{detail}</p></div>', unsafe_allow_html=True)


def show_transaction_table(rows):
    view = (
        (f"{date.fromisoformat(row['date']):%d/%m/%Y}", TYPE_LABELS[row["type"]],
         row["category"], money(row["amount"]), row.get("note", ""))
        for row in rows
    )
    data_table("Danh sách giao dịch", TX_COLUMNS, view, numeric=(3,), scroll=True)
    income = sum(row["amount"] for row in rows if row["type"] == "income")
    expense = sum(row["amount"] for row in rows if row["type"] == "expense")
    st.markdown(
        f'<div class="tx-totals"><span>{len(rows)} giao dịch</span>'
        f'<span class="total-income">Thu <strong>{money(income)}</strong></span>'
        f'<span class="total-expense">Chi <strong>{money(expense)}</strong></span>'
        f'<span>Chênh lệch <strong>{amount_change(income - expense)}</strong></span></div>',
        unsafe_allow_html=True,
    )


def reveal_saved_transactions(defaults):
    saved_rows = st.session_state.pop("tx_saved_rows", None)
    if not saved_rows:
        return set()
    start, end = defaults
    if st.session_state.get("txstart", start) <= st.session_state.get("txend", end):
        start = st.session_state.get("txstart", start)
        end = st.session_state.get("txend", end)
    dates = [date.fromisoformat(row["date"]) for row in saved_rows]
    reset_range("tx", (min(start, *dates), max(end, *dates)))
    selected_type = st.session_state.get("tx_type", "Tất cả")
    if selected_type != "Tất cả" and any(row["type"] != TYPES[selected_type] for row in saved_rows):
        st.session_state.tx_type = "Tất cả"
    selected_category = st.session_state.get("tx_category", "Tất cả")
    if selected_category != "Tất cả" and any(row["category"] != selected_category for row in saved_rows):
        st.session_state.tx_category = "Tất cả"
    st.session_state.tx_actions = False
    return {row["transaction_id"] for row in saved_rows}

try:
    if page == "Dashboard":
        header("TỔNG QUAN", "Tổng quan tài chính", "Thu chi và thay đổi trong khoảng thời gian đã chọn.")
        all_rows = client.get_transactions(user)
        dates = default_range(all_rows)
        start, end = period_inputs("dash", dates, st.columns(2))
        if start > end:
            st.error("Ngày bắt đầu phải trước hoặc bằng ngày kết thúc.")
            st.button("Đổi khoảng ngày", on_click=reset_range, args=("dash", dates))
            st.stop()

        filters = {"from": str(start), "to": str(end)}
        current = client.get_stats(user, filters)
        duration = (end - start).days + 1
        previous = client.get_stats(user, {"from": str(start - timedelta(days=duration)), "to": str(start - timedelta(days=1))})
        if not client.get_transactions(user, filters):
            detail = ("Tài khoản này chưa có giao dịch. Hãy thêm khoản thu hoặc chi đầu tiên."
                      if not all_rows else "Chưa có giao dịch trong khoảng này. Bạn có thể chọn lại kỳ hoặc ghi một khoản mới.")
            empty_state("Chưa có giao dịch trong kỳ", detail)
            with st.container(horizontal=True, gap="small"):
                st.button("Thêm giao dịch", type="primary", on_click=open_transaction_form)
                st.button("Đổi khoảng ngày", on_click=reset_range, args=("dash", dates))
        else:
            st.markdown(f'''<div class="ledger-summary">
                <div class="ledger-primary"><div class="ledger-label">Chênh lệch thu − chi</div><div class="ledger-period">{start:%d/%m/%Y} – {end:%d/%m/%Y}</div><div class="ledger-amount">{money(current['balance'])}</div><div class="ledger-context">{amount_change(current['balance'] - previous['balance'])} so với khoảng trước</div></div>
                <div class="ledger-secondary"><div class="ledger-label">Tổng thu</div><div class="ledger-value">{money(current['income'])}</div><div class="ledger-context">{amount_change(current['income'] - previous['income'])} so với khoảng trước</div></div>
                <div class="ledger-secondary"><div class="ledger-label">Tổng chi</div><div class="ledger-value">{money(current['expense'])}</div><div class="ledger-context">{amount_change(current['expense'] - previous['expense'])} so với khoảng trước</div></div>
                </div>''', unsafe_allow_html=True)
            st.caption("Chênh lệch là thu trừ chi trong kỳ. Chuyển nội bộ không tính vào tổng thu hoặc chi.")

        if all_rows:
            section_rule("CƠ CẤU VÀ DIỄN BIẾN")
            left, right = st.columns([1.35, 1], gap="large")
            with left:
                st.subheader("Chi tiêu theo danh mục")
                primary_caption("Tỷ trọng trong khoảng ngày đã chọn")
                if current["categories"]:
                    categories = sorted(current["categories"].items(), key=lambda item: (-item[1], item[0]))
                    data_table("Chi tiêu theo danh mục", ["Danh mục", "Tổng chi (VND)", "Tỷ trọng"],
                               [(category, money(amount), Share(amount / current["expense"] * 100)) for category, amount in categories],
                               numeric=(1,))
                else:
                    st.caption("Chưa phát sinh chi tiêu trong khoảng này.")
                names = set(current["categories"]) | set(previous["categories"])
                if names:
                    comparison = [
                        (category, previous["categories"].get(category, 0), current["categories"].get(category, 0))
                        for category in sorted(names)
                    ]
                    section_rule("SO VỚI KHOẢNG TRƯỚC")
                    st.caption(f"So sánh với {duration} ngày liền trước, cùng độ dài với khoảng đã chọn.")
                    data_table("So sánh chi theo danh mục", ["Danh mục", "Khoảng trước", "Khoảng này", "Chênh lệch"],
                               [(category, money(old), money(new), amount_change(new - old))
                                for category, old, new in comparison], numeric=(1, 2, 3))
                    largest = max(new - old for _, old, new in comparison)
                    if largest > 0:
                        names = ", ".join(category for category, old, new in comparison if new - old == largest)
                        st.caption(f"Tăng nhiều nhất theo số tiền: {names} ({amount_change(largest)}). Đây là số tiền tuyệt đối, chưa áp dụng ngưỡng 'tăng mạnh'.")
                    else:
                        st.caption("Không có danh mục nào tăng so với khoảng trước theo số tiền tuyệt đối.")
            with right:
                st.subheader("So sánh thu và chi")
                granularity = st.radio("Đơn vị so sánh", ["Tuần", "Tháng"], key="dash_granularity", horizontal=True)
                prior, active = compare_periods(client, user, end, granularity)
                primary_caption(f"Kỳ này · {active['range']}")
                st.caption(f"Kỳ trước · {prior['range']} · Đơn vị VND")
                labels = {"income": "Thu", "expense": "Chi", "balance": "Chênh lệch"}
                chart_data = pd.DataFrame([
                    {"Kỳ": period["label"], "Ngày": period["range"], "Loại": labels[key], "Số tiền": period[key]}
                    for period in (prior, active) for key in ("income", "expense")
                ])
                chart = alt.Chart(chart_data).mark_bar(size=26, cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
                    x=alt.X("Kỳ:N", sort=["Kỳ trước", "Kỳ này"], title=None, axis=alt.Axis(labelAngle=0)),
                    xOffset=alt.XOffset("Loại:N", sort=["Thu", "Chi"]),
                    y=alt.Y("Số tiền:Q", axis=alt.Axis(format="~s"), title="VND"),
                    color=alt.Color("Loại:N", scale=alt.Scale(domain=["Thu", "Chi"], range=["#5c5153", "#a1263d"]),
                                    legend=alt.Legend(orient="top", title=None, labelColor="#5c5153")),
                    tooltip=[alt.Tooltip("Kỳ:N"), alt.Tooltip("Ngày:N"), alt.Tooltip("Loại:N"),
                             alt.Tooltip("Số tiền:Q", format=",.0f", title="Số tiền (VND)")],
                ).properties(height=165, background="transparent").configure_axis(
                    labelColor="#5c5153", titleColor="#5c5153", gridColor="#e2d9da",
                ).configure_view(stroke=None)
                st.altair_chart(chart, width="stretch", theme=None, alt=f"Biểu đồ cột Thu và Chi theo {granularity.lower()}")
                data_table("So sánh thu chi theo kỳ", ["Chỉ số", "Kỳ trước", "Kỳ này", "Chênh lệch"],
                           [(label, money(prior[key]).removesuffix(" VND"), money(active[key]).removesuffix(" VND"),
                             amount_change(active[key] - prior[key]).removesuffix(" VND")) for key, label in labels.items()],
                           numeric=(1, 2, 3))

    elif page == "Thu chi":
        header("NGHIỆP VỤ / THU CHI", "Giao dịch của bạn", "Ghi lại và quản lý từng khoản thu, chi trong một nơi.")
        all_rows = client.get_transactions(user)
        dates = default_range(all_rows)
        categories = sorted({row["category"] for row in all_rows})
        saved_ids = reveal_saved_transactions(dates)
        with st.container(key="tx_toolbar"):
            columns = st.columns([1, 1, 1, 1.25])
            start, end = period_inputs("tx", dates, columns)
            kind = columns[2].selectbox("Loại", ["Tất cả", *TYPES], key="tx_type")
            category = columns[3].selectbox("Danh mục", ["Tất cả", *categories], key="tx_category")
        if start > end:
            st.error("Ngày bắt đầu phải trước hoặc bằng ngày kết thúc.")
        filters = {"from": str(start), "to": str(end), "type": TYPES.get(kind),
                   "category": None if category == "Tất cả" else category}
        rows = sorted(
            client.get_transactions(user, filters),
            key=lambda row: (row["transaction_id"] in saved_ids, row["date"], row["transaction_id"]),
            reverse=True,
        )
        if st.session_state.get("notice"):
            st.success(st.session_state.pop("notice"))

        with st.expander("Thêm giao dịch hoặc nhập CSV", key="tx_actions", on_change="rerun"):
            add_tab, import_tab = st.tabs(["Thêm giao dịch", "Nhập CSV"], key="tx_tabs", on_change="rerun")
            with add_tab:
                tx_type = st.selectbox("Loại giao dịch", list(CATEGORIES), key="tx_add_type")
                with st.form("tx_add"):
                    a, b = st.columns(2)
                    day = a.date_input("Ngày giao dịch", dates[1], format="DD/MM/YYYY")
                    amount = b.number_input("Số tiền (VND)", min_value=0, step=1000)
                    cat = st.selectbox("Danh mục", CATEGORIES[tx_type])
                    note = st.text_input("Ghi chú (không bắt buộc)")
                    add = st.form_submit_button("Thêm giao dịch", type="primary")
                if add:
                    if amount <= 0:
                        st.error("Vui lòng nhập số tiền lớn hơn 0.")
                    else:
                        item = {"transaction_id": str(uuid.uuid4()), "date": str(day), "type": TYPES[tx_type],
                                "amount": amount, "category": cat, "note": note}
                        client.add_transaction(user, item)
                        st.session_state.tx_saved_rows = [item]
                        st.session_state.notice = "Đã thêm giao dịch vào danh sách của phiên."
                        st.rerun()
            with import_tab:
                primary_caption("CSV UTF-8, ngày YYYY-MM-DD, số tiền nguyên và không dùng dấu phân cách hàng nghìn.")
                st.caption("Chỉ nhập khi toàn bộ file hợp lệ. Mã giao dịch trùng trong file hoặc trong tài khoản sẽ bị từ chối.")
                upload_id = st.session_state.get("tx_upload_id", 0)
                upload = st.file_uploader("Chọn file CSV", type="csv", key=f"tx_upload_{upload_id}")
                if upload:
                    try:
                        data = pd.read_csv(upload, encoding="utf-8-sig", dtype=str, keep_default_na=False)
                        normalized, errors, warnings = validate(data, user, [row["transaction_id"] for row in all_rows])
                        for warning in warnings:
                            st.warning(warning)
                        if errors:
                            st.error("File có lỗi. Chưa lưu dòng nào.")
                            data_table("Lỗi CSV", ["Dòng", "Chi tiết"], [(e["line"], e["message"]) for e in errors], scroll=True)
                        elif data.empty:
                            st.warning("File không có dòng dữ liệu.")
                        else:
                            st.success(f"{len(data)} dòng hợp lệ. Xem trước rồi xác nhận nhập vào phiên.")
                            data_table("Xem trước CSV", list(data.columns), data.head(20).itertuples(index=False, name=None), scroll=True)
                            if len(data) > 20:
                                st.caption("Hiển thị 20 dòng đầu. Toàn bộ file đã được kiểm tra.")
                            if st.button("Nhập vào phiên giả lập", type="primary"):
                                result = client.import_transactions(user, data)
                                if result["errors"]:
                                    st.error("Không nhập được dữ liệu. Chưa lưu dòng nào.")
                                    data_table("Lỗi nhập CSV", ["Dòng", "Chi tiết"],
                                               [(e["line"], e["message"]) for e in result["errors"]], scroll=True)
                                else:
                                    imported_ids = set(normalized["transaction_id"].str.strip())
                                    st.session_state.tx_saved_rows = [
                                        row for row in client.get_transactions(user) if row["transaction_id"] in imported_ids
                                    ]
                                    st.session_state.notice = f"Đã nhập {result['accepted']} giao dịch vào danh sách của phiên."
                                    st.session_state.tx_upload_id = upload_id + 1
                                    st.rerun()
                    except (ValueError, UnicodeError, pd.errors.ParserError) as exc:
                        st.error(f"Không đọc được CSV: {exc}")

        section_rule("DANH SÁCH GIAO DỊCH")
        if rows:
            show_transaction_table(rows)
            with st.expander("Sửa hoặc xóa giao dịch trong phiên"):
                ids={f"{r['date']} · {r['category']} · {money(r['amount'])} · {r['transaction_id'][-8:]}":r for r in rows}
                selected=st.selectbox("Chọn giao dịch", list(ids), key="tx_edit_pick")
                item=ids[selected]
                type_labels = TYPE_LABELS
                category_options = CATEGORIES
                new_type=st.selectbox("Loại giao dịch mới",list(category_options),index=list(category_options).index(type_labels[item["type"]]),key="edit_type_"+item["transaction_id"])
                options=list(category_options[new_type])
                # CSV có thể chứa danh mục ngoài danh sách demo; giữ nguyên
                # danh mục gốc khi chưa đổi loại để tránh ghi đè âm thầm.
                if new_type == type_labels[item["type"]] and item["category"] not in options:
                    options.insert(0, item["category"])
                initial_category=item["category"] if item["category"] in options else options[0]
                new_category=st.selectbox("Danh mục mới",options,index=options.index(initial_category),key="edit_cat_"+item["transaction_id"]+new_type)
                new_date=st.date_input("Ngày giao dịch mới",date.fromisoformat(item["date"]),key="edit_date_"+item["transaction_id"])
                new_amount=st.number_input("Số tiền mới (VND)",min_value=1,value=int(item["amount"]),step=1000,key="edit_amount_"+item["transaction_id"])
                new_note=st.text_input("Ghi chú mới",value=item.get("note", ""),key="edit_note_"+item["transaction_id"])
                a,b=st.columns(2)
                if a.button("Lưu thay đổi"):
                    client.update_transaction(user,item["transaction_id"],{"date":str(new_date),"type":TYPES[new_type],"category":new_category,"amount":new_amount,"note":new_note})
                    st.session_state.notice = "Đã cập nhật giao dịch trong phiên."
                    st.rerun()
                confirm = st.checkbox("Tôi muốn xóa giao dịch đã chọn",key="confirm_"+item["transaction_id"])
                if b.button("Xóa giao dịch", disabled=not confirm):
                    client.delete_transaction(user,item["transaction_id"])
                    st.session_state.notice = "Đã xóa giao dịch trong phiên."
                    st.rerun()
        else:
            detail = ("Tài khoản này chưa có giao dịch." if not all_rows else "Không có giao dịch khớp với khoảng ngày và bộ lọc đã chọn.")
            empty_state("Chưa tìm thấy giao dịch", detail)
            def reset_transaction_filters():
                reset_range("tx", dates)
                st.session_state.tx_type = "Tất cả"
                st.session_state.tx_category = "Tất cả"

            with st.container(horizontal=True, gap="small"):
                st.button("Thêm giao dịch", key="tx_empty_add", type="primary", on_click=open_transaction_form)
                st.button("Đổi khoảng ngày", on_click=reset_transaction_filters)

    elif page == "Dự báo":
        header("THÔNG MINH / DỰ BÁO", "Nhìn trước 7 ngày", "Một góc nhìn tham khảo để bạn chủ động với chi tiêu sắp tới.")
        st.warning("DỮ LIỆU MẪU CONTRACT ML · Không phải kết quả suy luận từ lịch sử trong ứng dụng.")
        scenario = {"Theo tài khoản":"auto", "Mô hình thành công":"ok", "Dự báo cơ sở":"fallback_baseline", "Chưa đủ dữ liệu":"insufficient_data"}[forecast_scenario]
        result = ml_client.forecast(user, scenario)
        section_rule("KẾT QUẢ DỰ BÁO")
        if result["status"] == "insufficient_data":
            st.info(f"Chưa đủ lịch sử: dữ liệu mẫu có {result['days_available']} ngày; cần tối thiểu {result['min_days_required']} ngày.")
            st.caption(f"Ngày gốc dự báo: {result['as_of_date']} · Khoảng dự kiến: {result['forecast_start_date']} – {result['forecast_end_date']} · Phiên bản: {result['model_version']}")
            st.caption("Đây là kịch bản minh họa, không được tính từ giao dịch trong ứng dụng.")
        else:
            if result["status"] == "fallback_baseline":
                st.info("Dự báo cơ sở: giá trị minh họa theo kịch bản tổng chi 7 ngày gần nhất.")
            a,b=st.columns([1,1.2],gap="large")
            with a: st.metric("Tổng chi dự kiến",money(result["predicted_total_vnd"]))
            with b:
                start=pd.Timestamp(result["forecast_start_date"]); end=pd.Timestamp(result["forecast_end_date"])
                st.markdown(f"**{start:%d/%m} – {end:%d/%m/%Y}**")
            primary_caption(f"Ngày gốc dự báo {result['as_of_date']} · Lịch sử {result['days_available']} ngày · {result['model_name']} · {result['model_version']}")
            st.caption("Thời điểm tạo dự báo: contract mẫu chưa cung cấp.")
            st.info(result["limitations_note"])

    elif page == "Cảnh báo":
        header("THÔNG MINH / CẢNH BÁO", "Giao dịch cần xem xét", "Bạn là người quyết định cuối cùng đối với từng cảnh báo.")
        st.warning("DỮ LIỆU MẪU CONTRACT ML · Các giao dịch bên dưới là ví dụ độc lập, không lấy từ danh sách Thu chi.")
        scenario = {"Theo tài khoản":"auto", "Có cảnh báo":"ok", "Không có cảnh báo":"empty", "Mô hình chưa sẵn sàng":"model_unavailable"}[anomaly_scenario]
        batch = ml_client.anomaly_batch(user, scenario)
        section_rule("KẾT QUẢ RÀ SOÁT")
        st.caption(batch["disclaimer"])
        if batch["status"] == "model_unavailable":
            st.info("Mô hình phát hiện bất thường chưa sẵn sàng. Các chức năng thu chi khác vẫn có thể sử dụng.")
        else:
            alerts = [item for item in batch["items"] if item["is_anomaly"]]
            primary_caption(f"Đã chấm {batch['total_evaluated']} giao dịch chi mẫu · Đánh dấu {batch['flagged_count']} · Phiên bản {batch['model_version']}")
            if not alerts: st.info("Không có giao dịch mẫu nào được đánh dấu trong kết quả này.")
            page_size = 10
            total_pages = max(1, (len(alerts) + page_size - 1) // page_size)
            page_number = st.number_input("Trang cảnh báo", min_value=1, max_value=total_pages, value=1, step=1) if total_pages > 1 else 1
            for item in alerts[(page_number - 1) * page_size : page_number * page_size]:
                with st.container(border=True):
                    a,b=st.columns([2,1])
                    with a:
                        category=CATEGORY_LABELS.get(item["category"],item["category"])
                        st.markdown(f"#### {category} · {money(item['amount_vnd'])}")
                        primary_caption(f"{pd.Timestamp(item['timestamp']).strftime('%H:%M %d/%m/%Y %z')} · Mã {item['transaction_id']}")
                        st.write(f"Điểm bất thường: {item['anomaly_score']:.5f} · Ngưỡng: {item['threshold']:.5f}")
                        if item["reasons"]:
                            st.write("Lý do cần xem xét:")
                            for reason in item["reasons"]: st.write("• " + reason)
                        else: st.caption("Kết quả này chưa cung cấp lý do chi tiết.")
                        st.caption("Điểm là thước đo bất thường, không phải xác suất gian lận.")
                    with b:
                        key=(user,item["transaction_id"],batch["model_version"])
                        feedback=ml_client.feedback.get(key)
                        if feedback:
                            st.success("Đã ghi trong phiên: " + ("Đúng" if feedback["is_confirmed_anomaly"] else "Sai"))
                            st.caption(f"Mô hình: {feedback['model_version']} · Thời điểm: {feedback['created_at']}")
                        else:
                            st.write("Cảnh báo này có phù hợp không?")
                            st.caption("Đúng: cần xem xét; Sai: không thấy bất thường. Không kết luận gian lận.")
                            x,y=st.columns(2)
                            if x.button("Đúng",key="y"+item["transaction_id"]): ml_client.save_feedback(user,item["transaction_id"],True,batch); st.rerun()
                            if y.button("Sai",key="n"+item["transaction_id"]): ml_client.save_feedback(user,item["transaction_id"],False,batch); st.rerun()

    else:
        header("KẾ HOẠCH / TIẾT KIỆM", "Biến mục tiêu thành kế hoạch", "Thử thay đổi giả định để xem bạn có thể đạt mục tiêu khi nào.")
        section_rule("MỤC TIÊU VÀ KỊCH BẢN")
        left,right=st.columns([1,1.35],gap="large")
        with left:
            st.subheader("Giả định của bạn")
            goal=st.number_input("Mục tiêu (VND)",min_value=0,value=12000000,step=100000)
            saved=st.number_input("Đã tiết kiệm (VND)",min_value=0,value=2000000,step=100000)
            income=st.number_input("Thu nhập mỗi tháng (VND)",min_value=0,value=8000000,step=100000)
            essential=st.number_input("Chi thiết yếu mỗi tháng (VND)",min_value=0,value=4000000,step=100000)
            optional=st.number_input("Chi tùy chọn mỗi tháng (VND)",min_value=0,value=3000000,step=100000)
        with right:
            st.subheader("So sánh kịch bản")
            primary_caption(f"Mục tiêu {money(goal)} · Đã có {money(saved)} · Không tính lãi suất")
            result = savings(goal, saved, income, essential, optional)
            base = result[0]["months"]
            for row in result:
                months = row["months"]
                with st.container(border=True):
                    scenario, duration = st.columns([2, 1])
                    with scenario:
                        st.markdown(f"**{row['scenario']}**")
                        primary_caption(f"Chi {money(row['cost'])}/tháng · Tiết kiệm {money(row['monthly'])}/tháng")
                    with duration:
                        st.metric("Thời gian", f"{months} tháng" if months is not None else "Chưa thể đạt")
                        if months is not None and base is not None and months != base:
                            st.caption(f"{months - base:+d} tháng so với giữ nguyên")
            st.caption("Nếu đã đủ mục tiêu, thời gian bằng 0. Nếu chưa đủ và mức tiết kiệm không dương, mục tiêu chưa thể đạt với giả định này.")
            st.markdown("**Cách tính**")
            st.caption("Số tiền còn thiếu ÷ số tiền tiết kiệm mỗi tháng, làm tròn lên. Kết quả dùng để tham khảo và không bao gồm lãi suất.")
except (ApiError, MLContractError):
    st.error("Không tải được dữ liệu hoặc dữ liệu trả về không hợp lệ. Vui lòng kiểm tra và thử lại.")
    if st.button("Thử lại"): st.rerun()
