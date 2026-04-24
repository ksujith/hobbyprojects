import streamlit as st
import sqlite3
import random
import os
import pandas as pd
import json
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List, Any, Optional

# Try to import LangChain components (optional)
try:
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

# --- CONFIGURATION ---
st.set_page_config(
    page_title="Campaign RL Agent v3.0",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🤖"
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 15px;
        padding: 20px;
        margin: 10px 0;
        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
    }
    .campaign-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 15px;
        border-left: 5px solid #28a745;
        margin: 10px 0;
    }
    .agent-status {
        color: #dc3545;
        font-weight: bold;
        font-size: 1.1em;
    }
    .success-status {
        color: #28a745;
        font-weight: bold;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
</style>
""", unsafe_allow_html=True)

# --- DATABASE CONNECTION ---
DATABASE_PATH = "outreach_campaigns.db"

def get_db_connection():
    """Get database connection"""
    return sqlite3.connect(DATABASE_PATH)

def init_rl_tables():
    """Initialize additional tables for RL tracking"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # RL Sessions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rl_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id TEXT,
            session_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            lead_profile TEXT,
            final_status TEXT,
            total_reward INTEGER,
            actions_taken TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # RL Actions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rl_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            action_type TEXT,
            agent_message TEXT,
            lead_response TEXT,
            reward INTEGER,
            state_before TEXT,
            state_after TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES rl_sessions (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize RL tables
init_rl_tables()

# --- ENHANCED LEAD GENERATION ---
def generate_campaign_lead():
    """Generate a lead using existing campaign data + RL enhancements"""
    # Read from existing campaigns database
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if we have existing campaigns
    cursor.execute("SELECT COUNT(*) FROM campaigns")
    campaign_count = cursor.fetchone()[0]
    
    if campaign_count > 0:
        # Use existing campaign data as inspiration
        cursor.execute("SELECT company_name, industry, decision_maker, position FROM campaigns ORDER BY RANDOM() LIMIT 1")
        existing_data = cursor.fetchone()
    else:
        existing_data = None
    
    conn.close()
    
    # Generate lead profile
    if existing_data:
        company_name, industry, decision_maker, position = existing_data
    else:
        companies = ["TechFlow Inc", "DataDriven Solutions", "CloudScale Systems", "InnovateNow Corp", "FutureTech Labs"]
        industries = ["Technology", "Healthcare", "Finance", "Manufacturing", "Retail"]
        names = ["Sarah Chen", "Michael Rodriguez", "Emily Johnson", "David Park", "Lisa Thompson"]
        positions = ["VP of Engineering", "CTO", "Head of Marketing", "Operations Director", "CEO"]
        
        company_name = random.choice(companies)
        industry = random.choice(industries)
        decision_maker = random.choice(names)
        position = random.choice(positions)
    
    company_sizes = ["Startup", "SMB", "Enterprise", "Fortune 500"]
    
    return {
        "name": decision_maker,
        "position": position,
        "company_name": company_name,
        "industry": industry,
        "company_size": random.choice(company_sizes),
        "interest_level": round(random.uniform(0.1, 0.9), 2),
        "status": "New",
        "created_at": datetime.now(),
        "pain_points": random.choice([
            "Manual processes", "Data integration", "Scalability issues", 
            "Cost optimization", "Team productivity", "Security concerns"
        ]),
        "budget_range": random.choice(["$10K-50K", "$50K-100K", "$100K-500K", "$500K+"]),
        "decision_timeline": random.choice(["Immediate", "1-3 months", "3-6 months", "6+ months"])
    }

# --- RL DECISION ENGINE ---
class RLSalesAgent:
    """Enhanced RL Agent with campaign integration"""
    
    def __init__(self):
        self.q_table = self._initialize_q_table()
        self.learning_rate = 0.1
        self.discount_factor = 0.9
        self.exploration_rate = 0.2
        
    def _initialize_q_table(self):
        """Initialize Q-table for state-action values"""
        states = ["New", "Connected", "Replied", "Meeting_Booked", "Lost"]
        actions = ["Connect", "Soft_Value", "Hard_Close", "Wait", "Follow_Up"]
        
        q_table = {}
        for state in states:
            q_table[state] = {}
            for action in actions:
                q_table[state][action] = 0.0
        
        return q_table
    
    def get_best_action(self, state, lead_profile=None):
        """Get best action using epsilon-greedy policy"""
        if random.random() < self.exploration_rate:
            # Explore: random action
            actions = list(self.q_table[state].keys())
            return random.choice(actions)
        else:
            # Exploit: best known action
            state_actions = self.q_table[state]
            best_action = max(state_actions.items(), key=lambda x: x[1])[0]
            
            # Context-aware adjustments based on lead profile
            if lead_profile:
                best_action = self._adjust_for_context(best_action, state, lead_profile)
            
            return best_action
    
    def _adjust_for_context(self, action, state, lead_profile):
        """Adjust action based on lead context"""
        # High-interest leads: be more aggressive
        if lead_profile.get('interest_level', 0.5) > 0.7 and state == "Connected":
            if action == "Soft_Value" and random.random() < 0.3:
                return "Hard_Close"
        
        # Low-interest leads: be more patient
        if lead_profile.get('interest_level', 0.5) < 0.3 and action == "Hard_Close":
            return "Soft_Value"
        
        # Enterprise companies: more formal approach
        if lead_profile.get('company_size') == "Enterprise" and state == "New":
            return "Connect"  # Always connect first for enterprise
        
        return action
    
    def update_q_value(self, state, action, reward, next_state):
        """Update Q-value using Q-learning algorithm"""
        current_q = self.q_table[state][action]
        max_next_q = max(self.q_table[next_state].values())
        
        new_q = current_q + self.learning_rate * (
            reward + self.discount_factor * max_next_q - current_q
        )
        
        self.q_table[state][action] = new_q
    
    def get_reasoning(self, action, state, lead_profile):
        """Get human-readable reasoning for the action"""
        reasoning_map = {
            ("Connect", "New"): f"Lead is new. Establishing connection is priority for {lead_profile.get('company_size', 'Unknown')} companies.",
            ("Soft_Value", "Connected"): f"Building rapport with {lead_profile.get('position', 'decision maker')}. Sharing relevant insights.",
            ("Hard_Close", "Replied"): f"Strong engagement detected. {lead_profile.get('decision_timeline', 'Unknown timeline')} suggests urgency.",
            ("Follow_Up", "Connected"): "Maintaining engagement without being pushy. Building long-term relationship.",
            ("Wait", any): "Strategic patience. Monitoring lead behavior and market timing."
        }
        
        return reasoning_map.get((action, state), f"Executing {action} strategy based on current {state} status.")

# --- LLM INTEGRATION (if available) ---
def generate_personalized_message(action, lead_profile, agent_reasoning):
    """Generate personalized message using LLM or fallback templates"""
    
    if LANGCHAIN_AVAILABLE and "OPENAI_API_KEY" in os.environ:
        try:
            llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.7)
            
            template = """
            You are a professional sales development representative with expertise in {industry}.
            
            LEAD PROFILE:
            Name: {name}
            Position: {position}
            Company: {company_name} ({company_size})
            Industry: {industry}
            Pain Points: {pain_points}
            Budget Range: {budget_range}
            Decision Timeline: {decision_timeline}
            
            CONTEXT: {reasoning}
            
            TASK: Write a {action_type} message for LinkedIn/Email.
            
            GUIDELINES:
            - If Connect: Professional introduction, mention their role/company
            - If Soft_Value: Share specific insight relevant to their pain points
            - If Hard_Close: Direct ask for meeting, reference urgency
            - If Follow_Up: Gentle re-engagement, add new value
            - If Wait: Brief check-in message
            
            Keep it conversational, professional, and under 100 words.
            Message:
            """
            
            prompt = ChatPromptTemplate.from_template(template)
            chain = prompt | llm | StrOutputParser()
            
            message = chain.invoke({
                "name": lead_profile['name'],
                "position": lead_profile['position'],
                "company_name": lead_profile['company_name'],
                "company_size": lead_profile['company_size'],
                "industry": lead_profile['industry'],
                "pain_points": lead_profile['pain_points'],
                "budget_range": lead_profile['budget_range'],
                "decision_timeline": lead_profile['decision_timeline'],
                "action_type": action,
                "reasoning": agent_reasoning
            })
            
            return message.strip()
            
        except Exception as e:
            st.warning(f"LLM generation failed: {e}. Using fallback templates.")
    
    # Fallback templates
    templates = {
        "Connect": f"Hi {lead_profile['name']}, I noticed you're leading {lead_profile['position']} at {lead_profile['company_name']}. I work with {lead_profile['industry']} companies on {lead_profile['pain_points'].lower()}. Would love to connect!",
        "Soft_Value": f"Thanks for connecting! I just published insights on {lead_profile['pain_points'].lower()} trends in {lead_profile['industry']}. Given your role at {lead_profile['company_name']}, thought you'd find it relevant. Happy to share!",
        "Hard_Close": f"I think we could solve your {lead_profile['pain_points'].lower()} challenges within your {lead_profile['budget_range']} budget. Given your {lead_profile['decision_timeline'].lower()} timeline, should we schedule 15 minutes this week?",
        "Follow_Up": f"Hope you're doing well! Wanted to circle back on our {lead_profile['industry']} discussion. Any updates on your {lead_profile['pain_points'].lower()} priorities?",
        "Wait": f"Quick check-in - how are things progressing with your {lead_profile['industry']} initiatives? Always happy to help when timing is right."
    }
    
    return templates.get(action, "Professional outreach message")

def simulate_lead_response(lead_profile, agent_message, action, current_status):
    """Simulate lead response with enhanced realism"""
    
    base_interest = lead_profile['interest_level']
    company_factor = {"Startup": 1.2, "SMB": 1.0, "Enterprise": 0.8, "Fortune 500": 0.6}
    position_factor = {"CEO": 0.7, "CTO": 1.1, "VP of Engineering": 1.0, "Head of Marketing": 1.2}
    timeline_factor = {"Immediate": 1.5, "1-3 months": 1.2, "3-6 months": 1.0, "6+ months": 0.8}
    
    # Calculate response probability
    response_prob = base_interest
    response_prob *= company_factor.get(lead_profile['company_size'], 1.0)
    response_prob *= position_factor.get(lead_profile['position'], 1.0)
    response_prob *= timeline_factor.get(lead_profile['decision_timeline'], 1.0)
    
    outcome_roll = random.random()
    reward = 0
    new_status = current_status
    
    # Enhanced response logic
    if action == "Connect":
        if current_status == "New":
            if outcome_roll < (0.4 + response_prob * 0.3):
                new_status = "Connected"
                reward = 10
                response = f"Thanks for connecting! Always interested in {lead_profile['industry']} innovations."
            else:
                reward = 0
                response = "(Connection request pending...)"
        else:
            reward = -5
            response = "Already connected - avoid duplicate outreach."
            
    elif action == "Soft_Value":
        if current_status == "Connected":
            if outcome_roll < (0.6 + response_prob * 0.2):
                new_status = "Replied"
                reward = 25
                response = f"Interesting insights! Our {lead_profile['pain_points'].lower()} challenges are top priority. Tell me more about your approach."
            else:
                reward = -2
                response = "(Seen but no reply...)"
        else:
            reward = -10
            response = "Cannot send value prop without connection."
            
    elif action == "Hard_Close":
        if current_status == "Replied":
            if outcome_roll < (0.7 + response_prob * 0.1):
                new_status = "Meeting_Booked"
                reward = 100
                response = f"Perfect timing! Given our {lead_profile['decision_timeline'].lower()} timeline, let's schedule for Tuesday 2pm."
            else:
                new_status = "Lost"
                reward = -75
                response = "Too aggressive for our current priorities. Please remove me from future outreach."
        else:
            new_status = "Lost"
            reward = -100
            response = "Premature closing attempt. Relationship damaged."
            
    elif action == "Follow_Up":
        if current_status == "Connected":
            if outcome_roll < 0.4:
                new_status = "Replied"
                reward = 15
                response = f"Good timing! We're actually revisiting our {lead_profile['pain_points'].lower()} strategy."
            else:
                reward = -1
                response = "(No response to follow-up)"
        else:
            reward = -5
            response = "Follow-up without proper foundation."
            
    elif action == "Wait":
        reward = -1  # Small time penalty
        if current_status == "Connected" and outcome_roll < 0.1:
            new_status = "Replied"
            reward = 20
            response = f"Hi! Been thinking about our conversation on {lead_profile['industry']} trends. Ready to explore next steps."
        else:
            response = "(Waiting period - monitoring activity...)"
    
    return response, reward, new_status

# --- STREAMLIT UI ---

# Initialize session state
if 'rl_agent' not in st.session_state:
    st.session_state.rl_agent = RLSalesAgent()
if 'current_lead' not in st.session_state:
    st.session_state.current_lead = generate_campaign_lead()
if 'session_history' not in st.session_state:
    st.session_state.session_history = []
if 'total_reward' not in st.session_state:
    st.session_state.total_reward = 0
if 'campaigns_data' not in st.session_state:
    st.session_state.campaigns_data = []

# Header
st.title("🤖 Campaign RL Agent v3.0")
st.markdown("**Integrated RL Sales Agent with Campaign Database & Advanced Analytics**")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["🎯 Live Campaign", "📊 Analytics Hub", "🗄️ Campaign Database", "⚙️ Agent Config"])

