#!/usr/bin/env python3
"""
Enhanced Customer Outreach System v2.0
Advanced AI-powered lead generation and outreach with improved prompts and capabilities
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

# ============================================================================
# ENHANCED TOOLS WITH BETTER ERROR HANDLING
# ============================================================================

class DatabaseTool(BaseTool):
    """Enhanced database tool with better error handling and logging"""
    name: str = "Advanced Database Tool"
    description: str = "Stores, retrieves, and analyzes lead information with enhanced data validation"
    
    def __init__(self):
        super().__init__()
        self.db_path = "leads_v2.db"
        self._init_db()
    
    def _init_db(self):
        """Initialize enhanced database schema"""
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
                company_size TEXT,
                revenue_range TEXT,
                budget_range TEXT,
                urgency_level TEXT,
                profile_data TEXT,
                research_score INTEGER,
                bant_score TEXT,
                outreach_status TEXT DEFAULT 'pending',
                campaign_data TEXT,
                response_tracking TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS campaign_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER,
                campaign_type TEXT,
                message_count INTEGER,
                open_rate REAL,
                response_rate REAL,
                conversion_rate REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (lead_id) REFERENCES leads (id)
            )
        ''')
        conn.commit()
        conn.close()
    
    def _run(self, action: str, data: str = None) -> str:
        """Enhanced database operations with validation"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            if action == "save_lead":
                lead_data = json.loads(data)
                # Validate required fields
                required_fields = ['lead_name', 'industry', 'key_decision_maker']
                for field in required_fields:
                    if not lead_data.get(field):
                        return f"Error: Missing required field '{field}'"
                
                cursor.execute('''
                    INSERT INTO leads (lead_name, industry, key_decision_maker, position, 
                                     milestone, contact_email, company_size, revenue_range,
                                     budget_range, urgency_level, profile_data, research_score, bant_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    lead_data.get('lead_name'),
                    lead_data.get('industry'),
                    lead_data.get('key_decision_maker'),
                    lead_data.get('position'),
                    lead_data.get('milestone'),
                    lead_data.get('contact_email'),
                    lead_data.get('company_size'),
                    lead_data.get('revenue_range'),
                    lead_data.get('budget_range'),
                    lead_data.get('urgency_level'),
                    json.dumps(lead_data.get('profile_data', {})),
                    lead_data.get('research_score', 0),
                    json.dumps(lead_data.get('bant_score', {}))
                ))
                conn.commit()
                return f"Lead {lead_data.get('lead_name')} saved successfully with ID {cursor.lastrowid}"
            
            elif action == "get_leads":
                cursor.execute("SELECT * FROM leads ORDER BY research_score DESC, created_at DESC LIMIT 20")
                leads = cursor.fetchall()
                return json.dumps([dict(zip([col[0] for col in cursor.description], row)) for row in leads])
            
            elif action == "analytics":
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total_leads,
                        AVG(research_score) as avg_score,
                        COUNT(CASE WHEN outreach_status = 'completed' THEN 1 END) as completed_campaigns
                    FROM leads
                ''')
                stats = cursor.fetchone()
                return json.dumps({
                    'total_leads': stats[0],
                    'average_research_score': round(stats[1] or 0, 2),
                    'completed_campaigns': stats[2]
                })
                
        except Exception as e:
            return f"Database error: {str(e)}"
        finally:
            conn.close()

