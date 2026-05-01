import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
import time

# --- 0. 定数設定 ---
TRIAL_TICKET_DAYS = 7     # 初回無料チケット
TICKET_2WK_DAYS = 14      # メダル交換用チケット
MEDAL_COST_2WK = 10000    # 必要メダル数
SUMMER_PRICE = 500
WINTER_PRICE = 2000

# --- 1. ページ構成・接続 ---
st.set_page_config(page_title="Ski-Fit AI", layout="wide", page_icon="⛄")
conn = st.connection("gsheets", type=GSheetsConnection)



def get_users():
    return conn.read(worksheet="Users", ttl=0)

def get_config():
    return conn.read(worksheet="Config", ttl=0)

# --- 2. 日付・季節判定 ---
now = datetime.now()
is_summer = 6 <= now.month <= 10

# --- 3. ログイン・セッション管理 ---
if 'user' not in st.session_state:
    st.title("⛄ Ski-Fit AI へようこそ！")
    df_u = get_users()
    tab_log, tab_reg = st.tabs(["ログイン", "新しく登録する"])

    with tab_reg:
        new_u = st.text_input("お名前（ひらがな）")
        new_p = st.text_input("パスワード", type="password")
        new_b = st.date_input("お誕生日", min_value=datetime(2010, 1, 1))
        if st.button("登録してチケットをもらう！"):
            if new_u in df_u['username'].values:
                st.error("その名前はもう使われているよ。")
            else:
                new_row = pd.DataFrame([{
                    "username": new_u, "password": new_p, "medals": 0,
                    "birthday": new_b.strftime("%m-%d"), "plan": "Free",
                    "ticket_inventory": 1, "is_first_login": True, "premium_until": ""
                }])
                conn.update(worksheet="Users", data=pd.concat([df_u, new_row], ignore_index=True))
                st.success("登録できたよ！ログインしてね。")

    with tab_log:
        u_in = st.text_input("お名前", key="li_u")
        p_in = st.text_input("パスワード", type="password", key="li_p")
        if st.button("ログイン"):
            user_match = df_u[(df_u['username'] == u_in) & (df_u['password'] == p_in)]
            if not user_match.empty:
                u_data = user_match.iloc[0]
                st.session_state.user = u_in
                st.session_state.medals = int(u_data['medals'])
                st.session_state.is_first_login = u_data['is_first_login']
                st.session_state.birthday = u_data['birthday']
                
                # 有効期限チェック
                is_p = u_data['plan'] == "Premium"
                if u_data['premium_until']:
                    if now <= datetime.strptime(u_data['premium_until'], "%Y-%m-%d"):
                        is_p = True
                st.session_state.plan = "Premium" if is_p else "Free"
                st.rerun()
    st.stop()

# --- 4. チュートリアル ---
if st.session_state.is_first_login:
    st.balloons()
    with st.expander("❄️ ユッキーのチュートリアル", expanded=True):
        st.write(f"### ようこそ、{st.session_state.user}ちゃん！")
        st.info("🎒もちものに『1週間無料チケット』を入れたよ！好きな時に使ってスタートしてね。")
        if st.button("わかった！"):
            df_u = get_users()
            df_u.loc[df_u['username'] == st.session_state.user, 'is_first_login'] = False
            conn.update(worksheet="Users", data=df_u)
            st.session_state.is_first_login = False
            st.rerun()

# --- 5. メインメニュー ---
st.sidebar.title(f"⛄ {st.session_state.user}")
st.sidebar.markdown(f"### 🏅 メダル: {st.session_state.medals:,} 枚")
menu = st.sidebar.radio("メニュー", ["⛷️ AIコーチング", "🎒 もちもの", "🛍️ メダルショップ", "🏔️ スキー場クイズ", "👨‍👩‍👧 親専用"])

# --- 6. 各機能の実装 ---

