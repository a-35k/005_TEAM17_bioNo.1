import streamlit as st
import pandas as pd
import pydeck as pdk

# -----------------------------
# 페이지 설정
# -----------------------------
st.set_page_config(
    page_title="농축산물별 수입 국가 분석 프로그램",
    layout="wide"
)

# -----------------------------
# 카테고리 / 색상 설정
# -----------------------------
FOOD_CATEGORIES = {
    "육류": ["돼지고기", "소고기"],
    "과일": ["망고", "오렌지", "바나나", "포도"],
    "채소": ["당근", "감자", "브로콜리"],
    "어류": ["연어", "고등어"],
    "주류": ["맥주", "위스키", "와인"]
}

CATEGORY_COLORS = {
    "육류": "#ef4444",
    "과일": "#f59e0b",
    "채소": "#10b981",
    "어류": "#3b82f6",
    "주류": "#8b5cf6"
}

ITEM_TO_CATEGORY = {}
for category, items in FOOD_CATEGORIES.items():
    for item in items:
        ITEM_TO_CATEGORY[item] = category

# -----------------------------
# 국가 좌표
# -----------------------------
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
    "남아프리카공화국": [-30.5595, 22.9375],
    "벨기에": [50.5039, 4.4699],
    "스코틀랜드": [56.4907, -4.2026],
    "아일랜드": [53.1424, -7.6921]
}

