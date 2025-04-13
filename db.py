# save ticktick data to database to avoid rate limiting(use caching)
# use mongodb to store data
# as ticktick data structure is not fully known, use a flexible schema

from pymongo import MongoClient
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Any, Optional
import os
from dotenv import load_dotenv
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

class TickTickDB:
    def __init__(self, mongo_uri: str = None):
        """Initialize MongoDB connection
        
        Args:
            mongo_uri: MongoDB connection URI, defaults to environment variable
        """
        load_dotenv()
        mongo_uri = mongo_uri or os.getenv("MONGODB_URI", "mongodb://admin:password@mongodb:27017/")
        
        self.client = MongoClient(mongo_uri)
        self.db = self.client["ticktick"]
        self.logger = logging.getLogger(__name__)
        
        # Create indexes for better query performance
        self._create_indexes()
    
    def _create_indexes(self):
        """Create necessary indexes for collections"""
        try:
            # Index for tasks
            self.db.tasks.create_index([("id", 1)], unique=True)
            self.db.tasks.create_index([("projectId", 1)])
            self.db.tasks.create_index([("last_updated", 1)])
            self.db.tasks.create_index([("cache_expiry", 1)])
            
            # Index for projects
            self.db.projects.create_index([("id", 1)], unique=True)
            self.db.projects.create_index([("last_updated", 1)])
            self.db.projects.create_index([("cache_expiry", 1)])
            
            # Index for notes
            self.db.notes.create_index([("id", 1)], unique=True)
            self.db.notes.create_index([("last_updated", 1)])
            self.db.notes.create_index([("cache_expiry", 1)])
            
            self.logger.info("Successfully created indexes")
        except Exception as e:
            self.logger.error(f"Error creating indexes: {str(e)}")
            raise
    
    def _convert_to_dict(self, item: Any) -> Dict[str, Any]:
        """Convert Pydantic model or any object to dictionary"""
        if isinstance(item, BaseModel):
            return item.model_dump()
        elif isinstance(item, dict):
            return item
        else:
            return dict(item)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def save_tasks(self, tasks: List[Any], cache_duration: int = 300) -> None:
        """Save tasks to database with caching
        
        Args:
            tasks: List of task objects or dictionaries
            cache_duration: Cache duration in seconds (default: 5 minutes)
        """
        try:
            current_time = datetime.utcnow()
            cache_expiry = current_time + timedelta(seconds=cache_duration)
            
            for task in tasks:
                task_dict = self._convert_to_dict(task)
                task_dict["last_updated"] = current_time
                task_dict["cache_expiry"] = cache_expiry
                self.db.tasks.update_one(
                    {"id": task_dict["id"]},
                    {"$set": task_dict},
                    upsert=True
                )
            self.logger.info(f"Saved {len(tasks)} tasks with cache expiry at {cache_expiry}")
        except Exception as e:
            self.logger.error(f"Error saving tasks: {str(e)}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def save_projects(self, projects: List[Any], cache_duration: int = 3600) -> None:
        """Save projects to database with caching
        
        Args:
            projects: List of project objects or dictionaries
            cache_duration: Cache duration in seconds (default: 1 hour)
        """
        try:
            current_time = datetime.utcnow()
            cache_expiry = current_time + timedelta(seconds=cache_duration)
            
            for project in projects:
                project_dict = self._convert_to_dict(project)
                project_dict["last_updated"] = current_time
                project_dict["cache_expiry"] = cache_expiry
                self.db.projects.update_one(
                    {"id": project_dict["id"]},
                    {"$set": project_dict},
                    upsert=True
                )
            self.logger.info(f"Saved {len(projects)} projects with cache expiry at {cache_expiry}")
        except Exception as e:
            self.logger.error(f"Error saving projects: {str(e)}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def save_notes(self, notes: List[Any], cache_duration: int = 300) -> None:
        """Save notes to database with caching
        
        Args:
            notes: List of note objects or dictionaries
            cache_duration: Cache duration in seconds (default: 5 minutes)
        """
        try:
            current_time = datetime.utcnow()
            cache_expiry = current_time + timedelta(seconds=cache_duration)
            
            for note in notes:
                note_dict = self._convert_to_dict(note)
                note_dict["last_updated"] = current_time
                note_dict["cache_expiry"] = cache_expiry
                self.db.notes.update_one(
                    {"id": note_dict["id"]},
                    {"$set": note_dict},
                    upsert=True
                )
            self.logger.info(f"Saved {len(notes)} notes with cache expiry at {cache_expiry}")
        except Exception as e:
            self.logger.error(f"Error saving notes: {str(e)}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def get_tasks(self, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get tasks from database
        
        Args:
            project_id: Optional project ID to filter tasks
        
        Returns:
            List of task dictionaries
        """
        try:
            query = {"cache_expiry": {"$gt": datetime.utcnow()}}
            if project_id is not None:
                query["projectId"] = project_id
            
            tasks = list(self.db.tasks.find(query))
            self.logger.info(f"Retrieved {len(tasks)} tasks from cache")
            return tasks
        except Exception as e:
            self.logger.error(f"Error getting tasks: {str(e)}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def get_projects(self) -> List[Dict[str, Any]]:
        """Get projects from database
        
        Returns:
            List of project dictionaries
        """
        try:
            projects = list(self.db.projects.find({
                "cache_expiry": {"$gt": datetime.utcnow()}
            }))
            self.logger.info(f"Retrieved {len(projects)} projects from cache")
            return projects
        except Exception as e:
            self.logger.error(f"Error getting projects: {str(e)}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def get_notes(self) -> List[Dict[str, Any]]:
        """Get notes from database
        
        Returns:
            List of note dictionaries
        """
        try:
            notes = list(self.db.notes.find({
                "cache_expiry": {"$gt": datetime.utcnow()}
            }))
            self.logger.info(f"Retrieved {len(notes)} notes from cache")
            return notes
        except Exception as e:
            self.logger.error(f"Error getting notes: {str(e)}")
            raise
    
    def close(self):
        """Close MongoDB connection"""
        try:
            self.client.close()
            self.logger.info("Database connection closed")
        except Exception as e:
            self.logger.error(f"Error closing database connection: {str(e)}")
            raise

