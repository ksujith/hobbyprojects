# Customer Outreach AI Agent - FastAPI Version

A complete FastAPI implementation of the Customer Outreach AI Agent with real-time processing, SQLite database, and responsive web interface.

## Features

🎯 **Campaign Management**
- Create personalized outreach campaigns
- Real-time AI processing simulation
- Campaign history and tracking
- Lead profiling and analysis

🤖 **AI Agent Workflow**
- Sales Representative Agent (Lead Analysis)
- Lead Sales Representative Agent (Email Generation)
- Real-time progress tracking
- Task status monitoring

📊 **Analytics & Metrics**
- Personalization scores
- Sentiment analysis
- Campaign performance tracking
- Success rate monitoring

📱 **Modern UI**
- Responsive design (mobile-friendly)
- Clean, minimalist interface
- Real-time status updates
- Interactive campaign management

## Technical Stack

- **Backend**: FastAPI (single file)
- **Database**: SQLite with raw SQL queries
- **Frontend**: Vanilla HTML/CSS/JavaScript
- **Styling**: Custom CSS (no frameworks)
- **Real-time**: JavaScript polling for status updates

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements_fastapi.txt
```

### 2. Run the Application

```bash
python outreach_app.py
```

### 3. Access the Interface

Open your browser to: http://localhost:8001

## Database Schema

The application automatically creates these SQLite tables:

### campaigns
- Campaign details and results
- Generated emails and metrics
- Status tracking and timestamps

### agent_tasks
- AI agent workflow tracking
- Task status and completion times
- Detailed progress monitoring

### agent_config
- Agent configuration settings
- Tool preferences and parameters

### campaign_metrics
- Performance analytics
- Success rate tracking
- Historical data

## API Endpoints

### Campaign Management
- `POST /api/campaigns` - Create new campaign
- `GET /api/campaigns` - List all campaigns
- `GET /api/campaigns/{id}` - Get campaign details
- `GET /api/campaigns/{id}/status` - Real-time status

### Dashboard
- `GET /` - Main interface

## Features Overview

### 1. Campaign Creation
- Lead information input form
- Industry and milestone tracking
- Automatic validation
- Template saving

### 2. AI Processing Simulation
- Two-agent workflow simulation
- Real-time progress updates
- Task status monitoring
- Error handling

### 3. Results Display
- Generated email preview
- Performance metrics
- Campaign analytics
- Export options

### 4. Campaign History
- All campaigns dashboard
- Status tracking
- Performance overview
- Quick access to results

## Customization

### Agent Behavior
The MockAIAgent class simulates CrewAI behavior. To integrate with real CrewAI:

1. Replace MockAIAgent with actual CrewAI agents
2. Update the process_campaign_with_ai function
3. Add real API keys and configuration

### UI Customization
- Modify CSS variables in the main HTML
- Add new sections to the interface
- Customize the color scheme and layout

### Database Extensions
- Add new tables for advanced features
- Implement reporting and analytics
- Add user management and authentication

## Production Deployment

### Environment Variables
```bash
export DATABASE_PATH="/path/to/production.db"
export HOST="0.0.0.0"
export PORT="8001"
```

### Docker Deployment
```dockerfile
FROM python:3.11-slim
COPY requirements_fastapi.txt .
RUN pip install -r requirements_fastapi.txt
COPY outreach_app.py .
EXPOSE 8001
CMD ["python", "outreach_app.py"]
```

### Security Considerations
- Add authentication and authorization
- Implement rate limiting
- Add input validation and sanitization
- Use environment variables for sensitive data

## Development

### Adding New Features
1. Update database schema in `init_database()`
2. Add new API endpoints
3. Update the frontend interface
4. Test the complete workflow

### Testing
- Unit tests for API endpoints
- Integration tests for workflows
- Frontend testing with different devices
- Performance testing with multiple campaigns

## Troubleshooting

### Common Issues
- **Database locked**: Ensure proper connection closing
- **Port already in use**: Change port in uvicorn.run()
- **CSS not loading**: Check file paths and permissions

### Debug Mode
Add `debug=True` to uvicorn.run() for detailed error messages.

## License

This project is provided as-is for educational and development purposes.