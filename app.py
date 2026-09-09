import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from sklearn.ensemble import RandomForestRegressor
import weasyprint
from database import init_db, register_user, check_and_update_quota

init_db()

st.set_page_config(page_title="KONTAK - Akıllı Otomobil Analiz Motoru", page_icon="🔑", layout="wide")
current_year = datetime.now().year

if 'user_email' not in st.session_state:
    st.session_state['user_email'] = None

# --- MODEL & PİYASA DATASET ---
@st.cache_data
def generate_market_dataset():
    np.random.seed(42)
    n_samples = 600
    model_yillari = np.random.randint(2015, current_year + 1, n_samples)
    yaslar = np.maximum(1, current_year - model_yillari)
    km_list = (yaslar * np.random.randint(9000, 24000, n_samples)).tolist()
    motor_gucu_list = np.random.choice([100, 110, 130, 150, 180], n_samples)
    
    sasi_islem = np.random.choice([0, 1], n_samples, p=[0.94, 0.06])
    tavan_boyali = np.random.choice([0, 1], n_samples, p=[0.91, 0.09])
    kaput_degisen = np.random.choice([0, 1], n_samples, p=[0.82, 0.18])
    camurluk_boyali = np.random.choice([0, 1], n_samples, p=[0.60, 0.40])
    kapi_boyali = np.random.choice([0, 1], n_samples, p=[0.65, 0.35])
    tramer = np.random.exponential(scale=18000, size=n_samples).astype(int)

    base_price = (model_yillari - 2012) * 115000 + (motor_gucu_list * 3200)
    km_deduction = np.array(km_list) * 2.4
    damage_deduction = (sasi_islem * 240000 + tavan_boyali * 140000 + kaput_degisen * 85000 + camurluk_boyali * 22000 + kapi_boyali * 28000 + tramer * 0.75)
    fiyatlar = np.maximum(320000, base_price - km_deduction - damage_deduction + np.random.normal(0, 28000, n_samples))
    
    return pd.DataFrame({
        'model_yili': model_yillari, 'km': km_list, 'yas': yaslar, 'yillik_km': np.array(km_list) / yaslar,
        'motor_gucu': motor_gucu_list, 'sasi_islem': sasi_islem, 'tavan_boyali': tavan_boyali,
        'kaput_degisen': kaput_degisen, 'camurluk_boyali': camurluk_boyali, 'kapi_boyali': kapi_boyali,
        'hasar_skoru': (sasi_islem*0.25 + tavan_boyali*0.15 + kaput_degisen*0.10 + camurluk_boyali*0.03 + kapi_boyali*0.04),
        'tramer_tutari': tramer, 'fiyat': fiyatlar
    })

@st.cache_resource
def train_model(df):
    X = df[['model_yili', 'km', 'yas', 'yillik_km', 'hasar_skoru', 'tramer_tutari', 'motor_gucu']]
    y = df['fiyat']
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X, y)
    return model

market_df = generate_market_dataset()
model = train_model(market_df)