class EnhancedSentimentAnalysisTool(BaseTool):
    """Advanced sentiment analysis with scoring and recommendations"""
    name: str = "Advanced Sentiment Analysis Tool"
    description: str = (
        "Analyzes text sentiment, tone, and emotional triggers to ensure "
        "outreach messages are positive, engaging, and appropriately persuasive. "
        "Returns sentiment score, tone analysis, and improvement suggestions."
    )
    
    def _run(self, text: str) -> str:
        """Enhanced sentiment analysis with detailed feedback"""
        if not text or len(text.strip()) < 10:
            return "Error: Text too short for meaningful analysis"
        
        # Enhanced word analysis
        positive_words = ['innovative', 'growth', 'success', 'opportunity', 'value',
                         'benefit', 'solution', 'achievement', 'excellence', 'partnership',
                         'transform', 'optimize', 'empower', 'streamline', 'competitive']
        
        negative_words = ['problem', 'issue', 'difficult', 'challenge', 'concern',
                         'struggle', 'pain', 'frustration', 'expensive', 'complex']
        
        urgency_words = ['urgent', 'quickly', 'immediately', 'deadline', 'limited time']
        
        text_lower = text.lower()
        word_count = len(text.split())
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        urgency_count = sum(1 for word in urgency_words if word in text_lower)
        
        # Calculate sentiment score
        base_score = 0.5
        sentiment_modifier = (positive_count - negative_count) * 0.1
        length_modifier = min(0.1, word_count / 1000)  # Bonus for appropriate length
        
        final_score = max(0.0, min(1.0, base_score + sentiment_modifier + length_modifier))
        
        # Determine sentiment category
        if final_score >= 0.7:
            sentiment = "highly positive"
        elif final_score >= 0.6:
            sentiment = "positive"
        elif final_score >= 0.4:
            sentiment = "neutral"
        else:
            sentiment = "negative"
        
        # Generate recommendations
        recommendations = []
        if final_score < 0.6:
            recommendations.append("Consider adding more value-focused language")
        if urgency_count > 2:
            recommendations.append("Reduce urgency language to avoid appearing pushy")
        if word_count > 200:
            recommendations.append("Consider shortening for better readability")
        if positive_count == 0:
            recommendations.append("Add positive outcome language")
            
        return json.dumps({
            'sentiment': sentiment,
            'score': round(final_score, 2),
            'word_count': word_count,
            'positive_words': positive_count,
            'negative_words': negative_count,
            'urgency_indicators': urgency_count,
            'recommendations': recommendations,
            'approval_status': 'approved' if final_score >= 0.6 else 'needs_revision'
        })

class CompetitorIntelligenceTool(BaseTool):
    """Enhanced competitor analysis with market positioning"""
    name: str = "Advanced Competitor Intelligence Tool"
    description: str = "Analyzes competitive landscape and market positioning with industry insights"
    
    def _run(self, company_name: str, industry: str) -> str:
        """Enhanced competitor analysis"""
        # Industry-specific competitor mapping
        competitors_db = {
            "Online Education Technology": {
                "direct": ["Coursera", "Udemy", "Pluralsight", "MasterClass"],
                "indirect": ["YouTube Learning", "LinkedIn Learning", "Skillshare"],
                "market_size": "$350B",
                "growth_rate": "15% annually",
                "key_trends": ["AI-powered personalization", "Micro-learning", "Corporate training"]
            },
            "Software Development": {
                "direct": ["GitHub", "GitLab", "Atlassian", "JetBrains"],
                "indirect": ["Microsoft DevOps", "AWS CodeCommit", "Azure DevOps"],
                "market_size": "$25B",
                "growth_rate": "12% annually", 
                "key_trends": ["DevOps automation", "AI code assistance", "Cloud-native development"]
            },
            "E-commerce": {
                "direct": ["Shopify", "WooCommerce", "BigCommerce", "Magento"],
                "indirect": ["Amazon", "Squarespace", "Wix"],
                "market_size": "$120B",
                "growth_rate": "18% annually",
                "key_trends": ["Mobile commerce", "Social commerce", "AI recommendations"]
            }
        }
        
        industry_info = competitors_db.get(industry, {
            "direct": ["Industry-specific competitors"],
            "indirect": ["General market players"], 
            "market_size": "Research required",
            "growth_rate": "Research required",
            "key_trends": ["Digital transformation", "AI adoption", "Customer experience"]
        })
        
        analysis = {
            "company": company_name,
            "industry": industry,
            "market_overview": {
                "size": industry_info["market_size"],
                "growth": industry_info["growth_rate"],
                "trends": industry_info["key_trends"]
            },
            "competitive_landscape": {
                "direct_competitors": industry_info["direct"][:3],
                "indirect_competitors": industry_info["indirect"][:3],
                "market_position": "Analysis shows strong differentiation opportunities"
            },
            "differentiation_opportunities": [
                "AI-powered personalization features",
                "Industry-specific customization",
                "Enhanced user experience design",
                "Integration ecosystem expansion",
                "Premium support and consulting services"
            ],
            "competitive_threats": [
                "Established market players with large user bases",
                "Price competition from low-cost providers",
                "Feature parity from major tech companies"
            ],
            "strategic_recommendations": [
                f"Position {company_name} as innovation leader in {industry}",
                "Focus on unique value propositions vs. direct feature comparison",
                "Leverage recent milestones as proof of momentum",
                "Emphasize personalized solution approach"
            ]
        }
        
        return json.dumps(analysis, indent=2)

