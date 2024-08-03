import time
from random import random

from urllib3.exceptions import HTTPError as BaseHTTPError

import requests

import Config


class YandexArtAPI:
    def __init__(self):

        self.modelURI = f'art://{Config.KATID}/yandex-art/latest'
        self.update_iamtoken()
        self.AUTH_HEADERS = {
            'Authorization': f'Bearer {Config.IAMTOKEN}',
        }
        rand_seed = int(random() * 10000000000)
        self.seed = f'{rand_seed}'
        self.widthRatio = 2
        self.heightRatio = 1
        self.text = ''
        self.messages = [{
            'weight': '1',
            'text': self.text,
        }]

    def update_iamtoken(self):
        response = requests.post('https://iam.api.cloud.yandex.net/iam/v1/tokens',
                                 json={'yandexPassportOauthToken': Config.YAOAUTHTOKEN})
        data = response.json()
        Config.IAMTOKEN = data['iamToken']
        self.AUTH_HEADERS = {
            'Authorization': f'Bearer {Config.IAMTOKEN}',
        }

    def set_ratio(self, width_ratio, height_ratio):
        self.widthRatio = width_ratio
        self.heightRatio = height_ratio

    def set_text(self, text):
        self.text = text

    def seed_update(self):
        random_seed = int(random() * 10000000000)
        self.seed = random_seed

    def generate(self):
        params = {
            "modelUri": self.modelURI,
            "generationOptions": {
                "seed": self.seed,
                "aspectRatio": {
                    "widthRatio": self.widthRatio,
                    "heightRatio": self.heightRatio
                }
            },
            "messages": [
                {
                    "weight": "1",
                    "text": self.text
                }
            ]
        }
        data = {}
        try:
            response = requests.post('https://llm.api.cloud.yandex.net/foundationModels/v1/imageGenerationAsync',
                                     headers=self.AUTH_HEADERS,
                                     json=params)
            data = response.json()
        except BaseHTTPError:
            print("error")
        if 'id' in data.keys():
            attempts = 10
            while attempts > 0:
                try:
                    response = requests.get(f'https://llm.api.cloud.yandex.net:443/operations/{data["id"]}',
                                            headers=self.AUTH_HEADERS)
                    data = response.json()
                except BaseHTTPError:
                    data = {'done': True, 'response': {'image': 'error'}}
                if data['done']:
                    return data['response']['image']

                attempts -= 1
                time.sleep(10)
        else:
            return 'error'
