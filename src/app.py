
import json
import os
import requests
import msal
from flask import Flask, render_template, jsonify, request
import random
from datetime import datetime, timedelta
import csv
import io
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# --- Azure AD and Cost Management API Configuration ---
TENANT_ID = os.getenv("AZURE_TENANT_ID")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
SUBSCRIPTION_ID = os.getenv("AZURE_SUBSCRIPTION_ID")

# --- Get Access Token ---
def get_access_token():
    """Authenticates with Azure AD and retrieves an access token."""
    authority = f"https://login.microsoftonline.com/{TENANT_ID}"
    app_msal = msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=authority,
        client_credential=CLIENT_SECRET
    )
    result = app_msal.acquire_token_for_client(scopes=["https://management.azure.com/.default"])
    return result.get("access_token")

# --- Get Cost Data from Azure ---
def get_azure_cost_data(timeframe):
    """Fetches cost data from the Azure Cost Management API."""
    token = get_access_token()
    if not token:
        return {"error": "Failed to acquire access token."}

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    end_date = datetime.utcnow().date()
    if timeframe == 'daily':
        start_date = end_date - timedelta(days=30)
        granularity = 'Daily'
    elif timeframe == 'weekly':
        start_date = end_date - timedelta(weeks=12)
        granularity = 'Weekly'
    elif timeframe == 'monthly':
        start_date = end_date - timedelta(days=365)
        granularity = 'Monthly'
    else:
        return {"error": "Invalid timeframe"}

    url = f"https://management.azure.com/subscriptions/{SUBSCRIPTION_ID}/providers/Microsoft.CostManagement/query?api-version=2023-03-01"
    
    payload = {
        "type": "Usage",
        "timeframe": "Custom",
        "timePeriod": {
            "from": str(start_date),
            "to": str(end_date)
        },
        "dataset": {
            "granularity": granularity,
            "aggregation": {
                "totalCost": {
                    "name": "Cost",
                    "function": "Sum"
                }
            },
            "grouping": [
                {
                    "type": "Dimension",
                    "name": "ResourceGroup"
                }
            ]
        }
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code != 200:
        return {"error": f"Azure API request failed with status code {response.status_code}: {response.text}"}

    results = response.json()
    
    # Process the results to match the mock data format
    processed_data = {
        "labels": [],
        "costs": [],
        "resource_group_distribution": {}
    }
    
    # This part needs to be adjusted based on the actual API response structure
    # For now, this is a placeholder
    if 'properties' in results and 'rows' in results['properties']:
        for row in results['properties']['rows']:
            processed_data['costs'].append(row[0])
            # Assuming the date is in the second column
            processed_data['labels'].append(row[1]) 
            # Assuming resource group is in the third column
            rg_name = row[2]
            if rg_name not in processed_data['resource_group_distribution']:
                processed_data['resource_group_distribution'][rg_name] = 0
            processed_data['resource_group_distribution'][rg_name] += row[0]

    return processed_data


# --- Mock Data Generation ---

def generate_mock_data(timeframe):
    """Generates mock cost data for different timeframes."""
    end_date = datetime.now()
    if timeframe == 'daily':
        num_days = 30
        start_date = end_date - timedelta(days=num_days - 1)
        date_format = "%Y-%m-%d"
        cost_range = (150, 250)
    elif timeframe == 'weekly':
        num_weeks = 12
        start_date = end_date - timedelta(weeks=num_weeks - 1)
        date_format = "Week %W, %Y"
        cost_range = (1000, 1800)
    elif timeframe == 'monthly':
        num_months = 12
        start_date = end_date - timedelta(days=365)
        date_format = "%B %Y"
        cost_range = (4000, 8000)
    else:
        return {"error": "Invalid timeframe"}

    data = {
        "labels": [],
        "costs": [],
        "resource_group_distribution": {
            "rg-prod-01": 0,
            "rg-dev-01": 0,
            "rg-staging-01": 0
        }
    }

    current_date = start_date
    while current_date <= end_date:
        if timeframe == 'daily':
            data["labels"].append(current_date.strftime(date_format))
            cost = random.uniform(cost_range[0], cost_range[1])
            data["costs"].append(round(cost, 2))
            current_date += timedelta(days=1)
        elif timeframe == 'weekly':
            data["labels"].append(current_date.strftime(date_format))
            cost = random.uniform(cost_range[0], cost_range[1])
            data["costs"].append(round(cost, 2))
            current_date += timedelta(weeks=1)
        elif timeframe == 'monthly':
            # Group by month
            month_year = current_date.strftime("%B %Y")
            if month_year not in data["labels"]:
                data["labels"].append(month_year)
                cost = random.uniform(cost_range[0], cost_range[1])
                data["costs"].append(round(cost, 2))
            current_date += timedelta(days=1)


    total_cost = sum(data["costs"])
    data["resource_group_distribution"]["rg-prod-01"] = round(total_cost * 0.60, 2)
    data["resource_group_distribution"]["rg-dev-01"] = round(total_cost * 0.25, 2)
    data["resource_group_distribution"]["rg-staging-01"] = round(total_cost * 0.15, 2)

    return data

# --- Routes ---

@app.route('/')
def index():
    """Renders the main dashboard page."""
    return render_template('index.html')

@app.route('/api/cost-data')
def get_cost_data_route():
    """API endpoint to fetch cost data."""
    timeframe = request.args.get('timeframe', 'daily')
    use_mock_data = request.args.get('use_mock_data', 'true') == 'true'

    data = None
    if use_mock_data:
        data = generate_mock_data(timeframe)
    else:
        # Check for Azure credentials ONLY when real data is requested
        if not all([TENANT_ID, CLIENT_ID, CLIENT_SECRET, SUBSCRIPTION_ID]) or any(val is None or val.startswith("your_") for val in [TENANT_ID, CLIENT_ID, SUBSCRIPTION_ID]):
            return jsonify({"error": "Azure credentials are not configured in the .env file."}), 400
        
        data = get_azure_cost_data(timeframe)
        if 'error' in data:
            return jsonify(data), 500

    # Calculate metrics if data is available
    if data and "costs" in data:
        total_cost = sum(data.get('costs', []))
        num_costs = len(data.get('costs', []))
        average_daily_cost = total_cost / num_costs if num_costs > 0 else 0
        if timeframe == 'daily' and num_costs > 0:
            forecasted_monthly_cost = (total_cost / num_costs) * 30
        else:
            forecasted_monthly_cost = total_cost

        return jsonify({
            "total_cost": round(total_cost, 2),
            "average_daily_cost": round(average_daily_cost, 2),
            "forecasted_monthly_cost": round(forecasted_monthly_cost, 2),
            "spending_trend": {
                "title": f"{timeframe.capitalize()} Spending Trend",
                "labels": data.get("labels", []),
                "data": data.get("costs", [])
            },
            "resource_distribution": {
                "title": "Cost Distribution by Resource Group",
                "labels": list(data.get("resource_group_distribution", {}).keys()),
                "data": list(data.get("resource_group_distribution", {}).values())
            }
        })
    else:
        return jsonify({"error": "No data available"}), 404

@app.route('/export-csv')
def export_csv():
    """Exports cost data to a CSV file."""
    timeframe = request.args.get('timeframe', 'daily')
    data = generate_mock_data(timeframe)

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(['Date', 'Cost']) # Header
    for label, cost in zip(data['labels'], data['costs']):
        writer.writerow([label, cost])

    output.seek(0)

    return output.getvalue(), 200, {
        'Content-Disposition': f'attachment; filename=cost_data_{timeframe}.csv',
        'Content-Type': 'text/csv'
    }


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=False, use_reloader=False)