# Initialize enhanced tools
database_tool = DatabaseTool()
enhanced_sentiment_tool = EnhancedSentimentAnalysisTool()
competitor_intel_tool = CompetitorIntelligenceTool()

# Standard tools
directory_read_tool = DirectoryReadTool(directory='./instructions')
file_read_tool = FileReadTool()
search_tool = SerperDevTool()
scrape_tool = ScrapeWebsiteTool()
file_writer_tool = FileWriterTool()

# ============================================================================
# ENHANCED AGENTS WITH IMPROVED PROMPTS
# ============================================================================

sales_research_agent = Agent(
    role="Senior Sales Research Specialist",
    goal=(
        "Conduct comprehensive lead qualification and competitive intelligence "
        "to identify high-value prospects that align with our ideal customer profile "
        "and have demonstrable budget, authority, need, and timeline (BANT criteria). "
        "Achieve 85%+ accuracy in lead scoring and qualification."
    ),
    backstory=(
        "You are a seasoned B2B sales research professional with 8+ years of experience "
        "in lead qualification and market intelligence. Your expertise lies in analyzing "
        "digital footprints, financial indicators, and business signals to identify "
        "prospects most likely to convert. You have a proven track record of increasing "
        "sales team efficiency by 40% through precise lead scoring and qualification. "
        "Your research methodology combines data analysis, social selling insights, "
        "and competitive intelligence to build comprehensive prospect profiles that "
        "enable highly targeted outreach campaigns. You're known for your attention to "
        "detail, fact-checking rigor, and ability to uncover insights others miss."
    ),
    allow_delegation=False,
    verbose=True,
    max_iter=3,
    memory=True
)

outreach_specialist_agent = Agent(
    role="Senior Outreach Marketing Specialist", 
    goal=(
        "Create compelling, personalized outreach campaigns that achieve >25% response rates "
        "by leveraging psychological triggers, value propositions, and timing optimization. "
        "Ensure every message provides standalone value and builds authentic relationships."
    ),
    backstory=(
        "You are an elite outreach specialist with a background in psychology and "
        "marketing automation. You've crafted over 10,000 personalized outreach messages "
        "across various industries, consistently achieving above-average response rates. "
        "Your approach combines behavioral psychology principles, persuasive copywriting, "
        "and data-driven personalization to create messages that resonate with decision-makers. "
        "You understand the buyer's journey intimately and know how to position solutions "
        "as must-have investments rather than nice-to-have features. Your messages are "
        "known for being concise, value-focused, and action-oriented while maintaining "
        "authenticity and building genuine relationships. You never send generic templates."
    ),
    allow_delegation=False,
    verbose=True,
    max_iter=3,
    memory=True
)

campaign_analyst_agent = Agent(
    role="Campaign Performance Analyst",
    goal=(
        "Analyze outreach campaign effectiveness and provide data-driven optimization "
        "recommendations to improve response rates and conversion metrics."
    ),
    backstory=(
        "You are a data-driven marketing analyst with expertise in campaign optimization "
        "and conversion rate analysis. You specialize in A/B testing, performance tracking, "
        "and identifying the key factors that drive successful outreach campaigns."
    ),
    allow_delegation=False,
    verbose=True,
    max_iter=2,
    memory=True
)

# ============================================================================
# ENHANCED TASKS WITH IMPROVED PROMPTS
# ============================================================================

