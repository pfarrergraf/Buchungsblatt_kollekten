"""Zeigt den Body der E-Mails an, die nicht geparst werden konnten."""
import json
from pathlib import Path
import win32com.client

# EntryIDs der fehlgeschlagenen E-Mails (aus dem Log)
FAILED_IDS = [
    "00000000709CC58678EE284F86AA07B6BF51A59B07000AFE130D7EB1474C80A21F25BDBB3F59007B7AA2443800003ED6CC2C4045174EB550618D417715A10004DCE2E0F20000",
    "00000000709CC58678EE284F86AA07B6BF51A59B07000AFE130D7EB1474C80A21F25BDBB3F59007B7AA2443800003ED6CC2C4045174EB550618D417715A10004DCE2E0D40000",
    "00000000709CC58678EE284F86AA07B6BF51A59B07000AFE130D7EB1474C80A21F25BDBB3F59007B7AA2443800003ED6CC2C4045174EB550618D417715A10004B94AF0050000",
]

outlook = win32com.client.Dispatch("Outlook.Application")
ns = outlook.GetNamespace("MAPI")

for entry_id in FAILED_IDS:
    try:
        msg = ns.GetItemFromID(entry_id)
        print(f"\n{'='*60}")
        print(f"Betreff: {msg.Subject}")
        print(f"Empfangen: {msg.ReceivedTime}")
        print(f"Body (repr):\n{repr(msg.Body[:500])}")
        print(f"\nBody (plain):\n{msg.Body[:500]}")
    except Exception as e:
        print(f"Fehler bei {entry_id[:20]}...: {e}")
