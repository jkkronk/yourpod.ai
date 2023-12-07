import streamlit as st
import datetime
import generate_from_topic
import generate_from_pdf
import podcast
from elevenlabs import clone, voices, set_api_key
from tempfile import NamedTemporaryFile

st.set_page_config(
    page_title="YourPod.ai",
    page_icon="🎙",
    layout="centered",
    initial_sidebar_state="auto",
)

def initialize_session():
    keys = ['session_id', 'openai_api_key', 'elevenlabs_api_key',
            'openai_voice', 'elevenlabs_voice', 'voice_cloning_temp_file', 'podcast_length']
    for key in keys:
        if key not in st.session_state:
            st.session_state[key] = None

initialize_session()

st.title("YourPod.ai")

# Sidebar controls
openai_api_key = st.sidebar.text_input("OpenAI API Key")
if openai_api_key.startswith("sk-"):
    st.session_state.openai_api_key = openai_api_key
    st.session_state.podcast_length = st.sidebar.slider(
        "How long would you like the podcast to be? (mins)", 2, 25, 5
    )
    st.session_state.openai_voice = st.sidebar.selectbox(
        "Pick your OpenAI podcast host voice.", ["alloy", "echo", "fable", "onyx", "nova", "shimmer"], index=5
    )
else:
    st.sidebar.warning("Please enter your Open AI key", icon="⚠️")

elevenlabs_api_key = st.sidebar.text_input("Elevenlabs API Key")
if elevenlabs_api_key:
    st.session_state.elevenlabs_api_key = elevenlabs_api_key
    set_api_key(elevenlabs_api_key)
    voice_cloning = st.sidebar.checkbox("Voice cloning")
    if voice_cloning:
        voice_cloning_file = st.sidebar.file_uploader(
            "Upload an audio file to clone the voice from.", type=["wav"]
        )
        if voice_cloning_file:
            with NamedTemporaryFile(suffix=".mp3", delete=True) as temp_file:
                temp_file_name = temp_file.name  # Get the file path
                with open(temp_file_name, "wb") as f:
                    f.write(voice_cloning_file.read())
                st.session_state.elevenlabs_voice = clone(
                    name="my_generated_voice_"+str(datetime.datetime.now()),
                    description="Custom voice",
                    files=[temp_file_name],
                )
    else:
        st.session_state.elevenlabs_voice = st.sidebar.selectbox(
            "Pick your podcast host voice.", [v.name for v in voices()]
        )
else:
    st.sidebar.warning("Please enter your Elevenlabs API key for more custom voices and voice cloning.", icon="⚠️")

# Main window
with st.form("text"):
    text = st.text_area("Create a podcast about...")
    submitted = st.form_submit_button("Generate From Text")
    if submitted:
        if not st.session_state.openai_api_key:
            st.warning("Please enter your OpenAI API key!", icon="⚠️")
        else:
            st.success("Generating podcast... This can take a few minutes.", icon="🎙")
            with st.spinner('Wait for it...'):
                input_text = text
                podcast_overview = generate_from_topic.get_podcast_overview(input_text, st.session_state.podcast_length, openai_api_key=st.session_state.openai_api_key)
                st.success(f"Outline Done! -- Title: {podcast_overview.title} -- Sections To Generate: {len(podcast_overview.section_overviews)}", icon="✅")
                new_podcast = generate_podcast.Podcast(**podcast_overview.dict(), length_in_minutes=0, transcript="", sections=[])

                bar = st.progress(0, text="Generating sections...")
                for nr, section_overview in enumerate(podcast_overview.section_overviews):
                    bar.progress((nr+1)/len(podcast_overview.section_overviews), text=f"Generating section {nr+1}/{len(podcast_overview.section_overviews)}...")
                    section = generate_from_topic.get_podcast_section(podcast_overview, section_overview, new_podcast, desired_length=st.session_state.podcast_length, openai_api_key=st.session_state.openai_api_key)
                    if nr > 0 and section.sound_effect_intro:
                        new_podcast.transcript += "\n\n" + f"[{section.sound_effect_intro}]"
                    new_podcast.transcript += "\n\n" + section.transcript
                    new_podcast.length_in_minutes += section.length_in_seconds / 60
                    new_podcast.sections.append(section)

            st.success("Transcript Done!", icon="✅")
            st.info(new_podcast.transcript)
            with st.spinner('Generating Audio...'):
                audio = podcast.generate_audio(new_podcast, st.session_state.elevenlabs_voice, st.session_state.openai_voice, st.session_state.openai_api_key)
            st.audio(audio)

st.text("OR")

with st.form("pdf"):
    pdf_file = st.file_uploader("Upload an PDF File to Generate Podcast", type=["pdf"])
    submitted = st.form_submit_button("Generate From PDF")
    if submitted:
        if not st.session_state.openai_api_key:
            st.warning("Please enter your OpenAI API key!", icon="⚠️")
        else:
            st.success("Generating podcast... This can take a few minutes.", icon="🎙")
            pdf_podcast = generate_from_pdf.PdfTopic(pdf_file, st.session_state.openai_api_key)
            new_podcast = pdf_podcast.generate_podcast()

            for sec in new_podcast.sections:
                print("\n SECTION: " + sec.transcript)

            st.success("Transcript Done! -- Title: {podcast.title}" , icon="✅")
            st.info(new_podcast.transcript)

            with st.spinner('Generating Audio...'):
                audio = podcast.generate_audio(new_podcast, st.session_state.elevenlabs_voice,
                                                        st.session_state.openai_voice, st.session_state.openai_api_key)
            st.audio(audio)