comprehensive_lead_research_task = Task(
    description=(
        "OBJECTIVE: Conduct comprehensive research and qualification analysis on {lead_name}, "
        "a {industry} company, to determine their fit as a high-value prospect.\n\n"

        "RESEARCH REQUIREMENTS:\n"
        "1. COMPANY PROFILE:\n"
        "   - Revenue range and growth trajectory (last 2 years)\n"
        "   - Employee count and recent hiring trends\n"
        "   - Funding status, investors, and financial health indicators\n"
        "   - Market position and competitive landscape\n"
        "   - Technology stack and current solutions in use\n\n"

        "2. DECISION MAKER ANALYSIS:\n"
        "   - Key stakeholders and decision-making hierarchy\n"
        "   - Background, experience, and professional interests of {key_decision_maker}\n"
        "   - Recent content, posts, or public statements\n"
        "   - Pain points and business priorities based on public information\n\n"

        "3. BUSINESS TRIGGERS & TIMING:\n"
        "   - Recent milestones: {milestone} and other significant events\n"
        "   - Quarterly/annual business cycles and budget timing\n"
        "   - Expansion plans, new initiatives, or strategic changes\n"
        "   - Current challenges that align with our solution capabilities\n\n"

        "4. COMPETITIVE INTELLIGENCE:\n"
        "   - Current vendors/solutions they likely use\n"
        "   - Gaps in their current technology stack\n"
        "   - Budget allocation patterns for similar solutions\n\n"

        "RESEARCH GUIDELINES:\n"
        "- Only include information you can verify from reliable sources\n"
        "- Cite sources when possible (website URLs, press releases, etc.)\n"
        "- Flag any assumptions or unverified information clearly\n"
        "- Focus on information relevant to our value proposition\n"
        "- Identify specific business metrics or KPIs they likely track\n\n"

        "QUALIFICATION CRITERIA:\n"
        "Rate the lead on BANT criteria (1-5 scale):\n"
        "- Budget: Likelihood they have budget for our solution\n"
        "- Authority: Access to decision-makers identified\n"
        "- Need: Clear business need that aligns with our offering\n"
        "- Timeline: Urgency or timing indicators for purchase decision\n\n"

        "Save all findings to the database for future reference and analysis."
    ),
    expected_output=(
        "Deliver a comprehensive lead qualification report with the following structure:\n\n"

        "## EXECUTIVE SUMMARY\n"
        "- Overall lead score (1-100) with justification\n"
        "- BANT qualification ratings (Budget: X/5, Authority: X/5, Need: X/5, Timeline: X/5)\n"
        "- Primary recommendation (High/Medium/Low priority)\n"
        "- Confidence level in assessment\n\n"

        "## COMPANY INTELLIGENCE\n"
        "- Company overview with key metrics (revenue, employees, growth)\n"
        "- Financial health and growth indicators\n"
        "- Technology stack and current solutions\n"
        "- Market position and competitive context\n"
        "- Recent business developments and milestones\n\n"

        "## STAKEHOLDER ANALYSIS\n"
        "- Decision-maker profiles with contact preferences\n"
        "- Influence map and approval process\n"
        "- Personal interests and professional background\n"
        "- Recent activities and public statements\n"
        "- Communication style preferences\n\n"

        "## BUSINESS TRIGGERS & OPPORTUNITIES\n"
        "- Recent developments and their implications\n"
        "- Timing considerations and budget cycles\n"
        "- Specific pain points our solution addresses\n"
        "- Competitive vulnerabilities or gaps\n"
        "- Urgency indicators and decision timeline\n\n"

        "## ENGAGEMENT STRATEGY RECOMMENDATIONS\n"
        "- Optimal outreach timing and frequency\n"
        "- Key value propositions to emphasize\n"
        "- Relevant case studies or social proof\n"
        "- Potential objections and response strategies\n"
        "- Recommended communication channels\n\n"

        "## SOURCE VERIFICATION\n"
        "- List of sources consulted with URLs where available\n"
        "- Confidence level of each data point (High/Medium/Low)\n"
        "- Areas requiring additional research\n"
        "- Verification status of key claims"
    ),
    tools=[search_tool, scrape_tool, competitor_intel_tool, database_tool, file_writer_tool],
    agent=sales_research_agent,
)

