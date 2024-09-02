import streamlit as st
import pandas as pd
from PyPDF2 import PdfReader
import re
import pytesseract
from PIL import Image
import pdf2image
import math
from io import BytesIO

# Function to extract text from PDF
def extract_text_from_pdf(pdf_file):
    reader = PdfReader(pdf_file)
    full_text = ""
    for page in reader.pages:
        full_text += page.extract_text() + "\n"
    return full_text

# Function to convert PDF to image and use OCR to extract text
def extract_text_using_ocr(pdf_file):
    images = pdf2image.convert_from_bytes(pdf_file.read())
    full_text = ""
    for image in images:
        text = pytesseract.image_to_string(image)
        full_text += text + "\n"
    return full_text

# General function to extract data from text using regex
def extract_data_from_text(text):
    data = []
    
    # Regex pattern to handle roll numbers starting with '0801', names, and decimal marks/status
    pattern = re.compile(r"(0801[A-Z\d]*[A-Z]?)\s+([A-Za-z\s]+?)\s+(\d+(\.\d+)?|A|None|Absent)", re.IGNORECASE)
    matches = pattern.findall(text)
    
    for match in matches:
        enrollment_no = match[0].strip()
        name = match[1].strip()
        marks_or_status = match[2].strip() if match[2] else "None"  # Handle missing marks
        
        if 'D' in enrollment_no.upper():  # Special handling for cases with 'D'
            st.write(f"Enrollment Number with D: {enrollment_no}, Name: {name}, Marks/Status: {marks_or_status}")

        if marks_or_status.replace('.', '', 1).isdigit():
            marks = math.ceil(float(marks_or_status))  # Use math.ceil() to round up
            status = "Present"
        elif marks_or_status.lower() in ["a", "absent", "none"]:
            marks = None
            status = "Absent"
        else:
            marks = None
            status = "Unknown"  # Handle unknown statuses
        
        data.append((enrollment_no, name, marks, status))
    
    return data

# Function to process the data
def process_data(data):
    df = pd.DataFrame(data, columns=['Enrollment No', 'Name', 'Marks', 'Status'])
    
    # Drop rows where 'Enrollment No' or 'Name' is missing
    df.dropna(subset=['Enrollment No', 'Name'], inplace=True)
    
    # Debugging: Print out DataFrame for inspection
    st.write("DataFrame:\n", df.head(10))  # Print first 10 rows for inspection
    
    # Handling 'Present' status
    df.loc[(df['Marks'].notnull()) & (df['Marks'] >= 7), 'Status'] = 'Pass'
    df.loc[(df['Marks'].notnull()) & (df['Marks'] < 7), 'Status'] = 'Fail'
    
    # Update status for 'Absent'
    df['Status'] = df['Status'].fillna('Absent')
    
    passed = df[df['Status'] == 'Pass']
    failed = df[df['Status'] == 'Fail']
    absent = df[df['Status'] == 'Absent']
    
    return passed, failed, absent

# Streamlit UI
def main():
    st.title("Student Data Processing App")
    
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf", type="png", type="jpeg", type="jpg")
    
    if uploaded_file is not None:
        st.write("Processing file...")
        
        # Extract text from the PDF
        text = extract_text_from_pdf(uploaded_file)
        
        # If no text is extracted, try using OCR
        if not text.strip():
            st.write("No text extracted from PDF, attempting OCR...")
            text = extract_text_using_ocr(uploaded_file)
        
        if not text.strip():
            st.write("No data extracted. Please check the PDF format.")
        else:
            # Extract data using regex
            data = extract_data_from_text(text)
            
            # Print extracted data for debugging
            st.write("Extracted Data:", data)
            
            passed, failed, absent = process_data(data)
            
            # Print DataFrames for debugging
            st.write("\nPassed Students:\n", passed)
            st.write("\nFailed Students:\n", failed)
            st.write("\nAbsent Students:\n", absent)
            
            # Create downloadable Excel file
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                if not passed.empty:
                    passed.to_excel(writer, sheet_name="Passed Students", index=False)
                if not failed.empty:
                    failed.to_excel(writer, sheet_name="Failed Students", index=False)
                if not absent.empty:
                    absent.to_excel(writer, sheet_name="Absent Students", index=False)
            
            output.seek(0)
            st.download_button(
                label="Download Excel file",
                data=output,
                file_name="student_marks.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

if __name__ == "__main__":
    main()
