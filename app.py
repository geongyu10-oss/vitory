import streamlit as st
import pandas as pd
import soccerdata as sd
import re
from pathlib import Path

# Streamlit Cloud의 설치 패키지 폴더는 쓰기 권한이 없을 수 있으므로
# SeleniumBase 드라이버와 soccerdata 캐시를 쓰기 가능한 /tmp로 이동합니다.
DRIVER_DIR = Path("/tmp/seleniumbase_drivers")
DATA_DIR = Path("/tmp/soccerdata_fbref")
DRIVER_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

try:
    from seleniumbase.core import browser_launcher
    browser_launcher.override_driver_dir(str(DRIVER_DIR))
except (ImportError, AttributeError):
    # SeleniumBase 버전에 따라 override 기능이 없을 수 있습니다.
    pass

st.set_page_config(page_title="유럽 5대 리그 선수 기록 분석", page_icon="⚽", layout="wide")
st.title("⚽ 유럽 5대 리그 선수 시즌 기록 분석")
st.write("선수 이름과 시즌을 입력하면 FBref의 공개 시즌 통계를 찾아 보여줍니다.")

def flatten_columns(df):
    result = df.copy()
    if isinstance(result.columns, pd.MultiIndex):
        result.columns = [
            " ".join(str(x) for x in col if str(x) not in ("", "nan", "None")).strip()
            for col in result.columns.to_list()
        ]
    else:
        result.columns = [str(c) for c in result.columns]
    return result

@st.cache_data(ttl=86400, show_spinner=False)
def load_big5_season(season_text):
    reader = sd.FBref(
        leagues=["Big 5 European Leagues Combined"],
        seasons=[season_text],
        data_dir=DATA_DIR,
        headless=True,
    )
    frame = reader.read_player_season_stats(stat_type="standard")
    frame = frame.reset_index()
    return flatten_columns(frame)

def find_column(columns, candidates):
    for candidate in candidates:
        for col in columns:
            if str(col).strip().lower() == candidate.lower():
                return col
    for candidate in candidates:
        for col in columns:
            if candidate.lower() in str(col).lower():
                return col
    return None

def shown(value):
    return "-" if pd.isna(value) else str(value)

with st.form("search_form"):
    col1, col2 = st.columns(2)
    with col1:
        player_query = st.text_input("선수 이름", placeholder="예: Son Heung-Min")
    with col2:
        season_query = st.text_input("시즌", value="2022-2023", placeholder="예: 2022-2023")
    submitted = st.form_submit_button("시즌 기록 검색", type="primary", use_container_width=True)

st.caption("선수 이름은 영문 입력을 권장합니다. 시즌은 2022-2023처럼 입력하세요.")

if submitted:
    season_query = season_query.strip()
    if not player_query.strip():
        st.error("선수 이름을 입력해 주세요.")
    elif not re.fullmatch(r"\d{4}[-/]\d{2,4}", season_query):
        st.error("시즌을 2022-2023 형식으로 입력해 주세요.")
    else:
        try:
            with st.spinner("FBref에서 시즌 기록을 불러오는 중입니다. 첫 조회는 시간이 걸릴 수 있습니다."):
                df = load_big5_season(season_query)

            player_col = find_column(df.columns, ["player"])
            if player_col is None:
                st.error("자료에서 선수 이름 항목을 찾지 못했습니다.")
            else:
                query = player_query.strip().casefold()
                player_names = df[player_col].fillna("").astype(str)
                matches = df[player_names.str.casefold().str.contains(re.escape(query), na=False)].copy()

                if matches.empty:
                    st.warning("해당 시즌에서 선수를 찾지 못했습니다. 영문 이름을 확인해 주세요.")
                else:
                    matches["_player_label"] = matches[player_col].astype(str)
                    choices = matches["_player_label"].drop_duplicates().tolist()
                    chosen_name = st.selectbox("검색된 선수 선택", choices)
                    selected = matches[matches["_player_label"] == chosen_name]

                    league_col = find_column(selected.columns, ["league", "comp"])
                    team_col = find_column(selected.columns, ["team", "squad"])

                    st.subheader(f"{chosen_name} · {season_query} 시즌")
                    for index, (_, row) in enumerate(selected.iterrows()):
                        league = shown(row[league_col]) if league_col else "유럽 5대 리그"
                        team = shown(row[team_col]) if team_col else "-"
                        st.markdown(f"### {league} · {team}")

                        stat_fields = [
                            ("출전 경기", ["MP"]),
                            ("선발 출전", ["Starts"]),
                            ("출전 시간", ["Min"]),
                            ("골", ["Gls"]),
                            ("도움", ["Ast"]),
                            ("골+도움", ["G+A"]),
                        ]
                        metric_cols = st.columns(3)
                        for i, (label, keys) in enumerate(stat_fields):
                            stat_col = find_column(selected.columns, keys)
                            value = shown(row[stat_col]) if stat_col else "-"
                            metric_cols[i % 3].metric(label, value)

                        extra_fields = [
                            ("출전 경기", ["MP"]), ("선발 출전", ["Starts"]),
                            ("출전 시간(분)", ["Min"]), ("90분 환산", ["90s"]),
                            ("골", ["Gls"]), ("도움", ["Ast"]), ("골+도움", ["G+A"]),
                            ("페널티킥 골", ["PK"]), ("경고", ["CrdY"]), ("퇴장", ["CrdR"]),
                        ]
                        table_rows = []
                        for label, keys in extra_fields:
                            col = find_column(selected.columns, keys)
                            if col:
                                table_rows.append((label, shown(row[col])))
                        table = pd.DataFrame(table_rows, columns=["기록 항목", "시즌 기록"])
                        st.dataframe(table, hide_index=True, use_container_width=True)
                        st.download_button(
                            "기록 CSV 다운로드",
                            table.to_csv(index=False).encode("utf-8-sig"),
                            file_name=f"player_{season_query}_{index+1}.csv",
                            mime="text/csv",
                            key=f"csv_{index}",
                        )

        except PermissionError as exc:
            st.error("브라우저 드라이버 파일 권한 오류가 계속 발생했습니다.")
            st.code(str(exc))
            st.info("Streamlit 앱을 재부팅한 뒤 다시 시도해 주세요. 그래도 같으면 오류 전문을 보내 주세요.")
        except Exception as exc:
            st.error("FBref 자료를 불러오지 못했습니다.")
            st.caption(f"오류 종류: {type(exc).__name__}")
            st.code(str(exc))
            st.info("FBref 접속 제한, 데이터가 없는 시즌, 라이브러리 호환성 문제일 수 있습니다.")

with st.expander("자료 출처 및 안내"):
    st.markdown("""
    - 자료 출처: [FBref 유럽 5대 리그 통계](https://fbref.com/en/comps/Big5/)
    - 수집 도구: [soccerdata](https://soccerdata.readthedocs.io/)
    - 검색 범위: 프리미어리그, 라리가, 분데스리가, 세리에 A, 리그 1
    - 첫 조회는 자료를 내려받으므로 시간이 걸릴 수 있습니다.
    - 자료가 없는 선수·시즌은 검색되지 않을 수 있습니다.
    """)
