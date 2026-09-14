import streamlit as st
import pandas as pd
from datetime import datetime, date
import gspread
from google.oauth2.service_account import Credentials
import os

st.set_page_config(
    page_title="TCC Orders",
    page_icon="🧀",
    layout="wide"
)

# ---------------- CONFIG ----------------

HEADERS = [
    "Date", "Outlet", "Order ID", "Channel", "Item ID", "Item", "Qty",
    "Unit Price", "Discount", "Reason", "Payment Mode", "Net Sale",
    "Added By", "Shift"
]

DEFAULT_MENU = [
    {"Item ID": "Combo179", "Item": "Combo179", "Unit Price": 179},
    {"Item ID": "Combo249", "Item": "Combo249", "Unit Price": 249},
    {"Item ID": "SF", "Item": "Salted Fries", "Unit Price": 79},
    {"Item ID": "PPF", "Item": "Peri Peri Fries", "Unit Price": 89},
    {"Item ID": "CoBF", "Item": "Corn Balls Full", "Unit Price": 159},
    {"Item ID": "VP", "Item": "Veggie Pizza Nachos", "Unit Price": 119},
    {"Item ID": "JBF", "Item": "Jalepeno Balls Full", "Unit Price": 159},
]

USERS = {
    "admin": "Gaurav",
    "staff1": "Chandan",
    "staff2": "Surya"
}

OUTLETS = ["Shailendra Nagar", "MG Road"]

CHANNELS = [
    "Dine-in",
    "Takeaway",
    "Delivery",
    "Zomato",
    "Swiggy"
]

PAYMENT_MODES = [
    "Cash",
    "Online",
    "Zomato Transfer",
    "Swiggy Transfer"
]


# ---------------- GOOGLE SHEETS ----------------

@st.cache_resource
def get_gsheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes
    )

    client = gspread.authorize(creds)

    sheet_name = st.secrets["google_sheet"]["name"]

    sh = client.open(sheet_name)

    ws = sh.worksheet("Orders")

    return ws


def ensure_headers(ws):
    existing = ws.row_values(1)

    if existing != HEADERS:
        ws.update("A1:N1", [HEADERS])


@st.cache_data(ttl=30)
def load_orders():
    ws = get_gsheet()

    ensure_headers(ws)

    records = ws.get_all_records()

    if not records:
        return pd.DataFrame(columns=HEADERS)

    df = pd.DataFrame(records)

    for c in HEADERS:
        if c not in df.columns:
            df[c] = ""

    return df[HEADERS]


def append_rows(rows):
    ws = get_gsheet()

    ensure_headers(ws)

    ws.append_rows(
        rows,
        value_input_option="USER_ENTERED",
        table_range="A1:N"
    )


def replace_all_orders(df):
    ws = get_gsheet()

    ws.clear()

    ws.update("A1:N1", [HEADERS])

    if not df.empty:
        values = (
            df.fillna("")
            .astype(str)
            .values
            .tolist()
        )

        ws.update(
            f"A2:N{len(values) + 1}",
            values
        )


# ---------------- HELPERS ----------------

def shift_for_time(dt):
    t = dt.time()

    if (
        t >= datetime.strptime("09:00", "%H:%M").time()
        and t < datetime.strptime("14:00", "%H:%M").time()
    ):
        return "Morning"

    if (
        t >= datetime.strptime("14:00", "%H:%M").time()
        and t < datetime.strptime("18:00", "%H:%M").time()
    ):
        return "Evening"

    if t >= datetime.strptime("18:00", "%H:%M").time():
        return "Night"

    return "Night"


def next_order_id(selected_date, df):
    prefix = pd.Timestamp(selected_date).strftime("%d%m%y")

    nums = []

    if not df.empty:
        for x in df["Order ID"].astype(str):

            if x.startswith(prefix):

                tail = x[len(prefix):]

                if tail.isdigit():
                    nums.append(int(tail))

    n = max(nums, default=0) + 1

    return f"{prefix}{n:03d}"


@st.cache_data(ttl=300)
def menu_df():

    try:
        ws = get_gsheet()

        mws = ws.spreadsheet.worksheet("Menu")

        data = mws.get_all_records()

        if data:

            m = pd.DataFrame(data)

            required = {
                "Item ID",
                "Item",
                "Unit Price"
            }

            if required.issubset(m.columns):

                return m[
                    ["Item ID", "Item", "Unit Price"]
                ]

    except Exception:
        pass

    return pd.DataFrame(DEFAULT_MENU)


