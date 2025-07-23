#!/usr/bin/env python3
"""
Real Email Agent with SMTP Support
==================================

Email agent that sends actual emails using SMTP (Gmail, Outlook, or custom SMTP).
Supports multiple SMTP providers including open-source options.
"""

import asyncio
import logging
import os
import sys
import json
import uuid
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

# Setup path
project_root = Path(__file__).parent
sys.path.append(str(project_root))
sys.path.append(str(project_root / "src"))

# Load environment
from dotenv import load_dotenv
load_dotenv()

# Core imports
from langchain_anthropic import ChatAnthropic
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import uvicorn
import aiohttp

logger = logging.getLogger(__name__)

class RealEmailAgent:
    """Real email agent that sends actual emails via SMTP"""
    
    def __init__(self, llm, hub_url: str, agent_port: int = 8003):
        self.llm = llm
        self.hub_url = hub_url
        self.agent_port = agent_port
        self.app = FastAPI()
        self.agent_id = f"real_email_agent_{agent_port}"
        
        # Email configuration - check multiple providers
        self.smtp_config = self._configure_smtp()
        
        # Default recipient configuration
        self.default_recipient = os.getenv("EMAIL_TO") or os.getenv("EMAIL_USER") or "rajpraba_1986@yahoo.com.sg"
        
        self.setup_routes()
        
        print(f"✅ Real Email Agent initialized")
        print(f"   Agent ID: {self.agent_id}")
        print(f"   Default recipient: {self.default_recipient}")
        print(f"   SMTP Server: {self.smtp_config['smtp_server']}")
        print(f"   SMTP Configured: {'✅ Yes' if self.smtp_config['configured'] else '❌ No (will simulate)'}")
    
    def _configure_smtp(self) -> Dict[str, Any]:
        """Configure SMTP settings from environment variables"""
        
        # Check for Gmail configuration
        gmail_user = os.getenv("GMAIL_USER")
        gmail_password = os.getenv("GMAIL_APP_PASSWORD")  # Gmail App Password
        
        # Check for Outlook configuration  
        outlook_user = os.getenv("OUTLOOK_USER")
        outlook_password = os.getenv("OUTLOOK_PASSWORD")
        
        # Check for custom SMTP configuration (both formats supported)
        custom_smtp_server = os.getenv("SMTP_SERVER") or os.getenv("EMAIL_SMTP_SERVER")
        custom_smtp_user = os.getenv("SMTP_USER") or os.getenv("EMAIL_USER")
        custom_smtp_password = os.getenv("SMTP_PASSWORD") or os.getenv("EMAIL_PASSWORD")
        custom_smtp_port = os.getenv("SMTP_PORT") or os.getenv("EMAIL_SMTP_PORT")
        
        # Priority: Custom SMTP > Gmail > Outlook > Simulation
        if custom_smtp_server and custom_smtp_user and custom_smtp_password:
            return {
                "provider": "custom",
                "smtp_server": custom_smtp_server,
                "smtp_port": int(custom_smtp_port or 587),
                "email_user": custom_smtp_user,
                "email_password": custom_smtp_password,
                "use_tls": os.getenv("SMTP_USE_TLS", "true").lower() == "true",
                "configured": True
            }
        elif gmail_user and gmail_password:
            return {
                "provider": "gmail",
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "email_user": gmail_user,
                "email_password": gmail_password,
                "use_tls": True,
                "configured": True
            }
        elif outlook_user and outlook_password:
            return {
                "provider": "outlook",
                "smtp_server": "smtp-mail.outlook.com",
                "smtp_port": 587,
                "email_user": outlook_user,
                "email_password": outlook_password,
                "use_tls": True,
                "configured": True
            }
        else:
            # Fallback to simulation
            return {
                "provider": "simulation",
                "smtp_server": "localhost",
                "smtp_port": 25,
                "email_user": "noreply@localhost",
                "email_password": "",
                "use_tls": False,
                "configured": False
            }
    
    def setup_routes(self):
        """Setup FastAPI routes for MCP protocol"""
        
        @self.app.post("/mcp/request")
        async def handle_mcp_request(request: Request):
            """Handle MCP requests"""
            try:
                data = await request.json()
                return await self.process_mcp_request(data)
            except Exception as e:
                return {"jsonrpc": "2.0", "error": {"code": -1, "message": str(e)}}
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy", 
                "agent_id": self.agent_id, 
                "service": "email",
                "smtp_configured": self.smtp_config['configured'],
                "smtp_provider": self.smtp_config['provider']
            }
        
        @self.app.post("/send-email")
        async def send_email_endpoint(request: Request):
            """Direct email sending endpoint"""
            try:
                data = await request.json()
                result = await self.send_extraction_notification(
                    extracted_data=data.get("extracted_data", []),
                    extraction_metadata=data.get("extraction_metadata", {}),
                    recipient=data.get("recipient", self.default_recipient)
                )
                return {"status": "success", "result": result}
            except Exception as e:
                return {"status": "error", "error": str(e)}
        
        @self.app.get("/smtp-test")
        async def smtp_test():
            """Test SMTP connection"""
            result = await self.test_smtp_connection()
            return {"smtp_test": result}
    
    async def process_mcp_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process MCP requests"""
        try:
            method = request_data.get("method")
            params = request_data.get("params", {})
            request_id = request_data.get("id")
            
            print(f"🔍 REAL EMAIL DEBUG: Received method: {method}")
            print(f"🔍 REAL EMAIL DEBUG: Params keys: {list(params.keys())}")
            
            if method == "send_extraction_notification":
                print(f"🔍 REAL EMAIL DEBUG: Processing send_extraction_notification")
                print(f"🔍 REAL EMAIL DEBUG: Has extraction_data: {'extraction_data' in params}")
                print(f"🔍 REAL EMAIL DEBUG: Data count: {params.get('data_count', 0)}")
                
                # Handle both the old format and new format from working web extraction agent
                if "extraction_data" in params:
                    # New format from working web extraction agent
                    result = await self.send_extraction_notification(
                        extracted_data=params.get("extraction_data", []),
                        extraction_metadata={
                            "source": params.get("extraction_source", "Unknown"),
                            "data_count": params.get("data_count", 0),
                            "method": params.get("extraction_method", "unknown"),
                            "source_url": params.get("extraction_data", [{}])[0].get("url", "N/A") if params.get("extraction_data") else "N/A"
                        },
                        recipient=params.get("recipient", self.default_recipient)
                    )
                else:
                    # Old format
                    result = await self.send_extraction_notification(
                        extracted_data=params.get("extracted_data", []),
                        extraction_metadata=params.get("extraction_metadata", {}),
                        recipient=params.get("recipient", self.default_recipient)
                    )
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": result
                }
            elif method == "send_notification":
                result = await self.send_notification(
                    recipient=params.get("recipient", self.default_recipient),
                    subject=params.get("subject", "Notification"),
                    body=params.get("body", ""),
                    priority=params.get("priority", "normal")
                )
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": result
                }
            elif method == "test_smtp":
                result = await self.test_smtp_connection()
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": result
                }
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"}
                }
                
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request_data.get("id"),
                "error": {"code": -1, "message": str(e)}
            }
    
    async def test_smtp_connection(self) -> Dict[str, Any]:
        """Test SMTP connection with timeout"""
        if not self.smtp_config['configured']:
            return {
                "status": "not_configured",
                "message": "SMTP not configured, using simulation mode"
            }
        
        try:
            # Test SMTP connection with timeout
            result = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(None, self._test_smtp_sync),
                timeout=10  # 10 second timeout
            )
            return result
        except asyncio.TimeoutError:
            return {
                "status": "timeout",
                "message": f"SMTP connection test timed out after 10 seconds"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"SMTP test failed: {str(e)}"
            }
    
    def _test_smtp_sync(self) -> Dict[str, Any]:
        """Synchronous SMTP connection test with timeout"""
        try:
            print(f"🔧 Testing SMTP connection to {self.smtp_config['smtp_server']}...")
            
            if self.smtp_config['use_tls']:
                server = smtplib.SMTP(self.smtp_config['smtp_server'], self.smtp_config['smtp_port'], timeout=5)
                server.starttls()
            else:
                server = smtplib.SMTP(self.smtp_config['smtp_server'], self.smtp_config['smtp_port'], timeout=5)
            
            server.login(self.smtp_config['email_user'], self.smtp_config['email_password'])
            server.quit()
            
            print("✅ SMTP connection test successful!")
            return {
                "status": "success",
                "message": f"Successfully connected to {self.smtp_config['provider']} SMTP",
                "server": self.smtp_config['smtp_server'],
                "provider": self.smtp_config['provider']
            }
            
        except Exception as e:
            print(f"❌ SMTP connection test failed: {e}")
            return {
                "status": "failed",
                "message": str(e),
                "server": self.smtp_config['smtp_server'],
                "provider": self.smtp_config['provider']
            }
    
    async def send_extraction_notification(self, extracted_data: List[Dict], 
                                         extraction_metadata: Dict, 
                                         recipient: Optional[str] = None) -> Dict[str, Any]:
        """Send email notification with extracted data"""
        try:
            recipient_email = recipient or self.default_recipient
            
            print(f"📧 Preparing extraction notification email...")
            print(f"   Recipient: {recipient_email}")
            print(f"   Data points: {len(extracted_data)}")
            
            # Generate email content using Claude
            subject = await self.generate_email_subject(extraction_metadata, len(extracted_data))
            html_body = await self.generate_email_body(extracted_data, extraction_metadata)
            
            # Send email
            result = await self.send_email_smtp(
                recipient=recipient_email,
                subject=subject,
                extracted_data=extracted_data,
                metadata=extraction_metadata
            )
            
            return {
                "status": "success" if result.get("sent") else "failed",
                "notification_id": str(uuid.uuid4()),
                "recipient": recipient_email,
                "subject": subject,
                "data_points": len(extracted_data),
                "sent_at": datetime.now().isoformat(),
                "email_sent": result.get("sent", False),
                "smtp_provider": self.smtp_config['provider'],
                "method": result.get("method", "unknown"),
                "error": result.get("error") if not result.get("sent") else None
            }
            
        except Exception as e:
            print(f"❌ Failed to send extraction notification: {e}")
            return {
                "status": "error",
                "error": str(e),
                "recipient": recipient_email if 'recipient_email' in locals() else "unknown"
            }
    
    async def generate_email_subject(self, metadata: Dict, data_count: int) -> str:
        """Generate email subject using Claude"""
        try:
            prompt = f"""
            Generate a professional email subject line for a data extraction report.
            
            Extraction metadata: {json.dumps(metadata, indent=2)}
            Number of data points: {data_count}
            
            Make it concise and informative. Include the source/target and data count.
            Example: "Yahoo Finance Data Extraction Complete - 15 Stock Records"
            
            Return only the subject line, no quotes or extra text.
            """
            
            response = await self.llm.ainvoke(prompt)
            subject = response.content.strip().strip('"').strip("'")
            return subject[:100]  # Limit subject length
            
        except Exception as e:
            print(f"⚠️  Failed to generate subject, using default: {e}")
            return f"Data Extraction Report - {data_count} Records"
    
    async def generate_email_body(self, extracted_data: List[Dict], metadata: Dict) -> str:
        """Generate HTML email body using Claude"""
        try:
            prompt = f"""
            Generate a clean, professional HTML email body for a data extraction report.
            
            Extraction metadata: {json.dumps(metadata, indent=2)}
            Sample extracted data (first 3 items): {json.dumps(extracted_data[:3], indent=2)}
            Total data points: {len(extracted_data)}
            
            Create an HTML email that includes:
            1. Professional greeting
            2. Brief summary of the extraction (source, timestamp, data count)
            3. Clean HTML table showing the first 5 data items with proper formatting
            4. Summary statistics if applicable (stock prices, changes, etc.)
            5. Professional closing
            
            Use clean, professional HTML styling with inline CSS.
            Keep it concise and business-appropriate.
            Make the table responsive and well-formatted.
            
            Return only the HTML body content, no extra text or markdown.
            """
            
            response = await self.llm.ainvoke(prompt)
            return response.content
            
        except Exception as e:
            print(f"⚠️  Failed to generate email body: {e}")
            return self.generate_fallback_email_body(extracted_data, metadata)
    
    def generate_fallback_email_body(self, extracted_data: List[Dict], metadata: Dict) -> str:
        """Generate enhanced HTML email body with detailed extracted information"""
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5;">
            <div style="max-width: 800px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <h2 style="color: #2c3e50; margin-bottom: 20px; border-bottom: 2px solid #3498db; padding-bottom: 10px;">📊 Data Extraction Report</h2>
                
                <div style="background-color: #ecf0f1; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="color: #34495e; margin-top: 0; margin-bottom: 15px;">📋 Extraction Summary</h3>
                    <ul style="margin: 0; padding-left: 20px;">
                        <li><strong>Source:</strong> {metadata.get('source', 'Hub-mediated A2A Communication')}</li>
                        <li><strong>Data Count:</strong> {len(extracted_data)}</li>
                        <li><strong>Method:</strong> {metadata.get('method', 'browserbase_hub')}</li>
                        <li><strong>Source URL:</strong> {metadata.get('source_url', 'Multiple Sources')}</li>
                        <li><strong>Extracted:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</li>
                    </ul>
                </div>
                
                <h3 style="color: #34495e; margin-bottom: 15px;">🌐 Extracted Data</h3>
        """
        
        # Process each extracted item with detailed information
        for i, item in enumerate(extracted_data):
            url = item.get('url', 'N/A')
            name = item.get('name', f'Item {i+1}')
            title = item.get('title', 'No Title')
            content = item.get('content', 'No content available')
            extracted_data_detail = item.get('extracted_data', {})
            
            # Determine background color alternating
            bg_color = "#f8f9fa" if i % 2 == 0 else "white"
            
            html_body += f"""
                <div style="background-color: {bg_color}; border: 1px solid #ddd; border-radius: 8px; margin: 15px 0; padding: 20px;">
                    <h4 style="color: #2c3e50; margin: 0 0 10px 0; border-bottom: 1px solid #bdc3c7; padding-bottom: 5px;">
                        🔗 {name}
                    </h4>
                    <table style="width: 100%; border-collapse: collapse; margin: 10px 0;">
                        <tr>
                            <td style="padding: 8px; font-weight: bold; color: #34495e; width: 80px; vertical-align: top;">URL:</td>
                            <td style="padding: 8px; color: #2c3e50;"><a href="{url}" style="color: #3498db; text-decoration: none;">{url}</a></td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; font-weight: bold; color: #34495e; width: 80px; vertical-align: top;">Title:</td>
                            <td style="padding: 8px; color: #2c3e50; font-weight: 600;">{title}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px; font-weight: bold; color: #34495e; width: 80px; vertical-align: top;">Content:</td>
                            <td style="padding: 8px; color: #2c3e50;">{content}</td>
                        </tr>
            """
            
            # Add detailed extracted data based on type
            if extracted_data_detail:
                html_body += """
                        <tr>
                            <td style="padding: 8px; font-weight: bold; color: #34495e; width: 80px; vertical-align: top;">Details:</td>
                            <td style="padding: 8px; color: #2c3e50;">
                """
                
                # Format different types of extracted data
                if 'repositories' in extracted_data_detail:
                    # GitHub repositories
                    repos = extracted_data_detail.get('repositories', [])
                    languages = extracted_data_detail.get('languages', [])
                    stats = extracted_data_detail.get('stats', {})
                    
                    html_body += """
                                <div style="background: #e8f6fd; padding: 10px; border-radius: 4px; margin: 5px 0;">
                                    <strong>📚 GitHub Profile Details:</strong><br>
                    """
                    if repos:
                        html_body += f"• <strong>Repositories:</strong> {', '.join(repos[:5])}"
                        if len(repos) > 5:
                            html_body += f" (and {len(repos) - 5} more)"
                        html_body += "<br>"
                    
                    if languages:
                        html_body += f"• <strong>Languages:</strong> {', '.join(languages)}<br>"
                    
                    if stats:
                        html_body += f"• <strong>Public Repos:</strong> {stats.get('public_repos', 'N/A')}<br>"
                        html_body += f"• <strong>Followers:</strong> {stats.get('followers', 'N/A')}<br>"
                        html_body += f"• <strong>Following:</strong> {stats.get('following', 'N/A')}<br>"
                    
                    html_body += "</div>"
                
                elif 'stock_data' in extracted_data_detail:
                    # Stock/Financial data
                    stock_data = extracted_data_detail.get('stock_data', {})
                    key_stats = extracted_data_detail.get('key_stats', {})
                    
                    html_body += """
                                <div style="background: #e8f8f5; padding: 10px; border-radius: 4px; margin: 5px 0;">
                                    <strong>📈 Financial Data:</strong><br>
                    """
                    if stock_data:
                        html_body += f"• <strong>Symbol:</strong> {stock_data.get('symbol', 'N/A')}<br>"
                        html_body += f"• <strong>Price:</strong> {stock_data.get('price', 'N/A')}<br>"
                        html_body += f"• <strong>Change:</strong> {stock_data.get('change', 'N/A')} ({stock_data.get('change_percent', 'N/A')})<br>"
                        html_body += f"• <strong>Volume:</strong> {stock_data.get('volume', 'N/A')}<br>"
                        html_body += f"• <strong>Market Cap:</strong> {stock_data.get('market_cap', 'N/A')}<br>"
                    
                    if key_stats:
                        html_body += f"• <strong>P/E Ratio:</strong> {key_stats.get('pe_ratio', 'N/A')}<br>"
                        html_body += f"• <strong>Dividend Yield:</strong> {key_stats.get('dividend_yield', 'N/A')}<br>"
                        html_body += f"• <strong>52W High:</strong> {key_stats.get('52_week_high', 'N/A')}<br>"
                        html_body += f"• <strong>52W Low:</strong> {key_stats.get('52_week_low', 'N/A')}<br>"
                    
                    html_body += "</div>"
                
                elif 'top_stories' in extracted_data_detail:
                    # News/Hacker News stories
                    stories = extracted_data_detail.get('top_stories', [])
                    
                    html_body += """
                                <div style="background: #fff4e6; padding: 10px; border-radius: 4px; margin: 5px 0;">
                                    <strong>📰 Top Stories:</strong><br>
                    """
                    for j, story in enumerate(stories[:3]):
                        html_body += f"• <strong>{story.get('title', 'No title')}</strong><br>"
                        html_body += f"  Points: {story.get('points', 'N/A')} | Comments: {story.get('comments', 'N/A')}<br>"
                    
                    if len(stories) > 3:
                        html_body += f"... and {len(stories) - 3} more stories<br>"
                    
                    html_body += "</div>"
                
                else:
                    # Generic structured data
                    html_body += """
                                <div style="background: #f0f0f0; padding: 10px; border-radius: 4px; margin: 5px 0;">
                                    <strong>📋 Structured Data:</strong><br>
                    """
                    for key, value in list(extracted_data_detail.items())[:5]:
                        if isinstance(value, (list, dict)):
                            html_body += f"• <strong>{key.title()}:</strong> {str(value)[:100]}{'...' if len(str(value)) > 100 else ''}<br>"
                        else:
                            html_body += f"• <strong>{key.title()}:</strong> {value}<br>"
                    html_body += "</div>"
                
                html_body += """
                            </td>
                        </tr>
                """
            
            html_body += """
                    </table>
                </div>
            """
        
        html_body += f"""
                <div style="margin: 30px 0; padding: 20px; background-color: #e8f6fd; border-left: 4px solid #3498db; border-radius: 0 5px 5px 0;">
                    <p style="margin: 0; color: #2c3e50;">
                        <strong>🎯 Report Summary:</strong><br>
                        This automated extraction captured {len(extracted_data)} data records from multiple sources using hub-mediated A2A communication.
                        The data includes detailed information from websites, financial data, GitHub repositories, and news sources.
                    </p>
                </div>
                
                <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #bdc3c7; text-align: center; color: #7f8c8d; font-size: 12px;">
                    <p style="margin: 5px 0;">🤖 Generated by MCP Multi-Agent System with Hub Architecture</p>
                    <p style="margin: 5px 0;">📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html_body
    
    async def send_email_smtp(self, recipient: str, subject: str, extracted_data: List[Dict], 
                             metadata: Dict) -> Dict[str, Any]:
        """Send email via SMTP with extraction data"""
        try:
            print(f"📤 Sending email to {recipient}")
            print(f"   Subject: {subject}")
            print(f"   SMTP Provider: {self.smtp_config['provider']}")
            
            # Generate HTML body from the data
            if isinstance(extracted_data, list) and len(extracted_data) > 0:
                html_body = await self.generate_email_body(extracted_data, metadata)
            else:
                html_body = self.generate_fallback_email_body(extracted_data or [], metadata)
            
            if self.smtp_config['configured']:
                # Send real email via SMTP
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, self._send_email_smtp_sync, recipient, subject, html_body)
                return result
            else:
                # Fallback to simulation
                return await self._send_email_simulation(recipient, subject, html_body)
                
        except Exception as e:
            print(f"❌ Email sending failed: {e}")
            return {
                "sent": False,
                "error": str(e),
                "recipient": recipient,
                "method": "failed"
            }
    
    def _send_email_smtp_sync(self, recipient: str, subject: str, html_body: str) -> Dict[str, Any]:
        """Send email synchronously via SMTP"""
        try:
            print(f"🔗 Connecting to SMTP server: {self.smtp_config['smtp_server']}:{self.smtp_config['smtp_port']}")
            
            # Create message
            message = MIMEMultipart("alternative")
            message["From"] = self.smtp_config['email_user']
            message["To"] = recipient
            message["Subject"] = subject
            
            # Add HTML body
            html_part = MIMEText(html_body, "html")
            message.attach(html_part)
            
            # Connect and send
            if self.smtp_config['use_tls']:
                server = smtplib.SMTP(self.smtp_config['smtp_server'], self.smtp_config['smtp_port'])
                server.starttls()
            else:
                server = smtplib.SMTP(self.smtp_config['smtp_server'], self.smtp_config['smtp_port'])
            
            # Login and send
            server.login(self.smtp_config['email_user'], self.smtp_config['email_password'])
            text = message.as_string()
            server.sendmail(self.smtp_config['email_user'], recipient, text)
            server.quit()
            
            print(f"✅ Email sent successfully via {self.smtp_config['provider']} SMTP!")
            
            return {
                "sent": True,
                "recipient": recipient,
                "subject": subject,
                "method": f"{self.smtp_config['provider']}_smtp",
                "smtp_server": self.smtp_config['smtp_server'],
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ SMTP sending failed: {e}")
            return {
                "sent": False,
                "error": str(e),
                "recipient": recipient,
                "method": "smtp_failed"
            }
    
    async def _send_email_simulation(self, recipient: str, subject: str, html_body: str) -> Dict[str, Any]:
        """Fallback email simulation"""
        print("⚠️  SMTP not configured, using simulation mode")
        
        # Simulate email sending delay
        await asyncio.sleep(1)
        
        # Save email to file for demonstration
        email_log_path = project_root / "data" / "sent_emails.log"
        email_log_path.parent.mkdir(exist_ok=True)
        
        with open(email_log_path, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*80}\n")
            f.write(f"SIMULATED EMAIL\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"To: {recipient}\n")
            f.write(f"Subject: {subject}\n")
            f.write(f"Body:\n{html_body}\n")
            f.write(f"{'='*80}\n")
        
        print(f"📝 Email simulated and logged to: {email_log_path}")
        
        return {
            "sent": False,
            "recipient": recipient,
            "subject": subject,
            "method": "simulated",
            "log_file": str(email_log_path),
            "timestamp": datetime.now().isoformat(),
            "note": "SMTP not configured - email was simulated"
        }
    
    async def send_simple_email(self, recipient: str, subject: str, html_body: str) -> Dict[str, Any]:
        """Send simple email with pre-formatted HTML body"""
        try:
            if self.smtp_config['configured']:
                # Send real email via SMTP
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, self._send_email_smtp_sync, recipient, subject, html_body)
                return result
            else:
                # Fallback to simulation
                return await self._send_email_simulation(recipient, subject, html_body)
                
        except Exception as e:
            return {
                "sent": False,
                "error": str(e),
                "recipient": recipient,
                "method": "failed"
            }

    async def send_notification(self, recipient: str, subject: str, 
                               body: str, priority: str = "normal") -> Dict[str, Any]:
        """Send simple notification email"""
        try:
            simple_html = f"""
            <html>
            <body style="font-family: Arial, sans-serif; margin: 20px; background-color: #f9f9f9; padding: 30px;">
                <div style="max-width: 500px; margin: 0 auto; background-color: white; padding: 25px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <h2 style="color: #2c3e50; margin-bottom: 20px; border-bottom: 2px solid #3498db; padding-bottom: 10px;">🔔 Notification</h2>
                    <div style="background-color: #ecf0f1; padding: 20px; border-radius: 5px; border-left: 4px solid #3498db;">
                        <p style="margin: 0; color: #2c3e50; font-size: 16px; line-height: 1.5;">{body}</p>
                    </div>
                    <div style="margin-top: 20px; padding-top: 15px; border-top: 1px solid #bdc3c7; font-size: 12px; color: #7f8c8d; text-align: center;">
                        <p style="margin: 0;">Priority: {priority.upper()} | Sent: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            result = await self.send_simple_email(recipient, subject, simple_html)
            
            return {
                "notification_id": str(uuid.uuid4()),
                "status": "sent" if result.get("sent") else "failed",
                "recipient": recipient,
                "subject": subject,
                "priority": priority,
                "sent_at": datetime.now().isoformat(),
                "method": result.get("method"),
                "smtp_provider": self.smtp_config['provider']
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def register_with_hub(self):
        """Register this agent with the MCP hub"""
        try:
            registration_request = {
                "jsonrpc": "2.0",
                "id": f"registration-{self.agent_id}",
                "method": "agents/register",
                "params": {
                    "agent_id": self.agent_id,
                    "agent_name": "Real Email Agent with SMTP",
                    "agent_type": "communication",
                    "host": "localhost",
                    "port": self.agent_port,
                    "endpoint_url": f"http://localhost:{self.agent_port}/mcp/request",
                    "capabilities": [
                        {
                            "name": "send_extraction_notification",
                            "description": "Send real email notification with extracted data via SMTP",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "extracted_data": {"type": "array", "description": "Extracted data to include"},
                                    "extraction_metadata": {"type": "object", "description": "Extraction metadata"},
                                    "recipient": {"type": "string", "description": "Email recipient"}
                                },
                                "required": ["extracted_data", "extraction_metadata"]
                            }
                        },
                        {
                            "name": "send_notification",
                            "description": "Send simple notification email via SMTP",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "recipient": {"type": "string", "description": "Email recipient"},
                                    "subject": {"type": "string", "description": "Email subject"},
                                    "body": {"type": "string", "description": "Email body"},
                                    "priority": {"type": "string", "description": "Email priority"}
                                },
                                "required": ["recipient", "subject", "body"]
                            }
                        },
                        {
                            "name": "test_smtp",
                            "description": "Test SMTP connection and configuration",
                            "parameters": {"type": "object", "properties": {}}
                        }
                    ],
                    "status": "active",
                    "metadata": {
                        "smtp_provider": self.smtp_config['provider'],
                        "smtp_configured": self.smtp_config['configured']
                    }
                }
            }
            
            async with aiohttp.ClientSession() as session:
                hub_mcp_url = "http://localhost:5000/mcp"
                async with session.post(hub_mcp_url, json=registration_request, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        result = await response.json()
                        if "result" in result:
                            print(f"✅ Successfully registered Real Email Agent: {result['result']}")
                            return True
                    
            return False
            
        except Exception as e:
            print(f"⚠️  Registration failed: {e}")
            return False
    
    async def start_agent_server(self):
        """Start the agent server"""
        print(f"🚀 Starting Real Email Agent on port {self.agent_port}")
        
        # Test SMTP connection on startup (non-blocking)
        if self.smtp_config['configured']:
            try:
                smtp_test_result = await self.test_smtp_connection()
                if smtp_test_result['status'] == 'success':
                    print(f"✅ SMTP connection verified - real emails will be sent!")
                elif smtp_test_result['status'] == 'timeout':
                    print(f"⚠️  SMTP connection timed out - will use simulation mode")
                    print(f"   Message: {smtp_test_result.get('message')}")
                else:
                    print(f"⚠️  SMTP connection failed - will use simulation mode")
                    print(f"   Error: {smtp_test_result.get('message')}")
            except Exception as e:
                print(f"⚠️  SMTP test error - will use simulation mode: {e}")
        else:
            print("ℹ️  SMTP not configured - using simulation mode")
            print("   To send real emails, configure SMTP settings in .env file")
        
        # Register with hub (continue even if SMTP failed)
        try:
            await self.register_with_hub()
        except Exception as e:
            print(f"⚠️  Hub registration failed: {e}")
        
        # Start server
        config = uvicorn.Config(
            self.app,
            host="localhost",
            port=self.agent_port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()

async def main():
    """Main function to start the real email agent"""
    print("📨 Real Email Agent with SMTP Support Starting...")
    print("=" * 60)
    
    # Check environment
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not found")
        return
    
    print(f"✅ ANTHROPIC_API_KEY loaded ({len(api_key)} chars)")
    
    # Create LLM
    try:
        llm = ChatAnthropic(
            model=os.getenv('LLM_MODEL', 'claude-3-haiku-20240307'),
            temperature=0.1,
            api_key=api_key
        )
        print("✅ Anthropic LLM configured")
    except Exception as e:
        print(f"❌ Failed to create LLM: {e}")
        return
    
    # Create and start agent
    hub_url = "http://localhost:5000/mcp"
    agent_port = 8003
    
    agent = RealEmailAgent(llm, hub_url, agent_port)
    
    print("\n" + "=" * 60)
    print("📧 SMTP CONFIGURATION GUIDE")
    print("=" * 60)
    print("To send real emails, add to your .env file:")
    print("")
    print("# Gmail (recommended)")
    print("GMAIL_USER=your-email@gmail.com")
    print("GMAIL_APP_PASSWORD=your-16-char-app-password")
    print("")
    print("# Or Outlook")  
    print("OUTLOOK_USER=your-email@outlook.com")
    print("OUTLOOK_PASSWORD=your-password")
    print("")
    print("# Or custom SMTP")
    print("SMTP_SERVER=smtp.yourdomain.com")
    print("SMTP_USER=your-email@yourdomain.com") 
    print("SMTP_PASSWORD=your-password")
    print("SMTP_PORT=587")
    print("=" * 60)
    
    print("🚀 Real Email Agent configured, starting server...")
    print("   Press Ctrl+C to stop")
    print("=" * 60)
    
    try:
        await agent.start_agent_server()
    except KeyboardInterrupt:
        print("\n⏹️  Real Email Agent stopped by user")
    except Exception as e:
        print(f"❌ Real Email Agent failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
