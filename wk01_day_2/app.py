import datetime
import os
import requests
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from IPython.display import Markdown, display
from transformers import AutoTokenizer, AutoModelForCausalLM
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time
import gradio as gr

device = "cuda" # the device to load the model onto
model_name = "Qwen/QwQ-32B-Preview"
# Now you do not need to add "trust_remote_code=True"
model = AutoModelForCausalLM.from_pretrained(
    "Qwen/Qwen1.5-7B-Chat",
    torch_dtype="auto",
    device_map="auto"
)
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen1.5-7B-Chat")



# A class to represent a Webpage
# If you're not familiar with Classes, check out the "Intermediate Python" notebook
class Website:
    def __init__(self, url):
        self.url = url
        options = Options()

        # Uncomment the line below to run with a visible browser window
        # options.add_argument("--headless")

        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        service = Service()
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(url)

        # Allow more time for potential human verification pages to clear
        #input("Please complete the verification in the browser and press Enter to continue...")
        time.sleep(3)

        page_source = driver.page_source
        driver.quit()
        soup=BeautifulSoup(page_source, 'html.parser')
        self.title = soup.title.string if soup.title else "No title found"
        for irrelevant in soup(["script", "style", "img", "input"]):
            irrelevant.decompose()
        self.text = soup.get_text(separator="\n", strip=True)

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



# get the response
def summarize(url, system_prompt, model, tokenizer):
    website = Website(url)
    user_prompt= user_prompt_for(website)

    messages = [
        {"role": "system",
         "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    print(f'started tokenizer: {datetime.datetime.now()}')
    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )
    print(f'Ended tokenizer: {datetime.datetime.now()}')
    model_inputs = tokenizer([text], return_tensors="pt").to(device)

    generated_ids = model.generate(
        **model_inputs,
        max_new_tokens=len(system_prompt) + len(user_prompt) * 2
    )
    generated_ids = [
        output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
    ]

    response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
    return response


# A function to display this nicely in the Jupyter output, using markdown

def display_summary(url, model, tokenizer):
    is_valid = is_valid_url(url)
    if is_valid:
        try:
            results = summarize(url, system_prompt, model, tokenizer)
            if len(str(Markdown(results).data)) > 0:
                return Markdown(results).data
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
        # Website Summarizer
        ## Why read the entire website when you can get a quick summary here!!
        """, elem_id='site_title')
    with gr.Row() as summarized:
        with gr.Column(scale=1):
            url = gr.Text(label='Enter URL of Website to Summarize', placeholder='https://huggingface.co',
                          elem_id='text_label')
            summarize_btn = gr.Button('Summarize!')
        with gr.Column(scale=4):
            summary = gr.Markdown(label='Summary of website', show_copy_button=True)
    summarize_btn.click(fn=display_summary, inputs=[url], outputs=[summary], show_progress="full")
website_summarizer.launch()