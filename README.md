🏛️ TIC Portal | Tilburg Investment Club Internal System

A comprehensive internal management dashboard for the Tilburg Investment Club (TIC). This application serves as the central hub for portfolio tracking, governance, equity research, and member management.

Built with Python and Streamlit, it integrates real-time market data via Yahoo Finance and uses Google Sheets as a lightweight, collaborative backend database.

🚀 Features

📊 Portfolio & Market Analysis

Fundamental & Quant Dashboards: Real-time AUM tracking, sector allocation, and performance vs. S&P 500.

Live Ticker Tape: Scrolling banner with real-time price updates for portfolio assets.

Risk Engine: * Value at Risk (VaR) & CVaR calculations (95% confidence).

Correlation Matrix heatmap to identify concentration risks.

Monte Carlo Simulations (Geometric Brownian Motion).

Stock Research Terminal: Financial statements, relative valuation (peer comparison), and key ratios.

Valuation Sandbox: Interactive Discounted Cash Flow (DCF) model with sensitivity analysis.

🗳️ Governance & Operations

Role-Based Access Control: Distinct views for Board, Quant Team, Fundamental Analysts, and Guests.

Voting System: Digital voting on investment proposals with live results visualization.

Calendar: Smart calendar filtering for earnings calls, macro events, and internal meetings.

Inbox: Internal messaging system for broadcasting announcements or direct member communication.

⚙️ Administration

Member Database: CRUD operations for managing members, roles, and status.

Treasury Management: Capital injection handling and liquidation queue processing.

Reporting: Automated PDF report generation for fund status and meeting minutes.

Simulation: Paper trading leaderboard for member competitions.

🛠️ Tech Stack

Frontend: Streamlit

Data Manipulation: Pandas, NumPy

Visualization: Plotly Express, Plotly Graph Objects

Market Data: YFinance, Feedparser (RSS)

Backend/DB: Google Sheets API (gspread)

Reporting: FPDF

📦 Installation

Clone the repository:

git clone [https://github.com/yourusername/tic-portal.git](https://github.com/yourusername/tic-portal.git)
cd tic-portal


Install dependencies:
It is recommended to use a virtual environment.

pip install -r requirements.txt


Google Cloud Configuration:
This app requires a Google Service Account to access the database.

Create a project in Google Cloud Console.

Enable the Google Sheets API and Google Drive API.

Create a Service Account and download the JSON key.

Share your Google Sheet (TIC_Database_Master) with the client_email found in your JSON key.

Secrets Setup:
Create a file named .streamlit/secrets.toml in the root directory and add your GCP credentials:

[gcp_service_account]
type = "service_account"
project_id = "your-project-id"
private_key_id = "your-private-key-id"
private_key = "-----BEGIN PRIVATE KEY-----\n..."
client_email = "your-service-account-email"
client_id = "your-client-id"
auth_uri = "[https://accounts.google.com/o/oauth2/auth](https://accounts.google.com/o/oauth2/auth)"
token_uri = "[https://oauth2.googleapis.com/token](https://oauth2.googleapis.com/token)"
auth_provider_x509_cert_url = "[https://www.googleapis.com/oauth2/v1/certs](https://www.googleapis.com/oauth2/v1/certs)"
client_x509_cert_url = "your-cert-url"


▶️ Usage

Run the application locally:

streamlit run dashboard_TIC.py


Guest Access

If you do not have credentials, you can use the "Guest Access" button on the login screen to view the dashboard in Read-Only mode.

📂 Project Structure

tic-portal/
├── dashboard_TIC.py    # Main application entry point
├── requirements.txt    # Python dependencies
├── .streamlit/
│   └── secrets.toml    # API keys (DO NOT COMMIT)
└── README.md           # Documentation


🛡️ Disclaimer

This portal is for internal educational and informational purposes only.

No Financial Advice: Nothing herein constitutes an offer to sell or a solicitation of an offer to buy any security.

Data Accuracy: Market data is provided 'as-is' via third-party APIs and may contain delays.

📄 License

MIT
