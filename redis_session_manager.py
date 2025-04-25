import redis
import os
import json
from typing import Dict, Any, Optional
import time
from dotenv import load_dotenv

load_dotenv()

# Log environment variables (without sensitive data)
print("Environment variables check:")
print(f"Redis_Host exists: {'Redis_Host' in os.environ}")
print(f"Redis_Port exists: {'Redis_Port' in os.environ}")
print(f"Redis_Username exists: {'Redis_Username' in os.environ}")
print(f"Redis_Password exists: {'Redis_Password' in os.environ}")

REDIS_HOST = os.getenv("Redis_Host")
REDIS_PORT = os.getenv("Redis_Port")
REDIS_USERNAME = os.getenv("Redis_Username")
REDIS_PASSWORD = os.getenv("Redis_Password")

# Global redis client - will be initialized lazily
redis_client = None

def get_redis_client():
    """Create a Redis client with retry mechanism - lazy loading pattern"""
    global redis_client
    
    # Return existing client if already initialized
    if redis_client is not None:
        try:
            # Test if connection is still alive
            redis_client.ping()
            return redis_client
        except:
            # Reset client if connection is dead
            redis_client = None
    
    max_retries = 3
    retry_delay = 1  # seconds
    
    for attempt in range(max_retries):
        try:
            print(f"Attempting Redis connection (attempt {attempt + 1}/{max_retries})")
            print(f"Connection details - Host: {REDIS_HOST}, Port: {REDIS_PORT}")
            
            # Create Redis client with explicit configuration
            client = redis.Redis(
                host=REDIS_HOST,
                port=int(REDIS_PORT),
                username=REDIS_USERNAME,
                password=REDIS_PASSWORD,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True,
                ssl=True,  # Enable SSL/TLS
                ssl_cert_reqs=None  # Don't verify SSL certificate
            )
            
            # Test the connection
            print("Testing Redis connection with ping...")
            client.ping()
            print("Successfully connected to Redis")
            
            # Store the client globally
            global redis_client
            redis_client = client
            return client
            
        except redis.ConnectionError as e:
            print(f"Redis connection error: {str(e)}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print(f"Failed to connect to Redis after {max_retries} attempts")
                raise
        except Exception as e:
            print(f"Unexpected error while connecting to Redis: {type(e).__name__}: {str(e)}")
            raise

async def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a session from Redis"""
    try:
        client = get_redis_client()
        if not client:
            print("Error: Could not initialize Redis client")
            return None
            
        print(f"Attempting to get session with ID: {session_id}")
        session_key = f"session:{session_id}"
        session_data = client.get(session_key)
        
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
        print(f"Error getting session: {type(e).__name__}: {str(e)}")
        return None

async def update_session(session_id: str, **kwargs) -> bool:
    """Update session data in Redis"""
    try:
        client = get_redis_client()
        if not client:
            print("Error: Could not initialize Redis client")
            return False
            
        session_key = f"session:{session_id}"
        
        # Get existing session data
        existing_data = await get_session(session_id) or {}
        
        # Update with new values
        existing_data.update(kwargs)
        
        print(f"Updating session {session_id} with data: {existing_data}")
        
        # Save back to Redis with 1 hour expiration
        try:
            client.setex(
                session_key,
                3600,  # 1 hour expiration
                json.dumps(existing_data)
            )
            return True
        except redis.RedisError as e:
            print(f"Redis error while updating session: {str(e)}")
            return False
            
    except Exception as e:
        print(f"Error updating session: {type(e).__name__}: {str(e)}")
        return False

async def delete_session(session_id: str) -> bool:
    """Delete a session from Redis"""
    try:
        client = get_redis_client()
        if not client:
            print("Error: Could not initialize Redis client")
            return False
            
        session_key = f"session:{session_id}"
        client.delete(session_key)
        print(f"Successfully deleted session: {session_id}")
        return True
    except Exception as e:
        print(f"Error deleting session: {type(e).__name__}: {str(e)}")
        return False 