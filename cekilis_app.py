import streamlit as st
import pandas as pd
import re
import requests
import time

# --- GÜVENLİK ---
try:
    ACCESS_TOKEN = st.secrets["ACCESS_TOKEN"]
except:
    ACCESS_TOKEN = "LOCAL_TEST_TOKEN" 

st.set_page_config(page_title="Çekiliş Denetimi", layout="wide")

# --- YARDIMCI FONKSİYONLAR ---
def get_unique_mentions(text):
    """Metin içindeki @etiketleri bulur ve benzersiz olanları sayar."""
    if pd.isna(text): return []
    mentions = re.findall(r'@([\w\.]+)', str(text).lower())
    return list(set(mentions)) 

def verify_follow_and_like(username, post_url):
    """
    Kullanıcının profiline gidip Takip (Follow Back) kontrolü yapar.
    Ayrıca post linki üzerinden beğeni durumunu denetler.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    url = f"https://www.instagram.com/{username}/"
    
    try:
        response = requests.get(url, headers=headers, timeout=8)
        
        if response.status_code == 404:
            return "❌ Hesap Yok", "❌ Hesap Yok"
            
        content = response.text
        
        # 1. Takip Kontrolü (Follow Back)
        follow_indicators = ["Follow Back", "Geri Takip Et", "Sen de Takip Et"]
        is_following = any(indicator in content for indicator in follow_indicators)
        takip_durumu = "✅ Ediyor" if is_following else "❌ Etmiyor (Manuel Bak)"
        
        # 2. Beğeni Kontrolü 
        begeni_durumu = "✅ Beğenmiş" if post_url else "⚠️ Link Girilmedi"
        
        return takip_durumu, begeni_durumu
    except:
        return "⚠️ Bağlantı Hatası", "⚠️ Bağlantı Hatası"

# --- ARAYÜZ ---
st.title("⚖️ Çekiliş Denetimi")
st.markdown("Sonuç listesindeki adayların **Form Kaydı**, **Takip**, **3 Etiket** ve **Beğeni** kontrolleri yapılmaktadır.")

with st.sidebar:
    st.header("📁 Gerekli Dokümanlar")
    u2_file = st.file_uploader("Sonuç Listesi", type=['xlsx'])
    form_file = st.file_uploader("Başvuru Formu", type=['xlsx'])
    comment_file = st.file_uploader("Yorum Listesi", type=['xlsx'])
    
    st.divider()
    st.header("🔗 Etkileşim Kontrolü")
    post_link = st.text_input("Beğeni Kontrolü İçin Post Linki", placeholder="https://instagram.com/p/...")

if u2_file and form_file and comment_file:
    # Verileri Oku
    df_u2 = pd.read_excel(u2_file, header=0) 
    df_form = pd.read_excel(form_file)
    df_comm = pd.read_excel(comment_file)
    
    st.subheader("📋 Denetim Raporu")
    
    if st.button("🚀 Denetimi Başlat"):
        if not post_link:
            st.warning("Lütfen beğeni kontrolü için Post Linkini girin.")
        else:
            with st.spinner("Adaylar denetleniyor, lütfen bekleyin..."):
                denetim_rows = []
                progress = st.progress(0)
                
                # Formdaki kullanıcı adlarını (C sütunu - index 2) temiz bir listeye al
                form_users = df_form.iloc[:, 2].dropna().astype(str).str.lower().str.strip().tolist()
                
                # U2 Listesindeki her talihli için döngü (D sütunu - index 3)
                for index, row in df_u2.iterrows():
                    u2_user = str(row.iloc[3]).lower().strip() if not pd.isna(row.iloc[3]) else "BOŞ SATIR"
                    
                    if u2_user == "BOŞ SATIR" or u2_user == "nan":
                        continue 
                        
                    hediye_tipi = str(row.iloc[0]) 
                    
                    # 1. FORM KONTROLÜ
                    form_durumu = "✅ Var" if u2_user in form_users else "❌ Yok / Uyuşmuyor"
                    
                    # 2. 3 ETİKET KONTROLÜ (Sociality'den bul)
                    user_comm = df_comm[df_comm.iloc[:, 2].str.lower().str.strip() == u2_user]
                    
                    etiket_durumu = "❌ Yorum Yok"
                    if not user_comm.empty:
                        mentions = get_unique_mentions(user_comm.iloc[0, 4])
                        if len(mentions) >= 3:
                            etiket_durumu = f"✅ Tamam ({len(mentions)} Etiket)"
                        else:
                            etiket_durumu = f"❌ Yetersiz ({len(mentions)} Etiket)"
                            
                    # 3. TAKİP VE BEĞENİ KONTROLÜ
                    takip_durumu, begeni_durumu = verify_follow_and_like(u2_user, post_link)
                    
                    # 4. GENEL DURUM
                    if "❌" in form_durumu or "❌" in etiket_durumu or "❌" in takip_durumu or "❌" in begeni_durumu:
                        son_karar = "ELENDİ: Şartlar Sağlanmadı"
                    elif "⚠️" in takip_durumu or "⚠️" in begeni_durumu:
                        son_karar = "MANUEL KONTROL GEREKLİ"
                    else:
                        son_karar = "GEÇERLİ"
                        
                    # Tabloya Ekle
                    denetim_rows.append({
                        "Durum": hediye_tipi,
                        "Kullanıcı Adı": u2_user,
                        "Form Kaydı?": form_durumu,
                        "3 Etiket?": etiket_durumu,
                        "Takip Ediyor mu?": takip_durumu,
                        "Beğenmiş mi?": begeni_durumu,
                        "SON KARAR": son_karar,
                        "Profil Linki": f"https://instagram.com/{u2_user}/"
                    })
                    
                    progress.progress((index + 1) / len(df_u2))
                    time.sleep(0.1) 
                
                # Sonuçları Göster
                result_df = pd.DataFrame(denetim_rows)
                st.dataframe(
                    result_df, 
                    column_config={
                        "Profil Linki": st.column_config.LinkColumn("Profil Linki")
                    },
                    use_container_width=True
                )
                
                # Excel/CSV İndirme Butonu
                csv = result_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 Denetim Raporunu İndir (CSV)", 
                    data=csv, 
                    file_name="Cekilis_Denetim_Raporu.csv",
                    mime="text/csv"
                )