# A. 4段階コーチング
if menu == "⛷️ AIコーチング":
    st.title("⛷️ ユッキーの対話レッスン")
    if st.session_state.plan == "Premium":
        v_file = st.file_uploader("滑りの動画を送ってね", type=["mp4", "mov"])
        if v_file:
            st.subheader("分析レポート")
            st.write("#### ① 事実：今は少し板がハの字（プルーク）になっているよ。")
            st.chat_message("assistant", avatar="⛄").write("なんでハの字になっちゃうか、理由はわかるかな？")
            ans1 = st.text_input("ユッキーに答える", key="q1")
            
            if ans1:
                st.write("#### ③ 練習内容：次は片足を交互に浮かせて滑ってみよう！")
                st.chat_message("assistant", avatar="⛄").write("この練習をすると、どんな良いことがあると思う？")
                st.text_input("ユッキーに答える", key="q2")
    else:
        st.warning("プレミアム機能です。🎒もちものからチケットを使ってね！")

# B. もちもの (Inventory)
elif menu == "🎒 もちもの":
    st.title("🎒 キミのインベントリ")
    df_u = get_users()
    u_data = df_u[df_u['username'] == st.session_state.user].iloc[0]
    inv = int(u_data['ticket_inventory'])
    
    # 誕生月チケット自動チェック
    b_month = int(st.session_state.birthday.split("-")[0])
    if now.month == b_month:
        st.success("🎉 お誕生日おめでとう！今月は特別チケットが使えるよ！")

    st.metric("もっているチケット", f"{inv} 枚")
    if inv > 0 and st.button("チケットを1枚使って7日間プレミアムにする"):
        expiry = (now + timedelta(days=7)).strftime("%Y-%m-%d")
        df_u.loc[df_u['username'] == st.session_state.user, 'ticket_inventory'] = inv - 1
        df_u.loc[df_u['username'] == st.session_state.user, 'premium_until'] = expiry
        conn.update(worksheet="Users", data=df_u)
        st.success(f"スタート！ {expiry} まで使い放題だよ！")
        time.sleep(2)
        st.rerun()

# C. メダルショップ
elif menu == "🛍️ メダルショップ":
    st.title("🛍️ メダルショップ")
    st.subheader("💎 目玉アイテム")
    if st.button(f"🎫 2週間無料チケット (🏅{MEDAL_COST_2WK:,}枚)"):
        if st.session_state.medals >= MEDAL_COST_2WK:
            df_u = get_users()
            current_inv = int(df_u.loc[df_u['username'] == st.session_state.user, 'ticket_inventory'])
            df_u.loc[df_u['username'] == st.session_state.user, 'medals'] = st.session_state.medals - MEDAL_COST_2WK
            df_u.loc[df_u['username'] == st.session_state.user, 'ticket_inventory'] = current_inv + 1
            conn.update(worksheet="Users", data=df_u)
            st.balloons()
            st.success("チケットを交換したよ！🎒もちものを見てね。")
        else:
            st.error("メダルが足りないよ！")

# D. スキー場クイズ
elif menu == "🏔️ スキー場クイズ":
    st.title("🏔️ 1日1回！スキー場クイズ")
    # ここにクイズ10問を実装。正解数 score を取得
    score = 0 
    st.write("（※クイズ10問回答後...）")
    if st.button("クイズを完了してメダルをもらう"):
        # 実際にはクイズ回答ロジックを挟む
        df_u = get_users()
        df_u.loc[df_u['username'] == st.session_state.user, 'medals'] = st.session_state.medals + score
        conn.update(worksheet="Users", data=df_u)
        st.success(f"メダルを {score} 枚ゲットしたよ！")

# E. 親専用（支払い・管理）
elif menu == "👨‍👩‍👧 親専用":
    st.title("👨‍👩‍👧 保護者ページ")
    price = SUMMER_PRICE if is_summer else WINTER_PRICE
    st.write(f"現在のプラン: **{st.session_state.plan}**")
    st.write(f"この時期の料金: **月額 {price}円**")
    st.button(f"サブスクリプションを申し込む（月額 {price}円）")

# --- 7. 管理者ページ ---
if st.query_params.get("page") == "admin":
    st.title("🔐 管理パネル")
    if st.text_input("管理パスワード", type="password") == "interest2024":
        df_c = get_config()
        # ショップ商品、スキー場ニュースなどを編集
        new_items = st.text_area("ショップ商品(名前,メダル)", value=df_c.loc[df_c['key']=='shop_items', 'value'].values[0])
        if st.button("保存"):
            df_c.loc[df_c['key'] == 'shop_items', 'value'] = new_items
            conn.update(worksheet="Config", data=df_c)
            st.success("保存したよ！")
    st.stop()
