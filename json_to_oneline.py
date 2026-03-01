"""
json_to_oneline.py — Helper to convert a Google service account JSON key to one line.

Usage:
  1. Run:  python json_to_oneline.py
  2. It will ask you to drag-and-drop the JSON file path
  3. Copy the output → paste as GOOGLE_CREDENTIALS_JSON in GitHub Secrets
"""
import json
import sys

print("=" * 60)
print("Google Service Account JSON -> One Line Converter")
print("=" * 60)

# Try to get path from argument or prompt
if len(sys.argv) > 1:
    path = sys.argv[1].strip().strip('"').strip("'")
else:
    print("\nPaste the full path to your downloaded JSON key file.")
    print('(e.g. C:\\Users\\akash\\Downloads\\job-hunt-automation-abc123.json)')
    print()
    path = input("File path: ").strip().strip('"').strip("'")

try:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    one_line = json.dumps(data)

    print("\n" + "=" * 60)
    print("SUCCESS! Copy EVERYTHING between the lines below:")
    print("=" * 60)
    print(one_line)
    print("=" * 60)
    print("\nPaste that as the value for GOOGLE_CREDENTIALS_JSON in GitHub Secrets.")
    print("(It should start with {\"type\":\"service_account\" ...)")

except FileNotFoundError:
    print(f"\nERROR: File not found: {path}")
    print("Make sure you copied the full path correctly.")
except json.JSONDecodeError:
    print(f"\nERROR: File is not valid JSON. Did you select the right file?")
except Exception as e:
    print(f"\nERROR: {e}")

input("\nPress Enter to close...")