# ---------------- LOGIN ----------------

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:

    st.title("🧀 TCC Orders")

    st.caption("Staff ordering system")

    with st.form("login_form"):

        name = st.text_input("Name")

        password = st.text_input(
            "Password",
            type="password"
        )

        submitted = st.form_submit_button(
            "Login",
            use_container_width=True
        )

        if submitted:

            if (
                name in USERS
                and USERS[name] == password
            ):

                st.session_state.logged_in = True
                st.session_state.user = name

                st.rerun()

            else:

                st.error(
                    "Invalid name or password."
                )

    st.stop()


# ---------------- APP ----------------

user = st.session_state.user

df = load_orders()

menu = menu_df()


# ---------------- SIDEBAR ----------------

st.sidebar.title("🧀 TCC")

st.sidebar.write(
    f"Logged in as **{user}**"
)

page = st.sidebar.radio(
    "Go to",
    [
        "New Order",
        "Today So Far",
        "Export"
    ]
)

if st.sidebar.button("Logout"):

    st.session_state.clear()

    st.rerun()


# ---------------- NEW ORDER ----------------

if page == "New Order":

    st.title("🛒 New Order")

    c1, c2, c3 = st.columns(3)

    with c1:

        order_date = st.date_input(
            "Date",
            value=date.today(),
            max_value=date.today()
        )

    with c2:

        outlet = st.selectbox(
            "Outlet",
            OUTLETS
        )

    with c3:

        channel = st.selectbox(
            "Channel",
            CHANNELS
        )


    c4, c5 = st.columns(2)

    with c4:

        payment = st.selectbox(
            "Payment Mode",
            PAYMENT_MODES
        )

    with c5:

        discount = st.number_input(
            "Order Discount",
            min_value=0.0,
            value=0.0,
            step=1.0
        )


    reason = ""

    if discount > 0:

        if channel == "Zomato":

            reason = "Zomato discount"

        elif channel == "Swiggy":

            reason = "Swiggy discount"

        else:

            reason = st.text_input(
                "Discount Reason"
            )


    # ---------------- CART ----------------

    st.subheader("Items")

    if "cart" not in st.session_state:

        st.session_state.cart = []


    items_by_label = {

        f"{r['Item ID']} — {r['Item']} — ₹{float(r['Unit Price']):g}": r

        for _, r in menu.iterrows()

    }


    # ---------------- ADD ITEM ----------------

    with st.form(
        "add_order_item_form",
        clear_on_submit=True
    ):

        c1, c2 = st.columns([4, 1])

        with c1:

            label = st.selectbox(
                "+ Add Order Item",
                [
                    "Select item"
                ] + list(items_by_label.keys())
            )

        with c2:

            qty = st.number_input(
                "Qty",
                min_value=1,
                value=1,
                step=1
            )


        add = st.form_submit_button(
            "Add Item",
            use_container_width=True
        )


        if add:

            if label == "Select item":

                st.warning(
                    "Select an item first."
                )

            else:

                r = items_by_label[label]

                st.session_state.cart.append({

                    "Item ID": str(
                        r["Item ID"]
                    ),

                    "Item": str(
                        r["Item"]
                    ),

                    "Unit Price": float(
                        r["Unit Price"]
                    ),

                    "Qty": int(qty)

                })

                st.rerun()


    # ---------------- CURRENT CART ----------------

    if st.session_state.cart:

        st.write("### Current Order")

        remove_idx = None


        for i, item in enumerate(
            st.session_state.cart
        ):

            a, b, c, d = st.columns(
                [4, 1.5, 1.5, 0.8]
            )


            with a:

                st.write(
                    f"**{item['Item ID']} — "
                    f"{item['Item']}**"
                )


            with b:

                st.write(
                    f"₹{item['Unit Price']:g}"
                )


            with c:

                new_qty = st.number_input(

                    "Qty",

                    min_value=1,

                    step=1,

                    value=item["Qty"],

                    key=f"cart_qty_{i}"

                )

                item["Qty"] = int(
                    new_qty
                )


            with d:

                if st.button(
                    "✕",
                    key=f"remove_cart_{i}"
                ):

                    remove_idx = i


        if remove_idx is not None:

            st.session_state.cart.pop(
                remove_idx
            )

            st.rerun()


        # ---------------- TOTAL ----------------

        subtotal = sum(

            x["Unit Price"] * x["Qty"]

            for x in st.session_state.cart

        )

        net_total = max(
            0,
            subtotal - discount
        )


        st.metric(
            "Order Total",
            f"₹{net_total:,.0f}"
        )


        # ---------------- SUBMIT ORDER ----------------

        if st.button(
            "SUBMIT ORDER",
            type="primary",
            use_container_width=True
        ):

            now = datetime.now()

            order_id = next_order_id(
                order_date,
                df
            )


            remaining_discount = float(
                discount
            )

            rows = []


            for idx, item in enumerate(
                st.session_state.cart
            ):

                gross = (
                    item["Unit Price"]
                    * item["Qty"]
                )


                row_discount = 0

                if idx == 0:

                    row_discount = min(
                        remaining_discount,
                        gross
                    )

                    remaining_discount -= (
                        row_discount
                    )


                net = (
                    gross
                    - row_discount
                )


                rows.append([

                    order_date.strftime(
                        "%d-%m-%y"
                    ),

                    outlet,

                    order_id,

                    channel,

                    item["Item ID"],

                    item["Item"],

                    item["Qty"],

                    item["Unit Price"],

                    row_discount,

                    reason,

                    payment,

                    net,

                    user,

                    shift_for_time(now)

                ])


            # IMPORTANT:
            # Append the complete order ONCE

            append_rows(rows)


            # Clear cached Google Sheet data

            load_orders.clear()


            # Clear cart

            st.session_state.cart = []


            st.success(
                f"Order {order_id} saved successfully."
            )

            st.rerun()


    else:

        st.info(
            "Add at least one item."
        )


