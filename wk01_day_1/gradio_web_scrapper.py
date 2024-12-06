import os
import requests
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from IPython.display import Markdown, display
from openai import OpenAI
import gradio as gr

load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')

# Check the key
if not api_key:
    print("No API key was found - please head over to the troubleshooting notebook in this folder to identify & fix!")
elif not api_key.startswith("sk-"):
    print(
        "An API key was found, but it doesn't start sk-proj-; please check you're using the right key - see troubleshooting notebook")
elif api_key.strip() != api_key:
    print(
        "An API key was found, but it looks like it might have space or tab characters at the start or end - please remove them - see troubleshooting notebook")
else:
    print("API key found and looks good so far!")

openai = OpenAI()


# A class to represent a Webpage
# If you're not familiar with Classes, check out the "Intermediate Python" notebook
class Website:

    def __init__(self, url):
        """
        Create this Website object from the given url using the BeautifulSoup library
        """
        self.url = url
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        self.title = soup.title.string if soup.title else "No title found"
        for irrelevant in soup.body(["script", "style", "img", "input"]):
            irrelevant.decompose()
        self.text = soup.body.get_text(separator="\n", strip=True)


# Define our system prompt - you can experiment with this later, changing the last sentence to 'Respond in markdown in Spanish."
system_prompt = "You are an assistant that analyzes the contents of a website \
and provides a short summary, ignoring text that might be navigation related. \
Respond in markdown."


# A function that writes a User Prompt that asks for summaries of websites:
def user_prompt_for(website):
    user_prompt = f"You are looking at a website titled {website.title}"
    user_prompt += "\nThe contents of this website is as follows; \
    please provide a short summary of this website in markdown. \
    If it includes news or announcements, then summarize these too.\n\n"
    user_prompt += website.text
    return user_prompt


# See how this function creates exactly the format above
def messages_for(website):
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt_for(website)}
    ]


# And now: call the OpenAI API. You will get very familiar with this!
def summarize(url):
    website = Website(url)
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages_for(website)
    )
    return response.choices[0].message.content


# A function to display this nicely in the Jupyter output, using markdown

def display_summary(url):
    is_valid = is_valid_url(url)
    if is_valid:
        try:
            summary = summarize(url)
            if len(str(Markdown(summary).data)) > 0:
                return Markdown(summary).data
            else:
                gr.Warning(f'url:  {url}\n is not valid.')
                return 'Nothing to Show'
        except Exception as e:
            gr.Warning(f'url:  {url}\n is not valid.')
            return 'Nothing to Show'
    else:
        gr.Warning(f'url:  {url}\n is not valid.')
        return 'Nothing to Show'


def is_valid_url(url):
    import re
    regex = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return url is not None and regex.search(url)


# create gradio site for the app
def load_css():
    with open('../style.css', 'r') as file:
        css_content = file.read()
    return css_content


with gr.Blocks(css=load_css()) as website_summarizer:
    gr.Markdown(
        """
        # Website Summarizer!
        Why read the entire website when you can get a quick summary here.
        """, elem_id='site_title')
    with gr.Row():
        with gr.Column(scale=1):
            url = gr.Text(label='Enter URL of Website to Summarize', placeholder='https://huggingface.co',
                          elem_id='text_label')
            btn = gr.Button('Summarize!')
        with gr.Column(scale=4):
            summary = gr.Markdown(label='Summary of website', show_copy_button=True)
    btn.click(fn=display_summary, inputs=[url], outputs=[summary])
website_summarizer.launch()
