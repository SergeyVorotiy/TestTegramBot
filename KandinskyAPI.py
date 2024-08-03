import json
import os
import time

from urllib3.exceptions import HTTPError as BaseHTTPError

from dotenv import load_dotenv

import requests


load_dotenv()


class KandinskyAPI:

    def __init__(self):
        self.api_key = os.getenv('KANDINSKY_API_KEY')
        self.secret_key = os.getenv('KANDINSKY_SECRET_KEY')
        self.AUTH_HEADERS = {
            'X-Key': f'Key {self.api_key}',
            'X-Secret': f'Secret {self.secret_key}',
        }
        self.type = 'GENERATE'
        self.width = 1024
        self.height = 1024
        self.numImages = 1
        self.query = ''
        self.style = {}
        self.negative_prompt = ''
        self.URL = 'https://api-key.fusionbrain.ai/'
        model_response = requests.get(self.URL + 'key/api/v1/models', headers=self.AUTH_HEADERS)
        model_data = model_response.json()
        self.model = model_data[0]['id']
        styles_response = requests.get('https://cdn.fusionbrain.ai/static/styles/api', headers=self.AUTH_HEADERS)
        styles_data = styles_response.json()
        self.styles = styles_data

    def set_size(self, width, heigth):
        if (width > 0) and (width <= 1024):
            self.width = width
        else:
            self.width = 1024
        if (heigth > 0) and (heigth <= 1024):
            self.height = heigth
        else:
            self.height = 1024

    def set_style(self, style):
        if style in self.styles:
            self.style = style
        else:
            self.style = {
                'name': 'DEFAULT',
                'title': 'Свой стиль',
                'titleEn': 'No style',
                'image': 'https://cdn.fusionbrain.ai/static/download/img-style-personal.png'
            }

    def set_query(self, prompt):
        self.query = prompt

    def set_negative_prompt(self, negative_prompt):
        self.negative_prompt = negative_prompt

    def generate(self):
        params = {
            'type': self.type,
            'numImages': self.numImages,
            'width': self.width,
            'height': self.height,
            'style': self.style['name'],
            'negative_prompt': self.negative_prompt,
            'generateParams': {
                'query': self.query
            }
        }
        data = {
            'model_id': (None, self.model),
            'params': (None, json.dumps(params), 'application/json')
        }
        data = {}
        try:
            response = requests.post(self.URL + 'key/api/v1/text2image/run',
                                     headers=self.AUTH_HEADERS,
                                     files=data)
            data = response.json()
        except BaseHTTPError:
            print('error')
        if 'uuid' in data.keys():
            attempts = 10
            while attempts > 0:
                try:
                    response = requests.get(self.URL + 'key/api/v1/text2image/status/' + data['uuid'],
                                            headers=self.AUTH_HEADERS)
                    data = response.json()
                except BaseHTTPError:
                    data = {'status': 'DONE', 'images': 'error'}

                if data['status'] == 'DONE':
                    return data['images']

                attempts -= 1
                time.sleep(10)
        else:
            return 'error'