# -----------------------------
# CSS 스타일
# -----------------------------
st.markdown("""
<style>
div.stButton > button {
    width: 100%;
    border-radius: 12px;
    border: 1px solid #d1d5db;
    padding: 0.6rem 0.8rem;
    font-weight: 700;
    transition: all 0.2s ease-in-out;
    background-color: #ffffff;
    color: #111827;
}

div.stButton > button:hover {
    border: 1px solid #111827;
    background-color: #f3f4f6;
    color: #111827;
    transform: translateY(-1px);
}

.selected-box {
    padding: 14px 18px;
    border-radius: 14px;
    margin: 10px 0 18px 0;
    color: white;
    font-size: 18px;
    font-weight: bold;
    box-shadow: 0 4px 10px rgba(0,0,0,0.12);
}

.category-title {
    padding: 8px 14px;
    border-radius: 10px;
    color: white;
    font-weight: 800;
    margin-top: 16px;
    margin-bottom: 8px;
    display: inline-block;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# 유틸 함수
# -----------------------------
def load_csv(uploaded_file):
    encodings = ["utf-8", "utf-8-sig", "cp949"]
    for enc in encodings:
        try:
            uploaded_file.seek(0)
            return pd.read_csv(uploaded_file, encoding=enc)
        except Exception:
            continue
    return None

def get_value_column(df):
    if "수입금액" in df.columns:
        return "수입금액"
    if "수입중량" in df.columns:
        return "수입중량"
    return None

def validate_columns(df):
    value_col = get_value_column(df)
    required = ["품목", "국가"]

    for col in required:
        if col not in df.columns:
            return False, value_col

    if value_col is None:
        return False, value_col

    return True, value_col

def get_top5_by_food(df, food, value_col):
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

def value_to_red_color(value, min_value, max_value):
    if max_value == min_value:
        red = 200
        green_blue = 80
    else:
        ratio = (value - min_value) / (max_value - min_value)
        red = int(180 + ratio * 75)          # 180 ~ 255
        green_blue = int(200 - ratio * 180)  # 200 ~ 20

    return [red, green_blue, green_blue, 220]

def prepare_map_data(top5_df, value_col):
    rows = []

    if top5_df.empty:
        return pd.DataFrame()

    max_value = top5_df[value_col].max()
    min_value = top5_df[value_col].min()

    for _, row in top5_df.iterrows():
        country = row["국가"]
        if country in COUNTRY_COORDS:
            lat, lon = COUNTRY_COORDS[country]

            if max_value == min_value:
                radius = 450000
            else:
                ratio = (row[value_col] - min_value) / (max_value - min_value)
                radius = int(250000 + ratio * 350000)

            rows.append({
                "국가": country,
                "lat": lat,
                "lon": lon,
                "순위": int(row["순위"]),
                "값": row[value_col],
                "color": value_to_red_color(row[value_col], min_value, max_value),
                "radius": radius
            })

    return pd.DataFrame(rows)

def show_raw_data(df):
    with st.expander("원본 파일 미리보기"):
        st.dataframe(df.head(10), use_container_width=True)

def show_food_buttons():
    st.subheader("품목 선택")

    if "selected_food" not in st.session_state:
        st.session_state.selected_food = None

    for category, items in FOOD_CATEGORIES.items():
        color = CATEGORY_COLORS.get(category, "#6b7280")

        st.markdown(
            f'<div class="category-title" style="background-color:{color};">{category}</div>',
            unsafe_allow_html=True
        )

        cols = st.columns(len(items))
        for i, item in enumerate(items):
            with cols[i]:
                if st.button(item, key=f"btn_{category}_{item}", use_container_width=True):
                    st.session_state.selected_food = item

    return st.session_state.selected_food

def show_selected_food(food):
    if not food:
        return

    category = ITEM_TO_CATEGORY.get(food, "기타")
    color = CATEGORY_COLORS.get(category, "#6b7280")

    st.markdown(
        f'<div class="selected-box" style="background-color:{color};">선택된 품목: {food} ({category})</div>',
        unsafe_allow_html=True
    )

def show_top5_text(top5_df, value_col):
    if top5_df.empty:
        st.warning("선택한 품목에 대한 데이터가 없습니다.")
        return

    st.subheader("상위 5개 수입 국가")

    for _, row in top5_df.iterrows():
        st.write(f"{row['순위']}위 · {row['국가']} · {value_col}: {row[value_col]}")

    show_df = top5_df[["순위", "국가", value_col]].copy()
    st.dataframe(show_df, use_container_width=True)

def show_world_map(map_df):
    st.subheader("세계지도 시각화")

    if map_df.empty:
        st.warning("지도에 표시할 국가 좌표 데이터가 없습니다.")
        return

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=map_df,
        get_position="[lon, lat]",
        get_fill_color="color",
        get_radius="radius",
        pickable=True,
        opacity=0.85,
        stroked=True,
        get_line_color=[80, 0, 0, 180],
        line_width_min_pixels=1
    )

    view_state = pdk.ViewState(
        latitude=20,
        longitude=0,
        zoom=1,
        min_zoom=1,
        max_zoom=10
    )

    tooltip = {
        "html": """
        <b>국가:</b> {국가}<br/>
        <b>순위:</b> {순위}위<br/>
        <b>값:</b> {값}
        """,
        "style": {
            "backgroundColor": "rgba(0, 0, 0, 0.75)",
            "color": "white",
            "borderRadius": "8px"
        }
    }

    deck = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip=tooltip,
        map_style="light"
    )

    st.pydeck_chart(deck, use_container_width=True)
    st.caption("진한 빨강일수록 수입값이 큰 국가입니다.")

# -----------------------------
# 메인
# -----------------------------
def main():
    st.title("농축산물별 수입 국가 분석 프로그램")
    st.write("CSV 파일을 업로드한 뒤, 식품군별 버튼에서 품목을 선택하면 상위 수입 국가와 지도를 확인할 수 있습니다.")

    uploaded_file = st.file_uploader("CSV 파일 업로드", type=["csv"])

    if uploaded_file is None:
        st.info("샘플 CSV 또는 직접 만든 CSV 파일을 업로드해 주세요.")
        return

    df = load_csv(uploaded_file)

    if df is None:
        st.error("CSV 파일을 읽지 못했습니다. 파일 인코딩(utf-8, utf-8-sig, cp949)을 확인해 주세요.")
        return

    valid, value_col = validate_columns(df)
    if not valid:
        st.error("필수 컬럼이 없습니다. '품목', '국가', 그리고 '수입금액' 또는 '수입중량' 컬럼이 필요합니다.")
        st.write("현재 컬럼:", list(df.columns))
        return

    show_raw_data(df)

    selected_food = show_food_buttons()
    show_selected_food(selected_food)

    if selected_food is None:
        st.info("분석할 품목 버튼을 눌러 주세요.")
        return

    top5_df = get_top5_by_food(df, selected_food, value_col)
    show_top5_text(top5_df, value_col)

    map_df = prepare_map_data(top5_df, value_col)
    show_world_map(map_df)

if __name__ == "__main__":
    main()