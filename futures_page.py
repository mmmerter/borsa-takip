"""
Binance Futures - Streamlit Sayfası
===================================
Bu sayfa Binance Futures hesabınızın tüm verilerini görüntüler
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
from binance_futures import (
    get_futures_api, 
    get_cached_positions,
    get_cached_summary,
    get_cached_daily_pnl,
    get_cached_income_history,
    save_positions_to_sheet,
    save_daily_summary_to_sheet
)
from data_loader import _get_gspread_client


def format_currency(value, decimals=2):
    """Para formatı"""
    if value >= 0:
        return f"<span style='color: #00e676;'>+${value:,.{decimals}f}</span>"
    else:
        return f"<span style='color: #ff5252;'>${value:,.{decimals}f}</span>"


def format_percentage(value, decimals=2):
    """Yüzde formatı"""
    if value >= 0:
        return f"<span style='color: #00e676;'>+{value:.{decimals}f}%</span>"
    else:
        return f"<span style='color: #ff5252;'>{value:.{decimals}f}%</span>"


def create_pnl_chart(daily_pnl_df):
    """Günlük PnL grafiği"""
    if daily_pnl_df.empty:
        return None
    
    fig = go.Figure()
    
    # Günlük PnL bar chart
    colors = ['#00e676' if x >= 0 else '#ff5252' for x in daily_pnl_df['realized_pnl']]
    
    fig.add_trace(go.Bar(
        x=daily_pnl_df['date'],
        y=daily_pnl_df['realized_pnl'],
        name='Günlük PnL',
        marker_color=colors,
        hovertemplate='<b>%{x}</b><br>PnL: $%{y:.2f}<extra></extra>'
    ))
    
    # Kümülatif PnL çizgi grafiği
    fig.add_trace(go.Scatter(
        x=daily_pnl_df['date'],
        y=daily_pnl_df['cumulative_pnl'],
        name='Kümülatif PnL',
        line=dict(color='#2196f3', width=3),
        yaxis='y2',
        hovertemplate='<b>%{x}</b><br>Kümülatif: $%{y:.2f}<extra></extra>'
    ))
    
    fig.update_layout(
        title='Günlük Realized PnL',
        xaxis_title='Tarih',
        yaxis_title='Günlük PnL ($)',
        yaxis2=dict(
            title='Kümülatif PnL ($)',
            overlaying='y',
            side='right'
        ),
        hovermode='x unified',
        template='plotly_dark',
        height=400,
        showlegend=True
    )
    
    return fig


def create_position_pie_chart(positions_df):
    """Pozisyon dağılım grafiği"""
    if positions_df.empty:
        return None
    
    # Long vs Short dağılımı
    long_notional = positions_df[positions_df['side'] == 'LONG']['notional'].sum()
    short_notional = positions_df[positions_df['side'] == 'SHORT']['notional'].sum()
    
    fig = go.Figure(data=[go.Pie(
        labels=['Long', 'Short'],
        values=[long_notional, short_notional],
        hole=0.4,
        marker_colors=['#00e676', '#ff5252'],
        textposition='inside',
        texttemplate='%{label}<br>$%{value:,.0f}<br>%{percent}',
        hovertemplate='<b>%{label}</b><br>$%{value:,.2f}<br>%{percent}<extra></extra>'
    )])
    
    fig.update_layout(
        title='Pozisyon Dağılımı (Notional)',
        template='plotly_dark',
        height=300,
        showlegend=False
    )
    
    return fig


def create_leverage_chart(positions_df):
    """Leverage dağılım grafiği"""
    if positions_df.empty:
        return None
    
    fig = px.bar(
        positions_df,
        x='symbol',
        y='notional',
        color='leverage',
        color_continuous_scale='RdYlGn_r',
        title='Sembol Bazlı Notional ve Leverage',
        labels={'notional': 'Notional ($)', 'symbol': 'Sembol', 'leverage': 'Leverage'},
        hover_data=['side', 'size', 'unrealized_pnl']
    )
    
    fig.update_layout(
        template='plotly_dark',
        height=400,
        xaxis_tickangle=-45
    )
    
    return fig


def show_futures_dashboard():
    """Ana Futures dashboard"""
    
    st.title("📊 Binance Futures Dashboard")
    
    # API ayarları
    with st.sidebar:
        st.header("⚙️ API Ayarları")
        
        # Secrets'tan yükle (varsa)
        try:
            default_api_key = st.secrets["binance_futures"]["api_key"]
            default_api_secret = st.secrets["binance_futures"]["api_secret"]
            default_testnet = st.secrets["binance_futures"].get("testnet", False)
            st.success("✅ API bilgileri secrets'tan yüklendi")
        except:
            default_api_key = st.session_state.get('futures_api_key', '')
            default_api_secret = st.session_state.get('futures_api_secret', '')
            default_testnet = st.session_state.get('futures_testnet', False)
        
        # API credentials
        api_key = st.text_input(
            "API Key", 
            value=default_api_key,
            type='password',
            help="Binance Futures API anahtarınız"
        )
        api_secret = st.text_input(
            "API Secret",
            value=default_api_secret,
            type='password',
            help="Binance Futures API secret"
        )
        
        testnet = st.checkbox(
            "Testnet Kullan",
            value=default_testnet,
            help="Test ağında çalıştır"
        )
        
        # Kaydet
        if st.button("💾 Kaydet", use_container_width=True):
            st.session_state['futures_api_key'] = api_key
            st.session_state['futures_api_secret'] = api_secret
            st.session_state['futures_testnet'] = testnet
            st.success("✅ Ayarlar kaydedildi!")
            st.rerun()
        
        st.divider()
        
        # Yenileme
        auto_refresh = st.checkbox(
            "🔄 Otomatik Yenile (30s)",
            value=st.session_state.get('auto_refresh', False)
        )
        st.session_state['auto_refresh'] = auto_refresh
        
        if st.button("🔄 Manuel Yenile", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        # Google Sheets kaydetme
        st.divider()
        st.subheader("📝 Google Sheets")
        
        save_to_sheets = st.checkbox(
            "Sheets'e Kaydet",
            value=st.session_state.get('save_to_sheets', False),
            help="Verileri Google Sheets'e otomatik kaydet"
        )
        st.session_state['save_to_sheets'] = save_to_sheets
    
    # API key kontrolü
    if not api_key or not api_secret:
        st.warning("⚠️ Lütfen API bilgilerinizi sol menüden girin.")
        st.info("""
        ### 🔑 API Key Nasıl Alınır?
        
        1. [Binance](https://www.binance.com) hesabınıza giriş yapın
        2. Profil > API Management > Create API
        3. **Futures** iznini aktif edin
        4. IP whitelist ekleyin (güvenlik için)
        5. API Key ve Secret'ı buraya yapıştırın
        
        ⚠️ **ÖNEMLİ**: Sadece "Okuma" iznini verin, "Withdraw" iznini vermeyin!
        """)
        return
    
    # API bağlantısı
    try:
        api = get_futures_api(api_key, api_secret, testnet)
        
        # Bağlantı testi
        if not api.test_connection():
            st.error("❌ API bağlantısı başarısız! Lütfen bilgilerinizi kontrol edin.")
            return
        
    except Exception as e:
        st.error(f"❌ API bağlantı hatası: {str(e)}")
        return
    
    # Veri çekme
    try:
        with st.spinner("Veriler yükleniyor..."):
            summary = get_cached_summary(api)
            positions = get_cached_positions(api)
            daily_pnl = get_cached_daily_pnl(api, days=30)
        
        # Google Sheets'e kaydet
        if st.session_state.get('save_to_sheets', False):
            try:
                client = _get_gspread_client()
                if client:
                    if not positions.empty:
                        save_positions_to_sheet(positions, client)
                    save_daily_summary_to_sheet(summary, client)
            except Exception as e:
                st.warning(f"Sheets kaydetme hatası: {str(e)}")
        
    except Exception as e:
        st.error(f"❌ Veri çekme hatası: {str(e)}")
        return
    
    # ==========================================================
    #   ÖZET KPI'lar
    # ==========================================================
    
    st.header("💰 Hesap Özeti")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Cüzdan Bakiyesi",
            f"${summary['wallet_balance']:,.2f}",
            delta=None
        )
    
    with col2:
        st.metric(
            "Marjin Bakiyesi",
            f"${summary['margin_balance']:,.2f}",
            delta=None
        )
    
    with col3:
        st.metric(
            "Kullanılabilir",
            f"${summary['available_balance']:,.2f}",
            delta=None
        )
    
    with col4:
        # Toplam notional
        st.metric(
            "Toplam Pozisyon",
            f"${summary['total_notional']:,.0f}",
            delta=None
        )
    
    st.divider()
    
    # ==========================================================
    #   PnL Metrikleri
    # ==========================================================
    
    st.header("📈 Kar/Zarar Analizi")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        unrealized_color = "normal" if summary['unrealized_pnl'] >= 0 else "inverse"
        st.metric(
            "Gerçekleşmemiş PnL",
            f"${summary['unrealized_pnl']:,.2f}",
            delta=f"{(summary['unrealized_pnl'] / summary['wallet_balance'] * 100):.2f}%" if summary['wallet_balance'] > 0 else "0%",
            delta_color=unrealized_color
        )
    
    with col2:
        pnl_24h_color = "normal" if summary['realized_pnl_24h'] >= 0 else "inverse"
        st.metric(
            "Realized PnL (24h)",
            f"${summary['realized_pnl_24h']:,.2f}",
            delta=f"{(summary['realized_pnl_24h'] / summary['wallet_balance'] * 100):.2f}%" if summary['wallet_balance'] > 0 else "0%",
            delta_color=pnl_24h_color
        )
    
    with col3:
        pnl_7d_color = "normal" if summary['realized_pnl_7d'] >= 0 else "inverse"
        st.metric(
            "Realized PnL (7g)",
            f"${summary['realized_pnl_7d']:,.2f}",
            delta=f"{(summary['realized_pnl_7d'] / summary['wallet_balance'] * 100):.2f}%" if summary['wallet_balance'] > 0 else "0%",
            delta_color=pnl_7d_color
        )
    
    with col4:
        pnl_30d_color = "normal" if summary['realized_pnl_30d'] >= 0 else "inverse"
        st.metric(
            "Realized PnL (30g)",
            f"${summary['realized_pnl_30d']:,.2f}",
            delta=f"{(summary['realized_pnl_30d'] / summary['wallet_balance'] * 100):.2f}%" if summary['wallet_balance'] > 0 else "0%",
            delta_color=pnl_30d_color
        )
    
    st.divider()
    
    # ==========================================================
    #   Pozisyon Bilgileri
    # ==========================================================
    
    st.header("📍 Açık Pozisyonlar")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Toplam Pozisyon", summary['num_positions'])
    
    with col2:
        st.metric("Long Pozisyon", summary['num_long'], delta="🟢")
    
    with col3:
        st.metric("Short Pozisyon", summary['num_short'], delta="🔴")
    
    if not positions.empty:
        st.subheader("Pozisyon Detayları")
        
        # Pozisyon tablosu
        display_df = positions.copy()
        
        # Formatla
        display_df['entry_price'] = display_df['entry_price'].apply(lambda x: f"${x:,.4f}")
        display_df['mark_price'] = display_df['mark_price'].apply(lambda x: f"${x:,.4f}")
        display_df['unrealized_pnl'] = display_df['unrealized_pnl'].apply(lambda x: f"${x:,.2f}")
        display_df['unrealized_pnl_percent'] = display_df['unrealized_pnl_percent'].apply(lambda x: f"{x:.2f}%")
        display_df['liquidation_price'] = display_df['liquidation_price'].apply(lambda x: f"${x:,.4f}")
        display_df['notional'] = display_df['notional'].apply(lambda x: f"${x:,.0f}")
        
        # Kolon isimleri
        display_df.columns = [
            'Sembol', 'Yön', 'Miktar', 'Giriş Fiyatı', 'Mark Fiyat',
            'PnL ($)', 'PnL (%)', 'Leverage', 'Tasfiye Fiyatı',
            'Marjin Tipi', 'Notional', 'Zaman'
        ]
        
        # Göster
        st.dataframe(
            display_df.drop('Zaman', axis=1),
            use_container_width=True,
            height=400
        )
        
        # Grafikler
        col1, col2 = st.columns(2)
        
        with col1:
            pie_fig = create_position_pie_chart(positions)
            if pie_fig:
                st.plotly_chart(pie_fig, use_container_width=True)
        
        with col2:
            leverage_fig = create_leverage_chart(positions)
            if leverage_fig:
                st.plotly_chart(leverage_fig, use_container_width=True)
    
    else:
        st.info("📝 Açık pozisyon bulunmuyor.")
    
    st.divider()
    
    # ==========================================================
    #   PnL Grafiği
    # ==========================================================
    
    st.header("📊 Günlük PnL Analizi")
    
    if not daily_pnl.empty:
        # PnL istatistikleri
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_pnl = daily_pnl['realized_pnl'].sum()
            st.metric(
                "Toplam Realized PnL",
                f"${total_pnl:,.2f}",
                delta_color="normal" if total_pnl >= 0 else "inverse"
            )
        
        with col2:
            avg_daily_pnl = daily_pnl['realized_pnl'].mean()
            st.metric(
                "Ortalama Günlük PnL",
                f"${avg_daily_pnl:,.2f}",
                delta_color="normal" if avg_daily_pnl >= 0 else "inverse"
            )
        
        with col3:
            winning_days = len(daily_pnl[daily_pnl['realized_pnl'] > 0])
            total_days = len(daily_pnl)
            win_rate = (winning_days / total_days * 100) if total_days > 0 else 0
            st.metric(
                "Kazanan Gün Oranı",
                f"{win_rate:.1f}%",
                delta=f"{winning_days}/{total_days}"
            )
        
        with col4:
            max_daily_pnl = daily_pnl['realized_pnl'].max()
            st.metric(
                "En İyi Gün",
                f"${max_daily_pnl:,.2f}",
                delta="🎉"
            )
        
        # Grafik
        pnl_chart = create_pnl_chart(daily_pnl)
        if pnl_chart:
            st.plotly_chart(pnl_chart, use_container_width=True)
        
        # Detaylı tablo
        with st.expander("📋 Günlük PnL Detayları"):
            display_pnl = daily_pnl.copy()
            display_pnl['realized_pnl'] = display_pnl['realized_pnl'].apply(lambda x: f"${x:,.2f}")
            display_pnl['cumulative_pnl'] = display_pnl['cumulative_pnl'].apply(lambda x: f"${x:,.2f}")
            display_pnl.columns = ['Tarih', 'Günlük PnL', 'Kümülatif PnL']
            st.dataframe(display_pnl, use_container_width=True)
    
    else:
        st.info("📝 PnL verisi bulunamadı.")
    
    st.divider()
    
    # ==========================================================
    #   Gelir Geçmişi
    # ==========================================================
    
    st.header("💸 Gelir Geçmişi")
    
    try:
        income_history = get_cached_income_history(api, days=30)
        
        if not income_history.empty:
            # Gelir tipi özeti
            income_summary = income_history.groupby('income_type')['income'].sum().reset_index()
            income_summary = income_summary.sort_values('income', ascending=False)
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Gelir tipi bar chart
                fig = px.bar(
                    income_summary,
                    x='income_type',
                    y='income',
                    color='income',
                    color_continuous_scale='RdYlGn',
                    title='Gelir Tipi Dağılımı (30 Gün)',
                    labels={'income': 'Toplam ($)', 'income_type': 'Gelir Tipi'}
                )
                fig.update_layout(template='plotly_dark', height=400)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.subheader("Toplam Gelirler")
                for _, row in income_summary.iterrows():
                    income_val = row['income']
                    color = "🟢" if income_val >= 0 else "🔴"
                    st.metric(
                        row['income_type'],
                        f"{color} ${income_val:,.2f}"
                    )
            
            # Detaylı tablo
            with st.expander("📋 Gelir Detayları"):
                display_income = income_history.copy()
                display_income['income'] = display_income['income'].apply(lambda x: f"${x:,.4f}")
                display_income.columns = ['Zaman', 'Sembol', 'Gelir Tipi', 'Gelir', 'Varlık', 'Bilgi']
                st.dataframe(display_income, use_container_width=True, height=400)
        
        else:
            st.info("📝 Gelir geçmişi bulunamadı.")
    
    except Exception as e:
        st.warning(f"⚠️ Gelir geçmişi yüklenemedi: {str(e)}")
    
    # ==========================================================
    #   Alt Bilgi
    # ==========================================================
    
    st.divider()
    
    st.caption(f"Son güncelleme: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    st.caption("⚠️ Bu veriler bilgilendirme amaçlıdır. Yatırım tavsiyesi değildir.")
    
    # Otomatik yenileme
    if st.session_state.get('auto_refresh', False):
        import time
        time.sleep(30)
        st.rerun()


if __name__ == "__main__":
    show_futures_dashboard()
