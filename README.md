# Bernabei Price Tracker

A full-stack application to scrape, track, and visualize product prices from Bernabei.it.

## Features

- **Scraping**: Automatically extracts product name, current price, ordinary price, and tags.
- **History**: Maintains a historical record of all price changes.
- **Dashboard**: Modern web interface to view products and analyze price trends over time.
- **Search**: Filter products by name.
- **Details**: Interactive charts showing price evolution.

## Project Structure

- `backend/`: FastAPI application with SQLite database and scraping logic.
- `frontend/`: React + Vite application with Tailwind CSS and Recharts.

## Setup & Run

### 1. Backend

Navigate to the backend directory:

```bash
cd backend
```

Install dependencies:

```bash
pip install fastapi uvicorn sqlmodel requests beautifulsoup4
```

Run the server:

```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`.

### 2. Frontend

Navigate to the frontend directory:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Run the development server:

```bash
npm run dev
```

The dashboard will be available at `http://localhost:5173`.

## Usage

1. Open the dashboard.
2. Click **Update Prices** to trigger the scraper. It will fetch data from key categories (Wines, Spirits).
3. The dashboard will automatically refresh after a few seconds to show the new data.
4. Click on **View Price History** on any product card to see the price trend chart.