with tab4:
    st.header("🔧 Agent Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("RL Parameters")
        learning_rate = st.slider("Learning Rate", 0.01, 0.5, st.session_state.rl_agent.learning_rate, 0.01)
        exploration_rate = st.slider("Exploration Rate", 0.0, 0.5, st.session_state.rl_agent.exploration_rate, 0.05)
        discount_factor = st.slider("Discount Factor", 0.5, 1.0, st.session_state.rl_agent.discount_factor, 0.05)
        
        if st.button("Update RL Agent"):
            st.session_state.rl_agent.learning_rate = learning_rate
            st.session_state.rl_agent.exploration_rate = exploration_rate
            st.session_state.rl_agent.discount_factor = discount_factor
            st.success("RL Agent parameters updated!")
    
    with col2:
        st.subheader("LLM Settings")
        if LANGCHAIN_AVAILABLE:
            use_llm = st.checkbox("Use LLM for message generation", value="OPENAI_API_KEY" in os.environ)
            if use_llm and "OPENAI_API_KEY" not in os.environ:
                api_key = st.text_input("OpenAI API Key", type="password")
                if api_key:
                    os.environ["OPENAI_API_KEY"] = api_key
                    st.success("API Key set!")
        else:
            st.info("Install langchain-openai for LLM integration")
            use_llm = False
        
        st.subheader("Database Actions")
        if st.button("🗃️ Reset Campaign Database"):
            if st.checkbox("Confirm reset"):
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM rl_sessions")
                cursor.execute("DELETE FROM rl_actions")
                conn.commit()
                conn.close()
                st.success("Database reset!")

with tab3:
    st.header("🗄️ Campaign Database Integration")
    
    # Show existing campaigns from database
    conn = get_db_connection()
    
    # Recent campaigns
    campaigns_df = pd.read_sql_query("SELECT * FROM campaigns ORDER BY created_at DESC LIMIT 10", conn)
    if not campaigns_df.empty:
        st.subheader("📋 Recent Campaigns")
        st.dataframe(campaigns_df, use_container_width=True)
    else:
        st.info("No campaigns found in database. Start by creating some campaigns!")
    
    # RL Sessions history
    rl_sessions_df = pd.read_sql_query("SELECT * FROM rl_sessions ORDER BY session_start DESC LIMIT 10", conn)
    if not rl_sessions_df.empty:
        st.subheader("🤖 RL Session History")
        st.dataframe(rl_sessions_df, use_container_width=True)
    
    conn.close()
    
    # Create new campaign
    st.divider()
    st.subheader("➕ Create New Campaign")
    with st.form("new_campaign"):
        col1, col2 = st.columns(2)
        with col1:
            company = st.text_input("Company Name")
            industry = st.selectbox("Industry", ["Technology", "Healthcare", "Finance", "Manufacturing", "Retail"])
        with col2:
            decision_maker = st.text_input("Decision Maker")
            position = st.text_input("Position")
        milestone = st.text_area("Key Milestone/Goal")
        
        if st.form_submit_button("Create Campaign"):
            if all([company, industry, decision_maker, position, milestone]):
                conn = get_db_connection()
                cursor = conn.cursor()
                campaign_id = f"CAMP_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                cursor.execute(
                    "INSERT INTO campaigns (id, company_name, industry, decision_maker, position, milestone) VALUES (?, ?, ?, ?, ?, ?)",
                    (campaign_id, company, industry, decision_maker, position, milestone)
                )
                conn.commit()
                conn.close()
                st.success(f"Campaign {campaign_id} created!")
                st.rerun()

