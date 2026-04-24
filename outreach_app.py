#!/usr/bin/env python3
"""
Customer Outreach AI Agent - FastAPI Application
Single-file FastAPI app with SQLite database, vanilla CSS/JS, and clean UI
"""

from fastapi import FastAPI, Request, Form, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import sqlite3
import json
import asyncio
from datetime import datetime
from typing import Optional, Dict, List
import uuid
import os
from pydantic import BaseModel

# Initialize FastAPI app
app = FastAPI(title="Customer Outreach AI Agent", description="AI Powered Outreach System")

# Database initialization
DATABASE_PATH = "outreach_campaigns.db"

def init_database():
    """Initialize SQLite database with proper schema"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Campaigns table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS campaigns (
            id TEXT PRIMARY KEY,
            company_name TEXT NOT NULL,
            industry TEXT NOT NULL,
            decision_maker TEXT NOT NULL,
            position TEXT NOT NULL,
            milestone TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            lead_analysis TEXT,
            generated_email TEXT,
            email_subject TEXT,
            personalization_score INTEGER,
            sentiment_score REAL,
            word_count INTEGER,
            confidence_level TEXT,
            next_steps TEXT
        )
    ''')
    
    # Agent tasks table for tracking AI workflow
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agent_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id TEXT NOT NULL,
            agent_name TEXT NOT NULL,
            task_name TEXT NOT NULL,
            status TEXT NOT NULL,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            details TEXT,
            FOREIGN KEY (campaign_id) REFERENCES campaigns (id)
        )
    ''')
    
    # Configuration table for agent settings
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agent_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_type TEXT NOT NULL,
            config_key TEXT NOT NULL,
            config_value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Campaign performance tracking
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS campaign_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id TEXT NOT NULL,
            metric_type TEXT NOT NULL,
            metric_value REAL NOT NULL,
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (campaign_id) REFERENCES campaigns (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_database()

# Pydantic models
class CampaignCreate(BaseModel):
    company_name: str
    industry: str
    decision_maker: str
    position: str
    milestone: str

class AgentTask(BaseModel):
    agent_name: str
    task_name: str
    status: str
    details: Optional[str] = None

# Simulated AI Agent Processing (replacing actual AICRM for demo)
class MockAIAgent:
    """Mock AI agent that simulates AICRM behavior for demo purposes"""
    
    @staticmethod
    async def simulate_sales_rep_analysis(campaign_data: Dict) -> Dict:
        """Simulate Sales Representative agent analysis"""
        await asyncio.sleep(2)  # Simulate processing time
        
        analysis = {
            "company_profile": f"Analysis of {campaign_data['company_name']} in {campaign_data['industry']} sector",
            "decision_maker_profile": f"{campaign_data['decision_maker']} ({campaign_data['position']}) analysis",
            "milestone_analysis": f"Recent milestone: {campaign_data['milestone']}",
            "business_triggers": "Market expansion, product innovation, competitive positioning",
            "pain_points": ["Digital transformation needs", "Scalability challenges", "Market differentiation"],
            "value_opportunities": ["Process automation", "Enhanced analytics", "Customer experience"],
            "confidence_level": "Medium",
            "bant_score": {"budget": 4, "authority": 5, "need": 4, "timeline": 3}
        }
        
        return analysis
    
    @staticmethod
    async def simulate_outreach_generation(campaign_data: Dict, analysis: Dict) -> Dict:
        """Simulate Lead Sales Representative agent email generation"""
        await asyncio.sleep(3)  # Simulate processing time
        
        # Generate personalized email content
        email_content = f"""Dear {campaign_data['decision_maker']},

I hope this message finds you well. I wanted to take a moment to congratulate you and the entire {campaign_data['company_name']} team on your recent {campaign_data['milestone']}. Your commitment to advancing innovation in the {campaign_data['industry']} space continues to inspire industry leaders and drive meaningful change.

