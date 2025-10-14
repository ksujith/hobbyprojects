# Customer Outreach System

An AI-powered customer outreach and lead generation system built with CrewAI. This system uses multiple AI agents to research prospects, create detailed lead profiles, and generate personalized outreach campaigns.

## Features

### 🤖 AI Agents
- **Research Analyst**: Conducts comprehensive market research and competitor analysis
- **Sales Representative**: Creates detailed lead profiles and qualification
- **Lead Sales Representative**: Crafts personalized outreach campaigns

### 🛠️ Advanced Tools  
- **Database Tool**: SQLite-based lead management and tracking
- **Email Validator**: Validates email addresses
- **Competitor Analysis**: Market positioning and competitive intelligence
- **Enhanced Sentiment Analysis**: Optimizes message tone and engagement
- **Web Scraping**: Real-time company and news research

### 💾 Data Persistence
- Persistent SQLite database for lead management
- Campaign history and status tracking
- Profile data storage and retrieval

### 🖥️ Multiple Interfaces
- **Jupyter Notebook**: Interactive development and testing
- **Python Scripts**: Direct programmatic access
- **CLI Tool**: Command-line interface for production use

## Quick Start

### 1. Installation

```bash
# Clone or download the project
cd hobbyprojects

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Create a `.env` file with your API keys:

```bash
# Copy the example file
cp .env.example .env

# Edit with your actual API keys
OPENAI_API_KEY=your_openai_api_key_here
SERPER_API_KEY=your_serper_api_key_here  # Optional: for web search
```

### 3. Initialize System

```bash
# Initialize database and check configuration
python cli.py init

# Generate sample data for testing
python cli.py sample-data
```

## Usage

### CLI Commands

```bash
# Create a new outreach campaign
python cli.py create-campaign \
    --name "TechCorp Inc" \
    --industry "Software Development" \
    --decision-maker "Sarah Johnson" \
    --position "CTO" \
    --milestone "Series B funding" \
    --email "sarah@techcorp.com"

# List recent leads
python cli.py list-leads --limit 10

# Update lead status
python cli.py update-status "TechCorp Inc" contacted

# Import multiple leads from JSON
python cli.py batch-import --file sample_leads.json

# Get help for any command
python cli.py create-campaign --help
```

### Python Script Usage

```python
from enhanced_customer_outreach import run_outreach_campaign

# Define lead data
lead_data = {
    "lead_name": "DeepLearningAI",
    "industry": "Online Learning Platform", 
    "key_decision_maker": "Andrew Ng",
    "position": "CEO",
    "milestone": "new course launch",
    "contact_email": "contact@deeplearning.ai"
}

# Run campaign
result = run_outreach_campaign(lead_data)
print(result)
```

### Jupyter Notebook

Open `Customer_Outreach.ipynb` for interactive development and experimentation.

## File Structure

```
hobbyprojects/
├── README.md                          # This file
├── requirements.txt                   # Python dependencies
├── .env.example                       # Environment variables template
├── customer_outreach.py               # Original script (Colab version)
├── enhanced_customer_outreach.py      # Enhanced version with tools
├── cli.py                            # Command-line interface
├── Customer_Outreach.ipynb           # Jupyter notebook
├── leads.db                          # SQLite database (auto-created)
├── sample_leads.json                 # Sample data (generated)
└── campaign_*.txt                    # Generated campaign files
```

## Advanced Features

### Database Management

The system automatically creates and manages a SQLite database (`leads.db`) with the following schema:

- Lead information (name, industry, contact details)
- Profile data and research results
- Campaign status and tracking
- Timestamps for audit trails

### Custom Tools

#### DatabaseTool
- `save_lead`: Store lead information
- `get_leads`: Retrieve recent leads
- `update_status`: Update campaign status

#### CompetitorAnalysisTool
- Industry-specific competitor identification
- Market positioning analysis
- Differentiation opportunities

#### EnhancedSentimentAnalysisTool
- Message tone analysis
- Engagement optimization suggestions
- Professional communication guidelines

### Campaign Output

Each campaign generates:
- Initial outreach email
- LinkedIn connection message
- Follow-up sequence (2-3 messages)
- Timing recommendations
- Success metrics to track

## API Keys Setup

### OpenAI API Key
1. Visit [OpenAI Platform](https://platform.openai.com/api-keys)
2. Create a new API key
3. Add to your `.env` file

### Serper API Key (Optional)
1. Visit [Serper.dev](https://serper.dev/)
2. Sign up and get your API key
3. Add to your `.env` file for enhanced web search

## Troubleshooting

### Common Issues

**ModuleNotFoundError**: Install requirements
```bash
pip install -r requirements.txt
```

**API Key Errors**: Check your `.env` file
```bash
# Verify environment variables are loaded
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('OPENAI_API_KEY'))"
```

**Database Errors**: Reinitialize
```bash
python cli.py init
```

### Logging

Enable verbose logging by setting environment variable:
```bash
export CREWAI_LOG_LEVEL=DEBUG
```

## Contributing

This is a development project. To extend functionality:

1. Add new tools in `enhanced_customer_outreach.py`
2. Create new agents for specific use cases  
3. Add CLI commands in `cli.py`
4. Update database schema as needed

## License

This project is for educational and development purposes.