# scrapper-management


Below is an example README.md for your GitHub repository:

---

```markdown
# Scraper Management System

A FastAPI-based scraper management system that allows you to create tasks to scrape webpages using [cloudscraper](https://pypi.org/project/cloudscraper/) and stores the scraped data in a SQLite database. The UI is built with a macOS–inspired design and features three tabs:
- **Add Task**: Enter a URL to create a new scraping task.
- **Task List**: View a table of tasks with their status.
- **Scraped Data**: Browse scraped tasks using a two-pane layout—one pane shows a list of tasks and the other displays the raw HTML for the selected task.

The system uses background tasks to fetch data from the target URL and auto-updates the UI every 5 seconds without deselecting the chosen task.

## Features

- **FastAPI Backend**  
  - RESTful endpoints to create and manage scraping tasks.
  - Background scraping with cloudscraper.
  - SQLite persistence via SQLAlchemy.

- **Modern UI with macOS Aesthetic**  
  - Three tabs for adding tasks, listing tasks, and viewing scraped data.
  - Two-pane layout in the scraped data tab: task list and detailed raw HTML view.
  - Auto-update via JavaScript polling (every 5 seconds) that preserves the user's selected task.

- **Robust Data Model**  
  - Database table `webpages` with columns: `id` (auto-generated), `url` (unique), `raw_html`, `status`, and `status_code`.

## Tech Stack

- **Backend:** Python, FastAPI, SQLAlchemy, cloudscraper  
- **Database:** SQLite  
- **Frontend:** Jinja2 Templates, Bootstrap 5, custom CSS (macOS style)  
- **Deployment:** Uvicorn

## Installation

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/yourusername/scraper-management-system.git
   cd scraper-management-system
   ```

2. **Create a Virtual Environment:**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

   Your `requirements.txt` should include packages such as:
   - fastapi
   - uvicorn
   - sqlalchemy
   - cloudscraper
   - jinja2

4. **Initialize the Database:**

   The database is automatically created when you run the application for the first time.

## Usage

1. **Run the Application:**

   ```bash
   uvicorn app:app --reload
   ```

2. **Access the Application:**

   Open your browser and navigate to: [http://127.0.0.1:8000](http://127.0.0.1:8000)

3. **API Documentation:**

   Visit [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) for the interactive Swagger UI.

## Project Structure

```
scraper-management-system/
├── app.py                   # Main FastAPI application
├── requirements.txt         # List of Python dependencies
├── scraper.db               # SQLite database file (auto-created)
├── static/
│   └── style.css            # Custom CSS for macOS look and feel
└── templates/
    └── index.html           # Jinja2 HTML template for UI
```

## API Endpoints

- **GET /api/tasks**  
  Returns the list of all scraping tasks.

- **POST /api/tasks**  
  Create a new scraping task by sending a JSON payload with a URL.

- **POST /api/tasks/{task_id}/start**  
  Start the background scraping job for a specific task.

## UI Overview

- **Add Task Tab:**  
  Enter a URL and submit to create a new scraping task.

- **Task List Tab:**  
  Displays a table of tasks with columns for ID, URL, status, and HTTP status code. Tasks that are pending can be started with a button.

- **Scraped Data Tab:**  
  Features a two-pane layout:
  - **Left Pane:** A list of tasks (only those with non‑empty scraped data).  
  - **Right Pane:** Displays the full raw HTML of the selected task.
  - The task list and raw HTML pane auto-update every 5 seconds while preserving the selected task.

## Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](https://github.com/yourusername/scraper-management-system/issues).

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contact

Created by [Your Name](https://github.com/yourusername) - feel free to reach out!

```

---

Feel free to adjust URLs, contributor names, and additional sections as needed. This README provides a comprehensive overview of the project, installation, usage, and project structure for potential contributors and users.