# ---------------- TODAY ----------------

elif page == "Today So Far":

    st.title(
        f"📊 Today So Far — "
        f"{date.today().strftime('%d-%m-%Y')}"
    )


    today_str_dash = date.today().strftime(
        "%d-%m-%y"
    )


    today = df[
        df["Date"].astype(str)
        == today_str_dash
    ].copy()


    total = pd.to_numeric(
        today["Net Sale"],
        errors="coerce"
    ).fillna(0).sum()


    orders = today[
        "Order ID"
    ].nunique()


    qty = pd.to_numeric(
        today["Qty"],
        errors="coerce"
    ).fillna(0).sum()


    a, b, c = st.columns(3)

    a.metric(
        "Total Sales",
        f"₹{total:,.0f}"
    )

    b.metric(
        "Orders",
        int(orders)
    )

    c.metric(
        "Items Sold",
        int(qty)
    )


    if today.empty:

        st.info(
            "No orders yet today."
        )

    else:

        order_ids = list(
            today[
                "Order ID"
            ].astype(str).unique()
        )


        for oid in order_ids:

            order = today[
                today["Order ID"].astype(str)
                == oid
            ]


            order_total = pd.to_numeric(
                order["Net Sale"],
                errors="coerce"
            ).sum()


            with st.expander(
                f"Order {oid} — "
                f"₹{order_total:,.0f}"
            ):

                st.dataframe(
                    order,
                    use_container_width=True,
                    hide_index=True
                )

                st.caption(
                    "Editing can be enabled by "
                    "adding an admin/edit workflow; "
                    "historical dates are intentionally locked."
                )


# ---------------- EXPORT ----------------

else:

    st.title("📤 Export")

    st.caption(
        "Historical data is read-only from "
        "the ordering workflow. Export it "
        "for BI/Excel analysis."
    )


    df_export = df.copy()


    csv = (
        df_export
        .to_csv(index=False)
        .encode("utf-8")
    )


    st.download_button(

        "Download All Orders CSV",

        data=csv,

        file_name=(
            f"TCC_orders_"
            f"{datetime.now():%Y%m%d_%H%M%S}.csv"
        ),

        mime="text/csv",

        use_container_width=True

    )


    st.dataframe(
        df_export,
        use_container_width=True,
        hide_index=True
    )