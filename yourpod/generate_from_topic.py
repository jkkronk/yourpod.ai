from openai import OpenAI
import instructor

from podcast import PodcastOverview, PodcastSectionOverview, PodcastSection, Podcast

def get_podcast_overview(input_text, podcast_length, openai_api_key) -> PodcastOverview:
    client = instructor.patch(OpenAI(api_key=openai_api_key))
    prompt = f"""
                You are a podcast producer that has been asked to produce a podcast on {input_text}.
                The podcast should be about {podcast_length} minutes long. 
                A single host will be reading the podcast transcript. Please make it to the point, but also engaging.
                
                Write a outline of the podcast, consisting of several sections.
                Each section will be read one after the other as a continuous podcast with no breaks in between.
                Each section should be between 2 and 4 minutes long.
                Don't make the podcast too long, it should be about {podcast_length} minutes long. 
                Use as few sections as possible to make the podcast about {podcast_length} minutes long.
                Between each section, you can optionally add a sound effect, note that that a sound effect might not be 
                needed between all sections.
                
                Provide the title of the podcast, the description of the podcast and describe the high level content, 
                and length in minutes.
                """
    #print(f"Prompt: {prompt}")
    overview: PodcastOverview = client.chat.completions.create(
        model="gpt-4-1106-preview",
        response_model=PodcastOverview,
        messages=[
            {"role": "user", "content": prompt},
        ],
        max_retries=2,
    )
    #print(f"Overview: {overview}")
    return overview


def get_podcast_section(
    podcast_overview: PodcastOverview, section: PodcastSectionOverview, podcast: Podcast, desired_length: int, openai_api_key
) -> PodcastSection:
    client = instructor.patch(OpenAI(api_key=openai_api_key))
    """Generate a podcast section from a podcast overview."""
    prompt = f"""
                You are a podcast host that is explaining {podcast_overview.title} to your audience.
                The podcast is about {podcast_overview.description}.
                
                The podcast has the following episodes, with estimated length in seconds:
                {[[s.description, s.length_in_seconds] for s in podcast_overview.section_overviews]}
                
                Before this section, the transcript is:
                {podcast.transcript}
                
                You are now writing the detailed transcript for the section {section.description}.
                The transcipt for this section was initally estimated to be about {section.length_in_seconds} seconds to read, but please adjust it as needed to stay make the complete podcast about {desired_length} minutes long.
                The estimated length of the podcast so far is {podcast.length_in_minutes}. 
                The podcast should be about {desired_length} minutes long, so there is about {desired_length - podcast.length_in_minutes} minutes left for the rest of the podcast sections.
                A single host will be reading the podcast transcript. Plase make it to the point, but also engaging.
                
                Write the detailed transcript for this podcast section. 
                It will be concatenated with the other sections to form the full podcast transcript.
                """
    #print(f"Prompt: {prompt}")
    section: PodcastSection = client.chat.completions.create(
        model="gpt-4-1106-preview",
        response_model=PodcastSection,
        messages=[
            {"role": "user", "content": prompt},
        ],
    )
    #print(f"Section: {section}")
    return section


def get_podcast(input_text: str, podcast_length: int, openai_api_key) -> PodcastOverview:
    client = instructor.patch(OpenAI(api_key=openai_api_key))
    podcast_overview: PodcastOverview = get_podcast_overview(input_text, podcast_length)
    podcast: Podcast = Podcast(**podcast_overview.dict(), length_in_minutes=0, transcript="", sections=[])
    for section_overview in podcast_overview.section_overviews:
        section = get_podcast_section(podcast_overview, section_overview, podcast, desired_length=podcast_length)
        podcast.transcript += "\n\n\n" + f"[{section.sound_effect_intro}]" + "\n\n" + section.transcript 
        podcast.length_in_minutes += section.length_in_seconds / 60
        podcast.sections.append(section)

    return podcast


def get_podcast_image(cover_image_description: str) -> str:
    """Generate a podcast cover image from a description of the image."""
    return "https://www.google.com/url?sa=i&url=https%3A%2F%2Funsplash.com%2Fs%2Fphotos%2Fnatural&psig=AOvVaw1j_-1b18H9E8vIIJXnVbGE&ust=1700202091318000&source=images&cd=vfe&ved=0CBIQjRxqFwoTCKichsDwx4IDFQAAAAAdAAAAABAE"
