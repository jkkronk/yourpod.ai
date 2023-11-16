import openai 
import instructor
from pydantic import BaseModel, Field
from elevenlabs import voices, generate, set_api_key
from aiohttp import ClientSession
import asyncio
from pydub import AudioSegment
import io 

instructor.patch()


class PodcastOverview(BaseModel):
  title: str
  description: str
  podcast_length_in_mins: int
  description_of_episode_cover_image: str
  episodes: list[str] = Field(... , description="List of high level episode content.")


def get_podcast_overview(input_text, podcast_length) -> PodcastOverview:
  prompt = f"""
You are a podcast host that is explaining {input_text} to your audience.
You are writing a podcast that consists of {3} episodes of {podcast_length//3} minutes each.

Before we start writing the detailed transcript, lets write a outline of the podcast.
Describe the title of the podcast, the description of the podcast, 
the summary of the podcast, the description of the podcast cover image.

Then describe each episode of the podcast, with a high level summary of what you will talk about in each episode.
"""
  print(f"Prompt: {prompt}")
  overview: PodcastOverview = openai.ChatCompletion.create(
  model="gpt-4",
  response_model=PodcastOverview,
  messages=[
      {"role": "user", "content": prompt},
  ]
  )
  print(f"Overview: {overview}")
  return overview


class PodcastSection(BaseModel):
    episode_length_in_mins: int
    episode_transcript: str


async def get_podcast_section(podcast_overview: PodcastOverview, section) -> PodcastSection:
  """Generate a podcast section from a podcast overview."""
  prompt = f"""
You are a podcast host that is explaining {podcast_overview.title} to your audience.
The podcast is about {podcast_overview.description}.

The podcast has the following episodes: 
{podcast_overview.episodes}

You are now writing the transcript for the {section} of the podcast.

Write the detailed transcript for this podcast episode.
The episode should be about 5 minutes long.
"""
  print(f"Prompt: {prompt}")
  section: PodcastSection = await openai.ChatCompletion.acreate(
    model="gpt-4-1106-preview",
    response_model=PodcastSection,
    max_retries=2,
    messages=[
        {"role": "user", "content": prompt},
    ]
  )
  print(f"Section: {section}")
  return section


class Podcast(PodcastOverview):
  transcript: str


async def get_podcast(input_text: str, podcast_length: int) -> PodcastOverview:
  podcast_overview: PodcastOverview = get_podcast_overview(input_text, podcast_length)
  podcast : Podcast = Podcast(**podcast_overview.dict(), transcript="")
  async with ClientSession() as session:
    openai.aiosession.set(session)
    sections = await asyncio.gather(*[get_podcast_section(podcast_overview, episode) for episode in podcast_overview.episodes])
    for section in sections:
      podcast.transcript += "\n\n" + section.episode_transcript

  await openai.aiosession.get().close()
  return podcast


def get_podcast_image(cover_image_description: str) -> str:
  """Generate a podcast cover image from a description of the image."""
  response = openai.Image.create(
  prompt=cover_image_description,
  n=1,
  size="1024x1024"
  )
  image_url = response['data'][0]['url']
  return image_url



def text_2_speech(prompt, voice):
    audio_path = f'{voice}.wav'
    print(f"Generating audio for voice {voice}, to file {audio_path}")

    # split prompt into chunks less than 5000 characters
    chunks = [prompt[i:i + 4950] for i in range(0, len(prompt), 4950)]

    concatenated_audio = AudioSegment.empty()  # Creating an empty audio segment
    for chunk in chunks:
        chunk_audio = generate(
            text=chunk,
            voice=voice,
            model="eleven_multilingual_v2"
        )
        # Assuming that the generate function represents mp3
        audio_segment = AudioSegment.from_mp3(io.BytesIO(chunk_audio))
        concatenated_audio += audio_segment

    # Export concatenated audio to a file
    concatenated_audio.export(audio_path, format="mp3")

    # Get raw audio bytes to return
    buffer = io.BytesIO()
    concatenated_audio.export(buffer, format="mp3")
    raw_audio_bytes = buffer.getvalue()

    return audio_path, raw_audio_bytes