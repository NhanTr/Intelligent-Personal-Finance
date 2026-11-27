from dataclasses import dataclass
from html import escape

import streamlit as st

from core import money


@dataclass(frozen=True)
class Share:
    percent: float


def data_table(title, columns, rows, *, numeric=(), scroll=False):
    """Render a labelled table, escaping transaction and CSV values."""
    numeric = set(numeric)
    headers = "".join(
        f'<th scope="col" class="{"numeric" if i in numeric else ""}">{escape(column)}</th>'
        for i, column in enumerate(columns)
    )
    body = []
    for row in rows:
        cells = []
        for i, value in enumerate(row):
            if isinstance(value, Share):
                percent = value.percent
                text = (
                    f'<span class="share"><span>{percent:.1f}%</span>'
                    f'<span class="share-track" aria-hidden="true">'
                    f'<span style="width:{max(0, min(100, percent)):.2f}%"></span></span></span>'
                )
            else:
                text = escape(str(value))
            if i == 0:
                cells.append(f'<th scope="row">{text}</th>')
            else:
                cells.append(f'<td class="{"numeric" if i in numeric else ""}">{text}</td>')
        body.append("<tr>" + "".join(cells) + "</tr>")
    st.markdown(
        f'<div class="table-area{" table-scroll" if scroll else ""}" role="region" aria-label="{escape(title)}" tabindex="0">'
        f'<table aria-label="{escape(title)}"><thead><tr>{headers}</tr></thead>'
        f'<tbody>{"".join(body)}</tbody></table></div>',
        unsafe_allow_html=True,
    )


def section_rule(label):
    st.markdown(f'<div class="section-rule">{escape(label)}</div>', unsafe_allow_html=True)


def primary_caption(text):
    st.markdown(f'<p class="caption-primary">{escape(text)}</p>', unsafe_allow_html=True)


def amount_change(value):
    return ("+" if value > 0 else "") + money(value)
