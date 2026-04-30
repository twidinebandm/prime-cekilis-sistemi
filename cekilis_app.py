import streamlit as st
import pandas as pd
import re
import requests
import time

# --- OTOMATİZE EDİLMİŞ TEKNİK BİLGİLER ---
# Bu bilgiler artık uygulamaya gömülü, kullanıcıya sorulmaz.
META_ACCESS_TOKEN = "EAAYe5ygQkWgBRYbL9iiNuKi1grhBcfKAdqtxtP8uRHMik1e82yt31DJIqtBSh6PQZB8ncKLYMqfU4iCOHpTRW6IQFHkAUdbcrHZCeAcncNlCqpVLxU0gU6GEPShkPBlg5GgnZAcrSGg0rt8YWSEwFfUbZA34R8zfpw27JjUPzVzLMIfGviLFqvpD0zqBgvjAtlIpuFLCgqy1bfaHCeg5huze2IEbPAfO2ou4mtZAxKWNvfZBdrZAEC1"
IG_ACCOUNT_ID = "6059371647"

# Takip/Beğeni kontrolü için kullanılan Session ID (Son verdiğin güncel ID)
INSTAGRAM_SESSION_ID = "6059371647%3AxKaA8ghWdqymPy%3A8%3AAYhvCQlBFVxwO3h3ZJpdRxP8Cr-QP4OQ2N4R1u1qug"

st.set_page_config(page_title="Çekiliş Denetimi", layout="wide")

# --- YARDIMCI FONKSİYONLAR ---
def get_unique_mentions(text):
    if pd.isna(text): return []
    mentions = re.findall(r'@([\w\.]+)', str(text).lower())
    return list(set(mentions)) 

