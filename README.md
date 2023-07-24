![firefox_24-07-2023_23-54-39](https://github.com/Trisnox/Lost-Saga-GD-Scraper/assets/66292369/085fb0e0-3d0c-4dcc-8533-580370c80b83)

# Lost-Saga-GD-Scraper
A tool to scrape and download Lost Saga gear design. It directly scrape from various Lost Saga server, and then later converted into jpg using python.

All texture loaded are also automatically saved at `texture/`, which is located at current folder this script being run at. This any file though, this happens if you switch server, so keep that in mind.

# Running from executable
Get executable (windows) [here](https://github.com/Trisnox/Lost-Saga-GD-Scraper/releases/latest).

Run the exe, once the server is running, type `localhost:5000` or `http://127.0.0.1:5000` on any browser. You can press `Ctrl+C` on your command prompt to stop the server.

# Demo/Replit version
You can also try this script demo version, which is hosted on Replit.com. [Click here](https://lost-saga-gd-scraper.tris07.repl.co/).

The difference between demo version is that it doesn't save texture, unlike the local version.

# Running from source
Download [this repository as a zip](https://cdn.discordapp.com/attachments/558246912982122526/990994256862789662/unknown.png), or download the source from the [releases](https://github.com/Trisnox/Lost-Saga-GD-Scraper/releases/latest).

Run this command on your command prompt
```py
pip install -r requirements.txt
```
After installing requirements, you can run the script by using this command:
```py
[windows] python -m flask run
[linux]   python3 -m flask run
```
or
```py
[windows] python app.py
[linux]   python3 app.py
```
Once the server is running, type `localhost:5000` or `http://127.0.0.1:5000` on any browser. You can press `Ctrl+C` on your command prompt to stop the server.

# Support server
If you ever need assistance, you can contact me through my discord server: https://discord.gg/GJ2P6u4edG
