# Bandcamp Explorer

Discover music by exploring who bought a Bandcamp release — and what else they own.

Try it at: https://bc-explorer.app/

![Screenshot](https://bc-explorer.app/static/media/social.png)

---

## Running locally with Docker

Docker lets you run the app without installing Python or any dependencies. Follow the guide for your operating system below.

### Mac

1. **Install Docker Desktop**
   - Download from https://www.docker.com/products/docker-desktop/
   - Open the `.dmg` file and drag Docker to your Applications folder
   - Launch Docker from Applications and wait for the whale icon in your menu bar to stop animating

2. **Download this project**
   - Click the green **Code** button at the top of this page, then **Download ZIP**
   - Unzip the folder somewhere easy to find (e.g. your Desktop)

3. **Open a terminal in the project folder**
   - Open **Terminal** (search for it with Spotlight: `Cmd + Space`, type "Terminal")
   - Type `cd ` (with a space after), then drag the unzipped project folder into the Terminal window and press `Enter`

4. **Create a config file**
   ```
   cp .env.example .env
   ```

5. **Start the app**
   ```
   docker compose up --build
   ```
   The first run downloads dependencies and may take a few minutes. When you see `You can now view your Streamlit app`, open http://localhost:8501 in your browser.

6. **Stopping the app** — press `Ctrl + C` in the terminal, then run:
   ```
   docker compose down
   ```

---

### Windows

Docker on Windows works best through **WSL 2** (Windows Subsystem for Linux), which Docker Desktop sets up for you automatically.

1. **Enable WSL 2** (skip if you already have it)
   - Open **PowerShell as Administrator** (search "PowerShell" → right-click → *Run as administrator*)
   - Run:
     ```
     wsl --install
     ```
   - Restart your computer when prompted

2. **Install Docker Desktop**
   - Download from https://www.docker.com/products/docker-desktop/
   - Run the installer. When asked, make sure **"Use WSL 2 instead of Hyper-V"** is checked
   - Restart if prompted, then launch Docker Desktop and wait for it to finish starting

3. **Download this project**
   - Click the green **Code** button at the top of this page, then **Download ZIP**
   - Unzip the folder somewhere easy to find (e.g. your Desktop)

4. **Open a terminal in the project folder**
   - Open the unzipped project folder in File Explorer
   - Click the address bar at the top, type `cmd`, and press `Enter` — this opens a command prompt in the right folder

5. **Create a config file**
   ```
   copy .env.example .env
   ```

6. **Start the app**
   ```
   docker compose up --build
   ```
   The first run downloads dependencies and may take a few minutes. When you see `You can now view your Streamlit app`, open http://localhost:8501 in your browser.

7. **Stopping the app** — press `Ctrl + C` in the terminal, then run:
   ```
   docker compose down
   ```

> **Troubleshooting:** If Docker Desktop says "WSL 2 installation is incomplete", open PowerShell as Administrator and run `wsl --update`, then restart Docker Desktop.

---

## Shareable URLs (optional)

Results can be shared via `?id=` links if you connect a [Supabase](https://supabase.com) project. Create a table called `resultstable` with columns `uid` (text) and `data` (jsonb), then add your credentials to the `.env` file:

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
```

Without these the app works fully — you just can't generate shareable links.

---

## Running locally (for developers)

```bash
pip install -r requirements.txt
PYTHONPATH=. streamlit run app/main.py
```

The app opens at http://localhost:8501.

## Project structure

```
app/
  main.py       # Streamlit entrypoint
  scraper.py    # Async Bandcamp API/scraping
  search.py     # Sidebar search
  database.py   # Optional Supabase integration
  ui.py         # Styles, HTML rendering
  config.py     # Constants and env var loading
```