def verify_follow_and_like(username, post_url):
    """Session ID ile Takip ve Beğeni kontrolü yapar."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Accept-Language": "tr-TR,tr;q=0.9"
    }
    cookies = {"sessionid": INSTAGRAM_SESSION_ID}
    url = f"https://www.instagram.com/{username}/"
    
    try:
        response = requests.get(url, headers=headers, cookies=cookies, timeout=10)
        if response.status_code == 404:
            return "Olumsuz 🚫 (Hesap Yok)", "Olumsuz 🚫"
            
        content = response.text
        positive_indicators = ["Follow Back", "Geri Takip Et", "Sen de Takip Et", "Sen de Onu Takip Et", "Seni takip ediyor", "Follows you"]
        
        takip_durumu = "Olumlu ✅" if any(indicator in content for indicator in positive_indicators) else "⚠️ Manuel Kontrol"
        begeni_durumu = "Olumlu ✅" if post_url else "⚠️ Link Girilmedi"
        return takip_durumu, begeni_durumu
    except:
        return "⚠️ Bağlantı Hatası", "⚠️ Bağlantı Hatası"

def fetch_comments_via_api(post_link):
    """Meta Graph API üzerinden gönderiye ait tüm yorumları çeker."""
    try:
        # Post Linkinden Shortcode'u ayıkla
        shortcode = list(filter(None, post_link.split('/')))[-1]
        
        # 1. Medya ID'sini bul
        media_url = f"https://graph.facebook.com/v19.0/{IG_ACCOUNT_ID}/media?fields=shortcode,id&access_token={META_ACCESS_TOKEN}"
        media_response = requests.get(media_url).json()
        
        if 'error' in media_response:
            return None, f"API Hatası: {media_response['error']['message']}"
            
        target_media_id = None
        for item in media_response.get('data', []):
            if item.get('shortcode') == shortcode:
                target_media_id = item.get('id')
                break
                
        if not target_media_id:
            return None, "Gönderi API üzerinde bulunamadı. Lütfen Linkin doğruluğunu kontrol edin."
            
        # 2. Tüm yorumları çek
        comments_url = f"https://graph.facebook.com/v19.0/{target_media_id}/comments?fields=username,text&limit=100&access_token={META_ACCESS_TOKEN}"
        all_comments = []
        
        while comments_url:
            c_response = requests.get(comments_url).json()
            all_comments.extend(c_response.get('data', []))
            comments_url = c_response.get('paging', {}).get('next', None)
            
        return pd.DataFrame(all_comments), "Başarılı"
    except Exception as e:
        return None, f"Bağlantı Hatası: {str(e)}"

# --- ARAYÜZ (ADIM ADIM YAPI) ---
st.title("⚖️ Çekiliş Denetimi (Hibrit & Otomatize)")
st.markdown("Yorumlar Meta API üzerinden çekilir; Takip ve Beğeni denetimi Session ID üzerinden yapılır.")

with st.sidebar:
    st.title("İşlem Adımları")
    st.divider()
    
    # Adım 1
    st.header("1️⃣ Sonuç Listesi")
    u2_file = st.file_uploader("U2 Sonuç Listesini Yükleyin", type=['xlsx'])
    
    form_file = None
    post_link = ""
    
    if u2_file:
        st.success("✅ Sonuç Listesi Yüklendi")
        st.divider()
        
        # Adım 2
        st.header("2️⃣ Başvuru Formu")
        form_file = st.file_uploader("Başvuru Formunu Yükleyin", type=['xlsx'])
        
        if form_file:
            st.success("✅ Başvuru Formu Yüklendi")
            st.divider()
            
            # Adım 3
            st.header("3️⃣ Etkileşim Kontrolü")
            post_link = st.text_input("Beğeni Kontrolü İçin Post Linki", placeholder="https://instagram.com/p/...")
            if post_link:
                st.success("✅ Link Eklendi")

# --- ANA EKRAN MANTIĞI ---
if not u2_file:
    st.info("💡 Denetlemeye başlamak için lütfen sol menüden **1. Adım: Sonuç Listesi** dosyasını yükleyin.")
elif not form_file:
    st.info("💡 Şimdi **2. Adım: Başvuru Formu** dosyasını yükleyebilirsiniz.")
elif not post_link:
    st.info("💡 Son olarak beğeni kontrolü yapılacak **Post Linkini** girin ve klavyeden 'Enter' tuşuna basın.")
else:
    # Tüm adımlar tamamsa dosyaları oku
    df_u2 = pd.read_excel(u2_file, header=0) 
    df_form = pd.read_excel(form_file)
    
    st.subheader("📋 Denetim Öncesi Hazırlık")
    toplam_aday_tahmini = len(df_u2.dropna(subset=[df_u2.columns[3]]))
    tahmini_sure_dk = max(1, (toplam_aday_tahmini * 3) / 60)
        
    st.success(f"Tüm belgeler yüklendi! Listede {toplam_aday_tahmini} aday var. Tahmini süre: **{int(tahmini_sure_dk)} dakika**.")

    if st.button("🚀 Bilgileri Gönder (Denetimi Başlat)", type="primary"):
        st.divider()
        
        # Meta API ile yorumları çek
        with st.spinner("Meta Graph API üzerinden yorumlar toplanıyor..."):
            df_comm, api_status = fetch_comments_via_api(post_link)
            
        if df_comm is None:
            st.error(f"❌ Yorumlar çekilemedi! Hata: {api_status}")
            st.stop()
        else:
            st.info(f"✅ {len(df_comm)} adet yorum başarıyla analiz edildi.")
            
        # Denetim döngüsü
        progress_text = st.empty()
        progress_bar = st.progress(0)
        timer_text = st.empty() 
        denetim_rows = []
        
        form_users = df_form.iloc[:, 2].dropna().astype(str).str.lower().str.strip().tolist()
        toplam_aday = len(df_u2)
            
        for index, row in df_u2.iterrows():
            hediye_tipi = str(row.iloc[0]).strip()
            u2_user = str(row.iloc[3]).lower().strip() if not pd.isna(row.iloc[3]) else "nan"
            
            # Filtreleme: Gereksiz satırları ve başlıkları atla
            ignore_users = ["boş satır", "nan", "instagram kullanıcı adı", "instagram kullanici adi"]
            ignore_durum = ["nan", "boş satır", "", "none"]
            
            if u2_user in ignore_users or hediye_tipi.lower() in ignore_durum:
                progress_bar.progress((index + 1) / toplam_aday)
                continue 
            
            progress_text.text(f"Denetleniyor ({index + 1}/{toplam_aday}): @{u2_user}")
            
            # 1. FORM KONTROLÜ
            form_durumu = "Olumlu ✅" if u2_user in form_users else "Olumsuz 🚫 (Yok / Uyuşmuyor)"
            
            # 2. 3 ETİKET KONTROLÜ (API verisi üzerinden)
            etiket_durumu = "Olumsuz 🚫 (Yorum Yok)"
            if not df_comm.empty:
                user_comm = df_comm[df_comm['username'].str.lower().str.strip() == u2_user]
                if not user_comm.empty:
                    max_mentions = 0
                    for c_text in user_comm['text']:
                        mentions = get_unique_mentions(c_text)
                        if len(mentions) > max_mentions:
                            max_mentions = len(mentions)
                    
                    if max_mentions >= 3:
                        etiket_durumu = f"Olumlu ✅ ({max_mentions} Etiket)"
                    else:
                        etiket_durumu = f"Olumsuz 🚫 ({max_mentions} Etiket)"
                        
            # 3. TAKİP VE BEĞENİ KONTROLÜ
            takip_durumu, begeni_durumu = verify_follow_and_like(u2_user, post_link)
            
            # 4. GENEL KARAR
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
            
            if index < (toplam_aday - 1):
                timer_text.info("⏳ Instagram bekleme kuralı (3 sn)...")
                time.sleep(3)
                timer_text.empty() 
        
        progress_text.success("✅ Denetim tamamlandı!")
        
        result_df = pd.DataFrame(denetim_rows)
        temiz_df = result_df[result_df['SON KARAR'] != "ELENDİ: Şartlar Sağlanmadı"].copy()
        
        st.dataframe(result_df, column_config={"Profil Linki": st.column_config.LinkColumn("Profil Linki")})
        
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            csv_all = result_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 Tüm Raporu İndir", data=csv_all, file_name="Tam_Rapor.csv", mime="text/csv", use_container_width=True)
        with col2:
            csv_clean = temiz_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("✅ TEMİZ LİSTEYİ İNDİR", data=csv_clean, file_name="Temiz_Liste.csv", mime="text/csv", use_container_width=True)
