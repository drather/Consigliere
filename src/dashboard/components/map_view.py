"""
render_map_view — folium map component for apartment transaction data.
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
