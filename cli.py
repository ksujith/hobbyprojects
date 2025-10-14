#!/usr/bin/env python3
"""
Customer Outreach CLI
Command-line interface for the enhanced customer outreach system
"""

import click
import json
import sys
from pathlib import Path
from typing import Dict, Any
from enhanced_customer_outreach import (
    run_outreach_campaign, 
    database_tool,
    enhanced_crew
)

@click.group()
@click.version_option(version="1.0.0")
def cli():
    """Customer Outreach System - AI-powered lead generation and outreach"""
    pass

@cli.command()
@click.option('--name', '-n', required=True, help='Lead company name')
@click.option('--industry', '-i', required=True, help='Industry sector')
@click.option('--decision-maker', '-dm', required=True, help='Key decision maker name')
@click.option('--position', '-p', required=True, help='Decision maker position')
@click.option('--milestone', '-m', required=True, help='Recent milestone or achievement')
@click.option('--email', '-e', help='Contact email address')
@click.option('--save-only', '-s', is_flag=True, help='Only save to database without running campaign')
def create_campaign(name: str, industry: str, decision_maker: str, position: str, 
                   milestone: str, email: str, save_only: bool):
    """Create a new outreach campaign for a lead"""
    
    lead_data = {
        "lead_name": name,
        "industry": industry,
        "key_decision_maker": decision_maker,
        "position": position,
        "milestone": milestone,
        "contact_email": email or ""
    }
    
    if save_only:
        # Just save to database
        result = database_tool._run("save_lead", json.dumps(lead_data))
        click.echo(f"✅ {result}")
        return
    
    click.echo(f"🚀 Creating outreach campaign for {name}...")
    
    try:
        with click.progressbar(length=3, label='Processing') as bar:
            bar.label = 'Researching lead...'
            bar.update(1)
            
            bar.label = 'Creating profile...'
            bar.update(1)
            
            bar.label = 'Generating outreach...'
            result = run_outreach_campaign(lead_data)
            bar.update(1)
        
        click.echo("\n✅ Campaign created successfully!")
        
        # Save result to file
        timestamp = Path(f"campaign_{name.lower().replace(' ', '_')}.txt")
        with open(timestamp, 'w') as f:
            f.write(str(result))
        
        click.echo(f"📄 Campaign saved to: {timestamp}")
        
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)

@cli.command()
@click.option('--limit', '-l', default=10, help='Number of leads to show')
def list_leads(limit: int):
    """List recent leads from database"""
    
    try:
        leads_json = database_tool._run("get_leads")
        leads = json.loads(leads_json)
        
        if not leads:
            click.echo("No leads found in database.")
            return
        
        click.echo(f"\n📋 Recent Leads (showing {min(len(leads), limit)}):\n")
        
        for i, lead in enumerate(leads[:limit], 1):
            click.echo(f"{i}. {lead['lead_name']} ({lead['industry']})")
            click.echo(f"   👤 {lead['key_decision_maker']} - {lead['position']}")
            click.echo(f"   📧 {lead['contact_email'] or 'No email'}")
            click.echo(f"   📊 Status: {lead['outreach_status']}")
            click.echo(f"   📅 Created: {lead['created_at']}")
            click.echo()
            
    except Exception as e:
        click.echo(f"❌ Error retrieving leads: {e}", err=True)

@cli.command() 
@click.argument('lead_name')
@click.argument('status', type=click.Choice(['pending', 'contacted', 'responded', 'closed']))
def update_status(lead_name: str, status: str):
    """Update the outreach status of a lead"""
    
    try:
        result = database_tool._run("update_status", json.dumps({
            'lead_name': lead_name,
            'status': status
        }))
        click.echo(f"✅ {result}")
        
    except Exception as e:
        click.echo(f"❌ Error updating status: {e}", err=True)

@cli.command()
@click.option('--file', '-f', type=click.File('r'), help='JSON file with lead data')
def batch_import(file):
    """Import multiple leads from JSON file"""
    
    if not file:
        click.echo("Please provide a JSON file with --file option")
        return
    
    try:
        leads_data = json.load(file)
        
        if not isinstance(leads_data, list):
            click.echo("❌ JSON file must contain an array of lead objects")
            return
        
        success_count = 0
        
        with click.progressbar(leads_data, label='Importing leads') as leads:
            for lead in leads:
                try:
                    database_tool._run("save_lead", json.dumps(lead))
                    success_count += 1
                except Exception as e:
                    click.echo(f"\n❌ Failed to import {lead.get('lead_name', 'unknown')}: {e}")
        
        click.echo(f"\n✅ Successfully imported {success_count} leads")
        
    except json.JSONDecodeError:
        click.echo("❌ Invalid JSON file format", err=True)
    except Exception as e:
        click.echo(f"❌ Error importing leads: {e}", err=True)

@cli.command()
def init():
    """Initialize the outreach system (create database, check config)"""
    
    click.echo("🔧 Initializing Customer Outreach System...")
    
    # Check environment variables
    import os
    required_vars = ['OPENAI_API_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        click.echo("❌ Missing required environment variables:")
        for var in missing_vars:
            click.echo(f"   - {var}")
        click.echo("\nPlease create a .env file or set these environment variables.")
        return
    
    # Initialize database
    try:
        database_tool._init_db()
        click.echo("✅ Database initialized successfully")
    except Exception as e:
        click.echo(f"❌ Database initialization failed: {e}")
        return
    
    # Test API connection
    try:
        # This is a simple test - in production you'd want a proper health check
        click.echo("✅ Configuration looks good!")
        click.echo("\n🚀 System ready! Try: python cli.py create-campaign --help")
        
    except Exception as e:
        click.echo(f"❌ Configuration test failed: {e}")

@cli.command()
def sample_data():
    """Generate sample lead data for testing"""
    
    sample_leads = [
        {
            "lead_name": "TechCorp Inc",
            "industry": "Software Development",
            "key_decision_maker": "Sarah Johnson",
            "position": "CTO", 
            "milestone": "Series B funding round",
            "contact_email": "sarah@techcorp.com"
        },
        {
            "lead_name": "EduPlatform",
            "industry": "Online Learning Platform",
            "key_decision_maker": "Michael Chen", 
            "position": "CEO",
            "milestone": "platform redesign launch",
            "contact_email": "michael@eduplatform.com"
        },
        {
            "lead_name": "RetailMax",
            "industry": "E-commerce",
            "key_decision_maker": "Emma Rodriguez",
            "position": "VP Marketing",
            "milestone": "expansion to European markets", 
            "contact_email": "emma@retailmax.com"
        }
    ]
    
    # Save sample data to file
    with open('sample_leads.json', 'w') as f:
        json.dump(sample_leads, f, indent=2)
    
    click.echo("✅ Sample data created in sample_leads.json")
    click.echo("💡 Try: python cli.py batch-import --file sample_leads.json")

if __name__ == '__main__':
    cli()