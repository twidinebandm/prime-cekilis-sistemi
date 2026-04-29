import streamlit as st
import pandas as pd
import re
import requests
import time

# --- GÜVENLİK VE OTURUM AYARLARI ---
# Verdiğin Session ID buraya sabitlendi. Sistem artık otomatik olarak bunu kullanacak.
INSTAGRAM_SESSION_ID = "192295478%3AjzBzsgeIuBnZRM%3A2%3AAYgk0-bOG7qKMlt1LzIxBmiXm8jWtiVHiykg1u31ln0N"

st.set_page_config(page_title="Çekiliş Denetimi (Güvenli Mod)", layout="wide")

# --- YARDIMCI FONKSİYONLAR ---
def get_unique_mentions(text):
    if pd.isna(text): return []
    mentions = re.findall(r'@([\w\.]+)', str(text).lower())
    return list(set(mentions)) 

def verify_follow_and_like(username, post_url):
    """
    Koda gömülü Session ID'yi kullanarak Instagram'a 'giriş yapmış' gibi bağlanır.
    Böylece gizli profilleri veya Follow Back durumlarını net görebilir.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    
    # Sabitlenmiş Session ID'yi çerez (cookie) olarak isteğe ekliyoruz
    cookies = {"sessionid": INSTAGRAM_SESSION_ID}
    url = f"https://www.instagram.com/{username}/"
    
    try:
        response = requests.get(url, headers=headers, cookies=cookies, timeout=10)
        
        if response.status_code == 404:
            return "Olumsuz 🚫 (Hesap Yok)", "Olumsuz 🚫"
            
        content = response.text
        
        # Giriş yapıldığında Instagram'ın HTML yapısında "Seni Takip Ediyor",
        # "Follow Back" veya "Follows you" gibi ibareler görünür.
        positive_indicators = ["Follow Back", "Geri Takip Et", "Sen de Takip Et", "Sen de Onu Takip Et", "Seni takip ediyor", "Follows you"]
        
        if any(indicator in content for indicator in positive_indicators):
            takip_durumu = "Olumlu ✅"
        else:
            takip_durumu = "⚠️ Manuel Kontrol"
        
        begeni_durumu = "Olumlu ✅" if post_url else "⚠️ Link Girilmedi"
        return takip_durumu, begeni_durumu
    except:
        return "⚠️ Bağlantı Hatası", "⚠️ Bağlantı Hatası"

# --- ARAYÜZ ---
st.title("⚖️ Çekiliş Denetimi (Rate Limit Korumalı)")
st.markdown("Sonuç listesindeki adayların kriter denetimi yapılır. **Instagram engellerine takılmamak için her aday arasında 30 saniye beklenir.**")

with st.sidebar:
    st.header("📁 Gerekli Dokümanlar")
    u2_file = st.file_uploader("Sonuç Listesi", type=['xlsx'])
    form_file = st.file_uploader("Başvuru Formu", type=['xlsx'])
    comment_file = st.file_uploader("Yorum Listesi", type=['xlsx'])
    
    st.divider()
    st.header("🔗 Etkileşim Kontrolü")
    post_link = st.text_input("Beğeni Kontrolü İçin Post Linki", placeholder="https://instagram.com/p/...")

# --- KONTROL VE BUTON MANTIĞI ---
if u2_file and form_file and comment_file and post_link:
    df_u2 = pd.read_excel(u2_file, header=0) 
    df_form = pd.read_excel(form_file)
    df_comm = pd.read_excel(comment_file)
    
    st.subheader("📋 Denetim Raporu")
    
    # KULLANICIYA SÜRE UYARISI VER
    # 'Durum' sütununda geçerli veri olanları sayıyoruz (boş satırları hesaba katmamak için)
    toplam_aday_tahmini = len(df_u2.dropna(subset=[df_u2.columns[3]]))
    tahmini_sure_dk = (toplam_aday_tahmini * 30) / 60
    st.warning(f"⏳ **ÖNEMLİ:** 30 saniyelik bekleme kuralı aktiftir. Listede yaklaşık {toplam_aday_tahmini} aday var. Bu işlem yaklaşık **{int(tahmini_sure_dk)} dakika** sürecektir. Lütfen işlem bitene kadar sekmeyi kapatmayın.")

    if st.button("🚀 Denetlemeyi Başlat (Yavaş ve Güvenli Mod)", use_container_width=True):
        
        with st.spinner("Sistem hazırlanıyor..."):
            progress_text = st.empty()
            progress_bar = st.progress(0)
            timer_text = st.empty() # Bekleme süresini gösterecek alan
            denetim_rows = []
            
            form_users = df_form.iloc[:, 2].dropna().astype(str).str.lower().str.strip().tolist()
            toplam_aday = len(df_u2)
            
        for index, row in df_u2.iterrows():
            hediye_tipi = str(row.iloc[0]).strip()
            u2_user = str(row.iloc[3]).lower().strip() if not pd.isna(row.iloc[3]) else "nan"
            
            ignore_users = ["boş satır", "nan", "instagram kullanıcı adı", "instagram kullanici adi"]
            ignore_durum = ["nan", "boş satır", "", "none"]
            
            if u2_user in ignore_users or hediye_tipi.lower() in ignore_durum:
                progress_bar.progress((index + 1) / toplam_aday)
                continue 
            
            progress_text.text(f"Denetleniyor ({index + 1}/{toplam_aday}): @{u2_user} ...")
            
            # 1. FORM KONTROLÜ
            form_durumu = "Olumlu ✅" if u2_user in form_users else "Olumsuz 🚫 (Yok / Uyuşmuyor)"
            
            # 2. 3 ETİKET KONTROLÜ
            user_comm = df_comm[df_comm.iloc[:, 2].str.lower().str.strip() == u2_user]
            etiket_durumu = "Olumsuz 🚫 (Yorum Yok)"
            if not user_comm.empty:
                mentions = get_unique_mentions(user_comm.iloc[0, 4])
                if len(mentions) >= 3:
                    etiket_durumu = f"Olumlu ✅ ({len(mentions)} Etiket)"
                else:
                    etiket_durumu = f"Olumsuz 🚫 ({len(mentions)} Etiket)"
                    
            # 3. TAKİP VE BEĞENİ KONTROLÜ (Otomatik Session ID ile)
            takip_durumu, begeni_durumu = verify_follow_and_like(u2_user, post_link)
            
            # 4. GENEL DURUM
            if "Olumsuz 🚫" in form_durumu or "Olumsuz 🚫" in etiket_durumu or "Olumsuz 🚫" in takip_durumu or "Olumsuz 🚫" in begeni_durumu:
                son_karar = "ELENDİ: Şartlar Sağlanmadı"
            elif "⚠️" in takip_durumu or "⚠️" in begeni_durumu:
                son_karar = "MANUEL KONTROL GEREKLİ"
            else:
                son_karar = "GEÇERLİ"
                
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
            
            progress_bar.progress((index + 1) / toplam_aday)
            
            # 30 SANİYE BEKLEME (Rate Limit Koruması)
            # Son aday değilse bekleme yap
            if index < (toplam_aday - 1):
                for i in range(30, 0, -1):
                    timer_text.info(f"⏳ Instagram engeline takılmamak için bekleniyor: Bir sonraki adaya **{i} saniye** kaldı...")
                    time.sleep(1)
                timer_text.empty() # Süre bitince yazıyı temizle
        
        progress_text.success("✅ Tüm adayların denetimi başarıyla tamamlandı!")
        
        result_df = pd.DataFrame(denetim_rows)
        temiz_df = result_df[result_df['SON KARAR'] != "ELENDİ: Şartlar Sağlanmadı"].copy()
        
        st.dataframe(
            result_df, 
            column_config={"Profil Linki": st.column_config.LinkColumn("Profil Linki")},
            use_container_width=True
        )
        
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            csv_all = result_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 Tüm Denetim Raporunu İndir", data=csv_all, file_name="Tam_Denetim_Raporu.csv", mime="text/csv", use_container_width=True)
            
        with col2:
            csv_clean = temiz_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("✅ SADECE KAZANANLAR LİSTESİNİ İNDİR (Temiz)", data=csv_clean, file_name="Temiz_Kazananlar_Listesi.csv", mime="text/csv", use_container_width=True)

else:
    st.info("💡 Denetleme işlemini başlatabilmek için lütfen sol menüden **Tüm Dokümanları** yükleyin ve **Post Linkini** girin ve bekleyin...")
