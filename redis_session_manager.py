import redis
import os
import json
from typing import Dict, Any, Optional
import time
from dotenv import load_dotenv

load_dotenv()
REDIS_HOST =os.getenv("Redis_Host")
REDIS_PORT = os.getenv("Redis_Port")
REDIS_USERNAME = os.getenv("Redis_Username")
REDIS_PASSWORD = os.getenv("Redis_Password")


def get_redis_client():
    """Create a Redis client with retry mechanism"""
    max_retries = 3
    retry_delay = 1  # seconds
    
    for attempt in range(max_retries):
        try:
            # Create Redis client with explicit configuration
            client = redis.Redis(
                host=REDIS_HOST,
                port=int(REDIS_PORT),  # Ensure port is converted to int
                username=REDIS_USERNAME,
                password=REDIS_PASSWORD,
                decode_responses=True,
                socket_timeout=10,  # Increased timeout
                socket_connect_timeout=10,  # Increased connect timeout
                retry_on_timeout=True,
                max_connections=10,  # Limit max connections
                health_check_interval=30  # Add health check
            )
            
            # Test the connection
            client.ping()
            print("Successfully connected to Redis")
            return client
            
        except redis.ConnectionError as e:
            if attempt < max_retries - 1:
                print(f"Redis connection attempt {attempt + 1} failed. Retrying in {retry_delay} seconds...")
                print(f"Error: {str(e)}")
                time.sleep(retry_delay)
            else:
                print(f"Failed to connect to Redis after {max_retries} attempts: {str(e)}")
                raise
        except Exception as e:
            print(f"Unexpected error while connecting to Redis: {str(e)}")
            raise

# Initialize Redis client
try:
    redis_client = get_redis_client()
except Exception as e:
    print(f"Critical: Could not initialize Redis client: {str(e)}")
    redis_client = None

async def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a session from Redis"""
    if not redis_client:
        print("Error: Redis client not initialized")
        return None
        
    try:
        print(f"Attempting to get session with ID: {session_id}")
        session_key = f"session:{session_id}"
        session_data = redis_client.get(session_key)
        
        if session_data:
            try:
                decoded_data = json.loads(session_data)
                print(f"Retrieved session data: {decoded_data}")
                return decoded_data
            except json.JSONDecodeError as e:
                print(f"Error decoding session data: {str(e)}")
                return None
        
        print(f"No session found for ID: {session_id}")
        return None
    except Exception as e:
        print(f"Error getting session: {str(e)}")
        return None

async def update_session(session_id: str, **kwargs) -> bool:
    """Update session data in Redis"""
    if not redis_client:
        print("Error: Redis client not initialized")
        return False
        
    try:
        session_key = f"session:{session_id}"
        
        # Get existing session data
        existing_data = await get_session(session_id) or {}
        
        # Update with new values
        existing_data.update(kwargs)
        
        print(f"Updating session {session_id} with data: {existing_data}")
        
        # Save back to Redis with 1 hour expiration
        try:
            redis_client.setex(
                session_key,
                3600,  # 1 hour expiration
                json.dumps(existing_data)
            )
            return True
        except redis.RedisError as e:
            print(f"Redis error while updating session: {str(e)}")
            return False
            
    except Exception as e:
        print(f"Error updating session: {str(e)}")
        return False

async def delete_session(session_id: str) -> bool:
    """Delete a session from Redis"""
    if not redis_client:
        print("Error: Redis client not initialized")
        return False
        
    try:
        session_key = f"session:{session_id}"
        redis_client.delete(session_key)
        print(f"Successfully deleted session: {session_id}")
        return True
    except Exception as e:
        print(f"Error deleting session: {str(e)}")
        return False 