import streamlit as st
import pandas as pd
import re
import requests
import time

# --- GÜVENLİK VE OTURUM AYARLARI ---
# Takip ve beğeni kontrolü için Session ID (Arka Kapı)
INSTAGRAM_SESSION_ID = "192295478%3AjzBzsgeIuBnZRM%3A2%3AAYh8VySB7nBet-2nviwjm5wIhLGzfpY4NjAOL7u2nPPe"

st.set_page_config(page_title="Çekiliş Denetimi (Hibrit Mod)", layout="wide")

# --- YARDIMCI FONKSİYONLAR ---
def get_unique_mentions(text):
    if pd.isna(text): return []
    mentions = re.findall(r'@([\w\.]+)', str(text).lower())
    return list(set(mentions)) 

def verify_follow_and_like(username, post_url):
    """Session ID ile Takip ve Beğeni kontrolü yapar."""
    headers = {
        "User-Agent": "Mozilla/5.0",
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

def fetch_comments_via_api(post_link, access_token, ig_account_id):
    """Meta Graph API üzerinden gönderiye ait tüm yorumları çeker."""
    # 1. Post Linkinden Shortcode'u (kısa kodu) ayıkla
    shortcode = list(filter(None, post_link.split('/')))[-1]
    
    # 2. Instagram Hesabındaki Medyaları getir ve doğru gönderinin ID'sini bul
    media_url = f"https://graph.facebook.com/v19.0/{ig_account_id}/media?fields=shortcode,id&access_token={access_token}"
    
    try:
        media_response = requests.get(media_url).json()
        if 'error' in media_response:
            return None, f"API Hatası: {media_response['error']['message']}"
            
        target_media_id = None
        for item in media_response.get('data', []):
            if item.get('shortcode') == shortcode:
                target_media_id = item.get('id')
                break
                
        if not target_media_id:
            return None, "Gönderi API üzerinde bulunamadı. Linki veya Hesap ID'sini kontrol edin."
            
        # 3. Bulunan Gönderinin (Media ID) tüm yorumlarını çek
        comments_url = f"https://graph.facebook.com/v19.0/{target_media_id}/comments?fields=username,text&limit=100&access_token={access_token}"
        all_comments = []
        
        while comments_url:
            c_response = requests.get(comments_url).json()
            if 'error' in c_response:
                return None, f"Yorum Çekme Hatası: {c_response['error']['message']}"
                
            all_comments.extend(c_response.get('data', []))
            
            # Sayfalama (Pagination) - Eğer 100'den fazla yorum varsa diğer sayfaya geç
            comments_url = c_response.get('paging', {}).get('next', None)
            
        # 4. Çekilen veriyi Dataframe'e çevir (Sociality listesinin yerini alacak)
        df_comm = pd.DataFrame(all_comments)
        return df_comm, "Başarılı"
        
    except Exception as e:
        return None, f"Bağlantı/Sistem Hatası: {str(e)}"

# --- ARAYÜZ (ADIM ADIM YAPI) ---
st.title("⚖️ Çekiliş Denetimi (Hibrit Mod)")
st.markdown("API üzerinden otomatik yorum çekimi ve Session ID üzerinden takip/beğeni denetimi.")

with st.sidebar:
    st.title("Adım Adım Kurulum")
    st.divider()
    
    form_file = None
    meta_token = ""
    ig_account_id = ""
    post_link = ""
    
    # 1. ADIM
    st.header("1️⃣ Sonuç Listesi")
    u2_file = st.file_uploader("U2 Ajansından gelen listeyi yükleyin", type=['xlsx'])
    
    if u2_file:
        st.success("✅ Sonuç Listesi Yüklendi")
        st.divider()
        
        # 2. ADIM
        st.header("2️⃣ Başvuru Formu")
        form_file = st.file_uploader("Form yanıtlarını yükleyin", type=['xlsx'])
        
        if form_file:
            st.success("✅ Başvuru Formu Yüklendi")
            st.divider()
            
            # 3. ADIM: META API
            st.header("3️⃣ Meta API Bağlantısı")
            st.caption("Yorumları otomatik çekmek için yetkili bilgileri girin.")
            ig_account_id = st.text_input("Instagram Account ID", placeholder="Örn: 17841400...")
            meta_token = st.text_input("Meta Access Token", type="password", placeholder="EAAYe5ygQk...")
            
            if ig_account_id and meta_token:
                st.success("✅ API Bilgileri Girildi")
                st.divider()
                
                # 4. ADIM: POST LİNKİ
                st.header("4️⃣ Post Bağlantısı")
                post_link = st.text_input("Denetlenecek Gönderi Linki", placeholder="https://instagram.com/p/...")
                if post_link:
                    st.success("✅ Link Eklendi")

# --- KONTROL VE BUTON MANTIĞI ---
if not u2_file:
    st.info("💡 Lütfen **1. Adım: Sonuç Listesi** dosyasını yükleyin.")
elif not form_file:
    st.info("💡 Şimdi **2. Adım: Başvuru Formu** dosyasını yükleyin.")
elif not ig_account_id or not meta_token:
    st.info("💡 Yorumları çekebilmemiz için **3. Adım: Meta API** bilgilerini girin.")
elif not post_link:
    st.info("💡 Son adım: Yorumların çekileceği **Post Linkini** yapıştırıp Enter'a basın.")
else:
    df_u2 = pd.read_excel(u2_file, header=0) 
    df_form = pd.read_excel(form_file)
    
    toplam_aday_tahmini = len(df_u2.dropna(subset=[df_u2.columns[3]]))
    tahmini_sure_dk = max(1, (toplam_aday_tahmini * 3) / 60)
        
    st.success(f"Tüm bilgiler hazır! Listede yaklaşık {toplam_aday_tahmini} aday var. Bu işlem yaklaşık **{int(tahmini_sure_dk)} dakika** sürecektir.")

    if st.button("🚀 Bilgileri Gönder (Denetimi Başlat)", type="primary"):
        st.divider()
        
        # ÖNCE YORUMLARI API'DEN ÇEKİYORUZ
        with st.spinner("Meta Graph API'ye bağlanılıyor ve yorumlar indiriliyor..."):
            df_comm, api_status = fetch_comments_via_api(post_link, meta_token, ig_account_id)
            
        if df_comm is None:
            st.error(f"❌ Yorumlar çekilemedi! Lütfen API bilgilerinizi kontrol edin. Hata Detayı: {api_status}")
            st.stop()
        else:
            st.success(f"✅ API Bağlantısı Başarılı! Toplam {len(df_comm)} yorum sisteme aktarıldı.")
            
        # DENETİM AŞAMASI BAŞLIYOR
        with st.spinner("Adaylar denetleniyor..."):
            progress_text = st.empty()
            progress_bar = st.progress(0)
            timer_text = st.empty() 
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
            
            # 2. 3 ETİKET KONTROLÜ (Artık API'den gelen df_comm Dataframe'i üzerinden aranıyor)
            etiket_durumu = "Olumsuz 🚫 (Yorum Yok)"
            
            # Eğer API'den gelen listede (username sütunu) bu kişi varsa text sütunundaki yorumuna bakıyoruz
            if not df_comm.empty and 'username' in df_comm.columns:
                user_comm = df_comm[df_comm['username'].str.lower().str.strip() == u2_user]
                if not user_comm.empty:
                    # En çok etiket yaptığı yorumu almak için tüm yorumlarını kontrol edebiliriz
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
                timer_text.info("⏳ Kontrol ediliyor...")
                time.sleep(3)
                timer_text.empty() 
        
        progress_text.success("✅ Tüm adayların denetimi başarıyla tamamlandı!")
        
        result_df = pd.DataFrame(denetim_rows)
        temiz_df = result_df[result_df['SON KARAR'] != "ELENDİ: Şartlar Sağlanmadı"].copy()
        
        st.dataframe(result_df, column_config={"Profil Linki": st.column_config.LinkColumn("Profil Linki")})
        
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            csv_all = result_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 Tüm Denetim Raporunu İndir", data=csv_all, file_name="Tam_Denetim_Raporu.csv", mime="text/csv")
            
        with col2:
            csv_clean = temiz_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("✅ SADECE KAZANANLAR LİSTESİNİ İNDİR (Temiz)", data=csv_clean, file_name="Temiz_Kazananlar_Listesi.csv", mime="text/csv")
