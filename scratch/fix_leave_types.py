import sys
from pathlib import Path

# Add project root to path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from owl.load.database import get_session
from sqlalchemy import text

TARGET_TYPES = [
    "MATERNITY",
    "COMPASSIONATE",
    "PATERNITY",
    "SICK",
    "ANNUAL",
    "CASUAL AFTER ANNUAL",
    "PRE-RETIREMENT LEAVE",
    "EXAM"
]

def clean_leave_types():
    with get_session() as session:
        # 1. Fetch all current types
        current_types = session.execute(text("SELECT leave_type_id, leave_type_name FROM leave_types")).fetchall()
        
        # 2. Insert the target types if they don't exist, and keep track of their IDs
        target_map = {}
        for t_name in TARGET_TYPES:
            # Check if it exists exactly (case-insensitive)
            existing = session.execute(text("SELECT leave_type_id FROM leave_types WHERE UPPER(leave_type_name) = UPPER(:name)"), {"name": t_name}).scalar()
            if existing:
                target_map[t_name] = existing
                # Make sure the case is correct
                session.execute(text("UPDATE leave_types SET leave_type_name = :name WHERE leave_type_id = :id"), {"name": t_name, "id": existing})
            else:
                session.execute(text("INSERT INTO leave_types (leave_type_name) VALUES (:name)"), {"name": t_name})
                new_id = session.execute(text("SELECT leave_type_id FROM leave_types WHERE leave_type_name = :name"), {"name": t_name}).scalar()
                target_map[t_name] = new_id
        
        # 3. Map old types to the target types
        for old_id, old_name in current_types:
            norm_name = old_name.upper().strip().replace(" LEAVE", "")
            
            # Special case mapping
            if "PRE-RETIREMENT" in norm_name or "PRERETIREMENT" in norm_name:
                mapped_target = "PRE-RETIREMENT LEAVE"
            elif "CASUAL AFTER" in norm_name:
                mapped_target = "CASUAL AFTER ANNUAL"
            elif "CASUAL BEFORE" in norm_name:
                mapped_target = "ANNUAL"
            elif "ANNUAL" in norm_name:
                mapped_target = "ANNUAL"
            elif "MATERNITY" in norm_name:
                mapped_target = "MATERNITY"
            elif "COMPASSIONATE" in norm_name:
                mapped_target = "COMPASSIONATE"
            elif "PATERNITY" in norm_name:
                mapped_target = "PATERNITY"
            elif "SICK" in norm_name:
                mapped_target = "SICK"
            elif "EXAM" in norm_name:
                mapped_target = "EXAM"
            else:
                mapped_target = None
                
            if mapped_target and old_id != target_map[mapped_target]:
                new_id = target_map[mapped_target]
                print(f"Mapping '{old_name}' (ID {old_id}) to '{mapped_target}' (ID {new_id})")
                
                # Update any existing records to point to the new ID
                session.execute(text("UPDATE leave_records SET leave_type_id = :new_id WHERE leave_type_id = :old_id"), 
                                {"new_id": new_id, "old_id": old_id})
                
                # Delete the old type
                session.execute(text("DELETE FROM leave_types WHERE leave_type_id = :old_id"), {"old_id": old_id})
                
        session.commit()
        print("Leave types successfully consolidated!")
        
        # Print final types
        final_types = session.execute(text("SELECT leave_type_id, leave_type_name FROM leave_types")).fetchall()
        print("Final leave types in DB:")
        for r in final_types:
            print(f"{r[0]}: {r[1]}")

if __name__ == "__main__":
    clean_leave_types()
