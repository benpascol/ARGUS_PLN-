import os
import base64
import requests
import json
from dotenv import load_dotenv

load_dotenv('.env')
api_key = os.getenv('API')

img_path = 'data/samples/202601-514500001376-L.jpg'
with open(img_path, 'rb') as f:
    b64 = base64.b64encode(f.read()).decode('utf-8')

payload = {
    'model': 'meta/llama-3.2-11b-vision-instruct',
    'max_tokens': 200,
    'temperature': 0.1,
    'messages': [{
        'role': 'user',
        'content': [
            {'type': 'text', 'text': 'Analyze this electricity meter image. Extract the meter serial number (digits under the barcode), any handwritten or stamped IDPEL numbers, and identify the scene type. Output strictly valid JSON with keys: meter_serial_number, idpel, scene_type.'},
            {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{b64}'}}
        ]
    }]
}

headers = {
    'Authorization': f'Bearer {api_key}',
    'Content-Type': 'application/json'
}

resp = requests.post('https://integrate.api.nvidia.com/v1/chat/completions', json=payload, headers=headers, timeout=30)
print('HTTP Status:', resp.status_code)
if resp.status_code == 200:
    print('VLM Raw Response:\n', resp.json()['choices'][0]['message']['content'])
else:
    print('Error Response:', resp.text)
