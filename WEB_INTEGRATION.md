# Add these to the main project README

## Web Interface

Workday includes a web-based interface built with Next.js.

### Building the Frontend

```bash
# Navigate to web directory
cd web

# Install dependencies
npm install

# Build for production (static export)
npm run build
```

This will create a `web/out/` directory with static files.

### Running with FastAPI

The FastAPI backend automatically serves the frontend if the `web/out/` directory exists:

```bash
# From project root
python api.py
```

Then open `http://localhost:8000` in your browser.

### Development Mode

For frontend development with hot reload:

```bash
# Terminal 1: Run FastAPI backend
python api.py

# Terminal 2: Run Next.js dev server
cd web
npm run dev
```

Then open `http://localhost:3000` for the Next.js dev server.

## Web Interface Features

- **Timeline View**: Browse daily activities with time ranges
- **Activity Details**: View full descriptions and metadata
- **Recording Control**: Start/stop recording from the web UI
- **Date Navigation**: Browse past days
- **Responsive Design**: Works on desktop and mobile

## Tech Stack

### Backend
- Python 3.12+
- FastAPI
- SQLite
- OpenCV (screen recording)
- MSS (cross-platform screenshots)

### Frontend
- Next.js 14 (Static Export)
- React 18
- TypeScript
- Tailwind CSS
- date-fns