with tab2:
    st.header("📊 Advanced Analytics")
    
    # Performance metrics
    conn = get_db_connection()
    
    # Get RL performance data
    rl_metrics_query = """
    SELECT 
        COUNT(*) as total_sessions,
        AVG(total_reward) as avg_reward,
        COUNT(CASE WHEN final_status = 'Meeting_Booked' THEN 1 END) as successful_sessions
    FROM rl_sessions
    """
    
    rl_metrics = pd.read_sql_query(rl_metrics_query, conn)
    
    if not rl_metrics.empty and rl_metrics['total_sessions'].iloc[0] > 0:
        col1, col2, col3, col4 = st.columns(4)
        
        total_sessions = rl_metrics['total_sessions'].iloc[0]
        avg_reward = rl_metrics['avg_reward'].iloc[0] or 0
        successful_sessions = rl_metrics['successful_sessions'].iloc[0]
        conversion_rate = (successful_sessions / total_sessions) * 100 if total_sessions > 0 else 0
        
        col1.metric("Total Sessions", total_sessions)
        col2.metric("Avg Reward", f"{avg_reward:.1f}")
        col3.metric("Successful Sessions", successful_sessions)
        col4.metric("Conversion Rate", f"{conversion_rate:.1f}%")
        
        # Charts
        col1, col2 = st.columns(2)
        
        # Action distribution
        with col1:
            actions_query = "SELECT action_type, COUNT(*) as count FROM rl_actions GROUP BY action_type"
            actions_df = pd.read_sql_query(actions_query, conn)
            if not actions_df.empty:
                fig = px.pie(actions_df, values='count', names='action_type', title="Action Distribution")
                st.plotly_chart(fig, use_container_width=True)
        
        # Reward progression
        with col2:
            rewards_query = "SELECT session_id, total_reward FROM rl_sessions ORDER BY session_start"
            rewards_df = pd.read_sql_query(rewards_query, conn)
            if not rewards_df.empty:
                fig = px.line(rewards_df, x='session_id', y='total_reward', title="Reward Progression")
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("📈 Analytics will appear here after you run some RL sessions!")
    
    conn.close()

