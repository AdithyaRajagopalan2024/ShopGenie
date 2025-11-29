import streamlit as st
from productstore import store
import pandas as pd

st.set_page_config(
    page_title="Full Catalog",
    layout="wide"
)

st.title("Full Product Catalog")

products = store.list_products()

if products:
    # Convert list of product dicts to a pandas DataFrame for better display
    df = pd.DataFrame(products)
    # Reorder columns for a more logical presentation
    display_columns = ['id', 'name', 'category', 'brand', 'price', 'color', 'rating', 'stock', 'features']
    # Ensure all display columns exist in the dataframe
    df_display = df[[col for col in display_columns if col in df.columns]]
    st.dataframe(df_display, use_container_width=True)
else:
    st.warning("No products found in the catalog.")

