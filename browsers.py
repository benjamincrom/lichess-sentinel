import subprocess
import time
import webbrowser

import requests

USERNAME = 'benjamincrom4'
API_TOKEN = ''
USER_URL_TEMPLATE = 'https://lichess.org/api/user/{username}'

subprocess.Popen("/usr/bin/npm start --prefix /home/bcrom/repos/CameraChessWeb",
                 shell=True)
time.sleep(3)
chrome = webbrowser.get('/usr/bin/chromium-browser')
chrome.open_new('http://localhost:5173/play')
response = requests.get(USER_URL_TEMPLATE.format(username=USERNAME),
                        headers={"Authorization": f"Bearer {API_TOKEN}"},
                        timeout=30)

game_id, color = response.json()['playing'].split('/')[3:5]
chrome.open_new(f'https://lichess.org/{game_id}')
