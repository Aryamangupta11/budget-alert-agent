import streamlit as st
import sqlite3
import json
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date
from dotenv import load_dotenv

load_dotenv()

DB_PATH = "data/transactions.db"
BUDGETS_PATH = "data/budgets.json"

st.set_page_config(
    page_title="Budget Alert Agent",
    page_icon="💰",
    layout="wide"
)

st.markdown("""
<style>
    .main { background-color: #0f1117; }
    .block-container { padding-top: 2rem; }
    .metric-card {
        background: #1e2130;
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        border: 1px solid #2e3250;
        margin-bottom: 1rem;
    }
    .alert-critical {
        background: #2d1515;
        border-left: 4px solid #ff4b4b;
        border-radius: 0 10px 10px 0;
        padding: 1rem 1.2rem;
        margin-bottom: 1rem;
    }
    .alert-warning {
        background: #2d2415;
        border-left: 4px solid #ffa500;
        border-radius: 0 10px 10px 0;
        padding: 1rem 1.2rem;
        margin-bottom: 1rem;
    }
    .alert-safe {
        background: #152d1e;
        border-left: 4px solid #00c853;
        border-radius: 0 10px 10px 0;
        padding: 1rem 1.2rem;
        margin-bottom: 1rem;
    }
    .section-title {
        font-size: 1.3rem;
        font-weight: 600;
        margin-bottom: 1rem;
        color: #e0e0e0;
    }
    .stButton > button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


# ── helpers ───────────────────────────────────────────────────────────────────

def load_budgets():
    if not os.path.exists(BUDGETS_PATH):
        return {}
    with open(BUDGETS_PATH) as f:
        return json.load(f)

def save_budgets(budgets):
    os.makedirs("data", exist_ok=True)
    with open(BUDGETS_PATH, "w") as f:
        json.dump(budgets, f, indent=2)

def get_transactions():
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT date, description, amount, category FROM transactions ORDER BY date DESC",
        conn
    )
    conn.close()
    return df

def get_monthly_spend(category, year, month):
    if not os.path.exists(DB_PATH):
        return 0
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute("""
        SELECT COALESCE(SUM(amount), 0) FROM transactions
        WHERE category = ?
        AND strftime('%Y', date) = ?
        AND strftime('%m', date) = ?
    """, (category, str(year), f"{month:02d}"))
    total = cursor.fetchone()[0]
    conn.close()
    return total

def check_budgets():
    budgets = load_budgets()
    alerts = []
    today = date.today()
    days_in_month = 30
    expected_pct = today.day / days_in_month

    for category, limit in budgets.items():
        spent = get_monthly_spend(category, today.year, today.month)
        pct = (spent / limit * 100) if limit > 0 else 0
        remaining = limit - spent
        pace_warning = (spent / limit) > (expected_pct * 1.2) if limit > 0 else False

        if pct >= 90:
            level = "CRITICAL"
        elif pct >= 70:
            level = "WARNING"
        else:
            level = "SAFE"

        alerts.append({
            "category": category,
            "spent": round(spent, 2),
            "limit": limit,
            "pct_used": round(pct, 1),
            "remaining": round(remaining, 2),
            "level": level,
            "pace_warning": pace_warning,
            "days_remaining": days_in_month - today.day
        })
    return alerts

def generate_message(alert):
    from openai import OpenAI
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ.get("OPENROUTER_API_KEY")
    )
    prompt = f"""
    Write a short, friendly budget alert in 2 sentences.
    Category: {alert['category']}, Spent: Rs.{alert['spent']} of Rs.{alert['limit']} ({alert['pct_used']}%),
    Days remaining: {alert['days_remaining']}, Remaining: Rs.{alert['remaining']}, Level: {alert['level']}.
    Be direct, give one tip, use Rs. for currency, no markdown.
    """
    response = client.chat.completions.create(
        model="anthropic/claude-3-haiku",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()


# ── sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 💰 Budget Agent")
    st.markdown("---")
    page = st.radio(
        "Navigate",
        ["Dashboard", "Transactions", "Upload CSV", "Edit Budgets"],
        label_visibility="collapsed"
    )
    st.markdown("---")
    today = date.today()
    st.markdown(f"**Today:** {today.strftime('%d %b %Y')}")
    st.markdown(f"**Day {today.day} of 30**")

    df_all = get_transactions()
    total_spent = df_all["amount"].sum() if not df_all.empty else 0
    st.markdown(f"**Total logged:** Rs.{total_spent:,.0f}")


# ── dashboard ─────────────────────────────────────────────────────────────────

if page == "Dashboard":
    st.markdown("## Dashboard")

    alerts = check_budgets()
    budgets = load_budgets()

    if not budgets:
        st.warning("No budgets set yet. Go to Edit Budgets to get started.")
        st.stop()

    critical = sum(1 for a in alerts if a["level"] == "CRITICAL")
    warning  = sum(1 for a in alerts if a["level"] == "WARNING")
    safe     = sum(1 for a in alerts if a["level"] == "SAFE")
    total_budget = sum(budgets.values())
    total_spent_month = sum(a["spent"] for a in alerts)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Budget", f"Rs.{total_budget:,}")
    c2.metric("Spent This Month", f"Rs.{total_spent_month:,.0f}")
    c3.metric("Critical Alerts", critical, delta=f"{critical} over 90%" if critical else None,
              delta_color="inverse")
    c4.metric("Remaining", f"Rs.{total_budget - total_spent_month:,.0f}")

    st.markdown("---")
    col_left, col_right = st.columns([1.2, 1])

    with col_left:
        st.markdown('<div class="section-title">Category Breakdown</div>', unsafe_allow_html=True)
        fig = go.Figure()
        categories = [a["category"] for a in alerts]
        spent_vals = [a["spent"] for a in alerts]
        limit_vals = [a["limit"] for a in alerts]
        colors = ["#ff4b4b" if a["level"] == "CRITICAL"
                  else "#ffa500" if a["level"] == "WARNING"
                  else "#00c853" for a in alerts]

        fig.add_trace(go.Bar(
            name="Spent", x=categories, y=spent_vals,
            marker_color=colors, text=[f"Rs.{v:,.0f}" for v in spent_vals],
            textposition="outside"
        ))
        fig.add_trace(go.Bar(
            name="Budget", x=categories, y=limit_vals,
            marker_color="rgba(255,255,255,0.1)",
            text=[f"Rs.{v:,.0f}" for v in limit_vals],
            textposition="outside"
        ))
        fig.update_layout(
            barmode="overlay", paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)", font_color="#e0e0e0",
            height=320, margin=dict(t=20, b=20, l=10, r=10),
            legend=dict(orientation="h", y=-0.2),
            xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#2e3250")
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.markdown('<div class="section-title">Budget Usage</div>', unsafe_allow_html=True)
        fig2 = go.Figure(go.Pie(
            labels=categories,
            values=spent_vals,
            hole=0.5,
            marker_colors=colors,
            textinfo="label+percent"
        ))
        fig2.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#e0e0e0",
            height=320,
            margin=dict(t=20, b=20, l=10, r=10),
            showlegend=False
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")
    st.markdown('<div class="section-title">Budget Status</div>', unsafe_allow_html=True)

    for alert in alerts:
        pct = alert["pct_used"]
        bar_color = "#ff4b4b" if alert["level"] == "CRITICAL" else \
                    "#ffa500" if alert["level"] == "WARNING" else "#00c853"
        css_class = f"alert-{alert['level'].lower()}"

        st.markdown(f"""
        <div class="{css_class}">
            <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
                <span style="font-weight:600;color:#e0e0e0;">{alert['category']}</span>
                <span style="color:{bar_color};font-weight:600;">{pct}%</span>
            </div>
            <div style="background:#111;border-radius:4px;height:8px;margin-bottom:8px;">
                <div style="background:{bar_color};width:{min(pct,100)}%;height:8px;border-radius:4px;"></div>
            </div>
            <div style="font-size:0.82rem;color:#aaa;">
                Rs.{alert['spent']:,.0f} spent · Rs.{alert['remaining']:,.0f} remaining · {alert['days_remaining']} days left
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<div class="section-title">AI-Generated Alerts</div>', unsafe_allow_html=True)
    urgent = [a for a in alerts if a["level"] in ("CRITICAL", "WARNING")]

    if urgent:
        if st.button("Generate Claude Alerts", type="primary"):
            for alert in urgent:
                with st.spinner(f"Analysing {alert['category']}..."):
                    msg = generate_message(alert)
                bar_color = "#ff4b4b" if alert["level"] == "CRITICAL" else "#ffa500"
                st.markdown(f"""
                <div style="background:#1e2130;border-left:4px solid {bar_color};
                     border-radius:0 10px 10px 0;padding:1rem 1.2rem;margin-bottom:1rem;">
                    <strong style="color:{bar_color};">{alert['level']} — {alert['category']}</strong>
                    <p style="margin:6px 0 0;color:#ccc;font-size:0.9rem;">{msg}</p>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.success("All budgets on track — no alerts needed!")


# ── transactions ──────────────────────────────────────────────────────────────

elif page == "Transactions":
    st.markdown("## Transactions")

    df = get_transactions()
    if df.empty:
        st.info("No transactions yet. Upload a CSV to get started.")
        st.stop()

    col1, col2 = st.columns(2)
    with col1:
        cats = ["All"] + sorted(df["category"].unique().tolist())
        selected_cat = st.selectbox("Filter by category", cats)
    with col2:
        search = st.text_input("Search description", placeholder="e.g. Swiggy")

    filtered = df.copy()
    if selected_cat != "All":
        filtered = filtered[filtered["category"] == selected_cat]
    if search:
        filtered = filtered[filtered["description"].str.contains(search, case=False)]

    st.markdown(f"**{len(filtered)} transactions**")

    st.dataframe(
        filtered.rename(columns={
            "date": "Date", "description": "Description",
            "amount": "Amount (Rs.)", "category": "Category"
        }),
        use_container_width=True,
        hide_index=True
    )

    fig = px.bar(
        filtered.groupby("category")["amount"].sum().reset_index(),
        x="category", y="amount", color="category",
        title="Spending by Category",
        labels={"amount": "Total (Rs.)", "category": "Category"}
    )
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font_color="#e0e0e0", showlegend=False)
    st.plotly_chart(fig, use_container_width=True)


# ── upload csv ────────────────────────────────────────────────────────────────

elif page == "Upload CSV":
    st.markdown("## Upload Transactions")
    st.markdown("Upload your bank statement CSV. It must have columns: `date`, `description`, `amount`")

    uploaded = st.file_uploader("Choose a CSV file", type="csv")

    if uploaded:
        df_preview = pd.read_csv(uploaded)
        st.markdown("**Preview:**")
        st.dataframe(df_preview.head(10), use_container_width=True)

        if st.button("Import & Categorize", type="primary"):
            tmp_path = "data/uploaded_temp.csv"
            os.makedirs("data", exist_ok=True)
            df_preview.to_csv(tmp_path, index=False)

            # Check columns before processing
            required = {"date", "description", "amount"}
            actual = set(df_preview.columns.str.strip().str.lower())
            if not required.issubset(actual):
                missing = required - actual
                st.error(f"Wrong CSV format! Missing columns: {missing}. Your CSV has: {set(df_preview.columns.tolist())}")
                st.stop()

            with st.spinner("Loading transactions..."):
                from agent.ingester import load_transactions
                txs = load_transactions(tmp_path)

            if not txs:
                st.warning("No new transactions found — file may be empty or all rows were duplicates.")
            else:
                with st.spinner(f"Categorizing {len(txs)} transactions with Claude..."):
                    from agent.categorizer import categorize_transactions, save_categories
                    categorized = categorize_transactions(txs)
                    save_categories(categorized)
                st.success(f"Imported and categorized {len(categorized)} transactions!")
                st.balloons()


# ── edit budgets ──────────────────────────────────────────────────────────────

elif page == "Edit Budgets":
    st.markdown("## Edit Monthly Budgets")
    st.markdown("Set your monthly spending limits per category (in Rs.)")

    budgets = load_budgets()
    if not budgets:
        budgets = {
            "Food": 3000, "Transport": 2000, "Entertainment": 2000,
            "Utilities": 2000, "Shopping": 3000, "Health": 2000, "Other": 1000
        }

    updated = {}
    cols = st.columns(2)
    for i, (cat, val) in enumerate(budgets.items()):
        with cols[i % 2]:
            updated[cat] = st.number_input(
                f"{cat} (Rs.)", min_value=0, value=int(val), step=500, key=cat
            )

    st.markdown("---")
    col_a, col_b = st.columns(2)
    with col_a:
        new_cat = st.text_input("Add new category", placeholder="e.g. Gym")
    with col_b:
        new_limit = st.number_input("Budget limit (Rs.)", min_value=0, value=1000, step=500)

    if st.button("Save Budgets", type="primary"):
        if new_cat.strip():
            updated[new_cat.strip()] = new_limit
        save_budgets(updated)
        st.success("Budgets saved!")
        st.rerun()