strategic_outreach_campaign_task = Task(
    description=(
        "OBJECTIVE: Create a multi-touch outreach campaign for {key_decision_maker} at {lead_name} "
        "that achieves a >25% response rate through strategic personalization and value-focused messaging.\n\n"

        "CAMPAIGN REQUIREMENTS:\n"
        "1. PERSONALIZATION DEPTH:\n"
        "   - Reference specific details about their recent {milestone}\n"
        "   - Connect our solution to their likely business priorities\n"
        "   - Use their preferred communication style and tone\n"
        "   - Include relevant industry insights or trends\n"
        "   - Address their company's specific challenges\n\n"

        "2. VALUE PROPOSITION ALIGNMENT:\n"
        "   - Lead with business outcomes, not product features\n"
        "   - Quantify potential impact with realistic metrics\n"
        "   - Address their specific industry challenges\n"
        "   - Position our solution as a strategic investment\n"
        "   - Include relevant ROI projections\n\n"

        "3. PSYCHOLOGICAL TRIGGERS:\n"
        "   - Create appropriate urgency without being pushy\n"
        "   - Use social proof relevant to their industry/company size\n"
        "   - Appeal to their professional goals and aspirations\n"
        "   - Include reciprocity elements (valuable insights, resources)\n"
        "   - Build curiosity and intrigue\n\n"

        "4. MULTI-TOUCH SEQUENCE:\n"
        "   - Email 1: Introduction + Value hypothesis (150-200 words)\n"
        "   - Email 2: Follow-up with relevant case study (120-150 words)\n"
        "   - Email 3: Final attempt with different angle/offer (100-130 words)\n"
        "   - LinkedIn message: Brief, relationship-focused approach (50-75 words)\n\n"

        "MESSAGING GUIDELINES:\n"
        "- Keep subject lines under 50 characters\n"
        "- Use conversational, professional tone\n"
        "- Include specific, actionable next steps\n"
        "- Avoid jargon and overly promotional language\n"
        "- Each message should provide standalone value\n"
        "- Respect their time with concise, scannable format\n"
        "- Include clear value proposition in each touch\n\n"

        "COMPLIANCE REQUIREMENTS:\n"
        "- Ensure all claims are accurate and verifiable\n"
        "- Include proper opt-out language where required\n"
        "- Maintain professional boundaries\n"
        "- Respect communication preferences if known\n"
        "- Follow industry-specific regulations\n\n"

        "Run each message through sentiment analysis and optimize for maximum effectiveness."
    ),
    expected_output=(
        "Deliver a complete outreach campaign package with:\n\n"

        "## CAMPAIGN STRATEGY OVERVIEW\n"
        "- Target persona analysis and messaging themes\n"
        "- Optimal timing and sequencing rationale\n"
        "- Success metrics and expected response rates\n"
        "- Backup strategies if initial approach fails\n"
        "- Channel mix recommendations\n\n"

        "## EMAIL SEQUENCE (3 emails)\n"
        "For each email, provide:\n"
        "- Subject line (with 2-3 alternatives)\n"
        "- Email body with clear structure:\n"
        "  * Opening hook/personalization\n"
        "  * Value proposition statement\n"
        "  * Supporting evidence/social proof\n"
        "  * Clear call-to-action\n"
        "  * Professional signature\n"
        "- Optimal send timing recommendation\n"
        "- Sentiment analysis score and approval status\n"
        "- A/B testing variations\n\n"

        "## LINKEDIN OUTREACH\n"
        "- Connection request message (under 300 characters)\n"
        "- Follow-up message sequence (2-3 messages)\n"
        "- Content engagement strategy\n"
        "- Social proof elements to highlight\n\n"

        "## SUPPORTING MATERIALS\n"
        "- One-page value proposition summary\n"
        "- Relevant case study highlights\n"
        "- Industry-specific talking points\n"
        "- Competitive differentiation points\n\n"

        "## OBJECTION HANDLING PLAYBOOK\n"
        "- Top 5 likely objections with responses\n"
        "- Pricing/budget conversation starters\n"
        "- Competition comparison talking points\n"
        "- Risk mitigation and guarantee options\n\n"

        "## TRACKING & OPTIMIZATION\n"
        "- Key performance indicators to monitor\n"
        "- A/B testing recommendations\n"
        "- Campaign adjustment triggers\n"
        "- Success milestone definitions\n"
        "- Follow-up sequence for responders"
    ),
    tools=[enhanced_sentiment_tool, database_tool, file_writer_tool, search_tool],
    agent=outreach_specialist_agent,
)

