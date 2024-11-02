import openai
import streamlit as st
import base64
from streamlit.components.v1 import html
import pyperclip

# Configuration for the chatbot
config = {
    "model_name": "gpt-4o-mini",
    "temperature": 0,
    "max_tokens": 3000
}

# Load the password from Streamlit secrets (loaded when needed)
APP_PASSWORD = None

# Initialize session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "conversation" not in st.session_state:
    st.session_state.conversation = [{'role': 'system', 'content': "# Welcome to the medical chatbot."}]

if "user_messages" not in st.session_state:
    st.session_state.user_messages = []

if "all_messages" not in st.session_state:
    st.session_state.all_messages = []

if "transcription" not in st.session_state:
    st.session_state.transcription = ""

if "image_analysis" not in st.session_state:
    st.session_state.image_analysis = []

if "audio_data" not in st.session_state:
    st.session_state.audio_data = None

# Function to initialize OpenAI client only after login
def initialize_client():
    api_key = st.secrets.get("OPENAI_API_KEY")
    if not api_key:
        st.warning("Please enter your OpenAI API key to continue.")
        return None
    return openai.Client(api_key=api_key)

# Function to transcribe audio using Whisper API
def transcribe_audio(client, audio_bytes):
    try:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=("audio.wav", audio_bytes, "audio/wav")
        )
        return transcript.text
    except openai.error.InvalidRequestError:
        st.error("Invalid audio format. Please try again.")
    except openai.error.AuthenticationError:
        st.error("Authentication failed. Please check the API key.")
    except Exception as e:
        st.error(f"Unexpected error: {str(e)}")
    return None

# Function to analyze image using OpenAI API
def analyze_image(client, image_file):
    try:
        encoded_image = base64.b64encode(image_file.getvalue()).decode()
        response = client.chat.completions.create(
            model=config["model_name"],
            messages=[
                {
                    "role": "user",
                    "content": "You are an assistant for a radiologist. Provide the most notable radiological observations and suggest the main diagnostic hypothesis.",
                },
                {
                    "role": "user",
                    "content": {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"}}
                }
            ],
            max_tokens=300,
        )
        return response.choices[0].message.content
    except openai.error.InvalidRequestError:
        st.error("Invalid image format. Please try again.")
    except openai.error.AuthenticationError:
        st.error("Authentication failed. Please check the API key.")
    except Exception as e:
        st.error(f"Unexpected error: {str(e)}")
    return None

# Function to display the login page
def login_page():
    global APP_PASSWORD
    if APP_PASSWORD is None:
        APP_PASSWORD = st.secrets.get("APP_PASSWORD")
    
    st.markdown("<h1 style='color: purple;'>Asclepius Login</h1>", unsafe_allow_html=True)
    password = st.text_input("Digite a senha:", type="password")
    if st.button("Login"):
        if password == APP_PASSWORD:
            st.session_state.logged_in = True
            st.experimental_rerun()
        else:
            st.error("Senha incorreta. Por favor, tente novamente.")

# Function to call OpenAI API
def chatbot(client, conversation):
    with st.spinner('Processing, please wait...'):
        try:
            response = client.chat.completions.create(
                model=config["model_name"],
                messages=conversation,
                temperature=config["temperature"],
                max_tokens=config["max_tokens"]
            )
            return response.choices[0].message.content
        except openai.error.AuthenticationError:
            st.error("Authentication failed. Please check the API key.")
        except Exception as e:
            st.error(f"Unexpected error: {str(e)}")
    return None

# Main function to display the main content
def main_page(client):
    st.markdown("<h1 style='color: purple;'>Asclepius</h1>", unsafe_allow_html=True)
    st.header("Transcription and Image Analysis")

    # Audio Recording and Transcription
    st.header("Transcription of Audio")
    audio_file = st.file_uploader("Upload an audio file", type=["wav", "mp3", "m4a"])
    if audio_file is not None:
        st.audio(audio_file, format="audio/wav")
        if st.button("Transcribe Audio"):
            transcription = transcribe_audio(client, audio_file.getvalue())
            if transcription:
                st.session_state.transcription = transcription
                st.write("Transcription:", transcription)
                st.session_state.all_messages.append(f'TRANSCRIPTION: {transcription}')

    # Image Upload and Analysis
    st.header("Upload a Medical Image")
    image_file = st.file_uploader("Upload a medical image", type=["jpg", "jpeg", "png"])
    if image_file is not None:
        st.image(image_file, caption="Image", use_column_width=True)
        if st.button("Analyze Image"):
            image_analysis = analyze_image(client, image_file)
            if image_analysis:
                st.session_state.image_analysis.append(image_analysis)
                st.write("Image Analysis", image_analysis)
                st.session_state.all_messages.append(f'IMAGE ANALYSIS: {image_analysis}')

    # Text Input for Clinical Case
    st.header("Describe the clinical case. Type 'PRONTO' when done.")
    if prompt := st.text_area("Luis:", height=200, expand=True):
        if prompt.strip().upper() not in ["PRONTO", "PRESCRIÇÃO"]:
            st.session_state.user_messages.append(prompt)
            st.session_state.all_messages.append(f'Luis: {prompt}')
            st.session_state.conversation.append({'role': 'user', 'content': prompt})

            response = chatbot(client, st.session_state.conversation)
            if response:
                st.session_state.conversation.append({'role': 'assistant', 'content': response})
                st.session_state.all_messages.append(f'RECEPÇÃO: {response}')
                st.write(f'**RECEPÇÃO:** {response}')
        elif prompt.strip().upper() == "PRONTO":
            st.write("Generating notes and reports...")
            
            # Generate Reports
            generate_reports(client)
        elif prompt.strip().upper() == "PRESCRIÇÃO":
            st.write("Generating medical prescription...")
            generate_prescription(client)

# Generate reports function
def generate_reports(client):
    # Include transcription and image analysis in the notes
    all_input = '\n\n'.join(st.session_state.all_messages)
    if st.session_state.transcription:
        all_input += f"\n\nAudio Transcription:\n{st.session_state.transcription}"
    if st.session_state.image_analysis:
        all_input += f"\n\nImage Analysis:\n" + "\n".join(st.session_state.image_analysis)

    # Generate Intake Notes
    st.write("**Generating anamnesis...**")
    notes_conversation = [{'role': 'system', 'content': "# Prepare Notes"}]
    notes_conversation.append({'role': 'user', 'content': all_input})
    notes = chatbot(client, notes_conversation)
    if notes:
        st.write(f'**Notes Version:**\n\n{notes}')
        pyperclip.copy(notes)
        st.write("Notes copied to clipboard.")

# Generate prescription function
def generate_prescription(client):
    if 'notes' in st.session_state:
        prescription_conversation = [{'role': 'system', 'content': "# Medical Prescription"}]
        prescription_conversation.append({'role': 'user', 'content': st.session_state.notes})
        prescription = chatbot(client, prescription_conversation)
        if prescription:
            st.write(f'**Medical Prescription:**\n\n{prescription}')
            pyperclip.copy(prescription)
            st.write("Prescription copied to clipboard.")

# Main Execution Flow
if st.session_state.logged_in:
    client = initialize_client()
    if client:
        main_page(client)
else:
    login_page()
