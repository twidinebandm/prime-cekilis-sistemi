import streamlit as st
import pandas as pd
import re
import requests

# --- GÜVENLİK ---
try:
    ACCESS_TOKEN = st.secrets["ACCESS_TOKEN"]
except:
    st.stop()

st.set_page_config(page_title="Prime - Denetim Paneli", layout="wide")

# --- YARDIMCI FONKSİYONLAR ---
def get_mentions(text):
    if pd.isna(text): return []
    return list(set(re.findall(r'@([\w\.]+)', str(text).lower())))

def verify_active_profile(username):
    headers = {"User-Agent": "Mozilla/5.0"}
    url = f"https://www.instagram.com/{username}/"
    try:
        r = requests.get(url, headers=headers, timeout=5)
        return "✅ Aktif" if r.status_code == 200 else "❌ Pasif/404"
    except:
        return "⚠️ Kontrol Edilemedi"

# --- ARAYÜZ ---
st.title("⚖️ Çekiliş Denetim Sistemi")

with st.sidebar:
    st.header("📁 Gerekli Dokümanlar")
    u2_file = st.file_uploader("1. U2 Sonuç Listesi (SONUÇLAR...)", type=['xlsx'])
    form_file = st.file_uploader("2. Başvuru Formu (Yanıtlar...)", type=['xlsx'])
    comment_file = st.file_uploader("3. Sociality Yorum Listesi", type=['xlsx'])
    post_url = st.text_input("Beğeni Kontrolü İçin Post Linki")

if u2_file and form_file and comment_file:
    # Verileri Oku
    df_u2 = pd.read_excel(u2_file, header=0) # D sütunu kullanıcı adı
    df_form = pd.read_excel(form_file) # C sütunu kullanıcı adı
    df_comm = pd.read_excel(comment_file) # C sütunu kullanıcı adı

    st.subheader("📋 U2 Listesi Denetim Raporu")
    
    denetim_rows = []
    # U2 Listesindeki her talihli için döngü (D sütunu = df_u2.columns[3])
    for index, row in df_u2.iterrows():
        u2_user = str(row.iloc[3]).lower().strip() if not pd.isna(row.iloc[3]) else "BELİRTİLMEMİŞ"
        hediye_tipi = str(row.iloc[0]) # A sütunu hediye/asil-yedek bilgisi
        
        # 1. FORM KONTROLÜ (Tam Eşleşme)
        # Formda C sütunu = df_form.columns[2]
        form_match = df_form[df_form.iloc[:, 2].str.lower().str.strip() == u2_user]
        has_form = not form_match.empty
        
        # 2. YORUM VE ETİKET KONTROLÜ
        # Sociality C sütunu = df_comm.columns[2], E sütunu = df_comm.columns[4]
        user_comm = df_comm[df_comm.iloc[:, 2].str.lower().str.strip() == u2_user]
        has_3_mentions = False
        if not user_comm.empty:
            mentions = get_mentions(user_comm.iloc[0, 4])
            if len(mentions) >= 3:
                has_3_mentions = True

        # 3. DURUM BELİRLEME
        if u2_user == "BELİRTİLMEMİŞ":
            final_status = "BOŞ SATIR"
        elif not has_form:
            final_status = "ELENDİ: Başvuru Formu Kaydı Yok / Hatalı Yazım"
        elif not has_3_mentions:
            final_status = "ELENDİ: Yorumda 3 Etiket Şartı Sağlanmadı"
        else:
            final_status = "GEÇERLİ"

        denetim_rows.append({
            "Hediye/Durum": hediye_tipi,
            "Kullanıcı Adı (U2)": u2_user,
            "Form Kaydı": "✅ Var" if has_form else "❌ Yok",
            "3 Etiket": "✅ Tamam" if has_3_mentions else "❌ Eksik",
            "DENETİM SONUCU": final_status
        })

    result_df = pd.DataFrame(denetim_rows)
    st.dataframe(result_df, use_container_width=True)

    # Raporu İndir
    csv = result_df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Denetim Raporunu Excel Olarak İndir", data=csv, file_name="MPI_Denetim_Raporu.csv")

else:
    st.warning("Lütfen denetimi başlatmak için tüm dosyaları yükleyin.")