campaign_analysis_task = Task(
    description=(
        "OBJECTIVE: Analyze the created outreach campaign for optimization opportunities "
        "and provide data-driven recommendations for improvement.\n\n"

        "ANALYSIS REQUIREMENTS:\n"
        "1. MESSAGE EFFECTIVENESS ASSESSMENT:\n"
        "   - Sentiment analysis of each message\n"
        "   - Readability and scan-ability scores\n"
        "   - Call-to-action clarity and strength\n"
        "   - Personalization depth evaluation\n\n"

        "2. COMPETITIVE BENCHMARKING:\n"
        "   - Compare against industry best practices\n"
        "   - Identify unique differentiation elements\n"
        "   - Assess competitive positioning strength\n\n"

        "3. OPTIMIZATION RECOMMENDATIONS:\n"
        "   - A/B testing suggestions\n"
        "   - Message timing optimization\n"
        "   - Channel mix improvements\n"
        "   - Follow-up sequence enhancements\n\n"

        "Store analysis results in database for future campaign improvements."
    ),
    expected_output=(
        "Deliver a comprehensive campaign analysis report with:\n\n"

        "## CAMPAIGN EFFECTIVENESS ANALYSIS\n"
        "- Overall campaign score (1-100)\n"
        "- Message-by-message effectiveness ratings\n"
        "- Sentiment analysis summary\n"
        "- Personalization depth assessment\n\n"

        "## OPTIMIZATION RECOMMENDATIONS\n"
        "- Top 3 high-impact improvements\n"
        "- A/B testing priorities\n"
        "- Timing optimization suggestions\n"
        "- Channel mix refinements\n\n"

        "## PREDICTIVE SUCCESS METRICS\n"
        "- Expected response rate range\n"
        "- Conversion probability assessment\n"
        "- Revenue impact projection\n"
        "- Timeline to close estimation\n\n"

        "## CONTINUOUS IMPROVEMENT PLAN\n"
        "- Performance monitoring framework\n"
        "- Feedback collection mechanisms\n"
        "- Campaign iteration schedule\n"
        "- Success milestone definitions"
    ),
    tools=[enhanced_sentiment_tool, database_tool, competitor_intel_tool],
    agent=campaign_analyst_agent,
)

# ============================================================================
# ENHANCED CREW CONFIGURATION
# ============================================================================

enhanced_outreach_crew = Crew(
    agents=[sales_research_agent, outreach_specialist_agent, campaign_analyst_agent],
    tasks=[comprehensive_lead_research_task, strategic_outreach_campaign_task, campaign_analysis_task],
    verbose=True,
    memory=True,
    planning=True,
    max_rpm=10,
)

# ============================================================================
# INPUT VALIDATION AND TEMPLATES
# ============================================================================

def validate_inputs(inputs):
    """Enhanced input validation with detailed feedback"""
    required_fields = ['lead_name', 'industry', 'key_decision_maker', 'position']
    errors = []
    
    for field in required_fields:
        if not inputs.get(field) or not inputs[field].strip():
            errors.append(f"Required field '{field}' is missing or empty")
    
    if errors:
        raise ValueError("Input validation failed:\n" + "\n".join(errors))
    
    # Set intelligent defaults
    defaults = {
        'milestone': 'recent business expansion',
        'budget_range': 'enterprise ($50K+)',
        'urgency_level': 'medium',
        'company_size': '50-500 employees',
        'revenue_range': '$10M-100M',
        'previous_interactions': 'none',
        'referral_source': 'targeted research'
    }
    
    for key, default_value in defaults.items():
        if key not in inputs or not inputs[key]:
            inputs[key] = default_value
    
    return inputs

