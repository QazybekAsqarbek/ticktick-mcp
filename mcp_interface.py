import logging
from typing import List, Dict, Any, Optional
from db import TickTickDB
from datetime import datetime
import json
import os
import argparse
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.markdown import Markdown
import openai
from dotenv import load_dotenv
import asyncio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MCPInterface:
    def __init__(self):
        load_dotenv()
        self.db = TickTickDB()
        self.console = Console()
        
        # Get debug projects from environment - using the correct variable name
        debug_projects = os.getenv("DEBUG_PROJECTS", "").split(",")
        self.debug_projects = [p.strip() for p in debug_projects if p.strip()]
        if self.debug_projects:
            self.console.print(f"[yellow]Debug mode enabled. Working with projects: {', '.join(self.debug_projects)}[/yellow]")
    
    def _load_system_prompt(self) -> str:
        """Load the system prompt from file"""
        if not self.prompt_file.exists():
            self.console.print(f"[yellow]Warning: Prompt file not found at {self.prompt_file}[/yellow]")
            return self._get_default_prompt()
        
        try:
            with open(self.prompt_file, 'r') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error loading prompt file: {str(e)}")
            return self._get_default_prompt()
    
    def _get_default_prompt(self) -> str:
        """Get default system prompt"""
        return """You are an ADHD-friendly task management assistant. Your role is to help manage tasks, 
        break them down into manageable pieces, and provide support for maintaining focus and productivity. 
        You understand the challenges of ADHD and can provide strategies for task management that work 
        with neurodivergent thinking patterns."""
    
    def get_context(self) -> Dict[str, Any]:
        """Get current context from database"""
        try:
            # Using direct MongoDB queries
            tasks = self.db.get_tasks()
            projects = self.db.get_projects()
            notes = self.db.get_notes()
            
            return {
                "tasks": tasks,
                "projects": projects,
                "notes": notes,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting context: {str(e)}")
            return {}
    
    def chat_with_agent(self, user_input: str) -> str:
        """Chat with the AI agent about tasks"""
        try:
            # Get current context
            context = self.get_context()
            
            # Prepare messages for the AI
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"Current context: {json.dumps(context)}\n\nUser: {user_input}"}
            ]
            
            # Get response from OpenAI
            response = openai.ChatCompletion.create(
                model="gpt-4",  # or your preferred model
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error in chat_with_agent: {str(e)}")
            return f"Error: {str(e)}"
    
    async def get_project_tasks(self, project_name: Optional[str] = None) -> None:
        """Get and display tasks from specified project or debug projects
        
        Args:
            project_name: Optional specific project name to display
        """
        try:
            # Get all projects
            projects = await self.db.get_projects()
            
            if project_name:
                # Find specific project (exact match)
                target_project = next((p for p in projects if p.get("name") == project_name), None)
                if not target_project:
                    self.console.print(f"[red]Project '{project_name}' not found[/red]")
                    return
                projects = [target_project]
            elif self.debug_projects:
                # Filter projects based on DEBUG_PROJECTS (exact match)
                projects = [p for p in projects if p.get("name") in self.debug_projects]
                if not projects:
                    self.console.print(f"[red]No debug projects found. Looking for: {', '.join(self.debug_projects)}[/red]")
                    return
            
            for project in projects:
                # Get tasks for project
                tasks = await self.db.get_tasks(project_id=project["id"])
                
                if not tasks:
                    self.console.print(f"[yellow]No tasks found in project '{project.get('name')}'[/yellow]")
                    continue
                
                # Display tasks
                self.console.print(f"\n[bold]Tasks in {project.get('name')}:[/bold]")
                for task in tasks:
                    status = task.get("status", "Unknown")
                    status_color = "green" if status == "completed" else "yellow"
                    
                    self.console.print(Panel(
                        f"[bold]{task.get('title', 'Untitled')}[/bold]\n"
                        f"Status: [{status_color}]{status}[/{status_color}]\n"
                        f"ID: {task.get('id')}\n"
                        f"Last Updated: {task.get('last_updated', 'Unknown')}\n"
                        f"Cache Expires: {task.get('cache_expiry', 'No cache')}",
                        title=f"Task {task.get('id')}",
                        border_style="blue"
                    ))
            
        except Exception as e:
            self.console.print(f"[red]Error getting project tasks: {str(e)}[/red]")
    
    def run_cli(self):
        """Run the CLI interface"""
        while True:
            self.console.print("\n[bold]TickTick MCP Interface[/bold]")
            if self.debug_projects:
                self.console.print("1. View debug projects tasks")
            else:
                self.console.print("1. View all projects tasks")
            self.console.print("2. View specific project tasks")
            self.console.print("3. Exit")
            
            choice = Prompt.ask("Select an option", choices=["1", "2", "3"])
            
            if choice == "1":
                self.get_project_tasks()
            elif choice == "2":
                project_name = Prompt.ask("Enter project name")
                self.get_project_tasks(project_name)
            elif choice == "3":
                break
    
    def _show_help(self):
        """Show help information"""
        help_text = """
        Available commands:
        - help: Show this help message
        - exit/quit: Exit the program
        
        You can ask about:
        - Task organization and prioritization
        - Breaking down complex tasks
        - Managing deadlines and time
        - Dealing with task overwhelm
        - Finding focus strategies
        - Any other task-related questions
        """
        self.console.print(Markdown(help_text))

async def main():
    parser = argparse.ArgumentParser(description='TickTick MCP Interface')
    parser.add_argument('--project', type=str, help='Show tasks for specific project')
    parser.add_argument('--debug', action='store_true', help='Show tasks for debug projects')
    args = parser.parse_args()

    mcp = None
    try:
        mcp = MCPInterface()
        
        if args.project:
            await mcp.get_project_tasks(args.project)
        elif args.debug:
            await mcp.get_project_tasks()
        else:
            # If no arguments, run interactive mode
            await mcp.run_cli()
            
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
    finally:
        if mcp:
            mcp.db.close()

if __name__ == "__main__":
    asyncio.run(main()) 