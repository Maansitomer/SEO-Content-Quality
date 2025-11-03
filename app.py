import streamlit as st
import joblib
import pandas as pd
from bs4 import BeautifulSoup
import textstat
import re
from sklearn.metrics.pairwise import cosine_similarity
import warnings
import time

# Suppress warnings
warnings.filterwarnings('ignore')

# --- 1. Page Configuration ---
st.set_page_config(
    page_title="SEO Content Analyzer",
    page_icon="🤖",
    layout="wide"
)

# --- 2. COPY-PASTE YOUR HELPER FUNCTIONS ---

def process_html(html_content):
    """Parses HTML, cleans text, and extracts features."""
    if not isinstance(html_content, str):
        return "", 0, 0 
    
    soup = BeautifulSoup(html_content, 'html.parser')
    text = soup.get_text(separator=' ', strip=True)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^a-zA-Z\s]', '', text).lower()
    
    try:
        # Using Flesch-Kincaid Grade Level
        readability = textstat.flesch_kincaid_grade(text)
    except:
        # Assign a high (bad) score if textstat fails
        readability = 100 
        
    word_count = len(text.split())
    
    return text, readability, word_count

# This is our rule-based model from the notebook
def predict_quality(readability, word_count):
    """
    Predicts content quality based on the rule
    derived from the dataset (Word Count > 2452.0).
    """
    # This rule is hard-coded from your notebook's median
    if word_count > 2452.0:
        return "Good"
    else:
        return "Bad"

# --- 3. LOAD YOUR SAVED MODELS ---
@st.cache_resource
def load_models():
    """Loads the saved vectorizer and TF-IDF matrix."""
    try:
        vectorizer = joblib.load('tfidf_vectorizer.joblib')
        matrix = joblib.load('tfidf_matrix.joblib')
        return vectorizer, matrix
    except FileNotFoundError:
        st.error("Model files not found! 🔴")
        st.error("Please run the Jupyter notebook to create:")
        st.code("tfidf_vectorizer.joblib\ntfidf_matrix.joblib")
        return None, None

vectorizer, tfidf_matrix = load_models()

# --- 4. BUILD THE STREAMLIT INTERFACE ---

# --- Sidebar ---
st.sidebar.title("SEO Content Analyzer 🤖")
st.sidebar.markdown("Paste your raw HTML content below to analyze its quality and check for duplicates.")

html_input = st.sidebar.text_area("Paste HTML Here", height=300)
analyze_button = st.sidebar.button("Analyze Content", type="primary")

# --- Main Page ---
st.title("SEO Content Quality & Duplicate Detection")
st.markdown("This tool analyzes your HTML content to assess its **SEO Quality** and check for **Duplicate Content** against the project dataset.")
st.divider()

if not analyze_button:
    st.info("⬅️ Paste your HTML in the sidebar and click 'Analyze Content' to begin.")

if analyze_button:
    if not html_input:
        st.warning("Please paste some HTML content in the sidebar to analyze.")
    elif vectorizer is None:
        st.error("Models are not loaded. Cannot perform analysis.")
    else:
        # Show a spinner while processing
        with st.spinner('Analyzing... This may take a moment.'):
            # 1. Process the input
            cleaned_text, readability, word_count = process_html(html_input)
            
            # 2. Predict Quality
            quality_label = predict_quality(readability, word_count)
            
            # 3. Detect Duplicates
            new_text_vector = vectorizer.transform([cleaned_text])
            cosine_sims = cosine_similarity(new_text_vector, tfidf_matrix)
            
            # Get the highest similarity score
            max_similarity = cosine_sims.max()
            time.sleep(1) # Simulate a short delay for a better spinner experience

        st.subheader("Analysis Results")
        
        # Create tabs for organized output
        tab1, tab2 = st.tabs(["📊 Quality Score", "🔎 Duplicate Detection"])
        
        # --- Quality Score Tab ---
        with tab1:
            if quality_label == "Good":
                st.success(f"**Predicted Quality: Good**", icon="👍")
                st.markdown(f"**Reason:** The word count of **{word_count}** is greater than the dataset median of 2452.")
            else:
                st.error(f"**Predicted Quality: Bad**", icon="👎")
                st.markdown(f"**Reason:** The word count of **{word_count}** is less than or equal to the dataset median of 2452.")
            
            st.divider()
            
            st.subheader("Content Metrics")
            col1, col2 = st.columns(2)
            col1.metric("Word Count", f"{word_count}", help="Total number of words in the content.")
            col2.metric("Readability (Grade)", f"{readability:.1f}", help="Flesch-Kincaid Grade Level. Lower is generally easier to read.")

        # --- Duplicate Detection Tab ---
        with tab2:
            st.subheader("Similarity Score")
            st.metric("Highest Similarity", f"{max_similarity*100:.2f}%", help="Similarity to the most similar article in the dataset.")
            
            if max_similarity > 0.90:
                st.error("🚨 **High-Risk:** This content is a likely near-duplicate of existing content.")
            elif max_similarity > 0.70:
                st.warning("⚠️ **Warning:** This content has significant similarity to existing content.")
            else:
                st.success("✅ **Original:** This content appears to be original.")
            
            st.divider()
            st.info("This score represents the similarity to the most similar article in the original dataset (using TF-IDF & Cosine Similarity).")
            
            with st.expander("See Raw Cleaned Text"):
                st.text(cleaned_text)