# Industry-specific templates
INDUSTRY_TEMPLATES = {
    "Online Education Technology": {
        "pain_points": ["student engagement", "learning outcomes", "scalability", "content quality"],
        "value_drivers": ["personalization", "completion rates", "ROI measurement", "user experience"],
        "decision_factors": ["pedagogical effectiveness", "technical integration", "cost per learner"],
        "budget_cycle": "Q3-Q4 (academic year planning)",
        "key_metrics": ["completion rates", "engagement scores", "revenue per learner"]
    },
    "Software Development": {
        "pain_points": ["development velocity", "code quality", "collaboration", "deployment"],
        "value_drivers": ["productivity", "quality", "speed to market", "developer satisfaction"],
        "decision_factors": ["technical fit", "integration ease", "developer adoption"],
        "budget_cycle": "Q1-Q2 (annual planning)",
        "key_metrics": ["deployment frequency", "lead time", "bug rates"]
    },
    "Healthcare": {
        "pain_points": ["patient outcomes", "operational efficiency", "compliance", "cost management"],
        "value_drivers": ["patient satisfaction", "cost reduction", "regulatory compliance"],
        "decision_factors": ["clinical evidence", "ROI", "integration capabilities"],
        "budget_cycle": "Q4-Q1 (fiscal year planning)",
        "key_metrics": ["patient satisfaction", "cost per patient", "compliance scores"]
    }
}

def run_enhanced_outreach_campaign(lead_data: Dict[str, str]):
    """Run the enhanced outreach campaign with full validation and tracking"""
    print(f"\n🚀 Starting enhanced outreach campaign for {lead_data['lead_name']}")
    
    try:
        # Validate inputs
        validated_data = validate_inputs(lead_data)
        print("✅ Input validation passed")
        
        # Enhance data with industry templates
        industry = validated_data['industry']
        if industry in INDUSTRY_TEMPLATES:
            template = INDUSTRY_TEMPLATES[industry]
            validated_data.update({
                'industry_pain_points': template['pain_points'],
                'industry_value_drivers': template['value_drivers'],
                'budget_cycle': template['budget_cycle'],
                'key_metrics': template['key_metrics']
            })
        
        # Save initial lead data
        database_tool._run("save_lead", json.dumps(validated_data))
        print("✅ Lead data saved to database")
        
        # Execute the enhanced crew
        print("🔄 Executing AI agent workflow...")
        result = enhanced_outreach_crew.kickoff(inputs=validated_data)
        
        # Update status and save campaign results
        campaign_data = {
            'lead_name': validated_data['lead_name'],
            'status': 'campaign_created',
            'campaign_result': str(result),
            'created_at': datetime.now().isoformat()
        }
        
        database_tool._run("update_status", json.dumps(campaign_data))
        print("✅ Campaign completed and results saved")
        
        return result
        
    except Exception as e:
        print(f"❌ Error running enhanced campaign: {e}")
        return None

# Example usage with enhanced inputs
if __name__ == "__main__":
    enhanced_inputs = {
        "lead_name": "DeepLearningAI",
        "industry": "Online Education Technology",
        "key_decision_maker": "Andrew Ng",
        "position": "CEO and Founder",
        "milestone": "new AI course platform launch",
        "budget_range": "$100K-500K annually",
        "urgency_level": "high",
        "company_size": "50-200 employees",
        "revenue_range": "$10M-50M",
        "previous_interactions": "none",
        "referral_source": "industry research"
    }
    
    print("🎯 Enhanced Customer Outreach System v2.0")
    print("=" * 50)
    print("Key improvements:")
    print("✅ Enhanced agent expertise and prompts")
    print("✅ Comprehensive task descriptions with clear guidelines")
    print("✅ Advanced sentiment analysis and optimization")
    print("✅ Industry-specific templates and customization")
    print("✅ Enhanced database schema and analytics")
    print("✅ Campaign performance tracking and analysis")
    print("✅ Multi-agent workflow with quality validation")
    print("=" * 50)
    
    try:
        result = run_enhanced_outreach_campaign(enhanced_inputs)
        if result:
            print("\n🎉 Enhanced campaign completed successfully!")
            print("Check the database for detailed analytics and campaign data.")
    except Exception as e:
        print(f"❌ Error: {e}")