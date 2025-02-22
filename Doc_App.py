import os
import json
import pdfplumber
from groq import Groq
from fpdf import FPDF
from dotenv import load_dotenv
import streamlit as st

# Load API key from .env
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# System prompt
system_prompt = """
You are a helpful assistant. Extract the following key-value pairs from the provided text:
- Policy Number
- POLICY HOLDER NAMED INSURED
- Policy Period Inception
- Policy Period Expiration
- Construction
- Year Built
- Not more than 100 from hydrant
- Not more than 5 miles from Fire Dept.
- Pro Rata Additional Surcharges
- Forms and Endorsements
- Section 1 - Coverages, Please return the values which belong to this table only.
- Section 2 - Coverages, Please return as it is and Please return the values which belong to this table only.

Return the data as a valid JSON object. Ensure the values are exactly as they appear in the text. For example:
- If the text says "Not more than 100 from hydrant: Loyalty Customer", return "Loyalty Customer".
- If the text says "Not more than 5 miles from Fire Dept.: Bundle Package", return "Bundle Package".
- If the text says "Pro Rata Additional Surcharges = 0", return "Sprinkler System".
- Do not return boolean values (True/False) for any field.
"""

# Streamlit app title
st.set_page_config(page_title="Intelligent Doc Analyzer", layout="wide")
st.title("Intelligent Doc Analyzer")

# Sidebar for PDF upload
st.sidebar.header("Upload PDF")
uploaded_file = st.sidebar.file_uploader("Choose a PDF file", type="pdf")

def extract_text_from_pdf(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text()
    return text

def query_groq_api(text, model="llama3-70b-8192"):
    client = Groq(api_key=GROQ_API_KEY)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": text
            }
        ],
        response_format={"type": "json_object"}  # Ensure the response is JSON
    )
    # Parse the JSON string into a Python dictionary
    try:
        return json.loads(response.choices[0].message.content)
    except json.JSONDecodeError:
        raise ValueError("Failed to parse Groq API response as JSON.")

def create_summary_pdf(data, output_path):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # Add extracted data
    for key, value in data.items():
        if isinstance(value, dict):
            # Convert dictionary to a formatted string
            value_str = "\n".join([f"{k}: {v}" for k, v in value.items()])
        elif isinstance(value, list):
            # Convert list to a comma-separated string
            value_str = ", ".join(str(item) for item in value)
        else:
            value_str = str(value)
        
        # Use multi_cell for text wrapping
        pdf.multi_cell(200, 10, txt=f"{key}: {value_str}", align="L")
        pdf.ln(2)  # Add a small space between lines
    
    # Add a 3-4 line summary
    pdf.ln(10)  # Add some space
    pdf.set_font("Arial", size=12, style="B")
    pdf.cell(200, 10, txt="Summary:", ln=True)
    pdf.set_font("Arial", size=12)
    summary = [
        "This report summarizes the key details of the insurance policy.",
        "It includes information about the policy holder, policy number, and coverage details.",
        "Additional details such as construction type, year built, and discounts are also included.",
        "Please review the document for further information."
    ]
    for line in summary:
        pdf.multi_cell(200, 10, txt=line, align="L")
        pdf.ln(2)  # Add a small space between lines
    
    pdf.output(output_path)

def main(pdf_path, output_pdf_path):
    # Step 1: Extract text from PDF
    extracted_text = extract_text_from_pdf(pdf_path)
    
    # Step 2: Query Groq API
    structured_data = query_groq_api(extracted_text)
    
    # Step 3: Generate summary PDF
    create_summary_pdf(structured_data, output_pdf_path)
    
    return structured_data

if uploaded_file is not None:
    # Save the uploaded file temporarily
    with open("temp.pdf", "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    # Process the PDF
    st.sidebar.success("File uploaded successfully!")
    st.header("Extracted Information")
    
    # Run the main function
    output_pdf_path = "summary_report_V1.pdf"
    structured_data = main("temp.pdf", output_pdf_path)
    
    # Display the extracted data
    st.subheader("Extracted Data")
    st.json(structured_data)
    
    # Provide a download link for the generated PDF
    st.subheader("Download Summary Report")
    with open(output_pdf_path, "rb") as f:
        st.download_button(
            label="Download PDF",
            data=f,
            file_name=output_pdf_path,
            mime="application/pdf"
        )
else:
    st.sidebar.warning("Please upload a PDF file to proceed.")
