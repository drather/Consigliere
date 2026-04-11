"""
render_map_view — folium map component for apartment transaction data.
render_master_map_view — Tab5 전용: 마스터 단지 목록 기준 지도 렌더링.
"""
from __future__ import annotations

import pandas as pd
import folium


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

    Parameters
    ----------
    df : pd.DataFrame
        Columns: apt_name, district_code, deal_date, price, exclusive_area, floor
    geocoder : GeocoderService
        Instance with batch_geocode() method.

    Returns
    -------
    folium.Map
    """
    fmap = folium.Map(location=[37.5665, 126.9780], zoom_start=11)

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
        ).add_to(fmap)

    return fmap


def _build_master_popup_html(master, transactions: pd.DataFrame) -> str:
    """Tab5 전용: 단지 기본정보 + 실거래가 이력 팝업 HTML.

    Parameters
    ----------
    master : ApartmentMaster
    transactions : pd.DataFrame
        해당 단지의 거래 rows. 빈 DataFrame 허용.
    """
    year = (
        master.approved_date[:4]
        if master.approved_date and len(master.approved_date) >= 4
        else "-"
    )
    addr = master.road_address or master.legal_address or ""

    lines: list[str] = [f"<b>{master.apt_name}</b>"]
    if addr:
        lines.append(f"<br><small>{addr}</small>")
    lines.append("<hr>")
    lines.append(
        f"세대수: {master.household_count:,}세대 &nbsp;|&nbsp; "
        f"준공: {year}년 &nbsp;|&nbsp; "
        f"건설사: {master.constructor or '-'}"
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
    """Tab5 전용: 마스터 단지 목록 기준으로 마커를 그리고,
    각 단지의 실거래가 이력을 팝업으로 표시한다.

    Parameters
    ----------
    masters : List[ApartmentMaster]
        ApartmentMasterRepository.search() 결과
    transactions_df : pd.DataFrame
        복수 단지의 거래 합산 DataFrame. 빈 DataFrame 허용.
        컬럼: apt_name, district_code, deal_date, price, exclusive_area, floor
    geocoder : GeocoderProtocol
        batch_geocode() 메서드를 가진 지오코딩 서비스

    Returns
    -------
    folium.Map
    """
    fmap = folium.Map(location=[37.5665, 126.9780], zoom_start=11)

    if not masters:
        return fmap

    apt_keys = [
        {"apt_name": m.apt_name, "district_code": m.district_code}
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
            apt_txns = transactions_df[
                (transactions_df["apt_name"] == m.apt_name)
                & (transactions_df["district_code"] == m.district_code)
            ]
        else:
            apt_txns = pd.DataFrame()

        popup_html = _build_master_popup_html(m, apt_txns)
        has_transactions = not apt_txns.empty

        folium.Marker(
            location=[lat, lng],
            popup=folium.Popup(popup_html, max_width=380),
            tooltip=f"{m.apt_name} ({m.household_count:,}세대)",
            icon=folium.Icon(
                color="blue" if has_transactions else "gray",
                icon="home",
                prefix="fa",
            ),
        ).add_to(fmap)

    return fmap
