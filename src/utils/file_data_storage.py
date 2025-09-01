from dataclasses import asdict
from datetime import datetime
import json
from pathlib import Path
from src.core.ticket_processor import TicketData
from src.integrations.deepseek_client import IssueAnalysis


def dataclass_to_json(data) -> str:
    def default(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return str(obj)
    try:
        return json.dumps(asdict(data), default=default, indent=2)
    except:
        return str(data)

def get_data_category(data):
    if isinstance(data, TicketData):
        return "ticket_data"
    elif isinstance(data, IssueAnalysis):
        return "issue_analysis"
    elif data.__class__.__name__ == 'ClaudeExecutionResult':
        return "claude_code_results"
    else:
        return "no_category"
        
def build_data_file_path(identifier, data_category):
    return Path(f"fetched_data/tickets/{identifier}/{data_category}")

def log_data_to_file(data, identifier, category=None) -> None:
    # Save ticket_data to file
    try:
        if category:
            data_category = category
        else:
            data_category = get_data_category(data)
        
        output_dir = build_data_file_path(identifier, data_category)
        output_dir.mkdir(parents=True, exist_ok=True)


        ticket_data_path = output_dir / "data.txt"
        with ticket_data_path.open("w", encoding="utf-8") as f:
            f.write(dataclass_to_json(data))
            print(f"successfully write data to file {ticket_data_path}")
            return str(ticket_data_path)
    except Exception as e:
        print(f"ERROR: Can not log data to file {identifier} error_message {e}")