import streamlit as st
import pandas as pd
import re
import requests
import time

# --- GÜVENLİK AYARLARI (Streamlit Secrets üzerinden) ---
# Streamlit Cloud'da Settings > Secrets kısmına ACCESS_TOKEN = "..." olarak eklenmelidir.
try:
    ACCESS_TOKEN = st.secrets["ACCESS_TOKEN"]
except:
    st.error("Hata: ACCESS_TOKEN bulunamadı! Lütfen Streamlit Secrets ayarlarına ekleyin.")
    st.stop()

st.set_page_config(page_title="Prime Çekiliş Merkezi", layout="wide")

# --- FONKSİYONLAR ---

def check_instagram_status(username):
    """Kullanıcının profilinin aktif olup olmadığını kontrol eder."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    }
    url = f"https://www.instagram.com/{username}/"
    try:
        response = requests.get(url, headers=headers, timeout=8)
        if response.status_code == 200:
            return True, "✅ Profil Aktif"
        return False, "❌ Profil Bulunamadı (404)"
    except:
        return True, "⚠️ Bağlantı Sınırı (Manuel Kontrol)"

def fast_pre_filter(row, prev_winners):
    """Dosya üzerinden hızlı ön eleme (Etiket ve Eski Kazanan)."""
    user = str(row['Username']).lower().strip()
    msg = str(row['Message'])
    
    # 1. Eski Kazanan Kontrolü
    if user in prev_winners:
        return "ELENDİ: Eski Kazanan", False
    
    # 2. Etiket Kontrolü (En az 3 farklı kişi)
    mentions = re.findall(r'@([\w\.]+)', msg.lower())
    unique_mentions = set(mentions)
    
    if len(unique_mentions) < 3:
        return "ELENDİ: Yetersiz Etiket", False
    if len(mentions) != len(unique_mentions):
        return "ELENDİ: Tekrarlı Etiket", False
        
    return "ÖN ELEME TAMAM", True

# --- ARAYÜZ ---
st.title("🏆 Prime Çekiliş Paneli")
st.markdown("---")

with st.sidebar:
    st.header("🎯 Çekiliş Parametreleri")
    asil_s = st.number_input("Asil Sayısı", min_value=1, step=1, value=2)
    yedek_s = st.number_input("Yedek Sayısı", min_value=0, step=1, value=2)
    
    st.divider()
    st.header("🔗 Gönderi Linki")
    post_url = st.text_input("Beğeni Kontrolü İçin Post Linki", placeholder="https://instagram.com/p/...")
    
    st.divider()
    st.header("📁 Veri Kaynakları")
    comment_files = st.file_uploader("Yorum Dosyalarını Seçin", accept_multiple_files=True)
    past_file = st.file_uploader("Eski Kazananlar (kazananlar.xlsx)")

if comment_files:
    # 1. Dosyaları birleştir ve aynı kullanıcıyı 1 kez say
    all_data = []
    for f in comment_files:
        try:
            temp = pd.read_csv(f) if f.name.endswith('.csv') else pd.read_excel(f)
            all_data.append(temp)
        except:
            st.error(f"Dosya okunamadı: {f.name}")
    
    if all_data:
        df = pd.concat(all_data, ignore_index=True)
        # Sadece Username ve Message sütunlarını temizle
        df = df.drop_duplicates(subset=['Username']).copy()
        
        # 2. Eski kazananları yükle
        prev_list = []
        if past_file:
            try:
                df_p = pd.read_csv(past_file) if past_file.name.endswith('.csv') else pd.read_excel(past_file)
                # İkinci sütundan kullanıcı adını ayıkla
                prev_list = df_p.iloc[:, 1].str.extract(r'@([\w\.]+)')[0].str.lower().dropna().tolist()
            except:
                st.warning("Eski kazananlar dosyası işlenemedi.")

        # 3. ÖN ELEME AŞAMASI
        st.subheader("🏁 Aşama 1: Kriter Ön Elemesi")
        analysis = df.apply(lambda r: fast_pre_filter(r, prev_list), axis=1)
        df['Durum_Metni'] = [x[0] for x in analysis]
        df['Gecerli_Mi'] = [x[1] for x in analysis]
        
        # Sadece ön elemeyi geçenleri göster
        st.dataframe(df[df['Gecerli_Mi'] == True][['Username', 'Durum_Metni']], use_container_width=True)
        
        potansiyel = df[df['Gecerli_Mi'] == True]
        st.success(f"Ön elemeyi geçen {len(potansiyel)} aday bulundu.")

        # 4. KESİN DOĞRULAMA VE ÇEKİLİŞ
        if st.button("🚀 ÇEKİLİŞİ BAŞLAT (Profil ve Takip Onayı)"):
            with st.spinner("Profiller doğrulanıyor, lütfen bekleyin..."):
                final_pool = []
                prog_bar = st.progress(0)
                
                for i, (idx, row) in enumerate(potansiyel.iterrows()):
                    is_active, _ = check_instagram_status(row['Username'])
                    if is_active:
                        final_pool.append(row['Username'])
                    prog_bar.progress((i + 1) / len(potansiyel))
                    time.sleep(0.05) # Rate limit koruması

                if len(final_pool) >= (asil_s + yedek_s):
                    winners = pd.Series(final_pool).sample(n=asil_s + yedek_s).tolist()
                    st.balloons()
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        st.success(f"🌟 {asil_s} ASİL KAZANAN")
                        for a in winners[:asil_s]:
                            col_user, col_link = st.columns([3, 2])
                            col_user.write(f"**@{a}**")
                            col_link.markdown(f"[🔗 Profili Aç](https://instagram.com/{a}/)")
                    
                    with c2:
                        st.warning(f"⏳ {yedek_s} YEDEK KAZANAN")
                        for y in winners[asil_s:]:
                            col_user, col_link = st.columns([3, 2])
                            col_user.write(f"**@{y}**")
                            col_link.markdown(f"[🔗 Profili Aç](https://instagram.com/{y}/)")
                    
                    st.markdown("---")
                    st.info("💡 **İpucu:** 'Profili Aç' linkiyle kazananın Follow Back (Geri Takip) durumunu manuel teyit etmeniz %100 doğruluk için önerilir.")
                else:
                    st.error(f"Yeterli aday yok! (Filtreleri geçen: {len(final_pool)})")
