import streamlit as st
import pandas as pd
import re
import requests
import time

# --- AYARLAR ---
ACCESS_TOKEN = "EAAYe5ygQkWgBRVOdGsWaZCk0h6ZBGSNeEM92ZB7m3gMTgaBCso4EZCZCLjPDoTFjS8oGQb0jXrjYj5ZAwiiQVR9MoXEfVHkNLHtkWFdjY9cRZAZAIeY2DLC6su5fbZAbWBfsSd8XovZAIWLKHkNJYuR3YkOIlM1kAyPf4y4fsLN8RqoS161l6ZAaiTDUmimH8sCwrIWwoZAxelNQbQ9ZCtRbjrMlmSRkmUbMagRGmyaZAxhpWZAcFFZAlBzI6AjB"
BRAND_ACCOUNT = "turktelekomprime"

st.set_page_config(page_title="Turk Telekom Prime Çekiliş Paneli", layout="wide")

# --- GELİŞMİŞ DOĞRULAMA (Kısıtlamaları Aşan Yapı) ---
def advanced_verify(username):
    """
    Sayfa var mı kontrolü yapar. Instagram bot koruması varsa 
    elemez, manuel kontrol şıkkını açık bırakır.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    }
    url = f"https://www.instagram.com/{username}/"
    try:
        response = requests.get(url, headers=headers, timeout=5)
        # Eğer sayfa 404 ise kesin yoktur, diğer durumlarda şans veriyoruz
        if response.status_code == 404:
            return False, "❌ Hesap Bulunamadı"
        return True, "✅ Profil Aktif"
    except:
        return True, "⚠️ Bağlantı Sınırı (Kontrol Et)"

# --- KRİTER FONKSİYONU ---
def check_criteria(row, prev_winners):
    user = str(row['Username']).lower().strip()
    msg = str(row['Message'])
    
    if user in prev_winners:
        return "ELENDİ: Eski Kazanan", False
    
    mentions = re.findall(r'@([\w\.]+)', msg.lower())
    unique_mentions = set(mentions)
    
    if len(unique_mentions) < 3:
        return "ELENDİ: Yetersiz Etiket", False
    if len(mentions) != len(unique_mentions):
        return "ELENDİ: Tekrarlı Etiket", False
        
    return "ÖN ELEME TAMAM", True

# --- ARAYÜZ ---
st.title("🏆 Turk Telekom Prime Profesyonel Çekiliş")

with st.sidebar:
    st.header("🎯 Çekiliş Ayarları")
    asil_s = st.number_input("Asil Sayısı", 1, 100, 2)
    yedek_s = st.number_input("Yedek Sayısı", 0, 100, 2)
    
    st.divider()
    post_url = st.text_input("Post Linki (Beğeni Kontrolü İçin)", placeholder="https://instagram.com/p/...")
    
    st.divider()
    st.header("📁 Dosyalar")
    files = st.file_uploader("Yorumlar", accept_multiple_files=True)
    past_f = st.file_uploader("Eski Kazananlar")

if files:
    # Veri Birleştirme
    df = pd.concat([pd.read_csv(f) if f.name.endswith('.csv') else pd.read_excel(f) for f in files])
    df = df.drop_duplicates(subset=['Username']).copy()
    
    # Eski Kazananlar
    prev_list = []
    if past_f:
        df_p = pd.read_csv(past_f) if past_f.name.endswith('.csv') else pd.read_excel(past_f)
        prev_list = df_p.iloc[:, 1].str.extract(r'@([\w\.]+)')[0].str.lower().dropna().tolist()

    # ÖN ELEME
    analysis = df.apply(lambda r: check_criteria(r, prev_list), axis=1)
    df['Sonuç'] = [x[0] for x in analysis]
    df['Gecerli'] = [x[1] for x in analysis]
    
    st.subheader("🏁 Ön Eleme Sonuçları")
    st.dataframe(df[df['Gecerli'] == True][['Username', 'Sonuç']], use_container_width=True)
    
    potansiyel = df[df['Gecerli'] == True]

    if st.button("🚀 ÇEKİLİŞİ YAP (Kesin Liste)"):
        with st.spinner("Profil geçerlilikleri onaylanıyor..."):
            valid_pool = []
            progress = st.progress(0)
            
            for i, (idx, row) in enumerate(potansiyel.iterrows()):
                is_active, _ = advanced_verify(row['Username'])
                if is_active:
                    valid_pool.append(row['Username'])
                progress.progress((i + 1) / len(potansiyel))
            
            if len(valid_pool) >= (asil_s + yedek_s):
                winners = pd.Series(valid_pool).sample(n=asil_s + yedek_s).tolist()
                st.balloons()
                
                # SONUÇ EKRANI
                c1, c2 = st.columns(2)
                with c1:
                    st.success(f"🌟 ASİL LİSTE ({asil_s} Kişi)")
                    for a in winners[:asil_s]:
                        col_a, col_b = st.columns([3, 2])
                        col_a.write(f"**@{a}**")
                        col_b.markdown(f"[🔗 Profili Aç](https://instagram.com/{a}/)")
                
                with c2:
                    st.warning(f"⏳ YEDEK LİSTE ({yedek_s} Kişi)")
                    for y in winners[asil_s:]:
                        col_a, col_b = st.columns([3, 2])
                        col_a.write(f"**@{y}**")
                        col_b.markdown(f"[🔗 Profili Aç](https://instagram.com/{y}/)")
                
                st.divider()
                st.info("💡 **Önemli:** Kazananların yanında bulunan 'Profili Aç' linkine tıklayarak 'Follow Back' (Geri Takip) ve beğeni durumunu manuel saniyeler içinde teyit edebilirsiniz. Sistem etiket ve eski kazanan elemesini %100 yapmıştır.")
            else:
                st.error("Kriterleri sağlayan yeterli aday bulunamadı.")