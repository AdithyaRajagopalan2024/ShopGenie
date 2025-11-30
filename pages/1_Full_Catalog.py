import streamlit as st
from productstore import store
import pandas as pd

st.set_page_config(
    page_title="Full Catalog",
    layout="wide"
)

st.title("Full Product Catalog")

products = store.list_products()

if not products:
    st.warning("No products found in the catalog.")
else:
    for product in products:

        with st.container():
            col1, col2 = st.columns([1, 3])

            # LEFT: Product Image
            with col1:
                # if "image" in product and product["image"]:
                st.image(f"static/images/{product['image']}", width=180)
                # else:
                #     st.image("static/images/1.jpeg", width=180)

            # RIGHT: Product Details
            with col2:
                st.subheader(product.get("name", "Unnamed Product"))
                st.write(f"**Price:** Rs.{product.get('price', 'N/A')}")
                st.write(f"**Brand:** {product.get('brand', 'N/A')}")
                st.write(f"**Category:** {product.get('category', 'N/A')}")
                st.write(f"**Color:** {product.get('color', 'N/A')}")
                st.write(f"**Rating:** {product.get('rating', 'N/A')}")
                st.write(f"**Stock:** {product.get('stock', 'N/A')}")
                st.write(f"**Features:** {product.get('features', [])}")

            st.markdown("---")
