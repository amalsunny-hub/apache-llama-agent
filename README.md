# 🤖 Apache Llama Agent

**An AI Agent that monitors your Apache web server, identifies errors from logs, and restarts the service — all driven by Llama 3.2 running locally on your EC2 instance.**

> **Key idea:** Python never decides what to do. Llama reads the logs and decides everything. That is what makes this an AI Agent, not just a script.

---

## 📋 Table of Contents

1. [What This Does](#what-this-does)
2. [How It Works](#how-it-works)
3. [Project Structure](#project-structure)
4. [Requirements](#requirements)
5. [Step 1 — Launch EC2 Instance](#step-1--launch-ec2-instance)
6. [Step 2 — Update System & Install Python](#step-2--update-system--install-python)
7. [Step 3 — Create Swap File](#step-3--create-swap-file)
8. [Step 4 — Create the ollama-user](#step-4--create-the-ollama-user)
9. [Step 5 — Install & Start Apache](#step-5--install--start-apache)
10. [Step 6 — Install Ollama](#step-6--install-ollama)
11. [Step 7 — Download the Llama Model](#step-7--download-the-llama-model)
12. [Step 8 — Clone This Project](#step-8--clone-this-project)
13. [Step 9 — Set Up Virtual Environment](#step-9--set-up-virtual-environment)
14. [Step 10 — Run the Agent](#step-10--run-the-agent)
15. [Step 11 — Run as a Background Service](#step-11--run-as-a-background-service)
16. [Example Output](#example-output)
17. [How Each File Works](#how-each-file-works)
18. [Troubleshooting](#troubleshooting)

---

## What This Does

When you run this agent, here is what happens:

1. You tell the agent: *"Apache is returning errors, find the cause"*
2. Llama reads your request and decides to check Apache status first
3. Python runs `systemctl status httpd` and sends the output back to Llama
4. Llama reads the output and decides to check the error log next
5. Python runs `tail -n 30 /var/log/httpd/error_log` and sends it to Llama
6. Llama finds the error, explains it, and decides whether to restart or reload Apache
7. Python executes the restart command
8. Llama confirms everything is fixed and gives you a final report

**You just type your question. The AI does the rest.**

---

## How It Works

```
User types a question
        │
        ▼
   Python Agent (agent.py)
        │
        ▼
   Send to Llama via Ollama API
        │
        ▼
   Llama replies: TOOL: check_apache_error_log
        │
        ▼
   Python runs the Linux command
        │
        ▼
   Output sent back to Llama
        │
        ▼
   Llama reads output, picks next tool
        │
        ▼
   Loop continues until Llama says DONE
        │
        ▼
   Llama prints final diagnosis + fix
```

> Python never says "run this command." Only Llama says that. Python just executes whatever Llama chooses.

---

## Project Structure

```
apache-llama-agent/
│
├── agent.py         ← Main loop — runs the agent, manages conversation
├── llm.py           ← Talks to Ollama API (sends prompts, gets replies)
├── tools.py         ← Linux commands the agent can execute
├── prompts.py       ← System prompt — tells Llama how to behave
└── requirements.txt ← Python dependencies (just: requests)
```

### What each file does in plain English

| File | Role | Analogy |
|------|------|---------|
| `agent.py` | Manages the conversation loop | The manager |
| `llm.py` | Sends messages to Llama | The phone |
| `tools.py` | Runs Linux commands | The hands |
| `prompts.py` | Tells Llama its job and rules | The job description |

---

## Requirements

| Item | Value |
|------|-------|
| EC2 Instance Type | t3.small (2 vCPU, 2 GB RAM) |
| Operating System | AlmaLinux 9 |
| Python | 3.9 or higher |
| Ollama | Latest version |
| Llama Model | llama3.2:3b (~2 GB download) |
| Web Server | Apache (httpd) |

> **Why t3.small?** Llama 3.2 3B is a small model that runs on 2 GB RAM. It is slower than larger models but works well for this kind of task.

---

## Step 1 — Launch EC2 Instance

1. Go to the **AWS Console → EC2 → Launch Instance**
2. Set these values:

   | Setting | Value |
   |---------|-------|
   | Name | `apache-llama-agent` |
   | AMI | AlmaLinux 9 (search in AWS Marketplace, free tier available) |
   | Instance Type | `t3.small` |
   | Storage | 20 GB gp3 |
   | Security Group | Allow SSH (port 22) and HTTP (port 80) |

3. Create or select a key pair (`.pem` file)
4. Click **Launch Instance**

**Connect via SSH:**

```bash
ssh -i your-key.pem ec2-user@<your-ec2-public-ip>
```

---

## Step 2 — Update System & Install Python

Once you are logged in to your EC2 instance, run these commands one by one.

**Update all system packages:**

```bash
sudo dnf update -y
```

> This may take 2–5 minutes. It makes sure all packages are up to date.

**Install Python, pip, and git:**

```bash
sudo dnf install python3 python3-pip git -y
```

**Verify Python is installed:**

```bash
python3 --version
```

You should see something like: `Python 3.11.x`

---

## Step 3 — Create Swap File

> **Why is this needed?**
> t3.small only has **2 GB of RAM**. Llama 3.2 3B uses about 1.8 GB of that.
> Without swap, the OS can kill Ollama mid-response when memory runs low.
> A 2 GB swap file gives the system breathing room and prevents crashes.

**Check your current memory and swap:**

```bash
free -h
```

You will see swap is `0B` by default — we need to add it.

**Create a 2 GB swap file:**

```bash
sudo fallocate -l 2G /swapfile
```

**Set correct permissions (swap must not be readable by other users):**

```bash
sudo chmod 600 /swapfile
```

**Format it as swap space:**

```bash
sudo mkswap /swapfile
```

**Turn the swap on right now:**

```bash
sudo swapon /swapfile
```

**Verify swap is active:**

```bash
free -h
```

You should now see `2.0G` under the Swap row.

**Make swap permanent — survives reboots:**

```bash
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

**Verify it was added to fstab:**

```bash
cat /etc/fstab | grep swap
```

You should see the line: `/swapfile none swap sw 0 0`

**Optional — tune swappiness (how aggressively Linux uses swap):**

```bash
# Set to 10 — Linux will prefer RAM and only use swap when necessary
sudo sysctl vm.swappiness=10

# Make it permanent across reboots
echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
```

> **Result:** Your t3.small now has 2 GB RAM + 2 GB swap = 4 GB effective memory.
> Llama 3.2 3B will run stably without getting killed by the OS.

---

## Step 4 — Create the ollama-user

We create a dedicated system user called `ollama-user` to run the agent.

**Why a separate user?**

| Reason | Explanation |
|--------|-------------|
| Security | The agent only has the permissions it needs — nothing more |
| Isolation | If something goes wrong, it cannot affect other users or the system |
| Best practice | Services should never run as `root` or your personal login user |
| Clean logs | All agent activity is clearly tied to one user |

---

**Create the user (no home directory login, no password — service account only):**

```bash
sudo useradd -r -m -d /home/ollama-user -s /bin/bash -c "Ollama Agent Service User" ollama-user
```

What each flag means:

| Flag | Meaning |
|------|---------|
| `-r` | System account (lower UID, not a regular login user) |
| `-m` | Create a home directory at `/home/ollama-user` |
| `-d /home/ollama-user` | Set the home directory path |
| `-s /bin/bash` | Give it a bash shell (needed to run Python scripts) |
| `-c "..."` | A description label for the account |

---

**Verify the user was created:**

```bash
id ollama-user
```

You should see something like:
```
uid=999(ollama-user) gid=999(ollama-user) groups=999(ollama-user)
```

---

**Give ollama-user permission to control Apache (httpd) via sudo:**

The agent needs to restart Apache, read logs, and check ports. We give it only those specific permissions — not full sudo access.

```bash
sudo visudo
```

Scroll to the bottom and add this line:

```
ollama-user ALL=(ALL) NOPASSWD: /bin/systemctl restart httpd, /bin/systemctl reload httpd, /bin/systemctl status httpd, /bin/tail, /bin/journalctl, /bin/ss, /bin/df, /bin/free, /bin/chmod
```

Save and exit: press `Ctrl+X` → `Y` → `Enter`

> This means `ollama-user` can only run those specific commands with sudo — it cannot do anything else on the system.

---

**Switch to the ollama-user to verify:**

```bash
sudo su - ollama-user
```

You should see the prompt change to:
```
[ollama-user@ip-xxx ~]$
```

Type `exit` to go back to your normal user:

```bash
exit
```

---

## Step 5 — Install & Start Apache

Apache is the web server this agent will monitor and fix.

**Install Apache:**

```bash
sudo dnf install httpd -y
```

**Start Apache and enable it on boot:**

```bash
sudo systemctl start httpd
sudo systemctl enable httpd
```

**Check it is running:**

```bash
sudo systemctl status httpd
```

You should see `active (running)` in green.

**Test it works (from your browser):**

Open `http://<your-ec2-public-ip>` — you should see the AlmaLinux Apache welcome page.

> Make sure port 80 is open in your EC2 Security Group.

---

## Step 6 — Install Ollama

Ollama lets you run AI models (like Llama) directly on your server — no internet required, no API key needed.

**Install Ollama with one command:**

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

> This downloads and installs Ollama automatically.

**Start Ollama as a background service:**

```bash
sudo systemctl enable ollama
sudo systemctl start ollama
```

**Check it is running:**

```bash
sudo systemctl status ollama
```

**Verify the API is working:**

```bash
curl http://localhost:11434
```

You should see: `Ollama is running`

---

## Step 7 — Download the Llama Model

Download the Llama 3.2 3B model. This is a ~2 GB file.

```bash
ollama pull llama3.2:3b
```

> This will take a few minutes depending on your network speed. You only need to do this once.

**Test the model works:**

```bash
ollama run llama3.2:3b
```

Type anything (like `hello`) and press Enter. You should get a reply. Press `Ctrl+D` or type `/bye` to exit.

---

## Step 8 — Clone This Project

First switch to the `ollama-user` account — all project files must live inside this user's home directory:

```bash
sudo su - ollama-user
```

Your prompt will change to:
```
[ollama-user@ip-xxx ~]$
```

Now clone the project:

```bash
git clone https://github.com/amalsunny-hub/apache-llama-agent.git
cd apache-llama-agent
```

The project now lives at `/home/ollama-user/apache-llama-agent/`

> Stay as `ollama-user` for Steps 9 and 10 as well.

---

## Step 9 — Set Up Virtual Environment

A virtual environment keeps this project's Python packages separate from the system Python.

**Create the virtual environment:**

```bash
python3 -m venv venv
```

**Activate it:**

```bash
source venv/bin/activate
```

Your terminal prompt will change to show `(venv)` — this means it is active.

**Install the required packages:**

```bash
pip install -r requirements.txt
```

This installs only one package: `requests` (used to talk to Ollama).

**Verify installation:**

```bash
pip list
```

You should see `requests` in the list.

---

## Step 10 — Run the Agent

Make sure your virtual environment is active (`source venv/bin/activate`) and Ollama is running.

**Interactive mode (recommended for first run):**

```bash
python3 agent.py
```

The agent will ask you what you want to do. Type your question:

```
What would you like the agent to do?
Your request: Apache is returning 500 errors, find the cause and fix it
```

**Direct mode (pass the goal as an argument):**

```bash
python3 agent.py --goal "Check if Apache is running and show me any recent errors"
```

```bash
python3 agent.py --goal "Restart Apache and confirm it comes back up"
```

```bash
python3 agent.py --goal "Analyze my Apache server and find any problems"
```

---

## Step 11 — Run as a Background Service

This is the recommended way to run the agent in production.
Instead of running `python3 agent.py` manually every time, we register it as a **systemd service** so it:

- Starts automatically when the EC2 instance boots
- Restarts itself if it crashes
- Runs silently in the background — you never have to touch it

**No changes to any Python files are needed. Just follow these steps.**

---

### 11.1 — Create the service file

```bash
sudo nano /etc/systemd/system/llama-agent.service
```

Paste this exactly:

```ini
[Unit]
Description=Apache Llama Agent — AI-powered Apache monitor
After=network.target ollama.service
Wants=ollama.service

[Service]
Type=simple
User=ollama-user
WorkingDirectory=/home/ollama-user/apache-llama-agent
ExecStart=/home/ollama-user/apache-llama-agent/venv/bin/python3 agent.py --goal "Monitor Apache server health. Check for errors in logs. If Apache is down or crashed, restart it. Give a full diagnosis."
Restart=always
RestartSec=60
StandardOutput=append:/var/log/llama-agent.log
StandardError=append:/var/log/llama-agent.log

[Install]
WantedBy=multi-user.target
```

Save and exit: press `Ctrl+X` → `Y` → `Enter`

---

### 11.2 — What each line means

| Line | What it does |
|------|-------------|
| `After=ollama.service` | Waits for Ollama to start before running the agent |
| `Wants=ollama.service` | Starts Ollama automatically if it is not already running |
| `User=ollama-user` | Runs as the dedicated service account — not root, not your login user |
| `WorkingDirectory` | The project folder inside ollama-user's home directory |
| `ExecStart` | The exact command to run — uses the venv Python |
| `Restart=always` | If the agent crashes or finishes, restart it after 60 seconds |
| `RestartSec=60` | Wait 60 seconds before restarting (gives Ollama time to be ready) |
| `StandardOutput=append:...` | Save all output to a log file so you can read it later |

---

### 11.3 — Create the log file

```bash
sudo touch /var/log/llama-agent.log
sudo chown ollama-user:ollama-user /var/log/llama-agent.log
```

---

### 11.4 — Enable and start the service

Tell systemd to load the new service file:

```bash
sudo systemctl daemon-reload
```

Enable it so it starts automatically on every reboot:

```bash
sudo systemctl enable llama-agent
```

Start it right now:

```bash
sudo systemctl start llama-agent
```

---

### 11.5 — Check it is running

```bash
sudo systemctl status llama-agent
```

You should see something like:

```
● llama-agent.service — Apache Llama Agent — AI-powered Apache monitor
     Loaded: loaded (/etc/systemd/system/llama-agent.service; enabled)
     Active: active (running) since Sat 2025-06-21 10:00:00 UTC
```

---

### 11.6 — Watch the live output

This is the best part — you can watch the agent working in real time:

```bash
sudo tail -f /var/log/llama-agent.log
```

You will see something like:

```
════════════════════════════════════════════════════════════
   🤖  Apache Llama Agent  —  HazerCloud
════════════════════════════════════════════════════════════
  Checking Ollama connection... ✅ Connected
  Goal: Monitor Apache server health...

  🧠 Llama says:  TOOL: check_apache_status
  [Python] Executing: check_apache_status

  🧠 Llama says:  TOOL: check_apache_error_log
  [Python] Executing: check_apache_error_log

  🧠 Llama says:  DONE
     Apache is running normally. No errors found in logs.
     Disk and memory are healthy. No action needed.

════════════════════════════════════════════════════════════
  ✅ Agent finished.
════════════════════════════════════════════════════════════

Sleeping 60 seconds before next check...
```

Press `Ctrl+C` to stop watching (the agent keeps running in the background).

---

### 11.7 — Other useful commands

**Stop the service:**
```bash
sudo systemctl stop llama-agent
```

**Restart the service:**
```bash
sudo systemctl restart llama-agent
```

**Disable auto-start on boot:**
```bash
sudo systemctl disable llama-agent
```

**View the last 50 lines of the log:**
```bash
sudo tail -n 50 /var/log/llama-agent.log
```

**Clear the log file:**
```bash
sudo truncate -s 0 /var/log/llama-agent.log
```

---

### How it all connects now

```
EC2 boots
    │
    ▼
systemd starts ollama.service        ← Ollama loads Llama 3.2 3B into memory
    │
    ▼
systemd starts llama-agent.service   ← Runs as ollama-user (isolated, secure)
    │
    ▼
Agent runs → Llama reads logs → takes action → writes report to log file
    │
    ▼
Agent finishes → waits 60 seconds → runs again automatically
    │
    ▼
You just read /var/log/llama-agent.log whenever you want a report
```

**You never need to SSH in and run the agent manually again.**

---



```
════════════════════════════════════════════════════════════
   🤖  Apache Llama Agent  —  HazerCloud
   Powered by Ollama + Llama 3.2 3B on AlmaLinux 9
════════════════════════════════════════════════════════════
   Session started: 2025-06-20 10:32:15
════════════════════════════════════════════════════════════

  Checking Ollama connection... ✅ Connected

  Goal: Apache is returning 500 errors, find the cause and fix it

────────────────────────────────────────────────────────────
  Round 1
────────────────────────────────────────────────────────────

  🧠 Llama says:
     TOOL: check_apache_status

  [Python] Executing: check_apache_status

  📋 Output:
     ● httpd.service - The Apache HTTP Server
        Active: active (running) since Fri 2025-06-20 10:30:01 UTC
        ...

────────────────────────────────────────────────────────────
  Round 2
────────────────────────────────────────────────────────────

  🧠 Llama says:
     TOOL: check_apache_error_log

  [Python] Executing: check_apache_error_log

  📋 Output:
     [Fri Jun 20 10:28:45 2025] [error] [pid 1234] PHP Fatal error:
     Cannot redeclare function in /var/www/html/index.php on line 42

────────────────────────────────────────────────────────────
  Round 3
────────────────────────────────────────────────────────────

  🧠 Llama says:
     DONE

     DIAGNOSIS:
     Apache is running but returning 500 errors due to a PHP fatal error.
     File: /var/www/html/index.php at line 42
     Error: A function is declared twice (duplicate function name).

     RECOMMENDATION:
     1. Open /var/www/html/index.php and go to line 42
     2. Look for a duplicate function definition and remove one copy
     3. After fixing the PHP file, run: sudo systemctl reload httpd
     4. Apache itself does not need a restart — the issue is in the PHP code.

════════════════════════════════════════════════════════════
  ✅ Agent finished. Final report above.
════════════════════════════════════════════════════════════
```

---

## How Each File Works

### `agent.py` — The Manager

This is the file you run. It:
- Checks Ollama is reachable before starting
- Sends your goal to Llama
- Reads Llama's reply and looks for `TOOL: tool_name`
- Calls the right function from `tools.py`
- Sends the result back to Llama
- Repeats until Llama says `DONE`
- Has a safety limit of 10 rounds so it never loops forever

### `llm.py` — The Phone to Llama

This file has one main function: `ask_llama(prompt)`.

It sends an HTTP POST request to `http://localhost:11434/api/generate` and returns Llama's text response. Temperature is set to `0.1` (very low) so Llama gives consistent, reliable answers rather than creative ones.

### `tools.py` — The Hands

Contains one function per action:

| Function | Linux Command It Runs |
|----------|----------------------|
| `check_apache_status()` | `systemctl status httpd` |
| `check_apache_error_log()` | `tail -n 30 /var/log/httpd/error_log` |
| `check_apache_access_log()` | `tail -n 20 /var/log/httpd/access_log` |
| `check_system_journal()` | `journalctl -u httpd -n 30` |
| `check_disk_space()` | `df -h` |
| `check_memory()` | `free -h` |
| `check_port_80()` | `ss -tlnp sport = :80` |
| `restart_apache()` | `systemctl restart httpd` |
| `reload_apache()` | `systemctl reload httpd` |

### `prompts.py` — The Job Description

Contains the system prompt — the set of rules given to Llama at the start of every session. It tells Llama:
- Its role (Apache SysAdmin expert)
- What tools are available and what they do
- That it must reply `TOOL: name` or `DONE`
- Only one tool per reply
- How to structure its final diagnosis

---

## Troubleshooting

**Ollama not connecting:**
```bash
sudo systemctl start ollama
sudo systemctl status ollama
curl http://localhost:11434
```

**Model not found:**
```bash
ollama list           # See what models are downloaded
ollama pull llama3.2:3b   # Re-download if missing
```

**Apache log permission denied:**
```bash
# Make sure your user can read logs
sudo chmod 644 /var/log/httpd/error_log
sudo chmod 644 /var/log/httpd/access_log
```

**Agent is very slow:**
- t3.small has 2 GB RAM — Llama 3.2 3B needs most of that
- First run is slower (model loading into memory)
- Subsequent runs in the same session are faster
- If it times out, increase the timeout in `llm.py` (default 120 seconds)

**Python version error:**
```bash
python3 --version    # Must be 3.9+
```

---

## Why This Is an AI Agent (Not Just a Script)

A regular script would look like this:
```python
# Normal script — Python decides everything
status = check_apache_status()
if "failed" in status:
    restart_apache()
```

This agent works differently:
```python
# AI Agent — Llama decides everything
reply = ask_llama("Apache has errors. What should I do?")
# Llama replies: TOOL: check_apache_error_log
# Python runs it, sends output back
# Llama then decides: TOOL: restart_apache
# Python runs it
```

The difference: Llama **reads the actual output** and **reasons about what to do next**. It can handle situations the programmer never thought of, because it understands context.

---

## License

MIT License — free to use, modify, and share.

---

*Built with ❤️ by HazerCloud*
