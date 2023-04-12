import requests

payload = {'input': 'example input'}
response = requests.post('http://localhost:8000/explain', json=payload)

if response.status_code == 200:
    print(response.json())
else:
    print(f'Request failed with status code {response.status_code}')

