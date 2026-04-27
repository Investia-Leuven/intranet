import streamlit as st

st.markdown("""
<button onclick="alert('Hello from HTML!')">Click Me (HTML)</button>
""", unsafe_allow_html=True)

if st.button("Click Me (Streamlit)"):
    st.write("Streamlit button clicked")
