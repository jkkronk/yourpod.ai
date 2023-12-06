from pydantic import BaseModel, Field
from typing import Optional
from openai import AsyncOpenAI

from elevenlabs import generate
import asyncio
from pydub import AudioSegment
import io
from pathlib import Path
from tempfile import NamedTemporaryFile
import os

class PodcastSectionOverview(BaseModel):
    length_in_seconds: int = Field(..., description="The length of the section in seconds.")
    description: str = Field(..., description="List of high level episode content.")

class PodcastIntroOutro(BaseModel):
    title: str
    intro_transcript: str
    outro_transcript: str
    length_in_minutes: float

class PodcastOverview(BaseModel):
    title: str
    description: str
    section_overviews: list[PodcastSectionOverview]


class PodcastSection(BaseModel):
    length_in_seconds: int
    transcript: str


class Podcast(PodcastOverview):
    """The full podcast, including the transcript."""
    transcript: str
    length_in_minutes: float
    sections: list[PodcastSection]

def generate_audio(podcast, elevenlabs_voice, openai_voice, openai_key):
    if elevenlabs_voice:
        audio = text_2_speech(podcast.transcript, elevenlabs_voice)
    else:
        # Use openai voice
        audio = asyncio.run(text_2_speech_openai(podcast, openai_voice, openai_api_key=openai_key))
    return audio

def text_2_speech(prompt, voice):
    audio_path = f"temp.mp3"
    print(f"Generating audio for voice {voice}, to file {audio_path}")

    # split prompt into chunks less than 5000 characters
    chunks = [prompt[i : i + 4950] for i in range(0, len(prompt), 4950)]

    concatenated_audio = AudioSegment.empty()  # Creating an empty audio segment
    for chunk in chunks:
        chunk_audio = generate(text=chunk, voice=voice, model="eleven_multilingual_v2")
        # Assuming that the generate function represents mp3
        audio_segment = AudioSegment.from_mp3(io.BytesIO(chunk_audio))
        concatenated_audio += audio_segment

    # Export concatenated audio to a file
    concatenated_audio.export(audio_path, format="mp3")

    # Get raw audio bytes to return
    buffer = io.BytesIO()
    concatenated_audio.export(buffer, format="mp3")
    raw_audio_bytes = buffer.getvalue()

    return raw_audio_bytes


async def generate_audio_chunk(client, voice, chunk, nr):
    response = await client.audio.speech.create(
        model="tts-1",
        voice=voice,
        input=chunk
    )
    with NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
        temp_file_path = temp_file.name  # Get the file path
        response.stream_to_file(temp_file_path)  # Use the file path here
    chunk_audio = AudioSegment.from_mp3(temp_file_path)  # Use the file path to load the audio
    # Optionally delete the temporary file if needed
    os.remove(temp_file_path)
    return chunk_audio


async def text_2_speech_openai(podcast: Podcast, voice, openai_api_key):
    client = AsyncOpenAI(api_key=openai_api_key)
    speech_file_path = Path(__file__).parent / "speech.mp3"

    print(f"Generating audio for voice {voice}, to file {speech_file_path}")

    chunks = [section.transcript for section in podcast.sections]

    # make sure that each chunk is less than 4000 characters, otherwise split the chunk in two entries
    while any([len(chunk) > 4000 for chunk in chunks]):
        new_chunks = []
        for chunk in chunks:
            if len(chunk) > 4000:
                new_chunks.append(chunk[:4000])
                new_chunks.append(chunk[4000:])
            else:
                new_chunks.append(chunk)
        chunks = new_chunks

    tasks = []
    for nr, chunk in enumerate(chunks):
        tasks.append(generate_audio_chunk(client, voice, chunk, nr))
    chunk_audios = await asyncio.gather(*tasks)

    concatenated_audio = AudioSegment.empty()  # Creating an empty audio segment
    for chunk_audio in chunk_audios:
        concatenated_audio += chunk_audio

    # Export concatenated audio to a file
    with NamedTemporaryFile(suffix=".mp3", delete=True) as temp_file:
        temp_file_path = temp_file.name  # Get the file path
        concatenated_audio.export(temp_file_path, format="mp3")
        # read audio file and return raw bytes
        with open(temp_file_path, "rb") as f:
            raw_audio_bytes = f.read()

    return raw_audio_bytes
