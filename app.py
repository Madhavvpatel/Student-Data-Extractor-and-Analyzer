import streamlit as st
import pandas as pd
import re
import pytesseract
from PIL import Image
import pdf2image
import math
from PyPDF2 import PdfReader
import io

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

# Function to extract text from image file
def extract_text_from_image(image_file):
    image = Image.open(image_file)
    text = pytesseract.image_to_string(image)
    return text

# General function to extract data from text using regex
def extract_data_from_text(text):
    data = []
    
    # Regex pattern to handle roll numbers, names, and decimal marks/status
    pattern = re.compile(r"(\d{5,}[A-Z]*[A-Z]*)\s+([A-Za-z\s]+?)\s+(\d+(\.\d+)?|A|None|Absent)", re.IGNORECASE)
    matches = pattern.findall(text)
    
    for match in matches:
        enrollment_no = match[0].strip()
        name = match[1].strip()
        marks_or_status = match[2].strip()

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
    
    # Handling 'Present' status
    df.loc[(df['Marks'].notnull()) & (df['Marks'] >= 7), 'Status'] = 'Pass'
    df.loc[(df['Marks'].notnull()) & (df['Marks'] < 7), 'Status'] = 'Fail'
    
    # Update status for 'Absent'
    df['Status'] = df['Status'].fillna('Absent')
    
    passed = df[df['Status'] == 'Pass']
    failed = df[df['Status'] == 'Fail']
    absent = df[df['Status'] == 'Absent']
    
    return passed, failed, absent

# Function to generate Excel sheets
def generate_excel(passed, failed, absent, output_path):
    with pd.ExcelWriter(output_path) as writer:
        if not passed.empty:
            passed.to_excel(writer, sheet_name="Passed Students", index=False)
        if not failed.empty:
            failed.to_excel(writer, sheet_name="Failed Students", index=False)
        if not absent.empty:
            absent.to_excel(writer, sheet_name="Absent Students", index=False)

# Streamlit app
def main():
    st.title("Student Data Processing")

    uploaded_file = st.file_uploader("Choose a file", type=["pdf", "png", "jpeg", "jpg"])
    
    if uploaded_file is not None:
        file_extension = uploaded_file.name.split('.')[-1].lower()
        
        if file_extension == 'pdf':
            text = extract_text_from_pdf(uploaded_file)
            if not text.strip():
                st.write("No text extracted from PDF, attempting OCR...")
                text = extract_text_using_ocr(uploaded_file)
        elif file_extension in ['png', 'jpeg', 'jpg']:
            text = extract_text_from_image(uploaded_file)
        else:
            st.write("Unsupported file type")
            return

        if not text.strip():
            st.write("No data extracted. Please check the file format.")
            return
        
        # Extract data using regex
        data = extract_data_from_text(text)
        
        # Process data
        passed, failed, absent = process_data(data)
        
        # Display DataFrames
        st.write("Extracted Data:", data)
        st.write("Passed Students", passed)
        st.write("Failed Students", failed)
        st.write("Absent Students", absent)

        # Create downloadable Excel file
            # output = BytesIO()
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