At AICRM, we resonate deeply with your vision and the strategic direction you're taking. We develop tailored AI-powered solutions designed to meet the specific demands of innovative organizations like yours, helping to streamline processes, enhance decision-making, and accelerate growth.

We believe that a collaboration between {campaign_data['company_name']} and AICRM could significantly amplify the impact of your recent initiatives. Together, we can push the boundaries of what's possible and create even more value for your customers and stakeholders.

I would love the opportunity to discuss how our solutions can support your current objectives and help you achieve your future goals. Please let me know a convenient time for a brief conversation.

Best regards,

[Your Name]
[Your Position]
AICRM Solutions Team"""

        return {
            "subject": f"Congratulations on Your Recent {campaign_data['milestone']}!",
            "email_body": email_content,
            "personalization_score": 87,
            "sentiment_score": 0.82,
            "word_count": len(email_content.split()),
            "tone": "Professional & Engaging",
            "recommendations": [
                "Email includes specific company achievement reference",
                "Tone matches professional outreach standards", 
                "Clear call-to-action included",
                "Sentiment analysis: Highly positive"
            ]
        }

async def process_campaign_with_ai(campaign_id: str, campaign_data: Dict):
    """Process campaign through AI agent workflow"""
    
    # Update campaign status
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    try:
        # Step 1: Sales Rep Analysis
        cursor.execute(
            "INSERT INTO agent_tasks (campaign_id, agent_name, task_name, status, started_at) VALUES (?, ?, ?, ?, ?)",
            (campaign_id, "Sales Representative", "Lead Profiling & Analysis", "running", datetime.now())
        )
        conn.commit()
        
        analysis = await MockAIAgent.simulate_sales_rep_analysis(campaign_data)
        
        # Update task completion
        cursor.execute(
            "UPDATE agent_tasks SET status = ?, completed_at = ?, details = ? WHERE campaign_id = ? AND agent_name = ?",
            ("completed", datetime.now(), json.dumps(analysis), campaign_id, "Sales Representative")
        )
        
        # Step 2: Outreach Generation
        cursor.execute(
            "INSERT INTO agent_tasks (campaign_id, agent_name, task_name, status, started_at) VALUES (?, ?, ?, ?, ?)",
            (campaign_id, "Lead Sales Representative", "Personalized Outreach Creation", "running", datetime.now())
        )
        conn.commit()
        
        outreach = await MockAIAgent.simulate_outreach_generation(campaign_data, analysis)
        
        # Update task completion
        cursor.execute(
            "UPDATE agent_tasks SET status = ?, completed_at = ?, details = ? WHERE campaign_id = ? AND agent_name = ?",
            ("completed", datetime.now(), json.dumps(outreach), campaign_id, "Lead Sales Representative")
        )
        
        # Update campaign with results
        cursor.execute(
            """UPDATE campaigns SET 
               status = 'completed',
               updated_at = ?,
               lead_analysis = ?,
               generated_email = ?,
               email_subject = ?,
               personalization_score = ?,
               sentiment_score = ?,
               word_count = ?,
               confidence_level = ?""",
            (datetime.now(), json.dumps(analysis), outreach['email_body'], 
             outreach['subject'], outreach['personalization_score'], 
             outreach['sentiment_score'], outreach['word_count'], analysis['confidence_level'])
        )
        
        conn.commit()
        
    except Exception as e:
        # Mark campaign as failed
        cursor.execute(
            "UPDATE campaigns SET status = 'failed', updated_at = ? WHERE id = ?",
            (datetime.now(), campaign_id)
        )
        conn.commit()
        
    finally:
        conn.close()

# API Routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Main dashboard page"""
    return HTMLResponse(content=get_main_html(), status_code=200)

