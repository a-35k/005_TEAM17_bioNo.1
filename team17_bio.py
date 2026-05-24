import streamlit as st
import pandas as pd
import pydeck as pdk

# 페이지 기본 설정
st.set_page_config(page_title="농축산물별 수입 국가 분석 프로그램", layout="wide")

# 분석 대상 식품 목록
FOOD_CATEGORIES = {
    "육류": ["돼지고기", "소고기"],
    "과일": ["망고", "사과", "바나나", "포도"],
    "채소": ["당근", "감자", "브로콜리"],
    "어류": ["연어", "고등어"],
    "주류": ["맥주", "양주", "와인"]
}

# 국가명-좌표 매핑
COUNTRY_COORDS = {
    "미국": [37.0902, -95.7129],
    "중국": [35.8617, 104.1954],
    "일본": [36.2048, 138.2529],
    "호주": [-25.2744, 133.7751],
    "칠레": [-35.6751, -71.5430],
    "베트남": [14.0583, 108.2772],
    "태국": [15.8700, 100.9925],
    "필리핀": [12.8797, 121.7740],
    "뉴질랜드": [-40.9006, 174.8860],
    "캐나다": [56.1304, -106.3468],
    "독일": [51.1657, 10.4515],
    "프랑스": [46.2276, 2.2137],
    "이탈리아": [41.8719, 12.5674],
    "스페인": [40.4637, -3.7492],
    "노르웨이": [60.4720, 8.4689],
    "러시아": [61.5240, 105.3188],
    "브라질": [-14.2350, -51.9253],
    "멕시코": [23.6345, -102.5528],
    "아르헨티나": [-38.4161, -63.6167],
    "남아프리카공화국": [-30.5595, 22.9375]
}


def load_csv(uploaded_file):
    """
    업로드된 CSV 파일을 인코딩 문제를 고려하여 읽는 함수
    utf-8, utf-8-sig, cp949 순으로 시도
    """
    encodings = ["utf-8", "utf-8-sig", "cp949"]
    for enc in encodings:
        try:
            uploaded_file.seek(0)
            return pd.read_csv(uploaded_file, encoding=enc)
        except Exception:
            continue
    return None


def get_value_column(df):
    """
    수입 집계 기준 컬럼을 찾는 함수
    우선순위: 수입금액 -> 수입중량
    """
    if "수입금액" in df.columns:
        return "수입금액"
    if "수입중량" in df.columns:
        return "수입중량"
    return None


def validate_columns(df):
    """
    필수 컬럼 존재 여부를 확인하는 함수
    """
    value_col = get_value_column(df)
    required = ["품목", "국가"]
    for col in required:
        if col not in df.columns:
            return False, value_col
    if value_col is None:
        return False, value_col
    return True, value_col


def get_top5_by_food(df, food, value_col):
    """
    선택한 품목의 국가별 수입 상위 5개국을 반환하는 함수
    """
    filtered = df[df["품목"] == food].copy()
    if filtered.empty:
        return pd.DataFrame()

    result = (
        filtered.groupby("국가", as_index=False)[value_col]
        .sum()
        .sort_values(by=value_col, ascending=False)
        .head(5)
        .reset_index(drop=True)
    )
    result["순위"] = result.index + 1
    return result


def map_rank_to_color(rank):
    """
    순위별 색상과 진하기를 지정하는 함수
    1위가 가장 진하고 5위가 가장 연함
    """
    color_map = {
        1: [180, 0, 0, 220],
        2: [220, 50, 50, 200],
        3: [240, 100, 100, 180],
        4: [255, 150, 150, 160],
        5: [255, 200, 200, 140]
    }
    return color_map.get(rank, [150, 150, 150, 120])


def prepare_map_data(top5_df, value_col):
    """
    지도 시각화를 위한 좌표 및 색상 데이터를 생성하는 함수
    """
    rows = []
    for _, row in top5_df.iterrows():
        country = row["국가"]
        if country in COUNTRY_COORDS:
            lat, lon = COUNTRY_COORDS[country]
            rows.append({
                "국가": country,
                "lat": lat,
                "lon": lon,
                "순위": row["순위"],
                "값": row[value_col],
                "color": map_rank_to_color(row["순위"]),
                "radius": 300000 + (6 - row["순위"]) * 80000
            })
    return pd.DataFrame(rows)


def show_raw_data(df):
    """
    업로드한 원본 데이터의 상위 5개 행을 접었다 펼 수 있게 표시하는 함수
    """
    with st.expander("원본 파일 내용 확인"):
        st.dataframe(df.head(5), use_container_width=True)


def show_food_selector():
    """
    식품 목록 선택 UI를 생성하는 함수
    """
    food_list = []
    for category, items in FOOD_CATEGORIES.items():
        food_list.extend(items)
    return st.selectbox("식품 목록 선택", food_list)


def show_top5_text(top5_df, value_col):
    """
    상위 5개국 결과를 텍스트와 표로 출력하는 함수
    """
    if top5_df.empty:
        st.warning("선택한 품목에 대한 데이터가 없습니다.")
        return

    st.subheader("상위 5개 수입 국가")
    for _, row in top5_df.iterrows():
        st.write(f"{row['순위']}위: {row['국가']} ({value_col}: {row[value_col]})")

    st.dataframe(top5_df[["순위", "국가", value_col]], use_container_width=True)


def show_world_map(map_df):
    """
    세계지도 위에 국가별 수입 분포를 표시하는 함수
    """
    if map_df.empty:
        st.warning("지도에 표시할 국가 좌표 데이터가 없습니다.")
        return

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=map_df,
        get_position='[lon, lat]',
        get_fill_color='color',
        get_radius='radius',
        pickable=True
    )

    view_state = pdk.ViewState(
        latitude=20,
        longitude=0,
        zoom=1.2,
        min_zoom=1,
        max_zoom=10
    )

    tooltip = {
        "html": "<b>국가:</b> {국가}<br/><b>순위:</b> {순위}위<br/><b>값:</b> {값}",
        "style": {"backgroundColor": "white", "color": "black"}
    }

    st.pydeck_chart(pdk.Deck(
        map_style="mapbox://styles/mapbox/light-v9",
        initial_view_state=view_state,
        layers=[layer],
        tooltip=tooltip
    ))


def main():
    """
    메인 실행 함수
    """
    st.title("농축산물별 수입 국가 분석 프로그램")

    uploaded_file = st.file_uploader("CSV 파일 업로드", type=["csv"])

    if uploaded_file is None:
        st.info("CSV 파일을 업로드해 주세요.")
        return

    df = load_csv(uploaded_file)

    if df is None:
        st.error("CSV 파일을 읽을 수 없습니다. 인코딩 또는 파일 형식을 확인해 주세요.")
        return

    valid, value_col = validate_columns(df)
    if not valid:
        st.error("필수 컬럼이 없습니다. '품목', '국가', 그리고 '수입금액' 또는 '수입중량' 컬럼이 필요합니다.")
        return

    show_raw_data(df)

    selected_food = show_food_selector()

    top5_df = get_top5_by_food(df, selected_food, value_col)
    show_top5_text(top5_df, value_col)

    map_df = prepare_map_data(top5_df, value_col)
    st.subheader("세계지도 시각화")
    show_world_map(map_df)


if __name__ == "__main__":
    main()