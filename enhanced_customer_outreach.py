#!/usr/bin/env python3
"""
Enhanced Customer Outreach System
A more sophisticated version with additional tools and capabilities
"""

import os
import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Any
from dotenv import load_dotenv

from crewai_tools import (
    DirectoryReadTool, 
    FileReadTool, 
    SerperDevTool,
    ScrapeWebsiteTool,
    FileWriterTool
)
from crewai import Agent, Task, Crew
from crewai.tools import BaseTool

# Load environment variables
load_dotenv()

# Validate required environment variables
required_env_vars = ['OPENAI_API_KEY']
for var in required_env_vars:
    if not os.getenv(var):
        raise ValueError(f"Required environment variable {var} is not set")

os.environ['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY')

class DatabaseTool(BaseTool):
    """Tool for managing lead data in SQLite database"""
    name: str = "Database Tool"
    description: str = "Stores and retrieves lead information from database"
    
    def __init__(self):
        super().__init__()
        self.db_path = "leads.db"
        self._init_db()
    
    def _init_db(self):
        """Initialize the database with leads table"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_name TEXT NOT NULL,
                industry TEXT,
                key_decision_maker TEXT,
                position TEXT,
                milestone TEXT,
                contact_email TEXT,
                profile_data TEXT,
                outreach_status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
    
    def _run(self, action: str, data: str = None) -> str:
        """Execute database operations"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            if action == "save_lead":
                lead_data = json.loads(data)
                cursor.execute('''
                    INSERT INTO leads (lead_name, industry, key_decision_maker, position, milestone, contact_email, profile_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    lead_data.get('lead_name'),
                    lead_data.get('industry'),
                    lead_data.get('key_decision_maker'),
                    lead_data.get('position'),
                    lead_data.get('milestone'),
                    lead_data.get('contact_email'),
                    json.dumps(lead_data.get('profile_data', {}))
                ))
                conn.commit()
                return f"Lead {lead_data.get('lead_name')} saved successfully"
            
            elif action == "get_leads":
                cursor.execute("SELECT * FROM leads ORDER BY created_at DESC LIMIT 10")
                leads = cursor.fetchall()
                return json.dumps([dict(zip([col[0] for col in cursor.description], row)) for row in leads])
            
            elif action == "update_status":
                status_data = json.loads(data)
                cursor.execute('''
                    UPDATE leads SET outreach_status = ?, updated_at = CURRENT_TIMESTAMP 
                    WHERE lead_name = ?
                ''', (status_data['status'], status_data['lead_name']))
                conn.commit()
                return f"Status updated for {status_data['lead_name']}"
            
        except Exception as e:
            return f"Database error: {str(e)}"
        finally:
            conn.close()

class EmailValidatorTool(BaseTool):
    """Tool for validating email addresses"""
    name: str = "Email Validator Tool"
    description: str = "Validates email addresses and suggests improvements"
    
    def _run(self, email: str) -> str:
        """Validate email format"""
        import re
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if re.match(pattern, email):
            return f"Email {email} is valid"
        else:
            return f"Email {email} is invalid. Please check the format."

class CompetitorAnalysisTool(BaseTool):
    """Tool for analyzing competitors"""
    name: str = "Competitor Analysis Tool"
    description: str = "Analyzes competitor information and market positioning"
    
    def _run(self, company_name: str, industry: str) -> str:
        """Analyze competitors for a company"""
        # This is a simplified version - in reality, you'd integrate with APIs
        competitors = {
            "Online Learning Platform": ["Coursera", "Udemy", "Pluralsight", "LinkedIn Learning"],
            "Software Development": ["GitHub", "GitLab", "Atlassian", "Microsoft"],
            "E-commerce": ["Shopify", "WooCommerce", "BigCommerce", "Magento"]
        }
        
        industry_competitors = competitors.get(industry, ["No specific competitors found"])
        
        analysis = f"""
        Competitor Analysis for {company_name} in {industry}:
        
        Main Competitors: {', '.join(industry_competitors[:3])}
        
        Market Position: Based on the industry, {company_name} likely competes on:
        - Technology innovation
        - User experience
        - Content quality
        - Pricing strategies
        
        Differentiation Opportunities:
        - Personalized learning paths
        - AI-powered recommendations  
        - Industry-specific content
        - Integration capabilities
        """
        
        return analysis

# Enhanced Sentiment Analysis Tool
class EnhancedSentimentAnalysisTool(BaseTool):
    name: str = "Enhanced Sentiment Analysis Tool"
    description: str = "Analyzes sentiment and provides suggestions for improvement"
    
    def _run(self, text: str) -> str:
        """Analyze sentiment and provide feedback"""
        # Simple keyword-based analysis (in production, use proper NLP libraries)
        positive_words = ['excited', 'great', 'excellent', 'amazing', 'congratulations', 'success', 'innovative']
        negative_words = ['unfortunately', 'problem', 'issue', 'difficult', 'concern', 'worried']
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count > negative_count:
            sentiment = "positive"
            suggestion = "Great tone! The message sounds engaging and optimistic."
        elif negative_count > positive_count:
            sentiment = "negative" 
            suggestion = "Consider rephrasing to be more positive and solution-focused."
        else:
            sentiment = "neutral"
            suggestion = "Consider adding more enthusiasm and specific benefits to make it more engaging."
        
        return f"Sentiment: {sentiment}. {suggestion}"

# Initialize tools
database_tool = DatabaseTool()
email_validator_tool = EmailValidatorTool()
competitor_analysis_tool = CompetitorAnalysisTool()
enhanced_sentiment_tool = EnhancedSentimentAnalysisTool()

directory_read_tool = DirectoryReadTool(directory='./instructions')
file_read_tool = FileReadTool()
search_tool = SerperDevTool()
scrape_tool = ScrapeWebsiteTool()
file_writer_tool = FileWriterTool()

# Enhanced Agents
research_analyst_agent = Agent(
    role="Research Analyst",
    goal="Conduct comprehensive research on leads including competitor analysis and market positioning",
    backstory=(
        "You are a skilled research analyst with expertise in market research, "
        "competitive analysis, and business intelligence. You excel at gathering "
        "and synthesizing information from multiple sources to create comprehensive "
        "lead profiles that inform strategic outreach decisions."
    ),
    allow_delegation=False,
    verbose=True
)

sales_rep_agent = Agent(
    role="Sales Representative", 
    goal="Identify high-value leads and create detailed lead profiles",
    backstory=(
        "As a senior sales representative at CrewAI, you combine traditional "
        "sales expertise with modern AI tools to identify and qualify leads. "
        "You're known for your methodical approach to lead research and your "
        "ability to uncover unique value propositions for each prospect."
    ),
    allow_delegation=False,
    verbose=True
)

lead_sales_rep_agent = Agent(
    role="Lead Sales Representative",
    goal="Create personalized, high-converting outreach campaigns", 
    backstory=(
        "You are the top-performing sales representative at CrewAI, known for "
        "your ability to craft compelling, personalized messages that resonate "
        "with C-level executives. Your outreach campaigns consistently achieve "
        "high response rates through careful research and authentic communication."
    ),
    allow_delegation=False,
    verbose=True
)

# Enhanced Tasks
lead_research_task = Task(
    description=(
        "Conduct comprehensive research on {lead_name} in the {industry} sector. "
        "Research should include:\n"
        "1. Company background and recent news\n"
        "2. Key decision makers and their backgrounds\n"
        "3. Recent milestones and achievements\n"
        "4. Competitor analysis and market position\n"
        "5. Technology stack and current solutions\n"
        "6. Potential pain points and opportunities\n"
        "Save the lead information to the database for future reference."
    ),
    expected_output=(
        "A detailed research report including company profile, key personnel, "
        "recent developments, competitive landscape, and identified opportunities "
        "for our solutions. Include specific data points and sources."
    ),
    tools=[search_tool, scrape_tool, competitor_analysis_tool, database_tool, file_writer_tool],
    agent=research_analyst_agent,
)

lead_profiling_task = Task(
    description=(
        "Using the research report, create a comprehensive lead profile for {lead_name}. "
        "Focus on:\n"
        "1. Decision-making process and key influencers\n"
        "2. Current challenges and pain points\n"
        "3. Budget and timeline considerations\n"
        "4. Preferred communication styles\n"
        "5. Success metrics and KPIs they care about\n"
        "Validate contact information and update lead status in database."
    ),
    expected_output=(
        "A strategic lead profile with actionable insights for outreach, "
        "including recommended messaging angles, timing, and approach strategy."
    ),
    tools=[database_tool, email_validator_tool, file_read_tool],
    agent=sales_rep_agent,
)

personalized_outreach_task = Task(
    description=(
        "Create a multi-touch outreach campaign for {key_decision_maker} at {lead_name}. "
        "The campaign should:\n"
        "1. Reference their recent {milestone} authentically\n"
        "2. Connect our solutions to their specific challenges\n"
        "3. Include 3-4 different message variations\n"
        "4. Suggest optimal timing and channels\n"
        "5. Include follow-up sequence recommendations\n"
        "Ensure all messages pass sentiment analysis and maintain professional tone."
    ),
    expected_output=(
        "A complete outreach campaign including:\n"
        "- Initial outreach email\n"
        "- LinkedIn message\n" 
        "- Follow-up sequences (2-3 messages)\n"
        "- Timing recommendations\n"
        "- Success metrics to track"
    ),
    tools=[enhanced_sentiment_tool, database_tool, file_writer_tool],
    agent=lead_sales_rep_agent,
)

# Create Enhanced Crew
enhanced_crew = Crew(
    agents=[research_analyst_agent, sales_rep_agent, lead_sales_rep_agent],
    tasks=[lead_research_task, lead_profiling_task, personalized_outreach_task],
    verbose=True,
    memory=True
)

def run_outreach_campaign(lead_data: Dict[str, str]):
    """Run the complete outreach campaign for a lead"""
    print(f"\n🚀 Starting outreach campaign for {lead_data['lead_name']}")
    
    # Save initial lead data
    database_tool._run("save_lead", json.dumps(lead_data))
    
    # Execute the crew
    result = enhanced_crew.kickoff(inputs=lead_data)
    
    # Update status
    database_tool._run("update_status", json.dumps({
        'lead_name': lead_data['lead_name'], 
        'status': 'campaign_created'
    }))
    
    return result

# Example usage
if __name__ == "__main__":
    sample_lead = {
        "lead_name": "DeepLearningAI",
        "industry": "Online Learning Platform", 
        "key_decision_maker": "Andrew Ng",
        "position": "CEO",
        "milestone": "new course launch",
        "contact_email": "contact@deeplearning.ai"
    }
    
    try:
        result = run_outreach_campaign(sample_lead)
        print("\n✅ Campaign completed successfully!")
        print(f"Result: {result}")
    except Exception as e:
        print(f"❌ Error running campaign: {e}")