@app.post("/api/campaigns")
async def create_campaign(
    background_tasks: BackgroundTasks,
    company_name: str = Form(...),
    industry: str = Form(...),
    decision_maker: str = Form(...),
    position: str = Form(...),
    milestone: str = Form(...)
):
    """Create new outreach campaign"""
    
    campaign_id = str(uuid.uuid4())
    campaign_data = {
        "company_name": company_name,
        "industry": industry, 
        "decision_maker": decision_maker,
        "position": position,
        "milestone": milestone
    }
    
    # Save campaign to database
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        """INSERT INTO campaigns (id, company_name, industry, decision_maker, position, milestone, status)
           VALUES (?, ?, ?, ?, ?, ?, 'processing')""",
        (campaign_id, company_name, industry, decision_maker, position, milestone)
    )
    conn.commit()
    conn.close()
    
    # Start AI processing in background
    background_tasks.add_task(process_campaign_with_ai, campaign_id, campaign_data)
    
    return {"campaign_id": campaign_id, "status": "processing"}

@app.get("/api/campaigns/{campaign_id}")
async def get_campaign(campaign_id: str):
    """Get campaign details and status"""
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Get campaign details
    cursor.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,))
    campaign = cursor.fetchone()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Get agent tasks
    cursor.execute("SELECT * FROM agent_tasks WHERE campaign_id = ? ORDER BY started_at", (campaign_id,))
    tasks = cursor.fetchall()
    
    conn.close()
    
    # Format response
    campaign_data = {
        "id": campaign[0],
        "company_name": campaign[1],
        "industry": campaign[2], 
        "decision_maker": campaign[3],
        "position": campaign[4],
        "milestone": campaign[5],
        "status": campaign[6],
        "created_at": campaign[7],
        "updated_at": campaign[8],
        "lead_analysis": json.loads(campaign[9]) if campaign[9] else None,
        "generated_email": campaign[10],
        "email_subject": campaign[11],
        "personalization_score": campaign[12],
        "sentiment_score": campaign[13],
        "word_count": campaign[14],
        "confidence_level": campaign[15]
    }
    
    # Format tasks
    task_list = []
    for task in tasks:
        task_list.append({
            "agent_name": task[2],
            "task_name": task[3],
            "status": task[4],
            "started_at": task[5],
            "completed_at": task[6],
            "details": json.loads(task[7]) if task[7] else None
        })
    
    campaign_data["tasks"] = task_list
    
    return campaign_data

