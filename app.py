# app.py  —  TTA Itinerary Builder  |  Streamlit Frontend
import streamlit as st
from datetime import date, timedelta
from pdf_generator import build_pdf
from ai_enhancer import enhance_day_details

# ── Page Config ──────────────────────────────────────────────────
st.set_page_config(
    page_title="TTA Itinerary Builder",
    page_icon="compass",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ───────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Lora:wght@400;600;700&family=DM+Sans:wght@300;400;500;600&display=swap');

    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0D2B4E 0%, #0a2240 100%);
    }
    section[data-testid="stSidebar"] * { color: #E8F0F8 !important; }
    section[data-testid="stSidebar"] .stMarkdown h2 {
        color: #C9A84C !important;
        font-family: 'Lora', serif;
        font-size: 1.1rem;
        border-bottom: 1px solid #C9A84C44;
        padding-bottom: 6px;
        margin-bottom: 8px;
    }

    /* Main headings */
    h1 { font-family: 'Lora', serif !important; color: #0D2B4E !important; }
    h2, h3 { font-family: 'Lora', serif !important; color: #0D2B4E !important; }

    /* Expander */
    .streamlit-expanderHeader {
        background: #F5F7FA;
        border: 1px solid #C8D4E3;
        border-radius: 6px;
        font-weight: 600;
        color: #0D2B4E !important;
    }

    /* Tab active */
    button[data-baseweb="tab"][aria-selected="true"] {
        border-bottom: 3px solid #C9A84C !important;
        color: #0D2B4E !important;
        font-weight: 700;
    }

    /* Metric boxes */
    div[data-testid="metric-container"] {
        background: #F5F7FA;
        border: 1px solid #C8D4E3;
        border-radius: 8px;
        padding: 12px;
    }

    /* Download button */
    div[data-testid="stDownloadButton"] button {
        background: linear-gradient(135deg, #C9A84C, #e0b85c) !important;
        color: #0D2B4E !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 6px !important;
        font-size: 1rem !important;
        padding: 0.6rem 2rem !important;
        letter-spacing: 0.5px;
    }

    /* Primary button */
    div[data-testid="stButton"] button[kind="primary"] {
        background: #0D2B4E !important;
        color: white !important;
        border-radius: 6px !important;
    }

    /* Section cards */
    .section-card {
        background: #F5F7FA;
        border: 1px solid #C8D4E3;
        border-left: 4px solid #C9A84C;
        border-radius: 6px;
        padding: 16px 20px;
        margin-bottom: 12px;
    }

    /* Gold tag */
    .gold-tag {
        background: #C9A84C;
        color: #0D2B4E;
        font-weight: 700;
        font-size: 0.72rem;
        padding: 2px 10px;
        border-radius: 20px;
        display: inline-block;
        letter-spacing: 0.8px;
    }

    .navy-tag {
        background: #0D2B4E;
        color: white;
        font-weight: 600;
        font-size: 0.72rem;
        padding: 2px 10px;
        border-radius: 20px;
        display: inline-block;
    }

    hr { border-color: #C8D4E3 !important; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar — Company Info + AI Config ───────────────────────────
with st.sidebar:
    st.markdown("## Company Profile")
    company_name = st.text_input("Company Name", value="TTA Group")
    email        = st.text_input("Email",   value="Salesindia@ttagroups.net")
    phone        = st.text_input("Phone",   value="+91 9028227102")
    website      = st.text_input("Website", value="Ttagroups.net")

    st.markdown("---")
    # ── AI Configuration ─────────────────────────────────────────
    st.markdown("## AI Elaboration")
    st.caption("Enhance itinerary bullets with free AI. Pick your provider.")

    ai_provider = st.selectbox(
        "AI Provider",
        options=["groq", "gemini", "ollama"],
        format_func=lambda x: {
            "groq":   "Groq — Llama 3.3 (Free API)",
            "gemini": "Google Gemini Flash (Free API)",
            "ollama": "Ollama — Local / Offline (Free)",
        }[x],
        help="All options are free. Groq is recommended for speed.",
    )

    groq_api_key   = "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"
    gemini_api_key = ""
    ollama_model   = "llama3.2"
    ollama_base_url= "http://localhost:11434"

    if ai_provider == "groq":
        groq_api_key = st.text_input(
            "Groq API Key",
            type="password",
            placeholder="gsk_...",
            help="Free at console.groq.com — no credit card needed",
        )
        st.caption("[Get free Groq key](https://console.groq.com)")

    elif ai_provider == "gemini":
        gemini_api_key = st.text_input(
            "Gemini API Key",
            type="password",
            placeholder="AIza...",
            help="Free at aistudio.google.com — no credit card needed",
        )
        st.caption("[Get free Gemini key](https://aistudio.google.com/app/apikey)")

    elif ai_provider == "ollama":
        ollama_model    = st.text_input("Model name", value="llama3.2",
                                         help="Must be pulled in Ollama first")
        ollama_base_url = st.text_input("Ollama URL", value="http://localhost:11434")
        st.caption("Requires [Ollama](https://ollama.com) running locally")

    ai_enhance_all = st.checkbox(
        "Auto-enhance ALL days on PDF generate",
        value=False,
        help="If checked, all days are AI-elaborated when you click Generate PDF",
    )

    st.markdown("---")
    st.markdown("## Default T&C")
    st.caption("Add company-wide terms below.")
    default_tnc_raw = st.text_area(
        "One term per line",
        value=(
            "All prices are subject to availability at time of confirmation.\n"
            "Payment schedule as per booking confirmation.\n"
            "Rates are non-commissionable.\n"
            "The company reserves the right to amend itinerary due to operational reasons."
        ),
        height=160,
    )
    default_tnc = [t.strip() for t in default_tnc_raw.strip().splitlines() if t.strip()]

    st.markdown("---")
    st.caption("TTA Itinerary Builder v2.1")

# ── Main Area ────────────────────────────────────────────────────
st.markdown('<h1 style="margin-bottom:0">Itinerary & Quotation Builder</h1>', unsafe_allow_html=True)
st.markdown('<p style="color:#8A9BB0;margin-top:4px;font-size:0.95rem">Build professional travel quotations with PDF export — free, fast, yours.</p>', unsafe_allow_html=True)
st.markdown("---")

# ═══════════════════════════════════════════════════════════════
#  TABS
# ═══════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "  Trip Details",
    "  Hotels",
    "  Day-wise Itinerary",
    "  Costs & Pricing",
    "  Inclusions / Exclusions",
    "  Preview & Export",
])

# ═══════════════════════════════════════════════════════════════
#  TAB 1 — TRIP DETAILS
# ═══════════════════════════════════════════════════════════════
with tab1:
    st.subheader("Trip Overview")
    col1, col2 = st.columns(2)
    with col1:
        trip_title    = st.text_input("Trip Title *", value="AZERBAIJAN & GEORGIA COMBO",
                                       help="e.g. BALI FAMILY ESCAPE")
        trip_subtitle = st.text_input("Trip Tagline / Subtitle",
                                       value="THE GREAT CAUCASUS CROSSING",
                                       help="e.g. 7 Days of Paradise")
        trip_type     = st.text_input("Package Type", value="Combined Land Package",
                                       help="e.g. Leisure, MICE, Honeymoon")

    with col2:
        start_date  = st.date_input("Start Date", value=date(2026, 5, 18))
        num_pax     = st.number_input("Number of Passengers (Pax)", min_value=1, max_value=500, value=6)
        total_nights= st.number_input("Total Nights", min_value=1, max_value=60, value=6)

    st.markdown("---")
    st.subheader("Introduction Paragraph")
    intro_text = st.text_area(
        "This appears at the top of the PDF after the header",
        value=(
            f"Greetings from {company_name}! We are pleased to present this exclusive travel "
            "itinerary crafted especially for you. Please review the details below and feel free "
            "to reach out for any customization."
        ),
        height=100,
    )

# ═══════════════════════════════════════════════════════════════
#  TAB 2 — HOTELS
# ═══════════════════════════════════════════════════════════════
with tab2:
    st.subheader("Accommodation Details")
    num_hotels = st.number_input("How many hotel entries?", min_value=1, max_value=10, value=2)

    hotels = []
    for i in range(int(num_hotels)):
        with st.expander(f"Hotel {i + 1}", expanded=(i == 0)):
            h1, h2, h3, h4 = st.columns([2, 3, 2, 1])
            with h1:
                loc  = st.text_input("City / Location", key=f"hloc_{i}",
                                      value="Baku" if i == 0 else "Tbilisi")
            with h2:
                name = st.text_input("Hotel Name",     key=f"hname_{i}",
                                      value="Antique Hotel" if i == 0 else "Hotel Irmisa")
            with h3:
                room = st.text_input("Room Type",      key=f"hroom_{i}", value="Standard Room")
            with h4:
                nts  = st.number_input("Nights", min_value=1, max_value=30,
                                        key=f"hnts_{i}", value=3)
            hotels.append({"location": loc, "hotel_name": name, "room_type": room, "nights": nts})

    st.markdown("---")
    breakfast_note = st.text_input(
        "Meal Inclusion Note",
        value="Daily Breakfast is included at all hotels.",
    )

# ═══════════════════════════════════════════════════════════════
#  TAB 3 — DAY-WISE ITINERARY
# ═══════════════════════════════════════════════════════════════
with tab3:
    st.subheader("Day-wise Itinerary")
    st.caption(
        "Fill in your raw bullet points. Use the **Elaborate with AI** button on each day "
        "to expand them into rich travel descriptions — without changing the facts."
    )

    num_days = int(total_nights) + 1
    st.info(
        f"Based on {total_nights} nights you have **{num_days} days** to fill in.  "
        f"AI provider: **{ai_provider.upper()}**"
    )

    # ── Session state: store AI-elaborated versions per day ───────
    if "ai_details" not in st.session_state:
        st.session_state["ai_details"] = {}
    if "ai_status" not in st.session_state:
        st.session_state["ai_status"] = {}

    days = []

    for i in range(num_days):
        day_date  = start_date + timedelta(days=i)
        day_key   = f"day_{i}"
        day_label = f"Day {i + 1:02d}  —  {day_date.strftime('%d %b')}"

        with st.expander(day_label, expanded=(i == 0)):
            dc1, dc2 = st.columns(2)
            with dc1:
                location = st.text_input(
                    "Location / City", key=f"dloc_{i}",
                    value=["BAKU", "BAKU", "ABSHERON", "GABALA / TBILISI",
                           "TBILISI", "KAZBEGI", "DEPARTURE"][i]
                    if i < 7 else "",
                )
            with dc2:
                activity = st.text_input(
                    "Activity / Day Theme", key=f"dact_{i}",
                    value=["Arrival", "City Heritage Tour", "Fire & Rock Tour",
                           "Cross-Border Transfer", "Old Tbilisi City Tour",
                           "Ananuri - Gudauri - Kazbegi", "Final Departure"][i]
                    if i < 7 else "",
                )

            # ── Raw details input ─────────────────────────────────
            default_bullets = "\n".join([
                ["Airport pickup and transfer to hotel\nCheck-in and evening at leisure",
                 "Old City visit including Maiden Tower\nHeydar Aliyev Centre Photostop\nHighland Park overview",
                 "Gobustan Rock Museum & Mud Volcano by 4x4 UAZ\nAteshgah Fire Temple & Yanardag visit",
                 "Gabala Cable Car ride & Lake Nohur\nTransfer to Lagodekhi Border\nDrive to Tbilisi; check-in at hotel",
                 "Tbilisi Cable Car to Narikala Fortress\nSulphur Baths & Peace Bridge\nMetekhi Church & Shardeni Street",
                 "Ananuri Fortress & Zhinvali Reservoir\nGudauri Friendship Monument\nKazbegi: Gergety Church by 4x4 Jeep",
                 "Check-out after breakfast\nPrivate transfer to Tbilisi Airport for departure"][i]
            ] if i < 7 else [""])

            details_raw = st.text_area(
                "Raw bullet points — one per line",
                key=f"ddet_{i}",
                value=default_bullets,
                height=90,
            )
            raw_bullets = [d.strip() for d in details_raw.strip().splitlines() if d.strip()]

            # ── AI Enhance button row ─────────────────────────────
            col_btn, col_reset, col_status = st.columns([1.8, 1.2, 3])

            with col_btn:
                enhance_clicked = st.button(
                    "Elaborate with AI",
                    key=f"enhance_btn_{i}",
                    help="Expand your bullets with vivid travel writing (facts preserved)",
                )
            with col_reset:
                reset_clicked = st.button(
                    "Reset to Original",
                    key=f"reset_btn_{i}",
                    help="Remove AI elaboration and go back to your raw input",
                )

            # ── Handle enhance click ──────────────────────────────
            if enhance_clicked:
                if not raw_bullets:
                    st.session_state["ai_status"][day_key] = ("warning", "No bullet points to elaborate.")
                else:
                    with st.spinner(f"Elaborating Day {i + 1} with {ai_provider.upper()}..."):
                        elaborated, err = enhance_day_details(
                            location        = location,
                            activity        = activity,
                            bullet_points   = raw_bullets,
                            provider        = ai_provider,
                            groq_api_key    = groq_api_key,
                            gemini_api_key  = gemini_api_key,
                            ollama_model    = ollama_model,
                            ollama_base_url = ollama_base_url,
                        )
                    if err:
                        st.session_state["ai_status"][day_key] = ("error", err)
                        st.session_state["ai_details"][day_key] = raw_bullets
                    else:
                        st.session_state["ai_details"][day_key] = elaborated
                        st.session_state["ai_status"][day_key]  = (
                            "success",
                            f"Elaborated {len(elaborated)} bullet(s) successfully.",
                        )

            # ── Handle reset click ────────────────────────────────
            if reset_clicked:
                if day_key in st.session_state["ai_details"]:
                    del st.session_state["ai_details"][day_key]
                if day_key in st.session_state["ai_status"]:
                    del st.session_state["ai_status"][day_key]

            # ── Show status message ───────────────────────────────
            if day_key in st.session_state["ai_status"]:
                level, msg = st.session_state["ai_status"][day_key]
                if level == "success":
                    st.success(msg)
                elif level == "error":
                    st.error(f"AI error: {msg}")
                elif level == "warning":
                    st.warning(msg)

            # ── Show elaborated preview if available ──────────────
            if day_key in st.session_state["ai_details"]:
                ai
