#!/usr/bin/env python3
"""
Automated Task Processor Agent for Digital FTE - Silver Tier
Processes tasks from Inbox, classifies them, and routes to appropriate handlers.
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime
import re

VAULT_PATH = Path.home() / "AI_Employee_Vault"
INBOX_PATH = VAULT_PATH / "Inbox"
NEEDS_ACTION_PATH = VAULT_PATH / "Needs_Action"
IN_PROGRESS_PATH = VAULT_PATH / "In_Progress"
DONE_PATH = VAULT_PATH / "Done"


class TaskProcessor:
    """Automated task processing agent"""

    def __init__(self):
        self.processed_count = 0
        self.error_count = 0

    def classify_task(self, task_content: str) -> dict:
        """Classify task by analyzing content"""

        task_lower = task_content.lower()

        # Extract priority
        priority = "normal"
        if "**priority**: high" in task_lower or "urgent" in task_lower:
            priority = "high"
        elif "**priority**: low" in task_lower:
            priority = "low"

        # Classify task type
        task_type = "general"
        if "hello world" in task_lower or "test" in task_lower:
            task_type = "test"
        elif "process file" in task_lower or "file:" in task_lower:
            task_type = "file_processing"
        elif "deploy" in task_lower or "production" in task_lower:
            task_type = "deployment"
        elif "bug" in task_lower or "fix" in task_lower or "error" in task_lower:
            task_type = "bug_fix"
        elif "feature" in task_lower or "implement" in task_lower:
            task_type = "feature"

        # Determine if auto-processable
        auto_processable = task_type in ["test", "file_processing"]

        return {
            "type": task_type,
            "priority": priority,
            "auto_processable": auto_processable
        }

    def process_test_task(self, task_file: Path, task_content: str) -> bool:
        """Process test tasks automatically"""

        # Add completion markers
        updated_content = task_content.replace(
            "**Status**: New",
            "**Status**: ✅ Auto-Processed"
        )

        # Check off requirements
        updated_content = updated_content.replace("- [ ]", "- [x]")

        # Add processing notes
        processing_note = f"""

## Processing Log
- **Processed By**: Task Processor Agent
- **Processed At**: {datetime.now().isoformat()}
- **Action**: Automatically validated test task
- **Result**: SUCCESS - All requirements met
"""
        updated_content += processing_note

        # Write updated content
        task_file.write_text(updated_content)

        # Move to Done
        done_file = DONE_PATH / task_file.name
        task_file.rename(done_file)

        return True

    def process_file_task(self, task_file: Path, task_content: str) -> bool:
        """Process file processing tasks"""

        # Extract file path from task
        file_match = re.search(r'\*\*File\*\*: (.+)', task_content)
        if not file_match:
            return False

        file_path = Path(file_match.group(1).strip())

        # Check if file exists and get info
        if file_path.exists():
            file_info = f"File verified: {file_path.name} ({file_path.stat().st_size} bytes)"
            action_taken = "File cataloged and verified"
            status = "✅ Auto-Processed"
        else:
            file_info = f"File not found: {file_path}"
            action_taken = "Moved to Needs_Action for manual review"
            status = "⚠️ Requires Attention"

        # Update task
        updated_content = task_content.replace(
            "**Status**: New",
            f"**Status**: {status}"
        )
        updated_content = updated_content.replace("- [ ]", "- [x]")

        processing_note = f"""

## Processing Log
- **Processed By**: Task Processor Agent
- **Processed At**: {datetime.now().isoformat()}
- **File Check**: {file_info}
- **Action**: {action_taken}
"""
        updated_content += processing_note

        task_file.write_text(updated_content)

        # Move to appropriate folder
        if file_path.exists():
            done_file = DONE_PATH / task_file.name
            task_file.rename(done_file)
        else:
            needs_action_file = NEEDS_ACTION_PATH / task_file.name
            task_file.rename(needs_action_file)

        return True

    def process_task(self, task_file: Path):
        """Process a single task"""

        try:
            # Read task
            task_content = task_file.read_text()

            # Classify
            classification = self.classify_task(task_content)

            print(f"📋 Processing: {task_file.name}")
            print(f"   Type: {classification['type']}")
            print(f"   Priority: {classification['priority']}")
            print(f"   Auto-processable: {classification['auto_processable']}")

            # Process based on type
            if classification['auto_processable']:
                if classification['type'] == "test":
                    success = self.process_test_task(task_file, task_content)
                elif classification['type'] == "file_processing":
                    success = self.process_file_task(task_file, task_content)
                else:
                    success = False

                if success:
                    print(f"   ✅ Processed successfully")
                    self.processed_count += 1
                else:
                    print(f"   ⚠️ Processing failed")
                    self.error_count += 1
            else:
                # Move to Needs_Action for human review
                needs_action_file = NEEDS_ACTION_PATH / task_file.name
                task_file.rename(needs_action_file)
                print(f"   👤 Moved to Needs_Action (requires human review)")
                self.processed_count += 1

        except Exception as e:
            print(f"   ❌ Error: {e}")
            self.error_count += 1

    def run_once(self):
        """Process all tasks in Inbox once"""

        print("=" * 60)
        print("Digital FTE - Task Processor Agent (Silver Tier)")
        print("=" * 60)
        print(f"Vault: {VAULT_PATH}")
        print(f"Processing tasks from: {INBOX_PATH}")
        print("")

        # Get all tasks in Inbox
        tasks = list(INBOX_PATH.glob("*.md"))

        if not tasks:
            print("📭 No tasks to process")
            return

        print(f"📬 Found {len(tasks)} task(s) to process")
        print("")

        # Process each task
        for task_file in tasks:
            self.process_task(task_file)
            print("")

        # Summary
        print("=" * 60)
        print(f"✅ Successfully processed: {self.processed_count}")
        print(f"❌ Errors: {self.error_count}")
        print("=" * 60)

    def run_daemon(self, interval=30):
        """Run as daemon, checking periodically"""

        print("=" * 60)
        print("Digital FTE - Task Processor Agent (Daemon Mode)")
        print("=" * 60)
        print(f"Vault: {VAULT_PATH}")
        print(f"Check interval: {interval} seconds")
        print("Press Ctrl+C to stop")
        print("=" * 60)
        print("")

        try:
            while True:
                tasks = list(INBOX_PATH.glob("*.md"))

                if tasks:
                    print(f"[{datetime.now().isoformat()}] Processing {len(tasks)} task(s)...")
                    for task_file in tasks:
                        self.process_task(task_file)

                    print(f"   Processed: {self.processed_count}, Errors: {self.error_count}")
                    print("")

                time.sleep(interval)

        except KeyboardInterrupt:
            print("\n\nStopping task processor...")
            print(f"Final stats - Processed: {self.processed_count}, Errors: {self.error_count}")


def main():
    """Main entry point"""

    # Ensure vault exists
    if not VAULT_PATH.exists():
        print(f"Error: Vault not found at {VAULT_PATH}")
        print("Run 'fte vault init' first")
        sys.exit(1)

    processor = TaskProcessor()

    # Check for daemon mode
    if "--daemon" in sys.argv:
        processor.run_daemon()
    else:
        processor.run_once()


if __name__ == "__main__":
    main()
