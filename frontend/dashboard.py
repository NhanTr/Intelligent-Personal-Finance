from datetime import timedelta


def compare_periods(client, user, end, granularity):
    """Compare the calendar period through end with the prior full period."""
    if granularity == "Tuần":
        current_start = end - timedelta(days=end.weekday())
        previous_start = current_start - timedelta(days=7)
    elif granularity == "Tháng":
        current_start = end.replace(day=1)
        previous_start = (current_start - timedelta(days=1)).replace(day=1)
    else:
        raise ValueError(f"Đơn vị kỳ không hỗ trợ: {granularity}")

    def period(label, start, finish):
        stats = client.get_stats(user, {"from": str(start), "to": str(finish)})
        return {"label": label, "range": f"{start:%d/%m/%Y} – {finish:%d/%m/%Y}", **stats}

    previous = period("Kỳ trước", previous_start, current_start - timedelta(days=1))
    current = period("Kỳ này", current_start, end)
    return previous, current