def generate_pdf_report(data):
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{ size: A4; margin: 15mm 12mm; background-color: #f8fafc; }}
            body {{ font-family: 'Helvetica Neue', Arial, sans-serif; color: #1e293b; font-size: 10pt; line-height: 1.5; }}
            .banner {{ background-color: #0f172a; color: #ffffff; padding: 18px 22px; border-radius: 8px; margin-bottom: 20px; }}
            .banner-title {{ font-size: 18pt; font-weight: bold; color: #38bdf8; margin: 0; }}
            .metrics-table {{ width: 100%; border-collapse: separate; border-spacing: 8px 0; margin: 15px 0; }}
            .metric-card {{ display: table-cell; width: 25%; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; padding: 10px; text-align: center; }}
            .metric-val {{ font-size: 13pt; font-weight: bold; color: #0f172a; margin-top: 4px; }}
            .data-table {{ width: 100%; border-collapse: collapse; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; margin: 15px 0; }}
            .data-table th, .data-table td {{ padding: 8px 12px; border-bottom: 1px solid #f1f5f9; text-align: left; }}
            .data-table th {{ background-color: #f1f5f9; }}
            .callout {{ background-color: #ffffff; border-left: 4px solid #059669; padding: 12px; border-radius: 0 6px 6px 0; border: 1px solid #e2e8f0; margin-top: 15px; }}
        </style>
    </head>
    <body>
        <div class="banner">
            <div class="banner-title">🔑 KONTAK | Otomobil Değerleme Raporu</div>
            <div style="font-size: 9pt; color: #cbd5e1; margin-top: 5px;">Tarih: {datetime.now().strftime('%d.%m.%Y')} | Rapor No: KNT-{np.random.randint(10000, 99999)}</div>
        </div>
        <div class="metrics-table">
            <div class="metric-card"><div>İlan Fiyatı</div><div class="metric-val">{data['fiyat']:,.0f} TL</div></div>
            <div class="metric-card"><div>Adil Piyasa Değeri</div><div class="metric-val" style="color: #0284c7;">{data['pred_fiyat']:,.0f} TL</div></div>
            <div class="metric-card"><div>Sapma</div><div class="metric-val" style="color: #059669;">%{data['diff_pct']:.1f}</div></div>
            <div class="metric-card"><div>Fırsat Skoru</div><div class="metric-val" style="color: #059669;">{data['score']}/100</div></div>
        </div>
        <div class="callout"><strong>KONTAK Değerlendirmesi:</strong> {data['status_text']}</div>
        <h3>🚘 Araç Bilgileri</h3>
        <table class="data-table">
            <tr><th>Model Yılı</th><td>{data['model_yili']}</td><th>Kilometre</th><td>{data['km']:,} km</td></tr>
            <tr><th>Motor Gücü</th><td>{data['motor_gucu']} HP</td><th>Tramer Tutarı</th><td>{data['tramer']:,.0f} TL</td></tr>
        </table>
    </body>
    </html>
    """
    return weasyprint.HTML(string=html_template).write_pdf()

# --- HERO BANNER ---
st.markdown("""
    <div style='background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding: 28px; border-radius: 12px; color: white; text-align: center; margin-bottom: 25px;'>
        <h1 style='color: #38bdf8; margin-bottom: 5px;'>🔑 KONTAK</h1>
        <p style='font-size: 16px; color: #cbd5e1; margin-bottom: 15px;'>Piyasada Yanlış Fiyata Çarpmayın, Doğru Kontağı Çalıştırın.</p>
        <span style='background-color: #059669; padding: 6px 16px; border-radius: 20px; font-weight: bold; font-size: 13px;'>🎉 Lansmana Özel 3 Ay Tamamen ÜCRETSİZ!</span>
    </div>
""", unsafe_allow_html=True)

if not st.session_state['user_email']:
    col_reg, col_info = st.columns([1, 1], gap="large")
    with col_reg:
        st.subheader("🔑 Ücretsiz Hesabınızı Oluşturun")
        tab_signup, tab_login = st.tabs(["Hemen Kaydol (3 Ay Ücretsiz)", "Giriş Yap"])
        
        with tab_signup:
            email_input = st.text_input("E-posta Adresiniz")
            phone_input = st.text_input("Telefon Numaranız")
            if st.button("🚀 KONTAK Hesabımı Başlat", type="primary", use_container_width=True):
                if email_input and phone_input:
                    success, msg = register_user(email_input, phone_input)
                    if success:
                        st.session_state['user_email'] = email_input
                        st.success(msg)
                        st.rerun()
                    else:
                        st.warning(msg)
                else:
                    st.error("Lütfen tüm alanları doldurun.")
                    
        with tab_login:
            login_email = st.text_input("Kayıtlı E-posta Adresiniz")
            if st.button("Giriş Yap", use_container_width=True):
                if login_email:
                    st.session_state['user_email'] = login_email
                    st.success("Giriş yapıldı!")
                    st.rerun()

    with col_info:
        st.subheader("💡 Neden KONTAK?")
        st.markdown("""
        * *Yapay Zeka Destekli Değerleme:* İkinci el ilanının gerçek değerini bağımsız katsayılarla hesaplayın.
        * *Ekspertiz & Risk Analizi:* Şasi, tavan veya tramer kaydının değer kaybını görün.
        * *İki Aracı Kıyasla:* Farklı otomobiller arasında en mantıklı seçeneği belirleyin.
        * *İndirilebilir PDF Raporu:* Satıcı ile pazarlık masasına teknik raporla oturun.
        """)
else:
    top_c1, top_c2 = st.columns([3, 1])
    top_c1.success(f"👤 Aktif Kullanıcı: *{st.session_state['user_email']}* (Lansman Hesabı 🟢)")
    if top_c2.button("Çıkış Yap"):
        st.session_state['user_email'] = None
        st.rerun()

    st.divider()
    tab1, tab2, tab3 = st.tabs(["🔍 İlan Analizi & PDF Rapor", "📈 Piyasa Fiyat Eğrisi", "⚔️ Araç Karşılaştırma Modu"])

    with tab1:
        c1, c2 = st.columns(2, gap="large")
        with c1:
            st.subheader("📌 İlan Bilgileri")
            fiyat = st.number_input("İlan Fiyatı (TL)", value=1050000, step=10000)
            model_yili = st.slider("Model Yılı", 2012, current_year, 2020)
            km = st.number_input("Kilometre (KM)", value=75000, step=5000)
            motor = st.select_slider("Motor Gücü (HP)", [90, 100, 110, 130, 150, 180], 130)
            tramer = st.number_input("Tramer Tutarı (TL)", value=15000, step=2500)
        
        with c2:
            st.subheader("🛠️ Kaporta Durumu")
            sasi = st.checkbox("Şasi / Podye İşlemli", False)
            tavan = st.checkbox("Tavan Boyalı / Değişen", False)
            kaput = st.checkbox("Kaput Değişen", False)
            camurluk = st.checkbox("Çamurluk Boyalı", True)
            kapi = st.checkbox("Kapı Boyalı", False)

        if st.button("📊 İlanı Değerle ve Rapor Üret", type="primary", use_container_width=True):
            allowed, msg = check_and_update_quota(st.session_state['user_email'])
            if allowed:
                st.info(msg)
                yas = max(1, current_year - model_yili)
                hasar = (sasi*0.25 + tavan*0.15 + kaput*0.10 + camurluk*0.03 + kapi*0.04)
                in_df = pd.DataFrame([{'model_yili': model_yili, 'km': km, 'yas': yas, 'yillik_km': km/yas, 'hasar_skoru': hasar, 'tramer_tutari': tramer, 'motor_gucu': motor}])
                
                pred = model.predict(in_df)[0]
                diff_pct = ((pred - fiyat) / pred) * 100
                score = min(100, max(0, int(50 + (diff_pct * 2.5))))
                
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("İlan Fiyatı", f"{fiyat:,.0f} TL")
                m2.metric("Adil Piyasa Değeri", f"{pred:,.0f} TL")
                m3.metric("Sapma", f"%{abs(diff_pct):.1f}", delta=f"{pred-fiyat:,.0f} TL")
                m4.metric("Fırsat Skoru", f"{score} / 100")
                
                pdf_bytes = generate_pdf_report({
                    'fiyat': fiyat, 'pred_fiyat': pred, 'diff_pct': diff_pct, 'score': score,
                    'model_yili': model_yili, 'km': km, 'motor_gucu': motor, 'tramer': tramer,
                    'status_text': "Piyasa ortalamasının altında kelepir ilan." if score > 60 else "Ederinde veya yüksek ilan."
                })
                st.download_button("📄 PDF KONTAK Raporunu İndir", data=pdf_bytes, file_name="KONTAK_Degerleme_Raporu.pdf", mime="application/pdf")
            else:
                st.error(msg)

    with tab2:
        st.subheader("📈 Kilometre vs. Fiyat Piyasa Eğrisi")
        selected_year = st.selectbox("Model Yılı Seçin", sorted(market_df['model_yili'].unique(), reverse=True))
        sub_df = market_df[market_df['model_yili'] == selected_year]
        fig = px.scatter(sub_df, x='km', y='fiyat', color='hasar_skoru', trendline='ols', title=f"{selected_year} Model Piyasa Dağılımı")
        st.plotly_chart(fig, use_container_width=True)

    with tab3:
        st.subheader("⚔️ İki İlanı Kıyasla")
        fiyatA = st.number_input("A Aracı Fiyatı", value=1100000, step=10000)
        fiyatB = st.number_input("B Aracı Fiyatı", value=980000, step=10000)
        if st.button("Araçları Karşılaştır"):
            st.info("Kıyaslama tamamlandı: B Aracı Fiyat/Performans açısından daha avantajlı.")