@app.get("/api/campaigns")
async def list_campaigns():
    """Get all campaigns for dashboard"""
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, company_name, industry, decision_maker, position, status, created_at, 
               personalization_score, sentiment_score
        FROM campaigns 
        ORDER BY created_at DESC 
        LIMIT 50
    """)
    
    campaigns = cursor.fetchall()
    conn.close()
    
    campaign_list = []
    for campaign in campaigns:
        campaign_list.append({
            "id": campaign[0],
            "company_name": campaign[1],
            "industry": campaign[2],
            "decision_maker": campaign[3], 
            "position": campaign[4],
            "status": campaign[5],
            "created_at": campaign[6],
            "personalization_score": campaign[7],
            "sentiment_score": campaign[8]
        })
    
    return {"campaigns": campaign_list}

@app.get("/api/campaigns/{campaign_id}/status")
async def get_campaign_status(campaign_id: str):
    """Get real-time campaign processing status"""
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Get current status and latest tasks
    cursor.execute("SELECT status FROM campaigns WHERE id = ?", (campaign_id,))
    campaign_status = cursor.fetchone()
    
    if not campaign_status:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    cursor.execute("""
        SELECT agent_name, task_name, status, started_at, completed_at 
        FROM agent_tasks 
        WHERE campaign_id = ? 
        ORDER BY started_at DESC
    """, (campaign_id,))
    
    tasks = cursor.fetchall()
    conn.close()
    
    # Determine current progress
    progress = 0
    current_task = "Initializing..."
    
    if campaign_status[0] == "processing":
        if tasks:
            completed_tasks = len([t for t in tasks if t[2] == "completed"])
            total_tasks = len(tasks)
            progress = int((completed_tasks / max(total_tasks, 1)) * 100)
            
            # Find current running task
            running_task = next((t for t in tasks if t[2] == "running"), None)
            if running_task:
                current_task = f"{running_task[0]} - {running_task[1]}"
            elif completed_tasks == total_tasks:
                current_task = "Finalizing results..."
    
    elif campaign_status[0] == "completed":
        progress = 100
        current_task = "Campaign completed successfully"
    
    return {
        "status": campaign_status[0],
        "progress": progress,
        "current_task": current_task,
        "tasks": [{"agent": t[0], "task": t[1], "status": t[2]} for t in tasks]
    }

def get_main_html() -> str:
    """Return the main HTML page with embedded CSS and JavaScript"""
    return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Customer Outreach AI Agent</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
            background: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header-bar {
            background: #2c3e50;
            color: white;
            padding: 15px 20px;
            border-radius: 8px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .header-bar h1 {
            font-size: 24px;
            font-weight: 600;
        }
        
        .header-bar .subtitle {
            font-size: 14px;
            opacity: 0.8;
            margin-top: 2px;
        }
        
        .btn {
            background: #3498db;
            color: white;
            padding: 12px 24px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            text-decoration: none;
            display: inline-block;
            transition: background 0.2s;
        }
        
        .btn:hover {
            background: #2980b9;
        }
        
        .btn-secondary {
            background: #95a5a6;
        }
        
        .btn-secondary:hover {
            background: #7f8c8d;
        }
        
        .card {
            background: white;
            border-radius: 8px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .form-section {
            background: #ecf0f1;
            padding: 25px;
            border-radius: 8px;
            margin: 20px 0;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        .form-group label {
            display: block;
            font-weight: 600;
            margin-bottom: 8px;
            color: #2c3e50;
        }
        
        .form-control {
            width: 100%;
            padding: 12px 16px;
            border: 1px solid #bdc3c7;
            border-radius: 6px;
            font-size: 14px;
            background: white;
            transition: border-color 0.2s;
        }
        
        .form-control:focus {
            outline: none;
            border-color: #3498db;
            box-shadow: 0 0 0 2px rgba(52, 152, 219, 0.2);
        }
        
        .progress-container {
            background: white;
            border-radius: 8px;
            padding: 30px;
            margin: 30px 0;
            text-align: center;
            display: none;
        }
        
        .progress-bar {
            background: #ecf0f1;
            height: 12px;
            border-radius: 6px;
            margin: 20px 0;
            overflow: hidden;
        }
        
        .progress-fill {
            background: linear-gradient(90deg, #3498db, #2ecc71);
            height: 100%;
            width: 0%;
            border-radius: 6px;
            transition: width 0.3s ease;
        }
        
        .agent-status {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-top: 30px;
        }
        
        .agent-card {
            background: white;
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 20px;
        }
        
        .agent-card h4 {
            color: #2c3e50;
            margin-bottom: 10px;
        }
        
        .task-status {
            background: #f8f9fa;
            border-left: 4px solid #3498db;
            padding: 15px;
            margin: 10px 0;
            border-radius: 0 6px 6px 0;
            font-size: 14px;
        }
        
        .status-completed {
            color: #27ae60;
            font-weight: 600;
        }
        
        .status-running {
            color: #f39c12;
            font-weight: 600;
        }
        
        .status-pending {
            color: #95a5a6;
            font-weight: 600;
        }
        
        .email-preview {
            background: white;
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 25px;
            margin: 20px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .email-subject {
            border-bottom: 1px solid #eee;
            padding-bottom: 15px;
            margin-bottom: 20px;
            font-weight: 600;
            color: #2c3e50;
        }
        
        .email-body {
            line-height: 1.8;
            white-space: pre-line;
        }
        
        .results-section {
            display: none;
        }
        
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        
        .metric-card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }
        
        .metric-value {
            font-size: 24px;
            font-weight: 700;
            color: #3498db;
            margin-bottom: 5px;
        }
        
        .metric-label {
            font-size: 14px;
            color: #7f8c8d;
        }
        
        .recent-campaigns {
            margin-top: 30px;
        }
        
        .campaign-list {
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            margin-top: 15px;
        }
        
        .campaign-tag {
            background: white;
            padding: 10px 16px;
            border-radius: 20px;
            font-size: 13px;
            color: #2c3e50;
            border: 1px solid #ecf0f1;
        }
        
        .loading-spinner {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #3498db;
            border-radius: 50%;
            width: 30px;
            height: 30px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        @media (max-width: 768px) {
            .container {
                padding: 15px;
            }
            
            .header-bar {
                flex-direction: column;
                gap: 15px;
                text-align: center;
            }
            
            .agent-status {
                grid-template-columns: 1fr;
            }
            
            .card {
                padding: 20px;
            }
        }
        
        .hidden {
            display: none !important;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header-bar">
            <div>
                <h1>Customer Outreach AI Agent</h1>
                <div class="subtitle">AI Powered Outreach System</div>
            </div>
            <div>
                <button class="btn btn-secondary" onclick="showHistory()">📄 History</button>
                <button class="btn" onclick="showNewCampaign()">🚀 New Campaign</button>
            </div>
        </div>

        <!-- New Campaign Form -->
        <div id="campaignForm" class="card">
            <h2>🎯 Create New Outreach Campaign</h2>
            
            <div class="form-section">
                <h3>Target Lead Information</h3>
                
                <form id="outreachForm">
                    <div class="form-group">
                        <label for="companyName">Company/Lead Name *</label>
                        <input type="text" id="companyName" name="company_name" class="form-control" 
                               placeholder="e.g., DeepLearningAI" required>
                    </div>
                    
                    <div class="form-group">
                        <label for="industry">Industry Sector *</label>
                        <input type="text" id="industry" name="industry" class="form-control" 
                               placeholder="e.g., Online Learning Platform" required>
                    </div>
                    
                    <div class="form-group">
                        <label for="decisionMaker">Key Decision Maker *</label>
                        <input type="text" id="decisionMaker" name="decision_maker" class="form-control" 
                               placeholder="e.g., Andrew Ng" required>
                    </div>
                    
                    <div class="form-group">
                        <label for="position">Position/Title *</label>
                        <input type="text" id="position" name="position" class="form-control" 
                               placeholder="e.g., CEO" required>
                    </div>
                    
                    <div class="form-group">
                        <label for="milestone">Recent Milestone/Achievement *</label>
                        <input type="text" id="milestone" name="milestone" class="form-control" 
                               placeholder="e.g., product launch, funding round, expansion" required>
                    </div>
                    
                    <div style="margin-top: 30px;">
                        <button type="submit" class="btn">🚀 Start Outreach Campaign</button>
                        <button type="button" class="btn btn-secondary">📁 Save as Template</button>
                    </div>
                </form>
            </div>
            
            <!-- Recent Campaigns -->
            <div class="recent-campaigns">
                <h4>Recent Campaigns</h4>
                <div class="campaign-list" id="recentCampaigns">
                    <div class="campaign-tag">TechCorp → John Smith</div>
                    <div class="campaign-tag">HealthTech Inc → Dr. Sarah Johnson</div>
                    <div class="campaign-tag">FinanceAI → Michael Chen</div>
                </div>
            </div>
        </div>

        <!-- Processing Status -->
        <div id="processingStatus" class="progress-container">
            <div class="loading-spinner"></div>
            <h2>🤖 AICRM Working...</h2>
            <div class="progress-bar">
                <div class="progress-fill" id="progressBar"></div>
            </div>
            <p id="currentTask">Initializing campaign processing...</p>
            
            <div class="agent-status">
                <div class="agent-card">
                    <h4>🕵️ Sales Representative Agent</h4>
                    <p><strong>Task:</strong> Lead Profiling & Analysis</p>
                    <div class="task-status" id="salesRepStatus">
                        <span class="status-pending">⏳ Pending:</span> Starting analysis...
                    </div>
                </div>
                
                <div class="agent-card">
                    <h4>📧 Lead Sales Representative Agent</h4>
                    <p><strong>Task:</strong> Personalized Outreach Creation</p>
                    <div class="task-status" id="outreachStatus">
                        <span class="status-pending">⏳ Pending:</span> Waiting for analysis...
                    </div>
                </div>
            </div>
            
            <button class="btn btn-secondary" onclick="stopProcessing()">❌ Stop Processing</button>
        </div>

        <!-- Results Section -->
        <div id="resultsSection" class="results-section">
            <div class="card">
                <div class="header-bar" style="margin: -30px -30px 30px -30px;">
                    <div><strong>Campaign Complete: <span id="completedCampaignName"></span></strong></div>
                    <div>
                        <button class="btn btn-secondary">📄 Export</button>
                        <button class="btn">📧 Send Email</button>
                        <button class="btn" onclick="showNewCampaign()">🔍 New Campaign</button>
                    </div>
                </div>
                
                <!-- Campaign Summary -->
                <div class="form-section">
                    <h3>📊 Campaign Summary</h3>
                    <div class="metrics-grid">
                        <div class="metric-card">
                            <div class="metric-value" id="personalizationScore">--</div>
                            <div class="metric-label">Personalization Score</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value" id="sentimentScore">--</div>
                            <div class="metric-label">Sentiment Score</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value" id="wordCount">--</div>
                            <div class="metric-label">Word Count</div>
                        </div>
                        <div class="metric-card">
                            <div class="metric-value" id="confidenceLevel">--</div>
                            <div class="metric-label">Confidence Level</div>
                        </div>
                    </div>
                </div>
                
                <!-- Generated Email -->
                <h3>📧 Generated Outreach Email</h3>
                <div class="email-preview">
                    <div class="email-subject">
                        <strong>Subject:</strong> <span id="emailSubject"></span>
                    </div>
                    <div class="email-body" id="emailBody"></div>
                </div>
                
                <div style="margin-top: 20px;">
                    <button class="btn">✏️ Edit Email</button>
                    <button class="btn btn-secondary">🔄 Regenerate</button>
                    <button class="btn btn-secondary">📝 Create Variations</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        let currentCampaignId = null;
        let processingInterval = null;

        // Form submission
        document.getElementById('outreachForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(e.target);
            
            try {
                const response = await fetch('/api/campaigns', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                currentCampaignId = result.campaign_id;
                
                // Show processing screen
                showProcessing();
                startStatusPolling();
                
            } catch (error) {
                alert('Error starting campaign: ' + error.message);
            }
        });

        function showNewCampaign() {
            document.getElementById('campaignForm').style.display = 'block';
            document.getElementById('processingStatus').style.display = 'none';
            document.getElementById('resultsSection').style.display = 'none';
            
            // Clear form
            document.getElementById('outreachForm').reset();
        }

        function showProcessing() {
            document.getElementById('campaignForm').style.display = 'none';
            document.getElementById('processingStatus').style.display = 'block';
            document.getElementById('resultsSection').style.display = 'none';
        }

        function showResults() {
            document.getElementById('campaignForm').style.display = 'none';
            document.getElementById('processingStatus').style.display = 'none';
            document.getElementById('resultsSection').style.display = 'block';
        }

        function startStatusPolling() {
            if (processingInterval) {
                clearInterval(processingInterval);
            }
            
            processingInterval = setInterval(async () => {
                try {
                    const response = await fetch(`/api/campaigns/${currentCampaignId}/status`);
                    const status = await response.json();
                    
                    updateProcessingStatus(status);
                    
                    if (status.status === 'completed') {
                        clearInterval(processingInterval);
                        await loadCampaignResults();
                    } else if (status.status === 'failed') {
                        clearInterval(processingInterval);
                        alert('Campaign processing failed. Please try again.');
                        showNewCampaign();
                    }
                    
                } catch (error) {
                    console.error('Error polling status:', error);
                }
            }, 2000);
        }

        function updateProcessingStatus(status) {
            // Update progress bar
            document.getElementById('progressBar').style.width = status.progress + '%';
            document.getElementById('currentTask').textContent = status.current_task;
            
            // Update agent status
            const salesStatus = document.getElementById('salesRepStatus');
            const outreachStatus = document.getElementById('outreachStatus');
            
            status.tasks.forEach(task => {
                let statusElement;
                let statusText;
                
                if (task.agent === 'Sales Representative') {
                    statusElement = salesStatus;
                } else if (task.agent === 'Lead Sales Representative') {
                    statusElement = outreachStatus;
                }
                
                if (task.status === 'completed') {
                    statusText = `<span class="status-completed">✅ Completed:</span> ${task.task}`;
                } else if (task.status === 'running') {
                    statusText = `<span class="status-running">🔄 In Progress:</span> ${task.task}`;
                } else {
                    statusText = `<span class="status-pending">⏳ Pending:</span> ${task.task}`;
                }
                
                if (statusElement) {
                    statusElement.innerHTML = statusText;
                }
            });
        }

        async function loadCampaignResults() {
            try {
                const response = await fetch(`/api/campaigns/${currentCampaignId}`);
                const campaign = await response.json();
                
                // Update results display
                document.getElementById('completedCampaignName').textContent = campaign.company_name;
                document.getElementById('emailSubject').textContent = campaign.email_subject;
                document.getElementById('emailBody').textContent = campaign.generated_email;
                
                // Update metrics
                document.getElementById('personalizationScore').textContent = 
                    campaign.personalization_score ? campaign.personalization_score + '%' : 'N/A';
                document.getElementById('sentimentScore').textContent = 
                    campaign.sentiment_score ? (campaign.sentiment_score * 100).toFixed(0) + '%' : 'N/A';
                document.getElementById('wordCount').textContent = campaign.word_count || 'N/A';
                document.getElementById('confidenceLevel').textContent = campaign.confidence_level || 'N/A';
                
                showResults();
                
            } catch (error) {
                console.error('Error loading results:', error);
                alert('Error loading campaign results');
            }
        }

        function stopProcessing() {
            if (processingInterval) {
                clearInterval(processingInterval);
            }
            showNewCampaign();
        }

        function showHistory() {
            alert('Campaign history feature coming soon!');
        }

        // Load recent campaigns on page load
        window.addEventListener('load', async function() {
            try {
                const response = await fetch('/api/campaigns');
                const data = await response.json();
                
                const recentContainer = document.getElementById('recentCampaigns');
                recentContainer.innerHTML = '';
                
                data.campaigns.slice(0, 5).forEach(campaign => {
                    const tag = document.createElement('div');
                    tag.className = 'campaign-tag';
                    tag.textContent = `${campaign.company_name} → ${campaign.decision_maker}`;
                    tag.style.cursor = 'pointer';
                    tag.onclick = () => {
                        // Pre-fill form with campaign data
                        document.getElementById('companyName').value = campaign.company_name;
                        document.getElementById('industry').value = campaign.industry;
                        document.getElementById('decisionMaker').value = campaign.decision_maker;
                        document.getElementById('position').value = campaign.position;
                    };
                    recentContainer.appendChild(tag);
                });
                
            } catch (error) {
                console.error('Error loading recent campaigns:', error);
            }
        });
    </script>
</body>
</html>'''

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)