with tab1:
    st.header("🎯 Live Campaign Simulation")
    
    # Sidebar with lead profile
    with st.sidebar:
        st.header("🎯 Current Lead Profile")
        
        lead = st.session_state.current_lead
        
        # Enhanced lead profile card
        st.markdown(f"""
        <div class="metric-card">
            <h4>👤 {lead['name']}</h4>
            <p><strong>Position:</strong> {lead['position']}</p>
            <p><strong>Company:</strong> {lead['company_name']}</p>
            <p><strong>Industry:</strong> {lead['industry']} ({lead['company_size']})</p>
            <p><strong>Pain Points:</strong> {lead['pain_points']}</p>
            <p><strong>Budget:</strong> {lead['budget_range']}</p>
            <p><strong>Timeline:</strong> {lead['decision_timeline']}</p>
            <p><strong>Interest:</strong> {'🔥' if lead['interest_level'] > 0.7 else '🟡' if lead['interest_level'] > 0.4 else '❄️'} ({lead['interest_level']:.2f})</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Current state
        st.divider()
        st.subheader("📊 Campaign State")
        
        status_colors = {
            "New": "🔵",
            "Connected": "🟡", 
            "Replied": "🟠",
            "Meeting_Booked": "🟢",
            "Lost": "🔴"
        }
        
        st.markdown(f"**Status:** {status_colors.get(lead['status'], '⚪')} {lead['status']}")
        st.metric("Session Reward", st.session_state.total_reward)
        st.metric("Actions Taken", len(st.session_state.session_history))
        
        # Quick actions
        st.divider()
        st.subheader("🎮 Quick Actions")
        
        if st.button("🔄 Generate New Lead", use_container_width=True):
            # Save current session to database
            if st.session_state.session_history:
                conn = get_db_connection()
                cursor = conn.cursor()
                
                # Save RL session
                session_data = {
                    'lead_profile': json.dumps(st.session_state.current_lead),
                    'final_status': st.session_state.current_lead['status'],
                    'total_reward': st.session_state.total_reward,
                    'actions_taken': json.dumps([h['action'] for h in st.session_state.session_history])
                }
                
                cursor.execute(
                    "INSERT INTO rl_sessions (lead_profile, final_status, total_reward, actions_taken) VALUES (?, ?, ?, ?)",
                    (session_data['lead_profile'], session_data['final_status'], session_data['total_reward'], session_data['actions_taken'])
                )
                
                session_id = cursor.lastrowid
                
                # Save individual actions
                for action_data in st.session_state.session_history:
                    cursor.execute(
                        """INSERT INTO rl_actions 
                           (session_id, action_type, agent_message, lead_response, reward, state_before, state_after) 
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (session_id, action_data['action'], action_data['agent_message'], 
                         action_data['lead_response'], action_data['reward'], 
                         action_data['state_before'], action_data['state_after'])
                    )
                
                conn.commit()
                conn.close()
            
            # Reset for new lead
            st.session_state.current_lead = generate_campaign_lead()
            st.session_state.session_history = []
            st.session_state.total_reward = 0
            st.rerun()
        
        if st.button("💾 Save to Campaigns DB", use_container_width=True):
            # Save current lead as a campaign
            conn = get_db_connection()
            cursor = conn.cursor()
            
            campaign_id = f"RL_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            cursor.execute(
                """INSERT INTO campaigns 
                   (id, company_name, industry, decision_maker, position, milestone, status) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (campaign_id, lead['company_name'], lead['industry'], lead['name'], 
                 lead['position'], f"Address {lead['pain_points']} within {lead['decision_timeline']}", 
                 'processing')
            )
            
            conn.commit()
            conn.close()
            st.success(f"Saved as campaign: {campaign_id}")
    
    # Main interaction area
    col1, col2 = st.columns([2, 1])
    
    with col2:
        st.subheader("🧠 RL Decision Engine")
        
        lead = st.session_state.current_lead
        current_state = lead['status']
        
        # Get RL agent recommendation
        recommended_action = st.session_state.rl_agent.get_best_action(current_state, lead)
        reasoning = st.session_state.rl_agent.get_reasoning(recommended_action, current_state, lead)
        
        # Show Q-table values for current state
        q_values = st.session_state.rl_agent.q_table[current_state]
        
        st.markdown(f"""
        <div class="campaign-card">
            <h4>🎯 RL Recommendation</h4>
            <p><span class="agent-status">Best Action:</span> {recommended_action}</p>
            <p><strong>Reasoning:</strong> {reasoning}</p>
            <p><strong>Confidence:</strong> {'High' if max(q_values.values()) > 10 else 'Medium' if max(q_values.values()) > 0 else 'Learning'}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Q-values display
        st.subheader("📊 Q-Values (Learning Progress)")
        q_df = pd.DataFrame(list(q_values.items()), columns=['Action', 'Q-Value'])
        st.dataframe(q_df, use_container_width=True)
        
        st.divider()
        st.subheader("🎮 Action Selection")
        
        # Action buttons
        actions = ["Connect", "Soft_Value", "Hard_Close", "Follow_Up", "Wait"]
        disabled = lead['status'] in ['Meeting_Booked', 'Lost']
        
        action_icons = {
            "Connect": "🔗",
            "Soft_Value": "📄", 
            "Hard_Close": "💰",
            "Follow_Up": "🔄",
            "Wait": "⏳"
        }
        
        selected_action = None
        for action in actions:
            if st.button(f"{action_icons[action]} {action}", disabled=disabled, use_container_width=True):
                selected_action = action
                break
        
        # Process selected action
        if selected_action:
            state_before = lead['status']
            
            with st.spinner("🧠 RL Agent analyzing and generating message..."):
                # Generate message using LLM or templates
                agent_reasoning = st.session_state.rl_agent.get_reasoning(selected_action, state_before, lead)
                agent_message = generate_personalized_message(selected_action, lead, agent_reasoning)
            
            with st.spinner("🎭 Simulating lead response..."):
                # Simulate lead response
                lead_response, reward, state_after = simulate_lead_response(
                    lead, agent_message, selected_action, state_before
                )
            
            # Update RL agent
            st.session_state.rl_agent.update_q_value(state_before, selected_action, reward, state_after)
            
            # Update session state
            st.session_state.current_lead['status'] = state_after
            st.session_state.total_reward += reward
            
            # Add to history
            action_record = {
                'action': selected_action,
                'agent_message': agent_message,
                'lead_response': lead_response,
                'reward': reward,
                'state_before': state_before,
                'state_after': state_after,
                'timestamp': datetime.now(),
                'reasoning': agent_reasoning
            }
            
            st.session_state.session_history.append(action_record)
            st.rerun()
    
    with col1:
        st.subheader("💬 Campaign Conversation")
        
        # Status indicator
        status_messages = {
            "New": "🔵 Ready to initiate outreach",
            "Connected": "🟡 Connected - building relationship", 
            "Replied": "🟠 Engaged - strong interest detected",
            "Meeting_Booked": "🟢 SUCCESS - Meeting scheduled!",
            "Lost": "🔴 Campaign ended - relationship lost"
        }
        
        current_status = st.session_state.current_lead['status']
        st.markdown(f"**Status:** {status_messages.get(current_status, '⚪ Unknown')}")
        
        if not st.session_state.session_history:
            st.info("👋 Start your campaign by selecting an action! The RL agent will learn optimal strategies through interaction.")
        else:
            # Display conversation history
            for i, record in enumerate(st.session_state.session_history):
                with st.container():
                    # Agent message
                    with st.chat_message("assistant", avatar="🤖"):
                        st.write(f"**Action: {record['action']}**")
                        st.write(record['agent_message'])
                        st.caption(f"💭 Reasoning: {record['reasoning']}")
                        st.caption(f"⏰ {record['timestamp'].strftime('%H:%M:%S')}")
                    
                    # Lead response
                    with st.chat_message("user", avatar="👤"):
                        st.write(record['lead_response'])
                        if record['reward'] > 0:
                            st.success(f"✅ Reward: +{record['reward']}")
                        elif record['reward'] < 0:
                            st.error(f"❌ Penalty: {record['reward']}")
                        else:
                            st.info(f"⏸️ Neutral: {record['reward']}")
                        st.caption(f"🔄 State: {record['state_before']} → {record['state_after']}")
            
            # Final outcome display
            if current_status == "Meeting_Booked":
                st.balloons()
                st.success("🎉 **CAMPAIGN SUCCESS!** Meeting booked!")
                
                # Success metrics
                st.markdown("### 📊 Campaign Results")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Total Reward", st.session_state.total_reward)
                col2.metric("Actions Taken", len(st.session_state.session_history))
                col3.metric("Success Rate", "100%")
                col4.metric("Efficiency", f"{st.session_state.total_reward / max(len(st.session_state.session_history), 1):.1f}")
                
            elif current_status == "Lost":
                st.error("💔 **CAMPAIGN FAILED** - Lead relationship lost")
                
                # Failure analysis
                st.markdown("### 📊 Campaign Analysis")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Total Reward", st.session_state.total_reward)
                col2.metric("Actions Taken", len(st.session_state.session_history))
                col3.metric("Failure Point", record['state_before'])
                col4.metric("Learning Value", "High" if abs(st.session_state.total_reward) > 20 else "Medium")
        
        # Progress bar
        if st.session_state.session_history:
            st.divider()
            progress_mapping = {"New": 0, "Connected": 25, "Replied": 50, "Meeting_Booked": 100, "Lost": 0}
            progress = progress_mapping.get(current_status, 0)
            
            if current_status == "Meeting_Booked":
                st.progress(1.0, text="🎉 Campaign Successful - 100%")
            elif current_status == "Lost":
                st.progress(0.0, text="💔 Campaign Failed - 0%")
            else:
                st.progress(progress / 100, text=f"Campaign Progress: {progress}%")
            
            # Show next recommended action
            if current_status not in ["Meeting_Booked", "Lost"]:
                next_action = st.session_state.rl_agent.get_best_action(current_status, st.session_state.current_lead)
                st.info(f"💡 **RL Recommendation:** Next optimal action is '{next_action}' based on learned patterns")

