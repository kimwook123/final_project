import json
import os
from dotenv import load_dotenv

import openai

load_dotenv()

openai.organization = os.getenv('org-yVLXOriY3IlThaprcxXgWErZ')
openai.api_key = os.getenv('OPENAI_API_KEY')

lang = 'ko'

