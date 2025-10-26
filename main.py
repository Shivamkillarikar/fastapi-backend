from fastapi import FastAPI, UploadFile, Form, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Mail, Attachment, FileContent, FileName, FileType, Disposition
)
import base64
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize FastAPI app
app = FastAPI()

# Allow React frontend or any origin for now (can restrict later)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # change to your frontend URL later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------- EMAIL SENDER ----------------------
def send_email(body: str, image_file: UploadFile = None):
    sg = SendGridAPIClient(api_key=os.getenv("SENDGRID_API_KEY"))
    from_email = "shivamkillarikar007@gmail.com"
    to_email = "shivamkillarikar22@gmail.com"
    
    mail = Mail(from_email, to_email, "Citizen Query", body)

    # If user uploaded an image → attach it
    if image_file:
        file_data = image_file.file.read()
        encoded_file = base64.b64encode(file_data).decode()
        attachment = Attachment(
            FileContent(encoded_file),
            FileName(image_file.filename),
            FileType("image/jpeg"),
            Disposition("attachment"),
        )
        mail.attachment = attachment

    response = sg.client.mail.send.post(request_body=mail.get())
    return response.status_code

# ---------------------- FASTAPI ROUTE ----------------------
@app.post("/")
async def send_report(
    name: str = Form(...),
    email: str = Form(...),
    location: str = Form(...),
    complaint: str = Form(...),
    image: UploadFile = File(None)
):
    """
    Accepts:
    - name, email, location, complaint text
    - optional image
    Returns:
    - AI-generated email and status
    """

    # 1️⃣ Create prompt for GPT
    prompt = f"""
    You are an AI assistant for the Brihanmumbai Municipal Corporation (BMC).
    Your role is to draft clear, formal, and polite complaint or report emails to
    the Municipal Commissioner regarding civic or administrative issues reported by citizens.

    The email should always follow this format:

    Subject: <Short summary of the issue>

    Dear Municipal Commissioner,

    This email is sent by a concerned citizen named {name} from {location}.
    They are reporting the following issue:

    {complaint}

    Kindly take the necessary action at the earliest.

    Thank you for your attention.

    Best regards,  
    {name}  
    Contact: {email}
    """

    # 2️⃣ Generate email text
    ai_response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    email_body = ai_response.choices[0].message.content

    # 3️⃣ Send email with optional image
    status_code = send_email(email_body, image)

    # 4️⃣ Return response to frontend
    if status_code == 202:
        return {"status": "success", "message": "Email sent successfully", "email_body": email_body}
    else:
        return {"status": "error", "message": f"Failed to send email (code {status_code})", "email_body": email_body}

