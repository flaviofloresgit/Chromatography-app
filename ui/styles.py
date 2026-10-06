"""
Custom CSS styling and design system for the Chromatography GC-MS Streamlit app.
"""

def get_custom_css() -> str:
    return """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    /* Global Typography & Layout */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    .main .block-container {
        padding-top: 1.8rem;
        padding-bottom: 3rem;
        max-width: 1280px;
    }

    /* App Header Banner */
    .lab-header {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 50%, #0F766E 100%);
        color: white;
        padding: 1.5rem 2rem;
        border-radius: 14px;
        margin-bottom: 1.5rem;
        box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.25);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .lab-header h1 {
        font-size: 1.85rem;
        font-weight: 700;
        margin: 0;
        letter-spacing: -0.02em;
        color: #F8FAFC;
    }
    .lab-header p {
        font-size: 0.92rem;
        margin-top: 0.35rem;
        margin-bottom: 0;
        color: #94A3B8;
    }

    /* Badges & Pills */
    .badge {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.25rem 0.65rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .badge-success {
        background-color: #DCFCE7;
        color: #166534;
        border: 1px solid #86EFAC;
    }
    .badge-warning {
        background-color: #FEF3C7;
        color: #92400E;
        border: 1px solid #FCD34D;
    }
    .badge-info {
        background-color: #E0F2FE;
        color: #075985;
        border: 1px solid #7DD3FC;
    }
    .badge-high {
        background-color: #DCFCE7;
        color: #15803D;
        font-weight: 600;
    }
    .badge-medium {
        background-color: #FEF9C3;
        color: #A16207;
        font-weight: 600;
    }
    .badge-low {
        background-color: #FEE2E2;
        color: #B91C1C;
        font-weight: 600;
    }

    /* Modern Metric Cards */
    .metric-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 1.1rem 1.25rem;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .metric-label {
        font-size: 0.78rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: #64748B;
        margin-bottom: 0.25rem;
    }
    .metric-value {
        font-size: 1.55rem;
        font-weight: 700;
        color: #0F172A;
        letter-spacing: -0.02em;
    }
    .metric-sub {
        font-size: 0.75rem;
        color: #94A3B8;
        margin-top: 0.2rem;
    }

    /* Peak Card Details */
    .compound-box {
        background: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-left: 4px solid #2563EB;
        border-radius: 8px;
        padding: 1rem 1.25rem;
        margin-bottom: 1rem;
    }

    /* Chat bubble styles */
    .chat-bubble-user {
        background-color: #EFF6FF;
        border: 1px solid #DBEAFE;
        border-radius: 12px;
        padding: 0.85rem 1.1rem;
        margin-bottom: 0.75rem;
        color: #1E3A8A;
    }
    .chat-bubble-assistant {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 0.85rem 1.1rem;
        margin-bottom: 0.75rem;
        color: #1E293B;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04);
    }

    /* Clean Streamlit Tables */
    div[data-testid="stDataFrame"] {
        border-radius: 10px;
        overflow: hidden;
        border: 1px solid #E2E8F0;
    }

    /* Buttons */
    .stButton>button {
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.15s ease;
    }
    .stDownloadButton>button {
        border-radius: 8px;
        font-weight: 600;
    }
    </style>
    """