# Show Q-learning progress
if len(st.session_state.session_history) > 0:
    st.divider()
    st.subheader("🧠 RL Learning Progress")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Show Q-table heatmap
        q_table_data = []
        states = list(st.session_state.rl_agent.q_table.keys())
        actions = list(st.session_state.rl_agent.q_table[states[0]].keys())
        
        for state in states:
            for action in actions:
                q_table_data.append({
                    'State': state,
                    'Action': action, 
                    'Q_Value': st.session_state.rl_agent.q_table[state][action]
                })
        
        q_df = pd.DataFrame(q_table_data)
        q_pivot = q_df.pivot(index='State', columns='Action', values='Q_Value')
        
        fig = px.imshow(q_pivot, 
                       title="Q-Table Heatmap (Agent Learning)",
                       color_continuous_scale="RdYlGn",
                       aspect="auto")
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Reward progression
        rewards = [sum([h['reward'] for h in st.session_state.session_history[:i+1]]) 
                  for i in range(len(st.session_state.session_history))]
        
        reward_df = pd.DataFrame({
            'Step': range(1, len(rewards) + 1),
            'Cumulative_Reward': rewards
        })
        
        fig = px.line(reward_df, x='Step', y='Cumulative_Reward', 
                     title="Reward Progression",
                     line_shape='linear')
        st.plotly_chart(fig, use_container_width=True)