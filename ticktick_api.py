# TickTick API
# establish connection to TickTick API
# write functions to interact with TickTick API
# return data in a structured format

from dida365 import Dida365Client, ServiceType, TaskCreate, ProjectCreate
from datetime import datetime, timezone
import os
import asyncio
import time
from dotenv import load_dotenv
import logging
from tenacity import retry, stop_after_attempt, wait_exponential
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class Note:
    def __init__(self, id: str, title: str, content: str, created_time: datetime, modified_time: datetime):
        self.id = id
        self.title = title
        self.content = content
        self.created_time = created_time
        self.modified_time = modified_time

class TickTickAPI:
    def __init__(self):
        load_dotenv()
        
        # Store our custom environment variables before loading dida365
        custom_env = {
            "DEEPSEEK_API_KEY": os.getenv("DEEPSEEK_API_KEY"),
            "MONGODB_URI": os.getenv("MONGODB_URI")
        }
        
        # Temporarily remove custom environment variables
        for key in custom_env:
            if key in os.environ:
                del os.environ[key]
        
        try:
            # Initialize client with only the required environment variables
            self.client = Dida365Client(
                client_id=os.getenv("DIDA365_CLIENT_ID"),
                client_secret=os.getenv("DIDA365_CLIENT_SECRET"),
                service_type=ServiceType.TICKTICK,
                redirect_uri=os.getenv("DIDA365_REDIRECT_URI", "http://localhost:8080/callback")
            )
            
            # Authenticate if needed
            if not self.client.auth.token:
                self.client.authenticate()
        finally:
            # Restore custom environment variables
            for key, value in custom_env.items():
                if value is not None:
                    os.environ[key] = value
        
        # Rate limiting settings
        self.rate_limit_delay = 2.0  # seconds between requests
        self.last_request_time = time.time()
        self.batch_size = 5  # Number of projects to process in one batch
    
    async def _rate_limit(self):
        """Implement rate limiting with exponential backoff"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - time_since_last)
        self.last_request_time = time.time()
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _make_api_request(self, func, *args, **kwargs):
        """Make API request with retry logic"""
        await self._rate_limit()
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            if "exceed_query_limit" in str(e):
                # If we hit rate limit, wait longer before retrying
                await asyncio.sleep(10)
            raise
    
    async def get_tasks(self, project_id: Optional[str] = None):
        """Get all tasks with batching to avoid rate limits
        
        Args:
            project_id: Optional project ID to filter tasks by
        """
        try:
            projects = await self.get_projects()
            all_tasks = []
            
            # Process projects in batches
            for i in range(0, len(projects), self.batch_size):
                batch = projects[i:i + self.batch_size]
                for project in batch:
                    # Skip if project_id is specified and doesn't match
                    if project_id is not None and project.id != project_id:
                        continue
                        
                    try:
                        await self._rate_limit()
                        project_data = await self._make_api_request(
                            self.client.get_project_with_data,
                            project_id=project.id
                        )
                        all_tasks.extend(project_data.tasks)
                        logger.info(f"Retrieved tasks for project {project.name}")
                    except Exception as e:
                        logger.error(f"Error getting tasks for project {project.name}: {str(e)}")
                        continue
                
                # Add extra delay between batches
                if i + self.batch_size < len(projects):
                    await asyncio.sleep(5)
            
            return all_tasks
        except Exception as e:
            logger.error(f"Error in get_tasks: {str(e)}")
            raise
    
    async def get_task(self, task_id):
        """Get a specific task by ID"""
        try:
            await self._rate_limit()
            return await self._make_api_request(self.client.get_task, task_id=task_id)
        except Exception as e:
            logger.error(f"Error getting task {task_id}: {str(e)}")
            raise
    
    async def get_projects(self):
        """Get all projects"""
        try:
            await self._rate_limit()
            return await self._make_api_request(self.client.get_projects)
        except Exception as e:
            logger.error(f"Error getting projects: {str(e)}")
            raise
    
    async def get_project(self, project_id):
        """Get a specific project by ID"""
        try:
            await self._rate_limit()
            return await self._make_api_request(self.client.get_project, project_id=project_id)
        except Exception as e:
            logger.error(f"Error getting project {project_id}: {str(e)}")
            raise
    
    async def get_notes(self) -> List[Note]:
        """Get all notes from TickTick
        
        Returns:
            List of Note objects
        """
        try:
            # Since the API client doesn't have direct note support,
            # we'll use the task API to get notes
            # Notes in TickTick are stored as tasks with a specific type
            tasks = await self.get_tasks()
            notes = []
            
            for task in tasks:
                if hasattr(task, 'type') and task.type == 'note':
                    note = Note(
                        id=task.id,
                        title=task.title,
                        content=task.content or '',
                        created_time=task.created_time,
                        modified_time=task.modified_time
                    )
                    notes.append(note)
            
            logger.info(f"Retrieved {len(notes)} notes from tasks")
            return notes
        except Exception as e:
            logger.error(f"Error getting notes: {str(e)}")
            raise
    
    async def get_note(self, note_id: str) -> Optional[Note]:
        """Get a specific note by ID
        
        Args:
            note_id: ID of the note to retrieve
        
        Returns:
            Note object if found, None otherwise
        """
        try:
            task = await self.get_task(note_id)
            if task and hasattr(task, 'type') and task.type == 'note':
                return Note(
                    id=task.id,
                    title=task.title,
                    content=task.content or '',
                    created_time=task.created_time,
                    modified_time=task.modified_time
                )
            return None
        except Exception as e:
            logger.error(f"Error getting note {note_id}: {str(e)}")
            raise
    
    async def create_task(self, project_id, title, content=None, priority=None, start_date=None, due_date=None):
        """Create a new task"""
        try:
            await self._rate_limit()
            task = TaskCreate(
                project_id=project_id,
                title=title,
                content=content,
                priority=priority,
                start_date=start_date or datetime.now(timezone.utc),
                due_date=due_date,
                is_all_day=False,
                time_zone="UTC"
            )
            return await self._make_api_request(self.client.create_task, task)
        except Exception as e:
            logger.error(f"Error creating task: {str(e)}")
            raise
    
    async def create_project(self, name, color=None):
        """Create a new project"""
        try:
            await self._rate_limit()
            project = ProjectCreate(
                name=name,
                color=color
            )
            return await self._make_api_request(self.client.create_project, project)
        except Exception as e:
            logger.error(f"Error creating project: {str(e)}")
            raise
