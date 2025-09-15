#!/usr/bin/env python3
"""
Cron job script - runs once and exits
This replaces the continuous bot for scheduled execution
"""
import json
import os
import time
from datetime import datetime
import git
import discord
import asyncio

# Constants
REPO_URL = 'https://github.com/cvrve/Summer2025-Internships'
LOCAL_REPO_PATH = 'Summer2025-Internships'
JSON_FILE_PATH = os.path.join(LOCAL_REPO_PATH, '.github', 'scripts', 'listings.json')
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_IDS = os.getenv('CHANNEL_IDS', '').split(',') if os.getenv('CHANNEL_IDS') else []
MAX_RETRIES = 3

# Discord client setup
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

def clone_or_update_repo():
    """Clone or update the repository"""
    print("Cloning or updating repository...")
    if os.path.exists(LOCAL_REPO_PATH):
        try:
            repo = git.Repo(LOCAL_REPO_PATH)
            repo.remotes.origin.pull()
            print("Repository updated.")
        except git.exc.InvalidGitRepositoryError:
            os.rmdir(LOCAL_REPO_PATH)
            git.Repo.clone_from(REPO_URL, LOCAL_REPO_PATH)
            print("Repository cloned fresh.")
    else:
        git.Repo.clone_from(REPO_URL, LOCAL_REPO_PATH)
        print("Repository cloned fresh.")

def read_json():
    """Read JSON file and return data"""
    print(f"Reading JSON file from {JSON_FILE_PATH}...")
    if not os.path.exists(JSON_FILE_PATH):
        print("JSON file not found.")
        return []
    
    with open(JSON_FILE_PATH, 'r') as file:
        return json.load(file)

def format_message(role):
    """Format Discord message for a role"""
    message = f"**🚨 NEW INTERNSHIP ALERT 🚨**\n\n"
    message += f"**Company:** {role['company_name']}\n"
    message += f"**Position:** {role['title']}\n"
    
    if role.get('locations'):
        locations_str = ', '.join(role['locations'])
        message += f"**Location:** {locations_str}\n"
    
    if role.get('url'):
        message += f"**Apply:** {role['url']}\n"
    
    message += f"\n*Posted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
    return message

async def send_message_to_channel(channel_id, message):
    """Send message to a specific channel"""
    try:
        channel = client.get_channel(int(channel_id))
        if channel:
            await channel.send(message)
            print(f"Message sent to channel {channel_id}")
            return True
        else:
            print(f"Channel {channel_id} not found")
            return False
    except Exception as e:
        print(f"Failed to send message to channel {channel_id}: {e}")
        return False

async def check_and_send_updates():
    """Main function to check for updates and send messages"""
    print(f"Starting check at {datetime.now()}")
    
    # Update repository
    clone_or_update_repo()
    
    # Read current data
    new_data = read_json()
    if not new_data:
        print("No data found in JSON file")
        return
    
    # Read previous data
    previous_data = []
    if os.path.exists('previous_data.json'):
        with open('previous_data.json', 'r') as file:
            previous_data = json.load(file)
    
    # Compare and find new roles
    old_roles_dict = {(role['title'], role['company_name']): role for role in previous_data}
    new_roles = []
    
    for new_role in new_data:
        old_role = old_roles_dict.get((new_role['title'], new_role['company_name']))
        
        if not old_role and new_role['is_visible'] and new_role['active']:
            new_roles.append(new_role)
            print(f"New role found: {new_role['title']} at {new_role['company_name']}")
    
    # Send messages for new roles
    if new_roles:
        for role in new_roles:
            message = format_message(role)
            for channel_id in CHANNEL_IDS:
                await send_message_to_channel(channel_id, message)
                await asyncio.sleep(1)  # Rate limiting
    else:
        print("No new roles found")
    
    # Update previous data
    with open('previous_data.json', 'w') as file:
        json.dump(new_data, file)
    print("Updated previous data")
    
    print(f"Check completed at {datetime.now()}")

@client.event
async def on_ready():
    """When client is ready, run the check and exit"""
    print(f'Logged in as {client.user}')
    await check_and_send_updates()
    await client.close()

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("ERROR: DISCORD_TOKEN not found")
        exit(1)
    
    if not CHANNEL_IDS or CHANNEL_IDS == ['']:
        print("ERROR: CHANNEL_IDS not found")
        exit(1)
    
    print("Starting cron job...")
    client.run(DISCORD_TOKEN)