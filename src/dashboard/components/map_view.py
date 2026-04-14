"""
render_map_view — folium map component for apartment transaction data.
render_master_map_view — Tab5 전용: 마스터 단지 목록 기준 지도 렌더링.
"""
from __future__ import annotations

import pandas as pd
import folium


from folium.plugins import MarkerCluster

def _format_price(price: int) -> str:
    """Convert integer KRW price to '억 만원' string format."""
    eok = price // 100_000_000
    remainder = (price % 100_000_000) // 10_000  # in 만원 units

    if eok > 0 and remainder > 0:
        return f"{eok}억 {remainder:,}만원"
    elif eok > 0:
        return f"{eok}억"
    else:
        return f"{remainder:,}만원"


def _build_popup_html(apt_name: str, transactions: pd.DataFrame) -> str:
    """Build popup HTML with apt name and sorted transaction history."""
    rows_sorted = transactions.sort_values("deal_date", ascending=False)

    lines = [f"<b>{apt_name}</b><br><hr>"]
    for _, row in rows_sorted.iterrows():
        deal_date = row.get("deal_date", "")
        area = row.get("exclusive_area", "")
        price = row.get("price", 0)
        price_str = _format_price(int(price))
        lines.append(f"{deal_date} | {area}㎡ | {price_str}<br>")

    return "".join(lines)


def render_map_view(df: pd.DataFrame, geocoder) -> folium.Map:
    """
    Render a folium map with one marker per unique apartment.
    """
    fmap = folium.Map(location=[37.5665, 126.9780], zoom_start=11)
    marker_cluster = MarkerCluster().add_to(fmap)

    if df.empty:
        return fmap

    # Build unique apt list
    unique_apts = (
        df[["apt_name", "district_code"]]
        .drop_duplicates()
        .to_dict(orient="records")
    )

    coords_map = geocoder.batch_geocode(unique_apts)

    for apt_info in unique_apts:
        apt_name = apt_info["apt_name"]
        district_code = apt_info["district_code"]
        cache_key = f"{district_code}__{apt_name}"

        coords = coords_map.get(cache_key)
        if coords is None:
            continue

        lat, lng = coords
        apt_txns = df[(df["apt_name"] == apt_name) & (df["district_code"] == district_code)]
        popup_html = _build_popup_html(apt_name, apt_txns)

        folium.Marker(
            location=[lat, lng],
            popup=folium.Popup(popup_html, max_width=350),
            tooltip=apt_name,
        ).add_to(marker_cluster)

    return fmap


def _build_master_popup_html(master, transactions: pd.DataFrame) -> str:
    """단지 기본정보 + 실거래가 이력 팝업 HTML.

    ApartmentMaster / AptMasterEntry 두 타입을 모두 지원 (getattr로 optional 필드 접근).
    """
    approved = getattr(master, "approved_date", "") or ""
    year = approved[:4] if len(approved) >= 4 else "-"
    addr = (getattr(master, "road_address", "") or
            getattr(master, "legal_address", "") or "")
    household = getattr(master, "household_count", 0)
    constructor = getattr(master, "constructor", "") or "-"

    lines: list[str] = [f"<b>{master.apt_name}</b>"]
    if addr:
        lines.append(f"<br><small>{addr}</small>")
    lines.append("<hr>")

    if household:
        lines.append(
            f"세대수: {household:,}세대 &nbsp;|&nbsp; "
            f"준공: {year}년 &nbsp;|&nbsp; "
            f"건설사: {constructor}"
        )
    else:
        # AptMasterEntry: tx_count 표시
        tx_count = getattr(master, "tx_count", 0)
        last_traded = getattr(master, "last_traded", "") or "-"
        lines.append(
            f"거래건수: {tx_count:,}건 &nbsp;|&nbsp; 최근거래: {last_traded}"
        )
    lines.append("<hr>")

    if transactions.empty:
        lines.append("<i style='color:gray'>저장된 거래 이력이 없습니다</i>")
    else:
        lines.append("<b>실거래가 이력</b><br>")
        rows_sorted = transactions.sort_values("deal_date", ascending=False).head(10)
        for _, row in rows_sorted.iterrows():
            price_str = _format_price(int(row.get("price", 0)))
            lines.append(
                f"{row.get('deal_date', '')} | {row.get('exclusive_area', '')}㎡ | {price_str}<br>"
            )

    return "".join(lines)


def render_master_map_view(
    masters: list,
    transactions_df: pd.DataFrame,
    geocoder,
) -> folium.Map:
    """Tab5 전용: 마스터 단지 목록 기준으로 마커를 그리고 Clustering 적용."""
    fmap = folium.Map(location=[37.5665, 126.9780], zoom_start=11)
    marker_cluster = MarkerCluster().add_to(fmap)

    if not masters:
        return fmap

    apt_keys = [
        {
            "apt_name":     m.apt_name,
            "district_code": m.district_code,
            "address": (
                getattr(m, "road_address", None) or
                getattr(m, "legal_address", None) or
                None
            ),
        }
        for m in masters
    ]
    coords_map = geocoder.batch_geocode(apt_keys)

    for m in masters:
        cache_key = f"{m.district_code}__{m.apt_name}"
        coords = coords_map.get(cache_key)
        if coords is None:
            continue

        lat, lng = coords

        if not transactions_df.empty:
            master_nm = m.apt_name.strip().lower()
            apt_txns = transactions_df[
                (transactions_df["district_code"] == m.district_code)
                & transactions_df["apt_name"].apply(
                    lambda x: x.strip().lower() in master_nm
                    or master_nm in x.strip().lower()
                )
            ]
        else:
            apt_txns = pd.DataFrame()

        popup_html = _build_master_popup_html(m, apt_txns)
        has_transactions = not apt_txns.empty

        household = getattr(m, "household_count", 0)
        tooltip_text = (
            f"{m.apt_name} ({household:,}세대)"
            if household
            else f"{m.apt_name} ({getattr(m, 'tx_count', 0)}건)"
        )
        folium.Marker(
            location=[lat, lng],
            popup=folium.Popup(popup_html, max_width=380),
            tooltip=tooltip_text,
            icon=folium.Icon(
                color="blue" if has_transactions else "gray",
                icon="home",
                prefix="fa",
            ),
        ).add_to(marker_cluster)

    return fmap
