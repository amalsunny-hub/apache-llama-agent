"""
agent.py — The main Apache Health Agent.

This is the brain loop:
  1. Ask Llama what to do next
  2. Parse Llama's reply for a TOOL: command
  3. Execute that tool (run the Linux command)
  4. Send the output back to Llama
  5. Repeat until Llama says DONE

Python NEVER decides which tool to run.
Llama decides everything. That is what makes this an AI Agent.

Usage:
    python3 agent.py
    python3 agent.py --goal "Apache is returning 500 errors"
    python3 agent.py --goal "restart the apache server"
"""

import sys
import re
import argparse
from datetime import datetime

from llm import ask_llama, check_ollama_running
from tools import execute_tool, TOOLS
from prompts import SYSTEM_PROMPT, build_initial_prompt, build_followup_prompt


# ── Settings ───────────────────────────────────────────────────────────────────
MAX_ROUNDS = 10        # Safety limit — max number of tool calls per session
SEPARATOR  = "─" * 60


def parse_tool_from_reply(reply: str) -> str | None:
    """
    Extract the tool name from Llama's reply.

    Llama should say:  TOOL: check_apache_status
    We parse out:      check_apache_status

    Returns None if no TOOL: found (means Llama said DONE or gave a final answer).
    """
    # Match  TOOL: tool_name  (case-insensitive, with optional whitespace)
    match = re.search(r"TOOL:\s*([a-z_]+)", reply, re.IGNORECASE)
    if match:
        return match.group(1).strip().lower()
    return None


def is_done(reply: str) -> bool:
    """Check if Llama has finished its analysis."""
    return "DONE" in reply.upper()


def print_header():
    print("\n" + "═" * 60)
    print("   🤖  Apache Llama Agent")
    print("   Powered by Ollama + Llama 3.2 3B on AlmaLinux 9")
    print("═" * 60)
    print(f"   Session started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("═" * 60 + "\n")


def print_round(round_num: int, llm_reply: str, tool_name: str = None, tool_output: str = None):
    print(f"\n{SEPARATOR}")
    print(f"  Round {round_num}")
    print(SEPARATOR)
    print(f"\n  🧠 Llama says:\n     {llm_reply.strip()}")

    if tool_name:
        print(f"\n  ⚙️  Python executes: {tool_name}")

    if tool_output:
        # Trim very long outputs for display
        display = tool_output[:600] + "\n  ...(truncated)" if len(tool_output) > 600 else tool_output
        print(f"\n  📋 Output:\n")
        for line in display.split("\n"):
            print(f"     {line}")


def run_agent(user_goal: str):
    """Main agent loop."""

    print_header()

    # ── Pre-flight: check Ollama is running ───────────────────────────────────
    print("  Checking Ollama connection...", end=" ")
    if not check_ollama_running():
        print("❌ FAILED")
        print("\n  ERROR: Ollama is not running.")
        print("  Start it with:  sudo systemctl start ollama")
        sys.exit(1)
    print("✅ Connected\n")

    print(f"  Goal: {user_goal}")
    print(f"\n{SEPARATOR}")

    # ── Conversation history ──────────────────────────────────────────────────
    history = []

    # First message: user's goal
    history.append({"role": "user", "content": user_goal})

    # Build the initial prompt
    prompt = build_initial_prompt(user_goal)

    # ── Agent Loop ────────────────────────────────────────────────────────────
    for round_num in range(1, MAX_ROUNDS + 1):

        # Ask Llama what to do
        reply = ask_llama(prompt, system=SYSTEM_PROMPT)

        # Record Llama's reply
        history.append({"role": "assistant", "content": reply})

        # Check if Llama is done
        if is_done(reply) and not parse_tool_from_reply(reply):
            print_round(round_num, reply)
            print(f"\n{'═' * 60}")
            print("  ✅ Agent finished. Final report above.")
            print(f"{'═' * 60}\n")
            break

        # Parse tool from reply
        tool_name = parse_tool_from_reply(reply)

        if not tool_name:
            # Llama gave a free-form answer (not a tool call and not DONE)
            # Treat it as the final answer
            print_round(round_num, reply)
            print(f"\n{'═' * 60}")
            print("  ✅ Agent completed (free-form answer).")
            print(f"{'═' * 60}\n")
            break

        if tool_name not in TOOLS:
            # Llama hallucinated a tool name — correct it gently
            correction = f"Tool '{tool_name}' does not exist. Use one of: {list(TOOLS.keys())}"
            history.append({"role": "tool", "content": correction})
            print_round(round_num, reply, tool_name, correction)
            prompt = build_followup_prompt(history)
            continue

        # Execute the tool
        tool_output = execute_tool(tool_name)
        history.append({"role": "tool", "content": tool_output})

        print_round(round_num, reply, tool_name, tool_output)

        # Build next prompt with full history
        prompt = build_followup_prompt(history)

    else:
        # Hit MAX_ROUNDS limit
        print(f"\n  ⚠️  Reached maximum rounds ({MAX_ROUNDS}). Asking for final summary...")
        final_prompt = build_followup_prompt(history) + "\n\nYou must now reply DONE and give your final diagnosis."
        final_reply = ask_llama(final_prompt, system=SYSTEM_PROMPT)
        print(f"\n  🧠 Final Llama answer:\n{final_reply}")


# ── Entry Point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Apache Llama Agent — diagnose and fix Apache issues using AI"
    )
    parser.add_argument(
        "--goal",
        type=str,
        default=None,
        help='What you want the agent to do. Example: --goal "Apache is down, find why and fix it"'
    )
    args = parser.parse_args()

    if args.goal:
        goal = args.goal
    else:
        print("\n  What would you like the agent to do?")
        print("  Examples:")
        print("    - Analyze my Apache server and find any errors")
        print("    - Apache is returning 500 errors, find the cause")
        print("    - Restart Apache and confirm it is running")
        print("    - Check why Apache is slow\n")
        goal = input("  Your request: ").strip()

        if not goal:
            goal = "Analyze my Apache server and tell me if there are any errors or problems."

    run_agent(goal)
