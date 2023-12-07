from openai import OpenAI
import instructor
import PyPDF2

from podcast import PodcastOverview, PodcastSectionOverview, PodcastSection, Podcast, PodcastIntroOutro

def pdf_to_string(pdf_file: str) -> str:
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page_num in range(len(pdf_reader.pages)):
        page = pdf_reader.pages[page_num]
        text += f"\n \n NEW PAGE: \n {page.extract_text()}"
    return text

class PdfTopic():
    def __init__(self, pdf_path: str, openai_api_key: str):
        self.content = pdf_to_string(pdf_path)
        self.openai_api_key = openai_api_key

    def get_num_of_sections(self) -> int:
        return 1 + len(self.content) // 7500

    def get_section(self, section_number: int) -> str:
        return self.content[section_number*7500:(section_number+1)*7500]

    def generate_podcast_sections(self):
        podcast_sections = []
        print(self.get_num_of_sections())
        for i in range(self.get_num_of_sections()):
            print(f"Generating section {i+1}/{self.get_num_of_sections()}")
            pdf_section = self.get_section(i)
            client = instructor.patch(OpenAI(api_key=self.openai_api_key))
            prompt = f"""
                        You are a podcast producer that has been asked to produce a podcast on a pdf document.
                        A single host will be reading the podcast transcript. Please make it to the point, but also 
                        engaging and funny.
                        
                        The introduction is already done, please summarize the following section of the pdf document in 
                        to a transcript for the podcast.
                        
                        PDF:
                        {pdf_section}
                        """
            section: PodcastSection = client.chat.completions.create(
                model="gpt-4-1106-preview",
                response_model=PodcastSection,
                messages=[
                    {"role": "user", "content": prompt},
                ],
            )
            podcast_sections.append(section)

        return podcast_sections

    def generate_intro(self, podcast_sections):
        transcript = ""
        for sec in podcast_sections:
            transcript += "\n --NEW SECTION-- \n " + sec.transcript
        client = instructor.patch(OpenAI(api_key=self.openai_api_key))
        prompt = f"""
                                    You are a podcast producer that has been asked to produce a podcast and this is your
                                    script: {transcript}
                                    
                                    A single host will be reading the podcast transcript. Now please write an introduction
                                    transcript that shortly welcomes the listener and shortly recaps the content of the
                                    podcast.
                                    
                                    Additionally, add a short transcript that ends the podcast.
                                    
                                    Additionally, add a suiting title.
                                    
                                    Additinally, estimate the time it would take to read it.
                                    """
        intro_outro: PodcastIntroOutro = client.chat.completions.create(
                model="gpt-4-1106-preview",
                response_model=PodcastIntroOutro,
                messages=[
                    {"role": "user", "content": prompt},
                ],
            )

        return intro_outro



    def generate_podcast(self):
        sections = self.generate_podcast_sections()
        print("Generate intro and outro")
        intro_n_outro = self.generate_intro(sections)
        print("Generation done")

        full_podcast = Podcast
        full_podcast.title = intro_n_outro.title
        full_podcast.length_in_minutes = intro_n_outro.length_in_minutes

        all_sections = []
        all_sections.append(PodcastSection(length_in_seconds=1, transcript=intro_n_outro.intro_transcript))
        full_podcast.transcript = intro_n_outro.intro_transcript

        for sec in sections:
            all_sections.append(PodcastSection(length_in_seconds=1, transcript=sec.transcript))
            full_podcast.transcript += "\n\n" + sec.transcript

        all_sections.append(PodcastSection(length_in_seconds=1, transcript=intro_n_outro.outro_transcript))
        full_podcast.transcript += "\n\n" + intro_n_outro.outro_transcript

        full_podcast.sections = all_sections
        return full_podcast

