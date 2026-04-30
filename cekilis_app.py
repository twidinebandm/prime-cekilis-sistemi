def fetch_comments_via_api(post_link):
    try:
        # 1. Linki Temizle
        match = re.search(r'/(?:p|reel|tv)/([^/?#&]+)', post_link)
        if not match:
            return None, "Geçersiz Link Formatı."
        shortcode = match.group(1)
        
        # 2. Bağlı Tüm Business Hesaplarını Bul
        ig_accounts = []
        # Me Accounts sorgusu
        acc_url = f"https://graph.facebook.com/v19.0/me/accounts?fields=instagram_business_account,name&access_token={META_ACCESS_TOKEN}"
        acc_res = requests.get(acc_url).json()
        
        if 'data' in acc_res:
            for page in acc_res['data']:
                if 'instagram_business_account' in page:
                    ig_accounts.append(page['instagram_business_account']['id'])
        
        if not ig_accounts:
            return None, "Token'a bağlı hiçbir Instagram Business hesabı bulunamadı. Lütfen Meta Developer panelinden 'instagram_basic' iznini kontrol edin."

        target_media_id = None
        
        # 3. DERİN TARAMA: Her hesapta 100'erli paketler halinde gönderiyi ara
        for ig_account_id in ig_accounts:
            # Limit artırıldı (100)
            media_url = f"https://graph.facebook.com/v19.0/{ig_account_id}/media?fields=shortcode,id&limit=100&access_token={META_ACCESS_TOKEN}"
            
            # Sayfalarca geriye git (Eski postlar için)
            page_count = 0
            while media_url and not target_media_id and page_count < 5: # Son 500 postu tarar
                m_res = requests.get(media_url).json()
                if 'data' in m_res:
                    for item in m_res['data']:
                        if item.get('shortcode') == shortcode:
                            target_media_id = item.get('id')
                            break
                media_url = m_res.get('paging', {}).get('next')
                page_count += 1
                
        if not target_media_id:
            return None, f"Gönderi ({shortcode}) sistemde bulunamadı. Muhtemel sebepler: 1- Gönderi çok eski. 2- Token'ın bu hesabı görme yetkisi yok."

        # 4. Yorumları Çek
        all_comments = []
        comments_url = f"https://graph.facebook.com/v19.0/{target_media_id}/comments?fields=username,text&limit=100&access_token={META_ACCESS_TOKEN}"
        
        while comments_url:
            c_res = requests.get(comments_url).json()
            if 'data' in c_res:
                all_comments.extend(c_res['data'])
            comments_url = c_res.get('paging', {}).get('next')
            
        return pd.DataFrame(all_comments), "Başarılı"
    except Exception as e:
        return None, f"Sistem Hatası: {str(e)}"
